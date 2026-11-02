"""Offline canonical C1 replay with a mandatory 217-request parity gate.

Batch orchestration only: semantic processing belongs to publication_semantic_pipeline.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import patch

from . import publication_semantic_pipeline as pipeline
from .production_acceptance import (IMMUTABLE_ATTEMPT_FIELDS, derive_accepted_semantic_projection,
                                    derive_unresolved_identity_sidecar, run_attempt_controller)
from .production_runner import (DEFAULT_LIVE_ROOT, N6_ENVELOPES_PATH, ProductionPreflightError,
                                _load, _prepared_request, _write_immutable)
from .request_builder import PROJECT_ROOT, canonical_json, sha256_bytes
from .step5_freeze_materialization import _inputs

NAMESPACE = "canonical-semantic-replay-v1.0.0"
DEV_ROOT = PROJECT_ROOT / "data/curation/papers/m2/future_full_semantic_devset0_v015_schema013_tail"
# Only artifact hashes may vary with wrapper provenance. No semantic fields,
# evidence coordinates, request identity, validation statuses, or findings are ignored.
PROVENANCE_HASH_FIELDS = frozenset({
    "attemptSelectionHash", "acceptedSemanticProjectionHash", "unresolvedIdentitySidecarHash",
    "sidecarHash", "validationResultsHash", "usablePipelineOutputHash", "validationResultHash",
    "parsedOutputSha256", "inputRecordHash", "metadataSha256",
})


def semantic_content(value: Any) -> Any:
    """Remove only explicit derived provenance hashes for strict semantic parity."""
    if isinstance(value, Mapping):
        return {k: semantic_content(v) for k, v in value.items() if k not in PROVENANCE_HASH_FIELDS}
    if isinstance(value, list):
        return [semantic_content(v) for v in value]
    return value


def require_parity(expected: Any, actual: Any, label: str) -> None:
    """Fail closed before terminal recovery on any semantic mismatch."""
    if semantic_content(expected) != semantic_content(actual):
        raise ProductionPreflightError(f"canonical semantic parity mismatch: {label}")


def verify_dev_witnesses() -> dict[str, Any]:
    """Check authentic DEV-09/10 against the whole frozen DEVSET0 closure authority."""
    closure = _load(PROJECT_ROOT/"data/curation/papers/m2/publication_devset0_schema013_closure_v1.0.json")
    if closure["implementationCommit"] != "7d48e94" or closure["schema013AuthorityBundleID"] != "publication-semantic-v0.1.5-schema-v0.1.3":
        raise ProductionPreflightError("DEVSET0 schema013 closure drift")
    result = {}
    for dev in ("DEV-09", "DEV-10"):
        prefix = DEV_ROOT/dev/f"publication_full_semantic_{dev.lower().replace('-', '')}"
        def path(suffix: str) -> Path:
            """Resolve one preserved DEV witness artifact."""
            return Path(str(prefix) + "_" + suffix + ".json")
        request, metadata = _load(path("live_request")), _load(path("provider_metadata"))
        raw = path("exact_structured_model_output").read_bytes()
        authority = next(row for row in closure["units"] if row["developmentID"] == dev)
        if sha256_bytes(raw) != authority["rawOutputSha256"]:
            raise ProductionPreflightError("frozen DEV raw output drift")
        parser, parsed, validation, usable = pipeline.semantic_attempt(raw, request, provider_metadata=metadata)
        for suffix, value in (("parser_result", parser), ("validation_results", validation), ("usable_pipeline_output", usable)):
            require_parity(_load(path(suffix)), value, dev + "/" + suffix)
        if parsed != path("parsed_candidate").read_bytes():
            raise ProductionPreflightError(f"DEV canonical parsed envelope bytes differ: {dev}")
        result[dev] = {"parity": True, "usableCandidateCount": len(usable["candidateNodes"]) + len(usable["candidateEdges"])}
    return result


def original_hashes(root: Path) -> dict[str, str]:
    """Inventory every pre-existing artifact outside the new canonical namespace."""
    return {str(path.relative_to(root)): sha256_bytes(path.read_bytes())
            for path in sorted(root.rglob("*")) if path.is_file() and NAMESPACE not in path.relative_to(root).parts}


def _verify_hash(record: Mapping[str, Any], field: str) -> None:
    """Verify a self-hashed durable record."""
    body = dict(record); expected = body.pop(field, None)
    if expected != sha256_bytes(canonical_json(body)):
        raise ProductionPreflightError(f"preserved {field} drift")


def _load_attempt(root: Path, record: Mapping[str, Any], prepared: Mapping[str, Any], selection: Mapping[str, Any], number: int) -> tuple[bytes, dict[str, Any]]:
    """Check original selected/terminal attempt bytes against manifest and lifecycle."""
    attempt = next(row for row in selection["attempts"] if row["attemptNumber"] == number)
    path = root/f"attempt-{number:02d}"
    lifecycle = _load(path/"lifecycle.json")
    if lifecycle != attempt:
        raise ProductionPreflightError("attempt selection/lifecycle disagreement")
    raw = (path/"raw_model_output.json").read_bytes(); metadata = _load(path/"provider_metadata.json")
    response = _load(path/"provider_response.json")
    checks = {
        "rawOutputSha256": sha256_bytes(raw), "providerMetadataSha256": sha256_bytes(canonical_json(metadata)),
        "providerResponseSha256": sha256_bytes(canonical_json(response)),
        "requestInputSha256": prepared["request"]["requestInputSha256"],
        "providerInputSha256": sha256_bytes(prepared["providerInput"]),
        "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(prepared["schema"])),
    }
    if any(attempt.get(k) != v for k, v in checks.items()):
        raise ProductionPreflightError("authentic attempt hash/identity drift")
    if sha256_bytes(canonical_json(_load(path/"provider_request.json"))) != record["providerRequestBodySha256"] or metadata.get("rawModelOutputSha256") != checks["rawOutputSha256"]:
        raise ProductionPreflightError("provider request/raw metadata drift")
    return raw, metadata


def _replay_one(root: Path, record: Mapping[str, Any], prepared: Mapping[str, Any], original: Mapping[str, Any], recovery: bool) -> dict[str, Any]:
    """Replay an existing authentic attempt and reapply the frozen controller offline."""
    number = original["selectedAttemptNumber"] or original["attempts"][-1]["attemptNumber"]
    raw, metadata = _load_attempt(root, record, prepared, original, number)
    parser, parsed, validation, usable = pipeline.semantic_attempt(raw, prepared["request"], provider_metadata=metadata, production=True, attempt_number=number)
    def attempt(n: int) -> dict[str, Any]:
        """Supply only preserved attempts; never manufacture or dispatch a new sample."""
        matches = [row for row in original["attempts"] if row["attemptNumber"] == n]
        if len(matches) != 1:
            raise ProductionPreflightError("offline controller requested an unpreserved provider attempt")
        result = deepcopy(matches[0])
        if n == number:
            result.update(parserResult=parser, validation=validation, usablePipelineOutput=usable)
        return result
    selection = run_attempt_controller(attempt)
    if len(selection["attempts"]) != len(original["attempts"]):
        raise ProductionPreflightError("canonical replay changed original attempt count")
    for before, after in zip(original["attempts"], selection["attempts"]):
        if any(before[k] != after[k] for k in IMMUTABLE_ATTEMPT_FIELDS):
            raise ProductionPreflightError("canonical replay changed immutable attempt identity")
    if not recovery and (selection["selectedAttemptNumber"] != original["selectedAttemptNumber"] or selection["selectionDisposition"] != original["selectionDisposition"]):
        raise ProductionPreflightError("processable selection changed")
    artifacts = {"parser_result.json": parser, "validation_results.json": validation,
                 "usable_pipeline_output.json": usable, "attempt_selection.json": selection}
    if selection["selectedAttemptNumber"] is not None:
        artifacts["accepted_semantic_projection.json"] = derive_accepted_semantic_projection(selection, prepared["request"])
        artifacts["unresolved_identity_sidecar.json"] = derive_unresolved_identity_sidecar(selection, prepared["request"])
    source = root/"downstream-replay-v0.1.0" if (root/"downstream-replay-v0.1.0").exists() else root/f"attempt-{number:02d}"
    if not recovery:
        for name in ("parser_result.json", "validation_results.json", "usable_pipeline_output.json"):
            require_parity(_load(source/name), artifacts[name], record["requestID"] + "/" + name)
        acceptance_root = source if source.name == "downstream-replay-v0.1.0" else root
        for name in ("accepted_semantic_projection.json", "unresolved_identity_sidecar.json"):
            require_parity(_load(acceptance_root/name), artifacts[name], record["requestID"] + "/" + name)
    artifacts["provenance.json"] = {
        "replayVersion": NAMESPACE, "pipelineVersion": pipeline.PIPELINE_VERSION,
        "evidenceIsolationVersion": pipeline.ISOLATION_VERSION, "requestID": record["requestID"],
        "requestInputSha256": record["requestInputSha256"], "providerRequestBodySha256": record["providerRequestBodySha256"],
        "rawOutputSha256": sha256_bytes(raw), "providerMetadataSha256": sha256_bytes(canonical_json(metadata)),
        "originalSelectedAttemptNumber": original["selectedAttemptNumber"], "selectedAttemptNumber": selection["selectedAttemptNumber"],
        "originalSelectionDisposition": original["selectionDisposition"], "selectionDisposition": selection["selectionDisposition"],
        "originalAttemptSelectionSha256": sha256_bytes((root/"attempt_selection.json").read_bytes()),
        "providerReexecuted": False, "rawOutputChanged": False, "parityPreserved": not recovery,
        "amendedTerminalOutcome": recovery, "authoritativePriorDownstream": str(source.relative_to(root)),
    }
    if recovery:
        artifacts["recovery_accounting.json"] = _recovery_accounting(parser, validation, usable)
    return artifacts


def _recovery_accounting(parser: Mapping[str, Any], validation: Mapping[str, Any], usable: Mapping[str, Any]) -> dict[str, Any]:
    """Account for raw, directly excluded, cascaded, validated and usable candidates."""
    raw = parser.get("parsedDocument", {}); isolation = parser.get("evidenceIsolation", {})
    excluded = isolation.get("excludedRecords", [])
    rows = [row for row in validation.get("recordResults", []) if row.get("recordType") in {"candidate_node", "candidate_edge"}]
    cascades = [row for row in rows if row.get("candidateValidationStatus") == "rejected" and any(f["code"] in {"ENDPOINT_LIFECYCLE_INVALID", "ENDPOINT_REFERENCE_MISSING", "ENDPOINT_CLASS_UNRESOLVED"} for f in row.get("findings", []))]
    return {"rawEvidenceSpanCount": len(raw.get("evidenceSpans", [])),
            "failedEvidenceSpanIDs": isolation.get("failedEvidenceSpanIDs", []),
            "failureCodes": dict(Counter(f["code"] for f in parser.get("evidenceBinding", {}).get("findings", []))),
            "rawNodeCount": len(raw.get("candidateNodes", [])), "rawEdgeCount": len(raw.get("candidateEdges", [])),
            "directlyExcludedNodes": sum(x["recordType"] == "candidate_node" for x in excluded),
            "directlyExcludedEdges": sum(x["recordType"] == "candidate_edge" for x in excluded),
            "nestedAttributeExclusions": sum(any(d["pointer"].startswith("/attributes/") for d in x["failedEvidenceDependencies"]) for x in excluded),
            "excludedRecords": excluded, "subsequentDependencyRejections": [{"recordID": x["recordID"], "findings": x["findings"]} for x in cascades],
            "candidatesReachingValidation": len(rows),
            "candidateStatusCounts": dict(Counter(x["candidateValidationStatus"] for x in rows)),
            "usableNodes": len(usable.get("candidateNodes", [])), "usableEdges": len(usable.get("candidateEdges", [])),
            "recoveredNonempty": bool(usable.get("candidateNodes") or usable.get("candidateEdges"))}


def replay_all(root: Path = DEFAULT_LIVE_ROOT) -> dict[str, Any]:
    """Deny all network/key access, gate 217 parity, then replay 10 terminal attempts."""
    with patch("socket.socket.connect", side_effect=AssertionError("offline replay forbids network")), patch("src.extraction.llm.publications.production_runner.load_openai_api_key", side_effect=AssertionError("offline replay forbids API keys")):
        return _replay_all(root)


def _replay_all(root: Path) -> dict[str, Any]:
    """Perform both gates, preserve originals, and write the authoritative replay view."""
    before = original_hashes(root)
    dev = verify_dev_witnesses()
    manifest = _load(root/"publication_c1_run_manifest.json"); _verify_hash(manifest, "manifestSha256")
    records = manifest["requests"]
    if len(records) != 227 or len({x["requestID"] for x in records}) != 227:
        raise ProductionPreflightError("canonical replay requires the frozen 227 manifest")
    selections = {r["requestID"]: _load(root/"requests"/r["requestID"]/"attempt_selection.json") for r in records}
    for selection in selections.values():
        _verify_hash(selection, "attemptSelectionHash")
    processable = [r for r in records if selections[r["requestID"]]["selectedAttemptNumber"] is not None]
    terminal = [r for r in records if selections[r["requestID"]]["selectedAttemptNumber"] is None]
    if len(processable) != 217 or len(terminal) != 10:
        raise ProductionPreflightError("canonical replay requires the observed 217/10 checkpoint")
    for record in terminal:
        selection = selections[record["requestID"]]
        if selection["selectionDisposition"] != "terminal_non_retry_eligible_processing_failure" or selection["attempts"][-1]["parserResult"].get("processingCode") != "EVIDENCE_BINDING_FAILED":
            raise ProductionPreflightError("unexpected terminal outcome")
    inv, routing = _inputs(); n6 = {row["primarySourceUnitID"]: row for row in _load(N6_ENVELOPES_PATH)["envelopes"]}
    results = {}
    for recovery, group in ((False, processable), (True, terminal)):
        for index, record in enumerate(group):
            prepared = _prepared_request(record["primarySourceUnitID"], inv, routing, frozen_n6=n6.get(record["primarySourceUnitID"]))
            if any(prepared["request"][k] != record[k] for k in ("requestID", "requestInputSha256")) or sha256_bytes(canonical_json(prepared["body"])) != record["providerRequestBodySha256"]:
                raise ProductionPreflightError("frozen manifest identity drift")
            results[record["requestID"]] = _replay_one(root/"requests"/record["requestID"], record, prepared, selections[record["requestID"]], recovery)
            if (index + 1) % 20 == 0:
                print(f"{'recovery' if recovery else 'parity'}: {index + 1}/{len(group)}", flush=True)
        if not recovery:
            print("217-request semantic parity gate passed; beginning terminal recovery", flush=True)
    if original_hashes(root) != before:
        raise ProductionPreflightError("original artifacts changed during canonical replay")
    for request_id, artifacts in results.items():
        for filename, value in artifacts.items():
            _write_immutable(root/"requests"/request_id/NAMESPACE/filename, value)
    report = _aggregate(results, selections)
    report.update(devWitnessParity=dev, processableParity={"required": 217, "passed": 217, "failed": 0},
                  providerModelCalls=0, networkAndCredentialAccessBlocked=True,
                  originalArtifactsUnchanged=original_hashes(root) == before,
                  originalArtifactCount=len(before), originalArtifactInventorySha256=sha256_bytes(canonical_json(before)))
    if report["originalArtifactsUnchanged"] is not True:
        raise ProductionPreflightError("original artifact preservation failed")
    _write_immutable(root/NAMESPACE/"original_artifact_hashes.json", before)
    _write_immutable(root/NAMESPACE/"aggregate_report.json", report)
    return report


def _aggregate(results: Mapping[str, Any], originals: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize all canonical outcomes and every former terminal recovery."""
    artifacts = list(results.values())
    recovery = {key: value["recovery_accounting.json"] for key, value in results.items() if "recovery_accounting.json" in value}
    return {"replayVersion": NAMESPACE, "pipelineVersion": pipeline.PIPELINE_VERSION,
            "evidenceIsolationVersion": pipeline.ISOLATION_VERSION, "requestCount": len(artifacts),
            "originalDispositionDistribution": dict(Counter(x["selectionDisposition"] for x in originals.values())),
            "canonicalDispositionDistribution": dict(Counter(x["attempt_selection.json"]["selectionDisposition"] for x in artifacts)),
            "selectedAttemptDistribution": dict(Counter(str(x["attempt_selection.json"]["selectedAttemptNumber"]) for x in artifacts)),
            "originalEvidenceBindingFailureRequests": len(recovery),
            "isolatedSpanCount": sum(len(x["failedEvidenceSpanIDs"]) for x in recovery.values()),
            "recoveredNonemptyRequests": sum(x["recoveredNonempty"] for x in recovery.values()),
            "rawCandidatesInFormerTerminals": sum(x["rawNodeCount"] + x["rawEdgeCount"] for x in recovery.values()),
            "directlyExcludedCandidates": sum(x["directlyExcludedNodes"] + x["directlyExcludedEdges"] for x in recovery.values()),
            "subsequentDependencyRejections": sum(len(x["subsequentDependencyRejections"]) for x in recovery.values()),
            "salvagedUsableCandidates": sum(x["usableNodes"] + x["usableEdges"] for x in recovery.values()),
            "envelopeStatusDistribution": dict(Counter(x["validation_results.json"]["envelopeStatus"] for x in artifacts)),
            "usableOutputDistribution": dict(Counter("nonempty" if x["usable_pipeline_output.json"]["candidateNodes"] or x["usable_pipeline_output.json"]["candidateEdges"] else "empty" for x in artifacts)),
            "totalUsableNodes": sum(len(x["usable_pipeline_output.json"]["candidateNodes"]) for x in artifacts),
            "totalUsableEdges": sum(len(x["usable_pipeline_output.json"]["candidateEdges"]) for x in artifacts),
            "terminalRecoveryDetails": recovery}
