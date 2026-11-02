"""Focused offline checks of fixed review decisions and immutable provenance."""

import copy
import json

import pytest

from src.extraction.llm.publications import scierc_contextual_review as m


@pytest.fixture(scope="module")
def inputs():
    """Load only final review decisions and original source identities."""
    return m.load()


def test_coverage_metrics_supports(inputs):
    """Recompute every decision, fixed denominator, and expected micro score."""
    decisions, alternatives, result = m.reconcile(*inputs)
    assert len(decisions) == 447 and len(alternatives) == 61
    expected = {"entity": (994,1348,691,1685,2342,167,6,.4244235696,.5899109792,.4936677427),
                "relation": (594,1007,380,974,1601,200,1,.3710181137,.6098562628,.4613592233)}
    keys = ("TP","FP","FN","goldSupport","predictionSupport","additionalOverStrictA","salvagedAlternatives","precision","recall","f1")
    for layer, values in expected.items():
        assert tuple(result["metrics"][layer][k] for k in keys) == pytest.approx(values, rel=0, abs=5e-11)
    assert sum(r["accepted"] for r in decisions) == 360
    assert sum(r["interpretation"] == "not_equivalent" for r in decisions) == 83
    assert sum(r["interpretation"] == "not_established" for r in decisions) == 4
    assert sum(r["accepted"] for r in alternatives) == 7


@pytest.mark.parametrize("index", [0,1])
def test_missing_coverage_refused(inputs, index):
    """Neither selected nor alternative records may disappear."""
    altered = copy.deepcopy(list(inputs))
    altered[index].pop()
    with pytest.raises(ValueError, match="coverage"):
        m.reconcile(*altered)


def test_duplicate_case_refused(inputs):
    """Repeated accepted or rejected cases cannot weight the result twice."""
    altered = copy.deepcopy(list(inputs))
    altered[1].append(altered[1][0])
    with pytest.raises(ValueError, match="duplicate case"):
        m.reconcile(*altered)


@pytest.mark.parametrize("side", ["prediction","gold"])
def test_endpoint_collision_refused(inputs, side):
    """An alternative cannot reuse either endpoint of any earlier accepted pair."""
    case = copy.deepcopy(inputs[2][0])
    occupied = {}
    m.claim(case, occupied)
    other = copy.deepcopy(case)
    other["caseID"] += "-alternative"
    other["gold" if side == "prediction" else "prediction"]["id"] += "-new"
    with pytest.raises(ValueError, match="one-to-one"):
        m.claim(other, occupied)
    with pytest.raises(ValueError, match="one-to-one"):
        m.claim(case, occupied)


def test_identity_drift_refused(inputs):
    """Review judgment ingestion cannot rewrite source endpoints."""
    altered = copy.deepcopy(list(inputs))
    altered[0][0]["prediction"]["id"] = "invented"
    with pytest.raises(ValueError, match="source field drift"):
        m.reconcile(*altered)


def test_reproducible_outputs_and_unchanged_inputs(inputs):
    """All bound bytes remain unchanged, and stored outputs equal recomputation."""
    manifest = json.loads((m.OUT/"provenance_manifest.json").read_text())
    for item in manifest["inputs"] + manifest["outputs"] + [manifest["implementation"]]:
        m.prior.verify(item)
    decisions, alternatives, metrics = m.reconcile(*inputs)
    assert m.rows(m.OUT/"decision_ledger.jsonl") == decisions
    assert m.rows(m.OUT/"alternative_rematch_ledger.jsonl") == alternatives
    assert json.loads((m.OUT/"aggregate_metrics.json").read_text()) == metrics
