"""Build deterministic provider-neutral requests for approved Publication development units.

This module is intentionally publication-specific. It reads the approved development
manifest and frozen Publication authorities, preserves the selected source-unit record
without modification, and adds only explicit request-layer routing for development runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEVELOPMENT_MANIFEST_PATH = PROJECT_ROOT / "data/curation/papers/publication_llm_development_only_manifest.json"
DEVELOPMENT_INVENTORY_PATH = PROJECT_ROOT / "data/curation/papers/publication_llm_development_only_source_unit_inventory.jsonl"
TARGET_INVENTORY_PATH = PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml"
ONTOLOGY_SPEC_PATH = PROJECT_ROOT / "src/ontology/ontology_spec.yaml"
CANDIDATE_SCHEMA_PATH = PROJECT_ROOT / "schemas/publication_candidate_output.schema.json"
SOURCE_UNIT_CONTRACT_PATH = PROJECT_ROOT / "docs/publication_source_unit_contract.md"
EVIDENCE_VALIDATION_CONTRACT_PATH = PROJECT_ROOT / "docs/publication_evidence_validation_contract.md"
EVALUATION_MATCHING_CONTRACT_PATH = PROJECT_ROOT / "docs/publication_evaluation_matching_contract.md"
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.0.txt"

REQUEST_BUILDER_VERSION = "0.1.0"
REQUEST_SCHEMA_VERSION = "0.1.0"
PROMPT_VERSION = "publication-development-0.1.0"


class RequestBuildError(ValueError):
    """Report a deterministic development-request construction failure."""


def canonical_json(value: Any) -> bytes:
    """Serialize one value as compact sorted-key UTF-8 JSON with no final newline."""

    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_json_file(value: Any) -> bytes:
    """Serialize one canonical JSON file with exactly one LF terminator."""

    return canonical_json(value) + b"\n"


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 hexadecimal digest."""

    return hashlib.sha256(value).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON object or fail when the top-level value is not an object."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RequestBuildError(f"expected JSON object: {path}")
    return value


def load_yaml_object(path: Path) -> dict[str, Any]:
    """Load a UTF-8 YAML mapping or fail when the top-level value is not a mapping."""

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RequestBuildError(f"expected YAML mapping: {path}")
    return value


def load_development_inventory(path: Path = DEVELOPMENT_INVENTORY_PATH) -> list[dict[str, Any]]:
    """Load the immutable DEV-SET-0 outside-Pilot source-unit inventory."""

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(row, dict) for row in rows):
        raise RequestBuildError("development inventory must contain JSON objects")
    return rows


