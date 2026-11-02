"""Four synthetic T1/T2 checks; no corpus, provider or graph access."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import unittest

from src.extraction.llm.datasets.source_units import (
    bind_abstract_evidence,
    build_abstract_source_unit,
)


class DatasetSemanticSourceUnitTests(unittest.TestCase):
    """Exercise the bounded abstract reader and literal evidence interface."""

    owner = "a" * 32

    def build(self, abstract: object = "alpha beta alpha gamma", **kwargs):
        """Build a synthetic unit with caller-supplied snapshot provenance."""
        return build_abstract_source_unit(
            {"resource_id": self.owner, "abstract": abstract},
            accepted_owner_id=self.owner,
            provenance={"snapshotID": "synthetic-snapshot-1", "sourceVersion": "v1"},
            **kwargs,
        )

    def test_text_unicode_coordinates_identity_and_hash_stability(self):
        """Preserve Unicode and mixed newlines without byte-offset confusion."""
        text = "  café 🌊\r\n流量 e\u0301\rfin\n"
        unit = self.build(text)["unit"]
        record = unit.to_record()
        self.assertEqual(record["text"], text)
        self.assertEqual(record["artifactFamily"], "hydroshare")
        self.assertEqual(record["authorityTextSha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(record["integrityStatus"], "computed_only")
        self.assertEqual((record["startLine"], record["endLine"]), (1, 3))
        self.assertEqual(record["endOffsetInAuthority"], len(text))
        self.assertEqual(unit, self.build(text)["unit"])
        self.assertNotEqual(unit.source_unit_id, self.build(text + "x")["unit"].source_unit_id)
        other = build_abstract_source_unit(
            {"resource_id": self.owner, "abstract": text}, accepted_owner_id=self.owner,
            provenance={"snapshotID": "another-snapshot"},
        )["unit"]
        self.assertNotEqual(unit.source_unit_id, other.source_unit_id)
        evidence = bind_abstract_evidence(unit, [{"evidenceText": "流量 e\u0301\rfin"}])["evidenceSpans"][0]
        start, end = evidence["startOffsetInAuthority"], evidence["endOffsetInAuthority"]
        self.assertEqual(start, 10)
        self.assertEqual(text[start:end], evidence["evidenceText"])
        self.assertEqual((evidence["startLine"], evidence["endLine"]), (2, 3))

    def test_required_input_and_trusted_digest_failures(self):
        """Separate absent optional fields, malformed sources and digest checks."""
        for abstract, reason in ((None, "required_source_field_missing"),
                                 (42, "source_field_malformed"),
                                 ("\ud800", "source_field_malformed")):
            with self.subTest(abstract=repr(abstract)):
                result = self.build(abstract)
                self.assertEqual(result["status"], "failed_source_or_evidence_binding")
                self.assertEqual(result["diagnostic"]["reason"], reason)
                self.assertFalse(result["inputComplete"])
                self.assertIsNone(result["unit"])
        missing = build_abstract_source_unit(
            {"resource_id": self.owner}, accepted_owner_id=self.owner,
            provenance={"snapshotID": "synthetic"},
        )
        self.assertEqual(missing["diagnostic"]["reason"], "required_source_field_missing")
        self.assertEqual(self.build(None, required=False)["status"], "optional_input_absent")
        self.assertEqual(self.build([], required=False)["diagnostic"]["reason"], "source_field_malformed")
        self.assertEqual(self.build("")["status"], "source_read_success")
        mismatch = self.build("text", expected_authority_text_sha256="0" * 64)
        self.assertEqual(mismatch["diagnostic"]["reason"], "source_content_integrity_failure")
        self.assertEqual(mismatch["diagnostic"]["sourceField"], "abstract")
        self.assertEqual(mismatch["diagnostic"]["sourceVersion"], "v1")
        digest = hashlib.sha256(b"text").hexdigest()
        matched = self.build("text", expected_authority_text_sha256=digest)["unit"]
        self.assertEqual(matched.integrity_status, "matched_trusted_digest")
        self.assertEqual(self.build(expected_authority_text_sha256="bad")["diagnostic"]["reason"],
                         "trusted_digest_malformed")

    def test_literal_binding_and_explicit_locator_disambiguation(self):
        """Use exact literals, never repair missing or ambiguous quotations."""
        unit = self.build()["unit"]
        for quote, anchor, expected in (("beta", None, 6), ("missing", None, None),
                                        ("alpha", None, None), ("alpha", "alpha gamma", 11)):
            with self.subTest(quote=quote, anchor=anchor):
                supplied = [{"evidenceText": quote}]
                if anchor is not None:
                    supplied[0]["locatorAnchor"] = anchor
                original = deepcopy(supplied)
                result = bind_abstract_evidence(unit, supplied)
                self.assertEqual(supplied, original)
                if expected is None:
                    self.assertEqual(result["status"], "failed_source_or_evidence_binding")
                    self.assertEqual(result["diagnostic"]["reason"], "evidence_quote_unbound")
                    self.assertEqual(result["evidenceSpans"], [])
                else:
                    self.assertEqual(result["status"], "evidence_bound")
                    span = result["evidenceSpans"][0]
                    self.assertEqual(span["evidenceText"], quote)
                    self.assertEqual(span["startOffsetInAuthority"], expected)

    def test_owner_binding_immutability_and_no_graph_assertions(self):
        """Keep the exact accepted owner and emit only technical records."""
        resource = {"resource_id": self.owner, "abstract": "beta", "nested": [1]}
        provenance = {"snapshotID": "synthetic", "sourceVersion": "v1"}
        before = deepcopy((resource, provenance))
        result = build_abstract_source_unit(resource, accepted_owner_id=self.owner, provenance=provenance)
        unit = result["unit"]
        record = unit.to_record()
        self.assertEqual(record["canonicalArtifactID"], self.owner)
        record["text"] = "changed"
        self.assertEqual(unit.text, "beta")
        with self.assertRaises(FrozenInstanceError):
            unit.text = "changed"
        bound = bind_abstract_evidence(unit, [{"evidenceText": "beta", "sectionID": "fake",
                                             "sourceArtifactID": "fake", "startOffsetInUnit": 999}])
        self.assertEqual(bound["evidenceSpans"][0]["canonicalArtifactID"], self.owner)
        self.assertEqual(bound["evidenceSpans"][0]["startOffsetInAuthority"], 0)
        self.assertNotIn("sectionID", bound["evidenceSpans"][0])
        self.assertEqual((resource, provenance), before)
        mismatch = build_abstract_source_unit(resource, accepted_owner_id="b" * 32, provenance=provenance)
        self.assertEqual(mismatch["diagnostic"]["reason"], "source_owner_mismatch")
        bad_provenance = build_abstract_source_unit(resource, accepted_owner_id=self.owner, provenance={})
        self.assertEqual(bad_provenance["diagnostic"]["reason"], "source_provenance_missing_or_malformed")
        self.assertEqual(set(result), {"status", "unit", "inputComplete"})
        self.assertEqual(set(bound), {"status", "evidenceSpans", "bindingReport"})
        self.assertNotIn("abstained_no_evidence", repr((result, bound)))


if __name__ == "__main__":
    unittest.main()
