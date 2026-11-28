"""Fingerprint source-local extractions and project frozen Step 13 assertions."""
from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from src.annotation.alignment_review.prepare import PUBLICATION_UNITS
from src.annotation.publication_step8.contracts import canonical_text
from src.evaluation import compute_structural_metrics as metrics
from src.evaluation.step14_semantic_candidates import token
from src.evaluation.step14_alignment_workflow import ancestors, fits, require
from src.extraction.llm.publications.candidate_validation import _precedence_map


def digest(text):
    """Hash a literal source string."""
    return hashlib.sha256(text.encode()).hexdigest()


class Sources:
    """Resolve original evidence through pinned native publication or owner records."""

    def __init__(self, pin):
        self.pin = pin
        self.units = {}
        for path in PUBLICATION_UNITS:
            with pin(path).open() as f:
                for line in f:
                    u = json.loads(line)
                    key = u["sourceUnitID"], u["textHash"]
                    if key in self.units:
                        prior = self.units[key]
                        require(
                            all(
                                u[k] == prior[k]
                                for k in (
                                    "sourceFile",
                                    "rawFileSha256",
                                    "canonicalTextSha256",
                                    "startOffsetInDocument",
                                    "endOffsetInDocument",
                                )
                            ),
                            "AMBIGUOUS_UNIT",
                        )
                    self.units[key] = u

    @lru_cache(maxsize=None)
    def document(self, name, raw_hash, text_hash):
        """Bind the parsed revision to actual document bytes."""
        raw = self.pin(Path(name), raw_hash).read_bytes()
        text = canonical_text(raw)
        require(digest(text) == text_hash, "DOCUMENT_REVISION_DRIFT")
        return text

    @lru_cache(maxsize=None)
    def publication_unit(self, unit, text_hash):
        """Verify once per source unit without using unit identity as a duplicate key."""
        u = self.units[(unit, text_hash)]
        doc = self.document(u["sourceFile"], u["rawFileSha256"], u["canonicalTextSha256"])
        require(
            digest(u["text"]) == text_hash
            and doc[u["startOffsetInDocument"] : u["endOffsetInDocument"]] == u["text"],
            "SOURCE_UNIT_DRIFT",
        )
        return u, doc

    @lru_cache(maxsize=2)
    def owner(self, name, sha):
        """Use original request source text inside the hash-pinned owner report."""
        o = json.loads(self.pin(Path(name), sha).read_bytes())
        return {g["requestID"]: g["nativeValidationView"] for g in o["groupReports"]}

    def parent_path(self, record, pr):
        """Resolve the ordered native page-to-child attachment, independent of request aliases."""
        c = record.get("originalCandidate", {})
        if not c.get("parentPath"):
            return ()
        view = self.owner(pr["path"], pr["sha256"])[pr["requestID"]]
        req = view["originalReplay"]["requestResult"]["request"]
        edges = {
            ("candidate_edge", e["candidateID"]): (
                e["resolvedSource"]["endpointID"],
                e["originalCandidate"]["inventoryId"],
                e["resolvedTarget"]["endpointID"],
            )
            for e in view["projection"]["edges"]
        }
        edges.update(
            {
                ("accepted_assertion", e["assertionID"]): (e["sourceID"], e["inventoryId"], e["targetID"])
                for e in req["acceptedAssertions"]
            }
        )
        previous = req["owner"]["endpointID"]
        path = []
        for ref in c["parentPath"]:
            a, signature, b = edges[ref["referenceType"], ref["referenceID"]]
            require(a == previous, "STRUCTURAL_PATH_DISCONTINUITY")
            path.append((a, signature))
            previous = b
        require(previous == record["resolvedEndpoint"]["endpointID"], "STRUCTURAL_PATH_TARGET")
        return tuple(path)

    def span(self, e, pr):
        """Return document identity, revision, absolute coordinates and literal text digest."""
        text = e["evidenceText"]
        require(text and digest(text) == e["evidenceHash"], "EVIDENCE_HASH_DRIFT")
        family = pr["family"]
        if family == "publications":
            u, doc = self.publication_unit(e["sourceUnitID"], e["sourceUnitTextHash"])
            start, end = e["startOffsetInDocument"], e["endOffsetInDocument"]
            require(
                e["valid"]
                and doc[start:end] == text
                and u["startOffsetInDocument"] + e["startOffsetInUnit"] == start
                and u["startOffsetInDocument"] + e["endOffsetInUnit"] == end
                and u["canonicalArtifactID"] == e["sourceArtifactID"] == e["canonicalPaperID"],
                "PUBLICATION_SPAN_DRIFT",
            )
            document = [
                family,
                u["canonicalArtifactID"],
                u["sourceFile"],
                u["rawFileSha256"],
                u["canonicalTextSha256"],
            ]
        else:
            view = self.owner(pr["path"], pr["sha256"])[pr["requestID"]]
            request = view["originalReplay"]["requestResult"]["request"]
            (u,) = (u for u in request["sourceUnits"] if u["sourceUnitID"] == e["sourceUnitID"])
            start, end = e["startOffsetInAuthority"], e["endOffsetInAuthority"]
            offset = u.get("startOffsetInAuthority", 0)
            require(
                0 <= start - offset < end - offset <= len(u["text"])
                and u["text"][start - offset : end - offset] == text,
                "AUTHORITY_SPAN_DRIFT",
            )
            revision = e["authorityTextSha256"]
            require(
                revision
                and revision
                == u.get(
                    "authorityTextSha256", u.get("content_sha256", u.get("expectedAuthorityTextSha256"))
                ),
                "AUTHORITY_REVISION_DRIFT",
            )
            owner = request["owner"]["endpointID"]
            if family == "github":
                document = [family, owner, e["frozenCommitSha"], e["path"], e.get("cellIndex"), revision]
            elif family == "hydroshare":
                document = [family, owner, e["snapshotID"], e["sourceField"], e.get("source_path"), revision]
            elif family == "ciroh_hub":
                document = [family, owner, e["canonical_url"], e["content_sha256"], revision]
            else:
                raise ValueError("UNKNOWN_FAMILY")
        return [document, start, end, digest(text)]


