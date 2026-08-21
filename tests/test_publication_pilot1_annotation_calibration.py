"""Focused synthetic tests for Publication Pilot 1 Annotation / Calibration Mode."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from src.annotation.publication_pilot1.calibration.contracts import (
    CALIBRATION_ID_ORDER_HASH,
    CANDIDATE_ID_ORDER_HASH,
    PRIVATE_SCREENING_HASH,
    PRIVATE_SCREENING_RELATIVE,
    PROTECTED_HASHES,
    REGRESSION_SOURCE_UNIT_ID,
    AnnotationContractError,
    AnnotationContracts,
    canonical_json_hash,
    load_annotation_contracts,
    production_activation_payload,
    validate_effective_route,
    verify_protected_hashes,
)
from src.annotation.publication_pilot1.calibration.service import AnnotationService, active_timing_minutes
from src.annotation.publication_pilot1.calibration.store import AnnotationStore
from src.annotation.publication_pilot1.calibration.validation import validate_annotation


ROOT = Path(__file__).resolve().parents[1]


class MinuteClock:
    """Return deterministic timestamps one minute apart."""

    def __init__(self) -> None:
        """Initialize before the first timestamp."""

        self.minute = -1

    def __call__(self) -> str:
        """Return the next deterministic UTC timestamp."""

        self.minute += 1
        return f"2026-08-19T00:{self.minute:02d}:00.000000Z"


class AnnotationCalibrationTests(unittest.TestCase):
    """Exercise evidence, semantics, corrected routing, timing, and isolation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load discarded synthetic contracts only."""

        cls.contracts = load_annotation_contracts(ROOT)
        cls.unit_id = cls.contracts.unit_order[0]
        cls.text = cls.contracts.source_text(cls.unit_id)

    def setUp(self) -> None:
        """Create isolated temporary runtime storage."""

        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.runtime = Path(self.temporary.name)

    def span(self, literal: str, source_unit_id: str | None = None) -> dict[str, object]:
        """Return an exact code-point span for a literal."""

        unit_id = source_unit_id or self.unit_id
        text = self.contracts.source_text(unit_id)
        start = text.index(literal)
        return {
            "sourceUnitID": unit_id,
            "sourceUnitTextHash": self.contracts.units_by_id[unit_id]["textHash"],
            "startOffset": start,
            "endOffset": start + len(literal),
            "exactText": literal,
        }

    def payload(self) -> dict[str, object]:
        """Return a minimal editable draft."""

        return {"workflowState": "node_pass", "nodes": [], "relations": [], "targetStates": [], "uncertainties": []}

    def exposures(self, *context_unit_ids: str) -> list[dict[str, object]]:
        """Return valid synthetic append-only context exposure records."""

        primary = self.contracts.units_by_id[self.unit_id]
        rows = []
        for index, context_id in enumerate(context_unit_ids, start=1):
            context = self.contracts.units_by_id[context_id]
            same_section = context["sectionID"] == primary["sectionID"]
            rows.append({
                "exposureID": index,
                "primarySourceUnitID": self.unit_id,
                "contextSourceUnitID": context_id,
                "contextScope": "section_context" if same_section else "document_reconciliation",
                "contextPolicyName": "bounded_human_annotation_context",
                "contextPolicyVersion": "0.1.0",
                "contextSelectionReason": "same_section_context" if same_section else "distributed_assertion_evidence",
                "taskBindingType": None if same_section else "operational_target",
                "taskBindingID": None if same_section else "PUB-N-A-P13-METHOD",
                "exposedAt": f"2026-08-20T00:00:{index:02d}.000000Z",
            })
        return rows

    def node(self, local_id: str, target_id: str, literal: str) -> dict[str, object]:
        """Return one proposed synthetic node."""

        return {
            "localID": local_id, "operationalTargetID": target_id, "action": "propose_new",
            "existingNodeID": None, "deferredRecordID": None, "mentionSpan": self.span(literal),
            "evidence": [self.span(literal)],
        }

    def store(self, name: str, annotator: str = "annotator-a", clock=None) -> AnnotationStore:
        """Create one isolated synthetic store."""

        return AnnotationStore(
            self.runtime / f"{name}.sqlite3", mode="synthetic", annotation_session_id=name,
            annotator_id=annotator, bindings={"fixture": "discarded-v1"}, clock=clock or MinuteClock(),
        )

    def service(self, name: str) -> tuple[AnnotationService, AnnotationStore]:
        """Create one isolated service and return its owned test store."""

        store = self.store(name); self.addCleanup(store.close)
        return AnnotationService(self.contracts, store, self.runtime / "exports"), store

    def activation_file(self) -> Path:
        """Write an exact temporary activation binding used only for read-only integrity loading."""

        path = self.runtime / "activation.json"
        path.write_text(json.dumps(production_activation_payload(
            ROOT, "synthetic-integrity-reviewer", "synthetic-integrity-session",
            package_build_checkpoint="f" * 40,
        )), encoding="utf-8")
        return path

    def test_exact_source_reconstruction_and_hash(self) -> None:
        """Canonical synthetic text retains code points and exact UTF-8 identity."""

        unit = self.contracts.units_by_id[self.unit_id]
        self.assertIn("Café", self.text); self.assertIn("😀", self.text)
        self.assertEqual(len(self.text), unit["characterCount"])
        self.assertEqual(hashlib.sha256(self.text.encode()).hexdigest(), unit["textHash"])

    def test_canonical_document_hash_is_bound_and_drift_is_rejected(self) -> None:
        """The annotation envelope binds the upstream document hash, never a unit hash substitute."""

        normalized = validate_annotation(
            self.contracts, self.unit_id, self.payload(), annotation_session_id="s", annotator_id="a"
        )
        expected = self.contracts.canonical_document_hash(self.unit_id)
        self.assertEqual(normalized["canonicalDocumentHash"], expected)
        self.assertNotEqual(expected, normalized["sourceUnitTextHash"])
        unit = self.contracts.units_by_id[self.unit_id]
        original = unit["canonicalTextSha256"]
        unit["canonicalTextSha256"] = "0" * 64
        try:
            with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_CANONICAL_DOCUMENT_HASH_DRIFT"):
                validate_annotation(
                    self.contracts, self.unit_id, self.payload(), annotation_session_id="s", annotator_id="a"
                )
        finally:
            unit["canonicalTextSha256"] = original

    def test_discarded_canonical_file_reconstruction(self) -> None:
        """The guarded production reconstruction path slices normalized discarded source exactly."""

        raw = "Prefix\r\nCafe\u0301 😀 suffix\r"
        canonical = "Prefix\nCafe\u0301 😀 suffix\n"
        expected = "Cafe\u0301 😀"
        start = canonical.index(expected)
        source_path = self.runtime / "discarded-source.md"
        source_path.write_bytes(raw.encode("utf-8"))
        inventory_path = self.runtime / "data/curation/papers/pilot1"
        inventory_path.mkdir(parents=True)
        unit = dict(self.contracts.units_by_id[self.unit_id])
        unit.update({
            "sourceFile": "discarded-source.md",
            "startOffsetInDocument": start,
            "endOffsetInDocument": start + len(expected),
            "characterCount": len(expected),
            "textHash": hashlib.sha256(expected.encode("utf-8")).hexdigest(),
            "canonicalTextSha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        })
        unit.pop("text", None)
        (inventory_path / "publication_pilot1_source_unit_inventory.jsonl").write_text(
            json.dumps({**unit, "text": expected}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        guarded = replace(
            self.contracts,
            root=self.runtime,
            mode="calibration",
            units_by_id={self.unit_id: unit},
            canonical_document_hashes={str(unit["paperID"]): hashlib.sha256(canonical.encode("utf-8")).hexdigest()},
        )
        self.assertEqual(guarded.source_text(self.unit_id), expected)

    def test_browser_utf16_codepoint_round_trip(self) -> None:
        """Browser helpers round-trip ASCII, accents, combining text, and astral characters."""

        if shutil.which("node") is None:
            self.fail("Node.js is required for the browser offset conversion test")
        helper = ROOT / "src/annotation/publication_pilot1/calibration/static/selection_offsets.js"
        script = """
