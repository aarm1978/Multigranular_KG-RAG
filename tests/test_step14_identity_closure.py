"""Regression tests for the terminal Step 14 consumer, using synthetic original responses."""
from copy import deepcopy

import pytest

from src.evaluation import step14_identity_closure as closure
from test_step14_final_components import fixture, group


def response(first=None, last=None, lead=None, protected=()):
    """Replay the frozen evaluator before applying the closure contract."""
    body, binding = fixture()
    binding["protectedMemberships"] = protected
    value = dict(
        assessments=[first or group("E1", "E2"), group("E3", "E4"), last or group("E5")],
        relationLeads=[lead] if lead else [],
    )
    return closure.final.evaluate(value, body, binding), binding


def qualification():
    """Keep an explicit comparative contradiction in its original model-authored role."""
    return dict(
        group("E1", "E2"),
        conflictAssessment="compatible_qualification",
        contradictoryEvidenceIDs=["E5Q1"],
        qualifyingEvidenceIDs=["E1Q1"],
    )


def test_structured_qualification_and_independent_singleton():
    report, _ = response(qualification(), dict(group("E5"), contradictoryEvidenceIDs=["E5Q1"]))
    original = deepcopy(report)
    result = [closure.corrected(x) for x in report["assignments"]]
    assert not result[0]["reasons"] and not result[1]["reasons"]
    assert result[0]["modelItem"] == qualification()
    assert result[0]["citations"] == original["assignments"][0]["citations"]
    assert result[2]["reasons"] == ["AMBIGUOUS_DISTINCT_CONTRADICTION"]
    assert report == original


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"conflictAssessment": "material_conflict"}, "UNSUPPORTED_STRICT_IDENTITY"),
        ({"conflictAssessment": "unresolved_ambiguity"}, "UNSUPPORTED_STRICT_IDENTITY"),
        ({"qualifyingEvidenceIDs": ["unknown"]}, "UNKNOWN_QUALIFICATION"),
        ({"supportingEvidenceIDs": ["E1Q1", "E5Q1"]}, "MISSING_DIRECT_SUPPORT"),
    ],
)
def test_residual_failures_are_terminal(changes, reason):
    report, _ = response(dict(qualification(), **changes))
    assert reason in closure.corrected(report["assignments"][0])["reasons"]
    assert not closure.corrected(report["assignments"][1])["reasons"]


def test_protected_boundary_survives_qualification():
    report, _ = response(qualification(), protected=[["o0", "o2"]])
    assert "PROTECTED_MEMBERSHIP_CHANGE" in closure.corrected(report["assignments"][0])["reasons"]


@pytest.mark.parametrize(
    "subject,target,refs,expected",
    [
        ("implementation represented by E1/E2", "general group E3", ["E2Q1", "E3Q1"], "evidence_lead"),
        ("E1/E4", "E5", ["E1Q1", "E5Q1"], "unresolved_lead"),
        ("E1", "general group", ["E1Q1", "E3Q1"], "unresolved_lead"),
        ("E1", "E4", ["E2Q1", "E5Q1"], "unresolved_lead"),
        ("E1", "E2", ["E1Q1", "E2Q1"], "unresolved_lead"),
    ],
)
def test_endpoint_aliases_and_evidence(subject, target, refs, expected):
    lead = dict(
        subject=subject,
        object=target,
        evidenceIDs=refs,
        explanation="application depends on general model",
    )
    report, binding = response(lead=lead)
    bound = closure.resolve_lead(report["relationLeads"][0], report["assignments"], binding)
    assert bound["status"] == expected
    assert bound["original"]["modelItem"] == lead
    assert [x["binding"] for x in bound["citations"]] == [binding["evidence"][ref] for ref in refs]
    if expected == "evidence_lead":
        assert bound["sides"][1] == dict(index=1, membership=["o2", "o3"], namedOccurrences=["o2"])


def test_explicit_supersession_preserves_exact_targets():
    groups = {
        ("a", "c"): {"support": [1]},
        ("h", "i"): {"support": [], "authority": "researcher_approved_exact"},
    }
    locks = {("h", "i"): {}}
    prior = {"changed": ["a", "b"], "outside": ["x", "y"]}
    decisions = {"changed": {"d"}, "outside": {"e"}}
    result = closure.reconcile_prior(locks, groups, prior, decisions, dict.fromkeys("abc", "J"))
    assert result == [
        dict(priorTarget="changed", oldMembership=("a", "b"), component="J", priorDecisionIDs=["d"])
    ]
    assert set(groups) == {("a", "c"), ("h", "i"), ("x", "y")}
    with pytest.raises(ValueError, match="PROTECTED_MEMBERSHIP_CHANGE"):
        closure.reconcile_prior(locks, groups, prior, decisions, {"h": "J"})
    with pytest.raises(ValueError, match="PARTIAL_PRIOR_SCOPE"):
        closure.reconcile_prior(locks, groups, prior, decisions, {"b": "J"})


def test_directed_dedup_retains_held_support_and_projection():
    old = dict(predicate="dependsOn", subject="a", object="b", support=["q"])
    observation = dict(
        itemType="typedRelations",
        modelItem={"signatureID": "D"},
        occurrenceIDs=["a", "b"],
        status="review_required",
        citations=["q2"],
    )

    def read(folder, name):
        return (
            [old]
            if folder == closure.rec.PRIOR
            else [observation, dict(observation, occurrenceIDs=["b", "a"])]
        )

    rows, held = closure.relation_inventory(
        read, {"D": {"name": "dependsOn"}}, [], {"a": {"provisionalTarget": "p"}}
    )
    assert not held and len(rows) == 2
    assert [s["record"] for s in rows[0]["support"]] == [old, observation]
    assert rows[0]["projections"] == [{"a": {"provisionalTarget": "p"}}, {"b": None}]


def test_omitted_occurrence_has_no_manufactured_assessment():
    terminal = {"a": "mechanically_unresolved", "b": "mechanically_unresolved", "c": "abstention"}
    items = [
        dict(reference=["v2", "J", i], assessment=dict(occurrenceIDs=[o], reasons=e))
        for i, (o, e) in enumerate([("b", ["UNCITED_QUALIFICATION"]), ("c", [])])
    ]
    rows = list(
        closure.terminal_rows(terminal, dict.fromkeys(terminal, "J"), dict.fromkeys(terminal, {}), items)
    )
    assert rows[0]["reasons"] == ["OMITTED_FROM_PARTITION"] and rows[0]["assessmentReferences"] == []
    assert rows[1]["reasons"] == ["UNCITED_QUALIFICATION"]
    assert rows[2]["status"] == "abstention" and rows[2]["reasons"] == []
