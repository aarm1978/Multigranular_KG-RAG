"""Offline nine-request diagnostic preparation and native live/Batch operation.

Only explicit researcher submit/status/collect commands can contact providers.
No v0.4.1 default, source, schema, validator, policy or transport is changed.
"""
import argparse
import base64
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import socket
from types import FunctionType,SimpleNamespace
from unittest.mock import patch

from src.evaluation import source_local_semantic_pilot as previous
from src.extraction.llm import source_local_specialized as semantic
from src.extraction.llm.pilot_preflight import canonical,digest

ROOT=previous.ROOT
BASE=Path('var/study2_step13/source-local-semantic-pilot/v042')
adapter=previous.adapter
require=semantic.require


def bind(fn, **globals_):
    """Reuse accepted controllers with call-local dependencies, never global mutation."""
    result=FunctionType(fn.__code__,{**fn.__globals__,**globals_},fn.__name__,fn.__defaults__)
    result.__kwdefaults__=fn.__kwdefaults__;return result


def prepare(repo: Path=ROOT, output: Path=BASE) -> dict:
    """Prepare unchanged full owner contexts, then specialize only their provider targets."""
    root=repo/output;require(not root.exists(),'OUTPUT_ALREADY_EXISTS')
    # The existing preparer verifies all frozen inputs and refuses unsafe paths.
    parent=previous.prepare(repo=repo,output=output/'contexts')
    pins=deepcopy(parent['inputPins']);pins.update(parent['implementationPins'])
    pins[str(semantic.CONTRACT.relative_to(ROOT))]=digest(semantic.CONTRACT.read_bytes())
    records=[];bundles=[];lines=[]
    for entry in parent['requests']:
        context=json.loads((root/'contexts/queue'/entry['bundleFile']).read_bytes())
        for group in semantic.inventory(entry['family']):
            p=semantic.build(context,group)
            require(len(canonical(p['body']))<=previous.sizing.SIZING['maxEnvelopeBytes'],'SPECIALIZED_ENVELOPE_TOO_LARGE')
            raw=canonical(p)+b'\n';name=digest(raw)+'.json';item,line=adapter.batch.input_line(p,1,adapter.fingerprint)
            records.append(dict(family=entry['family'],ownerID=entry['ownerID'],groupID=group,
                bundleFile=name,bundleSha256=digest(raw),identity=adapter.fingerprint(p),batchItem=item,cost=previous.sizing.costs(p)))
            bundles.append((name,raw));lines.append(line)
    manifest=dict(version=semantic.VERSION,requests=records,inputPins=parent['inputPins'],
        implementationPins={k:v for k,v in pins.items() if k not in parent['inputPins']},
        contextManifestSha256=digest((root/'contexts/queue-manifest.json').read_bytes()),
        pricing={'batch':adapter.batch.PRICING,'live':adapter.batch.baseline.PRICING},
        batchInputSha256=digest(b''.join(lines)),providerCalls=0,kgAuthorization=False,
        requestCountByOwner=dict(Counter(r['ownerID'] for r in records)),
        estimate=dict(requestCount=len(records),basis='native envelope-byte token heuristics and recorded pricing; not actual provider tokens or charges',
            batchScenariosUSD={k:sum(r['cost']['costUSD'][k] for r in records) for k in records[0]['cost']['costUSD']}))
    ratio=adapter.batch.baseline.PRICING['cacheWriteUSDPerMillion']/adapter.batch.PRICING['cacheWriteUSDPerMillion']
    require(ratio==adapter.batch.baseline.PRICING['outputUSDPerMillion']/adapter.batch.PRICING['outputUSDPerMillion'],'PRICING_RATIO_DRIFT')
    manifest['estimate']['liveScenariosUSD']={k:v*ratio for k,v in manifest['estimate']['batchScenariosUSD'].items()}
    (root/'queue').mkdir()
    for name,raw in bundles:
        with (root/'queue'/name).open('xb') as handle:handle.write(raw)
    for name,raw in [('queue-manifest.json',canonical(manifest)+b'\n'),('batch-input.jsonl',b''.join(lines))]:
        with (root/name).open('xb') as handle:handle.write(raw)
    with (root/'summary.md').open('x') as handle:
        handle.write('# Specialized source-local diagnostic v0.4.2\n\n'+
            '\n'.join(f"- {owner}: {count} requests" for owner,count in manifest['requestCountByOwner'].items())+
            '\n\nNine specialized requests, three full-source owners; no provider calls. Context bundles are validation authorities, not additional queued requests.\n\n'+
            json.dumps(manifest['estimate'],indent=2)+'\n')
    return manifest


