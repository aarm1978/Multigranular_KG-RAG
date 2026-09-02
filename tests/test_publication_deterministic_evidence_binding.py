"""Focused no-call tests for prospective literal evidence binding."""

from __future__ import annotations

import hashlib
import unittest

from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans
from src.extraction.llm.publications.prospective_evidence_binding_schema import (
    derive_prospective_evidence_binding_schema,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    build_full_semantic_request,
    load_c0_bindings,
)
from src.extraction.llm.publications.openai_provider import build_provider_input


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


if __name__ == "__main__":
    unittest.main()
