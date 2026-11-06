# Step 14: prospective embedding-discovery preflight

**Offline measurement and planning only.** This prepares no embeddings, provider
requests, similarity judgments, accepted identities, canonical IDs, scientific
relations, graph materialization, or revised metrics. Step 14A remains skipped.
All eligibility and retrieval settings below are proposals requiring researcher
approval before embedding execution; existing identity policy is unchanged.

Authorities: [semantic candidates](study2_step14_semantic_candidates.md),
[semantic review](study2_step14_semantic_review.md),
[identity pilot](study2_step14_semantic_identity_pilot.md),
[next review queue](study2_step14_next_review_queue.md), and
[granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md).
Original proposals/recommendations and the 29 approved batch-01 subsets retain
their distinct authorities. Ontology v0.1.7 and Step 13/order-50 remain frozen.

## Known inventory versus measurements still to run

The existing candidate manifest records **37,225 prepared occurrences**. Its
class counts sum to **13,551** in the existing semantic-comparison lane:

| Class | Saved prepared occurrences |
|---|---:|
| Tool | 7,216 |
| Algorithm | 1,257 |
| Workflow | 123 |
| AgentBasedModel | 16 |
| ConceptualModel | 132 |
| MLModel | 2,163 |
| ProcessBasedModel | 2,401 |
| StatisticalModel | 243 |

These are saved inventory counts, **not measured embedding-eligible totals**.
The other 23,674 prepared occurrences remain in the identifier/geographic lane.
Dependency, DatasetMention, discourse, metrics, parameters, and other excluded
classes are not silently reintroduced. The manifest also records 52 missing-
provenance flags, seven retained abstract-class flags, and 111 multiple-label flags
across all prepared occurrences; these flag populations can overlap.

Only schemas, manifests, and a bounded saved record were inspected for this task.
The full occurrence scan, text statistics, and workload estimates are deliberately
left to the researcher-terminal preflight. No corpus-level duplicate rate, token
total, source-family distribution, or actual eligible count is claimed here.

## Offline inventory and proposed eligibility

Stream the existing `semantic-candidates/v1/occurrences.jsonl` once for measurement.
Verify its manifest-pinned bytes, the candidate blocks, review/pilot/live authority
manifests, approved-batch bindings, and pinned `next-review-queue/v1` reservation.
Check current ontology and frozen key-reconstruction implementation hashes. Reuse
the existing text and key functions; do not reopen the graph or extraction.

For every original occurrence, preserve its ID, class/inventory ID, source families
and artifacts, exact row/text hash and line/JSON pointers, evidence/provenance
pointers, original version values, granularity, and preparation flags. Existing
curation status is recorded as metadata, not identity evidence or an inferred
owner/reference role. Missing provenance is not recovered from ID prefixes.
Existing provenance flags describe the saved preparation, not a fresh audit of
all available authorities; they may conservatively hold records that another
diagnostic could recover through an exact documented path. This preflight does
not silently repair those fields or equate a hold with genuinely absent evidence.

The stored `embeddingText` is exactly class + labels + descriptions + distinct
evidence quotations. The preflight checks this projection rather than constructing
new descriptions. It measures characters, UTF-8 bytes, approximate tokens, and
class-only, label-only, or contextual content; class/family-set joint strata have
explicit occurrence denominators. A multi-family record is counted once in its
family-set stratum, not assigned to a guessed family.

**Proposed first index:** existing semantic-comparison classes only, compatible
nonabstract class/inventory, no existing blocking exclusion, one explicit source
family, source artifacts and evidence, nonempty evidence text, and contextual text
beyond the label. Hold texts above the proposed 2,048 estimated-token planning
limit; never truncate them to pass. All held records remain in the inventory with
reasons. Missing versions alone are not an exclusion. Multiple labels remain
visible and are proposed for consideration here even though lexical blocking
excluded them; that coverage extension requires researcher approval.

