"""Validate, preserve, and summarize completed independent Step 8 reviews.

This deterministic materializer accepts only the two role-bound production exports.
It preserves their received bytes and prepares agreement/disagreement artifacts; it
does not adjudicate, edit a judgment, or assemble a positive reference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from src.annotation.publication_step8 import INTERFACE_VERSION
from src.annotation.publication_step8.contracts import (DUPLICATE_DECISIONS, JUDGMENTS, PACKAGES,
                                                         ReviewInputs, digest, evidence_contexts)
from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


M2 = Path("data/curation/papers/m2")
OUTPUT_ROOT = M2 / "publication_step8_human_review"
DISTRIBUTION_MANIFEST = M2 / "publication_step8_review_distribution_manifest_v1.0.1.json"
AUTHORITY_FREEZE = M2 / "publication_step5_evaluation_authority_freeze_v0.1.4.json"
AUTHORITY_DOC = Path("docs/publication_step5_evaluation_authority_v0.1.4.md")
AMENDMENT_DOC = Path("docs/study2_evaluation_protocol_amendment_v0.3.md")
DEFAULT_INPUTS = (
    PROJECT_ROOT / "var/publication_step8_review/received/reviewer_1/review-session.json",
    PROJECT_ROOT / "var/publication_step8_review/received/reviewer_2/review-session.json",
)
OUTPUTS = {
    "reviewer_1": OUTPUT_ROOT / "publication_step8_initial_review_reviewer_1_v1.0.0.json",
    "reviewer_2": OUTPUT_ROOT / "publication_step8_initial_review_reviewer_2_v1.0.0.json",
    "preservation": OUTPUT_ROOT / "publication_step8_initial_review_preservation_record_v1.0.0.json",
    "agreement": OUTPUT_ROOT / "publication_step8_initial_review_agreement_v1.0.0.json",
    "agreement_markdown": OUTPUT_ROOT / "publication_step8_initial_review_agreement_v1.0.0.md",
    "disagreements": OUTPUT_ROOT / "publication_step8_prereconciliation_disagreement_package_v1.0.0.json",
}
CATEGORIES = tuple(JUDGMENTS)


class Step8InitialReviewError(ValueError):
    """Report an input, binding, or immutable-output failure without repair."""


def _binding(path: Path, root: Path = PROJECT_ROOT) -> dict[str, str]:
    """Return a repository-relative exact-byte binding."""

    return {"path": path.as_posix(), "sha256": sha256_bytes((root / path).read_bytes())}


def _artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Attach a canonical self-hash to one generated artifact."""

    body = dict(payload)
    body["artifactSha256"] = sha256_bytes(canonical_json(body))
    return body


