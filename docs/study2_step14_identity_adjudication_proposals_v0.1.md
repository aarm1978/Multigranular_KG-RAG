# Step 14: prospective 43-case identity adjudication proposals v0.1

## Status, authority, and verified scope

**Historical provisional triage, followed by a bounded researcher approval batch.**
The 43-case triage was provisional ChatGPT-assisted review, not researcher
adjudication. Only the 29 subsets listed below have subsequently received explicit
researcher approval. The original proposals and LLM recommendations remain intact.
It is not independent/blinded annotation, a new acceptance policy, or a claim of
population precision/recall. The [evaluation decisions](evaluation_decisions.md)
and frozen order-50 metrics remain unchanged.

The [granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md),
[identity pilot](study2_step14_semantic_identity_pilot.md),
[semantic review](study2_step14_semantic_review.md), and
[live recommendation contract](study2_step14_identity_live.md) govern this proposal.
Ontology [v0.1.7](../src/ontology/ontology_spec.yaml) remains frozen. Named-technique
or named-product identity never implies identical implementations, trained weights,
configurations, releases, deployments, or executions. Conceptual correspondence
alone is not entity identity; no new family/instance relationship is asserted.

Saved authority: `var/study2_step14/semantic-identity-live/v2/manifest.json`, SHA-256
`c2712f7e90b04c64e039a21302fb5b05ef922508f47b5a461ece813cb638662c`.
Its upstream pilot manifest is pinned at
`45654787b5545e37bab65c95e9fdd770452651518db20fe6402e9980b0ac209a`.
The live package, its input/output/implementation hashes, all completed-attempt
artifact hashes, raw response extraction, and local recommendation bindings were
verified offline without regeneration or provider calls.

| Verified quantity | Count |
|---|---:|
| Completed cases C001–C043 | 43 |
| Unique original occurrences / case memberships | 232 / 232 |
| Original LLM assessments | 75 |
| Model-reported unassessed occurrences | 0 |
| Whole-case entity-identity proposals | 26 |
| Partial or conditional review cases | 11 |
| Cases with no entity merge proposed | 6 |
| Subsequently approved entity-identity subsets / occurrences | 29 / 99 |
| Remaining unapproved occurrences / allocated canonical IDs | 133 / 0 |

The 26/11/6 counts describe the provisional ChatGPT-assisted **triage categories**,
not accepted matches. Whole-case proposals can contain flagged members requiring
interpretation. C016 is a partial/conditional review case with **no entity subset**
proposed. Unresolved or excluded members are not declared different entities.

## Subsequent researcher approval — batch 01

The [append-only decision records](evaluation/study2_step14_identity_approvals_batch01.jsonl)
record **24 complete cases**: C001, C002, C003, C005, C006, C007, C008,
C010, C011, C012, C013, C015, C017, C019, C021, C022, C026, C029, C030,
C033, C037, C039, C040, C043; and **five partial subsets only**:

- C023: O001–O005
- C028: O001–O002
- C032: O001–O002
- C035: O001, O005, O006, O008, O012, O015, O018
- C036: O001–O002

These are 29 approved subsets covering 99 distinct original occurrences. All
other 133 occurrences remain unapproved, not rejected. In particular, C020 and
C031 remain proposals. Approval is limited to the recorded class and granularity:
named-technique approval is not trained-model identity, and C032 approves only
the NWM v2.1 pair. All original evidence, version/source-role restrictions, conflict
citations, and review flags remain attached, including C002's trained-algorithm
wording, C021's year discrepancy, and C033's sparse title context. Approval does
not rewrite these assertions or claim that their underlying uncertainty vanished.

Each decision has its own ID/revision, explicit researcher authority, rationale,
case/context/package/proposal hashes, exact occurrence set, evidence IDs, original
candidate memberships, and unmodified recommendation references. Decision IDs
identify decisions, not canonical entities. Initial revisions have no superseded
decision. Future corrections must append a new revision with a supersession
reference; do not rewrite these records. The original pilot ledger template is
unchanged. No transitive union, canonical allocation, ontology change, or graph
materialization is authorized.

