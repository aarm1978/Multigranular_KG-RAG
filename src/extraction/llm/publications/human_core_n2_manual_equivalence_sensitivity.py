"""Build the bounded N=2 researcher-reviewed equivalence sensitivity artifact.

This is deliberately separate from the frozen deterministic matcher.  It preserves
only researcher-supplied positive equivalences and mechanically binds the relation
counterparts whose B edge IDs were not separately recorded.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.extraction.llm.publications.human_core_n2_reliability import (
    GOLD_ROOT,
    AuthorityError,
    Record,
    load_frozen_inputs,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PRIMARY_PATH = GOLD_ROOT / "publication_human_core_n2_pre_adjudication_reliability_v0.1.5.json"
OUTPUT_PATH = GOLD_ROOT / "publication_human_core_n2_manual_equivalence_sensitivity_v0.1.json"
SYNTHESIS_PATH = GOLD_ROOT / "publication_human_core_n2_final_reliability_synthesis_v0.1.md"
CHECKPOINT = "cce912f3d30a0925deb6db858eb1b5961f942285"


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest for one frozen or generated file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key_index(records: list[Record]) -> dict[tuple[str, str, str], list[Record]]:
    """Index source-unit candidate anchors without collapsing partitions."""
    output: dict[tuple[str, str, str], list[Record]] = {}
    for record in records:
        key = (record.unit, record.kind, record.value["candidateID"])
        output.setdefault(key, []).append(record)
    return output


def _record(index: dict[tuple[str, str, str], list[Record]], unit: str, kind: str, candidate: str, label: str | None = None) -> Record:
    """Resolve one supplied candidate anchor to its fully-qualified frozen key."""
    try:
        matches = index[unit, kind, candidate]
    except KeyError as exc:
        raise AuthorityError(f"approved candidate anchor is absent: {unit} {kind} {candidate}") from exc
    if label is not None:
        matches = [row for row in matches if (row.value.get("displayLabel") or row.value.get("label")) == label]
    if len(matches) != 1:
        raise AuthorityError(f"approved candidate anchor is ambiguous: {unit} {kind} {candidate}")
    return matches[0]


NODE_CASES = (
    ("N01", "evaluate", "pub:79:sec:0004:unit:0001", "node-0001", "hydroGOF", "node-0011", "R package hydroGOF", "same assertion / boundary variation"),
    ("N02", "evaluate", "pub:79:sec:0004:unit:0001", "node-0002", "SALib", "node-0012", "python library SALib", "same assertion / boundary variation"),
    ("N03", "evaluate", "pub:79:sec:0004:unit:0001", "node-0007", "NWM", "node-0015", "National Water Model (NWM)", "same assertion / boundary variation"),
    ("N04", "evaluate", "pub:79:sec:0004:unit:0001", "node-0004", "SWMM", "node-0016", "Storm Water Management Model (SWMM; Rossman 2015)", "same assertion / boundary variation"),
    ("N05", "evaluate", "pub:79:sec:0004:unit:0001", "node-0005", "HBV", "node-0017", "Hydrologiska Byrans Vat- ˚ tenbalansavdelning (HBV) model", "same assertion / boundary variation"),
    ("N06", "evaluate", "pub:79:sec:0004:unit:0001", "node-0016", "the HBV and TOPMODEL case studies", "node-0008", "HBV and TOPMODEL", "same assertion / boundary variation"),
    ("N07", "evaluate", "pub:79:sec:0004:unit:0001", "node-0012", "SWMM-simulated streamflow", "node-0019", "streamflow", "same assertion / boundary variation"),
    ("N08", "evaluate", "pub:34:sec:0015:unit:0001", "node-0025", "The LSTM streamflow model achieved a median daily Nash-Sutcliffe Efficiency (NSE) (Nash & Sutcliffe, [1970](#page-25-27)) of 0.7849 for the eight gaging stations in the JRB.", "node-0022", "achieved a median daily Nash-Sutcliffe Efficiency (NSE) (Nash & Sutcliffe, [1970](#page-25-27)) of 0.7849", "same assertion / boundary variation"),
    ("N09", "evaluate", "pub:34:sec:0015:unit:0001", "node-0031", "the model was run from 2000/01/01–2009/12/31 to predict discharge for the 17 HUC10 watersheds in the study area", "node-0014", "run from 2000/01/01–2009/12/31", "same assertion / boundary variation"),
    ("N10", "evaluate", "pub:79:sec:0004:unit:0001", "node-0022", "Difficulties frequently arise in model performance evaluation due to multiple interpretations of output or data products, differing mathematical descriptions of underlying processes, and uncertainties present in the input and parameter datasets", "node-0001", "Difficulties frequently arise in model performance evaluation", "same assertion / boundary variation"),
    ("N11", "evaluate", "pub:34:sec:0015:unit:0001", "node-0020", "observed discharge data", "node-0010", "observed discharge data", "same occurrence / characterization disagreement"),
    ("M01", "monitor", "pub:34:sec:0015:unit:0001", "node-0023", "This LSTM model was similar to those developed and reported in previous streamflow and water quality studies (Feng et al., [2020;](#page-23-7) Ouyang et al., [2021;](#page-25-25) Rahmani, Lawson, et al., [2021](#page-25-12); Rahmani, Shen, et al., [2021](#page-25-26))", "node-0026", "similar to those developed and reported in previous streamflow and water quality studies", "same assertion / boundary variation"),
    ("M02", "monitor", "pub:34:sec:0015:unit:0001", "node-0024", "We selected 29 basin attributes (Table [A1](#page-21-0) in the Appendix [A\\)](#page-17-0) similar to those chosen in previous LSTM studies (Ouyang et al., [2021\\)](#page-25-25).", "node-0027", "similar to those chosen in previous LSTM studies", "same assertion / boundary variation"),
    ("M03", "monitor", "pub:79:sec:0004:unit:0001", "node-0033", "A recent study by Stagge et al. (2019) found low reproducibility (5.6% of total sampled articles) in research published in 2017 from six hydrology and water resources journals.", "node-0028", "A recent study by Stagge et al. (2019) found low reproducibility", "same assertion / boundary variation"),
    ("M04", "monitor", "pub:79:sec:0004:unit:0001", "node-0034", "Gil et al. (2016) introduces the concept of the Geoscience Paper of the Future, with a best practice requiring authors to make data, software, and methods openly accessible, citable, and well-documented.", "node-0029", "Gil et al. (2016) introduces the concept of the Geoscience Paper of the Future", "same assertion / boundary variation"),
)

# The B endpoint labels are preserved semantic anchors, not B edge IDs.  Binding an
# edge requires exactly one B relation in the stated unit/operational target ending at
# the uniquely identified B endpoint.
RELATION_CASES = (
    ("R01", "evaluate", "pub:34:sec:0015:unit:0001", "edge-0010", "PUB-R-C-P17-STUDIESFEATURE-PAPER-BRANCH", "JRB"),
    ("R02", "evaluate", "pub:34:sec:0015:unit:0001", "edge-0011", "PUB-R-C-P17-STUDIESFEATURE-PAPER-BRANCH", "HUC8 subbasins"),
    ("R03", "evaluate", "pub:34:sec:0015:unit:0001", "edge-0012", "PUB-R-C-P17-STUDIESFEATURE-PAPER-BRANCH", "HUC10 watersheds"),
    ("R04", "evaluate", "pub:34:sec:0015:unit:0001", "edge-0013", "PUB-R-C-P20-USESDATASET-NEW-PROSE-EVIDENCE", "NASA NLDAS-2 forcing data set"),
    ("R05", "evaluate", "pub:34:sec:0015:unit:0001", "edge-0009", "PUB-R-C-P16-MENTIONSVARIABLE", "daily basin discharge"),
    ("R06", "evaluate", "pub:79:sec:0004:unit:0001", "edge-0001", "PUB-R-C-P13-USESMODEL-PAPER-BRANCH", "Storm Water Management Model (SWMM; Rossman 2015)"),
    ("R07", "evaluate", "pub:79:sec:0004:unit:0001", "edge-0002", "PUB-R-C-P13-USESMODEL-PAPER-BRANCH", "Hydrologiska Byrans Vat- ˚ tenbalansavdelning (HBV) model"),
    ("R08", "evaluate", "pub:79:sec:0004:unit:0001", "edge-0003", "PUB-R-C-P13-USESMODEL-PAPER-BRANCH", "TOPMODEL"),
    ("R09", "evaluate", "pub:79:sec:0004:unit:0001", "edge-0004", "PUB-R-C-P15-USESTOOL", "R package hydroGOF"),
    ("R10", "evaluate", "pub:79:sec:0004:unit:0001", "edge-0005", "PUB-R-C-P15-USESTOOL", "python library SALib"),
)


def _treatment(record: Record) -> str | None:
    """Return the preserved treatment for one node or relation record."""
    return record.treatments.get(record.value.get("operationalTargetID") or record.value.get("operationalRelationID"))


def _bind_relation_b(records: list[Record], unit: str, operational_relation: str, endpoint_label: str) -> Record:
    """Mechanically bind a B relation through its unique frozen endpoint label."""
    nodes = {
        row.value["candidateID"]: row
        for row in records
        if row.kind == "node" and row.unit == unit and (row.value.get("displayLabel") or row.value.get("label")) == endpoint_label
    }
    if len(nodes) != 1:
        raise AuthorityError(f"B endpoint anchor is not unique: {unit} {endpoint_label!r}")
    endpoint_id = next(iter(nodes))
    matches = [
        row for row in records
        if row.kind == "relation" and row.unit == unit
        and row.value.get("operationalRelationID") == operational_relation
        and row.value.get("target", {}).get("referenceType") == "candidate_node"
        and row.value["target"].get("referenceID") == endpoint_id
    ]
    if len(matches) != 1:
        raise AuthorityError(f"B relation binding is not unique: {unit} {operational_relation} {endpoint_label!r} ({len(matches)} matches)")
    return matches[0]


def _case(case_id: str, treatment: str, left: Record, right: Record, category: str | None = None) -> dict[str, Any]:
    """Serialize a positive researcher-approved one-to-one equivalence only."""
    row = {"caseID": case_id, "treatment": f"extract_and_{treatment}", "annotatorAKey": left.key, "annotatorBKey": right.key}
    if category is not None:
        row["reviewCategory"] = category
    return row


def build(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Validate and build the bounded secondary sensitivity artifact."""
    a, b, _ = load_frozen_inputs(root)
    primary_path = root / PRIMARY_PATH.relative_to(PROJECT_ROOT)
    primary = json.loads(primary_path.read_text(encoding="utf-8"))
    if primary.get("artifactType") != "human_to_human_n2_pre_adjudication_reliability":
        raise AuthorityError("primary N=2 artifact has unexpected identity")
    primary_pairs = {(row["annotatorAKey"], row["annotatorBKey"]) for kind in ("nodes", "relations") for row in primary["pairings"][kind]}
    a_index, b_index = _key_index(a), _key_index(b)
    evaluate_nodes: list[dict[str, Any]] = []; monitor_nodes: list[dict[str, Any]] = []
    for case_id, bucket, unit, a_id, a_label, b_id, b_label, category in NODE_CASES:
        left, right = _record(a_index, unit, "node", a_id, a_label), _record(b_index, unit, "node", b_id, b_label)
        if _treatment(left) != f"extract_and_{bucket}" or _treatment(right) != f"extract_and_{bucket}":
            raise AuthorityError(f"approved node pair has incorrect treatment: {case_id}")
        (evaluate_nodes if bucket == "evaluate" else monitor_nodes).append(_case(case_id, bucket, left, right, category))
    evaluate_relations: list[dict[str, Any]] = []
    for case_id, bucket, unit, a_id, operational_relation, endpoint_label in RELATION_CASES:
        left = _record(a_index, unit, "relation", a_id)
        right = _bind_relation_b(b, unit, operational_relation, endpoint_label)
        if left.value.get("operationalRelationID") != operational_relation or _treatment(left) != "extract_and_evaluate" or _treatment(right) != "extract_and_evaluate":
            raise AuthorityError(f"approved relation pair has incorrect frozen binding: {case_id}")
        evaluate_relations.append(_case(case_id, bucket, left, right))
    monitor_relation_left = _record(a_index, "pub:79:sec:0004:unit:0001", "relation", "edge-0014")
    monitor_relation_right = _record(b_index, "pub:79:sec:0004:unit:0001", "relation", "edge-0001")
    if _treatment(monitor_relation_left) != "extract_and_monitor" or _treatment(monitor_relation_right) != "extract_and_monitor":
        raise AuthorityError("MR01 has incorrect treatment")
    monitor_relations = [_case("MR01", "monitor", monitor_relation_left, monitor_relation_right)]
    additions = {"extractAndEvaluate": {"nodes": evaluate_nodes, "relations": evaluate_relations}, "extractAndMonitor": {"nodes": monitor_nodes, "relations": monitor_relations}}
    all_cases = evaluate_nodes + evaluate_relations + monitor_nodes + monitor_relations
    if len(all_cases) != 26:
        raise AuthorityError("approved positive equivalence case count is not exactly 26")
    for kind_cases in (evaluate_nodes, evaluate_relations, monitor_nodes, monitor_relations):
        if len({row["annotatorAKey"] for row in kind_cases}) != len(kind_cases) or len({row["annotatorBKey"] for row in kind_cases}) != len(kind_cases):
            raise AuthorityError("sensitivity addition consumes a record more than once within a stratum")
    if any((row["annotatorAKey"], row["annotatorBKey"]) in primary_pairs for row in all_cases):
        raise AuthorityError("sensitivity addition overlaps a deterministic pairing")
    expected = {
        "extractAndEvaluate": {"nodes": (55, 48, 28, 39, 0.7572815533980582), "relations": (25, 28, 13, 23, 0.8679245283018868)},
        "extractAndMonitor": {"nodes": (18, 19, 7, 11, 0.5945945945945946), "relations": (5, 4, 2, 3, 0.6666666666666666)},
    }
    derived: dict[str, Any] = {}
    for bucket, kinds in expected.items():
        derived[bucket] = {}
        for kind, (a_count, b_count, primary_matched, total, f1) in kinds.items():
            added = len(additions[bucket][kind])
            if primary_matched + added != total or 2 * total / (a_count + b_count) != f1:
                raise AuthorityError(f"frozen sensitivity total mismatch: {bucket} {kind}")
            derived[bucket][kind] = {"annotatorASupport": a_count, "annotatorBSupport": b_count, "primaryDeterministicMatchedSupport": primary_matched, "approvedAdditionalEquivalences": added, "sensitivityMatchedSupport": total, "symmetricPairwiseF1": f1}
    return {
        "artifactType": "human_to_human_n2_manual_equivalence_sensitivity",
        "artifactVersion": "0.1.0",
        "scope": {"positiveResearcherReviewedEquivalenceDecisionsOnly": True, "secondarySensitivityAnalysis": True, "notAdjudication": True, "notReplacementForDeterministicReliability": True, "notExhaustiveDiscrepancyClassification": True, "noNegativeCaseInventoryClaimed": True},
        "historicalPrimaryFinalizationCheckpoint": CHECKPOINT,
        "primaryFrozenDeterministicReliability": {"path": str(PRIMARY_PATH.relative_to(PROJECT_ROOT)), "sha256": _sha256(primary_path)},
        "approvedAdditionalEquivalences": additions,
        "approvedPositiveEquivalenceCaseCount": len(all_cases),
        "derivedSensitivity": derived,
    }


