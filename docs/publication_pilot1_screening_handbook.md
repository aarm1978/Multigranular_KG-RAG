# Publication Pilot 1 Source-Unit Screening Handbook

**Version:** 0.1.1
**Status:** Frozen for Publication Pilot 1 production screening
**Freeze date:** 2026-08-11
**Scope:** Publication Pilot 1, Block A human screening and routing only
**Applies to:** the 267 structurally eligible and request-eligible publication source units
**Does not apply to:** annotation, evidence-span selection, gold construction, adjudication, model evaluation, or Block B sample partitioning

---

## 1. Purpose

The source-unit review is a **pre-annotation screening and routing task**. Its purpose is to characterize every open Publication Pilot 1 source unit prospectively so that Block A can:

1. determine which **Publication Pilot 1 operational semantic targets** should be available to a later annotator for that unit;
2. characterize the unit's expected semantic density, relation density, routing difficulty, context needs, and recurring boundary distinctions;
3. derive reporting-family and sampling-stratum coverage;
4. select a deliberately varied calibration set and construct a prospective per-artifact candidate order **without using model predictions, gold labels, annotation counts, or timing outcomes**.

### 1.1 What screening means

For this handbook:

> **Routing a target means that the target is a legitimate annotation possibility for the source unit if supported by the source. It does not assert that an instance or edge is present.**

The reviewer is therefore deciding **what a later annotation task should be allowed/expected to look for**, not creating the annotation itself.

### 1.2 What screening is not

During screening, do **not**:

- create node instances;
- create relation instances;
- highlight or record evidence spans;
- assign offsets;
- count exact positive instances;
- construct gold labels;
- adjudicate ambiguity;
- use model predictions or confidence;
- use web search or external knowledge to resolve the unit;
- globally identify or merge entities;
- infer a relation only because two compatible node types are mentioned.

The frozen evidence rule remains:

> **No supported evidence span means no accepted semantic assertion.**

That rule is enforced later during annotation/extraction. Screening must not simulate that later evidence-labeling step.

---

## 2. Authority and source of the interface targets

The ontology defines the available semantic vocabulary, but **the ontology alone does not define the Publication Pilot 1 screening menu**.

Use the following authority chain:

1. `src/ontology/ontology_spec.yaml` and generated `ciroh_ontology.owl` — formal ontology authority.
2. Frozen Publication Phase B outputs — deterministic backbone authority.
3. `docs/publication_llm_extraction_target_inventory.md` — binding Publication Pilot 1 operational decisions.
4. `src/extraction/llm/publications/publication_target_inventory.yaml` — binding machine-readable Publication Pilot 1 target profile.
5. `data/curation/papers/pilot1/publication_pilot1_target_display_catalog.yaml` — accepted human-facing presentation catalog used by the screening interface.

### 2.1 Why the ontology is not enough

A class or relation may exist in the ontology but still be:

- already produced deterministically;
- context-only;
- required infrastructure rather than an LLM prediction;
- out of scope for Publication Pilot 1;
- reserved for another source family;
- deferred to a separate protocol;
- an abstract superclass that must not be directly instantiated.

Examples of ontology-supported items that are **not ordinary screening targets** include `Person/Author`, `Paper`, `Venue`, `Subject`, `Organization`, `Award`, `Measurement`, `SoftwareEntity`, `ComputationalModel`, `Place`, and `HydrologicFeature`.

### 2.2 What the interface shows

The accepted display catalog contains the human-facing:

- display label;
- short definition;
- boundary hint;
- pilot treatment;
- decision role;
- display group;
- ontology/backend class;
- relation domain and range where applicable.

The interface shows only `humanVisible: true` targets. These consist of:

- `extract_and_evaluate` targets;
- `extract_and_monitor` targets;
- a small number of `deferred_resolution` targets.

Only `extract_and_evaluate` and `extract_and_monitor` targets count as **primary semantic routing** for candidate eligibility. A unit routed only to deferred-resolution targets does not enter the primary calibration/candidate pool.

**Rule:** Never invent a target that is not present in the interface/catalog, even if a similarly named ontology relation seems logically possible.

---

## 3. Where the 267 units are

The canonical Block A worklist is:

```text
data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv
```

It contains **358 rows total**. The current accepted population is partitioned as:

