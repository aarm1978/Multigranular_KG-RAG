"""Regression checks for source occurrence deduplication and lossless alignment projection."""
from copy import deepcopy

import pytest

from src.evaluation import step14_deduplicated_alignment as stage
from src.evaluation import step14_extraction_duplicates as dup


class Source:
    """Synthetic source with explicit document revision and offsets."""

    def span(self, e, pr):
        return [
            [pr["family"], "paper", pr["revision"]],
            e["startOffsetInDocument"],
            e["endOffsetInDocument"],
            e["evidenceHash"],
        ]


def native(candidate_id="n1", local="e1", text="A uses X.", start=0, revision="1"):
    """Use the publication bound-evidence shape, including attribute-specific citations."""
    e = dict(
        sourceUnitID="unit" + local,
        sourceUnitTextHash="unit-hash",
        sourceArtifactID="paper",
        canonicalPaperID="paper",
        startOffsetInDocument=start,
        endOffsetInDocument=start + len(text),
        startOffsetInUnit=0,
        endOffsetInUnit=len(text),
        evidenceSpanID=local,
        evidenceText=text,
        evidenceHash=dup.digest(text),
    )
    c = dict(
        label="X",
        className="Tool",
        candidateID=candidate_id,
        evidenceSpanIDs=[local],
        attributes=[dict(attributeName="version", value="v2", evidenceSpanIDs=[local])],
    )
    return dict(candidate=c, evidenceOccurrences=[e]), dict(family="publications", revision=revision)


NODE = {"class": "Tool", "inventoryId": "A-DOM02", "attributes": {"label": "X", "version": "v2"}}


def key(n, pr):
    return dup.fingerprint(NODE, n, pr, Source())


def test_source_mention_aliases_revisions_spans_and_semantic_attributes():
    a, pr = native()
    b, q = native("other", "other-evidence")
    assert key(a, pr) == key(b, q)
    assert key(a, pr) != key(*native(start=10)) and key(a, pr) != key(*native(revision="2"))
    b["candidate"]["attributes"][0]["value"] = "v3"
    assert key(a, pr) != key(b, q)
    b["candidate"]["attributes"][0]["evidenceSpanIDs"] = ["unknown"]
    assert key(b, q) == (None, "unbound_attribute_evidence")
    assert key(*native(text="X compared with X"))[0] is None
    del a["evidenceOccurrences"][0]["startOffsetInDocument"]
    assert key(a, pr) == (None, "missing_span_or_revision")


def group(gid, ids, historical=False):
    return dict(
        groupID=gid,
        occurrenceIDs=list(ids),
        authority="researcher_approved_exact" if historical else "automatic_prediction",
        decisionEvidence=[gid],
        ontologyClass="Tool",
        identityScope="within_artifact",
        sourceFamilies=["github"],
        approval=dict(occurrenceIDs=list(ids), materializationStatus="not_authorized")
        if historical
        else None,
    )


def test_collapsed_duplicate_projected_membership_and_exact_historical_authority():
    groups = [group("G1", "ab"), group("H", "cd", True), group("G3", "ef")]
    original = deepcopy(groups)
    ledger, active, _, owner, unresolved = stage.project_groups(
        groups, dict(a="a", b="a", c="c", d="d", e="c", f="d")
    )
    assert not unresolved and len(active) == 1 and set(owner) == set("cd")
    assert {g["disposition"] for g in ledger} == {"collapsed_singleton", "coincident_memberships"}
    assert (
        active[0]["historicalApprovals"] == [groups[1]["approval"]]
        and not active[0]["materializationAuthorized"]
    )
    assert groups == original


def test_overlapping_scopes_do_not_propagate():
    groups = [group("A", "ab"), group("B", "cd"), group("C", "ef", True)]
    ledger, active, _, owner, held = stage.project_groups(
        groups, dict(a="a", b="b", c="b", d="d", e="e", f="f")
    )
    assert [g["groupID"] for g in active] == ["C"] and set(owner) == set("ef") and held == set("abd")
    assert ledger[0]["conflicts"] == [dict(otherGroups=["B"], sharedRepresentatives=["b"])]


class Signature:
    def valid(self, s, p, a, b):
        return s == "valid"


def relation(a, b, old_a, old_b):
    return dict(
        subject=old_a,
        object=old_b,
        predicate="hasComponent",
        support=[
            dict(
                signature="valid",
                evidence=[{"binding": {"occurrenceID": k}} for k in (a, b)],
                citedEndpoints=[[a], [b]],
            )
        ],
    )


