"""Focused no-network tests for DEV-02 bounded-node-family diagnostic setup."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

import jsonschema

from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans
from src.extraction.llm.publications.dev02_bounded_node_family_stability import (
    FAMILIES, OUTPUT_ROOT, build_family_provider_input, build_family_request, derive_family_schema,
    family_definition_authority, prepare,
)
from src.extraction.llm.publications.request_builder import canonical_json


class BoundedNodeFamilyStabilityTests(unittest.TestCase):
    """Prove the diagnostic is narrow, deterministic, and no-call."""

    def test_exact_partition_excludes_special_targets(self) -> None:
        authority = family_definition_authority()
        flattened = [target["operationalTargetID"] for family in authority["families"] for target in family["targets"]]
        self.assertEqual(len(flattened), 40)
        self.assertEqual(len(set(flattened)), 40)
        self.assertFalse(set(flattened) & set(authority["excludedDeterministicContextTargetIDs"]))
        self.assertFalse(set(flattened) & set(authority["excludedDeferredResolutionTargetIDs"]))
        self.assertEqual([len(targets) for _, targets in FAMILIES.values()], [7, 4, 9, 7, 6, 7])

    def test_family_schema_is_node_only_and_target_locked(self) -> None:
        for family_id in FAMILIES:
            request = build_family_request(family_id)
            schema = derive_family_schema(request)
            expected = set(request["eligibleOperationalTargetIDs"])
            branches = schema["properties"]["candidateNodes"]["items"]["anyOf"]
            self.assertEqual({branch["properties"]["operationalTargetID"]["const"] for branch in branches}, expected)
            self.assertEqual(set(schema["$defs"]["abstention"]["properties"]["operationalTargetID"]["anyOf"][0]["enum"]), expected)
            self.assertEqual(schema["properties"]["candidateEdges"]["maxItems"], 0)
            self.assertEqual(schema["properties"]["deferredRecords"]["maxItems"], 0)
            serialized = json.dumps(schema, sort_keys=True, separators=(",", ":"))
            self.assertNotRegex(serialized, r"PUB-R-")
            self.assertTrue(set(re.findall(r"PUB-N-[A-Za-z0-9-]+", serialized)) <= expected)
            root = {key: value for key, value in schema.items() if key != "$defs"}

            def refs(value: object) -> set[str]:
                if isinstance(value, dict):
                    found = {value["$ref"].removeprefix("#/$defs/")} if isinstance(value.get("$ref"), str) and value["$ref"].startswith("#/$defs/") else set()
                    for child in value.values():
                        found.update(refs(child))
                    return found
                if isinstance(value, list):
                    return set().union(*(refs(child) for child in value))
                return set()

            reachable = refs(root)
            pending = list(reachable)
            while pending:
                name = pending.pop()
                for child in refs(schema["$defs"][name]):
                    if child not in reachable:
                        reachable.add(child)
                        pending.append(child)
            self.assertEqual(set(schema["$defs"]), reachable)
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate({"candidateNodes": [], "candidateEdges": [{}], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}, schema)

    def test_source_first_common_prefix_and_family_specific_surfaces(self) -> None:
        inputs = {}
        prefix_lengths = set()
        source_lengths = set()
        for family_id in FAMILIES:
            request = build_family_request(family_id)
            provider_input, prefix_length, source_length = build_family_provider_input(request)
            inputs[family_id] = provider_input
            prefix_lengths.add(prefix_length)
            source_lengths.add(source_length)
            self.assertNotIn(b"historical_diagnostic_node_pool", provider_input)
            self.assertNotIn(b"secondary_fixed_node_reference", provider_input)
            source_bytes = canonical_json(request["sourceUnit"])
            source_start = provider_input.index(source_bytes)
            self.assertLess(source_start + len(source_bytes), prefix_length)
            self.assertIn(b'"eligibleOperationalTargetIDs"', provider_input[prefix_length:])
            self.assertIn(b'"targetDefinitions"', provider_input[prefix_length:])
            self.assertEqual(set(request["eligibleOperationalTargetIDs"]), set(FAMILIES[family_id][1]))
        self.assertEqual(len(prefix_lengths), 1)
        self.assertEqual(len(source_lengths), 1)
        length = next(iter(prefix_lengths))
        self.assertEqual({value[:length] for value in inputs.values()}, {next(iter(inputs.values()))[:length]})

    def test_prepare_is_byte_identical_and_has_required_transport_settings(self) -> None:
        first = prepare()
        second = prepare()
        self.assertEqual(first, second)
        self.assertEqual(first["providerCalls"], 0)
        for record in first["familyPreflights"]:
            family = record["familyID"]
            r1 = OUTPUT_ROOT / family / "R1"
            r2 = OUTPUT_ROOT / family / "R2"
            self.assertEqual((r1 / "complete_request_body.json").read_bytes(), (r2 / "complete_request_body.json").read_bytes())
            self.assertEqual(record["model"], "gpt-5.6-sol")
            self.assertEqual(record["reasoningEffort"], "medium")
            self.assertEqual(record["maxOutputTokens"], 32768)
            self.assertFalse(record["store"])
            body = json.loads((r1 / "complete_request_body.json").read_text())
            self.assertFalse(body.get("background", False))
            provider_input = (r1 / "provider_input.txt").read_bytes()
            self.assertNotIn(b"historical_diagnostic_node_pool", provider_input)
            self.assertNotIn(b"secondary_fixed_node_reference", provider_input)
            self.assertIn("specializedSchemaByteCount", record)
            self.assertIn("completeRequestBodyByteCount", record)
        self.assertIn("commonProviderInputPrefixByteCount", first)
        self.assertIn("sourceUnitByteCount", first)

    def test_historical_pool_is_unreconciled_and_secondary_reference_is_46(self) -> None:
        prepare()
        historical = json.loads((OUTPUT_ROOT / "historical_diagnostic_node_pool.json").read_text())
        fixed = json.loads((OUTPUT_ROOT / "secondary_fixed_node_reference.json").read_text())
        self.assertEqual(historical["semanticReconciliation"]["status"], "pending")
        self.assertEqual({row["sourceRun"] for row in historical["sourceRunProvenance"]}, {"A4", "A7", "A8"})
        self.assertEqual(fixed["nodeCount"], 46)

    def test_existing_evidence_binding_remains_compatible(self) -> None:
        request = build_family_request("F1")
        literal = request["sourceUnit"]["text"][:20]
        payload = {"evidenceSpans": [{"evidenceSpanID": "evidence-0001", "evidenceText": literal, "locatorAnchor": None}]}
        _, binding = bind_evidence_spans(payload, request["sourceUnit"])
        self.assertEqual(binding["bindingStatus"], "bound")
