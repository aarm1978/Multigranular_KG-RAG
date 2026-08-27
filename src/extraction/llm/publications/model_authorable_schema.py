"""Derive the OpenAI model-authorable Publication schema from the frozen envelope.

The frozen candidate schema remains the only semantic contract. This module selects
only its five semantic payload properties, follows their referenced definitions, and
mechanically adapts unsupported JSON Schema composition keywords for OpenAI strict
Structured Outputs. The unchanged M1 validator remains authoritative for every
conditional semantic rule omitted from the provider transport projection.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import jsonschema

from src.extraction.llm.publications.request_builder import (
    CANDIDATE_SCHEMA_PATH,
    canonical_json,
    load_json_object,
    sha256_bytes,
)


MODEL_AUTHORABLE_SCHEMA_VERSION = "publication-model-authorable-0.1.0"
MODEL_AUTHORABLE_KEYS = (
    "candidateNodes",
    "candidateEdges",
    "evidenceSpans",
    "abstentions",
    "deferredRecords",
)
PIPELINE_OWNED_ENVELOPE_KEYS = frozenset({"schemaVersion", "outputStage", "metadata"})
FROZEN_CANDIDATE_SCHEMA_SHA256 = (
    "affd13215dc8023723e7e497f6fce9696cbf8af9bb7c01a85e8aa560033a776d"
)
UNSUPPORTED_COMPOSITION_KEYS = frozenset(
    {"allOf", "not", "if", "then", "else", "dependentRequired", "dependentSchemas"}
)
UNSUPPORTED_PROVIDER_KEYWORDS = frozenset({"uniqueItems", "readOnly"})
OPENAI_SUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "$defs",
        "$ref",
        "additionalProperties",
        "anyOf",
        "const",
        "description",
        "enum",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "items",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "multipleOf",
        "pattern",
        "properties",
        "required",
        "type",
    }
)
OPENAI_MAX_NESTING_DEPTH = 10
OPENAI_MAX_OBJECT_PROPERTIES = 5000
OPENAI_MAX_SCHEMA_STRING_BUDGET = 120000
OPENAI_MAX_ENUM_VALUES = 1000
OPENAI_LARGE_ENUM_THRESHOLD = 250
OPENAI_MAX_LARGE_ENUM_STRING_BUDGET = 15000
PROVIDER_PRIMITIVE_TYPES = frozenset(
    {"string", "number", "boolean", "integer", "null", "object", "array"}
)
STRING_CONSTRAINT_KEYS = frozenset({"pattern", "minLength", "maxLength", "format"})
NUMERIC_CONSTRAINT_KEYS = frozenset(
    {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"}
)
ARRAY_CONSTRAINT_KEYS = frozenset({"minItems", "maxItems"})


class ModelAuthorableSchemaError(ValueError):
    """Report frozen-schema drift or an invalid provider projection."""


def _json_primitive_type(value: Any) -> str:
    """Return the exact JSON primitive type of a Python-decoded scalar value."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    raise ModelAuthorableSchemaError("const/enum contains a non-primitive JSON value")


def _infer_direct_constraint_type(schema: Mapping[str, Any]) -> str | None:
    """Infer one unambiguous provider type from direct primitive constraints."""

    inferred: set[str] = set()
    if "const" in schema:
        inferred.add(_json_primitive_type(schema["const"]))
    if isinstance(schema.get("enum"), list):
        enum = schema["enum"]
        if not enum:
            raise ModelAuthorableSchemaError("cannot infer an explicit type from an empty enum")
        enum_types = {_json_primitive_type(item) for item in enum}
        if len(enum_types) != 1:
            raise ModelAuthorableSchemaError(
                f"cannot infer one explicit type from mixed enum types: {sorted(enum_types)}"
            )
        inferred.update(enum_types)
    if set(schema) & STRING_CONSTRAINT_KEYS:
        inferred.add("string")
    if set(schema) & NUMERIC_CONSTRAINT_KEYS:
        inferred.add("number")
    if set(schema) & ARRAY_CONSTRAINT_KEYS:
        inferred.add("array")
    if len(inferred) > 1:
        raise ModelAuthorableSchemaError(
            f"direct constraints imply incompatible explicit types: {sorted(inferred)}"
        )
    return next(iter(inferred), None)


