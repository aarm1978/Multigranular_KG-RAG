"""v0.4.2 request specialization and exact owner consolidation over unchanged v0.4.1."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

from jsonschema import Draft202012Validator
from src.extraction.llm import source_local_semantics as base
from src.extraction.llm.pilot_preflight import canonical, digest, check_strict_structure
from src.extraction.llm.publications.batch_transport import decode

VERSION='study2-source-local-specialized/0.4.2'
CONTRACT=Path(__file__).resolve().parents[3]/'docs/study2_source_local_specialized_v0.4.2.md'
require=base.require
MODELS=['A-DOM03a','A-DOM03b','A-DOM03c','A-DOM03d','A-DOM03e']
FEATURES=['A-DOM07a','A-DOM07b','A-DOM07c','A-DOM07d','A-DOM07e','A-DOM07f']
# Dependencies are local to each request; repeated endpoint targets are intentional.
GROUPS={
 'hydroshare':{
  'observations_and_geography':(['A-DOM04','A-D12','A-DOM05','A-DOM08','A-DOM11','A-DOM12']+FEATURES,['C-D16','C-D17','C-D15','C-D23']),
  'software_and_processing':(['A-DOM02','A-C11','A-C01']+MODELS,['C-D18','C-D24','C-D25','C-D26','C-D22','D-17','D-22']),
  'resource_references':(['A-D01','A-P01','A-C01'],['C-D14','C-D19'])},
 'github':{
  'software_roles_and_use':(['A-C07','A-DOM02','A-C01','A-C11','A-C08','A-DOM13','A-C10','A-P13','A-D01','A-P25']+MODELS,
    ['C-C07','C-C11','C-C22','D-22','C-C21','C-C23','C-C10','C-C08','C-C20','C-C09','C-C16','C-C15']),
  'quantities_and_concepts':(['A-DOM04','A-DOM12','A-DOM05','A-DOM11'],['C-C12','C-C24','C-C25','C-C26']),
  'datasets_and_citations':(['A-D01','A-P25','A-P01','A-C01'],['C-C17','C-C19','D-17'])},
 'ciroh_hub':{
  'products_and_references':(['A-DOM02','A-C01','A-D01','A-P25','A-P13','A-P01']+MODELS,
    ['C-DC17','C-DC19','C-DC07','C-DC16','C-DC27','C-DC28','D-22','C-DC24','C-DC25','C-DC26','D-23']),
  'procedures_and_dependents':(['A-C11','A-DC05','A-DC06','A-DC08','A-DOM12'],['C-DC20','C-DC10','C-DC09','C-DC12','C-DC11']),
  'scientific_occurrences':(['A-DOM05','A-DOM04','A-DOM11','A-DOM13']+FEATURES,['C-DC08','C-DC23'])}}


def inventory(family: str) -> dict:
    """Check complete authorized coverage and closed relation/dependency endpoints."""
    profile=base.profiles.get_profile(family,version=base.VERSION)
    groups=GROUPS[family]
    for column,key in enumerate(('entities','relations')):
        require(set().union(*(set(g[column]) for g in groups.values()))==set(profile[key]),'SPECIALIZED_COVERAGE_GAP:'+key)
    spec=base.profiles.load_ontology();classes={c['id']:c for c in spec['classes']};iris={c['iri']:c for c in spec['classes']}
    def matches(identifier,signature):
        """Use native ontology inheritance without inferring semantic identity."""
        c=classes[identifier];names=signature if isinstance(signature,list) else [signature]
        while c:
            if c['name'] in names:return True
            c=iris.get(c.get('parent'))
        return False
    for name,(nodes,edges) in groups.items():
        require(len(nodes)==len(set(nodes)) and len(edges)==len(set(edges)),'DUPLICATE_GROUP_TARGET')
        for identifier in edges:
            declaration=profile['relations'][identifier]['declaration']
            for side in ('domain','range'):
                required={c for c in profile['entities'] if matches(c,declaration[side])}
                # The owner exists independently and never requires rediscovery.
                required.discard(profile['ownerClassID']) if side=='domain' else None
                require(required<=set(nodes),'GROUP_ENDPOINT_GAP:'+name+':'+identifier+':'+side)
        if set(nodes)&{'A-DC06','A-DC08','A-DOM12'} and family=='ciroh_hub':
            require({'A-DC05','A-DC06'}<=set(nodes) and {'C-DC20','C-DC10','C-DC11','C-DC12'}<=set(edges),'GROUP_PARENT_PATH_GAP')
    return {name:dict(entities=sorted(nodes),relations=sorted(edges)) for name,(nodes,edges) in groups.items()}


def group_schema(context: dict, group: str) -> dict:
    """Narrow native strict branches and require the native fragment contribution field."""
    family=context['semanticRequest']['request']['artifactFamily'];scope=inventory(family)[group]
    schema=deepcopy(context['body']['text']['format']['schema'])
    schema['properties']['schemaVersion']['enum']=[VERSION]
    for key,target in [('candidateNodes','entities'),('candidateEdges','relations')]:
        schema['properties'][key]['items']['anyOf']=[b for b in schema['properties'][key]['items']['anyOf'] if b['properties']['inventoryId']['enum'][0] in scope[target]]
    fragments=[]
    for branch in schema['$defs']['fragment']['anyOf']:
        if 'contribution' in branch['properties']:
            branch['properties']['contribution']={'type':'string','minLength':1,'pattern':r'\S'}
            fragments.append(branch)
    require(fragments,'CONTRIBUTION_SCHEMA_MISSING')
    schema['$defs']['fragment']['anyOf']=fragments
    schema['properties']['abstentions']['items']['properties']['inventoryId']={'type':'string','enum':sorted(scope['entities']+scope['relations'])}
    check_strict_structure(schema)
    return schema


PROVIDER_PROJECTION_VERSION='source-local-provider-projection/0.4.3'


def provider_projection(value, *, path=(), removed=None):
    """Remove operational historical diagnostics recursively, including encoded JSON.

    Source units are immutable evidence authorities. A reserved diagnostic field
    inside one is a conflict to report, never permission to edit source content.
    Removed records stay in the private base context and an explicit local index.
    """
    removed=[] if removed is None else removed
    if isinstance(value,dict):
        result={}
        for key,item in value.items():
            if key=='historicalSourceDiagnostics':
                require('sourceUnits' not in path,'DIAGNOSTIC_FIELD_IN_SOURCE_UNIT')
                removed.append(dict(path=list(path)+( [key] ),value=deepcopy(item)))
            else:result[key]=provider_projection(item,path=(*path,key),removed=removed)
        return result
    if isinstance(value,list):
        return [provider_projection(item,path=(*path,index),removed=removed) for index,item in enumerate(value)]
    if isinstance(value,str):
        try:decoded=json.loads(value)
        except (ValueError,TypeError):return value
        if isinstance(decoded,(dict,list)):
            count=len(removed);projected=provider_projection(decoded,path=(*path,'$json'),removed=removed)
            if len(removed)!=count:return canonical(projected).decode()
    return deepcopy(value)


def assert_provider_clean(envelope: dict) -> None:
    """Fail if any nested provider object or encoded JSON contains diagnostic fields."""
    removed=[];provider_projection(envelope,removed=removed)
    require(not removed,'PROVIDER_HISTORICAL_DIAGNOSTICS_FORBIDDEN')


def build(context: dict, group: str, *, provider_projection_version: str | None = None) -> dict:
    """Keep full trusted context privately and transmit only the assigned target profile."""
    require(context==base.prepare_request(context['semanticRequest'],context['requestInputs']),'BASE_CONTEXT_DRIFT')
    body=deepcopy(context['semanticRequest']['request']);family=body['artifactFamily'];scope=inventory(family)[group]
    profile=body['targetProfile']
    for key in ('entities','relations'):profile[key]={i:profile[key][i] for i in scope[key]}
    profile['genericOccurrenceTargets']=[i for i in profile['genericOccurrenceTargets'] if i in scope['entities']]
    body.update(contractID=VERSION,schemaVersion=VERSION,promptIdentifier=VERSION+':'+group,
        requestGroup=dict(groupID=group,targets=scope,allGroups=inventory(family),baseContextSha256=context['semanticRequest']['requestSha256']))
    body['responseContract']['schemaVersion']=VERSION
    body['responseContract']['multiFragmentRule']='Every evidence fragment, even a single fragment, requires a nonblank contribution explaining its role; never invent or repair evidence.'
    body['instructions'] += ['This specialized request covers only requestGroup.targets. Other groups handle the other authorized targets. All complete source context remains available.',
        'Every evidence fragment must include a nonblank contribution explaining its role, including single-fragment evidence.',
        'Candidate references and parentPath candidate_edge references are local to this response. Propose required local endpoints/parents together with their independently evidenced relations; never refer to candidates from another request. Exact supplied deterministic endpoints remain reusable.']
    body['executableCoverage']={k:v for k,v in scope.items()}
    local_diagnostics=[]
    if provider_projection_version is not None:
        require(provider_projection_version==PROVIDER_PROJECTION_VERSION,'UNKNOWN_PROVIDER_PROJECTION')
        original_units=deepcopy(body['sourceUnits'])
        body=provider_projection(body,removed=local_diagnostics)
        require(body['sourceUnits']==original_units,'PROVIDER_SOURCE_CONTENT_DRIFT')
    wire=canonical(body);sha=digest(wire);schema=group_schema(context,group)
    envelope=deepcopy(context['body']);envelope['input']=wire.decode()
    envelope['text']['format'].update(name=family+'_specialized_v042',schema=schema)
    if provider_projection_version is not None:
        envelope=provider_projection(envelope,removed=local_diagnostics)
        assert_provider_clean(envelope)
        require(json.loads(envelope['input'])==body,'PROVIDER_INPUT_DRIFT')
    result=dict(request={'requestID':family+':v042:'+group+':'+sha},
        semanticRequest=dict(status='request_ready',request=body,requestSha256=sha,diagnostics=[]),
        requestInputs=dict(baseContext=deepcopy(context),groupID=group),body=envelope,
        binding=dict(version=VERSION,baseContextSha256=context['semanticRequest']['requestSha256'],groupID=group,
            sourceSha256=context['binding']['sourceSha256'],providerInputSha256=sha,providerEnvelopeSha256=digest(canonical(envelope)),
            schemaSha256=digest(canonical(schema)),policySha256=digest(CONTRACT.read_bytes())))
    if provider_projection_version is not None:
        result['binding']['providerProjectionVersion']=provider_projection_version
        result['requestInputs']['localHistoricalDiagnostics']=local_diagnostics
    return result


def verify(prepared: dict) -> None:
    """Reconstruct all specialized bytes; caller input cannot silently narrow coverage."""
    require(prepared==build(prepared['requestInputs']['baseContext'],prepared['requestInputs']['groupID'],provider_projection_version=prepared['binding'].get('providerProjectionVersion')),'SPECIALIZED_REQUEST_DRIFT')


def replay(prepared: dict, raw: bytes, *, expected_request_sha256: str) -> dict:
    """Validate authentic group bytes, then explicitly label the native validation view.

    Only schemaVersion changes in the native view. No candidate field, evidence,
    contribution, ID or endpoint is repaired. Original response bytes stay separate.
    """
    verify(prepared)
    require(prepared['semanticRequest']['requestSha256']==expected_request_sha256,'GROUP_ASSOCIATION_MISMATCH')
    payload=decode(raw);Draft202012Validator(prepared['body']['text']['format']['schema']).validate(payload)
    context=prepared['requestInputs']['baseContext'];view={**payload,'schemaVersion':base.VERSION}
    native=base.replay(context,canonical(view),expected_request_sha256=context['semanticRequest']['requestSha256'])
    report=dict(schemaVersion=VERSION,groupID=prepared['binding']['groupID'],requestID=prepared['request']['requestID'],
        requestSha256=expected_request_sha256,responseSha256=digest(raw),responseBytesHex=raw.hex(),
        baseContextSha256=context['semanticRequest']['requestSha256'],nativeValidationView=native,
        validationViewTransform='schemaVersion only; native originalReplay refers to this explicit view, not authentic provider bytes',
        projection=native['projection'],unresolvedAssertions=native['unresolvedAssertions'],
        abstentions=native['abstentions'],zeroYield=native['zeroYield'],kgAuthorization=False)
    report['reportSha256']=digest(canonical(report));return report


def consolidate(items: list[tuple[dict,dict]]) -> dict:
    """Combine a complete owner's group reports by exact existing IDs/triples only."""
    require(bool(items),'EMPTY_OWNER_REPORTS');by_group={};context=items[0][0]['requestInputs']['baseContext']
    family=context['semanticRequest']['request']['artifactFamily'];owner=context['semanticRequest']['request']['owner']
    for p,r in items:
        verify(p);group=p['binding']['groupID']
        require(group not in by_group,'DUPLICATE_GROUP_REPORT')
        require(p['requestInputs']['baseContext']==context,'MIXED_OWNER_CONTEXTS')
        require(r['reportSha256']==digest(canonical({k:v for k,v in r.items() if k!='reportSha256'})),'GROUP_REPORT_DRIFT')
        require(r['requestID']==p['request']['requestID'] and r['requestSha256']==p['semanticRequest']['requestSha256']
                and r['baseContextSha256']==context['semanticRequest']['requestSha256'] and r['groupID']==group,'REPORT_ASSOCIATION_DRIFT')
        raw=bytes.fromhex(r['responseBytesHex'])
        require(digest(raw)==r['responseSha256'],'RESPONSE_DRIFT')
        payload=decode(raw);Draft202012Validator(p['body']['text']['format']['schema']).validate(payload)
        native=r['nativeValidationView']
        require(native['status']=='projection_completed','GROUP_PROCESSING_BLOCKED')
        require(native['reportSha256']==digest(canonical({k:v for k,v in native.items() if k!='reportSha256'})), 'NATIVE_VIEW_DRIFT')
        require(native['originalReplay']['responseSha256']==digest(canonical({**payload,'schemaVersion':base.VERSION}))
                and native['projectionSha256']==digest(canonical(native['projection']))
                and r['projection']==native['projection'],'VALIDATION_VIEW_ASSOCIATION_DRIFT')
        by_group[group]=(p,r)
    require(set(by_group)==set(inventory(family)),'INCOMPLETE_OWNER_GROUPS')
    nodes={};edges={};derived={};connected=set();reports=[]
    for group,(p,r) in sorted(by_group.items()):
        reports.append(deepcopy(r));native=r['nativeValidationView']
        for key,store in [('nodes',nodes),('edges',edges)]:
            for record in native['projection'][key]:
                identity=(record['resolvedEndpoint']['endpointID'] if key=='nodes' else
                    (record['originalCandidate']['inventoryId'],record['resolvedSource']['endpointID'],record['resolvedTarget']['endpointID']))
                row=store.setdefault(identity,dict(sourceLocalCandidateID=record['sourceLocalCandidateID'],records=[]))
                row['records'].append(dict(requestID=r['requestID'],groupID=group,record=deepcopy(record)))
        # Include admitted exact duplicate edges in stronger-relation precedence too.
        decisions={d['candidateID']:d for d in native['decisions']}
        for c in native['originalReplay']['validationResult']['candidateChecks']:
            if c['kind']=='edge' and decisions[c['candidateID']]['disposition'] in {'accepted','suppressed_duplicate'}:
                a,b=c['resolvedSource']['endpointID'],c['resolvedTarget']['endpointID']
                if a==owner['endpointID']:connected.add(b)
                if b==owner['endpointID']:connected.add(a)
        for d in native['derivedConstructionInput']['assertions']:
            row=derived.setdefault(d['assertionID'],dict(assertionID=d['assertionID'],targetID=d['targetID'],constructionInputs=[]))
            row['constructionInputs'].append(dict(requestID=r['requestID'],groupID=group,
                requiredAcceptedProjectionSha256=native['projectionSha256'],assertion=deepcopy(d)))
    suppressed=[{**derived[k],'reason':'stronger_accepted_owner_relation_in_specialized_response'} for k in sorted(derived) if derived[k]['targetID'] in connected]
    result=dict(schemaVersion=VERSION+'/owner-consolidation',owner=deepcopy(owner),artifactFamily=family,
        baseContextSha256=context['semanticRequest']['requestSha256'],groupReports=reports,
        nodes=[nodes[k] for k in sorted(nodes)],edges=[edges[k] for k in sorted(edges)],
        derivedConstructionInputs=[derived[k] for k in sorted(derived) if derived[k]['targetID'] not in connected],
        suppressedDerivedMentions=suppressed,deferredSourceRecords=deepcopy(context['semanticRequest']['request']['deferredSourceRecords']),
        diagnosticsRule='All held/suppressed candidates, unresolved assertions, abstentions, exact evidence and native provenance remain in groupReports; never merge names or infer cross-group endpoint references.',
        kgAuthorization=False)
    result['zeroYield']=not (result['nodes'] or result['edges'] or result['derivedConstructionInputs'])
    result['reportSha256']=digest(canonical(result));return result
