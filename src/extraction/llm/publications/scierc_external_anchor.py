"""Deterministic, benchmark-native SciERC external-anchor mechanics.

This module deliberately contains no provider dispatch.  It separates processed
SciERC gold (used only by scoring) from the model-facing document projection.
Live manifest construction is fail-closed until the researcher supplies an
authorized textual definition for the official ``EVALUATE-FOR`` label.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tarfile
from typing import Any, Iterable, Mapping, Sequence

from src.extraction.llm.publications.openai_provider import build_responses_api_request
from src.extraction.llm.publications.publication_artifacts import write_durable_canonical
from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


SOURCE_FREEZE_PATH = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/scierc_external_anchor_source_freeze_v0.1.0.json"
ADAPTER_FREEZE_PATH = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/scierc_external_anchor_adapter_freeze_v0.1.2.json"
RUNTIME_ROOT = PROJECT_ROOT / "var/scierc_external_anchor"
RUNNER_VERSION = "scierc-external-anchor/0.1.0"
MAX_OUTPUT_TOKENS = 32768
SYMMETRIC_RELATIONS = frozenset({"COMPARE", "CONJUNCTION"})


class SciERCAnchorError(ValueError):
    """Report a frozen-authority, data-integrity, or benchmark-format failure."""


@dataclass(frozen=True)
class SciERCDocument:
    """One parsed benchmark document with global token indexing retained exactly."""

    document_id: str
    tokens: tuple[str, ...]
    gold_entities: tuple[tuple[int, int, str], ...]
    gold_relations: tuple[tuple[int, int, int, int, str], ...]


def _load_json_object(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object or fail closed."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SciERCAnchorError(f"EXPECTED_JSON_OBJECT:{path}")
    return value


def _sha256_stream(handle: Any) -> str:
    """Return the SHA-256 digest of an already-open binary stream."""

    digest = hashlib.sha256()
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def source_freeze() -> dict[str, Any]:
    """Load the frozen benchmark-source binding."""

    return _load_json_object(SOURCE_FREEZE_PATH)


def adapter_freeze() -> dict[str, Any]:
    """Load the frozen benchmark-adapter binding."""

    return _load_json_object(ADAPTER_FREEZE_PATH)


def verify_archive(archive_path: Path, freeze: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Verify archive identity before reading any member, then stream-verify splits."""

    authority = source_freeze() if freeze is None else dict(freeze)
    actual_archive_sha = _sha256_stream(archive_path.open("rb"))
    expected_archive_sha = str(authority["officialArchive"]["sha256"])
    if actual_archive_sha != expected_archive_sha:
        raise SciERCAnchorError(
            f"ARCHIVE_SHA256_MISMATCH:expected={expected_archive_sha}:actual={actual_archive_sha}"
        )
    results: dict[str, Any] = {
        "archivePath": str(archive_path), "archiveSha256": actual_archive_sha, "splits": {}
    }
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for split_name, specification in sorted(authority["splits"].items()):
            member = archive.getmember(str(specification["path"]))
            stream = archive.extractfile(member)
            if stream is None:
                raise SciERCAnchorError(f"ARCHIVE_MEMBER_UNREADABLE:{specification['path']}")
            payload = stream.read()
            actual_sha = sha256_bytes(payload)
            if actual_sha != specification["sha256"]:
                raise SciERCAnchorError(f"SPLIT_SHA256_MISMATCH:{split_name}")
            documents = parse_processed_split(payload)
            if len(documents) != specification["documentCount"]:
                raise SciERCAnchorError(f"SPLIT_DOCUMENT_COUNT_MISMATCH:{split_name}")
            results["splits"][split_name] = {
                "path": specification["path"], "byteCount": len(payload),
                "sha256": actual_sha, "documentCount": len(documents),
            }
    return results


