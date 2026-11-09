"""Prepare a bounded evidence-bound Step 14 review batch; never adjudicate identity."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import socket
from unittest.mock import patch

from src.evaluation import step14_retrieval_reconciliation as reconciliation

retrieval = reconciliation.retrieval
require = retrieval.require
VERSION = 'step14-evidence-review-batch/0.1.0'
SOURCE = reconciliation.OUTPUT
ROOT = Path('var/study2_step14/evidence-review-batch01')
CONTRACT = Path('docs/study2_step14_evidence_review_batch_v0.1.md')
# Retrieval-priority stopwords only; never aliases, ontology changes or identity rules.
GENERIC = set('a an the of for and or in on with by to from using based model models tool tools algorithm algorithms workflow workflows system systems software method methods framework frameworks data network networks learning deep computational process conceptual statistical agent'.split())
POOL_LIMIT = 64


def words(text: str) -> set[str]:
    """Tokenize original names for priority only, without generating aliases."""
    return set(re.findall(r'[^\W_]+',text.casefold()))


def name_tokens(row: dict) -> set[str]:
    """Retain non-generic name tokens of at least three characters."""
    return {w for label in row['labels'] for w in words(label) if len(w)>=3 and w not in GENERIC}


def context(row: dict) -> bool:
    """Mechanical actionability: a literal label plus context beyond its words."""
    label_words=set().union(*(words(s) for s in row['labels']))
    return any(e['labelPresent'] and len(words(e['literalExcerpt'])-label_words-GENERIC)>=3
               for e in row['selectedEvidence'])


def features(pair: dict, occurrences: dict, frequencies: Counter) -> dict:
    """Rank review utility, not probability of identity or semantic correctness."""
    left,right=(occurrences[x] for x in pair['occurrenceIDs'])
    shared=name_tokens(left)&name_tokens(right)
    cross=[]
    for row,other in ((left,right),(right,left)):
        for label in other['labels']:
            if name_tokens(dict(labels=[label])) and any(label.casefold() in e['literalExcerpt'].casefold() for e in row['selectedEvidence']):
                cross.append(label)
    named_cue=bool(shared or cross)
    contextual=context(left) and context(right)
    lf,rf=left['granularity'],right['granularity']
    unknown=lambda value:any(term in value.casefold() for term in ('unspecified','unknown','unresolved'))
    granularity=('unspecified_requires_review' if unknown(lf) or unknown(rf) else
                 'matching_recorded_granularity_requires_review' if lf==rf else 'different_recorded_granularity')
    version_diff=bool(left['versions'] and right['versions'] and left['versions']!=right['versions'])
    quotes_left={e['fullQuoteSha256'] for e in left['selectedEvidence']}
    quotes_right={e['fullQuoteSha256'] for e in right['selectedEvidence']}
    shared_quotes=sorted(quotes_left&quotes_right)
    scores={v:sum(d['nomination']['scores'][v] for d in pair['directions'])/len(pair['directions']) for v in retrieval.VIEWS}
    rarity=sum(math.log((len(occurrences)+1)/(frequencies[w]+1)) for w in sorted(shared))
    # This cue identifies only review-batch repetition, never an entity or grouping.
    cue=min(shared,key=lambda w:(frequencies[w],w)) if shared else '|'.join(sorted(set(s.casefold() for s in cross)))
    priority=[int(not version_diff and granularity!='different_recorded_granularity'),
              int(bool(shared)),int(granularity=='matching_recorded_granularity_requires_review'),
              rarity,int(not shared_quotes),int(set(pair['nominationViews'])==set(retrieval.VIEWS)),
              min(scores.values()),int(len(pair['directions'])==2)]
    return dict(actionable=named_cue and contextual, literalNamedCue=named_cue,
        contextualEvidenceBoth=contextual,sharedNameTokens=sorted(shared),crossLabelLiteralMentions=sorted(set(cross)),
        labelCueForDiversityOnly=cue,recordedGranularityAssessment=granularity,
        recordedVersionMetadataDiffers=version_diff,sharedFullQuoteHashes=shared_quotes,
        meanViewScores=scores,priorityVector=priority,
        caveat='Literal cross-mentions may compare distinct entities; shared quotes are not independent corroboration.')


def rank(item: dict) -> tuple:
    """Use deterministic descending utility, then stable pair hash."""
    return (*(-x for x in item['selectionFeatures']['priorityVector']),item['pairKeySha256'])


def retain(pool: dict, item: dict) -> None:
    """Bound each scope/class/family pool and prevent one repeated cue dominating it."""
    cue=item['selectionFeatures']['labelCueForDiversityOnly']
    old=pool.get(cue)
    if old is not None and rank(old)<=rank(item):return
    pool[cue]=item
    if len(pool)>POOL_LIMIT:
        worst=max(pool,key=lambda k:rank(pool[k]));del pool[worst]


def select_stream(source: Path, occurrences: dict, expected: dict, per_scope: int) -> tuple[list,list,dict]:
    """Stream existing pair records once; no new retrieval or transitive clustering."""
    frequencies=Counter(w for row in occurrences.values() for w in name_tokens(row))
    pools=defaultdict(dict); anchors=defaultdict(dict); counts=Counter(); status_counts=Counter(); scope_counts=Counter()
    digest=hashlib.sha256(); previous=None
    with source.open('rb') as stream:
        for line,raw in enumerate(stream,1):
            digest.update(raw); pair=json.loads(raw); ids=pair['occurrenceIDs']
            require(len(ids)==2 and ids==sorted(set(ids)) and all(x in occurrences for x in ids),'PAIR_MEMBERSHIP_DRIFT')
            require(previous is None or tuple(ids)>previous,'PAIR_ORDER_OR_DUPLICATE_DRIFT');previous=tuple(ids)
            require(pair['pairKeySha256']==retrieval.candidates.token(ids),'PAIR_HASH_DRIFT')
            counts['pairs']+=1;status_counts[pair['review']['primary']]+=1;scope_counts[pair['scope']]+=1
            new=pair['review']['newPair'];approved=bool(pair['review']['sharedMemberships']['approved'])
            if not new and not approved:continue
            f=features(pair,occurrences,frequencies)
            if new:
                counts['newPairs']+=1
                counts['newWithLiteralNamedCue']+=int(f['literalNamedCue'])
                counts['newWithContextBoth']+=int(f['contextualEvidenceBoth'])
                if not f['actionable']:continue
                counts['newMeetingReviewPriorityConditions']+=1
            item=dict(pair,selectionFeatures=f,pairReference=dict(file=str(source),line=line,
                      rawLineSha256=hashlib.sha256(raw).hexdigest(),recordSha256=retrieval.candidates.token(pair)))
            key=(pair['scope'],pair['ontologyClass'],pair['sourceFamilyPair'])
            if new:retain(pools[key],item)
            elif approved:retain(anchors[key],item)
    require(digest.hexdigest()==expected['pairsSha256'],'PAIR_FILE_HASH_DRIFT')
    require(counts['pairs']==expected['summary']['uniqueUnorderedPairs'],'PAIR_COUNT_DRIFT')
    require(dict(status_counts)==expected['summary']['counts']['reviewStatus'],'REVIEW_COUNT_DRIFT')
    require(dict(scope_counts)==expected['summary']['counts']['scope'],'SCOPE_COUNT_DRIFT')
    selected=[]
    for scope in retrieval.SCOPES:
        available=sorted((p for key,values in pools.items() if key[0]==scope for p in values.values()),key=rank)
        used_ids=set();used_cues=set()
        for item in available:
            cue=item['selectionFeatures']['labelCueForDiversityOnly']
            if used_ids.intersection(item['occurrenceIDs']) or cue in used_cues:continue
            selected.append(item);used_ids.update(item['occurrenceIDs']);used_cues.add(cue)
            if sum(x['scope']==scope for x in selected)==per_scope:break
    chosen_anchors=[];used_decisions=set()
    for scope in retrieval.SCOPES:
        available=sorted((p for key,values in anchors.items() if key[0]==scope for p in values.values()),key=rank)
        for item in available:
            decisions=set(item['review']['sharedMemberships']['approved'])
            if decisions&used_decisions:continue
            chosen_anchors.append(item);used_decisions.update(decisions);break
    counts['selectedNewCases']=len(selected);counts['separateApprovedAnchors']=len(chosen_anchors)
    counts['unselectedNewPairsNotRejected']=counts['newPairs']-len(selected)
    return selected,chosen_anchors,dict(counts)


def enrich(items: list[dict], occurrences: dict) -> dict:
    """Recover only selected original evidence records, keeping offsets and hashes."""
    needed={oid for item in items for oid in item['occurrenceIDs']}; result={}
    for line,original in enumerate(retrieval.rows(retrieval.preflight.review.INPUT/'occurrences.jsonl'),1):
        oid=original['occurrenceID']
        if oid not in needed:continue
        projection=occurrences[oid]; ref=projection['originalReference']
        require(line==ref['line'] and retrieval.candidates.token(original)==ref['recordSha256'],'ORIGINAL_OCCURRENCE_DRIFT')
        endpoint=reconciliation.compact_endpoint(projection)
        endpoint['nativeProvenanceReference']=dict(ref,jsonPointer='/nativeReferences')
        endpoint['evidenceSources']=[]
        for fragment in projection['selectedEvidence']:
            index=int(fragment['reference']['jsonPointer'].rsplit('/',1)[1]); evidence=original['evidenceReferences'][index]
            quote=evidence['evidenceText']
            require(retrieval.candidates.token(evidence)==fragment['reference']['evidenceRecordSha256'],'EVIDENCE_RECORD_DRIFT')
            require(retrieval.digest(quote)==fragment['fullQuoteSha256'] and quote[fragment['quoteStart']:fragment['quoteEnd']]==fragment['literalExcerpt'],'EVIDENCE_OFFSET_DRIFT')
            endpoint['evidenceSources'].append(dict(evidencePointer=fragment['reference']['jsonPointer'],
                originalSourceMetadata={k:v for k,v in evidence.items() if k!='evidenceText'}))
        result[oid]=endpoint
    require(set(result)==needed,'MISSING_ORIGINAL_EVIDENCE')
    return result


def package_cases(items: list[dict], endpoints: dict, anchors: bool=False, approvals: dict | None=None) -> list:
    """Make pair-specific questions without turning candidates or anchors into new decisions."""
    output=[]
    for number,item in enumerate(items,1):
        ids=item['occurrenceIDs']; left,right=(endpoints[x] for x in ids)
        case=dict(item,caseID=('ANCHOR-' if anchors else 'REVIEW-')+f'{number:02d}',
            endpoints=[left,right],decisionStatus='existing_approval_anchor_no_new_judgment' if anchors else 'unreviewed',
            decisionAuthority=None,canonicalID=None)
        if anchors:
            case['originalApprovals']=[approvals[x] for x in item['review']['sharedMemberships']['approved']]
            case['identityQuestion']='Diagnostic anchor only: inspect the recorded approval at its original exact membership and granularity. No reinterpretation or new approval is requested.'
        else:
            case['identityQuestion']=(f"Do {left['labels']!r} and {right['labels']!r} denote the same {item['ontologyClass']} scientific referent at an explicitly compatible granularity, or only related concepts/reference targets, distinct entities, or unresolved referents? Identify the supporting and conflicting literal evidence; preserve family, release, implementation and instance distinctions.")
            case['selectionReason']='Literal named-reference cue and contextual evidence at both endpoints; recorded granularity/version compatibility considered before complementary scores and reciprocity. Selection is not a semantic judgment.'
        output.append(case)
    return output


def run(output: Path, per_scope: int=11) -> dict:
    """Consume completed reconciliation under its pins and write a fresh review package."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(),'FRESH_OUTPUT_REQUIRED')
    require(10<=per_scope<=12,'CASES_PER_SCOPE_MUST_BE_10_TO_12')
    manifest=retrieval.load(SOURCE/'manifest.json'); pins=dict(manifest['inputHashes'])
    require(manifest['version']==reconciliation.VERSION,'RECONCILIATION_VERSION_DRIFT')
    require(retrieval.identity.sha(Path(reconciliation.__file__))==manifest['implementationSha256'],'RECONCILIATION_IMPLEMENTATION_DRIFT')
    for name,h in manifest['outputHashes'].items():pins[str(SOURCE/name)]=h
    for path in (SOURCE/'manifest.json',CONTRACT):pins[str(path)]=retrieval.identity.sha(path)
    for path,h in pins.items():retrieval.preflight.pilot.verify(Path(path),h,{})
    summary=retrieval.load(SOURCE/'summary.json')
    occurrences=reconciliation.load_occurrences(reconciliation.PREPARED)
    selected,anchors,counts=select_stream(SOURCE/'pairs.jsonl',occurrences,
        dict(pairsSha256=manifest['outputHashes']['pairs.jsonl'],summary=summary),per_scope)
    # Recheck full original directional bindings and exact prior memberships for every selected pair.
    for item in selected+anchors:
        left,right=(occurrences[x] for x in item['occurrenceIDs'])
        require(item['review']==reconciliation.review_status(left,right),'PRIOR_STATUS_DRIFT')
        for direction in item['directions']:reconciliation.validate_nomination(direction['nomination'],occurrences)
    endpoints=enrich(selected+anchors,occurrences)
    approvals={}
    for line,record in enumerate(retrieval.rows(retrieval.preflight.approvals.APPROVALS),1):
        approvals[record['decisionID']]=dict(originalRecord=record,reference=dict(file=str(retrieval.preflight.approvals.APPROVALS),line=line,recordSha256=retrieval.candidates.token(record)))
    cases=package_cases(selected,endpoints); anchor_cases=package_cases(anchors,endpoints,True,approvals)
    for path,h in pins.items():retrieval.preflight.pilot.verify(Path(path),h,{})
    output.mkdir(parents=True)
    retrieval.write(output/'cases.json',dict(version=VERSION,cases=cases))
    retrieval.write(output/'anchors.json',dict(version=VERSION,anchors=anchor_cases))
    result=dict(version=VERSION,counts=counts,targetNewCases=per_scope*3,
        selectedByScope={s:sum(c['scope']==s for c in cases) for s in retrieval.SCOPES},
        selectedByClass=dict(Counter(c['ontologyClass'] for c in cases)),
        selectedByFamilyPair=dict(Counter(c['sourceFamilyPair'] for c in cases)),
        newIdentityDecisions=0,graphWrites=0,
        limitations=['Post-retrieval utility-ranked selection, not a calibrated precision ranking or population accuracy sample.',
            'The earlier 24-case diversity diagnostic does not estimate alignment accuracy.',
            'Literal named cues, shared quotes, reciprocity and scores do not establish identity; full context may show comparison or distinct implementations.',
            'Unknown granularity/version remains unresolved; no new ontology or identity authority is introduced.',
            'At most 64 distinct lexical cues per scope/class/family pool, one selected cue and no reused endpoint per scope; unselected pairs remain unchanged and are not rejected.'])
    retrieval.write(output/'summary.json',result)
    lines=['# First evidence-bound retrieval identity review batch','',
           f"New review cases: {len(cases)} (target {per_scope*3}); separate existing-approval anchors: {len(anchor_cases)}.",
           'All new cases are unreviewed. Pair case IDs are bookkeeping, not canonical identities.','',
           *result['limitations'],'']
    for case in cases+anchor_cases:
        lines += [f"## {case['caseID']} — {case['scope']} / {case['ontologyClass']}",'',case['identityQuestion'],'',
                  f"Prior status: {case['review']['primary']}; pair key: `{case['pairKeySha256']}`.",
                  'Scores (name/evidence): '+str(case['selectionFeatures']['meanViewScores']),
                  'Granularity/version flags: '+str({k:case['selectionFeatures'][k] for k in ('recordedGranularityAssessment','recordedVersionMetadataDiffers')}),'']
        for endpoint in case['endpoints']:
            lines += [f"- `{endpoint['occurrenceID']}` — {endpoint['labels']!r}; source artifacts: {endpoint['sourceArtifacts']!r}",
                      f"  Original evidence reference: `{endpoint['originalReference']['file']}` line {endpoint['originalReference']['line']} (SHA-256 `{endpoint['originalReference']['recordSha256']}`)."]
            for e in endpoint['selectedEvidence']:
                lines += ['',*('> '+line for line in e['literalExcerpt'].splitlines()),'']
        if 'originalApprovals' in case:lines+=['Original approval IDs: '+', '.join(a['originalRecord']['decisionID'] for a in case['originalApprovals']),'']
    (output/'review.md').write_text('\n'.join(lines)+'\n')
    (output/'summary.md').write_text('# Review batch summary\n\n'
        +f"{len(cases)} new unreviewed pair cases; {len(anchor_cases)} separate existing-approval anchors.\n\n"
        +'| Scope | New cases |\n|---|---:|\n'
        +''.join(f"| {scope} | {count} |\n" for scope,count in result['selectedByScope'].items())
        +'\nSelection accounting: '+json.dumps(counts,sort_keys=True)+'\n\n'
        +'\n\n'.join(result['limitations'])+'\n')
    retrieval.write(output/'manifest.json',dict(version=VERSION,inputHashes=pins,
        implementationSha256=retrieval.identity.sha(Path(__file__)),
        outputHashes={p.name:retrieval.identity.sha(p) for p in sorted(output.iterdir())},providerCalls=0))
    return result


def main() -> None:
    """Execute offline only, using existing artifacts and no providers."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'v1')
    parser.add_argument('--cases-per-scope',type=int,default=11);args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
        print(json.dumps(run(args.output,args.cases_per_scope),sort_keys=True))


if __name__=='__main__':main()
