"""Offline checks of projection, historical binding and independent case validation."""
import pytest
from src.evaluation import step14_final_relations as r


def test_complete_endpoint_projection():
    owner = {"a": "g", "b": "g"}
    assert r.project([["a", "b"], ["c"]], owner) == ("g", "c")
    assert r.project([["a", "c"], ["b"]], owner) is None
    assert r.project([["a"], ["b"]], owner) == ("g", "g")


def test_archive_resolution_requires_original_digest():
    path = r.ARCHIVE / r.w.SPEC.name
    assert r.historical(r.w.SPEC, r.w.r.identity.sha(path)) == path
    with pytest.raises(ValueError, match="HISTORICAL_DRIFT"):
        r.historical(r.w.SPEC, r.w.r.identity.sha(r.w.SPEC))


def fixture():
    case = dict(
        evidence=["q1", "q2"],
        options={"forward": ["s"], "reverse": []},
        sides=[["a"], ["b"]],
        internal=False,
    )
    return dict(
        cases={"p": case, "i": dict(case, internal=True, options={}, key=["g", "g", "a", "b"])},
        evidence={"q1": {"occurrenceID": "a"}, "q2": {"occurrenceID": "b"}},
    )


def answer(**changes):
    return dict(
        dict(
            case="p",
            outcome="relation",
            signature="s",
            direction="forward",
            explanation="Supported by both source spans",
            evidence=["q1", "q2"],
        ),
        **changes
    )


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"direction": "reverse"}, "INVALID_DIRECTION_OR_SIGNATURE"),
        ({"evidence": ["q1"]}, "MISSING_ENDPOINT_SUPPORT"),
        ({"evidence": ["q1", "q2", "unknown"]}, "UNKNOWN_CASE_EVIDENCE"),
        ({"case": "i"}, "INVALID_CASE_OUTCOME"),
    ],
)
def test_granular_relation_validation(changes, reason):
    result = r.validate({"items": [answer(**changes), answer()]}, fixture())
    assert reason in result["items"][0]["reasons"] and result["items"][1]["reasons"] == []
    assert result["missingOrUnresolved"] == ["i"]


def test_exception_and_terminal_abstention():
    result = r.validate(
        {
            "items": [
                answer(case="i", outcome="material_exception", signature=None, direction=None),
                answer(outcome="abstain", evidence=[], signature=None, direction=None),
            ]
        },
        fixture(),
    )
    assert result["missingOrUnresolved"] == []
    assert all(not x["reasons"] for x in result["items"])


def test_unresolved_lead_needs_unique_cited_sides(monkeypatch):
    monkeypatch.setattr(r, "lead_aliases", lambda _: {"E1": "a", "E2": "b", "E3": "c"})
    lead = dict(
        original={"modelItem": dict(subject="E1/E2", object="E3")},
        citations=[dict(binding=dict(occurrenceID=o)) for o in ["a", "c"]],
    )
    assert r.recover(lead, {"a": "g", "b": "g"}) == [["a", "b"], ["c"]]
    assert r.recover(lead, {}) is None
    lead["citations"].pop()
    assert r.recover(lead, {"a": "g", "b": "g"}) is None