def fingerprint(node, record, pr, sources):
    """Match a single literal mention with complete source spans and semantic content."""
    c = record.get("originalCandidate", record.get("candidate"))
    if not c:
        return None, "controlled_vocabulary"
    label = c.get("label")
    if not label:
        return None, "missing_label"
    evidence = record.get("evidenceOccurrences", record.get("boundEvidence", []))
    if not evidence:
        return None, "missing_evidence"
    common = {"sourceUnitID", "evidenceText", "evidenceHash"}
    required = {
        "publications": {
            "sourceArtifactID",
            "canonicalPaperID",
            "sourceUnitTextHash",
            "startOffsetInUnit",
            "endOffsetInUnit",
            "startOffsetInDocument",
            "endOffsetInDocument",
        },
        "github": {"authorityTextSha256", "frozenCommitSha", "path"},
        "hydroshare": {"authorityTextSha256", "snapshotID", "sourceField"},
        "ciroh_hub": {"authorityTextSha256", "canonical_url", "content_sha256"},
    }[pr["family"]] | common
    if pr["family"] != "publications":
        required.update(("startOffsetInAuthority", "endOffsetInAuthority"))
    if any(any(e.get(k) is None or e[k] == "" for k in required) for e in evidence):
        return None, "missing_span_or_revision"
    spans = [sources.span(e, pr) for e in evidence]
    document = token(spans[0][0])
    if any(token(s[0]) != document for s in spans):
        return None, "multiple_documents"
    pattern = (
        (r"(?<!\w)" if label[0].isalnum() or label[0] == "_" else "")
        + re.escape(label)
        + (r"(?!\w)" if label[-1].isalnum() or label[-1] == "_" else "")
    )
    mentions = {
        (s[1] + m.start(), s[1] + m.end())
        for s, e in zip(spans, evidence)
        for m in re.finditer(pattern, e["evidenceText"])
    }
    if len(mentions) != 1:
        return None, "multiple_literal_locations" if mentions else "absent_literal_location"
    # Source-local evidence explanations are provenance; only bound text and semantic
    # declarations describe the node. Preserve attribute-to-span associations.
    semantic = {
        k: v
        for k, v in c.items()
        if k not in ("candidateID", "evidenceSpanIDs", "evidence", "attributes", "parentPath")
    }
    if "attributes" in c:
        by_alias = {e["evidenceSpanID"]: s for e, s in zip(evidence, spans) if "evidenceSpanID" in e}
        attrs = []
        for a in c["attributes"]:
            refs = a.get("evidenceSpanIDs", [])
            if any(q not in by_alias for q in refs):
                return None, "unbound_attribute_evidence"
            attrs.append(
                dict(
                    fields={k: v for k, v in a.items() if k != "evidenceSpanIDs"},
                    spans=sorted(token(by_alias[q]) for q in refs),
                )
            )
        semantic["attributes"] = sorted(map(token, attrs))
    if "resolvedEndpoint" in record:
        semantic["endpoint"] = {k: v for k, v in record["resolvedEndpoint"].items() if k != "endpointID"}
    return (
        token(
            [
                node["class"],
                node["inventoryId"],
                node.get("attributes"),
                semantic,
                sorted(map(token, spans)),
                sorted(mentions),
            ]
        ),
        "verified_mention",
    )


