"""Deterministically compute the frozen pre-adjudication Human Core N=2 view.

This module deliberately implements only the Human-to-Human rules in the amended
matching contract.  It never changes an annotation or supplies an adjudication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[4]
GOLD_ROOT = PROJECT_ROOT / "data/curation/papers/m2/human_core_gold"
COMPOSITE_PATH = GOLD_ROOT / "publication_human_core_annotator_a_n2_composite_view_v0.1.5.json"
PRESERVATION_PATH = GOLD_ROOT / "publication_human_core_reliability_annotation_preservation_v0.1.5.json"
DEFAULT_OUTPUT = GOLD_ROOT / "publication_human_core_n2_pre_adjudication_reliability_v0.1.5.json"
DEFAULT_REPORT = GOLD_ROOT / "publication_human_core_n2_pre_adjudication_reliability_v0.1.5.md"
N2_UNITS = ("pub:34:sec:0015:unit:0001", "pub:79:sec:0004:unit:0001")


class AuthorityError(ValueError):
    """Raised when a frozen input or required provenance field is invalid."""


@dataclass(frozen=True)
class Record:
    """A positive annotation record with its frozen provenance and evidence index."""

    role: str
    partition: str
    session: str
    unit: str
    kind: str
    value: dict[str, Any]
    evidence: dict[str, dict[str, Any]]
    artifact: str
    treatments: dict[str, str]
    target_states: dict[str, str]

    @property
    def key(self) -> str:
        candidate = self.value.get("candidateID")
        if not isinstance(candidate, str) or not candidate:
            raise AuthorityError("record lacks candidateID")
        return "|".join(("human", self.role, self.partition, self.session, self.unit, self.kind, candidate))


def _sha256(path: Path) -> str:
    """Return the SHA-256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    """Load a JSON object or fail closed."""
    if not path.is_file():
        raise AuthorityError(f"missing frozen authority: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AuthorityError(f"authority is not an object: {path}")
    return data


def _verify_bound_path(root: Path, binding: dict[str, Any]) -> None:
    """Verify one path/SHA binding embedded in a frozen authority."""
    path = root / binding["path"]
    if _sha256(path) != binding["sha256"]:
        raise AuthorityError(f"SHA-256 mismatch for frozen authority: {binding['path']}")


def load_frozen_inputs(root: Path = PROJECT_ROOT) -> tuple[list[Record], list[Record], dict[str, Any]]:
    """Load and validate the exact frozen A composite and B raw export."""
    composite = _load(root / COMPOSITE_PATH.relative_to(PROJECT_ROOT))
    preservation = _load(root / PRESERVATION_PATH.relative_to(PROJECT_ROOT))
    if tuple(composite.get("sourceUnitIDs", ())) != N2_UNITS or tuple(preservation.get("submittedSourceUnitIDs", ())) != N2_UNITS:
        raise AuthorityError("frozen N=2 membership does not exactly match the contract")
    for authority in composite.get("sourceAuthorities", {}).values():
        if authority.get("path"):
            _verify_bound_path(root, authority)
        else:
            for binding in authority.values():
                if isinstance(binding, dict) and "path" in binding:
                    _verify_bound_path(root, binding)
                if isinstance(binding, dict) and "export" in binding:
                    _verify_bound_path(root, binding["export"])
                if isinstance(binding, dict):
                    for nested in binding.values():
                        if isinstance(nested, dict) and "path" in nested:
                            _verify_bound_path(root, nested)
    export_binding = preservation.get("export", {})
    _verify_bound_path(root, export_binding)
    b_export = _load(root / export_binding["path"])
    if b_export.get("annotationSessionID") != preservation.get("annotationSessionID") or b_export.get("annotatorID") != preservation.get("annotatorID"):
        raise AuthorityError("Annotator B export session or annotator provenance differs from preservation record")

    a_records: list[Record] = []
    for unit_entry in composite.get("units", []):
        if unit_entry.get("sourceUnitID") not in N2_UNITS:
            raise AuthorityError("Annotator A composite contains a non-N=2 unit")
        for partition in ("primaryV014", "supplementalV015"):
            partition_entry = unit_entry.get(partition)
            annotation = partition_entry.get("annotation") if isinstance(partition_entry, dict) else None
            if not isinstance(annotation, dict):
                raise AuthorityError(f"Annotator A composite lacks {partition}")
            a_records.extend(_records(annotation, "annotator_a", partition))
    b_records: list[Record] = []
    seen_units: set[str] = set()
    for wrapper in b_export.get("annotations", []):
        annotation = wrapper.get("annotation") if isinstance(wrapper, dict) else None
        if not isinstance(annotation, dict):
            raise AuthorityError("Annotator B export annotation is unavailable")
        unit = annotation.get("sourceUnitID")
        if unit not in N2_UNITS or unit in seen_units:
            raise AuthorityError("Annotator B export has invalid N=2 membership")
        seen_units.add(unit)
        b_records.extend(_records(annotation, "annotator_b", "reliabilityV015"))
    if tuple(sorted(seen_units)) != tuple(sorted(N2_UNITS)):
        raise AuthorityError("Annotator B export does not contain every frozen N=2 unit")
    provenance = {
        "annotatorAComposite": str(COMPOSITE_PATH.relative_to(PROJECT_ROOT)),
        "annotatorBPreservation": str(PRESERVATION_PATH.relative_to(PROJECT_ROOT)),
        "annotatorBRawExport": export_binding["path"],
        "annotatorBRawExportSHA256": export_binding["sha256"],
    }
    return a_records, b_records, provenance


def _records(annotation: dict[str, Any], role: str, partition: str) -> list[Record]:
    """Convert one source-unit annotation to provenance-qualified positive records."""
    required = ("annotationSessionID", "sourceUnitID", "sourceArtifactID", "evidenceSpans")
    if any(not annotation.get(field) for field in required):
        raise AuthorityError("annotation lacks required provenance or evidence fields")
    evidence = {span["evidenceSpanID"]: span for span in annotation["evidenceSpans"]}
    output: list[Record] = []
    for kind, field in (("node", "nodes"), ("relation", "relations")):
        for value in annotation.get(field, []):
            if not isinstance(value, dict) or not value.get("candidateID"):
                raise AuthorityError("record lacks required candidate provenance")
            ids = value.get("evidenceSpanIDs")
            if not isinstance(ids, list) or not ids or any(item not in evidence for item in ids):
                raise AuthorityError("record lacks resolvable relation/node evidence")
            states = {row["operationalTargetID"]: row["state"] for row in annotation.get("targetStates", [])}
            treatments = annotation.get("completenessTreatmentByTarget")
            if not isinstance(treatments, dict) or not isinstance(states, dict):
                raise AuthorityError("annotation lacks routed treatment or target-state provenance")
            output.append(Record(role, partition, annotation["annotationSessionID"], annotation["sourceUnitID"], kind, value, evidence, annotation["sourceArtifactID"], treatments, states))
    return output


def _span(span: dict[str, Any]) -> tuple[int, int, str, str]:
    """Return validated unit-offset span coordinates and text."""
    start, end = span.get("startOffsetInUnit"), span.get("endOffsetInUnit")
    if not isinstance(start, int) or not isinstance(end, int) or end <= start:
        raise AuthorityError("invalid required half-open span")
    unit, artifact = span.get("sourceUnitID"), span.get("sourceArtifactID")
    if not isinstance(unit, str) or not isinstance(artifact, str):
        raise AuthorityError("span lacks source provenance")
    return start, end, unit, artifact


def span_metrics(left: dict[str, Any], right: dict[str, Any]) -> dict[str, float | bool]:
    """Compute the contract's character-span metrics for one span pair."""
    ls, le, lu, la = _span(left)
    rs, re, ru, ra = _span(right)
    intersection = max(0, min(le, re) - max(ls, rs)) if lu == ru and la == ra else 0
    precision, recall = intersection / (le - ls), intersection / (re - rs)
    f1 = 0.0 if not precision + recall else 2 * precision * recall / (precision + recall)
    exact = ls == rs and le == re and left.get("exactText") == right.get("exactText") and lu == ru and la == ra
    return {"precision": precision, "recall": recall, "f1": f1, "exact": exact, "qualifies": f1 >= .80 and precision >= .70 and recall >= .70}


def _identity_conflicts(left: Record, right: Record) -> bool:
    """Apply only explicit frozen source-local identity conflict guards."""
    for field in ("existingNodeID", "identityScope", "artifactScope"):
        a, b = left.value.get(field), right.value.get(field)
        if a is not None and b is not None and a != b:
            return True
    for field in ("contextualOwner", "contextualModel", "contextualMethod", "contextualExperiment", "contextualCondition", "contextualValue", "contextualRole"):
        a, b = left.value.get(field), right.value.get(field)
        if a is not None and b is not None and a != b:
            return True
    return False


def _coverage(spans: Iterable[dict[str, Any]]) -> dict[str, list[tuple[int, int]]]:
    """Merge character spans by source unit for evidence-set comparison."""
    grouped: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for item in spans:
        start, end, unit, _ = _span(item)
        grouped[unit].append((start, end))
    for unit, intervals in grouped.items():
        merged: list[tuple[int, int]] = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        grouped[unit] = merged
    return dict(grouped)


def _evidence_metrics(left: Record, right: Record) -> dict[str, float | bool]:
    """Compare resolved evidence span character coverage for two records."""
    a = _coverage(left.evidence[item] for item in left.value["evidenceSpanIDs"])
    b = _coverage(right.evidence[item] for item in right.value["evidenceSpanIDs"])
    def length(value: dict[str, list[tuple[int, int]]]) -> int:
        return sum(end - start for rows in value.values() for start, end in rows)
    intersection = 0
    for unit in set(a) & set(b):
        for x1, x2 in a[unit]:
            for y1, y2 in b[unit]:
                intersection += max(0, min(x2, y2) - max(x1, y1))
    alen, blen = length(a), length(b)
    precision, recall = intersection / alen, intersection / blen
    f1 = 0.0 if not precision + recall else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1, "exact": a == b}


