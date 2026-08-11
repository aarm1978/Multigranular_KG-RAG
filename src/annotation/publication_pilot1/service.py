"""Application service for human-driven Publication Pilot 1 screening."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    BOOLEAN_FIELDS,
    DENSITIES,
    MULTI_FIELDS,
    OPEN_UNIT_COUNT,
    RECURRING_DISTINCTIONS,
    ROUTING_COMPLEXITIES,
    ContractBundle,
    ContractError,
    is_open,
)
from .store import DraftStore, utc_now


EDITABLE_FIELDS = {
    "screeningRationale",
    "likelyExhaustiveEmptyTargetIDs",
    "likelyRecurringDistinctions",
    "expectedAssertionDensity",
    "expectedRelationDensity",
    "routingComplexity",
    *BOOLEAN_FIELDS,
    "routedNodeOperationalTargetIDs",
    "routedRelationOperationalTargetIDs",
    "screeningNotes",
}


class ScreeningService:
    """Coordinate immutable contracts, validated drafts, navigation, and export."""

    def __init__(self, contracts: ContractBundle, store: DraftStore, export_dir: Path, dry_run: bool) -> None:
        """Create a service for one isolated production or dry-run namespace."""

        self.contracts = contracts
        self.store = store
        self.export_dir = export_dir.resolve()
        self.dry_run = dry_run
        self.rows_by_id = {row["sourceUnitID"]: row for row in contracts.rows}
        self.targets = contracts.target_by_id()
        self.node_ids = {target_id for target_id, target in self.targets.items() if target["targetKind"] == "node"}
        self.relation_ids = {target_id for target_id, target in self.targets.items() if target["targetKind"] == "relation"}

    def bootstrap(self) -> dict[str, Any]:
        """Return deterministic controls, target catalog, and session state for the UI."""

        drafts = self.store.all_drafts()
        units = []
        for row in self.contracts.open_rows:
            draft = drafts.get(row["sourceUnitID"], {})
            units.append({
                "sourceUnitID": row["sourceUnitID"],
                "paperID": row["paperID"],
                "sectionRole": row["sectionRole"],
                "sectionTitle": row["sectionTitle"],
                "characterCount": int(row["characterCount"]),
                "sourceConversionStatus": row["sourceConversionStatus"],
                "completed": bool(draft.get("completed", False)),
            })
        return {
            "mode": "dry-run" if self.dry_run else "production",
            "reviewerID": self.store.reviewer_id(),
            "reviewerLocked": self.store.reviewer_locked(),
            "progress": self.progress(),
            "units": units,
            "targets": list(self.contracts.targets),
            "controls": {
                "densities": list(DENSITIES),
                "routingComplexities": list(ROUTING_COMPLEXITIES),
                "recurringDistinctions": list(RECURRING_DISTINCTIONS),
            },
        }

    def progress(self) -> dict[str, int]:
        """Return reviewed and remaining counts for the 267 open units."""

        completed = self.store.completed_count()
        return {"reviewed": completed, "total": OPEN_UNIT_COUNT, "remaining": OPEN_UNIT_COUNT - completed}

    def unit(self, source_unit_id: str) -> dict[str, Any]:
        """Return one open unit, exact validated text, and its persisted draft."""

        row = self.rows_by_id.get(source_unit_id)
        if row is None or not is_open(row):
            raise ContractError(f"SCREENING_UNIT_NOT_OPEN:{source_unit_id}")
        try:
            text = self.contracts.load_source_text(source_unit_id)
            validation_error = None
        except ContractError as exc:
            text, validation_error = "", str(exc)
        return {
            "metadata": {
                "paperID": row["paperID"],
                "sourceArtifactID": row["sourceArtifactID"],
                "sourceUnitID": row["sourceUnitID"],
                "sectionTitle": row["sectionTitle"],
                "sectionRole": row["sectionRole"],
                "characterCount": int(row["characterCount"]),
                "contentTypes": row["contentTypes"].split("|") if row["contentTypes"] else [],
                "sourceConversionStatus": row["sourceConversionStatus"],
                "reviewRequired": row["reviewRequired"] == "true",
                "reviewReasons": row["reviewReasons"].split("|") if row["reviewReasons"] else [],
                "sourceUnitTextHash": row["sourceUnitTextHash"],
            },
            "text": text,
            "textValidationError": validation_error,
            "reviewBlocked": validation_error is not None,
            "draft": self.store.load_draft(source_unit_id),
        }

    def _clean_payload(self, payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Validate draft shape and clear incompatible exhaustive-empty selections."""

        unknown = set(payload) - EDITABLE_FIELDS
        if unknown:
            raise ContractError(f"SCREENING_DETERMINISTIC_OR_UNKNOWN_FIELD:{sorted(unknown)[0]}")
        cleaned: dict[str, Any] = {}
        for field in EDITABLE_FIELDS:
            value = payload.get(field)
            if field in MULTI_FIELDS:
                if value is None:
                    value = []
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    raise ContractError(f"SCREENING_INVALID_ARRAY:{field}")
                cleaned[field] = sorted(set(item.strip() for item in value if item.strip()))
            elif field in BOOLEAN_FIELDS:
                if value not in (True, False, None):
                    raise ContractError(f"SCREENING_INVALID_BOOLEAN:{field}")
                cleaned[field] = value
            else:
                if value is None:
                    value = ""
                if not isinstance(value, str):
                    raise ContractError(f"SCREENING_INVALID_STRING:{field}")
                cleaned[field] = value
        node_ids = set(cleaned["routedNodeOperationalTargetIDs"])
        relation_ids = set(cleaned["routedRelationOperationalTargetIDs"])
        if node_ids - self.node_ids:
            raise ContractError(f"ROUTING_UNKNOWN_OR_NON_NODE_TARGET:{sorted(node_ids - self.node_ids)[0]}")
        if relation_ids - self.relation_ids:
            raise ContractError(f"ROUTING_UNKNOWN_OR_NON_RELATION_TARGET:{sorted(relation_ids - self.relation_ids)[0]}")
        routed = node_ids | relation_ids
        requested_empty = set(cleaned["likelyExhaustiveEmptyTargetIDs"])
        allowed_empty = {
            target_id for target_id in routed
            if self.targets[target_id]["pilotTreatment"] == "extract_and_evaluate"
        }
        cleared = sorted(requested_empty - allowed_empty)
        cleaned["likelyExhaustiveEmptyTargetIDs"] = sorted(requested_empty & allowed_empty)
        if set(cleaned["likelyRecurringDistinctions"]) - set(RECURRING_DISTINCTIONS):
            raise ContractError("SCREENING_UNKNOWN_RECURRING_DISTINCTION")
        return cleaned, cleared

    def _validate_completion(self, cleaned: Mapping[str, Any]) -> None:
        """Require every explicit human judgment needed for reviewed status."""

        if not self.store.reviewer_id():
            raise ContractError("REVIEWER_ID_REQUIRED")
        if not str(cleaned["screeningRationale"]).strip():
            raise ContractError("SCREENING_RATIONALE_REQUIRED")
        if cleaned["expectedAssertionDensity"] not in DENSITIES:
            raise ContractError("SCREENING_ASSERTION_DENSITY_REQUIRED")
        if cleaned["expectedRelationDensity"] not in DENSITIES:
            raise ContractError("SCREENING_RELATION_DENSITY_REQUIRED")
        if cleaned["routingComplexity"] not in ROUTING_COMPLEXITIES:
            raise ContractError("SCREENING_ROUTING_COMPLEXITY_REQUIRED")
        for field in BOOLEAN_FIELDS:
            if cleaned[field] not in (True, False):
                raise ContractError(f"SCREENING_EXPLICIT_BOOLEAN_REQUIRED:{field}")

    def save(self, source_unit_id: str, payload: Mapping[str, Any], mark_reviewed: bool) -> dict[str, Any]:
        """Autosave human fields, optionally completing the unit after validation."""

        if not self.store.reviewer_id():
            raise ContractError("REVIEWER_ID_REQUIRED")
        unit = self.unit(source_unit_id)
        if unit["reviewBlocked"]:
            raise ContractError(str(unit["textValidationError"]))
        cleaned, cleared = self._clean_payload(payload)
        completed = mark_reviewed or bool(unit["draft"].get("completed", False))
        if completed:
            self._validate_completion(cleaned)
        cleaned["screeningReviewerID"] = self.store.reviewer_id()
        saved = self.store.save_draft(source_unit_id, cleaned, completed)
        return {
            "draft": saved,
            "clearedExhaustiveEmptyTargetIDs": cleared,
            "progress": self.progress(),
            "reviewerLocked": self.store.reviewer_locked(),
        }

    def _human_export_values(self, draft: Mapping[str, Any]) -> dict[str, str]:
        """Convert one draft to exact compiler-compatible CSV strings."""

        result = {column: "" for column in self.contracts.human_columns}
        for field in EDITABLE_FIELDS:
            value = draft.get(field, "")
            if field in MULTI_FIELDS:
                result[field] = "|".join(sorted(set(value or [])))
            elif field in BOOLEAN_FIELDS:
                result[field] = "" if value is None else str(bool(value)).lower()
            else:
                result[field] = str(value or "")
        result["screeningReviewerID"] = str(draft.get("screeningReviewerID", ""))
        result["screenedAt"] = str(draft.get("screenedAt", ""))
        result["screeningStatus"] = "reviewed" if draft.get("completed") else ""
        return result

    def _validate_complete_drafts(self, drafts: Mapping[str, Mapping[str, Any]]) -> None:
        """Revalidate every persisted open draft before compiler-ready export."""

        for row in self.contracts.open_rows:
            source_unit_id = row["sourceUnitID"]
            draft = drafts.get(source_unit_id)
            if not draft or not draft.get("completed"):
                raise ContractError(f"COMPLETE_EXPORT_MISSING_REVIEWED_UNIT:{source_unit_id}")
            cleaned, cleared = self._clean_payload({field: draft.get(field) for field in EDITABLE_FIELDS})
            if cleared:
                raise ContractError(f"COMPLETE_EXPORT_INVALID_EXHAUSTIVE_EMPTY:{source_unit_id}")
            self._validate_completion(cleaned)
            if not str(draft.get("screeningReviewerID", "")).strip():
                raise ContractError(f"COMPLETE_EXPORT_REVIEWER_MISSING:{source_unit_id}")
            if draft["screeningReviewerID"] != self.store.reviewer_id():
                raise ContractError(f"COMPLETE_EXPORT_REVIEWER_ATTRIBUTION_MISMATCH:{source_unit_id}")
            screened_at = str(draft.get("screenedAt", ""))
            try:
                parsed = datetime.fromisoformat(screened_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ContractError(f"COMPLETE_EXPORT_INVALID_SCREENED_AT:{source_unit_id}") from exc
            if not screened_at.endswith("Z") or parsed.utcoffset() is None:
                raise ContractError(f"COMPLETE_EXPORT_INVALID_SCREENED_AT:{source_unit_id}")

    def export(self, complete: bool) -> Path:
        """Export all 358 rows without invoking or materializing Block A compilation."""

        if complete and self.dry_run:
            raise ContractError("DRY_RUN_COMPILER_READY_EXPORT_FORBIDDEN")
        drafts = self.store.all_drafts()
        if complete and self.store.completed_count() != OPEN_UNIT_COUNT:
            raise ContractError(f"COMPLETE_EXPORT_REQUIRES_267_REVIEWED:{self.store.completed_count()}")
        if complete:
            self._validate_complete_drafts(drafts)
        output_rows = []
        for canonical in self.contracts.rows:
            row = dict(canonical)
            if is_open(canonical) and canonical["sourceUnitID"] in drafts:
                row.update(self._human_export_values(drafts[canonical["sourceUnitID"]]))
            output_rows.append(row)
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=self.contracts.headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
        timestamp = utc_now()
        if complete:
            filename = "publication_pilot1_screening_worklist_reviewed.csv"
        else:
            stamp = timestamp.replace("-", "").replace(":", "").replace("T", "_").replace("Z", "Z")
            prefix = "publication_pilot1_screening_dry_run" if self.dry_run else "publication_pilot1_screening_worklist"
            filename = f"{prefix}_incomplete_backup_{stamp}.csv"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        path = (self.export_dir / filename).resolve()
        canonical_path = (self.contracts.root / "data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv").resolve()
        if path == canonical_path:
            raise ContractError("CANONICAL_WORKLIST_OVERWRITE_FORBIDDEN")
        content = stream.getvalue().encode("utf-8")
        path.write_bytes(content)
        self.store.record_export("complete" if complete else "partial", timestamp, hashlib.sha256(content).hexdigest())
        return path
