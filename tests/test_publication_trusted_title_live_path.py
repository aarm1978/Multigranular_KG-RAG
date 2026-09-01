"""Tests that the approved C2A title constraint is the current provider path."""

import inspect
import tempfile
from pathlib import Path
import unittest

import jsonschema

from src.extraction.llm.publications import run_publication_full_devset0_node_development as runner
from src.extraction.llm.publications.candidate_validation import validate_candidate_envelope


class PublicationTrustedTitleLivePathTests(unittest.TestCase):
    """Guard pre-generation trusted-title promotion without output repair."""

    def test_prepare_unit_uses_exact_trusted_title_and_only_that_binding(self) -> None:
        """The live provider schema preserves raw title bytes and rejects alternatives."""

        binding = runner.load_c0_bindings()[0]
        with tempfile.TemporaryDirectory() as directory:
            state = runner.prepare_unit(binding, output_dir=Path(directory))
        title = state["request"]["sourceUnit"]["sectionTitleRaw"]
        properties = state["schema"]["$defs"]["evidenceSpan"]["properties"]
        self.assertEqual(properties["sectionTitle"], {"type": "string", "const": title})
        validator = jsonschema.Draft202012Validator(properties["sectionTitle"])
        self.assertTrue(validator.is_valid(title))
        self.assertFalse(validator.is_valid(title.strip("*")))
        self.assertFalse(validator.is_valid(f" {title}"))
        self.assertEqual(properties["sourceArtifactID"].get("const"), None)
        self.assertEqual(properties["sourceUnitID"].get("const"), None)
        self.assertEqual(properties["sectionID"].get("const"), None)

    def test_live_runner_has_no_counterfactual_or_repair_step(self) -> None:
        """Provider output flows directly to schema validation and unchanged downstream."""

        source = inspect.getsource(runner.run_live_unit)
        self.assertNotIn("_section_title_only_copy", source)
        self.assertNotIn("repair", source.lower())
        self.assertIn("validate_model_authorable_payload(payload, state[\"schema\"])", source)
        self.assertIn("_downstream(raw_output, request)", source)

    def test_v4_validator_still_owns_exact_title_equality(self) -> None:
        """The unchanged validator remains the semantic equality authority."""

        source = inspect.getsource(validate_candidate_envelope)
        self.assertIn("_validate_evidence", source)


if __name__ == "__main__":
    unittest.main()
