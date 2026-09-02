"""Measure current DEV-SET-0 full-semantic request-size and redundancy facts offline."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.evidence_coordinate_guide import (
    COORDINATE_GUIDE_SEPARATOR,
    build_coordinate_guided_provider_input,
    build_evidence_coordinate_guide,
)
from src.extraction.llm.publications.openai_provider import (
    build_responses_api_request,
    provider_input_projection,
)
from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    canonical_json_file,
    sha256_bytes,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    C1B_MAX_OUTPUT_TOKENS,
    DEV_IDS,
    build_full_semantic_request,
    load_c0_bindings,
)
from src.extraction.llm.publications.trusted_evidence_metadata_schema import (
    derive_trusted_evidence_metadata_schema,
)


AUDIT_VERSION = "publication-full-semantic-input-contract-efficiency/0.1.0"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "data/curation/papers/m2/"
    "full_semantic_input_contract_efficiency_audit"
)
PIPELINE_EVALUATION_PROVENANCE_FIELDS = (
    "row",
    "production_responsibility",
    "pilot_treatment",
    "direct_instantiation",
    "emission_mode",
    "evaluation_mode",
    "observation_refs",
)
SEMANTIC_OR_CONTRACTUAL_FIELDS = (
    "operational_id",
    "ontology_ids",
    "formal_classes",
    "formal_relations",
    "operational_target",
    "operational_relation",
    "operational_signatures",
    "raw_operational_signature",
    "allowed_actions",
    "endpoint_usage",
    "evidence_requirement",
    "positive_criterion",
    "boundary",
    "identity_policy",
)


def _write(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical, reproducible JSON audit artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _replace_projection_value(
    request: Mapping[str, Any], *, text: str | None = None,
    target_definitions: Sequence[Mapping[str, Any]] | None = None,
) -> bytes:
    """Serialize the bounded projection after one isolated hypothetical replacement."""

    projection = provider_input_projection(request)
    projection["sourceUnit"] = dict(projection["sourceUnit"])
    if text is not None:
        projection["sourceUnit"]["text"] = text
    if target_definitions is not None:
        projection["targetDefinitions"] = list(target_definitions)
    return canonical_json(projection)


def _field_group_bytes(targets: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> int:
    """Return canonical bytes occupied by selected target-definition fields alone."""

    return len(canonical_json([
        {key: row[key] for key in fields if key in row} for row in targets
    ]))


def _literal_ambiguity(source_text: str, guide: Mapping[str, Any]) -> dict[str, Any]:
    """Measure repeated token literals that make literal-only offsets ambiguous."""

    occurrences = Counter(str(row["tokenText"]) for row in guide["entries"])
    repeated = {token: count for token, count in occurrences.items() if count > 1}
    return {
        "guideTokenOccurrences": sum(occurrences.values()),
        "distinctGuideTokenLiterals": len(occurrences),
        "repeatedGuideTokenLiteralKinds": len(repeated),
        "repeatedGuideTokenOccurrences": sum(repeated.values()),
        "examples": [
            {"literal": token, "occurrences": count}
            for token, count in sorted(repeated.items(), key=lambda item: (-item[1], item[0]))[:10]
        ],
        "literalOnlyOffsetRule": (
            "derive offsets only when an exact returned literal has exactly one occurrence; "
            "zero or multiple occurrences fail closed and require returned coordinates"
        ),
        "sourceTextSha256": sha256_bytes(source_text.encode("utf-8")),
    }


def audit_unit(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Build one exact full-semantic input and measure non-overlapping size facts."""

    request = build_full_semantic_request(binding)
    guide = build_evidence_coordinate_guide(request["sourceUnit"])
    provider_input = build_coordinate_guided_provider_input(request, guide)
    schema = derive_trusted_evidence_metadata_schema(request)
    bounded = _replace_projection_value(request)
    empty_text = _replace_projection_value(request, text="")
    empty_targets = _replace_projection_value(request, target_definitions=[])
    prompt = request["prompt"]["text"].encode("utf-8")
    guide_bytes = canonical_json(guide)
    schema_bytes = canonical_json(schema)
    api_body = canonical_json(build_responses_api_request(
        provider_input, model_authorable_schema=schema,
        max_output_tokens=C1B_MAX_OUTPUT_TOKENS, background=True,
    ))
    source_text_delta = len(bounded) - len(empty_text)
    target_delta = len(bounded) - len(empty_targets)
    metadata_delta = len(bounded) - source_text_delta - target_delta
    target_definitions = request["targetDefinitions"]
    pipeline_bytes = _field_group_bytes(
        target_definitions, PIPELINE_EVALUATION_PROVENANCE_FIELDS
    )
    semantic_bytes = _field_group_bytes(
        target_definitions, SEMANTIC_OR_CONTRACTUAL_FIELDS
    )
    reduced_request = deepcopy(request)
    reduced_request["targetDefinitions"] = [
        {
            key: value for key, value in row.items()
            if key not in PIPELINE_EVALUATION_PROVENANCE_FIELDS
        }
        for row in target_definitions
    ]
    reduced_provider_input = build_coordinate_guided_provider_input(
        reduced_request, guide
    )
    reduced_api_body = canonical_json(build_responses_api_request(
        reduced_provider_input, model_authorable_schema=schema,
        max_output_tokens=C1B_MAX_OUTPUT_TOKENS, background=True,
    ))
    return {
        "developmentID": binding["developmentID"],
        "sourceUnitID": binding["sourceUnitID"],
        "providerInputSha256": sha256_bytes(provider_input),
        "apiRequestBodySha256": sha256_bytes(api_body),
        "exactBytes": {
            "canonicalSourceUnitText": source_text_delta,
            "promptInstructions": len(prompt),
            "targetDefinitions": target_delta,
            "coordinateGuidance": len(guide_bytes),
            "otherBoundedRequestMetadata": metadata_delta,
            "boundedRequest": len(bounded),
            "structuredOutputSchema": len(schema_bytes),
            "providerInput": len(provider_input),
            "backgroundResponsesApiBody": len(api_body),
        },
        "compositionCheck": {
            "providerInputEqualsComponents": len(provider_input) == (
                len(prompt) + len("\n\nBounded trusted development request JSON:\n".encode("utf-8"))
                + len(bounded) + len(COORDINATE_GUIDE_SEPARATOR.encode("utf-8"))
                + len(guide_bytes)
            ),
            "boundedRequestEqualsCategories": len(bounded) == (
                source_text_delta + target_delta + metadata_delta
            ),
        },
        "targetDefinitionFieldGroups": {
            "semanticOrContractualFields": list(SEMANTIC_OR_CONTRACTUAL_FIELDS),
            "pipelineEvaluationProvenanceFields": list(PIPELINE_EVALUATION_PROVENANCE_FIELDS),
            "semanticOrContractualCanonicalBytes": semantic_bytes,
            "pipelineEvaluationProvenanceCanonicalBytes": pipeline_bytes,
        },
        "literalOffsetAmbiguity": _literal_ambiguity(request["sourceUnit"]["text"], guide),
        "hypotheticalSeparablyMeasurable": {
            "omitPipelineEvaluationProvenanceFieldsFromProviderTargetDefinitions": {
                "currentFieldGroupCanonicalBytes": pipeline_bytes,
                "currentProviderInputBytes": len(provider_input),
                "hypotheticalProviderInputBytes": len(reduced_provider_input),
                "providerInputReductionBytes": len(provider_input) - len(reduced_provider_input),
                "currentBackgroundResponsesApiBodyBytes": len(api_body),
                "hypotheticalBackgroundResponsesApiBodyBytes": len(reduced_api_body),
                "apiBodyReductionBytes": len(api_body) - len(reduced_api_body),
                "classification": "transport_only_candidate_pending semantic-equivalence review",
                "notImplemented": True,
            },
            "omitCoordinateGuide": {
                "currentBytes": len(COORDINATE_GUIDE_SEPARATOR.encode("utf-8")) + len(guide_bytes),
                "classification": "methodological_or_contractual; guide supports exact coordinate production",
                "notImplemented": True,
            },
        },
    }