const o=require(process.argv[1]);
for(const text of ['ordinary ASCII','café naïve','Cafe\u0301 composed','flow 😀 astral']){
 for(let cp=0;cp<=Array.from(text).length;cp++){
  const u=o.utf16OffsetFromCodePoint(text,cp);
  if(o.codePointOffsetFromUtf16(text,u)!==cp)process.exit(2);
  if(o.sliceByCodePoints(text,0,cp)!==Array.from(text).slice(0,cp).join(''))process.exit(3);
 }
}
if(o.sliceByCodePoints('A😀B',1,2)!=='😀')process.exit(4);
try{o.codePointOffsetFromUtf16('A😀B',2);process.exit(5)}catch(e){if(e.message!=='UTF16_OFFSET_SPLITS_SURROGATE_PAIR')process.exit(6)}
"""
        subprocess.run(["node", "-e", script, str(helper)], check=True, cwd=ROOT)

    def test_node_creation_with_multiple_evidence(self) -> None:
        """A supported node emits accepted candidate and evidence fields."""

        payload = self.payload(); node = self.node("node-0001", "PUB-N-A-P13-METHOD", "method")
        node["evidence"].append(self.span("produced")); payload["nodes"] = [node]
        result = validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        self.assertEqual(result["nodes"][0]["className"], "Method")
        self.assertEqual(len(result["nodes"][0]["evidenceSpanIDs"]), 2)
        self.assertEqual(result["evidenceSpans"][0]["evidenceText"], "method")

    def test_tool_mention_is_distinct_from_supporting_evidence(self) -> None:
        """The smoke-test Tool has exact identity without treating its mention as class support."""

        payload = self.payload()
        node = self.node(
            "node-0001", "PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE", "hydroGOF"
        )
        node["evidence"] = [self.span("we used the R package hydroGOF")]
        payload["nodes"] = [node]
        normalized = validate_annotation(
            self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a"
        )
        result = normalized["nodes"][0]
        self.assertEqual(result["mentionSpan"]["exactText"], "hydroGOF")
        self.assertEqual(result["label"], "hydroGOF")
        support = normalized["evidenceSpans"][int(result["evidenceSpanIDs"][0][-4:]) - 1]
        self.assertEqual(support["evidenceText"], "we used the R package hydroGOF")

    def test_node_mention_is_required_and_not_inferred_from_evidence(self) -> None:
        """Supporting prose cannot stand in for an explicit exact RMSE identity span."""

        payload = self.payload(); node = self.node("node-0001", "PUB-N-A-DOM11-EVALUATIONMETRIC", "RMSE")
        node["evidence"] = [self.span("produced")]; node.pop("mentionSpan"); payload["nodes"] = [node]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_NODE_MENTION_REQUIRED"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_invalid_node_mentions_fail_closed(self) -> None:
        """Mention hashes, code-point slices, literal text, and context authorization are independent checks."""

        base = self.node("node-0001", "PUB-N-A-DOM11-EVALUATIONMETRIC", "RMSE")
        mutations = []
        wrong_hash = dict(base["mentionSpan"]); wrong_hash["sourceUnitTextHash"] = "0" * 64
        mutations.append((wrong_hash, "ANNOTATION_NODE_MENTION_SOURCE_UNIT_HASH_MISMATCH"))
        wrong_offset = dict(base["mentionSpan"]); wrong_offset["endOffset"] = len(self.text) + 1
        mutations.append((wrong_offset, "ANNOTATION_NODE_MENTION_CODEPOINT_RANGE_INVALID"))
        wrong_text = dict(base["mentionSpan"]); wrong_text["exactText"] = "RMSX"
        mutations.append((wrong_text, "ANNOTATION_NODE_MENTION_EXACT_TEXT_MISMATCH"))
        unauthorized = self.span("rainfall data", self.contracts.unit_order[1])
        mutations.append((unauthorized, "ANNOTATION_NODE_MENTION_CONTEXT_NOT_AUTHORIZED"))
        for mention, code in mutations:
            payload = self.payload(); node = dict(base); node["mentionSpan"] = mention; payload["nodes"] = [node]
            with self.subTest(code=code), self.assertRaisesRegex(AnnotationContractError, code):
                validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_context_node_mention_sets_effective_discovery_scope(self) -> None:
        """An actually cited exposed mention, not exposure alone, raises the node scope."""

        context_id = "synthetic:publication:context:0001"
        payload = self.payload(); node = self.node("node-0001", "PUB-N-A-DOM11-EVALUATIONMETRIC", "RMSE")
        node["mentionSpan"] = self.span("reported value", context_id)
        node["evidence"] = [self.span("0.82", context_id)]
        node["discoveryScope"] = "section_context"; payload["nodes"] = [node]
        result = validate_annotation(
            self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a",
            context_exposures=self.exposures(context_id),
        )
        self.assertEqual(result["nodes"][0]["discoveryScope"], "section_context")

    def test_ui_uses_mentions_neutral_controls_and_mode_aware_copy(self) -> None:
        """Static UI wiring closes positive defaults and shows anchored local endpoints."""

        app = (ROOT / "src/annotation/publication_pilot1/calibration/static/app.js").read_text()
        page = (ROOT / "src/annotation/publication_pilot1/calibration/static/index.html").read_text()
        for placeholder in (
            "Select node type...", "Select identity action...", "Select relation...",
            "Select uncertainty target...", "Select uncertainty category...",
        ):
            self.assertIn(placeholder, app)
        self.assertIn("node.mentionSpan.exactText", app)
        self.assertIn("Select a calibration unit to begin.", app)
        self.assertIn("Set node mention from highlight", page)
        self.assertIn('id="add-node" disabled', page)
        self.assertNotIn("code points</small>", app)
        self.assertNotIn("activeContext.sourceUnitTextHash}`", app)

    def test_authorized_context_scopes_and_distributed_evidence(self) -> None:
        """Narrowest scope is derived from exact authorized unit bindings."""

        section_id = "synthetic:publication:context:0001"
        document_id = "synthetic:publication:context:0002"
        payload = self.payload()
        section_node = self.node("node-0001", "PUB-N-A-DOM11-EVALUATIONMETRIC", "RMSE")
        section_node["evidence"] = [self.span("reported value", section_id)]
        section_node["distributedEvidenceReason"] = "The named metric and reported value occur in separate units."
        section_node["discoveryScope"] = "section_context"
        payload["nodes"] = [section_node]
        result = validate_annotation(
            self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a",
            context_exposures=self.exposures(section_id),
        )
        self.assertEqual(result["nodes"][0]["discoveryScope"], "section_context")

        document_node = self.node("node-0001", "PUB-N-A-DOM12-PARAMETER", "flow")
        document_node["evidence"] = [self.span("default parameter", document_id)]
        document_node["distributedEvidenceReason"] = "The node mention and support occur in separate units."
        document_node["discoveryScope"] = "document_reconciliation"
        payload["nodes"] = [document_node]
        result = validate_annotation(
            self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a",
            context_exposures=self.exposures(document_id),
        )
        self.assertEqual(result["nodes"][0]["discoveryScope"], "document_reconciliation")

        distributed = self.node("node-0001", "PUB-N-A-P13-METHOD", "method")
        distributed["evidence"].append(self.span("separate results section", document_id))
        distributed["distributedEvidenceReason"] = "Identity and result are stated in separate canonical units."
        distributed["discoveryScope"] = "document_reconciliation"
        payload["nodes"] = [distributed]
        result = validate_annotation(
            self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a",
            context_exposures=self.exposures(document_id),
        )
        node = result["nodes"][0]
        self.assertEqual(node["discoveryScope"], "document_reconciliation")
        self.assertEqual(len({result["evidenceSpans"][int(ref[-4:]) - 1]["sourceUnitID"] for ref in node["evidenceSpanIDs"]}), 2)

    def test_context_binding_mismatch_cross_unit_span_and_scope_are_rejected(self) -> None:
        """Backend checks each context unit/hash/slice and does not permit cross-unit spans."""

        section_id = "synthetic:publication:context:0001"
        payload = self.payload()
        node = self.node("node-0001", "PUB-N-A-DOM11-EVALUATIONMETRIC", "RMSE")
        wrong_hash = self.span("reported value", section_id); wrong_hash["sourceUnitTextHash"] = "0" * 64
        node["evidence"] = [wrong_hash]; payload["nodes"] = [node]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_EVIDENCE_SOURCE_UNIT_HASH_MISMATCH"):
            validate_annotation(
                self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a",
                context_exposures=self.exposures(section_id),
            )

        unauthorized = self.span("rainfall data", self.contracts.unit_order[1])
        node["evidence"] = [unauthorized]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

        crossing = self.span("abc123")
        crossing["endOffset"] = len(self.text) + 2
        crossing["exactText"] = "abc123\nThe"
        node["evidence"] = [crossing]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_EVIDENCE_CODEPOINT_RANGE_INVALID"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

        node["evidence"] = [self.span("reported value", section_id)]
        node["discoveryScope"] = "local_unit"
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_DISCOVERY_SCOPE_MISMATCH"):
            validate_annotation(
                self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a",
                context_exposures=self.exposures(section_id),
            )

    def test_distributed_evidence_requires_operational_reason(self) -> None:
        """A multi-unit assertion records why its evidence must be combined."""

        node = self.node("node-0001", "PUB-N-A-P13-METHOD", "method")
        node["evidence"].append(self.span("reported value", "synthetic:publication:context:0001"))
        payload = self.payload(); payload["nodes"] = [node]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_DISTRIBUTED_EVIDENCE_REASON_REQUIRED"):
            validate_annotation(
                self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a",
                context_exposures=self.exposures("synthetic:publication:context:0001"),
            )

    def test_primary_open_is_lazy_and_cross_section_text_is_not_read(self) -> None:
        """Opening a unit reads only primary text and returns metadata-only context candidates."""

        service, _ = self.service("lazy-primary")
        observed: list[str] = []
        original = self.contracts.source_text

        def tracked(_contracts: AnnotationContracts, source_unit_id: str) -> str:
            """Record each exact source-text read."""

            observed.append(source_unit_id)
            return original(source_unit_id)

        with patch.object(AnnotationContracts, "source_text", autospec=True, side_effect=tracked):
            unit = service.unit(self.unit_id)
        self.assertEqual(observed, [self.unit_id])
        self.assertEqual([row["sourceUnitID"] for row in unit["contextUnits"]], [self.unit_id])
        self.assertTrue(unit["sectionContextCandidates"])
        self.assertGreaterEqual(len(unit["documentContextCandidates"]), 2)
        self.assertTrue(all("text" not in row for row in unit["sectionContextCandidates"] + unit["documentContextCandidates"]))

    def test_same_section_and_context_only_units_are_bounded_context_not_primary_tasks(self) -> None:
        """Eligible and context-only same-section units are inspectable without gaining menus."""

        service, store = self.service("section-context")
        context_only_id = "synthetic:publication:context-only:0001"
        opened = service.unit(self.unit_id)
        candidates = {row["sourceUnitID"]: row for row in opened["sectionContextCandidates"]}
        self.assertEqual(candidates[context_only_id]["contextEligibility"], "context_only")
        exposed = service.expose_context(
            self.unit_id, context_only_id, context_selection_reason="same_section_context"
        )
        self.assertIn("not an open annotation unit", exposed["contextUnit"]["text"])
        self.assertEqual(exposed["exposure"]["contextScope"], "section_context")
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_SYNTHETIC_UNIT_UNKNOWN"):
            service.unit(context_only_id)
        payload = self.payload()
        node = self.node("node-0001", "PUB-N-A-P13-METHOD", "method")
        node["evidence"] = [self.span("supplies context", context_only_id)]
        node["distributedEvidenceReason"] = "The mention and classification context occur in separate units."
        payload["nodes"] = [node]
        saved = service.save(self.unit_id, payload)
        self.assertEqual(saved["nodes"][0]["discoveryScope"], "section_context")
        self.assertEqual(store.exposed_context_ids(self.unit_id), (context_only_id,))

    def test_excluded_or_unresolved_units_cannot_become_context_evidence_sources(self) -> None:
        """Human context eligibility never promotes structurally unsafe source units."""

        service, _ = self.service("unsafe-context")
        service.unit(self.unit_id)
        context_id = "synthetic:publication:context:0003"
        unit = self.contracts.units_by_id[context_id]
        original = unit["eligibility"]
        for unsafe in ("excluded", "needs_review"):
            unit["eligibility"] = unsafe
            try:
                self.assertNotIn(context_id, self.contracts.context_candidate_ids(self.unit_id))
                with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED"):
                    service.expose_context(
                        self.unit_id, context_id, context_selection_reason="distributed_assertion_evidence",
                        operational_target_id="PUB-N-A-P13-METHOD",
                    )
            finally:
                unit["eligibility"] = original

    def test_cross_section_escalation_requires_reason_and_task_binding(self) -> None:
        """Document context is unavailable until one routed target or unresolved assertion authorizes it."""

        service, _ = self.service("document-guard")
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_CONTEXT_PRIMARY_UNIT_NOT_OPEN"):
            service.expose_context(
                self.unit_id, "synthetic:publication:context:0002",
                context_selection_reason="distributed_assertion_evidence",
                operational_target_id="PUB-N-A-P13-METHOD",
            )
        service.unit(self.unit_id)
        context_id = "synthetic:publication:context:0002"
        payload = self.payload(); node = self.node("node-0001", "PUB-N-A-P13-METHOD", "method")
        node["evidence"] = [self.span("default parameter", context_id)]; payload["nodes"] = [node]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED"):
            service.save(self.unit_id, payload)
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_DOCUMENT_CONTEXT_REASON_INVALID"):
            service.expose_context(self.unit_id, context_id, context_selection_reason="")
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_DOCUMENT_CONTEXT_TASK_BINDING_REQUIRED"):
            service.expose_context(
                self.unit_id, context_id, context_selection_reason="distributed_assertion_evidence"
            )
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_DOCUMENT_CONTEXT_TARGET_NOT_ROUTED"):
            service.expose_context(
                self.unit_id, context_id, context_selection_reason="distributed_assertion_evidence",
                operational_target_id="PUB-N-A-P20-CONCLUSION",
            )

    def test_cross_section_loading_is_one_unit_at_a_time_and_scope_depends_on_used_evidence(self) -> None:
        """Escalation loads only the selected unit; exposure alone does not inflate assertion scope."""

        service, store = self.service("document-one-at-a-time")
        service.unit(self.unit_id)
        selected = "synthetic:publication:context:0002"
        still_hidden = "synthetic:publication:context:0003"
        result = service.expose_context(
            self.unit_id, selected, context_selection_reason="distributed_assertion_evidence",
            operational_target_id="PUB-N-A-P13-METHOD",
        )
        self.assertEqual(result["contextUnit"]["sourceUnitID"], selected)
        self.assertEqual(store.exposed_context_ids(self.unit_id), (selected,))
        reopened = service.unit(self.unit_id)
        self.assertEqual({row["sourceUnitID"] for row in reopened["contextUnits"]}, {self.unit_id, selected})
        self.assertIn(still_hidden, {row["sourceUnitID"] for row in reopened["documentContextCandidates"]})
        local = self.payload(); local["nodes"] = [self.node("node-0001", "PUB-N-A-P13-METHOD", "method")]
        self.assertEqual(service.save(self.unit_id, local)["nodes"][0]["discoveryScope"], "local_unit")
        local["nodes"][0]["evidence"] = [self.span("default parameter", selected)]
        local["nodes"][0]["distributedEvidenceReason"] = "The mention and support occur in separate units."
        self.assertEqual(service.save(self.unit_id, local)["nodes"][0]["discoveryScope"], "document_reconciliation")
        local["nodes"][0]["evidence"] = [self.span("later discussion", still_hidden)]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED"):
            service.save(self.unit_id, local)

    def test_unresolved_assertion_can_bind_a_narrow_document_context_request(self) -> None:
        """An existing local assertion ID is an auditable alternative to a routed-target binding."""

        service, _ = self.service("unresolved-context")
        service.unit(self.unit_id)
        payload = self.payload(); payload["nodes"] = [self.node("node-0001", "PUB-N-A-P13-METHOD", "method")]
        service.save(self.unit_id, payload)
        result = service.expose_context(
            self.unit_id, "synthetic:publication:context:0003",
            context_selection_reason="document_local_entity_reconciliation",
            unresolved_assertion_id="node-0001",
        )
        self.assertEqual(result["exposure"]["taskBindingType"], "unresolved_assertion")
        self.assertEqual(result["exposure"]["taskBindingID"], "node-0001")

    def test_deterministic_endpoints_follow_the_exposed_context_boundary(self) -> None:
        """A context-contributed Phase-B ref appears only after that exact unit is exposed."""

        service, _ = self.service("endpoint-context-boundary")
        tool_id = "publication:tool:07b292b28372c3181bec"
        opened = service.unit(self.unit_id)
        self.assertNotIn(tool_id, {row["endpointID"] for row in opened["deterministicEndpoints"]})
        service.expose_context(
            self.unit_id, "synthetic:publication:context:0001",
            context_selection_reason="same_section_context",
        )
        self.assertNotIn(tool_id, {row["endpointID"] for row in service.unit(self.unit_id)["deterministicEndpoints"]})
        escalated = service.expose_context(
            self.unit_id, "synthetic:publication:context:0002",
            context_selection_reason="relation_endpoint_reconciliation",
            operational_target_id="PUB-R-C-P32-REFERENCESREPOSITORY",
        )
        self.assertIn(tool_id, {row["endpointID"] for row in escalated["deterministicEndpoints"]})

    def test_context_exposure_metadata_is_normalized_persisted_and_exported(self) -> None:
        """The annotation snapshot and session export reproduce every inspectable context unit."""

        service, store = self.service("context-audit")
        service.unit(self.unit_id)
        section_id = "synthetic:publication:context:0001"
        document_id = "synthetic:publication:context:0002"
        service.expose_context(self.unit_id, section_id, context_selection_reason="same_section_context")
        service.expose_context(
            self.unit_id, document_id, context_selection_reason="cross_section_coreference",
            operational_target_id="PUB-N-A-P13-METHOD",
        )
        saved = service.save(self.unit_id, self.payload())
        self.assertEqual(saved["primarySourceUnitID"], self.unit_id)
        self.assertEqual(saved["contextSourceUnitIDs"], [section_id, document_id])
        self.assertEqual(saved["contextPolicyName"], "bounded_human_annotation_context")
        self.assertEqual(len(saved["contextExposureEvents"]), 2)
        schema = json.loads((ROOT / "schemas/publication_pilot1_annotation_record.schema.json").read_text())
        annotation_record = {key: value for key, value in saved.items() if key != "persistence"}
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(annotation_record)), [])
        malformed = json.loads(json.dumps(annotation_record)); malformed["contextExposureEvents"][0]["extra"] = True
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(malformed)))
        exported = json.loads(service.export().read_text())
        self.assertEqual(len(exported["contextExposures"]), 2)
        self.assertEqual(store.context_exposures(self.unit_id), exported["contextExposures"])

    def test_node_without_evidence_is_rejected(self) -> None:
        """No semantic node survives backend validation without evidence."""

        payload = self.payload(); node = self.node("node-0001", "PUB-N-A-P13-METHOD", "method")
        node["evidence"] = []; payload["nodes"] = [node]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_NODE_EVIDENCE_REQUIRED"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def relation_payload(self) -> dict[str, object]:
        """Return compatible Method-to-Finding nodes and a produces edge."""

        payload = self.payload(); payload["workflowState"] = "relation_pass"
        payload["nodes"] = [
            self.node("node-0001", "PUB-N-A-P13-METHOD", "method"),
            self.node("node-0002", "PUB-N-A-P16-FINDING", "a clear finding"),
        ]
        payload["relations"] = [{
            "localID": "edge-0001", "operationalTargetID": "PUB-R-C-P07-PRODUCES",
            "sourceEndpointID": "node-0001", "targetEndpointID": "node-0002",
            "deferredRecordID": None, "evidence": [self.span("method produced a clear finding")],
        }]
        return payload

    def test_relation_creation_requires_edge_specific_evidence(self) -> None:
        """A directional edge stores evidence separate from endpoint evidence."""

        result = validate_annotation(self.contracts, self.unit_id, self.relation_payload(), annotation_session_id="s", annotator_id="a")
        edge = result["relations"][0]
        self.assertEqual(edge["source"]["referenceID"], "node-0001")
        self.assertEqual(edge["target"]["referenceID"], "node-0002")
        self.assertEqual(result["evidenceSpans"][-1]["evidenceText"], "method produced a clear finding")

    def test_relation_without_edge_evidence_is_rejected(self) -> None:
        """Endpoint spans cannot substitute for relation-specific evidence."""

        payload = self.relation_payload(); payload["relations"][0]["evidence"] = []
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_RELATION_EDGE_EVIDENCE_REQUIRED"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_missing_endpoint_and_wrong_direction_are_rejected(self) -> None:
        """Relations require both compatible endpoints in frozen direction."""

        payload = self.relation_payload(); payload["relations"][0]["sourceEndpointID"] = ""
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_RELATION_ENDPOINT_MISSING"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        payload = self.relation_payload(); edge = payload["relations"][0]
        edge["sourceEndpointID"], edge["targetEndpointID"] = edge["targetEndpointID"], edge["sourceEndpointID"]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_RELATION_DOMAIN_RANGE_MISMATCH"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_current_paper_is_an_exact_deterministic_endpoint(self) -> None:
        """A routed Paper-to-dataset edge may use only the bound current-paper endpoint."""

        unit_id = self.contracts.unit_order[1]
        text = self.contracts.source_text(unit_id)
        literal = "rainfall data"
        start = text.index(literal)
        payload = self.payload()
        payload["workflowState"] = "relation_pass"
        payload["nodes"] = [{
            "localID": "node-0001",
            "operationalTargetID": "PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE",
            "action": "propose_new",
            "existingNodeID": None,
            "deferredRecordID": None,
            "mentionSpan": {
                "sourceUnitID": unit_id,
                "sourceUnitTextHash": self.contracts.units_by_id[unit_id]["textHash"],
                "startOffset": start, "endOffset": start + len(literal), "exactText": literal,
            },
            "evidence": [{
                "sourceUnitID": unit_id,
                "sourceUnitTextHash": self.contracts.units_by_id[unit_id]["textHash"],
                "startOffset": start,
                "endOffset": start + len(literal),
                "exactText": literal,
            }],
        }]
        edge_text = "model uses rainfall data"
        edge_start = text.index(edge_text)
        payload["relations"] = [{
            "localID": "edge-0001",
            "operationalTargetID": "PUB-R-C-P20-USESDATASET-NEW-PROSE-EVIDENCE",
            "sourceEndpointID": "paper:synthetic-2",
            "targetEndpointID": "node-0001",
            "deferredRecordID": None,
            "evidence": [{
                "sourceUnitID": unit_id,
                "sourceUnitTextHash": self.contracts.units_by_id[unit_id]["textHash"],
                "startOffset": edge_start,
                "endOffset": edge_start + len(edge_text),
                "exactText": edge_text,
            }],
        }]
        result = validate_annotation(self.contracts, unit_id, payload, annotation_session_id="s", annotator_id="a")
        self.assertEqual(result["relations"][0]["source"], {
            "referenceType": "deterministic_node",
            "referenceID": "paper:synthetic-2",
            "artifactID": "synthetic:discarded:publication:synthetic-2",
        })

    def test_exact_phase_b_endpoint_bridge_and_relation_scope(self) -> None:
        """Only an exact source-unit ref resolves to its frozen Phase-B identity and class."""

        exact_id = "publication:repository:0603320a21f133eb4ad8"
        service_store = self.store("endpoint-bridge"); self.addCleanup(service_store.close)
        unit = AnnotationService(self.contracts, service_store, self.runtime / "exports").unit(self.unit_id)
        endpoint = next(row for row in unit["deterministicEndpoints"] if row["endpointID"] == exact_id)
        self.assertEqual((endpoint["className"], endpoint["displayLabel"]), ("Repository", "tempest"))

        payload = self.payload(); payload["workflowState"] = "relation_pass"
        payload["relations"] = [{
            "localID": "edge-0001", "operationalTargetID": "PUB-R-C-P32-REFERENCESREPOSITORY",
            "sourceEndpointID": "paper:synthetic", "targetEndpointID": exact_id,
            "deferredRecordID": None, "evidence": [self.span("Repository")],
            "relationScope": "inter_source",
        }]
        result = validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        self.assertEqual(result["relations"][0]["target"]["referenceID"], exact_id)
        self.assertEqual(result["relations"][0]["relationScope"], "inter_source")
        self.assertEqual(validate_annotation(
            self.contracts, self.unit_id, self.relation_payload(), annotation_session_id="s", annotator_id="a"
        )["relations"][0]["relationScope"], "intra_source")

        payload["relations"][0]["targetEndpointID"] = "tempest"
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_RELATION_ENDPOINT_UNKNOWN"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_relation_scope_audit_protects_the_six_external_artifact_targets(self) -> None:
        """Accepted effective routing disproves an unconditional intra-source invariant."""

        routes = [
            json.loads(line)
            for line in (ROOT / "data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl").read_text().splitlines()
        ]
        effective = {target for route in routes for target in route["eligibleRelationOperationalTargetIDs"]}
        external_classes = {"DatasetMention", "DatasetResource", "Repository", "Tool"}
        external_targets = {
            target_id for target_id in effective
            if any(
                external_classes & set(signature[side]["classes"])
                for signature in self.contracts.relation_targets[target_id]["operational_signatures"]
                for side in ("domain", "range")
            )
        }
        self.assertEqual(external_targets, {
            "PUB-R-C-P15-USESTOOL",
            "PUB-R-C-P20-USESDATASET-NEW-PROSE-EVIDENCE",
            "PUB-R-C-P24-MENTIONSDATASET",
            "PUB-R-C-P31-MENTIONSTOOL",
            "PUB-R-C-P32-REFERENCESREPOSITORY",
            "PUB-R-C-P33-HASCODEREPOSITORY",
        })
        self.assertTrue(all(
            "Paper" in signature["domain"]["classes"]
            for target_id in external_targets
            for signature in self.contracts.relation_targets[target_id]["operational_signatures"]
            if external_classes & set(signature["range"]["classes"])
        ))

    def test_unavailable_deterministic_ref_is_rejected_without_label_resolution(self) -> None:
        """Unknown refs fail exact Phase-B resolution; raw labels are never promoted."""

        unit = self.contracts.units_by_id[self.unit_id]
        original = list(unit["deterministicNodeRefs"])
        unit["deterministicNodeRefs"] = original + ["tempest"]
        try:
            with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_DETERMINISTIC_NODE_REF_UNRESOLVED"):
                self.contracts.deterministic_endpoints(self.unit_id)
        finally:
            unit["deterministicNodeRefs"] = original

    def test_structured_node_attributes_and_independent_evidence(self) -> None:
        """Only the six frozen class-bound attributes normalize with their own evidence."""

        section_id = "synthetic:publication:context:0001"
        metric = self.node("node-0001", "PUB-N-A-DOM11-EVALUATIONMETRIC", "RMSE")
        metric["evidence"] = [self.span("reported value", section_id)]
        metric["distributedEvidenceReason"] = "The metric mention and value occur in separate units."
        metric["attributes"] = [{"attributeName": "value", "value": "0.82", "evidence": [self.span("0.82", section_id)]}]
        parameter = self.node("node-0002", "PUB-N-A-DOM12-PARAMETER", "flow")
        parameter["evidence"] = [self.span("parameter range", section_id)]
        parameter["attributes"] = [
            {"attributeName": "value", "value": "2", "evidence": [self.span("2", section_id)]},
            {"attributeName": "range", "value": "2–5", "evidence": [self.span("2–5", section_id)]},
            {"attributeName": "calibrationStatus", "value": "default", "evidence": [self.span("default", "synthetic:publication:context:0002")]},
        ]
        parameter["distributedEvidenceReason"] = "Range and status occur in separate canonical units."
        repository = self.node("node-0003", "PUB-N-A-C01-REPOSITORY-NAMED-WITHOUT-EXACT-IDENTITY", "Repository")
        repository["attributes"] = [
            {"attributeName": "fork", "value": True, "evidence": [self.span("fork")]},
            {"attributeName": "commitSHA", "value": "abc123", "evidence": [self.span("abc123")]},
        ]
        payload = self.payload(); payload["nodes"] = [metric, parameter, repository]
        result = validate_annotation(
            self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a",
            context_exposures=self.exposures(section_id, "synthetic:publication:context:0002"),
        )
        attrs = {node["className"]: node["attributes"] for node in result["nodes"]}
        self.assertEqual(attrs["EvaluationMetric"][0]["value"], "0.82")
        self.assertEqual({row["attributeName"] for row in attrs["Parameter"]}, {"value", "range", "calibrationStatus"})
        self.assertEqual({row["attributeName"] for row in attrs["Repository"]}, {"fork", "commitSHA"})

    def test_invalid_structured_attributes_are_rejected(self) -> None:
        """Unsupported, class-incompatible, and unsupported assertions cannot enter output."""

        repository = self.node("node-0001", "PUB-N-A-C01-REPOSITORY-NAMED-WITHOUT-EXACT-IDENTITY", "Repository")
        payload = self.payload(); payload["nodes"] = [repository]
        repository["attributes"] = [{"attributeName": "fork", "value": True, "evidence": []}]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_NODE_ATTRIBUTE_EVIDENCE_REQUIRED"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        repository["attributes"] = [{"attributeName": "license", "value": "MIT", "evidence": [self.span("Repository")]}]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_NODE_ATTRIBUTE_UNSUPPORTED"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        method = self.node("node-0001", "PUB-N-A-P13-METHOD", "method")
        method["attributes"] = [{"attributeName": "commitSHA", "value": "abc123", "evidence": [self.span("abc123")]}]
        payload["nodes"] = [method]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_NODE_ATTRIBUTE_CLASS_INCOMPATIBLE"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        repository["attributes"] = [{
            "attributeName": "commitSHA", "value": "ABC123-normalized", "evidence": [self.span("abc123")]
        }]
        payload["nodes"] = [repository]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_NODE_ATTRIBUTE_EXACT_SOURCE_VALUE_REQUIRED"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_abstract_target_and_duplicate_local_ids_are_rejected(self) -> None:
        """Backend protection does not depend on the browser menu staying honest."""

        target = self.contracts.node_targets["PUB-N-A-P13-METHOD"]
        original = target["direct_instantiation"]
        target["direct_instantiation"] = False
        try:
            payload = self.payload()
            payload["nodes"] = [self.node("node-0001", "PUB-N-A-P13-METHOD", "method")]
            with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_ABSTRACT_NODE_TARGET_FORBIDDEN"):
                validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        finally:
            target["direct_instantiation"] = original

        payload = self.payload()
        payload["nodes"] = [
            self.node("node-0001", "PUB-N-A-P13-METHOD", "method"),
            self.node("node-0001", "PUB-N-A-P16-FINDING", "a clear finding"),
        ]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_DUPLICATE_LOCAL_ID"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_effective_route_not_human_screened_route_drives_menu(self) -> None:
        """Historical screened deferred targets never enter the effective menu."""

        route = self.contracts.routes_by_id[self.unit_id]
        deferred_node = "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B"
        deferred_edge = "PUB-R-C-P29-REFERENCESDATASET-EXACT-OMITTED-IDENTIFIER"
        self.assertIn(deferred_node, route["humanScreenedNodeOperationalTargetIDs"])
        self.assertNotIn(deferred_node, route["eligibleNodeOperationalTargetIDs"])
        store = self.store("effective-menu"); self.addCleanup(store.close)
        unit = AnnotationService(self.contracts, store, self.runtime / "exports").unit(self.unit_id)
        self.assertNotIn(deferred_node, {row["operationalTargetID"] for row in unit["nodeTargets"]})
        self.assertNotIn(deferred_edge, {row["operationalTargetID"] for row in unit["relationTargets"]})
        self.assertEqual(unit["endpointClassExpansions"], self.contracts.class_expansions)

    def test_structurally_unavailable_target_cannot_be_annotated(self) -> None:
        """Unavailable routing provenance is neither an annotation task nor a negative."""

        payload = self.payload()
        payload["nodes"] = [self.node("node-0001", "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B", "flow")]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_STRUCTURALLY_UNAVAILABLE_TARGET_FORBIDDEN"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_deferred_without_exact_ref_cannot_enter_and_id_is_not_synthesized(self) -> None:
        """Deferred IDs are accepted only from exact materialized refs and never generated."""

        route = self.contracts.routes_by_id[self.unit_id]
        original_effective = list(route["eligibleNodeOperationalTargetIDs"])
        original_unavailable = list(route["structurallyUnavailableOperationalTargets"])
        deferred = "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B"
        route["eligibleNodeOperationalTargetIDs"] = original_effective + [deferred]
        route["structurallyUnavailableOperationalTargets"] = []
        try:
            with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_DEFERRED_TARGET_WITHOUT_EXACT_BINDING"):
                validate_effective_route(
                    route,
                    self.contracts.units_by_id[self.unit_id],
                    {target_id for target_id, target in self.contracts.node_targets.items()
                     if target["pilot_treatment"] == "deferred_resolution"},
                )
        finally:
            route["eligibleNodeOperationalTargetIDs"] = original_effective
            route["structurallyUnavailableOperationalTargets"] = original_unavailable
        normalized = validate_annotation(self.contracts, self.unit_id, self.payload(), annotation_session_id="s", annotator_id="a")
        self.assertNotIn("deferredRecordID", json.dumps(normalized["evidenceSpans"]))
        self.assertFalse(any(node.get("deferredRecordID") for node in normalized["nodes"]))

    def test_regression_calibration_unit_passes_activation_with_deferred_excluded(self) -> None:
        """The pub:34 regression unit remains open with only valid effective targets."""

        contracts = load_annotation_contracts(ROOT, mode="calibration", activation_path=self.activation_file())
        self.assertIn(REGRESSION_SOURCE_UNIT_ID, contracts.unit_order)
        self.assertNotIn("text", contracts.units_by_id[REGRESSION_SOURCE_UNIT_ID])
        route = contracts.routes_by_id[REGRESSION_SOURCE_UNIT_ID]
        unavailable = {row["operationalTargetID"] for row in route["structurallyUnavailableOperationalTargets"]}
        effective = set(route["eligibleNodeOperationalTargetIDs"]) | set(route["eligibleRelationOperationalTargetIDs"])
        self.assertTrue(unavailable); self.assertTrue(effective); self.assertTrue(unavailable.isdisjoint(effective))
        self.assertEqual(route["routingStatus"], "routed")

    def test_non_effective_target_and_no_semantic_truncation(self) -> None:
        """Backend rejects non-effective targets and service never truncates long routes."""

        payload = self.payload(); payload["nodes"] = [self.node("node-0001", "PUB-N-A-P20-CONCLUSION", "finding")]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_NODE_TARGET_NOT_EFFECTIVELY_ROUTED"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        route = self.contracts.routes_by_id[self.unit_id]
        old_effective, old_screened = list(route["eligibleNodeOperationalTargetIDs"]), list(route["humanScreenedNodeOperationalTargetIDs"])
        thirteen = list(self.contracts.node_targets)[:13]
        route["eligibleNodeOperationalTargetIDs"] = thirteen; route["humanScreenedNodeOperationalTargetIDs"] = thirteen
        store = self.store("long-menu"); self.addCleanup(store.close)
        try:
            self.assertEqual(len(AnnotationService(self.contracts, store, self.runtime / "exports").unit(self.unit_id)["nodeTargets"]), 13)
        finally:
            route["eligibleNodeOperationalTargetIDs"] = old_effective; route["humanScreenedNodeOperationalTargetIDs"] = old_screened

    def test_exact_text_cross_unit_and_hash_drift_rejected(self) -> None:
        """Evidence cannot leak between units and route/text identity must agree."""

        payload = self.payload(); payload["nodes"] = [{
            "localID": "node-0001", "operationalTargetID": "PUB-N-A-P13-METHOD", "action": "propose_new",
            "existingNodeID": None, "deferredRecordID": None,
            "mentionSpan": self.span("method"),
            "evidence": [{
                "sourceUnitID": self.unit_id,
                "sourceUnitTextHash": self.contracts.units_by_id[self.unit_id]["textHash"],
                "startOffset": 0,
                "endOffset": 3,
                "exactText": "The",
            }],
        }]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_EVIDENCE_EXACT_TEXT_MISMATCH"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")
        route = self.contracts.routes_by_id[self.unit_id]; original = route["sourceUnitTextHash"]
        route["sourceUnitTextHash"] = "0" * 64
        try:
            with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_SOURCE_UNIT_HASH_DRIFT"):
                validate_annotation(self.contracts, self.unit_id, self.payload(), annotation_session_id="s", annotator_id="a")
        finally:
            route["sourceUnitTextHash"] = original

    def test_monitor_empty_is_not_exhaustive_negative(self) -> None:
        """Monitor completion remains distinct from completed zero-positive evaluate review."""

        route = self.contracts.routes_by_id[self.unit_id]
        monitored = next(t for t in route["eligibleNodeOperationalTargetIDs"] if self.contracts.node_targets[t]["pilot_treatment"] == "extract_and_monitor")
        payload = self.payload(); payload["targetStates"] = [{"operationalTargetID": monitored, "state": "reviewed_no_positive"}]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_TARGET_STATE_INCOMPATIBLE"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_submit_requires_every_effective_target_state(self) -> None:
        """Final submit requires actual completion state for every effective target."""

        payload = self.payload(); payload["workflowState"] = "review"
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_SUBMIT_TARGET_REVIEW_INCOMPLETE"):
            validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a", require_complete=True)

    def test_two_annotator_stores_are_independent(self) -> None:
        """One annotator cannot see or reuse another annotator's session state."""

        first, second = self.store("session-a", "annotator-a"), self.store("session-b", "annotator-b")
        self.addCleanup(first.close); self.addCleanup(second.close)
        normalized = validate_annotation(self.contracts, self.unit_id, self.payload(), annotation_session_id="session-a", annotator_id="annotator-a")
        first.save(self.unit_id, normalized); first.log_timing(self.unit_id, self.contracts.units_by_id[self.unit_id]["textHash"], "unit_opened")
        self.assertIsNone(second.load(self.unit_id)); self.assertEqual(second.timing_events(self.unit_id), [])
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_STATE_CONTRACT_MISMATCH:annotatorID"):
            AnnotationStore(first.path, mode="synthetic", annotation_session_id="session-a", annotator_id="annotator-b", bindings={"fixture": "discarded-v1"})

    def test_autosave_submission_reopen_revision_history(self) -> None:
        """Submission snapshots remain immutable across an auditable reopen."""

        store = self.store("revisions"); self.addCleanup(store.close)
        normalized = validate_annotation(self.contracts, self.unit_id, self.payload(), annotation_session_id="revisions", annotator_id="annotator-a")
        self.assertEqual(store.save(self.unit_id, normalized)["persistence"]["revisionNumber"], 1)
        self.assertEqual(store.submit(self.unit_id, normalized)["persistence"]["status"], "submitted")
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_SUBMITTED_RECORD_REOPEN_REQUIRED"):
            store.save(self.unit_id, normalized)
        self.assertEqual(store.reopen(self.unit_id, "Correct span boundary")["persistence"]["status"], "reopened")
        exported = store.export_payload()
        self.assertEqual(len(exported["submissions"]), 1); self.assertEqual(exported["auditActions"][-1]["action"], "reopened")

    def test_explicit_export_is_deterministic_and_revalidated(self) -> None:
        """Unchanged validated local state exports to byte-identical JSON and digest files."""

        store = self.store("deterministic-export")
        self.addCleanup(store.close)
        service = AnnotationService(self.contracts, store, self.runtime / "exports")
        service.save(self.unit_id, self.payload())
        first = service.export()
        first_bytes = first.read_bytes()
        digest_path = first.with_suffix(".annotation.sha256")
        self.assertEqual(digest_path.read_text().strip(), hashlib.sha256(first_bytes).hexdigest())
        second = service.export()
        self.assertEqual(second.read_bytes(), first_bytes)

    def test_timing_bindings_pause_and_interruption_exclusion(self) -> None:
        """Active time derives from frozen events after exclusions."""

        store = self.store("timing", clock=MinuteClock()); self.addCleanup(store.close)
        source_hash = self.contracts.units_by_id[self.unit_id]["textHash"]
        sequence = ["unit_opened", "pause_started", "pause_ended", "reading_complete", "node_pass_started", "technical_interruption_started", "technical_interruption_ended", "node_pass_completed", "relation_pass_started", "relation_pass_completed", "review_started", "submitted"]
        for event in sequence:
            record = store.log_timing(self.unit_id, source_hash, event)
            self.assertEqual(record["annotationSessionID"], "timing"); self.assertEqual(record["annotatorID"], "annotator-a")
            self.assertEqual(record["sourceUnitTextHash"], source_hash); self.assertEqual(record["routingVersion"], "0.1.2")
        summary = active_timing_minutes(store.timing_events(self.unit_id))
        self.assertEqual(summary, {"readingMinutes": 2.0, "nodePassMinutes": 2.0, "relationPassMinutes": 1.0, "reviewSubmitMinutes": 1.0, "activeAnnotationMinutes": 6.0})

    def test_malformed_timing_sequence_rejected(self) -> None:
        """Knowable ordering and nesting failures are rejected."""

        store = self.store("bad-timing"); self.addCleanup(store.close)
        source_hash = self.contracts.units_by_id[self.unit_id]["textHash"]
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_TIMING_SEQUENCE_INVALID"):
            store.log_timing(self.unit_id, source_hash, "node_pass_started")
        store.log_timing(self.unit_id, source_hash, "unit_opened"); store.log_timing(self.unit_id, source_hash, "pause_started")
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_TIMING_PAUSE_NESTING_INVALID"):
            store.log_timing(self.unit_id, source_hash, "pause_started")

    def test_production_reset_forbidden_and_activation_required(self) -> None:
        """Dry-run reset cannot touch production and default startup cannot expose calibration."""

        store = AnnotationStore(self.runtime / "production.sqlite3", mode="calibration", annotation_session_id="p", annotator_id="a", bindings={"fixture": "none"})
        self.addCleanup(store.close)
        with self.assertRaisesRegex(AnnotationContractError, "CALIBRATION_PRODUCTION_RESET_FORBIDDEN"):
            store.reset()
        production_runtime = ROOT / "var/publication_pilot1_annotation/calibration/production"
        existed = production_runtime.exists()
        with self.assertRaisesRegex(AnnotationContractError, "CALIBRATION_PRODUCTION_ACTIVATION_REQUIRED"):
            load_annotation_contracts(ROOT, mode="calibration")
        self.assertEqual(production_runtime.exists(), existed)

    def test_frozen_hashes_orders_private_screening_and_gate0(self) -> None:
        """Corrected Block A identity and unchanged authorities remain byte exact."""

        verify_protected_hashes(ROOT)
        manifest = json.loads((ROOT / "data/curation/papers/pilot1/publication_pilot1_calibration_manifest.json").read_text())
        order = json.loads((ROOT / "data/curation/papers/pilot1/publication_pilot1_pre_gate0_candidate_order.json").read_text())
        projection = {paper_id: [row["sourceUnitID"] for row in rows] for paper_id, rows in order["ordersByArtifact"].items()}
        self.assertEqual(len(manifest["calibrationSourceUnitIDs"]), 16)
        self.assertEqual(canonical_json_hash(manifest["calibrationSourceUnitIDs"]), CALIBRATION_ID_ORDER_HASH)
        self.assertEqual(sum(map(len, projection.values())), 215); self.assertEqual(canonical_json_hash(projection), CANDIDATE_ID_ORDER_HASH)
        self.assertEqual(hashlib.sha256((ROOT / PRIVATE_SCREENING_RELATIVE).read_bytes()).hexdigest(), PRIVATE_SCREENING_HASH)
        self.assertEqual(hashlib.sha256((ROOT / "data/curation/papers/pilot1/publication_pilot1_gate0_policy.yaml").read_bytes()).hexdigest(), PROTECTED_HASHES["data/curation/papers/pilot1/publication_pilot1_gate0_policy.yaml"])

    def test_forbidden_hidden_fields_rejected(self) -> None:
        """Model, gold, negative, and consolidation fields cannot enter state."""

        for field in ("gold", "model", "negativeAssertion", "sameAs"):
            payload = self.payload(); payload[field] = "forbidden"
            with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_FORBIDDEN_FIELD"):
                validate_annotation(self.contracts, self.unit_id, payload, annotation_session_id="s", annotator_id="a")

    def test_schema_and_handbook_versions(self) -> None:
        """New operational artifacts expose explicit versions and the evidence rule."""

        schema = json.loads((ROOT / "schemas/publication_pilot1_annotation_record.schema.json").read_text())
        handbook = (ROOT / "docs/publication_pilot1_annotation_calibration_handbook.md").read_text()
        self.assertEqual(schema["properties"]["annotationSchemaVersion"]["const"], "0.1.1")
        self.assertIn("**Handbook version:** 0.1.1", handbook); self.assertIn("No supported evidence span", handbook)

    def test_hardened_annotation_schema_validates_normalized_nested_records(self) -> None:
        """Draft 2020-12 schema is valid, accepts output, and closes nested records."""

        schema = json.loads((ROOT / "schemas/publication_pilot1_annotation_record.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        normalized = validate_annotation(
            self.contracts, self.unit_id, self.relation_payload(), annotation_session_id="s", annotator_id="a"
        )
        self.assertEqual(list(validator.iter_errors(normalized)), [])
        malformed = json.loads(json.dumps(normalized)); malformed["nodes"][0]["arbitraryProperty"] = True
        self.assertTrue(list(validator.iter_errors(malformed)))
        malformed = json.loads(json.dumps(normalized)); malformed["evidenceSpans"][0].pop("sourceUnitTextHash")
        self.assertTrue(list(validator.iter_errors(malformed)))
        malformed = json.loads(json.dumps(normalized)); malformed["nodes"][0].pop("mentionSpan")
        self.assertTrue(list(validator.iter_errors(malformed)))
        malformed = json.loads(json.dumps(normalized)); malformed["nodes"][0]["mentionSpan"]["arbitrary"] = True
        self.assertTrue(list(validator.iter_errors(malformed)))


if __name__ == "__main__":
    unittest.main()
