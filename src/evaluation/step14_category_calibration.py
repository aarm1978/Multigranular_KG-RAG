"""Eight-unit instruction-only category diagnostic; no identity decisions."""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json
import socket
import sqlite3
from unittest.mock import patch
from src.evaluation import step14_calibration_sampling as s
c=s.c
ROOT=c.ROOT/'v3'
VERSION='step14-category-calibration/0.1.0'
DOC=Path('docs/study2_step14_category_calibration_v0.1.md')
CLARIFICATION='''
Category-boundary clarification:
Failure to establish entity identity does not automatically require abstention.
When the supplied evidence demonstrates a shared named technique, architecture or model-family concept, conceptual_similarity_only remains available even when versions or trained instances cannot be equated. This conceptual observation does not equate those instances or discard their specificity.
shared_reference_target_only requires evidence that both endpoints identify the same reference target; a common label alone is insufficient.
same_entity_candidate requires evidence of the same referent at compatible actual granularity. different_entities_candidate requires positive evidence of distinct referents.
Use abstain when the supplied evidence does not substantiate any of the other categories.
Preserve version, implementation, trained-instance and dataset-subset distinctions; source/reference and mentions/uses roles; ontology-class compatibility; endpoint-local evidence and non-transitivity. Do not use external knowledge or infer missing specificity.
'''


def revised(body: dict) -> dict:
    """Append only the approved category clarification to current prospective instructions."""
    value=deepcopy(body);value['instructions']+='\n'+CLARIFICATION;return value


def comparable(a: dict,b: dict) -> None:
    """Bind current-prospective versus revised instructions and all unchanged fields."""
    c.require(a['instructions']==c.p.PROMPT+'\n'+c.CLARIFICATION,'CURRENT_INSTRUCTIONS_DRIFT')
    c.require(revised(a)==b,'ARM_COMPARABILITY_DRIFT')


def select(rows: list, excluded: set) -> tuple[list,dict]:
    """Four per scope, metadata diversity then predeclared salted hash."""
    chosen=[];available={}
    for cross in (True,False):
        pool=[x for x in rows if x['unitID'] not in excluded and bool(x['crossPairs'])==cross]
        available[str(cross)]=dict(units=len(pool),features=dict(Counter(f for x in pool for f in x['features'])))
        c.require(len(pool)>=4,'INSUFFICIENT_SCOPE_UNITS');covered=set()
        for _ in range(4):
            row=min(pool,key=lambda x:(-len(set(x['features'])-covered),c.live.token([VERSION,x['unitID']])))
            chosen.append(dict(row,selectionReason='scope_quota_metadata_gain_then_hash'));covered.update(row['features']);pool.remove(row)
    return chosen,dict(version=VERSION,available=available,selected=chosen,excludedUnits=sorted(excluded),
        crossPairs=sum(x['crossPairs'] for x in chosen),withinPairs=sum(x['withinPairs'] for x in chosen),
        sourceFamilyPairs=dict(sum((Counter(x['familyPairs']) for x in chosen),Counter())))


def verify(root: Path) -> dict:
    """Use historical hash guards and the explicit new arm comparison only."""
    with patch.object(c,'comparable',side_effect=comparable):return c.verify(root)


def prepare(root: Path) -> dict:
    """Freeze new contexts without altering or reusing historical requests as live work."""
    c.require(not root.exists(),'FRESH_OUTPUT_REQUIRED');pins={};excluded=set();pairs=set()
    for prior in (c.ROOT/'v1',c.ROOT/'v2'):
        manifest=c.verify(prior)
        for path in prior.rglob('*'):
            if path.is_file() and path.name!='.execution.lock':pins[str(path)]=c.r.identity.sha(path)
        for stage,key in (('development','development'),('held-out','heldOut')):
            for case in manifest['cases'][key]:
                excluded.add(case['unitID']);audit=c.live.load(prior/stage/'audit'/f"{case['caseID']}.json")
                pairs.update(audit['originalBinding']['pairs'].values())
    for path in (Path(__file__),Path(s.__file__),DOC):pins[str(path)]=c.r.identity.sha(path)
    with sqlite3.connect((c.p.SOURCE/'coverage.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        for key in pairs:
            found=db.execute('SELECT unit FROM candidates WHERE pairkey=?',(key,)).fetchone()
            c.require(found is not None,'HISTORICAL_PAIR_MISSING');excluded.add(found[0])
    rows=[]
    for item in c.r.rows(c.p.SOURCE/'contexts.jsonl'):
        row=s.describe(item['unitID'],item['payload'])
        classes={x['ontologyClass'] for x in item['payload']['entities']}
        if classes & {'MLModel','ProcessBasedModel','ConceptualModel','Algorithm'}:row['features'].append('named_technique_or_model_class')
        rows.append(row)
    selected,sampling=select(rows,excluded);sampling['excludedPairHashes']=sorted(pairs)
    sampling['armLabels']={'original':'current_prospective','prospective':'category_revised'}
    save=c.live.save
    def adapted_save(path,value,**kwargs):
        """Reuse native context construction while replacing only saved arm instructions."""
        rel=path.relative_to(root) if path.is_relative_to(root) else None
        if rel and rel.parts[0]=='development':return
        if rel and 'requests' in rel.parts and rel.parts[0]=='held-out':
            value=c.variant(value) if rel.parts[1]=='original' else revised(value)
        if rel==Path('preparation.json'):
            value=dict(value,developmentUnits=0,developmentPairs=0,newRequests=dict(development=0,heldOut=16),categoryCalibration=VERSION,armLabels=sampling['armLabels'])
        if rel==Path('manifest.json'):
            value['cases']['development']=[];value['inputHashes'].update(pins)
            for p,h in pins.items():c.r.preflight.pilot.verify(Path(p),h,{})
            save(root/'sampling.json',sampling)
            text='# Category diagnostic preparation\n\nEight new units; 16 requests. Original arm = current prospective; prospective arm = category revised.\n\n'
            text+=f"Cross-family pairs: {sampling['crossPairs']}; within-family pairs: {sampling['withinPairs']}.\n\n"
            text+='| Unit | Cross | Within | Tags |\n|---|---:|---:|---|\n'+''.join(f"| {x['unitID']} | {x['crossPairs']} | {x['withinPairs']} | {', '.join(x['tags'])} |\n" for x in selected)
            text+='\nPurpose-stratified diagnostic only. Prior v1/v2 results are historical, not evaluation of this revision. No accuracy or identity conclusions. Family concentration is recorded in sampling.json.\n'
            c.live.write(root/'sampling.md',text.encode())
            for name in ('sampling.json','sampling.md'):value['outputHashes'][name]=c.r.identity.sha(root/name)
        return save(path,value,**kwargs)
    with patch.object(c,'select_held',return_value=selected),patch.object(c.live,'save',side_effect=adapted_save):c.prepare(root)
    verify(root);return sampling


def main() -> None:
    """Offline preparation/reporting and separately initiated existing once-only execution."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','dry-run','report','run-held-out'])
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.command=='prepare':
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):value=prepare(args.root)
    else:
        with patch.object(c,'comparable',side_effect=comparable):
            if args.command=='run-held-out':value=c.execute(args.root,'held-out',args.execute)
            else:
                with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
                    value=c.report(args.root) if args.command=='report' else dict(status='verified',cases=c.verify(args.root)['cases'])
    print(json.dumps(value,sort_keys=True))


if __name__=='__main__':main()
