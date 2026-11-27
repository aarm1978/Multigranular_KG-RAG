"""Prepare residual-relations/v2 from the frozen v1 decisions and original occurrence witnesses."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile

import yaml
from src.evaluation import step14_residual_relations as prior

w, prep = prior.w, prior.prep
ROOT = prior.ROOT.parent / "v2"


def membership_overlay(groups):
    """Exclude only explicitly held automatic memberships and preserve their records verbatim."""
    active = {}
    excluded = {}
    for group in groups:
        gid = group["groupID"]
        if group.get("productionConsistencyHold"):
            w.require(group["authority"] == "automatic_prediction", "PROTECTED_AUTHORITY")
            excluded[gid] = group
        else:
            active[gid] = group
    owner = {o: gid for gid, group in active.items() for o in group["occurrenceIDs"]}
    removed = [o for group in excluded.values() for o in group["occurrenceIDs"]]
    w.require(
        len(owner) == sum(len(g["occurrenceIDs"]) for g in active.values())
        and len(set(removed)) == len(removed)
        and set(removed).isdisjoint(owner),
        "MEMBERSHIP_OVERLAP",
    )
    return active, excluded, owner


def projected_key(row, owner):
    """Require one unambiguous projected referent per original side, with source support for both."""
    sides = row["occurrenceEndpoints"]
    witnesses = {o for o, _ in prep.cited(row)}
    w.require(
        len(sides) == 2 and all(witnesses.intersection(side) for side in sides),
        "MISSING_ENDPOINT_EVIDENCE",
    )
    projected = prep.project(sides, owner)
    w.require(projected and projected[0] != projected[1], "AMBIGUOUS_OR_INTERNAL_SUPPORT")
    return tuple(sorted(projected))


def prepare(output: Path):
    """Apply the single authorized overlay, then reuse v1 request assembly and Batch packing."""
    w.require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    source = prior.ROOT
    prior.identity.f.replay.verify(source)
    pins = dict(w.live.load(source / "manifest.json")["inputHashes"])
    pins[str(source / "manifest.json")] = w.r.identity.sha(source / "manifest.json")
    pins[str(Path(__file__).resolve().relative_to(Path.cwd()))] = w.r.identity.sha(Path(__file__))

    def rows(name):
        """Consume only v1 artifacts verified by its manifest and pin their bytes in v2."""
        path = source / (name + ".jsonl")
        pins[str(path)] = w.r.identity.sha(path)
        return w.r.rows(path)

    active, excluded, owner = membership_overlay(rows("identity-groups"))
    removed = {o for g in excluded.values() for o in g["occurrenceIDs"]}
    w.require((len(excluded), len(removed)) == (4, 11), "AUTHORIZED_SCOPE_DRIFT")
    exceptions = list(rows("consistency-exceptions"))
    evidence = {(r["unit"], r["index"]): r for r in exceptions}
    overlay = [
        dict(
            originalGroup=g,
            originalOccurrences=g["occurrenceIDs"],
            disposition="terminal_nonconsolidation",
            authority="researcher_scoped_representation_decision",
            consistencyEvidence=[evidence[tuple(ref)] for ref in g["productionConsistencyHold"]],
        )
        for g in excluded.values()
    ]
    cases = defaultdict(list)
    affected = []
    for case in rows("relation-cases"):
        key = tuple(case["key"])
        if not excluded.keys() & set(key):
            cases[key].extend(case["support"])
            continue
        targets = []
        for row in case["support"]:
            new = projected_key(row, owner)
            targets.append(new)
            cases[new].append(row)
        affected.append(dict(originalKey=key, projectedSupportKeys=targets))
    w.require(len(affected) == 26, "AFFECTED_CASE_DRIFT")
    retained = {tuple(r["triple"]): r["support"] for r in rows("retained-relations")}
    w.require(
        len(retained) == 54 and all(not set(excluded).intersection(k[::2]) for k in retained),
        "RETAINED_RELATION_DRIFT",
    )
    recheck = list(rows("prior-relation-recheck"))
    w.require(
        all(not set(excluded).intersection((r["projectedTriple"] or [])[::2]) for r in recheck),
        "PREVIOUS_RELATION_PROJECTION_DRIFT",
    )
    typed = {tuple(sorted(k[::2])) for k in retained}
    coverage = []
    lost = set()
    counts = Counter()
    for r in rows("pair-coverage"):
        ids = [owner.get(o, o) for o in r["original"]]
        if r["after"][0] == r["after"][1] and ids[0] != ids[1]:
            lost.add(r["pairID"])
        same = ids[0] == ids[1]
        originally_same = r["before"][0] == r["before"][1]
        state = (
            ("retained_identity" if originally_same else "new_identity")
            if same
            else ("newly_separated" if originally_same else "still_distinct")
        )
        alignment = (
            "identity"
            if same
            else "retained_typed"
            if tuple(sorted(ids)) in typed
            else "no_current_direct_alignment"
        )
        counts[state] += 1
        coverage.append(
            dict(
                r,
                v1Projection=r["after"],
                after=ids,
                identityDisposition=state,
                currentAlignment=alignment,
            )
        )
    w.require(len(lost) == 13, "LOST_PAIR_DRIFT")
    records = {r["occurrenceID"]: r for r in w.r.rows(prep.ENDPOINTS)}
    added = []
    for p in w.r.rows(w.BASE / "adjudication-triage/v1/pair-inventory.jsonl"):
        if p["pairKeySha256"] not in lost:
            continue
        sides = [[o] for o in p["occurrenceIDs"]]
        citations = [
            dict(binding=dict(occurrenceID=o, **q))
            for o in p["occurrenceIDs"]
            for q in records[o]["selectedEvidence"]
        ]
        row = dict(
            kind="candidate",
            predicate=None,
            occurrenceEndpoints=sides,
            support=[dict(pair=p, citations=citations)],
        )
        new = projected_key(row, owner)
        cases[new].append(row)
        added.append(dict(pairID=p["pairKeySha256"], key=new))
    w.require({r["pairID"] for r in added} == lost and len(added) == len(lost), "LOST_PAIR_ACCOUNTING")
    leads = list(rows("leads"))
    aliases = {}
    for u in sorted({l["unit"] for l in leads}):
        path = prior.identity.ROOT / "bindings" / (u + ".json")
        w.require(str(path) in pins, "UNPINNED_ALIASES")
        aliases[u] = w.live.load(path)["aliases"]
    spec = yaml.safe_load(w.SPEC.read_text())
    summary = dict(
        identityGroups=len(active),
        identityOccurrences=len(owner),
        excludedGroups=len(excluded),
        unconsolidatedOccurrences=len(removed),
        affectedV1Cases=len(affected),
        newlyUnrepresentedPairs=len(lost),
        originalPairs=len(coverage),
        originalIdentity=counts,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "package"
        result = prior.publish(
            stage,
            pins,
            active,
            list(rows("assignments")),
            list(rows("supersessions")),
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
            w.ancestors(spec),
            summary,
        )
        manifest = w.live.load(stage / "manifest.json")
        for name, data in [
            ("membership-overlay", overlay),
            ("reprojected-cases", affected),
            ("additional-pairs", added),
        ]:
            path = stage / (name + ".jsonl")
            prep.emit(path, data)
            manifest["outputHashes"][path.name] = w.r.identity.sha(path)
        # publish writes an immutable manifest. Install the extended manifest in the private staging area.
        (stage / "manifest.json").unlink()
        w.live.save(stage / "manifest.json", manifest)
        stage.rename(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    print(json.dumps(prepare(parser.parse_args().root), indent=2))
