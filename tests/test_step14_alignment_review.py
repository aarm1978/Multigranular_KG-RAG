"""Focused checks for the two blinded reviewer views and resumable local sessions."""
from copy import deepcopy
import json

import pytest

from src.annotation.alignment_review import prepare as prep
from src.annotation.alignment_review.app import Session


def source(i, texts):
    """Two distinct artifacts share literal text and carry different version metadata."""
    return dict(
        occurrenceID=f"private-{i}",
        ontologyClass="Tool",
        sourceFamilies=["publications"],
        sourceArtifacts=[f"https://doi.org/test/{i % 2}"],
        labels=[f"Source label {i}"],
        versions={"entityVersion": str(i)},
        granularity="release",
        evidenceReferences=[
            dict(
                evidenceText=t,
                sectionTitle=f"Section {j}",
                startOffsetInUnit=0,
                endOffsetInUnit=len(t),
            )
            for j, t in enumerate(texts)
        ],
        rationale="HIDDEN MODEL JUDGMENT",
        attributes={"confidence": "HIDDEN SCORE"},
    )


def build(frame, originals, signatures=None):
    """Supply private source pointers without exposing original IDs to the evaluator."""
    provenance = {
        k: dict(
            originalReference=dict(
                file="private/ledger", line=i, recordSha256=prep.token(v)
            )
        )
        for i, (k, v) in enumerate(originals.items(), 1)
    }
    return prep.build_case("C01", frame, originals, provenance, signatures or {}, {})


@pytest.mark.parametrize("size", [2, 150])
def test_lossless_exact_dedup_and_blinding(size):
    rows = [source(i, ["same", "same", " same", str(i)]) for i in range(size)]
    originals = {o["occurrenceID"]: o for o in rows}
    frame = dict(
        groupID="private-group",
        occurrenceIDs=list(originals),
        ontologyClass="Tool",
        identityScope="between_families",
        decisionEvidence="HIDDEN DECISION",
    )
    snapshot = deepcopy(originals)
    case, private, counts = build(frame, originals)
    assert len(case["artifacts"]) == 2
    assert (
        counts["originalExcerpts"] == 4 * size
        and counts["distinctOriginalExcerpts"] == size + 2
    )
    for m in case["occurrences"]:
        b = private["members"][m["id"]]
        o = originals[b["occurrenceID"]]
        assert m["versions"] == o["versions"] and m["labels"] == o["labels"]
        assert b["artifact"] == o["sourceArtifacts"][0]
        assert [case["excerpts"][e["quote"]] for e in m["evidence"]] == [
            e["evidenceText"] for e in o["evidenceReferences"]
        ]
        assert (
            len(b["evidence"]) == 4
            and b["evidence"][1]["pointer"] == "/evidenceReferences/1"
        )
    assert originals == snapshot
    assert all(
        bad not in json.dumps(case)
        for bad in (
            "private-",
            "private/ledger",
            "confidence",
            "HIDDEN",
            "recordSha256",
            "groupID",
        )
    )


def test_relation_direction_cited_slice_and_context():
    rows = [source(i, ["long quotation"]) for i in range(3)]
    originals = {o["occurrenceID"]: o for o in rows}
    evidence = []
    for i, o in enumerate(rows, 1):
        oid = o["occurrenceID"]
        b = dict(
            occurrenceID=oid,
            source=dict(file="private/ledger", line=i, recordSha256=prep.token(o)),
            quote=dict(
                literalExcerpt="quotation",
                quoteStart=5,
                quoteEnd=14,
                fullQuoteSha256=prep.digest("long quotation"),
                reference=dict(
                    jsonPointer="/evidenceReferences/0",
                    evidenceRecordSha256=prep.token(o["evidenceReferences"][0]),
                ),
            ),
        )
        evidence.append(dict(original="HIDDEN rationale", binding=b))
    s = dict(
        signature="S",
        direction="reverse",
        citedEndpoints=[["private-1"], ["private-0"]],
        evidence=evidence,
    )
    f = dict(
        subject="private-1",
        object="private-0",
        predicate="hasComponent",
        endpointClasses=["Tool", "Tool"],
        evidenceScope="within_artifact",
        support=[s],
    )
    sig = {
        "S": dict(
            name="hasComponent",
            domain="Tool",
            range="Tool",
            note="Composition",
            evidence="Explicit composition",
        )
    }
    c, mapping, _ = build(f, originals, sig)
    assert [
        mapping["members"][e["occurrences"][0]]["occurrenceID"] for e in c["endpoints"]
    ] == ["private-1", "private-0"]
    assert len(c["occurrences"]) == 3 and c["definitions"][0]["note"] == "Composition"
    for m in c["occurrences"]:
        e = m["evidence"][0]
        assert (
            c["excerpts"][e["quote"]] == "long quotation"
            and c["excerpts"][e["relationEvidence"][0]] == "quotation"
        )
    assert "HIDDEN" not in json.dumps(c)
    evidence[0]["binding"]["quote"]["quoteStart"] = 0
    with pytest.raises(ValueError, match="citation drift"):
        build(f, originals, sig)