def _referenced_definition_names(value: Any) -> set[str]:
    """Collect local ``#/$defs`` names referenced anywhere in one schema value."""

    names: set[str] = set()
    if isinstance(value, Mapping):
        reference = value.get("$ref")
        prefix = "#/$defs/"
        if isinstance(reference, str) and reference.startswith(prefix):
            names.add(reference[len(prefix) :])
        for child in value.values():
            names.update(_referenced_definition_names(child))
    elif isinstance(value, list):
        for child in value:
            names.update(_referenced_definition_names(child))
    return names


def _definition_closure(
    properties: Mapping[str, Any], definitions: Mapping[str, Any]
) -> list[str]:
    """Resolve the deterministic transitive definition closure for semantic fields."""

    pending = sorted(_referenced_definition_names(properties))
    resolved: set[str] = set()
    while pending:
        name = pending.pop(0)
        if name in resolved:
            continue
        if name not in definitions:
            raise ModelAuthorableSchemaError(f"missing frozen schema definition: {name}")
        resolved.add(name)
        pending.extend(
            sorted(_referenced_definition_names(definitions[name]) - resolved - set(pending))
        )
    return sorted(resolved)


def _resolved_schema(branch: Mapping[str, Any], definitions: Mapping[str, Any]) -> Mapping[str, Any]:
    """Resolve one local definition reference for disjointness inspection."""

    reference = branch.get("$ref")
    prefix = "#/$defs/"
    if isinstance(reference, str) and reference.startswith(prefix):
        name = reference[len(prefix) :]
        resolved = definitions.get(name)
        if not isinstance(resolved, Mapping):
            raise ModelAuthorableSchemaError(f"unresolved oneOf definition: {name}")
        return resolved
    return branch


def _type_set(branch: Mapping[str, Any], definitions: Mapping[str, Any]) -> set[str]:
    """Return explicit JSON types for one frozen alternative when determinable."""

    resolved = _resolved_schema(branch, definitions)
    value = resolved.get("type")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value)
    enum = resolved.get("enum")
    if isinstance(enum, list) and enum:
        enum_types: set[str] = set()
        for item in enum:
            if item is None:
                enum_types.add("null")
            elif isinstance(item, bool):
                enum_types.add("boolean")
            elif isinstance(item, str):
                enum_types.add("string")
            elif isinstance(item, int):
                enum_types.update({"integer", "number"})
            elif isinstance(item, float):
                enum_types.add("number")
            else:
                return set()
        return enum_types
    constant = resolved.get("const")
    if constant is None and "const" in resolved:
        return {"null"}
    if isinstance(constant, str):
        return {"string"}
    if isinstance(constant, bool):
        return {"boolean"}
    if isinstance(constant, int):
        return {"integer", "number"}
    if isinstance(constant, float):
        return {"number"}
    return set()


def _discriminator_values(branch: Mapping[str, Any]) -> dict[str, set[Any]]:
    """Return required object discriminator values expressed as const or enum."""

    properties = branch.get("properties", {})
    required = set(branch.get("required", []))
    values: dict[str, set[Any]] = {}
    if not isinstance(properties, Mapping):
        return values
    for name, definition in properties.items():
        if name not in required or not isinstance(definition, Mapping):
            continue
        if "const" in definition:
            values[str(name)] = {definition["const"]}
        elif isinstance(definition.get("enum"), list):
            values[str(name)] = set(definition["enum"])
    return values


def _alternatives_are_disjoint(
    left: Mapping[str, Any], right: Mapping[str, Any], definitions: Mapping[str, Any]
) -> bool:
    """Prove two retained frozen alternatives cannot validate the same instance."""

    left_resolved = _resolved_schema(left, definitions)
    right_resolved = _resolved_schema(right, definitions)
    left_types = _type_set(left_resolved, definitions)
    right_types = _type_set(right_resolved, definitions)
    if left_types and right_types and left_types.isdisjoint(right_types):
        return True
    left_discriminators = _discriminator_values(left_resolved)
    right_discriminators = _discriminator_values(right_resolved)
    for name in set(left_discriminators) & set(right_discriminators):
        if left_discriminators[name].isdisjoint(right_discriminators[name]):
            return True
    return False