def _best_assignment(left: list[Record], right: list[Record], edges: dict[tuple[int, int], tuple[Any, ...]]) -> list[tuple[int, int]]:
    """Return the contract-ordered maximum one-to-one assignment for one unit."""
    if not edges:
        return []
    # Integer mixed-radix weights preserve the stated lexicographic preference
    # order.  Candidate IDs are sorted before matrix construction, so the final
    # deterministic Hungarian tie resolution is independent of input order.
    size = max(len(left), len(right))
    max_count = size + 1
    weights = [[0 for _ in range(size)] for _ in range(size)]
    left_order = sorted(range(len(left)), key=lambda i: left[i].key)
    right_order = sorted(range(len(right)), key=lambda j: right[j].key)
    max_f1 = 1_000_000
    for ri, i in enumerate(left_order):
        for cj, j in enumerate(right_order):
            values = edges.get((i, j))
            if values is None:
                continue
            encoded = 0
            for position, value in enumerate(values):
                if isinstance(value, float):
                    value = round(value * max_f1)
                # Boundary preferences are stored negative; shift to nonnegative.
                value = int(value) + (max_f1 if value < 0 else 0)
                encoded = encoded * (max_f1 * 2 + 1) + value
            weights[ri][cj] = (max_f1 * 2 + 1) ** len(values) * max_count + encoded
    maximum = max(max(row) for row in weights)
    # Hungarian algorithm for a square minimum-cost matrix (one-indexed form).
    u = [0] * (size + 1); v = [0] * (size + 1); p = [0] * (size + 1); way = [0] * (size + 1)
    for i in range(1, size + 1):
        p[0] = i; j0 = 0; minv = [None] * (size + 1); used = [False] * (size + 1)
        while True:
            used[j0] = True; i0 = p[j0]; delta = None; j1 = 0
            for j in range(1, size + 1):
                if not used[j]:
                    cur = maximum - weights[i0 - 1][j - 1] - u[i0] - v[j]
                    if minv[j] is None or cur < minv[j]: minv[j], way[j] = cur, j0
                    if delta is None or minv[j] < delta: delta, j1 = minv[j], j
            for j in range(size + 1):
                if used[j]: u[p[j]] += delta; v[j] -= delta
                elif minv[j] is not None: minv[j] -= delta
            j0 = j1
            if p[j0] == 0: break
        while True:
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
            if j0 == 0: break
    assigned = [(left_order[p[j] - 1], right_order[j - 1]) for j in range(1, size + 1) if p[j] and p[j] <= len(left_order) and j <= len(right_order) and (left_order[p[j] - 1], right_order[j - 1]) in edges]
    return sorted(assigned, key=lambda pair: (left[pair[0]].key, right[pair[1]].key))