def _candidate_target_rows(profile: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Index candidate-emittable frozen node and relation target rows."""

    rows = list(profile.get("node_targets", [])) + list(profile.get("relation_targets", []))
    return {
        str(row["operational_id"]): dict(row)
        for row in rows
        if row.get("emission_mode") in {"llm_candidate", "resolver_mediated_candidate"}
        or "link_existing" in row.get("allowed_actions", [])
    }


def _validate_requested_targets(
    target_ids: Sequence[str], profile: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Resolve an explicit unique target list against the frozen emittable profile."""

    if not target_ids:
        raise RequestBuildError("at least one operational target is required")
    if len(set(target_ids)) != len(target_ids):
        raise RequestBuildError("duplicate operational targets are not allowed")
    available = _candidate_target_rows(profile)
    unknown = [target_id for target_id in target_ids if target_id not in available]
    if unknown:
        raise RequestBuildError(f"unknown or non-emittable operational targets: {unknown}")
    incompatible = [
        target_id
        for target_id in target_ids
        if available[target_id].get("pilot_treatment")
        in {"out_of_scope", "required_infrastructure", "separate_follow_on_protocol"}
    ]
    if incompatible:
        raise RequestBuildError(f"operational targets are not development-emittable: {incompatible}")
    return [available[target_id] for target_id in target_ids]


def build_development_request(
    source_unit_id: str,
    operational_target_ids: Sequence[str],
    *,
    run_id: str,
    prompt_path: Path = DEFAULT_PROMPT_PATH,
    development_manifest_path: Path = DEVELOPMENT_MANIFEST_PATH,
    development_inventory_path: Path = DEVELOPMENT_INVENTORY_PATH,
) -> dict[str, Any]:
    """Build one canonical request for an exact approved development source unit."""

    manifest = load_json_object(development_manifest_path)
    if manifest.get("status") != "approved_for_development":
        raise RequestBuildError("development manifest is not approved_for_development")
    approved = {row["sourceUnitID"]: row for row in manifest.get("units", [])}
    if source_unit_id not in approved:
        raise RequestBuildError(f"source unit is not approved for development: {source_unit_id}")

    inventory = load_development_inventory(development_inventory_path)
    matching = [row for row in inventory if row.get("sourceUnitID") == source_unit_id]
    if len(matching) != 1:
        raise RequestBuildError(f"approved source unit must resolve exactly once: {source_unit_id}")
    source_unit = matching[0]
    publication_id = str(source_unit["paperID"])
    if publication_id != str(approved[source_unit_id]["sourcePublicationID"]):
        raise RequestBuildError("development manifest publication binding mismatch")
    pilot_ids = {str(value) for value in manifest.get("pilot1ArtifactIds", [])}
    if publication_id in pilot_ids:
        raise RequestBuildError(f"Pilot 1 publication is prohibited in development mode: {publication_id}")
    if not manifest.get("pilot1ArtifactDisjoint"):
        raise RequestBuildError("development manifest does not attest Pilot 1 disjointness")
    if source_unit.get("validationResults") != {"valid": True, "errorCodes": []}:
        raise RequestBuildError("source unit failed frozen integrity validation")
    if source_unit.get("eligibility") != "eligible" or not source_unit.get("requestEligible"):
        raise RequestBuildError("source unit is not request eligible")

    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    ontology = load_yaml_object(ONTOLOGY_SPEC_PATH)
    schema = load_json_object(CANDIDATE_SCHEMA_PATH)
    target_rows = _validate_requested_targets(operational_target_ids, profile)
    prompt_bytes = prompt_path.read_bytes()
    try:
        prompt_text = prompt_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RequestBuildError("development prompt must be UTF-8") from exc

    authority = {
        "candidateSchema": {
            "path": str(CANDIDATE_SCHEMA_PATH.relative_to(PROJECT_ROOT)),
            "version": schema["properties"]["schemaVersion"]["const"],
            "sha256": sha256_bytes(CANDIDATE_SCHEMA_PATH.read_bytes()),
        },
        "evidenceValidationContract": {
            "path": str(EVIDENCE_VALIDATION_CONTRACT_PATH.relative_to(PROJECT_ROOT)),
            "version": "0.1.0",
            "sha256": sha256_bytes(EVIDENCE_VALIDATION_CONTRACT_PATH.read_bytes()),
        },
        "evaluationMatchingContract": {
            "path": str(EVALUATION_MATCHING_CONTRACT_PATH.relative_to(PROJECT_ROOT)),
            "sha256": sha256_bytes(EVALUATION_MATCHING_CONTRACT_PATH.read_bytes()),
        },
        "ontology": {
            "path": str(ONTOLOGY_SPEC_PATH.relative_to(PROJECT_ROOT)),
            "version": str(ontology["ontology"]["version"]),
            "specSha256": sha256_bytes(ONTOLOGY_SPEC_PATH.read_bytes()),
            "validatedOwlSha256": profile["ontology"]["validated_owl_sha256"],
        },
        "sourceUnitContract": {
            "path": str(SOURCE_UNIT_CONTRACT_PATH.relative_to(PROJECT_ROOT)),
            "version": str(source_unit["contractVersion"]),
            "sha256": sha256_bytes(SOURCE_UNIT_CONTRACT_PATH.read_bytes()),
        },
        "targetInventory": {
            "path": str(TARGET_INVENTORY_PATH.relative_to(PROJECT_ROOT)),
            "profileID": profile["profile_id"],
            "version": str(profile["schema_version"]),
            "sha256": sha256_bytes(TARGET_INVENTORY_PATH.read_bytes()),
        },
    }
    request: dict[str, Any] = {
        "requestSchemaVersion": REQUEST_SCHEMA_VERSION,
        "requestBuilderVersion": REQUEST_BUILDER_VERSION,
        "purpose": "publication_llm_development_only",
        "developmentManifest": {
            "path": str(development_manifest_path.relative_to(PROJECT_ROOT)),
            "sha256": sha256_bytes(development_manifest_path.read_bytes()),
            "status": manifest["status"],
        },
        "developmentInventory": {
            "path": str(development_inventory_path.relative_to(PROJECT_ROOT)),
            "sha256": sha256_bytes(development_inventory_path.read_bytes()),
        },
        "runID": run_id,
        "sourcePublicationID": publication_id,
        "sourceArtifactID": source_unit["canonicalArtifactID"],
        "primarySourceUnitID": source_unit_id,
        "contextSourceUnitIDs": [],
        "requestScope": "local_unit",
        "includedCompleteSection": False,
        "extractionChannel": "open_discovery",
        "eligibleOperationalTargetIDs": list(operational_target_ids),
        "deferredRecordIDs": [],
        "sourceUnit": source_unit,
        "deterministicEndpoints": [],
        "acceptedLocalCandidateEndpoints": [],
        "deferredRecords": [],
        "targetDefinitions": target_rows,
        "prompt": {
            "path": str(prompt_path.relative_to(PROJECT_ROOT)),
            "version": PROMPT_VERSION,
            "sha256": sha256_bytes(prompt_bytes),
            "text": prompt_text,
        },
        "authorities": authority,
        "offlineResponseMetadata": {
            "provider": "recorded_provider_neutral",
            "modelName": "not_applicable_recorded_fixture",
            "modelVersion": None,
            "generationParameters": {
                "temperature": 0,
                "topP": 1,
                "seed": 0,
                "maxOutputTokens": 4096,
                "responseFormat": "structured_json",
            },
            "tokenUsage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
            "costUSD": None,
            "retryCount": 0,
            "responseCreatedAt": "2026-08-27T00:00:00Z",
        },
    }
    identity_projection = {
        "requestBuilderVersion": REQUEST_BUILDER_VERSION,
        "runID": run_id,
        "sourceUnitID": source_unit_id,
        "sourceUnitTextHash": source_unit["textHash"],
        "eligibleOperationalTargetIDs": list(operational_target_ids),
        "promptSha256": request["prompt"]["sha256"],
    }
    request["requestID"] = f"publication-request-{sha256_bytes(canonical_json(identity_projection))[:20]}"
    request["requestInputSha256"] = sha256_bytes(canonical_json(request))
    return request


def expected_candidate_metadata(
    request: Mapping[str, Any], raw_response_sha256: str
) -> dict[str, Any]:
    """Return pipeline-owned candidate metadata bound to a trusted request and response."""

    authorities = request["authorities"]
    return {
        "outputID": f"publication-output-{request['requestInputSha256'][:20]}",
        "requestID": request["requestID"],
        "runID": request["runID"],
        "sourceArtifactID": request["sourceArtifactID"],
        "primarySourceUnitID": request["primarySourceUnitID"],
        "contextSourceUnitIDs": list(request["contextSourceUnitIDs"]),
        "requestScope": request["requestScope"],
        "includedCompleteSection": request["includedCompleteSection"],
        "extractionChannel": request["extractionChannel"],
        "eligibleOperationalTargetIDs": list(request["eligibleOperationalTargetIDs"]),
        "deferredRecordIDs": list(request["deferredRecordIDs"]),
        "ontologyVersion": authorities["ontology"]["version"],
        "ontologySha256": authorities["ontology"]["validatedOwlSha256"],
        "targetInventoryProfileID": authorities["targetInventory"]["profileID"],
        "targetInventorySchemaVersion": authorities["targetInventory"]["version"],
        "targetInventorySha256": authorities["targetInventory"]["sha256"],
        "sourceUnitContractVersion": authorities["sourceUnitContract"]["version"],
        "sourceUnitContractSha256": authorities["sourceUnitContract"]["sha256"],
        "candidateSchemaVersion": authorities["candidateSchema"]["version"],
        "candidateSchemaSha256": authorities["candidateSchema"]["sha256"],
        "promptVersion": request["prompt"]["version"],
        "promptSha256": request["prompt"]["sha256"],
        "requestInputSha256": request["requestInputSha256"],
        "rawResponseSha256": raw_response_sha256,
        **dict(request["offlineResponseMetadata"]),
    }