Identifier-lane text is measured but held out of the proposed first embedding
index. Broader embedding coverage of papers/datasets/repositories/persons/
organizations/geography would require a separate scope decision, not merely the
presence of text. Within the proposed index, report available other-family pools
per exact class. A class without another eligible source family cannot provide
cross-family queries. Shared-artifact and referent checks still apply later.

**Duplication and workload:** count exact saved payload hashes, duplicated payload
groups, redundant occurrence payloads, exact repeated quotations, and quotations
seen across distinct recorded artifact IDs. Do not infer independence, mirrors,
or identity from those counts. A possible text cache stores one vector per exact
payload/model/configuration while retaining every original occurrence posting.
The duplicate-group artifact contains original IDs, not canonical entities.

Approximate tokens are `ceil(Unicode characters / 4)` per unchanged payload,
summed separately for all records and unique proposed-eligible payloads. This is
neither a tokenizer count nor a guaranteed bound. The report includes eligible
unique UTF-8 bytes. Vector-only float32 storage would be `4 × dimensions × unique
payloads`; ANN index, postings, metadata, and working-memory costs are additional.
API request count depends on the chosen model's input limits and approved batching;
monetary cost depends on tokenization/pricing. These remain unknown, not zero.
No API price lookup, tokenizer download, or model import is needed for preflight.

## Proposed bounded retrieval experiment — not implemented or authorized

1. Compare **exact ontology classes** across different explicit source families
   and disjoint recorded source-artifact sets. No superclass-based cross-class
   match, CFE retyping, or new ontology relation is assumed. Artifact IDs are not
   independently reconciled; undiscovered mirrors remain a limitation.
2. Select at most **500 original queries**, round-robin by class/family, with stable
   SHA-256(original occurrence ID) order inside strata. Exclude previously reviewed
   and reserved-queue occurrences as new queries; retain their postings as possible
   reference targets. This is purposive candidate discovery, not recall evaluation.
3. Retain at most **top 5** distinct target occurrences per query across all allowed
   families combined, and at most **1,000 unique unordered occurrence pairs** for
   the experiment. At most **20** proposed pairs may involve one target occurrence.
   Candidate caps are workload limits, not semantic similarity thresholds. Record
   retrieval rank/score/model, rejected-by-budget counts, and deterministic tie
   breaks. Stop at caps; no unbounded backfill after exclusions.
4. Keep identical-text postings separate. Allow at most **3 target postings from
   distinct recorded artifacts per text bucket per query**, subject to top-k and
   global caps. Do not expand one shared vector into all occurrence pairs. Index
   search method, bounded oversampling, score normalization, and ties require
   approval; no ANN library or distance computation is installed/executed here.
5. Oversized-block membership is reconstructed linearly during the existing
   occurrence scan and checked against original counts/hashes. Per-occurrence
   membership tags are retained; no block pair set is generated. Propose at most
   **10 queries per oversized block**, within the 500-query budget, and **20 pairs
   involving its members**, within all other caps. Overlapping memberships consume
   every applicable quota. No quota implies a representative sample or identity.

Top-k relevance cannot resolve scientific referent granularity. Architecture and
trained instance, named technique and implementation, family and release, base
resource and derived product stay distinguishable. Preserve version and scope
statements and accepted predicates in eventual review context. Unknown versions
are neither equal nor different; explicit differences are review evidence, not
automatically adjudicated contradictions. A source repository ID or capture commit
is not an entity-own identifier/version. A quoted citation/reference is not owner
identity. Before any embedding run, approve the model-visible text projection and
context policy: the unchanged saved concatenation can contain reference-target
language and source context, and is not certified as an entity-only description.

## Reconcile discoveries without pairwise expansion

The preflight emits inverted membership references, not discovered pairs. For a
future bounded pair, use intersections of its two original occurrence records:

- **Existing identifier/lexical blocks:** attach all original shared block IDs,
  exact keys, scope and evidence references; mark the opportunity as previously
  proposed rather than new. A local locator remains local. Do not materialize all
  pairs within those blocks to perform this test.
