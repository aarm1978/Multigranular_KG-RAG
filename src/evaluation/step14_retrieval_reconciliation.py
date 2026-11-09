"""Offline, disk-backed reconciliation of exact Step 14 retrieval nominations."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import socket
import sqlite3
import tempfile
from unittest.mock import patch

from src.evaluation import step14_two_view_retrieval as retrieval

preflight = retrieval.preflight
require = retrieval.require
VERSION = 'step14-retrieval-reconciliation/0.1.0'
PREPARED = retrieval.ROOT/'v2'
RETRIEVED = retrieval.ROOT/'retrieval-v2'
OUTPUT_ROOT = Path('var/study2_step14/retrieval-reconciliation')
OUTPUT = OUTPUT_ROOT/'v1'


def index_members(records, key: str) -> dict:
    """Index exact group membership without inducing pairs or transitive closure."""
    result = defaultdict(set)
    for row in records:
        for oid in row['occurrenceIDs']: result[oid].add(row[key])
    return result


def verify_sources(prepared: Path, retrieved: Path) -> tuple[dict, dict]:
    """Verify recorded hashes and all embedding receipts without executing SDK code."""
    pins = {}
    def check(path: Path, expected: str) -> None:
        """Reuse the native exact-byte verification utility."""
        preflight.pilot.verify(path,expected,pins)
    summary = retrieval.load(retrieved/'summary.json')
    require(summary['version'] == retrieval.VERSION, 'RETRIEVAL_VERSION_DRIFT')
    check(retrieved/'summary.json',retrieval.identity.sha(retrieved/'summary.json'))
    check(prepared/'manifest.json',summary['preparationSha256'])
    manifest = retrieval.load(prepared/'manifest.json')
    require(manifest['version'] == retrieval.VERSION and not manifest['previewOnly'], 'WRONG_PREPARATION')
    require((manifest['model'],manifest['dimensions']) == (retrieval.MODEL,retrieval.DIMENSIONS),'MODEL_DRIFT')
    for path,h in manifest['inputHashes'].items(): check(Path(path),h)
    for name,h in manifest['outputHashes'].items(): check(prepared/name,h)
    for name,h in summary['outputHashes'].items(): check(retrieved/name,h)
    inputs = list(retrieval.rows(prepared/'inputs.jsonl'))
    require(len({r['textSha256'] for r in inputs}) == len(inputs),'DUPLICATE_INPUT')
    require(all(retrieval.digest(r['text']) == r['textSha256'] for r in inputs),'INPUT_HASH_DRIFT')
    batches = list(retrieval.batches(inputs)); receipts = summary['receipts']
    require([r['batch'] for r in receipts] == list(range(len(batches))),'RECEIPT_COVERAGE_DRIFT')
    for receipt,batch in zip(receipts,batches):
        folder = prepared/'embeddings'/f"batch-{receipt['batch']:06d}"
        check(folder/'outcome.json',receipt['outcomeSha256'])
        check(folder/'response.json',receipt['responseSha256'])
        outcome = retrieval.load(folder/'outcome.json')
        require(outcome['status'] == 'completed' and outcome['responseSha256'] == receipt['responseSha256'],'INCOMPLETE_RECEIPT')
        request = dict(model=retrieval.MODEL,dimensions=retrieval.DIMENSIONS,encoding_format='float',input=[r['text'] for r in batch])
        expected = dict(preparationSha256=summary['preparationSha256'],requestSha256=retrieval.candidates.token(request),
                        inputHashes=[r['textSha256'] for r in batch],timeoutSeconds=600,maxRetries=0)
        require(retrieval.load(folder/'intent.json') == expected,'INTENT_BINDING_DRIFT')
        check(folder/'intent.json',retrieval.identity.sha(folder/'intent.json'))
    # Existing preflight pins review, approval and queue authorities. Its saved
    # membership metadata includes oversized blocks without expanding them.
    check(retrieval.PREFLIGHT,retrieval.PREFLIGHT_SHA)
    pm = retrieval.load(retrieval.PREFLIGHT)
    path = retrieval.PREFLIGHT.parent/'occurrence-preflight.jsonl'
    check(path,pm['outputHashes'][path.name])
    qm = retrieval.load(preflight.QUEUE/'manifest.json')
    check(preflight.QUEUE/'block-inventory.jsonl',qm['outputHashes']['block-inventory.jsonl'])
    document = retrieval.load(preflight.approvals.DOCUMENT)
    decisions = list(retrieval.rows(preflight.approvals.APPROVALS))
    preflight.approvals.validate_approvals(document,decisions)
    return summary,pins


def load_occurrences(prepared: Path) -> dict:
    """Keep only eligible endpoint metadata in memory, not nomination populations."""
    reviewed = index_members(retrieval.rows(preflight.PILOT/'review-cases.jsonl'),'caseID')
    approved = index_members(retrieval.rows(preflight.approvals.APPROVALS),'decisionID')
    queued = index_members(retrieval.rows(preflight.QUEUE/'block-inventory.jsonl'),'blockID')
    reserved = index_members(retrieval.rows(preflight.QUEUE/'proposed-sample.jsonl'),'blockID')
    metadata = {}
    for r in retrieval.rows(retrieval.PREFLIGHT.parent/'occurrence-preflight.jsonl'):
        oid = r['occurrenceID']; require(oid not in metadata,'DUPLICATE_PREFLIGHT_OCCURRENCE')
        require(set(r['reviewedCaseIDs']) == reviewed[oid] and set(r['priorApprovalDecisionIDs']) == approved[oid], 'PRIOR_MEMBERSHIP_DRIFT')
        metadata[oid] = dict(originalHash=r['textReference']['recordSha256'],
            reviewed=sorted(reviewed[oid]),approved=sorted(approved[oid]),queued=sorted(queued[oid]),
            reserved=sorted(reserved[oid]),blocks=r['existingBlockIDs'])
    result = {}; seen = set()
    for row in retrieval.rows(prepared/'occurrences.jsonl'):
        oid = row['occurrenceID']; require(oid not in seen,'DUPLICATE_OCCURRENCE'); seen.add(oid)
        require(oid in metadata and row['originalReference']['recordSha256'] == metadata[oid]['originalHash'],'OCCURRENCE_BINDING_DRIFT')
        if row['eligible']:
            result[oid] = row
            result[oid]['priorMemberships'] = metadata[oid]
    require(len(result) == retrieval.load(prepared/'manifest.json')['summary']['eligible'],'ELIGIBLE_COVERAGE_DRIFT')
    return result


def review_status(left: dict, right: dict) -> dict:
    """Only shared explicit membership qualifies; endpoint overlap stays separate."""
    common = {k:sorted(set(left['priorMemberships'][k]) & set(right['priorMemberships'][k]))
              for k in ('approved','reviewed','reserved','queued','blocks')}
    names = dict(approved='same_explicit_approved_subset',reviewed='same_prior_pilot_case',
                 reserved='same_reserved_queue_block',queued='same_existing_queue_block',blocks='same_existing_candidate_block')
    primary = next((names[k] for k in names if common[k]),'new_pair_relative_to_pinned_authorities')
    return dict(primary=primary,sharedMemberships=common,
                endpointMemberships={left['occurrenceID']:left['priorMemberships'],right['occurrenceID']:right['priorMemberships']},
                newPair=primary=='new_pair_relative_to_pinned_authorities')


def validate_nomination(row: dict, occurrences: dict) -> tuple[str,str]:
    """Require exact endpoints, scope, evidence references and both unaltered scores."""
    q,t = row['queryID'],row['targetID']
    require(q in occurrences and t in occurrences and q != t,'MISSING_OR_SELF_ENDPOINT')
    left,right = occurrences[q],occurrences[t]
    require(row['scope'] == retrieval.pair_scope(left,right) and row['ontologyClass'] == left['ontologyClass'],'CLASS_OR_SCOPE_DRIFT')
    for prefix,endpoint in (('query',left),('target',right)):
        require(row[prefix+'Reference'] == endpoint['originalReference'],'REFERENCE_DRIFT')
        require(row[prefix+'TextHashes'] == endpoint['textHashes'],'TEXT_BINDING_DRIFT')
    require(row['identityDecision'] is None and row['automaticMergeEligible'] is False,'UNEXPECTED_IDENTITY_DECISION')
    require(set(row['scores']) == set(retrieval.VIEWS),'VIEW_SCORE_MISSING')
    require(bool(row['nominatedBy']) and len(set(row['nominatedBy'])) == len(row['nominatedBy'])
            and set(row['nominatedBy']) <= set(retrieval.VIEWS),'INVALID_NOMINATION_VIEWS')
    require(all(isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x) and -1.00001 <= x <= 1.00001
                for x in row['scores'].values()),'INVALID_COSINE_SCORE')
    require(row['flags'] == retrieval.pair_flags(left,right),'FLAG_DRIFT')
    return tuple(sorted((q,t)))


def ingest(connection, path: Path, occurrences: dict, expected: dict) -> dict:
    """Stream 1-GB-scale JSONL to a bounded SQLite cache; repeated direction fails."""
    connection.execute('CREATE TABLE nominations(a TEXT,b TEXT,q TEXT,line INTEGER,payload TEXT,linehash TEXT,PRIMARY KEY(a,b,q)) WITHOUT ROWID')
    counts = Counter(); digest = hashlib.sha256()
    with path.open('rb') as source:
        for line,raw in enumerate(source,1):
            digest.update(raw); row = json.loads(raw); a,b = validate_nomination(row,occurrences)
            try:
                connection.execute('INSERT INTO nominations VALUES(?,?,?,?,?,?)',
                                   (a,b,row['queryID'],line,raw.decode(),hashlib.sha256(raw).hexdigest()))
            except sqlite3.IntegrityError as error:
                raise ValueError('DUPLICATE_DIRECTED_NOMINATION') from error
            counts[row['scope']] += 1
            if line % 5000 == 0: connection.commit()
    connection.commit()
    require(digest.hexdigest() == expected['outputHashes']['candidates.jsonl'],'NOMINATION_HASH_DRIFT')
    require(dict(counts) == {s:c['directedNominations'] for s,c in expected['scopes'].items() if c['directedNominations']},'NOMINATION_COUNT_DRIFT')
    return dict(counts)


class Distribution:
    """Constant-memory descriptive moments and fixed cosine histogram; no thresholds."""
    def __init__(self):
        """Start empty descriptive accounting."""
        self.n=0; self.mean=0.; self.m2=0.; self.low=None; self.high=None; self.bins=[0]*20

    def add(self, value: float) -> None:
        """Accumulate exact supplied values; bin only clips floating endpoint roundoff."""
        self.n+=1; delta=value-self.mean; self.mean+=delta/self.n; self.m2+=delta*(value-self.mean)
        self.low=value if self.low is None else min(self.low,value)
        self.high=value if self.high is None else max(self.high,value)
        self.bins[max(0,min(19,int((value+1)*10)))]+=1

    def report(self) -> dict:
        """Return distribution descriptions, never calibrated probabilities."""
        return dict(count=self.n,minimum=self.low,maximum=self.high,mean=self.mean if self.n else None,
                    populationStdDev=math.sqrt(max(0,self.m2/self.n)) if self.n else None,
                    histogramEdges=[round(-1+i/10,1) for i in range(21)],histogramCounts=self.bins)


def challenge(left: dict, right: dict, directions: list[dict]) -> tuple[str,float]:
    """Mechanically prioritize ambiguity without judging semantic identity."""
    flags = set(left['flags']+right['flags'])
    if left['versions'] and right['versions'] and left['versions'] != right['versions']:
        reason='different_structured_version_metadata_requires_scope_review'
    elif any('weak_context' in f or 'multiple_original_labels' in f or 'short_label' in f for f in flags):
        reason='weak_or_ambiguous_literal_context'
    else: reason='two_view_candidate_requires_referent_and_granularity_review'
    gap=max(abs(d['nomination']['scores']['name']-d['nomination']['scores']['evidence']) for d in directions)
    return reason,gap


def compact_endpoint(row: dict) -> dict:
    """Retain bounded selected evidence and hash-bound pointers to full originals."""
    return {k:row[k] for k in ('occurrenceID','ontologyClass','labels','sourceFamilies','sourceArtifacts',
            'versions','granularity','flags','originalReference','selectedEvidence')}


def summarize(connection, occurrences: dict, output: Path, shortlist_size: int) -> dict:
    """Stream unordered pairs, maintain compact strata and deterministic shortlist pools."""
    counts = {k:Counter() for k in ('scope','ontologyClass','sourceFamilyPair','nominationViewOverlap','reviewStatus','directions','challenge')}
    cooccurring = Counter(); directed_views = Counter(); scores = defaultdict(Distribution); pool = defaultdict(dict); total=0; directed=0
    query = connection.execute('SELECT a,b,q,line,payload,linehash FROM nominations ORDER BY a,b,q')
    with (output/'pairs.jsonl').open('xb') as target:
        for (a,b), group in itertools.groupby(query,key=lambda r:(r[0],r[1])):
            directions=[dict(sourceLine=r[3],sourceLineSha256=r[5],nomination=json.loads(r[4])) for r in group]
            require(1 <= len(directions) <= 2,'PAIR_DIRECTION_COUNT')
            left,right=occurrences[a],occurrences[b]; status=review_status(left,right)
            scope=directions[0]['nomination']['scope']; cls=left['ontologyClass']
            family=' | '.join(sorted([left['sourceFamilies'][0],right['sourceFamilies'][0]]))
            views=sorted({v for d in directions for v in d['nomination']['nominatedBy']}); overlap='+'.join(views)
            key=retrieval.candidates.token([a,b]); reason,gap=challenge(left,right,directions)
            pair=dict(pairKeySha256=key,occurrenceIDs=[a,b],scope=scope,ontologyClass=cls,sourceFamilyPair=family,
                directions=directions,nominationViews=views,review=status,challenge=reason,
                maxAbsoluteViewScoreDifference=gap,identityDecision=None,automaticMergeEligible=False)
            target.write(retrieval.identity.encoded(pair)+b'\n'); total+=1;directed+=len(directions)
            for dimension,value in [('scope',scope),('ontologyClass',cls),('sourceFamilyPair',family),
                ('nominationViewOverlap',overlap),('reviewStatus',status['primary']),('directions',str(len(directions))),('challenge',reason)]:
                counts[dimension][value]+=1
            cooccurring.update(k for k,v in status['sharedMemberships'].items() if v)
            directed_views.update('+'.join(sorted(d['nomination']['nominatedBy'])) for d in directions)
            for view in retrieval.VIEWS:
                values=[d['nomination']['scores'][view] for d in directions]
                for value in values: scores['directed|'+view].add(value)
                # Preserve both original values; pair summaries use their arithmetic mean explicitly.
                scores['unordered_pair_mean|'+view].add(sum(values)/len(values))
                scores['unordered_pair_mean|'+scope+'|'+view].add(sum(values)/len(values))
            if status['newPair']:
                stratum=(scope,cls,family,reason)
                rank=retrieval.digest(VERSION+key)
                # Two bounded slots per stratum: stable-hash representative and greatest view disagreement.
                for slot,sort_key in [('representative',(rank,)),('view_disagreement',(-gap,rank))]:
                    current=pool[stratum].get(slot)
                    if current is None or sort_key < current[0]: pool[stratum][slot]=(sort_key,pair)
    candidates={item[1]['pairKeySha256']:item[1] for slots in pool.values() for item in slots.values()}
    chosen=[]; used=Counter(); endpoints=set()
    while candidates and len(chosen)<shortlist_size:
        for scope in retrieval.SCOPES:
            options=[p for p in candidates.values() if p['scope']==scope]
            if not options or len(chosen)>=shortlist_size:continue
            selected=min(options,key=lambda p:(used['class',p['ontologyClass']],used['family',p['sourceFamilyPair']],
                used['challenge',p['challenge']],sum(x in endpoints for x in p['occurrenceIDs']),retrieval.digest(VERSION+p['pairKeySha256'])))
            candidates.pop(selected['pairKeySha256']);used['class',selected['ontologyClass']]+=1
            used['family',selected['sourceFamilyPair']]+=1;used['challenge',selected['challenge']]+=1
            endpoints.update(selected['occurrenceIDs']); selected=dict(selected)
            selected['endpoints']=[compact_endpoint(occurrences[x]) for x in selected['occurrenceIDs']]
            selected['prioritizationReason']='Scope round-robin; class/family/challenge diversity; endpoint reuse avoidance; stable hash tie-break. '+selected['challenge']
            chosen.append(selected)
    retrieval.write(output/'shortlist.json',dict(selection='Post-retrieval purposive diagnostic, not random population evaluation or identity adjudication.',
        maximumPairs=shortlist_size,pairs=chosen))
    return dict(uniqueUnorderedPairs=total,directedNominations=directed,reciprocalPairs=counts['directions']['2'],
        counts={k:dict(sorted(v.items())) for k,v in counts.items()},cooccurringReviewMembershipCounts=dict(cooccurring),
        directedNominationViewCounts=dict(directed_views),
        scoreDistributions={k:v.report() for k,v in sorted(scores.items())},shortlistPairs=len(chosen),
        shortlistByScope={s:sum(p['scope']==s for p in chosen) for s in retrieval.SCOPES},newIdentityDecisions=0,graphWrites=0)


def run(output: Path, shortlist_size: int = 24) -> dict:
    """Verify once, stream to local scratch, export immutable derived reconciliation."""
    require(output.resolve().is_relative_to(OUTPUT_ROOT.resolve()) and not output.exists(),'FRESH_OUTPUT_REQUIRED')
    require(0 < shortlist_size <= 48,'SHORTLIST_SIZE_MUST_BE_1_TO_48')
    source,pins=verify_sources(PREPARED,RETRIEVED); occurrences=load_occurrences(PREPARED)
    contract=Path('docs/study2_step14_retrieval_reconciliation_v0.1.md')
    pins[str(contract)]=retrieval.identity.sha(contract)
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='scratch-',dir=output) as scratch:
        connection=sqlite3.connect(str(Path(scratch)/'nominations.sqlite'))
        try:
            connection.execute('PRAGMA cache_size=-16384');connection.execute('PRAGMA temp_store=FILE')
            directed=ingest(connection,RETRIEVED/'candidates.jsonl',occurrences,source)
            summary=summarize(connection,occurrences,output,shortlist_size)
        finally:connection.close()
    require(summary['directedNominations']==sum(directed.values()),'PAIR_ACCOUNTING_DRIFT')
    # Recheck consumed bytes before writing the completion manifest.
    for path,expected in pins.items():preflight.pilot.verify(Path(path),expected,{})
    summary.update(version=VERSION,verifiedEmbeddingReceipts=len(source['receipts']),directedByScope=directed,
        preparationSha256=source['preparationSha256'],retrievalSummarySha256=pins[str(RETRIEVED/'summary.json')],
        nominationsSha256=pins[str(RETRIEVED/'candidates.jsonl')],
        limitations=['New means no shared explicit membership in the pinned prior authorities, not scientific novelty.',
            'Co-membership in a pilot case is not a pair-specific researcher approval; only shared explicit approved subsets are reported as such.',
            'Scores and nomination-view overlap are descriptive, not calibrated probabilities, accuracy estimates or identity thresholds.',
            'Shortlist is a post-retrieval purposive diagnostic; unresolved ontology/granularity decisions remain unchanged.'])
    retrieval.write(output/'summary.json',summary)
    lines=['# Step 14 retrieval reconciliation — no identity decisions','',
        f"{summary['directedNominations']:,} directed nominations → {summary['uniqueUnorderedPairs']:,} unordered pairs; {summary['reciprocalPairs']:,} reciprocal pairs.",
        f"Verified embedding receipts: {summary['verifiedEmbeddingReceipts']}. Diagnostic shortlist: {summary['shortlistPairs']} pairs.",'']
    for dimension,values in summary['counts'].items():
        lines.extend([f'## {dimension}','','| Value | Unordered pairs |','|---|---:|'])
        lines.extend(f"| {key.replace('|','/')} | {value:,} |" for key,value in values.items());lines.append('')
    lines+=['## Interpretation','',*summary['limitations'],'','See summary.json for descriptive moments and fixed-bin score histograms; shortlist.json for exact evidence pointers and prioritization reasons.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n')
    retrieval.write(output/'manifest.json',dict(version=VERSION,inputHashes=pins,
        implementationSha256=retrieval.identity.sha(Path(__file__)),
        outputHashes={p.name:retrieval.identity.sha(p) for p in sorted(output.iterdir())},providerCalls=0))
    return {k:summary[k] for k in ('directedNominations','uniqueUnorderedPairs','reciprocalPairs','shortlistPairs')}


def main() -> None:
    """Run offline only; never initialize a provider client or generate vectors."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT);parser.add_argument('--shortlist-size',type=int,default=24)
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
        print(json.dumps(run(args.output,args.shortlist_size),sort_keys=True))


if __name__=='__main__':main()
