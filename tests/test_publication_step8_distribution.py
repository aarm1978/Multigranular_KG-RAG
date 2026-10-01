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

    def test_role_bindings_contents_and_deterministic_zip(self) -> None:
        """Each ZIP contains only its role package, activation, sources, and launchers."""

        seen = set()
        for reviewer, assignment in distribution.ASSIGNMENTS.items():
            package = self.unpack(reviewer)
            checked = self.command(package, "verify")
            self.assertEqual(checked.returncode, 0, checked.stderr)
            manifest = json.loads((package / "PACKAGE_MANIFEST.json").read_text())
            self.assertEqual((manifest["reviewerID"], manifest["reviewRole"], manifest["reviewSessionID"]),
                             (reviewer, assignment["role"], assignment["session"]))
            self.assertEqual(manifest["inputPackageSha256"], distribution.PACKAGES[assignment["role"]][1])
            self.assertEqual(manifest["interfaceVersion"], "1.1.0")
            self.assertEqual(manifest["sourceInventorySha256"], distribution.INVENTORY_HASH)
            self.assertTrue(manifest["authorizedProductionReview"])
            self.assertFalse(manifest["privateOpaqueLineageIncluded"])
            names = set(manifest["files"])
            self.assertTrue({"START_REVIEW.command", "EXPORT_BACKUP.command", "EXPORT_FINAL.command", "README_REVIEWER.md",
                             "activation/production_activation.json", "src/annotation/publication_step8/distribution_runtime.py"} <= names)
            self.assertIn("vendor/yaml/__init__.py", names)
            self.assertFalse(any("opaque_lineage" in name or "internal" in name.lower() or name.endswith(".sqlite") for name in names))
            package_files = {name for name in names if name.startswith(distribution.PACKAGE_ROOT + "/")}
            self.assertEqual(package_files, {distribution.PACKAGE_ROOT + "/" + distribution.PACKAGES[assignment["role"]][0]})
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
        self.assertEqual(manifest["interfaceVersion"], "1.1.0")
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
