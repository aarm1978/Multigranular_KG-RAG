"""Build and verify the evaluation-only exact-extraction derivative and unsampled frames."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile

import yaml

from src.evaluation import step14_final_alignment as frozen
from src.evaluation import step14_extraction_duplicates as dup
from src.evaluation.materialize_step13_relationships import OUTPUT as SNAP, SOURCE, PUB
from src.evaluation.step14_semantic_candidates import OUTPUT as CANDIDATES, token
from src.evaluation.step14_identity_preview import sha
from src.evaluation.step14_automatic_acceptance_preview import group_scope
from src.evaluation.step14_alignment_workflow import require

ROOT = frozen.w.BASE / "deduplicated-alignment/v1"
BASE = Path("results/metrics/snapshots/hydroshare_github_hub_publications_deterministic.json")
AUTO = "automatic-identity-frame.jsonl"
HIST = "historical-approvals.jsonl"
REL = "typed-relation-frame.jsonl"


def rows(path):
    """Stream one local ledger."""
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def emit(path, records):
    """Write deterministic, independently addressable rows."""
    with path.open("x") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")


def project_groups(groups, reps):
    """Keep exact scopes separate and hold every disputed projected membership."""
    buckets = defaultdict(list)
    old_owner = {}
    for g in groups:
        for oid in g["occurrenceIDs"]:
            require(oid not in old_owner, "ORIGINAL_OVERLAP")
            old_owner[oid] = g["groupID"]
        key = tuple(sorted({reps[k] for k in g["occurrenceIDs"]}))
        buckets[key].append(g)
    incidence = defaultdict(set)
    for key in buckets:
        for oid in key:
            incidence[oid].add(key)
    ledger = []
    active = []
    unresolved = set()
    owner = {}
    for key, source in sorted(buckets.items()):
        rivals = {r for oid in key for r in incidence[oid] if r != key}
        protected = [g for g in source if g["authority"] == "researcher_approved_exact"]
        original_ids = sorted(g["groupID"] for g in source)
        unchanged = len(source) == 1 and set(key) == set(source[0]["occurrenceIDs"])
        gid = (
            (source[0]["groupID"] if unchanged else "step14-projected:" + token(key))
            if len(key) > 1
            else None
        )
        state = (
            "membership_conflict"
            if rivals
            else "collapsed_singleton"
            if len(key) == 1
            else "coincident_memberships"
            if len(source) > 1
            else "unchanged"
            if unchanged
            else "reprojected"
        )
        provenance = [
            dict(
                frame=HIST if g in protected else AUTO,
                groupID=g["groupID"],
                recordSha256=token(g),
                originalMembers=g["occurrenceIDs"],
                authority=g["authority"],
            )
            for g in source
        ]
        row = dict(
            groupID=gid,
            occurrenceIDs=list(key),
            originalGroups=original_ids,
            sourceRecords=provenance,
            disposition=state,
            authority="researcher_approved_exact" if protected else "automatic_prediction",
            memberEvidenceFile="occurrence-provenance.jsonl",
            sourceLocalMapping="../graph/node-mapping.jsonl",
            ontologyClass=source[0]["ontologyClass"],
            size=len(key),
            identityScope=source[0]["identityScope"],
            sourceFamilies=source[0]["sourceFamilies"],
            humanVerified=False if not protected else None,
            decisionEvidence=[dict(groupID=g["groupID"], evidence=g["decisionEvidence"]) for g in source],
            historicalApprovals=[g["approval"] for g in protected],
            approvalScope="original exact memberships only" if protected else None,
            materializationAuthorized=False,
            conflicts=[
                dict(
                    otherGroups=sorted(g["groupID"] for g in buckets[r]),
                    sharedRepresentatives=sorted(set(key) & set(r)),
                )
                for r in sorted(rivals)
            ],
        )
        require(len({g["ontologyClass"] for g in source}) == 1, "PROJECTED_CLASS_DRIFT")
        ledger.append(row)
        if rivals:
            unresolved.update(key)
        elif len(key) > 1:
            active.append(row)
            owner.update(dict.fromkeys(key, gid))
    require(not unresolved.intersection(owner), "AMBIGUOUS_ACTIVE_MEMBERSHIP")
    return ledger, active, old_owner, owner, unresolved


def project_relations(relations, reps, old_owner, owner, unresolved, classes, signatures):
    """Project directed original citation witnesses as complete support bundles."""
    triples = defaultdict(list)
    ledger = []
    for r in relations:
        before = (r["subject"], r["predicate"], r["object"])
        proposals = set()
        reasons = set()
        sources = []
        require(r["support"], "MISSING_ORIGINAL_SUPPORT")
        for s in r["support"]:
            cited = {e["binding"]["occurrenceID"] for e in s["evidence"]}
            ends = []
            witness = []
            for old, side in zip(before[::2], s["citedEndpoints"]):
                require(
                    side and set(side) <= cited and all(old_owner.get(o, o) == old for o in side),
                    "ORIGINAL_DIRECTION_DRIFT",
                )
                local = sorted({reps[o] for o in side})
                witness.append(local)
                if unresolved.intersection(local):
                    reasons.add("conflicting_identity_membership")
                projected = {owner.get(o, o) for o in local}
                if len(projected) != 1:
                    reasons.add("ambiguous_cited_endpoint")
                else:
                    ends.append(next(iter(projected)))
            require(len(witness) == 2, "MISSING_CITED_ENDPOINT")
            if len(ends) == 2:
                a, b = ends
                if a == b:
                    reasons.add("projected_self_relation")
                if not signatures.valid(s["signature"], before[1], classes[a], classes[b]):
                    reasons.add("invalid_signature")
                proposals.add((a, before[1], b))
            sources.append(dict(s, projectedCitedOccurrences=witness, originalTriple=before))
        if len(proposals) != 1:
            reasons.add("inconsistent_support_projection")
        key = next(iter(proposals)) if len(proposals) == 1 and not reasons else None
        row = dict(
            originalTriple=before,
            originalRecordSha256=token(r),
            projectedTriple=key,
            disposition="unresolved" if reasons else "retained" if before == key else "reprojected",
            reasons=sorted(reasons),
        )
        ledger.append(row)
        if key:
            triples[key].append((row, sources))
    frame = []
    for (a, p, b), parts in sorted(triples.items()):
        for row, _ in parts:
            row["contributingOriginalTriples"] = len(parts)
            if len(parts) > 1:
                row["disposition"] = "deduplicated"
        frame.append(
            dict(
                subject=a,
                predicate=p,
                object=b,
                authority="automatic_prediction",
                humanVerified=False,
                endpointClasses=[classes[a], classes[b]],
                support=[s for _, support in parts for s in support],
            )
        )
    return ledger, frame


def run(output):
    """Atomically publish both packages from pinned frozen inputs."""
    require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    frozen.prior.identity.f.replay.verify(frozen.ROOT)
    pins = {}

    def pin(path, expected=None):
        """Bind originals without changing historical path/hash authorities."""
        path = Path(path)
        if str(path) not in pins:
            pins[str(path)] = sha(path)
        require(expected is None or pins[str(path)] == expected, "INPUT_DRIFT:" + str(path))
        return path

    def manifest(path):
        return json.loads(pin(path / "manifest.json").read_bytes())

    fm = manifest(frozen.ROOT)
    cm = manifest(CANDIDATES)

    def frame_file(name):
        return pin(frozen.ROOT / name, fm["outputHashes"][name])

    snapshot = pin(SNAP / "snapshot.json", cm["inputHashes"][str(SNAP / "snapshot.json")])
    native = pin(
        SOURCE / "native-provenance.jsonl", cm["inputHashes"][str(SOURCE / "native-provenance.jsonl")]
    )
    deriv = SNAP / "derivation-provenance.jsonl"
    pin(deriv, cm["inputHashes"][str(deriv)])
    graph = json.loads(snapshot.read_bytes())
    dup.metrics.validate_snapshot(graph)
    nodes = {n["id"]: n for n in graph["nodes"]}
    origins = defaultdict(set)
    for component in json.loads(pin(BASE).read_bytes())["input"]["cumulativeProvenance"]["components"]:
        data = dup.metrics.load_snapshot(pin(component["path"], component["sha256"]))
        for n in data["nodes"]:
            origins[n["id"]].add(component["label"])
    spec = yaml.safe_load(pin(frozen.w.SPEC, fm["inputHashes"][str(frozen.w.SPEC)]).read_bytes())
    require(spec["ontology"]["version"] == "0.1.9", "ONTOLOGY_DRIFT")
    signatures = dup.Signatures(spec)
    authority = json.loads(pin("docs/study2_step13_relationship_consumer_v0.1.json").read_bytes())

    def policy(name):
        """Read the frozen rule table under its historical digest."""
        path = PUB / name
        return yaml.safe_load(pin(path, authority["inputHashes"][str(path)]).read_bytes())

    profile = policy("publication_target_inventory_v0.1.5.yaml")
    generic = policy("generic_mentions_policy_v0.1.1.yaml")
    declarations = {}
    for m in rows(pin(CANDIDATES / "occurrences.jsonl", cm["outputHashes"]["occurrences.jsonl"])):
        declarations[m["occurrenceID"]] = [
            m["labels"],
            m["versions"],
            m["granularity"],
            m["declaredExistingNodeIDs"],
            [{k: v for k, v in d.items() if k != "edgeID"} for d in m["identifierDeclarations"]],
        ]
    reps, blocks, refs, reasons = dup.census(graph, native, origins, dup.Sources(pin), profile, declarations)
    require(all(origins[k] for k in nodes), "NODE_FAMILY_MISSING")
    edges, assertions, edge_counts = dup.project_edges(
        graph["edges"], reps, nodes, signatures, generic, profile
    )
    identities = list(rows(frame_file(AUTO)))
    historical = list(rows(frame_file(HIST)))
    relations = list(rows(frame_file(REL)))
    ledger, active, old_owner, owner, unresolved = project_groups(identities + historical, reps)
    classes = {k: n["class"] for k, n in nodes.items()}
    for g in ledger:
        require(all(classes[k] == g["ontologyClass"] for k in g["occurrenceIDs"]), "IDENTITY_TYPE_DRIFT")
    classes.update({g["groupID"]: g["ontologyClass"] for g in active})
    dispositions, typed = project_relations(
        relations, reps, old_owner, owner, unresolved, classes, signatures
    )

    # The retained source occurrence can originate outside the earlier evaluation frame.
    member_file = frozen.w.BASE / "referent-groups/v1/members.jsonl"
    member_hash = fm["inputHashes"][str(member_file)]
    selected = set(owner) | {k for g in ledger for k in g["occurrenceIDs"]}
    for r in typed:
        selected.update(o for s in r["support"] for side in s["projectedCitedOccurrences"] for o in side)
    evidence = {
        m["occurrenceID"]: m for m in rows(pin(member_file, member_hash)) if m["occurrenceID"] in selected
    }
    require(selected == evidence.keys(), "MISSING_REPRESENTATIVE_EVIDENCE")
    for g in ledger:
        g["identityScope"] = group_scope([evidence[k] for k in g["occurrenceIDs"]])
        g["sourceFamilies"] = sorted({f for k in g["occurrenceIDs"] for f in origins[k]})
    sizes = {g["groupID"]: g["size"] for g in active}
    for r in typed:
        cited = {o for s in r["support"] for side in s["projectedCitedOccurrences"] for o in side}
        r.update(
            citedOccurrences=len(cited),
            evidenceScope=group_scope([evidence[k] for k in cited]),
            endpointSizes=[sizes.get(r[k], 1) for k in ("subject", "object")],
        )
    auto = [g for g in active if g["authority"] == "automatic_prediction"]
    by_class = defaultdict(Counter)
    by_family = defaultdict(Counter)
    by_location = Counter()
    block_rows = []
    for k, n in nodes.items():
        for counter in [by_class[n["class"]], by_family["+".join(sorted(origins[k]))]]:
            counter["originalNodes"] += 1
            counter["representatives"] += reps[k] == k
            counter["redundantCopies"] += reps[k] != k
    for fp, ids in sorted(blocks.items()):
        group_ids = {old_owner[o] for o in ids if o in old_owner}
        ungrouped = [o for o in ids if o not in old_owner]
        loc = (
            "outside_groups"
            if not group_ids
            else "across_groups"
            if len(group_ids) > 1
            else "grouped_and_ungrouped"
            if ungrouped
            else "within_group"
        )
        by_location[loc] += 1
        for c in (by_class[nodes[ids[0]]["class"]], by_family["+".join(sorted(origins[ids[0]]))]):
            c["duplicateBlocks"] += 1
        block_rows.append(
            dict(
                fingerprint=fp,
                representative=ids[0],
                originals=ids,
                groups=sorted(group_ids),
                ungrouped=ungrouped,
                location=loc,
            )
        )
    derived = dict(
        snapshot_type="source_local_extraction_deduplicated",
        evaluationOnly=True,
        nodes=[n for k, n in nodes.items() if reps[k] == k],
        edges=edges,
    )
    dup.metrics.validate_snapshot(derived)
    counts = dict(
        originalNodes=len(nodes),
        nodes=len(derived["nodes"]),
        originalEdges=len(graph["edges"]),
        edges=len(edges),
        duplicateBlocks=len(blocks),
        redundantCopies=len(nodes) - len(derived["nodes"]),
        blockLocation=by_location,
        blocksTouchingMultipleGroupsAndUngrouped=sum(
            len(b["groups"]) > 1 and bool(b["ungrouped"]) for b in block_rows
        ),
        byClass=by_class,
        byFamily=by_family,
        assertions=edge_counts,
        retainedWithoutFingerprint=Counter(reason for v in reasons.values() for reason in v),
        originalAutomatic=len(identities),
        historicalDecisions=len(historical),
        originalRelations=len(relations),
        identityDispositions=Counter(g["disposition"] for g in ledger for _ in g["originalGroups"]),
        reducedOriginalGroups=sum(
            len(set(g["occurrenceIDs"])) < len(s["originalMembers"])
            for g in ledger
            for s in g["sourceRecords"]
        ),
        conflictRepresentatives=len(unresolved),
        activeMemberships=len(active),
        activeOccurrences=len(owner),
        automaticGroups=len(auto),
        automaticOccurrences=sum(g["size"] for g in auto),
        largestAutomaticGroupBefore=max(g["size"] for g in identities),
        largestAutomaticGroupAfter=max((g["size"] for g in auto), default=0),
        historicalMemberships=len(active) - len(auto),
        relationDispositions=Counter(r["disposition"] for r in dispositions),
        directedRelations=len(typed),
        predicates=Counter(r["predicate"] for r in typed),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "package"
        graphdir = stage / "graph"
        align = stage / "alignment"
        graphdir.mkdir(parents=True)
        align.mkdir()
        with (graphdir / "snapshot.json").open("x") as f:
            json.dump(derived, f, separators=(",", ":"), ensure_ascii=False)
        emit(graphdir / "duplicate-blocks.jsonl", block_rows)
        emit(
            graphdir / "node-mapping.jsonl",
            (
                dict(
                    original=k,
                    representative=reps[k],
                    sourceFamilies=sorted(origins[k]),
                    ontologyClass=nodes[k]["class"],
                    nativeLines=refs.get(k, []),
                    retentionReasons=sorted(reasons[k]),
                )
                for k in sorted(nodes)
            ),
        )
        emit(graphdir / "assertion-mapping.jsonl", assertions)
        emit(align / "identity-dispositions.jsonl", ledger)
        emit(align / AUTO, auto)
        emit(align / HIST, historical)
        emit(align / "historical-projections.jsonl", (g for g in active if g["historicalApprovals"]))
        emit(align / "occurrence-provenance.jsonl", (evidence[k] for k in sorted(evidence)))
        emit(align / REL, typed)
        emit(align / "relation-dispositions.jsonl", dispositions)
        frozen.w.live.save(stage / "summary.json", counts)
        for script in [Path(__file__), Path(dup.__file__)]:
            pin(script.resolve().relative_to(Path.cwd()))
        frozen.w.live.save(
            stage / "manifest.json",
            dict(
                inputHashes=pins,
                originalProvenance=dict(
                    snapshot=str(snapshot),
                    native=str(native),
                    derivations=str(deriv),
                    frames=str(frozen.ROOT),
                ),
                outputHashes={
                    str(f.relative_to(stage)): sha(f) for f in sorted(stage.rglob("*")) if f.is_file()
                },
            ),
        )
        stage.rename(output)
    return counts


def verify(output):
    """Reconcile independently indexed original IDs, provenance links and unsampled frames."""
    summary = frozen.prior.identity.f.replay.verify(output)
    manifest = json.loads((output / "manifest.json").read_bytes())
    original = json.loads(Path(manifest["originalProvenance"]["snapshot"]).read_bytes())
    derivative = json.loads((output / "graph/snapshot.json").read_bytes())
    dup.metrics.validate_snapshot(derivative)
    nodes = {n["id"]: n for n in original["nodes"]}
    reps = {r["original"]: r["representative"] for r in rows(output / "graph/node-mapping.jsonl")}
    require(
        nodes.keys() == reps.keys()
        and set(reps.values()) == {n["id"] for n in derivative["nodes"]}
        and all(n == nodes[n["id"]] for n in derivative["nodes"]),
        "NODE_CONSERVATION",
    )
    removed = {k for k in reps if k != reps[k]}
    covered = set()
    for block in rows(output / "graph/duplicate-blocks.jsonl"):
        members = block["originals"]
        representative = block["representative"]
        require(
            members == sorted(set(members))
            and members[0] == representative
            and len(members) > 1
            and all(
                reps[k] == representative and nodes[k]["class"] == nodes[representative]["class"]
                for k in members
            )
            and not covered.intersection(members[1:]),
            "INVALID_DUPLICATE_BLOCK",
        )
        covered.update(members[1:])
    require(covered == removed, "REDUNDANT_NODE_ACCOUNTING")
    old = {e["id"]: e for e in original["edges"]}
    new = {e["id"]: e for e in derivative["edges"]}
    triples = {tuple(e[k] for k in ("source", "relation", "target")) for e in new.values()}
    require(len(triples) == len(new), "DUPLICATE_DERIVATIVE_TRIPLE")
    sig = dup.Signatures(yaml.safe_load(frozen.w.SPEC.read_bytes()))
    kept = set()
    for record in rows(output / "graph/assertion-mapping.jsonl"):
        e = old.pop(record["original"])
        a, p, b = record["projected"]
        require(
            (a, p, b) == (reps[e["source"]], e["relation"], reps[e["target"]])
            and (a != b or e["source"] == e["target"])
            and sig.valid(e["inventoryId"], p, nodes[a]["class"], nodes[b]["class"]),
            "ASSERTION_PROJECTION_DRIFT",
        )
        if record["disposition"] == "precedence_suppressed":
            require(
                (a, p, b) not in triples
                and record["suppressedBy"]
                and all(tuple(t) in triples for t in record["suppressedBy"]),
                "LOST_SUPPRESSOR",
            )
        else:
            target = new[record["retainedEdge"]]
            require((a, p, b) == (target["source"], target["relation"], target["target"]), "LOST_ASSERTION")
            if record["disposition"] == "retained":
                require(target == dict(e, source=a, target=b), "RETAINED_EDGE_DRIFT")
                kept.add(target["id"])
    require(not old and kept == new.keys(), "EDGE_CONSERVATION")
    align = output / "alignment"
    historical = list(rows(frozen.ROOT / HIST))
    require(historical == list(rows(align / HIST)), "APPROVAL_DRIFT")
    original_groups = list(rows(frozen.ROOT / AUTO)) + historical
    ledger, active, old_owner, owner, disputed = project_groups(original_groups, reps)
    actual = list(rows(align / "identity-dispositions.jsonl"))
    require(
        [
            (g["groupID"], g["occurrenceIDs"], g["disposition"], g["sourceRecords"], g["conflicts"])
            for g in actual
        ]
        == [
            (g["groupID"], g["occurrenceIDs"], g["disposition"], g["sourceRecords"], g["conflicts"])
            for g in ledger
        ],
        "GROUP_REPLAY_DRIFT",
    )
    require(
        list(rows(align / AUTO))
        == [g for g in actual if g["size"] > 1 and not g["conflicts"] and not g["historicalApprovals"]]
        and list(rows(align / "historical-projections.jsonl"))
        == [g for g in actual if g["size"] > 1 and not g["conflicts"] and g["historicalApprovals"]],
        "EVALUATION_FRAME_DRIFT",
    )
    classes = {k: n["class"] for k, n in nodes.items()}
    classes.update({g["groupID"]: g["ontologyClass"] for g in active})
    rledger, projected = project_relations(
        list(rows(frozen.ROOT / REL)), reps, old_owner, owner, disputed, classes, sig
    )
    require(
        list(rows(align / "relation-dispositions.jsonl")) == json.loads(json.dumps(rledger)),
        "RELATION_REPLAY_DRIFT",
    )
    saved = list(rows(align / REL))
    require(
        len(saved) == len(projected)
        and all({k: r[k] for k in base} == json.loads(json.dumps(base)) for r, base in zip(saved, projected)),
        "RELATION_FRAME_DRIFT",
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["build", "verify"])
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps((run if args.mode == "build" else verify)(args.output), indent=2))