def census(graph, native, origins, sources, profile, declarations):
    """Census every graph node, including structural and incompletely bound records."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    keys, refs, reasons = defaultdict(list), defaultdict(list), defaultdict(set)
    paths = defaultdict(set)
    with native.open() as f:
        for line, raw in enumerate(f, 1):
            row = json.loads(raw)
            if row["kind"] != "nodes":
                continue
            oid, pr, n = row["graphID"], row["provenance"], row["nativeRecord"]
            require(token(n) == row["nativeRecordSha256"], "NATIVE_NODE_DRIFT")
            refs[oid].append(line)
            origins[oid].add(pr.get("family", "controlled_vocabulary"))
            key, reason = fingerprint(nodes[oid], n, pr, sources)
            if key:
                keys[oid].append(key)
                path = sources.parent_path(n, pr)
                if path:
                    paths[oid].add(path)
            else:
                reasons[oid].add(reason)

    # Compare only identity-defining source context, independently of incident
    # assertion completeness. Never bridge two known, competing contextual owners.
    context_types = {
        r["operational_target"]
        for r in profile["node_targets"]
        if r.get("identity_policy", {}).get("scope") == "contextual_occurrence"
    }

    @lru_cache(maxsize=None)
    def parent_key(oid):
        """Normalize a verified parent mention or keep an authoritative structural key."""
        if oid not in refs:
            return oid
        if not keys.get(oid) or reasons.get(oid):
            return None
        ancestry = paths.get(oid, ())
        if len(ancestry) > 1:
            return None
        lineage = []
        for path in ancestry:
            for parent, sig in path:
                # The validated page-rooted path consists of successively shorter prefixes.
                if any(len(other) >= len(path) for other in paths.get(parent, ())):
                    return None
                ancestor = parent_key(parent)
                if ancestor is None:
                    return None
                lineage.append((ancestor, sig))
        return token([sorted(keys[oid]), lineage])

    owners = defaultdict(set)
    identifiers = defaultdict(set)
    for edge in graph["edges"]:
        a, b = edge["source"], edge["target"]
        if edge["relation"] == "hasIdentifier":
            identifiers[a].add(token(nodes[b]["attributes"]))
        if (
            nodes[b]["class"] in context_types
            and edge["relation"] in ("reportsMetric", "hasParameter")
            and nodes[a]["class"] != "Paper"
        ):
            owners[b].add(parent_key(a) or a)
    base = defaultdict(list)
    for oid in nodes:
        if oid not in refs:
            reasons[oid].add("native_structural_or_deterministic_record_without_document_spans")
        if reasons[oid]:
            continue
        parents = [[(parent_key(a), sig) for a, sig in path] for path in paths.get(oid, ())]
        if len(parents) > 1 or any(key is None for path in parents for key, _ in path):
            reasons[oid].add("structural_parent_undetermined")
            continue
        key = token(
            [
                sorted(origins[oid]),
                sorted(keys[oid]),
                parents,
                sorted(identifiers[oid]),
                declarations.get(oid),
            ]
        )
        base[key].append(oid)
    buckets = {}
    for key, ids in base.items():
        known = {owner for oid in ids for owner in owners.get(oid, ())}
        if len(known) <= 1:
            buckets[key] = ids
        else:
            for oid in ids:
                if len(owners[oid]) != 1:
                    reasons[oid].add("ambiguous_contextual_owner")
                else:
                    buckets.setdefault(token([key, sorted(owners[oid])]), []).append(oid)
    reps = {k: k for k in nodes}
    blocks = {}
    for key, ids in buckets.items():
        if len(ids) > 1:
            blocks[key] = sorted(ids)
            reps.update(dict.fromkeys(ids, min(ids)))
    return reps, blocks, refs, reasons


class Signatures:
    """Check v0.1.9 signatures using documented Phase B inventory spellings."""

    aliases = {
        ("A-ID01 (ID-R1)", "hasIdentifier"): "ID-R1",
        ("C-D09 / A-AG-R2", "fundedBy"): "C-D09",
        ("C-DC05/A-AG", "hasContributor"): "C-DC05",
        ("D-05", "referencesDataset"): "C-C19",
    }

    def __init__(self, spec):
        self.hierarchy = ancestors(spec)
        self.sigs = {r["id"]: r for r in spec["relations"]}
        self.iris = {r["name"]: r["iri"] for r in spec["classes"]}

    @lru_cache(maxsize=None)
    def valid(self, sig, pred, left, right):
        """Allow equivalent declared class IRIs, including Person/Author/Creator."""
        r = self.sigs.get(self.aliases.get((sig, pred), sig))

        def accepts(cls, allowed):
            values = allowed if isinstance(allowed, list) else [allowed]
            return fits(
                "RepoFile" if cls == "File" else cls,
                values + [self.iris[v] for v in values if v in self.iris],
                self.hierarchy,
            )

        return bool(r and r["name"] == pred and accepts(left, r["domain"]) and accepts(right, r["range"]))


def project_edges(edges, reps, nodes, signatures, generic, profile):
    """Apply lossless triple deduplication and the authorized same-pair precedence rules."""
    triples = defaultdict(list)
    pairs = defaultdict(set)
    for e in edges:
        a, b = reps[e["source"]], reps[e["target"]]
        require(a != b or e["source"] == e["target"], "INDUCED_SELF_LOOP:" + e["id"])
        require(
            signatures.valid(e["inventoryId"], e["relation"], nodes[a]["class"], nodes[b]["class"]),
            "EDGE_SIGNATURE:" + e["id"],
        )
        triples[a, e["relation"], b].append(e)
        pairs[a, b].add(e["relation"])
    strong = set(generic["stronger_role_relations"] + generic["specialized_subproperties"])
    weaker = _precedence_map(profile)
    kept = []
    dispositions = []
    counts = Counter()
    for (a, p, b), originals in sorted(triples.items()):
        # Resolve blockers to actual retained triples after weak-role suppression.
        blocked = set()
        if nodes[a]["class"] == "Paper" and weaker.get(p) in pairs[a, b]:
            blocked.add((a, weaker[p], b))
        if p == "mentions":
            if nodes[a]["class"] in ("Repository", "DatasetResource", "DocumentationPage"):
                for x, y in ((a, b), (b, a)):
                    blocked.update((x, q, y) for q in pairs.get((x, y), ()) if q != "mentions")
            else:
                blocked.update((a, q, b) for q in pairs[a, b] & strong)
        blocked = {
            k
            for k in blocked
            if not (nodes[k[0]]["class"] == "Paper" and weaker.get(k[1]) in pairs[k[0], k[2]])
        }
        originals.sort(key=lambda e: (e["source"] != a or e["target"] != b, e["id"]))
        chosen = originals[0]["id"]
        if not blocked:
            kept.append(dict(originals[0], source=a, target=b))
        for e in originals:
            state = (
                "precedence_suppressed"
                if blocked
                else "retained"
                if e["id"] == chosen
                else "duplicate_triple"
            )
            redirected = (e["source"], e["target"]) != (a, b)
            dispositions.append(
                dict(
                    original=e["id"],
                    projected=[a, p, b],
                    redirected=redirected,
                    disposition=state,
                    retainedEdge=None if blocked else chosen,
                    suppressedBy=sorted(blocked),
                )
            )
            counts[state] += 1
            counts["redirected"] += redirected
    final = {(e["source"], e["relation"], e["target"]) for e in kept}
    require(
        len(dispositions) == len(edges)
        and len(final) == len(kept)
        and all(tuple(b) in final for d in dispositions for b in d["suppressedBy"]),
        "ASSERTION_ACCOUNTING",
    )
    return kept, dispositions, counts
