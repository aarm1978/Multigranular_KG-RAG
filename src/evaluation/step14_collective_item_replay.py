"""Offline item-level replay of the completed collective population."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from itertools import combinations
import hashlib
import json
import socket
import tempfile
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError

from src.evaluation import step14_collective_validation as v3

w = v3.w
ROOT = v3.ROOT.parent / 'v4'
FIELDS = ('assessments', 'typedRelations', 'ontologyGaps')
VALID = 'mechanically_admissible'
HELD = 'review_required'
VERSION = 'collective-item-replay/0.4.0'


def digest(data):
    """Hash bytes using the repository manifest algorithm."""
    return hashlib.sha256(data).hexdigest()


def strings(value):
    """Extract attributable aliases without coercing malformed fields."""
    return [x for x in value if isinstance(x, str)] if isinstance(value, list) else []


def bind(payload, aliases, sources, provenance):
    """Join exact request excerpts to the producer's indexed selected-evidence record."""
    bindings = {}
    ends = {e['occurrenceID']: e for e in payload['occurrences']}
    w.require(ends.keys() == aliases.keys() and len(set(aliases.values())) == len(aliases), 'ENTITY_BINDINGS')
    for alias, e in ends.items():
        oid = aliases[alias]
        ep = provenance[oid]['endpoint']
        w.require(oid == ep['occurrenceID'] == provenance[oid]['member']['occurrenceID'] and
                  ep['sourceArtifacts'] == [sources[e['sourceArtifactRef']]] and
                  ep['ontologyClass'] == e['ontologyClass'], 'SOURCE_BINDING')
        quotes = ep['selectedEvidence']
        w.require(len(quotes) == len(e['evidence']), 'EVIDENCE_COUNT')
        for index, (q, original) in enumerate(zip(e['evidence'], quotes)):
            ref = q['evidenceID']
            w.require(ref not in bindings and q['text'] == original['literalExcerpt'], 'QUOTE_BINDING')
            bindings[ref] = dict(alias=alias, occurrenceID=oid, selectedEvidenceIndex=index,
                                 fullQuoteSha256=original['fullQuoteSha256'], reference=original['reference'])
    return bindings


