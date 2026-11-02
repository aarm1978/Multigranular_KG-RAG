"""Explicit researcher-operated Batch/live transport for the pinned GitHub pilot.

No preparation, semantic parser, acceptance or KG route is called. Live resumes
only durable responses; an intent without a response always stops for review.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import fcntl
import json
from pathlib import Path
from types import FunctionType

from src.evaluation import github_full_document_pilot as pilot
from src.evaluation import hub_full_content_pilot_batch as hub
from src.extraction.llm.publications import openai_provider as provider
from src.extraction.llm.publications.resumable_production_journal import journal_class, require
from src.extraction.llm.full_corpus_source_family_batch import seal

QUEUE_SHA = '81246d4b0da1267ad63d3499c5a5e479055b60035211dbf57d36840ad9aef5c6'
ROOT = pilot.ROOT
batch = hub.batch
canonical, sha = hub.canonical, hub.sha


def bound_helpers() -> dict:
    """Reuse Hub's pure queue/receipt adapters without mutating its module globals."""
    namespace={**hub.__dict__, 'pilot':pilot,'QUEUE':pilot.BASE,'QUEUE_SHA':QUEUE_SHA}
    for name in ('verify_prepared','load_queue','infrastructure'):
        fn=hub.__dict__[name]
        namespace[name]=FunctionType(fn.__code__,namespace,name,fn.__defaults__)
    return namespace


def execution_manifest(parent: dict, pins: dict, transport: str, capacity: int | None) -> dict:
    """Pin transport and executable dependencies separately from immutable requests."""
    if transport=='batch':require(type(capacity) is int and capacity>0,'SUPPLY_--queued-token-limit')
    entries=deepcopy(parent['requests'])
    for entry in entries:entry['estimatedCostUSD']=entry['cost']['costUSD']['pooled']
    paths=[Path(__file__),Path(hub.__file__),Path(provider.__file__),Path(batch.__file__),
           Path(batch.batch_transport.__file__),Path(journal_class.__code__.co_filename),
           Path(hub.adapter.batch_journal.__code__.co_filename)]
    return dict(version='github-full-document-execution/1.0',transport=transport,parentSha256=QUEUE_SHA,
        generatorPins=pins,implementationPins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths},
        requests=entries,queuedTokenLimit=capacity,meaningfulSampleRequests=8,maximumAttemptsPerRequest=1,
        pricing=batch.PRICING if transport=='batch' else batch.baseline.PRICING,
        scientificStatus='not_evaluated',kgAuthorization=False)


def live_result(raw: dict, prepared: dict, paired) -> dict:
    """Derive transport status and native usage accounting, never semantic validity."""
    result=dict(status='failed',responseID=None,usage=None,cost={'estimatedUSD':None,'basis':'unknown_usage'},
        holds=[],kgAuthorization=False,scientificStatus='not_evaluated')
    if raw['kind']!='response':
        result.update(status='ambiguous_submission',holds=['MANUAL_RECONCILIATION_REQUIRED']);return result
    try:
        response=batch.batch_transport.decode(base64.b64decode(raw['bytesBase64'],validate=True))
        require(isinstance(response,dict),'INVALID_RESPONSE_OBJECT')
    except (ValueError,TypeError):
        result['holds']=['INVALID_PROVIDER_JSON'];return result
    result.update(responseID=response.get('id'),usage=response.get('usage'),
                  status=response.get('status') if response.get('status') in ('completed','incomplete','failed','cancelled') else 'unknown_status')
    if not isinstance(response.get('id'),str) or not response['id']:result['holds'].append('MISSING_RESPONSE_ID')
    if response.get('model')!=prepared['body']['model'] or response.get('service_tier')!='default':
        result['holds'].append('MODEL_OR_TIER_DRIFT')
    try:result['cost']=paired.usage_cost(response,batch.baseline.PRICING)
    except (ValueError,TypeError,KeyError):result['holds'].append('MALFORMED_USAGE')
    if result['cost']['estimatedUSD'] is None:result['holds'].append('UNKNOWN_USAGE')
    return result


