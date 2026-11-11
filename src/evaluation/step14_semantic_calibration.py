"""Prospective instruction-only calibration; immutable baseline and separately gated stages."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import socket
import sqlite3
from unittest.mock import patch
from src.evaluation import step14_queue_compatibility_pilot as p

r=p.r
live=p.live
require=p.require
BASE=p.ROOT/'v2'
BASE_PIN='aee87a85c1b12315c3c8a5b7a4933b33972ad589074683f0b1328575ec19b3de'
ROOT=Path('var/study2_step14/semantic-calibration')
VERSION='step14-semantic-calibration/0.1.0'
CONTRACT=Path('docs/study2_step14_semantic_calibration_v0.1.md')
CLARIFICATION='''
Prospective semantic clarification:
Distinguish a named scientific referent at family/framework/technique granularity from a specific release, implementation, dataset subset or trained instance.
A distinctive name or acronym plus discriminating technical, functional, ownership or project context may support same_entity_candidate at the granularity actually denoted by both occurrences. Independent corroboration of every technical attribute is not required.
Identical or mirrored quotations are not independent confirmations. Their lack of independence is not itself grounds for abstention when the named referent and compatible granularity are otherwise adequately established.
Different described functions may be complementary facets of one tool or model. Recommend different_entities_candidate only with positive evidence of incompatible referents, not merely different descriptive emphases.
Never discard an explicit version, implementation, trained-instance or dataset-subset distinction to manufacture a family-level match. Unspecified specificity is unknown, not permission to merge.
Preserve source-versus-reference roles, mentions-versus-uses distinctions, ontology-class compatibility, non-transitivity and evidence-grounded abstention.
Use no external knowledge, browsing or case-specific rules. This clarification does not authorize indiscriminate reduction of evidence requirements.
'''


def variant(body: dict) -> dict:
    """Change exactly the semantic instructions and preserve all provider settings."""
    result=deepcopy(body);result['instructions']=body['instructions']+'\n'+CLARIFICATION
    return result


def comparable(original: dict, prospective: dict) -> None:
    """Fail unless matched requests differ only by the approved instruction suffix."""
    require(variant(original)==prospective,'ARM_COMPARABILITY_DRIFT')


def select_held(metadata: list, excluded: set) -> list:
    """Freeze hash-selected strata and ambiguity cues; never use model outcomes."""
    rows=sorted((x for x in metadata if x['unitID'] not in excluded),key=lambda x:r.candidates.token(['held-out/0.1',x['unitID']]))
    require(len(rows)>=16,'INSUFFICIENT_HELD_UNITS')
    strata=defaultdict(list)
    for row in rows:
        tags=set(row['tags']);scope='cross_family' if 'cross_family' in tags else 'within_family'
        density='sparse' if 'sparse' in tags else 'dense' if 'dense' in tags else 'medium'
        strata[(scope,density)].append(row)
    selected=[]
    for key in sorted(strata):selected.append(dict(strata[key][0],selectionReason='hash_minimum:'+':'.join(key)))
    for tag in ('recorded_specificity_difference','instance_language','generic_name_risk'):
        candidates=[x for x in rows if tag in x['tags'] and x['unitID'] not in {s['unitID'] for s in selected}]
        if candidates:selected.append(dict(candidates[0],selectionReason='hash_minimum:'+tag))
    for row in rows:
        if len(selected)==16:break
        if row['unitID'] not in {s['unitID'] for s in selected}:selected.append(dict(row,selectionReason='hash_fill'))
    require(len({x['unitID'] for x in selected})==16 and not ({x['unitID'] for x in selected}&excluded),'HELD_SELECTION_DRIFT')
    return selected


def result(folder: Path, body: dict) -> tuple[dict,dict | None]:
    """Read and verify authentic receipts without finalizing or mutating historical outcomes."""
    if not folder.exists():return dict(status='not_dispatched'),None
    intent=live.load(folder/'intent.json');require(intent['requestBodySha256']==live.token(body),'INTENT_DRIFT')
    if not (folder/'outcome.json').exists():return dict(status='interrupted_requires_resume',usage=None),None
    outcome=live.load(folder/'outcome.json')
    for name,h in outcome['artifactHashes'].items():r.preflight.pilot.verify(folder/name,h,{})
    if outcome['status']!='validated_recommendation_only':return outcome,None
    response=live.load(folder/'response.json')
    raw=live.provider.extract_model_output(response)
    require(raw==(folder/'model-output.txt').read_bytes(),'AUTHENTIC_OUTPUT_DRIFT')
    value=json.loads(raw);require(value==live.load(folder/'validated.json'),'VALIDATED_OUTPUT_DRIFT')
    p.validate(value,body)
    return outcome,value


def prepare(root: Path) -> dict:
    """Freeze development and both held-out arms before any prospective response."""
    require(root.resolve().is_relative_to(ROOT.resolve()) and not root.exists(),'FRESH_OUTPUT_REQUIRED')
    pins={};r.preflight.pilot.verify(BASE/'manifest.json',BASE_PIN,pins);baseline=p.verify(BASE)
    require(len(baseline['cases'])==16 and sum(x['pairs'] for x in baseline['cases'])==83,'BASELINE_COVERAGE_DRIFT')
    for path in BASE.rglob('*'):
        if path.is_file() and path.name!='.execution.lock':pins[str(path)]=r.identity.sha(path)
    for path in (Path(__file__),Path(p.__file__),Path(live.__file__),Path(live.provider.__file__),p.SCHEMA,CONTRACT,
                 Path('docs/study2_step14_identity_granularity_adjudication_v0.1.md')):
        pins[str(path)]=r.identity.sha(path)
    r.preflight.pilot.verify(p.SOURCE/'manifest.json',p.SOURCE_SHA,pins)
    qm=live.load(p.SOURCE/'manifest.json')
    for name in ('coverage.sqlite','contexts.jsonl','unit-bindings.jsonl','endpoint-provenance.jsonl'):
        r.preflight.pilot.verify(p.SOURCE/name,qm['outputHashes'][name],pins)
    development=[];base_pairs=set()
    for entry in baseline['cases']:
        cid=entry['caseID'];body=live.load(BASE/'requests'/f'{cid}.json');audit=live.load(BASE/'audit'/f'{cid}.json')
        status,value=result(BASE/'attempts'/cid,body)
        require(value is not None,'BASELINE_NOT_VALIDATED')
        require(body['instructions']==p.PROMPT,'BASELINE_INSTRUCTIONS_DRIFT')
        development.append(dict(entry,stage='development',baselineRequest=str(BASE/'requests'/f'{cid}.json'),baselineAttempt=str(BASE/'attempts'/cid)))
        base_pairs.update(x['pairKeySha256'] for x in audit['pairRecords'])
    require(len(base_pairs)==83,'BASELINE_PAIR_DUPLICATION')
    with sqlite3.connect((p.SOURCE/'coverage.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        origins=defaultdict(set)
        for uid,origin in db.execute('SELECT DISTINCT unit,origin FROM candidates WHERE disposition="queued"'):origins[uid].add(origin)
        metadata=[dict(unitID=x['unitID'],tags=sorted(p.tags(x['payload'],origins[x['unitID']]))) for x in r.rows(p.SOURCE/'contexts.jsonl')]
        selected=select_held(metadata,{x['unitID'] for x in baseline['cases']});wanted={x['unitID'] for x in selected}
        contexts={x['unitID']:x['payload'] for x in r.rows(p.SOURCE/'contexts.jsonl') if x['unitID'] in wanted}
        bindings={x['unitID']:x for x in r.rows(p.SOURCE/'unit-bindings.jsonl') if x['unitID'] in wanted}
        ids={v['occurrenceID'] for x in bindings.values() for v in x['entities'].values()}
        endpoints={x['occurrenceID']:x for x in r.rows(p.SOURCE/'endpoint-provenance.jsonl') if x['occurrenceID'] in ids}
        root.mkdir(parents=True);held=[]
        for entry in development:
            cid=entry['caseID'];body=live.load(Path(entry['baselineRequest']))
            live.save(root/'development'/'requests'/f'{cid}.json',variant(body))
            live.save(root/'development'/'audit'/f'{cid}.json',live.load(BASE/'audit'/f'{cid}.json'))
        for i,selection in enumerate(selected,1):
            uid=selection['unitID'];original=contexts[uid];binding=bindings[uid];cid=f'H{i:02}'
            require(r.candidates.token(original)==binding['contextSha256'],'QUEUE_CONTEXT_DRIFT')
            for ref in binding['entities'].values():require(r.candidates.token(endpoints[ref['occurrenceID']])==ref['endpointRecordSha256'],'ENDPOINT_DRIFT')
            pairs=[]
            for pair in original['pairs']:
                key=binding['pairs'][pair['id']];require(key not in base_pairs,'DEVELOPMENT_HELD_PAIR_OVERLAP')
                found=db.execute('SELECT detail,unit,disposition FROM candidates WHERE pairkey=?',(key,)).fetchone()
                require(found and found[1:]==(uid,'queued'),'PAIR_NOT_QUEUED');pairs.append(json.loads(found[0]))
            rebuilt,_=p.queue.e.compact_context(pairs,endpoints);require(rebuilt==original,'INDEPENDENT_CONTEXT_AUDIT_FAILED')
            payload=p.project(original);body=deepcopy(live.load(Path(development[0]['baselineRequest'])))
            body['input']=live.encode(payload).decode();body['text']['format']['schema']=p.schema_for(cid,payload)
            prospective=variant(body);comparable(body,prospective)
            for arm,request in [('original',body),('prospective',prospective)]:live.save(root/'held-out'/arm/'requests'/f'{cid}.json',request)
            live.save(root/'held-out'/'audit'/f'{cid}.json',dict(originalContext=original,originalBinding=binding,pairRecords=pairs,selection=selection))
            held.append(dict(caseID=cid,unitID=uid,pairs=len(pairs),tags=selection['tags'],selectionReason=selection['selectionReason']))
    cases=dict(development=development,heldOut=held)
    prep=dict(version=VERSION,developmentUnits=16,developmentPairs=83,heldOutUnits=len(held),heldOutPairs=sum(x['pairs'] for x in held),
        newRequests=dict(development=16,heldOut=32),heldSelection=held,providerCalls=0,
        limitations=['Development is reused diagnostic context; held-out results are reported separately.',
            'Two unadjudicated recommendation arms, not gold-standard accuracy or identity decisions.',
            'Lower abstention alone is not scientific improvement.'])
    live.save(root/'preparation.json',prep)
    files={str(path.relative_to(root)):r.identity.sha(path) for path in sorted(root.rglob('*.json'))}
    for path,h in pins.items():r.preflight.pilot.verify(Path(path),h,{})
    live.save(root/'manifest.json',dict(version=VERSION,inputHashes=pins,outputHashes=files,cases=cases))
    return prep


def verify(root: Path) -> dict:
    """Verify every frozen authority and instruction-only matched-arm invariant offline."""
    require(root.resolve().is_relative_to(ROOT.resolve()),'CALIBRATION_ROOT_REQUIRED')
    m=live.load(root/'manifest.json');require(m['version']==VERSION,'VERSION_DRIFT')
    for path,h in m['inputHashes'].items():r.preflight.pilot.verify(Path(path),h,{})
    for name,h in m['outputHashes'].items():r.preflight.pilot.verify(root/name,h,{})
    for case in m['cases']['development']:
        comparable(live.load(Path(case['baselineRequest'])),live.load(root/'development'/'requests'/f"{case['caseID']}.json"))
    for case in m['cases']['heldOut']:
        comparable(live.load(root/'held-out'/'original'/'requests'/f"{case['caseID']}.json"),live.load(root/'held-out'/'prospective'/'requests'/f"{case['caseID']}.json"))
    return m


def align(before: dict, after: dict, payload: dict) -> list:
    """Compare exact listed pairs only; neither arm is treated as a correct answer."""
    old={x['pairID']:x for x in before['assessments']};new={x['pairID']:x for x in after['assessments']}
    require(len(old)==len(before['assessments']) and len(new)==len(after['assessments']),'DUPLICATE_PAIR')
    require(set(old)==set(new)=={x['id'] for x in payload['pairs']},'PAIR_ALIGNMENT_DRIFT')
    rows=[]
    entities={x['id']:x for x in payload['entities']}
    for pair in payload['pairs']:
        pid=pair['id'];a=old[pid];b=new[pid];left,right=(entities[x] for x in pair['entities'])
        flags=[]
        if a['recommendation']!=b['recommendation']:
            if b['recommendation']=='same_entity_candidate':flags.append('new_same_entity_proposal')
            if b['recommendation']=='different_entities_candidate':flags.append('new_different_entities_proposal')
            if b['recommendation']=='abstain':flags.append('new_abstention_requires_inspection')
            if a['recommendation']=='same_entity_candidate':flags.append('lost_same_entity_proposal_requires_inspection')
        if a['evidenceIDs']!=b['evidenceIDs'] or a['conflictEvidenceIDs']!=b['conflictEvidenceIDs']:flags.append('citation_basis_changed_requires_inspection')
        rows.append(dict(pairID=pid,scope='cross_family' if set(left['sourceFamilies'])!=set(right['sourceFamilies']) else 'within_family',
            before=a,after=b,categoryChanged=a['recommendation']!=b['recommendation'],reviewFlags=flags,
            entities=[left,right]))
    return rows


def report(root: Path) -> dict:
    """Report matched changes and all failures/usage, without baseline writes or quality claims."""
    m=verify(root);summary={};worksheets={};all_rows=[]
    for stage,key in [('development','development'),('held-out','heldOut')]:
        outcomes=[];comparisons=[];transitions=Counter();strata=Counter()
        for case in m['cases'][key]:
            cid=case['caseID']
            if stage=='development':
                requests=[Path(case['baselineRequest']),root/'development'/'requests'/f'{cid}.json']
                folders=[Path(case['baselineAttempt']),root/'development'/'attempts'/cid]
                audit=live.load(root/'development'/'audit'/f'{cid}.json')
            else:
                requests=[root/'held-out'/arm/'requests'/f'{cid}.json' for arm in ('original','prospective')]
                folders=[root/'held-out'/arm/'attempts'/cid for arm in ('original','prospective')]
                audit=live.load(root/'held-out'/'audit'/f'{cid}.json')
            bodies=[live.load(x) for x in requests];results=[result(folder,body) for folder,body in zip(folders,bodies)]
            for arm,(outcome,_) in zip(('original','prospective'),results):outcomes.append(dict(caseID=cid,arm=arm,historical=(stage=='development' and arm=='original'),**outcome))
            if any(value is None for _,value in results):continue
            rows=align(results[0][1],results[1][1],json.loads(bodies[0]['input']))
            for row in rows:
                pid=row['pairID']
                pair_tags=p.tags(dict(entities=row['entities'],pairs=[dict(entities=[x['id'] for x in row['entities']])]),set())-{'sparse','dense','cross_family','within_family'}
                row.update(stage=stage,caseID=cid,unitID=case['unitID'],tags=sorted(pair_tags),unitTags=case['tags'],
                    exactPairKey=audit['originalBinding']['pairs'][pid],
                    originalOccurrenceIDs=[audit['originalBinding']['entities'][entity['id']]['occurrenceID'] for entity in row['entities']],
                    localEvidenceBindings={k:v for k,v in audit['originalBinding']['evidence'].items() if any(k.startswith(entity['id']+'Q') or k.startswith(entity['id']+'R') for entity in row['entities'])},
                    sourceBindings={s:audit['originalBinding']['sources'][s] for entity in row['entities'] for s in entity['sources']})
                transitions[(row['before']['recommendation'],row['after']['recommendation'])]+=1
                for tag in ['all']+row['tags']:
                    strata[(row['scope'],tag,'before_abstain')]+=int(row['before']['recommendation']=='abstain')
                    strata[(row['scope'],tag,'after_abstain')]+=int(row['after']['recommendation']=='abstain')
                comparisons.append(row)
        ordered=sorted(comparisons,key=lambda x:r.candidates.token([stage,x['exactPairKey']]))
        worksheets[stage]=[x for x in ordered if x['categoryChanged']][:6]+[x for x in ordered if not x['categoryChanged']][:6]
        all_rows.extend(comparisons)
        summary[stage]=dict(matchedPairs=len(comparisons),expectedPairs=sum(x['pairs'] for x in m['cases'][key]),
            categoryTransitions=[dict(before=k[0],after=k[1],count=n) for k,n in sorted(transitions.items())],
            abstentionStrata=[dict(scope=k[0],tag=k[1],measure=k[2],count=n) for k,n in sorted(strata.items())],
            reviewFlags=dict(Counter(flag for x in comparisons for flag in x['reviewFlags'])),outcomes=outcomes,
            usageByArm={arm:dict(knownInputTokens=sum((o.get('tokens') or {}).get('inputTokens') or 0 for o in outcomes if o['arm']==arm),
                knownOutputTokens=sum((o.get('tokens') or {}).get('outputTokens') or 0 for o in outcomes if o['arm']==arm),
                unknownUsage=sum(o['status']!='not_dispatched' and not o.get('usage') for o in outcomes if o['arm']==arm)) for arm in ('original','prospective')})
    result_doc=dict(version=VERSION,stages=summary,identityDecisions=0,
        limitation='Model-to-model transitions only; abstention reduction is not precision, recall, population accuracy or scientific improvement.')
    live.save(root/'comparison.json',dict(rows=all_rows),immutable=False)
    live.save(root/'worksheet.json',dict(stages=worksheets,reviewAuthority='unreviewed worksheet, no gold labels'),immutable=False)
    live.save(root/'report.json',result_doc,immutable=False)
    lines=['# Prospective semantic calibration','',result_doc['limitation'],'']
    for stage,values in summary.items():lines += [f"## {stage}",f"Matched pairs: {values['matchedPairs']} / {values['expectedPairs']}",json.dumps(values['categoryTransitions']),json.dumps(values['reviewFlags']),'']
    live.write(root/'report.md',('\n'.join(lines)+'\n').encode(),immutable=False)
    return result_doc


def execute(root: Path, stage: str, enabled: bool=False, call=None) -> dict:
    """Explicit separate stage gates; reuse native once-only attempts and transport unchanged."""
    require(stage in ('development','held-out'),'UNKNOWN_STAGE');require(enabled or call is not None,'LIVE_FLAG_REQUIRED')
    m=verify(root)
    with (root/'.execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if call is None:
            key=live.provider.load_openai_api_key();call=lambda body:live.provider._http_post_json(key,body)
        try:
            if stage=='development':
                for case in m['cases']['development']:
                    cid=case['caseID'];p.attempt(root/'development'/'attempts'/cid,live.load(root/'development'/'requests'/f'{cid}.json'),call)
            else:
                for i,case in enumerate(m['cases']['heldOut']):
                    cid=case['caseID']
                    for arm in (('original','prospective') if i%2==0 else ('prospective','original')):
                        p.attempt(root/'held-out'/arm/'attempts'/cid,live.load(root/'held-out'/arm/'requests'/f'{cid}.json'),call)
        finally:report(root)
    return report(root)


def main() -> None:
    """Keep all offline operations socket-blocked and both live stages separately explicit."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','dry-run','report','run-development','run-held-out'])
    parser.add_argument('--root',type=Path,default=ROOT/'v1');parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.command.startswith('run-'):value=execute(args.root,args.command.removeprefix('run-'),args.execute)
    else:
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
            value=prepare(args.root) if args.command=='prepare' else report(args.root) if args.command=='report' else dict(status='offline_dry_run_passed',stages=list(verify(args.root)['cases']))
    print(json.dumps(value,sort_keys=True))


if __name__=='__main__':main()
