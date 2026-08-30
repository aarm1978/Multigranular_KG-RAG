"""Focused no-network tests for M2-C2A trusted evidence metadata binding."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import jsonschema

from src.extraction.llm.publications.candidate_validation import VALIDATOR_VERSION
from src.extraction.llm.publications.request_builder import canonical_json
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    PROMPT_PATH,
    build_c1b_request,
    load_c0_bindings,
)
from src.extraction.llm.publications.run_publication_trusted_evidence_metadata_binding import (
    C1B_OUTPUT_DIR,
    _c1b_paths,
    _section_title_only_copy,
    _tree_snapshot,
    build_evidence_field_responsibility_audit,
    generate_c2a_artifacts,
)
from src.extraction.llm.publications.trusted_evidence_metadata_schema import (
    TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION,
    derive_trusted_evidence_metadata_schema,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TrustedEvidenceMetadataBindingTests(unittest.TestCase):
    """Prove C2A binds only trusted section titles and preserves C1B."""

    @classmethod
    def setUpClass(cls) -> None:
        """Generate one shared offline result for diagnostic assertions."""

        cls._temporary_directory = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls._temporary_directory.name)
        with patch(
            "src.extraction.llm.publications.openai_provider.urlopen",
            side_effect=AssertionError("C2A tests must not use network"),
        ):
            cls.result = generate_c2a_artifacts(cls.output_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the shared temporary artifact directory."""

        cls._temporary_directory.cleanup()

    @staticmethod
    def _request(development_id: str) -> dict[str, object]:
        """Return one trusted request from the accepted C0 binding."""

        binding = next(
            row for row in load_c0_bindings() if row["developmentID"] == development_id
        )
        return build_c1b_request(binding)

    @staticmethod
    def _title_constraint(request: dict[str, object]) -> dict[str, object]:
        """Return the prospective evidence title constraint for one request."""

        schema = derive_trusted_evidence_metadata_schema(request)
        return schema["$defs"]["evidenceSpan"]["properties"]["sectionTitle"]

    def test_exact_string_and_markup_are_preserved_as_provider_const(self) -> None:
        """A trusted HTML/Markdown title is copied without normalization."""

        request = self._request("DEV-02")
        expected = '<span id="page-15-0"></span>**2.7. Evaluation**'
        self.assertEqual(request["sourceUnit"]["sectionTitleRaw"], expected)
        self.assertEqual(
            self._title_constraint(request),
            {"type": "string", "const": expected},
        )

    def test_normalized_dev02_and_dev06_variants_are_rejected(self) -> None:
        """Only exact authoritative DEV-02 and DEV-06 title strings validate."""

        dev02_request = self._request("DEV-02")
        dev02 = jsonschema.Draft202012Validator(
            self._title_constraint(dev02_request)
        )
        self.assertTrue(
            dev02.is_valid('<span id="page-15-0"></span>**2.7. Evaluation**')
        )
        for value in (None, "2.7. Evaluation", "**2.7. Evaluation**"):
            self.assertFalse(dev02.is_valid(value), value)
        dev06_request = self._request("DEV-06")
        dev06 = jsonschema.Draft202012Validator(
            self._title_constraint(dev06_request)
        )
        self.assertTrue(dev06.is_valid("**3. Results**"))
        self.assertFalse(dev06.is_valid("3. Results"))
        self.assertFalse(dev06.is_valid(None))
        for development_id, request in (
            ("DEV-02", dev02_request),
            ("DEV-06", dev06_request),
        ):
            authentic = json.loads(
                _c1b_paths(development_id)["raw"].read_text(encoding="utf-8")
            )
            schema_validator = jsonschema.Draft202012Validator(
                derive_trusted_evidence_metadata_schema(request)
            )
            diagnostic, _ = _section_title_only_copy(
                authentic, request["sourceUnit"]["sectionTitleRaw"]
            )
            with self.subTest(developmentID=development_id):
                self.assertFalse(schema_validator.is_valid(authentic))
                self.assertTrue(
                    schema_validator.is_valid(diagnostic),
                    list(schema_validator.iter_errors(diagnostic)),
                )

    def test_null_authority_produces_exact_null_const(self) -> None:
        """A synthetic trusted null uses the provider-compatible null singleton."""

        request = deepcopy(self._request("DEV-01"))
        request["sourceUnit"]["sectionTitleRaw"] = None
        constraint = self._title_constraint(request)
        validator = jsonschema.Draft202012Validator(constraint)
        self.assertEqual(constraint, {"type": "null", "const": None})
        self.assertTrue(validator.is_valid(None))
        self.assertFalse(validator.is_valid(""))

    def test_all_ten_schemas_pass_the_existing_provider_audit(self) -> None:
        """Every C0-bound schema exposes 40 nodes, no relations, and exact titles."""

        audit = self.result["schemaAudit"]
        self.assertEqual(
            audit["prospectiveSchemaVersion"],
            TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION,
        )
        self.assertTrue(audit["allUnitsCompatible"])
        self.assertTrue(audit["allUnitsExposeFortyNodesAndZeroRelations"])
        self.assertTrue(audit["allUnitsBindExactAuthoritativeTitle"])
        for row in audit["units"]:
            with self.subTest(developmentID=row["developmentID"]):
                self.assertEqual(row["exposedNodeTargetCount"], 40)
                self.assertEqual(row["exposedRelationTargetCount"], 0)
                self.assertEqual(row["refSiblingCount"], 0)
                self.assertEqual(row["unresolvedReferenceCount"], 0)
                self.assertEqual(row["missingExplicitTypeCount"], 0)
                self.assertEqual(row["invalidAnyOfBranchCount"], 0)

    def test_responsibility_audit_changes_only_section_title(self) -> None:
        """Other potentially trusted evidence fields remain review-only in C2A."""

        audit = build_evidence_field_responsibility_audit()
        implemented = [
            row["fieldName"]
            for row in audit["fields"]
            if row["implementedProspectiveChangeInC2A"]
        ]
        self.assertEqual(implemented, ["sectionTitle"])
        self.assertEqual(audit["additionalFieldsBoundProspectively"], [])

    def test_counterfactual_copy_changes_only_section_title(self) -> None:
        """Reverting diagnostic titles reconstructs each authentic payload exactly."""

        for development_id in ("DEV-02", "DEV-05", "DEV-06"):
            paths = _c1b_paths(development_id)
            payload = json.loads(paths["raw"].read_text(encoding="utf-8"))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            copy, changes = _section_title_only_copy(
                payload, request["sourceUnit"]["sectionTitleRaw"]
            )
            for index, original in enumerate(payload["evidenceSpans"]):
                copy["evidenceSpans"][index]["sectionTitle"] = original["sectionTitle"]
            with self.subTest(developmentID=development_id):
                self.assertEqual(canonical_json(copy), canonical_json(payload))
                self.assertTrue(
                    all(row["jsonPointer"].endswith("/sectionTitle") for row in changes)
                )

    def test_unchanged_validator_is_used_and_dev05_offset_failure_survives(self) -> None:
        """C2A does not conceal the authentic DEV-05 coordinate error."""

        diagnostics = self.result["counterfactualDiagnostics"]
        dev05 = next(
            row for row in diagnostics["units"] if row["developmentID"] == "DEV-05"
        )
        codes = dev05["sectionTitleOnlyCounterfactual"][
            "validationFindingCodes"
        ]
        self.assertIn("OFFSET_MISMATCH_IN_UNIT", codes)
        self.assertIn("EVIDENCE_NOT_LITERAL", codes)
        wrapper = json.loads(
            next(
                (
                    self.output_dir
                    / "counterfactual/DEV-05"
                ).glob("*_validation_results.json")
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            wrapper["validationResults"]["validatorVersion"], VALIDATOR_VERSION
        )
        self.assertTrue(wrapper["unchangedValidatorUsed"])

    def test_dev06_attribute_findings_are_diagnosed_without_logic_change(self) -> None:
        """The DEV-06 cascade is measured after changing only trusted title metadata."""

        diagnosis = self.result["counterfactualDiagnostics"][
            "dev06CascadeDiagnosis"
        ]
        self.assertIn(
            "ATTRIBUTE_EVIDENCE_MISSING",
            diagnosis["authenticFindingCodeCounts"],
        )
        self.assertNotIn(
            "ATTRIBUTE_EVIDENCE_MISSING",
            diagnosis["counterfactualFindingCodeCounts"],
        )
        self.assertFalse(diagnosis["attributeEvidenceLogicModified"])

    def test_historical_artifacts_and_prompt_remain_byte_identical(self) -> None:
        """The complete accepted C1B tree and prompt v0.1.4 retain frozen hashes."""

        snapshot = _tree_snapshot(C1B_OUTPUT_DIR)
        self.assertEqual(snapshot["fileCount"], 184)
        self.assertEqual(
            snapshot["treeInventorySha256"],
            "bee13c4501597cf7793d6c9e93f3d4a5b35a2881bc0cd98b1a0a24ea03682a28",
        )
        self.assertEqual(
            hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest(),
            "6b180b88d718dbda7d9f30b28c484d263998ed8caa88eab516f531e488b8317f",
        )
        accepted = {
            "data/curation/papers/m2/c1a/publication_m2c1a_exact_structured_model_output.json": "db63a5f9cbb4e9f10d537f56d17ce54fac2c20266f067e10bd94d4f3ed696a0b",
            "data/curation/papers/m2/b3/publication_m2b3_exact_structured_model_output.json": "f6ca56b303e9fd61b5011f5d5d35edc097e828cda5d3637b72c44f2f119a89be",
        }
        for relative, expected in accepted.items():
            self.assertEqual(
                hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest(),
                expected,
            )

    def test_generation_has_no_provider_or_network_path(self) -> None:
        """Ordinary C2A generation remains fully offline and deterministic."""

        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "src.extraction.llm.publications.openai_provider.urlopen",
                side_effect=AssertionError("network access is forbidden"),
            ):
                result = generate_c2a_artifacts(Path(directory))
        self.assertEqual(result["schemaAudit"]["providerCalls"], 0)
        self.assertEqual(
            result["counterfactualDiagnostics"]["providerCalls"], 0
        )
        self.assertEqual(
            canonical_json(result),
            canonical_json(self.result),
        )


if __name__ == "__main__":
    unittest.main()
