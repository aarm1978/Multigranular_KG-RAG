"""Materialize fixed v0.6.0 LLM-assisted decisions; never adjudicate or extract."""

from collections import Counter
import json
from pathlib import Path

from . import scierc_external_anchor as a
from . import scierc_postrun_evaluation as prior

INPUT = a.RUNTIME_ROOT / "scierc_overlap_review_progress_v0.6.0"
SOURCE = a.RUNTIME_ROOT / "overlap_sensitivity_v0.1.0"
OUT = a.PROJECT_ROOT / "data/curation/papers/m2/scierc_contextual_equivalence_v0.1.0"
REPORT = a.PROJECT_ROOT / "data/curation/papers/m2/scierc_overlap_sensitivity_v0.1.0/aggregate_report.json"
REVIEW_SHA = "497b01055774147f3b703900b258fbe6b925796cc1a810eddd46d5e5026f20d6"
ZIP_SHA = "c12e1f8c66c52bfa15afd4d82f1cfa55cd4c5e24da95e237e715ee5f774f133b"


def require(condition: bool, message: str) -> None:
    """Fail closed on input drift or ambiguous matching."""
    if not condition:
        raise ValueError(message)


def rows(path: Path) -> list:
    """Read a ledger without changing any source bytes."""
    return [json.loads(line) for line in path.read_text().splitlines()]


def unique(items: list) -> dict:
    """Require unique case identities, including rejected decisions."""
    result = {r["caseID"]: r for r in items}
    require(len(result) == len(items), "duplicate case")
    return result


def claim(case: dict, occupied: dict) -> None:
    """Claim both scored-item endpoints globally within document/layer."""
    keys = [(side, case["layer"], case["documentID"], case[side]["id"]) for side in ("prediction", "gold")]
    require(not any(k in occupied for k in keys), "one-to-one conflict: " + case["caseID"])
    for key in keys:
        occupied[key] = case["caseID"]


def reconcile(selected: list, alternatives: list, sources: list, baseline: dict) -> tuple:
    """Resolve only source identities; all contextual judgments come from v0.6.0."""
    source = unique(sources)
    decisions = unique(selected)
    alternative_map = unique(alternatives)
    selected_ids = {k for k,v in source.items() if v["category"] == "overlap_pair" and v["selected"]}
    require(set(decisions) == selected_ids and len(decisions) == 447, "selected coverage")
    expected_alternatives = set()
    parent_ids = set()
    for row in selected:
        original = source[row["caseID"]]
        if "sourceCaseSha256" in row:
            require(row["sourceCaseSha256"] == a.sha256_bytes(a.canonical_json(original)), "case hash")
        require(row["sourceReviewSha256"] == REVIEW_SHA and row["sourceZipSha256"] == ZIP_SHA, "source identity")
        for key in ("documentID", "layer", "prediction", "gold", "context", "competingAlternativeCaseIDs", "selectedOrientation", "tokenIoU"):
            require(row[key] == original[key], "source field drift: " + key)
        if row["interpretation"] != "equivalent" and row["competingAlternativeCaseIDs"]:
            parent_ids.add(row["caseID"])
            expected_alternatives.update(row["competingAlternativeCaseIDs"])
    require(set(alternative_map) == expected_alternatives and len(alternatives) == 61 and len(parent_ids) == 52, "alternative coverage")
    occupied = {}
    exact = Counter()
    for case in sources:
        if case["category"] == "exact_locked":
            claim(case, occupied)
            exact[case["layer"]] += 1
    outputs = []
    counts = {}
    for name, ledger in (("selected", selected), ("alternative", alternatives)):
        compact = []
        counter = Counter()
        for row in sorted(ledger, key=lambda r: r["caseID"]):
            case = source[row["caseID"]]
            status = row["interpretation"]
            require(status in {"equivalent", "not_equivalent", "not_established"}, "unknown interpretation")
            require(row["independentlyHumanValidated"] is False and row["originalScoringOrMatchingChanged"] is False, "review nature drift")
            if name == "alternative":
                require(case["category"] == "overlap_pair" and not case["selected"], "alternative not residual")
                for key in ("documentID", "layer", "context", "tokenIoU"):
                    require(row[key] == case[key], "alternative source drift")
                for side in ("prediction", "gold"):
                    require(row[side+"Label"] == case[side]["label"] and row[side+"Text"] == " || ".join(x["text"] for x in case[side]["arguments"]), "alternative identity drift")
            if status == "equivalent":
                claim(case, occupied)
            counter[(row["layer"], status)] += 1
            item = {key: row[key] for key in ("caseID", "documentID", "layer", "interpretation", "differenceCategory")}
            item.update(predictionID=case["prediction"]["id"], goldID=case["gold"]["id"],
                        sourceCaseSha256=a.sha256_bytes(a.canonical_json(case)), accepted=status == "equivalent")
            if name == "alternative":
                item["alternativeAuditID"] = row["alternativeAuditID"]
                item["nonacceptedSelectedParents"] = sorted(k for k in parent_ids if row["caseID"] in decisions[k]["competingAlternativeCaseIDs"])
            else:
                for key in ("shortID", "decisionStatus", "researcherAccepted", "reviewer", "reviewerModel"):
                    item[key] = row[key]
            compact.append(item)
        counts[name] = {layer: {status: counter[layer,status] for status in ("equivalent", "not_equivalent", "not_established")} for layer in ("entity", "relation")}
        outputs.append(compact)
    metrics = {}
    for layer in ("entity", "relation"):
        strict = baseline["metrics"][layer]["strictA"]
        require(exact[layer] == strict["TP"], "strict source identity")
        added = sum(counts[k][layer]["equivalent"] for k in counts)
        tp = strict["TP"] + added
        gold, pred = strict["goldSupport"], strict["predictionSupport"]
        metrics[layer] = dict(TP=tp, FP=pred-tp, FN=gold-tp, goldSupport=gold, predictionSupport=pred,
                              precision=tp/pred, recall=tp/gold, f1=2*tp/(pred+gold), additionalOverStrictA=added,
                              salvagedAlternatives=counts["alternative"][layer]["equivalent"])
    return (*outputs, {"version":"0.1.0", "nature":"secondary LLM-assisted contextual-equivalence analysis; not independently human-adjudicated gold or replacement extraction score", "counts":counts, "metrics":metrics, "newProviderCalls":0})


