"""Focused residual coverage and whole-component validation contracts."""
from collections import defaultdict
from copy import deepcopy
from src.evaluation import step14_residual_alignment as residual
from test_step14_final_components import fixture, group


def test_projected_alignment_and_joint_presentation():
    owner = {"a": "G", "alias": "G"}
    relations = {("G", "c")}
    index = defaultdict(set, {"a": {"W1"}, "b": {"W1"}})
    pilot = defaultdict(set, {"a": {"U1"}, "d": {"U1"}})

    def case(o):
        return residual.classify("a", o, owner, relations, index, pilot)

    assert case("alias")["direct"] == "identity"
    assert case("c")["direct"] == "typed_relation"
    assert case("b")["jointRequests"] == ["W1"] and not case("b")["residual"]
    assert case("d")["residual"] and case("d")["pilotRequests"] == ["U1"]


def test_components_expand_exact_memberships_without_creating_comparisons():
    groups = {"G": {"occurrenceIDs": ["a", "other"]}, "lock": {"occurrenceIDs": ["p", "q"]}}
    edges = {("G", "b"), ("b", "lock"), ("x", "y")}
    units = list(residual.plan(edges, groups))
    assert units[0][:2] == (["a", "b", "other", "p", "q"], [("G", "b"), ("b", "lock")])
    assert units[1] == (["x", "y"], [("x", "y")], [])


def test_joint_supersession_and_independent_lead_failure():
    body, b = fixture()
    b["priorTargets"] = {"old": ["o0", "o2"]}
    a = group("E1", "E2")
    a["supportingEvidenceIDs"] = ["E1Q1 and E2Q1: copied text"]
    value = dict(assessments=[a, group("E3", "E4"), group("E5")], relationLeads=[{"broken": True}])
    original = deepcopy(value)
    report = residual.validate(value, body, b)
    assert value == original and report["assignments"][0]["originalModelItem"] == a
    assert report["status"] == "complete_prediction"
    assert report["supersessions"] == [
        dict(
            priorTarget="old",
            oldMembership=["o0", "o2"],
            replacementAssignmentIndices=[0, 1],
            status="prospective_supersession",
        )
    ]
    assert report["relationLeads"][0]["status"] == "unresolved_lead"


def test_protected_scope_and_partial_partition_preserve_prior():
    body, b = fixture()
    b["protectedMemberships"] = [["o0", "o1"]]
    b["priorTargets"] = {"old": ["o2", "o3"]}
    result = residual.validate(
        dict(assessments=[group("E1", "E3"), group("E2"), group("E4")], relationLeads=[]), body, b
    )
    assert result["status"] == "partial_prediction"
    assert "PROTECTED_MEMBERSHIP_CHANGE" in result["assignments"][0]["reasons"]
    assert result["supersessions"][0]["status"] == "unresolved_preserve_baseline"
