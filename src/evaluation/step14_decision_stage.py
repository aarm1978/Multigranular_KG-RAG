"""Offline decision-stage ledger: provisional A/B/C identities, never production KG writes."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import socket
from unittest.mock import patch
import yaml
from src.evaluation import step14_alignment_workflow as w
from src.evaluation import step14_automatic_acceptance_preview as ab

ROOT=w.BASE/'decision-stage/v1'
CONSOLIDATED=w.BASE/'alignment-workflow/live-recovery-v1/consolidated-v1'
PREPARED=w.BASE/'alignment-workflow/prepared-v018-source-context'
VERSION='step14-decision-stage/0.1.0'


def membership(ids: list) -> tuple:
    """Canonicalize exact memberships, without unions or transitive closure."""
    w.require(len(ids)==len(set(ids)) and len(ids)>=2,'INVALID_MEMBERSHIP')
    return tuple(sorted(ids))


def route_c(assessment: dict, members: dict) -> list[str]:
    """Treat complete strict predictions as support; do not interpret uncertainty prose as truth."""
    records=[members[o] for o in membership(assessment['occurrenceIDs'])]
    reasons=[]
    if assessment['category']!='strict_identity':reasons.append('not_strict_identity')
    if not assessment['granularity'].strip():reasons.append('missing_granularity_assessment')
    if assessment['contradictoryEvidenceIDs']:reasons.append('contradictory_evidence')
    if len({(e['ontologyClass'],e['inventoryId']) for e in records})!=1:reasons.append('class_inventory_conflict')
    if any(not e.get('originalReference') or not e.get('evidencePointers') for e in records):reasons.append('missing_original_evidence')
    if any(set(e.get('preparationFlags',[])) & {'missing_provenance','ontology_class_inventory_mismatch','abstract_class_retained_not_retyped'} for e in records):reasons.append('preparation_exclusion')
    signals=ab.compatibility_signals(records,[])
    return sorted(set(reasons+signals['demonstratedConflicts']+signals['unresolvedAmbiguities']))


def overlapping(rows: list[dict]) -> None:
    """Reuse the existing conservative complete-scope overlap guard, without choosing winners."""
    ab.prevent_overlaps(rows)


def run(output: Path) -> dict:
    """Read saved authorities once and emit lossless, evidence-bound materialization candidates."""
    w.require(not output.exists() and output.resolve().is_relative_to((w.BASE/'decision-stage').resolve()),'FRESH_OUTPUT_REQUIRED')
    pins={}
    def pin(path, expected=None):
        """Verify and record the actual consumed bytes."""
        w.r.preflight.pilot.verify(path,expected or w.r.identity.sha(path),pins);return path
    def artifact(folder,name):
        """Consume producer-hashed outputs, never regenerate upstream artifacts."""
        m=w.live.load(pin(folder/'manifest.json'));return pin(folder/name,m['outputHashes'][name])
    summary=w.live.load(pin(CONSOLIDATED/'summary.json'))
    units=list(w.r.rows(pin(CONSOLIDATED/'units.jsonl',summary['unitsSha256'])))
    w.require(len(units)==1795 and sum(x['unresolved'] for x in units)==31,'CONSOLIDATED_COUNT')
    requests={x['custom_id']:x['body'] for x in w.r.rows(artifact(PREPARED,'requests.jsonl'))}
    aliases=w.live.load(artifact(PREPARED,'alias-bindings.json'))
    evidence={x['occurrenceID']:x for x in w.r.rows(artifact(PREPARED,'occurrence-provenance.jsonl'))}
    members={x['occurrenceID']:x for x in w.r.rows(artifact(w.BASE/'referent-groups/v1','members.jsonl'))}
    originals=list(w.r.rows(artifact(w.BASE/'automatic-acceptance-preview/v2-null-summary-fix','group-simulations.jsonl')))
    pairs=list(w.r.rows(artifact(w.BASE/'adjudication-triage/v1','pair-inventory.jsonl')))
    routing=list(w.r.rows(artifact(PREPARED,'pair-routing.jsonl')))
    approvals=list(w.r.rows(artifact(PREPARED,'prior-decisions.jsonl')))
    spec=yaml.safe_load(pin(w.SPEC).read_text());w.require(spec['ontology']['version']=='0.1.8','ONTOLOGY_VERSION')
    hierarchy=w.ancestors(spec);signatures={r['id']:r for r in spec['relations']}
    w.require(len(pairs)==74051 and sum(bool(g['occurrenceIDs']) for g in originals)==51079,'BASELINE_COUNT')
    rows={};original_by_members=defaultdict(list)
    for g in originals:
        if not g['occurrenceIDs']:continue
        key=membership(g['occurrenceIDs']);original_by_members[key].append(g['simulationID'])
        rows[key]=dict(simulationID=g['simulationID'],occurrenceIDs=list(key),state=g['state'],
            acceptedBy=list(g['acceptedBy']),holdReasons=list(g['holdReasons']),holdKinds=list(g['holdKinds']),
            savedGroup=g,routeC=[],originalGroupIDs=[g['simulationID']],humanVerified=False)
    # Explicit scoped predictions, not inferred positive pair closure.
    assessments=[];relations=defaultdict(list);gaps=[];abstentions=[];invalid=[];opposition=[]
    for unit in units:
        uid=unit['unitID']
        if unit['unresolved']:invalid.append(unit);continue
        body=requests[uid];w.validate(unit['hypotheses'],body)
        resolved=w.resolve_output(unit['hypotheses'],aliases[uid]);w.require(resolved==unit['resolvedHypotheses'],'RESOLUTION_DRIFT')
        payload=w.json.loads(body['input']);bound={}
        for e in payload['occurrences']:
            oid=aliases[uid][e['occurrenceID']]
            for j,q in enumerate(e['evidence']):
                original=evidence[oid]['endpoint']['selectedEvidence'][j]
                w.require(q['text']==original['literalExcerpt'],'QUOTE_DRIFT')
                bound[q['evidenceID']]=dict(occurrenceID=oid,originalReference=evidence[oid]['endpoint']['originalReference'],selectedEvidence=original)
        def record(value,field,index):
            """Bind every local evidence alias to its original source record."""
            return dict(unitID=uid,field=field,index=index,value=value,evidenceBindings=bound,
                        selectedArtifacts=unit['selectedArtifacts'],origin=unit['origin'])
        for i,a in enumerate(resolved['assessments']):
            rec=record(a,'assessments',i);assessments.append(rec)
            if a['category']=='abstention':abstentions.append(rec)
            if a['category'] in ('distinct','related_nonidentical') or a['contradictoryEvidenceIDs']:
                opposition.append((set(a['occurrenceIDs']),rec))
            if a['category']!='strict_identity':continue
            key=membership(a['occurrenceIDs'])
            if key not in rows:rows[key]=dict(simulationID='anchor:'+w.live.token(key),occurrenceIDs=list(key),state=ab.HELD,acceptedBy=[],holdReasons=[],holdKinds=[],savedGroup=None,routeC=[],originalGroupIDs=[],humanVerified=False)
            rows[key]['routeC'].append(dict(record=rec,reasons=route_c(a,members)))
        for i,rel in enumerate(resolved['typedRelations']):
            sig=signatures[rel['signatureID']];a,b=rel['subject'],rel['object']
            w.require(w.fits(members[a]['ontologyClass'],sig['domain'],hierarchy) and w.fits(members[b]['ontologyClass'],sig['range'],hierarchy),'ONTOLOGY_SIGNATURE')
            relations[(a,sig['name'],b)].append(record(rel,'typedRelations',i))
            if sig['id'] in ('D-27','D-28'):opposition.append(({a,b},record(rel,'typedRelations',i)))
        gaps.extend(record(g,'ontologyGaps',i) for i,g in enumerate(resolved['ontologyGaps']))
    # Negative or explicit conflict predictions cannot silently disappear behind a new strict group.
    negative={tuple(sorted(p['occurrenceIDs'])):p for p in pairs if p['category']=='different_entities_candidate' or (p.get('assessment') or {}).get('conflictEvidenceIDs')}
    approval_sets=[set(a['occurrenceIDs']) for a in approvals]
    index=defaultdict(set)
    for key in rows:
        for o in key:index[o].add(key)
    conflicts=defaultdict(list)
    for ids,ref in opposition:
        counts=Counter(k for o in ids for k in index.get(o,()))
        for key,n in counts.items():
            if n>=2:conflicts[key].append(ref)
    for key,row in rows.items():
        reasons=[];ids=set(key)
        neg=[negative[p] for p in combinations(key,2) if p in negative]
        if neg:reasons.append('saved_negative_or_conflicting_pair')
        if conflicts[key]:reasons.append('contextual_conflicting_memberships_or_version_variant_relation')
        if any(ids & a and ids!=a for a in approval_sets):reasons.append('partial_historical_approval_overlap')
        if any(ids==a for a in approval_sets):
            row['state']='researcher_approved_exact_scope';row['acceptedBy']=[]
        else:
            c=row['routeC']
            if c and any(not x['reasons'] for x in c):
                row['state']=ab.ACCEPTED;row['acceptedBy']=sorted(set(row['acceptedBy'])|{'C'})
                row['holdReasons']=[]
            if c and any(x['reasons'] for x in c):reasons.append('conflicting_or_unsupported_route_c_assessment')
            if reasons:
                row['state']=ab.HELD;row['acceptedBy']=[]
            row['holdReasons']=sorted(set(row['holdReasons']+reasons+[reason for x in c for reason in x['reasons']]))
        row['conflicts']=dict(savedPairs=neg,contextual=conflicts[key])
        row['completeMembershipSupport']=bool(row['routeC'])
        row['crossRequestSupportPolicy']='exact complete assessment required; partial chains never combined'
    overlapping(list(rows.values()))
    d16=signatures['D-16'];mappings=[];identity_frame=[]
    for key,row in rows.items():
        row['representationCompatible']=all(w.fits(members[o]['ontologyClass'],d16['range'],hierarchy) for o in key)
        row['decisionVersion']=VERSION
        if row['state']==ab.ACCEPTED:
            cid='step14-provisional:'+w.live.token(key)
            row['provisionalCanonicalID']=cid
            for o in key:mappings.append(dict(occurrenceID=o,provisionalCanonicalID=cid,decisionID=row['simulationID'],originalMember=members[o],materializationHeld=not row['representationCompatible'],humanVerified=False))
            identity_frame.append(dict(decisionID=row['simulationID'],occurrenceIDs=list(key),routes=row['acceptedBy'],representationCompatible=row['representationCompatible'],humanVerified=False))
    output.mkdir(parents=True)
    def emit(name,values):
        """Write immutable local JSONL, with no graph mutation."""
        with (output/name).open('xb') as f:
            for value in values:f.write(w.live.encode(value)+b'\n')
    emit('decision-ledger.jsonl',rows.values());emit('occurrence-mappings.jsonl',mappings)
    emit('historical-approvals.jsonl',approvals);emit('invalid-units.jsonl',invalid)
    emit('assessment-inventory.jsonl',assessments);emit('abstentions.jsonl',abstentions);emit('ontology-gaps.jsonl',gaps)
    typed=[dict(proposalID=w.live.token(key),subject=key[0],predicate=key[1],object=key[2],support=refs,status='evidence_bound_proposal_not_approved') for key,refs in sorted(relations.items())]
    emit('typed-relation-proposals.jsonl',typed)
    emit('identity-evaluation-frame.jsonl',identity_frame);emit('relation-evaluation-frame.jsonl',typed)
    emit('pair-inventory.jsonl',pairs);emit('pair-routing.jsonl',routing)
    emit('oversized-scopes.jsonl',(g for g in originals if not g['occurrenceIDs']))
    emit('original-group-reconciliation.jsonl',(dict(originalGroupID=g['simulationID'],occurrenceIDs=g['occurrenceIDs'],decisionID=rows[membership(g['occurrenceIDs'])]['simulationID'],completeContextualAssessment=bool(rows[membership(g['occurrenceIDs'])]['routeC'])) for g in originals if g['occurrenceIDs']))
    # Original Step 13 assertions remain at their original paths; retain file hashes, never rewrite endpoints.
    assertion_refs=[]
    for path in map(Path,['data/interim/papers/publication_nodes_edges.json','data/interim/datasets/hydroshare_nodes_edges.json','data/interim/coderepos/github_nodes_edges.json','data/interim/documents/ciroh_hub_nodes_edges.json']):
        pin(path);assertion_refs.append(dict(path=str(path),sha256=pins[str(path)],mode='unchanged_assertion_reference'))
    w.live.save(output/'original-assertion-references.json',assertion_refs)
    counts=Counter(x['status'] for x in routing)
    w.require(counts['identity_lead_deferred_no_pair_reevaluation']==27310 and counts['preserved_not_renominated']==36573,'ROUTING_COUNTS')
    report=dict(version=VERSION,originalPairs=len(pairs),originalGroups=51079,contextualUnits=len(units),invalidUnits=len(invalid),
        states=dict(Counter(x['state'] for x in rows.values())),provisionalMappings=len(mappings),typedRelationProposals=len(typed),
        originalGroupsWithoutCompleteContextualAssessment=sum(not rows[k]['routeC'] for k in original_by_members),pairRouting=dict(counts),
        identityFrame=len(identity_frame),relationFrame=len(typed),historicalApprovals=len(approvals),humanSampleDrawn=False,graphWrites=0)
    w.live.save(output/'summary.json',report)
    for path in (Path(__file__),Path(ab.__file__),Path(w.__file__),Path('docs/study2_step14_automatic_identity_acceptance_v0.1.md')):pin(path)
    w.live.save(output/'manifest.json',dict(inputHashes=pins,outputHashes={p.name:w.r.identity.sha(p) for p in output.iterdir() if p.is_file()}))
    return report


def main() -> None:
    """Offline only; researcher-terminal execution is recommended for the full inventory."""
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT);args=p.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
        print(w.json.dumps(run(args.output),indent=2))


if __name__=='__main__':main()