def load() -> tuple:
    """Hash-check final inputs and original identity package, without earlier reviews."""
    metadata = json.loads((INPUT / "review_metadata.json").read_text())
    for name in ("interpretations_cumulative.jsonl", "alternative_audit.jsonl", "semantic_matching_summary.json", "review_progress_note.md"):
        item = prior.evidence(INPUT/name)
        require(all(item[k] == metadata[name][k] for k in ("sha256", "sizeBytes")), "final input hash")
    require(prior.evidence(SOURCE/"review.jsonl")["sha256"] == REVIEW_SHA, "original review hash")
    require(prior.evidence(SOURCE/"scierc_overlap_review_v0.1.0.zip")["sha256"] == ZIP_SHA == metadata["sourceZIP"]["sha256"], "original ZIP hash")
    return rows(INPUT/"interpretations_cumulative.jsonl"), rows(INPUT/"alternative_audit.jsonl"), rows(SOURCE/"review.jsonl"), json.loads(REPORT.read_text())


def materialize() -> None:
    """Write compact derived artifacts exclusively; preserve all inputs."""
    protected = sorted(INPUT.iterdir()) + [SOURCE/"review.jsonl", SOURCE/"scierc_overlap_review_v0.1.0.zip", REPORT, prior.DECISIONS, prior.A_PATH, prior.B_PATH, prior.MANIFEST, prior.OUT/"metrics.json"]
    before = [prior.evidence(p) for p in protected]
    decisions, alternatives, metrics = reconcile(*load())
    for layer, expected in (("entity", (994,1348,691,167,6)), ("relation", (594,1007,380,200,1))):
        require(tuple(metrics["metrics"][layer][k] for k in ("TP","FP","FN","additionalOverStrictA","salvagedAlternatives")) == expected, "expected result conflict")
    for name, value in (("decision_ledger.jsonl", decisions), ("alternative_rematch_ledger.jsonl", alternatives)):
        prior.write(OUT/name, b"".join(a.canonical_json(row)+b"\n" for row in value))
    prior.write(OUT/"aggregate_metrics.json", prior.encode(metrics))
    require(before == [prior.evidence(p) for p in protected], "protected input changed")
    outputs = [prior.evidence(OUT/name) for name in ("decision_ledger.jsonl", "alternative_rematch_ledger.jsonl", "aggregate_metrics.json")]
    prior.write(OUT/"provenance_manifest.json", prior.encode({"version":"0.1.0", "inputs":before, "outputs":outputs,
        "implementation":prior.evidence(Path(__file__)), "oneToOneVerified":True, "selectedCaseCoverage":447,
        "alternativeCaseCoverage":61, "nonacceptedSelectedCasesWithAlternatives":52,
        "sourcePackageUse":"identity/hash verification only, including endpoint identity and strict-lock collision checks; judgments exclusively from final v0.6.0", "independentlyHumanAdjudicated":False}))


if __name__ == "__main__":
    materialize()