def test_directed_witness_projection_deduplication_singleton_and_holds():
    rel = [relation("a", "c", "A", "C"), relation("b", "d", "B", "D")]
    reps = dict(a="a", b="a", c="c", d="c")
    old = dict(a="A", b="B", c="C", d="D")
    ledger, frame = stage.project_relations(
        rel, reps, old, {}, set(), {"a": "Tool", "c": "Tool"}, Signature()
    )
    assert len(frame) == 1 and (frame[0]["subject"], frame[0]["object"]) == ("a", "c")
    assert len(frame[0]["support"]) == 2 and {r["disposition"] for r in ledger} == {"deduplicated"}
    for held, mapping, reason in [
        ({"c"}, reps, "conflicting_identity_membership"),
        (set(), dict.fromkeys(reps, "a"), "projected_self_relation"),
    ]:
        l, f = stage.project_relations(rel, mapping, old, {}, held, {"a": "Tool", "c": "Tool"}, Signature())
        assert not f and all(reason in r["reasons"] for r in l)


def test_edge_provenance_precedence_and_direction():
    nodes = {"paper": {"class": "Paper"}, "x": NODE, "y": NODE}

    def e(i, a, p, b):
        return dict(id=i, source=a, target=b, relation=p, inventoryId="valid")

    edges = [
        e("e1", "paper", "usesTool", "x"),
        e("e2", "paper", "usesTool", "y"),
        e("e3", "paper", "mentions", "y"),
        e("e4", "paper", "mentionsTool", "y"),
        e("e5", "y", "mentions", "paper"),
    ]
    orig = deepcopy(edges)
    policy = dict(stronger_role_relations=["usesTool"], specialized_subproperties=["mentionsTool"])
    profile = dict(
        global_rules=dict(
            use_mention_reference_precedence={
                "usesTool": "supersedes mentionsTool for the same Paper-entity pair"
            }
        )
    )
    kept, ledger, counts = dup.project_edges(
        edges, dict(paper="paper", x="x", y="x"), nodes, Signature(), policy, profile
    )
    assert {e["id"] for e in kept} == {"e1", "e5"} and len(ledger) == len(edges)
    assert counts == dict(retained=2, duplicate_triple=1, precedence_suppressed=2, redirected=4)
    assert orig == edges
    with pytest.raises(ValueError, match="INDUCED_SELF_LOOP"):
        dup.project_edges(
            [e("bad", "x", "mentions", "y")], dict(x="x", y="x"), nodes, Signature(), policy, profile
        )


def test_owner_sensitive_mentions_and_structural_paths(tmp_path, monkeypatch):
    """Different owner contexts cannot be bridged by an owner-ambiguous duplicate."""
    from collections import defaultdict
    import json

    nodes = {
        k: dict(id=k, **{"class": cls})
        for k, cls in [
            ("p", "Paper"),
            ("q", "Paper"),
            ("x", "Method"),
            ("y", "Method"),
            ("m", "Parameter"),
            ("n", "Parameter"),
            ("u", "Parameter"),
            ("i", "Step"),
            ("j", "Step"),
            ("k", "Step"),
        ]
    }
    # x and y are distinct verified method mentions; m and n use the same literal span.
    records = []
    for oid in "xymnuijk":
        n = dict(
            key=oid if oid in "xy" else nodes[oid]["class"],
            path=[("q" if oid == "k" else "p", "hasStep")] if oid in "ijk" else [],
        )
        records.append(
            dict(
                kind="nodes",
                graphID=oid,
                nativeRecord=n,
                nativeRecordSha256=dup.token(n),
                provenance=dict(family="publications"),
            )
        )
    native_path = tmp_path / "native"
    native_path.write_text("".join(json.dumps(r) + "\n" for r in records))

    class Parents:
        def parent_path(self, n, pr):
            return tuple(tuple(x) for x in n["path"])

    monkeypatch.setattr(dup, "fingerprint", lambda node, n, pr, source: (n["key"], "verified_mention"))
    relations = [dict(source=a, target=b, relation="hasParameter") for a, b in [("x", "m"), ("y", "n")]]
    graph = dict(nodes=list(nodes.values()), edges=relations)
    prof = dict(
        node_targets=[
            dict(operational_target="Parameter", identity_policy=dict(scope="contextual_occurrence"))
        ]
    )
    reps, blocks, _, reasons = dup.census(graph, native_path, defaultdict(set), Parents(), prof, {})
    assert list(blocks.values()) == [["i", "j"]] and reps["k"] == "k"
    assert len({reps[k] for k in "mnu"}) == 3 and "ambiguous_contextual_owner" in reasons["u"]
