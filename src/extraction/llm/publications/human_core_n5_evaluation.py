"""Evaluate frozen Pilot 1 predictions against the immutable Human Core N=5 reference.

This module implements only extractor-to-Human-Core mode from the frozen amended
matching contract.  It derives a read-only reference view from the distinct primary
and supplemental exports and never mutates or semantically merges either source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .human_core_n2_reliability import AuthorityError


PROJECT_ROOT = Path(__file__).resolve().parents[4]
GOLD_ROOT = PROJECT_ROOT / "data/curation/papers/m2/human_core_gold"
PRIMARY_PATH = PROJECT_ROOT / "var/publication_pilot1_annotation/human-core/primary-researcher/exports/HUMAN_CORE_N5_PRIMARY_V1.annotation.json"
SUPPLEMENTAL_PATH = PROJECT_ROOT / "var/publication_pilot1_annotation/human-core/supplemental-researcher/exports/HUMAN_CORE_N5_SUPPLEMENTAL_V015.annotation.json"
PRIMARY_SHA256 = "9d71ae66c3218c4b8be21a3ea10b4015cb5502fce5eaf75f6bb0ac9922bc4e74"
SUPPLEMENTAL_SHA256 = "8d637084d3f14cae958b9a9bbe3acb8c74ca741a2c43a990ec939699266707a2"
ROUTING_PATH = PROJECT_ROOT / "data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl"
ROUTING_SHA256 = "66725306608139ccf3647ac7fd4a9fc150df67426498b6e3e7408320cb8c4a1f"
SUPPLEMENTAL_PACKAGE_PATH = GOLD_ROOT / "publication_human_core_supplemental_annotation_package_v0.1.5.json"
SUPPLEMENTAL_PACKAGE_SHA256 = "22d4946f0159361badbb8bf87517368a9d24ffa336d4c3549f3166c45b4334c2"
TARGET_INVENTORY_PATH = PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml"
TARGET_INVENTORY_GIT_BLOB = "8a4921d687e93d4e8db879ae2e9c611f07e04bd1"
HISTORICAL_C1_FREEZE_PATH = PROJECT_ROOT / "data/curation/papers/m2/publication_step6c_canonical_c1_freeze_v1.0.0.json"
CORRECTED_EVALUATION_ROOT = PROJECT_ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation"
CORRECTED_EVALUATION_FREEZE_PATH = CORRECTED_EVALUATION_ROOT / "publication_pilot1_corrected_evaluation_realization_freeze_v1.0.0.json"
CORRECTED_EVALUATION_FREEZE_ARTIFACT_SHA256 = "5aad26c75be98c759dacb14d31878e3c9c678662198b307d305360e3c9515842"
CORRECTED_PREDICTIONS_PATH = CORRECTED_EVALUATION_ROOT / "publication_pilot1_corrected_evaluation_canonical_predictions_v1.0.0.jsonl"
CORRECTED_PREDICTIONS_SHA256 = "e888c4c4c68ede19cb4c65275b96637fd183e64f887d9a649f70e57f98eadb86"
HUMAN_CORE_EXECUTION_COHORT = "human_core_n5"
MATCHING_CONTRACT_PATH = PROJECT_ROOT / "docs/publication_human_core_amended_matching_contract_v0.1.md"
V010_OUTPUT = GOLD_ROOT / "publication_human_core_n5_c1_confirmatory_evaluation_pre_freeze_v0.1.0.json"
V010_REPORT = GOLD_ROOT / "publication_human_core_n5_c1_confirmatory_evaluation_pre_freeze_v0.1.0.md"
V010_OUTPUT_SHA256 = "ee77ee845c6c92cbbf0776c46a09b1049d24b6b79d289ab98f90f8de0b2eaaba"
V010_REPORT_SHA256 = "a07292543dd4eae88edab9a569121cd850ccfcdd738af6c219e3bd76a4998414"
DEFAULT_OUTPUT = GOLD_ROOT / "publication_human_core_n5_corrected_evaluation_step7b_pre_freeze_v1.0.0.json"
DEFAULT_REPORT = GOLD_ROOT / "publication_human_core_n5_corrected_evaluation_step7b_pre_freeze_v1.0.0.md"


@dataclass(frozen=True)
class PredictionAuthority:
    """One immutable prediction realization available to the scorer."""

    name: str
    freeze_path: Path
    prediction_path: Path | None
    prediction_sha256: str | None
    artifact_type: str
    artifact_version: str
    execution: str
    report_title: str
    report_intro: str


@dataclass(frozen=True)
class EvaluationRecord:
    """One immutable human reference or accepted C1 prediction record."""

    side: str
    partition: str
    session_or_run: str
    request_id: str | None
    unit: str
    artifact: str
    kind: str
    value: dict[str, Any]
    evidence: tuple[dict[str, Any], ...]

    @property
    def target(self) -> str:
        """Return the record's operational target identifier."""
        field = "operationalTargetID" if self.kind == "node" else "operationalRelationID"
        value = self.value.get(field)
        if not isinstance(value, str) or not value:
            raise AuthorityError(f"{self.side} {self.kind} lacks {field}")
        return value

    @property
    def candidate_id(self) -> str:
        """Return the record-local candidate identifier."""
        value = self.value.get("candidateID")
        if not isinstance(value, str) or not value:
            raise AuthorityError(f"{self.side} {self.kind} lacks candidateID")
        return value

    @property
    def key(self) -> str:
        """Return the fully qualified stable provenance key required for ties."""
        if self.side == "reference":
            return "|".join(("human", "annotator_a", self.partition, self.session_or_run, self.unit, self.kind, self.candidate_id))
        if not self.request_id:
            raise AuthorityError("extractor record lacks immutable request provenance")
        return "|".join(("extractor", self.session_or_run, self.request_id, self.unit, self.kind, self.candidate_id))


