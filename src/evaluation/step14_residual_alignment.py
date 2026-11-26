"""Prepare one bounded residual whole-component Batch over the closed Step 14 population."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import re
import json
import math
from pathlib import Path
from statistics import quantiles
import tempfile
from unittest.mock import patch

from src.evaluation import step14_relation_closure as baseline

prep = baseline.prep
f = prep.final
w = f.w
ROOT = w.BASE / "residual-alignment/v1"
IDENTITY = {"same_entity_candidate", "abstain"}
original_evaluate = f.evaluate


def postings(read, pin):
    """Index actual request occurrences by execution stage; track the exploratory pilot separately."""
    index = defaultdict(set)
    pilot = defaultdict(set)

    def index_body(stage, request, aliases):
        ids = [x["occurrenceID"] for x in json.loads(request["body"]["input"])["occurrences"]]
        w.require(
            set(ids) == aliases.keys() and len(set(aliases.values())) == len(ids), "REQUEST_ALIAS_DRIFT"
        )
        for alias in ids:
            index[aliases[alias]].add(stage + "/" + request["custom_id"])

    folder = w.BASE / "alignment-workflow/prepared-v018-source-context"
    bindings = w.live.load(read(folder, "alias-bindings.json"))
    for r in w.r.rows(read(folder, "requests.jsonl")):
        index_body("alignment", r, bindings[r["custom_id"]])
    folder = w.BASE / "collective-adjudication/v4"
    paths = defaultdict(dict)
    for r in w.r.rows(read(folder, "unit-summaries.jsonl")):
        paths[Path(r["originalRequest"])][r["unitID"]] = r
    for path, units in paths.items():
        for r in w.r.rows(pin(path)):
            unit = units.pop(r["custom_id"])
            w.require(w.live.token(r["body"]) == unit["requestBodySha256"], "COLLECTIVE_BODY_DRIFT")
            index_body("collective", r, unit["aliasBindings"])
        w.require(not units, "MISSING_COLLECTIVE_UNIT")
    for folder in (f.previous.ROOT, f.ROOT):
        for r in w.r.rows(read(folder, "requests.jsonl")):
            b = w.live.load(read(folder, "bindings/" + r["custom_id"] + ".json"))
            index_body("component-" + folder.name, r, b["aliases"])
    folder = w.BASE / "anchor-pilot/prepared-v1"
    for r in w.r.rows(read(folder, "requests.jsonl")):
        for e in json.loads(r["body"]["input"])["occurrences"]:
            pilot[e["occurrenceID"]].add(r["custom_id"])
    return index, pilot


def classify(a, b, owner, relations, index, pilot):
    """Apply endpoint projection and request co-presence without inferring a pair decision."""
    key = tuple(sorted((owner.get(a, a), owner.get(b, b))))
    together = sorted(index[a] & index[b])
    direct = "identity" if key[0] == key[1] else "typed_relation" if key in relations else None
    return dict(
        projected=key,
        direct=direct,
        jointRequests=together,
        pilotRequests=sorted(pilot[a] & pilot[b]),
        residual=not direct and not together,
    )


def plan(edges, groups):
    """Use connected projected hypotheses to delimit questions, expanding each endpoint in full."""
    for refs, keys in f.previous.components(edges, edges):
        affected = [groups[k] for k in refs if k in groups]
        ids = sorted(o for k in refs for o in (groups[k]["occurrenceIDs"] if k in groups else [k]))
        yield ids, keys, affected


def normalize(value, evidence):
    """Resolve explicit E-alias prefixes with the final-closure grammar and exact local bindings."""
    normalized = deepcopy(value)
    for field in ("assessments", "relationLeads"):
        rows = normalized.get(field)
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            for k in (
                "supportingEvidenceIDs",
                "contradictoryEvidenceIDs",
                "qualifyingEvidenceIDs",
                "evidenceIDs",
            ):
                refs = row.get(k)
                if not isinstance(refs, list):
                    continue
                resolved = []
                for ref in refs:
                    if not isinstance(ref, str) or ref in evidence:
                        resolved.append(ref)
                        continue
                    prefix = ref.partition(":")[0]
                    # O-prefixed citations are foreign to this request namespace.
                    names = (
                        []
                        if re.search(baseline.ALIAS, prefix)
                        else baseline.aliases(re.sub(r"\bE(?=[1-9]\d*Q)", "O", prefix))
                    )
                    aliases = ["E" + name[1:] for name in names]
                    resolved.extend(
                        aliases if aliases and all(a in evidence for a in aliases) else [ref]
                    )
                row[k] = resolved
    return normalized


def validate(value, body, binding):
    """Reuse the frozen structured qualification and exact-membership safeguards."""
    result = original_evaluate(normalize(value, binding["evidence"]), body, binding)
    assignments = [prep.closure.corrected(r) for r in result["assignments"]]
    for row in assignments:
        row["originalModelItem"] = value["assessments"][row["itemIndex"]]
    leads = []
    for lead in result["relationLeads"]:
        # Schema failures stay localized; endpoint recovery only handles well-formed leads.
        if any(
            e not in ("NEEDS_TWO_INDEPENDENT_ASSIGNMENTS", "INVALID_ENDPOINT_EVIDENCE")
            for e in lead["reasons"]
        ):
            item = dict(original=lead, status="unresolved_lead", reasons=lead["reasons"])
        else:
            item = prep.closure.resolve_lead(lead, assignments, binding)
        item["originalModelItem"] = value["relationLeads"][lead["index"]]
        leads.append(item)
    admitted = {o for r in assignments if not r["reasons"] for o in r["occurrenceIDs"]}
    unresolved = sorted(set(binding["aliases"].values()) - admitted)
    complete = not unresolved and result["partitionAudit"]["partitionExact"]
    supersessions = []
    for target, ids in binding["priorTargets"].items():
        changed = [r for r in assignments if set(ids).intersection(r["occurrenceIDs"])]
        if not any(
            not r["reasons"]
            and r["category"] == "strict_identity"
            and set(r["occurrenceIDs"]) == set(ids)
            for r in changed
        ):
            supersessions.append(
                dict(
                    priorTarget=target,
                    oldMembership=ids,
                    replacementAssignmentIndices=[r["itemIndex"] for r in changed],
                    status="prospective_supersession"
                    if complete and all(r["category"] != "abstention" for r in changed)
                    else "unresolved_preserve_baseline",
                )
            )
    return dict(
        status="complete_prediction" if complete else "partial_prediction",
        assignments=assignments,
        partitionAudit=result["partitionAudit"],
        mechanicallyUnresolved=unresolved,
        supersessions=supersessions,
        relationLeads=leads,
        humanVerified=False,
        productionWrites=0,
    )


def prepare(output):
    """Write an immutable package only after reconstruction and exact coverage checks."""
    w.require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    f.replay.verify(baseline.ROOT)
    pins = {}

    def pin(path):
        if str(path) not in pins:
            pins[str(path)] = w.r.identity.sha(path)
        return path

    manifests = {}

    def read(folder, name):
        if folder not in manifests:
            manifests[folder] = w.live.load(pin(folder / "manifest.json"))["outputHashes"]
        path = pin(folder / name)
        w.require(pins[str(path)] == manifests[folder][name], "INPUT_DRIFT:" + name)
        return path

    pin(Path(__file__).resolve().relative_to(Path.cwd()))
    groups = {g["groupID"]: g for g in w.r.rows(read(baseline.ROOT, "identity-groups.jsonl"))}
    owner = {o: k for k, g in groups.items() for o in g["occurrenceIDs"]}
    relations = {
        tuple(sorted([r["subject"], r["object"]]))
        for r in w.r.rows(read(baseline.ROOT, "relations.jsonl"))
    }
    judged = {
        tuple(sorted(r["candidateKey"][:2]))
        for r in w.r.rows(read(baseline.ROOT, "judgments.jsonl"))
        if not r["reasons"]
    }
    index, pilot = postings(read, pin)
    phase = w.BASE / "adjudication-triage/v1"
    residual = []
    audit = []
    seen = set()
    edges = defaultdict(list)
    pair_counts = Counter()
    scopes = Counter()
    families = Counter()
    occurrences = set()
    referents = set()
    relation_keys = set()
    pilot_counts = Counter()
    for p in w.r.rows(read(phase, "pair-inventory.jsonl")):
        if p["coverageState"] != "validated_recommendation":
            continue
        a, b = p["occurrenceIDs"]
        cat = p["category"]
        pid = p["pairKeySha256"]
        w.require(pid not in seen, "DUPLICATE_INITIAL_PAIR")
        seen.add(pid)
        history = classify(a, b, owner, relations, index, pilot)
        audit.append(dict(pairID=pid, **history))
        if not history["residual"]:
            continue
        key = history["projected"]
        pair_counts[cat] += 1
        scopes[p["identityScope"]] += 1
        families["+".join(sorted(p["familyCombination"]))] += 1
        occurrences.update((a, b))
        referents.update(key)
        relation_keys.add(key)
        history["explicitPilotAssessments"] = []
        for uid in history["pilotRequests"]:
            path = pin(w.BASE / "anchor-pilot/prepared-v1/execution" / (uid + ".hypotheses.json"))
            for i, item in enumerate(w.live.load(path)["assessments"]):
                if {a, b} <= set(item["occurrenceIDs"]):
                    history["explicitPilotAssessments"].append(
                        dict(file=str(path), index=i, category=item["category"])
                    )
        if history["pilotRequests"]:
            pilot_counts[cat] += 1
        if cat in IDENTITY:
            edges[key].append(p)
        residual.append(
            dict(
                pair=p,
                **history,
                relationRoute="if_distinct_after_identity"
                if cat in IDENTITY
                else "different_entity_candidate",
                previouslyJudgedReferentPair=key in judged,
            )
        )
    w.require(
        len(seen) == 73416 and set(pair_counts) == IDENTITY | {"different_entities_candidate"},
        "INITIAL_POPULATION_DRIFT",
    )
    endpoints = {
        r["occurrenceID"]: r
        for r in w.r.rows(read(w.BASE / "unified-review-queue/v1", "endpoint-provenance.jsonl"))
    }
    members = {
        r["occurrenceID"]: r for r in w.r.rows(read(w.BASE / "referent-groups/v1", "members.jsonl"))
    }
    # Some protected group members were outside the selected review queue. Reuse
    # their already prepared literal windows, with the original occurrence hash.
    missing = {
        o
        for edge in edges
        for ref in edge
        for o in (groups[ref]["occurrenceIDs"] if ref in groups else [ref])
    } - endpoints.keys()
    for record in w.r.rows(read(w.BASE / "two-view-retrieval/v1", "occurrences.jsonl")):
        oid = record["occurrenceID"]
        if oid in missing:
            w.require(
                record["originalReference"]["recordSha256"]
                == members[oid]["originalReference"]["recordSha256"]
                and record["selectedEvidence"],
                "SUPPLEMENTAL_EVIDENCE_DRIFT",
            )
            endpoints[oid] = record
    w.require(missing <= endpoints.keys(), "INCOMPLETE_SOURCE_BINDINGS")
    sizes = Counter()
    inventory = []
    requests = []
    affected_counts = Counter()
    component_for = {}
    total_bytes = total_input = total_output = total_n = 0
    rates = []
    for req in w.r.rows(read(f.ROOT, "requests.jsonl")):
        template = req["body"]
        n = len(json.loads(template["input"])["occurrences"])
        usage = w.live.load(pin(f.ROOT / "execution" / (req["custom_id"] + ".response.json")))["usage"]
        total_bytes += len(w.live.encode(template))
        total_input += usage["input_tokens"]
        total_output += usage["output_tokens"]
        total_n += n
        rates.append(usage["output_tokens"] / n)
    high = quantiles(rates, n=100, method="inclusive")[94]
    output.parent.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp) / "package"
        stage.mkdir()
        for i, (ids, keys, affected) in enumerate(plan(edges, groups), 1):
            uid = f"X{i:04d}"
            n = len(ids)
            sizes[n] += 1
            pairs = [p for k in keys for p in edges[k]]
            for k in keys:
                component_for[k] = uid
            locks = []
            priors = {}
            for g in affected:
                affected_counts[g["authority"]] += 1
                if g["authority"] == "automatic_prediction":
                    priors[g["groupID"]] = g["occurrenceIDs"]
                else:
                    locks.append(g["occurrenceIDs"])
            hypotheses = sorted(
                set(tuple(sorted(h)) for h in [*(p["occurrenceIDs"] for p in pairs), *priors.values()])
            )
            body, aliases, sources = f.previous.request(ids, hypotheses, endpoints, members, template)
            evidence = f.replay.bind(
                json.loads(body["input"]),
                aliases,
                sources,
                {o: dict(endpoint=endpoints[o], member=members[o]) for o in ids},
            )
            body = f.final_body(body, aliases, locks, [])
            cap = min(f.MAX_OUTPUT, 1024 * math.ceil((2048 + 2 * high * n) / 1024))
            body["max_output_tokens"] = cap
            size = len(w.live.encode(body))
            f.pilot_preflight.check_schema_limits(body["text"]["format"]["schema"])
            w.require(
                size + cap + 2048 < f.CONTEXT and high * n < cap, "COMPONENT_RESOURCE_LIMIT:" + uid
            )
            requests.append(dict(custom_id=uid, url="/v1/responses", method="POST", body=body))
            w.live.save(
                stage / "bindings" / (uid + ".json"),
                dict(
                    aliases=aliases,
                    sources=sources,
                    evidence=evidence,
                    members={o: members[o] for o in ids},
                    protectedMemberships=locks,
                    priorTargets=priors,
                ),
            )
            inventory.append(
                dict(
                    unit=uid,
                    occurrences=n,
                    occurrenceIDs=ids,
                    projectedPairs=keys,
                    pairIDs=[p["pairKeySha256"] for p in pairs],
                    affectedGroups=[g["groupID"] for g in affected],
                    inputEstimate=math.ceil(size * total_input / total_bytes),
                    outputEstimate=math.ceil(n * total_output / total_n),
                    outputCap=cap,
                )
            )
        for r in residual:
            r["identityRequest"] = (
                component_for.get(r["projected"]) if r["pair"]["category"] in IDENTITY else None
            )
        w.require(
            sum(len(c["pairIDs"]) for c in inventory) == sum(pair_counts[k] for k in IDENTITY),
            "INCOMPLETE_IDENTITY_COVERAGE",
        )
        inp = sum(c["inputEstimate"] for c in inventory)
        out = sum(c["outputEstimate"] for c in inventory)
        caps = sum(c["outputCap"] for c in inventory)
        # Baseline-only workload scenario; actual new memberships and leads are unknown.
        prospective = relation_keys - judged
        affected_refs = {k for edge in edges for k in edge}
        recheck = []
        for row in w.r.rows(read(baseline.ROOT, "relations.jsonl")):
            recheck.append(
                dict(
                    **row, touchesIdentityComponent=bool({row["subject"], row["object"]} & affected_refs)
                )
            )
        summary = dict(
            initial=len(seen),
            residual=len(residual),
            byCategory=pair_counts,
            byScope=scopes,
            byFamily=families,
            exploratoryPilotJoint=pilot_counts,
            occurrences=len(occurrences),
            referents=len(referents),
            affectedGroups=affected_counts,
            identityProjectedPairs=len(edges),
            identityOriginalPairs=sum(pair_counts[k] for k in IDENTITY),
            requests=len(inventory),
            identityInputOccurrences=sum(n * v for n, v in sizes.items()),
            componentSizeHistogram=sizes,
            largest=sorted(((c["occurrences"], c["unit"]) for c in inventory), reverse=True)[:10],
            currentRelationPairs=len(relation_keys),
            baselineRelationPackingEstimate=len(w.pack_edges(prospective.copy(), limit=5)),
            baselineRelationsTouchingComponents=sum(r["touchesIdentityComponent"] for r in recheck),
            identityDistinctNominatedOccurrences=len(
                {o for r in residual if r["identityRequest"] for o in r["pair"]["occurrenceIDs"]}
            ),
            identityDistinctProjectedReferents=len(affected_refs),
            supplementalEvidenceOccurrences=len(missing),
            alreadyJudgedPairs=len(judged & relation_keys),
            inputEstimate=inp,
            outputEstimate=out,
            outputCaps=caps,
            batchUSD=(inp * 1.25 + out * 5) / 1e6,
            ceilingBatchUSD=(inp * 1.25 + caps * 5) / 1e6,
        )
        for name, rows in [
            ("requests", requests),
            ("components", inventory),
            ("residual-pairs", residual),
            ("initial-coverage", audit),
            ("baseline-relation-recheck", recheck),
        ]:
            prep.emit(stage / (name + ".jsonl"), rows)
        w.live.save(stage / "summary.json", summary)
        w.live.save(
            stage / "manifest.json",
            dict(
                inputHashes=pins,
                outputHashes={
                    str(p.relative_to(stage)): w.r.identity.sha(p)
                    for p in stage.rglob("*")
                    if p.is_file()
                },
            ),
        )
        stage.rename(output)
    return summary


def main():
    """Prepare or verify offline; reuse the complete-component Batch transport for researcher execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "verify", "submit", "status", "retrieve"])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.mode == "prepare":
        result = prepare(args.root)
    elif args.mode == "verify":
        result = f.replay.verify(args.root)
    else:
        with patch.object(w, "verify", f.replay.verify), patch.object(
            w, "process", f.process
        ), patch.object(f, "evaluate", validate):
            result = w.operate(args.root, args.mode)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
