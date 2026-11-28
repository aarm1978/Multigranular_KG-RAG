"""Prepare the exploratory alignment instrument from exact-deduplicated frames."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import yaml

from src.annotation.alignment_review import prepare as review
from src.evaluation import step14_deduplicated_alignment as authority

DEFAULT = review.DEFAULT.with_name("researcher-pilot-v2")
rows = authority.rows
require = review.require


def pilot_selection(groups, relations, previous, group_ledger, relation_ledger):
    """Keep valid old cases in order, replacing ineligible cases in their usability stratum."""
    identities = {g["groupID"]: g for g in groups}
    triples = {(r["subject"], r["predicate"], r["object"]): r for r in relations}
    old_groups = {
        s["groupID"]: (s, g) for g in group_ledger for s in g["sourceRecords"]
    }
    old_triples = {tuple(s["originalTriple"]): s for s in relation_ledger}
    selected, used = [], set()
    for cid, old in previous["cases"].items():
        key = old["frameKey"]
        if isinstance(key, str):
            source, new = old_groups[key]
            require(
                source["recordSha256"] == old["frameRecordSha256"],
                "prior identity drift",
            )
            if new["groupID"] in identities:
                frame = identities[new["groupID"]]
            else:
                scope = next(s["scope"] for s in previous["counts"] if s["case"] == cid)
                candidates = [
                    g
                    for g in groups
                    if g["identityScope"] == scope
                    and g["groupID"] not in used
                    and not set(g["originalGroups"]).intersection(
                        c["frameKey"]
                        for c in previous["cases"].values()
                        if isinstance(c["frameKey"], str)
                    )
                ]
                frame = min(
                    candidates,
                    key=lambda g: (
                        abs(g["size"] - len(source["originalMembers"])),
                        g["ontologyClass"] != new["ontologyClass"],
                        g["groupID"],
                    ),
                )
            used.add(frame["groupID"])
        else:
            d = old_triples[tuple(key)]
            require(
                d["originalRecordSha256"] == old["frameRecordSha256"],
                "prior relation drift",
            )
            frame = triples[tuple(d["projectedTriple"])]
        selected.append(frame)

    def changed(r):
        """Exercise an original citation whose retained occurrence differs."""
        return any(
            s["citedEndpoints"] != s["projectedCitedOccurrences"]
            for s in r.get("support", [])
        )

    if not any(map(changed, selected)):
        selected.append(next(r for r in relations if changed(r)))
    require(
        len({review.token(f) for f in selected}) == len(selected),
        "duplicate pilot case",
    )
    return selected


def validate_sides(frame, reps, owners):
    """Verify original directed citation witnesses against their recorded and current projections."""
    for s in frame["support"]:
        cited = {e["binding"]["occurrenceID"] for e in s["evidence"]}
        sides = s["citedEndpoints"]
        require(
            len(sides) == 2 and all(side and set(side) <= cited for side in sides),
            "missing directed original citation",
        )
        projected = [sorted({reps[o] for o in side}) for side in sides]
        require(
            projected == s["projectedCitedOccurrences"], "cited representative drift"
        )
        for side, end in zip(projected, (frame["subject"], frame["object"])):
            require(
                {owners.get(o, o) for o in side} == {end}, "directed membership drift"
            )


def representative_view(case, mapping, reps):
    """Render each representative once, retaining a private pointer for every extraction and span."""
    members, indices, contexts = {}, {}, {}
    case["contexts"] = {}
    original = mapping["members"]
    display = {}
    context_count = 0
    for row in case["occurrences"]:
        binding = original[row["id"]]
        rep = reps[binding["occurrenceID"]]
        metadata = {k: v for k, v in row.items() if k not in ("id", "evidence")}
        if rep not in members:
            members[rep] = dict(metadata, id=f"O{len(members)+1}", evidence=[])
            indices[rep] = {}
        member = members[rep]
        require(
            all(member[k] == v for k, v in metadata.items()),
            "incompatible duplicate member metadata",
        )
        display[row["id"]] = member["id"]
        binding.update(representativeID=rep, displayAlias=member["id"])
        for e, ref in zip(row["evidence"], binding["evidence"]):
            if "context" in e:
                before, after = e.pop("context")
                full = case["excerpts"][e["quote"]]
                window = before + full + after
                if window not in contexts:
                    alias = contexts[window] = f"X{len(contexts)+1}"
                    case["contexts"][alias] = dict(
                        before=before, quote=e["quote"], after=after
                    )
                e.update(
                    contextID=contexts[window],
                    quoteStartInContext=len(before),
                    quoteEndInContext=len(before) + len(full),
                )
                ref.pop("context")
                context_count += 1
            # Only identical displays for copies of this specific representative share a row.
            key = review.token(e)
            if key not in indices[rep]:
                indices[rep][key] = len(member["evidence"])
                member["evidence"].append(e)
            ref["displayEvidenceIndex"] = indices[rep][key]
    for end in case.get("endpoints", []):
        end["occurrences"] = list(dict.fromkeys(display[a] for a in end["occurrences"]))
    case["occurrences"] = list(members.values())
    case["memberUnit"] = "source-local representative"
    mapping["representatives"] = {m["id"]: rep for rep, m in members.items()}
    mapping["extractions"] = mapping.pop("members")
    return context_count


def prepare(output=DEFAULT, evaluator="researcher", selection=None):
    """Build a fresh portable pilot, independently resolving the original cited source lines."""
    require(not output.exists(), "output already exists")
    root = authority.ROOT
    authority.verify(root)
    align = root / "alignment"
    groups = list(rows(align / authority.AUTO))
    relations = list(rows(align / authority.REL))
    prior = None
    if selection is None:
        old = review.DEFAULT
        prior = json.loads((old / "private/mapping.json").read_bytes())
        require(
            authority.sha(old / "reviewer/cases.json") == prior["packageSha256"],
            "prior package drift",
        )
        selected = pilot_selection(
            groups,
            relations,
            prior,
            rows(align / "identity-dispositions.jsonl"),
            rows(align / "relation-dispositions.jsonl"),
        )
    else:
        selected = review.select(groups, relations, selection)
    require(
        all(f["authority"] == "automatic_prediction" for f in selected),
        "automatic frame required",
    )
    endpoints = {
        g["groupID"]: g
        for g in groups + list(rows(align / "historical-projections.jsonl"))
    }
    owners = {o: k for k, g in endpoints.items() for o in g["occurrenceIDs"]}
    reps = {
        r["original"]: r["representative"]
        for r in rows(root / "graph/node-mapping.jsonl")
    }
    sources = {}
    ids = set()
    for f in selected:
        if "groupID" in f:
            members = {o for s in f["sourceRecords"] for o in s["originalMembers"]}
            require(
                {reps[o] for o in members} == set(f["occurrenceIDs"]),
                "identity projection drift",
            )
            sources[f["groupID"]] = sorted(
                members.union(f["occurrenceIDs"]),
                key=lambda o: (reps[o], o != reps[o], o),
            )
            ids.update(sources[f["groupID"]])
        else:
            validate_sides(f, reps, owners)
            ids.update(review.citations(f)[1])
    projected = {
        m["occurrenceID"]: m for m in rows(align / "occurrence-provenance.jsonl")
    }
    member_file = review.frozen.w.BASE / "referent-groups/v1/members.jsonl"
    provenance = {
        m["occurrenceID"]: m for m in rows(member_file) if m["occurrenceID"] in ids
    }
    require(
        all(projected[o] == provenance[o] for o in ids.intersection(projected)),
        "representative provenance drift",
    )
    originals = review.selected_originals({o: provenance[o] for o in ids})
    units = review.wider_context(originals)
    signatures = {
        s["id"]: s
        for s in yaml.safe_load(review.frozen.w.SPEC.read_bytes())["relations"]
    }
    public = dict(
        evaluator=evaluator,
        purpose="Exploratory usability and workload pilot",
        cases=[],
    )
    private, stats = {}, []
    for n, f in enumerate(selected, 1):
        cid = f"C{n:02}"
        case, mapping, counts = review.build_case(
            cid,
            f,
            originals,
            provenance,
            signatures,
            units,
            source_ids=sources.get(f.get("groupID")),
        )
        if "groupID" in f:
            original_members = {
                o for s in f["sourceRecords"] for o in s["originalMembers"]
            }
            mapping["sourceRecords"] = f["sourceRecords"]
        else:
            original_members = set(review.citations(f)[1])
            review.describe_endpoints(
                case, f, endpoints, projected, representatives=reps
            )
            mapping["directedSupport"] = f["support"]
        counts["originalMembers"] = len(original_members)
        counts["contextReferences"] = representative_view(case, mapping, reps)
        if "groupID" in f:
            require(
                list(mapping["representatives"].values()) == f["occurrenceIDs"],
                "representative coverage drift",
            )
            labels = Counter(l for m in case["occurrences"] for l in m["labels"])
            case["label"] = (
                labels.most_common(1)[0][0] if labels else "Unnamed referent"
            )
        counts.update(
            representatives=len(case["occurrences"]),
            distinctContexts=len(case["contexts"]),
            distinctExcerptDisplays=len(case["excerpts"]),
        )
        if prior and cid in prior["cases"]:
            mapping["previousPilotKey"] = prior["cases"][cid]["frameKey"]
        public["cases"].append(case)
        private[cid] = mapping
        stats.append(counts)
    return review.publish(output, public, private, stats, root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--evaluator", default="researcher")
    parser.add_argument(
        "--selection",
        type=Path,
        help="Private keys in the deduplicated automatic frames",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            prepare(
                args.output,
                args.evaluator,
                json.loads(args.selection.read_bytes()) if args.selection else None,
            ),
            indent=2,
        )
    )
