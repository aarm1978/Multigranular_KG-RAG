# Step 11 format-conformance amendment v1.0.0

**Researcher-approved methodological correction — 2026-10-10.**
Applies explicitly as `study2-format-conformance/1.0.0` alongside the preserved
[Step 11 v0.3](study2_step11_source_specific_semantic_contracts_v0.3.md) and its
[acceptance history](handoffs/STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md).
Ontology v0.1.6, source eligibility, identity, target scope, semantic gates and
context selection are unchanged. This corrects representation/binding rules;
it does not waive semantic evidence or retrospectively change experimental results.

## Exact conformance rules

- `inventoryId` determines the source-authorized ontology declaration. Accept its
  exact canonical name or exact specification IRI (including the declared CURIE
  and its exact expansion using frozen prefixes). Relation IRIs follow the
  existing ontology builder's CIROH namespace/name minting rule. Record IRI-to-name
  conversion only in a derived representation. Reject other ID/name/IRI mismatches;
  never strip arbitrary namespaces, fuzzy-match, reinterpret reuse anchors, change
  endpoint identities or activate unsupported targets.
- Count exact Unicode occurrences, including overlaps, in the verified selected
  source unit. A unique quotation binds even if its redundant textual
  `locatorAnchor` is invalid; record `invalid_redundant_anchor_ignored_unique_literal`.
  Multiple occurrences still require an exact anchor occurring once and containing
  the quotation exactly once. Absent/nonliteral evidence fails. Malformed fields
  remain parser failures. Original quotations, anchors and every model-authored
  field remain in the authentic response; only the derived binding representation
  omits a demonstrated redundant invalid anchor.
- Source provenance, integrity, coordinates, visibility, independent node/edge
  evidence and dependency checks remain mandatory. Binding or conformance does not
  establish scientific truth. Semantic acceptance stays NOT EVALUATED and KG
  authorization stays FALSE.

## Versioned implementation and provenance

`src/extraction/llm/format_conformance.py` provides an explicit opt-in
`replay_conformant()` adapter. It reconstructs the trusted request, verifies its
independently supplied hash, parses the original response, records permitted
conversions, then invokes the existing family replay/validators on separately
hashed derived bytes. It retains exact original bytes (hex), original response
hash, derived bytes/hash, conversion pointers and the derived replay/hash.
An unchanged response retains byte-identical historical replay behavior.
No existing pipeline, parser, binder, prompt, ontology or default routing changes.
The derived replay's response hash identifies derived bytes, never provider output.

`study2-canonical-declaration-schema/1.0.0` restricts every inventory branch's
`class`/`relation` to its exact canonical name. `build_conformant_preflight()` reuses
existing envelope construction and strict-schema checks, assigning new schema and
wire hashes. Historical schema generation, envelopes and response versions stay
unchanged. This is offline structural verification, not remote API acceptance.
Future production must explicitly select this schema/conformance version; production
execution and Step 13 acceptance remain separately authorized work.

## Separate corrective analysis

Ignored directory: `var/study2_step12c/analysis/format-conformance-v1/`.
Each case retains an exact copy of the historical replay, the derived conformance
report, candidate-by-candidate before/after dispositions and unauthorized prospective
envelopes. The local script reconstructs the two original Wave C selections through
the accepted amendment-aware builders and verifies unchanged semantic request hashes.
Authentic outputs and historical reports are not overwritten.

| Case | Historical disposition | Corrective disposition |
|---|---|---|
| HS-09 | 4 source/evidence-binding failures | 2 nodes + 2 edges mechanically validated |
| HUB-08 | 4 rejected nodes + 4 unresolved edges | 3 nodes + 3 edges mechanically validated; Method node and describesMethod edge retain semantic conditions |

The Hub Method requires `supported_method` and `substantive_method_description`.
All other mechanically validated assertions still require semantic judgment. These
are corrective diagnostics, not replacements for the original Wave C outcomes,
new gold labels, prompt optimization or Step 12C closure.

## Optional two-request verification plan — NOT AUTHORIZED

New run IDs: **HS-09-FC01** and **HUB-08-FC01**. Maximum one attempt each, no retries
or substitutions. Preserve the respective original owners, ordered units, source
snapshots, endpoints and prompt versions (HydroShare 1.2.0; Hub 1.2.0). Reuse OpenAI
Responses, gpt-5.6-sol, medium reasoning, store=false, no tools, 32768 output tokens.
Only the strict response schema changes; no response/evidence repair at generation.

| Run | Semantic request SHA-256 | New schema SHA-256 | New envelope SHA-256 |
|---|---|---|---|
| HS-09-FC01 | `4f025c60a32ae06cd07a6da5b25eedc53dd8f63e18036a14ad1f54a467992502` | `16d1bba468640d6dadc0aeddbfc62f1e42f210636d4cf304a8032736121ba8a5` | `8470b8f9725ab6f57c7dbd44996deeee11bb2265d9c1e3aeffea4aff7cbbe324` |
| HUB-08-FC01 | `d3f34201c16ed23053b951579b620fdb192102ab1afccb80a6d937c2ac786b03` | `7dd4953a93b3b31e84e67c7f8a51f34b8de22cc94751ff4b047e9279dbaf9b68` | `e0b9e92b1c5a8ca50cde1b1794f9526d90976036b5ba66a37b46e1d51fa3651b` |

Before live authorization, add an explicit execution amendment/routing for these
new IDs using the existing terminal transport and approval checks; do not change
or bypass the frozen 30-ID manifest or reserve historical IDs again. Pin source,
implementation, schema, input and envelope hashes and allocate new immutable attempt
paths. Researcher approval must set per-case/aggregate monetary reservations,
context bounds and validity window. No authorized manifest is created here.
The plan and envelopes are ready for review; terminal dispatch is not yet ready.

Run each approved case sequentially with existing locks, credential-before-reservation,
STOP behavior, one-attempt policy and durable raw recording. Stop on any mismatch,
exception, ambiguous timeout or noncompleted response. Replay outputs separately with
explicit conformance version; review format success separately from semantic support.
Do not revise prompts based on these cases or use them to replace Wave C findings.