Case entries and JSON proposal statuses below preserve the **pre-approval triage**;
read the separate decision records for subsequent approval, rather than interpreting
historical `not_approved` proposal fields as current decision status. No case
disposition, proposed membership, or original model recommendation was rewritten.

## How to audit and read the case entries

The [machine-readable companion](study2_step14_identity_adjudication_proposals_v0.1.json)
is a reference index, not a decision ledger or mapping. For every case it retains
original case/context hashes, candidate memberships, exact original occurrence IDs
and classes, source artifact identities, evidence IDs, proposed subsets, and all
unresolved/excluded members. The common pinned manifest binds the package/input
hashes for every case. Each case has its own audit/request/attempt hashes.

`Cxxx`, `Oxxx`, and `Exxx` are request-local aliases. Resolve an O alias through
`occurrences`, and an E alias through `evidenceBindings`, within that case only.
Each `auditPointer` resolves against the SHA-256-bound `audit/Cxxx.json`. It
preserves the full original attributes, version statements, source/reference roles,
quotations, provenance, and exact frozen graph recovery pointers without copying
raw evidence into Git. `originalAcceptedRelationsPointer` preserves the selected
accepted relations and their exact predicates. No mention becomes use, no
reference becomes implementation, and no source artifact ID becomes a target ID.

`originalModelRecommendation` points to the unchanged, attributed `modelAuthored`
object; `originalRawResponse` pins its exact text. The compact assessment summaries
below and in the companion are attributed indexes, not replacements for the full
original rationale, missing-information, version, owner/reference, conflict, or
abstention fields. Indices below are one-based display numbers; JSON
`assessmentIndex` is zero-based. All recommendations remain from **gpt-6.1-sol,
medium**, with status `recommendation_only`.

Evidence citations support the **stated proposal granularity**, not every stronger
identity reading. The companion also retains the LLM's original conflict citations;
`reviewConcerns` records our explicit discrepancies or interpretive gaps with
member/evidence bindings. An empty proposal conflict list means no additional
identity-refuting evidence is asserted, not that conflicts have been adjudicated
away. Repeated excerpts and mirrored documentation are not independent confirmation.
Source capture versions are not entity versions; empty structured versions do not
erase version statements in quotations.

Evidence remains selected, not exhaustive. The original pilot omitted two of 421
relation-evidence occurrences (one `referencePublication`, one `usesTool`), as
recorded with exact edge IDs in the live contract. Nothing is restored or extracted
here. Missing evidence or a failed granularity interpretation prevents approval;
it does not authorize a fallback relation, retyping, or forced grouping.

## Proposed case dispositions

### C001 — NGIAB calibration repository (`Repository`)

**Whole-case proposal:** O001–O002 at **repository record** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E003): The named calibration repository and root link agree; local literal declarations are not promoted to global identifiers. No release, calibration run, or generated-data identity.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C002 — Random Forest (`Algorithm`)

**Whole-case proposal:** O001–O006 at **named technique** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E006): E001 defines the ensemble algorithm; E002–E006 name its use in distinct applications. The proposal deliberately differs from the LLM conceptual-only assessment at named-technique granularity. No fitted-forest, implementation, or training-run identity; TempEst 1 is a source system version.

**Review flag** (E002): O002/E002 explicitly says the algorithm has been trained. Confirm that the occurrence denotes the technique, rather than a fitted realization, before any whole-case approval; do not erase this ambiguity.

Original LLM: 1: `conceptual_similarity_only` [O001–O006]; 2: `shared_reference_target_only` [O002, O005].

### C003 — SWEML (`MLModel`)

**Whole-case proposal:** O001–O002 at **named model system** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E003): Both passages describe SWEML and its region-specific perceptron approach; repeated descriptions are not independent corroboration. No equality of regional trained networks, weights, runs, or releases.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C004 — JupyterHub (`Tool`)

**Partial/conditional review:** O007, O009 at **JupyterHub application/product** granularity; separately, O006, O008 at **JupyterHub-via-2i2c contextual platform referent** granularity. Unresolved/excluded from entity proposals: O001–O005.

Evidence (E007–E011): Retain O007/O009 as an application-level candidate and O006/O008 as a separate contextual platform candidate. O003 describes the product generally but does not establish a broader subset. Do not union these subsets or equate CIROH workshop, HydroShare, and 2i2c deployments.