| Structural state | Count | Human screening? |
|---|---:|---|
| `eligible` + `requestEligible=true` | 267 | **Yes** |
| `context_only` | 49 | No |
| `excluded` | 39 | No |
| `needs_review` | 3 | No; structurally blocked |
| **Total** | **358** | |

The 267 open rows are therefore exactly the rows satisfying:

```text
sourceEligibility == "eligible"
AND
requestEligible == "true"
```

The screening application presents these 267 rows as the open review population. The other 91 rows remain in the same worklist for provenance but are prefilled as non-open.

### 3.1 Where the actual text comes from

The 267 units are **not 267 independent Markdown files**. Each worklist row contains:

- `sourceTextPath`
- `startOffsetInDocument`
- `endOffsetInDocument`
- `sourceUnitTextHash`
- `sourceUnitID`

The application reads the canonical source document, slices the exact unit using the frozen zero-based half-open Unicode code-point offsets, and verifies the text/hash before displaying it.

### 3.2 Optional command-line check

From the repository root:

```bash
python - <<'PY'
import csv

path = "data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv"
with open(path, encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

open_rows = [
    r for r in rows
    if r["sourceEligibility"] == "eligible"
    and r["requestEligible"] == "true"
]

print("Total rows:", len(rows))
print("Open review rows:", len(open_rows))
print("First open IDs:")
for r in open_rows[:10]:
    print(r["sourceUnitID"])
PY
```

Expected open count: `267`.

---

## 4. Core screening principle

Use this question throughout the review:

> **If this source unit were later sent to an annotator, which authorized Publication Pilot 1 target types should the annotator be prepared to look for in this unit?**

This is deliberately broader than:

> “Which entities and relations have I already proven are present?”

The second question is annotation and must wait.

### 4.1 Conservative but not artificially narrow

Route a target when the unit provides a reasonable semantic locus for that target under the catalog definition and boundary.

Do not route a target merely because:

- its words appear lexically;
- its domain/range classes could theoretically coexist;
- the target is common in papers;
- it occurs elsewhere in the same paper;
- external knowledge suggests it should be present.

Do not remove a legitimate target merely to keep the menu small. The 5–12 option objective is a UI presentation goal, **not a semantic cap**.

---

## 5. Current-artifact ownership rule

This rule is especially important in Introductions and Related Work.

For **Paper-branch relations** such as:

- `usesModel — Paper branch`
- `usesTool`
- `usesDataset — new prose evidence`
- `studiesFeature — Paper branch`
- `studiesPlace — Paper branch`

the subject is the **current paper**, not a cited study described inside the current paper.

### 5.1 Cited-study use is not current-paper use

A sentence such as:

```text
Smith et al. used Model X to simulate flooding.
```

may justify `RelatedResearch`, `mentionsModel`, or other authorized prior-work semantics. It does **not** justify:

```text
CurrentPaper → usesModel → Model X
```

unless the displayed source unit separately indicates that the current study itself uses Model X. The same ownership rule applies to `usesTool`, `usesDataset`, `studiesFeature`, and `studiesPlace`.

### 5.2 `use > mention` operates per endpoint pair, not per source unit

The same source unit may legitimately route both `usesModel` and `mentionsModel` because different model endpoints may have different roles. Later annotation applies the frozen `use supersedes mention` precedence to the **same source–target pair**, not globally to the whole source unit. The same pair-level rule applies to tool and dataset use/mention relations.

---

## 6. Standard review workflow

### Step 1 — Read only the displayed unit and read-only metadata

Use:

- exact source-unit text;
- section title;
- section role;
- content type;
- visible deterministic/deferred metadata if the interface exposes it.

Do not open the web or search the complete paper to resolve a screening ambiguity. If surrounding section context would materially help, record `Section context useful = yes`.

### Step 2 — Decide whether the unit contains substantive Pilot 1 semantic material

If the unit is only editorial/administrative metadata, page furniture, copyright, author affiliations, article history, or another non-semantic fragment, zero routed targets is valid.

If substantive material is present, continue.

### Step 3 — Route node targets

Select the node classes that a later annotator should legitimately consider for this unit.

Think by families first:

- research framing;
- discourse structure;
- methods and experiments;
- models, algorithms, and tools;
- findings, conclusions, limitations, and future work;
- metrics, parameters, and variables;
- datasets and repositories;
- concepts and geography.

