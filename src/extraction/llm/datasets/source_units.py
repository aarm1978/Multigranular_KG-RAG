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


def read_readme_source_units(
    readme: Mapping[str, Any] | None, *, accepted_owner_id: str,
    provenance: Mapping[str, Any], required: bool = False,
    expected_authority_text_sha256: str | None = None,
    sections: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read caller-supplied original README text, without acquisition/enrichment.

    The trusted readme supplies resource_id, source_path and text. Provenance
    supplies snapshotID, optional sourceVersion, and sourceVerified=True (a
    caller attestation, not independent acquisition verification). Optional
    sections are trusted original startOffsetInAuthority/endOffsetInAuthority
    bounds, with optional headingContext. They create no ontology Sections.
    Digest verification occurs only against a separately supplied expected hash.
    """
    from copy import deepcopy

    result: dict[str, Any] = {"status": "source_read_success", "authority": None,
                              "sourceUnits": [], "diagnostics": [], "inputComplete": True}

    def fail(reason: str) -> dict[str, Any]:
        """Distinguish malformed/present or required inputs from optional absence."""
        result.update(status="failed_source_or_evidence_binding", inputComplete=False)
        result["diagnostics"].append({"reason": reason, "resource_id": accepted_owner_id,
                                      "sourceField": "README"})
        return result

    if not isinstance(accepted_owner_id, str) or not accepted_owner_id.strip() or not isinstance(provenance, Mapping):
        return fail("source_provenance_missing_or_malformed")
    snapshot, version = provenance.get("snapshotID"), provenance.get("sourceVersion")
    if (not isinstance(snapshot, str) or not snapshot.strip()
            or version is not None and (not isinstance(version, str) or not version.strip())):
        return fail("source_provenance_missing_or_malformed")
    if readme is None:
        if required:
            return fail("required_readme_missing")
        result["status"] = "optional_input_absent"
        result["diagnostics"].append({"reason": "optional_readme_absent", "resource_id": accepted_owner_id})
        return result
    if not isinstance(readme, Mapping) or readme.get("resource_id") != accepted_owner_id:
        return fail("source_owner_mismatch")
    path, text = readme.get("source_path"), readme.get("text")
    if not isinstance(path, str) or not path.strip() or not isinstance(text, str):
        return fail("required_readme_field_missing_or_malformed")
    if provenance.get("sourceVerified") is not True:
        return fail("readme_source_not_verified")
    expected = expected_authority_text_sha256
    if expected is not None and (not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None):
        return fail("trusted_digest_malformed")
    try:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        return fail("source_text_malformed")
    if expected is not None and digest != expected:
        return fail("source_content_integrity_failure")
    base = {"contractID": CONTRACT_ID, "artifactFamily": "hydroshare", "resource_id": accepted_owner_id,
            "canonicalArtifactID": accepted_owner_id, "snapshotID": snapshot, "sourceVersion": version,
            "sourceField": "README", "source_path": path, "sourceLocation": f"{accepted_owner_id}:{path}",
            "authorityTextSha256": digest, "expectedAuthorityTextSha256": expected,
            "integrityStatus": "matched_trusted_digest" if expected is not None else "computed_only",
            "sourceVerification": "caller_attested", "acquisitionIntegrityStatus": "not_independently_verified"}
    result["authority"] = {**base, "text": text}
    selected = sections if sections is not None else ([{"startOffsetInAuthority": 0,
        "endOffsetInAuthority": len(text)}] if text else [])
    if not isinstance(selected, list):
        return fail("readme_sections_malformed")
    seen = set()
    for section in selected:
        if (not isinstance(section, Mapping) or set(section) - {
                "startOffsetInAuthority", "endOffsetInAuthority", "headingContext"}):
            return fail("readme_section_metadata_invalid")
        start, end = section.get("startOffsetInAuthority"), section.get("endOffsetInAuthority")
        heading = section.get("headingContext")
        if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
                or heading is not None and not isinstance(heading, str) or (start, end) in seen):
            return fail("readme_section_bounds_invalid")
        seen.add((start, end))
        identity = json.dumps([accepted_owner_id, snapshot, version, "README", path, digest, start, end],
                              ensure_ascii=True, separators=(",", ":"))
        result["sourceUnits"].append({**base, "text": text[start:end],
            "sourceUnitID": "hydroshare:readme:" + hashlib.sha256(identity.encode()).hexdigest(),
            "startOffsetInAuthority": start, "endOffsetInAuthority": end,
            "startLine": _line_at(text, start), "endLine": _line_at(text, end - 1),
            "headingContext": heading, "sectionID": None})
    return deepcopy(result)


def bind_readme_evidence(reader_result: Mapping[str, Any], source_unit_id: str,
                         evidence_spans: list[Any]) -> dict[str, Any]:
    """Bind literal quotes against a trusted README reader result, never semantics."""
    from copy import deepcopy

    result = {"status": "failed_source_or_evidence_binding", "evidenceSpans": [],
              "originalEvidence": deepcopy(evidence_spans), "diagnostics": []}

    def fail(reason: str) -> dict[str, Any]:
        """Return no bound evidence on input or authority failure."""
        result["diagnostics"].append({"reason": reason, "sourceUnitID": source_unit_id})
        return result

    if not isinstance(reader_result, Mapping) or reader_result.get("status") != "source_read_success":
        return fail("source_read_not_successful")
    authority, units = reader_result.get("authority"), reader_result.get("sourceUnits")
    if not isinstance(authority, Mapping) or not isinstance(units, list):
        return fail("reader_result_malformed")
    selected = [u for u in units if isinstance(u, Mapping) and u.get("sourceUnitID") == source_unit_id]
    if len(selected) != 1:
        return fail("source_unit_missing_or_ambiguous")
    unit = selected[0]
    replay = read_readme_source_units({"resource_id": authority.get("resource_id"),
        "source_path": authority.get("source_path"), "text": authority.get("text")},
        accepted_owner_id=authority.get("canonicalArtifactID"), provenance={
            "snapshotID": authority.get("snapshotID"), "sourceVersion": authority.get("sourceVersion"),
            "sourceVerified": authority.get("sourceVerification") == "caller_attested"},
        expected_authority_text_sha256=authority.get("expectedAuthorityTextSha256"),
        sections=[{k: unit.get(k) for k in ("startOffsetInAuthority", "endOffsetInAuthority", "headingContext")}])
    if replay["status"] != "source_read_success" or replay["authority"] != authority or replay["sourceUnits"] != [unit]:
        return fail("source_unit_integrity_or_provenance_mismatch")
    if (not isinstance(evidence_spans, list) or not evidence_spans or any(not isinstance(s, Mapping)
            or set(s) - {"evidenceText", "locatorAnchor"} for s in evidence_spans)):
        return fail("invalid_or_model_authored_evidence_metadata")
    bound, report = bind_evidence_spans({"evidenceSpans": evidence_spans}, {
        "text": unit["text"], "startOffsetInDocument": unit["startOffsetInAuthority"],
        "canonicalArtifactID": unit["canonicalArtifactID"], "sourceUnitID": source_unit_id,
        "textHash": hashlib.sha256(unit["text"].encode()).hexdigest(),
        "sectionID": None, "sectionTitleRaw": unit["headingContext"]})
    result["bindingReport"] = report
    if report["bindingStatus"] != "bound":
        return fail("evidence_quote_unbound")
    metadata = {k: deepcopy(v) for k, v in unit.items() if k != "text"}
    for span in bound["evidenceSpans"]:
        start, end = span["startOffsetInDocument"], span["endOffsetInDocument"]
        result["evidenceSpans"].append({**metadata, **span, "startOffsetInAuthority": start,
            "endOffsetInAuthority": end, "startLine": _line_at(authority["text"], start),
            "endLine": _line_at(authority["text"], end - 1)})
    result["status"] = "evidence_bound"
    return result
