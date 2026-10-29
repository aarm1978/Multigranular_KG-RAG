"""Full-inventory offline preparation using unchanged source-local v0.4.2 contracts.

Incomplete preparation is inspectable but cannot be submitted. No implicit source
splitting, eligibility relaxation, semantic replay, or provider calls in prepare.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from src.evaluation import source_local_semantic_pilot as previous
from src.evaluation import source_local_specialized_pilot as specialized
from src.extraction.llm import source_family_inputs as sources
from src.extraction.llm import source_local_semantics as semantic
from src.extraction.llm import source_local_specialized as grouped
from src.extraction.llm.pilot_preflight import canonical, digest

ROOT=previous.ROOT
BASE=Path('var/study2_step13/source-local-specialized-production/v6')
VERSION='study2-source-local-production-selection/1.3.0'
GRAPHS=previous.GRAPHS
adapter=previous.adapter
require=semantic.require
CORPORA={'hydroshare':'data/interim/datasets/ciroh_hydroshare_corpus.json',
         'github':'data/interim/coderepos/ciroh_github_corpus.json',
         'ciroh_hub':'data/interim/documents/ciroh_hub_corpus.json'}

SIZING={**deepcopy(previous.sizing.SIZING),
    'version':'source-local-specialized-production-sizing/1.1.0',
    'maxSelectedTextBytes':262144,
    'grouping':{f:'complete_owner_context_shared_by_specialized_groups' for f in CORPORA},
    'rationale':'Measured all 335 frozen contexts after removing provider historical diagnostics: '
        'maximum source 255288 UTF-8 bytes; maximum specialized envelope 347760 bytes. '
        'Use a 256 KiB source planning margin with the unchanged 1 MB envelope and 32768 output-token ceiling. '
        'No source splitting, filtering, cache assumption or output-completeness guarantee; native truncation holds remain.'}


def source_fits(units: list) -> bool:
    """Apply the measured prospective text margin without modifying any source unit."""
    return sum(len(u['text'].encode()) for u in units)<=SIZING['maxSelectedTextBytes']


@contextmanager
def ontology_parse_cache():
    """Cache only YAML parsing; native hash/version checks still run on every read.

    Imported aliases of load_ontology retain its original global namespace. The
    invocation-local YAML facade therefore also accelerates those unchanged
    callers. Every result is detached; the original module binding is restored.
    """
    original=semantic.profiles.yaml.safe_load
    cached={}
    def parse(raw):
        """Reuse only exactly identical ontology bytes, never shared mutable results."""
        if raw not in cached:cached[raw]=original(raw)
        return deepcopy(cached[raw])
    with patch.object(semantic.profiles,'yaml',SimpleNamespace(safe_load=parse)):
        yield


def ontology_authority_report(repo: Path=ROOT) -> dict:
    """Verify frozen bytes and expose profile/validator authority conflicts without repair."""
    import yaml
    spec=semantic.profiles.load_ontology()
    ontology_path='src/ontology/ontology_spec.yaml'
    sha=digest((repo/ontology_path).read_bytes())
    require(sha==semantic.profiles.ONTOLOGY_SHA256 and spec['ontology']['version']=='0.1.7','FROZEN_ONTOLOGY_DRIFT')
    declarations={kind:{d['id']:d for d in spec[key]} for kind,key in [('entities','classes'),('relations','relations')]}
    profiles={};discrepancies=[]
    for family in CORPORA:
        profile=semantic.profiles.get_profile(family,version=semantic.VERSION);differences=[]
        for kind in declarations:
            for identifier,target in profile[kind].items():
                actual=target['declaration'];expected=declarations[kind].get(identifier)
                if actual!=expected:
                    differences.append(dict(inventoryId=identifier,frozenDeclaration=expected,profileDeclaration=actual))
        profiles[family]=dict(ontologyVersion=profile['ontologyVersion'],baseOntologyVersion=profile.get('baseOntologyVersion'),
            declarationDifferences=differences,signatureExtensions=profile.get('signatureExtensions',{}))
        if differences or profile['ontologyVersion']!='0.1.7':
            discrepancies.append(dict(family=family,reason='profile_not_exact_frozen_v017',inventoryIDs=[d['inventoryId'] for d in differences]))
    checks=[]
    for family,identifier,owner in [('github','C-C15','A-C01'),('ciroh_hub','C-DC25','A-DC01')]:
        profile=semantic.profiles.get_profile(family,version=semantic.VERSION);target=profile['relations'][identifier]
        check=semantic.profiles.check_target(family,identifier,version=semantic.VERSION,
            relation_name=target['declaration']['name'],source_class_id=owner,target_class_id='A-P25',
            gates={k:True for k in target['requiredGates']})
        checks.append(dict(family=family,inventoryId=identifier,targetClass='DatasetMention',
            structuralScopePass=check['structuralScopePass'],reasons=check['reasons'],
            meaning='Synthetic signature-only counterexample; not evidence validation or an accepted assertion.'))
    publication_path='src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml'
    raw=(repo/publication_path).read_bytes();publication=yaml.safe_load(raw)['ontology']
    history=dict(profilePath=publication_path,profileSha256=digest(raw),recordedAuthority=publication,
        matchesCurrentFrozenOntology=publication['version']=='0.1.7' and publication['spec_sha256_of_reviewed_copy']==sha,
        historicalOutputsModified=False)
    generator='var/study2_step13/publication-extraction-plan/v0.1/preflight.py'
    manifest=repo/'var/study2_step13/publications-gpt61-batch/v1/run-manifest.json'
    if manifest.exists() and (repo/generator).exists():
        m=json.loads(manifest.read_bytes());history.update(generatorPath=generator,generatorSha256=digest((repo/generator).read_bytes()),
            runManifestSha256=digest(manifest.read_bytes()),generatorMatchesCompletedRunPin=m['generatorPins'].get(generator)==digest((repo/generator).read_bytes()),
            authorityEvidence='build(): q[authorities][ontology] explicitly uses the reviewed v0.1.5 profile; prospectiveSourceUnitAuthority is separate.')
    return dict(version='source-local-ontology-authority-check/1.1',
        frozen=dict(path=ontology_path,version='0.1.7',sha256=sha),profiles=profiles,validatorSignatureChecks=checks,
        threeFamilyExact=not discrepancies,threeFamilyDiscrepancies=discrepancies,completedPublications=history,
        providerCalls=0,ontologyModified=False)


def owner_inventory(original: dict, recovery: dict, corpora: dict) -> list[dict]:
    """Reconcile whole frozen inventories, not only historically nonempty requests."""
    rows=[]
    for family,corpus in corpora.items():
        records=corpus if family=='hydroshare' else corpus['repos' if family=='github' else 'pages']
        seen=set()
        historical={e['ownerID'] for e in original['requests'] if e['family']==family}
        recovered={e['ownerID'] for e in recovery['requests'] if e['family']==family}
        require(family=='hydroshare' or not recovered,'RECOVERY_FAMILY_DRIFT')
        for record in records:
            owner=(record['resource_id'] if family=='hydroshare' else
                'github:repo:'+str(record['repo_id']) if family=='github' else
                'hub:page:'+digest(record['canonical_url'].encode())[:20])
            require(owner not in seen,'DUPLICATE_SOURCE_OWNER:'+owner);seen.add(owner)
            rows.append(dict(family=family,ownerID=owner,sourceRecordSha256=digest(canonical(record)),
                sourceSelection='recovery' if owner in recovered else 'original' if owner in historical else 'frozen_corpus_full_content',
                previouslyUnqueued=owner not in historical,
                sourceURL=record.get('canonical_url',record.get('html_url'))))
        require(historical<=seen and recovered<=historical,'OWNER_INVENTORY_MISMATCH:'+family)
        require(len(seen)==original['summary'][family]['owners'],'FROZEN_OWNER_COUNT_DRIFT:'+family)
        require(family=='ciroh_hub' or seen==historical,'UNEXPECTED_UNQUEUED_OWNER:'+family)
    extra=[r for r in rows if r['previouslyUnqueued']]
    require(len(extra)==3 and all(r['family']=='ciroh_hub' for r in extra),'UNQUEUED_HUB_INVENTORY_DRIFT')
    require(sum(r['sourceSelection']=='recovery' for r in rows)==20,'RECOVERY_OWNER_COUNT_DRIFT')
    return sorted(rows,key=lambda r:(r['family'],r['ownerID']))


def context(templates: list, family: str, owner: str, *, repo: Path, pins: dict,
            github_corpus: dict, read) -> dict:
    """Reuse the pilot's exact catalog and structured own-product version preparation."""
    corpus_path=CORPORA['github']
    graph_path=Path(GRAPHS[family]);graph=read(graph_path)
    endpoints,assertions,deferred=previous.catalog(graph,templates[0]['semanticRequest']['request'],str(graph_path),pins[str(graph_path)])
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
    return p