def test_missing_evidence_and_hash_integrity(tmp_path):
    o = source(1, [])
    f = dict(
        groupID="X",
        occurrenceIDs=[o["occurrenceID"]],
        ontologyClass="Tool",
        identityScope="within_artifact",
    )
    c, _, _ = build(f, {o["occurrenceID"]: o})
    assert c["occurrences"][0]["evidence"] == [] and c["excerpts"] == {}
    file = tmp_path / "originals"
    file.write_text(json.dumps(o) + "\n")
    member = dict(
        originalReference=dict(file=str(file), line=1, recordSha256=prep.token(o)),
        evidencePointers=[],
    )
    assert prep.selected_originals({o["occurrenceID"]: member}) == {
        o["occurrenceID"]: o
    }
    o["labels"] = ["changed"]
    file.write_text(json.dumps(o) + "\n")
    with pytest.raises(ValueError, match="drift"):
        prep.selected_originals({o["occurrenceID"]: member})


def test_session_interruption_correction_export_and_clocks(tmp_path):
    package = dict(
        evaluator="A",
        purpose="Exploratory",
        cases=[
            dict(id="C01", phase="Identity"),
            dict(id="C02", phase="Typed relation"),
        ],
    )
    prep.write(tmp_path / "cases.json", package)
    prep.write(
        tmp_path / "package-manifest.json",
        dict(files={"cases.json": prep.digest((tmp_path / "cases.json").read_text())}),
    )
    times = [10.0]
    s = Session(tmp_path, now=lambda: times[0])

    def act(kind, **kw):
        st = s.state()
        return s.change(
            dict(type=kind, revision=st["revision"], sourceUnitID=st["cursor"], **kw)
        )

    def answer(judgment, complete=False):
        return act(
            "save",
            judgment=judgment,
            completeReview=complete,
            comment="draft",
            problematic="O2",
        )

    act("open")
    times[0] += 5
    act("tick", activeSeconds=3)
    with pytest.raises(ValueError, match="complete identity group"):
        answer("Supported")
    answer("Unsupported")
    act("pause")
    times[0] += 500
    s.db.close()
    s = Session(tmp_path, now=lambda: times[0])
    assert (
        s.state()["records"]["C01"]["comment"] == "draft" and not s.state()["running"]
    )
    act("open")
    times[0] += 90  # Lost heartbeat after interruption
    act("tick", activeSeconds=90)
    act("go", target="C02")
    assert json.loads(s.export())["cases"][1]["judgment"] is None
    act("go", target="C01")
    answer("Supported", True)
    out = json.loads(s.export())
    assert out["summary"] == dict(
        cases=2, answered=1, elapsedSeconds=5, activeSeconds=3
    )
    assert out["cases"][0]["revisits"] == 2 and out["cases"][0]["inactiveSeconds"] == 2
    assert [e["judgment"] for e in out["edits"]] == ["Unsupported", "Supported"]
    assert [t["action"] for t in out["transitions"]] == [
        "open",
        "pause",
        "open",
        "go",
        "go",
    ]
    with pytest.raises(ValueError, match="another tab"):
        s.change(dict(type="pause", sourceUnitID="C01", revision=0))
    s.db.close()
    (tmp_path / "cases.json").write_text("{}")
    with pytest.raises(ValueError, match="package drift"):
        Session(tmp_path)


def test_projected_referents_keep_direction_and_cited_witnesses():
    frame = dict(
        subject="release",
        object="family",
        endpointSizes=[1, 3],
        predicate="isVersionOf",
        support=[dict(citedEndpoints=[["release"], ["short"]], evidence=[])],
    )
    groups = {"family": dict(occurrenceIDs=["long1", "long2", "short"])}
    provenance = {
        oid: dict(labels=[name])
        for oid, name in [
            ("release", "Model v2"),
            ("long1", "General model"),
            ("long2", "General model"),
            ("short", "GM"),
        ]
    }
    case = dict(endpoints=[dict(occurrences=["O1"]), dict(occurrences=["O2"])])
    prep.describe_endpoints(case, frame, groups, provenance)
    assert [e["label"] for e in case["endpoints"]] == ["Model v2", "General model"]
    assert case["endpoints"][1] == dict(
        label="General model", size=3, occurrences=["O2"]
    )
    frame["support"][0]["citedEndpoints"].reverse()
    with pytest.raises(ValueError, match="endpoint drift"):
        prep.describe_endpoints(case, frame, groups, provenance)


