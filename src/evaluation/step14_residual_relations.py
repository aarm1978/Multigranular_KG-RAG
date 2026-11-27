"""Close residual whole-component identity predictions and prepare the final relation Batch."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import yaml
from src.evaluation import step14_residual_alignment as identity

base, prep, w = identity.baseline, identity.prep, identity.w
ROOT = w.BASE / "residual-relations/v1"


def reconcile(priors, assignments, locks):
    """Preserve old scopes transitively only through conflicts with indivisible proposed scopes."""
    by_occ = {o: k for k, ids in priors.items() for o in ids}
    strict = {
        tuple(sorted(a["occurrenceIDs"]))
        for a in assignments
        if a["category"] == "strict_identity" and not a["reasons"]
    }
    unresolved = {
        o
        for a in assignments
        if a["reasons"] or a["category"] == "abstention"
        for o in a["occurrenceIDs"]
    }
    preserved = {by_occ[o] for o in unresolved if o in by_occ}
    boundaries = {tuple(sorted(ids)) for ids in locks}
    while True:
        fixed = boundaries | {tuple(sorted(priors[k])) for k in preserved}
        owner = {o: s for s in fixed for o in s}
        blocked = {s for s in strict if any(o in owner and owner[o] != s for o in s)}
        more = {by_occ[o] for s in blocked for o in s if o in by_occ}
        if more <= preserved:
            break
        preserved.update(more)
    return preserved, strict - blocked, blocked


def identity_results(read, pin, ledger):
    """Reproduce frozen receipts and ledger every affected prior and source assignment."""
    groups = dict(ledger)
    decisions = []
    changes = []
    leads = []
    exceptions = []
    packet = identity.ROOT
    requests = list(w.r.rows(read(packet, "requests.jsonl")))
    execution = packet / "execution"
    w.require(list(w.r.rows(pin(execution / "batch-input.jsonl"))) == requests, "SUBMISSION_DRIFT")
    native = {}
    for r in w.r.rows(pin(execution / "output_file_id.jsonl")):
        uid = r["custom_id"]
        w.require(
            uid not in native and r["response"]["status_code"] == 200, "DUPLICATE_OR_FAILED_RESULT"
        )
        native[uid] = r["response"]["body"]
    aliases = {}
    for req in requests:
        u = req["custom_id"]
        binding = w.live.load(read(packet, "bindings/" + u + ".json"))
        aliases[u] = binding["aliases"]
        raw = w.live.load(pin(execution / (u + ".response.json")))
        receipt = w.live.load(pin(execution / (u + ".validation.json")))
        w.require(raw == native.pop(u) and raw["status"] == "completed", "RAW_DRIFT")
        result = identity.validate(
            w.transport.decode(w.live.provider.extract_model_output(raw)), req["body"], binding
        )
        w.require(
            all(receipt[k] == v for k, v in result.items())
            and result["partitionAudit"]["partitionExact"],
            "REPLAY_DRIFT",
        )
        priors = binding["priorTargets"]
        rows = result["assignments"]
        keep, admit, blocked = reconcile(priors, rows, binding["protectedMemberships"])
        exact = {tuple(sorted(g["occurrenceIDs"])): k for k, g in groups.items()}
        for k, ids in priors.items():
            w.require(
                set(ledger[k]["occurrenceIDs"]) == set(ids)
                and ledger[k]["authority"] == "automatic_prediction",
                "PRIOR_DRIFT",
            )
            if k not in keep and tuple(sorted(ids)) not in admit:
                changes.append(
                    dict(
                        unit=u,
                        priorGroup=k,
                        oldMembership=ids,
                        sourceItems=[
                            a["itemIndex"] for a in rows if set(ids).intersection(a["occurrenceIDs"])
                        ],
                    )
                )
                del groups[k]
        for a in rows:
            ids = tuple(sorted(a["occurrenceIDs"]))
            ref = [u, a["itemIndex"]]
            state = "mechanically_unresolved" if a["reasons"] else a["category"]
            if ids in blocked and state == "strict_identity":
                state = "blocked_by_preserved_membership"
            if ids in admit and state == "strict_identity":
                gid = exact.get(ids, "step14-provisional:" + w.live.token(ids))
                if gid not in groups:
                    records = [binding["members"][o] for o in ids]
                    groups[gid] = dict(
                        groupID=gid,
                        occurrenceIDs=ids,
                        authority="automatic_prediction",
                        ontologyClass=records[0]["ontologyClass"],
                        identityScope=prep.closure.rec.d.ab.group_scope(records),
                        support=[ref],
                    )
            if a["modelItem"]["conflictAssessment"] == "material_conflict":
                exceptions.append(
                    dict(
                        unit=u,
                        index=a["itemIndex"],
                        assessment=a,
                        retainedPriorGroups=[
                            k for k in sorted(keep) if set(ids).intersection(priors[k])
                        ],
                    )
                )
            decisions.append(
                dict(
                    unit=u,
                    index=a["itemIndex"],
                    disposition=state,
                    assessment=a,
                    preservedPriorGroups=[k for k in sorted(keep) if set(ids).intersection(priors[k])],
                )
            )
        for i, l in enumerate(result["relationLeads"]):
            leads.append(dict(unit=u, index=i, **l))
    w.require(not native and len(requests) == 262, "POPULATION_DRIFT")
    return groups, decisions, changes, leads, exceptions, aliases


def projected_lead(lead, aliases, owner):
    """Resolve named endpoints and cited occurrences within one projected referent per side."""
    if lead["status"] == "evidence_lead":
        # An admissible lead already has two bound assignment sides. Narrow the
        # new question to the actually cited witnesses on each original side.
        cited = {c["binding"]["occurrenceID"] for c in lead["citations"]}
        sides = [sorted(set(side["membership"]) & cited) for side in lead["sides"]]
        key = prep.project(sides, owner)
        return sides if key and key[0] != key[1] else None
    raw = lead["original"]["modelItem"]
    if not isinstance(raw, dict) or any(
        reason
        not in (
            "AMBIGUOUS_OR_UNRESOLVED_SUBJECT",
            "AMBIGUOUS_OR_UNRESOLVED_OBJECT",
            "SAME_ASSIGNMENT",
            "UNCITED_SUBJECT",
            "UNCITED_OBJECT",
        )
        for reason in lead["reasons"]
    ):
        return None
    sides = []
    for field in ("subject", "object"):
        names = prep.closure.ALIAS.findall(raw[field])
        if not names or any(n not in aliases for n in names):
            return None
        sides.append(sorted({aliases[n] for n in names}))
    key = prep.project(sides, owner)
    if not key or key[0] == key[1]:
        return None
    cited = {c["binding"]["occurrenceID"] for c in lead["citations"] if c["binding"]}
    for i, k in enumerate(key):
        witnesses = {o for o in cited if owner.get(o, o) == k}
        if not witnesses:
            return None
        sides[i] = sorted(set(sides[i]) | witnesses)
    return sides


def validate(value, binding):
    """Normalize explicit local citation prefixes; validate independent items and exact case ownership."""
    w.require(isinstance(value, dict) and isinstance(value.get("items"), list), "INVALID_ENVELOPE")
    adapted = deepcopy(value)
    for item in adapted["items"]:
        if isinstance(item, dict) and isinstance(item.get("evidence"), list):
            names = []
            for s in item["evidence"]:
                names.extend((base.aliases(s) or [s]) if isinstance(s, str) else [s])
            item["evidence"] = names
    result = original_validate(adapted, binding)
    for i, r in enumerate(result["items"]):
        r["originalModelItem"] = value["items"][i]
    return result


def process(root, uid, body, response):
    """Archive raw provider output and reuse the existing validation receipt writer."""
    with patch.object(prep, "validate", validate):
        return prep.process(root, uid, body, response)


original_validate = prep.validate


def run(output):
    """Publish identity, coverage, reprojection and request ledgers atomically."""
    w.require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    identity.f.replay.verify(identity.ROOT)
    identity.f.replay.verify(base.ROOT)
    pins = {}
    manifests = {}

    def pin(path):
        if str(path) not in pins:
            pins[str(path)] = w.r.identity.sha(path)
        return path

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
        "FROZEN_SPEC_DRIFT",
    )
    hierarchy = w.ancestors(spec)
    sigs = {s["id"]: s for s in spec["relations"]}
    old = {g["groupID"]: g for g in w.r.rows(read(base.ROOT, "identity-groups.jsonl"))}
    groups, decisions, changes, leads, exceptions, aliases = identity_results(read, pin, old)
    owner = {o: k for k, g in groups.items() for o in g["occurrenceIDs"]}
    w.require(
        len(owner) == sum(len(g["occurrenceIDs"]) for g in groups.values()), "OVERLAPPING_FINAL_GROUPS"
    )
    w.require(
        all(groups.get(k) == g for k, g in old.items() if g["authority"] == "researcher_approved_exact"),
        "APPROVAL_DRIFT",
    )
    holds = defaultdict(list)
    for ex in exceptions:
        for gid in ex["retainedPriorGroups"]:
            holds[gid].append([ex["unit"], ex["index"]])
    for gid, g in list(groups.items()):
        if gid in holds:
            groups[gid] = dict(g, productionConsistencyHold=holds[gid])
        elif gid not in old:
            w.require(w.fits(g["ontologyClass"], sigs["D-16"]["range"], hierarchy), "NEW_GROUP_RANGE")
            g.update(rangeCompatible=True, provisionalTarget=gid, approval=None, sourceGroup=None)
    for ch in changes:
        ch["replacementByOccurrence"] = {o: owner.get(o) for o in ch["oldMembership"]}
    records = {
        e["occurrenceID"]: e
        for e in w.r.rows(read(w.BASE / "unified-review-queue/v1", "endpoint-provenance.jsonl"))
    }
    residual = {
        r["pair"]["pairKeySha256"] for r in w.r.rows(read(identity.ROOT, "residual-pairs.jsonl"))
    }
    audit = {r["pairID"]: r for r in w.r.rows(read(identity.ROOT, "initial-coverage.jsonl"))}
    cases = defaultdict(list)
    coverage = []
    counts = Counter()
    rescounts = Counter()
    sources = Counter()

    def add(row):
        key = prep.project(row["occurrenceEndpoints"], owner)
        w.require(key and key[0] != key[1], "INVALID_RELATION_ENDPOINTS")
        cases[tuple(sorted(key))].append(row)

    def original_pair(p):
        a, b = p["occurrenceIDs"]
        citations = [
            dict(binding=dict(occurrenceID=o, **q))
            for o in (a, b)
            for q in records[o]["selectedEvidence"]
        ]
        return dict(
            kind="candidate",
            predicate=None,
            occurrenceEndpoints=[[a], [b]],
            support=[dict(pair=p, citations=citations)],
        )

    for p in w.r.rows(read(w.BASE / "adjudication-triage/v1", "pair-inventory.jsonl")):
        if p["coverageState"] != "validated_recommendation":
            continue
        pid = p["pairKeySha256"]
        a, b = p["occurrenceIDs"]
        key = [owner.get(o, o) for o in (a, b)]
        before = audit[pid]["direct"] == "identity"
        after = key[0] == key[1]
        state = (
            ("retained_identity" if before else "new_identity")
            if after
            else ("newly_separated" if before else "still_distinct")
        )
        counts[state, p["category"], p["identityScope"]] += 1
        coverage.append(
            dict(
                pairID=pid,
                unitID=p["unitID"],
                original=p["occurrenceIDs"],
                before=audit[pid]["projected"],
                after=key,
                identityDisposition=state,
                category=p["category"],
                scope=p["identityScope"],
                residual=pid in residual,
                originalRecommendation=p["recommendationReference"],
            )
        )
        if pid in residual:
            rescounts["identity" if after else "distinct"] += 1
        if not after and (pid in residual or before):
            add(original_pair(p))
            sources["residual" if pid in residual else "newly_separated"] += 1
    residual_keys = {
        k
        for k, rs in cases.items()
        if any(x["support"][0]["pair"]["pairKeySha256"] in residual for x in rs)
    }
    before_leads = set(cases)
    admissible_keys = set()
    lead_log = []
    for lead in leads:
        u = lead["unit"]
        sides = projected_lead(lead, aliases[u], owner)
        entry = dict(**lead, projectedSides=sides)
        if sides:
            key = tuple(sorted(prep.project(sides, owner)))
            if lead["status"] == "evidence_lead":
                admissible_keys.add(key)
            add(
                dict(
                    kind="lead",
                    predicate=None,
                    occurrenceEndpoints=sides,
                    support=[dict(**lead, reference=["residual", u, lead["index"]])],
                )
            )
        lead_log.append(entry)
    # Recheck each actual supporting judgment, including equivalent signatures.
    previous = list(w.r.rows(read(base.ROOT, "relations.jsonl")))
    judgments = {
        (r["unit"], r["case"], r["index"]): r for r in w.r.rows(read(base.ROOT, "judgments.jsonl"))
    }
    recheck = []
    retained = defaultdict(list)
    classes = {o: r["ontologyClass"] for o, r in records.items()}
    classes.update({k: g["ontologyClass"] for k, g in groups.items()})
    for rel in previous:
        old_key = (rel["subject"], rel["predicate"], rel["object"])
        for s in rel["support"]:
            r = judgments[s["unit"], s["case"], s["index"]]
            new, reason = base.triple(r, owner, classes, sigs, hierarchy)
            entry = dict(
                originalTriple=old_key,
                source=s,
                projectedTriple=new,
                reason=reason,
                consistencyHolds=sorted(set((new or ())[::2]) & holds.keys()),
            )
            if new == old_key and not ({new[0], new[2]} & holds.keys()):
                entry["status"] = "retained"
                retained[new].append(s)
            elif new:
                entry["status"] = "targeted_reassessment"
                cited = {e["binding"]["occurrenceID"] for e in r["evidence"]}
                sides = [sorted(cited.intersection(side)) for side in r["originalSides"]]
                if r["original"]["direction"] == "reverse":
                    sides.reverse()
                add(
                    dict(
                        kind="earlier_relation",
                        predicate=old_key[1],
                        occurrenceEndpoints=sides,
                        support=[
                            dict(
                                sourceJudgment=s,
                                citations=[
                                    dict(
                                        binding=dict(
                                            occurrenceID=e["binding"]["occurrenceID"],
                                            **e["binding"]["quote"],
                                        )
                                    )
                                    for e in r["evidence"]
                                ],
                            )
                        ],
                    )
                )
            else:
                entry["status"] = "unresolved_projection"
            recheck.append(entry)
    # A direct typed alignment remains provisional while its changed scope is adjudicated.
    typed_pairs = {tuple(sorted((a, b))) for a, _, b in retained}
    direct_counts = Counter()
    for r in coverage:
        ids = r["after"]
        state = (
            "identity"
            if ids[0] == ids[1]
            else "retained_typed"
            if tuple(sorted(ids)) in typed_pairs
            else "no_current_direct_alignment"
        )
        r["currentAlignment"] = state
        direct_counts[state, r["category"], r["scope"]] += 1
    w.require(
        len(coverage) == len(audit) == 73416 and sum(rescounts.values()) == len(residual) == 14226,
        "PAIR_ACCOUNTING_DRIFT",
    )
    return publish(
        output,
        pins,
        groups,
        decisions,
        changes,
        lead_log,
        exceptions,
        cases,
        coverage,
        recheck,
        retained,
        records,
        owner,
        aliases,
        spec,
        hierarchy,
        dict(
            identityGroups=len(groups),
            identityOccurrences=len(owner),
            residual=rescounts,
            originalIdentity=Counter(r["identityDisposition"] for r in coverage),
            byCategoryScope=[
                dict(disposition=s, category=c, scope=a, count=n)
                for (s, c, a), n in sorted(counts.items())
            ],
            originalPairs=len(coverage),
            currentAlignmentByCategoryScope=[
                dict(alignment=s, category=c, scope=a, count=n)
                for (s, c, a), n in sorted(direct_counts.items())
            ],
            residualPairKeys=len(residual_keys),
            candidateSources=sources,
            admissibleLeadExtraPairs=len(admissible_keys - residual_keys),
            allLeadExtraPairs=len(
                set(k for k, rs in cases.items() if any(r["kind"] == "lead" for r in rs)) - before_leads
            ),
            leadDispositions=Counter(
                (r["status"] + "_" + ("bound" if r["projectedSides"] else "unbound")) for r in lead_log
            ),
            priorRelationDispositions=Counter(r["status"] for r in recheck),
        ),
    )


def publish(
    output,
    pins,
    groups,
    decisions,
    changes,
    leads,
    exceptions,
    cases,
    coverage,
    recheck,
    retained,
    records,
    owner,
    aliases,
    spec,
    hierarchy,
    summary,
):
    """Pack only explicit cases and write independently verifiable transport shards."""
    from src.extraction.llm.publications.full_corpus_gpt61_batch import MAX_BYTES

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "package"
        stage.mkdir()
        pending = set(cases)
        sizes = {k: len(g["occurrenceIDs"]) for k, g in groups.items()}
        units = []
        shard = 1
        used = 0
        requests = []
        tin = tout = caps = 0
        for refs in w.pack_edges(pending.copy(), limit=5):
            keys = sorted(k for k in pending if set(k) <= set(refs))
            pending.difference_update(keys)
            if not keys:
                continue
            with patch.object(prep, "lead_aliases", lambda s: aliases[s["unit"]]):
                body, b = prep.make_request(keys, cases, records, owner, sizes, spec, hierarchy, {})
            payload = json.loads(body["input"])
            for c in payload["cases"]:
                c["historical"] = [
                    h for h in c["historical"] if h.get("predicate") or h.get("description")
                ]
            # A previous relation may have several actual witnesses per endpoint.
            # Present the cited sets together without privileging their first occurrence.
            reverse = {o: a for a, o in b["aliases"].items()}
            for c, key in zip(payload["cases"], keys):
                c["historical"] = [h for h in c["historical"] if "originalSubject" not in h]
                for row in cases[key]:
                    if row["kind"] == "earlier_relation":
                        left, right = row["occurrenceEndpoints"]
                        c["historical"].append(
                            dict(
                                predicate=row["predicate"],
                                direction="forward"
                                if owner.get(left[0], left[0]) == key[0]
                                else "reverse",
                                originalSubjectWitnesses=[reverse[o] for o in left],
                                originalObjectWitnesses=[reverse[o] for o in right],
                            )
                        )
            body["input"] = w.live.encode(payload).decode()
            uid = f"Z{len(units)+1:05d}"
            request = dict(custom_id=uid, method="POST", url="/v1/responses", body=body)
            size = len(w.live.encode(request)) + 1
            w.require(
                size + body["max_output_tokens"] + 2048 < identity.f.CONTEXT and size <= MAX_BYTES,
                "REQUEST_SIZE",
            )
            if used + size > MAX_BYTES:
                shard += 1
                used = 0
            folder = stage / f"batch-{shard:03d}"
            w.live.save(folder / "bindings" / (uid + ".json"), b)
            requests.append((folder, request))
            used += size
            units.append(dict(unit=uid, shard=folder.name, keys=keys))
            tin += (size + 3) // 4
            tout += 200 + 250 * len(keys)
            caps += body["max_output_tokens"]
        w.require(not pending and sum(len(u["keys"]) for u in units) == len(cases), "PACKING_DRIFT")
        authority = defaultdict(Counter)
        for group in groups.values():
            authority[group["authority"]].update(groups=1, occurrences=len(group["occurrenceIDs"]))
        summary.update(
            identityAuthority=authority,
            scopedHolds=sum(bool(g.get("productionConsistencyHold")) for g in groups.values()),
            supersededGroups=len(changes),
            assignmentDispositions=Counter(a["disposition"] for a in decisions),
            retainedTypedTriples=len(retained),
            requests=len(units),
            relationCases=len(cases),
            shards=shard,
            estimatedInput=tin,
            estimatedOutput=tout,
            outputCap=caps,
            estimatedBatchUSD=(1.25 * tin + 5 * tout) / 1e6,
            outputCeilingBatchUSD=(1.25 * tin + 5 * caps) / 1e6,
        )
        for folder in sorted({f for f, _ in requests}):
            prep.emit(folder / "requests.jsonl", (r for f, r in requests if f == folder))
            w.live.save(folder / "summary.json", dict(requests=sum(f == folder for f, _ in requests)))
            w.live.save(
                folder / "manifest.json",
                dict(
                    inputHashes={},
                    outputHashes={
                        str(p.relative_to(folder)): w.r.identity.sha(p)
                        for p in folder.rglob("*")
                        if p.is_file()
                    },
                ),
            )
        for name, rows in [
            ("identity-groups", groups.values()),
            ("assignments", decisions),
            ("supersessions", changes),
            ("consistency-exceptions", exceptions),
            ("leads", leads),
            ("pair-coverage", coverage),
            ("prior-relation-recheck", recheck),
            ("retained-relations", (dict(triple=k, support=v) for k, v in sorted(retained.items()))),
            ("relation-cases", (dict(key=k, support=v) for k, v in sorted(cases.items()))),
            ("units", units),
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
    """Prepare/verify offline; allow separate researcher execution of the pinned shard."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["prepare", "verify", "submit", "status", "retrieve"])
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--shard", type=int, default=1)
    a = p.parse_args()
    if a.mode == "prepare":
        result = run(a.root)
    else:
        result = identity.f.replay.verify(a.root)
        if a.mode != "verify":
            w.require(1 <= a.shard <= result["shards"], "UNKNOWN_SHARD")
            with patch.object(w, "verify", identity.f.replay.verify), patch.object(
                w, "process", process
            ):
                result = w.operate(a.root / f"batch-{a.shard:03d}", a.mode)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