def full_hub_template(owner: dict) -> dict:
    """Seed newly included pages with native inventory/transport, without pilot metadata."""
    from src.evaluation import hub_full_content_pilot as hub
    from src.extraction.llm.documents import request_contract as contract
    inputs=owner['inputs'];hub.verified_reader(inputs)
    page=inputs['page'];text=page['content_mdx'];uid=hub.full_unit_id(page)
    unit=dict(artifactFamily='ciroh_hub',sourceUnitID=uid,page_key=page['page_key'],
        canonical_url=page['canonical_url'],content_sha256=page['content_sha256'],text=text,
        startOffsetInAuthority=0,endOffsetInAuthority=len(text),startLine=1,
        endLine=hub._line(text,len(text)-1),sectionID=None,contentKind='complete_materialized_mdx',eligibility='literal_authority')
    request=contract._finish(dict(endpointID=owner['ownerID'],inventoryId='A-DC01',**{'class':'DocumentationPage'},
        page_key=page['page_key'],canonical_url=page['canonical_url']),[unit],[uid],
        dict(fullAuthorityComplete=True,scientificEligibilityComplete=False),inputs['reader_result']['diagnostics'],
        inputs['accepted_endpoints'],inputs['accepted_assertions'],request_version=contract.WAVE_C_REQUEST_VERSION)
    require(request['status']=='request_ready','FULL_PAGE_SEED_REJECTED')
    return adapter.prepare(request,inputs)


