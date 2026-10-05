"""Focused checks for the self-contained bounded reconciliation ZIP."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.annotation.publication_step8 import reconciliation_distribution as distribution


class Step8ReconciliationDistributionTests(unittest.TestCase):
    """Verify the Mac package contains only reconciliation-authorized inputs/runtime."""

    def test_zip_verifies_and_excludes_initial_review_exports(self) -> None:
        """The local launcher reads only its frozen 11-item package and blank state."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, manifest = distribution.build(root / "joint.zip", "a" * 40)
            with zipfile.ZipFile(archive) as value:
                names = value.namelist()
                self.assertTrue(any(name.endswith("runtime/reconciliation_app.py") for name in names))
                self.assertTrue(any(name.endswith(distribution.PACKAGE.name) for name in names))
                self.assertFalse(any("initial_review_reviewer" in name or "opaque_lineage" in name for name in names))
                value.extractall(root / "unpacked")
            package = next((root / "unpacked").iterdir())
            command = [sys.executable, "runtime/reconciliation_app.py", "verify", "--package",
                       "data/curation/papers/m2/publication_step8_reconciliation/publication_step8_reconciliation_package_v1.0.0.json",
                       "--state", "state/reconciliation-state.json"]
            result = subprocess.run(command, cwd=package, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(manifest["reconciliationPackageSha256"], result.stdout)


if __name__ == "__main__":
    unittest.main()
