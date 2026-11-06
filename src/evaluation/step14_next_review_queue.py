"""Reconcile saved Step 14 reviews and propose a bounded queue; no new discovery."""
from __future__ import annotations

import argparse
import json
import socket
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from src.evaluation import step14_identity_proposals_validation as approvals
from src.evaluation import step14_semantic_candidates as candidates
from src.evaluation import step14_semantic_identity_pilot as pilot
from src.evaluation import step14_semantic_review as review

ROOT = Path('var/study2_step14/next-review-queue')
OUTPUT = ROOT / 'v1'
REVIEW = Path('var/study2_step14/semantic-review/v1')
PILOT = Path('var/study2_step14/semantic-identity-pilot/v1')
ID = 'identifier_declaration_only'
LEXICAL = 'lexical_similarity_only'
require = approvals.require


def scope_for_key(member: dict, key: list) -> str:
    """Use only declarations for this exact key; never infer scope from a URL."""
    field = member['identifierDeclarations']
    if field.get('truncated'):
        return 'unresolved_declaration_scope'
    bases = {d.get('basis') for d in field.get('value', [])
             if [d.get('scheme'), d.get('value')] == key[2:]}
    if not bases:
        return 'unresolved_declaration_scope'
    if bases <= {'deterministic_entity_own_field', 'C-D04'}:
        return 'deterministic_entity_own_identifier'
    if bases == {'accepted_source_local_candidate'}:
        return 'source_local_literal_declaration'
    if bases == {'deterministic_geospatial_target'}:
        return 'literal_geographic_declaration_no_namespace_equivalence'
    return 'mixed_or_unsupported_scope'


def select_sample(rows: list[dict], identifier_limit: int = 12, lexical_limit: int = 18,
                  member_limit: int = 8, total_limit: int = 160) -> list[str]:
    """Round-robin class/scope strata; complete blocks only, no pair expansion."""
    selected = []; workload = 0
    for mechanism, limit in ((ID, identifier_limit), (LEXICAL, lexical_limit)):
        buckets = defaultdict(list)
        for row in rows:
            if (row['candidateMechanism'] != mechanism or row['directReviewedCaseIDs']
                    or not row['newOccurrenceIDs'] or row['memberCount'] > member_limit
                    or row['contextGapOccurrenceIDs']):
                continue
            stratum = (row['ontologyClass'], tuple(sorted(row['identifierScopeCounts'])))
            buckets[stratum].append(row)
        for bucket in buckets.values():
            # Prefer entirely new work, then lower workload; no confidence score.
            bucket.sort(key=lambda r: (bool(r['reviewedOccurrenceIDs']), r['memberCount'], r['blockID']))
        picked = 0
        while any(buckets.values()) and picked < limit:
            for stratum in sorted(buckets):
                if not buckets[stratum] or picked >= limit:
                    continue
                row = buckets[stratum].pop(0)
                if workload + row['memberCount'] <= total_limit:
                    selected.append(row['blockID']); workload += row['memberCount']; picked += 1
    return selected


