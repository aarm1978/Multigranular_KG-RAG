"""Synthetic packaging, immutable export, validation, and consolidation tests."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src.annotation.publication_pilot1.calibration.contracts import (
    ANNOTATION_MVP_BASE_CHECKPOINT,
    AnnotationContractError,
    load_annotation_contracts,
    production_activation_payload,
    verify_production_activation,
)
from src.annotation.publication_pilot1.calibration.distribution import (
    BUNDLE_FILES,
    _git_build_checkpoint,
    _launcher_text,
    _package_source_paths,
    build_distribution_package,
    build_export_bundle,
    import_validated_bundles,
    synthetic_activation_payload,
    validate_export_bundle,
    verify_package,
    write_activation,
)
from src.annotation.publication_pilot1.calibration.service import AnnotationService
from src.annotation.publication_pilot1.calibration.store import AnnotationStore


ROOT = Path(__file__).resolve().parents[1]


class DeterministicClock:
    """Return deterministic, strictly increasing UTC timestamps."""

    def __init__(self) -> None:
        """Start immediately before the discarded fixture epoch."""

        self.value = datetime(2026, 8, 20, tzinfo=timezone.utc) - timedelta(minutes=1)

    def __call__(self) -> str:
        """Advance one minute and return canonical UTC text."""

        self.value += timedelta(minutes=1)
        return self.value.isoformat(timespec="microseconds").replace("+00:00", "Z")


class CalibrationDistributionTests(unittest.TestCase):
    """Exercise two independent discarded sessions through a derived master index."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load only the accepted discarded synthetic contract set."""

        cls.contracts = load_annotation_contracts(ROOT)

    def setUp(self) -> None:
        """Create private discarded runtime paths."""

        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.runtime = Path(self.temporary.name)

    def complete_payload(self, source_unit_id: str) -> dict[str, object]:
        """Return an exhaustively reviewed zero-positive discarded annotation."""

        route = self.contracts.routes_by_id[source_unit_id]
        target_ids = route["eligibleNodeOperationalTargetIDs"] + route["eligibleRelationOperationalTargetIDs"]
        states = []
        for target_id in target_ids:
            target = self.contracts.node_targets.get(target_id) or self.contracts.relation_targets[target_id]
            treatment = target["pilot_treatment"]
            state = {
                "extract_and_evaluate": "reviewed_no_positive",
                "extract_and_monitor": "monitored_review_complete",
                "deferred_resolution": "deferred_task_review_complete",
            }[treatment]
            states.append({"operationalTargetID": target_id, "state": state})
        return {
            "workflowState": "review", "nodes": [], "relations": [],
            "targetStates": states, "uncertainties": [],
        }

    def completed_service(self, annotator_id: str, session_id: str) -> AnnotationService:
        """Create and complete one discarded independent annotation store."""

        store = AnnotationStore(
            self.runtime / f"{session_id}.sqlite3", mode="synthetic",
            annotation_session_id=session_id, annotator_id=annotator_id,
            bindings={"fixture": "distribution-round-trip-v1"}, clock=DeterministicClock(),
        )
        self.addCleanup(store.close)
        service = AnnotationService(self.contracts, store, self.runtime / "legacy-exports")
        for index, source_unit_id in enumerate(self.contracts.unit_order):
            service.unit(source_unit_id)
            if index == 0:
                context_id = self.contracts.context_candidate_ids(source_unit_id, same_section=True)[0]
                service.expose_context(
                    source_unit_id, context_id, context_selection_reason="same_section_context",
                )
            for event_type in ("reading_complete", "pause_started", "pause_ended", "node_pass_started"):
                service.timing(source_unit_id, event_type)
            service.timing(source_unit_id, "technical_interruption_started")
            service.timing(source_unit_id, "technical_interruption_ended")
            for event_type in (
                "node_pass_completed", "relation_pass_started", "relation_pass_completed", "review_started",
            ):
                service.timing(source_unit_id, event_type)
            service.submit(source_unit_id, self.complete_payload(source_unit_id))
        return service

    def rewrite_bundle(self, source: Path, destination: Path, mutate) -> None:
        """Rewrite a discarded bundle after applying one deliberate corruption."""

        with zipfile.ZipFile(source) as archive:
            files = {name: archive.read(name) for name in BUNDLE_FILES}
        mutate(files)
        with zipfile.ZipFile(destination, "w") as archive:
            for name in BUNDLE_FILES:
                archive.writestr(name, files[name])

    def rewrite_bundle_with_valid_checksums(self, source: Path, destination: Path, mutate) -> None:
        """Rewrite discarded bundle content and consistently refresh its checksum manifest."""

        with zipfile.ZipFile(source) as archive:
            files = {name: archive.read(name) for name in BUNDLE_FILES}
        mutate(files)
        checksums = {
            name: hashlib.sha256(data).hexdigest()
            for name, data in files.items() if name != "checksums.json"
        }
        files["checksums.json"] = (
            json.dumps({"algorithm": "SHA-256", "files": checksums}, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        with zipfile.ZipFile(destination, "w") as archive:
            for name in BUNDLE_FILES:
                archive.writestr(name, files[name])

    def test_researcher_activation_is_identity_bound_and_creates_no_state(self) -> None:
        """Activation generation writes only its explicit file and rejects masquerading."""

        output = self.runtime / "activation.json"
        build_checkpoint = "f" * 40
        write_activation(
            ROOT, "SYNTHETIC_REVIEW_A", "SYNTHETIC_SESSION_A", output,
            package_build_checkpoint=build_checkpoint,
        )
        self.assertEqual(sorted(path.name for path in self.runtime.iterdir()), ["activation.json"])
        payload = verify_production_activation(
            output, ROOT, annotator_id="SYNTHETIC_REVIEW_A", annotation_session_id="SYNTHETIC_SESSION_A",
        )
        self.assertEqual(payload, production_activation_payload(
            ROOT, "SYNTHETIC_REVIEW_A", "SYNTHETIC_SESSION_A",
            package_build_checkpoint=build_checkpoint,
        ))
        with self.assertRaisesRegex(AnnotationContractError, "ACTIVATION_BINDING_MISMATCH"):
            verify_production_activation(
                output, ROOT, annotator_id="SYNTHETIC_REVIEW_B", annotation_session_id="SYNTHETIC_SESSION_A",
            )

    def test_git_build_checkpoint_accepts_clean_descendant_and_rejects_dirty_or_unrelated(self) -> None:
        """Real Git validation models a clean distribution commit after the accepted base."""

        repository = self.runtime / "git-provenance"
        repository.mkdir()

        def git(*arguments: str) -> str:
            """Run one local Git command in the discarded provenance repository."""

            result = subprocess.run(
                ["git", *arguments], cwd=repository, check=True, capture_output=True, text=True,
            )
            return result.stdout.strip()

        git("init", "-q"); git("config", "user.email", "discarded@example.invalid")
        git("config", "user.name", "Discarded Test")
        tracked = repository / "tracked.txt"; tracked.write_text("base\n", encoding="utf-8")
        git("add", "tracked.txt"); git("commit", "-q", "-m", "base")
        base_checkpoint = git("rev-parse", "HEAD")
        tracked.write_text("base\nlater\n", encoding="utf-8")
        git("add", "tracked.txt"); git("commit", "-q", "-m", "later distribution implementation")
        later_checkpoint = git("rev-parse", "HEAD")
        self.assertNotEqual(base_checkpoint, later_checkpoint)
        self.assertEqual(
            _git_build_checkpoint(repository, annotation_mvp_base_checkpoint=base_checkpoint),
            later_checkpoint,
        )
        (repository / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(AnnotationContractError, "WORKTREE_DIRTY"):
            _git_build_checkpoint(repository, annotation_mvp_base_checkpoint=base_checkpoint)
        (repository / "untracked.txt").unlink()
        tracked.write_text("tracked dirty change\n", encoding="utf-8")
        with self.assertRaisesRegex(AnnotationContractError, "WORKTREE_DIRTY"):
            _git_build_checkpoint(repository, annotation_mvp_base_checkpoint=base_checkpoint)
        git("restore", "tracked.txt")
        unrelated_checkpoint = git("commit-tree", git("write-tree"), "-m", "unrelated history")
        with self.assertRaisesRegex(AnnotationContractError, "BASE_CHECKPOINT_NOT_ANCESTOR"):
            _git_build_checkpoint(repository, annotation_mvp_base_checkpoint=unrelated_checkpoint)

    def test_partial_bundle_is_valid_backup_but_not_gate0_ready(self) -> None:
        """An incomplete immutable backup is explicitly barred from ready import."""

        store = AnnotationStore(
            self.runtime / "partial.sqlite3", mode="synthetic", annotation_session_id="partial-session",
            annotator_id="partial-annotator", bindings={"fixture": "discarded"}, clock=DeterministicClock(),
        )
        self.addCleanup(store.close)
        service = AnnotationService(self.contracts, store, self.runtime / "exports")
        activation = synthetic_activation_payload(self.contracts, "partial-annotator", "partial-session")
        bundle = build_export_bundle(service, activation, self.runtime / "partial.zip", gate0_ready=False)
        validated = validate_export_bundle(bundle, self.contracts, require_gate0_ready=False)
        self.assertEqual(validated["manifest"]["status"], "partial")
        with self.assertRaisesRegex(AnnotationContractError, "BUNDLE_NOT_GATE0_READY"):
            validate_export_bundle(bundle, self.contracts, require_gate0_ready=True)

    def test_checksum_corruption_is_rejected(self) -> None:
        """An immutable file modification is detected before semantic import."""

        service = self.completed_service("discarded-a", "discarded-session-a")
        activation = synthetic_activation_payload(self.contracts, "discarded-a", "discarded-session-a")
        bundle = build_export_bundle(service, activation, self.runtime / "valid.zip", gate0_ready=True)

        def corrupt(files: dict[str, bytes]) -> None:
            files["annotations.jsonl"] += b"\n"

        corrupt_bundle = self.runtime / "corrupt.zip"
        self.rewrite_bundle(bundle, corrupt_bundle, corrupt)
        with self.assertRaisesRegex(AnnotationContractError, "CHECKSUM_MISMATCH:annotations.jsonl"):
            validate_export_bundle(corrupt_bundle, self.contracts, require_gate0_ready=True)

    def test_export_and_validator_bind_package_build_checkpoint(self) -> None:
        """The immutable export carries build provenance and rejects a checksum-valid mismatch."""

        service = self.completed_service("discarded-a", "discarded-session-a")
        activation = synthetic_activation_payload(self.contracts, "discarded-a", "discarded-session-a")
        bundle = build_export_bundle(service, activation, self.runtime / "provenance.zip", gate0_ready=True)
        validated = validate_export_bundle(bundle, self.contracts, require_gate0_ready=True)
        self.assertEqual(validated["manifest"]["annotationMVPBaseCheckpoint"], ANNOTATION_MVP_BASE_CHECKPOINT)
        self.assertEqual(
            validated["manifest"]["packageBuildCheckpoint"],
            validated["activation"]["packageBuildCheckpoint"],
        )

        def alter_manifest(files: dict[str, bytes]) -> None:
            """Change only package provenance while leaving activation untouched."""

            manifest = json.loads(files["manifest.json"])
            manifest["packageBuildCheckpoint"] = "c" * 40
            files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")

        altered = self.runtime / "provenance-altered.zip"
        self.rewrite_bundle_with_valid_checksums(bundle, altered, alter_manifest)
        with self.assertRaisesRegex(AnnotationContractError, "MANIFEST_BINDING_MISMATCH:packageBuildCheckpoint"):
            validate_export_bundle(altered, self.contracts, require_gate0_ready=True)

    def test_immutable_export_path_rejects_different_bundle(self) -> None:
        """A different session cannot silently replace an existing immutable ZIP."""

        first = self.completed_service("discarded-a", "discarded-session-a")
        second = self.completed_service("discarded-b", "discarded-session-b")
        output = self.runtime / "immutable.zip"
        build_export_bundle(
            first, synthetic_activation_payload(self.contracts, "discarded-a", "discarded-session-a"),
            output, gate0_ready=True,
        )
        original = output.read_bytes()
        with self.assertRaisesRegex(AnnotationContractError, "OUTPUT_EXISTS_CONFLICT"):
            build_export_bundle(
                second, synthetic_activation_payload(self.contracts, "discarded-b", "discarded-session-b"),
                output, gate0_ready=True,
            )
        self.assertEqual(output.read_bytes(), original)

    def test_two_annotator_deterministic_round_trip_and_master_provenance(self) -> None:
        """Independent discarded A/B bundles validate and derive a non-overwriting master."""

        service_a = self.completed_service("discarded-a", "discarded-session-a")
        service_b = self.completed_service("discarded-b", "discarded-session-b")
        activation_a = synthetic_activation_payload(self.contracts, "discarded-a", "discarded-session-a")
        activation_b = synthetic_activation_payload(self.contracts, "discarded-b", "discarded-session-b")
        bundle_a = build_export_bundle(service_a, activation_a, self.runtime / "a.zip", gate0_ready=True)
        original_a = bundle_a.read_bytes()
        duplicate_a = build_export_bundle(service_a, activation_a, self.runtime / "a-again.zip", gate0_ready=True)
        bundle_b = build_export_bundle(service_b, activation_b, self.runtime / "b.zip", gate0_ready=True)
        self.assertEqual(bundle_a.read_bytes(), duplicate_a.read_bytes())
        validated_a = validate_export_bundle(bundle_a, self.contracts, require_gate0_ready=True)
        validated_b = validate_export_bundle(bundle_b, self.contracts, require_gate0_ready=True)
        self.assertEqual(validated_a["manifest"]["calibrationSourceUnitIDs"], list(self.contracts.unit_order))
        self.assertEqual(validated_b["manifest"]["calibrationSourceUnitIDs"], list(self.contracts.unit_order))
        self.assertNotEqual(validated_a["activation"]["annotatorID"], validated_b["activation"]["annotatorID"])
        master = import_validated_bundles([bundle_a, bundle_b], self.contracts, self.runtime / "master.sqlite3")
        self.assertEqual(bundle_a.read_bytes(), original_a)
        connection = sqlite3.connect(master)
        try:
            bundles = connection.execute(
                "SELECT bundle_sha256,annotator_id,annotation_session_id,activation_json,revision_audit_json FROM bundles ORDER BY annotator_id"
            ).fetchall()
            self.assertEqual(len(bundles), 2)
            self.assertEqual({row[1] for row in bundles}, {"discarded-a", "discarded-b"})
            self.assertEqual({row[2] for row in bundles}, {"discarded-session-a", "discarded-session-b"})
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM annotations").fetchone()[0], 4)
            self.assertEqual(connection.execute("SELECT COUNT(DISTINCT bundle_sha256) FROM annotations").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM context_exposures").fetchone()[0], 2)
            self.assertGreater(connection.execute("SELECT COUNT(*) FROM timing_events").fetchone()[0], 32)
            self.assertTrue(all(json.loads(row[3])["annotatorID"] == row[1] for row in bundles))
            self.assertTrue(all(json.loads(row[3])["packageBuildCheckpoint"] == "0" * 40 for row in bundles))
            self.assertTrue(all(json.loads(row[4])["submissions"] for row in bundles))
        finally:
            connection.close()

    def test_import_rejects_same_annotator_as_two_independent_bundles(self) -> None:
        """Two session files cannot turn one annotator identity into independence."""

        first = self.completed_service("discarded-same", "discarded-session-1")
        second = self.completed_service("discarded-same", "discarded-session-2")
        bundle_1 = build_export_bundle(
            first, synthetic_activation_payload(self.contracts, "discarded-same", "discarded-session-1"),
            self.runtime / "same-1.zip", gate0_ready=True,
        )
        bundle_2 = build_export_bundle(
            second, synthetic_activation_payload(self.contracts, "discarded-same", "discarded-session-2"),
            self.runtime / "same-2.zip", gate0_ready=True,
        )
        with self.assertRaisesRegex(AnnotationContractError, "ANNOTATOR_IDS_NOT_DISTINCT"):
            import_validated_bundles([bundle_1, bundle_2], self.contracts, self.runtime / "rejected.sqlite3")

    def test_mac_launcher_is_local_and_fail_closed(self) -> None:
        """The lightweight launcher checks dependencies and exact package activation locally."""

        launcher = _launcher_text("discarded-a", "discarded-session-a")
        self.assertIn("127.0.0.1", launcher)
        self.assertIn("verify-package", launcher)
        self.assertIn("calibration_activation.json", launcher)
        self.assertIn("Python 3.10+", launcher)
        self.assertNotIn("pip install", launcher)
        self.assertNotIn("conda install", launcher)

    def test_real_package_source_paths_exist_in_namespace_package_layout(self) -> None:
        """Every declared package input exists without requiring a src package marker."""

        paths = _package_source_paths(ROOT)
        missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
        self.assertEqual(missing, [])
        self.assertNotIn(ROOT / "src/__init__.py", paths)
        self.assertIn(ROOT / "src/annotation/__init__.py", paths)
        self.assertIn(ROOT / "src/annotation/publication_pilot1/__init__.py", paths)
        self.assertIn(ROOT / "src/annotation/publication_pilot1/calibration", paths)

    def test_package_builder_is_deterministic_with_discarded_inputs(self) -> None:
        """Package assembly and executable modes work without touching real calibration text."""

        fixture_root = self.runtime / "discarded-repository"
        runtime_file = fixture_root / "discarded/runtime.txt"
        guide = fixture_root / "docs/publication_pilot1_calibration_annotator_distribution.md"
        runtime_file.parent.mkdir(parents=True); guide.parent.mkdir(parents=True)
        runtime_file.write_text("discarded runtime\n", encoding="utf-8")
        guide.write_text("discarded guide\n", encoding="utf-8")

        def discarded_activation(
            root: Path, annotator: str, session: str, output: Path, *, package_build_checkpoint: str,
        ) -> Path:
            """Write a discarded activation placeholder inside a synthetic package."""

            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps({
                "annotatorID": annotator, "annotationSessionID": session,
                "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
                "packageBuildCheckpoint": package_build_checkpoint, "gate0PolicyHash": "f" * 64,
            }), encoding="utf-8")
            return output

        patches = (
            patch("src.annotation.publication_pilot1.calibration.distribution._git_build_checkpoint", return_value="b" * 40),
            patch("src.annotation.publication_pilot1.calibration.distribution._package_source_paths", return_value=[runtime_file.resolve()]),
            patch("src.annotation.publication_pilot1.calibration.distribution.write_activation", side_effect=discarded_activation),
            patch(
                "src.annotation.publication_pilot1.calibration.distribution.production_activation_payload",
                return_value={"gate0PolicyHash": "f" * 64},
            ),
        )
        with patches[0], patches[1], patches[2], patches[3]:
            first = build_distribution_package(
                fixture_root, "discarded-a", "discarded-session-a", self.runtime / "package-a.zip",
            )
            second = build_distribution_package(
                fixture_root, "discarded-a", "discarded-session-a", self.runtime / "package-a-copy.zip",
            )
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            names = archive.namelist()
            self.assertTrue(any(name.endswith("launch_annotation.command") for name in names))
            self.assertTrue(any(name.endswith("README_ANNOTATOR.md") for name in names))
            self.assertFalse(any(name.endswith(".sqlite3") for name in names))
            launcher = next(info for info in archive.infolist() if info.filename.endswith("launch_annotation.command"))
            self.assertTrue((launcher.external_attr >> 16) & 0o100)
            manifest = json.loads(archive.read(next(name for name in names if name.endswith("package_manifest.json"))))
            activation = json.loads(archive.read(next(name for name in names if name.endswith("calibration_activation.json"))))
            self.assertEqual(manifest["annotationMVPBaseCheckpoint"], ANNOTATION_MVP_BASE_CHECKPOINT)
            self.assertEqual(manifest["packageBuildCheckpoint"], "b" * 40)
            self.assertEqual(activation["packageBuildCheckpoint"], manifest["packageBuildCheckpoint"])

    def test_extracted_package_verification_needs_no_git_and_rejects_checkpoint_tampering(self) -> None:
        """Manifest hashes bind activation provenance without an extracted Git repository."""

        package = self.runtime / "extracted-package"
        activation_path = package / "activation/calibration_activation.json"
        activation_path.parent.mkdir(parents=True)
        checkpoint = "b" * 40

        def expected_activation(
            root: Path, annotator: str, session: str, *, package_build_checkpoint: str,
        ) -> dict[str, str]:
            """Return a minimal discarded activation contract for package-verifier isolation."""

            return {
                "annotatorID": annotator, "annotationSessionID": session,
                "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
                "packageBuildCheckpoint": package_build_checkpoint, "gate0PolicyHash": "f" * 64,
            }

        activation_path.write_text(json.dumps(
            expected_activation(package, "discarded-a", "discarded-session-a", package_build_checkpoint=checkpoint)
        ), encoding="utf-8")
        manifest = {
            "packageSchemaVersion": "0.1.0", "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
            "packageBuildCheckpoint": checkpoint, "annotatorID": "discarded-a",
            "annotationSessionID": "discarded-session-a",
            "interfaceVersion": "publication-pilot1-annotation-calibration/0.1.0",
            "annotationSchemaVersion": "0.1.0", "routingVersion": "0.1.2",
            "calibrationIdentityOrderHash": "182710041594edb979dcfd8e39041cf98523e383c9f3498ac1d74293d0378b98",
            "gate0PolicyHash": "f" * 64,
            "files": {"activation/calibration_activation.json": hashlib.sha256(activation_path.read_bytes()).hexdigest()},
        }
        manifest_path = package / "package_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertFalse((package / ".git").exists())
        with patch(
            "src.annotation.publication_pilot1.calibration.contracts.production_activation_payload",
            side_effect=expected_activation,
        ):
            self.assertEqual(verify_package(package)["packageBuildCheckpoint"], checkpoint)
            manifest["packageBuildCheckpoint"] = "c" * 40
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(AnnotationContractError, "ACTIVATION_BINDING_MISMATCH"):
                verify_package(package)
            manifest["packageBuildCheckpoint"] = checkpoint
            altered = expected_activation(
                package, "discarded-a", "discarded-session-a", package_build_checkpoint="c" * 40,
            )
            activation_path.write_text(json.dumps(altered), encoding="utf-8")
            manifest["files"]["activation/calibration_activation.json"] = hashlib.sha256(activation_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(AnnotationContractError, "ACTIVATION_BINDING_MISMATCH"):
                verify_package(package)

    def test_bundle_manifest_is_closed_to_expected_file_set(self) -> None:
        """The exchange format contains JSON records and never the SQLite working database."""

        service = self.completed_service("discarded-a", "discarded-session-a")
        bundle = build_export_bundle(
            service, synthetic_activation_payload(self.contracts, "discarded-a", "discarded-session-a"),
            self.runtime / "bundle.zip", gate0_ready=True,
        )
        with zipfile.ZipFile(bundle) as archive:
            self.assertEqual(set(archive.namelist()), set(BUNDLE_FILES))
            self.assertFalse(any(name.endswith(".sqlite3") for name in archive.namelist()))
            manifest = json.loads(archive.read("manifest.json"))
        self.assertEqual(manifest["status"], "synthetic_complete")


if __name__ == "__main__":
    unittest.main()
