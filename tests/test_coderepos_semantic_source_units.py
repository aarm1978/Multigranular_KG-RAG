"""Four bounded synthetic GitHub reader checks; no real corpus or providers."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.coderepos.source_units import read_repository_sources


class CodeRepositorySourceUnitTests(unittest.TestCase):
    """Check eligibility, authority precedence, Markdown cells and failures."""

    def setUp(self) -> None:
        """Create a fresh synthetic raw tree and Phase A repository record."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.contents = self.root / "Demo" / "contents"
        self.contents.mkdir(parents=True)
        self.repo = {"repo_id": 17, "name": "Demo", "full_name": "Example/Demo",
                     "archive": {"frozen_commit_sha": "a" * 40},
                     "readme": {"present": False, "text": None, "source_path": None},
                     "files": {"downloaded": []}}

    def add(self, path: str, text: str | bytes | None, **overrides: object) -> None:
        """Declare one selected source and optionally materialize synthetic bytes."""
        entry = {"path": path, "extension": Path(path).suffix, "file_role": "other",
                 "selection_reason": "allowed_semantic_folder", "downloaded": True}
        entry.update(overrides)
        self.repo["files"]["downloaded"].append(entry)
        if text is not None:
            target = self.contents / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)

    def test_eligibility_and_descriptive_other(self) -> None:
        """Admit selected prose formats without using role as the selector."""
        prose = "This workflow processes river discharge observations.\n"
        eligible = ["workshops/Flow.MD", "nested/tutorial/flow.markdown", "docs/flow.rst",
                    "docs/flow.txt", "CITATION.txt", "README", "CITATION"]
        for path in eligible:
            self.add(path, prose)
        self.add("examples/run.py", "The code must not enter semantic units.", file_role="example")
        self.add("LICENSE.md", prose, file_role="documentation")
        self.add("requirements.txt", "numpy scipy pandas", file_role="documentation")
        self.add("docs/admin.md", "Please submit pull requests for review.")
        self.add("docs/mixed.md", "# Workflow\n\n" + prose + "\n```python\nprint('hidden code')\n```\n\n![badge](https://example.test/badge)\n")
        self.add("docs/unknown.md", None, selection_reason="new_reason")
        self.add("docs/not-downloaded.md", None, downloaded=False)
        before = deepcopy(self.repo)
        result = read_repository_sources(self.repo, self.root)
        paths = {row["path"] for row in result["sourceUnits"]}
        self.assertEqual(paths, set(eligible + ["docs/mixed.md"]))
        self.assertTrue(all(row["contentKind"] == "prose" for row in result["sourceUnits"]))
        self.assertNotIn("print(", "".join(row["text"] for row in result["sourceUnits"]))
        self.assertTrue(any(row["reason"] == "unrecognized_selection_reason" for row in result["diagnostics"]))
        self.assertFalse(any(row["status"] == "failed_source_or_evidence_binding" for row in result["reads"]))
        self.assertEqual(self.repo, before)

    def test_readme_precedence_and_additional_readmes(self) -> None:
        """Use Phase A verbatim even when its raw duplicate is absent/different."""
        text = "# Readme\r\n\r\nThis repository models river flows.\r\n"
        self.repo["readme"] = {"present": True, "source_path": "README.md", "text": text}
        self.add("README.md", None, file_role="readme")
        self.add("docs/README.md", "This additional guide explains streamflow processing.\n", file_role="readme")
        self.repo["files"]["downloaded"].append(dict(self.repo["files"]["downloaded"][-1]))
        result = read_repository_sources(self.repo, self.root)
        self.assertEqual(len(result["authorities"]), 2)
        phase = result["authorities"][0]
        self.assertEqual(phase["text"], text)
        self.assertEqual(phase["authorityTextSha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertNotIn("rawFileSha256", phase)
        self.assertEqual(len(result["sourceUnits"]), 2)
        (self.contents / "README.md").write_text("Different raw text must never win.")
        self.assertEqual(read_repository_sources(self.repo, self.root), result)
        self.assertTrue(result["inputComplete"])
        self.repo["readme"]["text"] = 42
        bad = read_repository_sources(self.repo, self.root)
        self.assertTrue(any(row["reason"] == "phase_a_readme_malformed" for row in bad["diagnostics"]))
        self.assertNotIn("README.md", {row["path"] for row in bad["authorities"]})

    def test_notebook_markdown_fidelity_and_cell_identity(self) -> None:
        """Retain original cell indices, text and hashes; ignore code/outputs."""
        fragments = ["# Flow\r\n", "\r\n", "Measured café 🌊 discharge is documented here.\r\n"]
        notebook = {"cells": [
            {"cell_type": "code", "source": "raise RuntimeError('DO NOT EXECUTE')", "outputs": ["HIDDEN"]},
            {"cell_type": "markdown", "source": fragments},
            {"cell_type": "raw", "source": "RAW HIDDEN"},
            {"cell_type": "markdown", "source": "".join(fragments)},
        ]}
        raw = json.dumps(notebook, ensure_ascii=False).encode()
        self.add("notebooks/Flow.ipynb", raw, selection_reason="allowed_top_level_notebook")
        result = read_repository_sources(self.repo, self.root)
        self.assertEqual([a["cellIndex"] for a in result["authorities"]], [1, 3])
        self.assertEqual([a["text"] for a in result["authorities"]], ["".join(fragments)] * 2)
        self.assertTrue(all(a["rawFileSha256"] == hashlib.sha256(raw).hexdigest() for a in result["authorities"]))
        units = result["sourceUnits"]
        self.assertEqual(len(units), 2)
        self.assertNotEqual(units[0]["sourceUnitID"], units[1]["sourceUnitID"])
        self.assertNotIn("HIDDEN", repr(result))
        self.assertNotIn("RuntimeError", repr(result))
        self.assertEqual(read_repository_sources(self.repo, self.root), result)
        self.assertEqual(units[0]["startLine"], 3)
        self.assertEqual(units[0]["text"], "".join(fragments)[units[0]["startOffsetInAuthority"]:units[0]["endOffsetInAuthority"]])

    def test_paths_hashes_coordinates_and_source_failures(self) -> None:
        """Fail explicitly on unsafe, absent, unreadable, malformed or changed inputs."""
        raw = "# Flow\r\n\r\nCafé 🌊 models river discharge.\r\n".encode()
        self.add("docs/Flow.md", raw)
        self.add("docs/missing.md", None)
        self.add("docs/unreadable.md", None)
        (self.contents / "docs/unreadable.md").mkdir()
        self.add("docs/malformed.md", b"bad\x00text")
        self.add("notebooks/bad.ipynb", b"{bad json")
        self.add("notebooks/bad-cell.ipynb", json.dumps({"cells": [{"cell_type": "markdown", "source": [3]}]}))
        for path in ("../escape.md", "/absolute.md", "docs/../../escape.md", "C:\\escape.md"):
            self.add(path, None)
        outside = self.root / "outside.md"
        outside.write_text("External text should never be read.")
        (self.contents / "escape.md").symlink_to(outside)
        self.add("escape.md", None)
        result = read_repository_sources(self.repo, self.root)
        reasons = {row["reason"] for row in result["diagnostics"]}
        self.assertTrue({"unsafe_source_path", "downloaded_file_missing", "downloaded_file_unreadable",
                         "source_text_malformed", "downloaded_notebook_malformed",
                         "notebook_markdown_source_malformed"} <= reasons)
        self.assertFalse(result["inputComplete"])
        authority = result["authorities"][0]
        text = raw.decode().replace("\r\n", "\n")
        self.assertEqual(authority["text"], text)
        self.assertEqual(authority["rawFileSha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(authority["authorityTextSha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(authority["rawIntegrityStatus"], "computed_only")
        self.assertEqual(authority["textIntegrityStatus"], "computed_only")
        unit = result["sourceUnits"][0]
        self.assertEqual(unit["canonicalArtifactID"], "github:repo:17")
        self.assertIn("/blob/" + "a" * 40 + "/docs/Flow.md", unit["sourceLocation"])
        self.assertEqual((unit["startOffsetInAuthority"], unit["startLine"]), (8, 3))
        self.assertEqual(text[unit["startOffsetInAuthority"]:unit["endOffsetInAuthority"]], unit["text"])
        for expected in ("0" * 64, "malformed"):
            failed = read_repository_sources(self.repo, self.root, trusted_raw_sha256={"docs/Flow.md": expected})
            self.assertTrue(any(row["reason"] == "source_content_integrity_failure" for row in failed["diagnostics"]))
            self.assertEqual(failed["authorities"], [])
        verified = read_repository_sources(self.repo, self.root,
            trusted_raw_sha256={"docs/Flow.md": hashlib.sha256(raw).hexdigest()},
            trusted_authority_sha256={("docs/Flow.md", None): hashlib.sha256(text.encode()).hexdigest()})
        self.assertEqual(verified["authorities"][0]["textIntegrityStatus"], "matched_trusted_digest")
        text_failed = read_repository_sources(self.repo, self.root,
            trusted_authority_sha256={("docs/Flow.md", None): "0" * 64})
        self.assertEqual(text_failed["authorities"], [])
        with patch.object(Path, "read_bytes", side_effect=PermissionError("synthetic denial")):
            denied = read_repository_sources(self.repo, self.root)
        self.assertTrue(any(row["reason"] == "downloaded_file_unreadable" for row in denied["diagnostics"]))
        bad_repo = deepcopy(self.repo)
        bad_repo["archive"] = {}
        self.assertEqual(read_repository_sources(bad_repo, self.root)["diagnostics"][0]["reason"],
                         "source_provenance_missing_or_malformed")
        self.assertEqual(set(result), {"authorities", "sourceUnits", "reads", "diagnostics", "inputComplete"})
        self.assertNotIn("abstained_no_evidence", repr(result))


if __name__ == "__main__":
    unittest.main()
