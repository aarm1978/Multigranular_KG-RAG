"""Saved-decision overlap reconciliation without identity closure or new discovery."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import socket
import shutil
from unittest.mock import patch
from src.evaluation import step14_decision_stage as d

w=d.w
SOURCE=w.BASE/'decision-stage/v1'
ROOT=w.BASE/'decision-stage/v2'
OVERLAP='overlapping_eligible_complete_scopes_no_union'


def strength(row: dict) -> tuple[int,str] | None:
    """Recover pre-overlap route support from the saved complete-scope decisions."""
    saved=row.get('savedGroup') or {}
    guards=saved.get('safeguards',{})
    if guards.get('A') and all(v is True for v in guards['A'].values()):return 0,'A'
    if any(not x['reasons'] for x in row.get('routeC',[])):return 1,'C'
    if guards.get('B') and all(v is True for v in guards['B'].values()):return 2,'B'
    return None


def reconcile(rows: list[dict], protected: set[str]) -> tuple[list[dict],list[dict]]:
    """Select uncontested maximal existing scopes by evidence tier, retaining semantic ties."""
    candidates={};notes={}
    for row in rows:
        uid=row['simulationID'];ids=frozenset(row['occurrenceIDs']);support=strength(row)
        notes[uid]=dict(simulationID=uid,occurrenceIDs=sorted(ids),support=support,status='held_unsupported')
        conflicts=row.get('conflicts',{})
        if conflicts.get('savedPairs') or conflicts.get('contextual'):
            notes[uid]['status']='held_conflict';continue
        if ids & protected:
            notes[uid]['status']='held_protected_membership';continue
        if support:candidates[uid]=(ids,support,row)
    recovered=[];reserved=set(protected)
    for rank in range(3):
        current={u:x for u,x in candidates.items() if x[1][0]==rank and not x[0]&reserved}
        postings=defaultdict(set)
        for u,(ids,_,_) in current.items():
            for o in ids:postings[o].add(u)
        # A directly supported complete superset subsumes its smaller proposals;
        # this is never a union of their pair predictions.
        maximal={}
        for u,x in current.items():
            supers=set.intersection(*(postings[o] for o in x[0]))
            larger=[v for v in supers if x[0]<current[v][0]]
            if larger:notes[u].update(status='represented_by_complete_superset',alternatives=sorted(larger))
            else:maximal[u]=x
        maximal_ids=set(maximal)
        for u,(ids,route,row) in sorted(maximal.items()):
            competitors=(set.union(*(postings[o] for o in ids)) & maximal_ids)-{u}
            if competitors:
                notes[u].update(status='unresolved_equal_support',alternatives=sorted(competitors))
            else:
                result=deepcopy(row);result.update(state=d.ab.ACCEPTED,acceptedBy=[route[1]],holdReasons=[],holdKinds=[],
                    decisionVersion='step14-overlap-recovery/0.1.0',provisionalCanonicalID='step14-provisional:'+w.live.token(tuple(sorted(ids))),humanVerified=False)
                recovered.append(result);notes[u]['status']='recovered'
        # Reserve tied alternatives as well: weaker evidence cannot silently break a tie.
        reserved.update(o for ids,_,_ in maximal.values() for o in ids)
    for u,(ids,_,_) in candidates.items():
        if notes[u]['status']=='held_unsupported':notes[u]['status']='held_stronger_competing_scope'
    return recovered,[notes[u] for u in sorted(notes)]


def run(source: Path, output: Path) -> dict:
    """Read v1 decisions once; preserve all non-target dispositions and historical artifacts."""
    w.require(not output.exists() and output.resolve().is_relative_to((w.BASE/'decision-stage').resolve()),'FRESH_OUTPUT_REQUIRED')
    manifest=w.live.load(source/'manifest.json')
    for name,h in manifest['outputHashes'].items():w.require(w.r.identity.sha(source/name)==h,'V1_OUTPUT_DRIFT')
    rows=list(w.r.rows(source/'decision-ledger.jsonl'))
    targets=[r for r in rows if r['state']==d.ab.HELD and r['holdReasons']==[OVERLAP]]
    w.require(len(targets)==14051,'OVERLAP_POPULATION_DRIFT')
    approvals=list(w.r.rows(source/'historical-approvals.jsonl'))
    protected={o for row in rows if row['state'] in (d.ab.ACCEPTED,'researcher_approved_exact_scope') for o in row['occurrenceIDs']}
    protected.update(o for a in approvals for o in a['occurrenceIDs'])
    member_path=w.BASE/'referent-groups/v1/members.jsonl'
    w.require(w.r.identity.sha(member_path)==manifest['inputHashes'][str(member_path)],'MEMBER_DRIFT')
    members={x['occurrenceID']:x for x in w.r.rows(member_path)}
    pair_records={p['pairKeySha256']:p for p in w.r.rows(source/'pair-inventory.jsonl')}
    # Route C must refer to the complete exact scope; v1 already checked all endpoint citations.
    for row in targets:
        for support in row.get('routeC',[]):
            a=support['record']['value']
            w.require(set(a['occurrenceIDs'])==set(row['occurrenceIDs']),'C_MEMBERSHIP_DRIFT')
            w.require(d.route_c(a,members)==support['reasons'],'C_GUARD_DRIFT')
            if not support['reasons']:
                bound=support['record']['evidenceBindings']
                w.require({bound[q]['occurrenceID'] for q in a['supportingEvidenceIDs']}==set(row['occurrenceIDs']),'C_INCOMPLETE_EVIDENCE')
        saved=row.get('savedGroup')
        if saved:
            w.require(set(saved['occurrenceIDs'])==set(row['occurrenceIDs']),'AB_MEMBERSHIP_DRIFT')
            support=strength(row)
            if support and support[1]=='A':
                w.require(d.ab.identifier_guard(saved['originalKeys'],[members[o] for o in row['occurrenceIDs']]) is True,'OWNED_IDENTIFIER_SUPPORT')
            if support and support[1]=='B':
                direct=[pair_records[k] for k in saved['selectedPairKeys']]
                n=len(row['occurrenceIDs']);ids=set(row['occurrenceIDs'])
                w.require(len({tuple(sorted(p['occurrenceIDs'])) for p in direct})==n*(n-1)//2 and
                    all(set(p['occurrenceIDs'])<=ids and p['category']=='same_entity_candidate' and
                        p['coverageState']=='validated_recommendation' and p['modelIdentityLevel']=='entity' for p in direct),'INCOMPLETE_DIRECT_PAIR_SUPPORT')
    recovered,alternatives=reconcile(targets,protected)
    replacements={x['simulationID']:x for x in recovered}
    output.mkdir(parents=True)
    changed={'decision-ledger.jsonl','occurrence-mappings.jsonl','identity-evaluation-frame.jsonl','summary.json'}
    for name in manifest['outputHashes']:
        if name not in changed:shutil.copyfile(source/name,output/name)
    def emit(name,values):
        """Write deterministic ignored artifacts without graph updates."""
        with (output/name).open('xb') as stream:
            for value in values:stream.write(w.live.encode(value)+b'\n')
    emit('decision-ledger.jsonl',(replacements.get(x['simulationID'],x) for x in rows))
    mappings=list(w.r.rows(source/'occurrence-mappings.jsonl'));frame=list(w.r.rows(source/'identity-evaluation-frame.jsonl'))
    by_scope={scope:dict(groups=0,occurrences=set()) for scope in
              ('within_artifact','within_family_between_artifacts','between_families')}
    for row in recovered:
        records=[members[o] for o in row['occurrenceIDs']];scope=d.ab.group_scope(records)
        by_scope[scope]['groups']+=1;by_scope[scope]['occurrences'].update(row['occurrenceIDs'])
        for o in row['occurrenceIDs']:mappings.append(dict(occurrenceID=o,provisionalCanonicalID=row['provisionalCanonicalID'],decisionID=row['simulationID'],originalMember=members[o],materializationHeld=not row['representationCompatible'],humanVerified=False))
        frame.append(dict(decisionID=row['simulationID'],occurrenceIDs=row['occurrenceIDs'],routes=row['acceptedBy'],representationCompatible=row['representationCompatible'],humanVerified=False))
    w.require(len({x['occurrenceID'] for x in mappings})==len(mappings),'MAPPING_OVERLAP')
    emit('occurrence-mappings.jsonl',mappings);emit('identity-evaluation-frame.jsonl',frame);emit('overlap-alternatives.jsonl',alternatives)
    summary=w.live.load(source/'summary.json')
    summary.update(version='step14-overlap-recovery/0.1.0',recoveredGroups=len(recovered),recoveredOccurrences=sum(len(x['occurrenceIDs']) for x in recovered),
        recoveredByScope={k:dict(groups=v['groups'],occurrences=len(v['occurrences'])) for k,v in by_scope.items()},
        remainingOverlapBlockedGroups=len(targets)-len(recovered),overlapDispositions=dict(Counter(x['status'] for x in alternatives)),
        states=dict(Counter(replacements.get(x['simulationID'],x)['state'] for x in rows)),provisionalMappings=len(mappings),identityFrame=len(frame),
        limitation='Existing complete scopes only; no new membership unions or maximal-clique discovery. Equal-tier crossing alternatives remain held.')
    w.live.save(output/'summary.json',summary)
    pins=dict(manifest['inputHashes']);pins[str(source/'manifest.json')]=w.r.identity.sha(source/'manifest.json')
    for p in (Path(__file__),Path(d.__file__),Path(d.ab.__file__)):pins[str(p)]=w.r.identity.sha(p)
    w.live.save(output/'manifest.json',dict(inputHashes=pins,outputHashes={p.name:w.r.identity.sha(p) for p in output.iterdir() if p.is_file()}))
    return summary


def main() -> None:
    """Run only offline; use the researcher terminal for the full saved population."""
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--output',type=Path,default=ROOT);args=p.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
        print(w.json.dumps(run(args.source,args.output),indent=2))


if __name__=='__main__':main()