def check_groups(rows: list, requests: list) -> None:
    """Require exact owner/group coverage and reject duplicates or excluded owners."""
    require(all(r['status'] in {'prepared','blocked'} for r in rows),'UNKNOWN_OWNER_STATUS')
    require(len({(r['family'],r['ownerID']) for r in rows})==len(rows),'DUPLICATE_OWNER_ROW')
    scopes={f:set(grouped.inventory(f)) for f in {r['family'] for r in rows}}
    expected={(r['family'],r['ownerID']):scopes[r['family']] for r in rows if r['status']=='prepared'}
    actual=defaultdict(set)
    for e in requests:
        key=(e['family'],e['ownerID']);group=e['groupID']
        require(key in expected and group not in actual[key],'UNEXPECTED_OR_DUPLICATE_OWNER_GROUP')
        actual[key].add(group)
    require(dict(actual)==expected,'INCOMPLETE_OWNER_GROUPS')


def prepare(repo: Path=ROOT, output: Path=BASE) -> dict:
    """Seal all owner selections; retain size/failure holds and forbid partial submission."""
    require(not output.is_absolute() and '..' not in output.parts and output.parts[:3]==BASE.parts[:3]
            and len(output.parts)>=4,'OUTPUT_MUST_BE_ISOLATED')
    root=repo/output;require(not root.exists(),'OUTPUT_ALREADY_EXISTS')
    require(subprocess.run(['git','check-ignore','-q',str(output/'queue-manifest.json')],cwd=repo).returncode==0,'OUTPUT_NOT_IGNORED')
    pins={};cache={}
    def read(path):
        """Pin original bytes; cache parsed immutable authorities within this preparation."""
        path=str(path)
        if path not in cache:
            raw=(repo/path).read_bytes();pins[path]=digest(raw);cache[path]=json.loads(raw)
        return deepcopy(cache[path])
    original=read(previous.ORIGINAL/'queue-manifest.json');recovery=read(previous.RECOVERY/'queue-manifest.json')
    require(pins[str(previous.RECOVERY/'queue-manifest.json')]==previous.RECOVERY_SHA,'RECOVERY_QUEUE_DRIFT')
    corpora={f:read(p) for f,p in CORPORA.items()}
    for path,sha in original['sourcePins'].items():
        require(digest((repo/path).read_bytes())==sha,'HISTORICAL_SOURCE_DRIFT:'+path);pins[path]=sha
    rows=owner_inventory(original,recovery,corpora)
    ontology_report=ontology_authority_report(repo)
    implementation=previous.implementation_pins(repo)
    for path in (grouped.CONTRACT,Path(__file__).resolve().parents[2]/'docs/study2_source_local_production_selection_v1.md'):
        implementation[str(path.relative_to(repo))]=digest(path.read_bytes())
    from src.evaluation.semantic_coverage_diagnosis import Authorities
    from src.evaluation import hub_full_content_pilot as hub
    from src.extraction.llm.source_local_hub_evidence import regions
    resolver=Authorities(repo,{'github':corpora['github'],'ciroh_hub':corpora['ciroh_hub']})
    root.mkdir(parents=True,exist_ok=False);(root/'queue').mkdir();(root/'contexts').mkdir()
    requests=[];lines=[]
    def write(name,data):
        """Create an immutable artifact without replacing an existing file."""
        raw=canonical(data)+b'\n'
        with (root/name).open('xb') as handle:handle.write(raw)
        return digest(raw)
    for index,row in enumerate(rows):
        family,owner=row['family'],row['ownerID'];templates=[]
        parent=previous.RECOVERY if row['sourceSelection']=='recovery' else previous.ORIGINAL
        manifest=recovery if row['sourceSelection']=='recovery' else original
        entries=[e for e in manifest['requests'] if e['family']==family and e['ownerID']==owner]
        row['historicalBundles']=[]
        try:
            for e in entries:
                path=parent/'queue'/e['bundleFile'];t=read(path)
                require(pins[str(path)]==e['bundleSha256'] and adapter.fingerprint(t)==e['identity'],'SOURCE_BUNDLE_DRIFT')
                row['historicalBundles'].append(dict(path=str(path),sha256=pins[str(path)],identity=e['identity']))
                if family=='github':
                    for authority in t['requestInputs']['reader_result']['authorities']:
                        require(resolver.get(family,owner,authority)['text']==authority['text'],'ACQUIRED_AUTHORITY_DRIFT')
                templates.append(t)
            if row['previouslyUnqueued']:
                page=next(p for p in corpora['ciroh_hub']['pages'] if p['canonical_url']==row['sourceURL'])
                graph=read(hub.GRAPH)
                source_owner=next(sources.owners(repo,{'ciroh_hub':dict(records=[page],graph=graph,sourceSha256=pins[CORPORA['ciroh_hub']])}))
                templates=[full_hub_template(source_owner)]
                row['materializedRegionCharacters']=dict(Counter(regions(page['content_mdx'])))
                row['historicalEmptyReader']=not source_owner['units']
                row['eligibilityNote']='Complete authoritative MDX supplied; dynamic/code/uncertain regions remain subject to unchanged v0.4.1 evidence holds. Empty yield is legitimate.'
            p=context(templates,family,owner,repo=repo,pins=pins,github_corpus=corpora['github'],read=read)
            units=p['semanticRequest']['request']['sourceUnits']
            row['sources']=[dict(sourceUnitID=u['sourceUnitID'],textSha256=digest(u['text'].encode()),
                utf8Bytes=len(u['text'].encode()),provenance={k:v for k,v in u.items() if k!='text'}) for u in units]
            row['sourceBytes']=sum(u['utf8Bytes'] for u in row['sources'])
            name='contexts/'+digest(owner.encode())+'.json'
            row['contextFile']=name;row['contextSha256']=write(name,p)
            require(source_fits(units),'OWNER_CONTEXT_REQUIRES_EXPLICIT_STRUCTURAL_SUBDIVISION')
            prepared=[]
            for group in grouped.inventory(family):
                q=grouped.build(p,group,provider_projection_version=grouped.PROVIDER_PROJECTION_VERSION)
                require(len(canonical(q['body']))<=SIZING['maxEnvelopeBytes'],'SPECIALIZED_ENVELOPE_TOO_LARGE')
                prepared.append((group,q))
            for group,q in prepared:
                raw=canonical(q)+b'\n';name=digest(raw)+'.json'
                item,line=adapter.batch.input_line(q,1,adapter.fingerprint)
                write('queue/'+name,q);lines.append(line)
                requests.append(dict(family=family,ownerID=owner,groupID=group,bundleFile=name,
                    bundleSha256=digest(raw),identity=adapter.fingerprint(q),batchItem=item,cost=previous.sizing.costs(q),
                    envelopeBytes=len(canonical(q['body'])),batchLineBytes=len(line)))
            row['status']='prepared'
        except (ValueError,KeyError,FileNotFoundError,UnicodeError) as exc:
            row.update(status='blocked',reason=type(exc).__name__+': '+str(exc))
        print(json.dumps(dict(progress=index+1,total=len(rows),family=family,ownerID=owner,status=row['status'],reason=row.get('reason'))),flush=True)
    pins.update(resolver.raw_hashes)
    # Guard against inputs or implementation changing during a long offline preparation.
    for path,sha in {**pins,**implementation}.items():require(digest((repo/path).read_bytes())==sha,'INPUT_CHANGED_DURING_PREPARATION:'+path)
    check_groups(rows,requests)
    selection=dict(version=VERSION,semanticVersion=grouped.VERSION,owners=rows,inputPins=pins,
        eligibility='Unchanged v0.4.1 complete authority selection and v0.4.2 specialized targets; no scientific prefiltering of full Hub MDX.',
        blockedOwners=[r['ownerID'] for r in rows if r['status']=='blocked'],providerCalls=0,kgAuthorization=False)
    selection_sha=write('source-selection-manifest.json',selection)
    ontology_sha=write('ontology-authority.json',ontology_report)
    scenarios=('low','pooled','high','outputCeiling')
    manifest=dict(version=grouped.VERSION,selectionVersion=VERSION,providerProjectionVersion=grouped.PROVIDER_PROJECTION_VERSION,sourceSelectionSha256=selection_sha,
        requests=requests,inputPins=pins,implementationPins=implementation,batchInputSha256=digest(b''.join(lines)),
        productionReady=not selection['blockedOwners'] and ontology_report['threeFamilyExact'],blockedOwners=selection['blockedOwners'],
        ontologyAuthoritySha256=ontology_sha,ontologyReady=ontology_report['threeFamilyExact'],ontologyBlockers=ontology_report['threeFamilyDiscrepancies'],
        ownerCounts=dict(Counter(r['family'] for r in rows)),requestCounts=dict(Counter(r['family'] for r in requests)),
        pricing={'batch':adapter.batch.PRICING},sizing=SIZING,providerCalls=0,kgAuthorization=False,
        estimate=dict(requestCount=len(requests),excludedBlockedOwners=len(selection['blockedOwners']),
            basis='Prepared requests only; native envelope-byte heuristic scenarios, no cache savings or retries; not measured provider tokens or actual charges.',
            batchScenariosUSD={k:sum(r['cost']['costUSD'][k] for r in requests) for k in scenarios},
            inputTokenEstimates={k:sum(r['cost']['inputTokenEstimates'][k] for r in requests) for k in scenarios},
            outputTokenScenarios={k:sum(r['cost']['outputTokenScenarios'][k] for r in requests) for k in scenarios}))
    write('queue-manifest.json',manifest)
    with (root/'batch-input.jsonl').open('xb') as handle:handle.write(b''.join(lines))
    with (root/'summary.md').open('x') as handle:
        handle.write('# Full-inventory source-local v0.4.2 preparation\n\n'+json.dumps({k:manifest[k] for k in ('productionReady','ownerCounts','requestCounts','blockedOwners','ontologyBlockers','estimate')},indent=2)+'\n')
    return manifest