def pair_nodes(left: list[Record], right: list[Record]) -> list[tuple[Record, Record, dict[str, Any]]]:
    """Pair nodes using overlap/context eligibility and contract tie preferences."""
    pairs: list[tuple[Record, Record, dict[str, Any]]] = []
    for unit in N2_UNITS:
        a, b = [x for x in left if x.kind == "node" and x.unit == unit], [x for x in right if x.kind == "node" and x.unit == unit]
        edges: dict[tuple[int, int], tuple[Any, ...]] = {}
        metrics: dict[tuple[int, int], dict[str, Any]] = {}
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                measure = span_metrics(x.value["mentionSpan"], y.value["mentionSpan"])
                if measure["qualifies"] and not _identity_conflicts(x, y):
                    boundary = abs(x.value["mentionSpan"]["startOffsetInUnit"] - y.value["mentionSpan"]["startOffsetInUnit"]) + abs(x.value["mentionSpan"]["endOffsetInUnit"] - y.value["mentionSpan"]["endOffsetInUnit"])
                    edges[i, j] = (int(measure["exact"]), measure["f1"], -boundary)
                    metrics[i, j] = measure
        for i, j in _best_assignment(a, b, edges):
            pairs.append((a[i], b[j], metrics[i, j]))
    return pairs


def _endpoint_match(a: dict[str, Any], b: dict[str, Any], node_pairs: set[tuple[str, str]]) -> bool:
    """Determine endpoint occurrence correspondence only for assignment preference."""
    if a.get("referenceType") == b.get("referenceType") == "deterministic_node":
        return a.get("referenceID") == b.get("referenceID") and a.get("artifactID") == b.get("artifactID")
    return (a.get("referenceID"), b.get("referenceID")) in node_pairs


