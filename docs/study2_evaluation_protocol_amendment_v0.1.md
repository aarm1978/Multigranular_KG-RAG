# Study 2 Evaluation Protocol Amendment v0.1

**Status:** prospective amendment; effective while Human Core primary annotation is beginning

**Scope:** Study 2 publication-extraction evaluation

**Purpose:** record the prospective redesign of the human reference component. This is a
protocol amendment, not a manuscript section, an evaluation result, or a replacement for
the frozen annotation authorities.

## 1. Amendment boundary

This amendment prospectively documents the Human Core design used for the next evaluation
stage. It does not reinterpret, migrate, rerun, or otherwise alter historical
Calibration or DEV artifacts. It also does not alter the ontology, extraction
architecture, target inventory, routing, evidence rules, Human Core guide, annotation
application, Human Core freeze/package, or annotation state.

The amendment concerns evaluation architecture and the scope of the prospective human
reference. It does not make a representativeness claim for all 11 primary publications.

## 2. Original protocol and reason for amendment

The original Study 2 proposal framework contemplated a relatively large stratified human
gold standard, with at least two annotators per artifact, inter-annotator agreement (IAA)
and adjudication, followed by entity and relation Precision, Recall, and F1 evaluation.

Calibration showed that the burden of applying the semantic task was substantially higher
than expected. Annotators were also uncertain about whether they had achieved exhaustive
semantic coverage. Under those conditions, a larger nominally independent gold set is not
preferable when its completeness or correctness is doubtful. The redesign therefore
prioritizes a smaller, prospectively selected and source-grounded Human Core with explicit
scope and reliability controls over an unsupported claim of broad, exhaustive human gold.

| Original protocol | Amended protocol |
| --- | --- |
| Relatively large stratified human gold | Frozen N=5 Human Core, selected prospectively and model-blind before semantic inspection |
| At least two annotators per artifact | Researcher/task expert is the primary annotator; independent annotation is predeclared for a two-unit reliability subset |
| IAA plus adjudication across the planned gold | Reliability is limited to the predeclared subset; pooled human adjudication is a separate, pending reference component |
| Entity and relation P/R/F1 against the planned broad gold | Any production scoring must follow a pending amended Human Core matching and acceptance contract; Human Core does not claim representation of all 11 primary publications |

## 3. Rejected shortcut: LLM consensus is not gold

No LLM-LLM consensus gold will be created or used as a substitute for human reference.
Humans remain the authority for truth decisions. Model outputs may be evaluated against a
human reference under a later contract, but they must not establish, complete, or adjudicate
the reference merely by agreement with one another.

## 4. Frozen amended Human Core

The prospective Human Core is frozen with the following properties:

- **N=5** units, selected prospectively and model-blind before semantic inspection.
- The five units come from **five distinct publications** and cover **5/5 sampling strata**.
- The frozen routed coverage includes all **19 scored node targets** and all **16 scored
  relation targets**.
- The researcher/task expert is the primary annotator.
- Annotation is canonical-source and model-blind: the primary annotator does not use model
  prompts, outputs, validation results, confidence, or proposed labels to create the
  reference.
- Exhaustive review applies only to routed `extract_and_evaluate` targets. It must not be
  generalized to monitor targets, structurally unavailable targets, unrouted targets, or
  the entire publication corpus.
- An independent reliability subset of **2 units** is predeclared.

These properties establish a bounded, coverage-oriented Human Core. They do not support a
claim that the five units are representative of every semantic condition, artifact unit,
or all 11 primary publications.

## 5. Broader accepted evaluation architecture

The accepted Study 2 architecture separates evaluation purposes and evidence sources:

1. **Human Core Gold:** the bounded, model-blind human reference described above.
2. **Pooled human-adjudicated reference:** a later pooled reference for human decisions
   under a separately specified procedure.
3. **Model-blind completeness audit:** a separate audit of reference completeness that
   remains independent of model outputs.
4. **SciERC external IE anchor:** an external information-extraction anchor, governed by
   its own later contract.
5. **GraphRAG structural comparison only:** comparison is limited to the accepted
   schema-agnostic structural measures; it is not a correctness or human-gold baseline.

This architecture preserves the distinction between human semantic truth, extraction
quality, completeness evidence, external IE context, and structural comparison. In
particular, GraphRAG density or relational-richness results cannot establish semantic
correctness, and SciERC does not replace the Human Core for the CIROH publication task.

## 6. Status of amended components

| Component | Status | Boundary |
| --- | --- | --- |
| Human Core N=5 selection, five publications, 5/5 strata, and 19-node/16-relation routed coverage | **FROZEN** | Prospective, model-blind selection before semantic inspection |
| Primary annotator role, canonical-source/model-blind annotation, routed `extract_and_evaluate` exhaustiveness, and two-unit reliability subset | **FROZEN** | Bounded Human Core procedure only |
| Amended Human Core matching contract | **PENDING — not frozen** | Defines future scoring correspondence and aggregation; it does not alter historical Pilot 1 contracts |
| Pooled contributors, deduplication, and adjudication procedure | **PENDING — not frozen** | Defines the pooled human-adjudicated reference |
| Completeness-audit design and statistic | **PENDING — not frozen** | Must remain model-blind |
| SciERC contract | **PENDING — not frozen** | Defines the external IE anchor and permitted claims |
| Production acceptance policy | **PENDING — not frozen** | Does not follow automatically from Human Core annotation |

Pending components must be specified prospectively before their respective results are
used for production acceptance or confirmatory claims. This amendment does not silently
freeze any of them.

## 7. Operational interpretation

Human Core primary annotation and the independent reliability annotation may proceed under
their frozen authorities. This amendment neither changes their semantic task nor authorizes
access to model output during annotation. Later evaluation work must retain historical
Calibration and DEV provenance as created, maintain the current extraction architecture,
and distinguish Human Core evidence from any pooled, audit, SciERC, or GraphRAG result.
