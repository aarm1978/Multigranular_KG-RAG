"""Offline final relation replay, observed candidate coverage and unsampled evaluation frames."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile

import yaml
from src.evaluation import step14_representation_overlay as overlay

source = overlay.ROOT
prior, prep, w = overlay.prior, overlay.prep, overlay.w
ROOT = w.BASE / "final-alignment/v1"
ID = re.compile(prior.base.ALIAS + r"(?!\w)")
LABEL = re.compile(r"\s*\(([^():]*)\)")
JOIN = re.compile(r"\s*(?:,\s*(?:and\s+)?|and\s+|[/;&–—-]\s*)")


def aliases(text: str) -> list[str]:
    """Read only leading explicit IDs. Never interpolate ranges or scan quotation tails."""
    text = text.strip()
    ids = []
    pos = 0
    while match := ID.match(text, pos):
        ids.append(match[0])
        pos = match.end()
        label = LABEL.match(text, pos)
        if label:
            if ID.search(label[1]):
                also = re.fullmatch(r"(?:[^;]*;\s*)?also\s+(" + prior.base.ALIAS + r")", label[1])
                if not also or ID.search(label[1].split("also")[0]):
                    return []
                ids.append(also[1])
            pos = label.end()
        tail = text[pos:]
        if not tail.strip() or tail.lstrip().startswith(":"):
            return ids
        sep = JOIN.match(text, pos)
        if sep and ID.match(text, sep.end()):
            pos = sep.end()
            continue
        # Narrative suffixes describe the citations already read. An unfinished
        # list, alternative, or malformed next ID is not an explanatory suffix.
        if re.match(r"^(?:\s+|,\s+)(?!and\b|or\b|O\d|also\b)[A-Za-z]", tail):
            return ids
        return []
    return []


def replay(value, binding):
    """Keep original strings, normalized citations and independent item dispositions."""
    adapted = deepcopy(value)
    for item in adapted["items"]:
        refs = []
        for text in item["evidence"]:
            refs.extend(aliases(text) or [text])
        item["evidence"] = refs
    validated = prep.validate(adapted, binding)
    rows = []
    for i, entry in enumerate(validated["items"]):
        item = value["items"][i]
        case = binding["cases"][item["case"]]
        citations = []
        for text in item["evidence"]:
            for ref in aliases(text) or [text]:
                citations.append(
                    dict(
                        original=text,
                        alias=ref,
                        binding=binding["evidence"].get(ref),
                        caseBound=ref in case["evidence"],
                    )
                )
        rows.append(
            dict(
                index=i,
                case=item["case"],
                original=item,
                candidateKey=case["key"],
                originalSides=case["sides"],
                reasons=entry["reasons"],
                evidence=citations,
            )
        )
    return rows


def batch_rows(read, pin):
    """Compare native Batch bodies and historical receipts before applying the final contract."""
    folder = source / "batch-001"
    execution = folder / "execution"
    requests = list(w.r.rows(read(folder, "requests.jsonl")))
    w.require(requests == list(w.r.rows(pin(execution / "batch-input.jsonl"))), "SUBMISSION_DRIFT")
    native = {}
    for r in w.r.rows(pin(execution / "output_file_id.jsonl")):
        uid = r["custom_id"]
        w.require(uid not in native and r["response"]["status_code"] == 200, "BATCH_RESULT_DRIFT")
        native[uid] = r["response"]["body"]
    judgments = []
    for req in requests:
        uid = req["custom_id"]
        raw_path = pin(execution / (uid + ".response.json"))
        raw = w.live.load(raw_path)
        w.require(raw == native.pop(uid) and raw["status"] == "completed", "RAW_RESPONSE_DRIFT")
        value = w.transport.decode(w.live.provider.extract_model_output(raw))
        binding_path = read(folder, "bindings/" + uid + ".json")
        binding = w.live.load(binding_path)
        receipt = w.live.load(pin(execution / (uid + ".validation.json")))
        old = prior.validate(value, binding)
        w.require(all(receipt[k] == v for k, v in old.items()), "VALIDATION_DRIFT")
        w.require(
            Counter(i["case"] for i in value["items"]) == Counter(list(binding["cases"])),
            "CASE_ACCOUNTING",
        )
        for row, previous in zip(replay(value, binding), old["items"]):
            row.update(
                unit=uid,
                rawResponse=str(raw_path),
                sourceBinding=str(binding_path),
                priorReasons=previous["reasons"],
                disposition="mechanically_unresolved" if row["reasons"] else row["original"]["outcome"],
            )
            judgments.append(row)
    w.require(not native and len(requests) == 897 and len(judgments) == 2520, "BATCH_COVERAGE")
    return judgments


def coverage_state(projected, related):
    """Classify one original candidate observation, ignoring direction only for coverage."""
    if projected[0] == projected[1]:
        return "identity"
    return "typed_relation" if tuple(sorted(projected)) in related else "without_direct_alignment"


def run(output):
    """Produce complete frames from verified sources in a fresh local package."""
    w.require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    prior.identity.f.replay.verify(source)
    pins = {}

    def pin(p):
        if str(p) not in pins:
            pins[str(p)] = w.r.identity.sha(p)
        return p

    manifests = {}

    def read(folder, name):
        if folder not in manifests:
            manifests[folder] = w.live.load(pin(folder / "manifest.json"))["outputHashes"]
        path = pin(folder / name)
        w.require(pins[str(path)] == manifests[folder][name], "INPUT_DRIFT:" + name)
        return path

    pin(Path(__file__).resolve().relative_to(Path.cwd()))
    spec = yaml.safe_load(pin(w.SPEC).read_text())
    w.require(
        pins[str(w.SPEC)] == "6df101620e6931195b1fe5eb665ff15293f702004ca155c3cdba65d63c2dd2b5",
        "ONTOLOGY_DRIFT",
    )
    hierarchy = w.ancestors(spec)
    sigs = {r["id"]: r for r in spec["relations"]}
    groups = list(w.r.rows(read(source, "identity-groups.jsonl")))
    group_index = {g["groupID"]: g for g in groups}
    owner = {o: g["groupID"] for g in groups for o in g["occurrenceIDs"]}
    w.require(len(owner) == sum(len(g["occurrenceIDs"]) for g in groups), "GROUP_OVERLAP")
    provenance_file = read(w.BASE / "referent-groups/v1", "members.jsonl")
    members = {m["occurrenceID"]: m for m in w.r.rows(provenance_file)}
    classes = {o: m["ontologyClass"] for o, m in members.items()}
    classes.update({gid: g["ontologyClass"] for gid, g in group_index.items()})
    scope = prep.closure.rec.d.ab.group_scope
    earlier_groups = read(prep.closure.ROOT, "groups.jsonl")
    earlier = {r["groupID"]: (line, r) for line, r in enumerate(w.r.rows(earlier_groups), 1)}
    residual_items = read(source, "assignments.jsonl")
    residual_refs = {
        (r["unit"], r["index"]): (line, r["assessment"]["occurrenceIDs"])
        for line, r in enumerate(w.r.rows(residual_items), 1)
    }
    identity = []
    approvals = []
    for g in groups:
        ids = g["occurrenceIDs"]
        w.require(scope([members[o] for o in ids]) == g["identityScope"], "IDENTITY_SCOPE")
        frame = dict(
            g,
            size=len(ids),
            memberEvidenceFile=str(provenance_file),
            membershipSource=str(source / "identity-groups.jsonl"),
        )
        frame["sourceFamilies"] = sorted({f for o in ids for f in members[o]["sourceFamilies"]})
        if g["groupID"] in earlier:
            line, original = earlier[g["groupID"]]
            w.require(set(original["occurrenceIDs"]) == set(ids), "EARLIER_MEMBERSHIP_DRIFT")
            frame["decisionEvidence"] = [dict(file=str(earlier_groups), line=line)]
        else:
            pointers = []
            for ref in g["support"]:
                line, source_ids = residual_refs[tuple(ref)]
                w.require(set(source_ids) == set(ids), "RESIDUAL_MEMBERSHIP_DRIFT")
                pointers.append(dict(file=str(residual_items), line=line, unit=ref[0], index=ref[1]))
            w.require(pointers, "MISSING_IDENTITY_SUPPORT")
            frame["decisionEvidence"] = pointers
        if g["authority"] == "researcher_approved_exact":
            w.require(g["approval"] and g["provisionalTarget"] is None, "APPROVAL_AUTHORITY")
            approvals.append(frame)
        else:
            w.require(g["authority"] == "automatic_prediction", "UNKNOWN_AUTHORITY")
            frame["humanVerified"] = False
            identity.append(frame)
    judgments = batch_rows(read, pin)
    old_file = read(prior.base.ROOT, "judgments.jsonl")
    old = {(r["unit"], r["case"], r["index"]): r for r in w.r.rows(old_file)}
    triples = defaultdict(list)

    def include(row, expected=None):
        """Join cited witnesses to both original sides and recheck frozen signature and direction."""
        w.require(
            not row["reasons"] and row["original"]["outcome"] == "relation", "INVALID_RELATION_SUPPORT"
        )
        key, reason = prior.base.triple(row, owner, classes, sigs, hierarchy)
        w.require(
            key and not reason and (expected is None or tuple(expected) == key), "PROJECTED_TRIPLE_DRIFT"
        )
        if expected is None:
            w.require(tuple(sorted(key[::2])) == tuple(row["candidateKey"]), "CANDIDATE_KEY_DRIFT")
        sides = row["originalSides"]
        cited = {e["binding"]["occurrenceID"] for e in row["evidence"]}
        witnesses = [sorted(cited.intersection(s)) for s in sides]
        if row["original"]["direction"] == "reverse":
            witnesses.reverse()
        triples[key].append(
            dict(
                unit=row["unit"],
                case=row["case"],
                index=row["index"],
                signature=row["original"]["signature"],
                direction=row["original"]["direction"],
                rawResponse=str(pin(Path(row["rawResponse"]))),
                sourceBinding=str(pin(Path(row["sourceBinding"]))),
                evidence=row["evidence"],
                citedEndpoints=witnesses,
                candidateKey=row["candidateKey"],
            )
        )

    for r in w.r.rows(read(source, "retained-relations.jsonl")):
        for s in r["support"]:
            include(old[s["unit"], s["case"], s["index"]], r["triple"])
    for row in judgments:
        if row["disposition"] == "relation":
            include(row)
    relations = []
    used = set(owner)
    for (a, p, b), support in sorted(triples.items()):
        witnesses = {o for s in support for side in s["citedEndpoints"] for o in side}
        used.update(witnesses)
        relations.append(
            dict(
                subject=a,
                predicate=p,
                object=b,
                authority="automatic_prediction",
                humanVerified=False,
                endpointClasses=[classes[a], classes[b]],
                endpointSizes=[
                    len(group_index[k]["occurrenceIDs"]) if k in group_index else 1 for k in (a, b)
                ],
                evidenceScope=scope([members[o] for o in witnesses]),
                citedOccurrences=len(witnesses),
                support=support,
            )
        )
    related = {tuple(sorted((a, b))) for a, _, b in triples}
    coverage = []
    overall = Counter()
    residual = Counter()
    for r in w.r.rows(read(source, "pair-coverage.jsonl")):
        ends = [owner.get(o, o) for o in r["original"]]
        w.require(ends == r["after"], "PAIR_PROJECTION_DRIFT")
        state = coverage_state(ends, related)
        overall[state] += 1
        if r["residual"]:
            residual[state] += 1
        coverage.append(dict(r, finalAlignment=state))
    w.require(
        len({r["pairID"] for r in coverage}) == len(coverage) == 73416
        and sum(residual.values()) == 14226,
        "PAIR_ACCOUNTING",
    )
    summary = dict(
        requests=897,
        cases=len(judgments),
        originalOutcomes=Counter(r["original"]["outcome"] for r in judgments),
        unresolved=[
            dict(unit=r["unit"], case=r["case"], reasons=r["reasons"]) for r in judgments if r["reasons"]
        ],
        priorAdmissible=sum(not r["priorReasons"] for r in judgments),
        recovered=Counter(r["disposition"] for r in judgments if r["priorReasons"] and not r["reasons"]),
        terminal=Counter(r["disposition"] for r in judgments),
        identityGroups=len(groups),
        identityOccurrences=len(owner),
        automaticGroups=len(identity),
        historicalApprovals=len(approvals),
        uniqueRelations=len(triples),
        predicates=Counter(p for _, p, _ in triples),
        originalPairCoverage=overall,
        residualPairCoverage=residual,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "package"
        stage.mkdir()
        for name, rows in [
            ("judgments", judgments),
            ("automatic-identity-frame", identity),
            ("historical-approvals", approvals),
            ("typed-relation-frame", relations),
            ("occurrence-provenance", (members[o] for o in sorted(used))),
            ("pair-coverage", coverage),
        ]:
            prep.emit(stage / (name + ".jsonl"), rows)
        w.live.save(stage / "summary.json", summary)
        w.live.save(
            stage / "manifest.json",
            dict(inputHashes=pins, outputHashes={p.name: w.r.identity.sha(p) for p in stage.iterdir()}),
        )
        stage.rename(output)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["close", "verify"])
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    print(
        json.dumps(
            (run if args.mode == "close" else prior.identity.f.replay.verify)(args.output), indent=2
        )
    )