### Step 4 — Route relation targets independently

A relation is not routed automatically because compatible node targets were routed.

Route it only when the source unit provides a plausible **semantic role** for that relation under its catalog definition. Examples:

- a model may be mentioned without being used;
- a dataset may be described without being used;
- a place may appear as an affiliation rather than a study location;
- a Finding and Conclusion may both be plausible without an explicit `supports` relation;
- a Method and Parameter may coexist without evidence that the parameter belongs to that method.

### Step 5 — Apply current-artifact ownership where relevant

For Introduction/Related Work text, distinguish what the **current paper does** from what a **cited paper did**. Do not convert cited-study use into current-paper use.

### Step 6 — Mark recurring distinctions

Mark only the exact controlled distinctions that are likely to matter in later annotation of this unit:

- `Model/Method/Algorithm/Tool`
- `Finding/Conclusion`
- `ResearchProblem/ResearchGoal`
- `use/mention/reference`
- `EvaluationMetric/Parameter`

These fields identify **boundary pressure**, not gold labels.

### Step 7 — Assign expected densities

Use the anchors in Section 9.

### Step 8 — Assign routing complexity

Use the anchors in Section 9.

### Step 9 — Answer the three context/endpoint flags

Use the rules in Section 10.

### Step 10 — Consider likely exhaustive-empty targets

Use only the restricted rule in Section 11.

### Step 11 — Write a concise screening rationale

Use one of the templates in Section 13 and adapt only the bracketed content.

Optional notes should record genuine uncertainty, special conversion/context issues, or a reason to revisit the unit. Do not write an annotation narrative.

---

## 7. Node-routing quick reference

The interface/catalog is the authority. This table is a fast screening aid, not a replacement for the catalog definitions.

### 7.1 Research framing

| Target | Route when the unit is a plausible locus for... | Key boundary |
|---|---|---|
| Background | context directly motivating the current study | not generic introduction, gap, or goal |
| Theme | text-supported central thematic focus | avoid unsupported summary and keyword duplication |
| ResearchProblem | explicit gap, deficiency, uncertainty, unresolved challenge | not objective or general importance |
| ResearchQuestion | explicit question/interrogative formulation | do not rewrite objectives as questions |
| ResearchGoal | explicit aim/objective/current scientific action | not cited-study goals or future recommendations |
| ResearchSignificance | explicit statement of why the work/result matters | distinct from Background and Contribution |
| Hypothesis | explicit testable proposition | never infer from design or objective |
| Claim | argumentatively important author assertion | not every declarative sentence |

### 7.2 Discourse structure

| Target | Route when... | Key boundary |
|---|---|---|
| Definition | a term/measure/method/concept may be explicitly defined | explanation alone is not a definition |
| TheoreticalBasis | theory/framework/principle may ground the current work | mere mention is insufficient |
| Examples | an illustrative case/scenario/application may occur | evaluated test is Experiment |
| Discussion | results may be interpreted or explained | Finding says what happened; Discussion interprets |
| RelatedResearch | prior work may be substantively described/compared/synthesized | bare citations do not qualify |

### 7.3 Methods and experiments

| Target | Route when... | Key boundary |
|---|---|---|
| Method | an applied technique/procedure/approach may be described | named reusable entity may instead be Algorithm/Tool/model |
| Experiment | a delimited empirical/computational test may be described | not a single method or data description |
| DataDescription | origin, period, coverage, sample, resolution, variables, partition, or composition of data may be described | dataset identity is separate |

### 7.4 Models, algorithms, and tools

| Target | Route when... | Key boundary |
|---|---|---|
| Tool — new from publication prose | software application/platform/package/system may be discussed | scientific process representation may instead be a model |
| ProcessBasedModel | named physical/hydrologic/hydraulic/environmental computational model | separate applied Method/tool |
| ConceptualModel | named simplified conceptual computational model | distinguish from ProcessBasedModel |
| StatisticalModel | named statistical model with stable reusable identity | generic regression/estimation is normally Method |
| MLModel | data-driven model/trained architecture | training procedure is Method |
| Algorithm | named reusable computational procedure | generic applied technique may be Method |

### 7.5 Findings, conclusions, limitations, future work

