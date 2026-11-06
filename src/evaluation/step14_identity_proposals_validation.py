"""Read-only validation of the fixed prospective Step 14 proposal document.

The 43-case triage is provisional ChatGPT-assisted review. Separate append-only
records carry only the subsequent explicit researcher approvals. No generation,
decision-making, ledger update, canonical allocation, or provider call occurs here.
Run from the repository root with the saved, ignored live/v2 package available.
"""
from __future__ import annotations

import json
import argparse
import socket
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from src.evaluation import step14_identity_live as live

DOCUMENT = Path('docs/study2_step14_identity_adjudication_proposals_v0.1.json')
PACKAGE = Path('var/study2_step14/semantic-identity-live/v2')
PACKAGE_PIN = 'c2712f7e90b04c64e039a21302fb5b05ef922508f47b5a461ece813cb638662c'
# Fixed provisional ChatGPT-assisted triage scopes, not researcher approvals.
PARTIAL_SCOPES = {
    'C004': [[7, 9], [6, 8]], 'C014': [list(range(1, 13)) + list(range(15, 22))],
    'C016': [], 'C018': [[10, 17, 19], [11, 22]], 'C023': [[1, 2, 3, 4, 5]],
    'C025': [list(range(8, 16)) + [17], [5, 6]], 'C028': [[1, 2]],
    'C032': [[1, 2]], 'C034': [[1, 2]], 'C035': [[1, 5, 6, 8, 12, 15, 18]],
    'C036': [[1, 2]],
}
NO_ENTITY_CASES = {'C009', 'C024', 'C027', 'C038', 'C041', 'C042'}
APPROVALS = Path('docs/evaluation/study2_step14_identity_approvals_batch01.jsonl')
APPROVED_COMPLETE = {
    'C001', 'C002', 'C003', 'C005', 'C006', 'C007', 'C008', 'C010',
    'C011', 'C012', 'C013', 'C015', 'C017', 'C019', 'C021', 'C022',
    'C026', 'C029', 'C030', 'C033', 'C037', 'C039', 'C040', 'C043',
}
APPROVED_PARTIAL = {
    'C023': [1, 2, 3, 4, 5], 'C028': [1, 2], 'C032': [1, 2],
    'C035': [1, 5, 6, 8, 12, 15, 18], 'C036': [1, 2],
}
TRIAGE_CASES_PIN = '7c3ed82ca55b9dc089e49254c78c4ebf271c671d2ae069d894e6ee0129a9b33a'
REVIEW_ATTRIBUTION = (
    'Provisional ChatGPT-assisted 43-case triage; not researcher adjudication or '
    'independent/blinded review. Only the 29 subsets in the subsequent approval '
    'record have received explicit researcher approval.'
)


def validate_attribution(document: dict) -> None:
    """Keep historical proposals separate from subsequent researcher decisions."""
    require(document['reviewAuthority'] == REVIEW_ATTRIBUTION, 'Review attribution drift')
    require(document['subsequentApprovalRecord'] == {
        'file': str(APPROVALS), 'approvedSubsets': 29, 'approvedOccurrences': 99,
        'remainingUnapprovedOccurrences': 133, 'proposalStatusesAreHistorical': True,
    }, 'Approval attribution drift')
    require(live.token(document['cases']) == TRIAGE_CASES_PIN, 'Underlying proposals changed')


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
                'Provisional triage subset boundaries changed')
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
    validate_attribution(document)
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


