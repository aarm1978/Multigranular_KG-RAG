"""Focused synthetic T1/T2 coverage for Hub legacy and batch validation."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from src.extraction.llm.documents.candidate_validation import validate_procedure_candidate
from src.extraction.llm.documents.source_units import read_page_source_units
from src.extraction.llm.semantic_target_profiles import ONTOLOGY_PATH, check_target


class HubProcedureValidationTests(unittest.TestCase):
    """Check structure, independent evidence and holds without semantic acceptance."""

    def setUp(self) -> None:
        """Create a frozen synthetic page with multiple visible and held units."""
        text = ("# Guide\nPrepare café 🌊 inputs for the run.\nThis page describes the preparation procedure.\n"
                "Save the prepared inputs. Repeat Repeat.\n<Unknown>\nHidden text.\n</Unknown>\n"
                "{runtime}\n```python\nprint('example')\n```\n")
        url = "https://example.test/guide"
        self.page = {"page_key": "hub-page:" + url, "canonical_url": url,
            "corpus_path": "docs/guide.mdx", "source_path": "docs/guide.mdx", "source_group": "docs",
            "content_mdx": text, "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "file_sha256": "b" * 64,
            "headings": [{"ordinal": 1, "source_line": 1, "raw_text": "Guide", "level": 1}]}
        suffix = hashlib.sha256(url.encode()).hexdigest()[:20]
        self.page_id = "hub:page:" + suffix
        self.section = "hub:section:" + suffix + ":0001"
        self.mapping = {k: self.page[k] for k in ("page_key", "canonical_url", "content_sha256")}
        self.mapping["sections"] = [{"heading_ordinal": 1, "source_line": 1, "raw_text": "Guide", "section_id": self.section}]
        self.reader = read_page_source_units(self.page, accepted_section_mapping=self.mapping)
        self.payload = {
            "node": {"candidateID": "procedure-1", "class": "Procedure", "inventoryId": "A-DC05",
                     "label": "Prepare inputs", "evidence": [self.fragment("Prepare café 🌊 inputs for the run.")]},
            "edge": {"candidateID": "edge-1", "relation": "hasProcedure", "inventoryId": "C-DC20",
                     "sourceID": self.page_id, "targetCandidateID": "procedure-1",
                     "evidence": [self.fragment("This page describes the preparation procedure.")]}}

    def fragment(self, quote: str, **extra) -> dict:
        """Select a synthetic unit without inventing candidate coordinates."""
        unit = next(u for u in self.reader["sourceUnits"] if quote in u["text"])
        return {"sourceUnitID": unit["sourceUnitID"], "evidenceText": quote, **extra}

    def validate(self, payload=None, **kwargs) -> dict:
        """Pass the trusted page and reader independently of candidate content."""
        return validate_procedure_candidate(kwargs.pop("page", self.page), kwargs.pop("reader", self.reader),
            self.payload if payload is None else payload, accepted_page_id=kwargs.pop("page_id", self.page_id),
            accepted_section_mapping=kwargs.pop("mapping", self.mapping), **kwargs)

    def test_valid_structure_and_separate_evidence(self) -> None:
        """A validated pair establishes no procedural meaning or KG authorization."""
        result = self.validate()
        node, edge = result["candidates"]
        self.assertEqual([c["disposition"] for c in result["candidates"]], ["validated", "validated"])
        self.assertNotEqual(node["boundEvidence"][0]["evidenceText"], edge["boundEvidence"][0]["evidenceText"])
        self.assertTrue(edge["endpointsBound"])
        self.assertEqual(edge["targetProfileCheck"]["profileResult"], check_target("ciroh_hub", "C-DC20",
            relation_name="hasProcedure", source_class_id="A-DC01", target_class_id="A-DC05"))
        self.assertFalse(check_target("github", "C-DC20", relation_name="hasProcedure",
            source_class_id="A-DC01", target_class_id="A-DC05")["structuralScopePass"])
        self.assertEqual(result["semanticStatus"], "not_evaluated")
        self.assertFalse(result["graphAcceptance"])
        self.assertFalse(result["kgAuthorization"])
        same = deepcopy(self.payload)
        same["edge"]["evidence"] = deepcopy(same["node"]["evidence"])
        checked = self.validate(same)
        self.assertEqual(checked["candidates"][1]["disposition"], "validated")
        self.assertEqual(len(checked["candidates"][1]["evidenceBindings"]), 1)

    def test_multiple_units_sections_and_original_coordinates(self) -> None:
        """Preserve each fragment and unverified contribution without joining text."""
        payload = deepcopy(self.payload)
        payload["node"]["evidence"][0]["contribution"] = "States preparation goal"
        payload["node"]["evidence"].append(self.fragment("Save the prepared inputs.", contribution="States final action"))
        checked = self.validate(payload)
        node = checked["candidates"][0]
        self.assertEqual(node["disposition"], "validated")
        self.assertEqual(len({s["sourceUnitID"] for s in node["boundEvidence"]}), 2)
        for index, span in enumerate(node["boundEvidence"]):
            quote = payload["node"]["evidence"][index]["evidenceText"]
            text = self.page["content_mdx"]
            start = text.index(quote)
            self.assertEqual((span["startOffsetInAuthority"], span["endOffsetInAuthority"]), (start, start + len(quote)))
            self.assertEqual(span["startLine"], text[:start].count("\n") + 1)
            self.assertEqual(span["endLine"], span["startLine"])
            self.assertEqual(span["sectionID"], self.section)
            self.assertEqual(span["sourceArtifactID"], self.page_id)
            self.assertEqual(span["authorityTextSha256"], self.page["content_sha256"])
            self.assertEqual(span["evidenceHash"], hashlib.sha256(quote.encode()).hexdigest())
            for key in ("page_key", "canonical_url", "content_sha256", "file_sha256", "source_path", "corpus_path"):
                self.assertEqual(span[key], self.page[key])
            self.assertEqual(node["evidenceBindings"][index]["originalFragment"], payload["node"]["evidence"][index])
        no_section = read_page_source_units(self.page)
        self.assertIsNone(self.validate(reader=no_section, mapping=None)["candidates"][0]["boundEvidence"][0]["sectionID"])
        del payload["node"]["evidence"][1]["contribution"]
        self.assertEqual(self.validate(payload)["candidates"][0]["disposition"], "rejected_invalid_assertion")

    def test_invalid_targets_endpoints_quotes_and_dependencies(self) -> None:
        """Retain specific failures and never validate an edge to an invalid node."""
        for kind, field, value in (("node", "class", "Step"), ("node", "inventoryId", "A-DC06"),
                ("node", "inventoryId", "A-DC08"), ("node", "inventoryId", "A-DOM12"),
                ("edge", "relation", "hasStep"), ("edge", "inventoryId", "C-DC10"),
                ("edge", "sourceID", "procedure-1"), ("edge", "sourceID", "hub:page:other"),
                ("node", "source_path", "injected")):
            payload = deepcopy(self.payload)
            payload[kind][field] = value
            checked = self.validate(payload)["candidates"]
            self.assertEqual(checked[0 if kind == "node" else 1]["disposition"], "rejected_invalid_assertion")
            if kind == "node":
                self.assertEqual(checked[1]["disposition"], "unresolved_endpoint")
        for kind in ("node", "edge"):
            for quote in ("fabricated", "Repeat", ""):
                payload = deepcopy(self.payload)
                payload[kind]["evidence"] = [{**self.fragment("Repeat"), "evidenceText": quote}]
                checked = self.validate(payload)["candidates"]
                self.assertEqual(checked[0 if kind == "node" else 1]["disposition"], "failed_source_or_evidence_binding")
                if kind == "node":
                    self.assertEqual(checked[1]["disposition"], "unresolved_endpoint")
        located = deepcopy(self.payload)
        located["node"]["evidence"] = [self.fragment("Repeat", locatorAnchor="Repeat.")]
        self.assertEqual(self.validate(located)["candidates"][0]["disposition"], "validated")
        for evidence in ([], [self.fragment("Prepare café", startOffsetInAuthority=8)],
                         [self.fragment("Prepare café", content_sha256=self.page["content_sha256"])],
                         [{"sourceUnitID": "other-page-unit", "evidenceText": "Prepare café"}]):
            payload = deepcopy(self.payload)
            payload["node"]["evidence"] = evidence
            checked = self.validate(payload)["candidates"]
            self.assertNotEqual(checked[0]["disposition"], "validated")
            self.assertEqual(checked[1]["disposition"], "unresolved_endpoint")
        for target in (None, "unknown"):
            payload = deepcopy(self.payload)
            payload["edge"]["targetCandidateID"] = target
            self.assertEqual(self.validate(payload)["candidates"][1]["disposition"], "unresolved_endpoint")
        payload = deepcopy(self.payload)
        payload["node"] = None
        payload["edge"]["evidence"][0]["evidenceText"] = "fake"
        result = self.validate(payload)
        self.assertIn("target_endpoint_unresolved", repr(result["diagnostics"]))
        self.assertIn("evidence_quote_unbound", repr(result["diagnostics"]))

    def test_visibility_integrity_immutability_and_zero_effects(self) -> None:
        """Review each unit; permit only ontology reads and no external effects."""
        self.assertTrue(self.reader["reviewRequired"])
        self.assertEqual(self.validate()["candidates"][0]["disposition"], "validated")
        held = deepcopy(self.payload)
        held["node"]["evidence"] = [self.fragment("print('example')")]
        result = self.validate(held)
        self.assertEqual(result["candidates"][0]["disposition"], "needs_review")
        self.assertEqual(result["candidates"][1]["disposition"], "unresolved_endpoint")
        mixed = deepcopy(self.payload)
        mixed["node"]["evidence"][0]["contribution"] = "Proposed goal"
        mixed["node"]["evidence"].append(self.fragment("print('example')", contribution="Proposed action"))
        partial = self.validate(mixed)["candidates"]
        self.assertEqual(partial[0]["disposition"], "needs_review")
        self.assertEqual(len(partial[0]["boundEvidence"]), 1)
        self.assertEqual(partial[1]["disposition"], "unresolved_endpoint")
        for kind in ("node", "edge"):
            reader = deepcopy(self.reader)
            reader["diagnostics"].append({"status": "needs_review", "reason": "uncertain visibility",
                "sourceUnitID": self.payload[kind]["evidence"][0]["sourceUnitID"]})
            self.assertEqual(self.validate(reader=reader)["candidates"][0 if kind == "node" else 1]["disposition"], "needs_review")
        for page in ({**self.page, "content_sha256": "0" * 64}, {**self.page, "content_mdx": "changed"},
                     {**self.page, "page_key": "other"}, {**self.page, "source_path": "other.mdx"}):
            self.assertEqual(self.validate(page=page)["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.validate(page_id="wrong")["status"], "failed_source_or_evidence_binding")
        reader = deepcopy(self.reader)
        reader["sourceUnits"][1]["startOffsetInAuthority"] = 0
        self.assertEqual(self.validate(reader=reader)["candidates"][0]["disposition"], "failed_source_or_evidence_binding")
        before = deepcopy((self.page, self.reader, self.mapping, self.payload))
        original_open = io.open

        def authority_only(path, mode="r", *args, **kwargs):
            """Allow only read access to the frozen ontology specification."""
            self.assertEqual(Path(path), ONTOLOGY_PATH)
            self.assertEqual(mode, "rb")
            return original_open(path, mode, *args, **kwargs)

        with patch("io.open", side_effect=authority_only), patch("builtins.open", side_effect=AssertionError("No IO")), \
             patch("socket.socket", side_effect=AssertionError("No network")):
            first, second = self.validate(), self.validate()
        self.assertEqual(first, second)
        renamed = deepcopy(self.payload)
        renamed["node"]["candidateID"] = "procedure-2"
        renamed["edge"]["targetCandidateID"] = "procedure-2"
        other = self.validate(renamed)
        self.assertNotEqual(first["candidates"][0]["sourceLocalCandidateID"],
                            other["candidates"][0]["sourceLocalCandidateID"])
        altered_page = {**self.page, "content_mdx": self.page["content_mdx"] + "Additional prose.\n"}
        altered_page["content_sha256"] = hashlib.sha256(altered_page["content_mdx"].encode()).hexdigest()
        altered_mapping = {**self.mapping, "content_sha256": altered_page["content_sha256"]}
        altered_reader = read_page_source_units(altered_page, accepted_section_mapping=altered_mapping)
        revised = deepcopy(self.payload)
        for kind in ("node", "edge"):
            fragment = revised[kind]["evidence"][0]
            fragment["sourceUnitID"] = next(u["sourceUnitID"] for u in altered_reader["sourceUnits"]
                                            if fragment["evidenceText"] in u["text"])
        changed = self.validate(revised, page=altered_page, reader=altered_reader, mapping=altered_mapping)
        self.assertEqual(changed["candidates"][0]["disposition"], "validated")
        self.assertNotEqual(first["candidates"][0]["sourceLocalCandidateID"],
                            changed["candidates"][0]["sourceLocalCandidateID"])
        self.assertEqual((self.page, self.reader, self.mapping, self.payload), before)
        self.assertEqual(first["originalPayload"], self.payload)
        first["originalPayload"]["node"]["label"] = "changed copy"
        self.assertEqual(self.payload, before[3])
        self.assertNotIn("nodes", second)
        self.assertNotIn("edges", second)
        self.assertNotIn("abstained_no_evidence", repr(second))




class HubBatchValidationTests(unittest.TestCase):
    """Synthetic complete-profile checks, including dependency closure."""

    def setUp(self):
        """Reuse only the synthetic page fixture, without running legacy tests."""
        fixture = HubProcedureValidationTests()
        fixture.setUp()
        self.page, self.reader = fixture.page, fixture.reader
        self.mapping, self.page_id, self.section = fixture.mapping, fixture.page_id, fixture.section
        self.fragment = fixture.fragment
        from src.extraction.llm.semantic_target_profiles import get_profile
        self.profile = get_profile("ciroh_hub")
        self.endpoints = [dict(endpointID="exact-dataset", inventoryId="A-D01", **{"class": "DatasetResource"}),
                          dict(endpointID="exact-repo", inventoryId="A-C01", **{"class": "Repository"})]

    def ref(self, identifier, kind="candidate_node"):
        """Construct an explicit reference without inferring identity."""
        return {"referenceType": kind, "referenceID": identifier}

    def node(self, identifier, cid=None):
        """Create a literal-backed node with its frozen declaration name."""
        row = {"candidateID": cid or identifier, "inventoryId": identifier,
               "class": self.profile["entities"][identifier]["declaration"]["name"],
               "label": identifier, "evidence": [self.fragment("Prepare café 🌊 inputs for the run.")]}
        if identifier in {"A-D01", "A-C01"}:
            row["endpoint"] = self.ref("exact-dataset" if identifier == "A-D01" else "exact-repo", "accepted_endpoint")
        return row

    def edge(self, identifier, source, target, cid=None):
        """Construct independently supplied edge evidence."""
        return {"candidateID": cid or identifier, "inventoryId": identifier,
            "relation": self.profile["relations"][identifier]["declaration"]["name"],
            "source": source, "target": target,
            "evidence": [self.fragment("This page describes the preparation procedure.")]}

    def batch(self):
        """Cover every frozen entity/relation, using explicit parent paths."""
        nodes = [self.node(i) for i in self.profile["entities"]]
        owner = self.ref(self.page_id, "accepted_endpoint")
        signatures = {"C-DC17": (owner, self.ref("A-DOM03a")),
            "C-DC19": (self.ref("A-DOM02"), self.ref("A-DOM03b")),
            "C-DC07": (owner, self.ref("A-DOM02")), "C-DC16": (owner, self.ref("A-DOM03c")),
            "C-DC27": (owner, self.ref("A-D01")), "C-DC28": (owner, self.ref("A-P13")),
            "D-22": (self.ref("A-DOM03d"), self.ref("A-C01")),
            "C-DC20": (owner, self.ref("A-DC05")), "C-DC10": (self.ref("A-DC05"), self.ref("A-DC06")),
            "C-DC09": (self.ref("A-DC05"), self.ref("A-C11")),
            "C-DC12": (self.ref("A-DC06"), self.ref("A-DC08")),
            "C-DC11": (self.ref("A-DC05"), self.ref("A-DOM12"))}
        for row in nodes:
            path = {"A-DC06": ["C-DC20", "C-DC10"], "A-DC08": ["C-DC20", "C-DC10", "C-DC12"],
                    "A-DOM12": ["C-DC20", "C-DC11"]}.get(row["inventoryId"])
            if path:
                row["parentPath"] = [self.ref(i, "candidate_edge") for i in path]
        return {"candidateNodes": nodes, "candidateEdges": [self.edge(i, *signatures[i]) for i in self.profile["relations"]]}

    def validate(self, payload=None, **kwargs):
        """Call only the offline batch entry point."""
        from src.extraction.llm.documents.candidate_validation import validate_hub_candidates
        return validate_hub_candidates(kwargs.pop("page", self.page), kwargs.pop("reader", self.reader),
            self.batch() if payload is None else payload, accepted_page_id=kwargs.pop("page_id", self.page_id),
            accepted_section_mapping=self.mapping, accepted_endpoints=kwargs.pop("endpoints", self.endpoints), **kwargs)

    def index(self, result):
        """Index detached results by authentic candidate identifier."""
        return {r["candidateID"]: r for r in result["candidateChecks"]}

    def test_complete_allowlist_signatures_and_pending_gates(self):
        """Every active target binds, while parent/Method semantics remain pending."""
        result = self.validate()
        records = self.index(result)
        self.assertEqual(set(records), set(self.profile["entities"]) | set(self.profile["relations"]))
        for rec in records.values():
            self.assertTrue(rec["targetProfileCheck"]["targetStructuralCompatibility"], rec)
            self.assertTrue(rec["boundEvidence"])
            self.assertIn(rec["disposition"], {"validated", "suppressed_duplicate", "unresolved_condition"}, rec)
            self.assertFalse(rec["kgAuthorization"])
            self.assertEqual(rec["semanticStatus"], "not_evaluated")
        for key in ("A-DC06", "A-DC08", "A-DOM12", "C-DC10", "C-DC12", "C-DC11", "A-P13", "C-DC28"):
            self.assertEqual(records[key]["disposition"], "unresolved_condition")
        self.assertEqual(records["C-DC20"]["disposition"], "validated")
        for source, target in (("A-DOM02", "A-DOM03e"), ("A-DOM03e", "A-DOM02")):
            payload = {"candidateNodes": [self.node(source), self.node(target)],
                       "candidateEdges": [self.edge("C-DC19", self.ref(source), self.ref(target))]}
            self.assertEqual(self.index(self.validate(payload))["C-DC19"]["disposition"], "validated")
        for identifier in self.profile["relations"]:
            edge = self.edge(identifier, self.ref("exact-dataset", "accepted_endpoint"),
                             self.ref("exact-repo", "accepted_endpoint"))
            payload = {"candidateNodes": [], "candidateEdges": [edge]}
            self.assertEqual(self.index(self.validate(payload))[identifier]["disposition"], "rejected_invalid_assertion")

    def test_multiunit_coordinates_duplicates_and_exact_endpoints(self):
        """Original Unicode/Section coordinates and repeated citations survive."""
        payload = self.batch()
        tool = next(n for n in payload["candidateNodes"] if n["inventoryId"] == "A-DOM02")
        tool["evidence"] = [self.fragment("Prepare café 🌊 inputs for the run.", contribution="identity"),
                            self.fragment("Save the prepared inputs.", contribution="context")]
        tool["evidence"].append(deepcopy(tool["evidence"][0]))
        duplicate = deepcopy(next(e for e in payload["candidateEdges"] if e["inventoryId"] == "C-DC07"))
        duplicate["candidateID"] = "duplicate"
        payload["candidateEdges"].append(duplicate)
        records = self.index(self.validate(payload))
        self.assertTrue(records["duplicate"]["suppressedDuplicate"])
        self.assertTrue(records["duplicate"]["boundEvidence"])
        self.assertEqual(len(records["A-DOM02"]["boundEvidence"]), 3)
        for span in records["A-DOM02"]["boundEvidence"]:
            lo, hi = span["startOffsetInAuthority"], span["endOffsetInAuthority"]
            self.assertEqual(self.page["content_mdx"][lo:hi], span["evidenceText"])
            self.assertEqual(span["sectionID"], self.section)
            self.assertEqual(span["content_sha256"], self.page["content_sha256"])
            self.assertEqual(span["evidenceHash"], hashlib.sha256(span["evidenceText"].encode()).hexdigest())
        accepted = [{"assertionID": "already", "inventoryId": "C-DC27", "relation": "describesDataset",
                     "sourceID": self.page_id, "targetID": "exact-dataset"}]
        self.assertEqual(self.index(self.validate(accepted_assertions=accepted))["C-DC27"]["duplicateOf"], ["already"])
        self.assertNotIn("validated", [self.index(self.validate(endpoints=[]))["A-D01"]["disposition"]])
        self.assertEqual(self.validate(page_id="invented")["status"], "failed_source_or_evidence_binding")

    def test_failure_isolation_paths_and_order_independence(self):
        """A failed required relation holds descendants, not unrelated nodes."""
        payload = self.batch()
        next(e for e in payload["candidateEdges"] if e["inventoryId"] == "C-DC20")["evidence"] = []
        records = self.index(self.validate(payload))
        for key in ("A-DC06", "A-DC08", "A-DOM12", "C-DC10", "C-DC12", "C-DC11"):
            self.assertEqual(records[key]["disposition"], "unresolved_endpoint", records[key])
        self.assertEqual(records["A-DC05"]["disposition"], "validated")
        self.assertEqual(records["C-DC07"]["disposition"], "validated")
        payload["candidateNodes"].reverse()
        payload["candidateEdges"].reverse()
        reversed_records = self.index(self.validate(payload))
        self.assertEqual({k: r["disposition"] for k, r in records.items()},
                         {k: r["disposition"] for k, r in reversed_records.items()})
        payload = self.batch()
        next(n for n in payload["candidateNodes"] if n["inventoryId"] == "A-DC08")["parentPath"] = []
        records = self.index(self.validate(payload))
        self.assertEqual(records["A-DC08"]["disposition"], "unresolved_endpoint")
        self.assertEqual(records["C-DC12"]["disposition"], "unresolved_endpoint")
        self.assertEqual(records["A-DOM12"]["disposition"], "unresolved_condition")

    def test_fence_isolation_visibility_and_scoped_source_failures(self):
        """Fenced content is possible Example context, never Parameter prose."""
        payload = self.batch()
        for node in payload["candidateNodes"]:
            if node["inventoryId"] in {"A-DC08", "A-DOM12"}:
                node["evidence"] = [self.fragment("print('example')")]
        records = self.index(self.validate(payload))
        self.assertEqual(records["A-DC08"]["contextDisposition"], "possible_example_context")
        self.assertEqual(records["A-DC08"]["disposition"], "unresolved_condition")
        self.assertEqual(records["A-DOM12"]["disposition"], "needs_review")
        self.assertFalse(records["A-DOM12"]["boundEvidence"])
        reader = deepcopy(self.reader)
        bad_uid = self.fragment("Save the prepared inputs.")["sourceUnitID"]
        reader["diagnostics"].append({"status": "failed_source_or_evidence_binding", "sourceUnitID": bad_uid, "reason": "local_failure"})
        payload = self.batch()
        payload["candidateNodes"][0]["evidence"] = [self.fragment("Save the prepared inputs.")]
        result = self.validate(payload, reader=reader)
        records = self.index(result)
        self.assertFalse(result["inputComplete"])
        self.assertEqual(records[payload["candidateNodes"][0]["candidateID"]]["disposition"], "failed_source_or_evidence_binding")
        self.assertEqual(records["C-DC20"]["disposition"], "validated")
        reader["diagnostics"][-1].pop("sourceUnitID")
        self.assertEqual(self.index(self.validate(reader=reader))["C-DC20"]["disposition"], "failed_source_or_evidence_binding")

    def test_untrusted_metadata_quotes_and_global_failures(self):
        """Malformed identifiable assertions isolate; unidentified envelopes fail."""
        for change in ({"inventoryId": "D-26"}, {"inventoryId": "A-DOM03"}, {"inventoryId": []}, {"gates": {"accepted_procedure_or_step_parent": True}},
                       {"evidence": [{"sourceUnitID": self.reader["sourceUnits"][0]["sourceUnitID"], "evidenceText": "fabrication", "startLine": 1}]}):
            payload = {"candidateNodes": [self.node("A-DOM02"), self.node("A-DC05")],
                "candidateEdges": [self.edge("C-DC20", self.ref(self.page_id, "accepted_endpoint"), self.ref("A-DC05"))]}
            payload["candidateNodes"][0].update(change)
            records = self.index(self.validate(payload))
            self.assertEqual(records[payload["candidateNodes"][0]["candidateID"]]["disposition"], "rejected_invalid_assertion")
            self.assertEqual(records["C-DC20"]["disposition"], "validated")
        for quote in ("fabrication", "Repeat"):
            payload = {"candidateNodes": [self.node("A-DOM02")], "candidateEdges": []}
            payload["candidateNodes"][0]["evidence"] = [{**self.fragment("Repeat"), "evidenceText": quote}]
            records = self.index(self.validate(payload))
            self.assertEqual(records[payload["candidateNodes"][0]["candidateID"]]["disposition"], "failed_source_or_evidence_binding")
        payload = self.batch()
        payload["candidateNodes"].append({})
        self.assertEqual(self.validate(payload)["status"], "processing_failed")
        payload = self.batch()
        payload["candidateNodes"].append(deepcopy(payload["candidateNodes"][0]))
        self.assertEqual(self.validate(payload)["status"], "processing_failed")
        page = deepcopy(self.page)
        page["content_mdx"] += "tamper"
        self.assertEqual(self.validate(page=page)["status"], "failed_source_or_evidence_binding")

    def test_accepted_parent_path_immutability_and_zero_external_effects(self):
        """Exact accepted parents support paths without authorizing semantics."""
        payload = self.batch()
        originals = deepcopy((payload, self.page, self.reader, self.mapping, self.endpoints))
        original_open = io.open

        def guarded_open(file, mode="r", *args, **kwargs):
            """Permit only frozen ontology specification reads."""
            self.assertEqual(Path(file).resolve(), ONTOLOGY_PATH.resolve())
            self.assertNotIn("w", mode)
            return original_open(file, mode, *args, **kwargs)

        with patch("io.open", side_effect=guarded_open), patch("socket.socket", side_effect=AssertionError("network")):
            result = self.validate(payload)
        self.assertEqual((payload, self.page, self.reader, self.mapping, self.endpoints), originals)
        self.assertEqual(result, self.validate(payload))
        result["originalPayload"]["candidateNodes"][0]["label"] = "detached"
        self.assertEqual(payload, originals[0])
        self.assertFalse(result["kgAuthorization"])
        external = self.endpoints + [{"endpointID": "accepted-procedure", "inventoryId": "A-DC05", "class": "Procedure"}]
        node = self.node("A-DC08", "example")
        node["parentPath"] = [self.ref("accepted-parent", "accepted_assertion"), self.ref("attachment", "candidate_edge")]
        edge = self.edge("C-DC12", self.ref("accepted-procedure", "accepted_endpoint"), self.ref("example"), "attachment")
        assertion = {"assertionID": "accepted-parent", "inventoryId": "C-DC20", "relation": "hasProcedure",
                     "sourceID": self.page_id, "targetID": "accepted-procedure"}
        records = self.index(self.validate({"candidateNodes": [node], "candidateEdges": [edge]}, endpoints=external,
                                          accepted_assertions=[assertion]))
        self.assertTrue(records["example"]["parentPathStructurallyLinked"])
        self.assertEqual(records["example"]["disposition"], "unresolved_condition")
        # Exact accepted dependent endpoints still require the page-local path.
        external.append({"endpointID": "accepted-example", "inventoryId": "A-DC08", "class": "Example"})
        edge["target"] = self.ref("accepted-example", "accepted_endpoint")
        edge["parentPath"] = [self.ref("accepted-parent", "accepted_assertion")]
        records = self.index(self.validate({"candidateNodes": [], "candidateEdges": [edge]}, endpoints=external,
                                          accepted_assertions=[assertion]))
        self.assertTrue(records["attachment"]["parentPathStructurallyLinked"])
        self.assertEqual(records["attachment"]["disposition"], "unresolved_condition")
        edge.pop("parentPath")
        records = self.index(self.validate({"candidateNodes": [], "candidateEdges": [edge]}, endpoints=external,
                                          accepted_assertions=[assertion]))
        self.assertEqual(records["attachment"]["disposition"], "unresolved_endpoint")


    def test_parameter_prose_and_attachment_parent_agreement(self):
        """Headings may provide context, but cannot establish parameter identity."""
        external = self.endpoints + [
            {"endpointID": "parent", "inventoryId": "A-DC05", "class": "Procedure"},
            {"endpointID": "other-parent", "inventoryId": "A-DC05", "class": "Procedure"}]
        accepted = [{"assertionID": "path", "inventoryId": "C-DC20", "relation": "hasProcedure",
                     "sourceID": self.page_id, "targetID": "parent"}]
        node = self.node("A-DOM12", "parameter")
        node["parentPath"] = [self.ref("path", "accepted_assertion"), self.ref("attachment", "candidate_edge")]
        node["evidence"] = [self.fragment("Guide", contribution="heading")]
        edge = self.edge("C-DC11", self.ref("parent", "accepted_endpoint"), self.ref("parameter"), "attachment")
        payload = {"candidateNodes": [node], "candidateEdges": [edge]}
        records = self.index(self.validate(payload, endpoints=external, accepted_assertions=accepted))
        self.assertEqual(records["parameter"]["disposition"], "needs_review")
        node["evidence"].append(self.fragment("Prepare café 🌊 inputs for the run.", contribution="role claim"))
        records = self.index(self.validate(payload, endpoints=external, accepted_assertions=accepted))
        self.assertEqual(records["parameter"]["disposition"], "unresolved_condition")
        self.assertIn("explanatory_parameter_prose", records["parameter"]["targetProfileCheck"]["pendingGates"])
        alternative = deepcopy(edge)
        alternative["candidateID"] = "wrong-parent"
        alternative["source"] = self.ref("other-parent", "accepted_endpoint")
        payload["candidateEdges"].append(alternative)
        records = self.index(self.validate(payload, endpoints=external, accepted_assertions=accepted))
        self.assertEqual(records["wrong-parent"]["disposition"], "unresolved_endpoint")
        self.assertEqual(records["parameter"]["disposition"], "unresolved_condition")


if __name__ == "__main__":
    unittest.main()
