"""Localized whole-membership conflicts, scoped evidence and granular relation output."""
from copy import deepcopy
import pytest
from src.evaluation import step14_residual_relations as final


def row(category, *ids, bad=False):
    return dict(category=category, occurrenceIDs=ids, reasons=["invalid"] if bad else [])


@pytest.mark.parametrize("held", [row("abstention", "b"), row("strict_identity", "b", bad=True)])
def test_local_preservation_propagates_only_through_indivisible_competitors(held):
    priors = {"g1": ["a", "b"], "g2": ["c", "d"], "unrelated": ["f", "g"]}
    rows = [
        held,
        row("strict_identity", "a", "c"),
        row("strict_identity", "d", "e"),
        row("strict_identity", "f", "h"),
        row("distinct", "g"),
    ]
    preserved, admitted, blocked = final.reconcile(priors, rows, [])
    assert preserved == {"g1", "g2"}
    assert admitted == {("f", "h")}
    assert blocked == {("a", "c"), ("d", "e")}


def test_approval_protection_and_supported_split():
    keep, ok, blocked = final.reconcile(
        {"p": ["b", "c"]},
        [row("strict_identity", "a", "b"), row("distinct", "c"), row("distinct", "d")],
        [["a", "d"]],
    )
    assert keep == {"p"} and not ok and blocked == {("a", "b")}
    keep, ok, blocked = final.reconcile(
        {"p": ["b", "c"]}, [row("distinct", "b"), row("strict_identity", "c", "e")], []
    )
    assert not keep and not blocked and ok == {("c", "e")}


def test_reproject_lead_from_actual_witnesses_no_cartesian_expansion():
    lead = dict(
        status="evidence_lead",
        sides=[{"membership": ["a", "b"]}, {"membership": ["c"]}],
        citations=[{"binding": {"occurrenceID": o}} for o in ["a", "c"]],
    )
    owner = {"a": "new1", "b": "new2"}
    assert final.projected_lead(lead, {}, owner) == [["a"], ["c"]]
    lead["citations"].append({"binding": {"occurrenceID": "b"}})
    assert final.projected_lead(lead, {}, owner) is None


def test_held_lead_requires_explicit_unambiguous_cited_sides():
    lead = dict(
        status="unresolved_lead",
        original={"modelItem": {"subject": "E1 and E2", "object": "E3"}},
        reasons=["AMBIGUOUS_OR_UNRESOLVED_SUBJECT"],
        citations=[{"binding": {"occurrenceID": o}} for o in ["a", "c"]],
    )
    aliases = {"E1": "a", "E2": "b", "E3": "c"}
    assert final.projected_lead(lead, aliases, {}) is None
    assert final.projected_lead(lead, aliases, {"a": "G", "b": "G"}) == [["a", "b"], ["c"]]


def test_validation_keeps_raw_normalizes_only_known_case_evidence():
    answer = dict(
        case="P",
        outcome="relation",
        direction="forward",
        signature="S",
        explanation="test",
        evidence=["O1Q1 and O2Q1: copied wording"],
    )
    value = {"items": [answer, dict(answer, evidence=["O1Q1", "O3Q1"])]}
    original = deepcopy(value)
    b = dict(
        cases={
            "P": dict(
                internal=False,
                sides=[["a"], ["b"]],
                options={"forward": ["S"]},
                evidence=["O1Q1", "O2Q1"],
            )
        },
        evidence={k: {"occurrenceID": v} for k, v in [("O1Q1", "a"), ("O2Q1", "b"), ("O3Q1", "b")]},
    )
    out = final.validate(value, b)
    assert out["items"][0]["originalModelItem"] == answer and not out["items"][0]["reasons"]
    assert "UNKNOWN_CASE_EVIDENCE" in out["items"][1]["reasons"]
    assert value == original