def inspect_queue(repo: Path, output: Path, expected_sha: str, *, retain=False) -> tuple[dict,dict]:
    """Stream all bundles through native checks even when owner holds block submission."""
    root=repo/output;raw=(root/'queue-manifest.json').read_bytes()
    require(digest(raw)==expected_sha,'QUEUE_MANIFEST_DRIFT');m=json.loads(raw)
    require(m['version']==grouped.VERSION and m['selectionVersion']==VERSION,'VERSION_DRIFT')
    require(m['providerProjectionVersion']==grouped.PROVIDER_PROJECTION_VERSION and m['sizing']==SIZING,'PRODUCTION_POLICY_DRIFT')
    for path,sha in {**m['inputPins'],**m['implementationPins']}.items():require(digest((repo/path).read_bytes())==sha,'PIN_DRIFT:'+path)
    raw=(root/'source-selection-manifest.json').read_bytes();require(digest(raw)==m['sourceSelectionSha256'],'SELECTION_DRIFT')
    selection=json.loads(raw);rows=selection['owners'];check_groups(rows,m['requests'])
    expected=owner_inventory(json.loads((repo/previous.ORIGINAL/'queue-manifest.json').read_bytes()),
        json.loads((repo/previous.RECOVERY/'queue-manifest.json').read_bytes()),
        {f:json.loads((repo/p).read_bytes()) for f,p in CORPORA.items()})
    require([{k:r[k] for k in e} for r,e in zip(rows,expected)]==expected and len(rows)==len(expected),'OWNER_SELECTION_DRIFT')
    require(m['blockedOwners']==selection['blockedOwners']==[r['ownerID'] for r in rows if r['status']=='blocked'],'BLOCKED_OWNER_DRIFT')
    raw=(root/'ontology-authority.json').read_bytes();require(digest(raw)==m['ontologyAuthoritySha256'],'ONTOLOGY_REPORT_DRIFT')
    authority=json.loads(raw);require(authority==ontology_authority_report(repo),'ONTOLOGY_AUTHORITY_DRIFT')
    require(m['ontologyReady']==authority['threeFamilyExact'] and m['ontologyBlockers']==authority['threeFamilyDiscrepancies'],'ONTOLOGY_READINESS_DRIFT')
    require(m['productionReady']==(not m['blockedOwners'] and m['ontologyReady']),'READINESS_DRIFT')
    contexts={}
    for row in rows:
        if 'contextFile' in row:
            raw=(root/row['contextFile']).read_bytes();require(digest(raw)==row['contextSha256'],'CONTEXT_DRIFT')
            contexts[row['ownerID']]=digest(canonical(json.loads(raw)))
    bundles={};ids=set();lines=[]
    for e in m['requests']:
        raw=(root/'queue'/e['bundleFile']).read_bytes();require(digest(raw)==e['bundleSha256'],'BUNDLE_DRIFT')
        p=json.loads(raw);require(adapter.fingerprint(p)==e['identity'],'REQUEST_IDENTITY_DRIFT');grouped.verify(p)
        require(p['binding'].get('providerProjectionVersion')==grouped.PROVIDER_PROJECTION_VERSION,'UNCLEAN_PROVIDER_ROUTE')
        grouped.assert_provider_clean(p['body'])
        b=p['semanticRequest']['request'];require((b['artifactFamily'],b['owner']['endpointID'],p['binding']['groupID'])==(e['family'],e['ownerID'],e['groupID']),'ENTRY_OWNER_DRIFT')
        require(digest(canonical(p['requestInputs']['baseContext']))==contexts[e['ownerID']],'OWNER_CONTEXT_DRIFT')
        require(source_fits(b['sourceUnits']) and len(canonical(p['body']))<=SIZING['maxEnvelopeBytes'],'SIZE_HOLD')
        require(e['cost']==previous.sizing.costs(p),'COST_DRIFT')
        rid=p['request']['requestID'];require(rid not in ids,'DUPLICATE_REQUEST');ids.add(rid)
        item,line=adapter.batch.input_line(p,1,adapter.fingerprint);require(item==e['batchItem'],'BATCH_ITEM_DRIFT');lines.append(line)
        if retain:bundles[rid]=p
    require((root/'batch-input.jsonl').read_bytes()==b''.join(lines) and digest(b''.join(lines))==m['batchInputSha256'],'BATCH_INPUT_DRIFT')
    return m,bundles