def items_for(value, body, aliases, bindings, members):
    """Assign reasons per item; count only the claimed members' citations as direct support."""
    schema = body['text']['format']['schema']
    payload = json.loads(body['input'])
    signatures = {s['signatureID']:s for s in payload['allowedPredicates']}
    envelope = value if isinstance(value, dict) else {}
    arrays = {k: envelope.get(k) if isinstance(envelope.get(k), list) else [] for k in FIELDS}
    counts = Counter(o for a in arrays['assessments'] if isinstance(a, dict)
                     for o in strings(a.get('occurrenceIDs')))
    overlap = sorted(o for o,n in counts.items() if n > 1)
    omitted = sorted(aliases.keys() - counts.keys())
    layers = dict(schemaErrors=[dict(path=list(e.absolute_path), rule=e.validator)
                               for e in Draft202012Validator(schema).iter_errors(value)],
                  overlappingAliases=overlap, omittedAliases=omitted, unknownAliases=sorted(counts.keys()-aliases.keys()),
                  partitionExact=counts == Counter(list(aliases)), itemCounts={k:len(a) for k,a in arrays.items()})
    records = []
    for field, array in arrays.items():
        validator = Draft202012Validator(schema['properties'][field]['items'])
        for index, original in enumerate(array):
            item = original if isinstance(original,dict) else {}
            ids = strings([item.get('subject'),item.get('object')] if field == 'typedRelations' else item.get('occurrenceIDs'))
            category = item.get('category') if isinstance(item.get('category'),str) else field
            reasons = {'SCHEMA:'+e.json_path+':'+str(e.validator) for e in validator.iter_errors(original)}
            if not ids or len(set(ids)) != len(ids) or any(o not in aliases for o in ids):
                reasons.add('INVALID_MEMBERSHIP')
            cited = []
            direct = set()
            roles = ('supportingEvidenceIDs','contradictoryEvidenceIDs') if field=='assessments' else ('evidenceIDs',)
            for role in roles:
                for ref in strings(item.get(role)):
                    binding = bindings.get(ref)
                    location = 'unknown' if not binding else 'member' if binding['alias'] in ids else 'external'
                    cited.append(dict(field=role, evidenceID=ref, binding=binding, location=location))
                    if location == 'unknown':
                        reasons.add('UNKNOWN_EVIDENCE')
                    if location == 'member' and role != 'contradictoryEvidenceIDs':
                        direct.add(binding['alias'])
            external = [c['evidenceID'] for c in cited if c['location']=='external']
            if set(ids)-direct and category!='abstention':
                reasons.add('MISSING_DIRECT_SUPPORT')
            if field=='assessments':
                if set(ids).intersection(overlap):
                    reasons.add('PARTITION_OVERLAP')
                if not str(item.get('rationale','')).strip() or not str(item.get('granularity','')).strip():
                    reasons.add('MISSING_REASONING')
                if category=='strict_identity':
                    if external:
                        reasons.add('AMBIGUOUS_EXTERNAL_IDENTITY_EVIDENCE')
                    if item.get('contradictoryEvidenceIDs'):
                        reasons.add('CONTRADICTORY_IDENTITY')
                    records_in_scope = [members[aliases[o]] for o in ids if o in aliases]
                    if len(ids)<2 or len({(r['ontologyClass'],r['inventoryId']) for r in records_in_scope})!=1:
                        reasons.add('CLASS_OR_SIZE')
                    if records_in_scope:
                        signals = v3.legacy.ab.compatibility_signals(records_in_scope, [])
                        reasons.update(signals['demonstratedConflicts']+signals['unresolvedAmbiguities'])
                elif len(ids)!=1:
                    reasons.add('SINGLETON_ASSIGNMENT_REQUIRED')
                elif category=='distinct' and any(c['field']=='contradictoryEvidenceIDs' and
                                                  c['location']=='member' for c in cited):
                    reasons.add('AMBIGUOUS_DISTINCT_CONTRADICTION')
            elif field=='typedRelations':
                sig = signatures.get(item.get('signatureID')) if isinstance(item.get('signatureID'),str) else None
                if len(ids)!=2 or len(set(ids))!=2 or not sig or not all(o in aliases for o in ids):
                    reasons.add('INVALID_DIRECTED_SIGNATURE')
                elif (members[aliases[ids[0]]]['ontologyClass'] not in sig['compatibleSubjectClasses'] or
                      members[aliases[ids[1]]]['ontologyClass'] not in sig['compatibleObjectClasses']):
                    reasons.add('SIGNATURE_MISMATCH')
                if not str(item.get('rationale','')).strip():
                    reasons.add('EMPTY_RELATION_REASON')
                if sig and sig['name']=='isVersionOf':
                    reasons.add('RELEASE_TO_GENERAL_REFERENT_REQUIRES_REVIEW')
            elif not str(item.get('proposedMeaning','')).strip():
                reasons.add('EMPTY_GAP_MEANING')
            if field=='ontologyGaps' and external:
                reasons.add('EXTERNAL_GAP_CONTEXT_REQUIRES_REVIEW')
            status = HELD if reasons else VALID
            if field=='ontologyGaps' and len(ids)==1:
                reasons.add('SINGLETON_GAP_MISSING_ENDPOINT')
                status='unresolved_observation'
            elif category=='abstention' and not reasons:
                status='abstention'
            records.append(dict(itemType=field, itemIndex=index, category=category, modelItem=original,
                                occurrenceAliases=ids, occurrenceIDs=[aliases.get(o) for o in ids], citations=cited,
                                externalEvidenceIDs=external, status=status, reasons=sorted(reasons)))
    layers['unknownEvidenceIDs']=sorted({c['evidenceID'] for r in records for c in r['citations'] if c['location']=='unknown'})
    return records,layers


def reconciliation_gate(r, protected, strict_scopes, local_opposition):
    """Screen exact syntactic conflicts without inferring identity across windows."""
    blockers=[]
    if r['category']=='strict_identity' and r['status']==VALID:
        scope=tuple(sorted(r['occurrenceIDs']))
        if protected.intersection(scope):blockers.append('protected_membership')
        if any(strict_scopes[o]-{scope} for o in scope):blockers.append('competing_complete_membership')
        if any(local_opposition.get(key) for key in [scope,*combinations(scope,2)]):
            blockers.append('opposed_or_held_membership')
    permitted=r['category']=='strict_identity' and r['status']==VALID and not blockers
    return blockers, permitted