**Review flag** (E001–E006): O001/O002/O004/O005 describe servers, workshop instances, or linked environments; the evidence does not resolve deployment versus product referents across the case.

Original LLM: 1: `same_entity_candidate` [O006, O008]; 2: `same_entity_candidate` [O007, O009]; 3: `conceptual_similarity_only` [O001–O009]; 4: `abstain` [O001–O009].

### C005 — HydroShare tutorial (`DatasetResource`)

**Whole-case proposal:** O001–O002 at **resource record** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): The same entity-own HydroShare ID identifies the tutorial resource and referenced stub. Not individual files or revisions; citation years 2025/2026 do not establish resource versions.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C006 — TEEHR (`Tool`)

**Whole-case proposal:** O001–O002 at **named software tool** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Expanded names and model-output/observation evaluation functions agree. NWM v3.0 in E002 is not a TEEHR version; deployments/releases remain unspecified.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C007 — Backpropagation (`Algorithm`)

**Whole-case proposal:** O001–O018 at **named technique** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E018): Derivative accumulation, gradient chains, and weight/state-update contexts support the named algorithm across all 18 occurrences. Different training and data-assimilation uses do not establish one implementation. O014 is attribution context; O015 describes a possible, not actual, use.

Original LLM: 1: `same_entity_candidate` [O001–O018].

### C008 — NOAA-OWP/ngen (`Repository`)

**Whole-case proposal:** O001–O002 at **repository record** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Recorded repository identity and root references agree. Root, branch/file, and commit-history targets must not imply one code snapshot.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C009 — LSTM (Rust) (`MLModel`)

**No entity merge proposed:** no entity-identity subset. Unresolved/excluded from entity proposals: O001–O002.

Evidence (E001–E002): Repeated excerpts identify the Rust-port and realization links; they support reference coincidence, not model identity. Main-branch URLs and source commits do not pin model weights or releases.

Original LLM: 1: `shared_reference_target_only` [O001–O002].

### C010 — HydroShare retrospective paper (`Paper`)

**Whole-case proposal:** O001–O002 at **bibliographic paper** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Entity-own DOI and bibliographic title agree. Paper identity does not identify HydroShare software versions.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C011 — Annual temperature cycle paper (`Paper`)

**Whole-case proposal:** O001–O002 at **bibliographic paper** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Entity-own DOI, title, year, and bibliographic context agree. Citation suffixes 2024a/2024b are not article versions.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C012 — Recursive Feature Elimination (`Algorithm`)

**Whole-case proposal:** O001–O002 at **named technique** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): E001 describes feature selection using the procedure; E002 describes scaling before it. Named-technique identity is a deliberate prospective departure from the LLM conceptual-only recommendation. No shared LightGradientBoost implementation, selected features, or trained-model identity.

Original LLM: 1: `conceptual_similarity_only` [O001–O002].

### C013 — mhpi/dhbv2 (`Repository`)

**Whole-case proposal:** O001–O002 at **repository record** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Root, owner/name, and accepted identifier context agree. Tree/commit references and daily/multi-timescale labels do not identify one model implementation.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C014 — OWP HAND-FIM (`ProcessBasedModel`)

**Partial/conditional review:** O001–O012, O015–O021 at **named model/framework** granularity. Unresolved/excluded from entity proposals: O013–O014.

Evidence (E001–E022, E028–E037): O001–O012 and O015–O021 describe the named HAND/SRC framework across operational and study contexts. Retain scenarios, slope inputs, prediction configurations, results, and releases separately.

**Review flag** (E023–E027): O013/E023–E024 distinguishes default and adjusted SRC predictions; O014/E025–E027 mixes prediction and generic HAND context. Do not extend the framework proposal to these members.

Original LLM: 1: `same_entity_candidate` [O001–O012, O015–O021]; 2: `shared_reference_target_only` [O001, O009]; 3: `conceptual_similarity_only` [O001, O013–O014].

### C015 — WRF-Hydro (`ProcessBasedModel`)

**Whole-case proposal:** O001–O003 at **named model family** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E003): All three passages identify WRF-Hydro through its specific NWM/Noah-MP context. NWM 3.0 is not WRF-Hydro version identity; NWM configurations remain distinct.