def _write_immutable(path: Path, data: bytes) -> None:
    """Write exact bytes once, rejecting any divergent pre-existing output."""

    if path.exists() and path.read_bytes() != data:
        raise Step8InitialReviewError(f"OUTPUT_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object without deriving identity from its filesystem location."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Step8InitialReviewError(f"RECEIVED_REVIEW_INVALID:{path.name}") from exc
    if not isinstance(value, dict):
        raise Step8InitialReviewError(f"RECEIVED_REVIEW_INVALID:{path.name}")
    return value


def _load_distribution(root: Path) -> dict[str, Any]:
    """Load the self-hashed accepted distribution manifest."""

    path = root / DISTRIBUTION_MANIFEST
    payload = _load_json(path)
    observed = payload.pop("artifactSha256", None)
    if observed != sha256_bytes(canonical_json(payload)):
        raise Step8InitialReviewError("DISTRIBUTION_MANIFEST_SELF_HASH_DRIFT")
    if payload.get("artifactVersion") != "1.0.1" or payload.get("interfaceVersion") != INTERFACE_VERSION:
        raise Step8InitialReviewError("DISTRIBUTION_MANIFEST_VERSION_DRIFT")
    bundles = payload.get("reviewerBundles")
    if not isinstance(bundles, dict) or set(bundles) != {"reviewer_1", "reviewer_2"}:
        raise Step8InitialReviewError("DISTRIBUTION_MANIFEST_IDENTITY_DRIFT")
    payload["artifactSha256"] = observed
    return payload


def _expected_package(role: str, root: Path) -> tuple[dict[str, Any], str]:
    """Load the exact accepted package bound to one reviewer role."""

    name, expected_hash = PACKAGES[role]
    path = root / "data/curation/papers/m2/publication_step8_blinded_adjudication" / name
    if not path.is_file() or digest(path.read_bytes()) != expected_hash:
        raise Step8InitialReviewError(f"ACCEPTED_PACKAGE_BINDING_DRIFT:{role}")
    payload = _load_json(path)
    if payload.get("artifactSha256") is None or payload["artifactSha256"] != sha256_bytes(canonical_json({key: value for key, value in payload.items() if key != "artifactSha256"})):
        raise Step8InitialReviewError(f"ACCEPTED_PACKAGE_SELF_HASH_DRIFT:{role}")
    return payload, expected_hash


def _validate_events(review: Mapping[str, Any], expected: Mapping[str, Any], item_ids: set[str]) -> None:
    """Verify append-only event identity and final judgment projection consistency."""

    revisions = review.get("revisions")
    revision = review.get("revision")
    if not isinstance(revision, int) or revision < 0 or not isinstance(revisions, list) or len(revisions) != revision:
        raise Step8InitialReviewError("REVIEW_REVISION_HISTORY_INVALID")
    replayed: dict[str, str] = {}
    for number, event in enumerate(revisions, 1):
        if not isinstance(event, dict) or event.get("revision") != number:
            raise Step8InitialReviewError("REVIEW_REVISION_HISTORY_INVALID")
        if any(event.get(key) != expected[key] for key in ("reviewerID", "reviewRole", "reviewSessionID")):
            raise Step8InitialReviewError("REVIEW_EVENT_IDENTITY_DRIFT")
        if event.get("action") == "judgment":
            if event.get("judgmentItemID") not in item_ids or event.get("judgment") not in CATEGORIES:
                raise Step8InitialReviewError("REVIEW_EVENT_JUDGMENT_DRIFT")
            replayed[event["judgmentItemID"]] = event["judgment"]
    if replayed != review["judgments"]:
        raise Step8InitialReviewError("REVIEW_EVENT_FINAL_JUDGMENT_DRIFT")


def validate_received(inputs: tuple[Path, Path] = DEFAULT_INPUTS, root: Path = PROJECT_ROOT) -> dict[str, dict[str, Any]]:
    """Fail closed unless two exact, complete role-bound production exports are present."""

    manifest = _load_distribution(root)
    expected_by_identity = {
        (bundle["reviewerID"], bundle["reviewRole"], bundle["reviewSessionID"]): bundle
        for bundle in manifest["reviewerBundles"].values()
    }
    if len(expected_by_identity) != 2:
        raise Step8InitialReviewError("DISTRIBUTION_MANIFEST_IDENTITY_DRIFT")
    validated: dict[str, dict[str, Any]] = {}
    for path in inputs:
        raw = path.read_bytes()
        review = _load_json(path)
        identity = tuple(review.get(key) for key in ("reviewerID", "reviewRole", "reviewSessionID"))
        bundle = expected_by_identity.get(identity)
        if bundle is None or identity[0] in validated:
            raise Step8InitialReviewError("REVIEWER_ROLE_SESSION_BINDING_DRIFT")
        role = identity[1]
        package, package_hash = _expected_package(role, root)
        binding = bundle.get("packageManifest", {})
        expected = {"reviewerID": identity[0], "reviewRole": role, "reviewSessionID": identity[2],
                    "inputPackageSha256": package_hash, "runtimeSha256": binding.get("runtimeSha256"),
                    "sourceInventorySha256": binding.get("sourceInventorySha256"), "interfaceVersion": INTERFACE_VERSION}
        if any(review.get(key) != value for key, value in expected.items()):
            raise Step8InitialReviewError(f"REVIEW_PRODUCTION_BINDING_DRIFT:{identity[0]}")
        if review.get("mode") != "production" or review.get("syntheticDryRun") is not False:
            raise Step8InitialReviewError(f"REVIEW_NOT_PRODUCTION:{identity[0]}")
        item_ids = {item["judgmentItemID"] for item in package.get("judgmentItems", [])}
        units = package.get("primarySourceUnitIDs", [])
        groups = {group["duplicateReviewGroupID"] for group in package.get("duplicateReviewGroups", [])}
        judgments, duplicates = review.get("judgments"), review.get("duplicateDecisions")
        if (not isinstance(judgments, dict) or set(judgments) != item_ids or len(item_ids) != 182
                or any(value not in CATEGORIES for value in judgments.values())):
            raise Step8InitialReviewError(f"REVIEW_JUDGMENT_MEMBERSHIP_DRIFT:{identity[0]}")
        if not isinstance(duplicates, dict) or set(duplicates) != groups or any(value not in DUPLICATE_DECISIONS for value in duplicates.values()):
            raise Step8InitialReviewError(f"REVIEW_DUPLICATE_MEMBERSHIP_DRIFT:{identity[0]}")
        complete = review.get("unitCompletion")
        if review.get("complete") is not True or not isinstance(complete, dict) or set(complete) != set(units) or not all(value is True for value in complete.values()):
            raise Step8InitialReviewError(f"REVIEW_COMPLETION_DRIFT:{identity[0]}")
        expected_endpoints = ReviewInputs(role, root=root).endpoint_bindings
        if review.get("currentPaperEndpointBindings") != expected_endpoints:
            raise Step8InitialReviewError(f"REVIEW_CURRENT_PAPER_BINDING_DRIFT:{identity[0]}")
        _validate_events(review, expected, item_ids)
        validated[identity[0]] = {"raw": raw, "sha256": sha256_bytes(raw), "review": review,
                                  "package": package, "bundle": bundle, "inputPath": str(path)}
    if set(validated) != {bundle["reviewerID"] for bundle in manifest["reviewerBundles"].values()}:
        raise Step8InitialReviewError("REVIEWER_SET_INCOMPLETE")
    first, second = (validated[reviewer] for reviewer in sorted(validated))
    if set(first["review"]["judgments"]) != set(second["review"]["judgments"]):
        raise Step8InitialReviewError("PAIRED_JUDGMENT_MEMBERSHIP_DRIFT")
    return validated


def _fraction(value: Fraction | None) -> dict[str, str] | None:
    """Represent a finite statistic exactly and with a concise decimal display."""

    if value is None:
        return None
    return {"fraction": f"{value.numerator}/{value.denominator}", "decimal": f"{float(value):.12f}"}


def _agreement(items: list[dict[str, Any]], judgments_a: Mapping[str, str], judgments_b: Mapping[str, str]) -> dict[str, Any]:
    """Compute the predeclared three-category nominal agreement for one stratum."""

    matrix = {left: {right: 0 for right in CATEGORIES} for left in CATEGORIES}
    for item in items:
        left, right = judgments_a[item["judgmentItemID"]], judgments_b[item["judgmentItemID"]]
        matrix[left][right] += 1
    denominator = len(items)
    rows = {category: sum(matrix[category].values()) for category in CATEGORIES}
    columns = {category: sum(matrix[left][category] for left in CATEGORIES) for category in CATEGORIES}
    matches = sum(matrix[category][category] for category in CATEGORIES)
    expected_numerator = sum(rows[category] * columns[category] for category in CATEGORIES)
    observed = Fraction(matches, denominator)
    expected = Fraction(expected_numerator, denominator * denominator)
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    return {"pairedItemCount": denominator, "categories": list(CATEGORIES), "confusionCounts": matrix,
            "rowMarginals": rows, "columnMarginals": columns,
            "observedAgreement": {"matchingPairs": matches, "proportion": _fraction(observed)},
            "expectedAgreement": _fraction(expected), "cohensKappa": _fraction(kappa),
            "kappaUndefinedReason": "all expected agreement is one" if kappa is None else None}


def _agreement_markdown(agreement: Mapping[str, Any]) -> bytes:
    """Render a concise, deterministic report without reconciliation conclusions."""

    lines = ["# Step 8 initial-review agreement", "", "Pre-reconciliation candidate-support agreement on the fixed 182-item pool. This is not extraction IAA and does not replace Human Core reliability.", ""]
    for name in ("overall", "nodes", "relations"):
        value = agreement["strata"][name]
        observed = value["observedAgreement"]["proportion"]
        kappa = value["cohensKappa"] or {"decimal": "undefined"}
        lines.extend([f"## {name.title()}", "", f"Paired items: {value['pairedItemCount']}; observed agreement: {observed['decimal']} ({observed['fraction']}); Cohen's kappa: {kappa['decimal']}", "",
                      "| reviewer A \\ reviewer B | " + " | ".join(value["categories"]) + " | total |", "|---|" + "---|" * (len(value["categories"]) + 1)])
        for category in value["categories"]:
            lines.append("| " + category + " | " + " | ".join(str(value["confusionCounts"][category][column]) for column in value["categories"]) + f" | {value['rowMarginals'][category]} |")
        lines.append("| total | " + " | ".join(str(value["columnMarginals"][column]) for column in value["categories"]) + f" | {value['pairedItemCount']} |")
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def build(inputs: tuple[Path, Path] = DEFAULT_INPUTS, root: Path = PROJECT_ROOT) -> dict[str, bytes]:
    """Validate returns then build immutable preservation, agreement, and disagreement bytes."""

    validated = validate_received(inputs, root)
    primary, second = validated["reviewer_1"], validated["reviewer_2"]
    items = {item["judgmentItemID"]: item for item in primary["package"]["judgmentItems"]}
    ordered_items = [items[key] for key in sorted(items)]
    strata = {"overall": ordered_items,
               "nodes": [item for item in ordered_items if item["recordKind"] == "node"],
               "relations": [item for item in ordered_items if item["recordKind"] == "relation"]}
    agreement = _artifact({"artifactType": "publication_step8_initial_review_agreement", "artifactVersion": "1.0.0",
                            "analysis": "unreconciled_paired_candidate_support_judgments_not_extraction_iaa",
                            "initialReviewArtifacts": [{"reviewerID": reviewer, "path": OUTPUTS[reviewer].as_posix(), "sha256": data["sha256"]}
                                                       for reviewer, data in sorted(validated.items())],
                            "strata": {name: _agreement(values, primary["review"]["judgments"], second["review"]["judgments"])
                                        for name, values in strata.items()}})
    disagreement_ids = [item["judgmentItemID"] for item in ordered_items
                        if primary["review"]["judgments"][item["judgmentItemID"]] != second["review"]["judgments"][item["judgmentItemID"]]]
    review_inputs = ReviewInputs("primary", root=root)
    disagreements = []
    for item_id in disagreement_ids:
        item = items[item_id]
        rendered = review_inputs._reviewer_item(deepcopy(item))
        primary_unit = item["primarySourceUnitID"]
        contexts = item["authorizedContextSourceUnitIDs"]
        disagreements.append({"judgmentItem": {**rendered, "paragraphContexts": evidence_contexts(rendered, review_inputs.sources)},
                              "primarySource": review_inputs.sources[primary_unit],
                              "authorizedContext": [review_inputs.sources[unit] for unit in contexts],
                              "blindedInitialJudgments": {"initialReviewA": primary["review"]["judgments"][item_id],
                                                          "initialReviewB": second["review"]["judgments"][item_id]}})
    disagreement = _artifact({"artifactType": "publication_step8_prereconciliation_disagreement_package", "artifactVersion": "1.0.0",
                              "accessScope": "blinded_reconciliation_only", "reviewerIdentityMappingIncluded": False,
                              "sourcePackage": {"path": (M2 / "publication_step8_blinded_adjudication" / PACKAGES["primary"][0]).as_posix(),
                                                "sha256": PACKAGES["primary"][1]},
                              "itemCount": len(disagreements), "items": disagreements,
                              "boundary": "Contains only differing initial judgments and their existing authorized assertion, evidence, source/context, and frozen target guidance. It does not adjudicate, alter either initial review, or create a positive reference."})
    manifest = _load_distribution(root)
    preservation = _artifact({"artifactType": "publication_step8_initial_review_preservation_record", "artifactVersion": "1.0.0",
                              "distributionManifest": _binding(DISTRIBUTION_MANIFEST, root),
                              "authorityFreeze": _binding(AUTHORITY_FREEZE, root), "authority": _binding(AUTHORITY_DOC, root),
                              "amendment": _binding(AMENDMENT_DOC, root),
                              "reviews": [{"reviewerID": reviewer, "preservedArtifact": OUTPUTS[reviewer].as_posix(),
                                           "receivedSha256": value["sha256"], "preservedSha256": value["sha256"],
                                           "exactReceivedBytesPreserved": True,
                                           "productionBinding": {key: value["review"][key] for key in ("reviewerID", "reviewRole", "reviewSessionID", "inputPackageSha256", "runtimeSha256", "sourceInventorySha256", "interfaceVersion")},
                                           "judgmentItemCount": len(value["review"]["judgments"]), "complete": value["review"]["complete"],
                                           "unitCompletion": value["review"]["unitCompletion"]}
                                          for reviewer, value in sorted(validated.items())],
                              "agreementArtifact": {"path": OUTPUTS["agreement"].as_posix(), "sha256": sha256_bytes(canonical_json(agreement) + b"\n")},
                              "disagreementPackage": {"path": OUTPUTS["disagreements"].as_posix(), "sha256": sha256_bytes(canonical_json(disagreement) + b"\n")},
                              "boundary": {"reconciliationOccurred": False, "positiveReferenceAssembled": False,
                                           "candidateAssertionsAltered": False, "providerModelCallsOccurred": False}})
    return {"reviewer_1": primary["raw"], "reviewer_2": second["raw"],
            "agreement": canonical_json(agreement) + b"\n", "agreement_markdown": _agreement_markdown(agreement),
            "disagreements": canonical_json(disagreement) + b"\n", "preservation": canonical_json(preservation) + b"\n"}


def materialize(inputs: tuple[Path, Path] = DEFAULT_INPUTS, root: Path = PROJECT_ROOT, output_root: Path | None = None) -> dict[str, Path]:
    """Write validated outputs only after every input passes; never repair a return."""

    artifacts = build(inputs, root)
    destinations = {key: (output_root / path.name if output_root else root / path) for key, path in OUTPUTS.items()}
    for key, path in destinations.items():
        _write_immutable(path, artifacts[key])
    return destinations


def main() -> int:
    """Materialize the received-review preservation boundary without adjudication."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", action="append", type=Path, dest="reviews")
    args = parser.parse_args()
    try:
        reviews = tuple(args.reviews) if args.reviews else DEFAULT_INPUTS
        if len(reviews) != 2:
            raise Step8InitialReviewError("EXACTLY_TWO_REVIEW_EXPORTS_REQUIRED")
        for name, path in materialize(reviews).items():
            print(f"{name}: {path.relative_to(PROJECT_ROOT)}")
        return 0
    except (Step8InitialReviewError, OSError, ValueError) as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