def live_journal(native, paired, bundles):
    """Use native locking/hash chains/write-ahead recovery for one live attempt."""
    base=journal_class(native,None,None)
    class LiveJournal(base):
        """Pilot-only transitions over the unchanged durable journal machinery."""
        def __init__(self,*args,**kwargs):
            """Index the eight requests' exact event payloads."""
            super().__init__(*args,**kwargs);self.events={}

        def validate_event(self,rec):
            """Reject duplicate intents, altered identities and inconsistent results."""
            event,rid,pay=rec['event'],rec['requestID'],rec['payload']
            if event=='header':
                require(self.seq==0 and rid is None and pay==dict(manifestSha256=self.pin,generatorPins=self.manifest['generatorPins']),'HEADER_DRIFT');return
            require(self.seq>0 and rid in self.entries,'UNKNOWN_REQUEST')
            events=self.events.get(rid,{})
            require(event not in events,'DUPLICATE_LIVE_EVENT')
            if event=='intent':
                require(not events and pay==self.entries[rid]['identity'],'LIVE_IDENTITY_DRIFT')
                require(all(e.get('result',{}).get('status')=='completed' and not e['result']['holds'] for e in self.events.values()),'UNRESOLVED_PREVIOUS_SUBMISSION')
            elif event=='raw':
                require('intent' in events and pay['kind'] in ('response','http_error','transport_error'),'RAW_TRANSITION')
                if pay['kind']=='response':base64.b64decode(pay['bytesBase64'],validate=True)
            elif event=='result':
                require('raw' in events and pay==live_result(events['raw'],bundles[rid],paired),'LIVE_RECEIPT_DRIFT')
                if pay['responseID']:
                    require(not any(e.get('result',{}).get('responseID')==pay['responseID'] for e in self.events.values()),'DUPLICATE_RESPONSE_ID')
            else:raise ValueError('UNKNOWN_LIVE_EVENT')

        def accept(self,rec,digest,offset):
            """Index each durable event exactly once, including on restart."""
            self.seq,self.head=rec['seq'],digest
            if rec['requestID'] is not None:
                self.events.setdefault(rec['requestID'],{})[rec['event']]=rec['payload']
    return LiveJournal


def synchronous_call(key: str, body: dict, save_raw) -> None:
    """Reuse the synchronous client unchanged, capturing bytes before JSON decoding.

    A call-local urlopen delegate observes read() only; it neither constructs
    requests nor retries them and never mutates the existing provider module.
    """
    class CapturedResponse:
        """Persist the exact successful HTTP body before the native client parses it."""
        def __init__(self,response):
            """Keep the original native response object."""
            self.response=response
        def __enter__(self):
            """Delegate the native response context."""
            self.response.__enter__();return self
        def __exit__(self,*args):
            """Close the native response without suppressing exceptions."""
            return self.response.__exit__(*args)
        def read(self):
            """Journal wire bytes before returning them to the native decoder."""
            raw=self.response.read();save_raw(dict(kind='response',bytesBase64=base64.b64encode(raw).decode()));return raw
    def observed_open(*args,**kwargs):
        """Delegate the original prepared POST to the original HTTP implementation."""
        return CapturedResponse(provider.urlopen(*args,**kwargs))
    fn=provider._http_post_json
    call=FunctionType(fn.__code__,{**fn.__globals__,'urlopen':observed_open},fn.__name__,fn.__defaults__)
    call(key,body)


def live_report(log) -> dict:
    """Separate terminal transport outcomes from semantic acceptance."""
    rows=[];spent=0.;unknown=0
    for rid in log.entries:
        events=log.events.get(rid,{})
        result=events.get('result',dict(status='ambiguous_submission' if 'intent' in events else 'unsubmitted'))
        rows.append(dict(requestID=rid,**result))
        if 'result' in events:
            cost=result['cost']['estimatedUSD']
            if cost is None:unknown+=1
            else:spent+=cost
    return dict(transport='live',requests=rows,usagePricedUSD=spent,unknownUsageRequests=unknown,
                pricing=log.manifest['pricing'],kgAuthorization=False)


def readonly(log,native,report):
    """Inspect the native chain under a shared lock without recovery writes."""
    require(not log.staging.exists(),'RECOVERY_REQUIRED; restart explicit submit')
    with log.path.open('rb') as handle:
        fcntl.flock(handle,fcntl.LOCK_SH|fcntl.LOCK_NB);log.file=handle
        if log.checkpoint.exists():log.anchor=native.decode(log.checkpoint.read_bytes())
        native.Journal.replay(log)
        if log.manifest['transport']=='batch':hub.verify_execution_files(log)
        return report(log)


