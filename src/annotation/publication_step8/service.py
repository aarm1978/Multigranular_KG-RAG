"""Isolated local review sessions with explicit production activation and history."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import INTERFACE_VERSION
from .contracts import DUPLICATE_DECISIONS, INVENTORY_HASH, JUDGMENTS, ReviewError, ReviewInputs, canonical_json, runtime_hash


def activation_requirements(inputs: ReviewInputs, session_id: str, reviewer_id: str) -> dict[str, Any]:
    """Return the exact operator-approved activation fields; activate nothing."""

    return {"authorizedProductionReview": True, "reviewSessionID": session_id,
            "reviewerID": reviewer_id, "reviewRole": inputs.role,
            "inputPackageSha256": inputs.package_hash, "runtimeSha256": runtime_hash(),
            "sourceInventorySha256": INVENTORY_HASH, "interfaceVersion": INTERFACE_VERSION}


class ReviewService:
    """One process exposes exactly one role and local reviewer session."""

    def __init__(self, inputs: ReviewInputs, state_root: Path, session_id: str, reviewer_id: str,
                 mode: str = "dry-run", activation: Path | None = None) -> None:
        """Verify execution bindings before opening an isolated database."""

        if mode not in {"dry-run", "production"} or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", session_id):
            raise ReviewError("INVALID_MODE_OR_SESSION")
        if not reviewer_id.strip() or len(reviewer_id) > 120:
            raise ReviewError("REVIEWER_ID_REQUIRED")
        self.inputs, self.mode, self.session_id = inputs, mode, session_id
        self.runtime = runtime_hash()
        self.activation = activation
        if mode == "production":
            self._verify_activation(reviewer_id)
        inputs.verify_package()
        self.path = state_root / mode / inputs.role / (session_id + ".sqlite")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS session (id INTEGER PRIMARY KEY CHECK(id=1), binding TEXT NOT NULL, reviewer TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, kind TEXT NOT NULL, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS phases (unit TEXT PRIMARY KEY, phase TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (revision INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL);
        """)
        binding = canonical_json({"reviewSessionID": session_id, "reviewRole": inputs.role, "mode": mode,
                                  "inputPackageSha256": inputs.package_hash, "runtimeSha256": self.runtime,
                                  "sourceInventorySha256": INVENTORY_HASH, "interfaceVersion": INTERFACE_VERSION}).decode()
        existing = self.db.execute("SELECT * FROM session WHERE id=1").fetchone()
        if existing is not None and (existing["binding"] != binding or existing["reviewer"] != reviewer_id):
            self.db.close()
            raise ReviewError("SESSION_BINDING_OR_REVIEWER_DRIFT")
        if existing is None:
            self.db.execute("INSERT INTO session VALUES (1,?,?)", (binding, reviewer_id))
            self.db.commit()

    def close(self) -> None:
        """Flush and close the isolated local database."""

        self.db.close()

    def _verify_activation(self, reviewer: str) -> None:
        """Require exact explicit approval; missing or stale activation fails closed."""

        expected = activation_requirements(self.inputs, self.session_id, reviewer)
        if self.activation is None or not self.activation.is_file():
            raise ReviewError("PRODUCTION_ACTIVATION_REQUIRED")
        try:
            observed = json.loads(self.activation.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise ReviewError("INVALID_PRODUCTION_ACTIVATION") from exc
        if observed != expected:
            raise ReviewError("PRODUCTION_ACTIVATION_BINDING_DRIFT")

    def guard(self) -> None:
        """Check accepted input, runtime, and production approval before access."""

        self.inputs.verify_package()
        if runtime_hash() != self.runtime:
            raise ReviewError("RUNTIME_BINDING_DRIFT")
        if self.mode == "production":
            self._verify_activation(self.reviewer())

    def reviewer(self) -> str:
        """Read the persistent reviewer identity."""

        return self.db.execute("SELECT reviewer FROM session WHERE id=1").fetchone()[0]

    def revision(self) -> int:
        """Return the current optimistic concurrency revision."""

        return self.db.execute("SELECT COALESCE(MAX(revision),0) FROM events").fetchone()[0]

    def decisions(self) -> dict[str, str]:
        """Return only this session's current decisions."""

        return {row["id"]: row["value"] for row in self.db.execute("SELECT * FROM decisions ORDER BY id")}

    def phase(self, unit: str) -> str:
        """Default an unopened unit to source orientation."""

        row = self.db.execute("SELECT phase FROM phases WHERE unit=?", (unit,)).fetchone()
        return row[0] if row else "orientation"

    def _items(self, unit: str, kind: str | None = None) -> list[str]:
        """Derive assigned IDs from the session's accepted blinded package."""

        return [key for key, item in self.inputs.items.items()
                if item["primarySourceUnitID"] == unit and (kind is None or item["recordKind"] == kind)]

    def _groups(self, unit: str) -> list[str]:
        """Derive existing blinded groups for one assigned primary unit."""

        return [key for key, group in self.inputs.groups.items()
                if all(self.inputs.items[item]["primarySourceUnitID"] == unit for item in group["judgmentItemIDs"])]

    def state(self) -> dict[str, Any]:
        """Expose reviewer-local navigation and progress without private lineage."""

        self.guard()
        answers = self.decisions()
        units = [{"primarySourceUnitID": unit, "phase": self.phase(unit),
                  "nodesTotal": len(self._items(unit, "node")), "nodesAnswered": sum(key in answers for key in self._items(unit, "node")),
                  "relationsTotal": len(self._items(unit, "relation")), "relationsAnswered": sum(key in answers for key in self._items(unit, "relation"))}
                 for unit in self.inputs.units]
        return {"reviewSessionID": self.session_id, "reviewRole": self.inputs.role, "reviewerID": self.reviewer(),
                "mode": self.mode, "revision": self.revision(), "reviewerLocked": bool(answers),
                "units": units, "decisions": answers, "judgments": JUDGMENTS, "duplicateDecisions": DUPLICATE_DECISIONS,
                "answered": sum(key in answers for key in self.inputs.items), "total": len(self.inputs.items),
                "complete": all(key in answers for key in [*self.inputs.items, *self.inputs.groups])}

    def unit(self, unit: str) -> dict[str, Any]:
        """Return exactly one authorized unit's immutable review content."""

        self.guard()
        return self.inputs.unit(unit)

    def change(self, body: dict[str, Any]) -> dict[str, Any]:
        """Persist one deliberate action atomically with append-only revisions."""

        self.guard()
        if set(body) - {"expectedRevision", "action", "id", "value"}:
            raise ReviewError("UNKNOWN_ACTION_FIELDS")
        if type(body.get("expectedRevision")) is not int:
            raise ReviewError("REVISION_REQUIRED")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if body["expectedRevision"] != self.revision():
                raise ReviewError("STALE_REVISION_RELOAD_REQUIRED")
            action, key, value = body.get("action"), body.get("id"), body.get("value")
            answers = self.decisions()
            unit = None
            if action == "reviewer":
                if answers:
                    raise ReviewError("REVIEWER_IDENTITY_LOCKED")
                if not isinstance(value, str) or not value.strip() or len(value) > 120:
                    raise ReviewError("REVIEWER_ID_REQUIRED")
                if self.mode == "production":
                    self._verify_activation(value)
                self.db.execute("UPDATE session SET reviewer=? WHERE id=1", (value,))
            elif action in {"judgment", "duplicate"}:
                if action == "judgment":
                    item = self.inputs.items.get(key)
                    if item is None or value not in JUDGMENTS:
                        raise ReviewError("INVALID_JUDGMENT_OR_ITEM")
                    unit = item["primarySourceUnitID"]
                    needed = "nodes" if item["recordKind"] == "node" else "relations"
                    if self.phase(unit) != needed:
                        raise ReviewError("REVIEW_PHASE_MISMATCH")
                else:
                    group = self.inputs.groups.get(key)
                    if group is None or value not in DUPLICATE_DECISIONS:
                        raise ReviewError("INVALID_DUPLICATE_DECISION_OR_GROUP")
                    unit = self.inputs.items[group["judgmentItemIDs"][0]]["primarySourceUnitID"]
                    if self.phase(unit) != "relations":
                        raise ReviewError("REVIEW_PHASE_MISMATCH")
                self.db.execute("INSERT INTO decisions VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (key, action, value))
            elif action == "phase":
                unit = key
                if unit not in self.inputs.units:
                    raise ReviewError("UNIT_NOT_ASSIGNED")
                previous = self.phase(unit)
                allowed = {"orientation": {"nodes"}, "nodes": {"relations"}, "relations": {"nodes", "complete"}, "complete": set()}
                if value not in allowed[previous]:
                    raise ReviewError("INVALID_PHASE_TRANSITION")
                required = self._items(unit) + self._groups(unit) if value == "complete" else []
                if any(identifier not in answers for identifier in required):
                    raise ReviewError("UNIT_PHASE_INCOMPLETE")
                self.db.execute("INSERT INTO phases VALUES (?,?) ON CONFLICT(unit) DO UPDATE SET phase=excluded.phase", (unit, value))
            else:
                raise ReviewError("UNKNOWN_REVIEW_ACTION")
            event = {"reviewSessionID": self.session_id, "reviewerID": self.reviewer(), "reviewRole": self.inputs.role,
                     "action": action, "id": key, "value": value, "primarySourceUnitID": unit,
                     "timestamp": datetime.now(timezone.utc).isoformat(), "revision": self.revision() + 1}
            if action == "judgment":
                event.update(judgmentItemID=key, judgment=value)
            elif action == "duplicate":
                event.update(duplicateReviewGroupID=key, duplicateDecision=value)
            self.db.execute("INSERT INTO events(payload) VALUES (?)", (canonical_json(event).decode(),))
        return self.state()

    def export(self) -> bytes:
        """Export stable bytes for unchanged state, retaining every revision."""

        state = self.state()
        records = [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM events ORDER BY revision")]
        binding = json.loads(self.db.execute("SELECT binding FROM session WHERE id=1").fetchone()[0])
        return canonical_json({"exportVersion": INTERFACE_VERSION, **binding, "reviewerID": self.reviewer(),
                               "syntheticDryRun": self.mode == "dry-run", "revision": state["revision"],
                               "judgments": {key: value for key, value in sorted(state["decisions"].items()) if key in self.inputs.items},
                               "duplicateDecisions": {key: value for key, value in sorted(state["decisions"].items()) if key in self.inputs.groups},
                               "currentPaperEndpointBindings": getattr(self.inputs, "endpoint_bindings", {}),
                               "complete": state["complete"], "unitCompletion": {unit: self.phase(unit) == "complete" for unit in self.inputs.units},
                               "revisions": records}) + b"\n"