| Target | Route when... | Key boundary |
|---|---|---|
| Finding | current-study empirical/computational/analytical/qualitative result may be reported | not goal, expectation, recommendation, or cited result |
| Limitation | current study/method/data/experiment/finding may be explicitly constrained or qualified | not ResearchProblem |
| Conclusion | study-level synthesis/general conclusion may occur | repeated result remains Finding |
| Contribution | authors may claim what the study added | distinct from Goal and Significance |
| FutureWork | explicit later research activity may be proposed | not current goal or generic aspiration |

### 7.6 Metrics, parameters, variables

| Target | Route when... | Key boundary |
|---|---|---|
| EvaluationMetric | performance/evaluation measure may be reported | contextual occurrence; do not merge by name |
| Parameter | value/coefficient/threshold/configuration controlling model/method/algorithm/experiment | distinguish from measured Variable and Metric |
| Variable | measurable/observed/predicted/derived/analyzed quantity | not broad Concept, Metric, Parameter, or Unit |

### 7.7 Datasets and repositories

| Target | Route when... | Key boundary |
|---|---|---|
| DatasetMention — new from prose | dataset is named/described without sufficient exact resolved identity | preserve source-scoped identity |
| DatasetResource — exact identifier omitted by Phase B | exact dataset identifier appears to require resolver-mediated handling | deferred-resolution only |
| Repository — exact URL omitted by Phase B | exact repository URL appears to require resolver-mediated handling | deferred-resolution only |
| Repository — named without exact identity | repository is clearly referred to but canonical identity is absent | never global-merge by name |

### 7.8 Concepts and geography

| Target | Route when... | Key boundary |
|---|---|---|
| Concept | specific substantive scientific/technical notion is discussed and no more precise class applies | avoid terminology flooding |
| Watershed | basin/catchment/watershed/subbasin/drainage unit | river itself is RiverReach |
| RiverReach | river/stream/channel/flowpath/reach | watershed is separate |
| Gauge | hydrologic monitoring/measurement station | do not invent station identity |
| WaterBody | lake/reservoir/bay/estuary/other water body | surrounding region may be NamedPlace |
| Aquifer | named/source-scoped aquifer/hydrogeologic system | likely sparse |
| VPU | explicit NHDPlus Vector Processing Unit | do not infer from generic “region/unit” |
| NamedPlace | study-relevant named geographic area not better typed as hydrologic feature | exclude affiliations/publisher locations/incidental toponyms |

---

## 8. Relation-routing quick reference

Again, the catalog definition and displayed domain/range are authoritative.

| Relation target | Route when the unit is a plausible locus for... | Main caution |
|---|---|---|
| resolves | Method/Contribution/ResearchQuestion explicitly addressing a ResearchProblem | do not infer from co-occurrence |
| produces | Method/Experiment explicitly producing a Finding | prefer Experiment→Finding for combined test configuration |
| testedBy — Hypothesis branch | explicit Hypothesis tested by Method/Experiment | do not infer hypothesis |
| supports | explicit positive support/demonstration/confirmation | no negative-support; no Finding→Hypothesis branch |
| relatesTo — local semantic target | RelatedResearch substantively linked to accepted local Method/TheoreticalBasis/Concept/ResearchProblem | avoid generic thematic co-occurrence |
| hasLimitation — Finding branch | explicit Limitation qualifies a particular Finding | do not attach every limitation to every finding |
| usesModel — Paper branch | **current paper** trains/runs/calibrates/compares/evaluates/otherwise uses a model | cited-study use is not current-paper use; use supersedes mention only for same pair |
| usesModel — Method branch | a Method uses a model as component/resource | distinguish from `appliesTo` |
| appliesTo | Method is applied to/configures/analyzes/explains/calibrates/evaluates a model | do not duplicate `usesModel` unless roles differ |
| usesTool | **current study** actually employs a Tool | cited-study use is not current-study use; use supersedes mention only for same pair |
| mentionsVariable | current-study relevant Variable is observed/predicted/modeled/derived/analyzed | incidental variables excluded |
| studiesFeature — Paper branch | hydrologic feature is a study object/domain/unit of analysis for the **current paper** | not cited-study geography, affiliation, or incidental place |
| studiesFeature — Method branch | a particular Method is explicitly applied to a hydrologic feature | not automatically inherited from Paper |
| studiesPlace — Paper branch | NamedPlace is study area/model domain/data/result location for the **current paper** | not cited-study location, affiliation, or publisher place |
| studiesPlace — Method branch | a particular Method is explicitly applied in NamedPlace | not automatically inherited from Paper |
| usesDataset — new prose evidence | dataset is actually used by the **current study** for training/testing/forcing/analysis/observation/benchmarking | cited-study use is not current-study use; use supersedes mention only for same pair |
| mentionsModel | current paper discusses model without proof that current study uses it | may coexist with `usesModel` for different model pairs |
| mentionsDataset | current paper discusses dataset without proof of current-study use/formal dataset citation | may coexist with `usesDataset` for different dataset pairs |
| reportsMetric | Finding/Experiment explicitly reports an EvaluationMetric | metric and endpoint must align contextually |
| evaluates | EvaluationMetric explicitly evaluates a Method/model | proximity alone is insufficient |
| hasParameter | Method/Experiment/model has a contextual Parameter | identify plausible owner; not every parameter belongs to Paper |
| usesAlgorithm | Method explicitly uses named reusable Algorithm | no Paper→usesAlgorithm shortcut |
| referencesDataset — exact omitted identifier | formal dataset reference with exact identifier omitted/deferred by Phase B | deferred-resolution only |
| mentionsConcept | specific Concept is substantively discussed/defined/analyzed/applied | avoid terminology flooding |
| mentionsTool | current paper discusses Tool without proof that current study uses it | may coexist with `usesTool` for different tool pairs |
| referencesRepository | explicit repository reference without associated-code evidence | `hasCodeRepository` is stronger |
| hasCodeRepository | explicit evidence repository contains code/scripts/implementation/workflow associated with study | use only for associated code |

