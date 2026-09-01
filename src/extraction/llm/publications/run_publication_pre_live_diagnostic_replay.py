"""Run the no-call Publication pre-live diagnostic replay.

Only historical provider payload ``evidenceSpan.sectionTitle`` values are copied
to the exact trusted current request value.  The isolated outputs are explicitly
counterfactual transport emulations, never authentic model output or acceptance.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.model_authorable_schema import validate_model_authorable_payload  # noqa: E402
from src.extraction.llm.publications.request_builder import canonical_json, canonical_json_file, sha256_bytes  # noqa: E402
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (  # noqa: E402
    DEV_IDS,
    _validation_finding_code_counts,
    build_c1b_request,
    load_c0_bindings,
)
from src.extraction.llm.publications.run_publication_structured_development_smoke import _downstream  # noqa: E402
from src.extraction.llm.publications.run_publication_trusted_evidence_metadata_binding import (  # noqa: E402
    C1B_OUTPUT_DIR,
    _section_title_only_copy,
    _tree_snapshot,
)
from src.extraction.llm.publications.semantic_materializer import materialize_generic_mentions  # noqa: E402
from src.extraction.llm.publications.trusted_evidence_metadata_schema import derive_trusted_evidence_metadata_schema  # noqa: E402


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/pre_live_diagnostic_replay"
LABELS = {
    "artifactClass": "DEVELOPMENT_DIAGNOSTIC_REPLAY",
    "transportMethod": "COUNTERFACTUAL_TRANSPORT_EMULATION",
    "authenticity": "NOT_AUTHENTIC_NEW_MODEL_OUTPUT",
    "goldStatus": "NOT_GOLD",
    "evaluationStatus": "NOT_FORMAL_EVALUATION",
    "providerCalls": 0,
    "modelCallMade": False,
}
ACCEPTANCE_BASIS = "DEVELOPMENT_VALIDATOR_USABLE_PROXY"
ACCEPTANCE_STATUS = "NOT_FORMAL_ACCEPTANCE"


def _write(path: Path, value: Mapping[str, Any]) -> None:
    """Write one deterministic diagnostic JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _c1b_raw_path(development_id: str) -> Path:
    """Return one immutable authentic raw semantic payload path."""

    token = development_id.lower().replace("-", "")
    return C1B_OUTPUT_DIR / development_id / f"publication_m2c1b_{token}_exact_structured_model_output.json"


def _status_counts(validation: Mapping[str, Any]) -> Counter[str]:
    """Count candidate validation dispositions."""

    counts: Counter[str] = Counter()
    for row in validation.get("recordResults", []):
        if row.get("recordType") in {"candidate_node", "candidate_edge"}:
            counts[str(row.get("candidateValidationStatus"))] += 1
    return counts


def _accepted_proxy(
    request: Mapping[str, Any], parser: Mapping[str, Any], validation: Mapping[str, Any], usable: Mapping[str, Any]
) -> dict[str, Any]:
    """Adapt V12-usable nodes to the neutral non-formal accepted interface."""

    envelope = parser.get("parsedEnvelope", {})
    evidence_by_id = {
        str(row["evidenceSpanID"]): row for row in envelope.get("evidenceSpans", [])
    }
    valid_ids = {
        str(row["evidenceSpanID"])
        for row in validation.get("evidenceResults", [])
        if row.get("valid") is True
    }
    paper_id = str(request["sourceArtifactID"])
    unit_id = str(request["primarySourceUnitID"])
    nodes: list[dict[str, Any]] = []
    for candidate in usable.get("candidateNodes", []):
        occurrences: list[dict[str, Any]] = []
        for evidence_id in candidate.get("evidenceSpanIDs", []):
            span = evidence_by_id[str(evidence_id)]
            occurrence = {
                key: deepcopy(span[key])
                for key in (
                    "evidenceSpanID", "sourceUnitID", "startOffsetInUnit", "endOffsetInUnit",
                    "startOffsetInDocument", "endOffsetInDocument",
                )
            }
            occurrence["canonicalPaperID"] = paper_id
            occurrence["valid"] = str(evidence_id) in valid_ids
            occurrences.append(occurrence)
        nodes.append(
            {
                "nodeID": f"{unit_id}#{candidate['candidateID']}",
                "candidateID": candidate["candidateID"],
                "className": candidate["className"],
                "ontologyClassID": candidate["ontologyClassID"],
                "accepted": True,
                "acceptanceBasis": ACCEPTANCE_BASIS,
                "acceptanceStatus": ACCEPTANCE_STATUS,
                "evidenceOccurrences": occurrences,
            }
        )
    return {
        "projectionVersion": "publication-accepted-semantic-projection/0.1.0",
        "acceptanceBasis": ACCEPTANCE_BASIS,
        "acceptanceStatus": ACCEPTANCE_STATUS,
        "developmentOnly": True,
        "paperEndpoints": [
            {
                "nodeID": paper_id,
                "canonicalPaperID": paper_id,
                "resolutionSource": "trusted_request.sourceArtifactID",
            }
        ],
        "acceptedNodes": nodes,
        "acceptedEdges": [],
    }