def _assert_one_of_conversions_safe(value: Any, definitions: Mapping[str, Any]) -> None:
    """Fail unless every retained oneOf has pairwise-disjoint alternatives."""

    if isinstance(value, Mapping):
        alternatives = value.get("oneOf")
        if isinstance(alternatives, list):
            if not all(isinstance(branch, Mapping) for branch in alternatives):
                raise ModelAuthorableSchemaError("oneOf contains a non-schema alternative")
            for left_index, left in enumerate(alternatives):
                for right in alternatives[left_index + 1 :]:
                    if not _alternatives_are_disjoint(left, right, definitions):
                        raise ModelAuthorableSchemaError(
                            "oneOf to anyOf conversion is not provably semantics-preserving"
                        )
        for child in value.values():
            _assert_one_of_conversions_safe(child, definitions)
    elif isinstance(value, list):
        for child in value:
            _assert_one_of_conversions_safe(child, definitions)


def _adapt_for_openai_strict(value: Any) -> Any:
    """Mechanically adapt a frozen schema fragment to OpenAI's strict subset."""

    if isinstance(value, list):
        return [_adapt_for_openai_strict(child) for child in value]
    if not isinstance(value, Mapping):
        return deepcopy(value)
    if "$ref" in value:
        return {"$ref": deepcopy(value["$ref"])}
    adapted: dict[str, Any] = {}
    for key, child in value.items():
        if key in UNSUPPORTED_COMPOSITION_KEYS or key in UNSUPPORTED_PROVIDER_KEYWORDS:
            continue
        destination = "anyOf" if key == "oneOf" else key
        adapted[destination] = _adapt_for_openai_strict(child)
    properties = adapted.get("properties")
    if adapted.get("type") == "object" and isinstance(properties, Mapping):
        adapted["required"] = list(properties)
        adapted["additionalProperties"] = False
    if "type" not in adapted:
        inferred_type = _infer_direct_constraint_type(adapted)
        if inferred_type is not None:
            adapted["type"] = inferred_type
    return adapted


def _ref_inventory(value: Any) -> dict[str, Any]:
    """Inventory local references, sibling keywords, and unresolved targets."""

    root = value if isinstance(value, Mapping) else {}
    definitions = root.get("$defs", {}) if isinstance(root, Mapping) else {}
    ref_paths: list[str] = []
    sibling_paths: list[str] = []
    sibling_keywords: dict[str, int] = {}
    unresolved: list[dict[str, str]] = []

    def walk(schema: Any, pointer: str) -> None:
        """Inspect every schema-valued position without resolving recursively."""

        if not isinstance(schema, Mapping):
            return
        path = pointer or "/"
        if "$ref" in schema:
            ref_paths.append(path)
            siblings = sorted(set(schema) - {"$ref"})
            if siblings:
                sibling_paths.append(path)
                for keyword in siblings:
                    sibling_keywords[keyword] = sibling_keywords.get(keyword, 0) + 1
            reference = schema["$ref"]
            prefix = "#/$defs/"
            if reference == "#":
                pass
            elif isinstance(reference, str) and reference.startswith(prefix):
                target = reference[len(prefix) :]
                if target not in definitions:
                    unresolved.append({"path": path, "reference": reference})
            else:
                unresolved.append({"path": path, "reference": str(reference)})
            return
        for name, child in schema.get("properties", {}).items():
            walk(child, f"{pointer}/properties/{name}")
        if isinstance(schema.get("items"), Mapping):
            walk(schema["items"], f"{pointer}/items")
        for composition in ("anyOf", "oneOf", "allOf"):
            for index, branch in enumerate(schema.get(composition, [])):
                walk(branch, f"{pointer}/{composition}/{index}")
        for name, child in schema.get("$defs", {}).items():
            walk(child, f"{pointer}/$defs/{name}")

    walk(value, "")
    return {
        "totalRefNodes": len(ref_paths),
        "pureRefNodes": len(ref_paths) - len(sibling_paths),
        "refSiblingNodes": len(sibling_paths),
        "refSiblingPaths": sibling_paths,
        "refSiblingKeywords": dict(sorted(sibling_keywords.items())),
        "unresolvedRefTargets": len(unresolved),
        "unresolvedReferences": unresolved,
    }