Original LLM: 1: `same_entity_candidate` [O001–O003].

### C016 — LSTM networks (`MLModel`)

**Partial/conditional review:** no entity-identity subset. Unresolved/excluded from entity proposals: O001–O008.

Evidence (E001–E011): No entity subset is proposed. O003/O004/O006/O007/O008 primarily discuss architecture/family; O002/O005 include study-specific use/training; O001 is BMI implementation context. These are review partitions, not identities; O004 also contains comparative study context and O008 cites an application.

**Review flag** (E001, E003, E006, E008, E011): O002/E003 and O005/E008 cannot be collapsed into architecture-only occurrences by dropping the study-specific statements.

Original LLM: 1: `conceptual_similarity_only` [O001–O008].

### C017 — CAMELS publication (`Paper`)

**Whole-case proposal:** O001–O002 at **bibliographic paper** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Full citations agree on authors, title, DOI, year, journal, and pages, beyond the local DOI URL declaration. Do not promote local declarations into authoritative global identifiers or equate the paper with its dataset.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C018 — LSTM model (`MLModel`)

**Partial/conditional review:** O010, O017, O019 at **study-local model referent, checkpoint unresolved** granularity; separately, O011, O022 at **study-local model referent, checkpoint unresolved** granularity. Unresolved/excluded from entity proposals: O001–O009, O012–O016, O018, O020–O021.

Evidence (E013–E014, E024, E026, E030–E031): Retain only the LLM study-local subsets O010/O017/O019 and O011/O022 for further review. Shared-paper context is not checkpoint/configuration identity; no cross-subset union.

**Review flag** (E001–E003, E006, E014, E017–E019, E021–E023, E030–E031): O004 excludes combined-flow training, unlike O011/O022. O014/O016 mix standard and drainage-density variants. O001/O002 concern different deployment contexts; source release numbers are not LSTM versions.

Original LLM: 1: `same_entity_candidate` [O010, O017, O019]; 2: `same_entity_candidate` [O011, O022]; 3: `different_entities_candidate` [O004, O022]; 4: `different_entities_candidate` [O004, O011]; 5: `shared_reference_target_only` [O007–O008]; 6: `abstain` [O014, O016]; 7: `abstain` [O001–O002]; 8: `conceptual_similarity_only` [O001–O022].

### C019 — NGIAB data preprocess (`Repository`)

**Whole-case proposal:** O001–O003 at **repository record** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E005): Repository README, named content-source link, and preprocessing repository link agree. No file, notebook, branch, or implementation-version identity.

Original LLM: 1: `same_entity_candidate` [O001–O003].

### C020 — CFE (ConceptualModel) (`ConceptualModel`)

**Whole-case proposal:** O001–O009 at **named conceptual-model referent** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E011): Named CFE descriptions consistently identify the simplified hydrological model; retain this proposal within the recorded ConceptualModel class. No identity with C041 ProcessBasedModel occurrences; no BMI/original-code or calibrated-parameter equivalence.

**Review flag** (E007–E008, E017, E024–E025): O007 is module inventory context and O008/E008 is a 17-parameter study model. Confirm the named-model referent without erasing calibration/implementation specificity. The cross-class CFE question remains gated.

Original LLM: 1: `same_entity_candidate` [O001–O009].

### C021 — HydroShare social-objects paper (`Paper`)

**Whole-case proposal:** O001–O002 at **bibliographic paper** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E007): Entity-own DOI, authors, title, journal, and available pagination agree. Citation-year discrepancy is retained, not corrected or converted to an article-version difference.

**Review flag** (E001, E007): E007 gives 2015a, whereas E001 gives 2016. This is a bibliographic discrepancy requiring researcher attention, not an automatically rejected identity.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C022 — SCS Curve Number (`Algorithm`)

**Whole-case proposal:** O001–O002 at **named technique** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Both occurrences name the method and its runoff-estimation role. Not calibrated parameters, implementations, or executions.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C023 — Noah-OWP-Modular (`ProcessBasedModel`)

**Partial/conditional review:** O001–O005 at **named model** granularity. Unresolved/excluded from entity proposals: O006.

