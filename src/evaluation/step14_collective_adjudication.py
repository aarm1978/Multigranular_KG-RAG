"""Bounded collective partition hypotheses; offline preparation, explicit live/Batch transport."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import socket
from unittest.mock import patch
import yaml
from src.evaluation import step14_alignment_workflow as w
from src.evaluation import step14_automatic_acceptance_preview as ab

ROOT=w.BASE/'collective-adjudication/v1'
SOURCE=w.BASE/'decision-stage/v2'
INSTRUCTION='''Partition ALL input occurrences exactly once in assessments: strict_identity clusters
(at least two members), singleton distinct entities, or singleton abstentions. Distinct means
no supported identity within this local window, not a global rejection. No overlapping
assignments. A candidate neighborhood is not an entity. Require direct whole-group support,
compatible scientific granularity and version specificity for every cluster membership.
Never infer identity by positive chains. General referents, releases, implementations and
trained instances remain distinguishable. Missing information calls for abstention.
Cite each member's source evidence; report contradictions and uncertainty. Shared wording,
generic procedures, shared source, or similar names alone do not establish identity.
Independent source-local spans may support cross-artifact identity; direct cross-citation
is not required. Source artifact aliases supply context, not identity or version proof.
Typed relations are separate optional hypotheses and may cross partition assignments.
Joint evidence must support the specific predicate and direction, not mere co-occurrence.
Use only admissible ontology signatures; otherwise abstain or record an ontology gap.
These are local hypotheses, not approvals, canonical entities or graph assertions.
'''


def schema(payload: dict) -> dict:
    """Reuse endpoint/relation schema while restricting assignments to a partition."""
    result=w.response_schema(payload)
    result['properties']['assessments']['items']['properties']['category']['enum']=['strict_identity','distinct','abstention']
    return result


def validate(value: dict, body: dict) -> dict:
    """Check exact partitions, binding and mechanical conflicts; never certify semantics."""
    w.Draft202012Validator(body['text']['format']['schema']).validate(value)
    payload=w.json.loads(body['input']);ends={e['occurrenceID']:e for e in payload['occurrences']}
    refs={q['evidenceID']:o for o,e in ends.items() for q in e['evidence']};assigned=[]
    for a in value['assessments']:
        ids=a['occurrenceIDs'];assigned.extend(ids)
        w.require(ids and len(ids)==len(set(ids)),'MEMBERSHIP')
        w.require(a['granularity'].strip() and a['rationale'].strip(),'MISSING_REASONING')
        w.require(a['broaderReferent'] is None,'NO_CANONICAL_ANCHOR')
        w.require(all(q in refs and refs[q] in ids for q in a['supportingEvidenceIDs']+a['contradictoryEvidenceIDs']),'MISBOUND_EVIDENCE')
        if a['category']!='abstention':w.require({refs[q] for q in a['supportingEvidenceIDs']}==set(ids),'UNCITED_MEMBER')
        if a['category']=='strict_identity':
            w.require(len(ids)>=2 and len({ends[o]['ontologyClass'] for o in ids})==1,'CLASS_OR_SIZE')
            w.require(not a['contradictoryEvidenceIDs'],'CONTRADICTORY_IDENTITY')
            # The established compatibility utility distinguishes source capture metadata.
            records=[dict(ends[o],labels=ends[o]['names'],versions=ends[o].get('versions',{}),identifierDeclarations=[]) for o in ids]
            signals=ab.compatibility_signals(records,[])
            w.require(not signals['demonstratedConflicts'] and not signals['unresolvedAmbiguities'],'INCOMPATIBLE_IDENTITY')
        else:w.require(len(ids)==1,'SINGLETON_ASSIGNMENT_REQUIRED')
    w.require(len(assigned)==len(set(assigned)) and set(assigned)==set(ends),'EXACT_PARTITION_REQUIRED')
    # Reuse the unchanged typed-relation/gap validator with neutral coverage witnesses.
    relation_check=deepcopy(value)
    relation_check['assessments']=[dict(category='abstention',occurrenceIDs=[o],broaderReferent=None,granularity='not assessed by relation validator',supportingEvidenceIDs=[],contradictoryEvidenceIDs=[],rationale='coverage witness',uncertainty='') for o in ends]
    relation_body=deepcopy(body);relation_body['text']['format']['schema']=w.response_schema(payload)
    w.validate_original(relation_check,relation_body) if hasattr(w,'validate_original') else _relation_validate(relation_check,relation_body)
    return dict(status='validated_hypotheses_only',semanticValidation=False,identityApprovals=0,ontologyGapCount=len(value['ontologyGaps']))


_relation_validate=w.validate


def windows(scopes: list[dict], limit: int=12) -> tuple[list[list[str]],list[dict]]:
    """Block by saved hyperedge incidence, split without clique expansion or identity union."""
    postings=defaultdict(set)
    for i,s in enumerate(scopes):
        for o in s['occurrenceIDs']:postings[o].add(i)
    pending=set(postings);units=[]
    while pending:
        seed=min(pending);chosen=[];frontier={seed}
        while frontier and len(chosen)<limit:
            o=min(frontier);frontier.remove(o)
            if o not in pending:continue
            pending.remove(o);chosen.append(o)
            for i in postings[o]:frontier.update(x for x in scopes[i]['occurrenceIDs'] if x in pending)
        units.append(sorted(chosen))
    owner={o:i for i,ids in enumerate(units) for o in ids}
    boundaries=[dict(candidateID=s['candidateID'],windows=sorted({owner[o] for o in s['occurrenceIDs']})) for s in scopes]
    return units,boundaries


def make_body(ids: list[str], endpoints: dict, members: dict, spec: dict, template: dict) -> tuple[dict,dict,dict]:
    """Assemble only scientific context with reversible entity/evidence/source aliases."""
    body=deepcopy(template);occ=[];bindings={};sources={};provenance={}
    for i,o in enumerate(ids,1):
        e=endpoints[o];alias=f'E{i}';bindings[alias]=o
        occ.append(dict(occurrenceID=alias,names=e['labels'],ontologyClass=e['ontologyClass'],sourceFamilies=e['sourceFamilies'],
            **({'versions':e['versions']} if e.get('versions') else {}),
            **({'granularity':e['granularity']} if e.get('granularity') not in (None,'unspecified_requires_context_review') else {}),
            evidence=[dict(evidenceID=f'E{i}Q{j}',text=q['literalExcerpt']) for j,q in enumerate(e['selectedEvidence'],1)]))
        provenance[o]=dict(endpoint=e,member=members[o])
    body['input']=w.live.encode(dict(occurrences=occ,allowedPredicates=[])).decode()
    body=w.refresh_body(body,spec)
    body,sources=w.source_context_body(body,bindings,provenance)
    payload=w.json.loads(body['input'])
    for rel in payload['allowedPredicates']:rel.pop('id',None)
    body['input']=w.live.encode(payload).decode();body['instructions']=INSTRUCTION
    body['text']['format']['schema']=schema(payload)
    return body,bindings,sources


def prepare(root: Path, source: Path) -> dict:
    """Consume saved decisions once; keep exact excluded/deferred coverage outside prompts."""
    w.require(not root.exists() and root.resolve().is_relative_to((w.BASE/'collective-adjudication').resolve()),'FRESH_OUTPUT_REQUIRED')
    pins={}
    def read(folder,name):
        """Verify producer hashes before consuming provenance-bearing inputs."""
        m=w.live.load(folder/'manifest.json');path=folder/name
        w.require(w.r.identity.sha(path)==m['outputHashes'][name],'INPUT_DRIFT')
        pins[str(path)]=m['outputHashes'][name];return list(w.r.rows(path))
    decisions=read(source,'decision-ledger.jsonl');approvals=read(source,'historical-approvals.jsonl')
    pairs=read(source,'pair-inventory.jsonl');typed=read(source,'typed-relation-proposals.jsonl')
    endpoints={e['occurrenceID']:e for e in read(w.BASE/'unified-review-queue/v1','endpoint-provenance.jsonl')}
    members={e['occurrenceID']:e for e in read(w.BASE/'referent-groups/v1','members.jsonl')}
    resolved={o for g in decisions if g['state'] in ('provisional_accepted','researcher_approved_exact_scope') for o in g['occurrenceIDs']}
    resolved.update(o for a in approvals for o in a['occurrenceIDs'])
    relation_done={frozenset((r['subject'],r['object'])) for r in typed}
    candidates=[]
    for g in decisions:
        if g['state']!='held_undetermined':continue
        reasons=g['holdReasons']
        lane='overlap' if 'overlapping_eligible_complete_scopes_no_union' in reasons else 'missing_information' if any(any(t in reason.lower() for t in ('missing','incomplete','information','unresolved','evidence','comparison')) for reason in reasons) else None
        if lane:candidates.append(dict(candidateID=g['simulationID'],lane=lane,occurrenceIDs=g['occurrenceIDs']))
    for p in pairs:
        if p['category'] in w.PRIORITY:candidates.append(dict(candidateID=p['pairKeySha256'],lane='typed_relation',occurrenceIDs=p['occurrenceIDs']))
    active=[];coverage=[]
    for c in candidates:
        ids=c['occurrenceIDs'];status='prepared'
        if c['lane']=='typed_relation' and frozenset(ids) in relation_done:status='existing_relation_proposal'
        elif set(ids)&resolved:status='protected_resolved_membership_boundary'
        elif any(o not in endpoints or not endpoints[o].get('selectedEvidence') or len(endpoints[o].get('sourceArtifacts',[]))!=1 for o in ids):status='missing_source_evidence'
        if status=='prepared':active.append(c)
        coverage.append(dict(c,status=status))
    units,boundaries=windows(active)
    template_path=w.ROOT/'requests.jsonl'
    w.require(w.r.identity.sha(template_path)==w.live.load(w.ROOT/'manifest.json')['outputHashes']['requests.jsonl'],'TEMPLATE_DRIFT')
    template=next(w.r.rows(template_path))['body'];pins[str(template_path)]=w.r.identity.sha(template_path)
    spec=yaml.safe_load(w.SPEC.read_text());w.require(spec['ontology']['version']=='0.1.8','ONTOLOGY_VERSION')
    root.mkdir(parents=True);requests=[];aliases={};source_aliases={};unit_rows=[]
    lanes=defaultdict(set)
    for c,b in zip(active,boundaries):
        for i in b['windows']:lanes[i].add(c['lane'])
    for i,ids in enumerate(units):
        uid=f'C{i+1:05}';body,alias,src=make_body(ids,endpoints,members,spec,template)
        requests.append(dict(custom_id=uid,method='POST',url='/v1/responses',body=body));aliases[uid]=alias;source_aliases[uid]=src
        unit_rows.append(dict(unitID=uid,occurrenceIDs=ids,lanes=sorted(lanes[i]),sourceFamilies=sorted({f for o in ids for f in endpoints[o]['sourceFamilies']})))
    # Purposive pilot: deterministic round-robin over lane/family/size profiles.
    buckets=defaultdict(list)
    for u in unit_rows:buckets[(tuple(u['lanes']),tuple(u['sourceFamilies']),len(u['occurrenceIDs'])>2)].append(u['unitID'])
    pilot=[]
    while buckets and len(pilot)<10:
        for key in sorted(list(buckets)):
            if len(pilot)==10:break
            pilot.append(buckets[key].pop(0))
            if not buckets[key]:del buckets[key]
    w.require(8<=len(pilot)<=12,'INSUFFICIENT_PILOT_UNITS')
    rest=[r['custom_id'] for r in requests if r['custom_id'] not in pilot]
    packages=[('pilot',pilot),('batch-001',rest[:100])]+[(f'batch-{i//1000+2:03}',rest[i+100:i+1100]) for i in range(0,max(0,len(rest)-100),1000)]
    def emit(folder,name,rows):
        """Write deterministic local JSONL, preserving raw evidence outside prompts."""
        with (folder/name).open('xb') as f:
            for row in rows:f.write(w.live.encode(row)+b'\n')
    emit(root,'coverage.jsonl',coverage);emit(root,'boundaries.jsonl',boundaries);emit(root,'units.jsonl',unit_rows)
    used={o for ids in units for o in ids}
    emit(root,'occurrence-provenance.jsonl',(dict(occurrenceID=o,endpoint=endpoints[o],member=members[o]) for o in sorted(used)))
    for path in (Path(__file__),w.SPEC,Path(w.__file__),Path(w.pilot.__file__),Path(w.transport.__file__),Path(ab.__file__)):pins[str(path)]=w.r.identity.sha(path)
    sizes=sum(len(w.live.encode(r['body'])) for r in requests)
    summary=dict(requests=len(requests),requestsByLane=dict(Counter(l for u in unit_rows for l in u['lanes'])),laneCountsNonexclusive=True,
        distinctOccurrences=len(used),coverageStatuses=dict(Counter(c['status'] for c in coverage)),crossWindowCandidates=sum(len(b['windows'])>1 for b in boundaries),
        pilotUnits=pilot,packages={name:len(ids) for name,ids in packages},approximateInputTokens=[sizes//5,sizes//3],approximateOutputTokens=[len(requests)*1000,len(requests)*5000],
        costNote='Apply current model input/output rates per million tokens; Batch rate separately. No rate assumed or provider lookup performed.',
        scope='Saved overlap/missing-information groups and prioritized relational pairs only; protected boundaries and missing evidence remain held. No recursive execution.',providerCalls=0)
    def package(folder,selected):
        """Use disjoint execution roots so existing once-only transport supports shards."""
        folder.mkdir(exist_ok=True);selected=set(selected)
        emit(folder,'requests.jsonl',(r for r in requests if r['custom_id'] in selected))
        w.live.save(folder/'alias-bindings.json',{u:aliases[u] for u in sorted(selected)})
        w.live.save(folder/'source-artifact-bindings.json',{u:source_aliases[u] for u in sorted(selected)})
        w.live.save(folder/'summary.json',dict(summary,requests=len(selected)))
        w.live.save(folder/'manifest.json',dict(inputHashes=pins,outputHashes={p.name:w.r.identity.sha(p) for p in folder.iterdir() if p.is_file()}))
    for name,ids in packages:
        if ids:package(root/name,ids)
    emit(root,'requests.jsonl',requests);w.live.save(root/'summary.json',summary)
    w.live.save(root/'manifest.json',dict(inputHashes=pins,outputHashes={str(p.relative_to(root)):w.r.identity.sha(p) for p in root.rglob('*') if p.is_file()}))
    return summary


def verify(root: Path) -> dict:
    """Verify package and validator pins before any dispatch or offline validation."""
    m=w.live.load(root/'manifest.json')
    for name,h in m['outputHashes'].items():w.require(w.r.identity.sha(root/name)==h,'OUTPUT_DRIFT')
    for path,h in m['inputHashes'].items():
        if path.endswith('.py') or path==str(w.SPEC):w.require(w.r.identity.sha(Path(path))==h,'IMPLEMENTATION_DRIFT')
    return w.live.load(root/'summary.json')


def main() -> None:
    """Prepare offline; dispatch only explicit pilot or shard roots through proven transport."""
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','verify','validate','live','submit','status','retrieve'])
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--unit');p.add_argument('--response',type=Path)
    a=p.parse_args()
    if a.mode in ('prepare','verify','validate'):
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
            result=prepare(a.root,a.source) if a.mode=='prepare' else verify(a.root)
            if a.mode=='validate':
                w.require(a.unit and a.response,'UNIT_AND_RESPONSE_REQUIRED')
                body=next(r['body'] for r in w.r.rows(a.root/'requests.jsonl') if r['custom_id']==a.unit)
                result=validate(w.live.load(a.response),body)
    else:
        w.require((a.root/'alias-bindings.json').exists(),'USE_PILOT_OR_SHARD_ROOT')
        units=[r['custom_id'] for r in w.r.rows(a.root/'requests.jsonl') if not (a.root/'execution'/f"{r['custom_id']}.intent.json").exists()] if a.mode=='live' else None
        with patch.object(w,'verify',verify),patch.object(w,'validate',validate):result=w.operate(a.root,a.mode,units)
    print(w.json.dumps(result,indent=2))


if __name__=='__main__':main()