def render_synthesis(sensitivity: dict[str, Any]) -> str:
    """Render a distinct final N=2 synthesis report without editing frozen outputs."""
    p = sensitivity["primaryFrozenDeterministicReliability"]
    d = sensitivity["derivedSensitivity"]
    return "\n".join((
        "# Final N=2 Human-to-Human Reliability Synthesis", "",
        "## Authorities and scope", "",
        f"The primary frozen deterministic reliability result is [{p['path']}]({p['path']}) (SHA-256 `{p['sha256']}`), finalized at historical checkpoint `{CHECKPOINT}`; its companion frozen report is `data/curation/papers/m2/human_core_gold/publication_human_core_n2_pre_adjudication_reliability_v0.1.5.md`. The deterministic analysis is primary and remains unchanged.",
        "", "The secondary artifact is `publication_human_core_n2_manual_equivalence_sensitivity_v0.1.json`. It is a **human-reviewed equivalence sensitivity analysis**, not adjudication, not a gold standard, and not a replacement for or retrospective modification of the frozen matching contract or deterministic pairings. Annotator A and Annotator B remain unmodified.", "",
        "## Primary frozen deterministic reliability", "",
        "- `extract_and_evaluate` nodes: A=55, B=48, M=28, symmetric F1=0.543689.",
        "- `extract_and_evaluate` relations: A=25, B=28, M=13, symmetric F1=0.490566.",
        "- Node target presence/absence agreement: 25/27 = 92.6%.",
        "- Relation target presence/absence agreement: 20/24 = 83.3%.", "",
        "## Secondary human-reviewed equivalence sensitivity analysis", "",
        f"- `extract_and_evaluate` nodes: A=55, B=48, M={d['extractAndEvaluate']['nodes']['sensitivityMatchedSupport']}, symmetric F1={d['extractAndEvaluate']['nodes']['symmetricPairwiseF1']}.",
        f"- `extract_and_evaluate` relations: A=25, B=28, M={d['extractAndEvaluate']['relations']['sensitivityMatchedSupport']}, symmetric F1={d['extractAndEvaluate']['relations']['symmetricPairwiseF1']}.",
        f"- `extract_and_monitor` nodes: A=18, B=19, M={d['extractAndMonitor']['nodes']['sensitivityMatchedSupport']}, symmetric F1={d['extractAndMonitor']['nodes']['symmetricPairwiseF1']}.",
        f"- `extract_and_monitor` relations: A=5, B=4, M={d['extractAndMonitor']['relations']['sensitivityMatchedSupport']}, symmetric F1={d['extractAndMonitor']['relations']['symmetricPairwiseF1']}.", "",
        "Only the 26 positive researcher-approved equivalence cases were preserved. No exhaustive negative discrepancy classification was reconstructed. `extract_and_monitor` remains non-exhaustive. This bounded N=2 assessment must not be presented as a corpus-wide inter-annotator-agreement estimate.", "",
    ))


def main() -> None:
    """Write the new secondary artifact and distinct synthesis report."""
    result = build()
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SYNTHESIS_PATH.write_text(render_synthesis(result), encoding="utf-8")


if __name__ == "__main__":
    main()
