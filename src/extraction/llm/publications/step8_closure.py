"""Deterministic reconciliation intake and candidate-conditioned Step 8 assembly.

Consumes immutable human exports, never recomputes their agreement, and derives
the expected reconciliation runtime from the shipped distribution manifest.
Run with ``python -m src.extraction.llm.publications.step8_closure``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
M2 = Path("data/curation/papers/m2")
HUMAN = M2 / "publication_step8_human_review"
RECON = M2 / "publication_step8_reconciliation"
OUT = M2 / "publication_step8_final_evaluation"
BLIND = M2 / "publication_step8_blinded_adjudication"
INTAKE = Path("var/publication_step8_review/received/reconciliation/STEP8_FINAL_RECONCILIATION.json")
CATEGORIES = ("supported_as_proposed", "not_supported_as_proposed", "insufficient_evidence_to_decide", "adjudication_unresolved")
PATHS = {
    "manifest": RECON / "publication_step8_reconciliation_distribution_manifest_v1.0.1.json",
    "package": RECON / "publication_step8_reconciliation_package_v1.0.0.json",
    "disagreements": HUMAN / "publication_step8_prereconciliation_disagreement_package_v1.0.0.json",
    "agreement": HUMAN / "publication_step8_initial_review_agreement_v1.0.0.json",
    "agreementMarkdown": HUMAN / "publication_step8_initial_review_agreement_v1.0.0.md",
    "initialPreservation": HUMAN / "publication_step8_initial_review_preservation_record_v1.0.0.json",
    "reviewer_1": HUMAN / "publication_step8_initial_review_reviewer_1_v1.0.0.json",
    "reviewer_2": HUMAN / "publication_step8_initial_review_reviewer_2_v1.0.0.json",
    "primary": BLIND / "publication_step8b_blinded_primary_review_v1.0.0.json",
    "secondary": BLIND / "publication_step8b_blinded_second_review_v1.1.0.json",
    "lineage": BLIND / "publication_step8b_internal_opaque_lineage_map_v1.0.0.json",
    "pool": M2 / "publication_step8_internal_candidate_pool/publication_step8_internal_pre_review_candidate_pool_v1.0.1.json",
    "authorityFreeze": M2 / "publication_step5_evaluation_authority_freeze_v0.1.4.json",
    "authority": Path("docs/publication_step5_evaluation_authority_v0.1.4.md"),
    "amendment": Path("docs/study2_evaluation_protocol_amendment_v0.3.md"),
    **{f"predecessor{v}": Path(f"docs/publication_step5_evaluation_authority_v0.1.{v}.md") for v in (1, 2, 3)},
}
HASHES = {
    "manifest": "02089c08b2db3790878311d09319342447315ecd323a3e4b43a3403f0d2ba4d6",
    "package": "5e8029cf39444666c47561a837335c1cb436da33607761ea322fc8e19347269f",
    "disagreements": "eba8d291afa2fbfb2b2941f1422810236ce09ba2279bc6c792f70f76c872f19d",
    "agreement": "15174d2308f6663878c41cf5f514e8ebf8dd4a2926c962f6ffc484eea711e5b7",
    "agreementMarkdown": "7f432b032354d336f6dcdb16f2edb7122ef5464640da6afb3da0c996cfdf9964",
    "initialPreservation": "d929c483037ef2752126fa771cc690709eb1d4854622da4106de9fb43661cd97",
    "reviewer_1": "3fd1ef5891a1b1916ddda6c30f94d23ed56491abc39a23eb311e767c876f06e8",
    "reviewer_2": "a95b38970c8e35c2ca50d33f41960d9a105fd674d6af0c1983a30847b8738244",
    "primary": "112f14e3a9093ce8acc7fd47b06f150a01ba579dac641e7baad1956818fbe2f7",
    "secondary": "628bb07cfb5dd0a6df59fb367aec6b46492760b356dc380b64637d0e7b063983",
    "lineage": "6ba24afe7ee4a37313c6307f5a6a2974b0a69cb1af7f344198378d655b699c7b",
    "pool": "feb045ca031f1d40743725d70c57f9f613ea11df1f720481f97447944d9e12f7",
    "authorityFreeze": "c63fb5eb94338a5a40ccdfeb475d17be9b512084f9f74f29bd5f38ae72974fb4",
    "authority": "eee9e03afdc0c9104612cb38476acfe79f55a7d83f15ab2083fe9c22f44b7c1d",
    "amendment": "a19830b669b4cca82383f29e08ca5d663d0e839b20142423a8101c0c8ae5dc4c",
    "predecessor1": "f946b6d9a6cc0928bd575f6eefffaab68d70d905fff9deaae2db1cd984fa83c3",
    "predecessor2": "291b70577ad37b7df274df72cd2ccc1f8c9841cce8cf0240d4b7fd07eb27ffd2",
    "predecessor3": "8e8c15404bef55efedfcf493d751c3841913456a15a621f50add18179c9d824c",
}
OUTPUTS = {
    "received": RECON / "publication_step8_joint_reconciliation_export_v1.0.0.json",
    "preservation": RECON / "publication_step8_joint_reconciliation_preservation_v1.0.0.json",
    "ledger": OUT / "publication_step8_final_outcome_ledger_v1.0.0.json",
    "positive": OUT / "publication_step8_positive_pooled_reference_v1.0.0.json",
    "exclusions": OUT / "publication_step8_nonpositive_outcomes_v1.0.0.json",
    "summary": OUT / "publication_step8_final_summary_v1.0.0.md",
    "closure": OUT / "publication_step8_closure_freeze_v1.0.0.json",
}


class ClosureError(ValueError):
    """Reject drift, malformed intake, or incomplete assembly without repairs."""


def sha(data: bytes) -> str:
    """Hash exact bytes."""
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    """Serialize stable JSON with the shipped canonical convention."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def strict_json(data: bytes) -> dict[str, Any]:
    """Reject malformed JSON, duplicate keys at any depth, and non-JSON constants."""
    def pairs(entries: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in entries:
            if key in result:
                raise ClosureError(f"DUPLICATE_JSON_KEY:{key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ClosureError(f"INVALID_JSON_CONSTANT:{value}")

    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ClosureError("MALFORMED_JSON") from exc
    if not isinstance(result, dict):
        raise ClosureError("JSON_OBJECT_REQUIRED")
    return result


def binding(key: str) -> dict[str, str]:
    """Bind one accepted input by path and exact bytes."""
    return {"path": PATHS[key].as_posix(), "sha256": HASHES[key]}


def load_inputs(root: Path = ROOT) -> dict[str, Any]:
    """Validate frozen bytes without replaying reviews or recalculating agreement."""
    result = {}
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if sha(data) != HASHES[key]:
            raise ClosureError(f"FROZEN_BINDING_DRIFT:{path}")
        if path.suffix == ".json":
            value = strict_json(data)
            if "artifactSha256" in value:
                body = {k: v for k, v in value.items() if k != "artifactSha256"}
                if sha(canonical(body)) != value["artifactSha256"]:
                    raise ClosureError(f"SELF_HASH_DRIFT:{path}")
            result[key] = value
    return result


def shipped_runtime_hash(manifest: dict[str, Any]) -> str:
    """Reproduce shipped reconciliation_app.runtime_hash using manifest file hashes.

    The accepted exporter hashes a basename-to-SHA mapping of its two Python
    modules plus app.js, index.html, and style.css (no trailing newline).
    It does not hash the distribution builder, launcher, or current repository.
    """
    paths = ("runtime/reconciliation.py", "runtime/reconciliation_app.py",
             "runtime/reconciliation_static/app.js", "runtime/reconciliation_static/index.html",
             "runtime/reconciliation_static/style.css")
    files = manifest["packageManifest"]["files"]
    if any(path not in files for path in paths):
        raise ClosureError("SHIPPED_RUNTIME_BINDING_ABSENT")
    return sha(canonical({Path(path).name: files[path] for path in paths}))


def validate_intake(raw: bytes, frozen: dict[str, Any]) -> dict[str, Any]:
    """Validate exactly the fields emitted by the accepted reconciliation exporter."""
    value = strict_json(raw)
    expected = {"exportType": "publication_step8_final_reconciliation", "exportVersion": "1.0.0",
                "complete": True, "itemCount": 11, "reconciliationPackageSha256": HASHES["package"],
                "sourceDisagreementPackage": binding("disagreements"), "sourceAgreement": binding("agreement"),
                "runtimeSha256": shipped_runtime_hash(frozen["manifest"])}
    if set(value) != {*expected, "finalDecisions"}:
        raise ClosureError("EXPORT_SCHEMA_FIELDS_DRIFT")
    for key, wanted in expected.items():
        if type(value[key]) is not type(wanted) or value[key] != wanted:
            raise ClosureError(f"EXPORT_BINDING_OR_SCHEMA_DRIFT:{key}")
    package = frozen["package"]
    ids = package["judgmentItemIDs"]
    if (len(ids) != 11 or len(set(ids)) != 11 or package["sourceAgreement"] != binding("agreement")
            or package["sourceDisagreementPackage"] != binding("disagreements")
            or frozen["manifest"]["reconciliationPackage"] != binding("package")):
        raise ClosureError("FROZEN_RECONCILIATION_SCOPE_DRIFT")
    decisions = value["finalDecisions"]
    if not isinstance(decisions, dict) or set(decisions) != set(ids):
        raise ClosureError("EXACT_DISAGREEMENT_MEMBERSHIP_REQUIRED")
    if any(not isinstance(status, str) or status not in CATEGORIES for status in decisions.values()):
        raise ClosureError("UNAUTHORIZED_FINAL_CATEGORY")
    return value


def counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Count all four final statuses overall and by the two governed record kinds."""
    return {name: {status: sum(row["finalStatus"] == status for row in rows if kind is None or row["recordKind"] == kind)
                   for status in CATEGORIES} for name, kind in (("overall", None), ("nodes", "node"), ("relations", "relation"))}


def assemble(frozen: dict[str, Any], returned: dict[str, Any]) -> list[dict[str, Any]]:
    """Join immutable initial judgments and returned decisions, with exact lineage."""
    primary, secondary = frozen["primary"], frozen["secondary"]
    for field in ("judgmentItems", "primarySourceUnitIDs", "duplicateReviewGroups"):
        if primary[field] != secondary[field]:
            raise ClosureError("ROLE_PACKAGE_MEMBERSHIP_DRIFT")
    if (primary["duplicateReviewGroups"] or frozen["pool"]["unresolvedDuplicateReviewGroups"]
            or frozen["lineage"]["duplicateReviewGroups"]):
        raise ClosureError("NONZERO_DUPLICATE_GROUPS_REQUIRE_RETAINED_ASSEMBLY")
    items = {item["judgmentItemID"]: item for item in primary["judgmentItems"]}
    if len(items) != 182 or Counter(item["recordKind"] for item in items.values()) != {"node": 133, "relation": 49}:
        raise ClosureError("EXACT_182_133_49_MEMBERSHIP_REQUIRED")
    a, b = frozen["reviewer_1"]["judgments"], frozen["reviewer_2"]["judgments"]
    if set(a) != set(items) or set(b) != set(items):
        raise ClosureError("INITIAL_JUDGMENT_MEMBERSHIP_DRIFT")
    disagreements = {key for key in items if a[key] != b[key]}
    declared = {row["judgmentItem"]["judgmentItemID"] for row in frozen["disagreements"]["items"]}
    if len(disagreements) != 11 or disagreements != declared or disagreements != set(returned["finalDecisions"]):
        raise ClosureError("171_PLUS_11_ASSEMBLY_DRIFT")
    maps = {row["judgmentItemID"]: row for row in frozen["lineage"]["items"]}
    pooled = {row["pooledItemID"]: row for row in frozen["pool"]["retainedPooledItems"]}
    if len(maps) != 182 or set(maps) != set(items) or len(pooled) != 182:
        raise ClosureError("LINEAGE_MEMBERSHIP_DRIFT")
    rows = []
    for key, item in sorted(items.items()):
        lineage = maps[key]
        original = pooled.get(lineage["step8APooledItemID"])
        if (original is None or original["memberCandidateKeys"] != lineage["memberCandidateKeys"]
                or original["retainedRepresentativeCandidateKey"] != lineage["representativeCandidateKey"]
                or original["primarySourceUnitID"] != item["primarySourceUnitID"]
                or original["sourceArtifactID"] != item["sourceArtifactID"]
                or original["c1Provenance"] != lineage["c1Provenance"]):
            raise ClosureError(f"LINEAGE_RECONSTRUCTION_DRIFT:{key}")
        final = returned["finalDecisions"][key] if key in disagreements else a[key]
        if final not in CATEGORIES:
            raise ClosureError("UNAUTHORIZED_FINAL_CATEGORY")
        rows.append({"judgmentItemID": key, "recordKind": item["recordKind"],
                     "initialJudgments": {"reviewer_1": a[key], "reviewer_2": b[key]},
                     "finalStatus": final, "finalStatusSource": "joint_reconciliation" if key in disagreements else "initial_agreement",
                     "judgmentItem": item, "lineage": lineage})
    return rows


def artifact(kind: str, **payload: Any) -> bytes:
    """Create a deterministic self-hashed v1.0.0 artifact."""
    body = {"artifactType": kind, "artifactVersion": "1.0.0", **payload}
    body["artifactSha256"] = sha(canonical(body))
    return canonical(body) + b"\n"


def build(raw: bytes, root: Path = ROOT) -> dict[str, bytes]:
    """Validate every input and assembly gate before constructing closure bytes."""
    frozen = load_inputs(root)
    returned = validate_intake(raw, frozen)
    rows = assemble(frozen, returned)
    positive = [row for row in rows if row["finalStatus"] == CATEGORIES[0]]
    excluded = [row for row in rows if row["finalStatus"] != CATEGORIES[0]]
    reconciled = [row for row in rows if row["finalStatusSource"] == "joint_reconciliation"]
    provenance = {key: binding(key) for key in ("pool", "lineage", "primary", "secondary")}
    results = {"received": raw}
    results["preservation"] = artifact("publication_step8_joint_reconciliation_preservation",
        preservedExport={"path": OUTPUTS["received"].as_posix(), "sha256": sha(raw)},
        exactReceivedBytesPreserved=True, shippedDistribution=binding("manifest"),
        productionBindings={key: value for key, value in returned.items() if key != "finalDecisions"},
        completionAttestation={"source": "researcher_report_in_task_instruction",
                               "statement": "The researcher reports that both reviewers jointly completed reconciliation and returned this export."})
    results["ledger"] = artifact("publication_step8_final_outcome_ledger", accessScope="internal_evaluation",
        provenanceBindings=provenance, itemCount=182, initialAgreementCount=171, reconciledCount=11,
        statusCounts=counts(rows), items=rows)
    results["positive"] = artifact("publication_step8_positive_pooled_reference", accessScope="internal_evaluation",
        interpretation="candidate-conditioned source-local human-supported subset; not a production KG",
        provenanceBindings=provenance, inclusionRule="final supported_as_proposed only; zero duplicate groups",
        endpointPolicy="Keep exact proposed endpoints; do not promote endpoint nodes or cascade judgments.",
        itemCount=len(positive), recordKindCounts=dict(Counter(row["recordKind"] for row in positive)), items=positive)
    results["exclusions"] = artifact("publication_step8_nonpositive_outcomes", accessScope="internal_evaluation",
        provenanceBindings=provenance, itemCount=len(excluded), statusCounts=counts(excluded), items=excluded,
        reason="Final status is not supported_as_proposed. Insufficient evidence and adjudication unresolved are distinct retained results.")
    lines = ["# Step 8 final outcomes", "", "Candidate-conditioned, source-local pooled reference; researcher acceptance of closure is pending.",
             "Initial reviews and pre-reconciliation agreement are preserved unchanged. No post-reconciliation reliability metric is calculated.", "",
             "| Scope | Supported | Not supported | Insufficient evidence | Adjudication unresolved |",
             "|---|---:|---:|---:|---:|"]
    for scope, values in counts(rows).items():
        lines.append(f"| {scope} | " + " | ".join(str(values[status]) for status in CATEGORIES) + " |")
    lines += ["", f"Positive reference: {len(positive)} items; " + ", ".join(f"{kind}: {sum(row['recordKind'] == kind for row in positive)}" for kind in ("node", "relation")) + ".",
              f"Excluded nonpositive outcomes: {len(excluded)}. Duplicate groups: 0. No endpoint promotion, judgment cascade, or additional Production Acceptance filter.",
              "", "## Joint reconciliation outcomes", "", "| Opaque item | Kind | Final status |", "|---|---|---|"]
    lines += [f"| {row['judgmentItemID']} | {row['recordKind']} | {row['finalStatus']} |" for row in reconciled]
    results["summary"] = ("\n".join(lines) + "\n").encode()
    results["closure"] = artifact("publication_step8_closure_freeze", status="integrity_and_assembly_gates_passed",
        researcherAcceptance="pending", sourceBindings={key: binding(key) for key in PATHS},
        outputBindings={key: {"path": OUTPUTS[key].as_posix(), "sha256": sha(data)} for key, data in results.items()},
        materializer={"path": Path(__file__).resolve().relative_to(ROOT).as_posix(), "sha256": sha(Path(__file__).read_bytes())},
        gates={"exactProductionReconciliationBinding": True, "exact171Plus11Assembly": True,
               "exact133Nodes49Relations": True, "zeroDuplicateGroups": True, "positiveOnlyInclusion": True,
               "originalLineageReconstructible": True, "initialReviewAndAgreementBytesPreserved": True},
        finalStatusCounts=counts(rows), reconciliationStatusCounts=counts(reconciled), positiveItemCount=len(positive),
        positiveRecordKindCounts=dict(Counter(row["recordKind"] for row in positive)), excludedItemCount=len(excluded),
        boundary={"closureDependsOnFavorableScore": False, "automaticSemanticAdjudicationOccurred": False,
                  "productionKGConstructed": False, "providerModelCallsOccurred": False,
                  "assertionsModified": False, "postReconciliationKappaComputed": False})
    return results


def materialize(intake: Path = ROOT / INTAKE, root: Path = ROOT, destination: Path | None = None) -> dict[str, bytes]:
    """Preflight all immutable destinations, then write only task-owned new outputs."""
    results = build(intake.read_bytes(), root)
    base = destination if destination is not None else root
    for key, data in results.items():
        path = base / OUTPUTS[key]
        if path.exists() and path.read_bytes() != data:
            raise ClosureError(f"IMMUTABLE_OUTPUT_CONFLICT:{path}")
    for key, data in results.items():
        path = base / OUTPUTS[key]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
    return results


def main() -> int:
    """Run authorized deterministic intake and assembly without modifying the return."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, default=ROOT / INTAKE)
    args = parser.parse_args()
    try:
        results = materialize(args.intake)
    except (ClosureError, OSError) as exc:
        print(str(exc))
        return 2
    for key, data in results.items():
        print(f"{OUTPUTS[key]} {sha(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
