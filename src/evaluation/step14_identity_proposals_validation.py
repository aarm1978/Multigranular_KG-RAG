"""Read-only validation of the fixed prospective Step 14 proposal document.

No generation, adjudication, ledger update, canonical allocation, or provider call.
Run from the repository root with the saved, ignored live/v2 package available.
"""
from __future__ import annotations

import json
import socket
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from src.evaluation import step14_identity_live as live

DOCUMENT = Path('docs/study2_step14_identity_adjudication_proposals_v0.1.json')
PACKAGE = Path('var/study2_step14/semantic-identity-live/v2')
PACKAGE_PIN = 'c2712f7e90b04c64e039a21302fb5b05ef922508f47b5a461ece813cb638662c'
# Fixed proposal scopes from the researcher's directions, not an identity rule.
PARTIAL_SCOPES = {
    'C004': [[7, 9], [6, 8]], 'C014': [list(range(1, 13)) + list(range(15, 22))],
    'C016': [], 'C018': [[10, 17, 19], [11, 22]], 'C023': [[1, 2, 3, 4, 5]],
    'C025': [list(range(8, 16)) + [17], [5, 6]], 'C028': [[1, 2]],
    'C032': [[1, 2]], 'C034': [[1, 2]], 'C035': [[1, 5, 6, 8, 12, 15, 18]],
    'C036': [[1, 2]],
}
NO_ENTITY_CASES = {'C009', 'C024', 'C027', 'C038', 'C041', 'C042'}


def require(condition: bool, message: str) -> None:
    """Fail closed without relying on assertions enabled at interpreter startup."""
    if not condition:
        raise ValueError(message)


def pointer(value: object, path: str) -> object:
    """Resolve an exact JSON Pointer in a pinned saved record."""
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def verify_reference(reference: dict) -> Path:
    """Verify bytes without altering the referenced file."""
    path = Path(reference['file'])
    require(path.is_file(), f'Missing authority: {path}')
    require(live.identity.sha(path) == reference['sha256'], f'Hash drift: {path}')
    if reference.get('jsonPointer'):
        pointer(live.load(path), reference['jsonPointer'])
    return path


