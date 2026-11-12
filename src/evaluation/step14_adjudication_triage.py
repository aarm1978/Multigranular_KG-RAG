"""Consume saved Step 14 recommendations and discovery inventories offline."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import socket
import sqlite3
from unittest.mock import patch

from src.evaluation import step14_next_review_queue as queue
from src.evaluation import step14_referent_groups as referents
from src.evaluation import step14_two_view_retrieval as retrieval

r = referents.r
require = queue.require
BASE = Path('var/study2_step14')
ROOT = BASE / 'adjudication-triage'
CONSOLIDATED = BASE / 'live-recovery/v1/consolidated-v1'
VERSION = 'step14-adjudication-triage/0.1.0'
NONDECISION = 'unresolved_triage_only_no_identity_decision'


def reference(path: Path, line: int, row: dict) -> dict:
    """Point to a saved record without duplicating its evidence."""
    return dict(file=str(path), line=line, recordSha256=r.candidates.token(row))


def indexed(path: Path, key: str) -> tuple[dict, dict]:
    """Read an existing sidecar and reject duplicate identities."""
    records, refs = {}, {}
    for line, row in enumerate(r.rows(path), 1):
        value = row[key]
        require(value not in records, f'DUPLICATE_{key}')
        records[value] = row
        refs[value] = reference(path, line, row)
    return records, refs


def exact_approvals(ids: list[str], decisions: list[dict]) -> list[dict]:
    """Expose intersections and complete subsets, never their transitive union."""
    result = []
    members = set(ids)
    for decision in decisions:
        original = set(decision['occurrenceIDs'])
        if original & members:
            result.append(dict(decisionID=decision['decisionID'],
                exactApprovedOccurrenceIDs=decision['occurrenceIDs'],
                intersection=sorted(original & members), entireSubsetPresent=original <= members,
                entireCandidateWithinSubset=members <= original))
    return result


def pair_triage(pair: dict, endpoints: dict, assessment: dict | None,
                decisions: list[dict]) -> dict:
    """Describe explicit comparisons without converting model claims to judgments."""
    ids = pair['occurrenceIDs']
    require(ids == sorted(set(ids)) and len(ids) == 2, 'PAIR_MEMBERSHIP_DRIFT')
    require(pair['pairKeySha256'] == r.candidates.token(ids), 'PAIR_HASH_DRIFT')
    left, right = (endpoints[x] for x in ids)
    scope = retrieval.pair_scope(left, right)
    require(scope is not None, 'PAIR_CLASS_DRIFT')
    approvals = exact_approvals(ids, decisions)
    flags = retrieval.pair_flags(left, right)
    if left['granularity'] != right['granularity']:
        flags.append('recorded_granularity_differs')
    if any('unspecified' in x['granularity'] for x in (left, right)):
        flags.append('granularity_unspecified')
    if assessment:
        if assessment.get('conflictEvidenceIDs'):
            flags.append('model_reports_conflicting_evidence')
        if assessment.get('missingInformation'):
            flags.append('model_reports_missing_information')
        if (assessment['recommendation'] == 'same_entity_candidate'
                and assessment['identityLevel'] != 'entity'):
            flags.append('category_identity_level_tension_requires_review')
        if (any(a['entireCandidateWithinSubset'] for a in approvals)
                and assessment['recommendation'] != 'same_entity_candidate'):
            flags.append('recommendation_approval_tension_requires_review')
    return dict(pairKeySha256=pair['pairKeySha256'], occurrenceIDs=ids,
        ontologyClass=left['ontologyClass'], familyCombination=sorted(set(left['sourceFamilies']+right['sourceFamilies'])),
        identityScope=scope, nominationOrigin=pair['origin'],
        category=assessment['recommendation'] if assessment else 'unassessed',
        modelIdentityLevel=assessment['identityLevel'] if assessment else None,
        risks=sorted(set(flags)), exactApprovalSubsets=approvals, status=NONDECISION)


def reconcile_blocks(blocks: list[dict], pairs: list[dict]) -> tuple[list[dict], set[str]]:
    """Intersect only existing explicit pairs with blocks; never enumerate block pairs."""
    membership = defaultdict(set)
    rows = {}
    for block in blocks:
        bid = block['blockID']
        require(bid not in rows, 'DUPLICATE_BLOCK')
        ids = block['occurrenceIDs']
        oversized = block.get('status') == 'oversized_not_expanded'
        if not oversized:
            require(len(ids) == len(set(ids)) == block['memberCount'], 'BLOCK_MEMBERSHIP_DRIFT')
            require(r.candidates.token(sorted(ids)) == block['membershipSha256'], 'BLOCK_HASH_DRIFT')
            for oid in ids:
                membership[oid].add(bid)
        rows[bid] = dict(originalBlock=block, selectedPairKeys=[], selectedPairStates={},
            overlapStatus='unknown_not_expanded' if oversized else 'exact_explicit_pair_intersection',
            status=NONDECISION)
    represented = set()
    counts = defaultdict(Counter)
    for pair in pairs:
        a, b = pair['occurrenceIDs']
        for bid in sorted(membership[a] & membership[b]):
            rows[bid]['selectedPairKeys'].append(pair['pairKeySha256'])
            counts[bid][pair['coverageState']] += 1
            represented.add(pair['pairKeySha256'])
    for bid, row in rows.items():
        row['selectedPairKeys'].sort()
        row['selectedPairStates'] = dict(sorted(counts[bid].items()))
    return [rows[k] for k in sorted(rows)], represented


def prioritize(groups: list[dict], limit: int = 30, members: int = 160) -> list[dict]:
    """Bound complete review scopes; critical gaps precede ordinary work, no unions."""
    ordered = sorted(groups, key=lambda g: (g['priority'], len(g['occurrenceIDs']), g['groupID']))
    selected, used = [], 0
    for group in ordered:
        size = len(group['occurrenceIDs'])
        if group.get('needsReview', True) and size <= 8 and used + size <= members and len(selected) < limit:
            selected.append(group); used += size
    return selected


def run(output: Path) -> dict:
    """Read pinned saved artifacts once; publish only to a fresh ignored destination."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(), 'FRESH_OUTPUT_REQUIRED')
    pins = {}

    def pin(path: Path, expected: str | None = None) -> None:
        """Check shared pins for contradictions and verify saved bytes."""
        digest = expected or r.identity.sha(path)
        require(str(path) not in pins or pins[str(path)] == digest, 'CONTRADICTORY_INPUT_PIN')
        queue.pilot.verify(path, digest, pins)

    def package(name: str, files: list[str]) -> dict:
        """Use consumed output pins and preserve upstream authority chains as references."""
        root = BASE / name / 'v1'; path = root / 'manifest.json'
        pin(path); manifest = r.load(path)
        for name in files:
            pin(root / name, manifest['outputHashes'][name])
        # Check authority/manifest links, not raw corpus or graph payloads.
        for name, digest in manifest.get('inputHashes', {}).items():
            if name.startswith('docs/') or name.endswith('/manifest.json'):
                pin(Path(name), digest)
        return manifest

    package('unified-review-queue', ['coverage.sqlite', 'unit-bindings.jsonl', 'endpoint-provenance.jsonl', 'prior-decisions.jsonl'])
    package('referent-groups', ['groups.jsonl', 'members.jsonl', 'prior-decisions.jsonl'])
    next_manifest = package('next-review-queue', ['block-inventory.jsonl', 'oversized-inventory.jsonl'])
    package('semantic-candidates', ['candidate-blocks.jsonl'])
    for path in (queue.approvals.DOCUMENT, queue.approvals.APPROVALS,
                 Path('docs/study2_step14_scope_and_completion_decision_v0.1.md'),
                 Path('docs/study2_step14_identity_granularity_adjudication_v0.1.md'),
                 Path('docs/study2_step14_next_review_queue.md'), Path('docs/codex/CODEX_HANDOFF.md'),
                 Path('docs/study2_step14_adjudication_triage.md'), Path(__file__).relative_to(Path.cwd())):
        pin(path)
    decisions = list(r.rows(queue.approvals.APPROVALS))
    queue.approvals.validate_approvals(r.load(queue.approvals.DOCUMENT), decisions)
    for name in ('referent-groups', 'unified-review-queue'):
        require(list(r.rows(BASE/name/'v1/prior-decisions.jsonl')) == decisions, 'SAVED_APPROVAL_DRIFT')
    pin(CONSOLIDATED/'summary.json'); summary_input = r.load(CONSOLIDATED/'summary.json')
    pin(CONSOLIDATED/'recommendations.jsonl', summary_input['datasetSha256'])
    endpoints, endpoint_refs = indexed(BASE/'unified-review-queue/v1/endpoint-provenance.jsonl', 'occurrenceID')
    bindings, binding_refs = indexed(BASE/'unified-review-queue/v1/unit-bindings.jsonl', 'unitID')
    members, member_refs = indexed(BASE/'referent-groups/v1/members.jsonl', 'occurrenceID')
    saved_groups, group_refs = indexed(BASE/'referent-groups/v1/groups.jsonl', 'proposalID')
    ordinary, _ = indexed(BASE/'next-review-queue/v1/block-inventory.jsonl', 'blockID')
    oversized = list(r.rows(BASE/'next-review-queue/v1/oversized-inventory.jsonl'))
    for binding in bindings.values():
        for entity in binding['entities'].values():
            oid = entity['occurrenceID']
            require(r.candidates.token(endpoints[oid]) == entity['endpointRecordSha256'], 'ENDPOINT_BINDING_DRIFT')
    assessed, unit_ids, generation_origins = {}, set(), Counter()
    for line, row in enumerate(r.rows(CONSOLIDATED/'recommendations.jsonl'), 1):
        uid = row['binding']['unitID']
        require(uid not in unit_ids and row['binding'] == bindings[uid], 'RECOMMENDATION_BINDING_DRIFT')
        require(row['requestID'] == 'step14:'+uid and row['recommendations']['caseID'] == uid, 'UNIT_ID_DRIFT')
        require(row['identityApproved'] is False, 'UNEXPECTED_IDENTITY_APPROVAL')
        unit_ids.add(uid); generation_origins[row['provenance']['origin']] += 1
        seen = set()
        for assessment in row['recommendations']['assessments']:
            pid = assessment['pairID']; key = bindings[uid]['pairs'][pid]
            require(pid not in seen and key not in assessed, 'DUPLICATE_ASSESSMENT')
            seen.add(pid)
            assessed[key] = (assessment, reference(CONSOLIDATED/'recommendations.jsonl', line, row), uid)
        require(seen == set(bindings[uid]['pairs']), 'INCOMPLETE_VALIDATED_UNIT')
    require(len(assessed) == summary_input['uniqueAssessedPairs'] and len(unit_ids) == summary_input['validatedUnits'], 'SUMMARY_COUNT_DRIFT')
    require(dict(generation_origins) == summary_input['origins'], 'GENERATION_ORIGIN_DRIFT')
    invalid = {}
    for item in summary_input['remaining']:
        uid = item['requestID'].removeprefix('step14:')
        require(uid not in unit_ids and len(bindings[uid]['pairs']) == item['pairs'], 'INVALID_UNIT_DRIFT')
        for key in bindings[uid]['pairs'].values():
            require(key not in invalid, 'DUPLICATE_INVALID_PAIR')
            invalid[key] = uid
    require(set(bindings) == unit_ids | set(invalid.values()), 'UNACCOUNTED_UNIT')
    pairs, joint, dimensions = [], Counter(), defaultdict(Counter)
    dbpath = BASE/'unified-review-queue/v1/coverage.sqlite'
    with sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        for key, detail, disposition, origin, uid in db.execute('SELECT pairkey,detail,disposition,origin,unit FROM candidates ORDER BY pairkey'):
            original = json.loads(detail)
            require(key == original['pairKeySha256'] and origin == original['origin'], 'COVERAGE_KEY_DRIFT')
            assessment, ref, assessed_uid = assessed.get(key, (None, None, None))
            if disposition == 'queued':
                require(key in bindings[uid]['pairs'].values(), 'COVERAGE_BINDING_DRIFT')
                require(set(original['occurrenceIDs']) <= {e['occurrenceID'] for e in bindings[uid]['entities'].values()}, 'PAIR_ENDPOINT_BINDING_DRIFT')
                require((assessment is not None and assessed_uid == uid) or invalid.get(key) == uid, 'UNACCOUNTED_QUEUED_PAIR')
                state = 'validated_recommendation' if assessment else 'invalid_unresolved'
            else:
                require(disposition in ('prior_completed_pair_assessment', 'prior_group_assessment_overlap')
                        and key not in assessed and key not in invalid and uid is None, 'PRIOR_DISPOSITION_DRIFT')
                state = disposition
            row = pair_triage(original, endpoints, assessment, decisions)
            row.update(coverageState=state, originalCandidate=original, unitID=uid,
                recommendationReference=ref, assessment=assessment,
                bindingReference=binding_refs.get(uid), endpointReferences=[endpoint_refs[x] for x in row['occurrenceIDs']])
            pairs.append(row)
            if assessment:
                values = (row['category'], row['ontologyClass'], tuple(row['familyCombination']), row['identityScope'], origin, row['modelIdentityLevel'])
                joint[values] += 1
                for field in ('category', 'ontologyClass', 'familyCombination', 'identityScope', 'nominationOrigin', 'modelIdentityLevel'):
                    value = row[field]; dimensions[field][json.dumps(value, sort_keys=True)] += 1
    require({p['pairKeySha256'] for p in pairs if p['assessment']} == set(assessed), 'ORPHAN_ASSESSMENT')
    require({p['pairKeySha256'] for p in pairs if p['coverageState']=='invalid_unresolved'} == set(invalid), 'ORPHAN_INVALID_PAIR')
    blocks = list(r.rows(BASE/'semantic-candidates/v1/candidate-blocks.jsonl'))
    coverage, represented = reconcile_blocks(blocks, pairs)
    pair_index = {p['pairKeySha256']: p for p in pairs}
    groups = []
    for row in coverage:
        block = row['originalBlock']; bid = block['blockID']; ids = block['occurrenceIDs']
        row['priorCrossFamilyReview'] = ordinary.get(bid)
        row['savedReferentReference'] = group_refs.get(bid)
        row['exactApprovalSubsets'] = exact_approvals(ids, decisions)
        row['approvedWholeScope'] = any(a['entireCandidateWithinSubset'] for a in row['exactApprovalSubsets'])
        row['unresolvedScope'] = not row['approvedWholeScope']
        row['selectedPoolOccurrenceIDs'] = sorted(set(ids) & endpoints.keys())
        if block.get('status') == 'oversized_not_expanded':
            continue
        if bid in ordinary:
            require(ids == ordinary[bid]['occurrenceIDs'] and block['membershipSha256'] == ordinary[bid]['membershipSha256'], 'NEXT_QUEUE_MEMBERSHIP_DRIFT')
        if bid in saved_groups:
            require(ids == saved_groups[bid]['occurrenceIDs'], 'REFERENT_MEMBERSHIP_DRIFT')
        relevant = [pair_index[k] for k in row['selectedPairKeys']]
        scopes = {oid: queue.scope_for_key({'identifierDeclarations': {'value': members[oid]['identifierDeclarations']}}, block['key']) for oid in ids} if block['key'][0] == queue.ID else {}
        categories = sorted({p['category'] for p in relevant if p['assessment']})
        risks = sorted({risk for p in relevant for risk in p['risks']} | set(saved_groups.get(bid, {}).get('conflicts', [])))
        if len(categories) > 1:
            risks.append('mixed_pair_categories_not_logical_contradiction')
        critical = any(p['coverageState'] == 'invalid_unresolved' for p in relevant)
        groups.append(dict(groupID=bid, occurrenceIDs=ids, originalKey=block['key'],
            priority=0 if critical else (1 if any('tension' in x or 'conflict' in x or 'differs' in x for x in risks) else 2),
            risks=risks, identifierScopeByOccurrence=scopes, priorCrossFamilyReview=ordinary.get(bid),
            exactApprovalSubsets=row['exactApprovalSubsets'], selectedPairKeys=row['selectedPairKeys'],
            memberReferences=[member_refs[x] for x in ids],
            priorMembershipsByOccurrence={x: members[x]['priorMemberships'] for x in ids},
            status=NONDECISION, basis='original_direct_key_no_union',
            needsReview=critical or (not row['approvedWholeScope'] and
                not ordinary.get(bid, {}).get('directReviewedCaseIDs')),
            evidencePointersByOccurrence={x:dict(originalReference=members[x]['originalReference'],
                evidencePointers=members[x]['evidencePointers']) for x in ids}))
    # Pairs without an ordinary direct container remain explicit comparisons, not dropped.
    for pair in pairs:
        if pair['pairKeySha256'] not in represented:
            groups.append(dict(groupID='pair:'+pair['pairKeySha256'], occurrenceIDs=pair['occurrenceIDs'],
                priority=0 if pair['coverageState']=='invalid_unresolved' else 3,
                risks=pair['risks'], selectedPairKeys=[pair['pairKeySha256']],
                exactApprovalSubsets=pair['exactApprovalSubsets'], memberReferences=pair['endpointReferences'],
                priorMembershipsByOccurrence={x:endpoints[x].get('priorMemberships', {}) for x in pair['occurrenceIDs']},
                previousAssessments=pair['originalCandidate'].get('previousAssessments', []),
                identifierScopeByOccurrence={}, status=NONDECISION, basis='existing_explicit_pair_no_direct_key'))
    selected = prioritize(groups)
    incident = defaultdict(Counter)
    for pair in pairs:
        for oid in pair['occurrenceIDs']:
            incident[oid][pair['coverageState']] += 1
    invalid_rows = [dict(p, criticality='blocks_this_exact_comparison_only; inspect associated group risks before any later approval; does not reopen recommendation generation',
        endpointIncidentCoverage={oid:dict(sorted(incident[oid].items())) for oid in p['occurrenceIDs']},
        criticalityReasons=sorted(set(p['risks']) | {'unassessed_pair_requires_explicit_unresolved_disposition'}),
        affectedGroupIDs=[g['groupID'] for g in groups if p['pairKeySha256'] in g['selectedPairKeys']])
        for p in pairs if p['coverageState']=='invalid_unresolved']
    require(set(ordinary) <= {b['blockID'] for b in blocks}, 'MISSING_ORDINARY_BLOCK')
    require({b['blockID'] for b in oversized} <= {b['blockID'] for b in blocks if b.get('status') == 'oversized_not_expanded'}, 'MISSING_OVERSIZED_BLOCK')
    route_coverage = []
    for mechanism in sorted({b['key'][0] for b in blocks}):
        selected_rows = [x for x in coverage if x['originalBlock']['key'][0] == mechanism]
        route_pairs = {k for x in selected_rows for k in x['selectedPairKeys']}
        route_coverage.append(dict(route=mechanism, blocks=len(selected_rows),
            oversizedBlocks=sum(x['overlapStatus']=='unknown_not_expanded' for x in selected_rows),
            ordinaryDistinctOccurrences=len({o for x in selected_rows for o in x['originalBlock']['occurrenceIDs']}),
            uniqueSelectedPairOverlap=len(route_pairs),
            selectedPairStates=dict(Counter(pair_index[k]['coverageState'] for k in sorted(route_pairs))),
            exactApprovedWholeScopes=sum(x['approvedWholeScope'] for x in selected_rows),
            unresolvedScopes=sum(x['unresolvedScope'] for x in selected_rows),
            directPilotReviewedBlocks=sum(bool((x['priorCrossFamilyReview'] or {}).get('directReviewedCaseIDs')) for x in selected_rows),
            approvalOverlapBlocks=sum(bool(x['exactApprovalSubsets']) for x in selected_rows)))
    summary = dict(version=VERSION, discoveryRouteCoverage=route_coverage, selectedPoolPairs=len(pairs), validatedRecommendationPairs=len(assessed),
        validatedUnits=len(unit_ids), generationOrigins=dict(generation_origins),
        pairCoverageStates=dict(Counter(p['coverageState'] for p in pairs)),
        pairRiskCounts=dict(sorted(Counter(risk for p in pairs for risk in p['risks']).items())),
        recommendationDistributions={k:dict(sorted(v.items())) for k,v in dimensions.items()},
        jointRecommendationDistribution=[dict(category=k[0], ontologyClass=k[1], familyCombination=list(k[2]), identityScope=k[3], nominationOrigin=k[4], modelIdentityLevel=k[5], count=v) for k,v in sorted(joint.items())],
        preservedNextQueueCoverage=next_manifest['summary'], oversizedCrossFamilyBlocks=len(oversized),
        existingBlockCounts=dict(Counter(b['key'][0] for b in blocks)),
        selectedPairsInOrdinaryBlocks=len(represented), selectedPairsOutsideOrdinaryBlocks=len(pairs)-len(represented),
        blockPairMemberships=sum(len(x['selectedPairKeys']) for x in coverage),
        proposedReviewGroups=len(selected), proposedMemberOccurrences=sum(len(g['occurrenceIDs']) for g in selected),
        proposedDistinctOccurrences=len({o for g in selected for o in g['occurrenceIDs']}),
        totalReviewContainers=len(groups), unselectedReviewContainers=len(groups)-len(selected),
        proposedMinutesRange=[len(selected)*5, len(selected)*15],
        workloadBasis='Planning assumption 5–15 minutes per complete bounded group, not measured; evidence recovery may add time.',
        providerCalls=0, identityDecisions=0, graphWrites=0)
    for path, digest in pins.items():
        queue.pilot.verify(Path(path), digest, {})
    output.mkdir(parents=True)
    for name, records in [('pair-inventory.jsonl', pairs), ('block-coverage.jsonl', coverage),
                          ('oversized-inventory.jsonl', oversized), ('review-groups.jsonl', sorted(groups, key=lambda g:(g['priority'],g['groupID']))),
                          ('proposed-review.jsonl', selected), ('invalid-pairs.jsonl', invalid_rows),
                          ('prior-decisions.jsonl', decisions)]:
        with (output/name).open('x') as stream:
            for record in records:
                stream.write(r.identity.encoded(record).decode()+'\n')
    r.write(output/'summary.json', summary)
    (output/'report.md').write_text(report(summary))
    r.write(output/'manifest.json', dict(version=VERSION, inputHashes=pins,
        implementationHashes={str(Path(m.__file__).relative_to(Path.cwd())):r.identity.sha(Path(m.__file__)) for m in (queue, referents, retrieval, queue.approvals)},
        outputHashes={p.name:r.identity.sha(p) for p in sorted(output.iterdir())},
        providerCalls=0, identityDecisions=0, graphWrites=0))
    return summary


