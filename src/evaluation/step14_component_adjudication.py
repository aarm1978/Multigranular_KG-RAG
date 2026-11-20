"""Prepare complete conflict-component partitions from frozen Step 14 evidence."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from jsonschema import Draft202012Validator
from src.evaluation import step14_collective_identity_reconciliation as rec
from src.evaluation.step14_collective_overlap_audit import eligible_before_competition

w = rec.w
replay = rec.replay
ROOT = w.BASE / 'component-adjudication/v1'
# Reserve room for per-member reasoning plus optional leads under the saved 16k output cap.
MAX_MEMBERS = 24
MAX_INPUT_BYTES = 96000
PROMPT = """Partition this entire set using the quoted scientific evidence. Each occurrence belongs
to exactly one assessment: strict_identity (two or more members), singleton distinct, or
singleton abstention. Candidate memberships are previous hypotheses: reconsider any of them.
Assess the referent jointly across every member. Shared wording, source, or an A=B and B=C
chain alone cannot establish whole-group identity. Independent source spans can describe the
same referent. Distinguish general referents, releases, implementations, trained instances and
dataset subsets. Capture metadata may refer to the source artifact. Cite evidence for every
claimed membership and retain contradictions, uncertainty and granularity. broaderReferent is
nullable descriptive text. Optionally include short relationLeads across different partition
assignments when source evidence suggests a specific scientific relationship. Cite both
occurrences and explain the relationship. Mere similarity, terminology and co-occurrence are
insufficient. Use [] when there are no such leads. All outputs are prospective predictions."""


def components(proposals, seeds):
    """Traverse membership incidence; connectivity defines the question for the model."""
    postings = defaultdict(set)
    for key in proposals:
        for o in key:
            postings[o].add(key)
    remaining = set(seeds)
    for seed in sorted(seeds):
        if seed not in remaining:
            continue
        pending = [seed]
        groups, members = {seed}, set()
        while pending:
            for o in pending.pop():
                if o in members:
                    continue
                members.add(o)
                neighbors = postings[o] - groups
                groups.update(neighbors)
                pending.extend(neighbors)
        remaining.difference_update(groups)
        yield sorted(members), sorted(groups)


def staged_plan(ids, hypotheses):
    """Plan at most four overlapping evidence readings and one whole-component final."""
    if len(ids)>1+4*(MAX_MEMBERS-1):
        return dict(status='unresolved_exceeds_bounded_plan', requestsPrepared=0)
    freq=Counter(o for h in hypotheses for o in h['occurrenceIDs'])
    shared=min(ids,key=lambda o:(-freq[o],o))
    rest=[o for o in ids if o!=shared]
    width=min(MAX_MEMBERS-1,(len(rest)+1)//2)
    return dict(status='later_preparation_required',requestsPrepared=0,
                sharedOccurrence=shared,
                evidenceReadings=[[shared,*rest[i:i+width]] for i in range(0,len(rest),width)],
                finalRequired=True,finalOccurrenceIDs=ids)


def request(ids, groups, endpoints, members, template):
    """Reuse the original source aliases, exact quote construction and provider settings."""
    # Identity requests need no ontology predicate options.
    body, aliases, sources = replay.v3.legacy.make_body(ids,endpoints,members,
                                                        {'classes':[], 'relations':[]},template)
    reverse = {o:a for a,o in aliases.items()}
    payload = json.loads(body['input'])
    payload.pop('allowedPredicates')
    payload['candidateMemberships'] = [[reverse[o] for o in g] for g in groups]
    schema = w.pilot.schema(payload)
    props = schema['properties']['assessments']['items']['properties']
    props['category']['enum'] = ['strict_identity','distinct','abstention']
    endpoint = dict(type='string',enum=list(aliases))
    schema['properties']['relationLeads'] = dict(type='array',items=w.pilot.obj(dict(
        subject=endpoint,object=endpoint,evidenceIDs=dict(type='array',items=dict(type='string')),
        explanation=dict(type='string'))))
    schema['required'].append('relationLeads')
    body.update(input=w.live.encode(payload).decode(),instructions=PROMPT)
    body['text']['format'].update(name='component_partition',schema=schema)
    return body,aliases,sources


def evaluate(value, body, binding):
    """Independently validate the partition and each lead, preserving raw output."""
    aliases=binding['aliases']; refs=binding['evidence']
    schema=body['text']['format']['schema']
    w.require(isinstance(value,dict),'INVALID_ENVELOPE')
    # v4 validates assignment items against the original schema. Optional lead errors
    # remain in its schema diagnostics and cannot suppress an independent partition.
    payload=dict(json.loads(body['input']),allowedPredicates=[])
    identity_schema=replay.v3.legacy.schema(payload)
    identity_schema['properties']['assessments']=schema['properties']['assessments']
    adapted=dict(body,input=w.live.encode(payload).decode(),text=dict(format=dict(schema=identity_schema)))
    rows,layers=replay.items_for(dict(assessments=value.get('assessments'),typedRelations=[],ontologyGaps=[]),
                                 adapted,aliases,refs,binding['members'])
    reasons=[]
    if not layers['partitionExact']:reasons.append('INEXACT_PARTITION')
    if any(row['status'] not in (replay.VALID,'abstention') for row in rows):reasons.append('HELD_ASSIGNMENT')
    owner={o:i for i,row in enumerate(rows) for o in row['occurrenceAliases']}
    strict={tuple(sorted(row['occurrenceIDs'])) for row in rows if row['category']=='strict_identity' and None not in row['occurrenceIDs']}
    if any(tuple(sorted(g)) not in strict for g in binding['protectedMemberships']):
        reasons.append('PROTECTED_MEMBERSHIP_CHANGE')
    leads=[]
    supplied=value.get('relationLeads')
    for i,lead in enumerate(supplied if isinstance(supplied,list) else []):
        errors=[e.message for e in Draft202012Validator(schema['properties']['relationLeads']['items']).iter_errors(lead)]
        endpoints=[];citations=[]
        if not errors:
            a,b=lead['subject'],lead['object']
            endpoints=[aliases[a],aliases[b]]
            if a==b or owner.get(a)==owner.get(b):errors.append('SAME_ASSIGNMENT')
            citations=[dict(evidenceID=q,binding=refs.get(q)) for q in lead['evidenceIDs']]
            if not citations or any(c['binding'] is None for c in citations):errors.append('UNKNOWN_OR_MISSING_EVIDENCE')
            if not {a,b} <= {c['binding']['alias'] for c in citations if c['binding']}:errors.append('UNCITED_ENDPOINT')
            if not lead['explanation'].strip():errors.append('MISSING_EXPLANATION')
        if reasons:errors.append('PARTITION_REQUIRES_REVIEW')
        leads.append(dict(index=i,modelItem=lead,endpoints=endpoints,citations=citations,reasons=errors,
                          status='review_required' if errors else 'evidence_lead'))
    return dict(partitionStatus='held' if reasons else 'complete_prediction',partitionReasons=reasons,
                assignments=rows,relationLeads=leads,leadFieldValid=isinstance(supplied,list),
                priorMappingReview=binding['priorMappings'],humanVerified=False,productionWrites=0)


def process(root,uid,body,response):
    """Preserve native receipt and usage regardless of validity."""
    path=root/'execution'
    w.live.save(path/f'{uid}.response.json',response)
    report=dict(status='invalid_or_incomplete',usage=response.get('usage'))
    try:
        w.require(response.get('status')=='completed','INCOMPLETE_RESPONSE')
        value=w.transport.decode(w.live.provider.extract_model_output(response))
        report.update(evaluate(value,body,w.live.load(root/'bindings'/f'{uid}.json')))
        report['status']=report['partitionStatus']
    except (ValueError,TypeError,KeyError,w.live.provider.OpenAIProviderError) as exc:
        report['error']=str(exc)
    w.live.save(path/f'{uid}.validation.json',report)
    return report


def prepare(root):
    """Read pinned inventories and emit one request per reviewable complete component."""
    w.require(not root.exists(),'FRESH_OUTPUT_REQUIRED')
    pins={}
    def read(folder,name):
        path=folder/name
        h=w.live.load(folder/'manifest.json')['outputHashes'][name]
        w.require(w.r.identity.sha(path)==h,'INPUT_DRIFT:'+name)
        pins[str(path)]=h
        return w.r.rows(path)
    proposals=defaultdict(list);seeds=set();eligible=set()
    baseline=list(read(rec.ROOT,'groups.jsonl'))
    independently_eligible={tuple(g['occurrenceIDs']) for g in baseline if eligible_before_competition(g)}
    for g in baseline:
        key=tuple(sorted(g['occurrenceIDs']))
        proposals[key].append(['collective_group',g['groupID']])
        if g['state']==rec.d.ab.HELD:
            seeds.add(key)
            if any(tuple(c['occurrenceIDs']) in independently_eligible for c in g['competingCollectiveScopes']):eligible.add(key)
    for a in read(replay.ROOT,'item-ledger.jsonl'):
        if a['category']=='strict_identity':
            proposals[tuple(sorted(a['occurrenceIDs']))].append(['v4',*rec.ref(a)])
    for a in read(rec.PRIOR,'overlap-alternatives.jsonl'):
        if a['support']:proposals[tuple(sorted(a['occurrenceIDs']))].append(['earlier_candidate',a['simulationID']])
    prior_assessments=list(read(rec.PRIOR,'assessment-inventory.jsonl'))
    for a in prior_assessments:
        if a['value']['category']=='strict_identity':
            proposals[tuple(sorted(a['value']['occurrenceIDs']))].append(['earlier_assessment',a['unitID'],a['index']])
    historical={}
    for a in read(rec.ROOT,'historical-approvals.jsonl'):
        key=tuple(sorted(a['occurrenceIDs']))
        historical.setdefault(key,[]).append(a['decisionID'])
        proposals[key].append(['historical',a['decisionID']])
    by_target=defaultdict(list)
    for m in read(rec.ROOT,'occurrence-mappings.jsonl'):
        by_target[m['provisionalCanonicalID']].append(m['occurrenceID'])
    targets={tuple(sorted(ids)):cid for cid,ids in by_target.items()}
    for key,cid in targets.items():proposals[key].append(['prior_mapping',cid])
    members={m['occurrenceID']:m for m in read(w.BASE/'referent-groups/v1','members.jsonl')}
    endpoints={e['occurrenceID']:e for e in read(w.BASE/'unified-review-queue/v1','endpoint-provenance.jsonl')}
    pilot=replay.v3.SOURCE/'pilot'
    template=next(read(pilot,'requests.jsonl'))['body']
    ratios=[];input_ratios=[]
    # Empirical workload using the completed, varied stress pilot, including reasoning.
    stress=replay.v3.ROOT/'stress-pilot'
    for req in read(stress,'requests.jsonl'):
        path=stress/'execution'/f"{req['custom_id']}.response.json"
        pins[str(path)]=w.r.identity.sha(path)
        usage=w.live.load(path)['usage'];b=req['body']
        ratios.append(usage['output_tokens']/len(json.loads(b['input'])['occurrences']))
        input_ratios.append(usage['input_tokens']/len(w.live.encode(b)))
    inventory=[];requests=[];bindings={}
    low_in=high_in=low_out=high_out=0
    for index,(ids,groups) in enumerate(components(proposals,seeds),1):
        uid=f'J{index:04}'
        protected=[k for k in groups if k in historical]
        prior=[targets[k] for k in groups if k in targets]
        row=dict(unitID=uid,occurrenceIDs=ids,candidateGroups=[dict(occurrenceIDs=k,references=proposals[k]) for k in groups],
                 seedCount=sum(k in seeds for k in groups),eligibleCompetitorSeeds=sum(k in eligible for k in groups),priorMappings=prior,
                 protectedMemberships=protected,identityScope=rec.d.ab.group_scope([members[o] for o in ids]))
        inventory.append(row)
        if len(ids)>MAX_MEMBERS:
            row['status']='oversized';continue
        if any(o not in endpoints or not endpoints[o]['selectedEvidence'] or len(endpoints[o]['sourceArtifacts'])!=1 for o in ids):
            row['status']='missing_evidence';continue
        body,aliases,sources=request(ids,groups,endpoints,members,template)
        size=len(w.live.encode(body))
        if size>MAX_INPUT_BYTES or len(ids)*max(ratios)>body['max_output_tokens']:
            row['status']='oversized';continue
        row['status']='ready'
        requests.append(dict(custom_id=uid,body=body,method='POST',url='/v1/responses'))
        refs=replay.bind(json.loads(body['input']),aliases,sources,{o:dict(endpoint=endpoints[o],member=members[o]) for o in ids})
        bindings[uid]=dict(aliases=aliases,sources=sources,evidence=refs,members={o:members[o] for o in ids},
                           protectedMemberships=protected,priorMappings=prior)
        low_in+=size*min(input_ratios);high_in+=size*max(input_ratios)
        low_out+=len(ids)*min(ratios);high_out+=len(ids)*max(ratios)
    # Preserve earlier nonidentity/contextual evidence as local pointers, including
    # saved pair assessments. None of these historical outcomes become prompt labels.
    owner={o:i for i,row in enumerate(inventory) for o in row['occurrenceIDs']}
    for row in inventory:
        row['priorAssessmentRefs']=[]
        if row['status']=='oversized':
            row['stagedPlan']=staged_plan(row['occurrenceIDs'],row['candidateGroups'])
    def attach(ids,ref):
        for i,n in Counter(owner[o] for o in ids if o in owner).items():
            if n>=2:inventory[i]['priorAssessmentRefs'].append(ref)
    for a in prior_assessments:attach(a['value']['occurrenceIDs'],['assessment',a['unitID'],a['index']])
    for a in read(rec.PRIOR,'pair-inventory.jsonl'):attach(a['occurrenceIDs'],['pair',a['pairKeySha256']])
    for a in read(replay.ROOT,'item-ledger.jsonl'):
        for i in {owner[o] for o in a['occurrenceIDs'] if o in owner}:
            inventory[i]['priorAssessmentRefs'].append(['v4',*rec.ref(a)])
    ready=[row for row in inventory if row['status']=='ready']
    pilot_ids=[]
    for row in sorted(ready,key=lambda x:(x['identityScope'],len(x['occurrenceIDs']),x['unitID'])):
        if not any(p['identityScope']==row['identityScope'] for p in ready if p['unitID'] in pilot_ids):
            pilot_ids.append(row['unitID'])
    for row in sorted(ready,key=lambda x:-len(x['occurrenceIDs'])):
        if len(pilot_ids)>=4:break
        if row['unitID'] not in pilot_ids:pilot_ids.append(row['unitID'])
    def stats(rows):
        return dict(components=len(rows),uniqueOccurrences=sum(len(x['occurrenceIDs']) for x in rows),
                    candidateGroups=sum(len(x['candidateGroups']) for x in rows),seeds=sum(x['seedCount'] for x in rows))
    summary=dict(total=stats(inventory),eligibleCompetitorSeeds=len(eligible),byStatus={s:stats([x for x in inventory if x['status']==s]) for s in sorted({x['status'] for x in inventory})},
                 byScope={s:{status:stats([x for x in inventory if x['identityScope']==s and x['status']==status])
                             for status in ('ready','oversized','missing_evidence')} for s in rec.SCOPES},
                 memberHistogram=dict(Counter(len(x['occurrenceIDs']) for x in inventory)),
                 groupHistogram=dict(Counter(len(x['candidateGroups']) for x in inventory)),
                 touchingPriorMappings=sum(bool(x['priorMappings']) for x in inventory),
                 touchingHistoricalApprovals=sum(bool(x['protectedMemberships']) for x in inventory),
                 requests=len(requests),pilotUnits=pilot_ids,inputTokens=[round(low_in),round(high_in)],
                 outputTokens=[round(low_out),round(high_out)],allLiveUSD=[round((i*2.5+o*10)/1e6,2) for i,o in ((low_in,low_out),(high_in,high_out))])
    for path in (Path('src/evaluation/step14_collective_overlap_audit.py'),Path(rec.__file__),Path(w.pilot.__file__),Path(__file__),Path(replay.__file__),Path(w.__file__),Path(replay.v3.legacy.__file__),Path(w.transport.__file__),w.SPEC):
        pins[str(path)]=w.r.identity.sha(path)
    root.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root.parent) as temp:
        folder=Path(temp)/'package';folder.mkdir()
        for uid,b in bindings.items():w.live.save(folder/'bindings'/f'{uid}.json',b)
        replay.v3.coverage.write_rows(folder/'components.jsonl',inventory)
        replay.v3.coverage.write_rows(folder/'requests.jsonl',requests)
        w.live.save(folder/'summary.json',summary)
        w.live.save(folder/'manifest.json',dict(inputHashes=pins,outputHashes={str(p.relative_to(folder)):w.r.identity.sha(p) for p in folder.rglob('*') if p.is_file()}))
        folder.rename(root)
    return summary


def main():
    """Prepare and inspect offline; use the saved transport only for explicit dispatch commands."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','verify','inspect','pilot','submit','status','retrieve'])
    p.add_argument('--root',type=Path,default=ROOT)
    args=p.parse_args();root=args.root
    if args.mode=='prepare':result=prepare(root)
    else:
        summary=replay.verify(root)
        if args.mode=='verify':result=summary
        elif args.mode=='inspect':
            result=[r for r in w.r.rows(root/'requests.jsonl') if r['custom_id'] in summary['pilotUnits']]
        else:
            with patch.object(w,'verify',replay.verify),patch.object(w,'process',process):
                if args.mode=='pilot':
                    result={}
                    for uid in summary['pilotUnits']:
                        if not (root/'execution'/f'{uid}.intent.json').exists():
                            result.update(w.operate(root,'live',[uid]))
                elif args.mode=='submit':
                    ids=[r['custom_id'] for r in w.r.rows(root/'requests.jsonl') if r['custom_id'] not in summary['pilotUnits']]
                    result=w.operate(root,'submit',ids)
                else:result=w.operate(root,args.mode)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