def load_queue(repo: Path, output: Path, expected_sha: str) -> tuple[dict,dict]:
    """Refuse all provider operations on a partial full-production preparation."""
    m,bundles=inspect_queue(repo,output,expected_sha,retain=True)
    require(m['productionReady'],'PRODUCTION_BLOCKED:'+json.dumps(dict(owners=m['blockedOwners'],ontology=m.get('ontologyBlockers'))))
    return m,bundles


def operate(operation, transport, queue_sha, *, repo=ROOT, output=BASE, capacity=None, api=None, live_call=None):
    """Reuse the validated raw Batch journal controller with complete owner checks."""
    require(transport=='batch','BATCH_ONLY')
    return specialized.bind(previous.operate,load_queue=load_queue,semantic=grouped)(operation,transport,queue_sha,
        repo=repo,output=output,capacity=capacity,api=api,live_call=live_call)


def main():
    """Offline preparation/preflight/review block sockets; submission is explicit."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['prepare','preflight','submit','status','collect','review'])
    parser.add_argument('--output',type=Path,default=BASE);parser.add_argument('--queue-sha256');parser.add_argument('--queued-token-limit',type=int)
    args=parser.parse_args()
    def run():
        """Dispatch only the researcher-selected operation."""
        if args.operation=='prepare':
            m=prepare(output=args.output)
            return dict(output=str(args.output),queueSha256=digest((ROOT/args.output/'queue-manifest.json').read_bytes()),
                        productionReady=m['productionReady'],estimate=m['estimate'])
        require(args.queue_sha256,'EXPLICIT_QUEUE_SHA256_REQUIRED')
        if args.operation=='preflight':
            m,_=inspect_queue(ROOT,args.output,args.queue_sha256)
            result=dict(integrity='passed',productionReady=m['productionReady'],blockedOwners=m['blockedOwners'],
                ownerCounts=m['ownerCounts'],requestCounts=m['requestCounts'],estimate=m['estimate'],providerCalls=0,
                ontologyReady=m['ontologyReady'],ontologyBlockers=m['ontologyBlockers'])
            if m['productionReady']:result['nativeBatchPreflight']=operate('preflight','batch',args.queue_sha256,output=args.output)
            else:result['nativeBatchPreflight']='blocked: owner preparation or ontology authority is unresolved'
            destination=ROOT/args.output/'offline-preflight.json'
            raw=canonical(result)+b'\n'
            if destination.exists():require(destination.read_bytes()==raw,'PREFLIGHT_REPORT_ALREADY_EXISTS_WITH_DIFFERENT_STATE')
            else:
                with destination.open('xb') as handle:handle.write(raw)
            return result
        if args.operation=='review':
            return specialized.bind(specialized.review,load_queue=load_queue,operate=operate)(args.queue_sha256,'batch',output=args.output)
        return operate(args.operation,'batch',args.queue_sha256,output=args.output,capacity=args.queued_token_limit)
    with ontology_parse_cache():
        if args.operation in {'prepare','preflight','review'}:
            with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):result=run()
        else:result=run()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