- **Shared external references:** retain original `v2-row-sha256:` group identities
  and pinned `shared-reference-hubs.jsonl` recovery source. Existing tier, target
  scope, versions, and accepted predicates remain available there. A common tier-B
  locator or tier-C name never becomes tier-A identity through embedding proximity.
- **43 reviewed cases / 232 occurrences:** preserve case memberships. A shared case
  means prior joint context, not that every induced pair received an assessment.
  Inspect exact original subset recommendations before calling a pair reviewed.
  One reviewed endpoint alone does not make a new relationship reviewed.
- **29 approved subsets / 99 occurrences:** only a common explicit decision ID
  denotes coverage by that approved subset. No transitive closure, approval
  propagation, or canonical allocation follows. Other reviewed occurrences remain
  unapproved; model output remains recommendation-only.
- **Reserved 30-block / 74-occurrence queue:** keep reservation pointers. A pair
  involving a reserved endpoint goes to a deferred queue-overlap lane rather than
  silently consuming a second review slot. Cross-block new endpoints do not change
  the reserved blocks or their complete memberships.

Attach all applicable memberships, not just the first. Deduplicate a future pair
by sorted exact occurrence IDs while retaining all discovery mechanisms and
scores; do not union candidate groups or collapse entities. Existing candidates
can receive an additional discovery annotation later, not an inferred new identity
decision. Actual reconciliation of retrieved pairs is deferred with retrieval.

## Researcher decisions required before execution

- Embedding model, exact revision, local versus hosted execution, tokenizer,
  dimensions, license/data handling, and reproducible cache configuration.
- Entity text projection, approved context lengths and handling of overlong or
  ambiguous text; whether to include multi-label, multi-family, and identifier-lane
  records. The current preflight does not erase evidence to meet a planning cap.
- Query sampling, index/search method, similarity measure, top-k, bounded
  oversampling, duplicate-posting limits, class/source restrictions, oversized
  quotas, target degree limits, and total candidate-review budget.
- Monetary/API-token/request ceilings or local CPU/GPU/runtime/memory limits,
  batching, retries and stop conditions. Tokenizer-based measurement must precede
  a priced execution authorization. No existing key or provider access is probed.
- Evaluation of incremental **new candidate coverage** versus the existing
  identifier/reference/lexical queues; separate later identity yield from retrieval
  coverage. This purposive pilot cannot establish population precision/recall.

These are methodological gates, not a reason to amend the ontology whenever an
occurrence is unresolved. Representation questions from the identity policy remain
separate. Preflight completion alone does not authorize the embedding experiment.

## Researcher-terminal execution and outputs

Run from the repository root in the existing `multigranular-kg` environment:

```bash
python -m src.evaluation.step14_embedding_preflight
```

Fresh ignored outputs under `var/study2_step14/embedding-preflight/v1/`:
`occurrence-preflight.jsonl`, `duplicate-text-groups.jsonl`,
`oversized-preflight.jsonl`, `summary.json`,
`report.md`, and `manifest.json`. Occurrence records contain compact references and
measurements, not duplicated full quotations or vectors. The manifest records
input/output/implementation hashes, proposed limits, and zero provider/embedding/
graph/decision counts. Existing directories are refused; `--output` may select a
fresh sibling under the same root. Input bytes are checked again before writing.
The command blocks socket connections and does not load credentials.

Focused synthetic tests (no real corpus execution):

```bash
python -m unittest tests.test_step14_embedding_preflight tests.test_step14_semantic_candidates tests.test_step14_next_review_queue -q
```

Tests cover missing text/provenance, exact duplication without identity collapse,
class/family pools, reviewed/reserved/approved membership separation, oversized
hash reconstruction without pairs, text-budget holds without truncation,
determinism/nonmutation, version preservation, and fail-closed input drift.
