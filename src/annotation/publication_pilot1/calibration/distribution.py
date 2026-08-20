"""Package, export, validate, and import independent calibration annotations.

SQLite remains local working state.  Exchange and researcher import use immutable,
checksum-bound ZIP bundles containing only deterministic JSON/JSONL records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator

from ..contracts import sha256_file
from . import (
    ANNOTATION_OUTPUT_SCHEMA_VERSION,
    CONTEXT_POLICY_NAME,
    CONTEXT_POLICY_VERSION,
    GUIDELINE_VERSION,
    HANDBOOK_VERSION,
    INTERFACE_VERSION,
    ROUTING_VERSION,
)
from .contracts import (
    ACTIVATION_SCHEMA_VERSION,
    CALIBRATION_ID_ORDER_HASH,
    ANNOTATION_MVP_BASE_CHECKPOINT,
    AnnotationContractError,
    AnnotationContracts,
    canonical_json_hash,
    load_annotation_contracts,
    production_activation_payload,
    verify_production_activation,
)
from .service import AnnotationService, active_timing_minutes
from .store import TIMING_EVENTS


BUNDLE_SCHEMA_VERSION = "0.1.0"
PACKAGE_SCHEMA_VERSION = "0.1.0"
BUNDLE_FILES = (
    "activation.json", "manifest.json", "annotations.jsonl", "timing_events.jsonl",
    "context_exposures.jsonl", "revision_audit.json", "checksums.json",
)


def _json_bytes(value: object) -> bytes:
    """Serialize deterministic readable JSON with one trailing newline."""

    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    """Serialize deterministic compact JSON Lines."""

    return b"".join(
        json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        for row in rows
    )


def _sha256(data: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(data).hexdigest()


def _safe_identity(value: str, code: str) -> str:
    """Validate a stable identity suitable for records and local filenames."""

    cleaned = value.strip()
    if not cleaned or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in cleaned):
        raise AnnotationContractError(code)
    return cleaned


def write_activation(
    root: Path, annotator_id: str, annotation_session_id: str, output: Path, *,
    package_build_checkpoint: str | None = None,
) -> Path:
    """Write one deterministic researcher-issued production activation without state."""

    root = root.resolve()
    build_checkpoint = package_build_checkpoint or _git_build_checkpoint(root)
    payload = production_activation_payload(
        root.resolve(), _safe_identity(annotator_id, "CALIBRATION_ACTIVATION_ANNOTATOR_ID_INVALID"),
        _safe_identity(annotation_session_id, "CALIBRATION_ACTIVATION_SESSION_ID_INVALID"),
        package_build_checkpoint=build_checkpoint,
    )
    output = output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    encoded = _json_bytes(payload)
    if output.exists() and output.read_bytes() != encoded:
        raise AnnotationContractError("CALIBRATION_ACTIVATION_OUTPUT_EXISTS_CONFLICT")
    if not output.exists():
        output.write_bytes(encoded)
    os.chmod(output, 0o600)
    return output


def synthetic_activation_payload(
    contracts: AnnotationContracts, annotator_id: str, annotation_session_id: str,
) -> dict[str, Any]:
    """Build a discarded activation-shaped binding for synthetic round-trip tests."""

    annotator = _safe_identity(annotator_id, "CALIBRATION_ACTIVATION_ANNOTATOR_ID_INVALID")
    session = _safe_identity(annotation_session_id, "CALIBRATION_ACTIVATION_SESSION_ID_INVALID")
    return {
        "activationSchemaVersion": ACTIVATION_SCHEMA_VERSION, "activation": "SYNTHETIC_DISCARDED_ACTIVATION",
        "mode": "synthetic", "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
        "packageBuildCheckpoint": "0" * 40,
        "annotatorID": annotator, "annotationSessionID": session,
        "interfaceVersion": INTERFACE_VERSION, "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
        "guidelineVersion": GUIDELINE_VERSION,
        "guidelineHash": contracts.hashes["docs/publication_annotation_adjudication_guidelines.md"],
        "handbookVersion": HANDBOOK_VERSION,
        "routingVersion": ROUTING_VERSION, "contextPolicyName": CONTEXT_POLICY_NAME,
        "contextPolicyVersion": CONTEXT_POLICY_VERSION, "calibrationCount": len(contracts.unit_order),
        "calibrationManifestVersion": "synthetic-discarded-v1",
        "calibrationIdentityOrderHash": canonical_json_hash(list(contracts.unit_order)),
        "sourceUnitInventoryHash": contracts.hashes["data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"],
        "calibrationManifestHash": contracts.hashes["data/curation/papers/pilot1/publication_pilot1_calibration_manifest.json"],
        "routingHash": contracts.hashes["data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl"],
        "gate0PolicyHash": contracts.hashes["data/curation/papers/pilot1/publication_pilot1_gate0_policy.yaml"],
        "annotationSchemaHash": sha256_file(contracts.root / "schemas/publication_pilot1_annotation_record.schema.json"),
        "handbookHash": sha256_file(contracts.root / "docs/publication_pilot1_annotation_calibration_handbook.md"),
    }


def _validate_activation_payload(
    payload: Mapping[str, Any], contracts: AnnotationContracts, *, expected_annotator_id: str | None = None,
) -> None:
    """Validate production or discarded activation bindings without creating state."""

    if payload.get("mode") == "calibration":
        expected = production_activation_payload(
            contracts.root, str(payload.get("annotatorID", "")), str(payload.get("annotationSessionID", "")),
            package_build_checkpoint=str(payload.get("packageBuildCheckpoint", "")),
        )
    elif payload.get("mode") == "synthetic":
        expected = synthetic_activation_payload(
            contracts, str(payload.get("annotatorID", "")), str(payload.get("annotationSessionID", ""))
        )
    else:
        raise AnnotationContractError("CALIBRATION_ACTIVATION_MODE_INVALID")
    if dict(payload) != expected:
        raise AnnotationContractError("CALIBRATION_ACTIVATION_BINDING_MISMATCH")
    if expected_annotator_id is not None and payload["annotatorID"] != expected_annotator_id:
        raise AnnotationContractError("CALIBRATION_ACTIVATION_ANNOTATOR_MISMATCH")


def _validate_timing_rows(
    rows: Sequence[Mapping[str, Any]], contracts: AnnotationContracts, *, annotator_id: str, annotation_session_id: str,
    required_unit_ids: set[str], require_submitted: bool,
) -> None:
    """Validate independent timing identities, ordering, exclusions, and completion."""

    by_unit: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        unit_id = str(row.get("sourceUnitID", ""))
        if unit_id not in required_unit_ids:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_UNIT_INVALID:{unit_id}")
        if row.get("annotatorID") != annotator_id or row.get("annotationSessionID") != annotation_session_id:
            raise AnnotationContractError("CALIBRATION_BUNDLE_TIMING_IDENTITY_MISMATCH")
        if row.get("sourceUnitTextHash") != contracts.units_by_id[unit_id]["textHash"]:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_SOURCE_HASH_MISMATCH:{unit_id}")
        if row.get("interfaceVersion") != INTERFACE_VERSION or row.get("guidelineVersion") != GUIDELINE_VERSION:
            raise AnnotationContractError("CALIBRATION_BUNDLE_TIMING_VERSION_MISMATCH")
        if row.get("handbookVersion") != HANDBOOK_VERSION or row.get("routingVersion") != ROUTING_VERSION:
            raise AnnotationContractError("CALIBRATION_BUNDLE_TIMING_VERSION_MISMATCH")
        if row.get("eventType") not in TIMING_EVENTS:
            raise AnnotationContractError("CALIBRATION_BUNDLE_TIMING_EVENT_UNKNOWN")
        by_unit.setdefault(unit_id, []).append(row)
    if require_submitted and set(by_unit) != required_unit_ids:
        raise AnnotationContractError("CALIBRATION_BUNDLE_TIMING_UNIT_COVERAGE_MISMATCH")
    initial_sequence = (
        "unit_opened", "reading_complete", "node_pass_started", "node_pass_completed",
        "relation_pass_started", "relation_pass_completed", "review_started", "submitted",
    )
    revision_sequence = initial_sequence[2:]
    for unit_id, events in by_unit.items():
        timestamps = [str(event.get("timestamp", "")) for event in events]
        try:
            parsed = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in timestamps]
        except ValueError as exc:
            raise AnnotationContractError("CALIBRATION_BUNDLE_TIMING_TIMESTAMP_INVALID") from exc
        if any(value.tzinfo is None or value.utcoffset() != timedelta(0) for value in parsed):
            raise AnnotationContractError("CALIBRATION_BUNDLE_TIMING_TIMESTAMP_INVALID")
        if parsed != sorted(parsed):
            raise AnnotationContractError("CALIBRATION_BUNDLE_TIMING_ORDER_INVALID")
        main = [event.get("eventType") for event in events if event.get("eventType") in initial_sequence]
        prefix_length = min(len(main), len(initial_sequence))
        if tuple(main[:prefix_length]) != initial_sequence[:prefix_length]:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_SUBMISSION_SEQUENCE_INVALID:{unit_id}")
        remainder = main[len(initial_sequence):]
        while remainder:
            cycle = remainder[:len(revision_sequence)]
            if tuple(cycle) != revision_sequence[:len(cycle)]:
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_SUBMISSION_SEQUENCE_INVALID:{unit_id}")
            remainder = remainder[len(cycle):]
        if require_submitted and (not main or main[-1] != "submitted"):
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_SUBMISSION_SEQUENCE_INVALID:{unit_id}")
        exclusion: str | None = None; last_main: str | None = None
        for event in events:
            event_type = event.get("eventType")
            if event_type in {"pause_started", "technical_interruption_started"}:
                if exclusion is not None or last_main is None or last_main == "submitted":
                    raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_EXCLUSION_SEQUENCE_INVALID:{unit_id}")
                exclusion = str(event_type).removesuffix("_started")
            elif event_type in {"pause_ended", "technical_interruption_ended"}:
                expected = str(event_type).removesuffix("_ended")
                if exclusion != expected:
                    raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_EXCLUSION_SEQUENCE_INVALID:{unit_id}")
                exclusion = None
            elif exclusion is not None:
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_PHASE_DURING_EXCLUSION:{unit_id}")
            else:
                last_main = str(event_type)
        if exclusion is not None:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_TIMING_EXCLUSION_UNCLOSED:{unit_id}")
        if require_submitted and active_timing_minutes(events).get("activeAnnotationMinutes") is None:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_ACTIVE_TIME_INCOMPLETE:{unit_id}")


def _validate_annotation_records(
    rows: Sequence[Mapping[str, Any]], contracts: AnnotationContracts, *, annotator_id: str,
    annotation_session_id: str, required_unit_ids: set[str], require_submitted: bool,
) -> None:
    """Validate schema, calibration membership, hashes, identities, and submitted state."""

    schema = json.loads((contracts.root / "schemas/publication_pilot1_annotation_record.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema); validator = Draft202012Validator(schema)
    seen: set[str] = set()
    for row in rows:
        unit_id = str(row.get("sourceUnitID", ""))
        if unit_id in seen:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_DUPLICATE_ANNOTATION:{unit_id}")
        if unit_id not in required_unit_ids:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_NON_MEMBER_UNIT:{unit_id}")
        annotation = row.get("annotation")
        errors = sorted(validator.iter_errors(annotation), key=lambda error: list(error.path)) if isinstance(annotation, Mapping) else [None]
        if errors:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_ANNOTATION_SCHEMA_INVALID:{unit_id}")
        unit = contracts.units_by_id[unit_id]
        if annotation["sourceUnitID"] != unit_id or annotation["primarySourceUnitID"] != unit_id:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_PRIMARY_UNIT_MISMATCH:{unit_id}")
        if annotation["annotatorID"] != annotator_id or annotation["annotationSessionID"] != annotation_session_id:
            raise AnnotationContractError("CALIBRATION_BUNDLE_ANNOTATION_IDENTITY_MISMATCH")
        if annotation["sourceUnitTextHash"] != unit["textHash"]:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_SOURCE_HASH_MISMATCH:{unit_id}")
        if annotation["canonicalDocumentHash"] != contracts.canonical_document_hash(unit_id):
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_DOCUMENT_HASH_MISMATCH:{unit_id}")
        authorized_ids: set[str] = set()
        for binding in annotation["authorizedContextUnits"]:
            context_id = str(binding["sourceUnitID"])
            if context_id not in contracts.units_by_id or context_id in authorized_ids:
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_CONTEXT_BINDING_INVALID:{context_id}")
            context = contracts.units_by_id[context_id]
            expected_binding = {
                "sourceUnitTextHash": context["textHash"],
                "canonicalDocumentHash": contracts.canonical_document_hash(context_id),
                "sectionID": context["sectionID"],
                "startOffsetInDocument": int(context["startOffsetInDocument"]),
                "endOffsetInDocument": int(context["endOffsetInDocument"]),
            }
            if any(binding.get(key) != value for key, value in expected_binding.items()):
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_CONTEXT_BINDING_DRIFT:{context_id}")
            authorized_ids.add(context_id)
        if unit_id not in authorized_ids or set(annotation["contextSourceUnitIDs"]) != authorized_ids - {unit_id}:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_CONTEXT_BINDING_SET_MISMATCH:{unit_id}")
        for span in annotation["evidenceSpans"]:
            context_id = str(span["sourceUnitID"])
            if context_id not in authorized_ids:
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_EVIDENCE_CONTEXT_UNAUTHORIZED:{context_id}")
            context = contracts.units_by_id[context_id]; text = contracts.source_text(context_id)
            start, end = int(span["startOffsetInUnit"]), int(span["endOffsetInUnit"])
            exact = span["evidenceText"]
            expected_span = {
                "sourceArtifactID": context["canonicalArtifactID"], "sourceUnitTextHash": context["textHash"],
                "canonicalDocumentHash": contracts.canonical_document_hash(context_id), "sectionID": context["sectionID"],
                "startOffsetInDocument": int(context["startOffsetInDocument"]) + start,
                "endOffsetInDocument": int(context["startOffsetInDocument"]) + end,
                "evidenceHash": hashlib.sha256(exact.encode("utf-8")).hexdigest(),
            }
            if start < 0 or end <= start or end > len(text) or text[start:end] != exact:
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_EVIDENCE_SLICE_MISMATCH:{context_id}")
            if any(span.get(key) != value for key, value in expected_span.items()):
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_EVIDENCE_BINDING_DRIFT:{context_id}")
            document = contracts.canonical_document_text(context_id)
            if document[expected_span["startOffsetInDocument"]:expected_span["endOffsetInDocument"]] != exact:
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_EVIDENCE_DOCUMENT_SLICE_MISMATCH:{context_id}")
        if require_submitted and (row.get("status") != "submitted" or annotation["workflowState"] != "submitted"):
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_ANNOTATION_NOT_SUBMITTED:{unit_id}")
        seen.add(unit_id)
    if require_submitted and seen != required_unit_ids:
        raise AnnotationContractError("CALIBRATION_BUNDLE_ANNOTATION_UNIT_COVERAGE_MISMATCH")


def build_export_bundle(
    service: AnnotationService, activation: Mapping[str, Any], output: Path, *, gate0_ready: bool,
) -> Path:
    """Write an immutable deterministic session exchange bundle, never a SQLite database."""

    contracts = service.contracts; store = service.store
    _validate_activation_payload(activation, contracts, expected_annotator_id=store.annotator_id)
    if activation["annotationSessionID"] != store.annotation_session_id:
        raise AnnotationContractError("CALIBRATION_ACTIVATION_SESSION_MISMATCH")
    state = store.export_payload(); required = set(contracts.unit_order)
    order = {source_unit_id: index for index, source_unit_id in enumerate(contracts.unit_order)}
    annotations = sorted(state["annotations"], key=lambda row: order[row["sourceUnitID"]])
    require_complete = bool(gate0_ready)
    _validate_annotation_records(
        annotations, contracts, annotator_id=store.annotator_id,
        annotation_session_id=store.annotation_session_id, required_unit_ids=required,
        require_submitted=require_complete,
    )
    _validate_timing_rows(
        state["timingEvents"], contracts, annotator_id=store.annotator_id,
        annotation_session_id=store.annotation_session_id, required_unit_ids=required,
        require_submitted=require_complete,
    )
    status = "partial" if not gate0_ready else ("gate0_ready" if contracts.mode == "calibration" else "synthetic_complete")
    included = [row["sourceUnitID"] for row in annotations]
    manifest = {
        "bundleSchemaVersion": BUNDLE_SCHEMA_VERSION, "status": status, "mode": contracts.mode,
        "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
        "packageBuildCheckpoint": activation["packageBuildCheckpoint"], "annotatorID": store.annotator_id,
        "annotationSessionIDs": [store.annotation_session_id],
        "interfaceVersion": INTERFACE_VERSION, "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
        "guidelineVersion": GUIDELINE_VERSION, "guidelineHash": activation["guidelineHash"],
        "handbookVersion": HANDBOOK_VERSION,
        "routingVersion": ROUTING_VERSION, "contextPolicyName": CONTEXT_POLICY_NAME,
        "contextPolicyVersion": CONTEXT_POLICY_VERSION, "calibrationCount": len(contracts.unit_order),
        "calibrationManifestVersion": activation["calibrationManifestVersion"],
        "calibrationSourceUnitIDs": list(contracts.unit_order),
        "calibrationIdentityOrderHash": canonical_json_hash(list(contracts.unit_order)),
        "includedSourceUnitIDs": included, "activationHash": canonical_json_hash(dict(activation)),
        "sourceUnitInventoryHash": activation["sourceUnitInventoryHash"],
        "calibrationManifestHash": activation["calibrationManifestHash"],
        "routingHash": activation["routingHash"], "gate0PolicyHash": activation["gate0PolicyHash"],
        "annotationSchemaHash": activation["annotationSchemaHash"], "handbookHash": activation["handbookHash"],
    }
    revision_audit = {
        "revisions": state["revisions"], "submissions": state["submissions"],
        "auditActions": state["auditActions"],
    }
    content = {
        "activation.json": _json_bytes(dict(activation)), "manifest.json": _json_bytes(manifest),
        "annotations.jsonl": _jsonl_bytes(annotations),
        "timing_events.jsonl": _jsonl_bytes(state["timingEvents"]),
        "context_exposures.jsonl": _jsonl_bytes(state["contextExposures"]),
        "revision_audit.json": _json_bytes(revision_audit),
    }
    checksums = {name: _sha256(data) for name, data in sorted(content.items())}
    content["checksums.json"] = _json_bytes({"algorithm": "SHA-256", "files": checksums})
    output = output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in BUNDLE_FILES:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.external_attr = 0o100600 << 16
            info.compress_type = zipfile.ZIP_DEFLATED; archive.writestr(info, content[name])
    if output.exists():
        if output.read_bytes() == temporary.read_bytes():
            temporary.unlink(); return output
        temporary.unlink()
        raise AnnotationContractError("CALIBRATION_BUNDLE_OUTPUT_EXISTS_CONFLICT")
    os.replace(temporary, output); os.chmod(output, 0o600)
    return output


def _read_bundle(path: Path) -> tuple[dict[str, bytes], str]:
    """Read an exact safe bundle file set and verify every declared checksum."""

    data = path.read_bytes(); bundle_hash = _sha256(data)
    try:
        with zipfile.ZipFile(path) as archive:
            if tuple(sorted(archive.namelist())) != tuple(sorted(BUNDLE_FILES)):
                raise AnnotationContractError("CALIBRATION_BUNDLE_FILE_SET_INVALID")
            files = {name: archive.read(name) for name in BUNDLE_FILES}
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise AnnotationContractError("CALIBRATION_BUNDLE_ZIP_INVALID") from exc
    checksums = json.loads(files["checksums.json"])
    if checksums.get("algorithm") != "SHA-256" or set(checksums.get("files", {})) != set(BUNDLE_FILES) - {"checksums.json"}:
        raise AnnotationContractError("CALIBRATION_BUNDLE_CHECKSUM_MANIFEST_INVALID")
    for name, expected in checksums["files"].items():
        if _sha256(files[name]) != expected:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_CHECKSUM_MISMATCH:{name}")
    return files, bundle_hash


def _jsonl(data: bytes, code: str) -> list[dict[str, Any]]:
    """Parse a UTF-8 JSONL payload into objects."""

    try:
        rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnnotationContractError(code) from exc
    if any(not isinstance(row, dict) for row in rows):
        raise AnnotationContractError(code)
    return rows


def validate_export_bundle(
    path: Path, contracts: AnnotationContracts, *, require_gate0_ready: bool,
) -> dict[str, Any]:
    """Independently validate one immutable annotator bundle without modifying it."""

    files, bundle_hash = _read_bundle(path)
    try:
        activation = json.loads(files["activation.json"]); manifest = json.loads(files["manifest.json"])
        revision_audit = json.loads(files["revision_audit.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnnotationContractError("CALIBRATION_BUNDLE_JSON_INVALID") from exc
    _validate_activation_payload(activation, contracts)
    expected_status = "gate0_ready" if contracts.mode == "calibration" else "synthetic_complete"
    if require_gate0_ready and manifest.get("status") != expected_status:
        raise AnnotationContractError("CALIBRATION_BUNDLE_NOT_GATE0_READY")
    if manifest.get("status") not in {"partial", expected_status}:
        raise AnnotationContractError("CALIBRATION_BUNDLE_STATUS_INVALID")
    required = set(contracts.unit_order); ordered = list(contracts.unit_order)
    expected_manifest = {
        "bundleSchemaVersion": BUNDLE_SCHEMA_VERSION, "mode": contracts.mode,
        "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
        "packageBuildCheckpoint": activation["packageBuildCheckpoint"], "interfaceVersion": INTERFACE_VERSION,
        "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION, "guidelineVersion": GUIDELINE_VERSION,
        "guidelineHash": activation["guidelineHash"],
        "handbookVersion": HANDBOOK_VERSION, "routingVersion": ROUTING_VERSION,
        "contextPolicyName": CONTEXT_POLICY_NAME, "contextPolicyVersion": CONTEXT_POLICY_VERSION,
        "calibrationCount": len(ordered), "calibrationManifestVersion": activation["calibrationManifestVersion"],
        "calibrationSourceUnitIDs": ordered,
        "calibrationIdentityOrderHash": canonical_json_hash(ordered),
        "activationHash": canonical_json_hash(activation),
    }
    for key, value in expected_manifest.items():
        if manifest.get(key) != value:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_MANIFEST_BINDING_MISMATCH:{key}")
    if manifest.get("annotatorID") != activation["annotatorID"] or manifest.get("annotationSessionIDs") != [activation["annotationSessionID"]]:
        raise AnnotationContractError("CALIBRATION_BUNDLE_MANIFEST_IDENTITY_MISMATCH")
    for key in (
        "sourceUnitInventoryHash", "calibrationManifestHash", "routingHash", "gate0PolicyHash", "guidelineHash",
        "annotationSchemaHash", "handbookHash",
    ):
        if manifest.get(key) != activation[key]:
            raise AnnotationContractError(f"CALIBRATION_BUNDLE_MANIFEST_BINDING_MISMATCH:{key}")
    annotations = _jsonl(files["annotations.jsonl"], "CALIBRATION_BUNDLE_ANNOTATIONS_JSONL_INVALID")
    timing = _jsonl(files["timing_events.jsonl"], "CALIBRATION_BUNDLE_TIMING_JSONL_INVALID")
    exposures = _jsonl(files["context_exposures.jsonl"], "CALIBRATION_BUNDLE_CONTEXT_JSONL_INVALID")
    included = [row.get("sourceUnitID") for row in annotations]
    if manifest.get("includedSourceUnitIDs") != included:
        raise AnnotationContractError("CALIBRATION_BUNDLE_INCLUDED_UNIT_ORDER_MISMATCH")
    complete = manifest.get("status") == expected_status
    _validate_annotation_records(
        annotations, contracts, annotator_id=activation["annotatorID"],
        annotation_session_id=activation["annotationSessionID"], required_unit_ids=required,
        require_submitted=complete,
    )
    _validate_timing_rows(
        timing, contracts, annotator_id=activation["annotatorID"], annotation_session_id=activation["annotationSessionID"],
        required_unit_ids=required, require_submitted=complete,
    )
    revisions = revision_audit.get("revisions", [])
    submissions = revision_audit.get("submissions", [])
    actions = revision_audit.get("auditActions", [])
    if not all(isinstance(rows, list) for rows in (revisions, submissions, actions)):
        raise AnnotationContractError("CALIBRATION_BUNDLE_REVISION_AUDIT_INVALID")
    revision_keys: set[tuple[str, int]] = set()
    revision_ids: set[int] = set()
    revision_by_key: dict[tuple[str, int], Mapping[str, Any]] = {}
    for revision in revisions:
        if not isinstance(revision, Mapping):
            raise AnnotationContractError("CALIBRATION_BUNDLE_REVISION_AUDIT_INVALID")
        key = (str(revision.get("sourceUnitID", "")), int(revision.get("revisionNumber", 0)))
        if key[0] not in required or key[1] < 1 or key in revision_keys:
            raise AnnotationContractError("CALIBRATION_BUNDLE_REVISION_CONFLICT")
        if not isinstance(revision.get("annotation"), Mapping):
            raise AnnotationContractError("CALIBRATION_BUNDLE_REVISION_AUDIT_INVALID")
        revision_id = int(revision.get("revisionID", 0))
        if revision_id < 1 or revision_id in revision_ids:
            raise AnnotationContractError("CALIBRATION_BUNDLE_REVISION_CONFLICT")
        _validate_annotation_records(
            [{"sourceUnitID": key[0], "annotation": revision["annotation"]}], contracts,
            annotator_id=activation["annotatorID"], annotation_session_id=activation["annotationSessionID"],
            required_unit_ids=required, require_submitted=False,
        )
        revision_ids.add(revision_id)
        revision_keys.add(key); revision_by_key[key] = revision
    submission_keys: set[tuple[str, int]] = set()
    submission_ids: set[int] = set()
    for submission in submissions:
        if not isinstance(submission, Mapping):
            raise AnnotationContractError("CALIBRATION_BUNDLE_REVISION_AUDIT_INVALID")
        key = (str(submission.get("sourceUnitID", "")), int(submission.get("revisionNumber", 0)))
        if key not in revision_keys or key in submission_keys or not isinstance(submission.get("annotation"), Mapping):
            raise AnnotationContractError("CALIBRATION_BUNDLE_SUBMISSION_REVISION_INVALID")
        submission_id = int(submission.get("submissionID", 0))
        if submission_id < 1 or submission_id in submission_ids:
            raise AnnotationContractError("CALIBRATION_BUNDLE_SUBMISSION_REVISION_INVALID")
        if submission["annotation"] != revision_by_key[key]["annotation"]:
            raise AnnotationContractError("CALIBRATION_BUNDLE_SUBMISSION_PAYLOAD_MISMATCH")
        submission_ids.add(submission_id); submission_keys.add(key)
    for action in actions:
        if not isinstance(action, Mapping) or action.get("source_unit_id") not in required:
            raise AnnotationContractError("CALIBRATION_BUNDLE_AUDIT_ACTION_INVALID")
    if complete:
        submitted_units = {row.get("sourceUnitID") for row in submissions}
        if submitted_units != required:
            raise AnnotationContractError("CALIBRATION_BUNDLE_SUBMISSION_COVERAGE_MISMATCH")
        for row in annotations:
            key = (str(row["sourceUnitID"]), int(row["revisionNumber"]))
            matching = next((item for item in submissions if (item["sourceUnitID"], item["revisionNumber"]) == key), None)
            if matching is None or matching["annotation"] != row["annotation"]:
                raise AnnotationContractError(f"CALIBRATION_BUNDLE_CURRENT_SUBMISSION_MISMATCH:{row['sourceUnitID']}")
    for exposure in exposures:
        if exposure.get("primarySourceUnitID") not in required:
            raise AnnotationContractError("CALIBRATION_BUNDLE_CONTEXT_PRIMARY_INVALID")
        if exposure.get("contextPolicyName") != CONTEXT_POLICY_NAME or exposure.get("contextPolicyVersion") != CONTEXT_POLICY_VERSION:
            raise AnnotationContractError("CALIBRATION_BUNDLE_CONTEXT_VERSION_MISMATCH")
    if complete:
        embedded = [
            exposure for row in annotations for exposure in row["annotation"].get("contextExposureEvents", [])
        ]
        if sorted(embedded, key=lambda row: row["exposureID"]) != exposures:
            raise AnnotationContractError("CALIBRATION_BUNDLE_CONTEXT_EXPOSURE_SNAPSHOT_MISMATCH")
    return {
        "path": str(path.resolve()), "bundleSHA256": bundle_hash, "manifest": manifest,
        "activation": activation, "annotations": annotations, "timingEvents": timing,
        "contextExposures": exposures, "revisionAudit": revision_audit,
    }


def import_validated_bundles(
    bundle_paths: Sequence[Path], contracts: AnnotationContracts, master_database: Path, *,
    require_gate0_ready: bool = True,
) -> Path:
    """Validate independent bundles and derive a provenance-preserving master SQLite index."""

    if len(bundle_paths) < 1:
        raise AnnotationContractError("CALIBRATION_IMPORT_BUNDLE_REQUIRED")
    validated = [validate_export_bundle(path, contracts, require_gate0_ready=require_gate0_ready) for path in bundle_paths]
    annotators = [row["activation"]["annotatorID"] for row in validated]
    sessions = [row["activation"]["annotationSessionID"] for row in validated]
    if len(set(annotators)) != len(annotators):
        raise AnnotationContractError("CALIBRATION_IMPORT_ANNOTATOR_IDS_NOT_DISTINCT")
    if len(set(sessions)) != len(sessions):
        raise AnnotationContractError("CALIBRATION_IMPORT_SESSION_IDS_NOT_INDEPENDENT")
    assignments = [row["manifest"]["calibrationSourceUnitIDs"] for row in validated]
    if any(assignment != assignments[0] for assignment in assignments[1:]):
        raise AnnotationContractError("CALIBRATION_IMPORT_ASSIGNMENT_MISMATCH")
    master_database = master_database.resolve(); master_database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(master_database)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS bundles(
                bundle_sha256 TEXT PRIMARY KEY, source_path TEXT NOT NULL, annotator_id TEXT NOT NULL UNIQUE,
                annotation_session_id TEXT NOT NULL UNIQUE, status TEXT NOT NULL, imported_at TEXT NOT NULL,
                manifest_json TEXT NOT NULL, activation_json TEXT NOT NULL,
                revision_audit_json TEXT NOT NULL, validation_result TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS annotations(
                bundle_sha256 TEXT NOT NULL, source_unit_id TEXT NOT NULL, annotation_json TEXT NOT NULL,
                PRIMARY KEY(bundle_sha256, source_unit_id)
            );
            CREATE TABLE IF NOT EXISTS timing_events(
                bundle_sha256 TEXT NOT NULL, event_index INTEGER NOT NULL, event_json TEXT NOT NULL,
                PRIMARY KEY(bundle_sha256, event_index)
            );
            CREATE TABLE IF NOT EXISTS context_exposures(
                bundle_sha256 TEXT NOT NULL, exposure_index INTEGER NOT NULL, exposure_json TEXT NOT NULL,
                PRIMARY KEY(bundle_sha256, exposure_index)
            );
            """
        )
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        for bundle in validated:
            digest = bundle["bundleSHA256"]
            existing = connection.execute("SELECT 1 FROM bundles WHERE bundle_sha256=?", (digest,)).fetchone()
            if existing:
                continue
            connection.execute(
                "INSERT INTO bundles VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    digest, bundle["path"], bundle["activation"]["annotatorID"],
                    bundle["activation"]["annotationSessionID"], bundle["manifest"]["status"], now,
                    json.dumps(bundle["manifest"], sort_keys=True, separators=(",", ":")),
                    json.dumps(bundle["activation"], sort_keys=True, separators=(",", ":")),
                    json.dumps(bundle["revisionAudit"], sort_keys=True, separators=(",", ":")), "valid",
                ),
            )
            for annotation in bundle["annotations"]:
                connection.execute(
                    "INSERT INTO annotations VALUES (?,?,?)",
                    (digest, annotation["sourceUnitID"], json.dumps(annotation, sort_keys=True, separators=(",", ":"))),
                )
            for index, event in enumerate(bundle["timingEvents"], start=1):
                connection.execute(
                    "INSERT INTO timing_events VALUES (?,?,?)",
                    (digest, index, json.dumps(event, sort_keys=True, separators=(",", ":"))),
                )
            for index, exposure in enumerate(bundle["contextExposures"], start=1):
                connection.execute(
                    "INSERT INTO context_exposures VALUES (?,?,?)",
                    (digest, index, json.dumps(exposure, sort_keys=True, separators=(",", ":"))),
                )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise AnnotationContractError("CALIBRATION_IMPORT_DUPLICATE_IDENTITY_CONFLICT") from exc
    finally:
        connection.close()
    return master_database