def report(summary: dict) -> str:
    """State bounded workload and a proposed stopping rule, never acceptance policy."""
    return ('# Step 14 offline adjudication triage\n\n'
        f"Selected semantic/alias pool: {summary['selectedPoolPairs']} exact pairs; "
        f"{summary['validatedRecommendationPairs']} validated recommendations. "
        'This is not the full Step 14 candidate universe. Identifier lanes remain separate.\n\n'
        f"Proposed one bounded review set: {summary['proposedReviewGroups']} groups, "
        f"{summary['proposedMemberOccurrences']} member occurrences / {summary['proposedDistinctOccurrences']} distinct occurrences. "
        f"Planning time: {summary['proposedMinutesRange'][0]}–{summary['proposedMinutesRange'][1]} minutes (5–15 per group, unmeasured). "
        'At most 30 complete groups, 8 members each, 160 memberships total. Invalid comparisons first, then recorded risks, then ordinary keys and uncovered explicit pairs. '
        'Shared members and repeated evidence are not independent corroboration.\n\n'
        'Proposed stopping rule, subject to researcher acceptance: inspect the invalid comparisons and the bounded review set once; '
        'record exact decisions or explicit unresolved dispositions with evidence limitations. Stop without repeated batches, universal identity resolution, or an accuracy campaign. '
        'Carry remaining groups, identifier lanes and oversized blocks as unresolved; retain the ontology decision gate before separately authorized canonicalization.\n\n'
        'pair-inventory.jsonl contains exact unique selected comparisons, authentic assessment text, risks and evidence bindings. '
        'block-coverage.jsonl preserves every saved block and intersects only existing comparisons; its memberships must not be summed as unique pairs. '
        'Fully approved scopes and directly reviewed blocks are retained but excluded from ordinary shortlist selection unless an invalid comparison requires attention. Direct pilot review, full/partial occurrence overlap and exact approval subsets remain independent fields. '
        'Oversized overlap is unknown and no Cartesian pairs are generated. No selected-pool assessment implies resolution of an entire block.\n\n'
        'Different recommendations on different pairs are not logical contradictions. Structured version differences, unknown specificity, model-reported conflicts and category/identity-level tensions are review flags, not new semantic judgments. '
        'The invalid-pairs inventory records exact endpoints, affected containers and local criticality: these comparisons remain unassessed, not rejected; their failure does not invalidate unrelated validated recommendations. '
        'No transitive bridge or combined identity set is constructed.\n')


def main() -> None:
    """Execute locally with socket connections disabled and no provider imports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'v1')
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('OFFLINE_ONLY')), \
         patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('OFFLINE_ONLY')):
        print(json.dumps(run(args.output), sort_keys=True))


if __name__ == '__main__':
    main()
