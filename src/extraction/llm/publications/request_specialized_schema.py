"""Derive a request-bound OpenAI transport schema from frozen Publication authorities.

This module narrows the generic M2-B1 transport projection to operational targets in
one trusted request. It compiles only consequences already expressed by the frozen
candidate schema or target inventory; the unchanged M1 validator remains authoritative
for evidence, endpoint resolution, and constraints that cannot be represented safely.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import jsonschema

from src.extraction.llm.publications.model_authorable_schema import (
    MODEL_AUTHORABLE_SCHEMA_VERSION,
    ModelAuthorableSchemaError,
    _adapt_for_openai_strict,
    audit_openai_structured_outputs_schema,
    derive_model_authorable_schema,
)
from src.extraction.llm.publications.request_builder import (
    CANDIDATE_SCHEMA_PATH,
    TARGET_INVENTORY_PATH,
    canonical_json,
    load_json_object,
    load_yaml_object,
    sha256_bytes,
)


REQUEST_SPECIALIZED_SCHEMA_VERSION = "publication-request-specialized-0.1.1"


def _const_schema(value: Any) -> dict[str, Any]:
    """Return an explicit-type singleton schema for one JSON primitive."""

    if value is None:
        value_type = "null"
    elif isinstance(value, bool):
        value_type = "boolean"
    elif isinstance(value, str):
        value_type = "string"
    elif isinstance(value, int):
        value_type = "integer"
    elif isinstance(value, float):
        value_type = "number"
    else:
        raise ModelAuthorableSchemaError("request specialization requires a primitive const")
    return {"type": value_type, "const": value}


def _enum_schema(values: list[str]) -> dict[str, Any]:
    """Return an explicit string enum, collapsed to const when it has one value."""

    ordered = list(dict.fromkeys(values))
    if not ordered:
        raise ModelAuthorableSchemaError("request specialization produced an empty enum")
    return _const_schema(ordered[0]) if len(ordered) == 1 else {"type": "string", "enum": ordered}


def _target_index(profile: Mapping[str, Any]) -> dict[str, tuple[str, Mapping[str, Any]]]:
    """Index candidate-authorable node and relation rows by operational identifier."""

    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for kind, key in (("node", "node_targets"), ("relation", "relation_targets")):
        for row in profile.get(key, []):
            if row.get("allowed_actions"):
                indexed[str(row["operational_id"])] = (kind, row)
    return indexed


def _trusted_request_targets(
    request: Mapping[str, Any], profile: Mapping[str, Any]
) -> list[tuple[str, Mapping[str, Any]]]:
    """Validate and return request target rows in trusted request order."""

    eligible = list(request.get("eligibleOperationalTargetIDs", []))
    definitions = list(request.get("targetDefinitions", []))
    if [row.get("operational_id") for row in definitions] != eligible:
        raise ModelAuthorableSchemaError("request target definitions do not match eligible IDs")
    indexed = _target_index(profile)
    resolved: list[tuple[str, Mapping[str, Any]]] = []
    if len(eligible) != len(definitions):
        raise ModelAuthorableSchemaError("request target definitions have the wrong count")
    for target_id, supplied in zip(eligible, definitions):
        if target_id not in indexed:
            raise ModelAuthorableSchemaError(f"request target is not candidate-authorable: {target_id}")
        kind, authoritative = indexed[target_id]
        if canonical_json(supplied) != canonical_json(authoritative):
            raise ModelAuthorableSchemaError(f"request target definition drift: {target_id}")
        resolved.append((kind, authoritative))
    return resolved


def _condition_matches(condition: Mapping[str, Any], assignment: Mapping[str, Any]) -> bool | None:
    """Evaluate a frozen condition only when every required discriminator is known."""

    required = condition.get("required", [])
    if not all(name in assignment for name in required):
        return None
    projected = {name: assignment[name] for name in assignment}
    return jsonschema.Draft202012Validator(condition).is_valid(projected)


def _compiled_consequences(
    frozen_definition: Mapping[str, Any], assignment: Mapping[str, Any]
) -> tuple[dict[str, Any], list[int], list[int]]:
    """Collect property consequences of deterministically true frozen conditionals."""

    consequences: dict[str, Any] = {}
    compiled: list[int] = []
    deferred: list[int] = []
    for index, rule in enumerate(frozen_definition.get("allOf", []), start=1):
        condition = rule.get("if", {})
        result = _condition_matches(condition, assignment)
        if result is None:
            deferred.append(index)
        elif result:
            compiled.append(index)
            consequences.update(deepcopy(rule.get("then", {}).get("properties", {})))
    return consequences, compiled, deferred


def _attribute_schema(row: Mapping[str, Any], generic: Mapping[str, Any]) -> dict[str, Any]:
    """Select frozen candidate-attribute alternatives authorized by one target row."""

    names = {
        attribute["name"]
        for formal in row.get("formal_classes", [])
        for attribute in formal.get("attributes", [])
    }
    if not names:
        return {"type": "array", "items": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "maxItems": 0}
    alternatives = generic["$defs"]["candidateAttribute"]["anyOf"]
    selected = [deepcopy(branch) for branch in alternatives if branch["properties"]["attributeName"].get("const") in names]
    if {branch["properties"]["attributeName"]["const"] for branch in selected} != names:
        raise ModelAuthorableSchemaError("target attributes are not represented by the frozen candidate schema")
    item_schema = selected[0] if len(selected) == 1 else {"anyOf": selected}
    return {"type": "array", "items": item_schema}


def _apply_simple_consequence(properties: dict[str, Any], name: str, constraint: Mapping[str, Any]) -> None:
    """Apply one frozen scalar/array consequence without unsupported composition."""

    if name == "attributes":
        if constraint.get("maxItems") == 0:
            properties[name] = {"type": "array", "items": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "maxItems": 0}
        return
    adapted = _adapt_for_openai_strict(constraint)
    if set(adapted) == {"type"} or "const" in adapted or "enum" in adapted or "minLength" in adapted:
        properties[name] = adapted


def _node_branch(
    row: Mapping[str, Any], request: Mapping[str, Any], generic: Mapping[str, Any], frozen: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one target-bound candidate-node branch from frozen data."""

    base = deepcopy(generic["$defs"]["candidateNode"])
    properties = base["properties"]
    formal = row.get("formal_classes", [])
    actions = list(row.get("allowed_actions", []))
    if not formal or not actions:
        raise ModelAuthorableSchemaError("node target lacks frozen class/action authority")
    assignment = {
        "operationalTargetID": row["operational_id"],
        "origin": request["extractionChannel"],
    }
    properties["operationalTargetID"] = _const_schema(row["operational_id"])
    properties["ontologyClassID"] = _enum_schema([item["id"] for item in formal])
    properties["className"] = _enum_schema([item["name"] for item in formal])
    properties["action"] = _enum_schema(actions)
    properties["origin"] = _const_schema(request["extractionChannel"])
    properties["attributes"] = _attribute_schema(row, generic)

    compiled_all: set[int] = set()
    deferred_all: set[int] = set()
    action_branches: list[dict[str, Any]] = []
    for action in actions:
        action_base = deepcopy(base)
        action_properties = action_base["properties"]
        action_properties["action"] = _const_schema(action)
        current = dict(assignment, action=action)
        consequences, compiled, deferred = _compiled_consequences(frozen["$defs"]["candidateNode"], current)
        compiled_all.update(compiled)
        deferred_all.update(deferred)
        for name, constraint in consequences.items():
            _apply_simple_consequence(action_properties, name, constraint)
        action_properties["operationalTargetID"] = _const_schema(row["operational_id"])
        action_properties["ontologyClassID"] = _enum_schema([item["id"] for item in formal])
        action_properties["className"] = _enum_schema([item["name"] for item in formal])
        action_properties["action"] = _const_schema(action)
        action_properties["origin"] = _const_schema(request["extractionChannel"])
        action_properties["attributes"] = _attribute_schema(row, generic)
        if action == "link_existing":
            action_properties["identityScope"] = _const_schema("exact_existing_endpoint")
        elif row.get("emission_mode") == "resolver_mediated_candidate":
            action_properties["identityScope"] = _const_schema("resolver_pending")
        elif row.get("emission_mode") == "llm_candidate":
            action_properties["identityScope"] = _const_schema("source_local")
        if action_properties.get("identityScope", {}).get("const") == "source_local":
            action_properties["artifactScope"] = _const_schema("source_artifact")
        elif action_properties.get("identityScope", {}).get("const") in {"resolver_pending", "exact_existing_endpoint"}:
            action_properties["artifactScope"] = _const_schema("external_artifact")
        action_branches.append(action_base)
    branch = action_branches[0] if len(action_branches) == 1 else {"anyOf": action_branches}
    return branch, {"compiledConditionalRuleIndexes": sorted(compiled_all), "uncompiledConditionalRuleIndexes": sorted(deferred_all)}


