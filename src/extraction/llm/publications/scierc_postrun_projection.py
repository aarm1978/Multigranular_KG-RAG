"""Post-run, gold-independent failure isolation; never repair authentic predictions."""

from copy import deepcopy

import jsonschema

from . import scierc_external_anchor as a
from .scierc_smoke_runtime import _strict_json

REASON = "PREDICTED_MENTION_TEXT_NOT_EXACT_TOKEN_SPAN"


def require(condition, code: str) -> None:
    """Keep every non-authorized error category fail-closed."""
    if not condition:
        raise a.SciERCAnchorError(code)


def project(raw: bytes, document: a.SciERCDocument) -> tuple[dict, list]:
    """Find all mismatches only after gating all other original-record constraints."""
    payload = _strict_json(raw)
    jsonschema.Draft202012Validator(a.output_schema()).validate(payload)
    require(payload["documentID"] == document.document_id, "PREDICTION_DOCUMENT_ID_MISMATCH")
    entities = {}; signatures = set(); rejected = set(); ledger = []
    for entity in payload["entities"]:
        eid = entity["entityID"]
        require(eid.strip() and eid not in entities, "PREDICTED_ENTITY_ID_NOT_UNIQUE")
        start, end = entity["spanStart"], entity["spanEnd"]
        a._validate_span(start, end, len(document.tokens))
        a.sentence_for_span(start, end, document.sentence_ranges)
        label = a._validate_entity_label(entity["entityType"])
        signature = (start, end, label)
        require(signature not in signatures, "DUPLICATE_PREDICTED_ENTITY_SIGNATURE")
        signatures.add(signature); entities[eid] = entity
        if entity["mentionText"] != " ".join(document.tokens[start:end+1]):
            rejected.add(eid)
            ledger.append({"recordKind": "entity", "recordID": eid, "reasonKind": "direct", "reason": REASON,
                           "recordSha256": a.sha256_bytes(a.canonical_json(entity))})
    relation_ids = set(); signatures = set()
    for relation in payload["relations"]:
        rid = relation["relationID"]
        require(rid.strip() and rid not in relation_ids, "PREDICTED_RELATION_ID_NOT_UNIQUE_OR_EMPTY")
        relation_ids.add(rid)
        head, tail = relation["sourceEntityID"], relation["targetEntityID"]
        require(head in entities and tail in entities, "RELATION_ENDPOINT_NOT_SAME_DOCUMENT_ENTITY")
        spans = [(entities[e]["spanStart"], entities[e]["spanEnd"]) for e in (head, tail)]
        require(a.sentence_for_span(*spans[0], document.sentence_ranges) == a.sentence_for_span(*spans[1], document.sentence_ranges), "RELATION_CROSSES_SENTENCE_BOUNDARY")
        signature = a.relation_signature(relation["relationType"], *spans)
        require(signature not in signatures, "DUPLICATE_PREDICTED_RELATION_SIGNATURE")
        signatures.add(signature)
        dependencies = sorted({head, tail} & rejected)
        if dependencies:
            ledger.append({"recordKind": "relation", "recordID": rid, "reasonKind": "dependency",
                           "reason": "ENDPOINT_ENTITY_EXCLUDED", "excludedEntityIDs": dependencies,
                           "recordSha256": a.sha256_bytes(a.canonical_json(relation))})
    retained = {"documentID": payload["documentID"],
                "entities": [deepcopy(e) for e in payload["entities"] if e["entityID"] not in rejected],
                "relations": [deepcopy(e) for e in payload["relations"] if not {e["sourceEntityID"], e["targetEntityID"]} & rejected]}
    a.validate_prediction(retained, document)
    for row in ledger:
        row.update(documentID=document.document_id, sourceOutputSha256=a.sha256_bytes(raw))
    return retained, ledger