---

## 9. Density and complexity anchors

These are **prospective screening judgments**, not exact counts.

### 9.1 Expected assertion density

| Value | Operational anchor |
|---|---|
| `none` | No plausible Pilot 1 semantic assertions in the unit. |
| `low` | One or a few simple semantic assertions; usually one narrow target family. |
| `medium` | Several plausible assertions across one or more target families. |
| `high` | Semantically dense unit with many plausible assertions across multiple target families. |

Do not count exact instances.

### 9.2 Expected relation density

| Value | Operational anchor |
|---|---|
| `none` | No plausible Pilot 1 semantic relations. |
| `low` | One or a few simple relation possibilities. |
| `medium` | Several relation possibilities and/or multiple endpoint types. |
| `high` | Many relation possibilities across multiple relation families or complex endpoint roles. |

### 9.3 Routing complexity

| Value | Operational anchor |
|---|---|
| `low` | Routing is obvious: zero targets or a small, clear set with little boundary ambiguity. |
| `medium` | Multiple legitimate targets or at least one meaningful class/relation boundary must be considered. |
| `high` | Several target families and/or repeated boundary decisions are likely; use/mention, model/method/tool, metric/parameter, discourse distinctions, or endpoint roles require careful routing. |

A long unit is not automatically high complexity, and a short unit can be high complexity.

---

## 10. Context and endpoint flags

### 10.1 Distributed evidence likely?

Choose **yes** when later semantic interpretation may plausibly require evidence distributed across multiple source units rather than being locally self-contained.

Typical reasons:

- a statement is introduced here and completed elsewhere;
- a method/configuration is split across units;
- an entity role can only be established by combining distant text;
- a table/prose or subsection split is likely to distribute support.

Choose **no** when the displayed unit is sufficiently self-contained for the kinds of targets being routed.

### 10.2 Section context useful?

Choose **yes** when surrounding units from the same section would likely improve interpretation or disambiguation, even if the final evidence could still be local.

This is intentionally different from distributed evidence:

```text
sectionContextUseful = yes
distributedEvidenceLikely = no
```

is valid when neighboring prose helps interpretation but the assertion itself is locally supportable.

### 10.3 Deterministic endpoint likely?

Choose **yes** when a likely semantic relation may need to connect to an exact endpoint already present or resolvable from deterministic/deferred infrastructure.

Strong cues include:

- exact dataset/resource identifiers;
- canonical repository URLs;
- deterministic node/deferred references exposed by the interface;
- explicit source artifacts whose identity is expected to come from Phase B or resolver infrastructure.

Choose **no** merely because a named entity exists. The flag concerns the likely need for a deterministic/resolver endpoint, not entity importance.