def replay(output):
    """Read immutable packages and provider files, apply one contract, and publish atomically."""
    w.require(not output.exists(),'FRESH_OUTPUT_REQUIRED')
    baseline = v3.verify(v3.ROOT)
    pins = {}
    def pin(path):
        """Record exactly the bytes consumed, before decoding."""
        raw=path.read_bytes()
        pins[str(path)]=digest(raw)
        return raw
    for path in (Path(__file__),w.SPEC,v3.ROOT/'manifest.json',v3.SOURCE/'manifest.json',v3.legacy.ROOT/'manifest.json'):
        pin(path)
    provenance_path=v3.legacy.ROOT/'occurrence-provenance.jsonl'
    provenance={p['occurrenceID']:p for line in pin(provenance_path).splitlines() if (p:=json.loads(line))}
    members={o:p['member'] for o,p in provenance.items()}
    protected=set()
    decision=w.BASE/'decision-stage/v2'
    dm=json.loads(pin(decision/'manifest.json'))
    for name in ('occurrence-mappings.jsonl','historical-approvals.jsonl'):
        raw=pin(decision/name)
        w.require(digest(raw)==dm['outputHashes'][name],'PROTECTION_DRIFT')
        for line in raw.splitlines():
            row=json.loads(line)
            protected.update(row['occurrenceIDs'] if 'occurrenceIDs' in row else [row['occurrenceID']])
    paths=[v3.SOURCE/'pilot']+[v3.ROOT/name for name in sorted(baseline['packages'])]
    units=[]; ledger=[]; seen=set(); diagnostics=Counter()
    strict_scopes=defaultdict(set)
    local_opposition=defaultdict(set)
    historical_counts=Counter()
    for path in paths:
        execution=path/'execution'
        aliases=json.loads(pin(path/'alias-bindings.json'))
        sources=json.loads(pin(path/'source-artifact-bindings.json'))
        requests={r['custom_id']:r for line in pin(path/'requests.jsonl').splitlines() if (r:=json.loads(line))}
        native={}
        if path.name.startswith('batch'):
            w.require(pin(execution/'batch-input.jsonl')==(path/'requests.jsonl').read_bytes(),'BATCH_REQUEST_DRIFT')
            for line in pin(execution/'output_file_id.jsonl').splitlines():
                result=json.loads(line); uid=result['custom_id']
                w.require(uid not in native,'DUPLICATE_PROVIDER_RESULT')
                native[uid]=result['response']['body']
            w.require(native.keys()==requests.keys(),'PROVIDER_RESULT_SET')
        for uid,request in requests.items():
            w.require(uid not in seen,'DUPLICATE_UNIT');seen.add(uid)
            body=request['body']; raw_path=execution/f'{uid}.response.json'
            response=json.loads(pin(raw_path))
            if native:w.require(response==native[uid],'RAW_RESPONSE_DRIFT')
            prior_path=(v3.ROOT/'revalidation/execution' if path.name=='pilot' else execution)/f'{uid}.validation.json'
            prior=json.loads(pin(prior_path))
            w.require(json.loads(pin(execution/f'{uid}.intent.json'))['unitID'] == uid, 'INTENT_BINDING')
            strict_status=prior['status']
            historical_counts[(path.name,strict_status)]+=1
            unit=dict(unitID=uid,package=path.name,rawResponse=str(raw_path),rawSha256=pins[str(raw_path)],
                      originalRequest=str(path/'requests.jsonl'),requestBodySha256=digest(w.live.encode(body)),
                      originalValidation=str(prior_path),v3Status=strict_status,providerStatus=response.get('status'),
                      incompleteDetails=response.get('incomplete_details'),aliasBindings=aliases[uid])
            units.append(unit)
            try:
                w.require(response.get('status')=='completed' and not response.get('incomplete_details'),'INCOMPLETE_RESPONSE')
                value=w.transport.decode(w.live.provider.extract_model_output(response))
            except (ValueError,TypeError,KeyError,w.live.provider.OpenAIProviderError) as exc:
                unit.update(decodeError=str(exc),itemCounts={});continue
            payload=json.loads(body['input'])
            bindings=bind(payload,aliases[uid],sources[uid],provenance)
            records,layers=items_for(value,body,aliases[uid],bindings,members)
            unit.update(layers, decoded=True)
            try:
                v3.validate(value,body)
                rule=None
            except (ValueError,ValidationError,KeyError,TypeError) as exc:
                rule=str(exc)
            w.require((rule is None)==(strict_status=='validated_hypotheses_only'),'V3_REPLAY_DRIFT')
            unit['strictFailure']=rule
            rejected=path.name.startswith('batch') and rule is not None
            if rejected:
                diagnostics.update(dict(units=1,completedWithoutIncompleteDetails=1,schemaValid=int(not layers['schemaErrors']),
                    exactPartition=int(layers['partitionExact']),allReferencesKnown=int(not layers['unknownEvidenceIDs'])))
            for r in records:
                r.update(unitID=uid,rawResponse=str(raw_path),rawSha256=unit['rawSha256'],v3Status=strict_status)
                ledger.append(r)
                ids=r['occurrenceIDs']
                if rejected:
                    diagnostics[r['itemType']]+=1
                    if r['category']=='strict_identity':
                        diagnostics['strictWithContradictions']+=bool(r['modelItem'].get('contradictoryEvidenceIDs'))
                        diagnostics['strictMissingMemberSupport']+=int('MISSING_DIRECT_SUPPORT' in r['reasons'])
                    if r['itemType']=='assessments':
                        diagnostics['basicCleanAssessments']+=int(not r['externalEvidenceIDs'] and not (set(r['reasons'])-{'AMBIGUOUS_DISTINCT_CONTRADICTION'}))
                    if r['itemType']=='typedRelations':
                        diagnostics['relationsWithExternalEvidence']+=bool(r['externalEvidenceIDs'])
                    if r['itemType']=='ontologyGaps':
                        diagnostics['singletonGaps']+=len(ids)==1
                if r['category']=='strict_identity' and None not in ids:
                    scope=tuple(sorted(ids))
                    for o in scope:strict_scopes[o].add(scope)
                    if r['status']==HELD:
                        local_opposition[scope].add(uid)
                elif r['category']=='distinct' and len(ids)==1:
                    for other in aliases[uid].values():
                        if other!=ids[0]:local_opposition[tuple(sorted((ids[0],other)))].add(uid)
                elif r['itemType']=='typedRelations' and isinstance(r['modelItem'],dict) and r['modelItem'].get('signatureID') in ('D-27','D-28') and None not in ids:
                    local_opposition[tuple(sorted(ids))].add(uid)
    w.require(len(seen)==3930,'POPULATION_DRIFT')
    counts=Counter(); sensitivity=Counter(); reasons=Counter(); gates=Counter()
    reasons_by_category=Counter()
    for r in ledger:
        blockers,permitted=reconciliation_gate(r,protected,strict_scopes,local_opposition)
        r.update(reconciliationFlags=blockers,downstreamPolicyEvaluationPermitted=permitted,canonicalApproved=False)
        gates.update(blockers)
        counts[(r['category'],r['status'])]+=1
        sensitivity[(r['v3Status'],r['category'],r['status'])]+=1
        reasons.update(r['reasons'])
        reasons_by_category.update((r['category'],reason) for reason in r['reasons'])
    w.require(len({(r['unitID'],r['itemType'],r['itemIndex']) for r in ledger})==len(ledger),'DUPLICATE_ITEM')
    w.require(sum(sum(u['itemCounts'].values()) for u in units)==len(ledger),'ITEM_ACCOUNTING')
    def table(counter):
        return [dict(key=list(key),count=n) for key,n in sorted(counter.items())]
    summary=dict(contract=VERSION,units=len(units),items=len(ledger),previouslyInvalidBatchDiagnostics=diagnostics,
                 historicalByPackage=table(historical_counts),dispositions=table(counts),sensitivity=table(sensitivity),
                 reasons=reasons,reasonsByCategory=table(reasons_by_category),reconciliationFlags=gates,admittedToPolicyEvaluation=sum(r['downstreamPolicyEvaluationPermitted'] for r in ledger),
                 approvals=0,providerCalls=0)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        stage=Path(temp)/'package';stage.mkdir()
        v3.coverage.write_rows(stage/'item-ledger.jsonl',ledger)
        v3.coverage.write_rows(stage/'unit-summaries.jsonl',units)
        w.live.save(stage/'summary.json',summary)
        w.live.save(stage/'manifest.json',dict(contract=VERSION,inputHashes=pins,outputHashes={
            p.name:w.r.identity.sha(p) for p in stage.iterdir()}))
        stage.rename(output)
    return summary


def verify(output):
    """Verify recorded input and output hashes against current bytes."""
    manifest=w.live.load(output/'manifest.json')
    for name,h in manifest['inputHashes'].items():w.require(w.r.identity.sha(Path(name))==h,'INPUT_DRIFT:'+name)
    for name,h in manifest['outputHashes'].items():w.require(w.r.identity.sha(output/name)==h,'OUTPUT_DRIFT:'+name)
    return w.live.load(output/'summary.json')


def main():
    """Network-disabled local replay and checksum verification."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['replay','verify']);parser.add_argument('--output',type=Path,default=ROOT)
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')), patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
        print(json.dumps((replay if args.mode=='replay' else verify)(args.output),indent=2))


if __name__=='__main__':main()
