"""Focused no-call verification for the Publication Step 6C canonical freeze."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes
from src.extraction.llm.publications.step6c_freeze_materialization import (
    FREEZE_PATH,
    INDEX_PATH,
    LIFECYCLE_PATH,
    PREDICTIONS_PATH,
    SOURCE_ROOT,
    Step6CFreezeError,
    _build_request_records,
    materialize,
)


def jsonl(path: Path) -> list[dict]:
    """Load one canonical JSONL freeze artifact."""
    return [json.loads(line) for line in path.read_text().splitlines() if line]


class Step6CFreezeMaterializationTests(unittest.TestCase):
    def test_materialization_is_offline_idempotent_and_exactly_227(self) -> None:
        """Two runs produce identical bytes and cannot reach network or credentials."""
        with tempfile.TemporaryDirectory() as directory, \
                patch("socket.socket.connect", side_effect=AssertionError("network forbidden")), \
                patch("src.extraction.llm.publications.production_runner.load_openai_api_key", side_effect=AssertionError("key forbidden")):
            output = Path(directory)
            first = materialize(output_root=output)
            names = (FREEZE_PATH.name, PREDICTIONS_PATH.name, LIFECYCLE_PATH.name, INDEX_PATH.name)
            before = {name: (output/name).read_bytes() for name in names}
            second = materialize(output_root=output)
            self.assertEqual(first, second)
            self.assertEqual(before, {name: (output/name).read_bytes() for name in names})
            self.assertEqual(first["artifactSha256"], sha256_bytes(canonical_json({k: v for k, v in first.items() if k != "artifactSha256"})))
            predictions, ledgers, indexes = (jsonl(output/name) for name in names[1:])
            self.assertEqual((len(predictions), len(ledgers), len(indexes)), (227, 227, 227))
            self.assertEqual(len({row["requestID"] for row in indexes}), 227)
            self.assertEqual([row["ordinal"] for row in indexes], list(range(1, 228)))

    def test_predictions_and_lifecycle_match_canonical_totals(self) -> None:
        """Tracked output is sufficient for Step 7 while retaining nonaccepted truth."""
        predictions = jsonl(PREDICTIONS_PATH)
        ledgers = jsonl(LIFECYCLE_PATH)
        indexes = jsonl(INDEX_PATH)
        self.assertTrue(all(row["acceptedSemanticProjection"]["step7PredictionContent"] for row in predictions))
        self.assertEqual(sum(len(row["acceptedSemanticProjection"]["acceptedNodes"]) for row in predictions), 5301)
        self.assertEqual(sum(len(row["acceptedSemanticProjection"]["acceptedEdges"]) for row in predictions), 2941)
        self.assertEqual(sum(row["acceptedNodeCount"] for row in indexes), 5301)
        self.assertEqual(sum(row["acceptedEdgeCount"] for row in indexes), 2941)
        self.assertEqual(Counter(row["selectedAttemptNumber"] for row in indexes), {1: 226, 2: 1})
        self.assertEqual(Counter(row["envelopeStatus"] for row in indexes), {"valid": 183, "partially_valid": 44})
        self.assertEqual(sum(row["excludedEvidenceDependencyCount"] for row in indexes), 43)
        self.assertEqual(sum(row["processingFailureRecordCount"] for row in indexes), 1)
        self.assertEqual(sum(len(row["nonAcceptedRecords"]) for row in ledgers), 156)
        self.assertEqual(sum(len(row["abstentions"]) for row in ledgers), 36)
        self.assertEqual(sum(len(row["deferredRecords"]) for row in ledgers), 0)
        self.assertEqual(sum(len(row["unresolvedIdentitySidecar"]["records"]) for row in predictions), 0)

    def test_index_binds_every_prediction_and_ledger_record_hash(self) -> None:
        """Each request index binds its exact tracked prediction and lifecycle rows."""
        predictions = {row["requestID"]: row for row in jsonl(PREDICTIONS_PATH)}
        ledgers = {row["requestID"]: row for row in jsonl(LIFECYCLE_PATH)}
        for row in jsonl(INDEX_PATH):
            request_id = row["requestID"]
            self.assertEqual(row["predictionRecordSha256"], predictions[request_id]["recordSha256"])
            self.assertEqual(row["lifecycleRecordSha256"], ledgers[request_id]["recordSha256"])
            for value in (row, predictions[request_id], ledgers[request_id]):
                body = dict(value); expected = body.pop("recordSha256")
                self.assertEqual(expected, sha256_bytes(canonical_json(body)))

    def test_absent_canonical_request_fails_closed(self) -> None:
        """A missing canonical namespace cannot produce a tracked freeze row."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(Step6CFreezeError, "canonical request artifacts absent"):
                _build_request_records(1, {"requestID": "missing"}, Path(directory))


if __name__ == "__main__":
    unittest.main()
