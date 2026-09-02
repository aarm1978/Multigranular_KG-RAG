"""Focused no-call tests for prospective literal evidence binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans
from src.extraction.llm.publications.audit_ambiguous_evidence_anchor_feasibility import build_audit
from src.extraction.llm.publications.audit_authentic_evidence_binding_feasibility import _paths
from src.extraction.llm.publications.prospective_evidence_binding_schema import (
    derive_prospective_evidence_binding_schema,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    _downstream,
    build_full_semantic_request,
    load_c0_bindings,
    prepare_unit,
)
from src.extraction.llm.publications.openai_provider import build_provider_input
from src.extraction.llm.publications.request_builder import load_json_object


class DeterministicEvidenceBindingTests(unittest.TestCase):
    """Prove all location decisions remain exact and fail closed."""

    source = {"text": "alpha beta alpha gamma", "startOffsetInDocument": 40}

    def bind(self, text: str, anchor: object = None):
        span = {"evidenceSpanID": "evidence-0001", "evidenceText": text}
        if anchor is not None:
            span["locatorAnchor"] = anchor
        return bind_evidence_spans({"evidenceSpans": [span]}, self.source)

    def test_unique_literal_derives_offsets_and_hash(self):
        bound, result = self.bind("beta")
        span = bound["evidenceSpans"][0]
        self.assertEqual(result["bindingStatus"], "bound")
        self.assertEqual((span["startOffsetInUnit"], span["endOffsetInUnit"]), (6, 10))
        self.assertEqual((span["startOffsetInDocument"], span["endOffsetInDocument"]), (46, 50))
        self.assertEqual(span["evidenceHash"], hashlib.sha256(b"beta").hexdigest())

    def test_absent_and_ambiguous_literals_fail_closed(self):
        self.assertEqual(self.bind("missing")[1]["bindingStatus"], "failed")
        self.assertEqual(self.bind("alpha")[1]["bindingStatus"], "failed")

    def test_unique_anchor_disambiguates_without_changing_evidence(self):
        bound, result = self.bind("alpha", "alpha gamma")
        self.assertEqual(result["bindingStatus"], "bound")
        span = bound["evidenceSpans"][0]
        self.assertEqual(span["evidenceText"], "alpha")
        self.assertEqual(span["startOffsetInUnit"], 11)
        self.assertNotIn("locatorAnchor", span)

    def test_invalid_nonunique_and_multi_literal_anchors_fail_closed(self):
        self.assertEqual(self.bind("alpha", "alpha")[1]["bindingStatus"], "failed")
        self.assertEqual(self.bind("alpha", "not source")[1]["bindingStatus"], "failed")
        source = {"text": "alpha alpha tail", "startOffsetInDocument": 0}
        _, result = bind_evidence_spans({"evidenceSpans": [{"evidenceText": "alpha", "locatorAnchor": "alpha alpha tail"}]}, source)
        self.assertEqual(result["bindingStatus"], "failed")

    def test_provider_schema_excludes_computed_fields_and_input_excludes_guide(self):
        request = build_full_semantic_request(load_c0_bindings()[0])
        schema = derive_prospective_evidence_binding_schema(request)
        evidence = schema["$defs"]["evidenceSpan"]
        for key in ("startOffsetInUnit", "endOffsetInUnit", "startOffsetInDocument", "endOffsetInDocument", "evidenceHash"):
            self.assertNotIn(key, evidence["properties"])
        self.assertIn("locatorAnchor", evidence["properties"])
        self.assertNotIn("evidence-coordinate guide", build_provider_input(request).decode("utf-8"))
        self.assertNotIn("D-26", request["eligibleOperationalTargetIDs"])

    def test_full_semantic_preflight_records_its_actual_prompt_version(self):
        """Fresh full-semantic preparation remains explicitly bound to v0.1.5."""

        with tempfile.TemporaryDirectory() as directory:
            state = prepare_unit(load_c0_bindings()[0], output_dir=Path(directory), full_semantic=True)
        self.assertEqual(state["request"]["prompt"]["version"], "publication-development-0.1.5")
        self.assertEqual(state["preflight"]["promptVersion"], "publication-development-0.1.5")

    def test_authentic_ambiguous_cases_bind_only_with_their_committed_anchors(self):
        """Exercise DEV-06/07 literals without altering preserved raw outputs."""

        for case in build_audit()["cases"]:
            with self.subTest(case=case["evidenceSpanID"]):
                request = load_json_object(_paths(case["developmentID"])["request"])
                payload = {"evidenceSpans": [{
                    "evidenceSpanID": case["evidenceSpanID"],
                    "evidenceText": case["originalEvidenceText"],
                    "locatorAnchor": case["minimumUniqueLocatorAnchor"]["anchorText"],
                }]}
                bound, result = bind_evidence_spans(payload, request["sourceUnit"])
                self.assertEqual(result["bindingStatus"], "bound")
                self.assertEqual(bound["evidenceSpans"][0]["startOffsetInUnit"], case["historicalReturnedStartOffsetInUnit"])

    def test_dev05_historical_offset_remains_unchanged_while_prospective_binding_corrects_copy(self):
        """Use a copied literal; never rewrite the preserved DEV-05 response."""

        paths = _paths("DEV-05")
        request = load_json_object(paths["request"])
        historical = load_json_object(paths["raw"])
        span = next(row for row in historical["evidenceSpans"] if row["evidenceSpanID"] == "evidence-0003")
        bound, result = bind_evidence_spans({"evidenceSpans": [{
            "evidenceSpanID": span["evidenceSpanID"], "evidenceText": span["evidenceText"],
        }]}, request["sourceUnit"])
        self.assertEqual(result["bindingStatus"], "bound")
        self.assertEqual(span["startOffsetInUnit"], 545)
        self.assertEqual(bound["evidenceSpans"][0]["startOffsetInUnit"], 541)
        self.assertEqual(load_json_object(paths["raw"])["evidenceSpans"][2]["startOffsetInUnit"], 545)

    def test_trusted_metadata_survives_parse_binding_and_canonical_validation(self):
        """A copied authentic span retains trusted source/section values end to end."""

        paths = _paths("DEV-05")
        request = load_json_object(paths["request"])
        historical = load_json_object(paths["raw"])
        span = next(row for row in historical["evidenceSpans"] if row["evidenceSpanID"] == "evidence-0003")
        provider_span = {key: value for key, value in span.items() if key not in {
            "startOffsetInUnit", "endOffsetInUnit", "startOffsetInDocument", "endOffsetInDocument", "evidenceHash",
        }}
        provider_span["locatorAnchor"] = None
        raw = json.dumps({"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [provider_span], "abstentions": [], "deferredRecords": []}).encode("utf-8")
        parser, _, validation, _ = _downstream(raw, request, evidence_binding=True)
        bound = parser["parsedEnvelope"]["evidenceSpans"][0]
        for key in ("sourceArtifactID", "sourceUnitID", "sourceUnitTextHash", "sectionID", "sectionTitle"):
            self.assertEqual(bound[key], span[key])
        self.assertEqual(parser["evidenceBinding"]["bindingStatus"], "bound")
        self.assertTrue(validation["evidenceResults"][0]["valid"])


if __name__ == "__main__":
    unittest.main()