---

## 11. Likely exhaustive-empty targets

This field is intentionally narrow.

A target may be selected here only if:

1. it is already routed for the unit;
2. its treatment is `extract_and_evaluate`;
3. it is a target for which later annotation will use exhaustive completeness;
4. the reviewer prospectively expects the unit to contain **zero** supported instances.

This remains a screening expectation, **not a gold absence label**.

Do not:

- select monitored (`extract_and_monitor`) targets here;
- use the field to record every routed target that appears absent;
- treat it as definitive evidence of absence;
- spend extra time proving a negative.

**Default under uncertainty:** leave it unselected.

---

## 12. Recurring distinctions

Mark a distinction when the unit is likely to exercise that boundary during later annotation.

| Controlled value | Mark when... |
|---|---|
| `Model/Method/Algorithm/Tool` | named systems/procedures/software/models create plausible typing or role boundaries |
| `Finding/Conclusion` | unit mixes direct results with study-level synthesis |
| `ResearchProblem/ResearchGoal` | unit may contain both gap/problem language and objective/action language |
| `use/mention/reference` | model/tool/dataset/repository role may need actual-use vs mention/reference discrimination |
| `EvaluationMetric/Parameter` | numerical/configuration/evaluation language may require metric vs parameter discrimination |

Do not mark all five automatically for rich units.

---

## 13. Human screening judgment templates

The rationale should normally be **one concise sentence**. It should explain the nature of the unit and the basis for routing without listing every target.

Use these templates as controlled writing aids. Replace bracketed text only.

### Template A — no semantic target

```text
No substantive scientific content relevant to the Publication Pilot 1 semantic targets; the unit contains [editorial metadata / administrative metadata / page furniture / other non-semantic material] only.
```

### Template B — framing-focused unit

```text
Primarily research-framing content concerning [topic/problem/objective/significance], with routing limited to the framing and related semantic targets plausibly supported by the unit.
```

### Template C — methods/data unit

```text
Primarily methods/data content describing [procedure/data/model/configuration], with routing focused on applicable method, entity, measurement-context, and study-context targets.
```

### Template D — results unit

```text
Primarily results content reporting [findings/comparisons/metrics], with routing focused on findings, evaluation context, and applicable result-linked relations.
```

### Template E — discussion/conclusion unit

```text
Primarily interpretive or synthesis content concerning [result interpretation/limitations/conclusions/future work], with routing focused on the corresponding discourse targets and explicit supported relation types.
```

### Template F — study-area/geography unit

```text
Primarily study-area content identifying hydrologic features and/or named geographic areas relevant to the current study.
```

### Template G — resource/software/data unit

```text
Primarily resource-oriented content concerning [dataset/model/tool/repository], with routing preserving use-versus-mention-versus-reference and exact-identity boundaries.
```

### Template H — related-work unit

```text
Primarily related-research content describing or comparing prior work, with routing limited to substantive prior-research semantics and explicit local connections authorized for Pilot 1.
```

### Template I — mixed dense unit

```text
Semantically dense mixed content spanning [framing/methods/data/models/results/geography], with multiple target families and boundary distinctions likely to require later annotation.
```

### Template J — mixed Introduction / Related Work

```text
Semantically dense introduction combining [research background/problem/current-study framing] with substantive prior research and named scientific resources, requiring careful current-study-versus-cited-study ownership and use-versus-mention routing.
```

### Template K — genuinely ambiguous routing

```text
The unit supports prospective routing across [target/boundary A] and [target/boundary B], but the displayed text does not fully resolve the distinction; no external information was used.
```

### Optional screening-note templates

Use notes only when they add something not captured by the structured fields.

```text
Potential boundary to revisit during annotation: [X vs Y].
```

```text
Section context would likely help resolve [specific interpretation issue].
```

```text
Potential resolver-mediated identity: [dataset/repository]; exact identity should not be inferred during screening.
```

```text
REVISIT: screening decision remains uncertain because [brief reason].
```

Avoid notes such as “I think there are 3 findings” or pasted evidence quotations. Those belong to annotation, not screening.

---

## 14. Fast-path decision patterns

These are generic patterns, not examples from the real 267-unit production population.

### 14.1 Editorial/administrative fragment

Typical outcome:

