"""Replay preserved schema-0.1.2 outputs under the prospective schema-0.1.3 authority."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from src.extraction.llm.publications.authority_bundle import V015_SCHEMA013
from src.extraction.llm.publications.request_builder import canonical_json, canonical_json_file, load_json_object, sha256_bytes
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    _downstream,
    load_c0_bindings,
    prepare_unit,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PRESERVED_SCHEMA012_ROOT = (
    PROJECT_ROOT / "data/curation/papers/m2/"
    "future_full_semantic_devset0_v015_schema012_smoke1"
)
REPORT_PATH = (
    PROJECT_ROOT / "data/curation/papers/m2/"
    "publication_v015_schema013_schema012_artifact_compatibility_audit_v1.0.json"
)


def _paths(root: Path, development_id: str) -> dict[str, Path]:
    """Return the preserved, authority-bearing artifacts needed for one replay."""

    prefix = f"publication_full_semantic_{development_id.lower().replace('-', '')}"
    unit = root / development_id
    return {
        "providerInput": unit / f"{prefix}_exact_provider_input.txt",
        "modelSchema": unit / f"{prefix}_request_specialized_schema.json",
        "rawOutput": unit / f"{prefix}_exact_structured_model_output.json",
        "validation": unit / f"{prefix}_validation_results.json",
        "usable": unit / f"{prefix}_usable_pipeline_output.json",
    }


def _status_counts(validation: Mapping[str, Any]) -> dict[str, int]:
    """Return stable candidate validation-status totals."""

    return dict(sorted(Counter(
        str(row.get("candidateValidationStatus"))
        for row in validation.get("recordResults", [])
        if row.get("recordType") in {"candidate_node", "candidate_edge"}
    ).items()))


def _usable_projection(usable: Mapping[str, Any]) -> dict[str, Any]:
    """Return the candidate-only projection whose identity must survive replay."""

    return {
        "candidateNodes": usable.get("candidateNodes", []),
        "candidateEdges": usable.get("candidateEdges", []),
    }


def _finding_code_counts(findings: list[Mapping[str, Any]]) -> dict[str, int]:
    """Count finding codes while retaining validation-section provenance."""

    return dict(sorted(Counter(str(finding.get("code")) for finding in findings).items()))


def _nested_findings(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Flatten evidence or record findings without losing their report section."""

    return [
        finding
        for row in rows
        for finding in row.get("findings", [])
    ]


