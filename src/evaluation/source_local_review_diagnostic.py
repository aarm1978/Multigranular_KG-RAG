"""Bounded, read-only diagnostic shards; no repaired responses or acceptance decisions."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import socket
import traceback
from unittest.mock import patch

from src.evaluation import source_local_supplemental_review as review
from src.extraction.llm import source_local_semantics as base

ROOT=review.retry.ROOT
SOURCE=review.OUTPUT
DEST=Path('var/study2_step13/source-local-review-diagnostic/v1')
require,digest,canonical=review.require,review.digest,review.canonical


def counts(payload):
    """Count authentic model arrays, without judging or modifying them."""
    return {k:len(payload[k]) for k in ('candidateNodes','candidateEdges','abstentions')}


def abstention_issues(payload, body):
    """Identify the exact terms of the existing conjunction that fail."""
    targets={*body['targetProfile']['entities'],*body['targetProfile']['relations']}
    selected=set(body['selectedSourceUnitIDs']);result=[]
    for i,a in enumerate(payload['abstentions']):
        checks=dict(authorizedInventory=a['inventoryId'] in targets,nonemptySourceUnits=bool(a['sourceUnitIDs']),
                    selectedSourceUnits=set(a['sourceUnitIDs'])<=selected,nonemptyReason=bool(a['reason'].strip()))
        if not all(checks.values()):
            result.append(dict(field=f'abstentions[{i}]',abstentionID=a['abstentionID'],inventoryId=a['inventoryId'],
                conditions=checks,offendingSourceUnitIDs=sorted(set(a['sourceUnitIDs'])-selected),
                authorizedSourceUnitIDs=sorted(selected)))
    return result


def read_json(path):
    """Read immutable JSON and return its byte hash."""
    raw=path.read_bytes();return json.loads(raw),digest(raw)


def checked_report(path):
    """Check the saved native report digest before summarizing it."""
    record,sha=read_json(path)
    require(record['reportSha256']==digest(canonical({k:v for k,v in record.items() if k!='reportSha256'})), 'REPORT_HASH_DRIFT')
    return record,sha


def diagnose_failure(index):
    """Reproduce one authentic failure and inspect unchanged pre-enrichment checks only."""
    summary,_=read_json(ROOT/SOURCE/'summary.json');failure=summary['validationFailures'][index]
    qroot=ROOT/review.retry.QUEUE;q,sha=read_json(qroot/'queue-manifest.json')
    require(sha==review.retry.QUEUE_SHA,'QUEUE_DRIFT')
    e=next(e for e in q['requests'] if e['identity']['requestID']==failure['requestID'])
    p,sha=read_json(qroot/'queue'/e['bundleFile']);require(sha==e['bundleSha256'],'BUNDLE_DRIFT')
    require(review.retry.adapter.fingerprint(p)==e['identity'],'IDENTITY_DRIFT')
    selection,_=read_json(ROOT/SOURCE/'selection-manifest.json')
    selected=next(x for x in selection['selection'] if x['requestID']==failure['requestID'])
    matches=[]
    for path in (qroot/'execution/batch').glob('job-*-output_file_id.jsonl'):
        for line in path.open():
            row=json.loads(line)
            if row['custom_id']==e['batchItem']['custom_id']:matches.append(row['response']['body'])
    require(len(matches)==1,'RESPONSE_ASSOCIATION_DRIFT');response=matches[0]
    require(response['id']==selected['responseID'] and digest(canonical(response))==selected['responseSha256'],'RESPONSE_HASH_DRIFT')
    from src.extraction.llm.publications.openai_provider import extract_model_output
    raw=extract_model_output(response);payload=json.loads(raw)
    context=p['requestInputs']['baseContext'];body=context['semanticRequest']['request']
    issues=abstention_issues(payload,body);trace=[];fault={}
    try:review.semantic.replay(p,raw,expected_request_sha256=p['semanticRequest']['requestSha256'])
    except Exception as exc:
        require(type(exc).__name__==failure['exceptionType'] and str(exc)==failure['reason'],'FAILURE_NOT_REPRODUCED')
        for frame,line in traceback.walk_tb(exc.__traceback__):
            filename=Path(frame.f_code.co_filename)
            if filename.is_relative_to(ROOT):
                trace.append(dict(file=str(filename.relative_to(ROOT)),line=line,function=frame.f_code.co_name))
            if frame.f_code.co_name=='enrich_checks':
                candidate=frame.f_locals.get('candidate',{})
                fault=dict(candidateID=candidate.get('candidateID'),inventoryId=candidate.get('inventoryId'),
                    classification=candidate.get('classification'),field=frame.f_locals.get('field'),
                    value=frame.f_locals.get('ref'))
    else:raise ValueError('EXPECTED_FAILURE_MISSING')
    # This is precisely the existing native-validation input projection. No abstention
    # is corrected, no enrich_checks/acceptance run is bypassed to create a projection.
    projected={k:deepcopy(payload[k]) for k in ('candidateNodes','candidateEdges')}
    for node in projected['candidateNodes']:
        for field in ('exactIdentifier','productEndpointID','version'):node.pop(field,None)
    native=base.native_validation(context,projected)
    candidates=[dict(candidateID=c['candidateID'],kind=c['kind'],disposition=c['disposition'],
        boundEvidenceCount=len(c.get('boundEvidence',[])),findings=[f['reason'] for f in c.get('findings',[])])
        for c in native['candidateChecks']]
    return dict(**failure,family=e['family'],groupID=e['groupID'],responseID=response['id'],
        responseSha256=selected['responseSha256'],bundleSha256=e['bundleSha256'],counts=counts(payload),
        offendingAbstentions=issues,traceback=trace,exceptionCandidate=fault,
        nullPurposeDiagnostics=[dict(candidateID=c['candidateID'],classification=c.get('classification'),
            target=c.get('target'),categoryKey=c.get('categoryKey')) for c in payload['candidateEdges']
            if c['inventoryId']=='C-C07' and c.get('target') is None],
        classification='invalid model source ID; response-wide fail-closed gate' if issues else 'validator implementation defect',
        preEnrichmentCandidateChecks=candidates,preEnrichmentDispositions=dict(Counter(c['disposition'] for c in candidates)),
        recoveryScope='Diagnostic native checks only. No final acceptance, local materialization or candidate recovery is asserted.')


def group_stats(report):
    """Summarize authentic candidates and existing decisions without new validation."""
    native=report['nativeValidationView'];payload=json.loads(bytes.fromhex(report['responseBytesHex']))
    c=Counter(counts(payload));c.update(groups=1,zeroYieldRequests=int(report['zeroYield']),
        acceptedNodes=len(report['projection']['nodes']),acceptedEdges=len(report['projection']['edges']),
        unresolvedAssertions=len(report['unresolvedAssertions']))
    for d in native['decisions']:c['decision:'+d['disposition']]+=1
    return c


def report_shard(kind, part):
    """Read at most 100 reports per invocation to keep local diagnostics bounded."""
    paths=sorted((ROOT/SOURCE/kind).glob('*.json'))[part*100:(part+1)*100]
    require(bool(paths),'EMPTY_SHARD');stats=defaultdict(Counter);zeros=[];hashes={}
    for path in paths:
        r,sha=checked_report(path);hashes[path.name]=sha
        if kind=='groups':
            family=r['nativeValidationView']['originalReplay']['artifactFamily']
            stats[family+':'+r['groupID']].update(group_stats(r))
        elif r['zeroYield']:
            totals=Counter()
            for group in r['groupReports']:totals.update(group_stats(group))
            has_candidates=totals['candidateNodes']+totals['candidateEdges']>0
            category='candidates_present_but_no_accepted_yield' if has_candidates else 'no_model_candidates'
            row=dict(ownerID=r['owner']['endpointID'],family=r['artifactFamily'],category=category,counts=dict(totals))
            zeros.append(row);stats[r['artifactFamily']][category]+=1
    return dict(kind=kind,part=part,files=len(paths),inputHashes=hashes,stats={k:dict(v) for k,v in stats.items()},zeroYieldOwners=zeros)


def finish():
    """Combine compact diagnostic shards without re-reading large reports."""
    parts=ROOT/DEST/'parts'
    failures=[read_json(parts/f'failure-{i}.json')[0] for i in range(8)]
    groups=[read_json(parts/f'groups-{i}.json')[0] for i in range(10)]
    owners=[read_json(parts/f'owners-{i}.json')[0] for i in range(4)]
    require(sum(p['files'] for p in groups)==997 and sum(p['files'] for p in owners)==327,'SHARD_COVERAGE_DRIFT')
    strata=defaultdict(Counter);zero_family=defaultdict(Counter);zero=[]
    for p in groups:
        for k,v in p['stats'].items():strata[k].update(v)
    for p in owners:
        zero.extend(p['zeroYieldOwners'])
        for k,v in p['stats'].items():zero_family[k].update(v)
    require(len(zero)==52,'ZERO_YIELD_COVERAGE_DRIFT')
    samples={}
    for row in sorted(zero,key=lambda x:x['ownerID']):
        key=row['family']+':'+row['category'];samples.setdefault(key,[])
        if len(samples[key])<2:samples[key].append(row['ownerID'])
    families=defaultdict(Counter)
    for key,values in strata.items():families[key.split(':',1)[0]].update(values)
    result=dict(version='offline-diagnosis/1',sourceReview=str(SOURCE),failures=failures,
        sourceSummarySha256=digest((ROOT/SOURCE/'summary.json').read_bytes()),
        selectionManifestSha256=digest((ROOT/SOURCE/'selection-manifest.json').read_bytes()),
        diagnosticImplementationSha256=digest(Path(__file__).read_bytes()),
        successfulGroupsByFamily={k:dict(v) for k,v in sorted(families.items())},
        successfulGroupsByFamilyAndGroup={k:dict(v) for k,v in sorted(strata.items())},
        zeroYieldOwnersByFamily={k:dict(v) for k,v in zero_family.items()},zeroYieldOwners=zero,
        representativeSample=samples,limitations='Group counts are source-local and not deduplicated across groups. Native candidate checks for failures are pre-enrichment, not accepted recoveries. No source evidence adjudication.',
        recommendation='Correct the null-target enrichment crash for schema-authorized C-C07 diagnostics while preserving their non-KG status. Separately seek researcher approval for abstention-local rejection with preserved invalid abstentions; never repair source IDs or promote candidates without full replay.',
        providerCalls=0,acceptanceChanges=0)
    table=['# Supplemental review diagnosis','',result['recommendation'],'',
        '| Owner | Group | Nodes | Edges | Abstentions | Cause |','|---|---|---:|---:|---:|---|']
    for f in failures:
        c=f['counts'];table.append(f"| {f['ownerID']} | {f['groupID']} | {c['candidateNodes']} | {c['candidateEdges']} | {c['abstentions']} | {f['classification']} |")
    table+=['','## Successful groups','','```json',json.dumps(result['successfulGroupsByFamilyAndGroup'],indent=2),'```',
        '','## Zero-yield owners','','```json',json.dumps(result['zeroYieldOwnersByFamily'],indent=2),'```','',
        'Representative sample: `'+json.dumps(samples)+'`','',
        'All six Hub errors fail the selectedSourceUnitIDs membership condition in source_local_semantics.py:384. The source IDs are model-authored and invalid; whole-response rejection is the existing gate, not a newly introduced diagnostic decision. Localizing this rejection would require approval.',
        '', 'Both GitHub failures reach source_local_semantics.py:357 with target=null. C-C07 unclassified/ambiguous diagnostics explicitly permit null targets (coderepos/request_contract.py:94; candidate_validation.py:212-213). The enrichment AttributeError is an implementation defect. Such diagnostics must remain non-KG.',
        '', result['limitations'],
        '', 'See diagnostic.json for exact field conditions, tracebacks, candidate IDs and preliminary dispositions.']
    review.retry.files.seal(ROOT/DEST/'diagnostic.json',result)
    with (ROOT/DEST/'diagnostic.md').open('x') as handle:handle.write('\n'.join(table)+'\n')
    return dict(output=str(DEST),failures=8,successfulGroups=997,zeroYieldOwners=52)


def main():
    """Run one bounded diagnostic stage with sockets blocked; refuse overwrites."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['failure','groups','owners','finish']);parser.add_argument('--part',type=int,default=0)
    args=parser.parse_args();require(args.part>=0,'INVALID_PART')
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')),review.production.ontology_parse_cache():
        if args.stage=='finish':result=finish()
        else:
            path=ROOT/DEST/'parts'/f'{args.stage}-{args.part}.json';require(not path.exists(),'DIAGNOSTIC_ALREADY_EXISTS')
            result=diagnose_failure(args.part) if args.stage=='failure' else report_shard(args.stage,args.part)
            path.parent.mkdir(parents=True,exist_ok=True);review.retry.files.seal(path,result)
        print(json.dumps(dict(stage=args.stage,part=args.part,output=str(DEST))))


if __name__=='__main__':main()
