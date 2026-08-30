"""Build M2-C2A trusted evidence-metadata diagnostics without provider calls.

This development-only runner derives prospective schemas that bind only
``evidenceSpan.sectionTitle`` to trusted request metadata.  It also evaluates a
separately labelled counterfactual copy of each immutable C1B model output through
the unchanged M1 parser and validator.  Counterfactual artifacts are not extraction
outputs and are never materialized as usable pipeline artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import jsonschema

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.model_authorable_schema import (  # noqa: E402
    audit_openai_structured_outputs_schema,
    derive_model_authorable_schema,
)
from src.extraction.llm.publications.request_builder import (  # noqa: E402
    CANDIDATE_SCHEMA_PATH,
    TARGET_INVENTORY_PATH,
    canonical_json,
    canonical_json_file,
    load_json_object,
    sha256_bytes,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (  # noqa: E402
    DEV_IDS,
    PROMPT_PATH,
    _validation_finding_code_counts,
    build_c1b_request,
    load_c0_bindings,
)
from src.extraction.llm.publications.run_publication_multitarget_node_development import (  # noqa: E402
    _exposed_targets,
)
from src.extraction.llm.publications.run_publication_structured_development_smoke import (  # noqa: E402
    _downstream,
)
from src.extraction.llm.publications.trusted_evidence_metadata_schema import (  # noqa: E402
    HISTORICAL_SECTION_TITLE_SCHEMA,
    SECTION_TITLE_AUTHORITY_POINTER,
    SECTION_TITLE_SCHEMA_POINTER,
    TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION,
    authoritative_section_title,
    derive_trusted_evidence_metadata_schema,
    trusted_evidence_metadata_schema_record,
)


C1B_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/c1b"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/c2a"
COUNTERFACTUAL_LABELS = {
    "artifactRole": "COUNTERFACTUAL_DIAGNOSTIC_ONLY",
    "authenticModelOutput": False,
    "extractionOutput": False,
    "gold": False,
    "formalEvaluation": False,
    "authenticC1BModelOutputChanged": False,
}


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one deterministic JSON artifact with a trailing line feed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _c1b_paths(development_id: str) -> dict[str, Path]:
    """Return immutable accepted C1B paths for one unit."""

    prefix = f"publication_m2c1b_{development_id.lower().replace('-', '')}"
    directory = C1B_OUTPUT_DIR / development_id
    return {
        "request": directory / f"{prefix}_live_request.json",
        "raw": directory / f"{prefix}_exact_structured_model_output.json",
        "validation": directory / f"{prefix}_validation_results.json",
        "usable": directory / f"{prefix}_usable_pipeline_output.json",
    }


def _counterfactual_paths(output_dir: Path, development_id: str) -> dict[str, Path]:
    """Return isolated diagnostic-only paths for one counterfactual unit."""

    prefix = f"publication_m2c2a_{development_id.lower().replace('-', '')}"
    directory = output_dir / "counterfactual" / development_id
    return {
        "payload": directory / f"{prefix}_section_title_only_payload.json",
        "parser": directory / f"{prefix}_section_title_only_parser_result.json",
        "validation": directory / f"{prefix}_section_title_only_validation_results.json",
        "summary": directory / f"{prefix}_section_title_only_summary.json",
    }


def _tree_snapshot(directory: Path) -> dict[str, Any]:
    """Return a deterministic byte-hash inventory for an immutable directory."""

    rows = [
        {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "sha256": sha256_bytes(path.read_bytes()),
        }
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    ]
    return {
        "fileCount": len(rows),
        "treeInventorySha256": sha256_bytes(canonical_json(rows)),
        "files": rows,
    }


def build_evidence_field_responsibility_audit() -> dict[str, Any]:
    """Classify every frozen evidence property without expanding C2A scope."""

    frozen = load_json_object(CANDIDATE_SCHEMA_PATH)["$defs"]["evidenceSpan"]
    provider = derive_model_authorable_schema()["$defs"]["evidenceSpan"]
    authority: dict[str, tuple[str | None, bool, str]] = {
        "evidenceSpanID": (None, False, "MODEL_LOCAL_IDENTIFIER"),
        "sourceArtifactID": (
            "/sourceUnit/canonicalArtifactID and /sourceArtifactID",
            True,
            "TRUSTED_REQUEST_METADATA",
        ),
        "sourceUnitID": (
            "/sourceUnit/sourceUnitID within the bounded request",
            True,
            "TRUSTED_REQUEST_METADATA",
        ),
        "sourceUnitTextHash": (
            "/sourceUnit/textHash",
            True,
            "TRUSTED_REQUEST_METADATA",
        ),
        "sectionID": (
            "/sourceUnit/sectionID",
            True,
            "TRUSTED_REQUEST_METADATA",
        ),
        "sectionTitle": (
            SECTION_TITLE_AUTHORITY_POINTER,
            True,
            "TRUSTED_REQUEST_METADATA",
        ),
        "evidenceText": (None, False, "MODEL_AUTHORED_SEMANTIC_DECISION"),
        "startOffsetInUnit": (
            "selected evidence boundary in sourceUnit.text",
            False,
            "MODEL_AUTHORED_COORDINATE_DECISION",
        ),
        "endOffsetInUnit": (
            "selected evidence boundary in sourceUnit.text",
            False,
            "MODEL_AUTHORED_COORDINATE_DECISION",
        ),
        "startOffsetInDocument": (
            "sourceUnit.startOffsetInDocument plus selected unit boundary",
            False,
            "MODEL_AUTHORED_COORDINATE_DECISION",
        ),
        "endOffsetInDocument": (
            "sourceUnit.startOffsetInDocument plus selected unit boundary",
            False,
            "MODEL_AUTHORED_COORDINATE_DECISION",
        ),
        "evidenceHash": (
            "pipeline-computed SHA-256 of the selected evidenceText",
            False,
            "OTHER_CONTRACT_FIELD",
        ),
    }
    rows: list[dict[str, Any]] = []
    for name in frozen["required"]:
        source, single, responsibility = authority[name]
        rows.append(
            {
                "fieldName": name,
                "frozenSchemaRequired": True,
                "frozenSchemaConstraint": frozen["properties"][name],
                "authoritativeSource": source,
                "deterministicallySingleValuedBeforeGeneration": single,
                "currentProviderFacingConstraint": provider["properties"][name],
                "recommendedResponsibility": responsibility,
                "implementedProspectiveChangeInC2A": name == "sectionTitle",
                "otherPotentialBindingDeferredForResearcherReview": (
                    single and name != "sectionTitle"
                ),
            }
        )
    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "evidence_field_responsibility_audit",
        "developmentOnly": True,
        "providerCalls": 0,
        "candidateSchemaSha256": sha256_bytes(CANDIDATE_SCHEMA_PATH.read_bytes()),
        "immediateApprovedImplementationField": "evidenceSpan.sectionTitle",
        "additionalFieldsBoundProspectively": [],
        "fields": rows,
    }


def _schema_metrics(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the established provider audit into stable unit metrics."""

    explicit = audit["explicitTypeAudit"]
    refs = audit["refAudit"]
    metrics = audit["metrics"]
    return {
        "objectPropertyCount": metrics["totalObjectPropertyCount"],
        "enumValueCount": metrics["totalEnumValueCount"],
        "maximumDepth": metrics["maxNestingDepth"],
        "stringBudget": metrics["aggregateSchemaStringBudget"],
        "refSiblingCount": refs["refSiblingNodes"],
        "unresolvedReferenceCount": refs["unresolvedRefTargets"],
        "missingExplicitTypeCount": (
            explicit["constSchemasLackingExplicitType"]
            + explicit["enumSchemasLackingExplicitType"]
            + explicit["directlyConstrainedSchemasLackingCompatibleType"]
        ),
        "invalidAnyOfBranchCount": explicit["invalidAnyOfBranchCount"],
    }