```text
Assertion density: none
Relation density: none
Routing complexity: low
Node routing: none
Relation routing: none
```

### 14.2 Narrow framing fragment

Typical approach:

- route only plausible framing targets;
- relation density often none/low;
- complexity low/medium depending on Problem vs Goal or other boundaries.

### 14.3 Methods/data fragment

Typical approach:

- inspect Method/Experiment/DataDescription;
- inspect named models/tools/algorithms;
- inspect Variable/Parameter/Dataset targets;
- route relations only where actual semantic roles are plausible.

### 14.4 Results fragment

Typical approach:

- inspect Finding, EvaluationMetric, Variable;
- consider `reportsMetric`, `evaluates`, `produces`, or `supports` only if their semantic role is plausible;
- do not turn every result sentence into Conclusion.

### 14.5 Mixed abstract-like fragment

Typical approach:

- expect higher assertion/relation density;
- route across multiple families where legitimately applicable;
- mark recurring distinctions only for actual boundary pressure;
- do not interpret richness as permission to select every target.

### 14.6 Mixed Introduction / Related Work

Typical approach:

1. separate current-study framing from prior-study descriptions;
2. consider Background, ResearchProblem, ResearchQuestion/Goal, ResearchSignificance, Claim, Definition, and RelatedResearch where plausible;
3. route named models/tools/datasets/concepts conservatively;
4. apply the **current-artifact ownership rule** before routing Paper-branch `uses*` or `studies*` relations;
5. route `mentions*` where the current paper substantively discusses prior-work entities without proof of current-study use;
6. remember that `usesX` and `mentionsX` may both be routed for different endpoint pairs in the same unit;
7. use `use/mention/reference` and `ResearchProblem/ResearchGoal` recurring distinctions when those boundaries are genuinely active.

---

## 15. High-risk distinctions

### 15.1 ResearchProblem vs ResearchGoal

```text
ResearchProblem = what gap, deficiency, uncertainty, or challenge exists.
ResearchGoal    = what the current paper intends to do.
```

An objective does not automatically imply an explicit ResearchProblem.

### 15.2 Finding vs Conclusion

```text
Finding    = what the current study observed/produced.
Conclusion = higher-level study synthesis/general conclusion derived from findings.
```

A repeated result remains a Finding.

### 15.3 Method vs Algorithm vs Tool vs Model

```text
Method    = applied technique/procedure/activity.
Algorithm = named reusable computational procedure.
Tool      = software application/platform/package/system.
Model     = named computational representation/predictive entity.
```

Use the most specific supported concrete type. Never use abstract `ComputationalModel` as a fallback.

### 15.4 EvaluationMetric vs Parameter vs Variable

```text
EvaluationMetric = evaluates performance/outcome quality.
Parameter        = controls/configures a model, method, algorithm, or experiment.
Variable         = measured/observed/predicted/derived/analyzed quantity.
```

Preserve contextual occurrence boundaries.

### 15.5 Use vs mention vs reference

```text
actual current-study use -> usesModel / usesTool / usesDataset
current-paper discussion  -> mentionsModel / mentionsTool / mentionsDataset
formal data citation      -> referencesDataset
associated code           -> hasCodeRepository
generic repository ref    -> referencesRepository
```

For the **same endpoint pair**, use supersedes mention. A cited study's use does not become current-paper use.

---

## 16. Common screening errors

1. **Treating screening as annotation.**
   Do not identify exact spans, counts, or gold instances.

2. **Selecting every ontology-valid target.**
   Publication Pilot 1 uses the operational target profile/catalog, not the complete ontology.

3. **Routing relation from endpoint co-occurrence.**
   Domain/range compatibility is necessary but not sufficient.

4. **Attributing a cited study's actions to the current paper.**
   Prior-study `usesModel/usesDataset/usesTool/studiesPlace/studiesFeature` do not become current-paper relations.

5. **Treating affiliations as study geography.**
   Affiliations and publisher locations are not `NamedPlace` study targets.

6. **Treating keywords as proof of use.**
   A keyword can motivate Theme/Concept consideration but does not prove `usesModel`, `usesTool`, or `usesDataset`.

7. **Inventing missing relations.**
   If a label is not in the interface/catalog, do not create an analogue.

8. **Using external knowledge.**
   Screen the displayed canonical unit; record context need instead of researching the answer.

