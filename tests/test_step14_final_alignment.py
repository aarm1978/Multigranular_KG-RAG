"""Regression tests for anchored evidence parsing and observed pair accounting."""
from copy import deepcopy
import pytest
from src.evaluation import step14_final_alignment as stage


@pytest.mark.parametrize(
    "text, expected",
    [
        ('O2Q1 (scikit-learn) and O1Q1 (Python): "O3Q1"', ["O2Q1", "O1Q1"]),
        ('O1Q1 and O3Q1 list RF alongside "O9Q9".', ["O1Q1", "O3Q1"]),
        ("O2Q1 separately lists “O8Q3”.", ["O2Q1"]),
        ('O4Q1 (web app), O3Q1 and O5Q1 (HydroShare): "x"', ["O4Q1", "O3Q1", "O5Q1"]),
        ("O7Q1–O7Q4: excerpt", ["O7Q1", "O7Q4"]),
        ("O3Q1 (also O8Q1): quote", ["O3Q1", "O8Q1"]),
        ("O1Q1 (R1; also O3Q1): quote", ["O1Q1", "O3Q1"]),
        ("O3Q1, identifying the endpoint: O6Q1", ["O3Q1"]),
        ('"Quoted reference O1Q1"', []),
        ("O1Q1 or O2Q1", []),
        ("O1Q1 and missing", []),
        ("O1Q1extra: fake", []),
    ],
)
def test_citation_prefix(text, expected):
    assert stage.aliases(text) == expected


def test_replay_preserves_scope_support_and_raw_text():
    case = dict(
        key=["a", "b"],
        sides=[["a"], ["b"]],
        internal=False,
        options={"forward": ["S"]},
        evidence=["O1Q1", "O2Q1"],
    )
    b = dict(
        cases={k: case for k in ["P1", "P2", "P3"]},
        evidence={
            k: dict(occurrenceID=v, quote={"literalExcerpt": "original source"})
            for k, v in [("O1Q1", "a"), ("O2Q1", "b"), ("O2Q2", "b")]
        },
    )
    item = dict(
        case="P1",
        signature="S",
        direction="forward",
        outcome="relation",
        explanation="prediction",
        evidence=['O1Q1 (one) and O2Q1 (two): "model wording"'],
    )
    value = dict(
        items=[
            item,
            dict(item, case="P2", evidence=["O1Q1", "O2Q2"]),
            dict(item, case="P3", evidence=['O1Q1: "O2Q1"']),
        ]
    )
    before = deepcopy(value)
    a, bad, missing = stage.replay(value, b)
    assert not a["reasons"] and a["original"] == item
    assert a["evidence"][0]["binding"]["quote"]["literalExcerpt"] == "original source"
    assert "UNKNOWN_CASE_EVIDENCE" in bad["reasons"] and not bad["evidence"][1]["caseBound"]
    assert "MISSING_ENDPOINT_SUPPORT" in missing["reasons"] and value == before


def test_candidate_coverage_is_observed_and_direction_independent():
    related = {("a", "b")}
    assert stage.coverage_state(["b", "a"], related) == "typed_relation"
    assert stage.coverage_state(["a", "a"], related) == "identity"
    assert stage.coverage_state(["b", "c"], related) == "without_direct_alignment"
