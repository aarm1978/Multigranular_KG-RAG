"""Reconcile complete collective memberships against saved Step 14 authorities offline."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import tempfile

import yaml
from src.evaluation import step14_collective_item_replay as replay
from src.evaluation import step14_overlap_recovery as recovery

w = replay.w
d = recovery.d
PRIOR = recovery.ROOT
ROOT = w.BASE / 'collective-identity-reconciliation/v1'
VERSION = 'collective-identity-reconciliation/0.1.0'
SCOPES = ('within_artifact', 'within_family_between_artifacts', 'between_families')


def ref(item):
    """Reference one exact original item within its hashed v4 ledger."""
    return (item['unitID'], item['itemType'], item['itemIndex'])


def collective_index(items, units):
    """Keep strict groups separate, and resolve local opposition only within its window."""
    positives = defaultdict(list)
    memberships = defaultdict(set)
    strict_refs = defaultdict(set)
    opposition = defaultdict(set)
    for item in items:
        ids = tuple(sorted(item['occurrenceIDs']))
        if item['category'] == 'strict_identity':
            strict_refs[ids].add(ref(item))
            for oid in ids:
                memberships[oid].add(ids)
            if item['status'] == replay.VALID:
                positives[ids].append(item)
            else:
                opposition[ids].add(ref(item))
        elif item['category'] == 'distinct' and len(ids) == 1:
            for other in units[item['unitID']]['aliasBindings'].values():
                if other != ids[0]:
                    opposition[tuple(sorted((ids[0], other)))].add(ref(item))
        elif item['itemType'] == 'typedRelations' and item['modelItem']['signatureID'] in ('D-27','D-28'):
            opposition[ids].add(ref(item))
    return positives, memberships, strict_refs, opposition


def prior_index(read):
    """Index exact baseline routes, unresolved competitors, historical scopes and opposition."""
    mappings = list(read(PRIOR, 'occurrence-mappings.jsonl'))
    protected = {r['occurrenceID'] for r in mappings}
    approvals = list(read(PRIOR, 'historical-approvals.jsonl'))
    protected.update(o for r in approvals for o in r['occurrenceIDs'])
    alternatives = {}
    exact = {}
    for row in read(PRIOR, 'decision-ledger.jsonl'):
        key = tuple(sorted(row['occurrenceIDs']))
        guards = (row.get('savedGroup') or {}).get('safeguards', {})
        routes = [route for route in ('A','B') if guards.get(route) and
                  all(v is True for v in guards[route].values())]
        exact[key] = dict(id=row['simulationID'], routes=routes,
                          contextualHolds=sorted({r for s in row['routeC'] for r in s['reasons']}))
        if row['state'] == d.ab.HELD and row['holdReasons'] == [recovery.OVERLAP]:
            alternatives[key] = row
    opposition = defaultdict(set)
    for p in read(PRIOR, 'pair-inventory.jsonl'):
        if p['category']=='different_entities_candidate' or (p.get('assessment') or {}).get('conflictEvidenceIDs'):
            opposition[tuple(sorted(p['occurrenceIDs']))].add(('pair',p['pairKeySha256']))
    for r in read(PRIOR, 'assessment-inventory.jsonl'):
        a = r['value']
        if a['category'] in ('distinct','related_nonidentical') or a['contradictoryEvidenceIDs']:
            for pair in combinations(sorted(a['occurrenceIDs']),2):
                opposition[pair].add(('assessment',r['unitID'],r['index']))
    for r in read(PRIOR,'typed-relation-proposals.jsonl'):
        if r['predicate'] in ('isVariantOf','isVersionOf'):
            opposition[tuple(sorted((r['subject'],r['object'])))].add(('relation',r['proposalID']))
    return mappings, approvals, protected, exact, alternatives, opposition


def reconcile(items, units, members, prior, *, check_v4):
    """Apply the stored collective gate, route C and saved A/B/C precedence to exact groups."""
    _, _, protected, exact, alternatives, prior_opposition = prior
    positives, memberships, strict_refs, opposition = collective_index(items,units)
    candidates = dict(alternatives)
    groups = {}
    for key, appearances in sorted(positives.items()):
        exemplar = appearances[0]
        flags, eligible = replay.reconciliation_gate(exemplar, protected, memberships, opposition)
        if check_v4:
            w.require(all(a['reconciliationFlags']==flags and a['downstreamPolicyEvaluationPermitted']==eligible
                          for a in appearances), 'V4_GATE_DRIFT')
        conflicts = set.union(*(memberships[o] for o in key)) - {key}
        opposing_items = set().union(*(opposition.get(k, set()) for k in (key,*combinations(key,2))))
        earlier = set().union(*(prior_opposition.get(p,set()) for p in combinations(key,2)))
        reasons = set(flags)
        if earlier:
            reasons.add('prior_opposition')
        saved = exact.get(key, {})
        reasons.update(saved.get('contextualHolds',[]))
        for a in appearances:
            bound = {q['binding']['occurrenceID'] for q in a['citations']
                     if q['field']=='supportingEvidenceIDs' and q['location']=='member' and q['binding']}
            w.require(bound==set(key) and not a['externalEvidenceIDs'], 'MEMBER_EVIDENCE_DRIFT')
            reasons.update(d.route_c(dict(a['modelItem'],occurrenceIDs=list(key)), members))
        cid = 'step14-provisional:'+w.live.token(key)
        group = dict(groupID='collective:'+w.live.token(key), occurrenceIDs=list(key),
                     identityScope=d.ab.group_scope([members[o] for o in key]),
                     appearanceReferences=[ref(a) for a in appearances],
                     recoveredAppearances=sum(a['v3Status']=='invalid_or_incomplete' for a in appearances),
                     collectiveGateReasons=flags, collectiveGatePermitted=eligible,
                     competingCollectiveScopes=[dict(occurrenceIDs=k, items=sorted(strict_refs[k])) for k in sorted(conflicts)],
                     opposingCollectiveItems=sorted(opposing_items), priorOpposition=sorted(earlier),
                     priorDecisionID=saved.get('id'), routes=sorted(['C',*saved.get('routes',[])]),
                     reasons=sorted(reasons),state=d.ab.HELD, humanVerified=False)
        groups[key] = group
        if reasons:
            continue
        # Upgrade only a complete, eligible exact membership. Preserve the saved A/B guards.
        row = candidates.get(key, {})
        candidates[key] = dict(simulationID=group['groupID'], occurrenceIDs=list(key),
                               savedGroup=dict(safeguards={r:{'savedCompleteGuards':True} for r in saved.get('routes',[])}),
                               routeC=[dict(reasons=[])], conflicts=row.get('conflicts',{}))
    selected, notes = recovery.reconcile(list(candidates.values()),protected)
    accepted = {r['simulationID']:r for r in selected}
    by_id = {n['simulationID']:n for n in notes}
    for key, g in groups.items():
        if g['reasons']:
            continue
        uid = g['groupID']
        if uid in accepted:
            g.update(state=d.ab.ACCEPTED, provisionalCanonicalID=accepted[uid]['provisionalCanonicalID'],
                     acceptedBy=accepted[uid]['acceptedBy'])
        else:
            g['reasons']=[by_id[uid]['status']]
            g['priorOrCollectiveAlternatives']=by_id[uid].get('alternatives',[])
    return groups


def metrics(keys, groups):
    """Count unique occurrences separately in each complete-membership scope."""
    result = {}
    for scope in (*SCOPES,'all'):
        selected = [k for k in keys if scope=='all' or groups[k]['identityScope']==scope]
        result[scope]=dict(groups=len(selected),occurrences=len({o for k in selected for o in k}))
    return result


def run(output):
    """Publish audited group and mapping ledgers with a same-policy v3-only comparison."""
    w.require(not output.exists(),'FRESH_OUTPUT_REQUIRED')
    pins = {}
    def read(folder,name):
        """Check the producer's digest before reading a saved authority."""
        path = folder/name
        manifest = folder/'manifest.json'
        pins[str(manifest)] = w.r.identity.sha(manifest)
        pins[str(path)] = w.live.load(manifest)['outputHashes'][name]
        w.require(w.r.identity.sha(path)==pins[str(path)],'INPUT_DRIFT:'+name)
        return w.r.rows(path)
    items=list(read(replay.ROOT,'item-ledger.jsonl'))
    units={u['unitID']:u for u in read(replay.ROOT,'unit-summaries.jsonl')}
    members={r['occurrenceID']:r['member'] for r in read(replay.v3.legacy.ROOT,'occurrence-provenance.jsonl')}
    prior=prior_index(read)
    for p in (w.SPEC,Path(__file__),Path(d.__file__),Path(d.ab.__file__),Path(recovery.__file__),Path(replay.__file__),
              Path('docs/study2_step14_automatic_identity_acceptance_v0.1.md'),Path('docs/study2_step14_decision_stage.md')):
        pins[str(p)]=w.r.identity.sha(p)
    spec=yaml.safe_load(w.SPEC.read_text())
    w.require(spec['ontology']['version']=='0.1.8','ONTOLOGY_VERSION')
    hierarchy=w.ancestors(spec)
    target=next(r['range'] for r in spec['relations'] if r['id']=='D-16')
    groups=reconcile(items,units,members,prior,check_v4=True)
    old=reconcile([r for r in items if r['v3Status']=='validated_hypotheses_only'],units,members,prior,check_v4=False)
    current={k for k,g in groups.items() if g['state']==d.ab.ACCEPTED}
    previous={k for k,g in old.items() if g['state']==d.ab.ACCEPTED}
    mappings=list(prior[0])
    for key in sorted(current):
        g=groups[key]
        compatible=all(w.fits(members[o]['ontologyClass'],target,hierarchy) for o in key)
        g['representationCompatible']=compatible
        for o in key:
            mappings.append(dict(occurrenceID=o,originalMember=members[o],decisionID=g['groupID'],
                                 provisionalCanonicalID=g['provisionalCanonicalID'],humanVerified=False,
                                 materializationHeld=not compatible))
    w.require(len(mappings)==len({m['occurrenceID'] for m in mappings}),'MAPPING_OVERLAP')
    eligible={k for k,g in groups.items() if g['collectiveGatePermitted']}
    held=set(groups)-current
    recovered=Counter()
    for g in groups.values():
        if g['recoveredAppearances']:
            recovered['+'.join(g['collectiveGateReasons']) or 'permitted']+=g['recoveredAppearances']
    summary=dict(version='collective-identity-reconciliation/1',admissibleAppearances=sum(len(g['appearanceReferences']) for g in groups.values()),
                 eligibleAppearances=sum(len(groups[k]['appearanceReferences']) for k in eligible),
                 uniqueCandidates=metrics(groups,groups),eligible=metrics(eligible,groups),held=metrics(held,groups),
                 provisional=metrics(current,groups),v3OnlyProvisional=metrics(previous,old),
                 added=metrics(current-previous,groups),lost=metrics(previous-current,old),
                 recoveredByGate=dict(recovered),recoveredProvisionallyAccepted=sum(groups[k]['recoveredAppearances'] for k in current),
                 priorMappingRows=len(prior[0]),historicalApprovals=len(prior[1]),combinedMappingRows=len(mappings),
                 representationHeldNew=sum(m['materializationHeld'] for m in mappings[len(prior[0]):]),
                 heldGroupsByReason=dict(Counter(reason for k in held for reason in groups[k]['reasons'])))
    w.require(summary['admissibleAppearances']==4039 and summary['eligibleAppearances']==1408,'POPULATION_DRIFT')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        folder=Path(temp)/'package';folder.mkdir()
        emit=replay.v3.coverage.write_rows
        emit(folder/'groups.jsonl',groups.values())
        emit(folder/'occurrence-mappings.jsonl',mappings)
        emit(folder/'historical-approvals.jsonl',prior[1])
        emit(folder/'comparison.jsonl',(dict(occurrenceIDs=k,v3Provisional=k in previous,v4Provisional=k in current)
                                        for k in sorted(current|previous)))
        w.live.save(folder/'summary.json',summary)
        w.live.save(folder/'manifest.json',dict(inputHashes=pins,outputHashes={p.name:w.r.identity.sha(p) for p in folder.iterdir()}))
        folder.rename(output)
    return summary


def main():
    """Run from the repository root with the saved v4 and decision-stage packages."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['run','verify'])
    p.add_argument('--output',type=Path,default=ROOT)
    args=p.parse_args()
    result=(run if args.mode=='run' else replay.verify)(args.output)
    print(w.json.dumps(result,indent=2))


if __name__=='__main__':main()
