"""Tests for deterministic Publication M2-B3 evidence-coordinate guidance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from src.extraction.llm.publications.evidence_coordinate_guide import (
    COORDINATE_GUIDE_PATTERN,
    audit_evidence_coordinate_guide,
    build_coordinate_guided_provider_input,
    build_evidence_coordinate_guide,
)
from src.extraction.llm.publications.openai_provider import build_provider_input
from src.extraction.llm.publications.request_builder import canonical_json
from src.extraction.llm.publications.run_publication_coordinate_guided_development_smoke import (
    PROMPT_PATH,
    PROMPT_VERSION,
    build_dev_size_report,
    build_m2b3_request,
    run_coordinate_guided_live_smoke,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
M2B2_DIR = PROJECT_ROOT / "data/curation/papers/m2/b2"


def _synthetic_source(text: str, document_start: int = 100) -> dict[str, object]:
    """Create a minimal source-unit record for deterministic guide tests."""

    return {
        "sourceUnitID": "pub:test:sec:0001:unit:0001",
        "text": text,
        "textHash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "startOffsetInDocument": document_start,
    }


class EvidenceCoordinateGuideTests(unittest.TestCase):
    """Prove guide positions are exact, deterministic, Unicode-safe, and auxiliary."""

    def test_generation_is_byte_deterministic_and_exact(self) -> None:
        """Repeated construction yields identical canonical bytes and exact slices."""

        source = _synthetic_source("Alpha, beta!\nGamma.")
        first = build_evidence_coordinate_guide(source)
        second = build_evidence_coordinate_guide(source)
        self.assertEqual(canonical_json(first), canonical_json(second))
        for entry in first["entries"]:
            start, end = entry["startOffsetInUnit"], entry["endOffsetInUnit"]
            self.assertEqual(source["text"][start:end], entry["tokenText"])
            self.assertEqual(entry["startOffsetInDocument"], 100 + start)
            self.assertEqual(entry["endOffsetInDocument"], 100 + end)

    def test_records_are_ordered_nonoverlapping_and_cover_nonwhitespace_once(self) -> None:
        """Every non-whitespace code point belongs to one and only one token."""

        source = _synthetic_source("One  two\t+\nthree.")
        guide = build_evidence_coordinate_guide(source)
        audit = audit_evidence_coordinate_guide(source, guide)
        self.assertTrue(audit["valid"], audit["findings"])
        previous_end = 0
        coverage = [0] * len(source["text"])
        for entry in guide["entries"]:
            self.assertGreaterEqual(entry["startOffsetInUnit"], previous_end)
            previous_end = entry["endOffsetInUnit"]
            for offset in range(entry["startOffsetInUnit"], entry["endOffsetInUnit"]):
                coverage[offset] += 1
        self.assertEqual(
            coverage,
            [0 if character.isspace() else 1 for character in source["text"]],
        )

    def test_repeated_tokens_retain_distinct_match_positions(self) -> None:
        """Identical token text is represented by distinct regex spans, not search."""

        guide = build_evidence_coordinate_guide(_synthetic_source("same same same"))
        same = [entry for entry in guide["entries"] if entry["tokenText"] == "same"]
        self.assertEqual(
            [(entry["startOffsetInUnit"], entry["endOffsetInUnit"]) for entry in same],
            [(0, 4), (5, 9), (10, 14)],
        )

    def test_unicode_offsets_are_code_points_not_encoded_units(self) -> None:
        """Accented, scientific, and astral characters use Python code-point offsets."""

        text = "ASCII café Δ ± 𝄞 end"
        source = _synthetic_source(text, 1000)
        guide = build_evidence_coordinate_guide(source)
        self.assertTrue(audit_evidence_coordinate_guide(source, guide)["valid"])
        astral = next(entry for entry in guide["entries"] if entry["tokenText"] == "𝄞")
        self.assertEqual(astral["endOffsetInUnit"] - astral["startOffsetInUnit"], 1)
        self.assertNotEqual(len(text.encode("utf-8")), len(text))
        self.assertEqual(
            astral["startOffsetInDocument"],
            1000 + text.index("𝄞"),
        )

    def test_dev04_guide_contains_all_preserved_b2_literal_boundaries(self) -> None:
        """Guide tokens delimit the four independently known B2 literal occurrences."""

        request = build_m2b3_request()
        source = request["sourceUnit"]
        guide = build_evidence_coordinate_guide(source)
        entries = guide["entries"]
        by_start = {entry["startOffsetInUnit"]: entry for entry in entries}
        by_end = {entry["endOffsetInUnit"]: entry for entry in entries}
        preserved = json.loads(
            (M2B2_DIR / "publication_m2b2_exact_structured_model_output.json").read_text(
                encoding="utf-8"
            )
        )
        observed = []
        for evidence in preserved["evidenceSpans"]:
            literal = evidence["evidenceText"]
            self.assertEqual(source["text"].count(literal), 1)
            actual_start = source["text"].index(literal)
            actual_end = actual_start + len(literal)
            self.assertIn(actual_start, by_start)
            self.assertIn(actual_end, by_end)
            self.assertTrue(literal.startswith(by_start[actual_start]["tokenText"]))
            observed.append(
                (
                    actual_start,
                    actual_end,
                    source["startOffsetInDocument"] + actual_start,
                    source["startOffsetInDocument"] + actual_end,
                )
            )
        self.assertEqual(
            observed,
            [
                (156, 291, 27356, 27491),
                (293, 392, 27493, 27592),
                (398, 490, 27598, 27690),
                (491, 583, 27691, 27783),
            ],
        )

    def test_provider_input_appends_guide_without_replacing_source_text(self) -> None:
        """The new B3 presentation extends, but does not alter, historical input bytes."""

        request = build_m2b3_request()
        guide = build_evidence_coordinate_guide(request["sourceUnit"])
        current = build_provider_input(request)
        guided = build_coordinate_guided_provider_input(request, guide)
        self.assertTrue(guided.startswith(current))
        bounded_json = current.split(
            b"\n\nBounded trusted development request JSON:\n", 1
        )[1]
        projected = json.loads(bounded_json.decode("utf-8"))
        self.assertEqual(projected["sourceUnit"]["text"], request["sourceUnit"]["text"])
        self.assertGreater(len(guided), len(current))

    def test_prompt_v012_is_bound_and_v011_is_still_frozen(self) -> None:
        """B3 binds its new narrow prompt while accepted v0.1.1 stays byte-identical."""

        old_prompt = PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.1.txt"
        self.assertEqual(
            hashlib.sha256(old_prompt.read_bytes()).hexdigest(),
            "368d91f7ac8c6011a670002d1fdbc53215428292ed9ba0198d2f6a20929aa3eb",
        )
        request = build_m2b3_request()
        self.assertEqual(request["prompt"]["version"], PROMPT_VERSION)
        self.assertEqual(request["prompt"]["sha256"], hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest())
        self.assertIn("Do not estimate offsets by counting characters in serialized JSON", request["prompt"]["text"])

    def test_offline_size_report_covers_only_dev01_through_dev10(self) -> None:
        """The requested diagnostic contains ten deterministic rows and no network calls."""

        first = build_dev_size_report()
        second = build_dev_size_report()
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(first["networkCalls"], 0)
        self.assertEqual(
            [row["developmentID"] for row in first["units"]],
            [f"DEV-{index:02d}" for index in range(1, 11)],
        )
        for row in first["units"]:
            self.assertGreater(row["coordinateGuideEntryCount"], 0)
            self.assertGreater(row["providerInputByteIncrease"], row["canonicalCoordinateGuideBytes"])

    def test_accepted_authorities_and_live_artifacts_are_byte_identical(self) -> None:
        """Representative frozen authorities and authentic M2 outputs retain accepted hashes."""

        accepted_hashes = {
            "schemas/publication_candidate_output.schema.json": "50132ce01a16a21736f65e4b5d4b0354b3d1c53f07878352159d6ff36e94fce2",
            "src/extraction/llm/publications/publication_target_inventory.yaml": "6401c15b861c2362b67e03d56acd4a7304964f595d706311fd4f149eb69b3a5e",
            "src/extraction/llm/publications/request_builder.py": "9f45a128b09e05d174868eef072d84727844cecb72e473818fca9f08da405a21",
            "src/extraction/llm/publications/response_parser.py": "8f5ee5c455868240f8de8451611999c82354873cd4422a2d311de0566146eec2",
            "src/extraction/llm/publications/candidate_validation.py": "8c6074aa5708f519b73612ff7f1574de8311180d7b4a0e36551f6529415611d9",
            "data/curation/papers/m2/publication_m2a_exact_raw_model_output.json": "6c16dfe0c46806f7918a5e911a9c7aa5e4324fdb7baa57a92603f07d998f08ec",
            "data/curation/papers/m2/b1/publication_m2b1_attempt4_exact_structured_model_output.json": "444c10228ddffbfd30458752dfd8e2532dacb3ada44742ed06c5e07c6de4b68c",
            "data/curation/papers/m2/b2/publication_m2b2_exact_structured_model_output.json": "4f1d05c83ba0a088c23c1080fdad96de3a0b6c916c6496ca3d8d7ef30b439d5d",
            "data/curation/papers/m2/b2/publication_m2b2_provider_api_response.json": "570369e79e27c2b88ab68e6efa149f1a3ca694e09a356189c16707cebb54e7f4",
        }
        for relative, expected in accepted_hashes.items():
            with self.subTest(path=relative):
                self.assertEqual(
                    hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest(),
                    expected,
                )

    def test_mocked_runner_makes_one_no_tool_call_and_replays(self) -> None:
        """A mocked response traverses B3 once and does not invoke external network."""

        payload = json.loads(
            (M2B2_DIR / "publication_m2b2_exact_structured_model_output.json").read_text(
                encoding="utf-8"
            )
        )
        calls = []

        def transport(_api_key: str, body: dict[str, object]) -> dict[str, object]:
            """Return one exact-model completed response after inspecting B3 controls."""

            calls.append(body)
            self.assertNotIn("tools", body)
            self.assertFalse(body["store"])
            self.assertEqual(body["model"], "gpt-5.6-sol")
            self.assertEqual(body["reasoning"], {"effort": "medium"})
            self.assertIn("Deterministic trusted evidence-coordinate guide JSON", body["input"])
            return {
                "id": "resp_m2b3_synthetic",
                "object": "response",
                "created_at": 1787922000,
                "status": "completed",
                "model": "gpt-5.6-sol",
                "error": None,
                "incomplete_details": None,
                "output": [
                    {
                        "type": "message",
                        "id": "msg_m2b3_synthetic",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": canonical_json(payload).decode("utf-8"),
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 100,
                    "total_tokens": 200,
                    "output_tokens_details": {"reasoning_tokens": 10},
                },
            }

        with tempfile.TemporaryDirectory() as directory:
            result = run_coordinate_guided_live_smoke(
                "synthetic-secret", output_dir=Path(directory), transport=transport
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["parserResult"]["parseStatus"], "parsed")
        self.assertTrue(result["replayByteIdentical"])
        self.assertEqual(result["guide"]["tokenization"]["pattern"], COORDINATE_GUIDE_PATTERN)


if __name__ == "__main__":
    unittest.main()
