"""Focused contract tests for the frozen Human Core v0.1.5 supplemental overlay."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from src.annotation.publication_pilot1.calibration import (
    HUMAN_CORE_PRIMARY_ANNOTATOR_ID,
    HUMAN_CORE_SUPPLEMENTAL_SESSION_ID,
)
from src.annotation.publication_pilot1.calibration.contracts import (
    HUMAN_CORE_SUPPLEMENTAL_PACKAGE_RELATIVE,
    AnnotationContractError,
    load_annotation_contracts,
)
from src.annotation.publication_pilot1.calibration.service import AnnotationService
from src.annotation.publication_pilot1.calibration.store import AnnotationStore
from src.annotation.publication_pilot1.calibration.validation import validate_annotation
from src.annotation.publication_pilot1.calibration import app as annotation_app


ROOT = Path(__file__).resolve().parents[1]
NODE_TARGETS = {"PUB-N-A-DOM03E-AGENTBASEDMODEL", "PUB-N-A-AG02-ORGANIZATION-PROSE"}
RELATION_TARGETS = {
    "PUB-R-C-P13-USESMODEL-PAPER-BRANCH", "PUB-R-C-P13-USESMODEL-METHOD-BRANCH",
    "PUB-R-C-P14-APPLIESTO", "PUB-R-C-P23-MENTIONSMODEL", "PUB-R-C-P26-EVALUATES",
    "PUB-R-C-P27-HASPARAMETER", "PUB-R-C-P34-HASCOMPONENT",
}


class HumanCoreSupplementalV015Tests(unittest.TestCase):
    """Protect supplemental package scope and immutable primary endpoint behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the no-write supplemental contracts once."""

        cls.contracts = load_annotation_contracts(ROOT, mode="human-core-supplemental")

    def test_package_binds_frozen_v015_authorities_and_primary_export(self) -> None:
        """Every package authority hash matches the currently frozen local authority."""

        package = json.loads((ROOT / HUMAN_CORE_SUPPLEMENTAL_PACKAGE_RELATIVE).read_text(encoding="utf-8"))
        self.assertEqual(package["session"]["annotationSessionID"], HUMAN_CORE_SUPPLEMENTAL_SESSION_ID)
        self.assertEqual(package["session"]["annotatorID"], HUMAN_CORE_PRIMARY_ANNOTATOR_ID)
        for key in ("ontologySpec", "ontologyOwl", "guide", "supplementalGuide", "sampleFreeze", "primaryBaselineRecord", "primaryBaselineExport"):
            authority = package["authorities"][key]
            self.assertEqual(hashlib.sha256((ROOT / authority["path"]).read_bytes()).hexdigest(), authority["sha256"])
        self.assertEqual(package["authorities"]["ontologySpec"]["version"], "0.1.5")
        self.assertEqual(package["authorities"]["guide"]["version"], "1.1")

    def test_exactly_five_units_have_the_same_bounded_target_set(self) -> None:
        """The overlay covers all and only the frozen N=5 units and supplemental IDs."""

        self.assertEqual(len(self.contracts.unit_order), 5)
        self.assertEqual(self.contracts.mode, "human-core-supplemental")
        for unit_id in self.contracts.unit_order:
            route = self.contracts.routes_by_id[unit_id]
            self.assertEqual(set(route["eligibleNodeOperationalTargetIDs"]), NODE_TARGETS)
            self.assertEqual(set(route["eligibleRelationOperationalTargetIDs"]), RELATION_TARGETS)
            self.assertFalse(route["structurallyUnavailableOperationalTargets"])

    def test_existing_relation_treatment_and_evaluation_policy_are_preserved(self) -> None:
        """Affected existing relations retain their prior operational treatment verbatim."""

        package = json.loads((ROOT / HUMAN_CORE_SUPPLEMENTAL_PACKAGE_RELATIVE).read_text(encoding="utf-8"))
        current = yaml.safe_load((ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml").read_text(encoding="utf-8"))
        current_by_id = {row["operational_id"]: row for row in current["relation_targets"]}
        for target in package["targets"]["relation_targets"]:
            if target["operational_id"] == "PUB-R-C-P34-HASCOMPONENT":
                continue
            prior = current_by_id[target["operational_id"]]
            self.assertEqual(target["pilot_treatment"], prior["pilot_treatment"])
            self.assertEqual(target["evaluation_mode"], prior["evaluation_mode"])

    def test_primary_endpoints_are_read_only_same_unit_relation_endpoints(self) -> None:
        """Baseline endpoint projections neither appear as node targets nor cross unit boundaries."""

        unit_id = self.contracts.unit_order[0]
        endpoints = self.contracts.baseline_endpoints(unit_id)
        self.assertTrue(endpoints)
        self.assertTrue(all(key.startswith(f"baseline:{unit_id}:") for key in endpoints))
        self.assertTrue(all(value["endpointOrigin"] == "immutable_primary_baseline" for value in endpoints.values()))
        self.assertFalse(set(endpoints) & NODE_TARGETS)
        self.assertEqual(self.contracts.baseline_endpoints("not-a-unit"), {})

    def test_baseline_endpoint_cannot_be_recreated_as_a_supplemental_node(self) -> None:
        """Validation rejects a baseline endpoint in the node link-existing path."""

        unit_id = self.contracts.unit_order[0]
        endpoint_id, endpoint = next(iter(self.contracts.baseline_endpoints(unit_id).items()))
        target_id = next(
            target_id for target_id, target in self.contracts.node_targets.items()
            if target["formal_classes"][0]["name"] == endpoint["className"]
        ) if endpoint["className"] in {"AgentBasedModel", "Organization"} else "PUB-N-A-DOM03E-AGENTBASEDMODEL"
        text = self.contracts.source_text(unit_id)
        payload = {
            "workflowState": "node_pass", "relations": [], "targetStates": [], "uncertainties": [],
            "nodes": [{
                "localID": "node-0001", "operationalTargetID": target_id, "action": "link_existing",
                "existingNodeID": endpoint_id, "mentionSpan": {"sourceUnitID": unit_id, "sourceUnitTextHash": self.contracts.units_by_id[unit_id]["textHash"], "startOffset": 0, "endOffset": 1, "exactText": text[:1]},
                "evidence": [{"sourceUnitID": unit_id, "sourceUnitTextHash": self.contracts.units_by_id[unit_id]["textHash"], "startOffset": 0, "endOffset": 1, "exactText": text[:1]}], "attributes": [],
            }],
        }
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATION_NODE_ACTION_NOT_ALLOWED|ANNOTATION_LINK_EXISTING_ENDPOINT_NOT_AUTHORIZED"):
            validate_annotation(self.contracts, unit_id, payload, annotation_session_id=HUMAN_CORE_SUPPLEMENTAL_SESSION_ID, annotator_id=HUMAN_CORE_PRIMARY_ANNOTATOR_ID)

    def test_baseline_model_or_tool_can_be_used_as_a_relation_only_endpoint(self) -> None:
        """A session-local ABM may relate to a same-unit immutable baseline endpoint."""

        unit_id = self.contracts.unit_order[0]
        endpoint_id, endpoint = next((item for item in self.contracts.baseline_endpoints(unit_id).items() if item[1]["className"] in {"Tool", "ProcessBasedModel", "ConceptualModel", "StatisticalModel", "MLModel"}))
        text = self.contracts.source_text(unit_id)
        span = {"sourceUnitID": unit_id, "sourceUnitTextHash": self.contracts.units_by_id[unit_id]["textHash"], "startOffset": 0, "endOffset": 1, "exactText": text[:1]}
        payload = {
            "workflowState": "relation_pass", "targetStates": [], "uncertainties": [],
            "nodes": [{"localID": "node-0001", "operationalTargetID": "PUB-N-A-DOM03E-AGENTBASEDMODEL", "action": "propose_new", "mentionSpan": span, "evidence": [span], "attributes": []}],
            "relations": [{"localID": "edge-0001", "operationalTargetID": "PUB-R-C-P34-HASCOMPONENT", "sourceEndpointID": "node-0001", "targetEndpointID": endpoint_id, "evidence": [span]}],
        }
        normalized = validate_annotation(self.contracts, unit_id, payload, annotation_session_id=HUMAN_CORE_SUPPLEMENTAL_SESSION_ID, annotator_id=HUMAN_CORE_PRIMARY_ANNOTATOR_ID)
        self.assertEqual(normalized["relations"][0]["target"]["referenceID"], endpoint_id)
        self.assertEqual(normalized["relations"][0]["target"]["referenceType"], "deterministic_node")

    def test_external_baseline_endpoint_preserves_inter_source_relation_scope(self) -> None:
        """A primary external Tool remains external even when its artifact ID is the paper ID."""

        unit_id = self.contracts.unit_order[0]
        endpoint_id, endpoint = next((item for item in self.contracts.baseline_endpoints(unit_id).items() if item[1]["className"] == "Tool" and item[1]["artifactScope"] == "external_artifact"))
        text = self.contracts.source_text(unit_id)
        span = {"sourceUnitID": unit_id, "sourceUnitTextHash": self.contracts.units_by_id[unit_id]["textHash"], "startOffset": 0, "endOffset": 1, "exactText": text[:1]}
        payload = {"workflowState": "relation_pass", "targetStates": [], "uncertainties": [], "nodes": [{"localID": "node-0001", "operationalTargetID": "PUB-N-A-DOM03E-AGENTBASEDMODEL", "action": "propose_new", "mentionSpan": span, "evidence": [span], "attributes": []}], "relations": [{"localID": "edge-0001", "operationalTargetID": "PUB-R-C-P34-HASCOMPONENT", "sourceEndpointID": "node-0001", "targetEndpointID": endpoint_id, "evidence": [span]}]}
        normalized = validate_annotation(self.contracts, unit_id, payload, annotation_session_id=HUMAN_CORE_SUPPLEMENTAL_SESSION_ID, annotator_id=HUMAN_CORE_PRIMARY_ANNOTATOR_ID)
        self.assertEqual(endpoint["artifactScope"], "external_artifact")
        self.assertEqual(normalized["relations"][0]["relationScope"], "inter_source")

    def test_mode_session_and_handbook_bindings_fail_closed(self) -> None:
        """Each Human Core mode accepts only its own session and authority hash."""

        base = {"activation_file": None, "host": "127.0.0.1", "port": 8766}
        for mode, session in (("human-core", HUMAN_CORE_SUPPLEMENTAL_SESSION_ID), ("human-core-supplemental", "HUMAN_CORE_N5_PRIMARY_V1")):
            with self.assertRaisesRegex(AnnotationContractError, "IDENTITY_MISMATCH"):
                annotation_app.build_service(SimpleNamespace(**base, mode=mode, annotation_session_id=session, annotator_id=HUMAN_CORE_PRIMARY_ANNOTATOR_ID))
        captured: dict[str, object] = {}

        def fake_store(*args: object, **kwargs: object) -> object:
            captured.update(kwargs); return object()

        with patch.object(annotation_app, "AnnotationStore", side_effect=fake_store):
            annotation_app.build_service(SimpleNamespace(**base, mode="human-core-supplemental", annotation_session_id=HUMAN_CORE_SUPPLEMENTAL_SESSION_ID, annotator_id=HUMAN_CORE_PRIMARY_ANNOTATOR_ID))
        bindings = captured["bindings"]
        self.assertEqual(bindings["annotationHandbookHash"], "c937a86bfe2a920dac0ad0b7c9f16cc863f2c2ece68cd65e5b3bfa7aef2ba56e")
        self.assertEqual(bindings["supplementalGuideHash"], "9f0cdfbc73ec3ce68f27fb87a3e588325fa1800e6dd65d50dc29e5ed120cbfec")

    def test_service_exposes_baseline_endpoints_without_mutating_primary_export(self) -> None:
        """UI contract exposes relation endpoints while the preserved primary bytes remain exact."""

        package = json.loads((ROOT / HUMAN_CORE_SUPPLEMENTAL_PACKAGE_RELATIVE).read_text(encoding="utf-8"))
        path = ROOT / package["authorities"]["primaryBaselineExport"]["path"]
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            store = AnnotationStore(Path(temporary) / "supplemental.sqlite3", mode="human-core-supplemental", annotation_session_id=HUMAN_CORE_SUPPLEMENTAL_SESSION_ID, annotator_id=HUMAN_CORE_PRIMARY_ANNOTATOR_ID, bindings={"fixture": "supplemental-v015"})
            try:
                unit = AnnotationService(self.contracts, store, Path(temporary) / "exports").unit(self.contracts.unit_order[0], record_open=False)
            finally:
                store.close()
        self.assertTrue(any(row.get("endpointOrigin") == "immutable_primary_baseline" for row in unit["deterministicEndpoints"]))
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
        self.assertEqual(before, package["authorities"]["primaryBaselineExport"]["sha256"])