def run_replay(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Run all ten current-authority offline replays and semantic projections."""

    before = _tree_snapshot(C1B_OUTPUT_DIR)
    bindings = {str(row["developmentID"]): row for row in load_c0_bindings()}
    units: list[dict[str, Any]] = []
    for development_id in DEV_IDS:
        request = build_c1b_request(bindings[development_id])
        raw_path = _c1b_raw_path(development_id)
        authentic_raw = raw_path.read_bytes()
        payload = json.loads(authentic_raw)
        diagnostic, changes = _section_title_only_copy(
            payload, request["sourceUnit"]["sectionTitleRaw"]
        )
        schema = derive_trusted_evidence_metadata_schema(request)
        schema_findings = validate_model_authorable_payload(diagnostic, schema)
        if schema_findings:
            raise ValueError(f"{development_id} transport emulation violates current provider schema: {schema_findings}")
        emulated_raw = canonical_json(diagnostic)
        parser, _, validation, usable = _downstream(emulated_raw, request)
        projection = _accepted_proxy(request, parser, validation, usable)
        materialized = materialize_generic_mentions(projection)
        status = _status_counts(validation)
        evidence = list(validation.get("evidenceResults", []))
        class_counts = Counter(
            str(row["className"])
            for row in projection["acceptedNodes"]
            if any(
                edge["targetID"] == row["nodeID"]
                for edge in materialized["derivedEdges"]
                if edge["derivationKind"] == "paper_entity"
            )
        )
        discourse_node_ids = {
            row["nodeID"]
            for row in projection["acceptedNodes"]
            if any(edge["sourceID"] == row["nodeID"] for edge in materialized["derivedEdges"])
        }
        mentionable_ids = {
            edge["targetID"] for edge in materialized["derivedEdges"]
            if edge["derivationKind"] == "paper_entity"
        }
        counts = materialized["derivationCounts"]
        unit = {
            **LABELS,
            "developmentID": development_id,
            "currentRequestID": request["requestID"],
            "currentOntologyAuthority": request["authorities"]["ontology"],
            "authenticC1bRawSha256": sha256_bytes(authentic_raw),
            "changedField": "evidenceSpan.sectionTitle",
            "changedFieldCount": len(changes),
            "changedJsonPointers": [row["jsonPointer"] for row in changes],
            "allOtherAuthenticSemanticPayloadFieldsByteEquivalent": True,
            "postGenerationRepairApplied": False,
            "providerFacingSchemaAccepted": True,
            "totalCandidates": len(diagnostic.get("candidateNodes", [])) + len(diagnostic.get("candidateEdges", [])),
            "validatedCandidates": status["validated"],
            "rejectedCandidates": status["rejected"],
            "needsReviewCandidates": status["needs_review"],
            "supersededCandidates": status["superseded"],
            "deferredCandidates": status["deferred"],
            "usableNodes": len(usable.get("candidateNodes", [])),
            "evidenceSpanCount": len(evidence),
            "validEvidenceSpanCount": sum(row.get("valid") is True for row in evidence),
            "validationFindingCodeCounts": dict(sorted(_validation_finding_code_counts(validation).items())),
            "validationFindingCodes": sorted(_validation_finding_code_counts(validation)),
            "acceptanceBasis": ACCEPTANCE_BASIS,
            "acceptanceStatus": ACCEPTANCE_STATUS,
            "mentionableUsableEntityCount": len(mentionable_ids),
            "usableDiscourseNodeCount": len(discourse_node_ids),
            "paperGenericEdgeCountBeforeSuppression": counts["paperBeforeSuppression"],
            "paperGenericEdgeCountAfterSuppression": counts["paperAfterSuppression"],
            "discourseGenericEdgeCountBeforeSuppression": counts["discourseBeforeSuppression"],
            "discourseGenericEdgeCountAfterSuppression": counts["discourseAfterSuppression"],
            "exactCoordinateContainmentBindingCount": counts["exactCoordinateContainmentBindingCount"],
            "mentionableCountsByEntityClass": dict(sorted(class_counts.items())),
            "representativeDerivedEdges": materialized["derivedEdges"][:5],
        }
        unit_dir = output_dir / development_id
        token = development_id.lower().replace("-", "")
        _write(unit_dir / f"publication_pre_live_{token}_current_request.json", {**LABELS, "request": request})
        _write(unit_dir / f"publication_pre_live_{token}_transport_emulation.json", {**LABELS, "diagnosticPayload": diagnostic, "changes": changes})
        _write(unit_dir / f"publication_pre_live_{token}_validation.json", {**LABELS, "parser": parser, "validation": validation, "usable": usable})
        _write(unit_dir / f"publication_pre_live_{token}_accepted_proxy.json", {**LABELS, **projection})
        _write(unit_dir / f"publication_pre_live_{token}_generic_mentions.json", {**LABELS, **materialized})
        _write(unit_dir / f"publication_pre_live_{token}_summary.json", unit)
        units.append(unit)
    after = _tree_snapshot(C1B_OUTPUT_DIR)
    if canonical_json(before) != canonical_json(after):
        raise ValueError("immutable C1B bytes changed during pre-live replay")
    aggregate_codes: Counter[str] = Counter()
    for unit in units:
        aggregate_codes.update(unit["validationFindingCodeCounts"])
    result = {
        **LABELS,
        "recordVersion": "publication-pre-live-diagnostic-replay/0.1.0",
        "acceptanceBasis": ACCEPTANCE_BASIS,
        "acceptanceStatus": ACCEPTANCE_STATUS,
        "unitCount": len(units),
        "authenticC1bTreeByteIdentical": True,
        "authenticC1bTreeInventorySha256": before["treeInventorySha256"],
        "aggregateValidationFindingCodeCounts": dict(sorted(aggregate_codes.items())),
        "units": units,
    }
    _write(output_dir / "publication_pre_live_diagnostic_replay_summary.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Run deterministic diagnostic replay without a provider execution path."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    result = run_replay(args.output_dir)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