def pair_relations(left: list[Record], right: list[Record], node_pairs: list[tuple[Record, Record, dict[str, Any]]]) -> list[tuple[Record, Record, dict[str, Any]]]:
    """Pair relations solely through relation-evidence eligibility and stated preferences."""
    node_lookup = {(a.value["candidateID"], b.value["candidateID"]) for a, b, _ in node_pairs}
    pairs: list[tuple[Record, Record, dict[str, Any]]] = []
    for unit in N2_UNITS:
        a, b = [x for x in left if x.kind == "relation" and x.unit == unit], [x for x in right if x.kind == "relation" and x.unit == unit]
        edges: dict[tuple[int, int], tuple[Any, ...]] = {}; metrics: dict[tuple[int, int], dict[str, Any]] = {}
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                measure = _evidence_metrics(x, y)
                if measure["f1"] >= .80 and measure["precision"] >= .70 and measure["recall"] >= .70:
                    endpoints = int(_endpoint_match(x.value["source"], y.value["source"], node_lookup)) + int(_endpoint_match(x.value["target"], y.value["target"], node_lookup))
                    boundary = 0
                    for xid in x.value["evidenceSpanIDs"]:
                        for yid in y.value["evidenceSpanIDs"]:
                            xs, xe, _, _ = _span(x.evidence[xid]); ys, ye, _, _ = _span(y.evidence[yid]); boundary += abs(xs-ys) + abs(xe-ye)
                    edges[i, j] = (endpoints, int(measure["exact"]), measure["f1"], -boundary); metrics[i, j] = measure
        for i, j in _best_assignment(a, b, edges): pairs.append((a[i], b[j], metrics[i, j]))
    return pairs


def _mean(rows: list[float]) -> float | None:
    """Return an explicit undefined value for empty support."""
    return None if not rows else sum(rows) / len(rows)


