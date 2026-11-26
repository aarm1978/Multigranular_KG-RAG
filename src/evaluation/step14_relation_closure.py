"""Replay the final relation Batch and prepare the scoped pre-production decision ledger."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile

import yaml
from src.evaluation import step14_final_relations as prep

w = prep.w
ROOT = w.BASE / "relation-closure/v1"
VERSION_GROUP = "step14-provisional:eece01e553d9720d7de11d332d1d2e0aa41831e95d0604d2606811a22fa49c11"
GENERIC = "publication-extraction-plan-v01-71c58f2bf023b26dda9ace78#node#node-0001"
ALIAS = r"O[1-9]\d*Q[1-9]\d*"
PREFIX = re.compile(
    rf"(?P<ids>{ALIAS}(?:(?:\s*/\s*|\s+and\s+|\s*,\s*){ALIAS})*)(?:\s*\((?P<label>[^()]*)\))?"
)


def aliases(text):
    """Parse explicit citation prefixes. Never search the reproduced quotation for IDs."""
    prefix = text.partition(":")[0].strip()
    match = PREFIX.fullmatch(prefix)
    if not match:
        return []
    ids = re.findall(ALIAS, match["ids"])
    label = match["label"] or ""
    if re.search(ALIAS, label):
        additional = re.fullmatch(rf"[^;]*;\s*also\s+({ALIAS})", label)
        if not additional or re.search(ALIAS, label.split(";")[0]):
            return []
        ids.append(additional[1])
    return ids


def replay_unit(uid, value, binding):
    """Validate a derived alias view while retaining native strings and authoritative excerpts."""
    adapted = deepcopy(value)
    local = deepcopy(binding)
    traces = []
    for original, item in zip(value["items"], adapted["items"]):
        case = binding["cases"][item["case"]]
        trace = []
        refs = []
        for text in original["evidence"]:
            names = aliases(text)
            # Unrecognized strings remain invalid under the original validator.
            refs.extend(names or [text])
            for name in names:
                source = binding["evidence"].get(name)
                scope = "case" if name in case["evidence"] else "out_of_scope"
                if (
                    (uid, item["case"], name) == ("T0018", "P2", "O2Q2")
                    and source
                    and any(source["occurrenceID"] in side for side in case["sides"])
                    and any(
                        binding["evidence"][e]["occurrenceID"] == source["occurrenceID"]
                        for e in case["evidence"]
                    )
                    and scope == "out_of_scope"
                ):
                    scope = "same_request_exact_endpoint"
                    local["cases"][item["case"]]["evidence"].append(name)
                trace.append(dict(original=text, alias=name, scope=scope, binding=source))
        item["evidence"] = refs
        traces.append(trace)
    report = prep.validate(adapted, local)
    rows = []
    for index, result in enumerate(report["items"]):
        item = value["items"][index]
        case = binding["cases"][item["case"]]
        rows.append(
            dict(
                unit=uid,
                index=index,
                case=item["case"],
                original=item,
                evidence=traces[index],
                originalSides=case["sides"],
                candidateKey=case["key"],
                reasons=result["reasons"],
            )
        )
    return rows


def correction(groups, rows, members):
    """Apply only the researcher-authorized T0118 supersession after checking all five witnesses."""
    old = groups[VERSION_GROUP]
    exceptions = [r for r in rows if r["unit"] == "T0118"]
    kept = set()
    for r in exceptions:
        a, b = r["originalSides"]
        cited = {e["binding"]["occurrenceID"] for e in r["evidence"] if e["binding"]}
        w.require(
            not r["reasons"]
            and r["original"]["outcome"] == "material_exception"
            and r["candidateKey"] == [VERSION_GROUP, VERSION_GROUP, *a, *b]
            and len(a) == 1
            and b == [GENERIC]
            and {a[0], GENERIC} <= cited,
            "EXCEPTION_DRIFT",
        )
        kept.add(a[0])
    w.require(
        len(exceptions) == len(kept) == 5
        and GENERIC not in kept
        and kept | {GENERIC} == set(old["occurrenceIDs"])
        and old["authority"] == "automatic_prediction",
        "AUTHORIZED_SCOPE_DRIFT",
    )
    rejected = [r for r in rows if r["unit"] == "T0117"]
    w.require(
        len(rejected) == 8
        and all(
            not r["reasons"]
            and r["original"]["outcome"] == "mistaken"
            and len(groups[r["candidateKey"][0]]["occurrenceIDs"]) == 245
            for r in rejected
        )
        and len({r["candidateKey"][0] for r in rejected}) == 1,
        "PRESERVED_GENERAL_GROUP",
    )
    ids = sorted(kept)
    gid = "step14-provisional:" + w.live.token(ids)
    replacement = dict(
        authority=old["authority"],
        groupID=gid,
        occurrenceIDs=ids,
        ontologyClass=old["ontologyClass"],
        identityScope=prep.closure.rec.d.ab.group_scope([members[o] for o in ids]),
        supersedes=VERSION_GROUP,
        support=[[r["unit"], r["case"], r["index"]] for r in exceptions],
    )
    return replacement, dict(
        originalGroup=old,
        replacement=replacement,
        excludedOccurrence=GENERIC,
        authority="Researcher-authorized T0118 correction: retain five v1.2 baseline occurrences and unconsolidate the generic occurrence.",
        excludedSource=members[GENERIC],
        decisions=replacement["support"],
    )


def triple(row, owner, classes, signatures, hierarchy):
    """Project only actually cited endpoint occurrences, preserving subject/object direction."""
    item = row["original"]
    witnesses = {c["binding"]["occurrenceID"] for c in row["evidence"] if c["binding"]}
    sides = [sorted(set(side) & witnesses) for side in row["originalSides"]]
    projected = prep.project(sides, owner)
    if projected is None or projected[0] == projected[1]:
        return None, "AMBIGUOUS_OR_SELF_PROJECTION"
    a, b = projected if item["direction"] == "forward" else projected[::-1]
    sig = signatures[item["signature"]]
    if not (
        w.fits(classes[a], sig["domain"], hierarchy) and w.fits(classes[b], sig["range"], hierarchy)
    ):
        return None, "FINAL_SIGNATURE_MISMATCH"
    return (a, sig["name"], b), None


def run(output):
    """Verify original artifacts and atomically publish the complete unsampled proposal population."""
    w.require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    prep.source_pins()
    prep.final.replay.verify(prep.ROOT)
    manifest = w.live.load(prep.ROOT / "manifest.json")
    pins = dict(manifest["inputHashes"])
    pins.update({str(prep.ROOT / p): h for p, h in manifest["outputHashes"].items()})

    def pin(path):
        """Bind execution evidence and the replay implementation by byte hash."""
        pins[str(path)] = w.r.identity.sha(path)
        return path

    pin(prep.ROOT / "manifest.json")
    pin(Path(__file__).resolve().relative_to(Path.cwd()))
    execution = prep.ROOT / "execution"
    requests = list(w.r.rows(prep.ROOT / "requests.jsonl"))
    submitted = list(w.r.rows(pin(execution / "batch-input.jsonl")))
    w.require(submitted == requests, "SUBMITTED_REQUEST_DRIFT")
    native = {}
    for result in w.r.rows(pin(execution / "output_file_id.jsonl")):
        uid = result["custom_id"]
        w.require(uid not in native and result["response"]["status_code"] == 200, "BATCH_BINDING")
        native[uid] = result["response"]["body"]
    rows = []
    baseline = Counter()
    for req in requests:
        uid = req["custom_id"]
        raw = w.live.load(pin(execution / (uid + ".response.json")))
        w.require(native.pop(uid) == raw and raw["status"] == "completed", "RAW_DRIFT")
        value = w.transport.decode(w.live.provider.extract_model_output(raw))
        binding = w.live.load(prep.ROOT / "bindings" / (uid + ".json"))
        report = w.live.load(pin(execution / (uid + ".validation.json")))
        original = prep.validate(value, binding)
        w.require(all(report[k] == v for k, v in original.items()), "RECEIPT_DRIFT")
        w.require(
            Counter(i["case"] for i in value["items"]) == Counter(list(binding["cases"])),
            "FROZEN_CASE_COVERAGE",
        )
        revised = replay_unit(uid, value, binding)
        for r, prev in zip(revised, original["items"]):
            r["priorReasons"] = prev["reasons"]
            r["rawResponse"] = str(execution / (uid + ".response.json"))
            r["sourceBinding"] = str(prep.ROOT / "bindings" / (uid + ".json"))
            baseline["rejected" if prev["reasons"] else "passed"] += 1
        rows.extend(revised)
    w.require(not native and len(requests) == 118 and len(rows) == 221, "POPULATION_DRIFT")
    groups = {g["groupID"]: g for g in w.r.rows(prep.SOURCE / "groups.jsonl")}
    members = {
        m["occurrenceID"]: m["originalMember"]
        for m in w.r.rows(prep.SOURCE / "occurrence-mappings.jsonl")
    }
    replacement, change = correction(groups, rows, members)
    del groups[VERSION_GROUP]
    groups[replacement["groupID"]] = replacement
    owner = {o: g["groupID"] for g in groups.values() for o in g["occurrenceIDs"]}
    w.require(
        len(groups) == 2195
        and len(owner) == sum(len(g["occurrenceIDs"]) for g in groups.values())
        and set(owner) == members.keys() - {GENERIC},
        "FINAL_MEMBERSHIPS",
    )
    spec = yaml.safe_load(w.SPEC.read_text())
    hierarchy = w.ancestors(spec)
    signatures = {s["id"]: s for s in spec["relations"]}
    classes = {e["occurrenceID"]: e["ontologyClass"] for e in w.r.rows(prep.ENDPOINTS)}
    classes.update({gid: g["ontologyClass"] for gid, g in groups.items()})
    totals = defaultdict(Counter)
    population = []
    for gid, g in groups.items():
        ids = g["occurrenceIDs"]
        scope = prep.closure.rec.d.ab.group_scope([members[o] for o in ids])
        w.require(
            scope == g["identityScope"]
            and w.fits(g["ontologyClass"], signatures["D-16"]["range"], hierarchy),
            "REPRESENTATION_DRIFT",
        )
        for k in (scope, g["authority"]):
            totals[k].update(groups=1, occurrences=len(ids))
        population.append(
            dict(
                groupID=gid,
                authority=g["authority"],
                occurrenceIDs=ids,
                ontologyClass=g["ontologyClass"],
                identityScope=scope,
                rangeCompatible=True,
                approval=g.get("approval"),
                sourceGroup=g.get("supersedes", gid),
                provisionalTarget=gid if g["authority"] == "automatic_prediction" else None,
                support=g["support"],
            )
        )
    relations = defaultdict(list)
    dispositions = Counter()
    for r in rows:
        outcome = r["original"]["outcome"]
        if not r["reasons"] and outcome == "relation":
            key, error = triple(r, owner, classes, signatures, hierarchy)
            if error:
                r["reasons"].append(error)
            else:
                r["projectedTriple"] = key
                relations[key].append(
                    dict(
                        unit=r["unit"], case=r["case"], index=r["index"], candidateKey=r["candidateKey"]
                    )
                )
        r["disposition"] = "mechanically_unresolved" if r["reasons"] else outcome
        dispositions[r["disposition"]] += 1
    summary = dict(
        requests=len(requests),
        judgments=len(rows),
        baseline=baseline,
        dispositions=dispositions,
        groups=len(groups),
        occurrences=len(owner),
        identityCounts=totals,
        uniqueRelations=len(relations),
        relationPredicates=Counter(k[1] for k in relations),
        predictedPredicates=Counter(
            signatures[r["original"]["signature"]]["name"]
            for r in rows
            if r["original"]["outcome"] == "relation"
        ),
        scopedCitations=sum(
            c["scope"] == "same_request_exact_endpoint" for r in rows for c in r["evidence"]
        ),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp) / "package"
        stage.mkdir()
        prep.emit(stage / "identity-groups.jsonl", population)
        prep.emit(stage / "judgments.jsonl", rows)
        prep.emit(
            stage / "relations.jsonl",
            (
                dict(subject=a, predicate=p, object=b, support=s, humanVerified=False)
                for (a, p, b), s in sorted(relations.items())
            ),
        )
        w.live.save(stage / "supersession.json", change)
        w.live.save(stage / "summary.json", summary)
        w.live.save(
            stage / "manifest.json",
            dict(inputHashes=pins, outputHashes={p.name: w.r.identity.sha(p) for p in stage.iterdir()}),
        )
        stage.rename(output)
    return summary


def main():
    """Build in a fresh directory or verify all pinned source and output hashes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "verify"))
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps((run if args.mode == "run" else prep.final.replay.verify)(args.output), indent=2))


if __name__ == "__main__":
    main()
