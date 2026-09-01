"""Bind trusted Publication evidence metadata in current provider schemas.

Version 0.2.1 builds on the request-specialized 0.1.1 transport
projection.  It narrows only ``evidenceSpan.sectionTitle`` to the exact trusted
``sourceUnit.sectionTitleRaw`` value.  The frozen candidate schema and the
unchanged M1 validator remain the semantic authorities.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import jsonschema

from src.extraction.llm.publications.model_authorable_schema import (
    ModelAuthorableSchemaError,
    audit_openai_structured_outputs_schema,
)
from src.extraction.llm.publications.request_builder import (
    CANDIDATE_SCHEMA_PATH,
    TARGET_INVENTORY_PATH,
    canonical_json,
    sha256_bytes,
)
from src.extraction.llm.publications.request_specialized_schema import (
    REQUEST_SPECIALIZED_SCHEMA_VERSION,
    derive_request_specialized_schema,
)


TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION = "publication-request-specialized-0.2.1"
SECTION_TITLE_AUTHORITY_POINTER = "/sourceUnit/sectionTitleRaw"
SECTION_TITLE_SCHEMA_POINTER = "/$defs/evidenceSpan/properties/sectionTitle"
HISTORICAL_SECTION_TITLE_SCHEMA = {"$ref": "#/$defs/stringOrNull"}


def _exact_section_title_schema(value: str | None) -> dict[str, Any]:
    """Return the provider-compatible exact const for one authoritative title."""

    if value is None:
        return {"type": "null", "const": None}
    if isinstance(value, str):
        return {"type": "string", "const": value}
    raise ModelAuthorableSchemaError(
        "sourceUnit.sectionTitleRaw must be a string or null"
    )


def authoritative_section_title(request: Mapping[str, Any]) -> str | None:
    """Read the sole title authority from the trusted source-unit request record."""

    source_unit = request.get("sourceUnit")
    if not isinstance(source_unit, Mapping) or "sectionTitleRaw" not in source_unit:
        raise ModelAuthorableSchemaError(
            "trusted request lacks sourceUnit.sectionTitleRaw"
        )
    value = source_unit["sectionTitleRaw"]
    if value is not None and not isinstance(value, str):
        raise ModelAuthorableSchemaError(
            "sourceUnit.sectionTitleRaw must be a string or null"
        )
    return value


def derive_trusted_evidence_metadata_schema(
    request: Mapping[str, Any],
    *,
    schema_path: Path = CANDIDATE_SCHEMA_PATH,
    inventory_path: Path = TARGET_INVENTORY_PATH,
) -> dict[str, Any]:
    """Derive the current provider schema and bind exactly one trusted field."""

    schema = deepcopy(
        derive_request_specialized_schema(
            request,
            schema_path=schema_path,
            inventory_path=inventory_path,
        )
    )
    try:
        properties = schema["$defs"]["evidenceSpan"]["properties"]
        historical = properties["sectionTitle"]
    except (KeyError, TypeError) as exc:
        raise ModelAuthorableSchemaError(
            "request-specialized schema lacks the frozen evidence sectionTitle path"
        ) from exc
    if historical != HISTORICAL_SECTION_TITLE_SCHEMA:
        raise ModelAuthorableSchemaError(
            "historical sectionTitle transport shape drifted before prospective binding"
        )
    properties["sectionTitle"] = _exact_section_title_schema(
        authoritative_section_title(request)
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    audit = audit_openai_structured_outputs_schema(schema)
    if not audit["compatible"]:
        raise ModelAuthorableSchemaError(
            f"trusted-metadata schema is not OpenAI-compatible: {audit['findings']}"
        )
    return schema


def trusted_evidence_metadata_schema_record(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Return deterministic provenance for the current provider title binding."""

    historical = derive_request_specialized_schema(request)
    prospective = derive_trusted_evidence_metadata_schema(request)
    title = authoritative_section_title(request)
    record: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "current_trusted_evidence_metadata_transport_specialization",
        "developmentOnly": True,
        "providerCalls": 0,
        "historicalRequestSpecializedSchemaVersion": REQUEST_SPECIALIZED_SCHEMA_VERSION,
        "prospectiveRequestSpecializedSchemaVersion": TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION,
        "historicalBehavior": {
            "field": "evidenceSpan.sectionTitle",
            "constraint": HISTORICAL_SECTION_TITLE_SCHEMA,
            "responsibility": "model_authorable_within_stringOrNull",
        },
        "prospectiveBehavior": {
            "field": "evidenceSpan.sectionTitle",
            "constraint": _exact_section_title_schema(title),
            "responsibility": "trusted_request_metadata_exact_const",
            "authorityPointer": SECTION_TITLE_AUTHORITY_POINTER,
            "transportSchemaPointer": SECTION_TITLE_SCHEMA_POINTER,
            "normalizationApplied": False,
        },
        "onlyProspectiveFieldBound": "evidenceSpan.sectionTitle",
        "candidateSchemaSha256": sha256_bytes(CANDIDATE_SCHEMA_PATH.read_bytes()),
        "targetInventorySha256": sha256_bytes(TARGET_INVENTORY_PATH.read_bytes()),
        "historicalSchemaSha256": sha256_bytes(canonical_json(historical)),
        "prospectiveSchemaSha256": sha256_bytes(canonical_json(prospective)),
        "providerCompatibilityAudit": audit_openai_structured_outputs_schema(
            prospective
        ),
    }
    record["recordSha256"] = sha256_bytes(canonical_json(record))
    return record
