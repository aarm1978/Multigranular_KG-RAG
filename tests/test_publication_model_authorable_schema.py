"""Tests for deterministic derivation of the Publication model-authorable schema."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.model_authorable_schema import (  # noqa: E402
    FROZEN_CANDIDATE_SCHEMA_SHA256,
    MODEL_AUTHORABLE_KEYS,
    OPENAI_MAX_ENUM_VALUES,
    OPENAI_MAX_NESTING_DEPTH,
    OPENAI_MAX_OBJECT_PROPERTIES,
    OPENAI_MAX_SCHEMA_STRING_BUDGET,
    OPENAI_SUPPORTED_SCHEMA_KEYWORDS,
    PIPELINE_OWNED_ENVELOPE_KEYS,
    UNSUPPORTED_COMPOSITION_KEYS,
    ModelAuthorableSchemaError,
    _adapt_for_openai_strict,
    _missing_explicit_type_inventory,
    _ref_inventory,
    _schema_keyword_inventory,
    audit_openai_structured_outputs_schema,
    derive_model_authorable_schema,
    model_authorable_schema_record,
    validate_model_authorable_payload,
)
from src.extraction.llm.publications.request_builder import (  # noqa: E402
    CANDIDATE_SCHEMA_PATH,
    canonical_json,
    sha256_bytes,
)


VALID_FIXTURE = (
    PROJECT_ROOT / "data/curation/papers/m1/publication_m1_recorded_raw_response.json"
)
M2A_FIXTURE = (
    PROJECT_ROOT / "data/curation/papers/m2/publication_m2a_exact_raw_model_output.json"
)
ATTEMPT2_SCHEMA = (
    PROJECT_ROOT
    / "data/curation/papers/m2/b1/publication_m2b1_model_authorable_schema.json"
)
ATTEMPT3_SCHEMA = (
    PROJECT_ROOT
    / "data/curation/papers/m2/b1/publication_m2b1_attempt3_model_authorable_schema.json"
)


class ModelAuthorableSchemaTests(unittest.TestCase):
    """Prove the provider schema remains a strict projection of frozen M1."""

    def test_derivation_is_deterministic(self) -> None:
        """Repeated derivation produces byte-identical canonical JSON and records."""

        self.assertEqual(
            canonical_json(derive_model_authorable_schema()),
            canonical_json(derive_model_authorable_schema()),
        )
        self.assertEqual(
            canonical_json(model_authorable_schema_record()),
            canonical_json(model_authorable_schema_record()),
        )

    def test_pipeline_owned_envelope_fields_are_absent(self) -> None:
        """Only the five frozen semantic arrays occur at the provider root."""

        schema = derive_model_authorable_schema()
        self.assertEqual(tuple(schema["properties"]), MODEL_AUTHORABLE_KEYS)
        self.assertFalse(set(schema["properties"]) & PIPELINE_OWNED_ENVELOPE_KEYS)
        encoded = canonical_json(schema).decode("utf-8")
        for prohibited in (
            '"schemaVersion"',
            '"outputStage"',
            '"metadata"',
            '"requestInputSha256"',
            '"provider"',
            '"validationResultsHash"',
        ):
            self.assertNotIn(prohibited, encoded)

    def test_definitions_are_mechanical_adaptations_of_frozen_definitions(self) -> None:
        """Every retained definition equals the documented mechanical projection."""

        frozen = json.loads(CANDIDATE_SCHEMA_PATH.read_text(encoding="utf-8"))
        derived = derive_model_authorable_schema()
        for name, definition in derived["$defs"].items():
            with self.subTest(definition=name):
                self.assertEqual(
                    definition, _adapt_for_openai_strict(frozen["$defs"][name])
                )

    def test_actual_keyword_vocabulary_is_explicitly_supported(self) -> None:
        """Every keyword in the actual projection belongs to the allowed vocabulary."""

        schema = derive_model_authorable_schema()
        inventory = _schema_keyword_inventory(schema)
        audit = audit_openai_structured_outputs_schema(schema)
        self.assertEqual(sorted(inventory), audit["keywordInventory"])
        self.assertFalse(inventory - OPENAI_SUPPORTED_SCHEMA_KEYWORDS)
        self.assertTrue(audit["compatible"], audit["findings"])

    def test_unsupported_constraints_are_transport_only_omissions(self) -> None:
        """Frozen unique/composition constraints never leak into provider transport."""

        frozen_text = CANDIDATE_SCHEMA_PATH.read_text(encoding="utf-8")
        schema = derive_model_authorable_schema()
        inventory = _schema_keyword_inventory(schema)
        self.assertIn('"uniqueItems"', frozen_text)
        self.assertNotIn("uniqueItems", inventory)
        self.assertFalse(inventory & UNSUPPORTED_COMPOSITION_KEYS)
        record = model_authorable_schema_record()
        adaptations = {row["frozenKeyword"]: row for row in record["transportAdaptations"]}
        self.assertIn("uniqueItems", adaptations)
        self.assertIn("oneOf", adaptations)

    def test_every_actual_object_is_closed_and_all_properties_are_required(self) -> None:
        """The recursive provider audit enforces OpenAI's object requirements."""

        schema = derive_model_authorable_schema()

        def inspect(value: object) -> None:
            """Recursively inspect all schema-valued positions."""

            if not isinstance(value, dict):
                return
            properties = value.get("properties")
            if value.get("type") == "object" or isinstance(properties, dict):
                self.assertIs(value.get("additionalProperties"), False)
                self.assertEqual(set(value.get("required", [])), set(properties or {}))
            for child in (properties or {}).values():
                inspect(child)
            if isinstance(value.get("items"), dict):
                inspect(value["items"])
            for branch in value.get("anyOf", []):
                inspect(branch)
            for child in value.get("$defs", {}).values():
                inspect(child)

        inspect(schema)

    def test_actual_schema_is_within_documented_provider_limits(self) -> None:
        """Depth, property, string, and enum measures pass the provider limits."""

        audit = audit_openai_structured_outputs_schema(derive_model_authorable_schema())
        metrics = audit["metrics"]
        self.assertLessEqual(metrics["maxNestingDepth"], OPENAI_MAX_NESTING_DEPTH)
        self.assertLessEqual(
            metrics["totalObjectPropertyCount"], OPENAI_MAX_OBJECT_PROPERTIES
        )
        self.assertLessEqual(
            metrics["aggregateSchemaStringBudget"], OPENAI_MAX_SCHEMA_STRING_BUDGET
        )
        self.assertLessEqual(metrics["totalEnumValueCount"], OPENAI_MAX_ENUM_VALUES)

    def test_attempt2_schema_fails_explicit_type_audit_at_all_known_paths(self) -> None:
        """The new local audit rejects the exact schema rejected by attempt 2."""

        schema = json.loads(ATTEMPT2_SCHEMA.read_text(encoding="utf-8"))
        audit = audit_openai_structured_outputs_schema(schema)
        inventory = _missing_explicit_type_inventory(schema)
        self.assertFalse(audit["compatible"])
        self.assertTrue(inventory["constSchemasLackingExplicitType"])
        self.assertTrue(inventory["enumSchemasLackingExplicitType"])
        self.assertEqual(
            len(inventory["directlyConstrainedSchemasLackingCompatibleType"]),
            len(inventory["constSchemasLackingExplicitType"])
            + len(inventory["enumSchemasLackingExplicitType"]),
        )
        self.assertIn(
            "/$defs/candidateAttribute/anyOf/0/properties/attributeName",
            inventory["constSchemasLackingExplicitType"],
        )

    def test_corrected_schema_has_complete_compatible_explicit_types(self) -> None:
        """No direct const, enum, or primitive constraint lacks a compatible type."""

        schema = derive_model_authorable_schema()
        inventory = _missing_explicit_type_inventory(schema)
        self.assertEqual(inventory["constSchemasLackingExplicitType"], [])
        self.assertEqual(inventory["enumSchemasLackingExplicitType"], [])
        self.assertEqual(
            inventory["directlyConstrainedSchemasLackingCompatibleType"], []
        )
        explicit = audit_openai_structured_outputs_schema(schema)["explicitTypeAudit"]
        self.assertEqual(explicit["constSchemasLackingExplicitType"], 0)
        self.assertEqual(explicit["enumSchemasLackingExplicitType"], 0)
        self.assertEqual(
            explicit["directlyConstrainedSchemasLackingCompatibleType"], 0
        )
        self.assertEqual(explicit["invalidAnyOfBranchCount"], 0)

    def test_const_and_enum_only_fragments_receive_proven_types(self) -> None:
        """Synthetic frozen fragments exercise the complete defect class."""

        self.assertEqual(
            _adapt_for_openai_strict({"const": "value"}),
            {"const": "value", "type": "string"},
        )
        self.assertEqual(
            _adapt_for_openai_strict({"enum": ["A", "B"]}),
            {"enum": ["A", "B"], "type": "string"},
        )
        with self.assertRaisesRegex(ModelAuthorableSchemaError, "mixed enum types"):
            _adapt_for_openai_strict({"enum": ["A", 1]})

    def test_type_specific_constraints_require_compatible_explicit_types(self) -> None:
        """A constraint with a missing or incompatible primitive type fails locally."""

        bad_schema = {
            "type": "object",
            "properties": {"value": {"type": "number", "pattern": "^x$"}},
            "required": ["value"],
            "additionalProperties": False,
        }
        audit = audit_openai_structured_outputs_schema(bad_schema)
        self.assertFalse(audit["compatible"])
        self.assertTrue(
            any("compatible type" in finding for finding in audit["findings"])
        )

    def test_every_nested_anyof_branch_is_audited_independently(self) -> None:
        """One invalid nested branch is reported by its deterministic branch path."""

        bad_schema = {
            "type": "object",
            "properties": {
                "value": {
                    "anyOf": [
                        {"const": "value"},
                        {"type": "null"},
                    ]
                }
            },
            "required": ["value"],
            "additionalProperties": False,
        }
        audit = audit_openai_structured_outputs_schema(bad_schema)
        self.assertFalse(audit["compatible"])
        self.assertEqual(audit["explicitTypeAudit"]["invalidAnyOfBranchCount"], 1)
        self.assertEqual(
            audit["explicitTypeAudit"]["invalidAnyOfBranchPaths"],
            ["/properties/value/anyOf/0"],
        )

    def test_provenance_counts_explicit_type_adaptations_mechanically(self) -> None:
        """The schema record derives, rather than hard-codes, type-addition counts."""

        record = model_authorable_schema_record()
        attempt2 = json.loads(ATTEMPT2_SCHEMA.read_text(encoding="utf-8"))
        inventory = _missing_explicit_type_inventory(attempt2)
        self.assertEqual(
            record["explicitTypeAdaptationCounts"],
            {
                "constSchemasGivenExplicitType": len(
                    inventory["constSchemasLackingExplicitType"]
                ),
                "enumSchemasGivenExplicitType": len(
                    inventory["enumSchemasLackingExplicitType"]
                ),
                "otherConstraintSchemasGivenExplicitType": len(
                    set(
                        inventory[
                            "directlyConstrainedSchemasLackingCompatibleType"
                        ]
                    )
                    - set(inventory["constSchemasLackingExplicitType"])
                    - set(inventory["enumSchemasLackingExplicitType"])
                ),
            },
        )

    def test_ref_sibling_fails_provider_audit_before_adaptation(self) -> None:
        """A `$ref` carrying description is rejected at its exact local path."""

        schema = {
            "type": "object",
            "properties": {
                "value": {"$ref": "#/$defs/x", "description": "local annotation"}
            },
            "required": ["value"],
            "additionalProperties": False,
            "$defs": {"x": {"type": "string"}},
        }
        audit = audit_openai_structured_outputs_schema(schema)
        self.assertFalse(audit["compatible"])
        self.assertTrue(
            any(
                "/properties/value $ref must be the only keyword" in finding
                for finding in audit["findings"]
            )
        )

    def test_ref_transport_adaptation_removes_every_sibling(self) -> None:
        """The provider projection of any `$ref` node is exactly the reference."""

        frozen_fragment = {
            "$ref": "#/$defs/x",
            "description": "local annotation",
            "title": "local title",
            "readOnly": True,
        }
        self.assertEqual(
            _adapt_for_openai_strict(frozen_fragment), {"$ref": "#/$defs/x"}
        )

    def test_actual_schema_has_only_pure_resolved_refs(self) -> None:
        """All references in the final actual schema are pure and resolvable."""

        inventory = _ref_inventory(derive_model_authorable_schema())
        self.assertGreater(inventory["totalRefNodes"], 0)
        self.assertEqual(inventory["refSiblingNodes"], 0)
        self.assertEqual(inventory["refSiblingPaths"], [])
        self.assertEqual(inventory["unresolvedRefTargets"], 0)
        self.assertEqual(inventory["unresolvedReferences"], [])
        self.assertEqual(inventory["pureRefNodes"], inventory["totalRefNodes"])

    def test_attempt3_ref_defect_and_provenance_are_derived(self) -> None:
        """Provenance derives the reviewed defect from the preserved attempt-3 schema."""

        attempt3 = json.loads(ATTEMPT3_SCHEMA.read_text(encoding="utf-8"))
        before = _ref_inventory(attempt3)
        record = model_authorable_schema_record()
        self.assertIn(
            "/$defs/evidenceSpan/properties/sectionTitle",
            before["refSiblingPaths"],
        )
        self.assertEqual(
            record["refSiblingNodesDetectedBeforeAdaptation"],
            before["refSiblingNodes"],
        )
        self.assertEqual(record["refSiblingNodesAfterAdaptation"], 0)
        self.assertEqual(
            record["refSiblingKeywordsRemoved"], before["refSiblingKeywords"]
        )

    def test_unresolved_local_ref_fails_closed(self) -> None:
        """A pure but unresolved local reference fails provider compatibility."""

        schema = {
            "type": "object",
            "properties": {"value": {"$ref": "#/$defs/missing"}},
            "required": ["value"],
            "additionalProperties": False,
            "$defs": {},
        }
        audit = audit_openai_structured_outputs_schema(schema)
        self.assertFalse(audit["compatible"])
        self.assertEqual(audit["refAudit"]["unresolvedRefTargets"], 1)
        self.assertTrue(any("unresolved $ref" in finding for finding in audit["findings"]))

    def test_frozen_schema_drift_fails_closed(self) -> None:
        """The derivation refuses a changed authority until explicitly reviewed."""

        self.assertEqual(
            sha256_bytes(CANDIDATE_SCHEMA_PATH.read_bytes()),
            FROZEN_CANDIDATE_SCHEMA_SHA256,
        )
        changed = json.loads(CANDIDATE_SCHEMA_PATH.read_text(encoding="utf-8"))
        changed["title"] = "drifted"
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "schema.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ModelAuthorableSchemaError, "hash changed"):
                derive_model_authorable_schema(path)

    def test_correct_model_authorable_fixture_is_accepted(self) -> None:
        """The known valid semantic M1 fixture satisfies the derived schema."""

        payload = json.loads(VALID_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(validate_model_authorable_payload(payload), [])

    def test_m2a_structural_shape_is_rejected(self) -> None:
        """The authentic M2-A shape fails before unchanged semantic validation."""

        payload = json.loads(M2A_FIXTURE.read_text(encoding="utf-8"))
        errors = validate_model_authorable_payload(payload)
        self.assertTrue(errors)
        joined = "\n".join(errors)
        self.assertIn("candidateID", joined)
        self.assertIn("evidenceSpanID", joined)
        self.assertIn("Additional properties", joined)


if __name__ == "__main__":
    unittest.main()
