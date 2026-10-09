"""In-memory HydroShare abstract units under frozen Step 11 v0.3 §§2–3.

Callers supply a frozen resource, an accepted DatasetResource endpoint and a
snapshot ID. No files, corpus, provider or graph are accessed. Read/binding status
is technical only: this module never evaluates semantic evidence or abstention.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans


CONTRACT_ID = "study2-step11-semantic-contracts/v0.3"


def _line_at(text: str, offset: int) -> int:
    """Return a one-based line at a code-point offset; CRLF is one break."""
    return 1 + sum(match.end() <= offset for match in re.finditer(r"\r\n|\r|\n", text))


@dataclass(frozen=True)
class AbstractSourceUnit:
    """One exact abstract field, not a Section or semantic graph assertion.

    Offsets are zero-based, half-open Unicode-code-point positions in ``text``.
    End lines refer to the last included character (line 1 for empty text).
    ``snapshot_id`` identifies caller-supplied provenance, not verified acquisition.
    """

    resource_id: str
    snapshot_id: str
    source_version: str | None
    text: str
    source_unit_id: str
    authority_text_sha256: str
    expected_authority_text_sha256: str | None
    integrity_status: str
    artifact_family: str = "hydroshare"

    def to_record(self) -> dict[str, Any]:
        """Return detached metadata with exact field authority and coordinates."""
        return {
            "contractID": CONTRACT_ID,
            "artifactFamily": self.artifact_family,
            "canonicalArtifactID": self.resource_id,
            "resource_id": self.resource_id,
            "sourceUnitID": self.source_unit_id,
            "snapshotID": self.snapshot_id,
            "sourceVersion": self.source_version,
            "sourceField": "abstract",
            "sourceLocation": f"{self.resource_id}:abstract",
            "text": self.text,
            "authorityTextSha256": self.authority_text_sha256,
            "expectedAuthorityTextSha256": self.expected_authority_text_sha256,
            "integrityStatus": self.integrity_status,
            "startOffsetInAuthority": 0,
            "endOffsetInAuthority": len(self.text),
            "startLine": 1,
            "endLine": _line_at(self.text, max(0, len(self.text) - 1)),
        }


def build_abstract_source_unit(
    resource: Mapping[str, Any],
    *,
    accepted_owner_id: str,
    provenance: Mapping[str, Any],
    required: bool = True,
    expected_authority_text_sha256: str | None = None,
) -> dict[str, Any]:
    """Build one unit from a supplied record, without normalizing its abstract.

    ``provenance`` requires a nonempty ``snapshotID``; ``sourceVersion`` is optional.
    The accepted owner must equal ``resource_id`` exactly. Absent/null optional
    abstracts are skipped; malformed present values fail even when optional.
    Empty strings are successful reads, with no claim about semantic evidence.
    Expected digests, when supplied, are trusted lowercase SHA-256 text digests.
    """
    owner = resource.get("resource_id")
    snapshot = provenance.get("snapshotID")
    version = provenance.get("sourceVersion")
    context = {
        "artifactFamily": "hydroshare", "resource_id": owner,
        "acceptedOwnerID": accepted_owner_id, "sourceField": "abstract",
        "snapshotID": snapshot, "sourceVersion": version,
    }

    def failure(reason: str) -> dict[str, Any]:
        """Retain source identity on technical failure, without an absence claim."""
        return {"status": "failed_source_or_evidence_binding", "unit": None,
                "diagnostic": {**context, "reason": reason}, "inputComplete": False}

    if not isinstance(owner, str) or not owner or owner != accepted_owner_id:
        return failure("source_owner_mismatch")
    if not isinstance(snapshot, str) or not snapshot.strip():
        return failure("source_provenance_missing_or_malformed")
    if version is not None and (not isinstance(version, str) or not version.strip()):
        return failure("source_provenance_missing_or_malformed")
    expected = expected_authority_text_sha256
    if expected is not None and (
        not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None
    ):
        return failure("trusted_digest_malformed")
    text = resource.get("abstract")
    if text is None:
        if required:
            return failure("required_source_field_missing")
        return {"status": "optional_input_absent", "unit": None,
                "diagnostic": {**context, "reason": "optional_source_field_absent"},
                "inputComplete": True}
    if not isinstance(text, str):
        return failure("source_field_malformed")
    try:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        return failure("source_field_malformed")
    if expected is not None and digest != expected:
        result = failure("source_content_integrity_failure")
        result["diagnostic"].update({"authorityTextSha256": digest,
                                     "expectedAuthorityTextSha256": expected})
        return result
    identity = json.dumps([owner, snapshot, version, "abstract", 0, len(text), digest],
                          ensure_ascii=True, separators=(",", ":"))
    unit = AbstractSourceUnit(
        resource_id=owner, snapshot_id=snapshot, source_version=version, text=text,
        source_unit_id=f"hydroshare:{owner}:abstract:{hashlib.sha256(identity.encode()).hexdigest()}",
        authority_text_sha256=digest, expected_authority_text_sha256=expected,
        integrity_status="matched_trusted_digest" if expected is not None else "computed_only",
    )
    return {"status": "source_read_success", "unit": unit, "inputComplete": True}


def bind_abstract_evidence(unit: AbstractSourceUnit, evidence_spans: list[Any]) -> dict[str, Any]:
    """Bind supplied quotes with the unchanged Publication literal binder.

    The trusted unit must come from ``build_abstract_source_unit``. Only quotation
    and locator inputs reach the binder; supplied offsets/metadata cannot pass
    through. Null Section fields are compatibility placeholders, not ontology IDs.
    Any binding failure returns diagnostics and no usable bound spans. Originals
    remain caller-owned and unchanged. Binding success is not semantic acceptance.
    """
    payload = {"evidenceSpans": [
        {key: span[key] for key in ("evidenceText", "locatorAnchor") if key in span}
        if isinstance(span, Mapping) else span for span in evidence_spans
    ]}
    trusted = {
        "text": unit.text, "startOffsetInDocument": 0,
        "canonicalArtifactID": unit.resource_id, "sourceUnitID": unit.source_unit_id,
        "textHash": unit.authority_text_sha256, "sectionID": None, "sectionTitleRaw": None,
    }
    bound, report = bind_evidence_spans(payload, trusted)
    context = unit.to_record()
    context.pop("text")
    if report["bindingStatus"] != "bound":
        return {"status": "failed_source_or_evidence_binding", "evidenceSpans": [],
                "diagnostic": {**context, "reason": "evidence_quote_unbound"},
                "bindingReport": report}
    spans = []
    for span in bound["evidenceSpans"]:
        start, end = span["startOffsetInDocument"], span["endOffsetInDocument"]
        spans.append({
            **context, "evidenceText": span["evidenceText"],
            "evidenceHash": span["evidenceHash"],
            "startOffsetInAuthority": start, "endOffsetInAuthority": end,
            "startLine": _line_at(unit.text, start),
            "endLine": _line_at(unit.text, end - 1),
        })
    return {"status": "evidence_bound", "evidenceSpans": spans, "bindingReport": report}