def reconcile(blocks: list[dict], oversized: list[dict], cases: list[dict], decisions: list[dict]) -> dict:
    """Separate direct block review, occurrence overlap, and exact approved subsets."""
    case_index = {c['caseID']: c for c in cases}
    require(len(case_index) == len(cases), 'Duplicate reviewed case')
    approved = defaultdict(list)
    for decision in decisions:
        require(decision['caseID'] in case_index, 'Approval without reviewed case')
        for occurrence in decision['occurrenceIDs']:
            require(occurrence in case_index[decision['caseID']]['occurrenceIDs'], 'Approval membership drift')
            approved[occurrence].append(decision['decisionID'])
    seen = defaultdict(list)
    for case in cases:
        require(len(case['occurrenceIDs']) == len(set(case['occurrenceIDs'])), 'Duplicate case occurrence')
        for occurrence in case['occurrenceIDs']:
            seen[occurrence].append(case['caseID'])
    rows = []; ids = set()
    for block in sorted(blocks, key=lambda b: b['blockID']):
        bid = block['blockID']; members = block['occurrenceIDs']
        require(bid not in ids, 'Duplicate block'); ids.add(bid)
        require(len(members) == len(set(members)) == block['memberCount'], 'Invalid block membership')
        require(candidates.token(sorted(members)) == block['membershipSha256'], 'Membership hash drift')
        require(block['candidateMechanism'] in (ID, LEXICAL), 'Unknown mechanism')
        require(block['key'][:2] == [block['candidateMechanism'], block['ontologyClass']], 'Key drift')
        require({m['occurrenceID'] for m in block['members']} == set(members)
                and len(block['members']) == len(members), 'Dossier member drift')
        families = Counter(f for m in block['members'] for f in set(m['sourceFamilies']))
        require(len(families) > 1 and dict(families) == block['sourceFamilyDistribution'], 'Family drift')
        require(all(m['ontologyClass'] == block['ontologyClass'] for m in block['members']), 'Class mismatch')
        direct = sorted(c['caseID'] for c in cases if bid in c['originalCandidateIDs'])
        for cid in direct:
            require(set(case_index[cid]['occurrenceIDs']) == set(members)
                    and case_index[cid]['ontologyClass'] == block['ontologyClass'], 'Reviewed block drift')
        overlap = sorted(set(members) & seen.keys())
        scopes = {m['occurrenceID']: scope_for_key(m, block['key']) for m in block['members']} if block['candidateMechanism'] == ID else {}
        gaps = sorted(m['occurrenceID'] for m in block['members'] if not m['sourceArtifacts']
                      or not m['evidenceExcerpts'] or all(e['missingEvidenceText'] for e in m['evidenceExcerpts']))
        rows.append(dict(blockID=bid, key=block['key'], ontologyClass=block['ontologyClass'],
            candidateMechanism=block['candidateMechanism'], occurrenceIDs=members,
            memberCount=len(members), membershipSha256=block['membershipSha256'],
            dossierReference=dict(file=str(REVIEW/'review-dossier.jsonl'), blockID=bid, recordSha256=candidates.token(block)),
            sourceFamilyDistribution=dict(sorted(families.items())), sourceArtifacts=block['sourceArtifacts'],
            directReviewedCaseIDs=direct, overlappingCaseIDs=sorted({c for o in overlap for c in seen[o]}),
            sameMembershipReviewedCaseIDs=sorted(c['caseID'] for c in cases if set(c['occurrenceIDs']) == set(members)
                                                and c['ontologyClass'] == block['ontologyClass']),
            reviewedOccurrenceIDs=overlap, newOccurrenceIDs=sorted(set(members)-seen.keys()),
            priorApprovalDecisionIDsByOccurrence={o: sorted(approved[o]) for o in members if o in approved},
            identifierScopeByOccurrence=scopes, identifierScopeCounts=dict(sorted(Counter(scopes.values()).items())),
            contextGapOccurrenceIDs=gaps, existingBlockFlags=block['existingBlockFlags'],
            identityState='no_new_decision_prior_approvals_do_not_extend',
            reviewState='directly_reviewed' if direct else 'not_directly_reviewed'))
    overs = []
    for block in sorted(oversized, key=lambda b: b['blockID']):
        require(block['blockID'] not in ids, 'Duplicate oversized block'); ids.add(block['blockID'])
        cross = len(block['sourceFamilyDistribution']) > 1
        require(block['crossFamily'] == cross and block['membershipVerified'], 'Oversized summary drift')
        if cross:
            row = deepcopy(block)
            row.update(originalSummaryReference=dict(file=str(REVIEW/'oversized-summary.jsonl'),
                       blockID=block['blockID'], recordSha256=candidates.token(block)),
                       overlapStatus='not_recomputed_membership_not_expanded', selectedForReview=False)
            overs.append(row)
    selected = select_sample(rows)
    unreviewed = [r for r in rows if not r['directReviewedCaseIDs']]
    strata = Counter((r['candidateMechanism'], r['ontologyClass']) for r in unreviewed)
    return dict(blocks=rows, oversized=overs, selectedBlockIDs=selected, summary=dict(
        ordinaryCrossFamilyBlocks=len(rows), directlyReviewedBlocks=len(rows)-len(unreviewed),
        unreviewedBlocks=len(unreviewed), unreviewedByMechanism=dict(sorted(Counter(r['candidateMechanism'] for r in unreviewed).items())),
        unreviewedWithFullOccurrenceOverlap=sum(not r['newOccurrenceIDs'] for r in unreviewed),
        unreviewedWithPartialOccurrenceOverlap=sum(bool(r['newOccurrenceIDs'] and r['reviewedOccurrenceIDs']) for r in unreviewed),
        oversizedCrossFamilyBlocks=len(overs), reviewedCases=len(cases), reviewedOccurrences=len(seen),
        approvedOccurrences=len(approved), unreviewedStrata=[dict(mechanism=k[0], ontologyClass=k[1], blocks=v) for k,v in sorted(strata.items())]))


