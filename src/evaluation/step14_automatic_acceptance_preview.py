"""Offline, provisional complete-group automatic identity acceptance feasibility."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import socket
from unittest.mock import patch

from src.evaluation import step14_adjudication_triage as triage

r = triage.r
require = triage.require
ROOT = triage.BASE / 'automatic-acceptance-preview'
POLICY = Path('docs/study2_step14_automatic_identity_acceptance_v0.1.md')
VERSION = 'step14-automatic-acceptance-preview/0.1.0'
OWN_NAMESPACES = {'Paper': {'doi'}, 'DatasetResource': {'doi', 'hydroshare'},
                  'Repository': {'github'}, 'Person': {'orcid'}, 'Organization': {'ror'}}
ACCEPTED = 'provisional_accepted'
HELD = 'held_undetermined'
NONIDENTITY = 'provisional_nonidentity_complete_group'


def group_scope(records: list[dict]) -> str:
    """Apply source-based scope to the complete set, not inferred scientific identity."""
    artifacts = set(records[0]['sourceArtifacts'])
    for record in records[1:]:
        artifacts.intersection_update(record['sourceArtifacts'])
    if artifacts:
        return 'within_artifact'
    if len({tuple(sorted(x['sourceFamilies'])) for x in records}) == 1:
        return 'within_family_between_artifacts'
    return 'between_families'


def combine_containers(groups: list[dict]) -> list[dict]:
    """Deduplicate exact complete memberships only; never connect or enlarge them."""
    combined = {}
    for group in groups:
        ids = tuple(sorted(group['occurrenceIDs']))
        require(len(ids) >= 2 and len(ids) == len(set(ids)), 'INVALID_COMPLETE_MEMBERSHIP')
        row = combined.setdefault(ids, dict(occurrenceIDs=list(ids), originalGroupIDs=[],
                                          originalKeys=[], selectedPairKeys=set()))
        row['originalGroupIDs'].append(group['groupID'])
        if group.get('originalKey') and group['originalKey'] not in row['originalKeys']:
            row['originalKeys'].append(group['originalKey'])
        row['selectedPairKeys'].update(group['selectedPairKeys'])
    result = []
    for ids, row in sorted(combined.items()):
        row['originalGroupIDs'].sort(); row['originalKeys'].sort()
        row['selectedPairKeys'] = sorted(row['selectedPairKeys'])
        row['simulationID'] = 'scope:' + r.candidates.token(list(ids))
        result.append(row)
    return result


def identifier_guard(keys: list[list], records: list[dict]) -> bool | None:
    """Verify exact own-role scheme/value declarations, not source URLs or local links."""
    candidates = [k for k in keys if k[0] == triage.queue.ID]
    if not candidates:
        return None
    for key in candidates:
        _, cls, scheme, value = key
        if scheme not in OWN_NAMESPACES.get(cls, set()):
            continue
        if all(record['ontologyClass'] == cls and any(
                d.get('scheme') == scheme and d.get('value') == value and
                (d.get('basis') == 'deterministic_entity_own_field' or
                 (d.get('basis') == 'C-D04' and cls == 'DatasetResource' and scheme == 'doi'))
                for d in record.get('identifierDeclarations', [])) for record in records):
            return True
    return False


def guarded_state(guards: dict[str, bool | None]) -> str:
    """Only every explicitly true guard permits a provisional simulation result."""
    return ACCEPTED if guards and all(value is True for value in guards.values()) else HELD


def simulate(group: dict, pairs: dict, members: dict, endpoints: dict,
             decisions: list[dict], bindings: dict) -> dict:
    """Evaluate saved evidence contracts without extracting new semantic judgments."""
    ids = group['occurrenceIDs']; records = [members[x] for x in ids]
    selected = [pairs[k] for k in group['selectedPairKeys']]
    require(all(set(p['occurrenceIDs']) <= set(ids) for p in selected), 'CONTAINER_PAIR_DRIFT')
    require(len({tuple(p['occurrenceIDs']) for p in selected}) == len(selected), 'DUPLICATE_EXPLICIT_PAIR')
    prior = triage.exact_approvals(ids, decisions)
    identical_approval = any(set(a['exactApprovedOccurrenceIDs']) == set(ids) for a in prior)
    versions = {r.candidates.token(x['versions']) for x in records}
    # Current producer supplies no certified granularity/referent/version relation.
    # Equal strings and fluent model prose must not substitute for that certificate.
    guards = dict(classCompatible=len({(x['ontologyClass'], x['inventoryId']) for x in records}) == 1,
        sourceEvidencePresent=all(x.get('evidencePointers') and x.get('originalReference') and
                                 x['sourceFamilies'] and x['sourceArtifacts'] for x in records),
        noPreparationExclusions=not any(set(x.get('preparationFlags', [])) &
            {'missing_provenance', 'ontology_class_inventory_mismatch', 'abstract_class_retained_not_retyped'} for x in records),
        referentCompatibility=None, granularityCompatibility=None,
        entityVersionCompatibility=False if len(versions) > 1 else None,
        pilotScopeCompatible=not prior or identical_approval)
    route_a = dict(guards, exactEntityOwnedIdentifier=identifier_guard(group['originalKeys'], records))
    positive = all(p['coverageState'] == 'validated_recommendation' and
                   p['category'] == 'same_entity_candidate' and p['modelIdentityLevel'] == 'entity'
                   for p in selected)
    evidence = all(endpoints.get(oid, {}).get('selectedEvidence') for oid in ids)
    bound_evidence = True
    for pair in selected:
        assessment = pair.get('assessment') or {}
        binding = bindings.get(pair.get('unitID'), {})
        refs = binding.get('evidence', {})
        cited = assessment.get('evidenceIDs', [])
        if (not cited or any(eid not in refs for eid in cited) or
                not set(pair['occurrenceIDs']) <= {refs[eid]['occurrenceID'] for eid in cited if eid in refs}):
            bound_evidence = False
    route_b = dict(guards,
        assessmentEvidenceBoundToBothEndpoints=bool(selected) and bound_evidence,
        completePositiveComparisons=bool(selected) and positive and len(selected) == len(ids)*(len(ids)-1)//2,
        noModelConflictOrMissingInformation=bool(selected) and all(p.get('assessment') is not None and
            not p['assessment'].get('conflictEvidenceIDs') and not p['assessment'].get('missingInformation') for p in selected),
        endpointSelectedEvidencePresent=evidence)
    routes = sorted({key[0] for key in group['originalKeys']} | {p['nominationOrigin'] for p in selected})
    states = {'A': guarded_state(route_a) if any(k[0]==triage.queue.ID for k in group['originalKeys']) else 'not_applicable',
              'B': guarded_state(route_b)}
    negative = any(p['coverageState']=='validated_recommendation' and
                   p['category']=='different_entities_candidate' for p in selected)
    if identical_approval:
        state = 'researcher_approved_exact_scope'
    elif prior:
        state = HELD
    elif negative:
        state = NONIDENTITY
    else:
        state = ACCEPTED if ACCEPTED in states.values() else HELD
    return dict(group, routes=routes, ontologyClass=sorted({x['ontologyClass'] for x in records}),
        familyCombination=sorted({f for x in records for f in x['sourceFamilies']}),
        identityScope=group_scope(records), memberCount=len(ids),
        state=state, alternativeStates=states, safeguards={'A':route_a, 'B':route_b},
        holdReasons=sorted({name for guards_for_route in (route_a, route_b)
                            for name, value in guards_for_route.items() if value is not True}),
        exactApprovalSubsets=prior, modelNegativePairPresent=negative,
        simulationOnly=True, identityDecisions=0)


def prevent_overlaps(groups: list[dict]) -> None:
    """Hold every overlapping eligible scope instead of choosing or unioning identities."""
    index = defaultdict(list)
    for row in groups:
        if row['state'] == ACCEPTED:
            for oid in row['occurrenceIDs']:
                index[oid].append(row)
    blocked = {g['simulationID'] for rows in index.values() if len(rows) > 1 for g in rows}
    for row in groups:
        if row['simulationID'] in blocked:
            row['state'] = HELD
            row['holdReasons'] = sorted(set(row['holdReasons']) | {'overlapping_eligible_complete_scopes_no_union'})


def distribution(rows: list[dict], unit: str) -> list[dict]:
    """Count distinct explicit units and known occurrences; route facets are nonadditive."""
    buckets = defaultdict(list)
    for row in rows:
        for dimension in ('routes', 'ontologyClass', 'familyCombination', 'identityScope'):
            values = row[dimension] if dimension == 'routes' else [row[dimension]]
            for value in values:
                buckets[(dimension, json.dumps(value, sort_keys=True), row['state'])].append(row)
    return [dict(dimension=key[0], value=json.loads(key[1]), state=key[2], unit=unit,
                 count=len(values), distinctKnownOccurrences=len({o for row in values for o in row['occurrenceIDs']}),
                 unknownMembershipUnits=sum(not row['occurrenceIDs'] for row in values))
            for key, values in sorted(buckets.items())]


def evaluate(groups: list[dict], pairs: dict, members: dict, endpoints: dict,
             decisions: list[dict], oversized: list[dict], bindings: dict) -> tuple[list, list, dict]:
    """Simulate complete saved scopes and reconcile explicit pairs, with no discovery."""
    rows = [simulate(g, pairs, members, endpoints, decisions, bindings) for g in combine_containers(groups)]
    prevent_overlaps(rows)
    accepted_pairs = {k for row in rows if row['state']==ACCEPTED for k in row['selectedPairKeys']}
    pair_routes = defaultdict(set)
    for row in rows:
        for key in row['selectedPairKeys']:
            pair_routes[key].update(k[0] for k in row['originalKeys'])
    pair_rows = []
    for key, pair in sorted(pairs.items()):
        state = ACCEPTED if key in accepted_pairs else HELD
        if pair['category']=='different_entities_candidate' and pair['coverageState']=='validated_recommendation':
            state = 'provisional_nonidentity_pair'
        elif pair['coverageState'] != 'validated_recommendation' and state != ACCEPTED:
            state = 'unresolved'
        pair_rows.append(dict(pairKeySha256=key, occurrenceIDs=pair['occurrenceIDs'],
            routes=sorted(pair_routes[key] | {pair['nominationOrigin']}), ontologyClass=[pair['ontologyClass']],
            familyCombination=pair['familyCombination'], identityScope=pair['identityScope'],
            state=state, originalCoverageState=pair['coverageState'], originalCategory=pair['category'],
            simulationOnly=True))
    overs = [dict(simulationID='oversized:'+x['originalBlock']['blockID'], occurrenceIDs=[],
        memberCount=x['originalBlock']['memberCount'], state=HELD, routes=[x['originalBlock']['key'][0]],
        ontologyClass=[x['originalBlock']['key'][1]],
        familyCombination=sorted(x['knownSummary']['sourceFamilyDistribution']) if x.get('knownSummary') else 'unknown_not_reexpanded',
        identityScope='between_families' if x.get('knownSummary', {}).get('crossFamily') else 'unknown_not_reexpanded',
        originalBlock=x['originalBlock'], savedSummary=x.get('knownSummary'),
        holdReasons=['oversized_membership_and_overlap_not_expanded'], simulationOnly=True) for x in oversized]
    all_rows = rows + overs
    accepted = [x for x in rows if x['state']==ACCEPTED]
    summary = dict(version=VERSION, candidateCompleteScopes=len(rows), oversizedScopes=len(overs),
        candidateKnownOccurrences=len({o for row in rows for o in row['occurrenceIDs']}),
        groupStates=dict(Counter(x['state'] for x in all_rows)),
        explicitPairStates=dict(Counter(x['state'] for x in pair_rows)),
        explicitPairCoverage=dict(Counter(x['originalCoverageState'] for x in pair_rows)),
        provisionalAcceptedGroups=len(accepted), provisionalAcceptedOccurrences=len({o for g in accepted for o in g['occurrenceIDs']}),
        provisionalAcceptedImpliedPairs=sum(len(g['occurrenceIDs'])*(len(g['occurrenceIDs'])-1)//2 for g in accepted),
        groupDistributions=distribution(all_rows, 'group'), pairDistributions=distribution(pair_rows, 'explicit_pair'),
        heldGuardCounts=dict(sorted(Counter(reason for g in all_rows if g['state']==HELD for reason in g['holdReasons']).items())),
        alternativeStates={route:dict(Counter(g['alternativeStates'][route] for g in rows)) for route in ('A', 'B')},
        pilotApprovalSubsets=len(decisions), pilotDistinctApprovedOccurrences=len({o for d in decisions for o in d['occurrenceIDs']}),
        automaticEvaluationFrameExists=bool(accepted), evaluationCasesDrawn=0,
        identityDecisions=0, graphWrites=0, providerCalls=0)
    return all_rows, pair_rows, summary


def run(source: Path, output: Path) -> dict:
    """Consume saved triage hashes and sidecars; do not rerun the corpus pipeline."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(), 'FRESH_OUTPUT_REQUIRED')
    pins = {}

    def pin(path: Path, expected: str | None = None) -> None:
        """Verify consumed bytes and retain their exact pins."""
        digest = expected or r.identity.sha(path)
        require(str(path) not in pins or pins[str(path)] == digest, 'CONTRADICTORY_PIN')
        triage.queue.pilot.verify(path, digest, pins)

    pin(source/'manifest.json'); manifest = r.load(source/'manifest.json')
    require(manifest['version']=='step14-adjudication-triage/0.1.0', 'UNSUPPORTED_TRIAGE')
    for name in ('summary.json', 'pair-inventory.jsonl', 'block-coverage.jsonl', 'review-groups.jsonl',
                 'oversized-inventory.jsonl', 'prior-decisions.jsonl'):
        pin(source/name, manifest['outputHashes'][name])
    member_path = triage.BASE/'referent-groups/v1/members.jsonl'
    endpoint_path = triage.BASE/'unified-review-queue/v1/endpoint-provenance.jsonl'
    binding_path = triage.BASE/'unified-review-queue/v1/unit-bindings.jsonl'
    for path in (member_path, endpoint_path, binding_path, triage.queue.approvals.APPROVALS, triage.queue.approvals.DOCUMENT):
        pin(path, manifest['inputHashes'][str(path)])
    authority_path = triage.BASE/'semantic-candidates/v1/manifest.json'
    pin(authority_path, manifest['inputHashes'][str(authority_path)])
    authority = r.load(authority_path)
    for name in ('src/ontology/ontology_spec.yaml', 'src/ontology/ciroh_ontology.owl'):
        pin(Path(name), authority['inputHashes'][name])
    # Preserve the historical triage manifest, including its old handoff hash.
    # Only consumed immutable artifacts are rechecked, not now-superseded handoff bytes.
    for path in (POLICY, Path(__file__).relative_to(Path.cwd()), Path(triage.__file__).relative_to(Path.cwd())):
        pin(path)
    members, _ = triage.indexed(member_path, 'occurrenceID')
    endpoints, _ = triage.indexed(endpoint_path, 'occurrenceID')
    bindings, _ = triage.indexed(binding_path, 'unitID')
    pairs, _ = triage.indexed(source/'pair-inventory.jsonl', 'pairKeySha256')
    groups, _ = triage.indexed(source/'review-groups.jsonl', 'groupID')
    decisions = list(r.rows(source/'prior-decisions.jsonl'))
    require(decisions == list(r.rows(triage.queue.approvals.APPROVALS)), 'PILOT_APPROVAL_DRIFT')
    triage.queue.approvals.validate_approvals(r.load(triage.queue.approvals.DOCUMENT), decisions)
    blocks = list(r.rows(source/'block-coverage.jsonl'))
    oversized = [x for x in blocks if x['originalBlock'].get('status')=='oversized_not_expanded']
    cross_oversized = list(r.rows(source/'oversized-inventory.jsonl'))
    cross_index = {x['blockID']:x for x in cross_oversized}
    oversized = [dict(x, knownSummary=cross_index.get(x['originalBlock']['blockID'])) for x in oversized]
    group_rows, pair_rows, summary = evaluate(list(groups.values()), pairs, members, endpoints, decisions, oversized, bindings)
    original_summary = r.load(source/'summary.json')
    require(summary['explicitPairCoverage']==original_summary['pairCoverageStates'], 'PAIR_COVERAGE_DRIFT')
    require(len(pairs)==original_summary['selectedPoolPairs'], 'PAIR_COUNT_DRIFT')
    summary['preservedTriageAccounting'] = {k:original_summary[k] for k in (
        'validatedRecommendationPairs', 'generationOrigins', 'preservedNextQueueCoverage',
        'oversizedCrossFamilyBlocks', 'discoveryRouteCoverage')}
    require(len(cross_oversized)==original_summary['oversizedCrossFamilyBlocks'], 'OVERSIZED_COUNT_DRIFT')
    summary['evaluationBlueprint'] = str(POLICY)
    for path, digest in pins.items():
        triage.queue.pilot.verify(Path(path), digest, {})
    output.mkdir(parents=True)
    for name, values in (('group-simulations.jsonl', group_rows), ('pair-simulations.jsonl', pair_rows),
                         ('oversized-inventory.jsonl', cross_oversized), ('prior-decisions.jsonl', decisions)):
        with (output/name).open('x') as stream:
            for value in values:
                stream.write(r.identity.encoded(value).decode()+'\n')
    r.write(output/'summary.json', summary)
    (output/'report.md').write_text(
        '# Provisional automatic acceptance feasibility\n\n'
        f"Complete candidate scopes: {summary['candidateCompleteScopes']}; oversized scopes: {summary['oversizedScopes']}. "
        f"Provisional accepted groups: {summary['provisionalAcceptedGroups']}; distinct accepted occurrences: {summary['provisionalAcceptedOccurrences']}.\n\n"
        'These are simulations, not policy acceptance or human verification. See summary.json for exact group/pair/occurrence distributions and preserved route accounting. '
        'Group and pair denominators differ; route facets overlap. Oversized memberships and scope remain unknown rather than expanded.\n\n'
        'Concrete limitation: saved granularity is unspecified and referent/version compatibility is not mechanically certified. Equal identifiers, version strings or model prose do not establish the missing conditions. '
        'Held groups are not rejected. Historical approvals stay exact and separate. No human sample is drawn.\n\n'
        f'One-time evaluation blueprint: {POLICY}. Freeze policy/frame first; select one budget of 60, 80 or 100 complete-group judgments, '
        'with stratified inclusion probabilities and weights, blinded evidence, and a bounded whole-group check. Zero automatic yield means no evaluation frame. '
        'Next decision: establish a reproducible safeguard interpretation before freezing production rules; no extra calls or extraction are authorized here.\n')
    r.write(output/'manifest.json', dict(version=VERSION, inputHashes=pins,
        outputHashes={p.name:r.identity.sha(p) for p in sorted(output.iterdir())},
        simulationOnly=True, identityDecisions=0, providerCalls=0, evaluationCasesDrawn=0))
    return summary


def main() -> None:
    """Run the preview offline only, into a fresh ignored output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--triage', type=Path, default=triage.ROOT/'v1')
    parser.add_argument('--output', type=Path, default=ROOT/'v1')
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('OFFLINE_ONLY')), \
         patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('OFFLINE_ONLY')):
        print(json.dumps(run(args.triage, args.output), sort_keys=True))


if __name__ == '__main__':
    main()