Evidence (E001–E005): O001–O005 describe the named Noah-MP refactoring and CFE-coupled land-surface model. No submodule revision, configuration, or compiled-build identity.

**Review flag** (E006): O006/E006 denotes a wrapper around a Git submodule; its entity boundary remains unresolved.

Original LLM: 1: `same_entity_candidate` [O001–O005]; 2: `shared_reference_target_only` [O001, O004]; 3: `conceptual_similarity_only` [O001–O006].

### C024 — SAC-SMA (`ConceptualModel`)

**No entity merge proposed:** no entity-identity subset. Unresolved/excluded from entity proposals: O001–O002.

Evidence (E001–E002): No entity subset: O001 is generic; O002 specifies SAC-SMA with SNOW-17 and unit-hydrograph routing. Configured benchmark/calibration is not equated with the general model; unresolved is not necessarily different.

Original LLM: 1: `conceptual_similarity_only` [O001–O002].

### C025 — T-Route (`Tool`)

**Partial/conditional review:** O008–O015, O017 at **named software project, separate subsets** granularity; separately, O005–O006 at **named software project, separate subsets** granularity. Unresolved/excluded from entity proposals: O001–O004, O007, O016.

Evidence (E006–E007, E009–E018, E020): Retain O008–O015 plus O017 as the NGIAB project-context subset and O005/O006 as the NOAA-OWP routing-project subset. No union; O001 branch, O007 kernels, O002/O003/O016 sparse tool/module descriptions stay separate.

**Review flag** (E005–E007): O004/E005 describes DEM channel-network generation, unlike the routing descriptions E006/E007. Preserve the inconsistent function description; do not repair it or infer a different entity.

Original LLM: 1: `same_entity_candidate` [O008–O015, O017]; 2: `same_entity_candidate` [O005–O006]; 3: `conceptual_similarity_only` [O001, O003, O005–O008, O016]; 4: `abstain` [O002, O006]; 5: `abstain` [O004–O005].

### C026 — DDS (`Algorithm`)

**Whole-case proposal:** O001–O004 at **named technique** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E004): All four occurrences identify DDS as a calibration algorithm. OSTRICH and ngen-cal contexts do not imply the same implementation or calibration execution.

Original LLM: 1: `same_entity_candidate` [O001–O004].

### C027 — XGBoost (`MLModel`)

**No entity merge proposed:** no entity-identity subset. Unresolved/excluded from entity proposals: O001–O005.

Evidence (E001–E006): No entity subset: contexts describe repeated training, parameter tuning, cross-validation, feature importance, and RF comparisons. Different research contexts do not by themselves prove different entities; no common fitted-model identity.

Original LLM: 1: `conceptual_similarity_only` [O001–O005].

### C028 — CUAHSI/notebooks (`Repository`)

**Partial/conditional review:** O001–O002 at **repository record** granularity. Unresolved/excluded from entity proposals: O003.

Evidence (E001–E003): O001/O002 explicitly locate development notebooks in the same repository and folder. O003 is reference-target support only; shared root URL does not extend entity identity or fix notebook versions.

Original LLM: 1: `same_entity_candidate` [O001–O002]; 2: `shared_reference_target_only` [O001–O003].

### C029 — NeuralHydrology paper (`Paper`)

**Whole-case proposal:** O001–O002 at **bibliographic paper** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E003): Entity-own DOI and compatible title/journal/year descriptions identify the paper candidate. Not identity of the software library, repository, or release.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C030 — RIce-Net (`MLModel`)

**Whole-case proposal:** O001–O002 at **named framework** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E006): Both describe the classifier/segmentation/ice-fraction/flag framework and 2023 training/2024 testing. Cedarburg-specific versus selected-station training descriptions do not establish identical trained artifacts or a contradiction.

Original LLM: 1: `same_entity_candidate` [O001–O002].

### C031 — CAMELS-US (`DatasetResource`)

**Whole-case proposal:** O001–O005 at **named base dataset resource** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E009): E001 explicitly distinguishes the sample from full CAMELS; E003 names CAMELS US; E005 identifies CONUS catchments; E007 names the benchmarking dataset; E009 refers to its 671 basins. No identity of samples, extensions, releases, files, training selections, or remapped AORC forcing products.