def _git_build_checkpoint(
    root: Path, *, annotation_mvp_base_checkpoint: str = ANNOTATION_MVP_BASE_CHECKPOINT,
) -> str:
    """Return the actual clean descendant HEAD used to build a researcher package."""

    root = root.resolve()
    try:
        top_level = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AnnotationContractError("CALIBRATION_PACKAGE_GIT_REPOSITORY_INVALID") from exc
    if Path(top_level).resolve() != root:
        raise AnnotationContractError("CALIBRATION_PACKAGE_GIT_ROOT_MISMATCH")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", annotation_mvp_base_checkpoint, head],
        cwd=root, capture_output=True, text=True,
    )
    if ancestry.returncode != 0:
        raise AnnotationContractError("CALIBRATION_PACKAGE_BASE_CHECKPOINT_NOT_ANCESTOR")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout
    if status:
        raise AnnotationContractError("CALIBRATION_PACKAGE_WORKTREE_DIRTY")
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        raise AnnotationContractError("CALIBRATION_PACKAGE_BUILD_CHECKPOINT_INVALID")
    return head


def _package_source_paths(root: Path) -> list[Path]:
    """Return the minimal code, contracts, inputs, and canonical documents needed locally."""

    relative = [
        Path("src/annotation/__init__.py"),
        Path("src/annotation/publication_pilot1/__init__.py"),
        Path("src/annotation/publication_pilot1/contracts.py"),
        Path("src/annotation/publication_pilot1/calibration"),
        Path("src/annotation/publication_pilot1/requirements.txt"),
        Path("src/extraction/llm/publications/publication_target_inventory.yaml"),
        Path("data/curation/papers/pilot1"), Path("data/interim/papers/publication_nodes_edges.json"),
        Path("schemas/publication_candidate_output.schema.json"),
        Path("schemas/publication_pilot1_unit_routing.schema.json"),
        Path("schemas/publication_pilot1_annotation_record.schema.json"),
        Path("docs/publication_annotation_adjudication_guidelines.md"),
        Path("docs/publication_evidence_validation_contract.md"),
        Path("docs/publication_evaluation_matching_contract.md"),
        Path("docs/publication_pilot1_annotation_calibration_handbook.md"),
        Path("var/publication_pilot1_screening/exports/publication_pilot1_screening_worklist_reviewed.csv"),
    ]
    inventory = [
        json.loads(line) for line in (root / "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    relative.extend(Path(value) for value in sorted({row["sourceFile"] for row in inventory}))
    return [root / value for value in relative]


def _copy_package_path(source: Path, root: Path, destination: Path) -> None:
    """Copy one repository-relative file or tree without mutable runtime state."""

    relative = source.relative_to(root); target = destination / relative
    if source.is_dir():
        shutil.copytree(
            source, target, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    else:
        raise AnnotationContractError(f"CALIBRATION_PACKAGE_REQUIRED_FILE_MISSING:{relative}")


def _launcher_text(annotator_id: str, session_id: str) -> str:
    """Return a double-clickable local-only macOS launcher."""

    annotator = shlex.quote(annotator_id); session = shlex.quote(session_id)
    return f'''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Contact the researcher; nothing was installed." >&2; exit 2
fi
python3 -c 'import sys; assert sys.version_info >= (3,10); import yaml, jsonschema' || {{
  echo "Python 3.10+, PyYAML, and jsonschema are required. Contact the researcher; nothing was installed." >&2; exit 2;
}}
python3 -m src.annotation.publication_pilot1.calibration.distribution verify-package --package-root .
python3 -m src.annotation.publication_pilot1.calibration.app --mode calibration \\
  --activation-file activation/calibration_activation.json --annotator-id {annotator} \\
  --annotation-session-id {session} --host 127.0.0.1 --port 8766 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT INT TERM
for attempt in {{1..20}}; do
  if python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8766/api/bootstrap", timeout=0.2)' >/dev/null 2>&1; then break; fi
  if ! kill -0 "$server_pid" 2>/dev/null; then echo "Local annotation server failed to start." >&2; wait "$server_pid"; fi
  sleep 0.25
done
open http://127.0.0.1:8766/
wait "$server_pid"
'''


def _export_launcher_text(annotator_id: str, session_id: str, *, final: bool) -> str:
    """Return a bound backup or final-bundle macOS command."""

    flag = "--gate0-ready" if final else "--partial"
    suffix = "final" if final else "partial"
    return f'''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p exports
python3 -m src.annotation.publication_pilot1.calibration.distribution export-bundle \\
  --activation activation/calibration_activation.json --annotator-id {shlex.quote(annotator_id)} \\
  --annotation-session-id {shlex.quote(session_id)} {flag} \\
  --output exports/publication_pilot1_calibration_{suffix}.zip
echo "Bundle written under exports/. Return the ZIP file to the researcher."
'''


def build_distribution_package(
    root: Path, annotator_id: str, annotation_session_id: str, output_zip: Path,
) -> Path:
    """Build a private checkpoint-bound macOS package without opening production state/text."""

    root = root.resolve(); build_checkpoint = _git_build_checkpoint(root)
    annotator = _safe_identity(annotator_id, "CALIBRATION_PACKAGE_ANNOTATOR_ID_INVALID")
    session = _safe_identity(annotation_session_id, "CALIBRATION_PACKAGE_SESSION_ID_INVALID")
    with tempfile.TemporaryDirectory() as temporary_name:
        package = Path(temporary_name) / f"publication_pilot1_calibration_{annotator}"
        package.mkdir()
        for source in _package_source_paths(root):
            _copy_package_path(source, root, package)
        activation_path = package / "activation/calibration_activation.json"
        write_activation(
            root, annotator, session, activation_path, package_build_checkpoint=build_checkpoint,
        )
        guide = root / "docs/publication_pilot1_calibration_annotator_distribution.md"
        shutil.copy2(guide, package / "README_ANNOTATOR.md")
        scripts = {
            "launch_annotation.command": _launcher_text(annotator, session),
            "export_backup.command": _export_launcher_text(annotator, session, final=False),
            "export_final.command": _export_launcher_text(annotator, session, final=True),
        }
        for name, text in scripts.items():
            path = package / name; path.write_text(text, encoding="utf-8"); os.chmod(path, 0o755)
        if _git_build_checkpoint(root) != build_checkpoint:
            raise AnnotationContractError("CALIBRATION_PACKAGE_BUILD_CHECKPOINT_CHANGED")
        files = sorted(path for path in package.rglob("*") if path.is_file())
        manifest = {
            "packageSchemaVersion": PACKAGE_SCHEMA_VERSION,
            "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
            "packageBuildCheckpoint": build_checkpoint,
            "annotatorID": annotator, "annotationSessionID": session,
            "interfaceVersion": INTERFACE_VERSION, "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
            "routingVersion": ROUTING_VERSION, "calibrationIdentityOrderHash": CALIBRATION_ID_ORDER_HASH,
            "gate0PolicyHash": production_activation_payload(
                root, annotator, session, package_build_checkpoint=build_checkpoint,
            )["gate0PolicyHash"],
            "files": {str(path.relative_to(package)): sha256_file(path) for path in files},
        }
        (package / "package_manifest.json").write_bytes(_json_bytes(manifest))
        output_zip = output_zip.resolve(); output_zip.parent.mkdir(parents=True, exist_ok=True)
        temporary_zip = output_zip.with_suffix(output_zip.suffix + ".tmp")
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(package.rglob("*")):
                if not path.is_file():
                    continue
                arcname = str(path.relative_to(package.parent)); mode = 0o755 if path.suffix == ".command" else 0o600
                info = zipfile.ZipInfo(arcname, (1980, 1, 1, 0, 0, 0)); info.external_attr = (0o100000 | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED; archive.writestr(info, path.read_bytes())
        if output_zip.exists():
            if output_zip.read_bytes() == temporary_zip.read_bytes():
                temporary_zip.unlink(); return output_zip
            temporary_zip.unlink()
            raise AnnotationContractError("CALIBRATION_PACKAGE_OUTPUT_EXISTS_CONFLICT")
        os.replace(temporary_zip, output_zip); os.chmod(output_zip, 0o600)
    return output_zip


def verify_package(package_root: Path) -> dict[str, Any]:
    """Verify a generated unpacked package before any production application starts."""

    package_root = package_root.resolve()
    try:
        manifest = json.loads((package_root / "package_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnnotationContractError("CALIBRATION_PACKAGE_MANIFEST_INVALID") from exc
    expected_bindings = {
        "packageSchemaVersion": PACKAGE_SCHEMA_VERSION,
        "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
        "interfaceVersion": INTERFACE_VERSION, "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
        "routingVersion": ROUTING_VERSION, "calibrationIdentityOrderHash": CALIBRATION_ID_ORDER_HASH,
    }
    if any(manifest.get(key) != value for key, value in expected_bindings.items()):
        raise AnnotationContractError("CALIBRATION_PACKAGE_BINDING_MISMATCH")
    files = manifest.get("files", {})
    if not isinstance(files, Mapping):
        raise AnnotationContractError("CALIBRATION_PACKAGE_MANIFEST_INVALID")
    for relative, expected in files.items():
        path = (package_root / relative).resolve()
        if package_root not in path.parents:
            raise AnnotationContractError("CALIBRATION_PACKAGE_FILE_PATH_INVALID")
        if not path.is_file() or sha256_file(path) != expected:
            raise AnnotationContractError(f"CALIBRATION_PACKAGE_FILE_HASH_MISMATCH:{relative}")
    activation = package_root / "activation/calibration_activation.json"
    activation_payload = verify_production_activation(
        activation, package_root, annotator_id=str(manifest.get("annotatorID", "")),
        annotation_session_id=str(manifest.get("annotationSessionID", "")),
        expected_package_build_checkpoint=str(manifest.get("packageBuildCheckpoint", "")),
    )
    if manifest.get("gate0PolicyHash") != activation_payload["gate0PolicyHash"]:
        raise AnnotationContractError("CALIBRATION_PACKAGE_BINDING_MISMATCH")
    return manifest


def _root() -> Path:
    """Return repository/package root from this module."""

    return Path(__file__).resolve().parents[4]


def _calibration_contracts_for_bundle(root: Path, bundle: Path) -> AnnotationContracts:
    """Load contracts with a bundle activation for read-only researcher validation."""

    files, _ = _read_bundle(bundle)
    with tempfile.TemporaryDirectory() as temporary_name:
        activation_path = Path(temporary_name) / "activation.json"
        activation_path.write_bytes(files["activation.json"])
        return load_annotation_contracts(root, mode="calibration", activation_path=activation_path)


def main(argv: Sequence[str] | None = None) -> int:
    """Run researcher packaging/import or annotator export commands."""

    parser = argparse.ArgumentParser(description=__doc__); subparsers = parser.add_subparsers(dest="command", required=True)
    activation_parser = subparsers.add_parser("create-activation")
    activation_parser.add_argument("--annotator-id", required=True); activation_parser.add_argument("--annotation-session-id", required=True)
    activation_parser.add_argument("--output", type=Path, required=True)
    package_parser = subparsers.add_parser("build-package")
    package_parser.add_argument("--annotator-id", required=True); package_parser.add_argument("--annotation-session-id", required=True)
    package_parser.add_argument("--output", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify-package"); verify_parser.add_argument("--package-root", type=Path, required=True)
    export_parser = subparsers.add_parser("export-bundle")
    export_parser.add_argument("--activation", type=Path, required=True); export_parser.add_argument("--annotator-id", required=True)
    export_parser.add_argument("--annotation-session-id", required=True); export_parser.add_argument("--output", type=Path, required=True)
    export_status = export_parser.add_mutually_exclusive_group(required=True)
    export_status.add_argument("--partial", action="store_true"); export_status.add_argument("--gate0-ready", action="store_true")
    validate_parser = subparsers.add_parser("validate-bundle"); validate_parser.add_argument("bundle", type=Path)
    validate_parser.add_argument("--allow-partial", action="store_true")
    import_parser = subparsers.add_parser("import-bundles"); import_parser.add_argument("bundles", nargs="+", type=Path)
    import_parser.add_argument("--master-database", type=Path, required=True)
    args = parser.parse_args(argv); root = _root()
    try:
        if args.command == "create-activation":
            result: object = str(write_activation(root, args.annotator_id, args.annotation_session_id, args.output))
        elif args.command == "build-package":
            result = str(build_distribution_package(root, args.annotator_id, args.annotation_session_id, args.output))
        elif args.command == "verify-package":
            result = verify_package(args.package_root)
        elif args.command == "export-bundle":
            from .app import build_service
            application_args = argparse.Namespace(
                mode="calibration", activation_file=str(args.activation), annotator_id=args.annotator_id,
                annotation_session_id=args.annotation_session_id,
            )
            service = build_service(application_args)
            try:
                activation = json.loads(args.activation.read_text(encoding="utf-8"))
                result = str(build_export_bundle(service, activation, args.output, gate0_ready=args.gate0_ready))
            finally:
                service.store.close()
        elif args.command == "validate-bundle":
            contracts = _calibration_contracts_for_bundle(root, args.bundle)
            result = validate_export_bundle(args.bundle, contracts, require_gate0_ready=not args.allow_partial)
            result = {"bundleSHA256": result["bundleSHA256"], "status": result["manifest"]["status"]}
        else:
            contracts = _calibration_contracts_for_bundle(root, args.bundles[0])
            result = str(import_validated_bundles(args.bundles, contracts, args.master_database))
        print(json.dumps(result, indent=2, sort_keys=True) if not isinstance(result, str) else result)
        return 0
    except (AnnotationContractError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=os.sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
