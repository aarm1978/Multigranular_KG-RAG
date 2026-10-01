"""T1/T2 tests of bounded initial review execution, with no real human judgments."""

from __future__ import annotations

import copy
import json
import tempfile
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.annotation.publication_step8.app import make_handler
from src.annotation.publication_step8.contracts import JUDGMENTS, TARGET_INVENTORY, ReviewError, ReviewInputs, digest, evidence_contexts
from src.annotation.publication_step8.service import ReviewService, activation_requirements


def fixture(role: str = "primary") -> SimpleNamespace:
    """Provide synthetic package-only input for persistence/activation tests."""

    return SimpleNamespace(role=role, package_hash="synthetic-package-" + role, units=["synthetic-unit"],
                           items={"opaque-node": {"primarySourceUnitID": "synthetic-unit", "recordKind": "node"},
                                  "opaque-relation": {"primarySourceUnitID": "synthetic-unit", "recordKind": "relation"}},
                           groups={}, verify_package=lambda: None)


def change(service: ReviewService, action: str, key: str, value: str) -> dict:
    """Submit an explicit synthetic action at the current revision."""

    return service.change({"expectedRevision": service.revision(), "action": action, "id": key, "value": value})


class SourceAndPackageTests(unittest.TestCase):
    """Read-only checks over accepted packages and exact authorized text."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load each accepted role without creating a reviewer database."""

        cls.primary, cls.second = ReviewInputs("primary"), ReviewInputs("second")

    def test_role_membership_and_context_are_package_derived(self) -> None:
        """Only accepted primary IDs are navigable; context remains supporting text."""

        self.assertEqual((len(self.primary.items), len(self.second.items)), (182, 182))
        self.assertEqual(len(self.primary.units), 6)
        self.assertEqual(len(self.second.units), 6)
        self.assertEqual(self.second.units, self.primary.units)
        self.assertEqual(self.second.items, self.primary.items)
        for unit in self.primary.units:
            self.assertEqual(self.second.unit(unit), self.primary.unit(unit))
        context = "pub:46:sec:0006:unit:0002"
        self.assertIn(context, self.primary.sources)
        with self.assertRaisesRegex(ReviewError, "UNIT_NOT_ASSIGNED"):
            self.primary.unit(context)
        with self.assertRaisesRegex(ReviewError, "UNIT_NOT_ASSIGNED"):
            self.second.unit(context)

    def test_source_text_and_every_evidence_segment_are_exact(self) -> None:
        """Paragraph rendering never changes source characters or evidence offsets."""

        for unit in self.primary.units:
            view = self.primary.unit(unit)
            for item in view["items"]:
                for context in item["paragraphContexts"]:
                    source = self.primary.sources[context["sourceUnitID"]]["text"]
                    self.assertEqual("".join(segment["text"] for segment in context["segments"]), source[context["startOffsetInUnit"]:context["endOffsetInUnit"]])
                for occurrence, evidence in enumerate(item["evidenceOccurrences"], 1):
                    highlighted = "".join(segment["text"] for context in item["paragraphContexts"] if context["occurrence"] == occurrence
                                          for segment in context["segments"] if "evidence" in segment["highlights"])
                    self.assertEqual(highlighted, evidence["evidenceText"])

    def test_paragraph_boundaries_unicode_and_no_inferred_label(self) -> None:
        """Multiple paragraphs and astral Unicode preserve code-point coordinates."""

        text = "A 😀 river.\n\nB flow.\n\nC end."
        item = {"recordKind": "node", "assertion": {"label": "not literal"}, "evidenceOccurrences": [{"sourceUnitID": "u", "startOffsetInUnit": 2, "endOffsetInUnit": 18}]}
        contexts = evidence_contexts(item, {"u": {"text": text}})
        self.assertEqual(len(contexts), 2)
        self.assertFalse(any("label" in segment["highlights"] for context in contexts for segment in context["segments"]))
        self.assertEqual("".join(segment["text"] for context in contexts for segment in context["segments"] if "evidence" in segment["highlights"]), text[2:18])
        relation = {**item, "recordKind": "relation", "assertion": {"relationName": "causes", "sourceEndpoint": {"label": "river"}, "targetEndpoint": {"label": "flow"}}}
        rendered = evidence_contexts(relation, {"u": {"text": text}})
        self.assertEqual({kind for context in rendered for segment in context["segments"] for kind in segment["highlights"]}, {"source", "target", "evidence"})

    def test_literal_mentions_are_bounded_to_each_cited_evidence_interval(self) -> None:
        """Every literal occurrence inside evidence highlights; none outside does."""

        text = "LSTM outside cited evidence. LSTM LSTM cited evidence."
        start = text.index("LSTM LSTM")
        end = start + len("LSTM LSTM")
        node = {"recordKind": "node", "assertion": {"label": "LSTM"},
                "evidenceOccurrences": [{"sourceUnitID": "u", "startOffsetInUnit": start, "endOffsetInUnit": end}]}
        contexts = evidence_contexts(node, {"u": {"text": text}})
        labels = [segment["text"] for context in contexts for segment in context["segments"] if "label" in segment["highlights"]]
        self.assertEqual(labels, ["LSTM", "LSTM"])
        self.assertEqual(contexts[0]["renderingKind"], "cited_evidence_paragraph")
        self.assertEqual(contexts[0]["renderingLabel"], "Cited-evidence paragraph for evidence occurrence 1")

        relation = {"recordKind": "relation", "assertion": {"sourceEndpoint": {"label": "LSTM"},
                    "targetEndpoint": {"label": "LSTM"}}, "evidenceOccurrences": node["evidenceOccurrences"]}
        endpoint_contexts = evidence_contexts(relation, {"u": {"text": text}})
        mentions = [segment for context in endpoint_contexts for segment in context["segments"]
                    if "source" in segment["highlights"] or "target" in segment["highlights"]]
        self.assertEqual([segment["text"] for segment in mentions], ["LSTM", "LSTM"])

    def test_target_guidance_is_derived_from_frozen_inventory(self) -> None:
        """Reviewer criteria and boundaries use the exact frozen target rows."""

        import yaml

        inventory = yaml.safe_load((self.primary.root / TARGET_INVENTORY).read_text(encoding="utf-8"))
        authoritative = {row["operational_id"]: row for row in [*inventory["node_targets"], *inventory["relation_targets"]]}
        for item in self.primary.items.values():
            guidance = self.primary.target_guidance[item["operationalTarget"]["operationalID"]]
            row = authoritative[item["operationalTarget"]["operationalID"]]
            self.assertEqual(guidance, {"positiveCriterion": row["positive_criterion"], "boundary": row["boundary"]})

    def test_current_paper_is_display_only_with_internal_export_binding(self) -> None:
        """The reviewer gets a neutral endpoint label while the export retains its ID."""

        raw = next(item for item in self.primary.items.values() if item["judgmentItemID"] in self.primary.endpoint_bindings)
        shown = next(item for item in self.primary.unit(raw["primarySourceUnitID"])["items"]
                     if item["judgmentItemID"] == raw["judgmentItemID"])
        endpoint_name = self.primary.endpoint_bindings[raw["judgmentItemID"]][0]["endpoint"]
        self.assertEqual(shown["assertion"][endpoint_name], {"endpointKind": "deterministic_node", "displayLabel": "Current paper"})
        with tempfile.TemporaryDirectory() as directory:
            service = ReviewService(self.primary, Path(directory), "display-only", "synthetic-reviewer")
            try:
                exported = json.loads(service.export())
            finally:
                service.close()
        self.assertEqual(exported["currentPaperEndpointBindings"][raw["judgmentItemID"]], self.primary.endpoint_bindings[raw["judgmentItemID"]])

    def test_package_and_source_drift_fail_closed(self) -> None:
        """Exact accepted file binding and source inventory hashes are mandatory."""

        with patch("src.annotation.publication_step8.contracts.PACKAGES", {"primary": (self.primary.package_path.name, "wrong")}):
            with self.assertRaisesRegex(ReviewError, "BLINDED_PACKAGE_BINDING_DRIFT"):
                ReviewInputs("primary")
        with patch("src.annotation.publication_step8.contracts.INVENTORY_HASH", "wrong"):
            with self.assertRaisesRegex(ReviewError, "SOURCE_INVENTORY_BINDING_DRIFT"):
                ReviewInputs("primary")
        with patch("src.annotation.publication_step8.contracts.TARGET_INVENTORY_HASH", "wrong"):
            with self.assertRaisesRegex(ReviewError, "TARGET_INVENTORY_BINDING_DRIFT"):
                ReviewInputs("primary")

    def test_reviewer_payload_has_no_internal_lineage(self) -> None:
        """Every served unit recursively excludes forbidden system metadata."""

        forbidden = {"requestID", "runID", "candidateID", "provider", "modelName", "outputID", "validationLineage", "sourceFile", "candidateKey", "c1Provenance", "candidateValidationStatus", "supersededByRecordID", "memberCandidateKeys"}

        def inspect(value: object) -> None:
            """Visit all nested source and assertion structures."""

            if isinstance(value, dict):
                self.assertFalse(set(value) & forbidden)
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)

        for unit in self.second.units:
            inspect(self.second.unit(unit))