**Review flag** (E001, E003, E005, E009, E013, E015): O001/O002/O003/O005 contain selection, extension, training, or derived-product context. The proposal concerns only their base-resource referent; if an occurrence instead denotes a subset/product, flag it rather than forcing whole-case approval.

Original LLM: 1: `same_entity_candidate` [O001–O005]; 2: `shared_reference_target_only` [O001–O005].

### C032 — NWM (`ProcessBasedModel`)

**Partial/conditional review:** O001–O002 at **v2.1 release** granularity. Unresolved/excluded from entity proposals: O003–O005.

Evidence (E001–E004): O001/O002 explicitly say current v2.1 retrospective and prospective v3.0; only this pair is proposed. O004 is v3.0 (E009); O003/O005 have unresolved release specificity; no family-level bridge.

**Review flag** (E002, E004–E006, E009–E010): Empty structured versions do not erase explicit releases in E002/E004/E009. The LLM family-wide reference-target recommendation is not adopted as release identity.

Original LLM: 1: `same_entity_candidate` [O001–O002]; 2: `shared_reference_target_only` [O001–O005]; 3: `different_entities_candidate` [O001, O004]; 4: `different_entities_candidate` [O002, O004].

### C033 — Kriging (`Algorithm`)

**Whole-case proposal:** O001–O003 at **named technique** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E003): Three occurrences name Kriging in streamflow, remapping, and groundwater-surface contexts. Named-technique identity deliberately differs from the LLM conceptual-only result. Semivariogram variants, interpolation products, implementations, and executions remain distinct.

**Review flag** (E001, E006): O001/E001 is title-only support; the selected relation evidence repeats it rather than adding methodological detail. Do not read a specific Kriging variant into it.

Original LLM: 1: `conceptual_similarity_only` [O001–O003].

### C034 — Tethys Visualizer (`Tool`)

**Partial/conditional review:** O001–O002 at **named software tool** granularity. Unresolved/excluded from entity proposals: O003.

Evidence (E001–E003): O001/O002 have the same Visualizer download function and linked ngiab-client context, supporting the proposed named-tool reading beyond URL coincidence. No identical deployment/version claim; O003 remains unresolved.

**Review flag** (E001–E004, E007): This is a prospective named-tool proposal beyond the LLM shared-reference-target result. Mirrored wording is not independent confirmation; E004/E007 supplies only setup context for O003.

Original LLM: 1: `shared_reference_target_only` [O001–O002]; 2: `conceptual_similarity_only` [O001–O003].

### C035 — Singularity (`Tool`)

**Partial/conditional review:** O001, O005–O006, O008, O012, O015, O018 at **named platform** granularity. Unresolved/excluded from entity proposals: O002–O004, O007, O009–O011, O013–O014, O016–O017.

Evidence (E001, E005–E006, E008, E013, E016, E019): Propose only O001/O005/O006/O008/O012/O015/O018 as platform references. No union with NGIAB Singularity images, builds, or ambiguous container references.

**Review flag** (E003, E006): The LLM also proposed an image-lineage subset; it is retained as an original recommendation but is not adopted as an entity proposal here. Distinguish O006 platform from O003 image/build context.

Original LLM: 1: `same_entity_candidate` [O001, O005–O006, O008, O012, O015, O018]; 2: `same_entity_candidate` [O003–O004, O009–O011, O014]; 3: `conceptual_similarity_only` [O002–O003, O006–O007, O013, O016–O017]; 4: `different_entities_candidate` [O003, O006].

### C036 — Soil Freeze-Thaw Model (`ProcessBasedModel`)

**Partial/conditional review:** O001–O002 at **named model** granularity. Unresolved/excluded from entity proposals: O003.

Evidence (E001–E002): O001/O002 share the soil heat-transfer/freeze-thaw description and model repository association. O003 remains unresolved; NWM v4.0 and citation 2025c are not model versions.

**Review flag** (E003, E008–E009): O003 has only module-list/citation context in the selected evidence; no stronger source-bound identity support was found in this package. Temporary unavailability in E007 is not different-entity evidence.

Original LLM: 1: `same_entity_candidate` [O001–O002]; 2: `shared_reference_target_only` [O001–O002]; 3: `conceptual_similarity_only` [O001–O003].

