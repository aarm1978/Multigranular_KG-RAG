"""Held-out sampling correction; reuse immutable calibration instructions and execution."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import json
import socket
import sqlite3
from unittest.mock import patch
from src.evaluation import step14_semantic_calibration as c

V1=c.ROOT/'v1'
ROOT=c.ROOT/'v2'
POLICY='step14-held-out-sampling/0.2.0'
DOC=Path('docs/study2_step14_calibration_sampling_v0.2.md')


def describe(uid: str, payload: dict) -> dict:
    """Count actual pair endpoints, never classify a whole unit by a single tag."""
    entities={x['id']:x for x in payload['entities']};cross=0;families=Counter()
    for pair in payload['pairs']:
        a,b=(entities[x]['sourceFamilies'] for x in pair['entities'])
        c.require(len(a)==len(b)==1,'AMBIGUOUS_SOURCE_FAMILY')
        cross+=a!=b;families['|'.join(sorted((a[0],b[0])))]+=1
    tags=sorted(c.p.tags(payload,set()))
    density='sparse' if len(payload['pairs'])<=2 else 'dense' if len(payload['pairs'])>=10 else 'medium'
    features={'density:'+density}|{'family:'+k for k in families}|{'tag:'+t for t in tags if t in ('recorded_specificity_difference','instance_language','generic_name_risk')}
    return dict(unitID=uid,tags=tags,crossPairs=cross,withinPairs=len(payload['pairs'])-cross,
                familyPairs=dict(families),features=sorted(features))


def select(rows: list, excluded: set) -> tuple[list,dict]:
    """Eight per scope, feasible cross-pair target, diversity gain then salted hash."""
    pool=[x for x in rows if x['unitID'] not in excluded];chosen=[];available={};unmet=[]
    for scope in ('cross','within'):
        candidates=[x for x in pool if bool(x['crossPairs'])==(scope=='cross')]
        available[scope]=dict(units=len(candidates),pairs=sum(x['crossPairs'] if scope=='cross' else x['withinPairs'] for x in candidates),
            features=dict(Counter(f for x in candidates for f in x['features'])))
        c.require(len(candidates)>=8,'INSUFFICIENT_'+scope.upper()+'_UNITS')
        maximum=sum(sorted((x['crossPairs'] for x in candidates),reverse=True)[:8]);target=min(24,maximum) if scope=='cross' else 0
        if scope=='cross' and maximum<24:unmet.append('24 cross-family pairs unavailable in eight units')
        selected=[];covered=set()
        for i in range(8):
            feasible=[]
            largest=sorted(candidates,key=lambda x:x["crossPairs"],reverse=True)[:9]
            for row in candidates:
                rest=[x['crossPairs'] for x in largest if x['unitID']!=row['unitID']][:7-i]
                if sum(x['crossPairs'] for x in selected)+row['crossPairs']+sum(rest)>=target:feasible.append(row)
            c.require(feasible,'SAMPLING_FEASIBILITY_DRIFT')
            row=min(feasible,key=lambda x:(-len(set(x['features'])-covered),c.live.token([POLICY,x['unitID']])))
            selected.append(row);covered.update(row['features']);candidates=[x for x in candidates if x['unitID']!=row['unitID']]
        chosen.extend(dict(x,selectionReason='scope_quota_feasible_diversity_gain_then_hash') for x in selected)
    return chosen,dict(policy=POLICY,available=available,unmetTargets=unmet,excludedUnits=sorted(excluded),selected=chosen,
        crossPairs=sum(x['crossPairs'] for x in chosen),withinPairs=sum(x['withinPairs'] for x in chosen),
        crossUnits=sum(bool(x['crossPairs']) for x in chosen),withinOnlyUnits=sum(not x['crossPairs'] for x in chosen),
        familyPairs=dict(sum((Counter(x['familyPairs']) for x in chosen),Counter())))


def prepare(root: Path) -> dict:
    """Adapt preparation writes only; never regenerate or dispatch development requests."""
    c.require(not root.exists(),'FRESH_OUTPUT_REQUIRED');old=c.verify(V1)
    historical=c.live.load(V1/'report.json')
    c.require(historical['stages']['development']['matchedPairs']==83,'DEVELOPMENT_INCOMPLETE')
    for case in old['cases']['development']:
        cid=case['caseID'];_,value=c.result(V1/'development'/'attempts'/cid,c.live.load(V1/'development'/'requests'/f'{cid}.json'))
        c.require(value is not None,'DEVELOPMENT_NOT_VALIDATED')
    c.require(not any((V1/'held-out').glob('*/attempts/*/intent.json')),'V1_HELD_ALREADY_EXECUTED')
    pins={str(p):c.r.identity.sha(p) for p in V1.rglob('*') if p.is_file() and p.name!='.execution.lock'}
    for p in (Path(__file__),DOC):pins[str(p)]=c.r.identity.sha(p)
    excluded={x['unitID'] for cases in old['cases'].values() for x in cases};pairs=set()
    for case in old['cases']['development']:
        pairs.update(c.live.load(V1/'development'/'audit'/f"{case['caseID']}.json")['originalBinding']['pairs'].values())
    with sqlite3.connect((c.p.SOURCE/'coverage.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        for key in pairs:
            found=db.execute('SELECT unit FROM candidates WHERE pairkey=?',(key,)).fetchone()
            c.require(found is not None,'DEVELOPMENT_PAIR_MISSING');excluded.add(found[0])
    rows=[describe(x['unitID'],x['payload']) for x in c.r.rows(c.p.SOURCE/'contexts.jsonl')]
    selected,sampling=select(rows,excluded);sampling['excludedDevelopmentPairHashes']=sorted(pairs)
    save=c.live.save
    def adapted_save(path, value, **kwargs):
        """Keep the native builder's verified held-out envelopes, omit development writes."""
        rel=path.relative_to(root) if path.is_relative_to(root) else None
        if rel and rel.parts[0]=='development':return
        if rel==Path('preparation.json'):
            value=dict(value,developmentUnits=0,developmentPairs=0,newRequests=dict(development=0,heldOut=32),historicalDevelopment=str(V1),samplingPolicy=POLICY)
        if rel==Path('manifest.json'):
            value['cases']['development']=[];value['inputHashes'].update(pins)
            for p,h in pins.items():c.r.preflight.pilot.verify(Path(p),h,{})
            save(root/'sampling.json',sampling)
            save(root/'historical-development.json',historical['stages']['development'])
            text='# Held-out sampling v2\n\n'+f"Cross-family: {sampling['crossPairs']} pairs in {sampling['crossUnits']} units. Within-family: {sampling['withinPairs']} pairs; {sampling['withinOnlyUnits']} within-only units.\n\n"
            text+='Selection uses only source metadata and pair structure; no recommendation outcomes. No identity or accuracy conclusions.\n\n'
            text+='| Unit | Cross pairs | Within pairs | Tags |\n|---|---:|---:|---|\n'
            text+=''.join(f"| {x['unitID']} | {x['crossPairs']} | {x['withinPairs']} | {', '.join(x['tags'])} |\n" for x in selected)
            c.live.write(root/'sampling.md',text.encode())
            for name in ('sampling.json','sampling.md','historical-development.json'):value['outputHashes'][name]=c.r.identity.sha(root/name)
        return save(path,value,**kwargs)
    with patch.object(c,'select_held',return_value=selected),patch.object(c.live,'save',side_effect=adapted_save):c.prepare(root)
    c.verify(root)
    return sampling


def main() -> None:
    """Only the separately named held-out live gate can dispatch requests."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','dry-run','report','run-held-out'])
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.command=='run-held-out':value=c.execute(args.root,'held-out',args.execute)
    else:
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
            value=prepare(args.root) if args.command=='prepare' else c.report(args.root) if args.command=='report' else dict(status='verified',cases=c.verify(args.root)['cases'])
    print(json.dumps(value,sort_keys=True))


if __name__=='__main__':main()
