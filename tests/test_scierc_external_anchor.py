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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.scierc_external_anchor import (  # noqa: E402
    SciERCAnchorError, build_run_manifest, inference_projection, output_schema,
    parse_processed_document, relation_signature, score_documents, validate_prediction,
    verify_archive,
)


def document() -> object:
    """Return a tiny synthetic processed SciERC document."""

    return parse_processed_document({"doc_key": "synthetic-1", "sentences": [["A", "method", "wins"], ["metric"]],
        "ner": [[[0, 1, "Method"]], [[3, 3, "Metric"]]],
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

    def test_projection_is_gold_free_and_preserves_global_indices(self) -> None:
        """Model-facing input contains source text/tokens, never gold fields."""

        projection = inference_projection(document())
        self.assertEqual([item["index"] for item in projection["tokens"]], [0, 1, 2, 3])
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
        self.assertIsNone(result["composite"])
        self.assertEqual(relation_signature("COMPARE", (3, 3), (0, 1)), ("COMPARE", (0, 1), (3, 3)))
        self.assertNotEqual(relation_signature("USED-FOR", (3, 3), (0, 1)), relation_signature("USED-FOR", (0, 1), (3, 3)))
        endpoint_type_variant = prediction(); endpoint_type_variant["entities"][0]["entityType"] = "Task"  # type: ignore[index]
        type_result = score_documents([(document(), endpoint_type_variant)])
        self.assertEqual(type_result["entity"]["TP"], 1)
        self.assertEqual(type_result["relation"]["TP"], 1)

    def test_manifest_is_fail_closed_for_missing_evaluate_for_definition(self) -> None:
        """No body hash or live-ready manifest exists while prompt semantics are unresolved."""

        manifest = build_run_manifest([document()], {"COMPARE": "synthetic only"})
        self.assertEqual(manifest["status"], "blocked_pending_prompt_semantics")
        self.assertIn("EVALUATE-FOR", manifest["promptStatus"]["missingRelationDefinitions"])
        self.assertIsNone(manifest["requests"][0]["providerRequestBodySha256"])
        self.assertEqual(output_schema()["properties"]["entities"]["items"]["properties"]["entityType"]["enum"][0], "Generic")

    def test_ready_manifest_accounts_for_repeated_overhead_without_pricing(self) -> None:
        """A complete synthetic definition set yields body hashes and bounded accounting."""

        definitions = {label: "synthetic fixture definition" for label in ("COMPARE", "CONJUNCTION", "EVALUATE-FOR", "FEATURE-OF", "HYPONYM-OF", "PART-OF", "USED-FOR")}
        manifest = build_run_manifest([document()], definitions)
        self.assertEqual(manifest["status"], "ready_for_explicit_live_execution")
        self.assertIsNotNone(manifest["requests"][0]["providerRequestBodySha256"])
        self.assertGreater(manifest["preflightAccounting"]["totalConservativeInputTokenUpperBound"], 0)
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
