"""Focused no-network tests for SciERC external-anchor mechanics."""

from __future__ import annotations

import io
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.scierc_external_anchor import (  # noqa: E402
    SciERCAnchorError, build_run_manifest, inference_projection, output_schema,
    parse_processed_document, relation_signature, score_documents, validate_prediction,
    verify_archive, build_request_body, _build_candidate_records, canonical_json,
    ARCHIVE_PATH, source_freeze, parse_processed_split, sha256_bytes,
)


def document() -> object:
    """Return a tiny synthetic processed SciERC document."""

    return parse_processed_document({"doc_key": "synthetic-1", "sentences": [["A", "method", "wins", "metric"], ["Other"]],
        "ner": [[[0, 1, "Method"], [3, 3, "Metric"]], []],
        "relations": [[[0, 1, 3, 3, "COMPARE"]], []]})


def prediction(reverse_symmetric: bool = False) -> dict[str, object]:
    """Return one valid gold-equivalent synthetic prediction."""

    source, target = ("e2", "e1") if reverse_symmetric else ("e1", "e2")
    return {"documentID": "synthetic-1", "entities": [
        {"entityID": "e1", "entityType": "Method", "spanStart": 0, "spanEnd": 1, "mentionText": "A method"},
        {"entityID": "e2", "entityType": "Metric", "spanStart": 3, "spanEnd": 3, "mentionText": "metric"}],
        "relations": [{"relationID": "r1", "relationType": "COMPARE", "sourceEntityID": source, "targetEntityID": target}]}