def parse_processed_split(payload: bytes) -> list[SciERCDocument]:
    """Parse DyGIE++ processed JSON lines without altering benchmark offsets."""

    try:
        rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SciERCAnchorError("INVALID_PROCESSED_JSONL") from exc
    if not rows or not all(isinstance(row, Mapping) for row in rows):
        raise SciERCAnchorError("PROCESSED_SPLIT_MUST_CONTAIN_JSON_OBJECT_ROWS")
    return [parse_processed_document(row) for row in rows]


def parse_processed_document(row: Mapping[str, Any]) -> SciERCDocument:
    """Parse one processed document and preserve its document-global offsets."""

    document_id = row.get("doc_key")
    sentences = row.get("sentences")
    ner = row.get("ner")
    relations = row.get("relations")
    if not isinstance(document_id, str) or not document_id or not all(isinstance(x, list) for x in (sentences, ner, relations)):
        raise SciERCAnchorError("INVALID_PROCESSED_DOCUMENT_SHAPE")
    if not (len(sentences) == len(ner) == len(relations)):
        raise SciERCAnchorError("SENTENCE_ANNOTATION_ALIGNMENT_FAILURE")
    tokens = tuple(str(token) for sentence in sentences for token in sentence)
    entities: list[tuple[int, int, str]] = []
    edges: list[tuple[int, int, int, int, str]] = []
    for sentence_entities in ner:
        for item in sentence_entities:
            if not isinstance(item, list) or len(item) != 3:
                raise SciERCAnchorError("INVALID_GOLD_ENTITY_SHAPE")
            start, end, label = item
            _validate_span(start, end, len(tokens))
            entities.append((start, end, _validate_entity_label(label)))
    for sentence_relations in relations:
        for item in sentence_relations:
            if not isinstance(item, list) or len(item) != 5:
                raise SciERCAnchorError("INVALID_GOLD_RELATION_SHAPE")
            hs, he, ts, te, label = item
            _validate_span(hs, he, len(tokens)); _validate_span(ts, te, len(tokens))
            edges.append((hs, he, ts, te, _validate_relation_label(label)))
    return SciERCDocument(document_id, tokens, tuple(entities), tuple(edges))


def inference_projection(document: SciERCDocument) -> dict[str, Any]:
    """Return the gold-free, model-facing representation for one document."""

    return {
        "documentID": document.document_id,
        "tokens": [{"index": index, "text": token} for index, token in enumerate(document.tokens)],
        "text": " ".join(document.tokens),
    }


def output_schema() -> dict[str, Any]:
    """Return the strict benchmark-native structured output schema."""

    entity_labels = adapter_freeze()["benchmarkNativeEntityLabels"]
    relation_labels = adapter_freeze()["benchmarkNativeRelationLabels"]
    return {
        "type": "object", "additionalProperties": False,
        "required": ["documentID", "entities", "relations"],
        "properties": {
            "documentID": {"type": "string"},
            "entities": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "required": ["entityID", "entityType", "spanStart", "spanEnd", "mentionText"],
                "properties": {"entityID": {"type": "string"}, "entityType": {"type": "string", "enum": entity_labels},
                    "spanStart": {"type": "integer", "minimum": 0}, "spanEnd": {"type": "integer", "minimum": 0}, "mentionText": {"type": "string"}}}},
            "relations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "required": ["relationID", "relationType", "sourceEntityID", "targetEntityID"],
                "properties": {"relationID": {"type": "string"}, "relationType": {"type": "string", "enum": relation_labels},
                    "sourceEntityID": {"type": "string"}, "targetEntityID": {"type": "string"}}}},
        },
    }


def _validate_span(start: Any, end: Any, token_count: int) -> None:
    """Require a document-global zero-based inclusive span."""

    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start or end >= token_count:
        raise SciERCAnchorError("INVALID_DOCUMENT_GLOBAL_INCLUSIVE_SPAN")