### C037 — EvaluationWithBuildingFootprint (`Tool`)

**Whole-case proposal:** O001–O007 at **named FIMeval module** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E007): Distinctive module name, FIMeval context, and building-impact evaluation function agree across all seven occurrences. Different flood applications are not common executions or releases; repeated passages add no corroboration.

Original LLM: 1: `same_entity_candidate` [O001–O007].

### C038 — Transformer (`MLModel`)

**No entity merge proposed:** no entity-identity subset. Unresolved/excluded from entity proposals: O001–O009.

Evidence (E001–E009): No entity subset: workshop models, NeuralHydrology encoding class, GeoDTR/GeoDTR+ components, and rainfall-runoff study models remain unresolved. Do not infer entity identity from study co-location or conceptual similarity; single models/ensembles remain distinguishable.

Original LLM: 1: `conceptual_similarity_only` [O001–O009]; 2: `abstain` [O003, O008–O009]; 3: `abstain` [O002, O004, O006].

### C039 — Parallel wave-front routing (`Algorithm`)

**Whole-case proposal:** O001–O002 at **named technique** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Both passages describe concurrent processing of independent branches using topological ordering. The named-technique proposal deliberately differs from the LLM conceptual-only result. Mirrored wording is not independent confirmation and does not identify one implementation.

Original LLM: 1: `conceptual_similarity_only` [O001–O002].

### C040 — AWS CLI (`Tool`)

**Whole-case proposal:** O001–O005 at **named software product** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E005): S3 upload, EC2 management, tagging, and infrastructure prerequisites support the product-level referent. No release, installed copy, account, deployment, or execution identity.

Original LLM: 1: `same_entity_candidate` [O001–O005].

### C041 — CFE (ProcessBasedModel) (`ProcessBasedModel`)

**No entity merge proposed:** no entity-identity subset. Unresolved/excluded from entity proposals: O001–O002.

Evidence (E001–E003): No entity subset: recorded ProcessBasedModel occurrences include default configuration and original-code versus BMI-CFE comparisons. Matching test outputs do not prove implementation identity; do not join C020 or retype either case.

**Review flag** (E001–E003): C020 uses ConceptualModel while C041 uses ProcessBasedModel for named CFE references. This cross-case classification/representation issue is separate from insufficient evidence about implementation identity.

Original LLM: 1: `conceptual_similarity_only` [O001–O002].

### C042 — Muskingum-Cunge (`ProcessBasedModel`)

**No entity merge proposed:** no entity-identity subset. Unresolved/excluded from entity proposals: O001–O002.

Evidence (E001–E003): No entity subset: general routing discussion differs in specificity from the differentiable GPU/implicit-scheme component with learned hydraulic parameters. No version conflict inferred; specialized implementation is not collapsed into family identity.

Original LLM: 1: `conceptual_similarity_only` [O001–O002].

### C043 — rust-lstm-1025 (`Repository`)

**Whole-case proposal:** O001–O002 at **repository record** granularity. Unresolved/excluded from entity proposals: none.

Evidence (E001–E002): Recorded owner/name, identity regime, and repository-root references agree. No equality of Rust/Python implementations, trained weights, main-branch state, or v0.1.0 code snapshot.

Original LLM: 1: `same_entity_candidate` [O001–O002].

## Disagreements and limits requiring attention

- **C002, C012, C033, C039:** named-technique entity proposals deliberately differ
  from the original conceptual-only recommendations. They do not retroactively
  change those recommendations. C002/O002 has explicit trained-algorithm wording;
  C033/O001 has title-only support. These limitations require interpretation before
  approval, not automatic whole-case grouping.
- **C034:** the proposed named-tool O001/O002 identity is broader than the LLM's
  shared-reference-target result. The shared functionality and title support the
  proposal; they do not establish release or deployment identity.
- **C035:** retain the model's additional NGIAB image-lineage recommendation only as
  an original recommendation. This task proposes only the named-platform subset.
- **C020/C031:** retain the proposed named model/base-resource grouping but flag
  parameterized, subset, extension, and derived-product contexts. Do not erase
  occurrence specificity to make a whole-case approval possible.
