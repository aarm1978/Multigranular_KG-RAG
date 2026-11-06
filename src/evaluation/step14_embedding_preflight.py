"""Prospective offline embedding workload inventory, never embedding execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import socket
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch

import yaml

from src.evaluation import step14_identity_preview as identity
from src.evaluation import step14_semantic_candidates as candidates
from src.evaluation import step14_semantic_identity_pilot as pilot
from src.evaluation import step14_semantic_review as review
from src.evaluation import step14_identity_proposals_validation as approvals

ROOT = Path('var/study2_step14/embedding-preflight')
QUEUE = Path('var/study2_step14/next-review-queue/v1')
QUEUE_PIN = '2b84abe340f7e49c94a16fea625b3b17bada4eb22dd53b0eb04ca8bb8370e757'
PILOT = Path('var/study2_step14/semantic-identity-pilot/v1')
REVIEW = Path('var/study2_step14/semantic-review/v1')
HUBS = Path('var/study2_step14/alignment-opportunities/v2/shared-reference-hubs.jsonl')
PLAN = dict(status='requires_researcher_approval', embeddingModel=None, tokenizer=None,
            dimensions=None, currencyBudget=None, runtimeBudget=None,
            queryLimit=500, topKPerQuery=5, totalCandidatePairBudget=1000,
            targetOccurrenceDegreeLimit=20, postingsPerTextPerQuery=3,
            queriesPerOversizedBlock=10, pairsPerOversizedBlock=20,
            estimatedTokensPerItemPlanningLimit=2048)
require = approvals.require


def text_hash(text: str) -> str:
    """Hash exact saved UTF-8 text; no fuzzy normalization or inferred aliases."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def membership_index(groups: list[dict], id_field: str, member_field: str) -> dict:
    """Index memberships linearly, never generate the induced pairs."""
    index = defaultdict(list)
    for group in groups:
        for occurrence in group[member_field]:
            index[occurrence].append(group[id_field])
    return {k: sorted(set(v)) for k,v in index.items()}


