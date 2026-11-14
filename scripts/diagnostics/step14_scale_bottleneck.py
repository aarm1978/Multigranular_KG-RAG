"""One-off saved-artifact Step 14 bottleneck diagnostic; never accepts alignments."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import signal
import socket
from unittest.mock import patch
from src.evaluation import step14_multigranular_preview as old

r=old.r
BASE=old.baseline.triage.BASE
OUTPUT=BASE/'scale-bottleneck-diagnostic/v1'


def component_shapes(groups: list[dict]) -> dict:
    """Classify overlapping sets using inverted membership; no induced identity pairs."""
    sets=[frozenset(g['occurrenceIDs']) for g in groups]
    postings=defaultdict(set)
    for i,members in enumerate(sets):
        for oid in members:postings[oid].add(i)
    duplicate=len(sets)-len(set(sets)); subset_pairs=0; has_partial=False
    for i,members in enumerate(sets):
        common=set.intersection(*(postings[o] for o in members))
        subset_pairs+=sum(len(sets[j])>len(members) for j in common)
        if not has_partial:
            neighbors=set.union(*(postings[o] for o in members))
            has_partial=any(not (members<=sets[j] or sets[j]<=members) for j in neighbors)
    return dict(groups=len(groups), distinctOccurrences=len(postings), duplicateScopes=duplicate,
        duplicateOriginalProposals=sum(max(0,len(g['originalGroupIDs'])-1) for g in groups),
        properSubsetSupersetPairs=subset_pairs, hasPartialOverlap=has_partial,
        maxOccurrenceDegree=max(map(len,postings.values()),default=0),
        highDegreeOccurrences=sum(len(v)>=10 for v in postings.values()),
        topBridges=[dict(occurrenceID=k,degree=len(v)) for k,v in sorted(postings.items(),key=lambda x:(-len(x[1]),x[0]))[:5]])


def endpoint_features(endpoint: dict, member: dict) -> dict:
    """Describe available literal evidence; cue flags are not semantic classifications."""
    text=' '.join(q['literalExcerpt'] for q in endpoint.get('selectedEvidence',[]))
    names={old.normalized(x) for x in endpoint.get('labels',[])}
    own={(d['scheme'],d['value']) for d in member.get('identifierDeclarations',[])
         if d.get('basis') in ('deterministic_entity_own_field','C-D04')}
    return dict(names=names,text=old.normalized(text),quote=bool(text.strip()),own=own,
        declarations=bool(member.get('identifierDeclarations')),
        version=bool(re.search(r'\b(?:version\s+|release\s+|v)\d',text,re.I)),
        context=bool(re.search(r'\b(?:model|software|framework|dataset|tool|simulation|version|implementation)\b',text,re.I)),
        relationCue=bool(re.search(r'\b(?:uses?|based on|derived|subset|trained|architecture|implementation|container|deployment)\b',text,re.I)))


def pair_flags(left: dict, right: dict, record: dict, status: str) -> list[str]:
    """Non-exclusive evidence/metadata observations, never a single-cause partition."""
    result=[]
    if left['quote'] and right['quote']:result.append('both_selected_quotations_available')
    else:result.append('selected_quotation_missing_one_or_both')
    if left['names'] & right['names']:
        result.append('exact_normalized_name_overlap')
        if not left['version'] and not right['version']:result.append('matching_names_without_explicit_version_cues')
    if left['version'] != right['version']:result.append('one_version_cue_one_unspecified')
    if left['own'] & right['own']:result.append('shared_entity_owned_identifier')
    if left['declarations'] or right['declarations']:result.append('identifier_declaration_available')
    if any(f'{long} ({short})' in left['text']+' '+right['text'] for long in left['names']|right['names']
           for short in left['names']|right['names'] if len(long)>len(short)):
        result.append('literal_alias_expansion_available')
    if left['relationCue'] or right['relationCue']:result.append('related_but_distinct_language_cue_not_judgment')
    assessment=record.get('assessment') or {}
    if assessment.get('missingInformation'):result.append('model_reports_missing_information')
    if assessment.get('conflictEvidenceIDs'):result.append('model_reports_conflict')
    if record['category']=='different_entities_candidate':result.append('model_negative_identity_candidate')
    if record['category'] in ('conceptual_similarity_only','shared_reference_target_only'):result.append('model_nonentity_relationship')
    if status=='held' and left['quote'] and right['quote']:
        result.append('quotations_present_detector_did_not_establish_broader_support')
    if not left['context'] or not right['context']:result.append('scientific_context_cues_sparse_not_proven_absent')
    if left['names'] & right['names'] and (assessment.get('conflictEvidenceIDs') or record['category']=='different_entities_candidate'):
        result.append('possible_homonym_or_specificity_conflict')
    return sorted(result)


def run(output: Path) -> dict:
    """Stream existing records and write only one compact ignored diagnostic package."""
    old.require(output.resolve().is_relative_to((BASE/'scale-bottleneck-diagnostic').resolve()) and not output.exists(),'FRESH_OUTPUT_REQUIRED')
    roots={'multi':BASE/'multigranular-preview/v2','auto':BASE/'automatic-acceptance-preview/v2-null-summary-fix',
           'triage':BASE/'adjudication-triage/v1','queue':BASE/'unified-review-queue/v1','members':BASE/'referent-groups/v1'}
    pins={}; manifests={}
    for label,root in roots.items():
        path=root/'manifest.json';r.preflight.pilot.verify(path,r.identity.sha(path),pins);manifests[label]=r.load(path)
    def consume(label: str, name: str) -> Path:
        """Verify the producer's exact output pin before consumption."""
        path=roots[label]/name;r.preflight.pilot.verify(path,manifests[label]['outputHashes'][name],pins);return path
    # Verify direct chain links where the saved downstream consumer records them.
    for label,manifest in manifests.items():
        for path,digest in manifest.get('inputHashes',{}).items():
            if path in pins:old.require(pins[path]==digest,'AUTHORITY_CHAIN_DRIFT')
    msummary=r.load(consume('multi','summary.json'));asummary=r.load(consume('auto','summary.json'))
    eligible={g['simulationID']:g for g in r.rows(consume('multi','exact-candidate-groups.jsonl'))}
    components=list(r.rows(consume('multi','overlap-components.jsonl')))
    anchors=list(r.rows(consume('multi','candidate-anchors.jsonl')))
    endpoints={e['occurrenceID']:e for e in r.rows(consume('queue','endpoint-provenance.jsonl'))}
    members={e['occurrenceID']:e for e in r.rows(consume('members','members.jsonl'))}
    features={oid:endpoint_features(e,members.get(oid,{})) for oid,e in endpoints.items()}
    all_ids=set();initial_ineligible=set();accepted=set();blocked=set();cross_accepted=set();cross_blocked=set();overs=[];ineligible_count=0
    by_state=defaultdict(set)
    for g in r.rows(consume('auto','group-simulations.jsonl')):
        ids=set(g['occurrenceIDs'])
        if not ids:overs.append(g);continue
        all_ids.update(ids);by_state[g['state']].update(ids)
        if g['preOverlapState']!=old.baseline.ACCEPTED:initial_ineligible.update(ids);ineligible_count+=1
        if g['state']==old.baseline.ACCEPTED:
            accepted.update(ids)
            if g['identityScope']=='between_families':cross_accepted.update(ids)
        if g['preOverlapState']==old.baseline.ACCEPTED and g['state']!=old.baseline.ACCEPTED:
            blocked.update(ids)
            if g['identityScope']=='between_families':cross_blocked.update(ids)
    eligible_ids={o for g in eligible.values() for o in g['occurrenceIDs']}
    component_rows=[];occ_component={};gid_component={}
    for ci,component in enumerate(components):
        gs=[eligible[k] for k in component['groupIDs']]
        shape=component_shapes(gs);ids={o for g in gs for o in g['occurrenceIDs']}
        for oid in ids:old.require(oid not in occ_component,'OVERLAPPING_COMPONENTS');occ_component[oid]=ci
        for gid in component['groupIDs']:gid_component[gid]=ci
        shape.update(componentIndex=ci,ontologyClasses=sorted({c for g in gs for c in g['ontologyClass']}),
            sourceFamilies=sorted({f for g in gs for f in g['familyCombination']}),
            originalComponentReference=dict(file=str(roots['multi']/'overlap-components.jsonl'),line=ci+1),internalExplicitPairStates=Counter())
        component_rows.append(shape)
    overlay={};broader=set();cross_held=set();pair_index={};flag_counts=defaultdict(Counter);flag_examples={};coverage=Counter()
    for row in r.rows(consume('multi','pair-overlay.jsonl')):
        overlay[row['pairKeySha256']]=(row['status'],row['broaderSupport']['reason'])
        if row['status']=='broader_candidate':broader.update(row['occurrenceIDs'])
    # Only small, bounded per-name selections for documented examples; no new candidate generation.
    examples={'NWM':{'nwm','national water model'},'LSTM':{'lstm','long short-term memory'},
              'NextGen':{'nextgen','nextgen framework'},'GEE':{'gee','google earth engine'}}
    example_ids={name:sorted([oid for oid,f in features.items() if f['names'] & labels]) for name,labels in examples.items()}
    case_candidates=[];case_keys=set();negative_internal=Counter();cross_held_ids=set();cross_all_ids=set();positive_internal=Counter()
    for record in r.rows(consume('triage','pair-inventory.jsonl')):
        key=record['pairKeySha256'];ids=record['occurrenceIDs'];status,reason=overlay[key]
        pair_index[tuple(ids)]=(key,status,record['category'])
        coverage[record['coverageState']]+=1
        left,right=(features[x] for x in ids)
        flags=pair_flags(left,right,record,status)
        if endpoints[ids[0]]['ontologyClass']!=endpoints[ids[1]]['ontologyClass']:flags.append('class_mismatch')
        cross=record['identityScope']=='between_families'
        if cross:cross_all_ids.update(ids)
        if cross and status=='held':cross_held_ids.update(ids)
        for scope in ['all_pairs']+(['held_pairs'] if status=='held' else [])+(['cross_family_pairs'] if cross else [])+(['cross_family_held_pairs'] if cross and status=='held' else []):
            flag_counts[scope].update(flags);flag_counts[scope]['pairs']+=1
        ci=occ_component.get(ids[0]);internal=ci is not None and ci==occ_component.get(ids[1])
        if internal:
            component_rows[ci]['internalExplicitPairStates'][record['category']]+=1
            if record['category']=='different_entities_candidate':negative_internal[ci]+=1
            if record['category']=='same_entity_candidate':positive_internal[ci]+=1
        # At most 30 cases: first stable example per scope/flag, plus major-component contradictions.
        tags=[('cross:' if cross else 'within:')+f for f in flags if f not in ('both_selected_quotations_available','identifier_declaration_available')]
        if internal and record['category']=='different_entities_candidate':tags.insert(0,'component_negative:'+str(ci))
        fresh=[tag for tag in tags if tag not in flag_examples]
        if fresh and len(case_candidates)<30 and key not in case_keys:
            for tag in fresh:flag_examples[tag]=key
            case_keys.add(key)
            case_candidates.append(dict(pairKeySha256=key,flags=flags,illustrates=fresh,identityScope=record['identityScope'],
                originalCategory=record['category'],coverageState=record['coverageState'],overlayStatus=status,detectorReason=reason,
                recommendationReference=record.get('recommendationReference'),bindingReference=record.get('bindingReference'),
                endpoints=[{field:endpoints[oid].get(field) for field in ('occurrenceID','ontologyClass','labels','sourceFamilies','versions','originalReference','selectedEvidence')} for oid in ids],
                interpretation=('Strict identity is a candidate hypothesis; missing granularity must be resolved.' if record['category']=='same_entity_candidate' else
                    'Related-but-distinct or broader correspondence requires affirmative referent evidence.' if record['category'] in ('conceptual_similarity_only','shared_reference_target_only') else
                    'Difference or abstention is a candidate interpretation; no automatic rejection.'),
                originalModelAssessment=record.get('assessment'),
                additionalEvidence='Source-grounded role, named referent, entity version and family/instance compatibility; recover full context through saved pointers.',
                componentIndex=ci if internal else None))
    old.require(dict(coverage)==asummary['explicitPairCoverage'],'PAIR_COUNT_DRIFT')
    old.require(len(overlay)==msummary['savedBaseline']['explicitPairCoverage']['validated_recommendation']+sum(v for k,v in coverage.items() if k!='validated_recommendation'),'OVERLAY_COUNT_DRIFT')
    eligible_pair_keys={k for g in eligible.values() for k in g['selectedPairKeys']}
    provisional_pair_keys={k for g in eligible.values() if g['state']==old.baseline.ACCEPTED for k in g['selectedPairKeys']}
    recall_checks={}
    for name,ids in example_ids.items():
        # Select up to three per exact source-family tuple, deterministic by original ID.
        strata=defaultdict(list)
        for oid in ids:strata[tuple(endpoints[oid]['sourceFamilies'])].append(oid)
        chosen=sorted({o for values in strata.values() for o in values[:3]})
        counts=Counter();checked=[]
        for i,a in enumerate(chosen):
            for b in chosen[i+1:]:
                if endpoints[a]['sourceFamilies']==endpoints[b]['sourceFamilies']:continue
                hit=pair_index.get(tuple(sorted([a,b])))
                state='absent_from_selected_inventory' if hit is None else 'present_'+hit[1]
                if hit and hit[0] in eligible_pair_keys and hit[0] not in provisional_pair_keys:
                    state='present_eligible_but_overlap_blocked'
                counts[state]+=1
                checked.append(dict(occurrenceIDs=[a,b],selectedPairKey=hit[0] if hit else None,state=state))
        recall_checks[name]=dict(indexedLabelOccurrences=len(ids),boundedCheckedOccurrences=len(chosen),counts=dict(counts),checks=checked,
            caveat='Label search is a bounded lookup of documented examples, not evidence of equivalence or candidate recall.')
    for row in component_rows:
        row['knownNegativeIdentityComparisons']=negative_internal[row['componentIndex']]
        row['mixedClass']=len(row['ontologyClasses'])>1
        row['internalExplicitPairStates']=dict(row['internalExplicitPairStates'])
    nonsingle=[c for c in component_rows if c['groups']>1]
    ceilings=dict(knownCandidateOccurrences=len(all_ids),provisionalOccurrences=len(accepted),
        initiallyIneligibleScopes=ineligible_count,initiallyIneligibleDistinctOccurrences=len(initial_ineligible),
        initiallyIneligibleBeyondEligible=len(initial_ineligible-eligible_ids),eligibleDistinctOccurrences=len(eligible_ids),
        blockedDistinctOccurrences=len(blocked),blockedBeyondProvisional=len(blocked-accepted),
        crossFamilyBlockedBeyondProvisional=len(cross_blocked-accepted),
        crossFamilyProvisionalOccurrences=len(cross_accepted),broaderOccurrences=len(broader),broaderBeyondEligible=len(broader-eligible_ids),
        allCandidatesBeyondProvisional=len(all_ids-accepted),crossFamilyHeldPairOccurrences=len(cross_held_ids),
        crossFamilyHeldBeyondProvisional=len(cross_held_ids-accepted),
        oversizedScopes=len(overs),oversizedMembershipSum=sum(x['memberCount'] for x in overs),
        oversizedDistinctOccurrences=None,oversizedIncrementalCoverage=None,
        caveat='Set ceilings over already selected candidates, not predicted matches or recall. Oversized membership lists are deliberately unavailable; their sum is not a distinct-occurrence count.')
    summary=dict(ceilings=ceilings,savedBaseline={k:asummary[k] for k in ('candidateCompleteScopes','preOverlapAcceptedGroups','overlapBlockedGroups','provisionalAcceptedGroups','provisionalAcceptedImpliedPairs','pilotApprovalSubsets','pilotDistinctApprovedOccurrences')},
        componentCount=len(component_rows),singletonComponents=sum(c['groups']==1 for c in component_rows),
        nonsingletonComponents=len(nonsingle),groupsInNonsingletonComponents=sum(c['groups'] for c in nonsingle),
        componentSizeDistribution=dict(sorted(Counter(c['groups'] for c in component_rows).items())),
        componentsWithSubsetRelations=sum(c['properSubsetSupersetPairs']>0 for c in component_rows),
        componentsWithPartialOverlap=sum(c['hasPartialOverlap'] for c in component_rows),
        duplicateScopeMemberships=sum(c['duplicateScopes'] for c in component_rows),
        duplicateOriginalProposals=sum(c['duplicateOriginalProposals'] for c in component_rows),
        componentsWithKnownNegativePairs=len(negative_internal),knownInternalNegativePairs=sum(negative_internal.values()),
        occurrencesInComponentsWithNegativePredictions=sum(c['distinctOccurrences'] for c in component_rows if c['knownNegativeIdentityComparisons']),
        highDegreeBridgeOccurrences=sum(c['highDegreeOccurrences'] for c in component_rows),
        occurrencesInPartialOverlapComponents=sum(c['distinctOccurrences'] for c in component_rows if c['hasPartialOverlap']),
        largestComponents=component_rows[:10],componentStrata=[dict(classes=list(k[0]),families=list(k[1]),components=v) for k,v in sorted(Counter((tuple(c['ontologyClasses']),tuple(c['sourceFamilies'])) for c in component_rows).items())],
        flags={k:dict(sorted(v.items())) for k,v in flag_counts.items()},boundedExampleChecks=recall_checks,
        broaderVersionCategories=msummary['versionComparisonCounts'],anchorHypotheses=len(anchors),
        existingProvisionalIdentityScopes=len([g for g in eligible.values() if g['state']==old.baseline.ACCEPTED]),
        actualProductionMappings=0,diagnosticCases=len(case_candidates),providerCalls=0,graphWrites=0)
    summary['top10Contribution']=dict(groups=sum(c['groups'] for c in component_rows[:10]),occurrences=sum(c['distinctOccurrences'] for c in component_rows[:10]))
    for path in (Path(__file__).relative_to(Path.cwd()),Path('docs/study2_step14_scale_bottleneck_diagnostic.md')):
        r.preflight.pilot.verify(path,r.identity.sha(path),pins)
    for manifest in manifests.values():
        for path,digest in manifest.get('inputHashes',{}).items():
            if path in pins:old.require(pins[path]==digest,'AUTHORITY_CHAIN_DRIFT')
    for path,h in pins.items():r.preflight.pilot.verify(Path(path),h,{})
    output.mkdir(parents=True)
    r.write(output/'summary.json',summary)
    r.write(output/'cases.json',dict(status='diagnostic_only_not_adjudication',cases=case_candidates))
    (output/'report.md').write_text(report(summary))
    r.write(output/'manifest.json',dict(inputHashes=pins,outputHashes={p.name:r.identity.sha(p) for p in sorted(output.iterdir())},providerCalls=0,graphWrites=0,identityDecisions=0))
    return summary