def _edge_branch(
    row: Mapping[str, Any], request: Mapping[str, Any], generic: Mapping[str, Any], frozen: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one target-bound candidate-edge branch from frozen data."""

    base = deepcopy(generic["$defs"]["candidateEdge"])
    properties = base["properties"]
    formal = row.get("formal_relations", [])
    actions = list(row.get("allowed_actions", []))
    properties["operationalRelationID"] = _const_schema(row["operational_id"])
    properties["ontologyRelationID"] = _enum_schema([item["id"] for item in formal])
    properties["relationName"] = _enum_schema([item["name"] for item in formal])
    properties["action"] = _enum_schema(actions)
    properties["origin"] = _const_schema(request["extractionChannel"])
    compiled_all: set[int] = set()
    deferred_all: set[int] = set()
    action_branches: list[dict[str, Any]] = []
    for action in actions:
        action_base = deepcopy(base)
        action_properties = action_base["properties"]
        action_properties["action"] = _const_schema(action)
        consequences, compiled, deferred = _compiled_consequences(
            frozen["$defs"]["candidateEdge"],
            {"operationalRelationID": row["operational_id"], "origin": request["extractionChannel"], "action": action},
        )
        compiled_all.update(compiled)
        deferred_all.update(deferred)
        for name, constraint in consequences.items():
            _apply_simple_consequence(action_properties, name, constraint)
        action_properties["operationalRelationID"] = _const_schema(row["operational_id"])
        action_properties["ontologyRelationID"] = _enum_schema([item["id"] for item in formal])
        action_properties["relationName"] = _enum_schema([item["name"] for item in formal])
        action_properties["action"] = _const_schema(action)
        action_properties["origin"] = _const_schema(request["extractionChannel"])
        action_branches.append(action_base)
    branch = action_branches[0] if len(action_branches) == 1 else {"anyOf": action_branches}
    return branch, {
        "compiledConditionalRuleIndexes": sorted(compiled_all),
        "uncompiledConditionalRuleIndexes": sorted(deferred_all),
        "endpointSignatureTransportConstraint": (
            "not compiled; V7-V8 resolve trusted endpoint classes and frozen "
            "signatures downstream"
        ),
        "relationScopeTransportConstraint": (
            "frozen intra_source|inter_source enum retained; V8 derives the exact "
            "assertion scope from resolved endpoint artifact ownership"
        ),
    }


def _empty_candidate_array() -> dict[str, Any]:
    """Return a strict zero-length array that exposes no unauthorized target fields."""

    return {"type": "array", "items": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "maxItems": 0}


def _prune_definitions(schema: dict[str, Any]) -> None:
    """Remove definitions no longer reachable after request specialization."""

    def refs(value: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(value, Mapping):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                found.add(reference.removeprefix("#/$defs/"))
            for child in value.values():
                found.update(refs(child))
        elif isinstance(value, list):
            for child in value:
                found.update(refs(child))
        return found

    definitions = schema.get("$defs", {})
    root_without_defs = {key: value for key, value in schema.items() if key != "$defs"}
    needed = refs(root_without_defs)
    pending = list(needed)
    while pending:
        name = pending.pop()
        new = refs(definitions.get(name, {})) - needed
        needed.update(new)
        pending.extend(new)
    schema["$defs"] = {name: definitions[name] for name in sorted(needed)}


def derive_request_specialized_schema(
    request: Mapping[str, Any],
    *,
    schema_path: Path = CANDIDATE_SCHEMA_PATH,
    inventory_path: Path = TARGET_INVENTORY_PATH,
) -> dict[str, Any]:
    """Derive and audit a strict transport schema specialized to one request."""

    generic = derive_model_authorable_schema(schema_path)
    frozen = load_json_object(schema_path)
    profile = load_yaml_object(inventory_path)
    targets = _trusted_request_targets(request, profile)
    node_branches: list[dict[str, Any]] = []
    edge_branches: list[dict[str, Any]] = []
    for kind, row in targets:
        branch, _ = (_node_branch(row, request, generic, frozen) if kind == "node" else _edge_branch(row, request, generic, frozen))
        (node_branches if kind == "node" else edge_branches).append(branch)
    schema = deepcopy(generic)
    schema["properties"]["candidateNodes"] = _empty_candidate_array() if not node_branches else {"type": "array", "items": node_branches[0] if len(node_branches) == 1 else {"anyOf": node_branches}}
    schema["properties"]["candidateEdges"] = _empty_candidate_array() if not edge_branches else {"type": "array", "items": edge_branches[0] if len(edge_branches) == 1 else {"anyOf": edge_branches}}
    _prune_definitions(schema)
    jsonschema.Draft202012Validator.check_schema(schema)
    audit = audit_openai_structured_outputs_schema(schema)
    if not audit["compatible"]:
        raise ModelAuthorableSchemaError(f"request-specialized schema is not OpenAI-compatible: {audit['findings']}")
    return schema


def request_specialized_schema_record(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return auditable request-specialization provenance and hashes."""

    generic = derive_model_authorable_schema()
    specialized = derive_request_specialized_schema(request)
    frozen = load_json_object(CANDIDATE_SCHEMA_PATH)
    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    coverage: list[dict[str, Any]] = []
    for kind, row in _trusted_request_targets(request, profile):
        _, item = (_node_branch(row, request, generic, frozen) if kind == "node" else _edge_branch(row, request, generic, frozen))
        coverage.append({"targetID": row["operational_id"], "targetKind": kind, **item})
    record: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "request_specialized_model_authorable_transport_schema",
        "developmentOnly": True,
        "genericModelAuthorableSchemaVersion": MODEL_AUTHORABLE_SCHEMA_VERSION,
        "requestSpecializedSchemaVersion": REQUEST_SPECIALIZED_SCHEMA_VERSION,
        "candidateSchemaSha256": sha256_bytes(CANDIDATE_SCHEMA_PATH.read_bytes()),
        "targetInventorySha256": sha256_bytes(TARGET_INVENTORY_PATH.read_bytes()),
        "requestInputSha256": request.get("requestInputSha256"),
        "eligibleOperationalTargetIDs": list(request.get("eligibleOperationalTargetIDs", [])),
        "conditionalCompilationCoverage": coverage,
        "uncompiledAuthorities": [
            {"constraint": "edge endpoint operational signatures and assertion-level relation scope", "downstreamAuthority": "unchanged M1 V7-V8 validator using resolved endpoint artifact ownership"},
            {"constraint": "literal evidence, offsets, hashes, authorization, lifecycle, and usable output", "downstreamAuthority": "unchanged M1 V1-V12 validator"},
        ],
        "genericSchemaSha256": sha256_bytes(canonical_json(generic)),
        "specializedSchemaSha256": sha256_bytes(canonical_json(specialized)),
        "providerCompatibilityAudit": audit_openai_structured_outputs_schema(specialized),
    }
    record["recordSha256"] = sha256_bytes(canonical_json(record))
    return record
