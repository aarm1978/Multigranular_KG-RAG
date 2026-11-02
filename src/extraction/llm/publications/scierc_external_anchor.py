"""Deterministic, benchmark-native SciERC external-anchor mechanics.

This module deliberately contains no provider dispatch.  It separates processed
SciERC gold (used only by scoring) from the model-facing document projection.
Candidate construction never authorizes provider execution.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tarfile
from typing import Any, Iterable, Mapping, Sequence

import jsonschema

from src.extraction.llm.publications.openai_provider import build_responses_api_request
from src.extraction.llm.publications.publication_artifacts import write_durable_canonical
from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


SOURCE_FREEZE_PATH = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/scierc_external_anchor_source_freeze_v0.1.0.json"
ADAPTER_FREEZE_PATH = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/scierc_external_anchor_adapter_freeze_v0.1.2.json"
RUNTIME_ROOT = PROJECT_ROOT / "var/scierc_external_anchor"
RUNNER_VERSION = "scierc-external-anchor/0.2.0"
CONFIG_PATH = Path(__file__).with_name("scierc_configuration_v0.2.0.json")
PROMPT_PATH = Path(__file__).parent / "prompts/scierc_native_v0.2.0.txt"
ARCHIVE_PATH = RUNTIME_ROOT / "source/sciERC_processed.tar.gz"
GUIDELINE_PATH = RUNTIME_ROOT / "source/scierc_annotation_guideline.pdf"
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
    sentence_ranges: tuple[tuple[int, int], ...]


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
    with archive_path.open("rb") as handle:
        actual_archive_sha = _sha256_stream(handle)
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
            documents = parse_processed_split(payload, include_gold=False)
            if len(documents) != specification["documentCount"]:
                raise SciERCAnchorError(f"SPLIT_DOCUMENT_COUNT_MISMATCH:{split_name}")
            results["splits"][split_name] = {
                "path": specification["path"], "byteCount": len(payload),
                "sha256": actual_sha, "documentCount": len(documents),
            }
    return results


def parse_processed_split(payload: bytes, *, include_gold: bool = True) -> list[SciERCDocument]:
    """Parse DyGIE++ processed JSON lines without altering benchmark offsets."""

    try:
        rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SciERCAnchorError("INVALID_PROCESSED_JSONL") from exc
    if not rows or not all(isinstance(row, Mapping) for row in rows):
        raise SciERCAnchorError("PROCESSED_SPLIT_MUST_CONTAIN_JSON_OBJECT_ROWS")
    documents = [parse_processed_document(row, include_gold=include_gold) for row in rows]
    if len({document.document_id for document in documents}) != len(documents):
        raise SciERCAnchorError("DUPLICATE_DOCUMENT_ID")
    return documents


def parse_processed_document(row: Mapping[str, Any], *, include_gold: bool = True) -> SciERCDocument:
    """Parse one processed document and preserve its document-global offsets."""

    if not isinstance(row, Mapping):
        raise SciERCAnchorError("INVALID_PROCESSED_DOCUMENT_SHAPE")
    document_id = row.get("doc_key")
    sentences = row.get("sentences")
    if not isinstance(document_id, str) or not document_id or not isinstance(sentences, list) or not sentences:
        raise SciERCAnchorError("INVALID_PROCESSED_DOCUMENT_SHAPE")
    ranges = []
    tokens_list = []
    for sentence in sentences:
        if not isinstance(sentence, list) or not sentence or any(type(token) is not str or not token for token in sentence):
            raise SciERCAnchorError("INVALID_SOURCE_TOKENS")
        ranges.append((len(tokens_list), len(tokens_list) + len(sentence) - 1))
        tokens_list.extend(sentence)
    tokens = tuple(tokens_list)
    if not include_gold:
        return SciERCDocument(document_id, tokens, (), (), tuple(ranges))
    ner = row.get("ner")
    relations = row.get("relations")
    if not isinstance(ner, list) or not isinstance(relations, list):
        raise SciERCAnchorError("INVALID_GOLD_COLLECTIONS")
    if not (len(sentences) == len(ner) == len(relations)):
        raise SciERCAnchorError("SENTENCE_ANNOTATION_ALIGNMENT_FAILURE")
    entities: list[tuple[int, int, str]] = []
    edges: list[tuple[int, int, int, int, str]] = []
    for sentence_index, sentence_entities in enumerate(ner):
        if not isinstance(sentence_entities, list):
            raise SciERCAnchorError("INVALID_GOLD_ENTITY_SHAPE")
        for item in sentence_entities:
            if not isinstance(item, list) or len(item) != 3:
                raise SciERCAnchorError("INVALID_GOLD_ENTITY_SHAPE")
            start, end, label = item
            _validate_span(start, end, len(tokens))
            if sentence_for_span(start, end, tuple(ranges)) != sentence_index:
                raise SciERCAnchorError("GOLD_ENTITY_SENTENCE_MISMATCH")
            entities.append((start, end, _validate_entity_label(label)))
    for sentence_index, sentence_relations in enumerate(relations):
        if not isinstance(sentence_relations, list):
            raise SciERCAnchorError("INVALID_GOLD_RELATION_SHAPE")
        for item in sentence_relations:
            if not isinstance(item, list) or len(item) != 5:
                raise SciERCAnchorError("INVALID_GOLD_RELATION_SHAPE")
            hs, he, ts, te, label = item
            _validate_span(hs, he, len(tokens)); _validate_span(ts, te, len(tokens))
            if any(sentence_for_span(a, b, tuple(ranges)) != sentence_index for a, b in ((hs, he), (ts, te))):
                raise SciERCAnchorError("GOLD_RELATION_SENTENCE_MISMATCH")
            edges.append((hs, he, ts, te, _validate_relation_label(label)))
    return SciERCDocument(document_id, tokens, tuple(entities), tuple(edges), tuple(ranges))


def sentence_for_span(start: int, end: int, ranges: tuple[tuple[int, int], ...]) -> int:
    """Resolve a span wholly within one sentence; reject boundary crossing."""

    for index, (lower, upper) in enumerate(ranges):
        if lower <= start <= end <= upper:
            return index
    raise SciERCAnchorError("MENTION_CROSSES_SENTENCE_BOUNDARY")


def inference_projection(document: SciERCDocument) -> dict[str, Any]:
    """Return the gold-free, model-facing representation for one document."""

    return {
        "documentID": document.document_id,
        "tokens": [{"index": index, "text": token} for index, token in enumerate(document.tokens)],
        "text": " ".join(document.tokens),
        "sentences": [{"sentenceIndex": index, "start": start, "end": end}
                      for index, (start, end) in enumerate(document.sentence_ranges)],
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

    if type(start) is not int or type(end) is not int or start < 0 or end < start or end >= token_count:
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

    try:
        jsonschema.Draft202012Validator(output_schema()).validate(payload)
    except jsonschema.ValidationError as exc:
        raise SciERCAnchorError("INVALID_PREDICTION_SCHEMA") from exc
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
        if not isinstance(entity_id, str) or not entity_id.strip() or entity_id in bound:
            raise SciERCAnchorError("PREDICTED_ENTITY_ID_NOT_UNIQUE")
        start, end = row["spanStart"], row["spanEnd"]; _validate_span(start, end, len(document.tokens))
        sentence_for_span(start, end, document.sentence_ranges)
        label = _validate_entity_label(row["entityType"])
        if row["mentionText"] != " ".join(document.tokens[start:end + 1]):
            raise SciERCAnchorError("PREDICTED_MENTION_TEXT_NOT_EXACT_TOKEN_SPAN")
        signature = (start, end, label)
        if signature in signatures:
            raise SciERCAnchorError("DUPLICATE_PREDICTED_ENTITY_SIGNATURE")
        signatures.add(signature); bound[entity_id] = signature
    edge_signatures: set[tuple[str, tuple[int, int], tuple[int, int]]] = set()
    relation_ids: set[str] = set()
    for row in relations:
        if not isinstance(row, Mapping) or not all(key in row for key in ("relationID", "relationType", "sourceEntityID", "targetEntityID")):
            raise SciERCAnchorError("INVALID_PREDICTED_RELATION_SHAPE")
        source, target = row["sourceEntityID"], row["targetEntityID"]
        relation_id = row["relationID"]
        if not relation_id.strip() or relation_id in relation_ids:
            raise SciERCAnchorError("PREDICTED_RELATION_ID_NOT_UNIQUE_OR_EMPTY")
        relation_ids.add(relation_id)
        if source not in bound or target not in bound:
            raise SciERCAnchorError("RELATION_ENDPOINT_NOT_SAME_DOCUMENT_ENTITY")
        if sentence_for_span(*bound[source][:2], document.sentence_ranges) != sentence_for_span(*bound[target][:2], document.sentence_ranges):
            raise SciERCAnchorError("RELATION_CROSSES_SENTENCE_BOUNDARY")
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
    seen: set[str] = set()
    for document, prediction in documents_and_predictions:
        if document.document_id in seen:
            raise SciERCAnchorError("DUPLICATE_DOCUMENT_ID")
        seen.add(document.document_id)
        bound = validate_prediction(prediction, document)
        gold_entities = set(document.gold_entities)
        predicted_entities = set(bound["entities"].values())
        gold_relations = {relation_signature(label, (hs, he), (ts, te)) for hs, he, ts, te, label in document.gold_relations}
        predicted_relations = set(bound["relationSignatures"])
        _add_counts(entity_counts, gold_entities, predicted_entities)
        _add_counts(relation_counts, gold_relations, predicted_relations)
    return {"entity": _metrics(entity_counts), "relation": _metrics(relation_counts)}


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
    f1 = None if 2 * tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn)
    return {"TP": tp, "FP": fp, "FN": fn, "goldSupport": counts["goldSupport"], "predictionSupport": counts["predictionSupport"], "precision": precision, "recall": recall, "f1": f1}


def configuration() -> dict[str, Any]:
    """Require the approved candidate settings, independently of live authorization."""

    config = _load_json_object(CONFIG_PATH)
    expected = {"model": "gpt-5.6-sol", "reasoningEffort": "medium", "maxOutputTokens": 32768,
                "store": False, "executionMode": "synchronous_stateless", "automaticRedispatch": False,
                "runtimeAccepted": False, "researcherLiveAuthorization": False}
    if any(config.get(key) != value for key, value in expected.items()):
        raise SciERCAnchorError("CANDIDATE_CONFIGURATION_DRIFT")
    if adapter_freeze()["baseLLM"] != config["model"] or adapter_freeze()["reasoningEffort"] != config["reasoningEffort"]:
        raise SciERCAnchorError("FROZEN_CONFIGURATION_DRIFT")
    return config


def build_request_body(document: SciERCDocument) -> dict[str, Any]:
    """Build exact source-only request bytes through the shared stateless body builder."""

    config = configuration()
    input_bytes = PROMPT_PATH.read_bytes() + b"\nSciERC benchmark document:\n" + canonical_json(inference_projection(document))
    body = build_responses_api_request(input_bytes, model_authorable_schema=output_schema(), max_output_tokens=MAX_OUTPUT_TOKENS)
    body["text"]["format"]["name"] = "scierc_native_payload"
    if body["model"] != config["model"] or body["reasoning"] != {"effort": config["reasoningEffort"]} or body["store"] is not False or "background" in body or "tools" in body:
        raise SciERCAnchorError("PROVIDER_BODY_CONFIGURATION_DRIFT")
    return body


def _build_candidate_records(documents: Sequence[SciERCDocument]) -> dict[str, Any]:
    """Build review records; the public official builder alone establishes split identity."""

    if len({doc.document_id for doc in documents}) != len(documents):
        raise SciERCAnchorError("DUPLICATE_DOCUMENT_ID")
    schema = output_schema(); schema_sha = sha256_bytes(canonical_json(schema))
    manifest: dict[str, Any] = {"artifactType": "scierc_external_anchor_preflight_candidate", "artifactVersion": "0.2.0",
        "runnerVersion": RUNNER_VERSION, "providerModelCalls": 0, "logicalRequestPolicy": "one official document = one logical inference request",
        "logicalRequestCount": len(documents), "configuredOutputCeilingTokens": MAX_OUTPUT_TOKENS,
        "providerConfiguration": {"model": adapter_freeze()["baseLLM"], "reasoningEffort": adapter_freeze()["reasoningEffort"], "store": False, "executionMode": "synchronous_stateless"},
        "schemaSha256": schema_sha, "promptSha256": sha256_bytes(PROMPT_PATH.read_bytes()),
        "configurationSha256": sha256_bytes(CONFIG_PATH.read_bytes()),
        "buildReady": True, "runtimeAccepted": False, "researcherLiveAuthorization": False,
        "automaticRedispatch": False, "requests": []}
    for document in sorted(documents, key=lambda item: item.document_id):
        projection = inference_projection(document)
        record: dict[str, Any] = {"documentID": document.document_id, "projectionSha256": sha256_bytes(canonical_json(projection)), "schemaSha256": schema_sha,
            "promptSha256": manifest["promptSha256"], "configurationSha256": manifest["configurationSha256"],
            "providerRequestBodySha256": None, "terminalStatus": "not_dispatched"}
        body = build_request_body(document)
        record["inputTokenAccounting"] = {"exactProviderInputTokens": None,
            "serializedRequestUtf8Bytes": len(canonical_json(body)),
            "includesRepeatedPromptAndSchemaOverhead": True}
        record["providerRequestBodySha256"] = sha256_bytes(canonical_json(body))
        manifest["requests"].append(record)
    conservative_inputs = [row["inputTokenAccounting"]["serializedRequestUtf8Bytes"] for row in manifest["requests"]]
    manifest["preflightAccounting"] = {
        "inputAccountingMethod": "serialized_request_utf8_bytes_proxy_not_provider_tokens",
        "includesRepeatedPromptAndSchemaOverhead": True,
        "totalSerializedRequestUtf8Bytes": sum(conservative_inputs),
        "exactProviderInputTokens": None,
        "observedUsage": None, "observedLatency": None,
        "configuredOutputCeilingTokensPerRequest": MAX_OUTPUT_TOKENS,
        "configuredOutputCeilingTokensAllLogicalRequests": len(documents) * MAX_OUTPUT_TOKENS,
        "futureObservedUsageSource": "preserved provider usage metadata",
        "futureObservedLatencySource": "per-request client elapsedMilliseconds",
        "apiPricing": None,
    }
    manifest["status"] = "NOT AUTHORIZED FOR PROVIDER EXECUTION"
    return manifest


def build_run_manifest(archive_path: Path = ARCHIVE_PATH) -> dict[str, Any]:
    """Build only from all 100 unique documents of the verified frozen test split.

    JSON decoding is mechanical; test gold fields are never passed to parsers,
    request construction, validation, scoring, or prompt decisions.
    """

    config = configuration()
    if sha256_bytes(GUIDELINE_PATH.read_bytes()) != config["guidelineSha256"]:
        raise SciERCAnchorError("GUIDELINE_HASH_MISMATCH")
    verified = verify_archive(archive_path)
    spec = source_freeze()["splits"]["test"]
    with tarfile.open(archive_path, "r:gz") as archive:
        payload = archive.extractfile(spec["path"]).read()
    if sha256_bytes(payload) != spec["sha256"]:
        raise SciERCAnchorError("TEST_SPLIT_HASH_MISMATCH")
    documents = parse_processed_split(payload, include_gold=False)
    if len(documents) != 100 or len({doc.document_id for doc in documents}) != 100:
        raise SciERCAnchorError("OFFICIAL_TEST_MEMBERSHIP_FAILURE")
    manifest = _build_candidate_records(documents)
    manifest["source"] = {"archiveSha256": verified["archiveSha256"], "test": spec,
        "sourceFreezeFileSha256": sha256_bytes(SOURCE_FREEZE_PATH.read_bytes()),
        "adapterFreezeFileSha256": sha256_bytes(ADAPTER_FREEZE_PATH.read_bytes()),
        "guidelineSha256": config["guidelineSha256"]}
    manifest["implementationSha256"] = sha256_bytes(Path(__file__).read_bytes())
    manifest["providerBuilderSha256"] = sha256_bytes(Path(__file__).with_name("openai_provider.py").read_bytes())
    manifest["documentIDsSha256"] = sha256_bytes(canonical_json(sorted(doc.document_id for doc in documents)))
    manifest["manifestSha256"] = sha256_bytes(canonical_json(manifest))
    return manifest


def runtime_record(manifest_record: Mapping[str, Any]) -> dict[str, Any]:
    """Create a no-call durable output skeleton with future usage and latency fields."""

    return {"documentID": manifest_record["documentID"], "providerRequestBodySha256": manifest_record["providerRequestBodySha256"],
        "schemaSha256": manifest_record["schemaSha256"], "promptSha256": manifest_record["promptSha256"],
        "configurationSha256": manifest_record["configurationSha256"],
        "requestedModel": configuration()["model"], "reasoningEffort": "medium", "maxOutputTokens": MAX_OUTPUT_TOKENS,
        "rawProviderResponse": None, "rawModelOutputBase64": None, "usage": None,
        "latency": {"clientStartedAt": None, "clientCompletedAt": None, "elapsedMilliseconds": None},
        "terminalStatus": "not_dispatched"}


def persist_request_artifacts(document_id: str, body: Mapping[str, Any], root: Path = RUNTIME_ROOT) -> dict[str, Path]:
    """Persist an exact dispatch request and schema in the ignored runtime namespace.

    This helper is intentionally transport-free.  A future explicitly authorized
    dispatcher must call it before dispatch and then preserve raw response/output
    beside these bytes.
    """

    request_root = root / "requests" / sha256_bytes(document_id.encode("utf-8"))
    schema_path = request_root / "model_authorable_schema.json"
    body_path = request_root / "provider_request.json"
    for path, payload in ((schema_path, body["text"]["format"]["schema"]), (body_path, dict(body))):
        if path.exists() and path.read_bytes() != canonical_json(payload) + b"\n":
            raise SciERCAnchorError("RUNTIME_ARTIFACT_CONFLICT")
        write_durable_canonical(path, payload)
    return {"schema": schema_path, "providerRequest": body_path}


def write_runtime_manifest(manifest: Mapping[str, Any], root: Path = RUNTIME_ROOT) -> Path:
    """Write a separate ignored runtime manifest without dispatching a provider call."""

    path = root / "preflight_candidate.json"
    if manifest.get("researcherLiveAuthorization") is not False or manifest.get("runtimeAccepted") is not False:
        raise SciERCAnchorError("CANDIDATE_CANNOT_AUTHORIZE_EXECUTION")
    if path.exists() and path.read_bytes() != canonical_json(manifest) + b"\n":
        raise SciERCAnchorError("RUNTIME_ARTIFACT_CONFLICT")
    write_durable_canonical(path, dict(manifest))
    return path
