"""Focused tests for the local Publication Pilot 1 screening interface MVP."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sqlite3
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from dataclasses import replace
from http.server import HTTPServer
from pathlib import Path

from src.annotation.publication_pilot1 import INTERFACE_VERSION
from src.annotation.publication_pilot1.app import build_service, make_handler
from src.annotation.publication_pilot1.service import ScreeningService
from src.annotation.publication_pilot1.contracts import (
    PROTECTED_HASHES,
    RECURRING_DISTINCTIONS,
    SCREENING_HANDBOOK_PATH,
    SCREENING_HANDBOOK_SHA256,
    ContractError,
    load_contracts,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DOWNSTREAM_NAMES = {
    "publication_pilot1_screening.jsonl",
    "publication_pilot1_unit_routing.jsonl",
    "publication_pilot1_target_coverage_matrix.csv",
    "publication_pilot1_pre_gate0_candidate_order.json",
    "publication_pilot1_calibration_manifest.json",
}


def neutral_review() -> dict[str, object]:
    """Return a synthetic, semantically neutral, fully explicit human form payload."""

    return {
        "screeningRationale": "Synthetic interface-contract test; not a real semantic judgment.",
        "likelyExhaustiveEmptyTargetIDs": [],
        "likelyRecurringDistinctions": [],
        "expectedAssertionDensity": "none",
        "expectedRelationDensity": "none",
        "routingComplexity": "low",
        "distributedEvidenceLikely": False,
        "sectionContextUseful": False,
        "deterministicEndpointLikely": False,
        "routedNodeOperationalTargetIDs": [],
        "routedRelationOperationalTargetIDs": [],
        "screeningNotes": "",
    }


class ScreeningInterfaceTests(unittest.TestCase):
    """Verify frozen inputs, persistence, controls, source text, and export behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the immutable real contracts once without changing them."""

        cls.contracts = load_contracts(ROOT)
        cls.canonical_hash = sha256_file(
            ROOT / "data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv"
        )

    def setUp(self) -> None:
        """Create a private temporary production service for each test."""

        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.service = build_service(ROOT, base / "state", base / "exports", False)
        self.service.store.change_reviewer("reviewer-test")
        self.first_id = self.contracts.open_rows[0]["sourceUnitID"]

    def tearDown(self) -> None:
        """Close and remove temporary local screening state."""

        self.service.store.close()
        self.temp.cleanup()

    def test_protected_hashes_and_population_counts(self) -> None:
        """Protected anchors and the 358/267/49/39/3 population remain exact."""

        for path, digest in PROTECTED_HASHES.items():
            self.assertEqual(self.contracts.protected_hashes[path], digest)
        self.assertEqual(self.contracts.protected_hashes[SCREENING_HANDBOOK_PATH], SCREENING_HANDBOOK_SHA256)
        self.assertEqual(len(self.contracts.rows), 358)
        self.assertEqual(len(self.contracts.open_rows), 267)
        counts = {status: sum(row["sourceEligibility"] == status for row in self.contracts.rows) for status in ("context_only", "excluded", "needs_review")}
        self.assertEqual(counts, {"context_only": 49, "excluded": 39, "needs_review": 3})

    def test_source_unit_slice_and_hash_are_validated_before_display(self) -> None:
        """Displayed text is the canonical Unicode-code-point slice with its accepted hash."""

        unit = self.service.unit(self.first_id)
        record = self.contracts.inventory_by_id[self.first_id]
        self.assertFalse(unit["reviewBlocked"])
        self.assertEqual(unit["text"], record["text"])
        self.assertEqual(hashlib.sha256(unit["text"].encode()).hexdigest(), record["textHash"])

    def test_frozen_handbook_rules_hash_and_quick_reference_are_available(self) -> None:
        """The frozen repository handbook is hash-bound and locally available."""

        handbook = ROOT / "docs/publication_pilot1_screening_handbook.md"
        text = handbook.read_text(encoding="utf-8")
        self.assertIn("**Version:** 0.1.1", text)
        self.assertIn("**Status:** Frozen for Publication Pilot 1 production screening", text)
        self.assertIn("**Freeze date:** 2026-08-11", text)
        self.assertEqual(sha256_file(handbook), SCREENING_HANDBOOK_SHA256)
        self.assertEqual(INTERFACE_VERSION, "0.1.1")
        self.assertIn("## 5. Current-artifact ownership rule", text)
        self.assertIn("same source–target pair", text)
        self.assertIn("### 14.6 Mixed Introduction / Related Work", text)
        html = (ROOT / "src/annotation/publication_pilot1/static/index.html").read_text(encoding="utf-8")
        self.assertIn("Handbook / Quick reference", html)
        self.assertIn('href="/handbook"', html)

    def test_blank_draft_has_no_semantic_preselection(self) -> None:
        """A new unit contains no inferred targets, flags, density, or complexity."""

        draft = self.service.unit(self.first_id)["draft"]
        self.assertFalse(draft["completed"])
        for key in ("routedNodeOperationalTargetIDs", "routedRelationOperationalTargetIDs"):
            self.assertNotIn(key, draft)

    def test_manual_ui_aids_do_not_create_semantic_defaults(self) -> None:
        """Templates require a choice and no-target clearing preserves every judgment field."""

        module = ROOT / "src/annotation/publication_pilot1/static/ui_aids.js"
        payload = neutral_review()
        payload.update({
            "routedNodeOperationalTargetIDs": ["node-a"],
            "routedRelationOperationalTargetIDs": ["relation-a"],
            "likelyExhaustiveEmptyTargetIDs": ["node-a"],
            "likelyRecurringDistinctions": ["use/mention/reference"],
            "expectedAssertionDensity": "high",
            "expectedRelationDensity": "medium",
            "routingComplexity": "high",
            "distributedEvidenceLikely": True,
            "sectionContextUseful": False,
            "deterministicEndpointLikely": True,
            "screeningRationale": "Reviewer-authored text",
        })
        script = f"""
          const aids = require({json.dumps(str(module))});
          const draft = {json.dumps(payload)};
          const blank = aids.selectRationaleTemplate(draft.screeningRationale, "", false);
          const refused = aids.selectRationaleTemplate(draft.screeningRationale, "Results", false);
          const accepted = aids.selectRationaleTemplate(draft.screeningRationale, "Results", true);
          const cleared = aids.clearSemanticTargets(draft);
          if (Object.keys(aids.rationaleTemplates).length !== 11) process.exit(2);
          if (blank.applied || blank.value !== draft.screeningRationale) process.exit(3);
          if (refused.applied || refused.value !== draft.screeningRationale) process.exit(4);
          if (!accepted.applied || !accepted.value.includes("[findings/comparisons/metrics]")) process.exit(5);
          for (const key of ["routedNodeOperationalTargetIDs","routedRelationOperationalTargetIDs","likelyExhaustiveEmptyTargetIDs","likelyRecurringDistinctions"]) if (cleared[key].length) process.exit(6);
          for (const key of ["expectedAssertionDensity","expectedRelationDensity","routingComplexity","distributedEvidenceLikely","sectionContextUseful","deterministicEndpointLikely","screeningRationale","screeningNotes"]) if (cleared[key] !== draft[key]) process.exit(7);
        """
        result = subprocess.run(["node", "-e", script], cwd=ROOT, check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        aids_source = module.read_text(encoding="utf-8")
        self.assertNotIn("sectionRole", aids_source)
        self.assertNotIn("sourceText", aids_source)

    def test_frozen_handbook_templates_exactly_match_ui_templates(self) -> None:
        """Template names, order, and text cannot drift from the frozen handbook."""

        handbook = (ROOT / SCREENING_HANDBOOK_PATH).read_text(encoding="utf-8")
        section = handbook.split("## 13. Human screening judgment templates", 1)[1].split(
            "### Optional screening-note templates", 1
        )[0]
        matches = re.findall(
            r"^### Template [A-K] — (.+?)\n\n```text\n(.+?)\n```$",
            section,
            flags=re.MULTILINE | re.DOTALL,
        )
        handbook_templates: dict[str, str] = {}
        for heading, template in matches:
            name = heading.removesuffix(" unit").replace("related-work", "Related work")
            name = name[0].upper() + name[1:]
            handbook_templates[name] = template
        module = ROOT / "src/annotation/publication_pilot1/static/ui_aids.js"
        script = f"const aids=require({json.dumps(str(module))});process.stdout.write(JSON.stringify(aids.rationaleTemplates));"
        result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
        ui_templates = json.loads(result.stdout)
        self.assertEqual(len(handbook_templates), 11)
        self.assertEqual(list(handbook_templates.items()), list(ui_templates.items()))

    def test_deterministic_and_deferred_refs_are_exact_and_do_not_set_flag(self) -> None:
        """Accepted reference strings are read-only context and never set a semantic boolean."""

        source_id = self.first_id
        exact = {
            "deterministicNodeRefs": "node:exact-a|node:exact-b",
            "deterministicEdgeRefs": "edge:exact-a",
            "deferredRecordRefs": "deferred:exact-a",
        }
        rows = tuple({**row, **exact} if row["sourceUnitID"] == source_id else row for row in self.contracts.rows)
        synthetic_contracts = replace(self.contracts, rows=rows)
        service = ScreeningService(synthetic_contracts, self.service.store, Path(self.temp.name) / "exports", False)
        unit = service.unit(source_id)
        for field in ("deterministicNodeRefs", "deterministicEdgeRefs", "deferredRecordRefs"):
            self.assertEqual(unit["metadata"][field], exact[field])
        self.assertNotIn("deterministicEndpointLikely", unit["draft"])

    def test_deterministic_fields_cannot_be_edited(self) -> None:
        """The service rejects attempts to submit canonical metadata as human fields."""

        with self.assertRaisesRegex(ContractError, "SCREENING_DETERMINISTIC_OR_UNKNOWN_FIELD"):
            self.service.save(self.first_id, {**neutral_review(), "paperID": "changed"}, False)
        self.assertEqual(sha256_file(ROOT / "data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv"), self.canonical_hash)

    def test_autosave_reload_reviewer_and_screened_at_audit_semantics(self) -> None:
        """Drafts and reviewer persist; completed edits preserve screenedAt and append revisions."""

        self.service.store.change_reviewer("reviewer-test")
        saved = self.service.save(self.first_id, neutral_review(), True)["draft"]
        screened_at = saved["screenedAt"]
        self.service.store.close()
        base = Path(self.temp.name)
        self.service = build_service(ROOT, base / "state", base / "exports", False)
        self.assertEqual(self.service.store.reviewer_id(), "reviewer-test")
        self.assertEqual(self.service.unit(self.first_id)["draft"]["screenedAt"], screened_at)
        edited = neutral_review()
        edited["screeningNotes"] = "Edited completed synthetic record."
        resaved = self.service.save(self.first_id, edited, False)["draft"]
        self.assertTrue(resaved["completed"])
        self.assertEqual(resaved["screenedAt"], screened_at)
        revisions = self.service.store.connection.execute(
            "SELECT COUNT(*) AS count FROM revisions WHERE source_unit_id = ?", (self.first_id,)
        ).fetchone()["count"]
        self.assertEqual(revisions, 2)
        sidecar = json.loads(self.service.store.sidecar_path.read_text())
        self.assertEqual(sidecar["reviewerID"], "reviewer-test")
        self.assertIn(self.first_id, sidecar["perUnitRevisionTimestamps"])

    def test_bound_autosave_flushes_unit_a_before_navigation_to_unit_b(self) -> None:
        """Immediate navigation persists A's detached snapshot and never writes it to B."""

        coordinator = ROOT / "src/annotation/publication_pilot1/static/save_coordinator.js"
        script = f"""
          const Coordinator = require({json.dumps(str(coordinator))});
          const persisted = {{}};
          let current = "unit-a";
          const saves = new Coordinator(async request => {{
            await new Promise(resolve => setTimeout(resolve, 5));
            persisted[request.sourceUnitID] = request.draft;
            return request;
          }}, 1000);
          saves.schedule({{sourceUnitID:"unit-a", draft:{{screeningNotes:"exact A change"}}}});
          if (!saves.hasUnsavedChanges()) process.exit(6);
          saves.navigate("unit-b", async id => {{ current = id; }}).then(() => {{
            if (current !== "unit-b") process.exit(2);
            if (persisted["unit-a"].screeningNotes !== "exact A change") process.exit(3);
            if (persisted["unit-b"] !== undefined) process.exit(4);
            if (saves.hasUnsavedChanges()) process.exit(7);
          }}).catch(() => process.exit(5));
        """
        result = subprocess.run(["node", "-e", script], cwd=ROOT, check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_state_contract_compatible_reopen_and_incompatible_rejection(self) -> None:
        """Existing state reopens only when every persisted binding remains exact."""

        base = Path(self.temp.name) / "binding"
        first = build_service(ROOT, base / "state", base / "exports", False)
        first.store.change_reviewer("binding-reviewer")
        path = first.store.path
        first.store.close()
        compatible = build_service(ROOT, base / "state", base / "exports", False)
        self.assertEqual(compatible.store.reviewer_id(), "binding-reviewer")
        self.assertEqual(compatible.store.get_metadata("screeningHandbookSha256"), SCREENING_HANDBOOK_SHA256)
        sidecar = json.loads(compatible.store.sidecar_path.read_text(encoding="utf-8"))
        self.assertEqual(sidecar["screeningHandbookSha256"], SCREENING_HANDBOOK_SHA256)
        self.assertEqual(compatible.bootstrap()["provenance"]["screeningHandbookSha256"], SCREENING_HANDBOOK_SHA256)
        compatible.store.close()
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE metadata SET value = ? WHERE key = ?", ("drift", "canonicalWorklistHash"))
        with self.assertRaisesRegex(ValueError, "SCREENING_STATE_CONTRACT_MISMATCH:canonicalWorklistHash"):
            build_service(ROOT, base / "state", base / "exports", False)
        with sqlite3.connect(path) as connection:
            observed = connection.execute("SELECT value FROM metadata WHERE key = 'canonicalWorklistHash'").fetchone()[0]
        self.assertEqual(observed, "drift")
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE metadata SET value = ? WHERE key = ?",
                (PROTECTED_HASHES["data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv"], "canonicalWorklistHash"),
            )
            connection.execute(
                "UPDATE metadata SET value = ? WHERE key = ?", ("drift", "screeningHandbookSha256")
            )
        with self.assertRaisesRegex(
            ValueError, "SCREENING_STATE_CONTRACT_MISMATCH:screeningHandbookSha256"
        ):
            build_service(ROOT, base / "state", base / "exports", False)
        with sqlite3.connect(path) as connection:
            observed = connection.execute(
                "SELECT value FROM metadata WHERE key = 'screeningHandbookSha256'"
            ).fetchone()[0]
        self.assertEqual(observed, "drift")

        dry = build_service(ROOT, base / "dry-state", base / "dry-exports", True)
        dry_path = dry.store.path
        dry.store.close()
        with sqlite3.connect(dry_path) as connection:
            connection.execute("UPDATE metadata SET value = ? WHERE key = ?", ("old-interface", "screeningInterfaceVersion"))
        reset = build_service(ROOT, base / "dry-state", base / "dry-exports", True, reset_dry_run=True)
        self.assertEqual(reset.store.get_metadata("screeningInterfaceVersion"), "0.1.1")
        self.assertEqual(reset.store.get_metadata("screeningHandbookSha256"), SCREENING_HANDBOOK_SHA256)
        self.assertFalse(reset.store.all_drafts())
        reset.store.close()

    def test_reviewer_identity_locks_after_first_revision(self) -> None:
        """The single reviewer may change before saving but never after attribution begins."""

        self.service.store.change_reviewer("before-first-save")
        self.assertFalse(self.service.store.reviewer_locked())
        saved = self.service.save(self.first_id, neutral_review(), True)["draft"]
        self.assertTrue(self.service.store.reviewer_locked())
        with self.assertRaisesRegex(ValueError, "SCREENING_REVIEWER_ID_LOCKED_AFTER_FIRST_REVISION"):
            self.service.store.change_reviewer("different-reviewer")
        self.assertEqual(self.service.store.reviewer_id(), "before-first-save")
        self.assertTrue(saved["completed"])
        self.assertEqual(saved["screeningReviewerID"], "before-first-save")
        self.assertEqual(self.service.unit(self.first_id)["draft"]["screeningReviewerID"], "before-first-save")

    def test_zero_target_review_and_explicit_boolean_validation(self) -> None:
        """Zero routed targets are valid, while every boolean requires a human choice."""

        self.service.store.change_reviewer("reviewer-test")
        invalid = neutral_review()
        invalid["sectionContextUseful"] = None
        with self.assertRaisesRegex(ContractError, "SCREENING_EXPLICIT_BOOLEAN_REQUIRED"):
            self.service.save(self.first_id, invalid, True)
        result = self.service.save(self.first_id, neutral_review(), True)
        self.assertTrue(result["draft"]["completed"])
        self.assertEqual(result["draft"]["routedNodeOperationalTargetIDs"], [])

    def test_catalog_drives_targets_and_operational_id_serialization(self) -> None:
        """Catalog definitions drive UI choices; node/relation IDs serialize unchanged."""

        targets = self.service.targets
        node = next(t for t in targets.values() if t["targetKind"] == "node" and t["pilotTreatment"] == "extract_and_monitor")
        relation = next(t for t in targets.values() if t["targetKind"] == "relation")
        self.assertTrue(node["displayLabel"] and node["shortDefinition"] and node["boundaryHint"])
        payload = neutral_review()
        payload["routedNodeOperationalTargetIDs"] = [node["operationalTargetID"]]
        payload["routedRelationOperationalTargetIDs"] = [relation["operationalTargetID"]]
        self.service.store.change_reviewer("reviewer-test")
        self.service.save(self.first_id, payload, True)
        path = self.service.export(False)
        with path.open(newline="", encoding="utf-8") as handle:
            row = next(row for row in csv.DictReader(handle) if row["sourceUnitID"] == self.first_id)
        self.assertEqual(row["routedNodeOperationalTargetIDs"], node["operationalTargetID"])
        self.assertEqual(row["routedRelationOperationalTargetIDs"], relation["operationalTargetID"])

    def test_exhaustive_empty_rule_and_unrouting_clear(self) -> None:
        """Only routed evaluate targets survive in exhaustive-empty selections."""

        evaluate = next(t for t in self.service.targets.values() if t["pilotTreatment"] == "extract_and_evaluate")
        monitor = next(t for t in self.service.targets.values() if t["pilotTreatment"] == "extract_and_monitor")
        payload = neutral_review()
        route_key = "routedNodeOperationalTargetIDs" if evaluate["targetKind"] == "node" else "routedRelationOperationalTargetIDs"
        payload[route_key] = [evaluate["operationalTargetID"]]
        payload["likelyExhaustiveEmptyTargetIDs"] = [evaluate["operationalTargetID"], monitor["operationalTargetID"]]
        result = self.service.save(self.first_id, payload, False)
        self.assertEqual(result["draft"]["likelyExhaustiveEmptyTargetIDs"], [evaluate["operationalTargetID"]])
        self.assertEqual(result["clearedExhaustiveEmptyTargetIDs"], [monitor["operationalTargetID"]])
        payload[route_key] = []
        result = self.service.save(self.first_id, payload, False)
        self.assertEqual(result["draft"]["likelyExhaustiveEmptyTargetIDs"], [])
        self.assertEqual(result["clearedExhaustiveEmptyTargetIDs"], sorted(payload["likelyExhaustiveEmptyTargetIDs"]))

    def test_controlled_vocabularies_are_exact(self) -> None:
        """Recurring distinctions and density/complexity fields accept only frozen values."""

        self.assertEqual(tuple(self.service.bootstrap()["controls"]["recurringDistinctions"]), RECURRING_DISTINCTIONS)
        invalid = neutral_review()
        invalid["likelyRecurringDistinctions"] = ["invented"]
        with self.assertRaisesRegex(ContractError, "SCREENING_UNKNOWN_RECURRING_DISTINCTION"):
            self.service.save(self.first_id, invalid, False)
        self.service.store.change_reviewer("reviewer-test")
        invalid = neutral_review()
        invalid["expectedRelationDensity"] = "not_applicable"
        with self.assertRaisesRegex(ContractError, "SCREENING_RELATION_DENSITY_REQUIRED"):
            self.service.save(self.first_id, invalid, True)

    def test_partial_export_reconstructs_all_rows_and_preserves_deterministic_fields(self) -> None:
        """Backup export has exactly the canonical schema and immutable field values."""

        self.service.save(self.first_id, neutral_review(), False)
        path = self.service.export(False)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            exported = list(reader)
            self.assertEqual(tuple(reader.fieldnames or ()), self.contracts.headers)
        self.assertEqual(len(exported), 358)
        for canonical, actual in zip(self.contracts.rows, exported):
            for field in self.contracts.deterministic_columns:
                self.assertEqual(actual[field], canonical[field])
        self.assertEqual(exported[0]["screeningStatus"], self.contracts.rows[0]["screeningStatus"])
        self.assertEqual(sha256_file(ROOT / "data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv"), self.canonical_hash)

    def test_complete_export_blocked_until_all_267_reviewed(self) -> None:
        """Compiler-ready export is unavailable before all open units complete."""

        with self.assertRaisesRegex(ContractError, "COMPLETE_EXPORT_REQUIRES_267_REVIEWED"):
            self.service.export(True)

    def test_complete_export_reconstructs_compiler_ready_358_rows(self) -> None:
        """A fully synthetic reviewed session exports every row with no extra columns."""

        for row in self.contracts.open_rows:
            self.service.save(row["sourceUnitID"], neutral_review(), True)
        path = self.service.export(True)
        self.assertEqual(path.name, "publication_pilot1_screening_worklist_reviewed.csv")
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            self.assertEqual(tuple(reader.fieldnames or ()), self.contracts.headers)
        self.assertEqual(len(rows), 358)
        self.assertEqual(sum(row["screeningStatus"] == "reviewed" for row in rows), 267)
        for canonical, actual in zip(self.contracts.rows, rows):
            for field in self.contracts.deterministic_columns:
                self.assertEqual(actual[field], canonical[field])
        complete_hash = sha256_file(path)
        complete_sidecar = json.loads(self.service.store.sidecar_path.read_text())
        self.assertEqual(complete_sidecar["lastExportKind"], "complete")
        self.assertEqual(complete_sidecar["exportedReviewedCsvHash"], complete_hash)
        self.assertTrue(complete_sidecar["exportedReviewedCsvTimestamp"].endswith("Z"))
        changed = neutral_review()
        changed["screeningNotes"] = "Synthetic post-complete backup revision."
        self.service.save(self.first_id, changed, False)
        partial_path = self.service.export(False)
        sidecar = json.loads(self.service.store.sidecar_path.read_text())
        self.assertEqual(sidecar["completedUnitCount"], 267)
        self.assertEqual(sidecar["lastExportKind"], "partial")
        self.assertEqual(sidecar["lastExportHash"], sha256_file(partial_path))
        self.assertNotEqual(sidecar["lastExportHash"], complete_hash)
        self.assertEqual(sidecar["exportedReviewedCsvHash"], complete_hash)
        self.assertEqual(
            sidecar["exportedReviewedCsvTimestamp"], complete_sidecar["exportedReviewedCsvTimestamp"]
        )

    def test_dry_run_state_isolated_and_resettable(self) -> None:
        """Dry-run decisions use another database and reset cannot touch production."""

        base = Path(self.temp.name)
        dry = build_service(ROOT, base / "state", base / "exports", True)
        try:
            dry.store.change_reviewer("dry-reviewer")
            dry.save(self.first_id, neutral_review(), False)
            dry.set_revisit(self.first_id, True)
            with self.assertRaisesRegex(ValueError, "SCREENING_REVIEWER_ID_LOCKED_AFTER_FIRST_REVISION"):
                dry.store.change_reviewer("other-dry-reviewer")
            self.assertNotEqual(dry.store.path, self.service.store.path)
            self.assertFalse(self.service.unit(self.first_id)["draft"]["updatedAt"])
            dry.store.reset()
            self.assertFalse(dry.unit(self.first_id)["draft"]["updatedAt"])
            self.assertFalse(dry.store.revisit_ids())
            self.assertEqual(dry.store.reviewer_id(), "")
            dry.store.change_reviewer("other-dry-reviewer")
            self.assertEqual(dry.store.reviewer_id(), "other-dry-reviewer")
            with self.assertRaisesRegex(ContractError, "DRY_RUN_COMPILER_READY_EXPORT_FORBIDDEN"):
                dry.export(True)
        finally:
            dry.store.close()

    def test_revisit_is_local_persistent_filter_state_and_never_exported(self) -> None:
        """A manual bookmark survives reopen but cannot alter the canonical CSV contract."""

        self.service.set_revisit(self.first_id, True)
        self.assertTrue(self.service.unit(self.first_id)["revisit"])
        self.assertTrue(next(u for u in self.service.bootstrap()["units"] if u["sourceUnitID"] == self.first_id)["revisit"])
        self.service.store.close()
        base = Path(self.temp.name)
        self.service = build_service(ROOT, base / "state", base / "exports", False)
        self.assertIn(self.first_id, self.service.store.revisit_ids())
        path = self.service.export(False)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertNotIn("revisit", reader.fieldnames or [])
            self.assertEqual(tuple(reader.fieldnames or ()), self.contracts.headers)
        sidecar = json.loads(self.service.store.sidecar_path.read_text())
        self.assertEqual(sidecar["revisitSourceUnitIDs"], [self.first_id])
        self.service.set_revisit(self.first_id, False)
        self.assertNotIn(self.first_id, self.service.store.revisit_ids())

    def test_local_artifacts_ignored_and_no_inference_dependencies(self) -> None:
        """Private state is Git-ignored and the application imports no inference clients."""

        self.assertIn("var/publication_pilot1_screening/", (ROOT / ".gitignore").read_text())
        package = ROOT / "src/annotation/publication_pilot1"
        source = "\n".join(path.read_text() for pattern in ("*.py", "static/*.js") for path in package.glob(pattern))
        for forbidden in ("import openai", "from openai", "import requests", "import httpx", "anthropic"):
            self.assertNotIn(forbidden, source.lower())
        self.assertNotIn('fetch("http', source.lower())

    def test_interface_does_not_materialize_block_a_outputs(self) -> None:
        """Saving and backup export do not invoke the Block A materialization boundary."""

        output = ROOT / "data/curation/papers/pilot1"
        before = {name: (output / name).exists() for name in DOWNSTREAM_NAMES}
        self.service.save(self.first_id, neutral_review(), False)
        self.service.export(False)
        after = {name: (output / name).exists() for name in DOWNSTREAM_NAMES}
        self.assertEqual(after, before)

    def test_browser_entrypoint_smoke(self) -> None:
        """The local HTTP entrypoint serves the page and bootstrap JSON on loopback."""

        try:
            server = HTTPServer(("127.0.0.1", 0), make_handler(self.service))
        except PermissionError:
            self.skipTest("sandbox forbids even loopback socket binding")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urllib.request.urlopen(base + "/", timeout=3) as response:
                self.assertIn(b"Publication Pilot 1", response.read())
            with urllib.request.urlopen(base + "/api/bootstrap", timeout=3) as response:
                bootstrap = json.load(response)
            with urllib.request.urlopen(base + "/handbook", timeout=3) as response:
                self.assertIn(b"Frozen for Publication Pilot 1 production screening", response.read())
            self.assertEqual(bootstrap["progress"]["total"], 267)
            self.assertEqual(len(bootstrap["targets"]), 69)
            self.assertEqual(bootstrap["provenance"]["screeningInterfaceVersion"], "0.1.1")
            self.assertEqual(bootstrap["provenance"]["screeningHandbookSha256"], SCREENING_HANDBOOK_SHA256)
            page = (ROOT / "src/annotation/publication_pilot1/static/index.html").read_text(encoding="utf-8")
            self.assertIn("Screening is prospective routing, not annotation.", page)
            self.assertIn("Do not use external search or AI assistance", page)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
