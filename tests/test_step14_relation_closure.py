"""Focused tests for citation parsing, the scoped exception and occurrence-based projection."""
from copy import deepcopy

import pytest
from src.evaluation import step14_relation_closure as c


@pytest.mark.parametrize(
    "text,expected",
    [
        ("O1Q1", ["O1Q1"]),
        ('O2Q2 and O3Q1: "O1Q1 is merely quoted"', ["O2Q2", "O3Q1"]),
        ("O1Q2 / O3Q2 (release): excerpt", ["O1Q2", "O3Q2"]),
        ("O1Q2 (R1; also O3Q1): excerpt", ["O1Q2", "O3Q1"]),
        ("contains O2Q2", []),
        ("O1Q1 or O2Q2", []),
        ("O1Q1foo: text", []),
    ],
)
def test_prefix_only(text, expected):
    assert c.aliases(text) == expected


def fixture():
    case = dict(
        key=["a", "b"],
        sides=[["a"], ["b"]],
        internal=False,
        evidence=["O1Q1", "O2Q1"],
        options={"forward": ["s"], "reverse": []},
    )
    bindings = {
        k: dict(occurrenceID=v, quote={"literalExcerpt": "authoritative"})
        for k, v in [("O1Q1", "a"), ("O2Q1", "b"), ("O2Q2", "b")]
    }
    item = dict(
        case="P2",
        outcome="relation",
        direction="forward",
        signature="s",
        explanation="rationale",
        evidence=["O1Q1: paraphrase", "O2Q2: different wording"],
    )
    return {"items": [item]}, dict(cases={"P2": case}, evidence=bindings)


def test_only_authorized_endpoint_and_preserved_evidence():
    value, b = fixture()
    before = deepcopy((value, b))
    row = c.replay_unit("T0018", value, b)[0]
    assert not row["reasons"]
    assert row["original"] == before[0]["items"][0]
    assert row["evidence"][1]["scope"] == "same_request_exact_endpoint"
    assert row["evidence"][1]["binding"]["quote"]["literalExcerpt"] == "authoritative"
    assert (value, b) == before
    assert "UNKNOWN_CASE_EVIDENCE" in c.replay_unit("T0019", value, b)[0]["reasons"]
    b["evidence"]["O2Q2"]["occurrenceID"] = "other"
    assert "UNKNOWN_CASE_EVIDENCE" in c.replay_unit("T0018", value, b)[0]["reasons"]


def test_project_only_cited_originals_and_equivalent_predicates():
    value, b = fixture()
    row = c.replay_unit("T0018", value, b)[0]
    row["originalSides"][1].append("baseline")
    owner = {"baseline": "new"}
    sig = {"s": dict(name="hasComponent", domain="Tool", range="Tool")}
    sig["s2"] = sig["s"]
    args = (owner, dict.fromkeys(["a", "b", "new"], "Tool"), sig, {"Tool": {"Tool"}})
    assert c.triple(row, *args) == (("a", "hasComponent", "b"), None)
    row["original"].update(direction="reverse", signature="s2")
    assert c.triple(row, *args) == (("b", "hasComponent", "a"), None)
    owner["b"] = "a"
    assert c.triple(row, *args)[0] is None


def test_authority_requires_five_distinct_internal_witnesses():
    old = {"occurrenceIDs": [c.GENERIC, *"abcde"], "authority": "automatic_prediction"}
    r = dict(
        unit="T0118",
        reasons=[],
        original={"outcome": "material_exception"},
        candidateKey=[c.VERSION_GROUP, c.VERSION_GROUP, "a", c.GENERIC],
        originalSides=[["a"], [c.GENERIC]],
        evidence=[{"binding": {"occurrenceID": o}} for o in ("a", c.GENERIC)],
    )
    with pytest.raises(ValueError, match="AUTHORIZED_SCOPE_DRIFT"):
        c.correction({c.VERSION_GROUP: old}, [r] * 5, {})
