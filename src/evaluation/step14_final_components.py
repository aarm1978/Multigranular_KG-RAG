"""One final, complete-component semantic prediction per pending Step 14 component."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
from statistics import quantiles
from unittest.mock import patch
from jsonschema import Draft202012Validator

from src.evaluation import step14_component_adjudication as previous
from src.extraction.llm import pilot_preflight

w = previous.w
replay = previous.replay
ROOT = previous.ROOT.parent / 'v2'
CONTEXT = 1_050_000
MAX_OUTPUT = 128_000
INSTRUCTIONS = previous.PROMPT + """
Interpret differences in configuration, application, time step and source context. Decide
whether they are compatible qualifications of the same referent, a material identity
contradiction, or unresolved ambiguity. Cite qualifyingEvidenceIDs for compatible context,
contradictoryEvidenceIDs for substantive counterevidence, and supportingEvidenceIDs for
direct support. A qualification cannot substitute for a member's own supporting citation.
Split or abstain for material conflict or unresolved identity/granularity. An evidence-based
abstention is a final outcome. Quote references resolve through the component text table.
Previous memberships and cited contrasts are hypotheses for reconsideration, regardless of
frequency. Preserve each exact locked membership as a strict group. These locks are external
boundary constraints and do not supply semantic evidence. Give concise whole-group reasons.
"""


def final_body(body, aliases, protected, contrasts):
    """Compact repeated literal text, preserve every evidence alias and reduce enum repetition."""
    body = deepcopy(body)
    payload = json.loads(body['input'])
    reverse = {o:a for a,o in aliases.items()}
    text_ids = {}
    for occurrence in payload['occurrences']:
        for q in occurrence['evidence']:
            text = q.pop('text')
            q['textRef'] = text_ids.setdefault(text, f'T{len(text_ids)+1}')
    payload.update(textTable={t:text for text,t in text_ids.items()},
                   lockedMemberships=[[reverse[o] for o in g] for g in protected],
                   priorContrasts=contrasts)
    body.update(input=w.live.encode(payload).decode(), instructions=INSTRUCTIONS)
    schema = body['text']['format']['schema']
    assignment = schema['properties']['assessments']['items']
    assignment['properties'].update(
        conflictAssessment=dict(type='string',enum=['no_conflict','compatible_qualification','material_conflict','unresolved_ambiguity']),
        qualifyingEvidenceIDs=dict(type='array',items=dict(type='string')))
    assignment['required'] += ['conflictAssessment','qualifyingEvidenceIDs']
    # Keep the full alias enum once. Lead endpoints are checked against exact bindings.
    for name in ('subject','object'):
        schema['properties']['relationLeads']['items']['properties'][name] = dict(type='string')
    return body


def evaluate(value, body, binding):
    """Retain independent valid assignments, model abstentions and evidence leads."""
    w.require(isinstance(value,dict),'INVALID_ENVELOPE')
    aliases,refs = binding['aliases'],binding['evidence']
    payload = dict(json.loads(body['input']),allowedPredicates=[])
    schema = body['text']['format']['schema']
    identity_schema = previous.replay.v3.legacy.schema(payload)
    identity_schema['properties']['assessments'] = schema['properties']['assessments']
    adapted = dict(body,input=w.live.encode(payload).decode(),text=dict(format=dict(schema=identity_schema)))
    rows,layers = replay.items_for(dict(assessments=value.get('assessments'),typedRelations=[],ontologyGaps=[]),
                                   adapted,aliases,refs,binding['members'])
    assigned = {}
    for row in rows:
        item = row['modelItem'] if isinstance(row['modelItem'],dict) else {}
        ids = set(row['occurrenceIDs'])
        reasons = set(row['reasons'])
        cited = replay.strings(item.get('qualifyingEvidenceIDs'))
        row['qualificationBindings'] = [dict(evidenceID=q,binding=refs.get(q)) for q in cited]
        if any(q not in refs for q in cited):
            reasons.add('UNKNOWN_QUALIFICATION')
        role = item.get('conflictAssessment')
        if role=='compatible_qualification' and not cited:
            reasons.add('UNCITED_QUALIFICATION')
        if row['category']=='strict_identity' and role in ('material_conflict','unresolved_ambiguity'):
            reasons.add('UNSUPPORTED_STRICT_IDENTITY')
        if any(ids.intersection(lock) and (ids!=set(lock) or row['category']!='strict_identity')
               for lock in binding['protectedMemberships']):
            reasons.add('PROTECTED_MEMBERSHIP_CHANGE')
        row['reasons'] = sorted(reasons)
        if reasons:
            row['status']='mechanically_unresolved'
        else:
            for a in row['occurrenceAliases']:
                assigned[a] = row['itemIndex']
    unresolved = sorted(aliases[a] for a in aliases.keys()-assigned.keys())
    leads = []
    lead_schema = Draft202012Validator(schema['properties']['relationLeads']['items'])
    supplied = value.get('relationLeads')
    for i,lead in enumerate(supplied if isinstance(supplied,list) else []):
        errors = [e.message for e in lead_schema.iter_errors(lead)]
        endpoints=[]; citations=[]
        if not errors:
            a,b=lead['subject'],lead['object']
            endpoints=[aliases.get(a),aliases.get(b)]
            citations=[dict(evidenceID=q,binding=refs.get(q)) for q in lead['evidenceIDs']]
            if a not in assigned or b not in assigned or assigned[a]==assigned[b]:
                errors.append('NEEDS_TWO_INDEPENDENT_ASSIGNMENTS')
            if any(c['binding'] is None for c in citations) or not {a,b}<={c['binding']['alias'] for c in citations if c['binding']}:
                errors.append('INVALID_ENDPOINT_EVIDENCE')
            if not lead['explanation'].strip():
                errors.append('EMPTY_EXPLANATION')
        leads.append(dict(index=i,modelItem=lead,endpoints=endpoints,citations=citations,reasons=errors,
                          status='mechanically_unresolved' if errors else 'evidence_lead'))
    supersessions=[]
    for cid,old in binding['priorTargets'].items():
        changes=[r for r in rows if set(old).intersection(r['occurrenceIDs'])]
        if not any(r['category']=='strict_identity' and set(r['occurrenceIDs'])==set(old)
                   and not r['reasons'] for r in changes):
            supersessions.append(dict(priorTarget=cid,oldMembership=old,
                                      replacementAssignmentIndices=[r['itemIndex'] for r in changes],
                                      status='affected_unresolved' if set(old).intersection(unresolved)
                                      else 'prospective_supersession'))
    return dict(status='complete_prediction' if layers['partitionExact'] and not unresolved else 'partial_prediction',
                assignments=rows,mechanicallyUnresolved=unresolved,partitionAudit=layers,
                relationLeads=leads,leadFieldValid=isinstance(supplied,list),supersessions=supersessions,
                humanVerified=False,productionWrites=0)


def process(root,uid,body,response):
    """Archive provider bytes as received and report item-level outcomes."""
    base=root/'execution'
    w.live.save(base/f'{uid}.response.json',response)
    report=dict(status='invalid_or_incomplete',usage=response.get('usage'))
    try:
        w.require(response.get('status')=='completed','INCOMPLETE_RESPONSE')
        value=w.transport.decode(w.live.provider.extract_model_output(response))
        report.update(evaluate(value,body,w.live.load(root/'bindings'/f'{uid}.json')))
    except (ValueError,TypeError,KeyError,w.live.provider.OpenAIProviderError) as exc:
        report['error']=str(exc)
    w.live.save(base/f'{uid}.validation.json',report)
    return report


def prepare(root):
    """Size the frozen pending components using actual observed v1 tokens and request bytes."""
    w.require(not root.exists(),'FRESH_OUTPUT_REQUIRED')
    source=previous.ROOT
    replay.verify(source)
    pins={}
    def pin(path):
        pins[str(path)]=w.r.identity.sha(path)
        return path
    def read(folder,name):
        path=pin(folder/name)
        w.require(pins[str(path)]==w.live.load(folder/'manifest.json')['outputHashes'][name],'INPUT_DRIFT')
        return w.r.rows(path)
    inventory=list(read(source,'components.jsonl'))
    requests={r['custom_id']:r['body'] for r in read(source,'requests.jsonl')}
    endpoints={e['occurrenceID']:e for e in read(w.BASE/'unified-review-queue/v1','endpoint-provenance.jsonl')}
    members={m['occurrenceID']:m for m in read(w.BASE/'referent-groups/v1','members.jsonl')}
    retained=[]; held={}; total=Counter();rates=[];byte_total=0
    for uid,body in requests.items():
        raw=w.live.load(pin(source/'execution'/f'{uid}.response.json'))
        path=pin(source/'execution'/f'{uid}.validation.json')
        report=w.live.load(path)
        w.require(raw['status']=='completed' and raw['usage']==report['usage'],'INCOMPLETE_V1')
        n=len(json.loads(body['input'])['occurrences'])
        for key in ('input_tokens','output_tokens'):total[key]+=raw['usage'][key]
        total['occurrences']+=n
        rates.append(raw['usage']['output_tokens']/n)
        byte_total+=len(w.live.encode(body))
        if report['status']=='complete_prediction':
            retained.append(dict(unitID=uid,report=str(path),sha256=pins[str(path)]))
        else:
            w.require(report['status']=='held','UNEXPECTED_V1_STATUS')
            held[uid]=report
    w.require(len(retained)==115 and len(held)==7,'V1_CHECKPOINT')
    pricing=Path('src/extraction/llm/publications/full_corpus_gpt61_production.py')
    for path in (Path(__file__),Path(previous.__file__),Path(replay.__file__),Path(pilot_preflight.__file__),
                 Path(w.__file__),Path(w.transport.__file__),pricing,source/'manifest.json'):
        pin(path)
    observed=total['output_tokens']/total['occurrences']
    high=quantiles(rates,n=100,method='inclusive')[94]
    template=next(iter(requests.values()))
    rows=[]; planned=[]; bindings={}
    for g in inventory:
        uid=g['unitID']
        if uid in requests and uid not in held:continue
        ids=g['occurrenceIDs'];n=len(ids)
        groups=[h['occurrenceIDs'] for h in g['candidateGroups']]
        body,aliases,sources=previous.request(ids,groups,endpoints,members,template)
        payload=json.loads(body['input'])
        ref=replay.bind(payload,aliases,sources,{o:dict(endpoint=endpoints[o],member=members[o]) for o in ids})
        # The held v1 request used these exact ordered aliases and quotations.
        contrasts=[]
        if uid in held:
            old=w.live.load(pin(source/'bindings'/f'{uid}.json'))
            w.require(old['aliases']==aliases and old['evidence']==ref,'HELD_BINDING_DRIFT')
            for r in held[uid]['assignments']:
                item=r['modelItem']
                contrasts.append({k:item[k] for k in ('category','occurrenceIDs','supportingEvidenceIDs','contradictoryEvidenceIDs','granularity','rationale','uncertainty')})
        body=final_body(body,aliases,g['protectedMemberships'],contrasts)
        # Twice the observed 95th percentile rate, plus fixed reasoning room.
        cap=min(MAX_OUTPUT,1024*math.ceil((2048+2*high*n)/1024))
        body['max_output_tokens']=cap
        size=len(w.live.encode(body))
        est=math.ceil(size*total['input_tokens']/byte_total)
        projected=math.ceil(observed*n)
        # Byte-level upper bound plus an allowance for message framing.
        headroom=CONTEXT-size-2048-cap
        w.require(headroom>0 and high*n<cap,'INSUFFICIENT_COMPONENT_HEADROOM')
        counts=pilot_preflight.check_schema_limits(body['text']['format']['schema'])
        Draft202012Validator.check_schema(body['text']['format']['schema'])
        w.require(body['model']==template['model']=='gpt-6.1-sol','MODEL_DRIFT')
        priors={r[1]:h['occurrenceIDs'] for h in g['candidateGroups'] for r in h['references'] if r[0]=='prior_mapping'}
        bindings[uid]=dict(aliases=aliases,sources=sources,evidence=ref,members={o:members[o] for o in ids},
                           protectedMemberships=g['protectedMemberships'],priorTargets=priors)
        planned.append(dict(custom_id=uid,method='POST',url='/v1/responses',body=body))
        rows.append(dict(unitID=uid,fromV1='held' if uid in held else 'oversized',occurrences=n,bytes=size,
                         estimatedInput=est,estimatedOutput=projected,outputCap=cap,
                         conservativeRemainingContext=headroom,schemaCounts=counts))
    w.require(len(planned)==42 and len(planned)+len(retained)==len(inventory),'COVERAGE_DRIFT')
    inp=sum(r['estimatedInput'] for r in rows);out=sum(r['estimatedOutput'] for r in rows)
    caps=sum(r['outputCap'] for r in rows)
    summary=dict(preserved=len(retained),prepared=len(rows),v1Usage=total,requests=rows,
                 estimatedInput=inp,estimatedOutput=out,outputCeiling=caps,
                 estimatedBatchUSD=(inp*1.25+out*5)/1e6,outputCeilingBatchUSD=(inp*1.25+caps*5)/1e6)
    # The manifest is written last; transport cannot verify or use a partial package.
    root.mkdir(parents=True)
    for uid,b in bindings.items():w.live.save(root/'bindings'/f'{uid}.json',b)
    replay.v3.coverage.write_rows(root/'requests.jsonl',planned)
    replay.v3.coverage.write_rows(root/'preserved-v1.jsonl',retained)
    w.live.save(root/'summary.json',summary)
    w.live.save(root/'manifest.json',dict(inputHashes=pins,outputHashes={
        str(p.relative_to(root)):w.r.identity.sha(p) for p in root.rglob('*') if p.is_file()}))
    return summary


def main():
    """Verify offline, or explicitly operate the single Batch using existing transport."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','verify','submit','status','retrieve'])
    p.add_argument('--root',type=Path,default=ROOT)
    args=p.parse_args()
    if args.mode=='prepare':result=prepare(args.root)
    elif args.mode=='verify':result=replay.verify(args.root)
    else:
        with patch.object(w,'verify',replay.verify),patch.object(w,'process',process):
            result=w.operate(args.root,args.mode)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
