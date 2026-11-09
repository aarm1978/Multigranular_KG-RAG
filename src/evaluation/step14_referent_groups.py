"""Offline direct-key grouping proposals; no identity decisions or transitive closure."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import socket
from unittest.mock import patch

from src.evaluation import step14_evidence_review_batch as batch

r = batch.retrieval
require = r.require
VERSION = 'step14-referent-groups/0.1.0'
ROOT = Path('var/study2_step14/referent-groups')
INVENTORY = Path('var/study2_step14/semantic-candidates/v1')
CONTRACT = Path('docs/study2_step14_referent_groups_v0.1.md')


def member(row: dict, line: int) -> dict:
    """Retain exact references and literal metadata without copying full source documents."""
    fields = ('occurrenceID', 'ontologyClass', 'inventoryId', 'lane', 'labels', 'versions',
              'granularity', 'sourceFamilies', 'sourceArtifacts', 'identifierDeclarations',
              'declaredExistingNodeIDs', 'preparationFlags', 'nativeReferences')
    result = {k: row[k] for k in fields}
    result['originalReference'] = dict(file=str(INVENTORY/'occurrences.jsonl'), line=line,
                                      recordSha256=r.candidates.token(row))
    result['evidencePointers'] = [dict(jsonPointer=f'/evidenceReferences/{i}',
        recordSha256=r.candidates.token(e)) for i, e in enumerate(row['evidenceReferences'])]
    result['deterministicIdentityLane'] = any(d.get('basis') in
        ('deterministic_entity_own_field', 'C-D04') for d in row['identifierDeclarations'])
    return result


def propose(block: dict, records: dict) -> dict | None:
    """Keep one direct original key; never combine overlapping blocks or infer identity."""
    ids = block['occurrenceIDs']; key = block['key']
    require(len(ids) == len(set(ids)) == block['memberCount'], 'BLOCK_MEMBERSHIP_DRIFT')
    require(r.candidates.token(ids) == block['membershipSha256'], 'MEMBERSHIP_HASH_DRIFT')
    require(all(x in records for x in ids), 'UNKNOWN_MEMBER')
    members = [records[x] for x in ids]
    require(all(x['ontologyClass'] == key[1] for x in members), 'CLASS_DRIFT')
    if key[0] == 'lexical_similarity_only':
        # Reuse the existing non-generic name cue solely as a review-screening aid.
        # This is NOT a determination that the literal name is a unique referent.
        if not batch.name_tokens(dict(labels=[key[2]])):
            return None
        basis = 'literal_named_referent_candidate'
    else:
        require(key[0] == 'identifier_declaration_only', 'UNKNOWN_BLOCK_KIND')
        basis = 'explicit_identifier_declaration'
    conflicts = list(block.get('flags', []))
    if len({r.candidates.token(x['versions']) for x in members}) > 1:
        conflicts.append('recorded_version_metadata_differs_no_bridge_authorized')
    if len({x['granularity'] for x in members}) > 1:
        conflicts.append('recorded_granularity_differs_no_bridge_authorized')
    if len({x['inventoryId'] for x in members}) > 1:
        conflicts.append('inventory_identity_conflict')
    conflicts.append('referent_and_granularity_require_review')
    return dict(proposalID=block['blockID'], originalBlock=block, basis=basis,
        occurrenceIDs=ids, sourceFamilies=sorted({f for x in members for f in x['sourceFamilies']}),
        conflicts=sorted(set(conflicts)), status='unresolved_proposal',
        identityDecision=None, canonicalID=None, automaticMergeEligible=False,
        retrievalPairCount=0, retrievalByScope={}, exactApprovalSubsets=[])


def attach_approvals(groups: list, approvals: list) -> None:
    """Retain explicit subset boundaries; overlap never extends an approval."""
    for group in groups:
        members = set(group['occurrenceIDs'])
        for decision in approvals:
            approved = set(decision['occurrenceIDs'])
            overlap = sorted(members & approved)
            if overlap:
                group['exactApprovalSubsets'].append(dict(decisionID=decision['decisionID'],
                    originalOccurrenceIDs=decision['occurrenceIDs'], overlap=overlap,
                    fullOriginalSubsetPresent=approved <= members,
                    originalRecordSha256=r.candidates.token(decision)))


def summarize(groups: list, records: dict, pair_counts: dict) -> dict:
    """Count set coverage, not inferred entities or population accuracy."""
    covered = {x for g in groups for x in g['occurrenceIDs']}
    approved = {x for g in groups for a in g['exactApprovalSubsets'] for x in a['overlap']}
    return dict(version=VERSION, groups=len(groups), occurrenceCoverage=len(covered),
        inventoryOccurrences=len(records), ungroupedOccurrences=len(set(records)-covered),
        groupsByBasis=dict(Counter(g['basis'] for g in groups)),
        coveredByFamily=dict(Counter(f for x in covered for f in records[x]['sourceFamilies'])),
        inventoryByFamily=dict(Counter(f for x in records.values() for f in x['sourceFamilies'])),
        coveredByLane=dict(Counter(records[x]['lane'] for x in covered)),
        crossFamilyOccurrenceCoverage=len({x for g in groups if len(g['sourceFamilies']) > 1 for x in g['occurrenceIDs']}),
        deterministicIdentityOccurrences=sum(records[x]['deterministicIdentityLane'] for x in covered),
        crossFamilyGroups=sum(len(g['sourceFamilies']) > 1 for g in groups),
        previouslyApprovedOccurrenceMemberships=len(approved),
        ambiguousGroups=len(groups), retrievalAccounting=pair_counts,
        identityDecisions=0, canonicalIDsAllocated=0, providerCalls=0)


def run(output: Path) -> dict:
    """Verify existing artifacts and prepare one bounded review set without retrieval reruns."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(), 'FRESH_OUTPUT_REQUIRED')
    manifest = r.load(batch.SOURCE/'manifest.json'); pins = dict(manifest['inputHashes'])
    for name, h in manifest['outputHashes'].items(): pins[str(batch.SOURCE/name)] = h
    require(manifest['implementationSha256'] == r.identity.sha(Path(batch.reconciliation.__file__)), 'IMPLEMENTATION_DRIFT')
    inventory = r.load(INVENTORY/'manifest.json')
    for name, h in inventory['outputHashes'].items(): pins[str(INVENTORY/name)] = h
    for path in (INVENTORY/'manifest.json', batch.SOURCE/'manifest.json', CONTRACT, Path(__file__)):
        pins.setdefault(str(path), r.identity.sha(path))
    for path, h in pins.items(): r.preflight.pilot.verify(Path(path), h, {})
    approvals = list(r.rows(r.preflight.approvals.APPROVALS))
    r.preflight.approvals.validate_approvals(r.load(r.preflight.approvals.DOCUMENT), approvals)
    prior = {x['occurrenceID']: x for x in r.rows(r.PREFLIGHT.parent/'occurrence-preflight.jsonl')}
    records = {}
    for line, row in enumerate(r.rows(INVENTORY/'occurrences.jsonl'), 1):
        oid = row['occurrenceID']; require(oid not in records, 'DUPLICATE_OCCURRENCE')
        require(oid in prior and prior[oid]['textReference']['recordSha256'] == r.candidates.token(row), 'ORIGINAL_BINDING_DRIFT')
        records[oid] = member(row, line)
        records[oid]['priorMemberships'] = {k: prior[oid][k] for k in
            ('reviewedCaseIDs', 'priorApprovalDecisionIDs', 'reservedQueueBlockIDs', 'existingBlockIDs')}
    groups = []; omitted = []
    for block in r.rows(INVENTORY/'candidate-blocks.jsonl'):
        group = propose(block, records)
        if group is None: omitted.append(block['blockID'])
        else: groups.append(group)
    attach_approvals(groups, approvals)
    index = defaultdict(set)
    for i, g in enumerate(groups):
        for oid in g['occurrenceIDs']: index[oid].add(i)
    # Linear scan of existing pairs; never enumerate the Cartesian product of a group.
    counts = Counter(); samples = defaultdict(list)
    for line, pair in enumerate(r.rows(batch.SOURCE/'pairs.jsonl'), 1):
        ids = pair['occurrenceIDs']
        require(len(ids) == 2 and ids == sorted(set(ids)) and all(x in records for x in ids), 'PAIR_ID_DRIFT')
        require(pair['pairKeySha256'] == r.candidates.token(ids), 'PAIR_HASH_DRIFT')
        common = index[ids[0]] & index[ids[1]]
        counts['pairs'] += 1; counts['directKeyRepresentedPairs' if common else 'unrepresentedPairsRetained'] += 1
        for i in sorted(common):
            g = groups[i]; g['retrievalPairCount'] += 1
            g['retrievalByScope'][pair['scope']] = g['retrievalByScope'].get(pair['scope'], 0)+1
            if len(samples[i]) < 3:
                samples[i].append(dict(file=str(batch.SOURCE/'pairs.jsonl'), line=line,
                    recordSha256=r.candidates.token(pair), occurrenceIDs=ids,
                    directions=pair['directions'], review=pair['review']))
    expected = r.load(batch.SOURCE/'summary.json')
    require(counts['pairs'] == expected['uniqueUnorderedPairs'], 'PAIR_COUNT_DRIFT')
    summary = summarize(groups, records, dict(counts))
    summary['genericNameBlocksNotSelected'] = len(omitted)
    summary['excludedSnapshotClasses'] = inventory['coverage']['excludedByClass']
    # Single bounded set: round-robin family/basis strata, then small actionable groups.
    pools = defaultdict(list)
    for i, g in enumerate(groups):
        if len(g['occurrenceIDs']) <= 16:
            pools[(tuple(g['sourceFamilies']), g['basis'])].append(i)
    for pool in pools.values():
        pool.sort(key=lambda i: (-int(len(groups[i]['sourceFamilies'])>1),
            -int(groups[i]['retrievalPairCount']>0), len(groups[i]['occurrenceIDs']), groups[i]['proposalID']))
    chosen = []
    while len(chosen) < 12 and any(pools.values()):
        for key in sorted(pools):
            if pools[key] and len(chosen) < 12: chosen.append(pools[key].pop(0))
    review = [dict(group=groups[i], members=[records[x] for x in groups[i]['occurrenceIDs']],
        directRetrievalExamples=samples[i], question='Same referent at compatible class and granularity, distinct referents, or unresolved? Do not infer approval from this grouping.') for i in chosen]
    summary['boundedReviewGroups'] = len(review)
    for path, h in pins.items(): r.preflight.pilot.verify(Path(path), h, {})
    output.mkdir(parents=True)
    for name, values in [('groups.jsonl', groups), ('members.jsonl', list(records.values())), ('prior-decisions.jsonl', approvals)]:
        with (output/name).open('x') as stream:
            for value in values: stream.write(r.identity.encoded(value).decode()+'\n')
    r.write(output/'review.json', dict(version=VERSION, cases=review))
    r.write(output/'summary.json', summary)
    (output/'summary.md').write_text('# Canonical-referent grouping preparation\n\n'
        +json.dumps(summary, indent=2)+'\n\nProposals only. Groups overlap and are never unioned. '
        'All memberships remain unresolved except the exact separately preserved prior approvals. '
        'The single bounded review set is utility-selected, not a quality estimate. '
        'Unselected and unrepresented pairs remain in the pinned reconciliation, not rejected. '
        'Generic-name screening is incomplete; surviving names do not establish distinctive identity.\n')
    r.write(output/'manifest.json', dict(version=VERSION, inputHashes=pins,
        outputHashes={p.name:r.identity.sha(p) for p in sorted(output.iterdir())}, providerCalls=0))
    return summary


def main() -> None:
    """Run only with network connections blocked."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'v1')
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('OFFLINE_ONLY')), \
         patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('OFFLINE_ONLY')):
        print(json.dumps(run(args.output), sort_keys=True))


if __name__ == '__main__': main()
