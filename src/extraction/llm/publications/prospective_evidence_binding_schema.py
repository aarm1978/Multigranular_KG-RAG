"""Derive the fresh full-semantic provider schema for deterministic evidence binding."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import jsonschema

from src.extraction.llm.publications.deterministic_evidence_binding import (
    COMPUTED_EVIDENCE_FIELDS,
    LOCATOR_ANCHOR_FIELD,
)
from src.extraction.llm.publications.model_authorable_schema import (
    ModelAuthorableSchemaError,
    audit_openai_structured_outputs_schema,
)
from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes
from src.extraction.llm.publications.trusted_evidence_metadata_schema import (
    derive_trusted_evidence_metadata_schema,
)


PROSPECTIVE_EVIDENCE_BINDING_SCHEMA_VERSION = "publication-request-specialized-0.3.0"


def derive_prospective_evidence_binding_schema(request: Mapping[str, Any]) -> dict[str, Any]:
    """Remove pipeline-computed evidence coordinates/hash from provider output.

    ``locatorAnchor`` is nullable solely because strict Structured Outputs requires all
    object properties to be required. A null value means it is absent.
    """

    schema = deepcopy(derive_trusted_evidence_metadata_schema(request))
    evidence = schema["$defs"]["evidenceSpan"]
    properties = evidence["properties"]
    required = evidence["required"]
    for name in COMPUTED_EVIDENCE_FIELDS:
        properties.pop(name, None)
        required.remove(name)
    properties[LOCATOR_ANCHOR_FIELD] = {"type": ["string", "null"]}
    required.append(LOCATOR_ANCHOR_FIELD)
    jsonschema.Draft202012Validator.check_schema(schema)
    audit = audit_openai_structured_outputs_schema(schema)
    if not audit["compatible"]:
        raise ModelAuthorableSchemaError(f"evidence-binding schema incompatible: {audit['findings']}")
    return schema


def prospective_evidence_binding_schema_record(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return deterministic provenance for the prospective-only schema delta."""

    historical = derive_trusted_evidence_metadata_schema(request)
    prospective = derive_prospective_evidence_binding_schema(request)
    record: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "prospective_deterministic_evidence_binding_provider_schema",
        "developmentOnly": True,
        "providerCalls": 0,
        "schemaVersion": PROSPECTIVE_EVIDENCE_BINDING_SCHEMA_VERSION,
        "baseTrustedMetadataSchemaSha256": sha256_bytes(canonical_json(historical)),
        "prospectiveSchemaSha256": sha256_bytes(canonical_json(prospective)),
        "removedProviderAuthoredFields": sorted(COMPUTED_EVIDENCE_FIELDS),
        "locatorAnchor": {
            "field": LOCATOR_ANCHOR_FIELD,
            "semanticAuthority": False,
            "purpose": "location_only_disambiguation_for_repeated_exact_evidence",
            "nullableBecauseStrictStructuredOutputsRequiresProperties": True,
        },
        "canonicalEvidenceAndV1V12Unchanged": True,
    }
    record["recordSha256"] = sha256_bytes(canonical_json(record))
    return record