def report(s: dict) -> str:
    """Render one decision memo with explicit descriptive ceilings and a bounded proposal."""
    c=s['ceilings'];f=s['flags']['cross_family_held_pairs'];top=s['top10Contribution']
    return f'''# Step 14 scale bottleneck diagnostic — decision support only

## Measured bottleneck

{s['savedBaseline']['overlapBlockedGroups']:,} overlap-blocked scopes are represented by {s['nonsingletonComponents']} non-singleton reconciliation components, not that many independent human identity decisions. There are {s['singletonComponents']} singleton components. The ten largest contain {top['groups']:,} groups and {top['occurrences']:,} distinct occurrences. Components are diagnostic structures, never equivalence classes.

{s['componentsWithSubsetRelations']} components contain proper subset/superset relationships; {s['componentsWithPartialOverlap']} contain partial overlaps. There are {s['duplicateScopeMemberships']} exact duplicate scopes and {s['duplicateOriginalProposals']} redundant original proposals already folded into exact scopes. {s['componentsWithKnownNegativePairs']} components contain {s['knownInternalNegativePairs']} explicit negative model comparisons: these are incompatible *predictions*, not independently established contradictions. High occurrence degree describes bridge risk, not proof of ambiguity. Subset overlap is not authority to accept a superset.

## Coverage and headroom

| Unit or population | Count |
|---|---:|
| Existing disjoint provisional groups | {s['savedBaseline']['provisionalAcceptedGroups']} |
| Their distinct occurrences | {c['provisionalOccurrences']} |
| Pre-overlap eligible distinct occurrences | {c['eligibleDistinctOccurrences']} |
| Blocked occurrences beyond current provisional coverage | {c['blockedBeyondProvisional']} |
| Between-family blocked occurrences beyond current provisional coverage | {c['crossFamilyBlockedBeyondProvisional']} |
| Initially ineligible complete scopes | {c['initiallyIneligibleScopes']} |
| Distinct occurrences in those scopes | {c['initiallyIneligibleDistinctOccurrences']} |
| Ineligible occurrences outside pre-overlap eligibility | {c['initiallyIneligibleBeyondEligible']} |
| Known candidate occurrences beyond current provisional coverage | {c['allCandidatesBeyondProvisional']} |
| Broader covered occurrences / beyond strict eligibility | {c['broaderOccurrences']} / {c['broaderBeyondEligible']} |
| Candidate anchor hypotheses | {s['anchorHypotheses']} |
| Oversized scopes / summed memberships | {c['oversizedScopes']} / {c['oversizedMembershipSum']} |

All additional counts are mechanical candidate ceilings, **not expected true matches, validated recovery or recall**. The oversized distinct and incremental ceilings are unknown; no membership expansion was performed. The 29 exact historical approval subsets remain separate from provisional scopes and are never propagated. No actual canonical mapping is created.

## Why the broader detector stalls

{f['pairs']:,} held between-family pairs include {f.get('both_selected_quotations_available',0):,} with selected quotations on both endpoints; {f.get('matching_names_without_explicit_version_cues',0):,} have exact normalized name overlap without explicit version cues. {f.get('literal_alias_expansion_available',0):,} have literal name-expansion patterns. {f.get('model_reports_missing_information',0):,} carry model-reported missing information; {f.get('model_reports_conflict',0):,} carry conflict evidence. These flags overlap and must not be summed as a causal partition. Missing a selected quote is not proof that the full source lacks evidence. Conversely, quotation availability is not proof of identity or family membership. Related-language and homonym flags are diagnostic cues only.

The grammar's failure to establish a relationship despite available text is separable from absent text, but this diagnostic does not relabel that text as sufficient semantic evidence. Detailed flags and bounded named-example selected-pair lookups are in summary.json. Absent selected combinations do not measure candidate recall: no all-corpus gold referent inventory exists, and no unselected universe was generated. The bounded lookup distinguishes present-but-overlap-blocked from other present candidates. The capped examples are illustrative, not evaluation labels.

## Decision between paths

**A — one deterministic reconciliation:** implementation-only deduplication/subset accounting could shrink the presentation burden. Its absolute additional occurrence ceiling is {c['blockedBeyondProvisional']} ({c['crossFamilyBlockedBeyondProvisional']} between-family), but no positive semantic gain is established by this count. Known conflicting predictions and partial overlaps preclude automatic component union. Workload: one bounded offline component ledger pass, zero provider calls; compatible full memberships would still need an acceptance rule and independent evaluation. Meaningful gain means fewer distinct decision units with preserved coverage/provenance, not merely fewer rows.

**B — bounded anchor-centric disambiguation pilot (recommended as a proposal, not authorized execution):** choose at most 12 distinct non-singleton component/referent units, with six between-family, three same-family across-artifact, and three conflict/ambiguity units where available. Deduplicate units across strata, sort by incremental occurrence coverage then stable component ID; cap each unit at 12 source occurrences and the entire pilot at 120. Review complete small components where possible; larger components use an explicitly incomplete anchored subset and cannot receive a whole-component conclusion. Do not produce a model-ready sample in this diagnostic. Maximum new coverage in this pilot is 120 distinct occurrences (at most 72 in the six cross-family slots); actual incremental coverage may be lower. The opportunity pool ceiling is {c['blockedBeyondProvisional']} blocked occurrences, not a forecast of pilot yield. Existing selected evidence is reusable, but version/source roles and homonyms remain scientific risks.

Propose at most 12 model requests, no automatic retries or expansion. Require structured candidate referents, exact occurrence membership, identity versus broader/related-distinct granularity, source-bound supporting/conflicting evidence IDs, explicit abstentions and unassessed members. Verify evidence bindings separately from semantics; verification is not semantic validation. LLM output is not gold or approval. Budget 2–4 hours for bounded developer/researcher inspection, explicitly nonconfirmatory, plus the already planned independent one-time 60/80/100-judgment evaluation after policy/frame freeze. Costs/tokens cannot be estimated defensibly before evidence packaging; do not authorize another 74,051-pair run.

Predeclare a pilot continuation threshold before selection: for example at least 20 previously uncovered occurrences across at least four coherent referent units, including at least two between-family units, with no unresolved incompatible memberships in each proposed set. This is a proposed decision criterion, not validated accuracy or a new acceptance policy. Stop after the fixed pilot even if it fails; do not tune and repeat. Any promising result still requires policy approval and independent probabilistic, model-blind evaluation.

**C — conservative closure:** zero additional accepted coverage by design, zero new provider work. Retain the {s['savedBaseline']['provisionalAcceptedGroups']} disjoint provisional scopes and all holds, complete the existing ontology/representation and independent evaluation gates, then separately authorize canonicalization. No claim of exhaustive identity resolution. This remains the fallback if B is not authorized or does not meet its predeclared criterion.

**Recommended next action:** researcher decision on the one fixed B pilot, using components as bounded evidence packages rather than entities. Do not implement it here. **Stopping condition:** one pilot only; without a meaningful predefined coverage gain and defensible memberships, retain unresolved cases and pursue conservative closure. The ontology amendment itself cannot repair missing referent evidence.
'''


def main() -> None:
    """Bound local diagnostic execution; timeouts publish no output directory."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--time-limit',type=int,default=25);args=parser.parse_args()
    def timeout(signum: int, frame: object) -> None:
        """Abort rather than consume an unbounded shell interval."""
        raise TimeoutError('Diagnostic exceeded time limit; rerun locally with --time-limit 0')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(args.time_limit)
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        result=run(args.output)
    signal.alarm(0)
    print(json.dumps({k:result[k] for k in ('ceilings','nonsingletonComponents','componentsWithKnownNegativePairs','top10Contribution')},sort_keys=True))

if __name__=='__main__':main()