class SciERCExternalAnchorTests(unittest.TestCase):
    """Exercise only synthetic data and offline deterministic mechanics."""

    def setUp(self) -> None:
        """Fail any accidental network use, including provider and token-count calls."""

        self.network_guard = patch("socket.socket.connect", side_effect=AssertionError("NETWORK_PROHIBITED"))
        self.network_guard.start()
        self.addCleanup(self.network_guard.stop)

    def test_projection_is_gold_free_and_preserves_global_indices(self) -> None:
        """Model-facing input contains source text/tokens, never gold fields."""

        projection = inference_projection(document())
        self.assertEqual([item["index"] for item in projection["tokens"]], [0, 1, 2, 3, 4])
        self.assertEqual(projection["sentences"], [{"sentenceIndex": 0, "start": 0, "end": 3}, {"sentenceIndex": 1, "start": 4, "end": 4}])
        self.assertNotIn("ner", projection); self.assertNotIn("relations", projection); self.assertNotIn("clusters", projection)

    def test_validation_requires_exact_mention_and_same_document_endpoint(self) -> None:
        """Binding rejects non-exact spans and dangling endpoints."""

        bound = validate_prediction(prediction(), document())
        self.assertEqual(bound["entities"]["e1"], (0, 1, "Method"))
        invalid = prediction(); invalid["relations"][0]["targetEntityID"] = "missing"  # type: ignore[index]
        with self.assertRaisesRegex(SciERCAnchorError, "SAME_DOCUMENT"):
            validate_prediction(invalid, document())

    def test_primary_scorer_uses_span_type_and_symmetric_relation_keys(self) -> None:
        """COMPARE reversal matches; relation endpoint entity type is not scored."""

        result = score_documents([(document(), prediction(reverse_symmetric=True))])
        self.assertEqual(result["entity"]["TP"], 2); self.assertEqual(result["relation"]["TP"], 1)
        self.assertNotIn("composite", result)
        self.assertEqual(relation_signature("COMPARE", (3, 3), (0, 1)), ("COMPARE", (0, 1), (3, 3)))
        self.assertNotEqual(relation_signature("USED-FOR", (3, 3), (0, 1)), relation_signature("USED-FOR", (0, 1), (3, 3)))
        endpoint_type_variant = prediction(); endpoint_type_variant["entities"][0]["entityType"] = "Task"  # type: ignore[index]
        type_result = score_documents([(document(), endpoint_type_variant)])
        self.assertEqual(type_result["entity"]["TP"], 1)
        self.assertEqual(type_result["relation"]["TP"], 1)

    def test_candidate_never_authorizes_execution(self) -> None:
        """A build-ready candidate is neither accepted nor live-authorized."""

        manifest = _build_candidate_records([document()])
        self.assertEqual(manifest["status"], "NOT AUTHORIZED FOR PROVIDER EXECUTION")
        self.assertTrue(manifest["buildReady"])
        self.assertFalse(manifest["runtimeAccepted"])
        self.assertFalse(manifest["researcherLiveAuthorization"])
        self.assertFalse(manifest["automaticRedispatch"])
        self.assertEqual(output_schema()["properties"]["entities"]["items"]["properties"]["entityType"]["enum"][0], "Generic")

    def test_ready_manifest_accounts_for_repeated_overhead_without_pricing(self) -> None:
        """A complete synthetic definition set yields body hashes and bounded accounting."""

        manifest = _build_candidate_records([document()])
        self.assertIsNotNone(manifest["requests"][0]["providerRequestBodySha256"])
        self.assertEqual(manifest["preflightAccounting"]["totalSerializedRequestUtf8Bytes"], len(canonical_json(build_request_body(document()))))
        self.assertIsNone(manifest["preflightAccounting"]["apiPricing"])

    def test_archive_hash_is_checked_before_member_access(self) -> None:
        """A mismatched archive is rejected without relying on member contents."""

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                data = b'{"doc_key":"x","sentences":[["x"]],"ner":[[]],"relations":[[]]}\n'
                info = tarfile.TarInfo("processed_data/json/test.json"); info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            with self.assertRaisesRegex(SciERCAnchorError, "ARCHIVE_SHA256_MISMATCH"):
                verify_archive(path)

    def test_verified_archive_streams_all_frozen_member_checks(self) -> None:
        """A synthetic archive proves member hashes and document counts are streamed."""

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.tar.gz"
            payloads = {split: b'{"doc_key":"' + split.encode() + b'","sentences":[["x"]],"ner":[[]],"relations":[[]]}\n' for split in ("train", "dev", "test")}
            with tarfile.open(path, "w:gz") as archive:
                for split, payload in payloads.items():
                    info = tarfile.TarInfo(f"processed_data/json/{split}.json"); info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))
            freeze = {"officialArchive": {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
                "splits": {split: {"path": f"processed_data/json/{split}.json", "sha256": hashlib.sha256(payload).hexdigest(), "documentCount": 1} for split, payload in payloads.items()}}
            report = verify_archive(path, freeze)
            self.assertEqual(sorted(report["splits"]), ["dev", "test", "train"])

    def test_gold_counterfactual_cannot_change_request_bytes(self) -> None:
        """Changing every gold field leaves exact provider body bytes identical."""

        original = document()
        changed = replace(original, gold_entities=((0, 0, "Task"),), gold_relations=())
        self.assertEqual(canonical_json(build_request_body(original)), canonical_json(build_request_body(changed)))
        source = {"doc_key": "same", "sentences": [["x"]], "ner": [["secret"]], "relations": "secret", "clusters": "secret"}
        changed_source = deepcopy(source)
        changed_source.update(ner=None, relations=None, clusters=["different"])
        first = build_request_body(parse_processed_document(source, include_gold=False))
        second = build_request_body(parse_processed_document(changed_source, include_gold=False))
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertNotIn(b"secret", canonical_json(first))

    def test_cross_sentence_mentions_and_relations_fail(self) -> None:
        """The former cross-sentence positive fixture is now explicitly invalid."""

        cross = replace(document(), sentence_ranges=((0, 2), (3, 4)))
        with self.assertRaisesRegex(SciERCAnchorError, "RELATION_CROSSES"):
            validate_prediction(prediction(), cross)
        bad = prediction(); bad["entities"][0].update(spanStart=2, spanEnd=3, mentionText="wins metric")
        with self.assertRaisesRegex(SciERCAnchorError, "MENTION_CROSSES"):
            validate_prediction(bad, cross)

    def test_zero_matches_empty_predictions_and_empty_support(self) -> None:
        """F1 is zero whenever its positive denominator has zero TP."""

        empty = {"documentID": "synthetic-1", "entities": [], "relations": []}
        result = score_documents([(document(), empty)])
        self.assertEqual(result["entity"]["f1"], 0)
        self.assertIsNone(result["entity"]["precision"])
        wrong = prediction()
        for entity in wrong["entities"]:
            entity["entityType"] = "Task"
        self.assertEqual(score_documents([(document(), wrong)])["entity"]["f1"], 0)
        blank = replace(document(), gold_entities=(), gold_relations=())
        self.assertIsNone(score_documents([(blank, empty)])["entity"]["f1"])
        self.assertEqual(score_documents([(blank, prediction())])["entity"]["f1"], 0)

    def test_directed_and_both_symmetric_reversals(self) -> None:
        """Directed reversals miss; each symmetric label matches in either order."""

        for label in ("USED-FOR", "EVALUATE-FOR", "FEATURE-OF", "HYPONYM-OF", "PART-OF", "COMPARE", "CONJUNCTION"):
            with self.subTest(label=label):
                doc = replace(document(), gold_relations=((0, 1, 3, 3, label),))
                pred = prediction(reverse_symmetric=True)
                pred["relations"][0]["relationType"] = label
                expected = 1 if label in {"COMPARE", "CONJUNCTION"} else 0
                self.assertEqual(score_documents([(doc, pred)])["relation"]["f1"], expected)

    def test_malformed_schema_types_and_relation_ids_rejected(self) -> None:
        """Invalid predictions fail explicitly without dropping or coercing records."""

        invalid = [None, [], {**prediction(), "extra": True}]
        for field, value in [("spanStart", True), ("spanEnd", 1.0), ("entityID", 9), ("entityType", "wrong"), ("mentionText", None)]:
            item = prediction(); item["entities"][0][field] = value; invalid.append(item)
        for field, value in [("relationID", ""), ("relationID", 1), ("sourceEntityID", []), ("relationType", "wrong")]:
            item = prediction(); item["relations"][0][field] = value; invalid.append(item)
        item = prediction(); item["relations"].append({**item["relations"][0], "relationType": "USED-FOR"}); invalid.append(item)
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(SciERCAnchorError):
                validate_prediction(item, document())

    def test_source_types_are_never_coerced(self) -> None:
        """Non-string tokens, Boolean indices, and malformed sentence lists fail."""

        for sentences in ([[1]], [[True]], ["text"], [[]]):
            with self.subTest(sentences=sentences), self.assertRaises(SciERCAnchorError):
                parse_processed_document({"doc_key": "x", "sentences": sentences}, include_gold=False)
        with self.assertRaises(SciERCAnchorError):
            parse_processed_document({"doc_key": "x", "sentences": [["x"]], "ner": [[[False, 0, "Task"]]], "relations": [[]]})

    def test_official_builder_has_no_document_substitution_argument(self) -> None:
        """Official membership can only come from verified bytes, not supplied records."""

        import inspect
        self.assertEqual(list(inspect.signature(build_run_manifest).parameters), ["archive_path"])
        with self.assertRaisesRegex(SciERCAnchorError, "DUPLICATE_DOCUMENT_ID"):
            _build_candidate_records([document(), document()])

    def test_duplicate_and_substituted_split_bytes_rejected(self) -> None:
        """Identity requires unique documents and frozen archive bytes, not just count."""

        row = b'{"doc_key":"x","sentences":[["x"]]}\n'
        with self.assertRaisesRegex(SciERCAnchorError, "DUPLICATE_DOCUMENT_ID"):
            parse_processed_split(row + row, include_gold=False)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "substitution.tar.gz"
            path.write_bytes(row * 100)
            with self.assertRaisesRegex(SciERCAnchorError, "ARCHIVE_SHA256_MISMATCH"):
                build_run_manifest(path)

    @unittest.skipUnless(ARCHIVE_PATH.exists(), "ignored official source archive not installed")
    def test_local_source_candidate_identity_and_non_test_mechanics(self) -> None:
        """Bind all test IDs without gold access and exercise one dev source mechanically."""

        from src.extraction.llm.publications import scierc_external_anchor as anchor
        original = anchor.parse_processed_document

        def source_only(row, *, include_gold=True):
            """Assert that every official candidate parse disables gold interpretation."""
            self.assertFalse(include_gold)
            return original(row, include_gold=False)

        with patch.object(anchor, "parse_processed_document", side_effect=source_only):
            manifest = build_run_manifest()
        authority = source_freeze()
        with tarfile.open(ARCHIVE_PATH) as archive:
            payload = archive.extractfile(authority["splits"]["test"]["path"]).read()
            # Identity/source projection only: no test gold fields are accessed.
            expected = parse_processed_split(payload, include_gold=False)
            dev_payload = archive.extractfile(authority["splits"]["dev"]["path"]).read()
        self.assertEqual(sha256_bytes(payload), authority["splits"]["test"]["sha256"])
        self.assertEqual([r["documentID"] for r in manifest["requests"]], sorted(d.document_id for d in expected))
        self.assertEqual(manifest["logicalRequestCount"], 100)
        self.assertEqual(len(set(r["documentID"] for r in manifest["requests"])), 100)
        reconstructed = _build_candidate_records(expected)
        self.assertEqual(manifest["requests"], reconstructed["requests"])
        self.assertEqual(sha256_bytes(dev_payload), authority["splits"]["dev"]["sha256"])
        dev = original(json.loads(dev_payload.splitlines()[0]), include_gold=False)
        validate_prediction({"documentID": dev.document_id, "entities": [], "relations": []}, dev)
        self.assertEqual(build_request_body(dev)["max_output_tokens"], 32768)
        self.assertFalse(manifest["researcherLiveAuthorization"])
