"""Offline prepare/replay and explicitly invoked native live/Batch diagnostic pilot.

Preparation selects three source owners without running extraction. Execution uses
existing durable transport and pricing, never an alternate HTTP/retry controller.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
from types import FunctionType, SimpleNamespace
from unittest.mock import patch

from src.extraction.llm import source_local_semantics as semantic
from src.extraction.llm import source_local_profile as policy
from src.extraction.llm import source_family_batch as adapter
from src.extraction.llm import source_family_queue as sizing
from src.extraction.llm.pilot_preflight import canonical, digest

ROOT=Path(__file__).resolve().parents[2]
BASE=Path('var/study2_step13/source-local-semantic-pilot/v041')
ORIGINAL=Path('var/study2_step13/source-families-gpt61-batch/v1')
RECOVERY=Path('var/study2_step13/hydroshare-readme-recovery/v2')
RECOVERY_SHA='57dab8abb6c4a78dbe6c22d184032872ae68764520e150c25de2ff40b084014c'
OWNERS={'hydroshare':'7477452a93e04b1099a3879353c2253a','github':'github:repo:697372188','ciroh_hub':'hub:page:c13b515845081546d688'}
GRAPHS={'hydroshare':'data/interim/datasets/hydroshare_nodes_edges_v016.json',
        'github':'data/interim/coderepos/github_nodes_edges_refs_v1.json',
        'ciroh_hub':'data/interim/documents/ciroh_hub_nodes_edges_refs_v1.json'}
require=semantic.require


def catalog(graph: dict, body: dict, graph_path: str, graph_sha: str) -> tuple[list,list,list]:
    """Retain exact source-local native provenance and deferred records, without promotion."""
    family=body['artifactFamily'];owner=body['owner']['endpointID'];profile=semantic.profiles.get_profile(family,version=semantic.VERSION)
    owners=[n for n in graph['nodes'] if n['id']==owner]
    require(len(owners)==1,'DETERMINISTIC_OWNER_MISSING_OR_AMBIGUOUS')
    source=owners[0]['evidence']['sourceArtifact'];endpoints=[]
    for node in graph['nodes']:
        target=profile['entities'].get(node.get('inventoryId'))
        if node['id']!=owner and target and node['class']==target['declaration']['name'] and node.get('evidence',{}).get('sourceArtifact')==source:
            endpoints.append(dict(endpointID=node['id'],inventoryId=node['inventoryId'],**{'class':node['class']},
                attributes=deepcopy(node.get('attributes',{})),nativeRecord=deepcopy(node),nativeGraphSha256=graph_sha))
    known={owner,*(e['endpointID'] for e in endpoints)};assertions=[]
    for edge in graph['edges']:
        identifier=edge['inventoryId']
        # Exact legacy alias is retained in nativeRecord, not rewritten in the graph.
        if family=='github' and identifier=='D-05' and edge['relation']=='referencesDataset':identifier='C-C19'
        if identifier in profile['relations'] and edge['source'] in known and edge['target'] in known and edge.get('evidence',{}).get('sourceArtifact')==source:
            assertions.append(dict(assertionID=edge['id'],inventoryId=identifier,relation=edge['relation'],sourceID=edge['source'],targetID=edge['target'],nativeRecord=deepcopy(edge),nativeGraphSha256=graph_sha))
    deferred=[]
    for category in ('deferred','unresolved'):
        for index,record in enumerate(graph.get(category,[])):
            belongs=(family=='github' and record.get('repoId')==body['owner'].get('repo_id') or
                     family=='ciroh_hub' and record.get('pageUrl')==body['owner'].get('canonical_url') or
                     family=='hydroshare' and record.get('resource_id')==owner)
            if belongs:
                deferred.append(dict(recordID=record.get('id'),sourceRecordReference=f'{graph_path}#/{category}/{index}',
                    sourceGraphSha256=graph_sha,originalRecord=deepcopy(record),disposition='unresolved_source_record_not_promoted'))
    return endpoints,assertions,deferred


def implementation_pins(repo: Path) -> dict:
    """Pin executed semantic, source, transport and contract code, including opt-in edits."""
    paths=set()
    for base in ('src/extraction/llm','src/evaluation'):
        # Hashing files is not execution; scope includes transitive dynamic adapter imports.
        paths.update(p for p in (repo/base).rglob('*.py'))
    paths.update([repo/'src/ontology/ontology_spec.yaml',repo/'docs/study2_source_local_semantics_v0.4.md',policy.INVENTORY,policy.POLICY_PATH])
    return {str(p.relative_to(repo)):digest(p.read_bytes()) for p in sorted(paths)}


def prepare(repo: Path=ROOT, output: Path=BASE) -> dict:
    """Prepare exactly three diagnostic owners with replacement-aware HydroShare input."""
    root=repo/output
    require(not root.exists(),'OUTPUT_ALREADY_EXISTS')
    require(not output.is_absolute() and '..' not in output.parts and output.parts[:3]==('var','study2_step13','source-local-semantic-pilot') and len(output.parts)>=4,'OUTPUT_MUST_BE_IGNORED_STUDY2_DIRECTORY')
    require(not any(root.resolve()==(repo/p).resolve() or (repo/p).resolve() in root.resolve().parents for p in (ORIGINAL,RECOVERY)),'PRODUCTION_OUTPUT_FORBIDDEN')
    require(subprocess.run(['git','check-ignore','-q',str(output/'queue-manifest.json')],cwd=repo).returncode==0,'OUTPUT_NOT_IGNORED')
    pins={}
    def read(path):
        """Read and pin exact source bytes, never regenerate missing artifacts."""
        raw=(repo/path).read_bytes();pins[str(path)]=digest(raw);return json.loads(raw)
    original=read(ORIGINAL/'queue-manifest.json');recovery=read(RECOVERY/'queue-manifest.json')
    require(pins[str(RECOVERY/'queue-manifest.json')]==RECOVERY_SHA,'RECOVERY_QUEUE_DRIFT')
    corpus_path='data/interim/coderepos/ciroh_github_corpus.json';github_corpus=read(Path(corpus_path))
    require(pins[corpus_path]==original['sourcePins'][corpus_path],'GITHUB_CORPUS_DRIFT')
    from src.evaluation.semantic_coverage_diagnosis import Authorities
    resolver=Authorities(repo,{'github':github_corpus,'ciroh_hub':{'pages':[]}})
    records=[];bundles=[];lines=[];coverage={}
    for family,owner in OWNERS.items():
        queue=recovery if family=='hydroshare' else original;parent=RECOVERY if family=='hydroshare' else ORIGINAL
        entries=[e for e in queue['requests'] if e['family']==family and e['ownerID']==owner]
        require(entries,'PILOT_OWNER_NOT_FOUND:'+family)
        templates=[]
        for entry in entries:
            path=parent/'queue'/entry['bundleFile'];t=read(path)
            require(pins[str(path)]==entry['bundleSha256'] and adapter.fingerprint(t)==entry['identity'],'SOURCE_BUNDLE_DRIFT')
            if family=='github':
                for authority in t['requestInputs']['reader_result']['authorities']:
                    current=resolver.get(family,owner,authority)
                    require(current['text']==authority['text'],'ACQUIRED_AUTHORITY_DRIFT')
            templates.append(t)
        graph_path=Path(GRAPHS[family]);graph=read(graph_path)
        endpoints,assertions,deferred=catalog(graph,templates[0]['semanticRequest']['request'],str(graph_path),pins[str(graph_path)])
        if family=='github':
            from src.extraction.llm.source_local_versions import SUPPORTED, fields
            source=next(r for r in github_corpus['repos'] if 'github:repo:'+str(r['repo_id'])==owner)
            paths=sorted({e.get('attributes',{}).get('sourcePath','') for e in endpoints
                if e['inventoryId'] in {'A-C10','A-DOM02'} and Path(e.get('attributes',{}).get('sourcePath','')).name.lower() in SUPPORTED})
            versions=[]
            for source_path in paths:
                files=[f for f in source['files']['inventory'] if f['path']==source_path and f['downloaded']]
                require(len(files)==1,'VERSION_FILE_AUTHORITY_MISSING')
                raw_path=Path('data/raw/coderepos')/source['name']/'contents'/source_path
                require((repo/'data/raw/coderepos').resolve() in (repo/raw_path).resolve().parents,'UNSAFE_VERSION_PATH')
                raw=(repo/raw_path).read_bytes();pins[str(raw_path)]=digest(raw);text=raw.decode('utf-8')
                try: values,_=fields(source_path,text)
                except ValueError:
                    deferred.append(dict(sourceRecordReference=str(raw_path),sourceGraphSha256=pins[str(graph_path)],
                        disposition='ambiguous_or_dynamic_structured_version',rawSha256=digest(raw)))
                    continue
                if Path(source_path).name.lower()=='citation.cff':
                    frozen=[dict(title=source['citation']['title'],version=source['citation']['version'])]
                else:
                    frozen=[dict(title=m['name'],version=m['version']) for m in source['software_metadata'] if m['source_path']==source_path]
                require(values in frozen,'VERSION_FROZEN_FIELDS_DRIFT')
                versions.append(dict(templates[0]['requestInputs']['accepted_repository'],path=source_path,cellIndex=None,
                    authorityKind='downloaded_file',text=text,rawFileSha256=digest(raw),authorityTextSha256=digest(text.encode()),
                    acquisitionIntegrityStatus='not_independently_verified; root fields equal frozen Phase A',sourceCorpusSha256=pins[corpus_path]))
            templates[0]=deepcopy(templates[0]);templates[0]['requestInputs']['versionAuthorities']=versions
        p=semantic.build(templates,deterministic_endpoints=endpoints,deterministic_assertions=assertions,deferred_records=deferred,
            deterministic_catalog_authority=dict(path=str(graph_path),sha256=pins[str(graph_path)],completeOwnerCatalog=True))
        require(sizing.fits(p['semanticRequest']['request']['sourceUnits']) and len(canonical(p['body']))<=sizing.SIZING['maxEnvelopeBytes'],'OWNER_CONTEXT_REQUIRES_EXPLICIT_STRUCTURAL_SUBDIVISION:'+owner)
        raw=canonical(p)+b'\n';name=digest(raw)+'.json';item,line=adapter.batch.input_line(p,1,adapter.fingerprint)
        cost=sizing.costs(p);records.append(dict(family=family,ownerID=owner,bundleFile=name,bundleSha256=digest(raw),identity=adapter.fingerprint(p),batchItem=item,cost=cost))
        bundles.append((name,raw));lines.append(line);coverage[family]=p['semanticRequest']['request']['executableCoverage']
    pins.update(resolver.raw_hashes)
    manifest=dict(version=semantic.VERSION,requests=records,inputPins=pins,implementationPins=implementation_pins(repo),
        batchInputSha256=digest(b''.join(lines)),providerCalls=0,kgAuthorization=False,
        scope='three-owner diagnostic, not family version selection',coverage=coverage,
        estimate=dict(requestCount=3,basis='actual prepared envelope bytes; native heuristic token scenarios, not measured provider tokens',
            batchScenariosUSD={k:sum(r['cost']['costUSD'][k] for r in records) for k in records[0]['cost']['costUSD']},
            eventualOwnerLowerBound={f:len({e['ownerID'] for e in original['requests'] if e['family']==f}) for f in OWNERS},
            productionEstimate='not extrapolated from three selected diagnostic owners; requires preparation of all complete owner contexts'))
    root.mkdir(parents=True,exist_ok=False);(root/'queue').mkdir()
    for name,raw in bundles:
        with (root/'queue'/name).open('xb') as handle:handle.write(raw)
    with (root/'batch-input.jsonl').open('xb') as handle:handle.write(b''.join(lines))
    with (root/'queue-manifest.json').open('xb') as handle:handle.write(canonical(manifest)+b'\n')
    with (root/'summary.md').open('x') as handle:
        handle.write('# Source-local semantic diagnostic v0.4\n\nThree complete owner contexts, zero provider calls. '
            'Existing runs unchanged. Live and Batch execution use the existing durable controller.\n\n'
            'The queue manifest contains executable coverage, input/code pins, deferred provenance and native token/cost scenarios. '
            'No three-family production cost extrapolation is warranted from this diagnostic selection.\n')
    return manifest


def load_queue(repo: Path, output: Path, expected_sha: str) -> tuple[dict,dict]:
    """Check the caller-pinned queue, all source/code pins and exact provider lines."""
    raw=(repo/output/'queue-manifest.json').read_bytes();require(digest(raw)==expected_sha,'QUEUE_MANIFEST_DRIFT')
    manifest=json.loads(raw);require(manifest['version']==semantic.VERSION,'PROSPECTIVE_VERSION_DRIFT')
    for group in ('inputPins','implementationPins'):
        for path,expected in manifest[group].items():require(digest((repo/path).read_bytes())==expected,'PIN_DRIFT:'+path)
    bundles={};lines=[]
    for entry in manifest['requests']:
        raw=(repo/output/'queue'/entry['bundleFile']).read_bytes();require(digest(raw)==entry['bundleSha256'],'BUNDLE_DRIFT')
        p=json.loads(raw);require(adapter.fingerprint(p)==entry['identity'],'REQUEST_IDENTITY_DRIFT')
        require(p['binding']['version']==semantic.VERSION,'WRONG_SEMANTIC_ROUTE')
        policy.coverage(entry['family'],p['body']['text']['format']['schema'])
        rid=p['request']['requestID'];require(rid not in bundles,'DUPLICATE_REQUEST');bundles[rid]=p
        item,line=adapter.batch.input_line(p,1,adapter.fingerprint);require(item==entry['batchItem'],'BATCH_ITEM_DRIFT');lines.append(line)
    require((repo/output/'batch-input.jsonl').read_bytes()==b''.join(lines) and digest(b''.join(lines))==manifest['batchInputSha256'],'BATCH_INPUT_DRIFT')
    return manifest,bundles


def operate(operation: str, transport: str, queue_sha: str, *, repo: Path=ROOT, output: Path=BASE, capacity=None, api=None, live_call=None) -> dict:
    """Bind existing live/Batch journal operations locally; no global monkeypatching."""
    from src.evaluation import github_full_document_pilot_execution as execution
    from src.evaluation import hub_full_content_pilot_batch as hub
    parent,bundles=load_queue(repo,output,queue_sha)
    def verify(p,entry):
        """Validate immutable bundles at every native journal boundary."""
        require(digest(canonical(p)+b'\n')==entry['bundleSha256'] and adapter.fingerprint(p)==entry['identity'],'BUNDLE_IDENTITY_DRIFT')
    infra=FunctionType(hub.infrastructure.__code__,{**hub.__dict__,'verify_prepared':verify},'infrastructure')
    def helpers():
        """Supply only queue/journal dependencies to the unchanged transport loop."""
        return {'load_queue':lambda repo:(parent,bundles),'infrastructure':infra}
    def manifest(parent,pins,transport,capacity):
        """Version diagnostic transport configuration independently of immutable queue."""
        if transport=='batch':require(type(capacity) is int and capacity>0,'QUEUED_TOKEN_LIMIT_REQUIRED')
        entries=deepcopy(parent['requests'])
        for e in entries:e['estimatedCostUSD']=e['cost']['costUSD']['pooled']
        return dict(version=semantic.VERSION+'/execution',transport=transport,parentSha256=queue_sha,generatorPins=pins,
            implementationPins=parent['implementationPins'],requests=entries,queuedTokenLimit=capacity,
            meaningfulSampleRequests=len(entries),maximumAttemptsPerRequest=1,
            pricing=adapter.batch.PRICING if transport=='batch' else adapter.batch.baseline.PRICING,
            scientificStatus='not_evaluated',kgAuthorization=False)
    fn=execution.operate
    bound=FunctionType(fn.__code__,{**fn.__globals__,'pilot':SimpleNamespace(BASE=output),'QUEUE_SHA':queue_sha,
        'bound_helpers':helpers,'execution_manifest':manifest},fn.__name__,fn.__defaults__)
    bound.__kwdefaults__=fn.__kwdefaults__
    result=bound(operation,transport,capacity,repo=repo,api=api,live_call=live_call)
    if 'requests' in result and isinstance(result['requests'],int):result['requests']=len(bundles)
    return result


def review_live(queue_sha: str, *, repo: Path=ROOT, output: Path=BASE) -> dict:
    """Replay durably recorded successful live responses offline, with native chain validation."""
    destination=repo/output/'review-live'
    if destination.exists():raise FileExistsError('REVIEW_ALREADY_EXISTS')
    from src.evaluation import github_full_document_pilot_execution as execution
    from src.extraction.llm.publications.openai_provider import extract_model_output
    parent,bundles=load_queue(repo,output,queue_sha)
    preflight=operate('preflight','live',queue_sha,repo=repo,output=output)
    require(preflight.get('initialized') is not False,'NO_LIVE_JOURNAL')
    paired,native,_=adapter.infrastructure()
    root=repo/output/'execution/live';raw=(root/'run-manifest.json').read_bytes()
    Journal=execution.live_journal(native,paired,bundles)
    log=Journal(root/'execution.jsonl',raw,digest(raw))
    events=execution.readonly(log,native,lambda log:deepcopy(log.events))
    reports=[]
    for rid,p in bundles.items():
        state=events.get(rid,{})
        require(state.get('result',{}).get('status')=='completed' and not state['result']['holds'],'LIVE_RESPONSE_NOT_VERIFIED:'+rid)
        response=json.loads(base64.b64decode(state['raw']['bytesBase64'],validate=True))
        result=semantic.replay(p,extract_model_output(response),expected_request_sha256=p['semanticRequest']['requestSha256'])
        reports.append((digest(rid.encode())+'.json',result))
    destination=repo/output/'review-live'
    destination.mkdir(exist_ok=False)
    for name,result in reports:
        with (destination/name).open('xb') as handle:handle.write(canonical(result)+b'\n')
    return dict(output=str(destination),requests=len(reports),providerCalls=0,
                acceptedNodes=sum(len(r['projection']['nodes']) for _,r in reports),
                acceptedEdges=sum(len(r['projection']['edges']) for _,r in reports),
                unresolved=sum(len(r['unresolvedAssertions']) for _,r in reports),kgAuthorization=False)


def replay_file(prepared: Path, response: Path, output: Path) -> dict:
    """Replay one recorded model payload offline into a new immutable report file."""
    require(not output.exists(),'OUTPUT_ALREADY_EXISTS')
    require((ROOT/BASE.parent).resolve() in output.resolve().parents,'REPORT_MUST_STAY_IN_PROSPECTIVE_PILOT_ROOT')
    p=json.loads(prepared.read_bytes())
    report=semantic.replay(p,response.read_bytes(),expected_request_sha256=p['semanticRequest']['requestSha256'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as handle:handle.write(canonical(report)+b'\n')
    return dict(report=str(output),reportSha256=report['reportSha256'],zeroYield=report['zeroYield'])


def main() -> None:
    """Offline commands block sockets; submit/status/collect are explicit researcher actions."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['prepare','preflight','submit','status','collect','replay','review-live'])
    parser.add_argument('--output',type=Path,default=BASE);parser.add_argument('--queue-sha256')
    parser.add_argument('--transport',choices=['live','batch'],default='live');parser.add_argument('--queued-token-limit',type=int)
    parser.add_argument('--prepared',type=Path);parser.add_argument('--response',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    def run():
        """Dispatch the selected operation without implicit provider work."""
        if args.operation=='prepare':
            manifest=prepare(output=args.output)
            return dict(queue=str(args.output),queueSha256=digest((ROOT/args.output/'queue-manifest.json').read_bytes()),estimate=manifest['estimate'],providerCalls=0)
        if args.operation=='replay':
            require(all([args.prepared,args.response,args.report]),'PREPARED_RESPONSE_REPORT_REQUIRED')
            return replay_file(args.prepared,args.response,args.report)
        require(args.queue_sha256,'EXPLICIT_QUEUE_SHA256_REQUIRED')
        if args.operation=='review-live':
            return review_live(args.queue_sha256,output=args.output)
        return operate(args.operation,args.transport,args.queue_sha256,output=args.output,capacity=args.queued_token_limit)
    if args.operation in ('prepare','preflight','replay','review-live'):
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
            result=run()
    else:result=run()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
