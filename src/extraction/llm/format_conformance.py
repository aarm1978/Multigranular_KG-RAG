"""Opt-in Step 11 format conformance; originals and legacy pipelines stay immutable."""
from copy import deepcopy
import importlib
import json
from typing import Any

from src.extraction.llm.pilot_preflight import canonical, digest, strict_schema
from src.extraction.llm.semantic_target_profiles import get_profile, load_ontology
from src.extraction.llm.publications.deterministic_evidence_binding import _occurrences

VERSION = "study2-format-conformance/1.0.0"
SCHEMA_VERSION = "study2-canonical-declaration-schema/1.0.0"
DIRECTORIES = {"hydroshare": "datasets", "github": "coderepos", "ciroh_hub": "documents"}


def declaration_values(declaration: dict) -> set[str]:
    """Accept the exact spec name, declared CURIE and its exact prefix expansion."""
    # Relation IRIs follow the frozen build_ontology.py minting rule.
    iri = declaration.get("iri", "ciroh:" + declaration["name"])
    prefixes = {p["prefix"]: p["iri"] for p in load_ontology()["prefixes"]}
    prefix, separator, local = iri.partition(":")
    expanded = prefixes[prefix] + local if separator and prefix in prefixes else iri
    return {declaration["name"], iri, expanded}


def derive(payload: dict, request: dict) -> tuple[dict, list[dict]]:
    """Derive only exact declaration/unique-quote conformance from built units.

    This is not validation. Callers must use replay_conformant for verified source,
    selected-unit, parser, dependency and semantic-gate checks.
    """
    result, changes = deepcopy(payload), []
    profile = get_profile(request["artifactFamily"])
    units = {u["sourceUnitID"]: u for u in request["sourceUnits"]}
    for group, targets, field in (("candidateNodes", "entities", "class"), ("candidateEdges", "relations", "relation")):
        for index, row in enumerate(result.get(group, [])):
            if not isinstance(row, dict):
                continue
            identifier = row.get("inventoryId")
            policy = profile[targets].get(identifier) if isinstance(identifier, str) else None
            value = row.get(field)
            if policy and isinstance(value, str):
                declaration = policy["declaration"]
                if value != declaration["name"] and value in declaration_values(declaration):
                    row[field] = declaration["name"]
                    changes.append({"pointer": f"/{group}/{index}/{field}", "reason": "exact_declared_iri_to_name",
                                    "original": value, "derived": row[field]})
            evidence = row.get("evidence")
            for offset, fragment in enumerate(evidence if isinstance(evidence, list) else []):
                if not isinstance(fragment, dict):
                    continue
                uid, quote = fragment.get("sourceUnitID"), fragment.get("evidenceText")
                unit = units.get(uid) if isinstance(uid, str) else None
                anchor = fragment.get("locatorAnchor")
                if not unit or not isinstance(quote, str) or not quote or not isinstance(anchor, str):
                    continue
                text = unit["text"]
                if len(_occurrences(text, quote)) == 1 and (len(_occurrences(text, anchor)) != 1 or quote not in anchor):
                    del fragment["locatorAnchor"]
                    changes.append({"pointer": f"/{group}/{index}/evidence/{offset}/locatorAnchor",
                                    "reason": "invalid_redundant_anchor_ignored_unique_literal", "original": anchor,
                                    "sourceUnitID": uid, "evidenceText": quote})
    return result, changes


def replay_conformant(recorded_response: bytes, *, family: str, request_inputs: dict,
                      expected_request_sha256: str, conformance_version: str) -> dict[str, Any]:
    """Replay an explicit derived representation, retaining exact authentic bytes.

    No legacy defaults change. The original parser runs before derivation; malformed
    envelopes remain processing failures. Existing pipelines reverify source integrity,
    selected units and dependencies. Their response hash labels DERIVED bytes only.
    """
    if conformance_version != VERSION or family not in DIRECTORIES:
        raise ValueError("unsupported conformance version or family")
    if not isinstance(recorded_response, bytes):
        raise TypeError("exact response bytes required")
    prefix = "src.extraction.llm." + DIRECTORIES[family]
    contract = importlib.import_module(prefix + ".request_contract")
    pipeline = importlib.import_module(prefix + ".offline_pipeline")
    request = contract.build_request(**deepcopy(request_inputs))
    if request.get("status") != "request_ready" or request.get("requestSha256") != expected_request_sha256:
        raise ValueError("verified request/hash required")
    parsed = contract.parse_recorded_response(recorded_response, request=request)
    derived_bytes, changes = recorded_response, []
    if parsed["status"] == "response_parsed":
        derived, changes = derive(json.loads(recorded_response), request["request"])
        if changes:
            derived_bytes = canonical(derived)
    replay = pipeline.replay_recorded_response(derived_bytes, request_inputs=deepcopy(request_inputs),
                                              expected_request_sha256=expected_request_sha256)
    record = json.loads(replay.report_json)
    # Never promote pre-existing identifiable parser failures by conformance.
    invalid = {r["candidateID"] for r in parsed["candidateRecords"] if r["parseDisposition"] != "pending_validation"}
    assert not any(r["candidateID"] in invalid and r["finalDisposition"] == "validated" for r in record["finalRecords"])
    return {"conformanceVersion": VERSION, "originalResponseBytesHex": recorded_response.hex(),
            "originalResponseSha256": digest(recorded_response), "semanticRequestSha256": expected_request_sha256,
            "derivedResponseBytesHex": derived_bytes.hex(), "derivedResponseSha256": digest(derived_bytes),
            "changes": changes, "derivedReplay": record, "derivedReplaySha256": replay.report_sha256,
            "semanticStatus": "not_evaluated", "kgAuthorization": False}


def canonical_response_schema(contract: dict, profile: dict, *, schema_version: str) -> dict:
    """Prospective strict schema; historical schema generation is unchanged."""
    if schema_version != SCHEMA_VERSION:
        raise ValueError("unsupported schema version")
    schema = strict_schema(contract, profile)
    for group, targets, field in (("candidateNodes", "entities", "class"), ("candidateEdges", "relations", "relation")):
        for branch in schema["properties"][group]["items"]["anyOf"]:
            identifier = branch["properties"]["inventoryId"]["enum"][0]
            branch["properties"][field] = {"type": "string", "enum": [profile[targets][identifier]["declaration"]["name"]]}
    return schema


def build_conformant_preflight(request_result: dict, *, schema_version: str,
                              output_ceiling: int = 32768, projection_version: str | None = None) -> dict:
    """Build an unauthorized prospective envelope without altering historical ones."""
    from src.extraction.llm.pilot_preflight import build_preflight, check_strict_structure
    result = build_preflight(request_result, output_ceiling=output_ceiling, projection_version=projection_version)
    body = request_result["request"]
    schema = canonical_response_schema(body["responseContract"], body["targetProfile"], schema_version=schema_version)
    check_strict_structure(schema)
    result["envelope"]["text"]["format"]["schema"] = schema
    result["envelope"]["text"]["format"]["name"] += "_canonical_v1"
    wire = canonical(result["envelope"])
    result.update(responseSchemaVersion=schema_version, conformanceVersion=VERSION,
                  wireBytes=wire, providerEnvelopeSha256=digest(wire), wireByteCount=len(wire),
                  schemaSha256=digest(canonical(schema)), schemaByteCount=len(canonical(schema)))
    return result
