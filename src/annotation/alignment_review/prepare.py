"""Prepare portable, blinded Step 14 reviewer packages from the frozen evaluation frames."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import yaml

from src.evaluation import step14_final_alignment as frozen
from src.evaluation.step14_semantic_candidates import token

HERE = Path(__file__).parent
DEFAULT = frozen.w.BASE / "alignment-evaluation/researcher-pilot-v1"
PUBLICATION_UNITS = (
    Path("data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"),
    Path(
        "var/study2_step13/publication-source-unit-extension/v0.2/publication-prospective-source-units.v0.2.jsonl"
    ),
)


def require(condition, message):
    """Reject drift or an ambiguous binding before publishing the package."""
    if not condition:
        raise ValueError(message)


def digest(text):
    """Hash verbatim UTF-8 source text."""
    return hashlib.sha256(text.encode()).hexdigest()


def write(path, value):
    """Write stable, readable UTF-8 JSON."""
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def select(groups, relations, selection=None):
    """Use explicit frame keys or fixed purposive usability strata in frame order."""
    if selection is None:
        groups = [
            next(
                g
                for g in groups
                if g["size"] == 2 and g["identityScope"] == "within_artifact"
            ),
            next(
                g
                for g in groups
                if 4 <= g["size"] <= 8
                and g["identityScope"] == "within_family_between_artifacts"
            ),
            max(
                (
                    g
                    for g in groups
                    if g["ontologyClass"] == "Tool"
                    and g["identityScope"] == "between_families"
                ),
                key=lambda g: g["size"],
            ),
        ]
        relations = [
            next(r for r in relations if r["predicate"] == p)
            for p in sorted({r["predicate"] for r in relations})
        ]
    else:
        gi = {g["groupID"]: g for g in groups}
        ri = {(r["subject"], r["predicate"], r["object"]): r for r in relations}
        groups = [gi[k] for k in selection["identity"]]
        relations = [ri[tuple(k)] for k in selection["relations"]]
    rows = groups + relations
    require(
        rows and len(set(map(token, rows))) == len(rows), "empty or duplicate selection"
    )
    require(
        all(r["authority"] == "automatic_prediction" for r in rows),
        "automatic frame required",
    )
    return rows


def citations(row):
    """Keep directed witness roles and every original relation-support binding."""
    sides = [set(), set()]
    cites = defaultdict(list)
    if "predicate" not in row:
        return sides, cites
    for s in row["support"]:
        for side, members in zip(sides, s["citedEndpoints"]):
            side.update(members)
        for entry in s["evidence"]:
            b = entry["binding"]
            cites[b["occurrenceID"]].append(b)
    return sides, cites


def selected_originals(members):
    """Dereference exact source lines and verify content and every evidence pointer."""
    files = defaultdict(dict)
    for oid, m in members.items():
        ref = m["originalReference"]
        files[ref["file"]][ref["line"]] = oid
    originals = {}
    for filename, lines in files.items():
        with open(filename, encoding="utf-8") as stream:
            for n, line in enumerate(stream, 1):
                if n not in lines:
                    continue
                o = json.loads(line)
                oid = lines[n]
                m = members[oid]
                require(
                    o["occurrenceID"] == oid
                    and token(o) == m["originalReference"]["recordSha256"],
                    "original occurrence drift",
                )
                pointers = {
                    e["jsonPointer"]: e["recordSha256"] for e in m["evidencePointers"]
                }
                require(
                    pointers
                    == {
                        f"/evidenceReferences/{j}": token(e)
                        for j, e in enumerate(o["evidenceReferences"])
                    },
                    "evidence drift",
                )
                originals[oid] = o
    require(originals.keys() == members.keys(), "missing original occurrence")
    return originals


def wider_context(originals):
    """Join available surrounding text through a matching source identity, hash and exact span."""
    wanted = {
        e.get("sourceUnitID")
        for o in originals.values()
        for e in o["evidenceReferences"]
    }
    units = {}
    for p in PUBLICATION_UNITS:
        if p.exists():
            for u in frozen.w.r.rows(p):
                if u["sourceUnitID"] in wanted:
                    text = u["text"]
                    require(digest(text) == u["textHash"], "source unit drift")
                    units[(u["sourceUnitID"], u["textHash"])] = text
    hub = Path("data/interim/documents/ciroh_hub_corpus.json")
    if hub.exists():
        for page in json.loads(hub.read_bytes())["pages"]:
            # The occurrence binding supplies the page URL and verified text hash.
            text = page["content_mdx"]
            units[(page["canonical_url"], digest(text))] = text
    return units


def build_case(cid, frame, originals, provenance, signatures, units, *, source_ids=None):
    """Build an allowlisted public view and private reversible evidence index."""
    sides, cites = citations(frame)
    identity = "groupID" in frame
    ids = frame["occurrenceIDs"] if identity else sorted(set(cites).union(*sides))
    if source_ids is not None:
        require(identity, "explicit source rows only apply to identity cases")
        ids = source_ids
    require(len(ids) == len(set(ids)) and ids, "invalid case membership")
    occurrences, artifacts, excerpts, private = [], {}, {}, {}
    scope = frame["identityScope" if identity else "evidenceScope"]
    case = dict(
        id=cid,
        phase="Identity" if identity else "Typed relation",
        occurrences=occurrences,
        artifacts=[],
        excerpts={},
        scope=scope,
    )
    aliases = {oid: f"O{i}" for i, oid in enumerate(ids, 1)}

    def excerpt(text):
        """Intern exact strings, preserving whitespace, case and punctuation."""
        if text not in excerpts:
            excerpts[text] = f"Q{len(excerpts) + 1}"
        return excerpts[text]

    for oid in ids:
        o = originals[oid]
        require(len(o["sourceArtifacts"]) == 1, "ambiguous artifact binding")
        art = o["sourceArtifacts"][0]
        artifact = artifacts.setdefault(
            art, dict(id=f"S{len(artifacts)+1}", families=o["sourceFamilies"])
        )
        if art.startswith(("http://", "https://")):
            artifact["source"] = art
        elif art.startswith("hydroshare:"):
            artifact["source"] = (
                "https://www.hydroshare.org/resource/" + art.split(":", 1)[1] + "/"
            )
        ref = provenance[oid]["originalReference"]
        bindings = private[aliases[oid]] = dict(
            occurrenceID=oid, artifact=art, source=ref, evidence=[]
        )
        member = dict(
            id=aliases[oid],
            artifact=artifact["id"],
            labels=o["labels"],
            ontologyClass=o["ontologyClass"],
            versions=o["versions"],
            granularity=o["granularity"],
            evidence=[],
        )
        attrs = o.get("attributes", {})
        member["details"] = {
            k: attrs[k]
            for k in (
                "version",
                "release",
                "doi",
                "orcid",
                "title",
                "name",
                "resourceId",
                "literalName",
                "displayName",
                "role",
                "softwareName",
                "versionExpression",
                "dateReleased",
                "defaultBranch",
                "description",
                "identifier",
                "identifierValue",
                "resourceType",
                "year",
            )
            if attrs.get(k)
        }
        occurrences.append(member)
        seen_cites = 0
        for n, e in enumerate(o["evidenceReferences"]):
            ptr = f"/evidenceReferences/{n}"
            full = e.get("evidenceText")
            item = dict(quote=excerpt(full) if full else None)
            item["location"] = {
                k: e[k]
                for k in (
                    "sectionTitle",
                    "path",
                    "sourceField",
                    "startLine",
                    "endLine",
                    "startOffsetInUnit",
                    "endOffsetInUnit",
                    "startOffsetInAuthority",
                    "endOffsetInAuthority",
                    "startOffsetInDocument",
                    "endOffsetInDocument",
                    "version",
                    "sourceVersion",
                    "sourceLocation",
                )
                if e.get(k) is not None
            }
            if e.get("canonical_url"):
                artifact["source"] = e["canonical_url"]
            unit = units.get((e.get("sourceUnitID"), e.get("sourceUnitTextHash")))
            if unit is None and e.get("canonical_url"):
                unit = units.get((e["canonical_url"], e.get("sourceUnitTextHash")))
            if unit and full:
                start, end = e["startOffsetInUnit"], e["endOffsetInUnit"]
                require(unit[start:end] == full, "context offset drift")
                before, after = unit[max(0, start - 240) : start], unit[end : end + 240]
                if before or after:
                    item["context"] = [before, after]
            bound = []
            for b in cites[oid]:
                q = b["quote"]
                if q["reference"]["jsonPointer"] != ptr:
                    continue
                require(
                    all(
                        b["source"][k] == ref[k]
                        for k in ("file", "line", "recordSha256")
                    )
                    and token(e) == q["reference"]["evidenceRecordSha256"]
                    and digest(full) == q["fullQuoteSha256"]
                    and full[q["quoteStart"] : q["quoteEnd"]] == q["literalExcerpt"],
                    "citation drift",
                )
                bound.append(excerpt(q["literalExcerpt"]))
                seen_cites += 1
            if bound:
                item["relationEvidence"] = list(dict.fromkeys(bound))
            member["evidence"].append(item)
            bindings["evidence"].append(
                dict(pointer=ptr, recordSha256=token(e), **item)
            )
        require(seen_cites == len(cites[oid]), "unbound relation citation")
    case["artifacts"] = list(artifacts.values())
    case["excerpts"] = {alias: text for text, alias in excerpts.items()}
    if identity:
        labels = Counter(label for m in occurrences for label in m["labels"])
        case.update(
            label=labels.most_common(1)[0][0] if labels else "Unnamed referent",
            ontologyClass=frame["ontologyClass"],
        )
        key = frame["groupID"]
    else:
        require(
            all(sides) and not sides[0].intersection(sides[1]),
            "ambiguous relation direction",
        )
        case["endpoints"] = [
            dict(ontologyClass=cls, occurrences=[aliases[o] for o in sorted(side)])
            for cls, side in zip(frame["endpointClasses"], sides)
        ]
        case["predicate"] = frame["predicate"]
        case["definitions"] = []
        for sig in sorted({s["signature"] for s in frame["support"]}):
            r = signatures[sig]
            require(r["name"] == case["predicate"], "predicate drift")
            case["definitions"].append(
                {k: r[k] for k in ("domain", "range", "note", "evidence") if k in r}
            )
        key = [frame["subject"], frame["predicate"], frame["object"]]
    original = [e["quote"] for m in occurrences for e in m["evidence"] if e["quote"]]
    stats = dict(
        case=cid,
        phase=case["phase"],
        scope=scope,
        occurrences=len(ids),
        artifacts=len(artifacts),
        originalExcerpts=len(original),
        distinctOriginalExcerpts=len(set(original)),
    )
    return (
        case,
        dict(frameKey=key, frameRecordSha256=token(frame), members=private),
        stats,
    )


def describe_endpoints(case, frame, groups, provenance, *, representatives=None):
    """Describe each projected referent using source labels and preserve its directed witnesses."""
    sides, _ = citations(frame)
    for key, size, witnesses, endpoint in zip(
        (frame["subject"], frame["object"]),
        frame["endpointSizes"],
        sides,
        case["endpoints"],
    ):
        members = groups[key]["occurrenceIDs"] if key in groups else [key]
        if representatives is not None:
            witnesses = {representatives[oid] for oid in witnesses}
        require(
            len(members) == size and witnesses.issubset(members),
            "directed endpoint drift",
        )
        labels = Counter(
            label for oid in members for label in provenance[oid]["labels"]
        )
        endpoint.update(
            label=labels.most_common(1)[0][0] if labels else "Unnamed referent",
            size=size,
        )


def prepare(output, evaluator, selection=None):
    """Atomically publish a fresh public application and a separate custodian crosswalk."""
    require(not output.exists(), "output already exists")
    root = frozen.ROOT
    frozen.prior.identity.f.replay.verify(root)

    def rows(name):
        return list(frozen.w.r.rows(root / (name + ".jsonl")))

    automatic = rows("automatic-identity-frame")
    frames = select(automatic, rows("typed-relation-frame"), selection)
    # Historical memberships may describe a relation endpoint but never enter phase 1.
    groups = {g["groupID"]: g for g in automatic + rows("historical-approvals")}
    ids = set()
    for f in frames:
        sides, cites = citations(f)
        ids.update(f.get("occurrenceIDs", []), cites, *sides)
    provenance = {m["occurrenceID"]: m for m in rows("occurrence-provenance")}
    originals = selected_originals({oid: provenance[oid] for oid in ids})
    units = wider_context(originals)
    signatures = {
        s["id"]: s for s in yaml.safe_load(frozen.w.SPEC.read_text())["relations"]
    }
    public = dict(
        evaluator=evaluator,
        purpose="Exploratory usability and workload pilot",
        cases=[],
    )
    private, stats = {}, []
    for n, f in enumerate(frames, 1):
        cid = f"C{n:02}"
        case, private[cid], counts = build_case(
            cid, f, originals, provenance, signatures, units
        )
        if "endpoints" in case:
            describe_endpoints(case, f, groups, provenance)
        public["cases"].append(case)
        stats.append(counts)
    return publish(output, public, private, stats, root)


def publish(output, public, private, stats, root):
    """Publish the portable reviewer and private bindings together under a fresh path."""
    require(not output.exists(), "output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "bundle"
        reviewer = stage / "reviewer"
        shutil.copytree(HERE / "static", reviewer / "static")
        for name in ("app.py", "http_local.py"):
            shutil.copyfile(HERE / name, reviewer / name)
        shutil.copyfile(
            HERE.parent / "publication_pilot1/static/save_coordinator.js",
            reviewer / "static/save_coordinator.js",
        )
        write(reviewer / "cases.json", public)
        files = {
            p.relative_to(reviewer).as_posix(): frozen.w.r.identity.sha(p)
            for p in sorted(reviewer.rglob("*"))
            if p.is_file()
        }
        write(reviewer / "package-manifest.json", dict(version=1, files=files))
        (stage / "private").mkdir()
        write(
            stage / "private/mapping.json",
            dict(
                cases=private,
                counts=stats,
                frameManifestSha256=frozen.w.r.identity.sha(root / "manifest.json"),
                packageSha256=frozen.w.r.identity.sha(reviewer / "cases.json"),
            ),
        )
        stage.rename(output)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--evaluator", default="researcher")
    parser.add_argument(
        "--selection",
        type=Path,
        help="Explicit private frame keys for an exploratory package",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            prepare(
                args.output,
                args.evaluator,
                json.loads(args.selection.read_text()) if args.selection else None,
            ),
            indent=2,
        )
    )
