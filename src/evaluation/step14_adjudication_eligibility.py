"""Offline eligibility alternatives and bounded review-unit packaging; no adjudication."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
from unittest.mock import patch

from src.evaluation import step14_referent_groups as grouping

b = grouping.batch
r = grouping.r
reconciliation = b.reconciliation
require = r.require
ROOT = Path('var/study2_step14/adjudication-eligibility')
GROUPS = grouping.ROOT/'v1'
PRIOR_BATCH = b.ROOT/'v1'
VERSION = 'step14-adjudication-eligibility/0.1.0'
CONTRACT = Path('docs/study2_step14_adjudication_eligibility_v0.1.md')
POLICIES = ('literal', 'context_either', 'context_both')
INSTRUCTION = ('Assess only the explicitly listed pairs independently under the pinned Step 14 identity/granularity policy. '
    'Distinguish entity identity, reference-target coincidence, conceptual similarity, different referents and insufficient evidence. '
    'Preserve class, family/release/implementation/instance distinctions. Missing specificity is uncertainty. '
    'Do not infer identity from names, scores, shared quotations or transitivity; do not extend prior approvals. '
    'Return recommendations only with supporting/conflicting evidence references and uncertainty, never canonical IDs or approvals.')
CRITERIA = dict(version=VERSION, status='proposed_requires_researcher_decision',
    recommendedForDiscussion='context_either', alternatives={
        'literal':'Unapproved original retrieved pair with nonempty literal evidence and provenance at both endpoints.',
        'context_either':'Literal alternative plus at least one endpoint with three distinct non-generic words beyond its label words.',
        'context_both':'Literal alternative plus that mechanical contextual cue at both endpoints; restrictive sensitivity alternative.'},
    rationale='Compare evidence readiness without choosing uncalibrated cosine cutoffs or request quotas. Context cues are not semantic sufficiency judgments.',
    scoreUse='Two-dimensional 0.1-width cosine bins by class and scope; scores never determine identity or eligibility.',
    nominationUse='Original top-k nomination in either view is sufficient; reciprocity and both-view nomination are descriptive signals.',
    holds='Exact approved subset is already covered. Missing literal/provenance is held. Context-only nonselection is deferred, not rejected identity.',
    uncertainty='Version differences, unknown granularity, generic names, weak label binding and shared quotes remain review flags, not identity decisions.',
    units='Direct-key groups are presentation containers only; otherwise exact endpoint-centered stars. Split into at most eight explicit pairs per unit, with no limit on total units.',
    accounting='Only original pairs are eligible; never add leaf-to-leaf pairs, transitive unions or cross-class retrieval.',
    workload='UTF-8 bytes/4 proxy from actual serialized context, plus byte upper bound; not tokenizer-exact, billable usage or a dollar estimate.')


def evidence_features(endpoint: dict) -> dict:
    """Measure literal context availability, not scientific validity."""
    labels = set().union(*(b.words(x) for x in endpoint['labels']))
    fragments = endpoint['selectedEvidence']
    literal = bool(endpoint['sourceArtifacts'] and endpoint['originalReference'] and
                   any(e['literalExcerpt'].strip() for e in fragments))
    contextual = any(len(b.words(e['literalExcerpt'])-labels-b.GENERIC) >= 3 for e in fragments)
    return dict(literal=literal, contextual=contextual,
        weakLabelContext=not any(e['labelPresent'] for e in fragments),
        genericName=not bool(b.name_tokens(endpoint)))


def assess(pair: dict, occurrences: dict, queued: dict | None = None) -> dict:
    """Reconcile exact approvals, retain single-view paths and expose ambiguity."""
    left, right = (occurrences[x] for x in pair['occurrenceIDs'])
    require(left['ontologyClass'] == right['ontologyClass'] == pair['ontologyClass'], 'CLASS_BINDING_DRIFT')
    review = reconciliation.review_status(left, right)
    require(review == pair['review'], 'PRIOR_DECISION_DRIFT')
    features = [evidence_features(x) for x in (left, right)]
    approved = bool(review['sharedMemberships']['approved'])
    literal = all(x['literal'] for x in features)
    contextual = sum(x['contextual'] for x in features)
    eligibility = dict(literal=not approved and literal,
        context_either=not approved and literal and contextual >= 1,
        context_both=not approved and literal and contextual == 2)
    flags = []
    if any(x['weakLabelContext'] for x in features): flags.append('weak_label_context')
    if any(x['genericName'] for x in features): flags.append('generic_name_collision_risk')
    if left['versions'] != right['versions']: flags.append('version_metadata_differs_or_missing')
    if left['granularity'] != right['granularity']: flags.append('granularity_metadata_differs')
    if any(any(w in x['granularity'].lower() for w in ('unspecified','unknown','unresolved')) for x in (left,right)):
        flags.append('granularity_unresolved')
    if {e['fullQuoteSha256'] for e in left['selectedEvidence']} & {e['fullQuoteSha256'] for e in right['selectedEvidence']}:
        flags.append('shared_quote_not_independent_confirmation')
    scores = {v:sum(d['nomination']['scores'][v] for d in pair['directions'])/len(pair['directions']) for v in r.VIEWS}
    pathway = '+'.join(sorted(pair['nominationViews']))
    queued_case = (queued or {}).get(pair['pairKeySha256'])
    if queued_case:
        require(queued_case['occurrenceIDs'] == pair['occurrenceIDs'], 'QUEUED_PAIR_DRIFT')
    prior_status = ('previous_evidence_batch_unresolved' if queued_case and review['newPair'] else review['primary'])
    return dict(eligible=eligibility, priorStatus=prior_status, originalReconciliationStatus=review['primary'],
        previousEvidenceBatchCase=queued_case, approvedSubsetIDs=review['sharedMemberships']['approved'],
        previousUnresolved=not approved and (not review['newPair'] or bool(queued_case)),
        newRelativeToAuthorities=review['newPair'] and not bool(queued_case),
        flags=flags, contextualEndpoints=contextual, scores=scores, pathway=pathway,
        reciprocal=len(pair['directions']) == 2,
        directedViewSignals=[dict(queryID=d['nomination']['queryID'], targetID=d['nomination']['targetID'],
            nominatedBy=d['nomination']['nominatedBy'], scores=d['nomination']['scores']) for d in pair['directions']],
        reasons={p:('already_exactly_approved' if approved else 'missing_literal_or_provenance' if not literal else
                    'eligible_proposal' if eligibility[p] else 'thin_context_deferred_not_rejected') for p in POLICIES})


def bin_score(value: float) -> int:
    """Place cosine in descriptive joint bins, without changing original values."""
    return min(19, max(0, int((value+1)*10)))


def unit_key(ids: list[str], index: dict, groups: dict) -> str:
    """Choose one existing direct group or a star center; never union memberships."""
    common = index.get(ids[0], set()) & index.get(ids[1], set())
    if common:
        bid = min(common, key=lambda x:(len(groups[x]['occurrenceIDs']), x))
        return 'direct:'+bid
    return 'center:'+min(ids)


def context_payload(pairs: list, endpoints: dict, approvals: dict) -> dict:
    """Build the actual proposed review context, including only explicit pairs."""
    ids = sorted({x for pair in pairs for x in pair['occurrenceIDs']})
    decisions = sorted({d for oid in ids for d in endpoints[oid]['priorMemberships']['approved']})
    return dict(instructions=INSTRUCTION, pairs=pairs, occurrences=[endpoints[x] for x in ids],
                originalApprovalRecords=[approvals[x] for x in decisions],
                identityDecisionsAuthorized=False)


def emit_units(db: sqlite3.Connection, output: Path, endpoints: dict, approvals: dict) -> dict:
    """Stream bounded contexts, storing references once and counting actual payload bytes."""
    stats = {}
    with (output/'review-units.jsonl').open('x') as stream:
        for policy in POLICIES:
            units = total = pair_count = baseline = maximum = 0
            pending = []; current = None
            def flush() -> None:
                """Persist one bounded explicit-pair unit, not an identity group."""
                nonlocal units, total, maximum
                if not pending: return
                payload = context_payload(pending, endpoints, approvals)
                size = len(r.identity.encoded(payload)); total += size; maximum = max(maximum, size); units += 1
                row = dict(policy=policy, container=current, pairs=list(pending),
                    occurrenceIDs=sorted({x for p in pending for x in p['occurrenceIDs']}),
                    contextSha256=r.candidates.token(payload), contextUTF8Bytes=size,
                    unitID=r.candidates.token([policy,current,[p['pairKeySha256'] for p in pending]]),
                    contextRecipe='instructions in criteria.json; exact occurrences in contexts.jsonl; prior-decisions.jsonl; pairs here')
                stream.write(r.identity.encoded(row).decode()+'\n')
            for container, data in db.execute(f'SELECT container, detail FROM pairs WHERE {policy}=1 ORDER BY container, pairkey'):
                pair = json.loads(data)
                if current != container or len(pending) == 8:
                    flush(); pending = []
                current = container; pending.append(pair); pair_count += 1
                baseline += len(r.identity.encoded(context_payload([pair],endpoints,approvals)))
            flush()
            stats[policy] = dict(eligiblePairs=pair_count, ungroupedRequests=pair_count, proposedReviewUnits=units,
                actualContextUTF8Bytes=total, approximateInputTokens=(total+3)//4,
                utf8ByteTokenUpperBound=total, maximumUnitBytes=maximum,
                pairwiseContextUTF8Bytes=baseline, pairwiseApproximateInputTokens=(baseline+3)//4,
                requestsSavedByPackaging=pair_count-units)
    return stats


def run(output: Path) -> dict:
    """Verify pinned inputs, stream all original pairs, and write a fresh offline analysis."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(), 'FRESH_OUTPUT_REQUIRED')
    manifest = r.load(GROUPS/'manifest.json'); pins = dict(manifest['inputHashes'])
    for name,h in manifest['outputHashes'].items(): pins[str(GROUPS/name)] = h
    for path in (GROUPS/'manifest.json',CONTRACT,Path(__file__)):
        pins.setdefault(str(path),r.identity.sha(path))
    for path,h in pins.items(): r.preflight.pilot.verify(Path(path),h,{})
    queued = {}
    qm = r.load(PRIOR_BATCH/'manifest.json')
    require(qm['implementationSha256'] == r.identity.sha(Path(b.__file__)), 'REVIEW_BATCH_IMPLEMENTATION_DRIFT')
    for path,h in qm['inputHashes'].items():
        require(path not in pins or pins[path] == h, 'AUTHORITY_PIN_CONFLICT')
        pins[path] = h
    for name,h in qm['outputHashes'].items(): pins[str(PRIOR_BATCH/name)] = h
    pins[str(PRIOR_BATCH/'manifest.json')] = r.identity.sha(PRIOR_BATCH/'manifest.json')
    for path,h in pins.items(): r.preflight.pilot.verify(Path(path),h,{})
    for case in r.load(PRIOR_BATCH/'cases.json')['cases']:
        require(case['identityDecision'] is None and not case['automaticMergeEligible'], 'UNEXPECTED_QUEUE_DECISION')
        key = r.candidates.token(case['occurrenceIDs'])
        require(key == case['pairKeySha256'] and key not in queued, 'QUEUED_PAIR_DRIFT')
        queued[key] = dict(caseID=case['caseID'],occurrenceIDs=case['occurrenceIDs'],
            file=str(PRIOR_BATCH/'cases.json'),recordSha256=r.candidates.token(case),status='unresolved_queue_not_approval')
    occurrences = reconciliation.load_occurrences(reconciliation.PREPARED)
    approval_rows = list(r.rows(r.preflight.approvals.APPROVALS))
    r.preflight.approvals.validate_approvals(r.load(r.preflight.approvals.DOCUMENT),approval_rows)
    require(len(approval_rows)==29 and sum(len(x['occurrenceIDs']) for x in approval_rows)==99, 'APPROVAL_CHECKPOINT_DRIFT')
    approvals = {x['decisionID']:x for x in approval_rows}
    endpoints = b.enrich([dict(occurrenceIDs=list(occurrences))], occurrences)
    for oid,row in endpoints.items(): row['priorMemberships'] = occurrences[oid]['priorMemberships']
    groups = {}; index = defaultdict(set)
    for group in r.rows(GROUPS/'groups.jsonl'):
        bid = group['proposalID']; require(bid not in groups,'DUPLICATE_GROUP')
        require(r.candidates.token(group['occurrenceIDs'])==group['originalBlock']['membershipSha256'],'GROUP_MEMBERSHIP_DRIFT')
        groups[bid] = group
        for oid in group['occurrenceIDs']: index[oid].add(bid)
    output.mkdir(parents=True)
    db = sqlite3.connect(output/'accounting.sqlite')
    db.execute('PRAGMA cache_size=-16384'); db.execute('PRAGMA temp_store=FILE')
    db.execute('CREATE TABLE pairs(pairkey TEXT PRIMARY KEY, container TEXT, literal INT, context_either INT, context_both INT, detail TEXT)')
    counters = Counter(); outcomes = Counter(); strata = Counter(); joint = Counter(); selected_joint = Counter(); flags = Counter(); examples = {}
    digest = hashlib.sha256(); previous = None
    with (b.SOURCE/'pairs.jsonl').open('rb') as source:
        offset = 0
        for line,raw in enumerate(source,1):
            digest.update(raw); pair = json.loads(raw); ids = pair['occurrenceIDs']
            require(ids==sorted(set(ids)) and len(ids)==2 and all(x in occurrences for x in ids), 'PAIR_ID_DRIFT')
            require(previous is None or tuple(ids)>previous,'PAIR_ORDER_DRIFT'); previous = tuple(ids)
            require(pair['pairKeySha256']==r.candidates.token(ids),'PAIR_HASH_DRIFT')
            for direction in pair['directions']: reconciliation.validate_nomination(direction['nomination'],occurrences)
            a = assess(pair,occurrences,queued); counters['originalPairs'] += 1
            counters[a['priorStatus']] += 1
            counters['reciprocalPairs'] += int(a['reciprocal'])
            for signal in a['directedViewSignals']:
                counters['directedNominationViews:'+ '+'.join(sorted(signal['nominatedBy']))] += 1
            if a['previousUnresolved']: counters['previouslyIdentifiedUnresolved'] += 1
            if a['newRelativeToAuthorities']: counters['newRelativeToAuthorities'] += 1
            for flag in a['flags']: flags[flag] += 1
            joint[(pair['ontologyClass'],pair['scope'],bin_score(a['scores']['name']),bin_score(a['scores']['evidence']),a['pathway'])] += 1
            for policy in POLICIES:
                outcomes[(policy,a['reasons'][policy])] += 1
                strata[(policy,pair['ontologyClass'],pair['scope'],pair['sourceFamilyPair'],a['pathway'],a['priorStatus'],str(a['eligible'][policy]))] += 1
                if a['eligible'][policy]:
                    counters[policy+(':new' if a['newRelativeToAuthorities'] else ':previously_identified_unresolved')] += 1
                    selected_joint[(policy,pair['ontologyClass'],pair['scope'],bin_score(a['scores']['name']),bin_score(a['scores']['evidence']))] += 1
            ref = dict(file=str(b.SOURCE/'pairs.jsonl'),line=line,byteOffset=offset,byteLength=len(raw),rawLineSha256=hashlib.sha256(raw).hexdigest())
            offset += len(raw)
            detail = dict(pairKeySha256=pair['pairKeySha256'],occurrenceIDs=ids, originalReference=ref,
                scope=pair['scope'],ontologyClass=pair['ontologyClass'],sourceFamilyPair=pair['sourceFamilyPair'],
                assessment=a, originalPriorReview=pair['review'])
            db.execute('INSERT INTO pairs VALUES(?,?,?,?,?,?)',(pair['pairKeySha256'],unit_key(ids,index,groups),
                *(int(a['eligible'][p]) for p in POLICIES),json.dumps(detail,sort_keys=True)))
            # Deterministic small examples across pathways and ambiguity, not an accuracy sample.
            categories = ['pathway:'+a['pathway']]+a['flags']+[a['reasons']['context_either']]
            if len(set(a['eligible'].values())) > 1:
                categories.append('alternative_disagreement:'+','.join(p for p in POLICIES if a['eligible'][p]))
            for category in categories:
                key=(pair['scope'],category)
                if key not in examples or detail['pairKeySha256']<examples[key]['pairKeySha256']:examples[key]=detail
            if line%5000==0:db.commit()
    db.commit()
    expected=r.load(b.SOURCE/'summary.json')
    require(counters['originalPairs']==expected['uniqueUnorderedPairs']==512024,'PAIR_COUNT_DRIFT')
    rm=r.load(b.SOURCE/'manifest.json')
    require(digest.hexdigest()==rm['outputHashes']['pairs.jsonl'],'PAIR_FILE_HASH_DRIFT')
    for policy in POLICIES:require(sum(n for (p,_),n in outcomes.items() if p==policy)==counters['originalPairs'],'ACCOUNTING_DRIFT')
    workload=emit_units(db,output,endpoints,approvals); db.close()
    for name,rows in [('contexts.jsonl',endpoints.values()),('prior-decisions.jsonl',approval_rows)]:
        with (output/name).open('x') as stream:
            for row in rows:stream.write(r.identity.encoded(row).decode()+'\n')
    chosen=[]
    for key in sorted(examples):
        item=examples[key]
        chosen.append(dict(stratum=key,pair=item,endpoints=[endpoints[x] for x in item['occurrenceIDs']],
            interpretation='Diagnostic risk signal, not an identity judgment. Shared names/quotes may compare distinct entities; absent lexical overlap or weak windows may conceal equivalence.'))
    r.write(output/'examples.json',dict(version=VERSION,examples=chosen))
    r.write(output/'criteria.json',dict(CRITERIA,contextInstructions=INSTRUCTION))
    r.write(output/'distributions.json',dict(jointBinWidth=.1,jointBinOrigin=-1,
        jointByClassScopeView=[dict(ontologyClass=k[0],scope=k[1],nameBin=k[2],evidenceBin=k[3],nominationPathway=k[4],count=v) for k,v in sorted(joint.items())],
        selectedJointByPolicy=[dict(policy=k[0],ontologyClass=k[1],scope=k[2],nameBin=k[3],evidenceBin=k[4],count=v) for k,v in sorted(selected_joint.items())],
        eligibilityStrata=[dict(policy=k[0],ontologyClass=k[1],scope=k[2],familyPair=k[3],pathway=k[4],priorStatus=k[5],eligible=k[6]=='True',count=v) for k,v in sorted(strata.items())]))
    summary=dict(version=VERSION,status='proposal_awaiting_researcher_criteria_decision',counts=dict(counters),
        approvalSubsets=29,approvalOccurrenceMemberships=99,previousEvidenceBatchCases=len(queued),approvalRecordsSha256=r.identity.sha(r.preflight.approvals.APPROVALS),
        outcomes={p:{reason:n for (policy,reason),n in outcomes.items() if policy==p} for p in POLICIES},
        workload=workload,flags=dict(flags),providerCalls=0,identityDecisions=0,
        limitations=['Exact-class blocking is inherited from retrieval; no new cross-class discovery.',
            'No score cutoff is scientifically calibrated; alternatives measure mechanical evidence readiness only.',
            'Context word count is a transparent proposed heuristic, not demonstrated semantic sufficiency.',
            'Generic names, release/instance ambiguity and comparison quotations can produce false positives.',
            'Truncated selected windows and lexical screening can conceal equivalence; nonselection is not rejection.',
            'Eight-pair packaging is a presentation bound, not a population quota; overlapping groups never imply transitivity.',
            'Token estimates use actual serialized draft contexts, not final provider envelopes or billing tokenization.'])
    r.write(output/'summary.json',summary)
    text=['# Step 14 eligibility alternatives (not approved)','',
          f"Original pairs: {counters['originalPairs']}; approved subsets: 29 / 99 occurrence memberships.",'',
          '| Alternative | Eligible pairs | Review units | Approximate input tokens |','|---|---:|---:|---:|']
    for p,w in workload.items():text.append(f"| {p} | {w['eligiblePairs']} | {w['proposedReviewUnits']} | {w['approximateInputTokens']} |")
    text+=['','Proposed discussion starting point: context_either. The researcher must select criteria; no dispatch is authorized.',
           'literal preserves thin-context opportunities at higher review burden; context_both can miss name-only/evidence-only equivalents.',
           'Inspect distributions.json for joint scores and class/scope/family imbalance; examples.json exposes ambiguity rather than adjudicating it.','',*summary['limitations']]
    (output/'summary.md').write_text('\n'.join(text)+'\n')
    for path,h in pins.items():r.preflight.pilot.verify(Path(path),h,{})
    r.write(output/'manifest.json',dict(version=VERSION,inputHashes=pins,
        outputHashes={p.name:r.identity.sha(p) for p in sorted(output.iterdir())},providerCalls=0))
    return summary


def main() -> None:
    """Run without network access; existing output directories are immutable."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'v1')
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')), patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        print(json.dumps(run(args.output),sort_keys=True))


if __name__=='__main__':main()