def _validate_entity_label(label: Any) -> str:
    """Require one exact frozen SciERC entity serialization."""

    if label not in adapter_freeze()["benchmarkNativeEntityLabels"]:
        raise SciERCAnchorError(f"INVALID_SCIERC_ENTITY_LABEL:{label}")
    return str(label)


def _validate_relation_label(label: Any) -> str:
    """Require one exact frozen SciERC relation serialization."""

    if label not in adapter_freeze()["benchmarkNativeRelationLabels"]:
        raise SciERCAnchorError(f"INVALID_SCIERC_RELATION_LABEL:{label}")
    return str(label)


def validate_prediction(payload: Mapping[str, Any], document: SciERCDocument) -> dict[str, Any]:
    """Validate and bind a prediction to exactly one benchmark document."""

    if payload.get("documentID") != document.document_id:
        raise SciERCAnchorError("PREDICTION_DOCUMENT_ID_MISMATCH")
    entities = payload.get("entities")
    relations = payload.get("relations")
    if not isinstance(entities, list) or not isinstance(relations, list):
        raise SciERCAnchorError("PREDICTION_COLLECTIONS_REQUIRED")
    bound: dict[str, tuple[int, int, str]] = {}
    signatures: set[tuple[int, int, str]] = set()
    for row in entities:
        if not isinstance(row, Mapping) or not all(key in row for key in ("entityID", "entityType", "spanStart", "spanEnd", "mentionText")):
            raise SciERCAnchorError("INVALID_PREDICTED_ENTITY_SHAPE")
        entity_id = row["entityID"]
        if not isinstance(entity_id, str) or not entity_id or entity_id in bound:
            raise SciERCAnchorError("PREDICTED_ENTITY_ID_NOT_UNIQUE")
        start, end = row["spanStart"], row["spanEnd"]; _validate_span(start, end, len(document.tokens))
        label = _validate_entity_label(row["entityType"])
        if row["mentionText"] != " ".join(document.tokens[start:end + 1]):
            raise SciERCAnchorError("PREDICTED_MENTION_TEXT_NOT_EXACT_TOKEN_SPAN")
        signature = (start, end, label)
        if signature in signatures:
            raise SciERCAnchorError("DUPLICATE_PREDICTED_ENTITY_SIGNATURE")
        signatures.add(signature); bound[entity_id] = signature
    edge_signatures: set[tuple[str, tuple[int, int], tuple[int, int]]] = set()
    for row in relations:
        if not isinstance(row, Mapping) or not all(key in row for key in ("relationID", "relationType", "sourceEntityID", "targetEntityID")):
            raise SciERCAnchorError("INVALID_PREDICTED_RELATION_SHAPE")
        source, target = row["sourceEntityID"], row["targetEntityID"]
        if source not in bound or target not in bound:
            raise SciERCAnchorError("RELATION_ENDPOINT_NOT_SAME_DOCUMENT_ENTITY")
        relation = _validate_relation_label(row["relationType"])
        signature = relation_signature(relation, bound[source][:2], bound[target][:2])
        if signature in edge_signatures:
            raise SciERCAnchorError("DUPLICATE_PREDICTED_RELATION_SIGNATURE")
        edge_signatures.add(signature)
    return {"documentID": document.document_id, "entities": bound, "relationSignatures": sorted(edge_signatures)}


def relation_signature(label: str, head: tuple[int, int], tail: tuple[int, int]) -> tuple[str, tuple[int, int], tuple[int, int]]:
    """Return the frozen primary relation key, canonicalizing symmetric labels."""

    _validate_relation_label(label)
    if label in SYMMETRIC_RELATIONS and tail < head:
        head, tail = tail, head
    return label, head, tail


