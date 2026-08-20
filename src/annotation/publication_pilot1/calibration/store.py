"""Isolated SQLite persistence for independent annotation/calibration sessions."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from . import (
    ANNOTATION_OUTPUT_SCHEMA_VERSION,
    CONTEXT_POLICY_NAME,
    CONTEXT_POLICY_VERSION,
    GUIDELINE_VERSION,
    HANDBOOK_VERSION,
    INTERFACE_VERSION,
    ROUTING_VERSION,
)
from .contracts import AnnotationContractError


TIMING_EVENTS = (
    "unit_opened", "reading_complete", "node_pass_started", "node_pass_completed",
    "relation_pass_started", "relation_pass_completed", "review_started", "submitted",
    "pause_started", "pause_ended", "technical_interruption_started", "technical_interruption_ended",
)
MAIN_EVENTS = set(TIMING_EVENTS[:8])


def utc_now() -> str:
    """Return an ordered UTC timestamp with microsecond resolution."""

    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class AnnotationStore:
    """Persist exactly one stable independent annotator session."""

    def __init__(
        self,
        path: Path,
        *,
        mode: str,
        annotation_session_id: str,
        annotator_id: str,
        bindings: Mapping[str, str],
        clock: Callable[[], str] = utc_now,
    ) -> None:
        """Open or initialize a version- and identity-bound SQLite database."""

        if not annotation_session_id.strip() or not annotator_id.strip():
            raise AnnotationContractError("ANNOTATION_SESSION_AND_ANNOTATOR_ID_REQUIRED")
        self.path, self.mode = path, mode
        self.annotation_session_id, self.annotator_id = annotation_session_id.strip(), annotator_id.strip()
        self.clock = clock
        path.parent.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS drafts (
                source_unit_id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                status TEXT NOT NULL, revision_number INTEGER NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS revisions (
                revision_id INTEGER PRIMARY KEY AUTOINCREMENT, source_unit_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL, payload TEXT NOT NULL, action TEXT NOT NULL,
                created_at TEXT NOT NULL, UNIQUE(source_unit_id, revision_number)
            );
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id INTEGER PRIMARY KEY AUTOINCREMENT, source_unit_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL, payload TEXT NOT NULL, submitted_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT, source_unit_id TEXT NOT NULL,
                action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS timing_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, source_unit_id TEXT NOT NULL,
                source_unit_text_hash TEXT NOT NULL, interface_version TEXT NOT NULL,
                guideline_version TEXT NOT NULL, handbook_version TEXT NOT NULL,
                routing_version TEXT NOT NULL, event_type TEXT NOT NULL, timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS context_exposures (
                exposure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                primary_source_unit_id TEXT NOT NULL,
                context_source_unit_id TEXT NOT NULL,
                context_scope TEXT NOT NULL,
                context_policy_name TEXT NOT NULL,
                context_policy_version TEXT NOT NULL,
                context_selection_reason TEXT NOT NULL,
                task_binding_type TEXT,
                task_binding_id TEXT,
                exposed_at TEXT NOT NULL
            );
            """
        )
        expected = {
            "annotationSessionID": self.annotation_session_id, "annotatorID": self.annotator_id,
            "mode": mode, "interfaceVersion": INTERFACE_VERSION,
            "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
            "guidelineVersion": GUIDELINE_VERSION, "handbookVersion": HANDBOOK_VERSION,
            "routingVersion": ROUTING_VERSION,
            "contextPolicyName": CONTEXT_POLICY_NAME, "contextPolicyVersion": CONTEXT_POLICY_VERSION,
            **bindings,
        }
        if existed:
            for key, value in expected.items():
                if self.metadata(key) != value:
                    self.connection.close()
                    raise AnnotationContractError(f"ANNOTATION_STATE_CONTRACT_MISMATCH:{key}")
        else:
            for key, value in expected.items():
                self._set_metadata(key, value)
            self._set_metadata("createdAt", self.clock())
            self.connection.commit()

    def close(self) -> None:
        """Close the local database."""

        self.connection.close()

    def metadata(self, key: str) -> str | None:
        """Return one immutable session binding."""

        row = self.connection.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def _set_metadata(self, key: str, value: str) -> None:
        """Set one initialization metadata binding."""

        self.connection.execute(
            "INSERT INTO metadata(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def load(self, source_unit_id: str) -> dict[str, Any] | None:
        """Load this session's draft for one unit."""

        row = self.connection.execute(
            "SELECT payload,status,revision_number,updated_at FROM drafts WHERE source_unit_id=?", (source_unit_id,)
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload"])
        payload["persistence"] = {
            "status": row["status"], "revisionNumber": row["revision_number"], "updatedAt": row["updated_at"]
        }
        return payload

    def summaries(self) -> dict[str, dict[str, Any]]:
        """Return non-semantic status for this session only."""

        return {
            str(row["source_unit_id"]): {
                "status": str(row["status"]), "revisionNumber": int(row["revision_number"]),
                "updatedAt": str(row["updated_at"]),
            }
            for row in self.connection.execute("SELECT source_unit_id,status,revision_number,updated_at FROM drafts")
        }

    def save(self, source_unit_id: str, payload: Mapping[str, Any], *, action: str = "autosave") -> dict[str, Any]:
        """Append an immutable revision and update the current draft pointer."""

        previous = self.connection.execute(
            "SELECT status,revision_number FROM drafts WHERE source_unit_id=?", (source_unit_id,)
        ).fetchone()
        if previous is not None and previous["status"] == "submitted":
            raise AnnotationContractError("ANNOTATION_SUBMITTED_RECORD_REOPEN_REQUIRED")
        revision = 1 if previous is None else int(previous["revision_number"]) + 1
        now = self.clock()
        serialized = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        status = "reopened" if previous is not None and previous["status"] == "reopened" else "draft"
        self.connection.execute(
            """INSERT INTO drafts(source_unit_id,payload,status,revision_number,updated_at) VALUES (?,?,?,?,?)
               ON CONFLICT(source_unit_id) DO UPDATE SET payload=excluded.payload,status=excluded.status,
               revision_number=excluded.revision_number,updated_at=excluded.updated_at""",
            (source_unit_id, serialized, status, revision, now),
        )
        self.connection.execute(
            "INSERT INTO revisions(source_unit_id,revision_number,payload,action,created_at) VALUES (?,?,?,?,?)",
            (source_unit_id, revision, serialized, action, now),
        )
        self.connection.commit()
        return self.load(source_unit_id) or {}

    def submit(self, source_unit_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create an immutable submission snapshot without overwriting prior submissions."""

        saved = self.save(source_unit_id, payload, action="submit_revision")
        revision, now = int(saved["persistence"]["revisionNumber"]), self.clock()
        serialized = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.connection.execute(
            "INSERT INTO submissions(source_unit_id,revision_number,payload,submitted_at) VALUES (?,?,?,?)",
            (source_unit_id, revision, serialized, now),
        )
        self.connection.execute("UPDATE drafts SET status='submitted',updated_at=? WHERE source_unit_id=?", (now, source_unit_id))
        self.connection.execute(
            "INSERT INTO audit_actions(source_unit_id,action,detail,created_at) VALUES (?,?,?,?)",
            (source_unit_id, "submitted", f"revision:{revision}", now),
        )
        self.connection.commit()
        return self.load(source_unit_id) or {}

    def reopen(self, source_unit_id: str, reason: str) -> dict[str, Any]:
        """Preserve submitted history and audit a deliberate reopen action."""

        row = self.connection.execute("SELECT status,payload FROM drafts WHERE source_unit_id=?", (source_unit_id,)).fetchone()
        if row is None or row["status"] != "submitted":
            raise AnnotationContractError("ANNOTATION_REOPEN_REQUIRES_SUBMITTED_RECORD")
        cleaned = reason.strip()
        if not cleaned:
            raise AnnotationContractError("ANNOTATION_REOPEN_REASON_REQUIRED")
        payload = json.loads(row["payload"])
        payload["workflowState"] = "reopened"
        now = self.clock()
        self.connection.execute(
            "UPDATE drafts SET payload=?,status='reopened',updated_at=? WHERE source_unit_id=?",
            (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")), now, source_unit_id),
        )
        self.connection.execute(
            "INSERT INTO audit_actions(source_unit_id,action,detail,created_at) VALUES (?,?,?,?)",
            (source_unit_id, "reopened", cleaned, now),
        )
        self.connection.commit()
        return self.load(source_unit_id) or {}

    def timing_events(self, source_unit_id: str) -> list[dict[str, str]]:
        """Return the complete bound event stream for one unit."""

        return [{
            "annotationSessionID": self.annotation_session_id, "annotatorID": self.annotator_id,
            "sourceUnitID": str(row["source_unit_id"]), "sourceUnitTextHash": str(row["source_unit_text_hash"]),
            "interfaceVersion": str(row["interface_version"]), "guidelineVersion": str(row["guideline_version"]),
            "handbookVersion": str(row["handbook_version"]), "routingVersion": str(row["routing_version"]),
            "timestamp": str(row["timestamp"]), "eventType": str(row["event_type"]),
        } for row in self.connection.execute(
            "SELECT * FROM timing_events WHERE source_unit_id=? ORDER BY event_id", (source_unit_id,)
        )]

    def context_exposures(self, primary_source_unit_id: str | None = None) -> list[dict[str, Any]]:
        """Return append-only human context-exposure audit records."""

        query = "SELECT * FROM context_exposures"
        parameters: tuple[str, ...] = ()
        if primary_source_unit_id is not None:
            query += " WHERE primary_source_unit_id=?"; parameters = (primary_source_unit_id,)
        query += " ORDER BY exposure_id"
        return [{
            "exposureID": int(row["exposure_id"]),
            "primarySourceUnitID": str(row["primary_source_unit_id"]),
            "contextSourceUnitID": str(row["context_source_unit_id"]),
            "contextScope": str(row["context_scope"]),
            "contextPolicyName": str(row["context_policy_name"]),
            "contextPolicyVersion": str(row["context_policy_version"]),
            "contextSelectionReason": str(row["context_selection_reason"]),
            "taskBindingType": None if row["task_binding_type"] is None else str(row["task_binding_type"]),
            "taskBindingID": None if row["task_binding_id"] is None else str(row["task_binding_id"]),
            "exposedAt": str(row["exposed_at"]),
        } for row in self.connection.execute(query, parameters)]

    def exposed_context_ids(self, primary_source_unit_id: str) -> tuple[str, ...]:
        """Return distinct context IDs in first-exposure order for one primary unit."""

        return tuple(dict.fromkeys(
            row["contextSourceUnitID"] for row in self.context_exposures(primary_source_unit_id)
        ))

    def log_context_exposure(
        self, primary_source_unit_id: str, context_source_unit_id: str, context_scope: str,
        context_selection_reason: str, *, task_binding_type: str | None, task_binding_id: str | None,
    ) -> dict[str, Any]:
        """Append one version-bound context exposure without changing annotation timing."""

        self.connection.execute(
            """INSERT INTO context_exposures(
                   primary_source_unit_id,context_source_unit_id,context_scope,context_policy_name,
                   context_policy_version,context_selection_reason,task_binding_type,task_binding_id,exposed_at
               ) VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                primary_source_unit_id, context_source_unit_id, context_scope, CONTEXT_POLICY_NAME,
                CONTEXT_POLICY_VERSION, context_selection_reason, task_binding_type, task_binding_id, self.clock(),
            ),
        )
        self.connection.commit()
        return self.context_exposures(primary_source_unit_id)[-1]

    def log_timing(self, source_unit_id: str, source_unit_text_hash: str, event_type: str) -> dict[str, str]:
        """Validate and append one frozen-vocabulary timing event."""

        if event_type not in TIMING_EVENTS:
            raise AnnotationContractError(f"ANNOTATION_TIMING_EVENT_UNKNOWN:{event_type}")
        prior = self.timing_events(source_unit_id)
        main = [event["eventType"] for event in prior if event["eventType"] in MAIN_EVENTS]
        pause_open = sum(e["eventType"] == "pause_started" for e in prior) > sum(e["eventType"] == "pause_ended" for e in prior)
        technical_open = sum(e["eventType"] == "technical_interruption_started" for e in prior) > sum(e["eventType"] == "technical_interruption_ended" for e in prior)
        if event_type in MAIN_EVENTS:
            if not main:
                expected = "unit_opened"
            elif main[-1] == "submitted":
                expected = "node_pass_started"
            else:
                expected = {
                    "unit_opened": "reading_complete", "reading_complete": "node_pass_started",
                    "node_pass_started": "node_pass_completed", "node_pass_completed": "relation_pass_started",
                    "relation_pass_started": "relation_pass_completed", "relation_pass_completed": "review_started",
                    "review_started": "submitted",
                }.get(main[-1])
            if event_type != expected:
                raise AnnotationContractError(f"ANNOTATION_TIMING_SEQUENCE_INVALID:{event_type}")
            if pause_open or technical_open:
                raise AnnotationContractError("ANNOTATION_TIMING_PHASE_EVENT_DURING_EXCLUSION")
        elif not main or main[-1] == "submitted":
            raise AnnotationContractError(f"ANNOTATION_TIMING_EXCLUSION_OUTSIDE_ACTIVE_SESSION:{event_type}")
        elif event_type == "pause_started" and (pause_open or technical_open):
            raise AnnotationContractError("ANNOTATION_TIMING_PAUSE_NESTING_INVALID")
        elif event_type == "pause_ended" and not pause_open:
            raise AnnotationContractError("ANNOTATION_TIMING_PAUSE_END_WITHOUT_START")
        elif event_type == "technical_interruption_started" and (technical_open or pause_open):
            raise AnnotationContractError("ANNOTATION_TIMING_TECHNICAL_NESTING_INVALID")
        elif event_type == "technical_interruption_ended" and not technical_open:
            raise AnnotationContractError("ANNOTATION_TIMING_TECHNICAL_END_WITHOUT_START")
        timestamp = self.clock()
        self.connection.execute(
            """INSERT INTO timing_events(source_unit_id,source_unit_text_hash,interface_version,guideline_version,
               handbook_version,routing_version,event_type,timestamp) VALUES (?,?,?,?,?,?,?,?)""",
            (source_unit_id, source_unit_text_hash, INTERFACE_VERSION, GUIDELINE_VERSION,
             HANDBOOK_VERSION, ROUTING_VERSION, event_type, timestamp),
        )
        self.connection.commit()
        return self.timing_events(source_unit_id)[-1]

    def reset(self) -> None:
        """Reset only discarded synthetic state."""

        if self.mode != "synthetic":
            raise AnnotationContractError("CALIBRATION_PRODUCTION_RESET_FORBIDDEN")
        self.connection.executescript(
            "DELETE FROM drafts; DELETE FROM revisions; DELETE FROM submissions; DELETE FROM audit_actions; "
            "DELETE FROM timing_events; DELETE FROM context_exposures;"
        )
        self.connection.commit()

    def export_payload(self) -> dict[str, Any]:
        """Build a deterministic session-scoped annotations, audit, and timing export."""

        annotations = [{
            "sourceUnitID": row["source_unit_id"], "status": row["status"],
            "revisionNumber": row["revision_number"], "updatedAt": row["updated_at"],
            "annotation": json.loads(row["payload"]),
        } for row in self.connection.execute(
            "SELECT source_unit_id,payload,status,revision_number,updated_at FROM drafts ORDER BY source_unit_id"
        )]
        revisions = [{
            "revisionID": int(row["revision_id"]), "sourceUnitID": str(row["source_unit_id"]),
            "revisionNumber": int(row["revision_number"]), "annotation": json.loads(row["payload"]),
            "action": str(row["action"]), "createdAt": str(row["created_at"]),
        } for row in self.connection.execute("SELECT * FROM revisions ORDER BY revision_id")]
        submissions = [{
            "submissionID": int(row["submission_id"]), "sourceUnitID": str(row["source_unit_id"]),
            "revisionNumber": int(row["revision_number"]), "annotation": json.loads(row["payload"]),
            "submittedAt": str(row["submitted_at"]),
        } for row in self.connection.execute("SELECT * FROM submissions ORDER BY submission_id")]
        actions = [dict(row) for row in self.connection.execute(
            "SELECT action_id,source_unit_id,action,detail,created_at FROM audit_actions ORDER BY action_id"
        )]
        timing: list[dict[str, str]] = []
        for row in self.connection.execute("SELECT DISTINCT source_unit_id FROM timing_events ORDER BY source_unit_id"):
            timing.extend(self.timing_events(str(row["source_unit_id"])))
        return {
            "annotationSessionID": self.annotation_session_id, "annotatorID": self.annotator_id,
            "mode": self.mode, "interfaceVersion": INTERFACE_VERSION,
            "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
            "guidelineVersion": GUIDELINE_VERSION, "handbookVersion": HANDBOOK_VERSION,
            "routingVersion": ROUTING_VERSION,
            "contextPolicyName": CONTEXT_POLICY_NAME, "contextPolicyVersion": CONTEXT_POLICY_VERSION,
            "annotations": annotations,
            "revisions": revisions, "submissions": submissions,
            "auditActions": actions, "timingEvents": timing,
            "contextExposures": self.context_exposures(),
        }
