"""Bounded persistent service for joint blinded Step 8 reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


FINAL_DECISIONS = ("supported_as_proposed", "not_supported_as_proposed", "insufficient_evidence_to_decide", "adjudication_unresolved")


class ReconciliationError(ValueError):
    """Fail closed on reconciliation package, state, or export drift."""


def digest(data: bytes) -> str:
    """Return an exact SHA-256 string."""

    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    """Serialize deterministic UTF-8 JSON without incidental whitespace."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class ReconciliationService:
    """Expose only the frozen disagreement package and a local decision map."""

    def __init__(self, package_path: Path, state_path: Path) -> None:
        """Verify the frozen package before opening a package-local state file."""

        self.package_path, self.state_path = package_path, state_path
        self.package_bytes = package_path.read_bytes()
        self.package_hash = digest(self.package_bytes)
        try:
            self.package = json.loads(self.package_bytes)
        except ValueError as exc:
            raise ReconciliationError("RECONCILIATION_PACKAGE_INVALID") from exc
        body = dict(self.package)
        observed = body.pop("artifactSha256", None)
        if observed != digest(canonical_json(body)) or self.package.get("artifactType") != "publication_step8_reconciliation_package":
            raise ReconciliationError("RECONCILIATION_PACKAGE_BINDING_DRIFT")
        self.items = {item["judgmentItem"]["judgmentItemID"]: item for item in self.package.get("items", [])}
        if (self.package.get("itemCount") != 11 or self.package.get("judgmentItemIDs") != sorted(self.items)
                or len(self.items) != 11 or tuple(self.package.get("allowedFinalDecisions", [])) != FINAL_DECISIONS):
            raise ReconciliationError("RECONCILIATION_PACKAGE_SCOPE_DRIFT")
        self._state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Load or initialize a package-bound local autosave state."""

        if not self.state_path.exists():
            return {"packageSha256": self.package_hash, "revision": 0, "decisions": {}}
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ReconciliationError("RECONCILIATION_STATE_INVALID") from exc
        if (not isinstance(value, dict) or value.get("packageSha256") != self.package_hash or not isinstance(value.get("revision"), int)
                or value["revision"] < 0 or not isinstance(value.get("decisions"), dict)
                or not set(value["decisions"]) <= set(self.items) or any(choice not in FINAL_DECISIONS for choice in value["decisions"].values())):
            raise ReconciliationError("RECONCILIATION_STATE_BINDING_DRIFT")
        return value

    def _save(self) -> None:
        """Atomically persist deterministic local state for resume."""

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_json(self._state) + b"\n")
        os.replace(temporary, self.state_path)

    def state(self) -> dict[str, Any]:
        """Return progress without exposing any unlisted candidate or reviewer identity."""

        return {"revision": self._state["revision"], "decisions": dict(self._state["decisions"]),
                "answered": len(self._state["decisions"]), "total": len(self.items),
                "complete": len(self._state["decisions"]) == len(self.items), "allowedFinalDecisions": list(FINAL_DECISIONS)}

    def item(self, item_id: str) -> dict[str, Any]:
        """Return one exact frozen disagreement item only."""

        if item_id not in self.items:
            raise ReconciliationError("RECONCILIATION_ITEM_NOT_ASSIGNED")
        return self.items[item_id]

    def decide(self, expected_revision: int, item_id: str, decision: str) -> dict[str, Any]:
        """Autosave one authorized final category with optimistic concurrency."""

        if expected_revision != self._state["revision"]:
            raise ReconciliationError("STALE_REVISION_RELOAD_REQUIRED")
        if item_id not in self.items or decision not in FINAL_DECISIONS:
            raise ReconciliationError("INVALID_RECONCILIATION_DECISION")
        self._state["decisions"][item_id] = decision
        self._state["revision"] += 1
        self._save()
        return self.state()

    def export(self, runtime_hash: str) -> bytes:
        """Return a canonical completed-session export, rejecting incomplete decisions."""

        if len(self._state["decisions"]) != len(self.items):
            raise ReconciliationError("RECONCILIATION_INCOMPLETE")
        return canonical_json({"exportType": "publication_step8_final_reconciliation", "exportVersion": "1.0.0",
                               "reconciliationPackageSha256": self.package_hash,
                               "sourceDisagreementPackage": self.package["sourceDisagreementPackage"],
                               "sourceAgreement": self.package["sourceAgreement"], "runtimeSha256": runtime_hash,
                               "itemCount": len(self.items), "complete": True,
                               "finalDecisions": {item_id: self._state["decisions"][item_id] for item_id in sorted(self.items)}}) + b"\n"
