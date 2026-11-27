"""Scope and evidence boundaries of the terminal representation overlay."""
from copy import deepcopy

import pytest

from src.evaluation import step14_representation_overlay as overlay


def group(k, ids, authority="automatic_prediction", **extra):
    return dict(groupID=k, occurrenceIDs=ids, authority=authority, **extra)


def candidate(left, right, witnesses):
    return dict(
        kind="candidate",
        occurrenceEndpoints=[left, right],
        support=[dict(citations=[dict(binding=dict(occurrenceID=o)) for o in witnesses])],
    )


def test_overlay_preserves_sources_and_exact_approvals():
    records = [
        group("held", ["a", "b"], productionConsistencyHold=[["X1", 2]]),
        group("automatic", ["c", "d"]),
        group("locked", ["e", "f"], "researcher_approved_exact"),
    ]
    before = deepcopy(records)
    active, excluded, owner = overlay.membership_overlay(records)
    assert records == before
    assert list(active.values()) == records[1:] and excluded == {"held": records[0]}
    assert set(owner) == set("cdef")
    assert overlay.projected_key(candidate(["a"], ["b"], ["a", "b"]), owner) == ("a", "b")


def test_protected_membership_cannot_be_excluded():
    with pytest.raises(ValueError, match="PROTECTED_AUTHORITY"):
        overlay.membership_overlay(
            [group("lock", ["a", "b"], "researcher_approved_exact", productionConsistencyHold=[1])]
        )


def test_reprojection_keeps_individual_witness_sides():
    owner = {"x": "other", "y": "other"}
    assert overlay.projected_key(candidate(["a"], ["x", "y"], ["a", "y"]), owner) == ("a", "other")
    with pytest.raises(ValueError, match="AMBIGUOUS_OR_INTERNAL"):
        overlay.projected_key(candidate(["a", "b"], ["x"], ["a", "b", "x"]), owner)
    with pytest.raises(ValueError, match="MISSING_ENDPOINT_EVIDENCE"):
        overlay.projected_key(candidate(["a"], ["x"], ["b", "x"]), owner)
