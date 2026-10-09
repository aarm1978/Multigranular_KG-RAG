"""Synthetic GitHub evidence and scoped source-failure checks."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.coderepos.source_units import read_repository_sources
from src.extraction.llm.coderepos.evidence_binding import bind_repository_evidence


class RepositoryEvidenceTests(unittest.TestCase):
    """Bind all supported authority channels without corpus/provider calls."""

    def setUp(self):
        """Build synthetic README, downloaded prose and Markdown cells."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        contents = self.root / "Demo" / "contents"
        contents.mkdir(parents=True)
        text = "# Guide\r\n\r\nCafé 🌊 describes streamflow flow flow.\r\n"
        (contents / "guide.md").write_bytes(text.encode())
        (contents / "notebook.ipynb").write_text(json.dumps({"cells": [
            {"cell_type": "code", "source": "NEVER EXECUTE"}, {"cell_type": "markdown", "source": text}]}))
        self.repo = {"repo_id": 1, "name": "Demo", "full_name": "Example/Demo",
            "archive": {"frozen_commit_sha": "a" * 40}, "readme": {"source_path": "README.md", "text": text},
            "files": {"downloaded": [{"path": p, "extension": Path(p).suffix, "downloaded": True,
                "selection_reason": "allowed_semantic_folder", "file_role": "other"} for p in ("guide.md", "notebook.ipynb")]}}
        self.reader = read_repository_sources(self.repo, self.root)
        self.owner = {k: self.reader["sourceUnits"][0][k] for k in ("canonicalArtifactID", "repo_id", "full_name", "frozenCommitSha")}

    def bind(self, unit=None, quotes=None, reader=None):
        """Bind one supplied trusted source unit."""
        unit = unit or self.reader["sourceUnits"][0]
        return bind_repository_evidence(self.reader if reader is None else reader, unit["sourceUnitID"],
            [{"evidenceText": "Café 🌊"}] if quotes is None else quotes, accepted_repository=self.owner)

    def test_channels_coordinates_and_literal_locators(self):
        """Retain README/raw-file/cell authority distinctions and Unicode offsets."""
        self.assertEqual(len(self.reader["sourceUnits"]), 3)
        for unit in self.reader["sourceUnits"]:
            bound = self.bind(unit)
            span = bound["evidenceSpans"][0]
            authority = next(a for a in self.reader["authorities"] if a["path"] == unit["path"])
            self.assertEqual(span["startOffsetInAuthority"], authority["text"].index("Café"))
            self.assertEqual(span["startLine"], 3)
            self.assertEqual(span["evidenceHash"], hashlib.sha256("Café 🌊".encode()).hexdigest())
            self.assertEqual(span["authorityTextSha256"], authority["authorityTextSha256"])
            self.assertEqual(span["cellIndex"], unit["cellIndex"])
            for quote in ("flow", "fake"):
                self.assertEqual(self.bind(unit, [{"evidenceText": quote}])["status"], "failed_source_or_evidence_binding")
            self.assertEqual(self.bind(unit, [{"evidenceText": "flow", "locatorAnchor": "flow."}])["status"], "evidence_bound")

    def test_integrity_eligibility_and_metadata_rejection(self):
        """Fail closed on provenance tampering and model metadata."""
        for field, value in (("text", "fake"), ("startLine", 99), ("frozenCommitSha", "0" * 40)):
            reader = deepcopy(self.reader)
            reader["sourceUnits"][0][field] = value
            self.assertEqual(self.bind(reader=reader)["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.bind(quotes=[{"evidenceText": "Café", "startLine": 3}])["status"], "failed_source_or_evidence_binding")
        reader = deepcopy(self.reader)
        reader["sourceUnits"][0]["eligibility"] = "uncertain"
        self.assertEqual(self.bind(reader=reader)["status"], "needs_review")

    def test_scoped_review_and_failure_isolation(self):
        """Unrelated paths, cells and spans cannot poison independently valid units."""
        reader = deepcopy(self.reader)
        reader["diagnostics"] = [{"status": "failed_source_or_evidence_binding", "path": "missing.md", "reason": "missing"},
            {"status": "needs_review", "path": "README.md", "startLine": 1, "endLine": 1, "reason": "heading"}]
        self.assertEqual(self.bind(reader=reader)["status"], "evidence_bound")
        reader["diagnostics"].append({"status": "needs_review", "path": "README.md", "startLine": 3, "endLine": 3})
        self.assertEqual(self.bind(reader=reader)["status"], "needs_review")
        reader["diagnostics"] = [{"status": "failed_source_or_evidence_binding", "path": "notebook.ipynb", "cellIndex": 0}]
        self.assertEqual(self.bind(self.reader["sourceUnits"][2], reader=reader)["status"], "evidence_bound")
        reader["diagnostics"] = [{"status": "failed_source_or_evidence_binding", "reason": "unknown scope"}]
        self.assertEqual(self.bind(reader=reader)["status"], "failed_source_or_evidence_binding")

    def test_immutability_and_zero_external_effects(self):
        """Binding performs no file reads, writes or provider calls."""
        before = deepcopy((self.reader, self.owner))
        with patch("builtins.open", side_effect=AssertionError("No IO")), patch("io.open", side_effect=AssertionError("No IO")), patch("socket.socket", side_effect=AssertionError("No network")):
            result = self.bind()
            self.assertEqual(result, self.bind())
        self.assertEqual(before, (self.reader, self.owner))
        self.assertFalse(result["kgAuthorization"])
        self.assertNotIn("nodes", result)
