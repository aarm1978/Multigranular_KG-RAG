"""Focused deterministic checks for private, role-isolated Step 8 Mac ZIPs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
import hashlib
from pathlib import Path

from src.annotation.publication_step8 import distribution
from src.annotation.publication_step8.distribution_scoped_inputs import SCOPED_SOURCE_PATH, ScopedReviewInputs
from src.annotation.publication_step8.distribution_runtime import DistributionError, export
from src.annotation.publication_step8.service import ReviewService


class Step8DistributionTests(unittest.TestCase):
    """Build test-only packages without creating a researcher production session."""

    def setUp(self) -> None:
        """Build two temporary ZIPs from the accepted role package bindings."""

        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.zips = {reviewer: distribution.build_package(reviewer, self.root / f"{reviewer}.zip", checkpoint="a" * 40)[0]
                     for reviewer in distribution.ASSIGNMENTS}

    def tearDown(self) -> None:
        """Discard synthetic test packages and their local package state."""

        self.temporary.cleanup()

    def unpack(self, reviewer: str) -> Path:
        """Unpack one ZIP to an isolated local reviewer folder."""

        target = self.root / f"unpacked-{reviewer}"
        with zipfile.ZipFile(self.zips[reviewer]) as archive:
            archive.extractall(target)
        return next(target.iterdir())

    def command(self, package: Path, action: str) -> subprocess.CompletedProcess[str]:
        """Run one package-local runtime action with only bundled PyYAML on path."""

        environment = {**os.environ, "PYTHONPATH": str(package / "vendor") + os.pathsep + str(package)}
        return subprocess.run([sys.executable, "-m", "src.annotation.publication_step8.distribution_runtime", action,
                               "--package-root", "."], cwd=package, env=environment, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_role_bindings_source_envelope_and_deterministic_zip(self) -> None:
        """Each ZIP carries only the exact scoped source-unit reviewer envelope."""

        seen = set()
        for reviewer, assignment in distribution.ASSIGNMENTS.items():
            package = self.unpack(reviewer)
            checked = self.command(package, "verify")
            self.assertEqual(checked.returncode, 0, checked.stderr)
            manifest = json.loads((package / "PACKAGE_MANIFEST.json").read_text())
            self.assertEqual((manifest["reviewerID"], manifest["reviewRole"], manifest["reviewSessionID"]),
                             (reviewer, assignment["role"], assignment["session"]))
            self.assertEqual(manifest["inputPackageSha256"], distribution.PACKAGES[assignment["role"]][1])
            self.assertEqual(manifest["interfaceVersion"], "1.1.1")
            self.assertTrue(manifest["authorizedProductionReview"])
            self.assertFalse(manifest["privateOpaqueLineageIncluded"])
            names = set(manifest["files"])
            self.assertTrue({"START_REVIEW.command", "EXPORT_BACKUP.command", "EXPORT_FINAL.command", "README_REVIEWER.md",
                             "activation/production_activation.json", "src/annotation/publication_step8/distribution_runtime.py"} <= names)
            self.assertIn("vendor/yaml/__init__.py", names)
            self.assertFalse(any("opaque_lineage" in name or "internal" in name.lower() or name.endswith(".sqlite") for name in names))
            self.assertIn(SCOPED_SOURCE_PATH, names)
            self.assertNotIn(distribution.INVENTORY, names)
            self.assertFalse(any(name.startswith("data/raw/") and name.endswith(".md") for name in names))
            package_files = {name for name in names if name.startswith(distribution.PACKAGE_ROOT + "/")}
            self.assertEqual(package_files, {distribution.PACKAGE_ROOT + "/" + distribution.PACKAGES[assignment["role"]][0]})
            scoped = json.loads((package / SCOPED_SOURCE_PATH).read_text())
            scoped_units = {row["sourceUnitID"] for row in scoped["sourceUnits"]}
            expected = set(scoped["primarySourceUnitIDs"]) | set(scoped["authorizedContextSourceUnitIDs"])
            self.assertEqual(scoped_units, expected)
            self.assertEqual(scoped["primarySourceUnitIDs"], json.loads((package / distribution.PACKAGE_ROOT /
                                                                           distribution.PACKAGES[assignment["role"]][0]).read_text())["primarySourceUnitIDs"])
            self.assertEqual(len(scoped_units), 7)
            self.assertEqual(manifest["sourceInventorySha256"], manifest["scopedSourceArtifactSha256"])
            self.assertEqual(scoped["fullInventoryProvenance"]["sha256"], distribution.INVENTORY_HASH)
            for raw in sorted({distribution.ROOT / row["sourceFile"] for row in
                               (json.loads(line) for line in (distribution.ROOT / distribution.INVENTORY).read_text().splitlines())
                               if row["sourceUnitID"] in expected}):
                raw_bytes = raw.read_bytes()
                self.assertFalse(any(raw_bytes == archive_bytes for archive_bytes in
                                     (zipfile.ZipFile(self.zips[reviewer]).read(name) for name in names)))
            self.assertNotIn(assignment["session"], seen)
            seen.add(assignment["session"])
            rebuilt, _ = distribution.build_package(reviewer, self.root / f"again-{reviewer}.zip", checkpoint="a" * 40)
            self.assertEqual(rebuilt.read_bytes(), self.zips[reviewer].read_bytes())

    def test_final_is_closed_until_complete_and_backup_is_marked(self) -> None:
        """Package exports never require or return SQLite state files."""

        package = self.unpack("reviewer_1")
        final = self.command(package, "final")
        self.assertEqual(final.returncode, 2)
        self.assertIn("FINAL_EXPORT_REVIEW_INCOMPLETE", final.stderr)
        backup = self.command(package, "backup")
        self.assertEqual(backup.returncode, 0, backup.stderr)
        path = package / "exports" / "STEP8_NON_FINAL_BACKUP.json"
        value = json.loads(path.read_text())
        self.assertEqual(value["exportKind"], "non_final_backup")
        self.assertFalse(value["complete"])
        self.assertEqual(value["reviewExport"]["reviewSessionID"], distribution.ASSIGNMENTS["reviewer_1"]["session"])
        self.assertFalse((package / "exports" / "STEP8_FINAL_EXPORT.json").exists())

    def test_final_requires_six_formal_unit_completions_after_all_answers(self) -> None:
        """A 182/182 decision state is insufficient until every assigned unit is complete."""

        package = self.unpack("reviewer_1")
        manifest = json.loads((package / "PACKAGE_MANIFEST.json").read_text())
        inputs = ScopedReviewInputs("primary", package)
        service = ReviewService(inputs, package / "state", manifest["reviewSessionID"], manifest["reviewerID"],
                                "production", package / "activation" / "production_activation.json")
        try:
            for identifier, item in inputs.items.items():
                service.db.execute("INSERT INTO decisions VALUES (?,?,?)", (identifier, "judgment", "supported_as_proposed"))
            for unit in inputs.units[:-1]:
                service.db.execute("INSERT INTO phases VALUES (?,?)", (unit, "complete"))
            service.db.commit()
        finally:
            service.close()
        with self.assertRaisesRegex(DistributionError, "FINAL_EXPORT_REVIEW_INCOMPLETE"):
            export(package, final=True)
        service = ReviewService(ScopedReviewInputs("primary", package), package / "state", manifest["reviewSessionID"],
                                manifest["reviewerID"], "production", package / "activation" / "production_activation.json")
        try:
            service.db.execute("INSERT INTO phases VALUES (?,?)", (inputs.units[-1], "complete"))
            service.db.commit()
        finally:
            service.close()
        final = export(package, final=True)
        self.assertEqual(final.name, "STEP8_FINAL_EXPORT.json")
        value = json.loads(final.read_text())
        self.assertEqual(len(value["judgments"]), 182)
        self.assertTrue(all(value["unitCompletion"].values()))

    def test_scoped_adapter_preserves_reviewer_rendering(self) -> None:
        """The distribution-only source adapter presents the same authorized content."""

        package = self.unpack("reviewer_1")
        scoped = ScopedReviewInputs("primary", package)
        repository = distribution.ReviewInputs("primary")
        self.assertEqual(scoped.units, repository.units)
        self.assertEqual(set(scoped.items), set(repository.items))
        for unit in scoped.units:
            self.assertEqual(scoped.unit(unit), repository.unit(unit))

    def test_tampered_activation_or_runtime_fails_before_state(self) -> None:
        """Launch verification rejects altered activation and runtime package bytes."""

        package = self.unpack("reviewer_2")
        activation = package / "activation" / "production_activation.json"
        activation.write_text("{}\n")
        result = self.command(package, "verify")
        self.assertEqual(result.returncode, 2)
        self.assertIn("PACKAGE_FILE_HASH_MISMATCH", result.stderr)
        self.assertFalse((package / "state").exists())

    def test_tracked_manifest_binds_final_local_zip_bytes(self) -> None:
        """The versioned manifest records both final ZIP hashes and immutable bindings."""

        manifest_path = distribution.MANIFEST_PATH
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text())
        body = dict(manifest)
        declared = body.pop("artifactSha256")
        self.assertEqual(declared, hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                                             separators=(",", ":")).encode()).hexdigest())
        self.assertEqual(manifest["interfaceVersion"], "1.1.1")
        self.assertFalse(any(manifest["boundary"].values()))
        for reviewer, assignment in distribution.ASSIGNMENTS.items():
            bundle = manifest["reviewerBundles"][reviewer]
            self.assertEqual((bundle["reviewerID"], bundle["reviewRole"], bundle["reviewSessionID"]),
                             (reviewer, assignment["role"], assignment["session"]))
            zip_path = distribution.ROOT / bundle["zipPath"]
            self.assertTrue(zip_path.is_file())
            self.assertEqual(hashlib.sha256(zip_path.read_bytes()).hexdigest(), bundle["zipSha256"])


if __name__ == "__main__":
    unittest.main()