def _missing_explicit_type_inventory(value: Any) -> dict[str, list[str]]:
    """Enumerate path-specific direct constraints lacking explicit provider types."""

    inventory = {
        "constSchemasLackingExplicitType": [],
        "enumSchemasLackingExplicitType": [],
        "directlyConstrainedSchemasLackingCompatibleType": [],
    }

    def walk(schema: Any, pointer: str) -> None:
        """Inspect every schema-valued position without following references."""

        if not isinstance(schema, Mapping):
            return
        schema_types = schema.get("type")
        explicit_types = (
            {schema_types}
            if isinstance(schema_types, str)
            else set(schema_types)
            if isinstance(schema_types, list)
            else set()
        )
        path = pointer or "/"
        if "const" in schema and not explicit_types:
            inventory["constSchemasLackingExplicitType"].append(path)
        if "enum" in schema and not explicit_types:
            inventory["enumSchemasLackingExplicitType"].append(path)
        implied_types: set[str] = set()
        if "const" in schema:
            try:
                implied_types.add(_json_primitive_type(schema["const"]))
            except ModelAuthorableSchemaError:
                implied_types.add("invalid")
        if isinstance(schema.get("enum"), list):
            try:
                implied_types.update(_json_primitive_type(item) for item in schema["enum"])
            except ModelAuthorableSchemaError:
                implied_types.add("invalid")
        if set(schema) & STRING_CONSTRAINT_KEYS:
            implied_types.add("string")
        if set(schema) & NUMERIC_CONSTRAINT_KEYS:
            implied_types.add("number")
        if set(schema) & ARRAY_CONSTRAINT_KEYS:
            implied_types.add("array")
        compatible = bool(explicit_types)
        for implied in implied_types:
            if implied == "integer":
                compatible = compatible and bool(explicit_types & {"integer", "number"})
            elif implied == "number":
                compatible = compatible and bool(explicit_types & {"integer", "number"})
            else:
                compatible = compatible and implied in explicit_types
        if implied_types and not compatible:
            inventory["directlyConstrainedSchemasLackingCompatibleType"].append(path)
        for name, child in schema.get("properties", {}).items():
            walk(child, f"{pointer}/properties/{name}")
        if isinstance(schema.get("items"), Mapping):
            walk(schema["items"], f"{pointer}/items")
        for composition in ("anyOf", "oneOf", "allOf"):
            for index, branch in enumerate(schema.get(composition, [])):
                walk(branch, f"{pointer}/{composition}/{index}")
        for name, child in schema.get("$defs", {}).items():
            walk(child, f"{pointer}/$defs/{name}")

    walk(value, "")
    return inventory


def _explicit_type_adaptation_counts(value: Any) -> dict[str, int]:
    """Count deterministic explicit-type additions required by a frozen projection."""

    inventory = _missing_explicit_type_inventory(value)
    return {
        "constSchemasGivenExplicitType": len(
            inventory["constSchemasLackingExplicitType"]
        ),
        "enumSchemasGivenExplicitType": len(
            inventory["enumSchemasLackingExplicitType"]
        ),
        "otherConstraintSchemasGivenExplicitType": len(
            set(inventory["directlyConstrainedSchemasLackingCompatibleType"])
            - set(inventory["constSchemasLackingExplicitType"])
            - set(inventory["enumSchemasLackingExplicitType"])
        ),
    }


def _schema_keyword_inventory(value: Any) -> set[str]:
    """Enumerate actual JSON Schema keywords, excluding property/definition names."""

    keywords: set[str] = set()
    if not isinstance(value, Mapping):
        return keywords
    for key, child in value.items():
        keywords.add(str(key))
        if key in {"properties", "$defs"} and isinstance(child, Mapping):
            for schema in child.values():
                keywords.update(_schema_keyword_inventory(schema))
        elif isinstance(child, Mapping):
            keywords.update(_schema_keyword_inventory(child))
        elif isinstance(child, list) and key not in {"required", "enum", "type"}:
            for schema in child:
                keywords.update(_schema_keyword_inventory(schema))
    return keywords