def _detection(a: list[Record], b: list[Record], pairs: list[tuple[Record, Record, dict[str, Any]]], kind: str) -> dict[str, Any]:
    """Produce symmetric detection and contract-specific evidence summaries."""
    aa, bb = [x for x in a if x.kind == kind], [x for x in b if x.kind == kind]
    matched = len(pairs)
    summary: dict[str, Any] = {"annotatorASupport": len(aa), "annotatorBSupport": len(bb), "matchedSupport": matched, "annotatorACoverage": None if not aa else matched / len(aa), "annotatorBCoverage": None if not bb else matched / len(bb), "symmetricPairwiseF1": None if not aa and not bb else 2 * matched / (len(aa) + len(bb))}
    if kind == "node":
        summary["mentionBoundary"] = {"exactCount": sum(bool(m["exact"]) for _, _, m in pairs), "support": matched, "exactRate": None if not matched else sum(bool(m["exact"]) for _, _, m in pairs) / matched, "boundaryTolerantCount": matched, "boundaryTolerantRate": None if not matched else 1.0, "meanF1": _mean([float(m["f1"]) for _, _, m in pairs])}
        evidence = [_evidence_metrics(x, y) for x, y, _ in pairs]
        summary["supportingEvidence"] = {"exactCount": sum(bool(m["exact"]) for m in evidence), "support": matched, "exactRate": None if not matched else sum(bool(m["exact"]) for m in evidence) / matched, "meanPrecision": _mean([float(m["precision"]) for m in evidence]), "meanRecall": _mean([float(m["recall"]) for m in evidence]), "meanF1": _mean([float(m["f1"]) for m in evidence])}
    else:
        summary["relationEvidence"] = {"exactCount": sum(bool(m["exact"]) for _, _, m in pairs), "support": matched, "exactRate": None if not matched else sum(bool(m["exact"]) for _, _, m in pairs) / matched, "meanPrecision": _mean([float(m["precision"]) for _, _, m in pairs]), "meanRecall": _mean([float(m["recall"]) for _, _, m in pairs]), "meanF1": _mean([float(m["f1"]) for _, _, m in pairs])}
    return summary


def _characterization(node_pairs: list[tuple[Record, Record, dict[str, Any]]], relation_pairs: list[tuple[Record, Record, dict[str, Any]]]) -> dict[str, Any]:
    """Report characterization agreement without feeding it back into matching."""
    def rate(values: Iterable[bool]) -> dict[str, Any]:
        rows = list(values); return {"numerator": sum(rows), "denominator": len(rows), "observedAgreement": None if not rows else sum(rows)/len(rows)}
    lookup = {(a.value["candidateID"], b.value["candidateID"]) for a,b,_ in node_pairs}
    def endpoint(a: dict[str, Any], b: dict[str, Any]) -> bool: return _endpoint_match(a, b, lookup)
    return {"nodes": {"exactOntologyClass": rate(a.value.get("ontologyClassID") == b.value.get("ontologyClassID") for a,b,_ in node_pairs), "exactOperationalTarget": rate(a.value.get("operationalTargetID") == b.value.get("operationalTargetID") for a,b,_ in node_pairs)}, "relations": {"exactOntologyRelationType": rate(a.value.get("ontologyRelationID") == b.value.get("ontologyRelationID") for a,b,_ in relation_pairs), "exactOperationalTarget": rate(a.value.get("operationalRelationID") == b.value.get("operationalRelationID") for a,b,_ in relation_pairs), "directionWhenSameRelationType": rate(a.value.get("source") == b.value.get("source") and a.value.get("target") == b.value.get("target") for a,b,_ in relation_pairs if a.value.get("ontologyRelationID") == b.value.get("ontologyRelationID")), "sourceEndpoint": rate(endpoint(a.value["source"],b.value["source"]) for a,b,_ in relation_pairs), "targetEndpoint": rate(endpoint(a.value["target"],b.value["target"]) for a,b,_ in relation_pairs), "bothEndpoints": rate(endpoint(a.value["source"],b.value["source"]) and endpoint(a.value["target"],b.value["target"]) for a,b,_ in relation_pairs)}}


