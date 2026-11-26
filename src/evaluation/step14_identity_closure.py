"""Offline closure of complete-component identity predictions and relation inputs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
import tempfile
from pathlib import Path
import re

import yaml
from src.evaluation import step14_final_components as final

w = final.w
rec = final.previous.rec
ROOT = w.BASE / "identity-closure/v1"
ALIAS = re.compile(r"\bE[0-9]+\b")


def corrected(row: dict) -> dict:
    """Respect a structured qualification while retaining every model-authored evidence role."""
    result = deepcopy(row)
    item = row["modelItem"]
    if (
        row["category"] == "strict_identity"
        and item.get("conflictAssessment") == "compatible_qualification"
    ):
        direct = {
            c["binding"]["occurrenceID"]
            for c in row["citations"]
            if c["field"] == "supportingEvidenceIDs" and c["location"] == "member" and c["binding"]
        }
        if (
            direct == set(row["occurrenceIDs"])
            and row.get("qualificationBindings")
            and all(c["binding"] for c in row["qualificationBindings"])
        ):
            result["reasons"] = sorted(
                set(row["reasons"]) - {"CONTRADICTORY_IDENTITY", "AMBIGUOUS_EXTERNAL_IDENTITY_EVIDENCE"}
            )
            if not result["reasons"]:
                result["status"] = final.replay.VALID
    return result


def resolve_lead(lead: dict, assignments: list, binding: dict) -> dict:
    """Resolve explicit E aliases to exactly one assignment per side without expanding a group."""
    original = lead["modelItem"]
    owners = {o: r for r in assignments if not r["reasons"] for o in r["occurrenceAliases"]}
    evidence = [
        dict(evidenceID=q, binding=binding["evidence"].get(q)) for q in original.get("evidenceIDs", [])
    ]
    cited = {c["binding"]["alias"] for c in evidence if c["binding"]}
    errors = []
    sides = []
    for field in ("subject", "object"):
        aliases = list(dict.fromkeys(ALIAS.findall(original.get(field, ""))))
        indices = {owners[a]["itemIndex"] for a in aliases if a in owners}
        if len(indices) != 1 or any(a not in owners for a in aliases):
            errors.append("AMBIGUOUS_OR_UNRESOLVED_" + field.upper())
            sides.append(None)
            continue
        r = owners[aliases[0]]
        if not cited.intersection(r["occurrenceAliases"]):
            errors.append("UNCITED_" + field.upper())
        sides.append(
            dict(
                index=r["itemIndex"],
                membership=r["occurrenceIDs"],
                namedOccurrences=[binding["aliases"][a] for a in aliases],
            )
        )
    if all(sides) and sides[0]["index"] == sides[1]["index"]:
        errors.append("SAME_ASSIGNMENT")
    if (
        not original.get("explanation", "").strip()
        or not evidence
        or any(not c["binding"] for c in evidence)
    ):
        errors.append("INVALID_LEAD_EVIDENCE")
    # Only endpoint-binding failures are reconsidered.
    errors.extend(
        e
        for e in lead["reasons"]
        if e not in ("NEEDS_TWO_INDEPENDENT_ASSIGNMENTS", "INVALID_ENDPOINT_EVIDENCE")
    )
    return dict(
        original=lead,
        sides=sides,
        citations=evidence,
        reasons=sorted(set(errors)),
        status="unresolved_lead" if errors else "evidence_lead",
    )


def run(output: Path) -> dict:
    """Build one disjoint proposal layer over immutable, hash-verified source records."""
    w.require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    pins = {}

    def pin(path):
        """Pin original bytes using a repository-relative source path."""
        pins[str(path)] = w.r.identity.sha(path)
        return path

    def read(folder, name):
        """Read the ledger only after matching its producer manifest."""
        path = pin(folder / name)
        manifest = w.live.load(pin(folder / "manifest.json"))
        w.require(pins[str(path)] == manifest["outputHashes"][name], "INPUT_DRIFT:" + name)
        return w.r.rows(path)

    final.replay.verify(final.ROOT)
    final.replay.verify(final.previous.ROOT)
    pin(Path(__file__).resolve().relative_to(Path.cwd()))
    spec = yaml.safe_load(pin(w.SPEC).read_text())
    w.require(spec["ontology"]["version"] == "0.1.8", "ONTOLOGY_VERSION")
    hierarchy = w.ancestors(spec)
    sigs = {s["id"]: s for s in spec["relations"]}
    members = {r["occurrenceID"]: r for r in read(w.BASE / "referent-groups/v1", "members.jsonl")}
    old = defaultdict(list)
    old_refs = defaultdict(set)
    for m in read(rec.ROOT, "occurrence-mappings.jsonl"):
        target = m["provisionalCanonicalID"]
        old[target].append(m["occurrenceID"])
        old_refs[target].add(m["decisionID"])
    approvals = list(read(rec.ROOT, "historical-approvals.jsonl"))
    groups = {}
    locks = {tuple(sorted(a["occurrenceIDs"])): a for a in approvals}
    for k, a in locks.items():
        groups[k] = dict(authority="researcher_approved_exact", approval=a, support=[])
    components, terminal, assessments, leads, stats = component_results(read, pin, groups)
    w.require(len(locks) == len(approvals), "DUPLICATE_APPROVAL")
    superseded = reconcile_prior(locks, groups, old, old_refs, components)
    projections = {}
    maps = []
    distribution = Counter()
    group_rows = []
    for ids, g in sorted(groups.items()):
        records = [members[o] for o in ids]
        classes = {m["ontologyClass"] for m in records}
        w.require(len(classes) == 1, "CLASS_MISMATCH")
        cls = classes.pop()
        compatible = w.fits(cls, sigs["D-16"]["range"], hierarchy)
        historical = g["authority"] == "researcher_approved_exact"
        gid = (
            g["approval"]["decisionID"]
            if historical
            else g.get("priorTarget", "step14-provisional:" + w.live.token(ids))
        )
        # Human exact approvals have an explicit independent materialization restriction.
        projection = dict(
            groupID=gid,
            authority=g["authority"],
            rangeCompatible=compatible,
            provisionalTarget=gid if compatible and not historical else None,
        )
        scope = rec.d.ab.group_scope(records)
        group_rows.append(
            dict(
                **g,
                **{k: v for k, v in projection.items() if k != "authority"},
                occurrenceIDs=ids,
                ontologyClass=cls,
                identityScope=scope,
            )
        )
        for o in ids:
            w.require(o not in projections and o not in terminal, "FINAL_MEMBERSHIP_OVERLAP")
            w.require(
                members[o]["originalReference"]
                and members[o]["sourceArtifacts"]
                and members[o]["sourceFamilies"],
                "MISSING_SOURCE",
            )
            projections[o] = projection
            maps.append(dict(occurrenceID=o, originalMember=members[o], **projection))
        distribution[g["authority"], cls, len(ids), scope, compatible] += 1
    for change in superseded:
        change["replacementByOccurrence"] = {
            o: projections.get(o) or dict(terminalStatus=terminal[o]) for o in change["oldMembership"]
        }

    w.require(
        set(components) == set(terminal) | (set(components) & projections.keys()),
        "FINAL_PARTITION_DRIFT",
    )
    relation_rows, unresolved = relation_inventory(read, sigs, leads, projections)
    frequencies = [
        dict(
            authority=a,
            ontologyClass=c,
            size=n,
            identityScope=s,
            rangeCompatible=k,
            groups=v,
            occurrences=n * v,
        )
        for (a, c, n, s, k), v in sorted(distribution.items())
    ]
    summary = dict(
        componentResults=stats,
        combinedComponentGroups=sum(stats[v + "_strict_groups"] for v in ("v1", "v2")),
        combinedComponentOccurrences=sum(stats[v + "_strict_occurrences"] for v in ("v1", "v2")),
        finalGroups=len(groups),
        finalOccurrences=len(projections),
        superseded=len(superseded),
        terminalComponentOccurrences=Counter(terminal.values()),
        relationInventory=Counter(r["kind"] for r in relation_rows),
        unresolvedLeadsBySource=Counter(r["reference"][0] for r in unresolved),
        distribution=frequencies,
        totals={
            k: breakdown(frequencies, k)
            for k in ("ontologyClass", "size", "identityScope", "authority", "rangeCompatible")
        },
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp) / "package"
        stage.mkdir()
        emit = final.replay.v3.coverage.write_rows
        for name, values in [
            ("groups", group_rows),
            ("occurrence-mappings", maps),
            ("supersessions", superseded),
            ("component-assignments", assessments),
            ("relation-inputs", relation_rows),
            ("unresolved-leads", unresolved),
            ("terminal-occurrences", terminal_rows(terminal, components, members, assessments)),
        ]:
            emit(stage / (name + ".jsonl"), values)
        w.live.save(stage / "summary.json", summary)
        w.live.save(
            stage / "manifest.json",
            dict(
                contract="identity-closure/1",
                inputHashes=pins,
                outputHashes={p.name: w.r.identity.sha(p) for p in stage.iterdir()},
            ),
        )
        stage.rename(output)
    return summary


def component_results(read, pin, groups):
    """Replay whole-component decisions and retain each source item independently."""
    terminal = {}
    components = {}
    assessments = []
    leads = []
    stats = Counter()
    preserved = {r["unitID"] for r in read(final.ROOT, "preserved-v1.jsonl")}
    native = {}
    for response in w.r.rows(pin(final.ROOT / "execution/output_file_id.jsonl")):
        uid = response["custom_id"]
        w.require(uid not in native, "DUPLICATE_BATCH_RESPONSE")
        native[uid] = response["response"]["body"]
    for version, folder in [("v1", final.previous.ROOT), ("v2", final.ROOT)]:
        for req in read(folder, "requests.jsonl"):
            uid = req["custom_id"]
            raw_path = pin(folder / "execution" / f"{uid}.response.json")
            report = w.live.load(pin(folder / "execution" / f"{uid}.validation.json"))
            binding = w.live.load(pin(folder / "bindings" / f"{uid}.json"))
            if version == "v1" and uid not in preserved:
                # These seven partitions were replaced in v2. Keep their optional leads
                # as historical signals only, without using the superseded assignments.
                w.require(report["status"] == "held", "PRESERVED_DRIFT")
                for lead in report["relationLeads"]:
                    leads.append(
                        dict(
                            reference=[version, uid, lead["index"]],
                            raw=str(raw_path),
                            original=lead,
                            status="superseded_partition_lead",
                            reasons=lead["reasons"],
                            citations=lead["citations"],
                        )
                    )
                continue
            if version == "v2":
                raw = w.live.load(raw_path)
                w.require(native.pop(uid) == raw and raw["status"] == "completed", "RAW_BINDING")
                replay = final.evaluate(
                    w.transport.decode(w.live.provider.extract_model_output(raw)), req["body"], binding
                )
                w.require(all(report[k] == v for k, v in replay.items()), "V2_REPLAY_DRIFT")
                rows = [corrected(a) for a in report["assignments"]]
                for before, after in zip(report["assignments"], rows):
                    if before["reasons"] and not after["reasons"]:
                        stats["v2_recovered_groups"] += 1
                        stats["v2_recovered_occurrences"] += len(after["occurrenceIDs"])
            else:
                w.require(report["status"] == "complete_prediction", "PRESERVED_DRIFT")
                rows = report["assignments"]
            ids = set(binding["aliases"].values())
            w.require(ids.isdisjoint(components), "COMPONENT_OVERLAP")
            components.update(dict.fromkeys(ids, uid))
            resolved = set()
            for row in rows:
                ref = [version, uid, row["itemIndex"]]
                assessments.append(
                    dict(
                        reference=ref,
                        assessment=row,
                        raw=str(raw_path),
                        sourceValidation=str(folder / "execution" / f"{uid}.validation.json"),
                    )
                )
                if row["reasons"]:
                    continue
                key = tuple(sorted(row["occurrenceIDs"]))
                w.require(set(key) <= ids and resolved.isdisjoint(key), "PARTITION_DRIFT")
                resolved.update(key)
                if row["category"] == "strict_identity":
                    g = groups.setdefault(key, dict(authority="automatic_prediction", support=[]))
                    g["support"].append(ref)
                    stats[version + "_strict_groups"] += 1
                    stats[version + "_strict_occurrences"] += len(key)
                else:
                    for o in key:
                        terminal[o] = row["category"]
            for o in ids - resolved:
                terminal[o] = "mechanically_unresolved"
            stats[version + "_complete" if ids == resolved else version + "_partial"] += 1
            for lead in report["relationLeads"]:
                item = resolve_lead(lead, rows, binding)
                if version == "v2" and lead["reasons"] and not item["reasons"]:
                    previous_status = resolve_lead(lead, report["assignments"], binding)["status"]
                    label = (
                        "alias_binding"
                        if previous_status == "evidence_lead"
                        else "newly_admissible_assignment"
                    )
                    stats["v2_recovered_lead_" + label] += 1
                if version == "v1":
                    w.require(lead["status"] != "evidence_lead" or not item["reasons"], "V1_LEAD_DRIFT")
                    # Preserved v1 dispositions are authoritative.
                    item["status"] = lead["status"]
                leads.append(dict(reference=[version, uid, lead["index"]], raw=str(raw_path), **item))
                stats[version + "_" + item["status"]] += 1
    w.require(not native and len(set(components.values())) == 157, "POPULATION_DRIFT")
    return components, terminal, assessments, leads, stats


def reconcile_prior(locks, groups, old, old_refs, components):
    """Keep exact locks and supersede only prior targets wholly inside one final component."""
    for k in locks:
        w.require(
            not set(k).intersection(components) or groups[k]["support"], "PROTECTED_MEMBERSHIP_CHANGE"
        )
    superseded = []
    for cid, ids in sorted(old.items()):
        key = tuple(sorted(ids))
        touched = set(ids).intersection(components)
        if touched:
            w.require(
                touched == set(ids) and len({components[o] for o in ids}) == 1, "PARTIAL_PRIOR_SCOPE"
            )
        if not touched or key in groups:
            g = groups.setdefault(key, dict(authority="automatic_prediction", support=[]))
            g.update(priorTarget=cid, priorDecisionIDs=sorted(old_refs[cid]))
        else:
            superseded.append(
                dict(
                    priorTarget=cid,
                    oldMembership=key,
                    component=components[ids[0]],
                    priorDecisionIDs=sorted(old_refs[cid]),
                )
            )
    return superseded


def terminal_rows(terminal, components, members, assessments):
    """Trace an unassigned occurrence to its omitted partition slot or affected assessment."""
    dependencies = defaultdict(list)
    reasons = defaultdict(set)
    for record in assessments:
        row = record["assessment"]
        for oid in row["occurrenceIDs"]:
            if oid in terminal:
                dependencies[oid].append(record["reference"])
                reasons[oid].update(row["reasons"])
    for oid, status in sorted(terminal.items()):
        if not dependencies[oid]:
            reasons[oid].add("OMITTED_FROM_PARTITION")
        yield dict(
            occurrenceID=oid,
            unitID=components[oid],
            status=status,
            assessmentReferences=dependencies[oid],
            reasons=sorted(reasons[oid]),
            originalMember=members[oid],
        )


def breakdown(rows: list, field: str) -> dict:
    """Report both disjoint group and occurrence counts for each category."""
    counts = defaultdict(Counter)
    for row in rows:
        for measure in ("groups", "occurrences"):
            counts[str(row[field])][measure] += row[measure]
    return dict(counts)


def relation_inventory(read, sigs, leads, projections):
    """Collect exact directed occurrence hypotheses and assignment-level evidence leads separately."""
    relation_inputs = defaultdict(list)

    def add(kind, predicate, sides, support):
        """Aggregate support by directed endpoint memberships and predicate."""
        key = (kind, predicate, *[tuple(sorted(side)) for side in sides])
        relation_inputs[key].append(support)

    for p in read(rec.PRIOR, "typed-relation-proposals.jsonl"):
        add(
            "typed",
            p["predicate"],
            [[p["subject"]], [p["object"]]],
            dict(source="decision-stage/v2", record=p),
        )
    for a in read(final.replay.ROOT, "item-ledger.jsonl"):
        if a["itemType"] == "typedRelations":
            add(
                "typed",
                sigs[a["modelItem"]["signatureID"]]["name"],
                [[o] for o in a["occurrenceIDs"]],
                dict(source="collective-adjudication/v4", record=a),
            )
    unresolved = []
    for item in leads:
        if item["status"] == "evidence_lead":
            add("lead", None, [s["membership"] for s in item["sides"]], item)
        else:
            unresolved.append(item)
    relation_rows = []
    for (kind, predicate, left, right), support in relation_inputs.items():
        relation_rows.append(
            dict(
                kind=kind,
                predicate=predicate,
                occurrenceEndpoints=[left, right],
                projections=[{o: projections.get(o) for o in side} for side in (left, right)],
                support=support,
            )
        )
    return relation_rows, unresolved


def main():
    """Close in a fresh ignored directory or verify all source and output hashes."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["run", "verify"])
    p.add_argument("--output", type=Path, default=ROOT)
    a = p.parse_args()
    result = (run if a.mode == "run" else final.replay.verify)(a.output)
    print(json.dumps({k: v for k, v in result.items() if k != "distribution"}, indent=2))


if __name__ == "__main__":
    main()