def _schema_metrics(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Compute OpenAI depth, property, string-budget, and enum-limit measures."""

    definitions = schema.get("$defs", {})

    def resolve(value: Mapping[str, Any]) -> Mapping[str, Any]:
        """Resolve a local definition reference for depth calculation."""

        reference = value.get("$ref")
        prefix = "#/$defs/"
        if isinstance(reference, str) and reference.startswith(prefix):
            resolved = definitions.get(reference[len(prefix) :])
            return resolved if isinstance(resolved, Mapping) else value
        return value

    def depth(value: Any, current: int, seen: frozenset[str]) -> int:
        """Return maximum object/array nesting depth through local references."""

        if not isinstance(value, Mapping):
            return current
        reference = value.get("$ref")
        if isinstance(reference, str):
            if reference in seen:
                return current
            return depth(resolve(value), current, seen | {reference})
        schema_type = value.get("type")
        next_depth = current + (
            1 if isinstance(schema_type, str) and schema_type in {"object", "array"} else 0
        )
        candidates = [next_depth]
        properties = value.get("properties")
        if isinstance(properties, Mapping):
            candidates.extend(depth(child, next_depth, seen) for child in properties.values())
        if isinstance(value.get("items"), Mapping):
            candidates.append(depth(value["items"], next_depth, seen))
        for branch in value.get("anyOf", []):
            candidates.append(depth(branch, next_depth, seen))
        return max(candidates)

    property_count = 0
    string_budget = 0
    enum_count = 0
    largest_enum_string_budget = 0

    def accumulate(value: Any) -> None:
        """Accumulate provider-defined counts from each literal schema occurrence."""

        nonlocal property_count, string_budget, enum_count, largest_enum_string_budget
        if not isinstance(value, Mapping):
            return
        properties = value.get("properties")
        if isinstance(properties, Mapping):
            property_count += len(properties)
            string_budget += sum(len(str(name)) for name in properties)
            for child in properties.values():
                accumulate(child)
        definitions_value = value.get("$defs")
        if isinstance(definitions_value, Mapping):
            string_budget += sum(len(str(name)) for name in definitions_value)
            for child in definitions_value.values():
                accumulate(child)
        enum = value.get("enum")
        if isinstance(enum, list):
            enum_count += len(enum)
            enum_string_budget = sum(len(item) for item in enum if isinstance(item, str))
            string_budget += enum_string_budget
            largest_enum_string_budget = max(largest_enum_string_budget, enum_string_budget)
        if "const" in value and isinstance(value["const"], str):
            string_budget += len(value["const"])
        if isinstance(value.get("items"), Mapping):
            accumulate(value["items"])
        for branch in value.get("anyOf", []):
            accumulate(branch)

    accumulate(schema)
    return {
        "maxNestingDepth": depth(schema, 0, frozenset()),
        "totalObjectPropertyCount": property_count,
        "aggregateSchemaStringBudget": string_budget,
        "totalEnumValueCount": enum_count,
        "largestEnumStringBudget": largest_enum_string_budget,
    }


def audit_openai_structured_outputs_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Audit an actual derived schema against OpenAI's documented strict subset."""

    findings: list[str] = []
    definitions = schema.get("$defs", {})
    keywords = sorted(_schema_keyword_inventory(schema))
    unknown = sorted(set(keywords) - OPENAI_SUPPORTED_SCHEMA_KEYWORDS)
    if unknown:
        findings.append(f"unsupported keywords: {unknown}")
    if schema.get("type") != "object":
        findings.append("root must be an object")
    if "anyOf" in schema:
        findings.append("root must not contain anyOf")

    any_of_branch_count = 0
    invalid_any_of_branches: list[str] = []

    def inspect(value: Any, pointer: str) -> None:
        """Check required/closed objects and recursively inspect every anyOf branch."""

        nonlocal any_of_branch_count
        if not isinstance(value, Mapping):
            return
        path = pointer or "/"
        if "$ref" in value:
            if set(value) != {"$ref"}:
                findings.append(
                    f"{path} $ref must be the only keyword; siblings: "
                    f"{sorted(set(value) - {'$ref'})}"
                )
            reference = value["$ref"]
            prefix = "#/$defs/"
            if reference == "#":
                return
            if not isinstance(reference, str) or not reference.startswith(prefix):
                findings.append(f"{path} has unsupported local $ref: {reference}")
            elif reference[len(prefix) :] not in definitions:
                findings.append(f"{path} has unresolved $ref: {reference}")
            return
        schema_type = value.get("type")
        explicit_types = (
            {schema_type}
            if isinstance(schema_type, str)
            else set(schema_type)
            if isinstance(schema_type, list)
            else set()
        )
        invalid_types = explicit_types - PROVIDER_PRIMITIVE_TYPES
        if invalid_types:
            findings.append(f"{path} has invalid explicit types: {sorted(invalid_types)}")
        direct_inventory = _missing_explicit_type_inventory(value)
        direct_path = "/"
        if direct_path in direct_inventory["constSchemasLackingExplicitType"]:
            findings.append(f"{path} const requires an explicit type")
        if direct_path in direct_inventory["enumSchemasLackingExplicitType"]:
            findings.append(f"{path} enum requires an explicit type")
        if direct_path in direct_inventory[
            "directlyConstrainedSchemasLackingCompatibleType"
        ]:
            findings.append(f"{path} direct primitive constraints lack a compatible type")
        properties = value.get("properties")
        if isinstance(properties, Mapping):
            if "object" not in explicit_types:
                findings.append(f"{path} properties require explicit object type")
            if value.get("additionalProperties") is not False:
                findings.append(f"{path} object is not closed")
            property_names = set(properties or {})
            if set(value.get("required", [])) != property_names:
                findings.append(f"{path} object properties are not all required")
        if isinstance(value.get("items"), Mapping) and "array" not in explicit_types:
            findings.append(f"{path} items require explicit array type")
        for name, child in (properties or {}).items():
            inspect(child, f"{pointer}/properties/{name}")
        if isinstance(value.get("items"), Mapping):
            inspect(value["items"], f"{pointer}/items")
        for index, branch in enumerate(value.get("anyOf", [])):
            any_of_branch_count += 1
            branch_path = f"{pointer}/anyOf/{index}"
            if not isinstance(branch, Mapping):
                findings.append(f"{branch_path} is not a schema")
                invalid_any_of_branches.append(branch_path)
            else:
                finding_count = len(findings)
                inspect(branch, branch_path)
                if len(findings) != finding_count:
                    invalid_any_of_branches.append(branch_path)
        for name, child in value.get("$defs", {}).items():
            inspect(child, f"{pointer}/$defs/{name}")

    inspect(schema, "")
    metrics = _schema_metrics(schema)
    if metrics["maxNestingDepth"] > OPENAI_MAX_NESTING_DEPTH:
        findings.append("nesting depth exceeds provider limit")
    if metrics["totalObjectPropertyCount"] > OPENAI_MAX_OBJECT_PROPERTIES:
        findings.append("object property count exceeds provider limit")
    if metrics["aggregateSchemaStringBudget"] > OPENAI_MAX_SCHEMA_STRING_BUDGET:
        findings.append("schema string budget exceeds provider limit")
    if metrics["totalEnumValueCount"] > OPENAI_MAX_ENUM_VALUES:
        findings.append("enum value count exceeds provider limit")
    if (
        metrics["totalEnumValueCount"] > OPENAI_LARGE_ENUM_THRESHOLD
        and metrics["largestEnumStringBudget"] > OPENAI_MAX_LARGE_ENUM_STRING_BUDGET
    ):
        findings.append("large enum string budget exceeds provider limit")
    const_schema_count = 0
    enum_schema_count = 0

    def count_direct_constraints(value: Any) -> None:
        """Count const and enum schemas in every actual schema-valued position."""

        nonlocal const_schema_count, enum_schema_count
        if not isinstance(value, Mapping):
            return
        const_schema_count += int("const" in value)
        enum_schema_count += int("enum" in value)
        for child in value.get("properties", {}).values():
            count_direct_constraints(child)
        if isinstance(value.get("items"), Mapping):
            count_direct_constraints(value["items"])
        for branch in value.get("anyOf", []):
            count_direct_constraints(branch)
        for child in value.get("$defs", {}).values():
            count_direct_constraints(child)

    count_direct_constraints(schema)
    type_inventory = _missing_explicit_type_inventory(schema)
    ref_inventory = _ref_inventory(schema)
    return {
        "compatible": not findings,
        "keywordInventory": keywords,
        "findings": findings,
        "metrics": metrics,
        "explicitTypeAudit": {
            "constSchemaCount": const_schema_count,
            "enumSchemaCount": enum_schema_count,
            "constSchemasLackingExplicitType": len(
                type_inventory["constSchemasLackingExplicitType"]
            ),
            "enumSchemasLackingExplicitType": len(
                type_inventory["enumSchemasLackingExplicitType"]
            ),
            "directlyConstrainedSchemasLackingCompatibleType": len(
                type_inventory["directlyConstrainedSchemasLackingCompatibleType"]
            ),
            "anyOfBranchCount": any_of_branch_count,
            "invalidAnyOfBranchCount": len(set(invalid_any_of_branches)),
            "invalidAnyOfBranchPaths": sorted(set(invalid_any_of_branches)),
        },
        "refAudit": ref_inventory,
        "limits": {
            "maxNestingDepth": OPENAI_MAX_NESTING_DEPTH,
            "maxObjectProperties": OPENAI_MAX_OBJECT_PROPERTIES,
            "maxSchemaStringBudget": OPENAI_MAX_SCHEMA_STRING_BUDGET,
            "maxEnumValues": OPENAI_MAX_ENUM_VALUES,
            "largeEnumThreshold": OPENAI_LARGE_ENUM_THRESHOLD,
            "maxLargeEnumStringBudget": OPENAI_MAX_LARGE_ENUM_STRING_BUDGET,
        },
    }


def derive_model_authorable_schema(
    schema_path: Path = CANDIDATE_SCHEMA_PATH,
    *,
    enforce_frozen_hash: bool = True,
) -> dict[str, Any]:
    """Derive the strict provider transport schema from the frozen candidate schema."""

    source_bytes = schema_path.read_bytes()
    source_hash = sha256_bytes(source_bytes)
    if enforce_frozen_hash and source_hash != FROZEN_CANDIDATE_SCHEMA_SHA256:
        raise ModelAuthorableSchemaError(
            "frozen Publication candidate schema hash changed; review derivation before use"
        )
    frozen = load_json_object(schema_path)
    frozen_properties = frozen.get("properties", {})
    missing = [key for key in MODEL_AUTHORABLE_KEYS if key not in frozen_properties]
    if missing:
        raise ModelAuthorableSchemaError(f"frozen semantic properties are missing: {missing}")
    selected_properties = {
        key: deepcopy(frozen_properties[key]) for key in MODEL_AUTHORABLE_KEYS
    }
    definitions = frozen.get("$defs", {})
    closure = _definition_closure(selected_properties, definitions)
    derived = {
        "type": "object",
        "additionalProperties": False,
        "properties": selected_properties,
        "required": list(MODEL_AUTHORABLE_KEYS),
        "$defs": {name: deepcopy(definitions[name]) for name in closure},
    }
    _assert_one_of_conversions_safe(derived, definitions)
    strict_schema = _adapt_for_openai_strict(derived)
    jsonschema.Draft202012Validator.check_schema(strict_schema)
    if set(strict_schema["properties"]) & PIPELINE_OWNED_ENVELOPE_KEYS:
        raise ModelAuthorableSchemaError("provider schema contains pipeline-owned fields")
    compatibility = audit_openai_structured_outputs_schema(strict_schema)
    if not compatibility["compatible"]:
        raise ModelAuthorableSchemaError(
            f"derived schema is not OpenAI-compatible: {compatibility['findings']}"
        )
    return strict_schema


def model_authorable_schema_record(
    schema_path: Path = CANDIDATE_SCHEMA_PATH,
) -> dict[str, Any]:
    """Return deterministic source/derived hashes and per-definition provenance."""

    frozen = load_json_object(schema_path)
    derived = derive_model_authorable_schema(schema_path)
    names = sorted(derived["$defs"])
    selected_properties = {
        key: deepcopy(frozen["properties"][key]) for key in MODEL_AUTHORABLE_KEYS
    }
    frozen_projection = {
        "type": "object",
        "additionalProperties": False,
        "properties": selected_properties,
        "required": list(MODEL_AUTHORABLE_KEYS),
        "$defs": {name: deepcopy(frozen["$defs"][name]) for name in names},
    }
    before_ref_inventory = _ref_inventory(frozen_projection)
    after_ref_inventory = _ref_inventory(derived)
    record: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "derived_model_authorable_transport_schema",
        "developmentOnly": True,
        "semanticAuthority": str(schema_path),
        "semanticAuthoritySha256": sha256_bytes(schema_path.read_bytes()),
        "modelAuthorableSchemaVersion": MODEL_AUTHORABLE_SCHEMA_VERSION,
        "modelAuthorableKeys": list(MODEL_AUTHORABLE_KEYS),
        "excludedPipelineOwnedEnvelopeKeys": sorted(PIPELINE_OWNED_ENVELOPE_KEYS),
        "transportAdaptations": [
            {
                "frozenKeyword": "oneOf",
                "providerTransportAction": "converted to anyOf after pairwise-disjointness proof",
                "reason": "OpenAI supports anyOf but does not list oneOf",
                "downstreamAuthority": "frozen candidate schema and unchanged M1 V1-V12 validator",
            },
            {
                "frozenKeyword": "allOf / if / then / else / not",
                "providerTransportAction": "omitted from transport projection",
                "reason": "unsupported OpenAI composition keywords",
                "downstreamAuthority": "unchanged M1 V1-V12 validator",
            },
            {
                "frozenKeyword": "uniqueItems",
                "providerTransportAction": "omitted from transport projection",
                "reason": "not listed among supported OpenAI array constraints",
                "downstreamAuthority": "frozen candidate schema and unchanged M1 validation",
            },
            {
                "frozenKeyword": "readOnly",
                "providerTransportAction": "annotation omitted from transport projection",
                "reason": "not a supported OpenAI generation constraint",
                "downstreamAuthority": "pipeline evidence-hash ownership and unchanged M1 validation",
            },
            {
                "frozenKeyword": "required",
                "providerTransportAction": "expanded to every retained object property",
                "reason": "OpenAI strict mode requires every object property",
                "downstreamAuthority": "frozen candidate schema and unchanged M1 validation",
            },
            {
                "frozenKeyword": "const / enum / direct primitive constraints",
                "providerTransportAction": (
                    "explicit primitive type added only where deterministically inferable"
                ),
                "reason": (
                    "OpenAI requires directly constrained primitive schemas to carry type"
                ),
                "semanticEffect": "value domain unchanged for proven primitive types",
                "downstreamAuthority": "frozen candidate schema and unchanged M1 validator",
            },
            {
                "frozenKeyword": "$ref with sibling keywords",
                "providerTransportAction": "$ref retained as the sole schema-node keyword",
                "reason": "OpenAI rejects sibling keywords on $ref nodes",
                "semanticEffect": (
                    "referenced constraint unchanged; local annotations omitted from transport"
                ),
                "downstreamAuthority": "frozen candidate schema and unchanged M1 validator",
            },
        ],
        "refSiblingNodesDetectedBeforeAdaptation": before_ref_inventory[
            "refSiblingNodes"
        ],
        "refSiblingNodesAfterAdaptation": after_ref_inventory["refSiblingNodes"],
        "refSiblingKeywordsRemoved": before_ref_inventory["refSiblingKeywords"],
        "refSiblingPathsAdapted": before_ref_inventory["refSiblingPaths"],
        "refInventoryBeforeAdaptation": before_ref_inventory,
        "refInventoryAfterAdaptation": after_ref_inventory,
        "explicitTypeAdaptationCounts": _explicit_type_adaptation_counts(
            frozen_projection
        ),
        "providerCompatibilityAudit": audit_openai_structured_outputs_schema(derived),
        "sourceDefinitionSha256": {
            name: sha256_bytes(canonical_json(frozen["$defs"][name])) for name in names
        },
        "derivedDefinitionSha256": {
            name: sha256_bytes(canonical_json(derived["$defs"][name])) for name in names
        },
        "derivedSchemaSha256": sha256_bytes(canonical_json(derived)),
    }
    record["recordSha256"] = sha256_bytes(canonical_json(record))
    return record


def validate_model_authorable_payload(
    payload: Any, schema: Mapping[str, Any] | None = None
) -> list[str]:
    """Return deterministic local validation messages for a provider payload."""

    active_schema = dict(schema) if schema is not None else derive_model_authorable_schema()
    validator = jsonschema.Draft202012Validator(active_schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    return [error.message for error in errors]