9. **Over-routing Concept.**
   Prefer a more precise class where one exists.

10. **Using abstract superclass fallback.**
   `ComputationalModel`, `SoftwareEntity`, `Place`, and `HydrologicFeature` are not direct Pilot 1 output classes.

11. **Applying use-over-mention globally to the whole unit.**
    Precedence operates on the same endpoint pair.

12. **Forcing the menu into 5–12 targets.**
    The UI target count is not a semantic cap.

---

## 17. Time-control rule for production screening

The goal is consistent prospective routing, not exhaustive semantic interpretation.

Recommended operational rule:

```text
ordinary unit: target approximately 1–2 minutes
difficult unit: do not exceed approximately 3 minutes on first pass
```

If a unit remains genuinely uncertain after the first pass:

1. save the draft;
2. add a short `REVISIT:` note;
3. continue to the next unit;
4. return later using the application's pending/review navigation.

Do not resolve the uncertainty with web search or model assistance.

This time-control rule is an operational recommendation for screening efficiency; it is not part of Gate 0 timing. Gate 0 later measures annotation time on the selected calibration units under its separate frozen timing policy.

---

## 18. Production integrity rule

The production screening must remain human and prospective.

Any AI/LLM assistance used to decide the routing of a **specific production source unit** would change the screening protocol and could contaminate the prospective selection process. Therefore:

- general handbook clarification is allowed;
- general questions about target definitions are allowed;
- specific production-unit routing decisions should not be delegated to an LLM under the current protocol.

If the protocol is ever changed to allow AI-assisted screening, that change must be versioned prospectively and its impact on calibration/evaluation selection must be documented before continuing.

---

## 19. Completion checklist for each unit

Before selecting **Mark reviewed & next**, confirm:

- the rationale describes screening, not annotation;
- assertion density is assigned;
- relation density is assigned;
- routing complexity is assigned;
- all three boolean flags are explicitly answered;
- recurring distinctions are marked only where relevant;
- node routes are legitimate Publication Pilot 1 targets;
- relation routes reflect plausible semantic roles, not mere endpoint co-occurrence;
- current-paper versus cited-study ownership has been checked where applicable;
- use-versus-mention precedence has not been applied globally across different endpoint pairs;
- exhaustive-empty choices, if any, are routed `extract_and_evaluate` targets only;
- no external information was used;
- optional notes contain no gold labels/evidence-span annotation.

---

## 20. Handbook freeze procedure

Before production screening begins:

1. incorporate this candidate handbook into the repository and approved interface aids;
2. complete one final **discarded smoke test** of the interface using the handbook;
3. correct only genuine ambiguity or implementation defects;
4. assign a final handbook version and SHA-256;
5. commit the frozen handbook and accepted UI aids;
6. reset/delete all dry-run state;
7. start production screening with a new production reviewer session;
8. do not silently change the handbook once production screening has begun.

A blocking defect discovered after production starts should trigger a documented, versioned correction and an explicit decision on whether already screened units require re-review.

---

## 21. Recommended UI aids before production

These aids may accelerate screening without changing semantic authority:

1. a persistent **Handbook / Quick reference** link or side panel;
2. human-selected **rationale template buttons/dropdown** that insert editable text but never infer a template automatically;
3. a one-click **No semantic targets** convenience action that clears semantic routing but still requires explicit density/complexity/flag decisions before completion;
4. read-only display of relevant `deterministicNodeRefs`, `deterministicEdgeRefs`, and `deferredRecordRefs` when present;
5. an interface-local **Revisit/bookmark** flag that is not exported into the canonical screening contract.

None of these aids may auto-select semantic targets or recommend routing from the source text.

---

## 22. Binding references for this handbook

- `docs/publication_pilot1_block_a_screening_routing_selection.md`
- `docs/publication_pilot1_screening_interface.md`
- `docs/publication_llm_extraction_target_inventory.md`
- `src/extraction/llm/publications/publication_target_inventory.yaml`
- `data/curation/papers/pilot1/publication_pilot1_target_display_catalog.yaml`
- `data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv`
- `schemas/publication_pilot1_screening_record.schema.json` (repository path as implemented)
- frozen CIROH ontology 0.1.3 specification and generated OWL

If the handbook conflicts with a frozen upstream authority, the upstream authority governs and the handbook must be corrected through a versioned change.