def build_prospective_schema_audit(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive, persist, and audit all ten prospective no-network schemas."""

    unit_rows: list[dict[str, Any]] = []
    specialization_rows: list[dict[str, Any]] = []
    for binding in load_c0_bindings():
        development_id = str(binding["developmentID"])
        request = build_c1b_request(binding)
        schema = derive_trusted_evidence_metadata_schema(request)
        record = trusted_evidence_metadata_schema_record(request)
        audit = audit_openai_structured_outputs_schema(schema)
        title = authoritative_section_title(request)
        constraint = schema["$defs"]["evidenceSpan"]["properties"]["sectionTitle"]
        title_validator = jsonschema.Draft202012Validator(constraint)
        nodes = _exposed_targets(schema, "operationalTargetID")
        relations = _exposed_targets(schema, "operationalRelationID")
        schema_path = (
            output_dir
            / "prospective_schemas"
            / development_id
            / f"publication_m2c2a_{development_id.lower().replace('-', '')}_trusted_section_title_schema.json"
        )
        _write_canonical(schema_path, schema)
        unit_rows.append(
            {
                "developmentID": development_id,
                "sourceUnitID": request["sourceUnit"]["sourceUnitID"],
                "authoritativeSectionTitleRaw": title,
                "sectionTitleConstraint": constraint,
                "authoritativeTitleAccepted": title_validator.is_valid(title),
                "nonAuthoritativeSentinelRejected": not title_validator.is_valid(
                    "__not_the_authoritative_title__"
                ),
                "schemaSha256": sha256_bytes(canonical_json(schema)),
                "schemaCanonicalBytes": len(canonical_json(schema)),
                "exposedNodeTargetCount": len(nodes),
                "exposedRelationTargetCount": len(relations),
                "exposedNodeOperationalTargetIDs": nodes,
                "providerCompatibility": "PASS" if audit["compatible"] else "FAIL",
                **_schema_metrics(audit),
            }
        )
        specialization_rows.append(
            {
                "developmentID": development_id,
                "sourceUnitID": request["sourceUnit"]["sourceUnitID"],
                "authoritativeSectionTitleRaw": title,
                "prospectiveSchemaSha256": record["prospectiveSchemaSha256"],
                "specializationRecordSha256": record["recordSha256"],
            }
        )

    by_id = {row["developmentID"]: row for row in unit_rows}
    dev02_constraint = by_id["DEV-02"]["sectionTitleConstraint"]
    dev06_constraint = by_id["DEV-06"]["sectionTitleConstraint"]
    dev02_validator = jsonschema.Draft202012Validator(dev02_constraint)
    dev06_validator = jsonschema.Draft202012Validator(dev06_constraint)
    null_request = deepcopy(build_c1b_request(load_c0_bindings()[0]))
    null_request["sourceUnit"]["sectionTitleRaw"] = None
    null_schema = derive_trusted_evidence_metadata_schema(null_request)
    null_constraint = null_schema["$defs"]["evidenceSpan"]["properties"]["sectionTitle"]
    schema_audit: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "prospective_devset0_trusted_section_title_schema_audit",
        "developmentOnly": True,
        "providerCalls": 0,
        "prospectiveSchemaVersion": TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION,
        "allUnitsCompatible": all(
            row["providerCompatibility"] == "PASS" for row in unit_rows
        ),
        "allUnitsExposeFortyNodesAndZeroRelations": all(
            row["exposedNodeTargetCount"] == 40
            and row["exposedRelationTargetCount"] == 0
            for row in unit_rows
        ),
        "allUnitsBindExactAuthoritativeTitle": all(
            row["authoritativeTitleAccepted"]
            and row["nonAuthoritativeSentinelRejected"]
            for row in unit_rows
        ),
        "dev02ExplicitChecks": {
            "acceptedExact": dev02_validator.is_valid(
                '<span id="page-15-0"></span>**2.7. Evaluation**'
            ),
            "rejectedValues": {
                "null": not dev02_validator.is_valid(None),
                "plain": not dev02_validator.is_valid("2.7. Evaluation"),
                "markdownOnly": not dev02_validator.is_valid(
                    "**2.7. Evaluation**"
                ),
                "trimmed": not dev02_validator.is_valid(
                    '<span id="page-15-0"></span>**2.7. Evaluation** '
                ),
            },
        },
        "dev06ExplicitChecks": {
            "acceptedExact": dev06_validator.is_valid("**3. Results**"),
            "rejectedValues": {
                "plain": not dev06_validator.is_valid("3. Results"),
                "null": not dev06_validator.is_valid(None),
                "trimmed": not dev06_validator.is_valid(" **3. Results**"),
            },
        },
        "nullSyntheticContractFixture": {
            "usedBecauseCurrentDevsetHasNoNullSectionTitleRaw": all(
                row["authoritativeSectionTitleRaw"] is not None for row in unit_rows
            ),
            "constraint": null_constraint,
            "nullAccepted": jsonschema.Draft202012Validator(
                null_constraint
            ).is_valid(None),
            "stringRejected": not jsonschema.Draft202012Validator(
                null_constraint
            ).is_valid(""),
        },
        "units": unit_rows,
    }
    specialization_record: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "trusted_section_title_specialization_record",
        "developmentOnly": True,
        "providerCalls": 0,
        "historicalVersion": "publication-request-specialized-0.1.0",
        "prospectiveVersion": TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION,
        "historicalBehavior": {
            "field": "evidenceSpan.sectionTitle",
            "constraint": HISTORICAL_SECTION_TITLE_SCHEMA,
            "responsibility": "model_authorable_within_stringOrNull",
        },
        "prospectiveBehavior": {
            "field": "evidenceSpan.sectionTitle",
            "authorityPointer": SECTION_TITLE_AUTHORITY_POINTER,
            "schemaPointer": SECTION_TITLE_SCHEMA_POINTER,
            "constraint": "exact typed const copied without normalization",
            "normalizationApplied": False,
        },
        "frozenCandidateSchemaModified": False,
        "historicalSchemasModified": False,
        "additionalEvidenceFieldsBound": [],
        "units": specialization_rows,
    }
    specialization_record["recordSha256"] = sha256_bytes(
        canonical_json(specialization_record)
    )
    return schema_audit, specialization_record


def _validation_summary(
    validation: Mapping[str, Any], usable: Mapping[str, Any]
) -> dict[str, Any]:
    """Summarize one authentic or counterfactual validator result."""

    status_counts: Counter[str] = Counter()
    for row in validation.get("recordResults", []):
        if row.get("recordType") in {"candidate_node", "candidate_edge"}:
            status_counts[str(row.get("candidateValidationStatus"))] += 1
    evidence = list(validation.get("evidenceResults", []))
    return {
        "validEvidenceSpanCount": sum(row.get("valid") is True for row in evidence),
        "evidenceSpanCount": len(evidence),
        "candidateStatusCounts": dict(sorted(status_counts.items())),
        "validatedCandidateCount": status_counts["validated"],
        "rejectedCandidateCount": status_counts["rejected"],
        "usableCandidateCount": len(usable.get("candidateNodes", []))
        + len(usable.get("candidateEdges", [])),
        "validationFindingCodeCounts": dict(
            sorted(_validation_finding_code_counts(validation).items())
        ),
        "validationFindingCodes": sorted(
            _validation_finding_code_counts(validation)
        ),
        "validationEnvelopeStatus": validation.get("envelopeStatus"),
    }


def _section_title_only_copy(
    payload: Mapping[str, Any], authoritative_title: str | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Copy one payload and change only every evidence span's section title."""

    diagnostic = deepcopy(dict(payload))
    changes: list[dict[str, Any]] = []
    evidence = diagnostic.get("evidenceSpans")
    if not isinstance(evidence, list):
        raise ValueError("authentic C1B evidenceSpans is not an array")
    for index, span in enumerate(evidence):
        if not isinstance(span, dict) or "sectionTitle" not in span:
            raise ValueError("authentic C1B evidence span lacks sectionTitle")
        old = span["sectionTitle"]
        span["sectionTitle"] = authoritative_title
        changes.append(
            {
                "jsonPointer": f"/evidenceSpans/{index}/sectionTitle",
                "evidenceSpanID": span.get("evidenceSpanID"),
                "authenticValue": old,
                "counterfactualValue": authoritative_title,
            }
        )
    verification = deepcopy(diagnostic)
    for index, original in enumerate(payload.get("evidenceSpans", [])):
        verification["evidenceSpans"][index]["sectionTitle"] = original["sectionTitle"]
    if canonical_json(verification) != canonical_json(payload):
        raise ValueError("counterfactual changed a field other than sectionTitle")
    return diagnostic, changes


def build_counterfactual_diagnostics(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Evaluate section-title-only copies while preserving authentic C1B bytes."""

    before = _tree_snapshot(C1B_OUTPUT_DIR)
    unit_rows: list[dict[str, Any]] = []
    authentic_totals: Counter[str] = Counter()
    counterfactual_totals: Counter[str] = Counter()
    authentic_codes: Counter[str] = Counter()
    counterfactual_codes: Counter[str] = Counter()
    for development_id in DEV_IDS:
        paths = _c1b_paths(development_id)
        request = load_json_object(paths["request"])
        raw = paths["raw"].read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{development_id} authentic output is not an object")
        authentic_validation = load_json_object(paths["validation"])
        authentic_usable = load_json_object(paths["usable"])
        diagnostic, changes = _section_title_only_copy(
            payload, authoritative_section_title(request)
        )
        diagnostic_raw = canonical_json(diagnostic)
        parser, _, validation, usable = _downstream(diagnostic_raw, request)
        authentic_summary = _validation_summary(
            authentic_validation, authentic_usable
        )
        counterfactual_summary = _validation_summary(validation, usable)
        for key in (
            "validEvidenceSpanCount",
            "evidenceSpanCount",
            "validatedCandidateCount",
            "rejectedCandidateCount",
            "usableCandidateCount",
        ):
            authentic_totals[key] += authentic_summary[key]
            counterfactual_totals[key] += counterfactual_summary[key]
        authentic_codes.update(authentic_summary["validationFindingCodeCounts"])
        counterfactual_codes.update(
            counterfactual_summary["validationFindingCodeCounts"]
        )
        unit = {
            "developmentID": development_id,
            "sourceUnitID": request["sourceUnit"]["sourceUnitID"],
            "authoritativeSectionTitleRaw": request["sourceUnit"][
                "sectionTitleRaw"
            ],
            "authenticRawModelOutputSha256": sha256_bytes(raw),
            "authentic": authentic_summary,
            "sectionTitleOnlyCounterfactual": counterfactual_summary,
            "changedFieldCount": len(changes),
            "changedJsonPointers": [row["jsonPointer"] for row in changes],
            "onlySectionTitleChanged": True,
            "postGenerationRepairAppliedToAuthenticOutput": False,
        }
        unit_rows.append(unit)
        artifact_paths = _counterfactual_paths(output_dir, development_id)
        _write_canonical(
            artifact_paths["payload"],
            {
                **COUNTERFACTUAL_LABELS,
                "developmentID": development_id,
                "authenticRawModelOutputSha256": sha256_bytes(raw),
                "transformation": {
                    "changedField": "evidenceSpan.sectionTitle",
                    "authoritativeSource": SECTION_TITLE_AUTHORITY_POINTER,
                    "allOtherFieldsChanged": False,
                    "changes": changes,
                },
                "diagnosticPayload": diagnostic,
            },
        )
        _write_canonical(
            artifact_paths["parser"],
            {
                **COUNTERFACTUAL_LABELS,
                "developmentID": development_id,
                "unchangedParserUsed": True,
                "parserResult": parser,
            },
        )
        _write_canonical(
            artifact_paths["validation"],
            {
                **COUNTERFACTUAL_LABELS,
                "developmentID": development_id,
                "unchangedValidatorUsed": True,
                "validationResults": validation,
            },
        )
        _write_canonical(
            artifact_paths["summary"],
            {**COUNTERFACTUAL_LABELS, **unit},
        )

    after = _tree_snapshot(C1B_OUTPUT_DIR)
    if canonical_json(before) != canonical_json(after):
        raise ValueError("immutable C1B artifacts changed during C2A diagnostics")
    disappeared = {
        code: count - counterfactual_codes.get(code, 0)
        for code, count in sorted(authentic_codes.items())
        if count > counterfactual_codes.get(code, 0)
    }
    appeared = {
        code: count - authentic_codes.get(code, 0)
        for code, count in sorted(counterfactual_codes.items())
        if count > authentic_codes.get(code, 0)
    }
    by_id = {row["developmentID"]: row for row in unit_rows}
    result: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        **COUNTERFACTUAL_LABELS,
        "providerCalls": 0,
        "method": {
            "changedFieldOnly": "evidenceSpan.sectionTitle",
            "authoritativeSource": SECTION_TITLE_AUTHORITY_POINTER,
            "parser": "unchanged M1 strict parser",
            "validator": "unchanged M1 V1-V12 validator",
            "usableOutputPersisted": False,
        },
        "authenticC1BTreeBefore": {
            key: value for key, value in before.items() if key != "files"
        },
        "authenticC1BTreeAfter": {
            key: value for key, value in after.items() if key != "files"
        },
        "authenticC1BTreeByteIdentical": canonical_json(before)
        == canonical_json(after),
        "units": unit_rows,
        "aggregate": {
            "authentic": dict(sorted(authentic_totals.items())),
            "sectionTitleOnlyCounterfactual": dict(
                sorted(counterfactual_totals.items())
            ),
            "authenticValidationFindingCodeCounts": dict(
                sorted(authentic_codes.items())
            ),
            "counterfactualValidationFindingCodeCounts": dict(
                sorted(counterfactual_codes.items())
            ),
            "findingOccurrencesDisappeared": disappeared,
            "findingOccurrencesAppeared": appeared,
            "invalidEvidenceSpansEliminated": (
                counterfactual_totals["validEvidenceSpanCount"]
                - authentic_totals["validEvidenceSpanCount"]
            ),
            "additionalHypotheticalUsableCandidates": (
                counterfactual_totals["usableCandidateCount"]
                - authentic_totals["usableCandidateCount"]
            ),
        },
        "dev05ResidualGenuineOffsetFailure": {
            "authentic": by_id["DEV-05"]["authentic"],
            "counterfactual": by_id["DEV-05"][
                "sectionTitleOnlyCounterfactual"
            ],
            "knownModelAuthoredUnitOffsets": [545, 708],
            "knownActualLiteralUnitOffsets": [541, 708],
            "offsetChangedByCounterfactual": False,
        },
        "dev06CascadeDiagnosis": {
            "primaryFailure": "SECTION_TITLE_MISMATCH",
            "authenticFindingCodeCounts": by_id["DEV-06"]["authentic"][
                "validationFindingCodeCounts"
            ],
            "counterfactualFindingCodeCounts": by_id["DEV-06"][
                "sectionTitleOnlyCounterfactual"
            ]["validationFindingCodeCounts"],
            "attributeEvidenceLogicModified": False,
            "causalInterpretation": (
                "Any ATTRIBUTE_EVIDENCE_MISSING findings that disappear do so after "
                "the referenced evidence becomes valid; only sectionTitle changed."
            ),
        },
    }
    return result


def _counterfactual_markdown(diagnostics: Mapping[str, Any]) -> str:
    """Render a compact human-readable counterfactual report."""

    lines = [
        "# M2-C2A section-title-only counterfactual diagnostics",
        "",
        "**COUNTERFACTUAL_DIAGNOSTIC_ONLY — NOT_AUTHENTIC_MODEL_OUTPUT — "
        "NOT_EXTRACTION_OUTPUT — NOT_GOLD — NOT_FORMAL_EVALUATION**",
        "",
        "The accepted C1B model outputs were not changed. Each diagnostic copy changes "
        "only `evidenceSpan.sectionTitle` to trusted `sourceUnit.sectionTitleRaw`.",
        "",
        "| Unit | Authentic evidence | Counterfactual evidence | Authentic V/R/U | Counterfactual V/R/U |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in diagnostics["units"]:
        authentic = row["authentic"]
        counterfactual = row["sectionTitleOnlyCounterfactual"]
        lines.append(
            f"| {row['developmentID']} | {authentic['validEvidenceSpanCount']}/{authentic['evidenceSpanCount']} "
            f"| {counterfactual['validEvidenceSpanCount']}/{counterfactual['evidenceSpanCount']} "
            f"| {authentic['validatedCandidateCount']}/{authentic['rejectedCandidateCount']}/{authentic['usableCandidateCount']} "
            f"| {counterfactual['validatedCandidateCount']}/{counterfactual['rejectedCandidateCount']}/{counterfactual['usableCandidateCount']} |"
        )
    lines.extend(
        [
            "",
            "V/R/U = validated candidates / rejected candidates / hypothetical usable candidates.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_c2a_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Generate every deterministic C2A audit and diagnostic artifact offline."""

    responsibility = build_evidence_field_responsibility_audit()
    schema_audit, specialization = build_prospective_schema_audit(output_dir)
    counterfactual = build_counterfactual_diagnostics(output_dir)
    _write_canonical(output_dir / "evidence_field_responsibility_audit.json", responsibility)
    _write_canonical(
        output_dir / "trusted_section_title_specialization_record.json",
        specialization,
    )
    _write_canonical(
        output_dir / "prospective_devset0_schema_audit.json", schema_audit
    )
    _write_canonical(
        output_dir / "c1b_section_title_counterfactual_diagnostics.json",
        counterfactual,
    )
    markdown_path = output_dir / "c1b_section_title_counterfactual_diagnostics.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_bytes(_counterfactual_markdown(counterfactual).encode("utf-8"))
    return {
        "responsibilityAudit": responsibility,
        "schemaAudit": schema_audit,
        "specializationRecord": specialization,
        "counterfactualDiagnostics": counterfactual,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the deterministic, network-free C2A artifact generator."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR
    )
    args = parser.parse_args(argv)
    result = generate_c2a_artifacts(args.output_dir)
    print(canonical_json(result["counterfactualDiagnostics"]).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