@dataclass(frozen=True)
class FrozenInputs:
    """Validated read-only inputs for the single confirmatory computation."""

    references: tuple[EvaluationRecord, ...]
    predictions: tuple[EvaluationRecord, ...]
    opportunities: dict[str, dict[str, str]]
    routes: dict[str, dict[str, Any]]
    baseline_aliases: dict[str, str]
    provenance: dict[str, Any]


HISTORICAL_C1_AUTHORITY = PredictionAuthority(
    name="historical_c1",
    freeze_path=HISTORICAL_C1_FREEZE_PATH,
    prediction_path=None,
    prediction_sha256=None,
    artifact_type="publication_human_core_n5_c1_confirmatory_evaluation_pre_freeze",
    artifact_version="0.1.1",
    execution="one_time_step_7b_confirmatory_evaluation",
    report_title="Publication Human Core N=5 C1 Confirmatory Evaluation — PRE-FREEZE",
    report_intro="Historical C1-only reproducibility authority; not for prospective Step 7 use.",
)
CORRECTED_EVALUATION_AUTHORITY = PredictionAuthority(
    name="corrected_pilot1_evaluation",
    freeze_path=CORRECTED_EVALUATION_FREEZE_PATH,
    prediction_path=CORRECTED_PREDICTIONS_PATH,
    prediction_sha256=CORRECTED_PREDICTIONS_SHA256,
    artifact_type="publication_human_core_n5_corrected_evaluation_step7b_pre_freeze",
    artifact_version="1.0.0",
    execution="one_time_step_7b_confirmatory_evaluation_against_corrected_pilot1_realization",
    report_title="Publication Human Core N=5 Corrected Evaluation Step 7B — PRE-FREEZE",
    report_intro="This is the prospective strict deterministic Step 7B result against the frozen corrected Pilot 1 evaluation realization. It does not alter historical C1 Step 7B artifacts and is not a Step 7C freeze or closure record.",
)


