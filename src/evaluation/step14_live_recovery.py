"""Isolated once-only recovery and recommendation-only consolidation for Step 14."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
from pathlib import Path
import socket
from unittest.mock import patch
from src.evaluation import step14_production_batch as production
from src.evaluation.source_family_production_verification import read_only_log

c=production.c
ROOT=Path('var/study2_step14/live-recovery/v1')
VERSION='step14-live-recovery/0.1.0'
require=production.require


def roster(entries: dict, outcomes: dict) -> list:
    """Reject missing/duplicate/nonterminal records and the wrong recovery population."""
    require(set(entries)==set(outcomes),'OUTCOME_COVERAGE_DRIFT')
    failed=[];complete=0
    for rid,out in outcomes.items():
        if out['status']=='validation_failed':failed.append(entries[rid])
        else:
            require(out['status']=='validated_recommendation_only' and out['processable'],'UNEXPECTED_OUTCOME');complete+=1
    require(len(failed)==21 and sum(e['pairs'] for e in failed)==70 and complete==14528,'RECOVERY_ROSTER_MISMATCH')
    return sorted(failed,key=lambda e:e['identity']['requestID'])


def prepare(root: Path) -> dict:
    """Read-only native journal verification; save only bindings and 21 exact bodies."""
    require(not root.exists(),'FRESH_OUTPUT_REQUIRED');source=production.ROOT
    manifest=production.verify(source);paired,native,_=production.shared.infrastructure()
    def check(p,e):
        require(production.fingerprint(p)==e['identity'],'REQUEST_DRIFT')
    def check_out(p,receipt,out,n):
        require(out==production.process(p,receipt,n),'OUTCOME_DRIFT')
    def check_receipt(p,receipt):
        require(receipt==production.b.response_record(receipt['row'],p,paired,receipt['batchID'],receipt['number']),'RECEIPT_DRIFT')
    J=production.batch_journal(native,check,production.fingerprint,check_out,check_receipt)
    pins={str(path):c.r.identity.sha(path) for path in (source/'run-manifest.json',source/'execution.jsonl',source/'head.json',Path(__file__))}
    pins.update(manifest['implementationPins'])
    with read_only_log(source,native,J,(source/'run-manifest.json').read_bytes()) as log:
        require(len(log.outcomes)==14549 and all('settled' in job for job in log.jobs.values()),'PRODUCTION_NOT_SETTLED')
        statuses={};originals=[]
        for (rid,n),offset in sorted(log.outcomes.items()):
            require(n==1 and rid not in statuses,'DUPLICATE_OR_RETRIED_ORIGINAL')
            out=log.payload_at(offset)['native'];statuses[rid]=out
            originals.append(dict(requestID=rid,outcomeOffset=offset,outcomeSha256=c.live.token(log.payload_at(offset)),
                receiptOffset=log.receipts[rid,n],receiptSha256=c.live.token(log.payload_at(log.receipts[rid,n]))))
        failed=roster(log.entries,statuses)
        root.mkdir(parents=True);cases=[]
        for entry in failed:
            rid=entry['identity']['requestID'];uid=rid.split(':',1)[1];p=log.prepared(rid)
            require(p==c.live.load(Path(entry['path'])),'ORIGINAL_PREPARED_DRIFT')
            path=root/'requests'/f'{uid}.json';c.live.save(path,p['body'])
            cases.append(dict(requestID=rid,unitID=uid,pairs=entry['pairs'],requestPath=str(path),bodySha256=c.live.token(p['body'])))
        head=dict(seq=log.seq,headSha256=log.head)
    for path,h in pins.items():c.r.preflight.pilot.verify(Path(path),h,{})
    c.live.save(root/'manifest.json',dict(version=VERSION,pins=pins,journalHead=head,cases=cases,originals=originals,productionManifest=str(source/'run-manifest.json')))
    return dict(units=len(cases),pairs=sum(x['pairs'] for x in cases),root=str(root),journalHead=head)


def verify(root: Path) -> dict:
    """Check immutable production/recovery bindings before any dispatch or selection."""
    m=c.live.load(root/'manifest.json');require(m['version']==VERSION,'VERSION_DRIFT')
    for path,h in m['pins'].items():c.r.preflight.pilot.verify(Path(path),h,{})
    for case in m['cases']:
        require(c.live.token(c.live.load(Path(case['requestPath'])))==case['bodySha256'],'RECOVERY_REQUEST_DRIFT')
    return m


def status(root: Path) -> dict:
    """Report explicit remaining units/pairs and separate authentic live usage."""
    m=verify(root);rows=[]
    for case in m['cases']:
        out,_=c.result(root/'attempts'/case['unitID'],c.live.load(Path(case['requestPath'])))
        rows.append(dict(case,**out))
    remaining=[dict(requestID=x['requestID'],pairs=x['pairs'],status=x['status']) for x in rows if x['status']!='validated_recommendation_only']
    result=dict(counts=dict(Counter(x['status'] for x in rows)),remaining=remaining,remainingPairs=sum(x['pairs'] for x in remaining),
        outcomes=rows,identityApproved=False,knownInputTokens=sum((x.get('tokens') or {}).get('inputTokens') or 0 for x in rows),
        knownOutputTokens=sum((x.get('tokens') or {}).get('outputTokens') or 0 for x in rows),unknownUsage=sum(x['status']!='not_dispatched' and not x.get('usage') for x in rows))
    c.live.save(root/'status.json',result,immutable=False);return result


def execute(root: Path, workers: int, enabled: bool=False, call=None) -> dict:
    """Reuse native once-only attempts under one process lock and at most four workers."""
    require(1<=workers<=4,'WORKER_LIMIT');require(enabled or call is not None,'LIVE_FLAG_REQUIRED');m=verify(root)
    with (root/'.execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if call is None:
            key=c.live.provider.load_openai_api_key();call=lambda body:c.live.provider._http_post_json(key,body)
        def worker(case):
            """Record each independent uncertainty; never redispatch that unit."""
            try:c.p.attempt(root/'attempts'/case['unitID'],c.live.load(Path(case['requestPath'])),call)
            except ValueError as exc:
                if str(exc)!='UNCERTAIN_OUTCOME_STOP':raise
        with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(worker,m['cases']))
    return status(root)


def selected_row(rid: str,p: dict,value: dict,provenance: dict,seen: set) -> dict:
    """Validate exact local pairs and prevent duplicate global pair selections."""
    c.p.validate(value,p['body']);mapping=p['binding']['pairs']
    keys=set(mapping.values());require(len(keys)==len(mapping) and not seen.intersection(keys),'DUPLICATE_ASSESSED_PAIR')
    require({a['pairID'] for a in value['assessments']}==set(mapping),'PAIR_COVERAGE_DRIFT');seen.update(keys)
    return dict(requestID=rid,binding=p['binding'],recommendations=value,provenance=provenance,identityApproved=False)


def consolidate(root: Path,output: Path) -> dict:
    """Select original successes plus validated replacements; never failed scientific data."""
    require(not output.exists(),'FRESH_OUTPUT_REQUIRED');m=verify(root)
    entries={e['identity']['requestID']:e for e in c.live.load(Path(m['productionManifest']))['requests']}
    cases={x['requestID']:x for x in m['cases']};seen=set();units=set();remaining=[];counts=Counter();rows=[]
    journal=production.ROOT/'execution.jsonl'
    with journal.open('rb') as handle:
        fcntl.flock(handle,fcntl.LOCK_SH|fcntl.LOCK_NB)
        for original in m['originals']:
            rid=original['requestID'];require(rid not in units,'DUPLICATE_UNIT');units.add(rid)
            p=c.live.load(Path(entries[rid]['path']));require(production.fingerprint(p)==entries[rid]['identity'],'PREPARED_DRIFT')
            handle.seek(original['outcomeOffset']);out=production.transport.decode(handle.readline())['record']['payload']
            require(c.live.token(out)==original['outcomeSha256'],'ORIGINAL_OUTCOME_DRIFT')
            provenance=dict(origin='batch',outcomeSha256=original['outcomeSha256'],receiptSha256=original['receiptSha256'],journalHead=m['journalHead'])
            if rid in cases:
                case=cases[rid];folder=root/'attempts'/case['unitID'];result,value=c.result(folder,p['body'])
                if value is None:
                    remaining.append(dict(requestID=rid,pairs=entry_pairs(p),status=result['status']));continue
                provenance=dict(origin='isolated_live_recovery',responseID=result['responseID'],responseSha256=result['artifactHashes']['response.json'],supersededOriginalOutcomeSha256=original['outcomeSha256'])
            else:
                require(out['native']['status']=='validated_recommendation_only','INVALID_ORIGINAL_SELECTION');value=out['native']['recommendations']
            rows.append(selected_row(rid,p,value,provenance,seen));counts[provenance['origin']]+=1
    require(units==set(entries),'MISSING_UNITS');require(len(rows)==14549-len(remaining) and len(seen)==73422-sum(x['pairs'] for x in remaining),'CONSOLIDATION_COVERAGE_DRIFT')
    verify(root);output.mkdir(parents=True)
    c.live.write(output/'recommendations.jsonl',b''.join(c.live.encode(row)+b'\n' for row in rows))
    summary=dict(validatedUnits=len(rows),uniqueAssessedPairs=len(seen),origins=dict(counts),remaining=remaining,complete=not remaining,
        datasetSha256=c.r.identity.sha(output/'recommendations.jsonl'),recoveryManifestSha256=c.r.identity.sha(root/'manifest.json'),identityApproved=False,
        accounting='Original Batch usage remains in production receipts; supplemental live usage remains in recovery outcomes. Neither is replaced.')
    c.live.save(output/'summary.json',summary);return summary


def entry_pairs(p: dict) -> int:
    """Count original exact pair bindings."""
    return len(p['binding']['pairs'])


def main() -> None:
    """Expose separately gated live execution and entirely offline other commands."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','live','status','consolidate'])
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--workers',type=int,default=4);parser.add_argument('--execute',action='store_true');parser.add_argument('--output',type=Path)
    a=parser.parse_args()
    if a.command=='live':result=execute(a.root,a.workers,a.execute)
    else:
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
            result=prepare(a.root) if a.command=='prepare' else status(a.root) if a.command=='status' else consolidate(a.root,a.output or a.root/'consolidated-v1')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