def score_documents(documents_and_predictions: Iterable[tuple[SciERCDocument, Mapping[str, Any]]]) -> dict[str, Any]:
    """Compute frozen micro entity and relation scores; never a composite score."""

    entity_counts: Counter[str] = Counter(); relation_counts: Counter[str] = Counter()
    for document, prediction in documents_and_predictions:
        bound = validate_prediction(prediction, document)
        gold_entities = set(document.gold_entities)
        predicted_entities = set(bound["entities"].values())
        gold_relations = {relation_signature(label, (hs, he), (ts, te)) for hs, he, ts, te, label in document.gold_relations}
        predicted_relations = set(bound["relationSignatures"])
        _add_counts(entity_counts, gold_entities, predicted_entities)
        _add_counts(relation_counts, gold_relations, predicted_relations)
    return {"entity": _metrics(entity_counts), "relation": _metrics(relation_counts), "composite": None}


def _add_counts(counts: Counter[str], gold: set[Any], predicted: set[Any]) -> None:
    """Accumulate exact-set micro counts."""

    matched = len(gold & predicted)
    counts.update({"TP": matched, "FP": len(predicted) - matched, "FN": len(gold) - matched,
                   "goldSupport": len(gold), "predictionSupport": len(predicted)})


def _metrics(counts: Mapping[str, int]) -> dict[str, Any]:
    """Render support, contingency counts, and micro P/R/F1."""

    tp, fp, fn = counts["TP"], counts["FP"], counts["FN"]
    precision = None if tp + fp == 0 else tp / (tp + fp)
    recall = None if tp + fn == 0 else tp / (tp + fn)
    f1 = None if precision is None or recall is None or precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"TP": tp, "FP": fp, "FN": fn, "goldSupport": counts["goldSupport"], "predictionSupport": counts["predictionSupport"], "precision": precision, "recall": recall, "f1": f1}


def prompt_status(label_definitions: Mapping[str, str]) -> dict[str, Any]:
    """Fail closed until every frozen label, especially EVALUATE-FOR, has text."""

    missing = [label for label in adapter_freeze()["benchmarkNativeRelationLabels"] if not isinstance(label_definitions.get(label), str) or not label_definitions[label].strip()]
    return {"dispatchReady": not missing, "missingRelationDefinitions": missing,
            "blockingReason": None if not missing else "UNRESOLVED_OFFICIAL_PROMPT_SEMANTICS"}


def build_run_manifest(documents: Sequence[SciERCDocument], label_definitions: Mapping[str, str]) -> dict[str, Any]:
    """Build a deterministic manifest; body hashes exist only for a dispatch-ready prompt."""

    if len({doc.document_id for doc in documents}) != len(documents):
        raise SciERCAnchorError("DUPLICATE_DOCUMENT_ID")
    status = prompt_status(label_definitions)
    schema = output_schema(); schema_sha = sha256_bytes(canonical_json(schema))
    manifest: dict[str, Any] = {"artifactType": "scierc_external_anchor_run_manifest", "artifactVersion": "0.1.0",
        "runnerVersion": RUNNER_VERSION, "providerModelCalls": 0, "logicalRequestPolicy": "one official document = one logical inference request",
        "logicalRequestCount": len(documents), "configuredOutputCeilingTokens": MAX_OUTPUT_TOKENS,
        "providerConfiguration": {"model": adapter_freeze()["baseLLM"], "reasoningEffort": adapter_freeze()["reasoningEffort"], "store": False, "executionMode": "synchronous_stateless"},
        "schemaSha256": schema_sha, "promptStatus": status, "requests": []}
    for document in sorted(documents, key=lambda item: item.document_id):
        projection = inference_projection(document)
        record: dict[str, Any] = {"documentID": document.document_id, "projectionSha256": sha256_bytes(canonical_json(projection)), "schemaSha256": schema_sha,
            "inputTokenAccounting": {"exactProviderInputTokens": None, "conservativeUtf8ByteUpperBound": None, "includesRepeatedPromptAndSchemaOverhead": True},
            "providerRequestBodySha256": None, "terminalStatus": "not_dispatched"}
        if status["dispatchReady"]:
            prompt = _prompt(label_definitions)
            input_bytes = prompt.encode("utf-8") + b"\n\nSciERC benchmark document:\n" + canonical_json(projection)
            body = build_responses_api_request(input_bytes, model_authorable_schema=schema, max_output_tokens=MAX_OUTPUT_TOKENS)
            record["inputTokenAccounting"]["conservativeUtf8ByteUpperBound"] = len(canonical_json(body))
            record["providerRequestBodySha256"] = sha256_bytes(canonical_json(body))
        manifest["requests"].append(record)
    conservative_inputs = [row["inputTokenAccounting"]["conservativeUtf8ByteUpperBound"] for row in manifest["requests"]]
    manifest["preflightAccounting"] = {
        "inputTokenEstimateMethod": "utf8_byte_upper_bound_v0.1.0",
        "includesRepeatedPromptAndSchemaOverhead": True,
        "totalConservativeInputTokenUpperBound": None if any(value is None for value in conservative_inputs) else sum(conservative_inputs),
        "configuredOutputCeilingTokensPerRequest": MAX_OUTPUT_TOKENS,
        "configuredOutputCeilingTokensAllLogicalRequests": len(documents) * MAX_OUTPUT_TOKENS,
        "futureObservedUsageSource": "preserved provider usage metadata",
        "futureObservedLatencySource": "per-request client elapsedMilliseconds",
        "apiPricing": None,
    }
    manifest["status"] = "ready_for_explicit_live_execution" if status["dispatchReady"] else "blocked_pending_prompt_semantics"
    manifest["manifestSha256"] = sha256_bytes(canonical_json(manifest))
    return manifest