def _presence_absence(a: list[Record], b: list[Record]) -> dict[str, Any]:
    """Build the exhaustive routed extract-and-evaluate unit-target 2x2 tables."""
    by_role_unit: dict[tuple[str, str], Record] = {}
    for record in a + b:
        by_role_unit.setdefault((record.role, record.unit), record)
    rows: dict[str, list[tuple[bool, bool]]] = {"node": [], "relation": []}
    for unit in N2_UNITS:
        ar, br = by_role_unit.get(("annotator_a", unit)), by_role_unit.get(("annotator_b", unit))
        if ar is None or br is None:
            raise AuthorityError("missing frozen routed target state for an N=2 annotator")
        # Presence/absence requires an exhaustive decision from both peers.  A
        # target exposed only to one frozen annotation is not silently treated
        # as an absence on the other side.
        targets = set(ar.treatments) & set(br.treatments)
        for target in sorted(targets):
            at, bt = ar.treatments.get(target), br.treatments.get(target)
            if at != "extract_and_evaluate" or bt != "extract_and_evaluate":
                continue
            if target not in ar.target_states or target not in br.target_states:
                raise AuthorityError(f"missing target state: {unit} {target}")
            kind = "relation" if target.startswith("PUB-R-") else "node"
            rows[kind].append((ar.target_states[target] == "reviewed_positive", br.target_states[target] == "reviewed_positive"))
    output: dict[str, Any] = {}
    for kind, values in rows.items():
        table = {"aPositive_bPositive": sum(x and y for x,y in values), "aPositive_bAbsent": sum(x and not y for x,y in values), "aAbsent_bPositive": sum(not x and y for x,y in values), "aAbsent_bAbsent": sum(not x and not y for x,y in values)}
        output[kind] = {"support": len(values), "table": table, "observedAgreement": None if not values else (table["aPositive_bPositive"] + table["aAbsent_bAbsent"]) / len(values)}
    return {"scope": "routed extract_and_evaluate unit-target decisions only", "byKind": output}