def schema_coverage(family: str, schema: dict) -> dict:
    """Validate specialized schema coverage when reusing the native queue loader."""
    actual={target:{b['properties']['inventoryId']['enum'][0] for b in schema['properties'][key]['items']['anyOf']}
        for key,target in [('candidateNodes','entities'),('candidateEdges','relations')]}
    matches=[group for group,scope in semantic.inventory(family).items() if all(actual[k]==set(scope[k]) for k in actual)]
    require(len(matches)==1,'SPECIALIZED_SCHEMA_SCOPE_DRIFT');return {'groupID':matches[0]}


def load_queue(repo: Path, output: Path, expected_sha: str) -> tuple[dict,dict]:
    """Reuse hash/pin/Batch checks, then reconstruct each group and check owner completeness."""
    loader=bind(previous.load_queue,semantic=semantic,policy=SimpleNamespace(coverage=schema_coverage))
    manifest,bundles=loader(repo,output,expected_sha)
    root=repo/output
    require(digest((root/'contexts/queue-manifest.json').read_bytes())==manifest['contextManifestSha256'],'CONTEXT_MANIFEST_DRIFT')
    groups=defaultdict(set);contexts={}
    for p in bundles.values():
        semantic.verify(p);b=p['semanticRequest']['request'];owner=b['owner']['endpointID'];family=b['artifactFamily'];group=p['binding']['groupID']
        require(previous.OWNERS.get(family)==owner,'DIAGNOSTIC_OWNER_DRIFT')
        require(group not in groups[family],'DUPLICATE_GROUP');groups[family].add(group)
        context=p['requestInputs']['baseContext']
        require(family not in contexts or contexts[family]==context,'OWNER_CONTEXT_DRIFT');contexts[family]=context
    require(set(groups)==set(previous.OWNERS),'INCOMPLETE_FAMILIES')
    require(all(groups[f]==set(semantic.inventory(f)) for f in groups),'INCOMPLETE_OWNER_GROUPS')
    return manifest,bundles


def operate(operation,transport,queue_sha,*,repo=ROOT,output=BASE,capacity=None,api=None,live_call=None):
    """Delegate to unchanged raw-only journal controllers, with this queue bound locally."""
    return bind(previous.operate,load_queue=load_queue,semantic=semantic)(operation,transport,queue_sha,
        repo=repo,output=output,capacity=capacity,api=api,live_call=live_call)