def validate_approvals(document: dict, records: list[dict], *, verify_files: bool = True) -> dict:
    """Check the explicit first approval batch against unchanged proposal bindings.

    This deliberately avoids replaying the already verified full input chain or
    provider-response validation. Hash-check only the directly reused authorities.
    Synthetic tests can disable filesystem checks; the CLI always enables them.
    """
    validate_attribution(document)
    expected_cases = sorted(APPROVED_COMPLETE | APPROVED_PARTIAL.keys())
    require([r['caseAlias'] for r in records] == expected_cases, 'Approval batch scope changed')
    proposal_hash = live.identity.sha(DOCUMENT)
    references = [document[k] for k in ('sourcePackage', 'pilotPackage', 'policy')]
    approved = set()
    cases = {c['caseAlias']: (i, c) for i, c in enumerate(document['cases'])}
    for record in records:
        alias = record['caseAlias']
        index, case = cases[alias]
        subset = case['proposedEntitySubsets'][0]
        members = ([o['alias'] for o in case['occurrences']] if alias in APPROVED_COMPLETE
                   else [f'O{i:03}' for i in APPROVED_PARTIAL[alias]])
        require(subset['memberAliases'] == members, 'Approved scope differs from proposal')
        occurrence_ids = [next(o['occurrenceID'] for o in case['occurrences'] if o['alias'] == m)
                          for m in members]
        require(subset['occurrenceIDs'] == occurrence_ids, 'Original occurrence resolution failed')
        require(not approved.intersection(occurrence_ids), 'Implicit union or duplicate approval')
        expected = dict(
            decisionID='step14-identity-batch01:' + alias, revision=1, supersedes=None,
            decisionStatus='approved_entity_identity',
            decisionAuthority='researcher_explicit_batch01_instruction',
            authorityStatement='The researcher has now explicitly approved the following batch of entity-identity proposals: 24 complete cases and five specified partial subsets. Approval does not authorize canonical-ID allocation, graph consolidation, ontology changes, or edits to frozen outputs.',
            caseAlias=alias,
            proposalReference=dict(file=str(DOCUMENT), sha256=proposal_hash, jsonPointer=f'/cases/{index}'),
            caseID=case['originalCaseID'], caseSha256=case['caseSha256'], contextSha256=case['contextSha256'],
            sourcePackage=document['sourcePackage'], pilotPackage=document['pilotPackage'], policy=document['policy'],
            audit=case['audit'], originalCandidateIDs=case['originalCandidateIDs'],
            ontologyClass=case['ontologyClass'], identityLevel='entity', memberAliases=members,
            occurrenceIDs=occurrence_ids, granularity=subset['granularity'],
            versionAndRoleRestrictions=case['versionAndRoleRestrictions'], subsetRestriction=subset['restriction'],
            conflictScope=subset.get('conflictScope'),
            supportingEvidenceIDs=[case['evidenceBindings'][e]['evidenceID'] for e in subset['supportingEvidenceAliases']],
            conflictingEvidenceIDs=[case['evidenceBindings'][e]['evidenceID'] for e in subset['conflictingEvidenceAliases']],
            retainedReviewConcerns=case['reviewConcerns'], originalModelRecommendation=case['originalModelRecommendation'],
            originalRawResponse=case['originalRawResponse'],
            rationale='Explicit researcher approval of this exact proposed subset at its stated granularity. ' + case['evidenceReview'],
            materializationStatus='not_authorized', transitiveUnionAuthorized=False,
        )
        require(record == expected, f'Approval record differs from authorized scope/restrictions: {alias}')
        approved.update(occurrence_ids)
        references.extend(record[k] for k in ('proposalReference', 'audit', 'originalModelRecommendation', 'originalRawResponse'))
    universe = {o['occurrenceID'] for c in document['cases'] for o in c['occurrences']}
    require(len(approved) == 99 and len(universe - approved) == 133, 'Approval coverage mismatch')
    if verify_files:
        # A file hash binds all internal JSON pointers; check each file only once.
        checked = {}
        for reference in references:
            name, digest = reference['file'], reference['sha256']
            if name not in checked:
                verify_reference(reference)
                checked[name] = digest
            require(checked[name] == digest, 'Inconsistent authority hash')
    return dict(approvedSubsets=len(records), approvedOccurrences=len(approved),
                remainingUnapprovedOccurrences=len(universe - approved), canonicalIDsAllocated=0)


def main() -> None:
    """Run the focused offline check; no output or ledger files are written."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approvals-only', action='store_true', help='Check batch 01 without a full package audit')
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('Offline validation')):
        document = live.load(DOCUMENT)
        records = [json.loads(line) for line in APPROVALS.read_text().splitlines()]
        result = {} if args.approvals_only else validate(document)
        result['researcherApprovalBatch01'] = validate_approvals(document, records)
        print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