def build_audit() -> dict[str, Any]:
    """Return the ten-unit offline audit with stable aggregate ordering and hashes."""

    rows = [audit_unit(binding) for binding in load_c0_bindings()]
    if tuple(row["developmentID"] for row in rows) != DEV_IDS:
        raise ValueError("audit must cover exactly DEV-01 through DEV-10")
    totals = {
        key: sum(row["exactBytes"][key] for row in rows)
        for key in rows[0]["exactBytes"]
    }
    transport_only_estimate = {
        key: sum(
            row["hypotheticalSeparablyMeasurable"]
            ["omitPipelineEvaluationProvenanceFieldsFromProviderTargetDefinitions"][key]
            for row in rows
        )
        for key in (
            "currentProviderInputBytes", "hypotheticalProviderInputBytes",
            "providerInputReductionBytes", "currentBackgroundResponsesApiBodyBytes",
            "hypotheticalBackgroundResponsesApiBodyBytes", "apiBodyReductionBytes",
        )
    }
    record: dict[str, Any] = {
        "auditVersion": AUDIT_VERSION,
        "artifactRole": "development_only_offline_full_semantic_input_contract_efficiency_audit",
        "developmentOnly": True,
        "networkCalls": 0,
        "providerCalls": 0,
        "modelCallMade": False,
        "executionModeMeasured": "background",
        "units": rows,
        "aggregateExactBytes": totals,
        "aggregateHypotheticalTransportOnlyEstimate": transport_only_estimate,
        "redundancyAndDependencyFindings": {
            "repeatedAcrossLayers": [
                "operational target identifiers and ontology class/relation names occur in target definitions and structured-output schema",
                "source-unit text occurs in the bounded request and token text is repeated in coordinate-guide entries",
                "evidence requirements and output field constraints are expressed in both prompt/target definitions and structured-output schema",
            ],
            "targetDefinitionBoundary": {
                "semanticExtraction": list(SEMANTIC_OR_CONTRACTUAL_FIELDS),
                "pipelineEvaluationProvenance": list(PIPELINE_EVALUATION_PROVENANCE_FIELDS),
                "decision": "classification only; no field was removed or request authority changed",
            },
            "evidenceOffsets": {
                "feasibleWhen": "returned literal evidence has exactly one exact occurrence in the canonical source-unit text",
                "ambiguousWhen": "the literal occurs zero times or more than once",
                "failClosedHandling": "retain current required coordinates; do not derive, select, or repair ambiguous offsets",
                "methodologicalBoundary": "literal-only offsets cannot generally replace current evidence/coordinate validation",
            },
        },
        "recommendedSmallestNextExperiment": {
            "kind": "offline differential request-equivalence audit",
            "scope": "one DEV unit, pipeline/evaluation/provenance target-definition fields only",
            "transportOnlyIf": "the researcher accepts a semantic-equivalence proof that no model instruction, schema, parser, validator, or authority consumes the omitted fields",
            "notAuthorizedChange": "do not alter evidence requirements, target boundaries, coordinate guide, or validation in this experiment",
        },
    }
    record["auditSha256"] = sha256_bytes(canonical_json(record))
    return record


