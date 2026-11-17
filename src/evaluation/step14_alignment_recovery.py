"""Isolated once-only live recovery of saved invalid alignment responses."""
from __future__ import annotations
import argparse
from collections import Counter
import fcntl
import json
import os
from pathlib import Path
import socket
from unittest.mock import patch
from src.evaluation import step14_alignment_workflow as w

SOURCE=w.ROOT
ROOT=w.BASE/'alignment-workflow/live-recovery-v1'
VALID='validated_hypotheses_only'
INVALID='invalid_or_incomplete'


def select(requests: dict, reports: dict, total: int = 1795, failures: int = 81) -> list[str]:
    """Derive the exact failure roster; refuse missing, extra or unknown statuses."""
    w.require(len(requests)==total and requests.keys()==reports.keys(),'ORIGINAL_COVERAGE')
    w.require(all(x['status'] in (VALID,INVALID) for x in reports.values()),'UNEXPECTED_STATUS')
    ids=sorted(u for u,v in reports.items() if v['status']==INVALID)
    w.require(len(ids)==failures,'FAILURE_COUNT')
    return ids


def prepare(root: Path, source: Path = SOURCE) -> dict:
    """Pin original receipts and save exactly the failed immutable request bodies."""
    w.require(not root.exists() and root.resolve().is_relative_to((w.BASE/'alignment-workflow').resolve()),'FRESH_RECOVERY_REQUIRED')
    w.verify(source)
    entries=list(w.r.rows(source/'requests.jsonl'));requests={x['custom_id']:x['body'] for x in entries}
    w.require(len(entries)==len(requests),'DUPLICATE_REQUEST')
    reports={p.name.removesuffix('.validation.json'):w.live.load(p) for p in (source/'execution').glob('*.validation.json')}
    roster=select(requests,reports)
    pins={str(p):w.r.identity.sha(p) for p in (Path(__file__),Path(w.__file__),Path(w.transport.__file__),source/'manifest.json',source/'requests.jsonl',source/'alias-bindings.json')}
    originals={}
    for uid in sorted(requests):
        refs={}
        for suffix in ('response.json','validation.json','hypotheses.json','resolved-hypotheses.json','ontology-gaps.json'):
            path=source/'execution'/f'{uid}.{suffix}'
            if path.exists():pins[str(path)]=w.r.identity.sha(path);refs[suffix]=str(path)
        w.require('response.json' in refs,'MISSING_ORIGINAL_RESPONSE')
        if reports[uid]['status']==VALID:w.require('hypotheses.json' in refs and 'resolved-hypotheses.json' in refs,'MISSING_VALID_OUTPUT')
        originals[uid]=dict(status=reports[uid]['status'],artifacts=refs)
    root.mkdir(parents=True)
    w.live.write(root/'alias-bindings.json',(source/'alias-bindings.json').read_bytes())
    bodies={}
    for uid in roster:
        body=requests[uid];w.require(body['model']=='gpt-6.1-sol' and body['reasoning']=={'effort':'medium'},'PROVIDER_SETTINGS')
        w.live.save(root/'requests'/f'{uid}.json',body);bodies[uid]=w.live.token(body)
    outputs={str(p.relative_to(root)):w.r.identity.sha(p) for p in root.rglob('*') if p.is_file()}
    manifest=dict(source=str(source),roster=roster,bodyHashes=bodies,originals=originals,inputHashes=pins,outputHashes=outputs)
    w.live.save(root/'manifest.json',manifest)
    return dict(requests=len(requests),recoveryRequests=len(roster),preservedValid=len(requests)-len(roster),root=str(root))


def verify(root: Path) -> dict:
    """Fail on altered source receipts, requests, alias mappings or implementation."""
    m=w.live.load(root/'manifest.json')
    for path,h in m['inputHashes'].items():w.require(w.r.identity.sha(Path(path))==h,'INPUT_DRIFT:'+path)
    for path,h in m['outputHashes'].items():w.require(w.r.identity.sha(root/path)==h,'OUTPUT_DRIFT:'+path)
    for uid in m['roster']:w.require(w.live.token(w.live.load(root/'requests'/f'{uid}.json'))==m['bodyHashes'][uid],'BODY_DRIFT')
    return m