def analyze(rows, blocks: list[dict], cases: list[dict], reserved: list[dict],
            decisions: list[dict], hubs: list[dict], spec: dict) -> dict:
    """Stream saved occurrences into metadata-only inventories and workload counts."""
    classes = {c['name']: c for c in spec['classes']}
    comparison = {'Tool', 'Algorithm', 'Workflow'} | {
        c for c in candidates.descendants(classes, 'ComputationalModel') if not classes[c].get('abstract')}
    by_key = {tuple(b['key']): b for b in blocks}
    require(len(by_key) == len(blocks) and len({b['blockID'] for b in blocks}) == len(blocks), 'Duplicate block')
    reviewed = membership_index(cases, 'caseID', 'occurrenceIDs')
    reservation = membership_index(reserved, 'blockID', 'occurrenceIDs')
    approved = membership_index(decisions, 'decisionID', 'occurrenceIDs')
    reference_groups = [dict(groupID='v2-row-sha256:'+candidates.token(h), targetIDs=h['targetIDs']) for h in hubs]
    references = membership_index(reference_groups, 'groupID', 'targetIDs')
    inventory = []; seen = set(); membership = defaultdict(list)
    texts = defaultdict(list); eligible_texts = defaultdict(list); quotes = defaultdict(lambda: [0,set()])
    coverage = defaultdict(Counter); reasons_count = Counter(); corpus = Counter()
    for line, row in enumerate(rows, 1):
        oid = row['occurrenceID']; cls = row['ontologyClass']
        require(oid not in seen, 'Duplicate occurrence ID'); seen.add(oid)
        families = row['sourceFamilies']; artifacts = row['sourceArtifacts']
        require(isinstance(families, list) and all(isinstance(x,str) and x for x in families), 'Invalid families')
        require(isinstance(artifacts, list) and all(isinstance(x,str) and x for x in artifacts), 'Invalid artifacts')
        evidence = row['evidenceReferences']
        labels = candidates.literals(row['labels']); descriptions = candidates.literals(row['contextualDescriptions'])
        evidence_texts = sorted({s for e in evidence for s in candidates.literals(e.get('evidenceText'))})
        text = row['embeddingText']
        require(isinstance(text, str), 'Invalid saved embedding text')
        require(text == '\n'.join([cls, *labels, *descriptions, *evidence_texts]), 'Saved text projection drift')
        require(candidates.token(row['originalSnapshotRecord']) == row['snapshotRecordSha256'], 'Snapshot record drift')
        keys = review.record_keys(row)
        bids = []; overs = []
        for key in sorted(keys):
            if key in by_key:
                b = by_key[key]; membership[b['blockID']].append(oid); bids.append(b['blockID'])
                if b['status'] == 'oversized_not_expanded':
                    overs.append(b['blockID'])
        has_label = any(s.strip() for s in labels)
        has_description = any(s.strip() for s in descriptions)
        has_quote = any(s.strip() for s in evidence_texts)
        text_kind = ('contextual' if has_description or has_quote else 'label_only' if has_label else 'class_only')
        reasons = []
        if row['lane'] != 'semantic_comparison' or cls not in comparison:
            reasons.append('outside_proposed_semantic_comparison_lane')
        if cls not in classes or row['inventoryId'] != classes[cls]['id'] or classes[cls].get('abstract'):
            reasons.append('incompatible_or_abstract_class')
        if review.EXCLUDED_FLAGS.intersection(row['preparationFlags']):
            reasons.append('existing_exclusion_flag')
        if not families or not artifacts or not evidence:
            reasons.append('missing_source_provenance')
        if len(set(families)) != 1:
            reasons.append('source_family_not_single_explicit_family')
        if not has_quote:
            reasons.append('missing_evidence_text')
        if text_kind != 'contextual':
            reasons.append('insufficient_context_beyond_label')
        estimated_tokens = math.ceil(len(text)/4)
        if estimated_tokens > PLAN['estimatedTokensPerItemPlanningLimit']:
            reasons.append('above_proposed_text_budget_no_truncation')
        eligible = not reasons
        reasons_count.update(reasons)
        digest = text_hash(text)
        texts[digest].append(oid)
        if eligible:
            eligible_texts[digest].append(oid)
        for e in evidence:
            for quote in candidates.literals(e.get('evidenceText')):
                if quote.strip():
                    entry = quotes[text_hash(quote)]; entry[0] += 1; entry[1].update(artifacts)
        counters = dict(occurrences=1, proposedIndexEligible=int(eligible),
                        proposedQueryEligible=int(eligible and oid not in reviewed and oid not in reservation),
                        contextual=int(text_kind=='contextual'), labelOnly=int(text_kind=='label_only'),
                        classOnly=int(text_kind=='class_only'), missingLabels=int(not has_label),
                        missingDescriptions=int(not has_description), missingEvidenceText=int(not has_quote),
                        missingStructuredVersions=int(not row['versions']),
                        multipleLexicalLabels=int(len(row['normalizedLabels'])>1),
                        curationStatusUnrecorded=int(not row['originalSnapshotRecord'].get('curationStatus')),
                        textCharacters=len(text), utf8Bytes=len(text.encode('utf-8')), approximateTokens=estimated_tokens)
        corpus.update(counters)
        family_set = '|'.join(sorted(set(families))) or 'missing'
        for stratum in (('class', cls), ('lane', row['lane']), ('familySet', family_set), ('classFamilySet', cls+'|'+family_set)):
            coverage[stratum].update(counters)
        inventory.append(dict(occurrenceID=oid, ontologyClass=cls, inventoryId=row['inventoryId'], lane=row['lane'],
            sourceFamilies=families, sourceArtifacts=artifacts, textKind=text_kind,
            embeddingTextSha256=digest, textCharacters=len(text), utf8Bytes=len(text.encode('utf-8')),
            approximateTokens=estimated_tokens, textReference=dict(file=str(review.INPUT/'occurrences.jsonl'),
                line=line, occurrenceID=oid, recordSha256=candidates.token(row), jsonPointer='/embeddingText'),
            evidencePointer='/evidenceReferences', provenancePointer='/nativeReferences',
            originalRecordPointer='/originalSnapshotRecord', identifierDeclarationsPointer='/identifierDeclarations',
            versions=row['versions'], recordedCurationStatus=row['originalSnapshotRecord'].get('curationStatus'),
            ownerReferenceAssessment='not_inferred_requires_source_bound_review', granularity=row['granularity'],
            preparationFlags=row['preparationFlags'], proposedIndexEligible=eligible,
            proposedQueryEligible=bool(eligible and oid not in reviewed and oid not in reservation),
            eligibilityHolds=reasons, existingBlockIDs=sorted(bids), oversizedBlockIDs=sorted(overs),
            reviewedCaseIDs=reviewed.get(oid,[]), reservedQueueBlockIDs=reservation.get(oid,[]),
            priorApprovalDecisionIDs=approved.get(oid,[]), sharedReferenceGroupIDs=references.get(oid,[])))
    families_by_id = {r['occurrenceID']: r['sourceFamilies'] for r in inventory}
    oversized_summary = []
    for block in blocks:
        members = sorted(membership[block['blockID']])
        require(len(members) == block['memberCount'], 'Block member count drift')
        require(candidates.token(members) == block['membershipSha256'], 'Block member hash drift')
        require(block['occurrenceIDs'] == ([] if block['status']=='oversized_not_expanded' else members), 'Block member list drift')
        if block['status'] == 'oversized_not_expanded':
            families = Counter(f for oid in members for f in set(families_by_id[oid]))
            oversized_summary.append(dict(blockID=block['blockID'], key=block['key'], memberCount=len(members),
                membershipSha256=block['membershipSha256'], membershipVerified=True,
                sourceFamilyDistribution=dict(sorted(families.items())), crossFamily=len(families)>1,
                pairsGenerated=0, querySelectionPerformed=False))
    lengths = {r['embeddingTextSha256']:r for r in inventory}
    duplicates = [dict(embeddingTextSha256=h, occurrenceIDs=ids,
                       occurrenceCount=len(ids), identityImplication='none') for h,ids in sorted(texts.items()) if len(ids)>1]
    pools = defaultdict(set)
    for row in inventory:
        if row['proposedIndexEligible']:
            pools[row['ontologyClass']].update(row['sourceFamilies'])
    for row in inventory:
        row['potentialPeerFamilies'] = sorted(pools[row['ontologyClass']] - set(row['sourceFamilies'])) if row['proposedIndexEligible'] else []
    query_count = sum(r['proposedQueryEligible'] and bool(r['potentialPeerFamilies']) for r in inventory)
    summary = dict(coverage=dict(corpus), proposedComparisonClasses=sorted(comparison),
        eligibilityHolds=dict(sorted(reasons_count.items())),
        strata=[dict(dimension=k[0], value=k[1], **dict(v)) for k,v in sorted(coverage.items())],
        duplication=dict(uniqueExactPayloads=len(texts), duplicatePayloadGroups=len(duplicates),
            redundantPayloadOccurrences=sum(len(v)-1 for v in texts.values()),
            uniqueExactEvidenceQuotations=len(quotes), repeatedEvidenceQuotationGroups=sum(v[0]>1 for v in quotes.values()),
            evidenceQuotationsAcrossMultipleArtifacts=sum(len(v[1])>1 for v in quotes.values()),
            warning='Exact text reuse is not independent corroboration or identity.'),
        workload=dict(proposedEligibleUniquePayloads=len(eligible_texts),
            approximateUniquePayloadTokens=sum(lengths[h]['approximateTokens'] for h in eligible_texts),
            uniquePayloadUtf8Bytes=sum(lengths[h]['utf8Bytes'] for h in eligible_texts),
            proposedQueryUpperBound=min(PLAN['queryLimit'],query_count),
            potentialCrossFamilyQueryOccurrences=query_count,
            directedRetrievalSlotUpperBound=min(PLAN['queryLimit'],query_count)*PLAN['topKPerQuery'],
            candidatePairBudget=PLAN['totalCandidatePairBudget'], actualRequests=None, currencyEstimate=None,
            estimationMethod='ceil(Unicode characters/4) per unchanged saved payload; not a tokenizer or API quota estimate',
            vectorStorageFormula='4 * approved_dimension * unique_payloads bytes for float32 vectors only; index and postings overhead excluded'),
        reconciliation=dict(existingBlocks=len(blocks), oversizedBlocks=sum(b['status']=='oversized_not_expanded' for b in blocks),
            oversizedCrossFamilyBlocks=sum(b['crossFamily'] for b in oversized_summary),
            reviewedOccurrencesInInventory=len(seen & reviewed.keys()), reviewedOccurrencesOutsideInventory=sorted(reviewed.keys()-seen),
            reservedOccurrencesInInventory=len(seen & reservation.keys()), reservedOccurrencesOutsideInventory=sorted(reservation.keys()-seen),
            approvedOccurrencesInInventory=len(seen & approved.keys()), sharedReferenceGroups=len(reference_groups)))
    return dict(occurrences=inventory, duplicateTexts=duplicates,
                oversized=sorted(oversized_summary,key=lambda b:b['blockID']), summary=summary)


