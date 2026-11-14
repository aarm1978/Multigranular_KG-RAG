"""Proposed non-identity overlay on saved Step 14 previews; no production mappings."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import socket
from unittest.mock import patch
from src.evaluation import step14_automatic_acceptance_preview as baseline

r = baseline.r
require = baseline.require
ROOT = baseline.triage.BASE/'multigranular-preview'
PROPOSAL = Path('docs/study2_step14_multigranular_alignment_proposal.md')
SUPPORTED = {'Tool', 'MLModel', 'ProcessBasedModel', 'ConceptualModel', 'AgentBasedModel', 'DatasetResource'}


def normalized(value: str) -> str:
    """Reuse the original lexical normalization only for matching literal evidence."""
    return r.candidates.normalize(value)


def bases(endpoint: dict) -> set[str]:
    """Remove only a terminal explicit numeric version cue from saved names."""
    return {normalized(re.sub(r'\s+(?:(?:version|release)\s+v?|v)(\d+(?:\.\d+)*)$', '', name, flags=re.I))
            for name in endpoint.get('labels', []) if name.strip()}


def broader_support(left: dict, right: dict) -> dict:
    """Recognize narrow affirmative name/version or name/family quotations, not similarity."""
    if left['ontologyClass'] != right['ontologyClass'] or left['ontologyClass'] not in SUPPORTED:
        return dict(status='held', reason='incompatible_or_unsupported_class', links=[])
    endpoints = [left, right]
    names = set.union(*(bases(e) for e in endpoints))
    # Aliases are local to this comparison and require an explicit expansion in source text.
    aliases = {name:name for name in names}
    for long in sorted(names, key=lambda x:(-len(x),x)):
        for short in sorted(names):
            if len(short) >= len(long):
                continue
            if any(f'{long} ({short})' in normalized(q['literalExcerpt'])
                   for e in endpoints for q in e.get('selectedEvidence', [])):
                aliases[short] = long
    supported = []
    for endpoint in endpoints:
        matches = defaultdict(list)
        for name in sorted(bases(endpoint)):
            for i, quote in enumerate(endpoint.get('selectedEvidence', [])):
                text = normalized(quote['literalExcerpt'])
                # Hold uncertain/contrastive contexts rather than interpreting their semantics.
                if re.search(r'\b(not|unlike|different|may|might|could|versus|vs|trained|architecture|subset|derived|build|branch|deployment|commit)\b', text):
                    continue
                pattern = r'(?<!\w)' + re.escape(name) + r'(?:\s+\([a-z0-9 -]+\))?\s+(?:(?:version|release)\s+v?(\d+(?:\.\d+)*)\b|(?:model\s+|software\s+)?family\b)'
                for match in re.finditer(pattern, text):
                    matches[aliases[name]].append(dict(selectedEvidenceIndex=i, reference=quote['reference'],
                        literalExcerpt=quote['literalExcerpt'], qualifier=match[1] or 'family',
                        evidenceSha256=r.candidates.token(quote)))
        supported.append(matches)
    common = set(supported[0]) & set(supported[1])
    if len(common) != 1 or any(len(x) != 1 for x in supported):
        return dict(status='held', reason='no_unique_affirmative_shared_referent', links=[])
    name = next(iter(common))
    qualifiers = [{x['qualifier'] for x in support[name]} for support in supported]
    if any(len(q) != 1 for q in qualifiers) or all(q == {'family'} for q in qualifiers):
        return dict(status='held', reason='ambiguous_or_absent_narrower_realization', links=[])
    return dict(status='broader_candidate', reason='explicit_named_version_or_family_quotation',
        anchorDescriptor=dict(ontologyClass=left['ontologyClass'], literalName=name, granularity='named_family'),
        links=[dict(occurrenceID=e['occurrenceID'], evidence=supported[i][name],
                    relationIntent='family_anchor_identity_candidate' if qualifiers[i]=={'family'} else 'broader_correspondence_candidate') for i,e in enumerate(endpoints)])


def overlap_components(groups: list[dict]) -> list[dict]:
    """Find overlap components for diagnostics only; never use them as identity groups."""
    by_occurrence = defaultdict(set)
    for i, group in enumerate(groups):
        for oid in group['occurrenceIDs']:
            by_occurrence[oid].add(i)
    unseen = set(range(len(groups))); result = []
    while unseen:
        pending = [min(unseen)]; indices = set(); occurrences = set()
        while pending:
            i = pending.pop()
            if i not in unseen:
                continue
            unseen.remove(i); indices.add(i)
            for oid in groups[i]['occurrenceIDs']:
                if oid not in occurrences:
                    occurrences.add(oid); pending.extend(by_occurrence[oid] & unseen)
        result.append(dict(groupIDs=sorted(groups[i]['simulationID'] for i in indices),
            groups=len(indices), occurrences=len(occurrences),
            bridgeOccurrences=sorted(o for o in occurrences if len(by_occurrence[o])>1)))
    return sorted(result, key=lambda x:(-x['groups'],x['groupIDs']))


def overlay(pairs: dict, endpoints: dict, groups: list[dict]) -> tuple[list, list, dict]:
    """Retain individual proposals; incompatible descriptors hold only affected links."""
    exact = {k for g in groups if g['preOverlapState']==baseline.ACCEPTED for k in g['selectedPairKeys']}
    rows = []
    for key, pair in sorted(pairs.items()):
        left,right = (endpoints[x] for x in pair['occurrenceIDs'])
        support = broader_support(left,right)
        row = dict(pairKeySha256=key, occurrenceIDs=pair['occurrenceIDs'],
            ontologyClass=pair['ontologyClass'], familyCombination=pair['familyCombination'],
            identityScope=pair['identityScope'], exactCandidate=key in exact,
            broaderSupport=support, originalRecommendationReference=pair['recommendationReference'],
            originalBindingReference=pair['bindingReference'], status='held', simulationOnly=True)
        if support['status']=='broader_candidate':
            # This is a local hypothesis ID, not a globally merged family or allocated canonical ID.
            row['anchorHypothesisID']='hypothesis:'+key
        rows.append(row)
    descriptors = defaultdict(set)
    for row in rows:
        for link in row['broaderSupport']['links']:
            descriptors[link['occurrenceID']].add(r.candidates.token(row['broaderSupport']['anchorDescriptor']))
    links=[]
    for row in rows:
        support=row['broaderSupport']
        for link in support['links']:
            link['status']='held_incompatible_anchor_descriptors' if len(descriptors[link['occurrenceID']])>1 else ('proposed_family_anchor_support' if link['relationIntent']=='family_anchor_identity_candidate' else 'proposed_nonidentity_correspondence')
            links.append(dict(link,anchorHypothesisID=row['anchorHypothesisID'], anchorDescriptor=support['anchorDescriptor'], pairKeySha256=row['pairKeySha256']))
        if support['links'] and all(x['status'].startswith('proposed_') for x in support['links']):
            row['status']='broader_candidate'
        elif support['links']:
            row['status']='held_ambiguous_anchor_bridge'
        elif row['exactCandidate']:
            row['status']='exact_candidate'
    safe=[x for x in links if x['status'].startswith('proposed_')]
    summary=dict(pairCategories=dict(Counter(x['status'] for x in rows)),
        exactCandidateExplicitPairs=len(exact),
        classifiedPairUniqueOccurrences=len({o for x in rows if x['status'] in ('exact_candidate','broader_candidate') for o in x['occurrenceIDs']}),
        broaderUniqueOccurrences=len({x['occurrenceID'] for x in safe}),
        proposedNonidentityLinks=sum(x['relationIntent']=='broader_correspondence_candidate' for x in safe),
        familyAnchorSupportLinks=sum(x['relationIntent']=='family_anchor_identity_candidate' for x in safe), distinctAnchorHypotheses=len({x['anchorHypothesisID'] for x in safe}),
        incompatibleAnchorOccurrences=sorted(o for o,d in descriptors.items() if len(d)>1),
        strata=[dict(category=k[0],ontologyClass=k[1],families=list(k[2]),scope=k[3],pairs=v)
                for k,v in sorted(Counter((x['status'],x['ontologyClass'],tuple(x['familyCombination']),x['identityScope']) for x in rows).items())],
        identityDecisions=0, graphWrites=0, providerCalls=0)
    return rows,links,summary


def run(source: Path, output: Path) -> dict:
    """Read hash-pinned saved outputs without rerunning acceptance, retrieval or discovery."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(),'FRESH_OUTPUT_REQUIRED')
    pins={}
    def pin(path: Path, digest: str | None = None) -> None:
        """Verify consumed bytes, preserving historical provenance separately."""
        r.preflight.pilot.verify(path,digest or r.identity.sha(path),pins)
    pin(source/'manifest.json');manifest=r.load(source/'manifest.json')
    for name in ('summary.json','group-simulations.jsonl','prior-decisions.jsonl','oversized-inventory.jsonl'):
        pin(source/name,manifest['outputHashes'][name])
    triage=baseline.triage.ROOT/'v1'
    pin(triage/'manifest.json',manifest['inputHashes'][str(triage/'manifest.json')])
    tm=r.load(triage/'manifest.json')
    pair_path=triage/'pair-inventory.jsonl';pin(pair_path,tm['outputHashes'][pair_path.name])
    endpoint_path=baseline.triage.BASE/'unified-review-queue/v1/endpoint-provenance.jsonl'
    pin(endpoint_path,manifest['inputHashes'][str(endpoint_path)])
    for path in (PROPOSAL,Path(__file__).relative_to(Path.cwd()),Path('src/ontology/ontology_spec.yaml'),
                 Path('src/ontology/ciroh_ontology.owl')):
        pin(path, manifest['inputHashes'][str(path)] if str(path).startswith('src/ontology/') else None)
    pairs,_=baseline.triage.indexed(pair_path,'pairKeySha256')
    endpoints,_=baseline.triage.indexed(endpoint_path,'occurrenceID')
    groups=list(r.rows(source/'group-simulations.jsonl'))
    ordinary=[g for g in groups if g['occurrenceIDs']]
    eligible=[g for g in ordinary if g['preOverlapState']==baseline.ACCEPTED]
    old=r.load(source/'summary.json')
    require(len(eligible)==old['preOverlapAcceptedGroups'],'BASELINE_ELIGIBILITY_DRIFT')
    require(sum(g['state']==baseline.ACCEPTED for g in ordinary)==old['provisionalAcceptedGroups'],'BASELINE_FINAL_DRIFT')
    rows,links,summary=overlay(pairs,endpoints,eligible)
    summary['savedBaseline']={k:old[k] for k in ('candidateCompleteScopes','preOverlapAcceptedGroups','overlapBlockedGroups','provisionalAcceptedGroups','acceptedByRoute','explicitPairCoverage','preservedTriageAccounting')}
    summary['exactCandidateGroups']=len(eligible)
    summary['exactCandidateUniqueOccurrences']=len({o for g in eligible for o in g['occurrenceIDs']})
    summary['strictAnchorHypotheses']=len(eligible)
    summary['candidateCoveredUniqueOccurrences']=len({o for g in eligible for o in g['occurrenceIDs']} |
        {link['occurrenceID'] for link in links if link['status'].startswith('proposed_')})
    summary['strictGroupStrata']=baseline.distribution([dict(g,state='exact_candidate') for g in eligible], 'group')
    summary['oversizedScopesRetained']=sum(not g['occurrenceIDs'] for g in groups)
    components=overlap_components(eligible)
    summary['largestOverlapComponents']=components[:10]
    summary['overlapComponents']=len(components)
    for path,h in pins.items():r.preflight.pilot.verify(Path(path),h,{})
    output.mkdir(parents=True)
    for name,values in [('pair-overlay.jsonl',rows),('proposed-links.jsonl',links),
                        ('exact-candidate-groups.jsonl',eligible),('overlap-components.jsonl',components),
                        ('prior-decisions.jsonl',list(r.rows(source/'prior-decisions.jsonl'))),
                        ('oversized-inventory.jsonl',[g for g in groups if not g['occurrenceIDs']])]:
        with (output/name).open('x') as stream:
            for value in values:stream.write(r.identity.encoded(value).decode()+'\n')
    examples=[]
    for category in sorted({x['status'] for x in rows}):
        examples.extend([x for x in rows if x['status']==category][:3])
    r.write(output/'examples.json',dict(purposiveDevelopmentExamples=examples,confirmatorySample=False))
    r.write(output/'summary.json',summary)
    (output/'report.md').write_text('# PROPOSED multigranular overlay\n\n'+
        f"Baseline: {len(eligible)} eligible scopes before overlap; {old['provisionalAcceptedGroups']} disjoint scopes afterward. "
        'These are complete membership hypotheses, not unique occurrences or anchors.\n\n'+
        json.dumps({k:v for k,v in summary.items() if k not in ('savedBaseline','largestOverlapComponents','strata')},indent=2)+
        '\n\nFamily hypotheses are pair-local, not globally deduplicated scientific families. No connected-component identity is inferred. '
        'Literal family/version cues are conservative development evidence, pending researcher approval. Missing cues remain held; no substantial recovery is assumed. '
        'Original evidence bindings remain attached; quotations never transfer between versions. See the proposed design for metric definitions and the evaluation gate.\n')
    r.write(output/'manifest.json',dict(inputHashes=pins,outputHashes={p.name:r.identity.sha(p) for p in sorted(output.iterdir())},status='PROPOSED_ONLY',graphWrites=0,identityDecisions=0))
    return summary


def main() -> None:
    """Run only the offline overlay; require a fresh ignored output destination."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=baseline.ROOT/'v2-null-summary-fix')
    parser.add_argument('--output',type=Path,default=ROOT/'v1')
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        print(json.dumps(run(args.baseline,args.output),sort_keys=True))

if __name__=='__main__':main()