def operate(mode: str, transport: str='batch', capacity=None, *, repo: Path=ROOT, api=None, live_call=None) -> dict:
    """Require explicit dispatch; every mode first verifies the pinned queue."""
    require(mode in ('preflight','submit','status','collect') and transport in ('batch','live'),'INVALID_MODE')
    require(transport=='batch' or mode!='collect','LIVE_HAS_NO_COLLECTION; responses are journaled synchronously')
    helpers=bound_helpers();parent,bundles=helpers['load_queue'](repo)
    paired,native,pins=hub.adapter.infrastructure()
    root=repo/pilot.BASE/'execution'/transport;path=root/'run-manifest.json'
    saved=batch.batch_transport.decode(path.read_bytes()) if path.exists() else None
    if not saved and mode in ('preflight','status'):
        require(not (root/'execution.jsonl').exists() or not (root/'execution.jsonl').read_bytes(),'ORPHAN_JOURNAL; restart submit')
        return dict(verified=True,initialized=False,requests=8,transport=transport,queueSha256=QUEUE_SHA,providerCalls=0)
    if saved:
        require(capacity is None or capacity==saved['queuedTokenLimit'],'CAPACITY_DRIFT');capacity=saved['queuedTokenLimit']
    manifest=execution_manifest(parent,pins,transport,capacity)
    wire=canonical(manifest)+b'\n'
    require(saved is None or path.read_bytes()==wire,'RUN_MANIFEST_DRIFT')
    require(mode!='collect' or saved is not None,'NO_BATCH_TO_COLLECT')
    if transport=='batch':Journal,_,_,record=helpers['infrastructure']();report=hub.report
    else:Journal=live_journal(native,paired,bundles);report=live_report
    log=Journal(root/'execution.jsonl',wire,sha(wire))
    if mode=='preflight' or transport=='live' and mode=='status':return readonly(log,native,report)
    with log:
        if path.exists():require(path.read_bytes()==wire,'RUN_MANIFEST_DRIFT')
        else:seal(path,wire)
        if transport=='batch':
            hub.verify_execution_files(log)
            if api is None:api=batch.batch_transport.BatchAPI(provider.load_openai_api_key())
            if mode=='submit':
                log.disposition=batch.submit_all(log,api,lambda e:bundles[e['identity']['requestID']],native,hub.adapter.fingerprint,1)
            elif mode=='collect':
                errors=batch.collect_once(log,api,hub.raw_outcome,record)
                require(not errors,'COLLECTION_STOP:'+json.dumps(errors))
            else:
                for jid,events in log.jobs.items():
                    if 'submitted' in events:
                        remote=api.retrieve(log.job(jid,'submitted')['id']);batch.check_batch_binding(log,jid,remote)
                        log.append('snapshot',jid,remote)
        else:
            key=None
            for rid,p in bundles.items():
                events=log.events.get(rid,{})
                if 'raw' in events and 'result' not in events:
                    log.append('result',rid,live_result(events['raw'],p,paired))
                if 'result' in events:
                    require(events['result']['status']=='completed' and not events['result']['holds'],'LIVE_TERMINAL_HOLD:'+rid)
                    continue
                require('intent' not in events,'AMBIGUOUS_SUBMISSION_STOP:'+rid)
                if live_call is None and key is None:key=provider.load_openai_api_key()
                log.append('intent',rid,hub.adapter.fingerprint(p))
                def save(raw):
                    """Persist response bytes before parsing, costing or moving onward."""
                    log.append('raw',rid,raw)
                try:
                    (live_call or synchronous_call)(key,deepcopy(p['body']),save)
                except provider.OpenAIHTTPError as exc:
                    if 'raw' not in log.events[rid]:save(dict(kind='http_error',diagnostic=exc.diagnostic))
                except Exception as exc:
                    if log.poisoned:raise
                    if 'raw' not in log.events[rid]:save(dict(kind='transport_error',exceptionType=type(exc).__name__))
                require('raw' in log.events[rid],'AMBIGUOUS_SUBMISSION_STOP:'+rid)
                result=live_result(log.events[rid]['raw'],p,paired);log.append('result',rid,result)
                require(result['status']=='completed' and not result['holds'],'LIVE_TERMINAL_HOLD:'+rid)
        return report(log)


def main() -> None:
    """Select transport explicitly for live; Batch remains the default."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('preflight','submit','status','collect'))
    parser.add_argument('--transport',choices=('batch','live'),default='batch')
    parser.add_argument('--queued-token-limit',type=int)
    args=parser.parse_args();print(json.dumps(operate(args.operation,args.transport,args.queued_token_limit),indent=2))


if __name__=='__main__':main()