def test_representatives_keep_exact_contexts_and_each_source_pointer():
    from src.annotation.alignment_review.projected import representative_view

    originals = {}
    # The first two addresses are copies. A different artifact repeats the same span.
    for i, (art, offset) in enumerate([(0, 10), (0, 10), (1, 90), (1, 112)]):
        o = source(art, ["river"])
        o["occurrenceID"] = f"private-{i}"
        o["evidenceReferences"][0]["startOffsetInDocument"] = offset
        originals[o["occurrenceID"]] = o
    f = dict(
        groupID="private-group",
        ontologyClass="Tool",
        identityScope="between_families",
        occurrenceIDs=list(originals),
    )
    c, mapping, _ = build(f, originals)
    for i, (m, b) in enumerate(zip(c["occurrences"], mapping["members"].values())):
        before = "The " if i < 3 else "the "
        m["evidence"][0]["context"] = [before, " here"]
        b["evidence"][0]["context"] = [before, " here"]
    reps = {k: k for k in originals}
    reps["private-1"] = "private-0"
    assert representative_view(c, mapping, reps) == 4
    assert len(c["occurrences"]) == 3 and len(c["contexts"]) == 2
    assert all(len(m["evidence"]) == 1 for m in c["occurrences"])
    assert [m["evidence"][0]["contextID"] for m in c["occurrences"]] == [
        "X1",
        "X1",
        "X2",
    ]
    for b in mapping["extractions"].values():
        o = originals[b["occurrenceID"]]
        m = next(m for m in c["occurrences"] if m["id"] == b["displayAlias"])
        e = m["evidence"][b["evidence"][0]["displayEvidenceIndex"]]
        assert m["versions"] == o["versions"]
        assert (
            e["location"]["startOffsetInDocument"]
            == o["evidenceReferences"][0]["startOffsetInDocument"]
        )
        assert b["source"]["recordSha256"] == prep.token(o)
        assert b["evidence"][0]["pointer"] == "/evidenceReferences/0"
        ctx = c["contexts"][e["contextID"]]
        text = ctx["before"] + c["excerpts"][ctx["quote"]] + ctx["after"]
        assert text[e["quoteStartInContext"] : e["quoteEndInContext"]] == "river"
    assert "private-" not in json.dumps(c)


def test_projected_citations_resolve_only_the_original_directed_witness():
    from src.annotation.alignment_review.projected import (
        validate_sides,
        representative_view,
    )

    rows = [source(i, [f"original witness {i}"]) for i in range(2)]
    evidence = []
    for i, o in enumerate(rows, 1):
        e = o["evidenceReferences"][0]
        text = e["evidenceText"]
        evidence.append(
            dict(
                binding=dict(
                    occurrenceID=o["occurrenceID"],
                    source=dict(
                        file="private/ledger", line=i, recordSha256=prep.token(o)
                    ),
                    quote=dict(
                        literalExcerpt=text,
                        quoteStart=0,
                        quoteEnd=len(text),
                        fullQuoteSha256=prep.digest(text),
                        reference=dict(
                            jsonPointer="/evidenceReferences/0",
                            evidenceRecordSha256=prep.token(e),
                        ),
                    ),
                )
            )
        )
    support = dict(
        signature="S",
        citedEndpoints=[["private-1"], ["private-0"]],
        projectedCitedOccurrences=[["retained-copy"], ["private-0"]],
        evidence=evidence,
    )
    frame = dict(
        predicate="hasComponent",
        subject="group",
        object="private-0",
        endpointClasses=["Tool", "Tool"],
        evidenceScope="within_artifact",
        support=[support],
    )
    reps = {"private-1": "retained-copy", "private-0": "private-0"}
    validate_sides(frame, reps, {"retained-copy": "group"})
    c, mapping, _ = build(
        frame, {o["occurrenceID"]: o for o in rows}, {"S": dict(name="hasComponent")}
    )
    representative_view(c, mapping, reps)
    end = c["endpoints"][0]["occurrences"][0]
    assert mapping["representatives"][end] == "retained-copy"
    m = next(m for m in c["occurrences"] if m["id"] == end)
    assert (
        c["excerpts"][m["evidence"][0]["relationEvidence"][0]] == "original witness 1"
    )
    with pytest.raises(ValueError, match="membership drift"):
        validate_sides(frame, reps, {"retained-copy": "different-group"})
    support["projectedCitedOccurrences"].reverse()
    with pytest.raises(ValueError, match="representative drift"):
        validate_sides(frame, reps, {})
    support["evidence"].pop()
    with pytest.raises(ValueError, match="original citation"):
        validate_sides(frame, reps, {})