- **C021:** retain the 2015a/2016 bibliographic discrepancy. **C025/O004:** retain
  the channel-network-generation versus routing description discrepancy. Neither
  is repaired or converted automatically into an identity rejection.
- **C004/C018/C025:** separate subset boundaries remain explicit. Study co-location,
  shared names, or overlapping model assessments cannot supply a transitive union.
  C018's documented training/deployment distinctions remain unresolved at exact
  checkpoint/configuration granularity.

The narrow evidence check did not find a package integrity blocker. It is not an
exhaustive source-document review or approval of every proposed member. The case
flags and original model conflict/missing-information fields remain open.

## Future ontology/representation decision gate

These questions require researcher decisions **before canonical materialization**;
they are distinct from ordinary missing identity evidence:

1. **CFE classification and cross-class identity (C020/C041):** the saved cases use
   `ConceptualModel` and `ProcessBasedModel`. Whether any cross-class identity is
   permissible cannot be decided by a shared name, common superclass, matching test
   outputs, or this proposal. Preserve both historical classes and implementations.
2. **Model family versus release (C032/NWM):** decide how an eventual representation
   would preserve family-level references alongside v2.1/v3.0 referents. Unknown
   release evidence for O003/O005 is an evidence gap, not a mandate for an amendment.
3. **Architecture/family versus trained instance (C016/C018/C038):** determine whether
   the current representation can preserve genuinely different referent levels
   without losing training, ensemble, component, or deployment context. Shared
   LSTM/Transformer architecture is not trained-instance identity.
4. **Necessity of additional relations:** only if a later, explicitly approved
   representation requires family-to-instance or model-version links should the
   researcher decide whether an ontology change is necessary. v0.1.7
   `hasModelVersion` is `Repository` → `ModelVersion`, not a general model-version
   relation. This document neither proposes nor adds a new property. Existing
   dataset membership/derivation properties require explicit evidence and are not
   inferred from resource similarity, subset labels, or differing versions.

Missing deployment IDs, unspecified releases, weak module-list evidence (C036/O003),
or ambiguous submodule context (C023/O006) are ordinary evidence limitations. They
must remain unresolved without inventing an ontology amendment or scientific fact.
Any further approval must follow the existing append-only decision contract, preserve
all original assertions and model recommendations, and precede a separately
authorized canonical-materialization design. The original pilot ledger stays untouched;
batch 01 records its decisions separately under that contract.

## Focused offline validation

From the repository root in the existing `multigranular-kg` environment:

```bash
python -m src.evaluation.step14_identity_proposals_validation
```

For the focused batch-01 approval check, without repeating the full package audit:

```bash
python -m src.evaluation.step14_identity_proposals_validation --approvals-only
```

Batch-01 validation confirmed 29 approved subsets, 99 approved occurrences, and
133 remaining unapproved occurrences. Direct proposal/audit/recommendation hashes
were checked without repeating the full corpus authority audit. The original 43
case objects remain identical to the pre-approval proposal artifact; only top-level
attribution metadata changed. Focused checks:

```bash
python -m unittest tests.test_step14_identity_approvals tests.test_step14_semantic_identity_pilot tests.test_step14_identity_live -q
```

Result: 29 tests run, 28 passed, one optional real-projection audit skipped. No
provider calls, frozen-output edits, canonical allocations, or graph writes.

The validator reads only; it writes no output or ledger and blocks network
connections. It verifies pinned package/input/attempt bytes, reproduces local
recommendation validation from original raw text, checks every O/E binding and
case membership, accounts for all 232 occurrences, enforces the proposed subset
boundaries, and rejects approval/canonical-allocation fields. It validates
traceability and structure, **not scientific truth**. Rechecking after proposal
review verifies immutable input preservation. No full-corpus discovery, extraction,
provider call, adjudication, ontology edit, or KG/metric operation occurs.

Validation at preparation passed for all 43 cases, 232 occurrences, and 75 original
assessments. Eight in-memory negative checks rejected an unknown member, wrong
class, unknown evidence, altered model summary, approval flag, wrong audit hash,
union of the separate C025 subsets, and canonical allocation. All 350 files in
the saved live/v2 directory remained byte-identical before/after these checks.
The input-authority checks passed again, and only the new proposal documentation,
binding companion, and read-only validator belong to this change.