def _sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    if not path.is_file():
        raise AuthorityError(f"missing frozen input: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha(path: Path) -> str:
    """Compute Git's SHA-1 blob identity without invoking Git."""
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object or fail closed."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityError(f"cannot load frozen JSON authority {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuthorityError(f"frozen JSON authority is not an object: {path}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL authority as a list of objects."""
    rows: list[dict[str, Any]] = []
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise AuthorityError(f"non-object JSONL row {number}: {path}")
            rows.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityError(f"cannot load frozen JSONL authority {path}: {exc}") from exc
    return rows


def _span(span: dict[str, Any]) -> tuple[int, int, str, str, str]:
    """Return validated half-open coordinates and literal text."""
    start, end = span.get("startOffsetInUnit"), span.get("endOffsetInUnit")
    unit, artifact = span.get("sourceUnitID"), span.get("sourceArtifactID")
    text = span.get("exactText", span.get("evidenceText"))
    if not isinstance(start, int) or not isinstance(end, int) or end <= start:
        raise AuthorityError("invalid required half-open evidence span")
    if not isinstance(unit, str) or not unit or not isinstance(artifact, str) or not artifact:
        raise AuthorityError("evidence span lacks exact source provenance")
    if not isinstance(text, str) or not text:
        raise AuthorityError("evidence span lacks exact literal text")
    return start, end, unit, artifact, text


def span_metrics(left: dict[str, Any], right: dict[str, Any]) -> dict[str, float | bool]:
    """Compute frozen qualifying character-span measures."""
    ls, le, lu, la, lt = _span(left)
    rs, re, ru, ra, rt = _span(right)
    intersection = max(0, min(le, re) - max(ls, rs)) if (lu, la) == (ru, ra) else 0
    precision, recall = intersection / (le - ls), intersection / (re - rs)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    exact = (ls, le, lu, la, lt) == (rs, re, ru, ra, rt)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact": exact,
        "qualifies": f1 >= 0.80 and precision >= 0.70 and recall >= 0.70,
    }


def _coverage(spans: Iterable[dict[str, Any]]) -> dict[tuple[str, str], list[tuple[int, int]]]:
    """Merge evidence character coverage independently by artifact and unit."""
    grouped: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for span in spans:
        start, end, unit, artifact, _ = _span(span)
        grouped[(artifact, unit)].append((start, end))
    for scope, intervals in grouped.items():
        merged: list[tuple[int, int]] = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        grouped[scope] = merged
    return dict(grouped)


def evidence_metrics(left: EvaluationRecord, right: EvaluationRecord) -> dict[str, float | bool]:
    """Compare evidence-set character coverage without imposing a joint-span rule."""
    a, b = _coverage(left.evidence), _coverage(right.evidence)
    length = lambda value: sum(end - start for rows in value.values() for start, end in rows)
    intersection = sum(
        max(0, min(ae, be) - max(astart, bstart))
        for scope in set(a) & set(b)
        for astart, ae in a[scope]
        for bstart, be in b[scope]
    )
    alen, blen = length(a), length(b)
    # Extractor-to-Human-Core mode is asymmetric: prediction coverage is
    # precision and immutable Human Core coverage is recall.
    precision, recall = intersection / blen, intersection / alen
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    exact_signatures = sorted(_span(item) for item in left.evidence) == sorted(_span(item) for item in right.evidence)
    return {"precision": precision, "recall": recall, "f1": f1, "exact": exact_signatures}


def _qualifying_evidence(left: EvaluationRecord, right: EvaluationRecord) -> bool:
    """Apply the ordinary rule: at least one evidence-span correspondence qualifies."""
    return any(span_metrics(a, b)["qualifies"] for a in left.evidence for b in right.evidence)


def _boundary_difference(left: EvaluationRecord, right: EvaluationRecord) -> int:
    """Return the deterministic total pairwise evidence-boundary difference."""
    total = 0
    for a in left.evidence:
        ast, aen, au, aa, _ = _span(a)
        for b in right.evidence:
            bst, ben, bu, ba, _ = _span(b)
            if (au, aa) == (bu, ba):
                total += abs(ast - bst) + abs(aen - ben)
    return total


def _identity_conflicts(reference: EvaluationRecord, prediction: EvaluationRecord) -> bool:
    """Apply only explicit frozen source-local identity conflict guards."""
    fields = (
        "existingNodeID", "identityScope", "artifactScope", "contextualOwner",
        "contextualModel", "contextualMethod", "contextualExperiment",
        "contextualCondition", "contextualValue", "contextualRole",
    )
    for field in fields:
        left, right = reference.value.get(field), prediction.value.get(field)
        if left is not None and right is not None and left != right:
            return True
    return False


def _human_records(export: dict[str, Any], partition: str, expected_session: str) -> tuple[list[EvaluationRecord], dict[str, dict[str, str]]]:
    """Create qualified records while preserving one immutable export partition."""
    if export.get("annotationSessionID") != expected_session or export.get("annotatorID") != "HUMAN_CORE_PRIMARY_RESEARCHER":
        raise AuthorityError(f"invalid immutable Annotator A provenance for {partition}")
    records: list[EvaluationRecord] = []
    treatments: dict[str, dict[str, str]] = {}
    for wrapper in export.get("annotations", []):
        annotation = wrapper.get("annotation") if isinstance(wrapper, dict) else None
        if not isinstance(annotation, dict) or wrapper.get("status") != "submitted" or annotation.get("workflowState") != "submitted":
            raise AuthorityError(f"{partition} contains a non-submitted or invalid annotation")
        unit, artifact = annotation.get("sourceUnitID"), annotation.get("sourceArtifactID")
        if not isinstance(unit, str) or not isinstance(artifact, str) or unit in treatments:
            raise AuthorityError(f"{partition} contains invalid or duplicate source-unit provenance")
        unit_treatments = annotation.get("completenessTreatmentByTarget")
        if not isinstance(unit_treatments, dict):
            raise AuthorityError(f"{partition} lacks a unit-specific treatment map")
        treatments[unit] = dict(unit_treatments)
        evidence = {row.get("evidenceSpanID"): row for row in annotation.get("evidenceSpans", []) if isinstance(row, dict)}
        for kind, field in (("node", "nodes"), ("relation", "relations")):
            for value in annotation.get(field, []):
                ids = value.get("evidenceSpanIDs") if isinstance(value, dict) else None
                if not isinstance(ids, list) or not ids or any(item not in evidence for item in ids):
                    raise AuthorityError(f"{partition} {kind} has unresolved evidence")
                records.append(EvaluationRecord("reference", partition, expected_session, None, unit, artifact, kind, value, tuple(evidence[item] for item in ids)))
    return records, treatments


def _prediction_records(row: dict[str, Any], realization_id: str) -> list[EvaluationRecord]:
    """Create records solely from one accepted-semantic Step 7 projection."""
    projection = row.get("acceptedSemanticProjection")
    if not isinstance(projection, dict) or projection.get("acceptanceStatus") != "production_accepted" or projection.get("step7PredictionContent") is not True:
        raise AuthorityError("Human Core prediction row is not frozen accepted-semantic Step 7 content")
    request = row.get("requestID")
    unit, artifact = projection.get("sourceUnitID"), projection.get("sourceArtifactID")
    attempt = projection.get("selectedProviderAttempt")
    output = projection.get("outputID")
    if not all(isinstance(value, str) and value for value in (request, unit, artifact, output)) or not isinstance(attempt, dict):
        raise AuthorityError("prediction projection lacks immutable run/request provenance")
    attempt_number = attempt.get("attemptNumber")
    request_hash = attempt.get("requestInputSha256")
    response_hash = attempt.get("providerResponseSha256")
    if not isinstance(attempt_number, int) or not all(isinstance(value, str) and value for value in (request_hash, response_hash)):
        raise AuthorityError("prediction projection lacks immutable selected-attempt provenance")
    run = f"{realization_id}|attempt-{attempt_number}|{output}|{request_hash}|{response_hash}"
    records: list[EvaluationRecord] = []
    for kind, field in (("node", "acceptedNodes"), ("relation", "acceptedEdges")):
        for wrapper in projection.get(field, []):
            if not isinstance(wrapper, dict) or wrapper.get("accepted") is not True:
                raise AuthorityError("prediction source contains a nonaccepted record")
            value = wrapper.get("candidate")
            evidence = wrapper.get("evidenceOccurrences")
            if not isinstance(value, dict) or not isinstance(evidence, list) or not evidence:
                raise AuthorityError("accepted prediction lacks candidate or evidence")
            records.append(EvaluationRecord("prediction", "acceptedSemanticProjection", run, request, unit, artifact, kind, value, tuple(evidence)))
    return records


def _inventory_targets() -> dict[str, dict[str, Any]]:
    """Load and validate the exact frozen v0.1.5 inventory blob."""
    if _git_blob_sha(TARGET_INVENTORY_PATH) != TARGET_INVENTORY_GIT_BLOB:
        raise AuthorityError("target inventory Git blob differs from frozen matching contract")
    value = yaml.safe_load(TARGET_INVENTORY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("profile_id") != "publication-pilot1-target-inventory-v0.1.5":
        raise AuthorityError("unexpected target inventory identity")
    rows = value.get("node_targets", []) + value.get("relation_targets", [])
    result = {row["operational_id"]: row for row in rows}
    if len(result) != len(rows):
        raise AuthorityError("duplicate operational target in frozen inventory")
    return result


def _prediction_binding(
    root: Path, authority: PredictionAuthority,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    """Validate one frozen realization and return its tracked prediction binding."""
    freeze_path = root / authority.freeze_path.relative_to(PROJECT_ROOT)
    freeze = _load_json(freeze_path)
    prediction_binding = freeze.get("trackedArtifacts", {}).get("predictions", {})
    if not isinstance(prediction_binding, dict):
        raise AuthorityError("prediction realization lacks a tracked prediction binding")
    if authority is HISTORICAL_C1_AUTHORITY:
        prediction_path = root / prediction_binding.get("path", "")
        if freeze.get("status") != "FROZEN_CLOSED" or freeze.get("step7Executed") is not False:
            raise AuthorityError("historical Step 6 freeze does not authorize its preserved C1 loader")
        if _sha256(prediction_path) != prediction_binding.get("sha256"):
            raise AuthorityError("historical canonical C1 prediction artifact differs from its Step 6 freeze")
        return freeze, prediction_binding, prediction_path

    if authority is not CORRECTED_EVALUATION_AUTHORITY:
        raise AuthorityError("unsupported prediction authority")
    if (
        freeze.get("artifactType") != "publication_pilot1_corrected_evaluation_realization_freeze"
        or freeze.get("artifactVersion") != "1.0.0"
        or freeze.get("status") != "FROZEN_CLOSED"
        or freeze.get("artifactSha256") != CORRECTED_EVALUATION_FREEZE_ARTIFACT_SHA256
    ):
        raise AuthorityError("corrected evaluation realization freeze identity is invalid")
    if authority.prediction_path is None or authority.prediction_sha256 is None:
        raise AuthorityError("corrected prediction authority is incomplete")
    expected_path = str(authority.prediction_path.relative_to(PROJECT_ROOT))
    if (
        prediction_binding.get("path") != expected_path
        or prediction_binding.get("sha256") != authority.prediction_sha256
        or prediction_binding.get("recordCount") != 11
    ):
        raise AuthorityError("corrected realization prediction binding is invalid")
    prediction_path = root / expected_path
    if _sha256(prediction_path) != authority.prediction_sha256:
        raise AuthorityError("corrected canonical prediction artifact differs from its realization freeze")
    return freeze, prediction_binding, prediction_path


def _load_inputs(
    authority: PredictionAuthority, root: Path = PROJECT_ROOT,
) -> FrozenInputs:
    """Validate one bound authority and build read-only evaluation inputs."""
    def local(path: Path) -> Path:
        return root / path.relative_to(PROJECT_ROOT)

    expected_hashes = (
        (PRIMARY_PATH, PRIMARY_SHA256), (SUPPLEMENTAL_PATH, SUPPLEMENTAL_SHA256),
        (ROUTING_PATH, ROUTING_SHA256), (SUPPLEMENTAL_PACKAGE_PATH, SUPPLEMENTAL_PACKAGE_SHA256),
    )
    for path, expected in expected_hashes:
        if _sha256(local(path)) != expected:
            raise AuthorityError(f"SHA-256 mismatch for frozen input: {path.relative_to(PROJECT_ROOT)}")

    freeze, prediction_binding, prediction_path = _prediction_binding(root, authority)

    primary = _load_json(local(PRIMARY_PATH))
    supplemental = _load_json(local(SUPPLEMENTAL_PATH))
    primary_records, primary_treatments = _human_records(primary, "primaryV014", "HUMAN_CORE_N5_PRIMARY_V1")
    supplemental_records, supplemental_treatments = _human_records(supplemental, "supplementalV015", "HUMAN_CORE_N5_SUPPLEMENTAL_V015")
    units = tuple(sorted(primary_treatments))
    if len(units) != 5 or tuple(sorted(supplemental_treatments)) != units:
        raise AuthorityError("primary and supplemental references do not contain the same exact N=5 units")

    routes_all = _jsonl(local(ROUTING_PATH))
    routes = {row["sourceUnitID"]: row for row in routes_all if row.get("sourceUnitID") in units}
    if tuple(sorted(routes)) != units:
        raise AuthorityError("unit routing does not contain each Human Core unit exactly once")
    package = _load_json(local(SUPPLEMENTAL_PACKAGE_PATH))
    overlay_rows = package.get("routingOverlay", {}).get("units", [])
    overlay = {row["sourceUnitID"]: row for row in overlay_rows}
    if tuple(sorted(overlay)) != units or len(overlay_rows) != len(overlay):
        raise AuthorityError("supplemental routing overlay is not exactly the frozen N=5")
    inventory = _inventory_targets() if root == PROJECT_ROOT else _inventory_targets_for_root(root)
    supplemental_definitions = {
        row["operational_id"]: row
        for field in ("node_targets", "relation_targets")
        for row in package.get("targets", {}).get(field, [])
    }

    opportunities: dict[str, dict[str, str]] = {}
    for unit in units:
        route = routes[unit]
        over = overlay[unit]
        if route.get("sourceArtifactID") != next(record.artifact for record in primary_records if record.unit == unit):
            raise AuthorityError(f"routing/reference artifact mismatch for {unit}")
        if route.get("sourceUnitTextHash") != over.get("sourceUnitTextHash"):
            raise AuthorityError(f"primary/supplemental unit hash mismatch for {unit}")
        routed = set(route.get("eligibleNodeOperationalTargetIDs", [])) | set(route.get("eligibleRelationOperationalTargetIDs", []))
        supplemental_routed = set(over.get("eligibleNodeOperationalTargetIDs", [])) | set(over.get("eligibleRelationOperationalTargetIDs", []))
        if set(primary_treatments[unit]) != routed or set(supplemental_treatments[unit]) != supplemental_routed:
            raise AuthorityError(f"annotation treatment map differs from unit-specific routing for {unit}")
        for target in sorted(routed | supplemental_routed):
            source_treatment = supplemental_treatments[unit].get(target, primary_treatments[unit].get(target))
            definition = inventory.get(target)
            if definition is None or definition.get("pilot_treatment") != source_treatment:
                raise AuthorityError(f"unit treatment differs from v0.1.5 inventory for {unit} {target}")
            if target in supplemental_routed:
                supplemental_definition = supplemental_definitions.get(target)
                if supplemental_definition is None or supplemental_definition.get("pilot_treatment") != source_treatment:
                    raise AuthorityError(f"supplemental package target treatment mismatch for {unit} {target}")
            if source_treatment == "extract_and_evaluate":
                opportunities.setdefault(unit, {})[target] = "relation" if target.startswith("PUB-R-") else "node"

    prediction_rows = _jsonl(prediction_path)
    if len(prediction_rows) != prediction_binding.get("recordCount"):
        raise AuthorityError("canonical C1 prediction record count differs from freeze")
    if authority is CORRECTED_EVALUATION_AUTHORITY:
        selected = [row for row in prediction_rows if row.get("executionCohort") == HUMAN_CORE_EXECUTION_COHORT]
        if any(row.get("executionCohort") == "step5_n6" for row in selected):
            raise AuthorityError("Step 5 N=6 prediction row entered Human Core selection")
    else:
        selected = [row for row in prediction_rows if row.get("acceptedSemanticProjection", {}).get("sourceUnitID") in units]
    if len(selected) != 5 or len({row["acceptedSemanticProjection"]["sourceUnitID"] for row in selected}) != 5:
        raise AuthorityError("prediction source does not provide exactly one row per Human Core unit")
    if {row["acceptedSemanticProjection"]["sourceUnitID"] for row in selected} != set(units):
        raise AuthorityError("prediction source units differ from the frozen Human Core N=5")
    realization_id = (
        "publication-pilot1-corrected-evaluation-v1.0.0"
        if authority is CORRECTED_EVALUATION_AUTHORITY
        else "publication-c1-canonical-v1.0.0"
    )
    predictions = tuple(record for row in selected for record in _prediction_records(row, realization_id))

    projection = _load_json(local(GOLD_ROOT / "publication_human_core_v0.1.5_composite_reference_projection.json"))
    if projection.get("destructiveMergeAuthorized") is not False:
        raise AuthorityError("composite reference projection does not preserve non-destructive composition")
    aliases = {row["alias"]: row["primaryLocalID"] for row in projection.get("baselineAliases", [])}
    provenance = {
        "matchingContract": str(MATCHING_CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "matchingContractSHA256": _sha256(local(MATCHING_CONTRACT_PATH)),
        "predictionAuthority": authority.name,
        "realizationFreeze": {
            "path": str(authority.freeze_path.relative_to(PROJECT_ROOT)),
            "artifactSha256": freeze.get("artifactSha256"),
        },
        "canonicalPredictions": prediction_binding,
        "primaryExport": {"path": str(PRIMARY_PATH.relative_to(PROJECT_ROOT)), "sha256": PRIMARY_SHA256},
        "supplementalExport": {"path": str(SUPPLEMENTAL_PATH.relative_to(PROJECT_ROOT)), "sha256": SUPPLEMENTAL_SHA256},
        "unitRouting": {"path": str(ROUTING_PATH.relative_to(PROJECT_ROOT)), "sha256": ROUTING_SHA256},
        "supplementalPackage": {"path": str(SUPPLEMENTAL_PACKAGE_PATH.relative_to(PROJECT_ROOT)), "sha256": SUPPLEMENTAL_PACKAGE_SHA256},
        "targetInventory": {"path": str(TARGET_INVENTORY_PATH.relative_to(PROJECT_ROOT)), "gitBlobSHA1": TARGET_INVENTORY_GIT_BLOB},
    }
    return FrozenInputs(tuple(primary_records + supplemental_records), predictions, opportunities, routes, aliases, provenance)


def load_frozen_inputs(root: Path = PROJECT_ROOT) -> FrozenInputs:
    """Load the sole prospective corrected Pilot 1 Step 7 prediction authority."""
    return _load_inputs(CORRECTED_EVALUATION_AUTHORITY, root)


def load_historical_c1_inputs(root: Path = PROJECT_ROOT) -> FrozenInputs:
    """Load preserved historical C1 inputs for legacy review-package reproducibility."""
    return _load_inputs(HISTORICAL_C1_AUTHORITY, root)


def _inventory_targets_for_root(root: Path) -> dict[str, dict[str, Any]]:
    """Load a copied frozen inventory for authority-failure tests."""
    path = root / TARGET_INVENTORY_PATH.relative_to(PROJECT_ROOT)
    if _git_blob_sha(path) != TARGET_INVENTORY_GIT_BLOB:
        raise AuthorityError("target inventory Git blob differs from frozen matching contract")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = value.get("node_targets", []) + value.get("relation_targets", [])
    return {row["operational_id"]: row for row in rows}


def _contract_assignment(
    left: list[EvaluationRecord],
    right: list[EvaluationRecord],
    edges: dict[tuple[int, int], tuple[int, float, int]],
) -> list[tuple[int, int]]:
    """Return the N=5 contract-ordered maximum one-to-one assignment.

    The integer objective encodes, in order, maximum cardinality, exact evidence,
    greater evidence overlap, and smaller boundary difference.  Its final bitset
    encodes the lexicographically smallest sorted sequence of fully-qualified
    (reference-key, prediction-key) pairs.  This is deliberately local to Step 7:
    N=2 reliability retains its frozen assignment implementation unchanged.
    """
    if not edges:
        return []
    size = max(len(left), len(right))
    maximum_matches = min(len(left), len(right))
    scale = 1_000_000
    ordered_left = sorted(range(len(left)), key=lambda index: left[index].key)
    ordered_right = sorted(range(len(right)), key=lambda index: right[index].key)
    ordered_edges = sorted(edges, key=lambda pair: (left[pair[0]].key, right[pair[1]].key))
    max_boundary = max(-int(values[2]) for values in edges.values())
    tie_base = 1 << len(ordered_edges)
    boundary_coefficient = tie_base
    overlap_coefficient = (maximum_matches * max_boundary + 1) * boundary_coefficient
    exact_coefficient = (maximum_matches * scale + 1) * overlap_coefficient
    cardinality_coefficient = (maximum_matches + 1) * exact_coefficient
    weights = [[0 for _ in range(size)] for _ in range(size)]
    row_index = {original: sorted_index for sorted_index, original in enumerate(ordered_left)}
    column_index = {original: sorted_index for sorted_index, original in enumerate(ordered_right)}
    for rank, (left_index, right_index) in enumerate(ordered_edges):
        exact, overlap, negative_boundary = edges[left_index, right_index]
        boundary = -int(negative_boundary)
        if boundary < 0:
            raise AuthorityError("assignment edge has an invalid boundary preference")
        tie_preference = 1 << (len(ordered_edges) - rank - 1)
        weights[row_index[left_index]][column_index[right_index]] = (
            cardinality_coefficient
            + int(exact) * exact_coefficient
            + round(float(overlap) * scale) * overlap_coefficient
            + (max_boundary - boundary) * boundary_coefficient
            + tie_preference
        )

    # Hungarian algorithm for a square minimum-cost matrix.  Every eligible
    # assignment has a unique final objective after the bitset tie-break.
    maximum = max(max(row) for row in weights)
    u = [0] * (size + 1)
    v = [0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)
    for row in range(1, size + 1):
        p[0] = row
        column0 = 0
        minimum = [None] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[column0] = True
            current_row = p[column0]
            delta = None
            next_column = 0
            for column in range(1, size + 1):
                if used[column]:
                    continue
                cost = maximum - weights[current_row - 1][column - 1] - u[current_row] - v[column]
                if minimum[column] is None or cost < minimum[column]:
                    minimum[column], way[column] = cost, column0
                if delta is None or minimum[column] < delta:
                    delta, next_column = minimum[column], column
            for column in range(size + 1):
                if used[column]:
                    u[p[column]] += delta
                    v[column] -= delta
                elif minimum[column] is not None:
                    minimum[column] -= delta
            column0 = next_column
            if p[column0] == 0:
                break
        while True:
            previous = way[column0]
            p[column0] = p[previous]
            column0 = previous
            if column0 == 0:
                break
    assigned = [
        (ordered_left[p[column] - 1], ordered_right[column - 1])
        for column in range(1, size + 1)
        if p[column]
        and p[column] <= len(ordered_left)
        and column <= len(ordered_right)
        and (ordered_left[p[column] - 1], ordered_right[column - 1]) in edges
    ]
    return sorted(assigned, key=lambda pair: (left[pair[0]].key, right[pair[1]].key))


def pair_nodes(references: list[EvaluationRecord], predictions: list[EvaluationRecord]) -> list[tuple[EvaluationRecord, EvaluationRecord, dict[str, Any]]]:
    """Assign eligible node pairs one-to-one within unit and operational target."""
    pairs: list[tuple[EvaluationRecord, EvaluationRecord, dict[str, Any]]] = []
    strata = sorted({(record.unit, record.target) for record in references + predictions if record.kind == "node"})
    for unit, target in strata:
        left = [record for record in references if record.kind == "node" and (record.unit, record.target) == (unit, target)]
        right = [record for record in predictions if record.kind == "node" and (record.unit, record.target) == (unit, target)]
        edges: dict[tuple[int, int], tuple[Any, ...]] = {}
        metrics: dict[tuple[int, int], dict[str, Any]] = {}
        for i, reference in enumerate(left):
            for j, prediction in enumerate(right):
                if reference.artifact != prediction.artifact or reference.value.get("ontologyClassID") != prediction.value.get("ontologyClassID"):
                    continue
                if _identity_conflicts(reference, prediction) or not _qualifying_evidence(reference, prediction):
                    continue
                measure = evidence_metrics(reference, prediction)
                edges[i, j] = (int(measure["exact"]), measure["f1"], -_boundary_difference(reference, prediction))
                metrics[i, j] = measure
        for i, j in _contract_assignment(left, right, edges):
            pairs.append((left[i], right[j], metrics[i, j]))
    return sorted(pairs, key=lambda row: (row[0].key, row[1].key))


def _node_indexes(records: Iterable[EvaluationRecord]) -> dict[tuple[str, str, str, str], EvaluationRecord]:
    """Index local nodes by side, partition/run, unit, and candidate ID."""
    return {(row.side, row.partition, row.unit, row.candidate_id): row for row in records if row.kind == "node"}


def _endpoint_identity(
    relation: EvaluationRecord,
    endpoint: dict[str, Any],
    nodes: dict[tuple[str, str, str, str], EvaluationRecord],
    routes: dict[str, dict[str, Any]],
    aliases: dict[str, str],
) -> tuple[str, str, str | None]:
    """Resolve local endpoints or return exact frozen deterministic identity."""
    reference_type, reference_id = endpoint.get("referenceType"), endpoint.get("referenceID")
    artifact = endpoint.get("artifactID")
    if not isinstance(reference_id, str):
        raise AuthorityError("relation endpoint lacks referenceID")
    if reference_type == "candidate_node":
        key = (relation.side, relation.partition, relation.unit, reference_id)
        node = nodes.get(key)
        if node is None:
            raise AuthorityError(f"unresolved local candidate endpoint: {relation.key} {reference_id}")
        return ("node", node.key, None)
    if reference_type != "deterministic_node":
        raise AuthorityError(f"unsupported endpoint reference type: {reference_type}")
    if relation.side == "reference" and reference_id in aliases:
        key = ("reference", "primaryV014", relation.unit, aliases[reference_id])
        node = nodes.get(key)
        if node is None:
            raise AuthorityError(f"unresolved frozen baseline alias: {reference_id}")
        return ("node", node.key, None)
    route = routes[relation.unit]
    paper_ids = {f"paper:{route['paperID']}", route["sourceArtifactID"]}
    if reference_id in paper_ids and artifact == route["sourceArtifactID"]:
        return ("deterministic", "current-paper", route["sourceArtifactID"])
    if not isinstance(artifact, str) or not artifact:
        raise AuthorityError("deterministic endpoint lacks exact artifact identity")
    return ("deterministic", reference_id, artifact)


def pair_relations(
    references: list[EvaluationRecord],
    predictions: list[EvaluationRecord],
    node_pairs: list[tuple[EvaluationRecord, EvaluationRecord, dict[str, Any]]],
    routes: dict[str, dict[str, Any]],
    aliases: dict[str, str],
) -> list[tuple[EvaluationRecord, EvaluationRecord, dict[str, Any]]]:
    """Assign relation pairs using exact type, direction, endpoints, and evidence."""
    nodes = _node_indexes(references + predictions)
    node_correspondence = {(left.key, right.key) for left, right, _ in node_pairs}

    def endpoint_matches(left: tuple[str, str, str | None], right: tuple[str, str, str | None]) -> bool:
        if left[0] == right[0] == "deterministic":
            return left == right
        return left[0] == right[0] == "node" and (left[1], right[1]) in node_correspondence

    pairs: list[tuple[EvaluationRecord, EvaluationRecord, dict[str, Any]]] = []
    strata = sorted({(record.unit, record.target) for record in references + predictions if record.kind == "relation"})
    for unit, target in strata:
        left = [record for record in references if record.kind == "relation" and (record.unit, record.target) == (unit, target)]
        right = [record for record in predictions if record.kind == "relation" and (record.unit, record.target) == (unit, target)]
        edges: dict[tuple[int, int], tuple[Any, ...]] = {}
        metrics: dict[tuple[int, int], dict[str, Any]] = {}
        for i, reference in enumerate(left):
            for j, prediction in enumerate(right):
                if reference.artifact != prediction.artifact or reference.value.get("ontologyRelationID") != prediction.value.get("ontologyRelationID"):
                    continue
                rs = _endpoint_identity(reference, reference.value["source"], nodes, routes, aliases)
                rt = _endpoint_identity(reference, reference.value["target"], nodes, routes, aliases)
                ps = _endpoint_identity(prediction, prediction.value["source"], nodes, routes, aliases)
                pt = _endpoint_identity(prediction, prediction.value["target"], nodes, routes, aliases)
                if not endpoint_matches(rs, ps) or not endpoint_matches(rt, pt) or not _qualifying_evidence(reference, prediction):
                    continue
                measure = evidence_metrics(reference, prediction)
                edges[i, j] = (int(measure["exact"]), measure["f1"], -_boundary_difference(reference, prediction))
                metrics[i, j] = measure
        for i, j in _contract_assignment(left, right, edges):
            pairs.append((left[i], right[j], metrics[i, j]))
    return sorted(pairs, key=lambda row: (row[0].key, row[1].key))


def _record_view(record: EvaluationRecord) -> dict[str, Any]:
    """Return an auditable, immutable record projection for result artifacts."""
    result: dict[str, Any] = {
        "key": record.key, "side": record.side, "partition": record.partition,
        "sourceUnitID": record.unit, "sourceArtifactID": record.artifact,
        "kind": record.kind, "candidateID": record.candidate_id,
        "operationalTargetID": record.target,
        "evidence": [
            {
                "sourceArtifactID": _span(span)[3], "sourceUnitID": _span(span)[2],
                "startOffsetInUnit": _span(span)[0], "endOffsetInUnit": _span(span)[1],
                "exactText": _span(span)[4],
            }
            for span in record.evidence
        ],
    }
    if record.kind == "node":
        result.update({"ontologyClassID": record.value.get("ontologyClassID"), "label": record.value.get("label")})
    else:
        result.update({
            "ontologyRelationID": record.value.get("ontologyRelationID"),
            "source": record.value.get("source"), "target": record.value.get("target"),
        })
    return result


def _metrics(reference: int, prediction: int, tp: int) -> dict[str, Any]:
    """Return support counts and micro metrics with undefined zero denominators."""
    fp, fn = prediction - tp, reference - tp
    precision = None if prediction == 0 else tp / prediction
    recall = None if reference == 0 else tp / reference
    f1 = None if precision is None or recall is None or precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"TP": tp, "FP": fp, "FN": fn, "referenceSupport": reference, "predictionSupport": prediction, "precision": precision, "recall": recall, "f1": f1}


def compute(inputs: FrozenInputs) -> dict[str, Any]:
    """Compute the single deterministic confirmatory N=5 evaluation."""
    references, predictions = list(inputs.references), list(inputs.predictions)
    node_pairs_all = pair_nodes(references, predictions)
    relation_pairs_all = pair_relations(references, predictions, node_pairs_all, inputs.routes, inputs.baseline_aliases)

    def in_scope(record: EvaluationRecord) -> bool:
        return inputs.opportunities.get(record.unit, {}).get(record.target) == record.kind

    scored_references = [row for row in references if in_scope(row)]
    scored_predictions = [row for row in predictions if in_scope(row)]
    node_pairs = [row for row in node_pairs_all if in_scope(row[0]) and in_scope(row[1])]
    relation_pairs = [row for row in relation_pairs_all if in_scope(row[0]) and in_scope(row[1])]
    paired_reference = {row[0].key for row in node_pairs + relation_pairs}
    paired_prediction = {row[1].key for row in node_pairs + relation_pairs}

    def breakdown(group_field: str) -> dict[str, Any]:
        keys = sorted({row.unit if group_field == "unit" else row.target for row in scored_references + scored_predictions})
        result: dict[str, Any] = {}
        for key in keys:
            result[key] = {}
            for kind, pairs in (("node", node_pairs), ("relation", relation_pairs)):
                select = lambda row: (row.unit if group_field == "unit" else row.target) == key and row.kind == kind
                ref = sum(select(row) for row in scored_references)
                pred = sum(select(row) for row in scored_predictions)
                matched = sum(select(left) for left, _, _ in pairs)
                if ref or pred or matched:
                    result[key][kind] = _metrics(ref, pred, matched)
        return result

    matches = {
        kind: [
            {"reference": _record_view(left), "prediction": _record_view(right), "evidence": measure}
            for left, right, measure in pairs
        ]
        for kind, pairs in (("nodes", node_pairs), ("relations", relation_pairs))
    }
    unmatched_reference = [_record_view(row) for row in sorted(scored_references, key=lambda item: item.key) if row.key not in paired_reference]
    unmatched_prediction = [_record_view(row) for row in sorted(scored_predictions, key=lambda item: item.key) if row.key not in paired_prediction]
    node_reference = sum(row.kind == "node" for row in scored_references)
    node_prediction = sum(row.kind == "node" for row in scored_predictions)
    relation_reference = sum(row.kind == "relation" for row in scored_references)
    relation_prediction = sum(row.kind == "relation" for row in scored_predictions)
    opportunities = [
        {"sourceUnitID": unit, "operationalTargetID": target, "kind": kind, "treatment": "extract_and_evaluate"}
        for unit in sorted(inputs.opportunities)
        for target, kind in sorted(inputs.opportunities[unit].items())
    ]
    authority_name = inputs.provenance.get("predictionAuthority")
    if authority_name == CORRECTED_EVALUATION_AUTHORITY.name:
        artifact_type = CORRECTED_EVALUATION_AUTHORITY.artifact_type
        artifact_version = CORRECTED_EVALUATION_AUTHORITY.artifact_version
        execution = CORRECTED_EVALUATION_AUTHORITY.execution
    else:
        artifact_type = "publication_human_core_n5_c1_confirmatory_evaluation_pre_freeze"
        artifact_version = "0.1.1"
        execution = "one_time_step_7b_confirmatory_evaluation"
    return {
        "artifactType": artifact_type,
        "artifactVersion": artifact_version,
        "status": "PRE_FREEZE",
        "execution": execution,
        "scope": "exact frozen N=5 routed extract_and_evaluate opportunities only; extract_and_monitor excluded",
        "explicitExclusions": ["Annotator B / N=2 reliability", "extract_and_monitor", "provider/model calls", "semantic repair, inference, normalization, adjudication, or deduplication"],
        "frozenInputs": inputs.provenance,
        "scoringOpportunities": opportunities,
        "aggregate": {
            "nodes": _metrics(node_reference, node_prediction, len(node_pairs)),
            "relations": _metrics(relation_reference, relation_prediction, len(relation_pairs)),
        },
        "byUnit": breakdown("unit"),
        "byTarget": breakdown("target"),
        "matchedRecords": matches,
        "unmatchedReferenceRecords": unmatched_reference,
        "unmatchedPredictionRecords": unmatched_prediction,
        "distributedEvidenceDiagnostics": {
            "rule": "ordinary qualifying-evidence rule; no joint-span obligation inferred",
            "referenceRecordKeys": sorted(row.key for row in scored_references if len(row.evidence) > 1),
            "predictionRecordKeys": sorted(row.key for row in scored_predictions if len(row.evidence) > 1),
        },
        "referenceComposition": {
            "mode": "read_only_non_destructive_partition_composition",
            "partitions": ["primaryV014", "supplementalV015"],
            "semanticMerge": False, "deduplication": False, "normalization": False,
            "relabeling": False, "repair": False, "inference": False, "adjudication": False,
        },
        "providerModelCalls": 0,
        "step7CExecuted": False,
        "freezeOrClosureRecordCreated": False,
    }


def render_report(result: dict[str, Any]) -> str:
    """Render a concise human-readable PRE-FREEZE report."""
    def value(number: float | None) -> str:
        return "undefined" if number is None else f"{number:.6f}"

    nodes, relations = result["aggregate"]["nodes"], result["aggregate"]["relations"]
    corrected = result.get("artifactType") == CORRECTED_EVALUATION_AUTHORITY.artifact_type
    title = CORRECTED_EVALUATION_AUTHORITY.report_title if corrected else HISTORICAL_C1_AUTHORITY.report_title
    intro = CORRECTED_EVALUATION_AUTHORITY.report_intro if corrected else HISTORICAL_C1_AUTHORITY.report_intro
    lines = [
        f"# {title}", "", intro, "",
        "## Aggregate confirmatory metrics", "",
        f"- Nodes: TP={nodes['TP']}, FP={nodes['FP']}, FN={nodes['FN']}, reference support={nodes['referenceSupport']}, prediction support={nodes['predictionSupport']}, micro P/R/F1={value(nodes['precision'])}/{value(nodes['recall'])}/{value(nodes['f1'])}.",
        f"- Relations: TP={relations['TP']}, FP={relations['FP']}, FN={relations['FN']}, reference support={relations['referenceSupport']}, prediction support={relations['predictionSupport']}, micro P/R/F1={value(relations['precision'])}/{value(relations['recall'])}/{value(relations['f1'])}.", "",
        "Only frozen unit-specific `extract_and_evaluate` opportunities are scored. `extract_and_monitor` is excluded. The JSON companion contains every scoring opportunity, matched pair, unmatched reference, unmatched prediction, and per-unit/per-target breakdown.", "",
        "## Per-unit descriptive counts", "",
    ]
    for unit, kinds in result["byUnit"].items():
        parts = [f"{kind}: TP={row['TP']} FP={row['FP']} FN={row['FN']} ref={row['referenceSupport']} pred={row['predictionSupport']}" for kind, row in kinds.items()]
        lines.append(f"- `{unit}` — " + "; ".join(parts) + ".")
    lines.extend(("", "Status remains **PRE-FREEZE**. Step 7C was not executed and Step 7 is not marked FROZEN/CLOSED.", ""))
    return "\n".join(lines)


def main() -> None:
    """Materialize the corrected-realization PRE-FREEZE Step 7B artifacts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise AuthorityError("corrected Step 7B output already exists; refusing to materialize it again")
    if _sha256(V010_OUTPUT) != V010_OUTPUT_SHA256 or _sha256(V010_REPORT) != V010_REPORT_SHA256:
        raise AuthorityError("historical v0.1.0 PRE-FREEZE artifacts differ from their preserved byte authorities")
    result = compute(load_frozen_inputs())
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(render_report(result), encoding="utf-8")


if __name__ == "__main__":
    main()