class SessionTests(unittest.TestCase):
    """Synthetic decisions remain in temporary databases under test identities."""

    def setUp(self) -> None:
        """Allocate one temporary namespace for synthetic fixtures."""

        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.services = []

    def tearDown(self) -> None:
        """Close databases before removing temporary synthetic state."""

        for service in self.services:
            service.close()
        self.temporary.cleanup()

    def service(self, role: str = "primary", session: str = "fixture", mode: str = "dry-run", activation: Path | None = None) -> ReviewService:
        """Open a synthetic test session."""

        value = ReviewService(fixture(role), self.root, session, "synthetic-reviewer", mode, activation)
        self.services.append(value)
        return value

    def test_workflow_vocabulary_free_navigation_completion_and_no_preselection(self) -> None:
        """Nodes and Relations are freely revisitable, while completion remains gated."""

        service = self.service()
        self.assertEqual(service.decisions(), {})
        with self.assertRaisesRegex(ReviewError, "REVIEW_PHASE_MISMATCH"):
            change(service, "judgment", "opaque-node", JUDGMENTS[0])
        change(service, "phase", "synthetic-unit", "nodes")
        for bad in ("edited_label", "adjudication_unresolved", "", "yes"):
            with self.assertRaisesRegex(ReviewError, "INVALID_JUDGMENT_OR_ITEM"):
                change(service, "judgment", "opaque-node", bad)
        change(service, "phase", "synthetic-unit", "relations")
        change(service, "phase", "synthetic-unit", "nodes")
        change(service, "judgment", "opaque-node", JUDGMENTS[0])
        with self.assertRaisesRegex(ReviewError, "REVIEWER_IDENTITY_LOCKED"):
            change(service, "reviewer", "", "different")
        change(service, "phase", "synthetic-unit", "relations")
        with self.assertRaisesRegex(ReviewError, "UNIT_PHASE_INCOMPLETE"):
            change(service, "phase", "synthetic-unit", "complete")
        change(service, "judgment", "opaque-relation", JUDGMENTS[1])
        change(service, "phase", "synthetic-unit", "complete")
        self.assertTrue(service.state()["complete"])

    def test_autosave_restore_history_export_and_stale_write(self) -> None:
        """Decisions and revisions resume exactly; stale clients cannot overwrite."""

        service = self.service()
        change(service, "phase", "synthetic-unit", "nodes")
        change(service, "judgment", "opaque-node", JUDGMENTS[0])
        change(service, "judgment", "opaque-node", JUDGMENTS[2])
        exported = service.export()
        self.assertEqual(exported, service.export())
        restored = self.service()
        self.assertEqual(restored.export(), exported)
        self.assertEqual(restored.decisions()["opaque-node"], JUDGMENTS[2])
        with self.assertRaisesRegex(ReviewError, "STALE_REVISION"):
            restored.change({"action": "judgment", "id": "opaque-node", "value": JUDGMENTS[0], "expectedRevision": 0})
        result = json.loads(exported)
        self.assertEqual(result["inputPackageSha256"], "synthetic-package-primary")
        events = [row for row in result["revisions"] if row["action"] == "judgment"]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["judgmentItemID"], "opaque-node")
        self.assertEqual(events[-1]["primarySourceUnitID"], "synthetic-unit")

    def test_reviewer_role_session_isolation(self) -> None:
        """Same session ID in another reviewer role cannot access primary answers."""

        primary, second, other = self.service(), self.service("second"), self.service(session="other")
        change(primary, "phase", "synthetic-unit", "nodes")
        change(primary, "judgment", "opaque-node", JUDGMENTS[0])
        self.assertEqual(second.decisions(), {})
        self.assertEqual(other.decisions(), {})
        self.assertEqual(second.state()["answered"], 0)

    def test_production_activation_and_dry_run_separation(self) -> None:
        """Only synthetic activation is used, entirely within the temporary fixture."""

        with self.assertRaisesRegex(ReviewError, "PRODUCTION_ACTIVATION_REQUIRED"):
            self.service(mode="production")
        self.assertFalse((self.root / "production").exists())
        path = self.root / "synthetic-activation.json"
        required = activation_requirements(fixture(), "fixture", "synthetic-reviewer")
        path.write_text(json.dumps({**required, "runtimeSha256": "wrong"}))
        with self.assertRaisesRegex(ReviewError, "PRODUCTION_ACTIVATION_BINDING_DRIFT"):
            self.service(mode="production", activation=path)
        path.write_text(json.dumps(required))
        production = self.service(mode="production", activation=path)
        dry = self.service()
        change(production, "phase", "synthetic-unit", "nodes")
        change(production, "judgment", "opaque-node", JUDGMENTS[0])
        self.assertEqual(dry.decisions(), {})
        with self.assertRaisesRegex(ReviewError, "REVIEWER_IDENTITY_LOCKED"):
            change(production, "reviewer", "", "other")
        with patch("src.annotation.publication_step8.service.runtime_hash", return_value="drift"):
            with self.assertRaisesRegex(ReviewError, "RUNTIME_BINDING_DRIFT"):
                production.export()

    def test_production_role_isolation_and_activation_package_drift(self) -> None:
        """Synthetic full-review roles remain separate; stale package approvals fail."""

        services = {}
        for role in ("primary", "second"):
            path = self.root / (role + "-synthetic-activation.json")
            required = activation_requirements(fixture(role), "fixture", "synthetic-reviewer")
            path.write_text(json.dumps({**required, "inputPackageSha256": "historical-package"}))
            with self.assertRaisesRegex(ReviewError, "PRODUCTION_ACTIVATION_BINDING_DRIFT"):
                self.service(role, mode="production", activation=path)
            path.write_text(json.dumps(required))
            services[role] = self.service(role, mode="production", activation=path)
        change(services["primary"], "phase", "synthetic-unit", "nodes")
        change(services["primary"], "judgment", "opaque-node", JUDGMENTS[0])
        self.assertEqual(services["second"].decisions(), {})
        self.assertEqual(services["second"].phase("synthetic-unit"), "orientation")
        services["second"].inputs.package_hash = "changed-package"
        with self.assertRaisesRegex(ReviewError, "PRODUCTION_ACTIVATION_BINDING_DRIFT"):
            services["second"].export()

    def test_duplicate_vocabulary_and_completion(self) -> None:
        """An existing blinded group requires a decision but no authored assertions."""

        service = self.service()
        service.inputs.groups = {"opaque-group": {"judgmentItemIDs": ["opaque-node", "opaque-relation"]}}
        change(service, "phase", "synthetic-unit", "nodes")
        change(service, "judgment", "opaque-node", JUDGMENTS[0])
        change(service, "phase", "synthetic-unit", "relations")
        change(service, "judgment", "opaque-relation", JUDGMENTS[0])
        self.assertFalse(service.state()["complete"])
        with self.assertRaisesRegex(ReviewError, "INVALID_DUPLICATE_DECISION_OR_GROUP"):
            change(service, "duplicate", "opaque-group", "merge")
        change(service, "duplicate", "opaque-group", "distinct_assertions")
        self.assertTrue(service.state()["complete"])

    def test_http_routes_and_role_exports_cannot_serve_private_files(self) -> None:
        """The actual handler exposes fixed routes and requires deliberate writes."""

        service = self.service("second")
        server = HTTPServer(("127.0.0.1", 0), make_handler(service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            state = json.load(urlopen(base + "/api/state"))
            self.assertEqual(state["reviewRole"], "second")
            for path in ("/api/primary", "/../../service.py", "/api/lineage", "/publication_step8b_internal_opaque_lineage_map_v1.0.0.json"):
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + path)
                self.assertEqual(error.exception.code, 404)
            body = json.dumps({"action": "phase", "id": "synthetic-unit", "value": "nodes", "expectedRevision": 0}).encode()
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base + "/api/action", body, {"Content-Type": "application/json"}))
            self.assertEqual(error.exception.code, 403)
            response = json.load(urlopen(Request(base + "/api/action", body, {"Content-Type": "application/json", "X-Review-Token": state["csrfToken"]})))
            self.assertEqual(response["revision"], 1)
            exported = json.load(urlopen(base + "/api/export"))
            self.assertEqual(exported["reviewRole"], "second")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
