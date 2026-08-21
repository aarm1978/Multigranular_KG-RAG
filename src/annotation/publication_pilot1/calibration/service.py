"""Service layer for isolated Publication Annotation / Calibration Mode."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import (
    ANNOTATION_OUTPUT_SCHEMA_VERSION,
    CONTEXT_POLICY_NAME,
    CONTEXT_POLICY_VERSION,
    GUIDELINE_VERSION,
    HANDBOOK_VERSION,
    INTERFACE_VERSION,
    ROUTING_VERSION,
)
from .contracts import AnnotationContractError, AnnotationContracts
from .store import AnnotationStore
from .validation import DOCUMENT_CONTEXT_REASONS, UNCERTAINTY_CATEGORIES, validate_annotation


def _parse_time(value: str) -> datetime:
    """Parse one stored UTC timestamp."""

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def active_timing_minutes(events: Sequence[Mapping[str, str]]) -> dict[str, float | None]:
    """Derive phase minutes while excluding pauses and technical interruptions.

    This session-level diagnostic neither aggregates annotators nor executes Gate 0.
    """

    exclusions: list[tuple[datetime, datetime]] = []
    open_pause: datetime | None = None
    open_technical: datetime | None = None
    for event in events:
        timestamp = _parse_time(event["timestamp"])
        if event["eventType"] == "pause_started":
            open_pause = timestamp
        elif event["eventType"] == "pause_ended" and open_pause is not None:
            exclusions.append((open_pause, timestamp)); open_pause = None
        elif event["eventType"] == "technical_interruption_started":
            open_technical = timestamp
        elif event["eventType"] == "technical_interruption_ended" and open_technical is not None:
            exclusions.append((open_technical, timestamp)); open_technical = None

    def duration(start_type: str, end_type: str) -> float | None:
        """Sum every completed original/revision phase interval."""

        opened: datetime | None = None
        intervals: list[tuple[datetime, datetime]] = []
        for event in events:
            if event["eventType"] == start_type:
                opened = _parse_time(event["timestamp"])
            elif event["eventType"] == end_type and opened is not None:
                intervals.append((opened, _parse_time(event["timestamp"]))); opened = None
        if not intervals:
            return None
        seconds = 0.0
        for start, end in intervals:
            value = (end - start).total_seconds()
            for excluded_start, excluded_end in exclusions:
                value -= max(0.0, (min(end, excluded_end) - max(start, excluded_start)).total_seconds())
            seconds += max(0.0, value)
        return round(seconds / 60.0, 6)

    result: dict[str, float | None] = {
        "readingMinutes": duration("unit_opened", "reading_complete"),
        "nodePassMinutes": duration("node_pass_started", "node_pass_completed"),
        "relationPassMinutes": duration("relation_pass_started", "relation_pass_completed"),
        "reviewSubmitMinutes": duration("review_started", "submitted"),
    }
    values = [value for value in result.values() if value is not None]
    result["activeAnnotationMinutes"] = round(sum(values), 6) if len(values) == 4 else None
    return result


class AnnotationService:
    """Coordinate effective routes, exact text, validation, timing, revisions, and export."""

    def __init__(self, contracts: AnnotationContracts, store: AnnotationStore, export_dir: Path) -> None:
        """Bind the service to one independent session and state namespace."""

        self.contracts, self.store, self.export_dir = contracts, store, export_dir.resolve()

    def _display_target(self, target_id: str, *, relation: bool) -> dict[str, Any]:
        """Return concise annotator-facing guidance for an effective target."""

        display = self.contracts.displays[target_id]
        target = self.contracts.relation_targets[target_id] if relation else self.contracts.node_targets[target_id]
        value = {
            "operationalTargetID": target_id, "displayLabel": display["displayLabel"],
            "shortDefinition": display["shortDefinition"], "boundaryHint": display["boundaryHint"],
            "displayGroup": display["displayGroup"], "pilotTreatment": target["pilot_treatment"],
        }
        if relation:
            value.update({"direction": target["raw_operational_signature"], "signatures": target["operational_signatures"]})
        else:
            value.update({"allowedActions": list(target["allowed_actions"]), "className": target["formal_classes"][0]["name"]})
        return value

    def bootstrap(self) -> dict[str, Any]:
        """Return bound provenance and this session's non-semantic unit status."""

        summaries = self.store.summaries()
        return {
            "mode": self.contracts.mode, "annotationSessionID": self.store.annotation_session_id,
            "annotatorID": self.store.annotator_id,
            "versions": {
                "interfaceVersion": INTERFACE_VERSION, "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
                "guidelineVersion": GUIDELINE_VERSION, "handbookVersion": HANDBOOK_VERSION,
                "routingVersion": ROUTING_VERSION,
            },
            "units": [{
                "sourceUnitID": unit_id, "sectionTitle": self.contracts.units_by_id[unit_id].get("sectionTitleRaw"),
                "characterCount": int(self.contracts.units_by_id[unit_id]["characterCount"]),
                "status": summaries.get(unit_id, {}).get("status", "not_started"),
            } for unit_id in self.contracts.unit_order],
            "uncertaintyCategories": sorted(UNCERTAINTY_CATEGORIES),
            "contextPolicy": {
                "name": CONTEXT_POLICY_NAME, "version": CONTEXT_POLICY_VERSION,
                "documentSelectionReasons": sorted(DOCUMENT_CONTEXT_REASONS),
            },
        }

    def _context_metadata(self, primary_source_unit_id: str, context_source_unit_id: str) -> dict[str, Any]:
        """Return canonical context metadata without reading source text."""

        primary = self.contracts.units_by_id[primary_source_unit_id]
        context = self.contracts.units_by_id[context_source_unit_id]
        return {
            "sourceUnitID": context_source_unit_id, "sourceUnitTextHash": context["textHash"],
            "canonicalDocumentHash": self.contracts.canonical_document_hash(context_source_unit_id),
            "sectionID": context["sectionID"], "sectionTitle": context.get("sectionTitleRaw"),
            "startOffsetInDocument": int(context["startOffsetInDocument"]),
            "endOffsetInDocument": int(context["endOffsetInDocument"]),
            "contextEligibility": context["eligibility"],
            "authorizationScope": (
                "local_unit" if context_source_unit_id == primary_source_unit_id
                else "section_context" if context["sectionID"] == primary["sectionID"]
                else "document_reconciliation"
            ),
        }

    def _deterministic_endpoints(self, source_unit_id: str) -> list[dict[str, str]]:
        """Expose exact endpoints only from primary and already exposed context units."""

        unit = self.contracts.units_by_id[source_unit_id]
        exposed = self.store.exposed_context_ids(source_unit_id)
        return [{
            "endpointID": f"paper:{unit['paperID']}", "className": "Paper",
            "displayLabel": "Current paper", "artifactID": unit["canonicalArtifactID"],
        }] + [
            {"endpointID": endpoint_id, **endpoint}
            for endpoint_id, endpoint in sorted(self.contracts.deterministic_endpoints(source_unit_id, exposed).items())
        ]

    def _editable(self, draft: Mapping[str, Any] | None) -> dict[str, Any]:
        """Convert stored candidate fields back to simple human controls."""

        if not draft:
            return {"workflowState": "reading", "nodes": [], "relations": [], "targetStates": [], "uncertainties": []}
        evidence = {span["evidenceSpanID"]: span for span in draft.get("evidenceSpans", [])}

        def spans(ids: Sequence[str]) -> list[dict[str, Any]]:
            """Convert referenced canonical spans to editable triples."""

            return [{
                "sourceUnitID": evidence[item]["sourceUnitID"],
                "sourceUnitTextHash": evidence[item]["sourceUnitTextHash"],
                "startOffset": evidence[item]["startOffsetInUnit"], "endOffset": evidence[item]["endOffsetInUnit"],
                "exactText": evidence[item]["evidenceText"],
            } for item in ids]

        return {
            "workflowState": draft.get("workflowState", "reading"),
            "nodes": [{
                "localID": node["candidateID"], "operationalTargetID": node["operationalTargetID"],
                "action": node["action"], "existingNodeID": node.get("existingNodeID"),
                "deferredRecordID": node.get("deferredRecordID"),
                "discoveryScope": node.get("discoveryScope"),
                "distributedEvidenceReason": node.get("distributedEvidenceReason"),
                "mentionSpan": {
                    "sourceUnitID": node["mentionSpan"]["sourceUnitID"],
                    "sourceUnitTextHash": node["mentionSpan"]["sourceUnitTextHash"],
                    "startOffset": node["mentionSpan"]["startOffsetInUnit"],
                    "endOffset": node["mentionSpan"]["endOffsetInUnit"],
                    "exactText": node["mentionSpan"]["exactText"],
                },
                "attributes": [{
                    "attributeName": attribute["attributeName"], "value": attribute["value"],
                    "evidence": spans(attribute["evidenceSpanIDs"]),
                } for attribute in node.get("attributes", [])],
                "evidence": spans(node["evidenceSpanIDs"]),
            } for node in draft.get("nodes", [])],
            "relations": [{
                "localID": edge["candidateID"], "operationalTargetID": edge["operationalRelationID"],
                "sourceEndpointID": edge["source"]["referenceID"], "targetEndpointID": edge["target"]["referenceID"],
                "deferredRecordID": edge.get("deferredRecordID"), "relationScope": edge.get("relationScope"),
                "discoveryScope": edge.get("discoveryScope"),
                "distributedEvidenceReason": edge.get("distributedEvidenceReason"),
                "evidence": spans(edge["evidenceSpanIDs"]),
            } for edge in draft.get("relations", [])],
            "targetStates": list(draft.get("targetStates", [])),
            "uncertainties": [{
                "operationalTargetID": row["operationalTargetID"], "category": row["category"],
                "note": row["note"], "evidence": spans(row["evidenceSpanIDs"]),
            } for row in draft.get("uncertainties", [])],
        }

    def unit(self, source_unit_id: str, *, record_open: bool = True) -> dict[str, Any]:
        """Return exact text and only the effective, untruncated annotation route."""

        if source_unit_id not in self.contracts.unit_order:
            code = "CALIBRATION_NON_MEMBER_UNIT_FORBIDDEN" if self.contracts.mode == "calibration" else "ANNOTATION_SYNTHETIC_UNIT_UNKNOWN"
            raise AnnotationContractError(f"{code}:{source_unit_id}")
        unit, route = self.contracts.units_by_id[source_unit_id], self.contracts.routes_by_id[source_unit_id]
        text = self.contracts.source_text(source_unit_id)
        if record_open and not self.store.timing_events(source_unit_id):
            self.store.log_timing(source_unit_id, str(unit["textHash"]), "unit_opened")
        node_targets = [self._display_target(target_id, relation=False) for target_id in route["eligibleNodeOperationalTargetIDs"]]
        relation_targets = [self._display_target(target_id, relation=True) for target_id in route["eligibleRelationOperationalTargetIDs"]]
        exposed_ids = self.store.exposed_context_ids(source_unit_id)
        context_units = []
        for context_id in self.contracts.authorized_context_ids(source_unit_id, exposed_ids):
            context_units.append({
                **self._context_metadata(source_unit_id, context_id),
                "text": text if context_id == source_unit_id else self.contracts.source_text(context_id),
            })
        draft, timing = self.store.load(source_unit_id), self.store.timing_events(source_unit_id)
        return {
            "metadata": {
                "sourceUnitID": source_unit_id, "sourceUnitTextHash": unit["textHash"],
                "canonicalDocumentHash": self.contracts.canonical_document_hash(source_unit_id),
                "sectionID": unit["sectionID"], "sectionTitle": unit.get("sectionTitleRaw"),
                "sectionRole": unit.get("sectionRole"),
            },
            "text": text, "contextUnits": context_units,
            "sectionContextCandidates": [
                self._context_metadata(source_unit_id, context_id)
                for context_id in self.contracts.context_candidate_ids(source_unit_id, same_section=True)
                if context_id not in exposed_ids
            ],
            "documentContextCandidates": [
                self._context_metadata(source_unit_id, context_id)
                for context_id in self.contracts.context_candidate_ids(source_unit_id, same_section=False)
                if context_id not in exposed_ids
            ],
            "contextExposures": self.store.context_exposures(source_unit_id),
            "contextPolicy": {"name": CONTEXT_POLICY_NAME, "version": CONTEXT_POLICY_VERSION},
            "nodeTargets": node_targets, "relationTargets": relation_targets,
            "deterministicEndpoints": self._deterministic_endpoints(source_unit_id), "editableDraft": self._editable(draft),
            "endpointClassExpansions": self.contracts.class_expansions,
            "persistence": None if draft is None else draft.get("persistence"),
            "timingEvents": timing, "activeTiming": active_timing_minutes(timing),
            "routingDoesNotAssertPresence": True, "effectiveRoutingApplied": True,
        }

    def expose_context(
        self, source_unit_id: str, context_source_unit_id: str, *, context_selection_reason: str,
        operational_target_id: str | None = None, unresolved_assertion_id: str | None = None,
    ) -> dict[str, Any]:
        """Authorize and lazily load exactly one bounded canonical context unit."""

        if source_unit_id not in self.contracts.unit_order:
            raise AnnotationContractError(f"ANNOTATION_CONTEXT_PRIMARY_UNIT_UNKNOWN:{source_unit_id}")
        timing = self.store.timing_events(source_unit_id)
        if not timing or timing[0]["eventType"] != "unit_opened":
            raise AnnotationContractError("ANNOTATION_CONTEXT_PRIMARY_UNIT_NOT_OPEN")
        candidates = set(self.contracts.context_candidate_ids(source_unit_id))
        if context_source_unit_id not in candidates:
            raise AnnotationContractError("ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED")
        current = self.store.load(source_unit_id)
        if current is not None and current.get("persistence", {}).get("status") == "submitted":
            raise AnnotationContractError("ANNOTATION_SUBMITTED_RECORD_REOPEN_REQUIRED")
        primary = self.contracts.units_by_id[source_unit_id]
        context = self.contracts.units_by_id[context_source_unit_id]
        same_section = context["sectionID"] == primary["sectionID"]
        binding_type: str | None = None; binding_id: str | None = None
        if same_section:
            if context_selection_reason != "same_section_context" or operational_target_id or unresolved_assertion_id:
                raise AnnotationContractError("ANNOTATION_SECTION_CONTEXT_REQUEST_INVALID")
            context_scope = "section_context"
        else:
            if context_selection_reason not in DOCUMENT_CONTEXT_REASONS:
                raise AnnotationContractError("ANNOTATION_DOCUMENT_CONTEXT_REASON_INVALID")
            if bool(operational_target_id) == bool(unresolved_assertion_id):
                raise AnnotationContractError("ANNOTATION_DOCUMENT_CONTEXT_TASK_BINDING_REQUIRED")
            route = self.contracts.routes_by_id[source_unit_id]
            routed = set(route["eligibleNodeOperationalTargetIDs"]) | set(route["eligibleRelationOperationalTargetIDs"])
            if operational_target_id:
                if operational_target_id not in routed:
                    raise AnnotationContractError("ANNOTATION_DOCUMENT_CONTEXT_TARGET_NOT_ROUTED")
                binding_type, binding_id = "operational_target", operational_target_id
            else:
                draft_ids = {
                    str(row.get("candidateID")) for key in ("nodes", "relations")
                    for row in (current or {}).get(key, []) if isinstance(row, Mapping)
                }
                if unresolved_assertion_id not in draft_ids:
                    raise AnnotationContractError("ANNOTATION_DOCUMENT_CONTEXT_ASSERTION_NOT_FOUND")
                binding_type, binding_id = "unresolved_assertion", unresolved_assertion_id
            context_scope = "document_reconciliation"
        context_text = self.contracts.source_text(context_source_unit_id)
        exposure = self.store.log_context_exposure(
            source_unit_id, context_source_unit_id, context_scope, context_selection_reason,
            task_binding_type=binding_type, task_binding_id=binding_id,
        )
        return {
            "contextUnit": {**self._context_metadata(source_unit_id, context_source_unit_id), "text": context_text},
            "exposure": exposure, "deterministicEndpoints": self._deterministic_endpoints(source_unit_id),
        }

    def save(self, source_unit_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Backend-validate and append an autosave revision."""

        normalized = validate_annotation(
            self.contracts, source_unit_id, payload,
            annotation_session_id=self.store.annotation_session_id, annotator_id=self.store.annotator_id,
            context_exposures=self.store.context_exposures(source_unit_id),
        )
        return self.store.save(source_unit_id, normalized)

    def timing(self, source_unit_id: str, event_type: str) -> dict[str, Any]:
        """Append one fully bound timing event."""

        if source_unit_id not in self.contracts.unit_order:
            raise AnnotationContractError(f"ANNOTATION_TIMING_UNIT_UNKNOWN:{source_unit_id}")
        unit = self.contracts.units_by_id[source_unit_id]
        event = self.store.log_timing(source_unit_id, str(unit["textHash"]), event_type)
        events = self.store.timing_events(source_unit_id)
        return {"event": event, "events": events, "activeTiming": active_timing_minutes(events)}

    def submit(self, source_unit_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Validate completeness, close timing, and freeze a submission snapshot."""

        normalized = validate_annotation(
            self.contracts, source_unit_id, payload,
            annotation_session_id=self.store.annotation_session_id, annotator_id=self.store.annotator_id,
            require_complete=True, context_exposures=self.store.context_exposures(source_unit_id),
        )
        normalized["workflowState"] = "submitted"
        self.timing(source_unit_id, "submitted")
        return self.store.submit(source_unit_id, normalized)

    def reopen(self, source_unit_id: str, reason: str) -> dict[str, Any]:
        """Audit a reopen and start a new timed node/revision pass."""

        current = self.store.load(source_unit_id)
        if current is None or current.get("persistence", {}).get("status") != "submitted":
            raise AnnotationContractError("ANNOTATION_REOPEN_REQUIRES_SUBMITTED_RECORD")
        if not reason.strip():
            raise AnnotationContractError("ANNOTATION_REOPEN_REASON_REQUIRED")
        self.timing(source_unit_id, "node_pass_started")
        return self.store.reopen(source_unit_id, reason)

    def export(self) -> Path:
        """Revalidate current records and write a deterministic explicit export."""

        payload = self.store.export_payload()
        for row in payload["annotations"]:
            validate_annotation(
                self.contracts, row["sourceUnitID"], self._editable(row["annotation"]),
                annotation_session_id=self.store.annotation_session_id, annotator_id=self.store.annotator_id,
                require_complete=row["status"] == "submitted",
                context_exposures=self.store.context_exposures(row["sourceUnitID"]),
            )
        self.export_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in self.store.annotation_session_id)
        path = self.export_dir / f"{safe}.annotation.json"
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        path.write_bytes(encoded)
        path.with_suffix(".annotation.sha256").write_text(hashlib.sha256(encoded).hexdigest() + "\n", encoding="utf-8")
        return path
