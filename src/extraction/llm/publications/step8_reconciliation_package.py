"""Materialize the bounded, blinded Step 8 reconciliation input package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


M2 = Path("data/curation/papers/m2")
HUMAN = M2 / "publication_step8_human_review"
DISAGREEMENTS = HUMAN / "publication_step8_prereconciliation_disagreement_package_v1.0.0.json"
AGREEMENT = HUMAN / "publication_step8_initial_review_agreement_v1.0.0.json"
PRESERVATION = HUMAN / "publication_step8_initial_review_preservation_record_v1.0.0.json"
OUTPUT = M2 / "publication_step8_reconciliation/publication_step8_reconciliation_package_v1.0.0.json"
EXPECTED = {
    DISAGREEMENTS: "eba8d291afa2fbfb2b2941f1422810236ce09ba2279bc6c792f70f76c872f19d",
    AGREEMENT: "15174d2308f6663878c41cf5f514e8ebf8dd4a2926c962f6ffc484eea711e5b7",
    PRESERVATION: "d929c483037ef2752126fa771cc690709eb1d4854622da4106de9fb43661cd97",
}
FINAL_DECISIONS = ["supported_as_proposed", "not_supported_as_proposed", "insufficient_evidence_to_decide", "adjudication_unresolved"]


class Step8ReconciliationPackageError(ValueError):
    """Report frozen-input drift or an immutable package output conflict."""


def _load(path: Path, root: Path) -> dict[str, Any]:
    """Load an exact frozen JSON artifact and verify its canonical self-hash."""

    full = root / path
    if not full.is_file() or sha256_bytes(full.read_bytes()) != EXPECTED[path]:
        raise Step8ReconciliationPackageError(f"FROZEN_BINDING_DRIFT:{path.name}")
    value = json.loads(full.read_text(encoding="utf-8"))
    body = dict(value)
    observed = body.pop("artifactSha256", None)
    if observed != sha256_bytes(canonical_json(body)):
        raise Step8ReconciliationPackageError(f"FROZEN_SELF_HASH_DRIFT:{path.name}")
    return value


def _binding(path: Path) -> dict[str, str]:
    """Represent an exact frozen artifact binding."""

    return {"path": path.as_posix(), "sha256": EXPECTED[path]}


def build(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Build the exact 11-item reconciliation package without resolving any item."""

    disagreements, agreement, preservation = (_load(path, root) for path in (DISAGREEMENTS, AGREEMENT, PRESERVATION))
    items = disagreements.get("items")
    if (disagreements.get("accessScope") != "blinded_reconciliation_only" or not isinstance(items, list)
            or disagreements.get("itemCount") != 11 or len(items) != 11):
        raise Step8ReconciliationPackageError("DISAGREEMENT_PACKAGE_SCOPE_DRIFT")
    ids = [item.get("judgmentItem", {}).get("judgmentItemID") for item in items]
    if any(not isinstance(item_id, str) for item_id in ids) or len(set(ids)) != 11 or ids != sorted(ids):
        raise Step8ReconciliationPackageError("DISAGREEMENT_PACKAGE_MEMBERSHIP_DRIFT")
    if agreement.get("strata", {}).get("overall", {}).get("pairedItemCount") != 182:
        raise Step8ReconciliationPackageError("AGREEMENT_BINDING_DRIFT")
    if len(preservation.get("reviews", [])) != 2 or not all(row.get("exactReceivedBytesPreserved") is True for row in preservation["reviews"]):
        raise Step8ReconciliationPackageError("INITIAL_REVIEW_PRESERVATION_DRIFT")
    body = {"artifactType": "publication_step8_reconciliation_package", "artifactVersion": "1.0.0",
            "accessScope": "joint_blinded_reconciliation_only", "sourceDisagreementPackage": _binding(DISAGREEMENTS),
            "sourceAgreement": _binding(AGREEMENT), "initialReviewPreservation": _binding(PRESERVATION),
            "itemCount": 11, "judgmentItemIDs": ids, "allowedFinalDecisions": FINAL_DECISIONS,
            "items": items,
            "boundary": "Reconciliation may choose one authorized final status for each listed item only. It cannot edit, repair, relabel, reclassify, relink, add, or search beyond the authorized assertion/evidence/source/context package. It does not alter either initial review or its agreement analysis and does not assemble a positive reference."}
    body["artifactSha256"] = sha256_bytes(canonical_json(body))
    return body


def materialize(root: Path = PROJECT_ROOT) -> Path:
    """Write the deterministic reconciliation package without overwriting divergence."""

    artifact = build(root)
    data = canonical_json(artifact) + b"\n"
    path = root / OUTPUT
    if path.exists() and path.read_bytes() != data:
        raise Step8ReconciliationPackageError("OUTPUT_ARTIFACT_CONFLICT")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


if __name__ == "__main__":
    print(materialize().relative_to(PROJECT_ROOT))
