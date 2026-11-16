"""Offline final Step 14 preparation; hypotheses only, with existing API transports."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import signal
import socket
from unittest.mock import patch
import yaml
from jsonschema import Draft202012Validator
from src.evaluation import step14_anchor_pilot as pilot

BASE = pilot.BASE
ROOT = BASE / 'alignment-workflow/prepared-v1'
SPEC = Path('src/ontology/ontology_spec.yaml')
r = pilot.diagnostic.r
require = pilot.require
live = pilot.live
transport = pilot.transport
PRIORITY = {'shared_reference_target_only', 'conceptual_similarity_only'}
PROMPT = pilot.PROMPT + '''
Also propose directed typed nonidentity relationships only when exact quotations affirm
that relationship between the named endpoints. Use an allowed signatureID and its stated
meaning, direction, evidence constraints and domain/range. Similarity or shared reference
is not a relation. Entity co-occurrence is insufficient. Do not confuse a referring source
artifact with the described entity. hasComponent is explicit composition, not family/version
membership; isMemberOf is dataset collection membership, never universal alignment.
Do not invent new endpoints. If affirmative relational evidence cannot be expressed by an
allowed predicate, describe an ontology gap separately, without minting a property or asserting
it. Abstain where evidence is insufficient. These are local hypotheses; no identity approval,
canonical allocation, OWL equality, or graph writes follow. Different requests are not a
transitive proof. Evaluate complete proposed strict groups; no union of overlapping proposals.
'''


def ancestors(spec: dict) -> dict:
    """Resolve declared class parents and external subclass anchors, without retyping."""
    classes = {c['name']: c for c in spec['classes']}
    by_iri = {c['iri']: c['name'] for c in spec['classes']}
    result = {}
    def visit(name, path):
        """Compute the small declared hierarchy with a cycle check."""
        require(name not in path, 'CLASS_CYCLE')
        c = classes.get(name, {}); values = {name, c.get('iri', name), 'owl:Thing'}
        parents = [c.get('parent')]
        if (c.get('anchor') or {}).get('relation') == 'subClassOf':
            parents.append(c['anchor']['curie'])
        for parent in filter(None, parents):
            key = by_iri.get(parent, parent)
            values.update(visit(key, path | {name}) if key in classes else {key})
        return values
    for name in classes:
        result[name] = visit(name, set())
    return result


def fits(cls: str, signature, hierarchy: dict) -> bool:
    """Honor signature unions and declared subclasses; unknown classes fail closed."""
    return cls in hierarchy and bool(hierarchy[cls] & set(signature if isinstance(signature, list) else [signature]))


def allowed_relations(ids: list, endpoints: dict, spec: dict, hierarchy: dict) -> list:
    """Offer compatible scientific signatures without the identity/provenance predicates."""
    types = {endpoints[o]['ontologyClass'] for o in ids}
    return [rel for rel in spec['relations'] if rel['name'] not in ('consolidatesTo', 'hasEvidence', 'hasIdentifier', 'wasExtractedBy')
            and any(fits(c, rel['domain'], hierarchy) for c in types)
            and any(fits(c, rel['range'], hierarchy) for c in types)]


def pack_edges(edges: set[tuple[str, str]], limit: int = 12) -> list[list[str]]:
    """Cover explicit nominated edges with bounded witness stars, never identity unions."""
    adjacency = defaultdict(set)
    for a, b in edges:
        adjacency[a].add(b); adjacency[b].add(a)
    units = []
    while adjacency:
        center = min(adjacency, key=lambda o: (-len(adjacency[o]), o))
        ids = [center] + sorted(adjacency[center], key=lambda o: (-len(adjacency[o]), o))[:limit-1]
        units.append(sorted(ids))
        for a in ids:
            for b in set(ids) & adjacency.get(a, set()):
                adjacency[b].discard(a)
            adjacency[a].difference_update(ids)
        adjacency = {a: bs for a, bs in adjacency.items() if bs}
    return units


def component_units(groups: list[dict], limit: int = 12) -> list[list[str]]:
    """Cover component occurrences through original-group witnesses, without expanding pairs."""
    postings = defaultdict(list)
    for g in groups:
        for o in g['occurrenceIDs']:
            postings[o].append(g['occurrenceIDs'])
    pending = set(postings); result = []
    while pending:
        center = min(pending, key=lambda o: (-len(postings[o]), o))
        neighbors = {o for members in postings[center] for o in members} - {center}
        chosen = [center] + sorted(neighbors, key=lambda o: (o not in pending, -len(postings[o]), o))[:limit-1]
        require(len(chosen)>1, 'ISOLATED_COMPONENT_OCCURRENCE')
        result.append(sorted(chosen)); pending.difference_update(chosen)
    return result


def affirmative_lead(pair: dict, endpoints: dict) -> list[dict]:
    """Conservative literal relational leads for negative/abstaining pairs, not semantic proof."""
    a, b = (endpoints[o] for o in pair['occurrenceIDs'])
    leads = []
    for owner in (a, b):
        for i, quote in enumerate(owner.get('selectedEvidence', [])):
            text = quote['literalExcerpt']
            for sentence in re.split(r'[.!?\n]', text):
                low = sentence.casefold()
                if re.search(r'\b(not|never|without|may|might|could|unlike)\b', low):
                    continue
                # Avoid a bare generic verb elsewhere in the excerpt being treated as support.
                left={label.casefold() for label in a['labels'] if len(label.strip())>=3 and label.casefold() in low}
                right={label.casefold() for label in b['labels'] if len(label.strip())>=3 and label.casefold() in low}
                distinct_names=any(x not in y and y not in x for x in left for y in right)
                if (distinct_names and re.search(r'\b(uses|implements|contains|derived from|based on|component of|version of|extends|trained on|depends on)\b', low)):
                    leads.append(dict(occurrenceID=owner['occurrenceID'], selectedEvidenceIndex=i, literalSentence=sentence))
    return leads


def response_schema(payload: dict) -> dict:
    """Extend the existing anchor schema with directed typed proposals and ontology gaps."""
    schema = pilot.schema(payload)
    ids = [e['occurrenceID'] for e in payload['occurrences']]
    text = dict(type='string'); refs = dict(type='array', items=text)
    relation = pilot.obj(dict(subject=dict(type='string', enum=ids), object=dict(type='string', enum=ids),
        signatureID=dict(type='string', enum=[r['id'] for r in payload['allowedPredicates']] or ['NO_ALLOWED_PREDICATE']),
        evidenceIDs=refs, rationale=text, uncertainty=text))
    gap = pilot.obj(dict(occurrenceIDs=dict(type='array', items=dict(type='string', enum=ids)),
        proposedMeaning=text, evidenceIDs=refs, uncertainty=text))
    schema['properties'].update(typedRelations=dict(type='array', items=relation), ontologyGaps=dict(type='array', items=gap))
    schema['required'] += ['typedRelations', 'ontologyGaps']
    return schema


def validate(value: dict, body: dict) -> dict:
    """Validate endpoint-bound hypotheses and exact signature direction; never approve semantics."""
    Draft202012Validator(body['text']['format']['schema']).validate(value)
    payload = json.loads(body['input'])
    original = dict(body, text=dict(format=dict(schema=pilot.schema(payload))))
    pilot.validate(dict(assessments=value['assessments']), original)
    endpoints = {e['occurrenceID']: e for e in payload['occurrences']}
    evidence = {q['evidenceID']: o for o,e in endpoints.items() for q in e['evidence']}
    signatures = {x['id']:x for x in payload['allowedPredicates']}
    def check_refs(ids, refs):
        """Every proposed endpoint needs its own original supporting evidence."""
        require(refs and all(q in evidence and evidence[q] in ids for q in refs), 'RELATION_EVIDENCE_BINDING')
        require({evidence[q] for q in refs}==ids, 'RELATION_UNCITED_ENDPOINT')
    for row in value['typedRelations']:
        a,b = row['subject'],row['object']; require(a!=b, 'SELF_RELATION')
        require(row['signatureID'] in signatures, 'NO_ALLOWED_PREDICATE')
        rel=signatures[row['signatureID']]
        require(endpoints[a]['ontologyClass'] in rel['compatibleSubjectClasses'] and
                endpoints[b]['ontologyClass'] in rel['compatibleObjectClasses'], 'SIGNATURE_MISMATCH')
        check_refs({a,b},row['evidenceIDs']);require(row['rationale'].strip(), 'EMPTY_RELATION_REASON')
    for row in value['ontologyGaps']:
        ids=set(row['occurrenceIDs']); require(len(ids)>=2 and len(ids)==len(row['occurrenceIDs']), 'GAP_MEMBERSHIP')
        check_refs(ids,row['evidenceIDs']);require(row['proposedMeaning'].strip(), 'EMPTY_GAP')
    return dict(status='validated_hypotheses_only', semanticValidation=False, identityApprovals=0,
                ontologyGapCount=len(value['ontologyGaps']), usage=None)


def prepare(root: Path) -> dict:
    """Reconcile saved populations and prepare one ignored, reproducible offline package."""
    require(not root.exists() and root.resolve().is_relative_to((BASE/'alignment-workflow').resolve()), 'FRESH_OUTPUT_REQUIRED')
    pins={}
    def source(folder, name):
        """Verify saved producer pins; no upstream stage is executed."""
        manifest=BASE/folder/'manifest.json'; path=BASE/folder/name
        r.preflight.pilot.verify(path,live.load(manifest)['outputHashes'][name],pins)
        pins[str(manifest)]=r.identity.sha(manifest)
        return path
    auto='automatic-acceptance-preview/v2-null-summary-fix'; multi='multigranular-preview/v2'
    groups=list(r.rows(source(auto,'group-simulations.jsonl')))
    components=list(r.rows(source(multi,'overlap-components.jsonl')))
    endpoints={e['occurrenceID']:e for e in r.rows(source('unified-review-queue/v1','endpoint-provenance.jsonl'))}
    members={e['occurrenceID']:e for e in r.rows(source('referent-groups/v1','members.jsonl'))}
    pairs={p['pairKeySha256']:p for p in r.rows(source('adjudication-triage/v1','pair-inventory.jsonl'))}
    prior=source(auto,'prior-decisions.jsonl'); oversized=source(auto,'oversized-inventory.jsonl')
    spec=yaml.safe_load(SPEC.read_text());require(spec['ontology']['version']=='0.1.7','ONTOLOGY_VERSION')
    hierarchy=ancestors(spec)
    eligible={g['simulationID']:g for g in groups if g.get('preOverlapState')=='provisional_accepted'}
    accepted=[g for g in groups if g['state']=='provisional_accepted']
    held=[g for g in groups if g['occurrenceIDs'] and g.get('preOverlapState')!='provisional_accepted']
    require((len(accepted),len(eligible)-len(accepted),len(held))==(364,13244,37471),'BASELINE_DRIFT')
    known={o for g in eligible.values() for o in g['occurrenceIDs']}
    accepted_ids=[o for g in accepted for o in g['occurrenceIDs']]
    require(len(accepted_ids)==len(set(accepted_ids)), 'NONDISJOINT_PROVISIONAL')
    root.mkdir(parents=True)
    def emit(name, rows):
        """Write deterministic JSONL without mutating any saved inputs."""
        with (root/name).open('xb') as f:
            for row in rows:f.write(live.encode(row)+b'\n')
    d16=next(x for x in spec['relations'] if x['name']=='consolidatesTo')
    proposals=[]
    for g in accepted:
        allowed=all(fits(c,d16['range'],hierarchy) for c in g['ontologyClass'])
        proposals.append(dict(proposalAnchor='local-proposal:'+g['simulationID'], canonicalID=None,
            occurrenceIDs=g['occurrenceIDs'], occurrenceMappings=[dict(occurrenceID=o,
                proposedTarget='local-proposal:'+g['simulationID'], originalReference=members[o]['originalReference']) for o in g['occurrenceIDs']],
            savedGroup=g, status='provisional_mapping_proposal_not_approved',
            representationGate='D-16_signature_compatible' if allowed else 'ontology_range_decision_required',
            productionGate='freeze_rule_and_independently_evaluate_before_materialization'))
    emit('mapping-proposals.jsonl', proposals)
    # Existing components only: no new connected-component inference.
    units=[]; component_ledger=[]
    for ci,c in enumerate(components):
        if len(c['groupIDs'])<2:continue
        gs=[eligible[k] for k in c['groupIDs']]
        local=component_units(gs); start=len(units)
        for ids in local:
            require(set(ids)<=endpoints.keys(),'MISSING_COMPONENT_ENDPOINT')
            units.append(dict(occurrenceIDs=ids, origin='overlap_component', componentLine=ci+1))
        component_ledger.append(dict(componentLine=ci+1,groupIDs=c['groupIDs'],
            occurrenceIDs=sorted({o for g in gs for o in g['occurrenceIDs']}), unitIndices=list(range(start,len(units))),
            completeGroupScopesInOneUnit=sum(any(set(g['occurrenceIDs'])<=set(ids) for ids in local) for g in gs),
            spanningGroupScopes=sum(not any(set(g['occurrenceIDs'])<=set(ids) for ids in local) for g in gs),
            status='reconciliation_structure_not_identity'))
    require(len(component_ledger)==240,'COMPONENT_COUNT_DRIFT')
    # Inventory actual holds and nonexclusive routing leads, never overturn saved decisions.
    identity_keys=set(); relation_keys=set(); cue_refs={}; category_counts=Counter(p['category'] for p in pairs.values())
    for key,p in pairs.items():
        if not all(o in endpoints and endpoints[o].get('selectedEvidence') for o in p['occurrenceIDs']):continue
        if p['category'] in PRIORITY:relation_keys.add(key)
        elif p['category'] in ('different_entities_candidate','abstain'):
            refs=affirmative_lead(p,endpoints)
            if refs:relation_keys.add(key);cue_refs[key]=refs
    reasons=Counter(); reason_occ=defaultdict(set); route_counts=Counter(); held_ids=set(); inventory=[]
    for g in held:
        ids=set(g['occurrenceIDs']);held_ids.update(ids)
        keys=set(g.get('selectedPairKeys',[]))
        complete_evidence=all(o in endpoints and endpoints[o].get('selectedEvidence') for o in ids)
        identity=(complete_evidence and len(g['ontologyClass'])==1 and not g.get('modelNegativePairPresent')
                  and not g.get('evidenceInterpretation',{}).get('demonstratedConflicts')
                  and not g.get('exactApprovalSubsets'))
        positives={k for k in keys if k in pairs and pairs[k]['category']=='same_entity_candidate'} if identity else set()
        identity_keys.update(positives)
        routes=[]
        if positives:routes.append('identity_reconciliation_candidate')
        if keys & relation_keys:routes.append('typed_relation_consideration')
        if not routes:routes=['unresolved']
        route_counts.update(routes)
        why=g.get('holdReasons') or [g['state']]
        reasons.update(set(why))
        for reason in set(why):reason_occ[reason].update(ids)
        inventory.append(dict(simulationID=g['simulationID'],occurrenceIDs=sorted(ids),savedState=g['state'],
            actualHoldReasons=g.get('holdReasons',[]),holdKinds=g.get('holdKinds',[]),
            evidenceInterpretation=g.get('evidenceInterpretation'),exactApprovalSubsets=g.get('exactApprovalSubsets',[]),
            routes=routes,selectedPairKeys=g.get('selectedPairKeys',[]),
            overlapWithEligible=sorted(ids & known),originalGroupIDs=g['originalGroupIDs']))
    emit('ineligible-inventory.jsonl',inventory)
    # Reuse co-located component units, then pack remaining explicit leads around shared witnesses.
    postings=defaultdict(set)
    for i,u in enumerate(units):
        for o in u['occurrenceIDs']:postings[o].add(i)
    key_units={}; remaining=set()
    for key in sorted(relation_keys):
        a,b=pairs[key]['occurrenceIDs'];matches=postings[a]&postings[b]
        if matches:key_units[key]=min(matches)
        else:remaining.add(tuple(sorted((a,b))))
    packed=pack_edges(remaining)
    for ids in packed:
        index=len(units); units.append(dict(occurrenceIDs=ids,origin='held_identity_or_typed_relation'))
        for o in ids:postings[o].add(index)
    for key in sorted(identity_keys|relation_keys):
        a,b=pairs[key]['occurrenceIDs'];matches=postings[a]&postings[b]
        if matches:key_units[key]=min(matches)
    nominations=defaultdict(list)
    for key,index in key_units.items():nominations[index].append(key)
    emit('component-coverage.jsonl',component_ledger)
    emit('pair-routing.jsonl',(dict(pairKeySha256=k,category=p['category'],occurrenceIDs=p['occurrenceIDs'],
        identityReconciliationLead=k in identity_keys,typedRelationLead=k in relation_keys,
        affirmativeLiteralLeads=cue_refs.get(k,[]),unitIndex=key_units.get(k),
        status='prepared_hypothesis' if k in key_units else 'identity_lead_deferred_no_pair_reevaluation' if k in identity_keys else 'preserved_not_renominated',
        originalRecommendation=p.get('recommendationReference'),originalBinding=p.get('bindingReference')) for k,p in pairs.items()))
    used={o for u in units for o in u['occurrenceIDs']}
    # Preserve original evidence once locally, and all provisional member provenance.
    emit('occurrence-provenance.jsonl',(dict(occurrenceID=o, endpoint=endpoints.get(o),member=members[o]) for o in sorted(used|set(accepted_ids))))
    live.write(root/'prior-decisions.jsonl',prior.read_bytes())
    live.write(root/'saved-cross-family-oversized.jsonl',oversized.read_bytes())
    emit('oversized-inventory.jsonl',(g for g in groups if not g['occurrenceIDs']))
    emit('ontology-signatures.jsonl',spec['relations'])
    sizes=[]; no_predicate=0; unit_rows=[]
    with (root/'requests.jsonl').open('xb') as out:
        for index,u in enumerate(units):
            ids=u['occurrenceIDs']; uid=f'W{index+1:05}'; occurrences=[]
            for i,o in enumerate(ids,1):
                e=endpoints[o]
                occurrences.append(dict(occurrenceID=o,names=e['labels'],ontologyClass=e['ontologyClass'],sourceFamilies=e['sourceFamilies'],
                    versions=e['versions'],granularity=e['granularity'],evidence=[dict(evidenceID=f'E{i}Q{j}',text=q['literalExcerpt']) for j,q in enumerate(e['selectedEvidence'],1)]))
            relations=[]
            for rel in allowed_relations(ids,endpoints,spec,hierarchy):
                relations.append(dict(signatureID=rel['id'],id=rel['id'],name=rel['name'],domain=rel['domain'],range=rel['range'],
                    evidenceRequirement=rel.get('evidence',''),meaning=rel.get('note',''),
                    compatibleSubjectClasses=sorted({endpoints[o]['ontologyClass'] for o in ids if fits(endpoints[o]['ontologyClass'],rel['domain'],hierarchy)}),
                    compatibleObjectClasses=sorted({endpoints[o]['ontologyClass'] for o in ids if fits(endpoints[o]['ontologyClass'],rel['range'],hierarchy)})))
            no_predicate+=not relations
            payload=dict(occurrences=occurrences,allowedPredicates=relations)
            body=dict(model=live.MODEL,reasoning=dict(effort='medium'),store=False,max_output_tokens=16384,instructions=PROMPT,
                input=live.encode(payload).decode(),text=dict(format=dict(type='json_schema',name='alignment_hypotheses',strict=True,schema=response_schema(payload))))
            sizes.append(len(live.encode(body)))
            out.write(live.encode(dict(custom_id=uid,method='POST',url='/v1/responses',body=body))+b'\n')
            unit_rows.append(dict(unitID=uid,**u,nominationPairKeys=nominations[index],
                sourceFamilies=sorted({f for o in ids for f in endpoints[o]['sourceFamilies']})))
    emit('units.jsonl',unit_rows)
    summary=dict(provisionalGroups=len(accepted),proposedOccurrenceMappings=len(accepted_ids),
        mappingOntologyRangeHolds=sum(p['representationGate']!='D-16_signature_compatible' for p in proposals),
        overlapGroups=len(eligible)-len(accepted),reconciliationComponents=len(component_ledger),
        overlapOccurrences=len({o for c in component_ledger for o in c['occurrenceIDs']}),
        initiallyIneligibleGroups=len(held),ineligibleDistinctOccurrences=len(held_ids),ineligibleOverlapWithEligible=len(held_ids&known),
        ineligibleOutsideEligible=len(held_ids-known),actualHoldReasonGroupCounts=dict(reasons),
        actualHoldReasonDistinctOccurrences={k:len(v) for k,v in reason_occ.items()},nonexclusiveIneligibleRoutes=dict(route_counts),
        savedPairCategories=dict(category_counts),typedRelationLeadPairs=len(relation_keys),identityReconciliationLeadPairs=len(identity_keys),
        negativeOrAbstainingLiteralLeadPairs=len(cue_refs),
        deferredIdentityLeadPairs=len(identity_keys-set(key_units)),
        oversizedScopes=sum(not g['occurrenceIDs'] for g in groups),
        savedCrossFamilyOversizedScopes=sum(1 for _ in r.rows(oversized)),requests=len(units),requestOrigins=dict(Counter(u['origin'] for u in units)),
        requestDistinctOccurrences=len(used),crossFamilyRequests=sum(len(u['sourceFamilies'])>1 for u in unit_rows),
        requestsWithoutCompatibleNonidentityPredicate=no_predicate,
        spanningGroupScopes=sum(c['spanningGroupScopes'] for c in component_ledger),
        approximateInputTokens=[sum(sizes)//5,sum(sizes)//3],approximateOutputTokens=[len(units)*1000,len(units)*5000],
        providerCalls=0,identityApprovals=0,graphWrites=0)
    live.save(root/'summary.json',summary)
    (root/'ontology-gaps.md').write_text('# Prospective representation gaps — no amendments implemented\n\n'
        f"{summary['mappingOntologyRangeHolds']} mapping proposals need a D-16 range decision. "
        f"{no_predicate} requests have no compatible existing nonidentity predicate. Neither count proves a new relation is needed.\n\n"
        'Generic family/release, architecture/instance and shared-reference-target relationships have no universal predicate in v0.1.7. '
        'The proposed correspondsToBroaderReferent remains unapproved. Do not repurpose hasComponent, hasModelVersion (Repository only), '
        'or dataset isMemberOf. Source-supported ontologyGaps in future responses require separate researcher decisions; absent support means abstention.\n')
    for path in (SPEC,Path(__file__),Path(pilot.__file__),Path(transport.__file__),Path('docs/study2_step14_automatic_identity_acceptance_v0.1.md'),Path('docs/study2_step14_identity_granularity_adjudication_v0.1.md')):
        pins[str(path)]=r.identity.sha(path)
    hashes={str(p.relative_to(root)):r.identity.sha(p) for p in root.iterdir() if p.is_file()}
    live.save(root/'manifest.json',dict(inputHashes=pins,outputHashes=hashes))
    return summary


def verify(root: Path) -> dict:
    """Verify prepared artifacts and active schema/ontology code without replaying upstream."""
    m=live.load(root/'manifest.json')
    for name,digest in m['outputHashes'].items():
        require(r.identity.sha(root/name)==digest,'OUTPUT_DRIFT:'+name)
    for path in (SPEC,Path(__file__),Path(pilot.__file__),Path(transport.__file__)):
        require(r.identity.sha(path)==m['inputHashes'][str(path)],'IMPLEMENTATION_DRIFT')
    return live.load(root/'summary.json')


def process(root: Path, uid: str, body: dict, response: dict) -> dict:
    """Keep native usage/receipts and validate proposed relations without scientific repair."""
    live.save(root/'execution'/f'{uid}.response.json',response)
    report=dict(status='invalid_or_incomplete',identityApprovals=0,usage=response.get('usage'))
    try:
        require(response.get('status')=='completed','INCOMPLETE_RESPONSE')
        value=transport.decode(live.provider.extract_model_output(response))
        report.update(validate(value,body));report['usage']=response.get('usage')
        live.save(root/'execution'/f'{uid}.hypotheses.json',value)
        live.save(root/'execution'/f'{uid}.ontology-gaps.json',value['ontologyGaps'])
    except Exception as exc:
        from jsonschema import ValidationError
        if not isinstance(exc,(ValueError,KeyError,TypeError,ValidationError,live.provider.OpenAIProviderError)):raise
        report['errorType']=type(exc).__name__
    live.save(root/'execution'/f'{uid}.validation.json',report)
    return report


def operate(root: Path, mode: str, units: list[str] | None = None, api=None) -> dict:
    """Use existing live/Batch HTTP and immutable dispatch claims for the prepared requests."""
    verify(root)
    requests={x['custom_id']:x for x in r.rows(root/'requests.jsonl')}
    execution=root/'execution';execution.mkdir(exist_ok=True)
    if mode in ('live','submit'):
        chosen=units or ([u for u in requests if not (execution/f'{u}.intent.json').exists()] if mode=='submit' else [])
        require(chosen and len(chosen)==len(set(chosen)) and set(chosen)<=requests.keys(),'REQUEST_SELECTION')
        require(not any((execution/f'{u}.intent.json').exists() for u in chosen),'ALREADY_ATTEMPTED')
        if mode=='submit':
            require(not (execution/'batch-intent.json').exists(),'BATCH_ALREADY_ATTEMPTED')
            raw=b''.join(live.encode(requests[u])+b'\n' for u in chosen)
            from src.extraction.llm.publications.full_corpus_gpt61_batch import MAX_BYTES, MAX_REQUESTS
            require(len(raw)<=MAX_BYTES and len(chosen)<=MAX_REQUESTS,'BATCH_TRANSPORT_SIZE_LIMIT')
            live.write(execution/'batch-input.jsonl',raw)
        for uid in chosen:pilot.claim(root,uid,mode)
        if api is None:api=transport.BatchAPI(live.provider.load_openai_api_key())
        if mode=='live':
            return {uid:process(root,uid,requests[uid]['body'],transport.decode(api.request('POST','/responses',live.encode(requests[uid]['body'])))) for uid in chosen}
        live.save(execution/'batch-intent.json',dict(units=chosen))
        upload=api.upload(execution/'batch-input.jsonl');live.save(execution/'upload.json',upload)
        receipt=api.create(upload['id'],dict(workflow='step14-alignment-v1',manifest=r.identity.sha(root/'manifest.json')))
        live.save(execution/'batch.json',receipt);return receipt
    receipt=live.load(execution/'batch.json')
    if api is None:api=transport.BatchAPI(live.provider.load_openai_api_key())
    status=api.retrieve(receipt['id'])
    if mode=='status':return status
    require(status['status'] in ('completed','failed','expired','cancelled'),'BATCH_NOT_TERMINAL')
    expected=set(live.load(execution/'batch-intent.json')['units']); seen=set();reports={}
    for field in ('output_file_id','error_file_id'):
        if not status.get(field):continue
        raw=api.content(status[field]);live.write(execution/f'{field}.jsonl',raw)
        for line in raw.splitlines():
            row=transport.decode(line);uid=row['custom_id']
            require(uid in expected and uid not in seen,'RESULT_BINDING');seen.add(uid)
            response=(row.get('response') or {}).get('body') or dict(status='failed',error=row.get('error'))
            reports[uid]=process(root,uid,requests[uid]['body'],response)
    return dict(results=reports,missing=sorted(expected-seen),status=status['status'])


def main() -> None:
    """Default preparation is network-disabled; execution requires an explicit terminal subcommand."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','verify','validate','live','submit','status','retrieve'])
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--units',nargs='+')
    p.add_argument('--response',type=Path);p.add_argument('--time-limit',type=int,default=25)
    args=p.parse_args()
    if args.mode in ('prepare','verify','validate'):
        def timeout(signum,frame):
            """Stop bounded offline work; an incomplete package cannot be dispatched."""
            raise TimeoutError('OFFLINE_TIME_LIMIT: use a fresh root and --time-limit 0 in researcher terminal')
        signal.signal(signal.SIGALRM,timeout);signal.alarm(args.time_limit)
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
            if args.mode=='prepare':value=prepare(args.root)
            else:
                value=verify(args.root)
                if args.mode=='validate':
                    require(args.units and len(args.units)==1 and args.response,'ONE_UNIT_AND_RESPONSE_REQUIRED')
                    request=next(x for x in r.rows(args.root/'requests.jsonl') if x['custom_id']==args.units[0])
                    value=validate(transport.decode(args.response.read_bytes()),request['body'])
        signal.alarm(0)
    else:value=operate(args.root,args.mode,args.units)
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