def validate_case(case: dict, schema: dict) -> tuple[set[str], int]:
    """Check proposal scope and exact membership/evidence against original audits."""
    alias = case['caseAlias']
    for field in ('audit', 'request', 'originalModelRecommendation',
                  'originalRawResponse', 'terminal'):
        verify_reference(case[field])
    require(case['audit']['file'] == str(PACKAGE / f'audit/{alias}.json'), 'Audit case mismatch')
    require(case['request']['file'] == str(PACKAGE / f'requests/{alias}.json'), 'Request case mismatch')
    attempt = PACKAGE / f'attempts/{alias}/0001'
    require(sorted((PACKAGE / 'attempts' / alias).iterdir()) == [attempt], 'Unexpected attempt set')
    for field, name in (('originalModelRecommendation', 'validated-recommendation.json'),
                        ('originalRawResponse', 'raw-model-output.txt'), ('terminal', 'terminal.json')):
        require(case[field]['file'] == str(attempt / name), 'Attempt case mismatch')
    audit = live.load(Path(case['audit']['file']))
    payload = audit['validationRequest']['payload']
    original = payload['case']
    context = json.loads(live.load(Path(case['request']['file']))['input'])
    terminal = live.load(attempt / 'terminal.json')
    require(terminal['status'] == 'validated_recommendation_only', 'Incomplete recommendation')
    for name, digest in terminal['artifactHashes'].items():
        require(live.identity.sha(attempt / name) == digest, f'Attempt drift: {alias}/{name}')
    raw = (attempt / 'raw-model-output.txt').read_bytes()
    require(raw == live.provider.extract_model_output(live.load(attempt / 'provider-response.json')),
            'Raw model output differs from provider response')
    rebound = live.bind_recommendation(raw, live.load(Path(case['request']['file'])), audit, schema)
    require(rebound == live.load(attempt / 'validated-recommendation.json'), 'Recommendation changed')
    model = rebound['modelAuthored']
    require(not model['unassessedOccurrenceIDs'], 'Unexpected unassessed model members')
    require(case['status'] == 'proposal_only' and case['approvalStatus'] == 'not_approved', 'Approval forbidden')
    for field, saved in (('originalCaseID', original['caseID']), ('caseSha256', original['caseSha256']),
                         ('contextSha256', payload['contextSha256']), ('ontologyClass', original['ontologyClass']),
                         ('originalCandidateIDs', original['originalCandidateIDs']), ('relatedCaseIDs', original['relatedCaseIDs'])):
        require(case[field] == saved, f'Case binding mismatch: {alias}/{field}')
    require(pointer(audit, case['originalCasePointer']) == original, 'Original case pointer mismatch')
    require(pointer(audit, case['originalAcceptedRelationsPointer']) == payload['acceptedRelations'], 'Relation pointer mismatch')
    require(case['originalModelRecommendation']['jsonPointer'] == '/modelAuthored', 'Model attribution pointer mismatch')
    require(case['modelAttribution'] == {'model': 'gpt-6.1-sol', 'reasoningEffort': 'medium', 'status': 'recommendation_only'}, 'Attribution drift')
    occurrences = {o['alias']: o for o in case['occurrences']}
    require(len(occurrences) == len(case['occurrences']), 'Duplicate occurrence alias')
    expected = {k: v for k, v in audit['aliases'].items() if k.startswith('O')}
    require({k: o['occurrenceID'] for k, o in occurrences.items()} == expected, 'Occurrence membership drift')
    require(set(expected.values()) == set(original['occurrenceIDs']), 'Original membership mismatch')
    model_occurrences = {o['occurrenceID']: o for o in context['occurrences']}
    for key, occurrence in occurrences.items():
        saved = pointer(audit, occurrence['auditPointer'])
        for field in ('occurrenceID', 'ontologyClass', 'sourceArtifacts', 'graphReference'):
            require(occurrence[field] == saved[field], f'Occurrence binding drift: {alias}/{key}/{field}')
        require(occurrence['ontologyClass'] == case['ontologyClass'], 'Incompatible class')
        require(occurrence['evidenceAliases'] == model_occurrences[key]['evidenceIDs'], 'Occurrence evidence drift')
    require(set(case['evidenceBindings']) == set(audit['evidenceBindings']), 'Evidence coverage drift')
    for key, binding in case['evidenceBindings'].items():
        require(binding['evidenceID'] == audit['aliases'][key], 'Evidence alias drift')
        require(pointer(audit, binding['auditPointer']) == audit['evidenceBindings'][key], 'Evidence pointer drift')
    summary = [{'assessmentIndex': i, 'memberAliases': a['occurrenceIDs'],
                'recommendation': a['recommendation'], 'identityLevel': a['identityLevel'],
                'evidenceAliases': a['evidenceIDs'], 'conflictEvidenceAliases': a['conflictEvidenceIDs']}
               for i, a in enumerate(model['assessments'])]
    require(case['originalAssessmentSummary'] == summary, 'Attributed recommendation summary changed')
    included = set()
    for subset in case['proposedEntitySubsets']:
        members = subset['memberAliases']
        require(len(members) >= 2 and len(members) == len(set(members)), 'Invalid proposed subset')
        require(set(members) <= set(expected), 'Unknown proposed member')
        require(not included.intersection(members), 'Overlapping proposals require explicit review, not union')
        require(subset['occurrenceIDs'] == [expected[m] for m in members], 'Proposed member binding drift')
        require(subset['status'] == 'proposal_only' and bool(subset['granularity']), 'Invalid proposal state')
        require(bool(subset['supportingEvidenceAliases']), 'Proposal without evidence')
        for field in ('supportingEvidenceAliases', 'conflictingEvidenceAliases'):
            require(set(subset[field]) <= set(case['evidenceBindings']), 'Unknown proposal evidence')
        included.update(members)
    unresolved = case['unresolvedOrExcludedFromEntityProposal']
    require(len(unresolved) == len(set(unresolved)) and set(unresolved) == set(expected) - included,
            'Unaccounted or multiply classified occurrence')
    for concern in case['reviewConcerns']:
        require(set(concern['memberAliases']) <= set(expected), 'Unknown concern member')
        require(set(concern['evidenceAliases']) <= set(case['evidenceBindings']), 'Unknown concern evidence')
    if case['disposition'] == 'whole_case_entity_identity_proposal':
        require(len(case['proposedEntitySubsets']) == 1 and included == set(expected), 'Whole-case proposal drift')
    if case['disposition'] == 'no_entity_merge_proposed':
        require(not included, 'Unexpected entity proposal')
    if alias in PARTIAL_SCOPES:
        require(case['disposition'] == 'partial_or_conditional_review', 'Partial disposition drift')
        require([s['memberAliases'] for s in case['proposedEntitySubsets']] ==
                [[f'O{i:03}' for i in group] for group in PARTIAL_SCOPES[alias]],
                'Researcher-directed subset boundaries changed')
    elif alias in NO_ENTITY_CASES:
        require(case['disposition'] == 'no_entity_merge_proposed', 'No-merge disposition drift')
    else:
        require(case['disposition'] == 'whole_case_entity_identity_proposal', 'Whole disposition drift')
    if 'nonIdentityReviewPartitions' in case:
        members = [m for p in case['nonIdentityReviewPartitions'] for m in p['memberAliases']]
        require(len(members) == len(set(members)) and set(members) == set(expected), 'Review partition drift')
    return set(expected.values()), len(model['assessments'])


