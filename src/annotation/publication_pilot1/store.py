"""SQLite persistence and audit sidecar for Publication Pilot 1 screening."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import INTERFACE_VERSION


def utc_now() -> str:
    """Return the current UTC time in an unambiguous seconds-resolution form."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class DraftStore:
    """Persist reviewer identity, per-unit drafts, revisions, and session metadata."""

    def __init__(self, path: Path, namespace: str, hashes: Mapping[str, str]) -> None:
        """Open or initialize a namespace-specific SQLite draft database."""

        self.path = path
        self.namespace = namespace
        self.hashes = dict(hashes)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing_database = path.exists()
        # The production HTTP server is intentionally single-request, but browser-level
        # tests may create the server loop on another thread.
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS drafts (
                source_unit_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                screened_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS revisions (
                revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_unit_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                completed INTEGER NOT NULL,
                revised_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS revisit_bookmarks (
                source_unit_id TEXT PRIMARY KEY,
                bookmarked_at TEXT NOT NULL
            );
            """
        )
        bindings = {
            "screeningInterfaceVersion": INTERFACE_VERSION,
            "namespace": namespace,
            **hashes,
        }
        if existing_database:
            for key, expected in bindings.items():
                if self.get_metadata(key) != expected:
                    self.connection.close()
                    raise ValueError(f"SCREENING_STATE_CONTRACT_MISMATCH:{key}")
        else:
            for key, value in bindings.items():
                self.set_metadata(key, value)
        created = self.get_metadata("sessionCreatedAt") or utc_now()
        defaults = {
            "sessionCreatedAt": created,
            "lastSavedAt": "",
            "reviewerID": "",
            "lastExportKind": "",
            "lastExportTimestamp": "",
            "lastExportHash": "",
            "exportedReviewedCsvHash": "",
            "exportedReviewedCsvTimestamp": "",
        }
        for key, value in defaults.items():
            if self.get_metadata(key) is None:
                self.set_metadata(key, value)
        self.connection.commit()
        self.write_sidecar()

    @property
    def sidecar_path(self) -> Path:
        """Return the JSON audit sidecar path adjacent to the database."""

        return self.path.with_suffix(".session.json")

    def close(self) -> None:
        """Close the SQLite connection."""

        self.connection.close()

    def get_metadata(self, key: str) -> str | None:
        """Return one session metadata value when present."""

        row = self.connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def set_metadata(self, key: str, value: str) -> None:
        """Set one session metadata value."""

        self.connection.execute(
            "INSERT INTO metadata(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def reviewer_id(self) -> str:
        """Return the current persistent reviewer identity."""

        return self.get_metadata("reviewerID") or ""

    def reviewer_locked(self) -> bool:
        """Return whether the first immutable local revision has locked identity."""

        row = self.connection.execute("SELECT EXISTS(SELECT 1 FROM revisions) AS locked").fetchone()
        return bool(row["locked"])

    def change_reviewer(self, reviewer_id: str) -> None:
        """Deliberately change and persist the reviewer identity."""

        cleaned = reviewer_id.strip()
        if not cleaned:
            raise ValueError("REVIEWER_ID_REQUIRED")
        current = self.reviewer_id()
        if self.reviewer_locked() and cleaned != current:
            raise ValueError("SCREENING_REVIEWER_ID_LOCKED_AFTER_FIRST_REVISION")
        self.set_metadata("reviewerID", cleaned)
        self.set_metadata("lastSavedAt", utc_now())
        self.connection.commit()
        self.write_sidecar()

    def load_draft(self, source_unit_id: str) -> dict[str, Any]:
        """Return a saved draft or a deliberately blank semantic draft."""

        row = self.connection.execute(
            "SELECT payload, completed, screened_at, updated_at FROM drafts WHERE source_unit_id = ?",
            (source_unit_id,),
        ).fetchone()
        if row is None:
            return {"sourceUnitID": source_unit_id, "completed": False, "screenedAt": "", "updatedAt": ""}
        payload = json.loads(row["payload"])
        payload.update({"sourceUnitID": source_unit_id, "completed": bool(row["completed"]), "screenedAt": row["screened_at"], "updatedAt": row["updated_at"]})
        return payload

    def all_drafts(self) -> dict[str, dict[str, Any]]:
        """Return every persisted unit draft keyed by source-unit ID."""

        return {row["source_unit_id"]: self.load_draft(row["source_unit_id"]) for row in self.connection.execute("SELECT source_unit_id FROM drafts")}

    def save_draft(self, source_unit_id: str, payload: Mapping[str, Any], completed: bool) -> dict[str, Any]:
        """Autosave a draft and append an immutable local revision record."""

        previous = self.connection.execute(
            "SELECT screened_at FROM drafts WHERE source_unit_id = ?", (source_unit_id,)
        ).fetchone()
        screened_at = str(previous["screened_at"]) if previous and previous["screened_at"] else (utc_now() if completed else "")
        saved_at = utc_now()
        serialized = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.connection.execute(
            """INSERT INTO drafts(source_unit_id, payload, completed, screened_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(source_unit_id) DO UPDATE SET payload=excluded.payload,
               completed=excluded.completed, screened_at=excluded.screened_at, updated_at=excluded.updated_at""",
            (source_unit_id, serialized, int(completed), screened_at, saved_at),
        )
        self.connection.execute(
            "INSERT INTO revisions(source_unit_id, payload, completed, revised_at) VALUES (?, ?, ?, ?)",
            (source_unit_id, serialized, int(completed), saved_at),
        )
        self.set_metadata("lastSavedAt", saved_at)
        self.connection.commit()
        self.write_sidecar()
        return self.load_draft(source_unit_id)

    def completed_count(self) -> int:
        """Return the number of completed open-unit drafts."""

        row = self.connection.execute("SELECT COUNT(*) AS count FROM drafts WHERE completed = 1").fetchone()
        return int(row["count"])

    def revisit_ids(self) -> set[str]:
        """Return source-unit IDs manually bookmarked for local revisit."""

        return {
            str(row["source_unit_id"])
            for row in self.connection.execute("SELECT source_unit_id FROM revisit_bookmarks")
        }

    def set_revisit(self, source_unit_id: str, revisit: bool) -> None:
        """Set or clear one interface-local bookmark without changing its draft."""

        if revisit:
            self.connection.execute(
                "INSERT INTO revisit_bookmarks(source_unit_id, bookmarked_at) VALUES (?, ?) "
                "ON CONFLICT(source_unit_id) DO UPDATE SET bookmarked_at=excluded.bookmarked_at",
                (source_unit_id, utc_now()),
            )
        else:
            self.connection.execute(
                "DELETE FROM revisit_bookmarks WHERE source_unit_id = ?", (source_unit_id,)
            )
        self.connection.commit()
        self.write_sidecar()

    def record_export(self, kind: str, timestamp: str, digest: str) -> None:
        """Record the latest export and preserve complete-reviewed provenance."""

        if kind not in {"complete", "partial"}:
            raise ValueError(f"SCREENING_UNKNOWN_EXPORT_KIND:{kind}")
        self.set_metadata("lastExportKind", kind)
        self.set_metadata("lastExportTimestamp", timestamp)
        self.set_metadata("lastExportHash", digest)
        if kind == "complete":
            if self.namespace != "production":
                raise ValueError("DRY_RUN_COMPILER_READY_EXPORT_FORBIDDEN")
            self.set_metadata("exportedReviewedCsvHash", digest)
            self.set_metadata("exportedReviewedCsvTimestamp", timestamp)
        self.connection.commit()
        self.write_sidecar()

    def manifest(self) -> dict[str, Any]:
        """Build the private application session/audit sidecar payload."""

        metadata = {row["key"]: row["value"] for row in self.connection.execute("SELECT key, value FROM metadata")}
        revisions = {
            row["source_unit_id"]: row["revised_at"]
            for row in self.connection.execute(
                "SELECT source_unit_id, MAX(revised_at) AS revised_at FROM revisions GROUP BY source_unit_id"
            )
        }
        return {
            "screeningInterfaceVersion": metadata["screeningInterfaceVersion"],
            "stateNamespace": self.namespace,
            "canonicalWorklistHash": metadata["canonicalWorklistHash"],
            "targetDisplayCatalogHash": metadata["targetDisplayCatalogHash"],
            "targetFamilyMappingHash": metadata["targetFamilyMappingHash"],
            "screeningSchemaHash": metadata["screeningSchemaHash"],
            "selectionPolicyHash": metadata["selectionPolicyHash"],
            "screeningHandbookSha256": metadata["screeningHandbookSha256"],
            "reviewerID": metadata["reviewerID"],
            "sessionCreatedAt": metadata["sessionCreatedAt"],
            "lastSavedAt": metadata["lastSavedAt"],
            "completedUnitCount": self.completed_count(),
            "perUnitRevisionTimestamps": revisions,
            "revisitSourceUnitIDs": sorted(self.revisit_ids()),
            "lastExportKind": metadata["lastExportKind"],
            "lastExportTimestamp": metadata["lastExportTimestamp"],
            "lastExportHash": metadata["lastExportHash"],
            "exportedReviewedCsvHash": metadata["exportedReviewedCsvHash"],
            "exportedReviewedCsvTimestamp": metadata["exportedReviewedCsvTimestamp"],
        }

    def write_sidecar(self) -> None:
        """Write the private session manifest deterministically beside the database."""

        self.sidecar_path.write_text(json.dumps(self.manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def reset(self) -> None:
        """Delete dry-run work and unlock its reviewer without touching production."""

        if self.namespace != "dry-run":
            raise ValueError("PRODUCTION_RESET_FORBIDDEN")

        self.connection.execute("DELETE FROM drafts")
        self.connection.execute("DELETE FROM revisions")
        self.connection.execute("DELETE FROM revisit_bookmarks")
        self.set_metadata("reviewerID", "")
        self.set_metadata("lastSavedAt", utc_now())
        self.set_metadata("lastExportKind", "")
        self.set_metadata("lastExportTimestamp", "")
        self.set_metadata("lastExportHash", "")
        self.set_metadata("exportedReviewedCsvHash", "")
        self.set_metadata("exportedReviewedCsvTimestamp", "")
        self.connection.commit()
        self.write_sidecar()

    @staticmethod
    def remove_dry_run_state(path: Path) -> None:
        """Explicitly remove only dry-run SQLite and sidecar files for reinitialization."""

        if path.name != "dry-run.sqlite3":
            raise ValueError("DRY_RUN_RESET_PATH_REQUIRED")
        candidates = (
            path,
            Path(f"{path}-wal"),
            Path(f"{path}-shm"),
            path.with_suffix(".session.json"),
        )
        for candidate in candidates:
            if candidate.exists():
                candidate.unlink()
