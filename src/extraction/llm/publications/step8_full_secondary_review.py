"""Freeze prospective 6/6 replication by copying the accepted blinded primary.

This successor never rebuilds candidates or writes historical Step 8B artifacts.
Run with ``python -m src.extraction.llm.publications.step8_full_secondary_review``.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .request_builder import PROJECT_ROOT, canonical_json, sha256_bytes
from .step8_blinded_adjudication import (
    AUTHORITY, AUTHORITY_SHA256, FILES, OUTPUT_ROOT, POOL, POOL_SHA256,
    SUBSET, SUBSET_SHA256, Step8BlindingError, _artifact, _load, _self_hash,
    _write_immutable,
)

M2 = Path("data/curation/papers/m2")
AUTHORITY_DOC = Path("docs/publication_step5_evaluation_authority_v0.1.4.md")
AMENDMENT_DOC = Path("docs/study2_evaluation_protocol_amendment_v0.3.md")
SELECTION = M2 / "step5_freeze/publication_pool_n6_selection_freeze_v0.1.1.json"
PACKAGE_DIR = OUTPUT_ROOT.relative_to(PROJECT_ROOT)
PRIMARY = PACKAGE_DIR / FILES["primary"]
PRIMARY_SHA256 = "112f14e3a9093ce8acc7fd47b06f150a01ba579dac641e7baad1956818fbe2f7"
OUTPUTS = {
    "scope": M2 / "step5_freeze/publication_pool_secondary_review_scope_freeze_v0.1.4.json",
    "secondary": PACKAGE_DIR / "publication_step8b_blinded_second_review_v1.1.0.json",
    "instructions": PACKAGE_DIR / "publication_step8b_reviewer_instructions_v1.1.0.json",
    "freeze": M2 / "publication_step5_evaluation_authority_freeze_v0.1.4.json",
}
PRESERVED = {
    PRIMARY: PRIMARY_SHA256,
    SELECTION: "dd223f47ee33d9546dd5915965ab3864030cca074afee8810fa82d0db34d7189",
    AUTHORITY.relative_to(PROJECT_ROOT): AUTHORITY_SHA256,
    SUBSET.relative_to(PROJECT_ROOT): SUBSET_SHA256,
    POOL.relative_to(PROJECT_ROOT): POOL_SHA256,
    PACKAGE_DIR / FILES["secondary"]: "f6c75ff80675ef2e940f2a6aa402c3df554c41bbb21aef6e85f6ea3bf7fdff2c",
    PACKAGE_DIR / FILES["mapping"]: "6ba24afe7ee4a37313c6307f5a6a2974b0a69cb1af7f344198378d655b699c7b",
    PACKAGE_DIR / FILES["instructions"]: "ffc16a7a14e19249720e587dd7f769e92cf6aa0e32a11d0c57e66ba39e33716f",
    Path("docs/publication_step5_evaluation_authority_v0.1.1.md"): "f946b6d9a6cc0928bd575f6eefffaab68d70d905fff9deaae2db1cd984fa83c3",
    Path("docs/publication_step5_evaluation_authority_v0.1.2.md"): "291b70577ad37b7df274df72cd2ccc1f8c9841cce8cf0240d4b7fd07eb27ffd2",
    Path("docs/publication_step5_evaluation_authority_v0.1.3.md"): "8e8c15404bef55efedfcf493d751c3841913456a15a621f50add18179c9d824c",
    Path("docs/study2_evaluation_protocol_amendment_v0.2.md"): "0686df5eff1ae393a710ba8ae2def39b3c53a7b6e675cf6584fc6a2c3511fe37",
    M2 / "publication_step5_evaluation_authority_freeze_v0.1.1.json": "4e5dffb3f391346fe5fb0f68e8c1d743ad8a4f248d8816a368e642a3fa1767c5",
    M2 / "publication_step5_evaluation_authority_freeze_v0.1.2.json": "cf270611e6bec11765c1d0c4a2c719275861f32373fba3955a31dbe11769349b",
}


def binding(path: Path, root: Path = PROJECT_ROOT) -> dict[str, str]:
    """Bind an existing file by its repository-relative path and exact bytes."""

    return {"path": path.as_posix(), "sha256": sha256_bytes((root / path).read_bytes())}


def generated_binding(path: Path, value: dict[str, Any]) -> dict[str, str]:
    """Bind the canonical output bytes before writing a new artifact."""

    return {"path": path.as_posix(), "sha256": sha256_bytes(canonical_json(value) + b"\n"),
            "artifactSha256": value["artifactSha256"]}


def build(root: Path = PROJECT_ROOT) -> dict[str, dict[str, Any]]:
    """Build the narrow successor and fail closed on accepted-input drift."""

    for path, expected in PRESERVED.items():
        if not (root / path).is_file() or binding(path, root)["sha256"] != expected:
            raise Step8BlindingError(f"FROZEN_BINDING_DRIFT:{path}")
    primary = _load(root / PRIMARY, PRIMARY_SHA256)
    selection = _load(root / SELECTION, PRESERVED[SELECTION])
    predecessor = _load(root / AUTHORITY.relative_to(PROJECT_ROOT), AUTHORITY_SHA256)
    old_instructions = _load(root / PACKAGE_DIR / FILES["instructions"], PRESERVED[PACKAGE_DIR / FILES["instructions"]])
    if not all(_self_hash(value) for value in (primary, selection, old_instructions)):
        raise Step8BlindingError("FROZEN_SELF_HASH_DRIFT")
    units = sorted(row["primarySourceUnitID"] for row in selection["selectedUnits"])
    items = primary["judgmentItems"]
    if (len(units) != len(set(units)) or primary["primarySourceUnitIDs"] != units
            or {item["primarySourceUnitID"] for item in items} != set(units)
            or len({item["judgmentItemID"] for item in items}) != len(items)):
        raise Step8BlindingError("PRIMARY_SELECTION_OR_ITEM_BINDING_DRIFT")

    scope = _artifact({
        "artifactType": "publication_pool_secondary_review_scope_freeze", "artifactVersion": "0.1.4",
        "status": "frozen_closed", "coverage": "all_accepted_primary_units_and_items",
        "authority": binding(AUTHORITY_DOC, root), "amendment": binding(AMENDMENT_DOC, root),
        "selection": binding(SELECTION, root), "acceptedPrimaryPackage": binding(PRIMARY, root),
        "preservedHistoricalSubset": binding(SUBSET.relative_to(PROJECT_ROOT), root),
        "selectedPrimarySourceUnitIDs": units,
        "judgmentItemIDs": [item["judgmentItemID"] for item in items],
        "unitCount": len(units), "itemCount": len(items),
        "recordKindCounts": dict(sorted(Counter(item["recordKind"] for item in items).items())),
        "duplicateReviewGroupCount": len(primary["duplicateReviewGroups"]),
        "independentInitialReviewsBeforeReconciliation": True,
        "authorizationCheckpoint": "2f28cbe7825b1320635dc68976b572e88e2202b4",
        "authorizationTiming": "before_any_step8_production_judgment_or_activation_file",
    })
    secondary_body = deepcopy(primary)
    secondary_body.pop("artifactSha256")
    secondary_body.update(artifactType="publication_step8b_blinded_second_review", artifactVersion="1.1.0")
    secondary = _artifact(secondary_body)
    instructions_body = deepcopy(old_instructions)
    instructions_body.pop("artifactSha256")
    instructions_body.update(
        artifactVersion="1.1.0",
        reviewScope="Each reviewer independently judges all assertions across the same six primary units using cited evidence and authorized context. Complete both initial reviews before reconciliation; preserve both originals.",
        summary={"primaryUnits": len(units), "primaryItems": len(items), "secondReviewUnits": len(units),
                 "secondReviewItems": len(items), "duplicateReviewGroups": len(primary["duplicateReviewGroups"])},
    )
    instructions = _artifact(instructions_body)
    retained_bindings = deepcopy(predecessor["frozenBindings"])
    retained_bindings.pop("secondaryReviewSubset")
    freeze = _artifact({
        "artifactType": "publication_step5_evaluation_authority_freeze_record", "recordVersion": "0.1.4",
        "status": "frozen_closed", "methodologicalChange": "prospective_step8_secondary_review_coverage_only",
        "authority": {**binding(AUTHORITY_DOC, root), "authorityID": "publication-step5-evaluation-authority", "version": "0.1.4"},
        "amendment": {**binding(AMENDMENT_DOC, root), "version": "0.3"},
        "preservedBindings": [{"path": path.as_posix(), "sha256": expected} for path, expected in sorted(PRESERVED.items())],
        "retainedFrozenBindings": retained_bindings,
        "secondaryReviewScope": generated_binding(OUTPUTS["scope"], scope),
        "primaryReviewPackage": binding(PRIMARY, root),
        "secondaryReviewPackage": generated_binding(OUTPUTS["secondary"], secondary),
        "reviewerInstructions": generated_binding(OUTPUTS["instructions"], instructions),
        "materializer": binding(Path(__file__).resolve().relative_to(PROJECT_ROOT), root),
        "executionBoundary": {"productionJudgmentsCreated": False, "productionActivationFilesCreated": False,
                              "providerModelCallsOccurred": False, "candidateRegenerationOccurred": False,
                              "reconciliationOccurred": False, "positiveReferenceAssembled": False},
    })
    return {"scope": scope, "secondary": secondary, "instructions": instructions, "freeze": freeze}


def materialize(root: Path = PROJECT_ROOT) -> dict[str, Path]:
    """Write only new versioned artifacts, with immutable/idempotent output checks."""

    artifacts = build(root)
    # Check every destination before writing any successor artifact.
    for key, relative in OUTPUTS.items():
        path = root / relative
        if path.exists() and path.read_bytes() != canonical_json(artifacts[key]) + b"\n":
            raise Step8BlindingError(f"OUTPUT_ARTIFACT_CONFLICT:{relative}")
    for key, relative in OUTPUTS.items():
        _write_immutable(root / relative, artifacts[key])
    return {key: root / relative for key, relative in OUTPUTS.items()}


if __name__ == "__main__":
    for name, path in materialize().items():
        print(f"{name}: {path.relative_to(PROJECT_ROOT)}")
