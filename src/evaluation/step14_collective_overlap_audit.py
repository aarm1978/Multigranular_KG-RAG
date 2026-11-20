"""Read-only sensitivity audit of the v1 collective overlap gate."""
from collections import Counter, defaultdict

from src.evaluation import step14_collective_identity_reconciliation as r

w = r.w
COMP = 'competing_complete_membership'


def eligible_before_competition(group):
    """Use the original pre-overlap guards; later baseline tie decisions are downstream."""
    downstream = {'unresolved_equal_support', 'represented_by_complete_superset',
                  'held_stronger_competing_scope'}
    return not set(group['reasons']) - downstream - {COMP}


def audit():
    """Count per unique group, with separate appearance-weighted recovered cohorts."""
    def rows(folder, name):
        path = folder/name
        expected = w.live.load(folder/'manifest.json')['outputHashes'][name]
        w.require(w.r.identity.sha(path)==expected, 'INPUT_DRIFT:'+name)
        return w.r.rows(path)

    groups = {tuple(g['occurrenceIDs']):g for g in rows(r.ROOT,'groups.jsonl')}
    items = {r.ref(a):a for a in rows(r.replay.ROOT,'item-ledger.jsonl')}
    units = {u['unitID']:set(u['aliasBindings'].values()) for u in rows(r.replay.ROOT,'unit-summaries.jsonl')}
    lost = {tuple(g['occurrenceIDs']) for g in rows(r.ROOT,'comparison.jsonl')
            if g['v3Provisional'] and not g['v4Provisional']}
    protected = {m['occurrenceID'] for m in rows(r.PRIOR,'occurrence-mappings.jsonl')}
    protected.update(o for a in rows(r.PRIOR,'historical-approvals.jsonl') for o in a['occurrenceIDs'])
    prior = defaultdict(set)
    for a in rows(r.PRIOR,'overlap-alternatives.jsonl'):
        ids = tuple(sorted(a['occurrenceIDs']))
        if a['support'] and not protected.intersection(ids):
            for o in ids:
                prior[o].add(ids)
    prior_kinds = {}
    for a in rows(r.PRIOR,'pair-inventory.jsonl'):
        kinds=set()
        if a['category']=='different_entities_candidate':kinds.add('prior_negative_pair')
        if (a.get('assessment') or {}).get('conflictEvidenceIDs'):kinds.add('prior_pair_conflict_citation')
        prior_kinds['pair',a['pairKeySha256']]=kinds
    for a in rows(r.PRIOR,'assessment-inventory.jsonl'):
        v=a['value']
        kinds=set()
        if v['category'] in ('distinct','related_nonidentical'):kinds.add('prior_local_'+v['category'])
        if v['contradictoryEvidenceIDs']:kinds.add('prior_contextual_contradiction')
        prior_kinds['assessment',a['unitID'],a['index']]=kinds
    for a in rows(r.PRIOR,'typed-relation-proposals.jsonl'):
        prior_kinds['relation',a['proposalID']]={'prior_'+a['predicate']}
    counts=defaultdict(Counter)
    cohort=defaultdict(Counter)
    additions=set()
    for ids,g in groups.items():
        tags=set()
        rivals=[tuple(c['occurrenceIDs']) for c in g['competingCollectiveScopes']]
        admissible=[k for k in rivals if k in groups]
        eligible=[k for k in admissible if eligible_before_competition(groups[k])]
        if rivals:
            tags.add('any_overlap')
            kind=('eligible_peer' if eligible else 'admissible_but_independently_blocked_peer'
                  if admissible else 'only_review_required_peers')
            tags.add(kind)
            if not eligible and g['reasons']==[COMP]:
                tags.add('sole_block_ineligible_peer')
                tags.add('sole_block_'+kind)
                if not set().union(*(prior[o] for o in ids))-{ids}:
                    additions.add(ids)
                    tags.add('uncontested_addition')
                    tags.add('addition_'+kind)
                else:tags.add('earlier_complete_competitor')
        else:
            kind='no_overlap'
        for ref in g['priorOpposition']:
            tags.update(prior_kinds[tuple(ref)])
            tags.add('any_prior_opposition')
        for ref in g['opposingCollectiveItems']:
            a=items[tuple(ref)]
            if a['category']=='distinct':
                w.require(len(set(ids)&units[a['unitID']])>=2,'NONLOCAL_DISTINCT')
                tags.add('local_distinct')
                tags.add('local_distinct_'+a['status'])
                cited={c['binding']['occurrenceID'] for c in a['citations'] if c['binding']}
                if cited.intersection(set(ids)-set(a['occurrenceIDs'])):
                    tags.add('distinct_cites_other_group_member')
            elif a['category']=='strict_identity':
                tags.update(a['reasons'])
            else:tags.add('proposed_'+a['modelItem']['signatureID'])
        tags.update(reason for reason in g['reasons'] if 'granular' in reason or 'version' in reason)
        for key in ('all',g['identityScope']):
            counts[key].update(tags)
        if g['recoveredAppearances']:
            label='+'.join(g['collectiveGateReasons']) or 'permitted'
            cohort[label][kind]+=g['recoveredAppearances']
            cohort[label+'_scope'][g['identityScope']]+=g['recoveredAppearances']
        if ids in lost:
            cohort['displaced'][kind]+=1
            cohort['displaced_sensitivity']['added' if ids in additions else 'still_held']+=1
            cohort['displaced_flags']['+'.join(g['collectiveGateReasons'])]+=1
            cohort['displaced_scope'][g['identityScope']]+=1
    accepted={k for k,g in groups.items() if g['state']==r.d.ab.ACCEPTED}
    counterfactual=accepted|additions
    w.require(sum(map(len,counterfactual))==len({o for k in counterfactual for o in k}),'SENSITIVITY_OVERLAP')
    return dict(groupCounts=counts,recoveredAppearancesAndDisplacedGroups=cohort,
                added=r.metrics(additions,groups),sensitivity=r.metrics(counterfactual,groups))


if __name__=='__main__':
    print(w.json.dumps(audit(),indent=2,sort_keys=True))