def run(output: Path = OUTPUT) -> dict:
    """Read only saved bounded dossiers/packages and write fresh ignored queue files."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(), 'Fresh queue output required')
    pins = {}
    def check(path: Path, digest: str) -> None:
        """Reuse manifest hash verification and retain input pins."""
        pilot.verify(path, digest, pins)
    document = approvals.live.load(approvals.DOCUMENT)
    decisions = list(review.json_rows(approvals.APPROVALS))
    approvals.validate_approvals(document, decisions)
    for path in (approvals.DOCUMENT, approvals.APPROVALS):
        check(path, approvals.live.identity.sha(path))
    for field in ('sourcePackage', 'pilotPackage', 'policy'):
        ref = document[field]; check(Path(ref['file']), ref['sha256'])
    pm = approvals.live.load(PILOT/'manifest.json')
    check(REVIEW/'manifest.json', pm['inputHashes'][str(REVIEW/'manifest.json')])
    rm = approvals.live.load(REVIEW/'manifest.json')
    for name in ('review-dossier.jsonl', 'oversized-summary.jsonl'):
        check(REVIEW/name, rm['outputHashes'][name])
    check(PILOT/'review-cases.jsonl', pm['outputHashes']['review-cases.jsonl'])
    for name in ('src/ontology/ontology_spec.yaml', 'src/ontology/ciroh_ontology.owl'):
        check(Path(name), pm['inputHashes'][name])
    cases = list(review.json_rows(PILOT/'review-cases.jsonl'))
    by_id = {c['caseID']: c for c in cases}
    require(set(by_id) == {c['originalCaseID'] for c in document['cases']}, 'Reviewed universe mismatch')
    for case in document['cases']:
        original = by_id[case['originalCaseID']]
        for field in ('caseSha256', 'ontologyClass', 'originalCandidateIDs'):
            require(original[field] == case[field], 'Pilot/live binding drift')
        require(set(original['occurrenceIDs']) == {o['occurrenceID'] for o in case['occurrences']}, 'Pilot/live member drift')
        for field in ('audit', 'request', 'terminal', 'originalModelRecommendation', 'originalRawResponse'):
            ref = case[field]; check(Path(ref['file']), ref['sha256'])
        require(approvals.live.load(Path(case['terminal']['file']))['status'] == 'validated_recommendation_only', 'Incomplete prior review')
    blocks = list(review.json_rows(REVIEW/'review-dossier.jsonl'))
    oversized = list(review.json_rows(REVIEW/'oversized-summary.jsonl'))
    require(len(oversized) == rm['summary']['oversizedBlocks'], 'Oversized coverage drift')
    result = reconcile(blocks, oversized, cases, decisions)
    require(len(blocks) == rm['summary']['dossierBlocks'], 'Dossier coverage drift')
    originals = {b['blockID']: b for b in blocks}; rows = {r['blockID']: r for r in result['blocks']}
    sample = []
    for bid in result['selectedBlockIDs']:
        row = deepcopy(rows[bid]); row['members'] = []
        for m in originals[bid]['members']:
            member = {k: m[k] for k in ('occurrenceID', 'ontologyClass', 'occurrenceReference', 'sourceFamilies',
                      'sourceArtifacts', 'labels', 'versions', 'identifierDeclarations', 'originalSnapshotReference')}
            member['provenanceReference'] = m['originalProvenance']['fullReference']
            member['evidence'] = [{k: e[k] for k in ('reference', 'evidenceSha256', 'excerpt', 'truncated', 'originalCharacters')}
                                  for e in m['evidenceExcerpts']]
            row['members'].append(member)
        sample.append(row)
    result['summary']['sample'] = dict(blocks=len(sample), memberOccurrences=sum(r['memberCount'] for r in sample),
        distinctOccurrences=len({o for r in sample for o in r['occurrenceIDs']}),
        newOccurrences=len({o for r in sample for o in r['newOccurrenceIDs']}),
        strata=[dict(mechanism=k[0], ontologyClass=k[1], blocks=v) for k,v in sorted(Counter((r['candidateMechanism'],r['ontologyClass']) for r in sample).items())])
    for path, digest in pins.items():
        pilot.verify(Path(path), digest, {})
    output.mkdir(parents=True)
    for name, values in (('block-inventory.jsonl', result['blocks']), ('oversized-inventory.jsonl', result['oversized']), ('proposed-sample.jsonl', sample)):
        (output/name).write_bytes(b''.join(candidates.identity.encoded(r)+b'\n' for r in values))
    report = ['# Prospective next Step 14 review queue', '', 'No new identity decisions or inferred relations. Prior approvals apply only to their exact subsets.',
        '', '## Coverage', '', '```json', json.dumps(result['summary'], indent=2), '```', '',
        '## Selection', '', 'At most 12 identifier and 18 lexical blocks, at most 8 members per block and 160 member occurrences total. Round-robin (ontology class, exact-key scope set) strata; lexical strata use class only. Within strata prefer no prior overlap, then smaller blocks, then block ID. Require at least one new occurrence and selected evidence/source artifacts for every member. Select complete blocks only; no replacement of omitted members. This is workload prioritization, not confidence or acceptance scoring.',
        '', '## Proposed sample', '', '| Block ID | Mechanism | Class | Members | Key |', '|---|---|---|---:|---|']
    report += [f"| {r['blockID']} | {r['candidateMechanism']} | {r['ontologyClass']} | {r['memberCount']} | {str(r['key']).replace('|', '/')} |" for r in sample]
    report += ['', '## Limits', '', 'Direct block review requires original candidate-ID membership. Shared-reference hub cases are separately accounted through exact occurrence overlap, not relabeled as reviews of identifier blocks. Full occurrence overlap is excluded from the proposed new sample, not marked rejected or approved. Local literal identifiers never become global identities. Unknown or truncated identifier scope remains unresolved. Selection is purposive, not population evaluation; omitted strata/blocks remain unresolved.',
        '', 'Oversized counts/families/membership hashes come from the pinned saved summaries, previously verified by semantic-review/v1. Membership and overlap are not recomputed or expanded here; no oversized pairs or subsets are generated. Full evidence/attributes remain at exact dossier and occurrence pointers; excerpts retain original truncation. Repeated artifacts or text are not independent corroboration. No raw graph or full candidate occurrence dataset is scanned.']
    (output/'report.md').write_text('\n'.join(report)+'\n')
    manifest = dict(version='step14-next-review-queue/0.1.0', summary=result['summary'], inputHashes=pins,
        implementationSha256=approvals.live.identity.sha(Path(__file__)),
        implementationHashes={str(Path(m.__file__).relative_to(Path.cwd())): approvals.live.identity.sha(Path(m.__file__))
                              for m in (approvals, pilot, review, candidates, approvals.live)},
        occurrenceReferenceBase=str(review.INPUT), newIdentityDecisions=0, providerCalls=0, graphWrites=0,
        selectionLimits=dict(identifierBlocks=12, lexicalBlocks=18, membersPerBlock=8, totalMemberOccurrences=160),
        outputHashes={p.name: approvals.live.identity.sha(p) for p in sorted(output.iterdir())})
    (output/'manifest.json').write_bytes(candidates.identity.encoded(manifest)+b'\n')
    return manifest


def main() -> None:
    """Run offline; a new output directory is required."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('Offline queue preparation')):
        print(json.dumps(run(args.output)['summary'], sort_keys=True))


if __name__ == '__main__':
    main()