def attempt(root: Path, uid: str, body: dict, api) -> str:
    """Resume local finalization only; a durable send intent permanently forbids resubmission."""
    execution=root/'execution';execution.mkdir(exist_ok=True)
    report=execution/f'{uid}.validation.json';raw=execution/f'{uid}.raw-response.json';intent=execution/f'{uid}.intent.json'
    if report.exists():return w.live.load(report)['status']
    if not raw.exists():
        if intent.exists():return 'uncertain_no_resubmission'
        w.pilot.claim(root,uid,'isolated_live_recovery')
        # Persist the directory entry before a request can reach the provider.
        fd=os.open(execution,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
        try:
            data=api.request('POST','/responses',w.live.encode(body))
        except (ValueError,OSError,TimeoutError):
            return 'uncertain_no_resubmission'
        w.live.write(raw,data)
    try:
        response=w.transport.decode(raw.read_bytes())
        return w.process(root,uid,body,response)['status']
    except (ValueError,TypeError,KeyError):
        return 'invalid_saved_receipt_no_resubmission'


def execute(root: Path, api=None) -> dict:
    """One sequential once-only pass; repeated invocations skip attempts and resume receipts."""
    m=verify(root)
    with (root/'.execution.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if api is None:api=w.transport.BatchAPI(w.live.provider.load_openai_api_key())
        outcomes={u:attempt(root,u,w.live.load(root/'requests'/f'{u}.json'),api) for u in m['roster']}
    return dict(counts=dict(Counter(outcomes.values())),outcomes=outcomes)


def validated_value(response: dict, body: dict, aliases: dict) -> tuple[dict,dict]:
    """Revalidate original model bytes and resolve aliases without repairing any output."""
    w.require(response.get('status')=='completed','INCOMPLETE_RESPONSE')
    value=w.transport.decode(w.live.provider.extract_model_output(response))
    w.validate(value,body)
    return value,w.resolve_output(value,aliases)


def consolidate(root: Path, output: Path) -> dict:
    """Retain every original unit, choosing only valid recovery outputs over invalid originals."""
    w.require(not output.exists() and output.resolve().is_relative_to(root.resolve()),'FRESH_CONSOLIDATION_REQUIRED')
    m=verify(root);source=Path(m['source']);aliases=w.live.load(root/'alias-bindings.json')
    requests={x['custom_id']:x['body'] for x in w.r.rows(source/'requests.jsonl')}
    rows=[];counts=Counter()
    with (root/'.execution.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        for uid,original in sorted(m['originals'].items()):
            origin='original';status=original['status'];refs=original['artifacts'];recovery_state='not_selected'
            if uid in m['roster']:
                execution=root/'execution';report=execution/f'{uid}.validation.json'
                recovery_state=w.live.load(report)['status'] if report.exists() else ('uncertain_no_resubmission' if (execution/f'{uid}.intent.json').exists() else 'not_attempted')
                if recovery_state==VALID:
                    origin='recovery';status=VALID
                    refs={s:str(execution/f'{uid}.{s}') for s in ('response.json','validation.json','hypotheses.json','resolved-hypotheses.json')}
            value=resolved=None
            if status==VALID:
                value,resolved=validated_value(w.live.load(Path(refs['response.json'])),requests[uid],aliases[uid])
                w.require(value==w.live.load(Path(refs['hypotheses.json'])) and resolved==w.live.load(Path(refs['resolved-hypotheses.json'])),'VALIDATED_OUTPUT_DRIFT')
            counts['valid' if status==VALID else 'unresolved']+=1;counts[origin]+=1
            rows.append(dict(unitID=uid,origin=origin,status=status,unresolved=status!=VALID,recoveryStatus=recovery_state,
                original=original,selectedArtifacts={k:dict(path=v,sha256=w.r.identity.sha(Path(v))) for k,v in refs.items()},
                hypotheses=value,resolvedHypotheses=resolved,identityApproved=False))
        w.require({x['unitID'] for x in rows}==set(requests),'CONSOLIDATED_COVERAGE')
        output.mkdir(parents=True);w.live.write(output/'units.jsonl',b''.join(w.live.encode(x)+b'\n' for x in rows))
        summary=dict(total=len(rows),counts=dict(counts),manifestSha256=w.r.identity.sha(root/'manifest.json'),unitsSha256=w.r.identity.sha(output/'units.jsonl'))
        w.live.save(output/'summary.json',summary)
    return summary


def main() -> None:
    """Expose offline preparation/consolidation and researcher-terminal live execution."""
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','verify','live','consolidate'])
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.mode=='live':value=execute(args.root)
    else:
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
            if args.mode=='prepare':value=prepare(args.root)
            elif args.mode=='verify':value=dict(recoveryRequests=len(verify(args.root)['roster']))
            else:value=consolidate(args.root,args.output or args.root/'consolidated-v1')
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