def render_report(audit: Mapping[str, Any]) -> str:
    """Render a compact human-readable companion without reproducing source text."""

    lines = [
        "# Full-semantic input-contract efficiency audit",
        "",
        "Offline only: 0 provider/model calls. Sizes are UTF-8 canonical JSON bytes.",
        "",
        "| Unit | Text | Prompt | Targets | Guide | Metadata | Schema | Provider input | API body |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    labels = ("canonicalSourceUnitText", "promptInstructions", "targetDefinitions", "coordinateGuidance", "otherBoundedRequestMetadata", "structuredOutputSchema", "providerInput", "backgroundResponsesApiBody")
    for row in audit["units"]:
        values = row["exactBytes"]
        lines.append("| " + row["developmentID"] + " | " + " | ".join(str(values[key]) for key in labels) + " |")
    lines.extend([
        "",
        "## Findings",
        "",
        "- The guide repeats source tokens with two coordinate systems; it is a methodological/contractual candidate, not a transport-only reduction.",
        "- Target definitions repeat target identity and constraints also represented in the structured schema. Pipeline/evaluation/provenance fields are separately measurable transport-only candidates pending semantic-equivalence review.",
        "- Across DEV-01–DEV-10, omitting only the classified pipeline/evaluation/provenance target-definition fields would reduce the provider input by " + str(audit["aggregateHypotheticalTransportOnlyEstimate"]["providerInputReductionBytes"]) + " bytes and the API body by " + str(audit["aggregateHypotheticalTransportOnlyEstimate"]["apiBodyReductionBytes"]) + " bytes; this is an estimate, not an implemented change.",
        "- Literal evidence can yield offsets only when it appears exactly once in the canonical source-unit text. Repeated or absent literals are ambiguous and must fail closed; current returned coordinates remain required.",
        "- Smallest next experiment: an offline, one-unit differential equivalence audit of pipeline/evaluation/provenance target-definition fields only; do not alter evidence, target, schema, or validation rules.",
        "",
    ])
    return "\n".join(lines)


def write_audit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Write machine-readable and Markdown audit artifacts deterministically."""

    audit = build_audit()
    _write(output_dir / "publication_full_semantic_input_contract_efficiency_audit.json", audit)
    (output_dir / "publication_full_semantic_input_contract_efficiency_report.md").write_text(
        render_report(audit), encoding="utf-8"
    )
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    """Run the explicitly no-call audit."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    audit = write_audit(args.output_dir)
    print(json.dumps({"auditSha256": audit["auditSha256"], "networkCalls": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