def review(queue_sha: str, transport: str, *, repo: Path=ROOT, output: Path=BASE) -> dict:
    """Verify receipts read-only, replay each authentic group, then consolidate owners."""
    from src.evaluation import github_full_document_pilot_execution as execution
    from src.evaluation import hub_full_content_pilot_batch as hub
    from src.extraction.llm.publications.openai_provider import extract_model_output
    destination=repo/output/('review-'+transport)
    require(not destination.exists(),'REVIEW_ALREADY_EXISTS')
    parent,bundles=load_queue(repo,output,queue_sha)
    preflight=operate('preflight',transport,queue_sha,repo=repo,output=output)
    require(preflight.get('initialized') is not False,'NO_EXECUTION_JOURNAL')
    paired,native,_=adapter.infrastructure();root=repo/output/'execution'/transport
    raw=(root/'run-manifest.json').read_bytes()
    if transport=='live':
        Journal=execution.live_journal(native,paired,bundles)
    else:
        def verify_prepared(p,entry):
            """Native journal checks exact pinned specialized request bytes."""
            require(adapter.fingerprint(p)==entry['identity'] and digest(canonical(p)+b'\n')==entry['bundleSha256'],'BUNDLE_IDENTITY_DRIFT')
        Journal,_,_,_=bind(hub.infrastructure,verify_prepared=verify_prepared)()
    log=Journal(root/'execution.jsonl',raw,digest(raw))
    def payloads(log):
        """Read only verified completed responses; missing/held groups block consolidation."""
        result={}
        for rid in bundles:
            if transport=='live':
                state=log.events.get(rid,{})
                require(state.get('result',{}).get('status')=='completed' and not state['result']['holds'],'LIVE_RESPONSE_NOT_VERIFIED:'+rid)
                result[rid]=extract_model_output(json.loads(base64.b64decode(state['raw']['bytesBase64'],validate=True)))
            else:
                key=(rid,1);require(key in log.outcomes and key in log.receipts,'INCOMPLETE_BATCH_RESPONSE:'+rid)
                outcome=log.payload_at(log.outcomes[key])['native']
                require(outcome['processable'] and not outcome['transportHolds'],'BATCH_RESPONSE_NOT_VERIFIED:'+rid)
                receipt=log.payload_at(log.receipts[key])
                result[rid]=base64.b64decode(receipt['rawModelOutputBase64'],validate=True)
        return result
    responses=execution.readonly(log,native,payloads)
    by_owner=defaultdict(list);reports=[]
    for rid,p in sorted(bundles.items()):
        r=semantic.replay(p,responses[rid],expected_request_sha256=p['semanticRequest']['requestSha256'])
        reports.append((digest(rid.encode())+'.json',r));by_owner[p['semanticRequest']['request']['owner']['endpointID']].append((p,r))
    owners=[semantic.consolidate(items) for _,items in sorted(by_owner.items())]
    destination.mkdir();(destination/'groups').mkdir();(destination/'owners').mkdir()
    for name,r in reports:
        with (destination/'groups'/name).open('xb') as handle:handle.write(canonical(r)+b'\n')
    for r in owners:
        with (destination/'owners'/(digest(r['owner']['endpointID'].encode())+'.json')).open('xb') as handle:handle.write(canonical(r)+b'\n')
    summary=dict(output=str(destination),requests=len(reports),owners=len(owners),providerCalls=0,
        acceptedNodes=sum(len(r['nodes']) for r in owners),acceptedEdges=sum(len(r['edges']) for r in owners),
        derivedConstructionInputs=sum(len(r['derivedConstructionInputs']) for r in owners),kgAuthorization=False)
    with (destination/'summary.json').open('xb') as handle:handle.write(canonical(summary)+b'\n')
    return summary


def main():
    """Offline preparation/preflight/review block sockets; provider actions are explicit."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['prepare','preflight','submit','status','collect','review'])
    parser.add_argument('--output',type=Path,default=BASE);parser.add_argument('--queue-sha256')
    parser.add_argument('--transport',choices=['live','batch'],default='live');parser.add_argument('--queued-token-limit',type=int)
    args=parser.parse_args()
    def run():
        """Dispatch without implicitly submitting or recovering provider work."""
        if args.operation=='prepare':
            m=prepare(output=args.output)
            return dict(queue=str(args.output),queueSha256=digest((ROOT/args.output/'queue-manifest.json').read_bytes()),
                requestCountByOwner=m['requestCountByOwner'],estimate=m['estimate'],providerCalls=0)
        require(args.queue_sha256,'EXPLICIT_QUEUE_SHA256_REQUIRED')
        if args.operation=='review':return review(args.queue_sha256,args.transport,output=args.output)
        return operate(args.operation,args.transport,args.queue_sha256,output=args.output,capacity=args.queued_token_limit)
    if args.operation in {'prepare','preflight','review'}:
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):result=run()
    else:result=run()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
