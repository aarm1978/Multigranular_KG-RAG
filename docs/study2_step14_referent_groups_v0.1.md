# Step 14 direct-key referent grouping preparation v0.1

Authority: implementation preparation `step14-referent-groups/0.1.0` under the
[approved scope](study2_step14_scope_and_completion_decision_v0.1.md) and
[identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md).
No new identity cases or scientific equivalences are approved.

Reuse the existing four-family semantic occurrence inventory and its exact
identifier/lexical blocks. Each proposal has **one original direct key** and its
explicit original membership. Blocks are never unioned through shared members,
retrieval links, approvals or connected components. Original deterministic own-key
lanes are distinguished from local identifier declarations and semantic comparison
lanes. Locator identity, entity identity and conceptual similarity remain distinct.
Geographic declarations retain their unresolved namespace authority. Publication
`link_existing` declarations remain request-local, never global identity keys.

Named groups reuse complete original lexical keys, not token clusters or embedding
scores. The existing review utility stopwords omit clearly generic names; surviving
names are only potentially distinctive and remain unresolved. This screen does not
establish scientific specificity. Original labels, class, inventory, versions and
granularity remain available; differences and unknowns cannot bridge identity.
Administrative version metadata is not interpreted as an entity release.

Preserve original source/evidence/native-record pointers and hashes in a linear-size
member sidecar. Preserve prior approval records unchanged and report exact subset
intersections without extending approval to an entire group. Historical reviewed
cases and queued memberships remain metadata, not new decisions. The inventory's
excluded classes and ungrouped occurrences are reported, not silently treated as
resolved. This is not grouping every node in the structural snapshot.

Scan existing reconciled retrieval pairs once. Attach only pairs whose endpoints
already share the same direct key; never expand large groups quadratically. Pairs
outside these groups remain in their immutable input, explicitly counted as
unrepresented, not rejected. At most three original pair references and two-view
score records per selected review group keep the shareable package bounded.

One review set of at most twelve groups is selected by round-robin family-set and
basis strata, restricted to at most sixteen members per group. Within strata,
prioritize cross-family coverage, existing direct retrieval support, smaller groups,
and stable proposal IDs. Selection measures review utility, not identity probability
or population accuracy. Larger groups remain unresolved; no repeated batches or
exhaustive review are required. The existing ontology decision gate still applies
before any separately authorized canonicalization.

Run once from the repository root in the existing research environment:

```bash
python -m src.evaluation.step14_referent_groups --output var/study2_step14/referent-groups/v1
```

Fresh output required. Input hashes are verified before and after preparation;
network connections are blocked. No extraction, retrieval, embedding generation,
canonical allocation, ontology change or graph write occurs.

Outputs: `summary.json`, `summary.md`, bounded `review.json`; complete compact
`groups.jsonl`, `members.jsonl`, unchanged `prior-decisions.jsonl`, and hash manifest.
Share the two summaries and `review.json`; larger sidecars remain locally inspectable.
Original documents and full provider bodies are not copied. Proposal IDs are existing
block bookkeeping IDs, not canonical entity identifiers.

Focused check: `python -m unittest discover -s tests -p test_step14_referent_groups.py`.
Full processing and counts are reserved for the researcher's terminal.