def run(output: Path) -> dict:
    """Researcher-terminal full inventory; verify saved authorities, never call models."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(), 'Fresh preflight output required')
    pins = {}
    def check(path: Path, digest: str) -> None:
        """Keep the complete direct-input pin set for reproducibility."""
        pilot.verify(path, digest, pins)
    document = approvals.live.load(approvals.DOCUMENT)
    decisions = list(review.json_rows(approvals.APPROVALS))
    approvals.validate_approvals(document, decisions)
    for path in (approvals.DOCUMENT, approvals.APPROVALS):
        check(path, identity.sha(path))
    for key in ('pilotPackage', 'sourcePackage', 'policy'):
        ref = document[key]; check(Path(ref['file']), ref['sha256'])
    pm = approvals.live.load(PILOT/'manifest.json')
    check(REVIEW/'manifest.json', pm['inputHashes'][str(REVIEW/'manifest.json')])
    rm = approvals.live.load(REVIEW/'manifest.json')
    check(review.INPUT/'manifest.json', rm['inputHashes'][str(review.INPUT/'manifest.json')])
    cm = approvals.live.load(review.INPUT/'manifest.json')
    for name in ('occurrences.jsonl', 'candidate-blocks.jsonl'):
        check(review.INPUT/name, cm['outputHashes'][name])
    for name in ('src/ontology/ontology_spec.yaml', 'src/ontology/ciroh_ontology.owl'):
        check(Path(name), cm['inputHashes'][name])
    for module in (candidates, review):
        path = Path(module.__file__).relative_to(Path.cwd())
        check(path, pm['inputHashes'][str(path)])
    check(PILOT/'review-cases.jsonl', pm['outputHashes']['review-cases.jsonl'])
    check(HUBS, pm['inputHashes'][str(HUBS)])
    check(QUEUE/'manifest.json', QUEUE_PIN)
    qm = approvals.live.load(QUEUE/'manifest.json')
    check(QUEUE/'proposed-sample.jsonl', qm['outputHashes']['proposed-sample.jsonl'])
    for name in (str(approvals.DOCUMENT), str(approvals.APPROVALS)):
        require(qm['inputHashes'][name] == pins[name], 'Reserved queue authority drift')
    reserved = list(review.json_rows(QUEUE/'proposed-sample.jsonl'))
    require(len(reserved) == qm['summary']['sample']['blocks'], 'Reservation count drift')
    spec = yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())
    require(spec['ontology']['version'] == '0.1.7', 'Ontology version drift')
    result = analyze(review.json_rows(review.INPUT/'occurrences.jsonl'), list(review.json_rows(review.INPUT/'candidate-blocks.jsonl')),
                     list(review.json_rows(PILOT/'review-cases.jsonl')), reserved, decisions, list(review.json_rows(HUBS)), spec)
    require(result['summary']['coverage']['occurrences'] == cm['coverage']['preparedOccurrences'], 'Occurrence coverage drift')
    require(not result['summary']['reconciliation']['reservedOccurrencesOutsideInventory'], 'Reserved member missing')
    for name,h in pins.items():
        pilot.verify(Path(name),h,{})
    output.mkdir(parents=True)
    for name, values in (('occurrence-preflight.jsonl',result['occurrences']), ('duplicate-text-groups.jsonl',result['duplicateTexts']),
                         ('oversized-preflight.jsonl',result['oversized'])):
        (output/name).write_bytes(b''.join(identity.encoded(r)+b'\n' for r in values))
    (output/'summary.json').write_bytes(identity.encoded(result['summary'])+b'\n')
    report = ['# Prospective embedding preflight — no embeddings generated', '',
        'Eligibility and limits require researcher approval. See docs/study2_step14_embedding_preflight.md.', '',
        '| Class | Occurrences | Proposed index eligible | Proposed query eligible | Label only | Class only | Missing evidence text |',
        '|---|---:|---:|---:|---:|---:|---:|']
    report += [f"| {r['value']} | {r['occurrences']} | {r['proposedIndexEligible']} | {r['proposedQueryEligible']} | {r['labelOnly']} | {r['classOnly']} | {r['missingEvidenceText']} |"
               for r in result['summary']['strata'] if r['dimension']=='class']
    report += ['', '## Workload and holds', '', '```json', json.dumps({k:result['summary'][k]
               for k in ('workload','duplication','eligibilityHolds')},indent=2), '```', '',
        'Class/family-set joint denominators and reconciliation coverage are in summary.json. '
        'Query counts precede actual cross-family/artifact filtering and retrieval quotas. '
        'Token estimates are characters/4, not tokenizer counts. Exact duplication does not imply identity. '
        'No model, price, monetary ceiling, runtime allowance, or retrieval parameters have been approved. '
        'No pairs, vectors, canonical IDs, or scientific relations were produced.']
    (output/'report.md').write_text('\n'.join(report)+'\n')
    manifest = dict(version='step14-embedding-preflight/0.1.0', status='prospective_offline_inventory_only',
        inputHashes=pins, proposedPlan=PLAN, summary=result['summary'], providerCalls=0, embeddingsGenerated=0,
        graphWrites=0, newIdentityDecisions=0, pairsGenerated=0, implementationSha256=identity.sha(Path(__file__)),
        outputHashes={p.name:identity.sha(p) for p in sorted(output.iterdir())})
    (output/'manifest.json').write_bytes(identity.encoded(manifest)+b'\n')
    return manifest


def main() -> None:
    """Offline only: no provider imports are invoked for execution or key loading."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'v1')
    args = parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Offline preflight')), \
         patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('Offline preflight')):
        print(json.dumps(run(args.output)['summary']['workload'],sort_keys=True))


if __name__ == '__main__':
    main()