def compute(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Compute the complete deterministic N=2 pre-adjudication analysis."""
    a, b, provenance = load_frozen_inputs(root)
    node_pairs = pair_nodes(a, b)
    relation_pairs = pair_relations(a, b, node_pairs)
    node_summary, relation_summary = _detection(a,b,node_pairs,"node"), _detection(a,b,relation_pairs,"relation")
    diagnostics = {"nodeDetectionOnlyA": sorted(x.key for x in a if x.kind == "node" and x.key not in {p[0].key for p in node_pairs}), "nodeDetectionOnlyB": sorted(x.key for x in b if x.kind == "node" and x.key not in {p[1].key for p in node_pairs}), "relationDetectionOnlyA": sorted(x.key for x in a if x.kind == "relation" and x.key not in {p[0].key for p in relation_pairs}), "relationDetectionOnlyB": sorted(x.key for x in b if x.kind == "relation" and x.key not in {p[1].key for p in relation_pairs}), "nodeClassDisagreements": sum(x.value.get("ontologyClassID") != y.value.get("ontologyClassID") for x,y,_ in node_pairs), "nodeOperationalTargetDisagreements": sum(x.value.get("operationalTargetID") != y.value.get("operationalTargetID") for x,y,_ in node_pairs), "relationTypeDisagreements": sum(x.value.get("ontologyRelationID") != y.value.get("ontologyRelationID") for x,y,_ in relation_pairs), "relationOperationalTargetDisagreements": sum(x.value.get("operationalRelationID") != y.value.get("operationalRelationID") for x,y,_ in relation_pairs)}
    return {"artifactType": "human_to_human_n2_pre_adjudication_reliability", "artifactVersion": "0.1.0", "matchingContract": "docs/publication_human_core_amended_matching_contract_v0.1.md", "scope": "frozen N=2 only; descriptive pre-adjudication; no PASS/FAIL or acceptance logic", "sourceUnitIDs": list(N2_UNITS), "frozenInputs": provenance, "nodeDetection": node_summary, "relationDetection": relation_summary, "characterization": _characterization(node_pairs, relation_pairs), "exhaustivePresenceAbsence": _presence_absence(a,b), "disagreementDiagnostics": diagnostics, "pairings": {"nodes": [{"annotatorAKey":x.key,"annotatorBKey":y.key,"mentionSpan":m} for x,y,m in node_pairs], "relations": [{"annotatorAKey":x.key,"annotatorBKey":y.key,"relationEvidence":m} for x,y,m in relation_pairs]}}


def render_report(result: dict[str, Any]) -> str:
    """Render the concise contract-required human-readable descriptive report."""
    n, r, d, c = result["nodeDetection"], result["relationDetection"], result["disagreementDiagnostics"], result["characterization"]
    nt, rt = n["mentionBoundary"], r["relationEvidence"]
    ne = n["supportingEvidence"]
    p = result["exhaustivePresenceAbsence"]["byKind"]
    direction = c["relations"]["directionWhenSameRelationType"]
    return "\n".join(("# Human-to-Human N=2 Pre-Adjudication Reliability", "", "This is a deterministic descriptive comparison under the frozen amended matching contract. It contains no adjudication, annotation modification, reliability gate, PASS/FAIL result, or production-acceptance inference.", "", "## Detection and evidence", "", f"- Nodes: A={n['annotatorASupport']}, B={n['annotatorBSupport']}, matched={n['matchedSupport']}, A coverage={n['annotatorACoverage']:.6f}, B coverage={n['annotatorBCoverage']:.6f}, symmetric pairwise F1={n['symmetricPairwiseF1']:.6f}.", f"- Node mention boundaries: exact={nt['exactCount']}/{nt['support']} ({nt['exactRate']:.6f}); tolerant={nt['boundaryTolerantCount']}/{nt['support']}; mean F1={nt['meanF1']:.6f}.", f"- Node supporting evidence: exact={ne['exactCount']}/{ne['support']} ({ne['exactRate']:.6f}); mean P/R/F1={ne['meanPrecision']:.6f}/{ne['meanRecall']:.6f}/{ne['meanF1']:.6f}.", f"- Relations: A={r['annotatorASupport']}, B={r['annotatorBSupport']}, matched={r['matchedSupport']}, A coverage={r['annotatorACoverage']:.6f}, B coverage={r['annotatorBCoverage']:.6f}, symmetric pairwise F1={r['symmetricPairwiseF1']:.6f}.", f"- Relation evidence: exact={rt['exactCount']}/{rt['support']} ({rt['exactRate']:.6f}); mean P/R/F1={rt['meanPrecision']:.6f}/{rt['meanRecall']:.6f}/{rt['meanF1']:.6f}.", "", "## Characterization and exhaustive presence/absence", "", f"- Nodes: class={c['nodes']['exactOntologyClass']['numerator']}/{c['nodes']['exactOntologyClass']['denominator']}; operational target={c['nodes']['exactOperationalTarget']['numerator']}/{c['nodes']['exactOperationalTarget']['denominator']}.", f"- Relations: type={c['relations']['exactOntologyRelationType']['numerator']}/{c['relations']['exactOntologyRelationType']['denominator']}; target={c['relations']['exactOperationalTarget']['numerator']}/{c['relations']['exactOperationalTarget']['denominator']}; direction (same type)={direction['numerator']}/{direction['denominator']}; source endpoint={c['relations']['sourceEndpoint']['numerator']}/{c['relations']['sourceEndpoint']['denominator']}; target endpoint={c['relations']['targetEndpoint']['numerator']}/{c['relations']['targetEndpoint']['denominator']}; both={c['relations']['bothEndpoints']['numerator']}/{c['relations']['bothEndpoints']['denominator']}.", f"- Exhaustive node table (++,+−,−+,−−)={p['node']['table']['aPositive_bPositive']},{p['node']['table']['aPositive_bAbsent']},{p['node']['table']['aAbsent_bPositive']},{p['node']['table']['aAbsent_bAbsent']} (n={p['node']['support']}; observed agreement={p['node']['observedAgreement']:.6f}).", f"- Exhaustive relation table (++,+−,−+,−−)={p['relation']['table']['aPositive_bPositive']},{p['relation']['table']['aPositive_bAbsent']},{p['relation']['table']['aAbsent_bPositive']},{p['relation']['table']['aAbsent_bAbsent']} (n={p['relation']['support']}; observed agreement={p['relation']['observedAgreement']:.6f}).", "", "## Permitted disagreement diagnostics", "", f"- Detection-only: nodes A={len(d['nodeDetectionOnlyA'])}, B={len(d['nodeDetectionOnlyB'])}; relations A={len(d['relationDetectionOnlyA'])}, B={len(d['relationDetectionOnlyB'])}.", f"- Characterization: node class={d['nodeClassDisagreements']}, node operational target={d['nodeOperationalTargetDisagreements']}, relation type={d['relationTypeDisagreements']}, relation operational target={d['relationOperationalTargetDisagreements']}.", "", "The accompanying JSON artifact carries pairing keys, boundary/evidence summaries, and raw diagnostic keys for deterministic reproduction.", ""))


def main() -> None:
    """Run the frozen analysis and write its two deterministic artifacts."""
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT); parser.add_argument("--report", type=Path, default=DEFAULT_REPORT); args = parser.parse_args()
    result = compute(); args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"); args.report.write_text(render_report(result), encoding="utf-8")


if __name__ == "__main__":
    main()