def audit_unit(development_id: str, *, preserved_root: Path = PRESERVED_SCHEMA012_ROOT) -> dict[str, Any]:
    """Replay one preserved output against V015_SCHEMA013 without provider dispatch."""

    binding = next(row for row in load_c0_bindings() if row["developmentID"] == development_id)
    preserved = _paths(preserved_root, development_id)
    with TemporaryDirectory() as temporary:
        state = prepare_unit(
            binding,
            output_dir=Path(temporary),
            full_semantic=True,
            authority_bundle=V015_SCHEMA013,
        )
        parser, _parsed, validation, usable = _downstream(
            preserved["rawOutput"].read_bytes(),
            state["request"],
            endpoint_binding=True,
            evidence_binding=True,
        )
        successor_provider_input = state["providerInput"]
        successor_schema = state["paths"]["modelSchema"].read_bytes()

    old_validation = load_json_object(preserved["validation"])
    old_usable = load_json_object(preserved["usable"])
    preserved_projection = _usable_projection(old_usable)
    successor_projection = _usable_projection(usable)
    global_findings = list(validation.get("globalFindings", []))
    evidence_findings = _nested_findings(list(validation.get("evidenceResults", [])))
    record_findings = _nested_findings(list(validation.get("recordResults", [])))
    finding_code_counts = {
        "globalFindings": _finding_code_counts(global_findings),
        "evidenceResults": _finding_code_counts(evidence_findings),
        "recordResults": _finding_code_counts(record_findings),
    }
    endpoint_cascades = sum(
        1
        for finding in record_findings
        if finding.get("code") == "ENDPOINT_LIFECYCLE_INVALID"
    )
    row = {
        "developmentID": development_id,
        "networkCalls": state["preflight"]["networkCalls"],
        "transport": {
            "providerInput": {
                "preservedSha256": sha256_bytes(preserved["providerInput"].read_bytes()),
                "successorSha256": sha256_bytes(successor_provider_input),
                "byteIdentical": preserved["providerInput"].read_bytes() == successor_provider_input,
            },
            "requestSpecializedModelSchema": {
                "preservedSha256": sha256_bytes(preserved["modelSchema"].read_bytes()),
                "successorSha256": sha256_bytes(successor_schema),
                "byteIdentical": preserved["modelSchema"].read_bytes() == successor_schema,
            },
        },
        "preservedRawOutputSha256": sha256_bytes(preserved["rawOutput"].read_bytes()),
        "downstream": {
            "parserStatus": parser.get("parseStatus"),
            "endpointBindingStatus": parser.get("endpointBinding", {}).get("bindingStatus"),
            "evidenceBindingStatus": parser.get("evidenceBinding", {}).get("bindingStatus"),
            "preservedCandidateStatusCounts": _status_counts(old_validation),
            "successorCandidateStatusCounts": _status_counts(validation),
            "candidateStatusCountsRetained": _status_counts(old_validation) == _status_counts(validation),
            "preservedUsableProjectionSha256": sha256_bytes(canonical_json(preserved_projection)),
            "successorUsableProjectionSha256": sha256_bytes(canonical_json(successor_projection)),
            "usableProjectionRetained": preserved_projection == successor_projection,
            "successorFindingCodeCounts": finding_code_counts,
            "successorEndpointLifecycleCascadeFindingCount": endpoint_cascades,
        },
    }
    if development_id == "DEV-08":
        root_codes = {"SCHEMA_VALIDATION_FAILED", "ENDPOINT_LIFECYCLE_INVALID"}
        remaining_findings = [
            finding
            for finding in global_findings + evidence_findings + record_findings
            if finding.get("code") not in root_codes
        ]
        row["dev08Closure"] = {
            "cP34GenericEnumFailuresClosed": finding_code_counts["globalFindings"].get("SCHEMA_VALIDATION_FAILED", 0) == 0,
            "endpointLifecycleCascadeClosed": endpoint_cascades == 0,
            "independentRemainingWarningCodeCounts": _finding_code_counts([
                finding for finding in remaining_findings if finding.get("severity") == "warning"
            ]),
            "independentRemainingNonWarningFindingCodeCounts": _finding_code_counts([
                finding for finding in remaining_findings if finding.get("severity") != "warning"
            ]),
            "usableCandidateCount": len(successor_projection["candidateNodes"]) + len(successor_projection["candidateEdges"]),
        }
        downstream_compatible = (
            row["downstream"]["parserStatus"] == "parsed"
            and row["downstream"]["endpointBindingStatus"] == "bound"
            and row["downstream"]["evidenceBindingStatus"] == "bound"
            and row["dev08Closure"]["cP34GenericEnumFailuresClosed"]
            and row["dev08Closure"]["endpointLifecycleCascadeClosed"]
            and not row["dev08Closure"]["independentRemainingNonWarningFindingCodeCounts"]
        )
    else:
        downstream_compatible = (
            row["downstream"]["parserStatus"] == "parsed"
            and row["downstream"]["endpointBindingStatus"] == "bound"
            and row["downstream"]["evidenceBindingStatus"] == "bound"
            and row["downstream"]["candidateStatusCountsRetained"]
            and row["downstream"]["usableProjectionRetained"]
        )
    row["compatible"] = (
        row["networkCalls"] == 0
        and row["transport"]["providerInput"]["byteIdentical"]
        and row["transport"]["requestSpecializedModelSchema"]["byteIdentical"]
        and downstream_compatible
    )
    return row


def _report_from_units(units: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the canonical report envelope to already replayed unit rows."""

    report: dict[str, Any] = {
        "recordSchemaVersion": "1.0",
        "artifactRole": "preserved_schema012_output_schema013_compatibility_audit",
        "sourceAuthorityBundleID": "publication-semantic-v0.1.5-schema-v0.1.2",
        "successorAuthorityBundleID": V015_SCHEMA013.identifier,
        "providerCalls": 0,
        "modelCallMade": False,
        "units": units,
        "overallStatus": "PASS" if all(row["compatible"] for row in units) else "FAIL",
    }
    report["reportSha256"] = sha256_bytes(canonical_json(report))
    return report


def build_schema013_compatibility_report() -> dict[str, Any]:
    """Build the deterministic no-call schema012-to-schema013 compatibility record."""

    development_ids = [f"DEV-{index:02d}" for index in range(1, 9)]
    # Each replay is source-unit isolated. Ordered map preserves canonical report order
    # while keeping the offline audit within the local command-time budget.
    with ThreadPoolExecutor(max_workers=4) as executor:
        return _report_from_units(list(executor.map(audit_unit, development_ids)))


def write_schema013_compatibility_report(
    path: Path = REPORT_PATH, *, units: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Write the canonical compatibility audit without altering preserved artifacts."""

    report = build_schema013_compatibility_report() if units is None else _report_from_units(units)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(report))
    return report