def validate(document: dict) -> dict:
    """Validate all 43 fixed cases without scientific adjudication or writes."""
    require(document['status'] == 'prospective_proposals_only' and document['approvalStatus'] == 'not_approved', 'Approval forbidden')
    require(document['noTransitiveUnion'] is True, 'Union forbidden')
    require(document['sourcePackage']['sha256'] == PACKAGE_PIN, 'Wrong package pin')
    require(document['sourcePackage']['file'] == str(PACKAGE / 'manifest.json'), 'Wrong package')
    for field in ('sourcePackage', 'pilotPackage', 'policy'):
        verify_reference(document[field])
    live.verify_run(PACKAGE)
    schema = live.load(PACKAGE / 'recommendation.schema.json')
    cases = document['cases']
    require([c['caseAlias'] for c in cases] == [f'C{i:03}' for i in range(1, 44)], 'Case coverage drift')
    ids, assessments, memberships = set(), 0, 0
    for case in cases:
        members, count = validate_case(case, schema)
        ids.update(members)
        memberships += len(members)
        assessments += count
    counts = dict(Counter(c['disposition'] for c in cases))
    require(counts == {'whole_case_entity_identity_proposal': 26, 'partial_or_conditional_review': 11,
                       'no_entity_merge_proposed': 6}, 'Disposition coverage drift')
    coverage = dict(cases=len(cases), uniqueOccurrences=len(ids), caseMemberships=memberships,
                    originalModelAssessments=assessments, modelUnassessedOccurrences=0)
    require(coverage == document['expectedCoverage'], 'Coverage mismatch')
    require(coverage == dict(cases=43, uniqueOccurrences=232, caseMemberships=232,
                            originalModelAssessments=75, modelUnassessedOccurrences=0), 'Authority scope drift')
    def no_allocation(value: object) -> None:
        """Reject identity-allocation or approved-decision fields anywhere in proposals."""
        if isinstance(value, dict):
            require(not {'canonicalID', 'canonicalIDs', 'decisionAuthority', 'sameAs'} & value.keys(), 'Allocation forbidden')
            for nested in value.values():
                no_allocation(nested)
        elif isinstance(value, list):
            for nested in value:
                no_allocation(nested)
    no_allocation(document)
    live.verify_run(PACKAGE)
    for case in cases:
        for field in ('audit', 'request', 'originalModelRecommendation', 'originalRawResponse', 'terminal'):
            verify_reference(case[field])
    return dict(coverage=coverage, dispositions=counts, status='validated_proposals_only')


def main() -> None:
    """Run the focused offline check; no output or ledger files are written."""
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('Offline validation')):
        print(json.dumps(validate(live.load(DOCUMENT)), sort_keys=True))


if __name__ == '__main__':
    main()
