"""Prepare and validate the final evidence-bound relation Batch."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch
import json
import math
import tempfile

import yaml
from jsonschema import Draft202012Validator
from src.evaluation import step14_identity_closure as closure

w, final = closure.w, closure.final
ROOT = w.BASE / "typed-relation-adjudication/v1"
SOURCE = closure.ROOT
ARCHIVE = Path("tests/fixtures/ontology/v0.1.8")
ENDPOINTS = w.BASE / "unified-review-queue/v1/endpoint-provenance.jsonl"
emit = final.replay.v3.coverage.write_rows
PROMPT = """Judge each named case independently. Sources are original occurrence-local excerpts.
left/right are provisional referents. Historical directions, predicates and lead descriptions
are competing hypotheses. Joint evidence must support the specific relation and direction.
Similarity, co-occurrence and failure to establish identity do not establish a relation.
Respect versions, implementations, general referents and the ontology evidence requirements.
Return one item per supported predicate/direction, or a gap for affirmative evidence outside
the ontology, or abstain. Cite source quotations for both endpoints of positive judgments.
For an internal case, compare the two named original occurrences within the final identity
group: use material_exception only for a scientifically supported version relationship that
materially conflicts with the group. Otherwise use mistaken or abstain for ambiguity.
Explain each judgment. Internal cases cannot produce edges or change membership.
Use null signature and direction for outcomes other than relation."""
STRING = dict(type="string")
ITEM = w.pilot.obj(
    dict(
        case=STRING,
        outcome=dict(type="string", enum=["relation", "gap", "abstain", "material_exception", "mistaken"]),
        signature=dict(type=["string", "null"]),
        direction=dict(enum=["forward", "reverse", None], type=["string", "null"]),
        evidence=dict(type="array", items=STRING),
        explanation=STRING,
    )
)
SCHEMA = w.pilot.obj(dict(items=dict(type="array", items=ITEM)))


def historical(path, digest):
    """Resolve just the predecessor ontology paths through the exact v0.1.8 fixture."""
    if path in (w.SPEC, w.SPEC.with_name("ciroh_ontology.owl")):
        path = ARCHIVE / path.name
    w.require(w.r.identity.sha(path) == digest, "HISTORICAL_DRIFT:" + str(path))
    return path


def source_pins():
    """Verify the complete original closure manifest, including each original input."""
    path = SOURCE / "manifest.json"
    manifest = w.live.load(path)
    pins = {str(path): w.r.identity.sha(path)}
    for name, h in manifest["inputHashes"].items():
        pins[str(historical(Path(name), h))] = h
    for name, h in manifest["outputHashes"].items():
        pins[str(historical(SOURCE / name, h))] = h
    authority = ENDPOINTS.parent / "manifest.json"
    h = w.live.load(authority)["outputHashes"][ENDPOINTS.name]
    pins[str(historical(ENDPOINTS, h))] = h
    for path in (
        authority,
        w.SPEC,
        w.SPEC.with_name("ciroh_ontology.owl"),
        Path(__file__).resolve().relative_to(Path.cwd()),
    ):
        pins[str(path)] = w.r.identity.sha(path)
    w.require(
        pins[str(w.SPEC.with_name("ciroh_ontology.owl"))]
        == "cf318846d977f894dad1caa07d390e2ac2253bd2a6f8ecd1e1e43058891dc89a",
        "FROZEN_OWL",
    )
    w.require(
        pins[str(w.SPEC)] == "6df101620e6931195b1fe5eb665ff15293f702004ca155c3cdba65d63c2dd2b5",
        "FROZEN_SPEC",
    )
    return pins


def project(sides, owner):
    """Resolve each whole endpoint to one referent, retaining unmapped occurrences."""
    refs = [{owner.get(o, o) for o in side} for side in sides]
    return tuple(next(iter(s)) for s in refs) if all(len(s) == 1 for s in refs) else None


def cited(row):
    """Read original role-bound citations from each of the three saved support formats."""
    for s in row["support"]:
        if s.get("source") == "decision-stage/v2":
            for item in s["record"]["support"]:
                for ref in item["value"]["evidenceIDs"]:
                    binding = item["evidenceBindings"][ref]
                    yield binding["occurrenceID"], binding["selectedEvidence"]
        else:
            for c in s.get("record", s)["citations"]:
                b = c["binding"]
                yield b["occurrenceID"], b


def lead_aliases(item):
    """Retrieve the exact component-local namespace used in a lead explanation."""
    version, uid, _ = item["reference"]
    folder = final.ROOT if version == "v2" else final.previous.ROOT
    return w.live.load(folder / "bindings" / (uid + ".json"))["aliases"]


def recover(item, owner):
    """Recover explicit original aliases only when citations identify both projected sides."""
    aliases = lead_aliases(item)
    lead = item["original"]["modelItem"]
    sides = []
    for field in ("subject", "object"):
        names = closure.ALIAS.findall(lead[field])
        if not names or any(n not in aliases for n in names):
            return None
        sides.append(sorted({aliases[n] for n in names}))
    refs = project(sides, owner)
    evidence = {
        owner.get(b["occurrenceID"], b["occurrenceID"]) for c in item["citations"] if (b := c["binding"])
    }
    return sides if refs and refs[0] != refs[1] and set(refs) <= evidence else None


def make_request(keys, cases, records, owner, group_sizes, spec, hierarchy, group_context):
    """Bind the selected original quotations and offer signatures separately per direction."""
    refs = {r: f"R{i}" for i, r in enumerate(sorted({r for k in keys for r in k[:2]}), 1)}
    objects = {}
    bindings = {}
    checks = {}
    visible = []
    signatures = {}
    sources = {}

    def occurrence(o):
        if o not in objects:
            e = records[o]
            objects[o] = dict(
                id=f"O{len(objects)+1}",
                name=e["labels"],
                ontologyClass=e["ontologyClass"],
                sourceFamily=e["sourceFamilies"],
                source=[sources.setdefault(a, f"S{len(sources)+1}") for a in e["sourceArtifacts"]],
                versions=e["versions"],
                granularity=e["granularity"],
                quotes=[],
            )
        return objects[o]

    for n, key in enumerate(keys, 1):
        left, right = key[:2]
        internal = left == right
        rows = cases[key]
        cid = f"P{n}"
        evidence = set()
        sides = [set(), set()]
        hints = []
        for row in rows:
            original = row["occurrenceEndpoints"]
            direction = project(original, owner)
            reverse = not internal and direction[0] != left
            for i, side in enumerate(original):
                sides[i ^ reverse].update(side)
            hint = dict(predicate=row["predicate"], direction="reverse" if reverse else "forward")
            if row["kind"] == "lead":
                for lead in row["support"]:
                    names = lead_aliases(lead)

                    def rename(match):
                        return occurrence(names[match[0]])["id"] if match[0] in names else match[0]

                    hint = dict(
                        hint,
                        description=closure.ALIAS.sub(rename, lead["original"]["modelItem"]["explanation"]),
                    )
                    hints.append(hint)
            else:
                hint["originalSubject"] = occurrence(original[0][0])["id"]
                hint["originalObject"] = occurrence(original[1][0])["id"]
                hints.append(hint)
            for oid, b in cited(row):
                obj = occurrence(oid)
                matches = [
                    q
                    for q in records[oid]["selectedEvidence"]
                    if q["reference"] == b["reference"] and q["fullQuoteSha256"] == b["fullQuoteSha256"]
                ]
                w.require(len(matches) == 1, "SOURCE_QUOTE_DRIFT")
                if "literalExcerpt" in b:
                    w.require(matches[0]["literalExcerpt"] == b["literalExcerpt"], "LITERAL_DRIFT")
                q = matches[0]
                eid = obj["id"] + "Q" + str(records[oid]["selectedEvidence"].index(q) + 1)
                if eid not in bindings:
                    obj["quotes"].append(dict(id=eid, text=q["literalExcerpt"]))
                    bindings[eid] = dict(
                        occurrenceID=oid, quote=q, source=records[oid]["originalReference"]
                    )
                evidence.add(eid)
        classes = []
        endpoints = []
        for side, referent in zip(sides, (left, right)):
            cls = {records[o]["ontologyClass"] for o in side}
            w.require(len(cls) == 1, "MIXED_ENDPOINT_CLASSES")
            classes.append(cls.pop())
            endpoints.append(
                dict(
                    referent=refs[referent],
                    membershipSize=group_sizes.get(referent, 1),
                    witnesses=[occurrence(o)["id"] for o in sorted(side) if o in objects or internal],
                )
            )
        options = {}
        if not internal:
            for d, (a, b) in [("forward", classes), ("reverse", classes[::-1])]:
                options[d] = []
                for rel in w.allowed_relations(list(sides[0] | sides[1]), records, spec, hierarchy):
                    if w.fits(a, rel["domain"], hierarchy) and w.fits(b, rel["range"], hierarchy):
                        options[d].append(rel["id"])
                        signatures[rel["id"]] = {
                            k: rel[k] for k in ("name", "domain", "range", "evidence", "note") if k in rel
                        }
        visible.append(
            dict(
                case=cid,
                internal=internal,
                left=endpoints[0],
                right=endpoints[1],
                historical=hints,
                evidence=sorted(evidence),
                options=options,
            )
        )
        if internal:
            visible[-1]["finalGroupDescription"] = group_context[left]
            visible[-1]["versionEvidenceRequirement"] = next(
                r["evidence"] for r in spec["relations"] if r["id"] == "D-27"
            )
        checks[cid] = dict(
            key=key,
            sides=[sorted(s) for s in sides],
            options=options,
            evidence=sorted(evidence),
            internal=internal,
        )
    payload = dict(cases=visible, occurrences=list(objects.values()), signatures=signatures)
    body = dict(
        model="gpt-6.1-sol",
        reasoning=dict(effort="medium"),
        store=False,
        input=w.live.encode(payload).decode(),
        instructions=PROMPT,
        text=dict(format=dict(type="json_schema", name="relation_decisions", strict=True, schema=SCHEMA)),
        max_output_tokens=2048 + 1024 * len(keys),
    )
    return body, dict(cases=checks, evidence=bindings, aliases={r["id"]: o for o, r in objects.items()})


def validate(value, b):
    """Validate individual judgments and record missing cases without suppressing siblings."""
    w.require(isinstance(value, dict) and isinstance(value.get("items"), list), "INVALID_ENVELOPE")
    seen = set()
    items = []
    validator = Draft202012Validator(ITEM)
    for item in value["items"]:
        reasons = [e.message for e in validator.iter_errors(item)]
        if not reasons:
            cid = item["case"]
            c = b["cases"].get(cid)
            outcome = item["outcome"]
            if not c:
                reasons.append("UNKNOWN_CASE")
            else:
                refs = set(item["evidence"])
                if not refs <= set(c["evidence"]):
                    reasons.append("UNKNOWN_CASE_EVIDENCE")
                if outcome in ("relation", "gap", "material_exception"):
                    cited_ids = {b["evidence"][e]["occurrenceID"] for e in refs if e in b["evidence"]}
                    if not all(cited_ids.intersection(s) for s in c["sides"]):
                        reasons.append("MISSING_ENDPOINT_SUPPORT")
                if outcome not in (
                    ("material_exception", "abstain", "mistaken")
                    if c["internal"]
                    else ("relation", "gap", "abstain")
                ):
                    reasons.append("INVALID_CASE_OUTCOME")
                if outcome == "relation":
                    if item["signature"] not in c["options"].get(item["direction"], []):
                        reasons.append("INVALID_DIRECTION_OR_SIGNATURE")
                elif item["signature"] is not None or item["direction"] is not None:
                    reasons.append("UNEXPECTED_EDGE")
                if not item["explanation"].strip():
                    reasons.append("EMPTY_EXPLANATION")
                if not reasons:
                    seen.add(cid)
        items.append(dict(original=item, reasons=reasons))
    # Mutually exclusive case outcomes require a coherent judgment.
    for cid in seen.copy():
        valid = [i for i in items if not i["reasons"] and i["original"]["case"] == cid]
        outcomes = {i["original"]["outcome"] for i in valid}
        if len(outcomes) > 1 and outcomes != {"gap", "relation"}:
            for i in valid:
                i["reasons"].append("CONFLICTING_OUTCOMES")
            seen.remove(cid)
    exceptions = []
    for record in items:
        item = record["original"]
        if not record["reasons"] and item["outcome"] == "material_exception":
            case = b["cases"][item["case"]]
            exceptions.append(
                dict(
                    case=item["case"],
                    finalGroup=case["key"][0],
                    originalEndpoints=case["sides"],
                    rationale=item["explanation"],
                    evidence=[b["evidence"][ref] for ref in item["evidence"]],
                )
            )
    return dict(
        consistencyExceptions=exceptions,
        items=items,
        envelopeErrors=[e.message for e in Draft202012Validator(SCHEMA).iter_errors(value) if not e.path],
        missingOrUnresolved=sorted(b["cases"].keys() - seen),
    )


def process(root, uid, body, response):
    """Preserve native response and usage before independent item validation."""
    base = root / "execution"
    w.live.save(base / (uid + ".response.json"), response)
    report = dict(usage=response.get("usage"))
    try:
        w.require(response.get("status") == "completed", "INCOMPLETE_RESPONSE")
        value = w.transport.decode(w.live.provider.extract_model_output(response))
        report.update(validate(value, w.live.load(root / "bindings" / (uid + ".json"))))
    except (ValueError, TypeError, w.live.provider.OpenAIProviderError) as exc:
        report["error"] = str(exc)
    w.live.save(base / (uid + ".validation.json"), report)
    return report


def prepare(output):
    """Verify the closure and write a fresh, atomic preparation with one case per projection."""
    w.require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    pins = source_pins()
    spec = yaml.safe_load(w.SPEC.read_text())
    hierarchy = w.ancestors(spec)
    sig = next(r for r in spec["relations"] if r["id"] == "D-16")
    groups = list(w.r.rows(SOURCE / "groups.jsonl"))
    owner = {}
    sizes = {}
    overlay = []
    for g in groups:
        gid = g["groupID"]
        ids = g["occurrenceIDs"]
        w.require(set(ids).isdisjoint(owner), "OVERLAPPING_MEMBERS")
        owner.update(dict.fromkeys(ids, gid))
        sizes[gid] = len(ids)
        compatible = w.fits(g["ontologyClass"], sig["range"], hierarchy)
        overlay.append(
            dict(
                groupID=gid,
                occurrenceIDs=ids,
                authority=g["authority"],
                wasCompatible=g["rangeCompatible"],
                nowCompatible=compatible,
                historicalMaterialization=g.get("approval", {}).get("materializationStatus"),
            )
        )
    w.require(
        len(groups) == 2195
        and len(owner) == 8912
        and all(g["nowCompatible"] for g in overlay)
        and sum(not g["wasCompatible"] for g in overlay) == 11,
        "OVERLAY_DRIFT",
    )
    recorded = {m["occurrenceID"]: m["groupID"] for m in w.r.rows(SOURCE / "occurrence-mappings.jsonl")}
    w.require(owner == recorded, "MEMBERSHIP_DRIFT")
    cleared = Counter(g["ontologyClass"] for g in groups if not g["rangeCompatible"])
    w.require(cleared == {"Repository": 6, "Workflow": 5}, "REPRESENTATION_DRIFT")
    rows = list(w.r.rows(SOURCE / "relation-inputs.jsonl"))
    counts = Counter(r["predicate"] for r in rows if r["kind"] == "typed")
    cases = defaultdict(list)
    typed = set()
    leftovers = []

    def add(row):
        """Retain complete support while projecting both sides without expansion."""
        a, b = project(row["occurrenceEndpoints"], owner)
        key = tuple(sorted((a, b)))
        if a == b:
            w.require(
                row["predicate"] == "isVersionOf" and all(len(s) == 1 for s in row["occurrenceEndpoints"]),
                "UNEXPECTED_INTERNAL",
            )
            key += tuple(s[0] for s in row["occurrenceEndpoints"])
        elif row["kind"] == "typed":
            typed.add((a, b, row["predicate"]))
        cases[key].append(row)

    for row in rows:
        add(row)
    base_pairs = sum(len(k) == 2 for k in cases)
    recovered = 0
    for item in w.r.rows(SOURCE / "unresolved-leads.jsonl"):
        sides = recover(item, owner)
        if sides:
            add(dict(kind="lead", predicate=None, occurrenceEndpoints=sides, support=[item]))
            recovered += 1
        else:
            leftovers.append(item)
    records = {e["occurrenceID"]: e for e in w.r.rows(ENDPOINTS)}
    edges = {k for k in cases if len(k) == 2}
    packs = []
    for ids in w.pack_edges(edges.copy(), limit=5):
        selected = sorted(k for k in edges if set(k) <= set(ids))
        if selected:
            packs.append(selected)
        edges.difference_update(selected)
    internal = sorted(k for k in cases if len(k) > 2)
    internal_groups = {k[0] for k in internal}
    references = {
        tuple(ref): g["groupID"] for g in groups if g["groupID"] in internal_groups for ref in g["support"]
    }
    group_context = {}
    for assignment in w.r.rows(SOURCE / "component-assignments.jsonl"):
        group = references.get(tuple(assignment["reference"]))
        if group:
            item = assignment["assessment"]["modelItem"]
            group_context[group] = {k: item[k] for k in ("granularity", "rationale", "broaderReferent")}
    for g in sorted(internal_groups):
        packs.append([k for k in internal if k[0] == g])
    w.require(Counter(k for p in packs for k in p) == Counter(list(cases)), "PACKING_DRIFT")
    output.parent.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        root = Path(temp) / "package"
        root.mkdir()
        requests = []
        input_tokens = out = cap = 0
        for n, keys in enumerate(packs, 1):
            uid = f"T{n:04d}"
            body, b = make_request(keys, cases, records, owner, sizes, spec, hierarchy, group_context)
            final.pilot_preflight.check_schema_limits(SCHEMA)
            size = len(w.live.encode(body))
            w.require(size + body["max_output_tokens"] + 2048 < final.CONTEXT, "CONTEXT_HEADROOM")
            requests.append(dict(custom_id=uid, method="POST", url="/v1/responses", body=body))
            w.live.save(root / "bindings" / (uid + ".json"), b)
            input_tokens += math.ceil(size / 4)
            out += 250 * len(keys) + 200
            cap += body["max_output_tokens"]
        summary = dict(
            identityGroups=len(groups),
            occurrences=len(owner),
            rangeHoldsCleared=11,
            typed=counts,
            boundLeads=sum(r["kind"] == "lead" for r in rows),
            distinctDirectedNonself=len(typed),
            originalNonselfPairs=base_pairs,
            finalNonselfPairs=len(cases) - len(internal),
            recoveredHistoricalLeads=recovered,
            unresolved=len(leftovers),
            internalCases=len(internal),
            internalGroups=len({k[0] for k in internal}),
            requests=len(packs),
            inputTokens=input_tokens,
            estimatedOutput=out,
            outputCeiling=cap,
            estimatedBatchUSD=(1.25 * input_tokens + 5 * out) / 1e6,
            outputCeilingBatchUSD=(1.25 * input_tokens + 5 * cap) / 1e6,
        )
        emit(root / "requests.jsonl", requests)
        emit(root / "representation-overlay.jsonl", overlay)
        emit(root / "candidates.jsonl", (dict(key=k, support=v) for k, v in sorted(cases.items())))
        emit(root / "unresolved-leads.jsonl", leftovers)
        w.live.save(root / "summary.json", summary)
        w.live.save(
            root / "manifest.json",
            dict(
                inputHashes=pins,
                outputHashes={
                    str(p.relative_to(root)): w.r.identity.sha(p) for p in root.rglob("*") if p.is_file()
                },
            ),
        )
        root.rename(output)
    return summary


def main():
    """Prepare and verify offline or run the separately authorized Batch transport."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "verify", "submit", "status", "retrieve"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.mode == "prepare":
        result = prepare(args.root)
    elif args.mode == "verify":
        result = final.replay.verify(args.root)
    else:
        with patch.object(w, "verify", final.replay.verify), patch.object(w, "process", process):
            result = w.operate(args.root, args.mode)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
