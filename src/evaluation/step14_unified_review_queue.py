"""Prepare the researcher-selected Step 14 pool offline, without identity decisions."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import itertools
import json
import re
from pathlib import Path
import socket
import sqlite3
from unittest.mock import patch
from src.evaluation import step14_explicit_alias_preview as alias

e=alias.baseline
r=e.r
require=r.require
ROOT=Path('var/study2_step14/unified-review-queue')
ALIAS=alias.ROOT/'v1'
VERSION='step14-unified-review-queue/0.1.0'
CONTRACT=Path('docs/study2_step14_unified_review_queue_v0.1.md')


def prior_assessments(document: dict, pins: dict) -> dict:
    """Bind completed exact assessment memberships; never infer cross-subset judgments."""
    result=defaultdict(list)
    for case in document['cases']:
        for field in ('audit','originalModelRecommendation','terminal'):
            ref=case[field];r.preflight.pilot.verify(Path(ref['file']),ref['sha256'],pins)
        audit=r.load(Path(case['audit']['file']));model=r.load(Path(case['originalModelRecommendation']['file']))['modelAuthored']
        require(r.load(Path(case['terminal']['file']))['status']=='validated_recommendation_only','INCOMPLETE_PRIOR_ASSESSMENT')
        mapping={x['alias']:x['occurrenceID'] for x in case['occurrences']}
        require(all(audit['aliases'][k]==v for k,v in mapping.items()),'PRIOR_ALIAS_DRIFT')
        for i,assessment in enumerate(model['assessments']):
            ids=sorted(mapping[x] for x in assessment['occurrenceIDs'])
            require(len(ids)==len(set(ids)),'PRIOR_MEMBERSHIP_DRIFT')
            for pair in itertools.combinations(ids,2):
                result[r.candidates.token(list(pair))].append(dict(caseAlias=case['caseAlias'],assessmentIndex=i,
                    exactAssessmentOccurrenceIDs=ids,reference=case['originalModelRecommendation'],
                    disposition='prior_completed_pair_assessment' if len(ids)==2 else 'prior_group_assessment_overlap',
                    caveat='Model recommendation only; group membership does not establish every pairwise judgment.'))
    return result


def disposition(pair: dict, occurrences: dict, prior: dict) -> str:
    """Exclude exact approvals and defer previous assessments without promoting either."""
    left,right=(occurrences[x] for x in pair['occurrenceIDs'])
    if e.reconciliation.review_status(left,right)['sharedMemberships']['approved']:return 'approved_excluded'
    previous=prior.get(pair['pairKeySha256'],[])
    if any(x['disposition']=='prior_completed_pair_assessment' for x in previous):return 'prior_completed_pair_assessment'
    if previous:return 'prior_group_assessment_overlap'
    return 'queued'


def container(pair: dict, occurrences: dict, index: dict, groups: dict) -> str:
    """Reuse direct-key/anchor containers, partitioned by exact recorded specificity."""
    ids=pair['occurrenceIDs']
    return e.unit_key(ids,index,groups)+':'+r.candidates.token([
        [occurrences[x]['ontologyClass'],occurrences[x]['versions'],occurrences[x]['granularity']] for x in ids])


def emit(db: sqlite3.Connection, output: Path, endpoints: dict) -> dict:
    """Write explicit comparison units, lean local mappings, and exact pair coverage."""
    total=units=covered=0;examples={};pending=[];current=None
    with (output/'contexts.jsonl').open('x') as contexts,(output/'unit-bindings.jsonl').open('x') as bindings:
        def flush() -> None:
            """Bind every local ID and comparison without duplicating full provenance."""
            nonlocal total,units,covered
            if not pending:return
            payload,sidecar=e.compact_context(pending,endpoints)
            size=len(r.identity.encoded(payload))
            require(size<=12000 and len(payload['entities'])<=12 and len(pending)<=12,'CONTEXT_BOUND_EXCEEDED')
            uid=f'U{units+1:06}';units+=1;covered+=len(pending);total+=size
            contexts.write(r.identity.encoded(dict(unitID=uid,payload=payload)).decode()+'\n')
            pairs={f'P{i+1}':p['pairKeySha256'] for i,p in enumerate(pending)}
            for key in pairs.values():
                cur=db.execute('UPDATE candidates SET unit=? WHERE pairkey=? AND unit IS NULL AND disposition="queued"',(uid,key))
                require(cur.rowcount==1,'DUPLICATE_OR_MISSING_COVERAGE')
            binding=dict(unitID=uid,contextSha256=r.candidates.token(payload),pairs=pairs,
                entities={local:dict(occurrenceID=row['occurrenceID'],endpointRecordSha256=r.candidates.token(row)) for local,row in sidecar['entities'].items()},
                sources=sidecar['sources'],contextUTF8Bytes=size,
                evidence={eid:({k:v for k,v in ref.items() if k!='originalFragment'} | {'selectedFragmentIndex':int(eid.rsplit('Q',1)[1])-1})
                    if 'originalFragment' in ref else ref for eid,ref in sidecar['evidence'].items()})
            bindings.write(r.identity.encoded(binding).decode()+'\n')
            names=' '.join(label.lower() for p in pending for oid in p['occurrenceIDs'] for label in endpoints[oid]['labels'])
            categories=[x for x in ('nwm','lstm','gee','nextgen') if x in names]
            if len({f for p in pending for oid in p['occurrenceIDs'] for f in endpoints[oid]['sourceFamilies']})>1:categories.append('cross_family')
            specificity_text=names+' '+' '.join(f['literalExcerpt'] for p in pending for oid in p['occurrenceIDs'] for f in endpoints[oid]['selectedEvidence'])
            if any(set(endpoints[oid]['versions']) & {'version','versionNumber','commitSHA','fork','forkParent'} for p in pending for oid in p['occurrenceIDs']) or re.search(r'\b(?:v\d|version|release|trained|implementation|architecture)',specificity_text,re.I):
                categories.append('version_implementation')
            for category in categories:
                if category not in examples:examples[category]=dict(unitID=uid,payload=payload,binding=binding)
        for key,data in db.execute('SELECT container,detail FROM candidates WHERE disposition="queued" ORDER BY container,pairkey'):
            pair=json.loads(data)
            if key!=current:flush();pending=[]
            current=key
            trial=pending+[pair];payload,_=e.compact_context(trial,endpoints)
            if pending and (len(trial)>12 or len(payload['entities'])>12 or len(r.identity.encoded(payload))>12000):flush();pending=[]
            pending.append(pair)
        flush()
    require(db.execute('SELECT count(*) FROM candidates WHERE disposition="queued" AND unit IS NULL').fetchone()[0]==0,'UNCOVERED_PAIR')
    r.write(output/'examples.json',dict(examples=examples,missingCategories=sorted(set(['nwm','lstm','gee','nextgen','cross_family','version_implementation'])-set(examples))))
    return dict(reviewUnits=units,queuedPairs=covered,inputUTF8Bytes=total,approximateInputTokens=(total+3)//4,
        inputTokenByteUpperBound=total,outputTokenScenarioLow=covered*64,outputTokenScenarioHigh=covered*256,
        outputEstimateBasis='64–256 tokens per explicit comparison for category, short rationale and evidence references; planning scenario, not measured usage.',
        pairwiseRequestsAvoided=covered-units)


def run(output: Path) -> dict:
    """Consume the selected pool once with immutable sources and no provider calls."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(),'FRESH_OUTPUT_REQUIRED')
    manifest=r.load(ALIAS/'manifest.json');pins=dict(manifest['inputHashes'])
    for name in ('summary.json','incremental-pairs.jsonl'):pins[str(ALIAS/name)]=manifest['outputHashes'][name]
    for path in (ALIAS/'manifest.json',CONTRACT,Path(__file__)):pins.setdefault(str(path),r.identity.sha(path))
    for path,h in pins.items():r.preflight.pilot.verify(Path(path),h,{})
    document=r.load(r.preflight.approvals.DOCUMENT);approvals=list(r.rows(r.preflight.approvals.APPROVALS))
    r.preflight.approvals.validate_approvals(document,approvals)
    require(len(approvals)==29 and sum(len(x['occurrenceIDs']) for x in approvals)==99,'APPROVAL_CHECKPOINT_DRIFT')
    previous=prior_assessments(document,pins)
    occurrences=e.reconciliation.load_occurrences(e.reconciliation.PREPARED)
    endpoints=e.b.enrich([dict(occurrenceIDs=list(occurrences))],occurrences)
    for oid,row in endpoints.items():row['priorMemberships']=occurrences[oid]['priorMemberships']
    # Reuse the already pinned accepted incident-context records, not a graph reconstruction.
    relpath=r.preflight.PILOT/'accepted-relation-context.jsonl'
    pm=r.load(r.preflight.PILOT/'manifest.json');r.preflight.pilot.verify(relpath,pm['outputHashes'][relpath.name],pins)
    for line,rel in enumerate(r.rows(relpath),1):
        for field,other,direction in [('sourceID','targetID','outgoing'),('targetID','sourceID','incoming')]:
            if rel[field] not in endpoints:continue
            peer=occurrences.get(rel[other],{})
            endpoints[rel[field]].setdefault('incidentContext',[]).append(dict(modelFields=dict(direction=direction,predicate=rel['acceptedPredicate'],
                otherClass=peer.get('ontologyClass','not supplied'),otherNames=peer.get('labels',[]),literalEvidence=[x['excerpt'][:240] for x in rel['evidence'][:1]]),
                originalReference=dict(file=str(relpath),line=line,recordSha256=r.candidates.token(rel))))
    groups={};index=defaultdict(set)
    for group in r.rows(e.GROUPS/'groups.jsonl'):
        groups[group['proposalID']]=group
        for oid in group['occurrenceIDs']:index[oid].add(group['proposalID'])
    output.mkdir(parents=True)
    db=sqlite3.connect(output/'coverage.sqlite');db.execute('PRAGMA cache_size=-16384');db.execute('PRAGMA temp_store=FILE')
    db.execute('CREATE TABLE candidates(pairkey TEXT PRIMARY KEY, container TEXT, detail TEXT, disposition TEXT, origin TEXT, unit TEXT)')
    counts=Counter()
    def add(pair: dict,origin: str) -> None:
        """Store one exact pair once and preserve its source reference and disposition."""
        ids=pair['occurrenceIDs'];key=pair['pairKeySha256']
        require(ids==sorted(set(ids)) and len(ids)==2 and key==r.candidates.token(ids),'PAIR_ID_DRIFT')
        require(all(x in occurrences for x in ids),'UNKNOWN_OCCURRENCE')
        require(occurrences[ids[0]]['ontologyClass']==occurrences[ids[1]]['ontologyClass'],'CLASS_DRIFT')
        status=disposition(pair,occurrences,previous)
        require(status!='approved_excluded','APPROVED_PAIR_IN_SELECTED_POOL')
        detail=dict(pairKeySha256=key,occurrenceIDs=ids,originalReference=pair['originalReference'],origin=origin,
            previousAssessments=previous.get(key,[]))
        existing=db.execute('SELECT detail FROM candidates WHERE pairkey=?',(key,)).fetchone()
        if existing:
            require(json.loads(existing[0])['occurrenceIDs']==ids,'PAIR_ID_CONFLICT');counts['duplicateInputRows']+=1;return
        db.execute('INSERT INTO candidates VALUES(?,?,?,?,?,NULL)',(key,container(pair,occurrences,index,groups),json.dumps(detail,sort_keys=True),status,origin));counts[origin]+=1
    with sqlite3.connect((alias.SOURCE/'accounting.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as source:
        source.execute('PRAGMA query_only=ON')
        for key,data in source.execute('SELECT pairkey,detail FROM pairs WHERE alias_extended=1'):
            pair=json.loads(data);require(key==pair['pairKeySha256'],'ACCOUNTING_KEY_DRIFT');add(pair,'alias_extended')
    for pair in r.rows(ALIAS/'incremental-pairs.jsonl'):
        require(pair['incrementalEligible'] and not pair['approvedSubsetIDs'],'INVALID_ALIAS_ADDITION');add(pair,'explicit_alias')
    require(counts['alias_extended']==49731 and counts['explicit_alias']==24320,'POOL_COMPONENT_DRIFT')
    require(db.execute('SELECT count(*) FROM candidates').fetchone()[0]==74051,'UNION_COVERAGE_DRIFT')
    db.commit();workload=emit(db,output,endpoints)
    dispositions=dict(db.execute('SELECT disposition,count(*) FROM candidates GROUP BY disposition'))
    require(sum(dispositions.values())==74051 and workload['queuedPairs']==dispositions.get('queued',0),'DISPOSITION_COVERAGE_DRIFT')
    used=set()
    for (data,) in db.execute('SELECT detail FROM candidates'):
        used.update(json.loads(data)['occurrenceIDs'])
    with (output/'endpoint-provenance.jsonl').open('x') as stream:
        for oid in sorted(used):stream.write(r.identity.encoded(endpoints[oid]).decode()+'\n')
    db.commit();db.close()
    with (output/'prior-decisions.jsonl').open('x') as stream:
        for row in approvals:stream.write(r.identity.encoded(row).decode()+'\n')
    summary=dict(version=VERSION,selectedCandidates=74051,origins=dict(counts),dispositions=dispositions,workload=workload,
        approvalSubsetsPreserved=29,approvalMembershipsPreserved=99,identityDecisions=0,providerCalls=0,
        limitations=['Prior exact pair assessments are retained for researcher reconciliation, not blindly resubmitted.',
            'Overlap within a larger model assessment is deferred, not called pairwise adjudication or approval.',
            'All unlisted comparisons remain unexamined; groups never imply transitive identity.',
            'Literal windows and available incident context may be insufficient; insufficient evidence remains an outcome.',
            'Token scenarios are planning estimates, excluding future provider envelope/schema overhead.'])
    r.write(output/'summary.json',summary)
    (output/'summary.md').write_text('# Unified proposed LLM review queue\n\n'+json.dumps(summary,indent=2)+'\n')
    for path,h in pins.items():r.preflight.pilot.verify(Path(path),h,{})
    r.write(output/'manifest.json',dict(version=VERSION,inputHashes=pins,outputHashes={p.name:r.identity.sha(p) for p in sorted(output.iterdir())},providerCalls=0))
    return summary


def main() -> None:
    """Prepare offline; refuse overwriting every existing output directory."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'v1');args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        print(json.dumps(run(args.output),sort_keys=True))


if __name__=='__main__':main()
