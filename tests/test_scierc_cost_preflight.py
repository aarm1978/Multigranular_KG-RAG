"""Focused offline provenance and arithmetic tests; no runtime execution."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import scierc_cost_preflight as p


class PlanningTests(unittest.TestCase):
    """Verify only completed artifacts and transparent planning arithmetic."""

    @classmethod
    def setUpClass(cls):
        """Read authentic smoke once with network prohibited."""
        with patch("socket.socket.connect", side_effect=AssertionError("NETWORK_PROHIBITED")):
            cls.smoke = p.verify_smoke()
            cls.inputs = p.read_json(p.INPUTS)
            cls.report = p.build_report(cls.smoke, cls.inputs)

    def test_smoke_identity_and_usage(self):
        """Require supplied terminal hash, byte parity and structural replay."""
        self.assertTrue(all(v is True for k,v in self.smoke["verification"].items()
                            if k not in {"structuralValidation", "goldCompared", "benchmarkMetricsComputed"}))
        self.assertEqual(self.smoke["terminal"]["usage"]["total_tokens"], 7406)
        self.assertEqual(self.smoke["locallyRecordedDispatchAttempts"], 1)
        self.assertEqual(self.smoke["serviceTier"], "default")

    def test_terminal_mismatch_stops_before_source(self):
        """A changed terminal cannot become a new accepted preservation."""
        with patch.object(p, "evidence", return_value={"sha256": "wrong"}):
            with self.assertRaisesRegex(ValueError, "TERMINAL_HASH_MISMATCH"):
                p.verify_smoke()

    def test_pricing_replacement_and_reasoning_subset(self):
        """Cache writes replace ordinary input; output includes reasoning once."""
        rates = self.inputs["usdPerMillionTokens"]
        self.assertEqual(p.price(2116,2113,0,5290,rates), 0.116377)
        self.assertEqual(p.price(100,0,100,0,rates), 0.00004)
        with self.assertRaises(ValueError):
            p.price(100,80,30,0,rates)
        baseline = self.report["outputLatencyScenarios"][1]
        self.assertEqual(baseline["nonReasoningOutputTokens"],154600)
        self.assertEqual(baseline["reasoningTokens"],374400)
        self.assertEqual(baseline["totalOutputTokens"],529000)

    def test_input_scaling_includes_overhead_once(self):
        """Complete-body scaling rounds per request without adding prompt twice."""
        self.assertEqual(p.estimate_inputs([9741]*100,9741,2116),[2116]*100)
        self.assertEqual(p.estimate_inputs([1],9741,2116),[1])
        self.assertEqual(self.report["inputEstimation"]["totalRequestBytes"],995967)
        self.assertEqual(len(self.report["inputEstimation"]["perRequestEstimatedTokens"]),100)

    def test_caps_timing_and_separate_scopes(self):
        """Output cap alone is not total spending; smoke is outside 100 requests."""
        self.assertEqual(self.report["officialPlannedGenerationPosts"],100)
        self.assertEqual(self.report["completedSmokePostsSeparate"],1)
        self.assertEqual(self.report["outputCapCostAloneUSD"],65.536)
        self.assertAlmostEqual(self.report["timeAndRateLimits"]["baselineSequentialSeconds"],9369.1190542)
        self.assertIsNone(self.report["timeAndRateLimits"]["accountRPM"])
        self.assertGreater(self.report["conditionalConservativePlanning"]["usd"],65.536)

    def test_candidate_mutation_rejected(self):
        """Candidate self-identity changes cannot silently enter accounting."""
        changed = deepcopy(p.read_json(p.CANDIDATE)); changed["logicalRequestCount"] = 99
        with patch.object(p,"read_json",return_value=changed):
            with self.assertRaisesRegex(ValueError,"CANDIDATE_SELF_HASH"):
                p.build_report(self.smoke,self.inputs)

    def test_reproducible_and_no_overwrite(self):
        """Outputs bind exact preservation bytes and reject divergent artifacts."""
        self.assertEqual(self.report["smokePreservationSha256"],p.a.sha256_bytes(p.encoded(self.smoke)))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"review.json"
            p.write_review(path,b"original"); p.write_review(path,b"original")
            with self.assertRaisesRegex(ValueError,"REVIEW_ARTIFACT_CONFLICT"):
                p.write_review(path,b"changed")
            self.assertEqual(path.read_bytes(),b"original")
