"""Derive the prospective provider schema with pipeline-owned endpoint metadata."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import jsonschema

from src.extraction.llm.publications.model_authorable_schema import (
    ModelAuthorableSchemaError,
    audit_openai_structured_outputs_schema,
)
from src.extraction.llm.publications.prospective_evidence_binding_schema import (
    derive_prospective_evidence_binding_schema,
)
from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes


PROSPECTIVE_ENDPOINT_BINDING_SCHEMA_VERSION = "publication-request-specialized-0.5.0"


def derive_prospective_endpoint_binding_schema(request: Mapping[str, Any]) -> dict[str, Any]:
    """Remove model-authored endpoint artifact IDs from the v0.4.0 transport schema."""

    schema = deepcopy(derive_prospective_evidence_binding_schema(request))
    endpoint = schema["$defs"]["edgeEndpoint"]
    endpoint["properties"].pop("artifactID", None)
    endpoint["required"].remove("artifactID")
    jsonschema.Draft202012Validator.check_schema(schema)
    audit = audit_openai_structured_outputs_schema(schema)
    if not audit["compatible"]:
        raise ModelAuthorableSchemaError(f"endpoint-binding schema incompatible: {audit['findings']}")
    return schema


def prospective_endpoint_binding_schema_record(request: Mapping[str, Any]) -> dict[str, Any]:
    """Record the v0.4.0 to v0.5.0 provider ownership transition."""

    previous = derive_prospective_evidence_binding_schema(request)
    prospective = derive_prospective_endpoint_binding_schema(request)
    record: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "prospective_deterministic_endpoint_binding_provider_schema",
        "developmentOnly": True,
        "providerCalls": 0,
        "schemaVersion": PROSPECTIVE_ENDPOINT_BINDING_SCHEMA_VERSION,
        "baseEvidenceBindingSchemaSha256": sha256_bytes(canonical_json(previous)),
        "prospectiveSchemaSha256": sha256_bytes(canonical_json(prospective)),
        "removedProviderAuthoredFields": ["candidateEdges.*.source.artifactID", "candidateEdges.*.target.artifactID"],
        "semanticEndpointFieldsRemainModelAuthored": ["referenceType", "referenceID"],
        "canonicalEndpointArtifactMetadataAndV1V12Unchanged": True,
        "providerCompatibilityAudit": audit_openai_structured_outputs_schema(prospective),
    }
    record["recordSha256"] = sha256_bytes(canonical_json(record))
    return record