def _prompt(label_definitions: Mapping[str, str]) -> str:
    """Create the allowed benchmark-native instruction after complete definitions exist."""

    status = prompt_status(label_definitions)
    if not status["dispatchReady"]:
        raise SciERCAnchorError("UNRESOLVED_OFFICIAL_PROMPT_SEMANTICS")
    definitions = "\n".join(f"- {label}: {label_definitions[label].strip()}" for label in adapter_freeze()["benchmarkNativeRelationLabels"])
    return "Extract only benchmark-native SciERC entities and relations. Use exact indexed inclusive token spans. Relations must cite entities in this document. COMPARE and CONJUNCTION are symmetric; all other relations are directed.\nRelation definitions:\n" + definitions


def runtime_record(manifest_record: Mapping[str, Any]) -> dict[str, Any]:
    """Create a no-call durable output skeleton with future usage and latency fields."""

    return {"documentID": manifest_record["documentID"], "providerRequestBodySha256": manifest_record["providerRequestBodySha256"],
        "rawProviderResponse": None, "rawModelOutputBase64": None, "usage": None,
        "latency": {"clientStartedAt": None, "clientCompletedAt": None, "elapsedMilliseconds": None},
        "terminalStatus": "not_dispatched"}


def persist_request_artifacts(document_id: str, body: Mapping[str, Any], root: Path = RUNTIME_ROOT) -> dict[str, Path]:
    """Persist an exact dispatch request and schema in the ignored runtime namespace.

    This helper is intentionally transport-free.  A future explicitly authorized
    dispatcher must call it before dispatch and then preserve raw response/output
    beside these bytes.
    """

    request_root = root / "requests" / document_id
    schema_path = request_root / "model_authorable_schema.json"
    body_path = request_root / "provider_request.json"
    write_durable_canonical(schema_path, output_schema())
    write_durable_canonical(body_path, dict(body))
    return {"schema": schema_path, "providerRequest": body_path}


def write_runtime_manifest(manifest: Mapping[str, Any], root: Path = RUNTIME_ROOT) -> Path:
    """Write a separate ignored runtime manifest without dispatching a provider call."""

    path = root / "run_manifest.json"
    write_durable_canonical(path, dict(manifest))
    return path
