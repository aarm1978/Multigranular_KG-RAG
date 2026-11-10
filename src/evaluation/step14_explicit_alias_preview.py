"""Read-only explicit-alias complement to the immutable v2 eligibility baseline."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import socket
import sqlite3
import unicodedata
from unittest.mock import patch

from src.evaluation import step14_adjudication_eligibility as baseline

r = baseline.r
require = r.require
SOURCE = baseline.ROOT/'v2'
ROOT = Path('var/study2_step14/explicit-alias-preview')
VERSION = 'step14-explicit-alias-preview/0.1.0'
CONTRACT = Path('docs/study2_step14_explicit_alias_preview_v0.1.md')
QUALIFIERS = {'framework','software','package','library','tool','model','algorithm','workflow','implementation'}


def canonical(text: str) -> str:
    """Compare formatting only; never replace original labels or allocate identities."""
    return ''.join(c for c in unicodedata.normalize('NFKC',text).casefold() if c.isalnum())


def versions(text: str) -> tuple:
    """Keep numeric distinctions when punctuation normalization would erase them."""
    return tuple(re.findall(r'\d+(?:\.\d+)*',text))


def distinctive(text: str) -> bool:
    """Reject generic-only names; not a claim that a remaining name is unique."""
    return bool(baseline.b.name_tokens(dict(labels=[text])) - QUALIFIERS)


def forms(label: str) -> list[tuple[str,str]]:
    """Return only whole-name forms or explicitly parenthesized aliases."""
    result=[(label,'whole_name')]
    match=re.fullmatch(r'\s*(.+?)\s*\(([A-Za-z][A-Za-z0-9._-]{1,19})\)\s*',label)
    if match and distinctive(match[1]):
        result.extend([(match[1],'parenthetical_expansion'),(match[2],'parenthetical_acronym')])
    return result


def alias_cue(left: str, right: str) -> dict | None:
    """Nominate explicit literal variants, never substring/token-overlap equivalence."""
    if not distinctive(left) or not distinctive(right):return None
    if versions(left) != versions(right):return None
    for a,ar in forms(left):
        for b,br in forms(right):
            if canonical(a)==canonical(b) and len(canonical(a))>=3:
                return dict(kind='format_variant' if ar==br=='whole_name' else 'explicit_parenthetical',
                            leftLabel=left,rightLabel=right,matchedLiteralForms=[a,b])
    for short,long in ((left,right),(right,left)):
        # Full base must match; a shared token in two different referents is insufficient.
        words=long.split()
        while words and words[-1].casefold().strip('.,:;') in QUALIFIERS:
            words.pop()
            base=' '.join(words)
            if distinctive(base) and canonical(base)==canonical(short):
                return dict(kind='base_with_descriptive_qualifier',leftLabel=left,rightLabel=right,
                            matchedLiteralForms=[short,base])
    return None


def grounded_name(label: str, quote: str) -> bool:
    """Require whole-name boundaries while tolerating only presentation separators."""
    name=canonical(label)
    pattern=r'(?<!\w)'+r'[\W_]*'.join(re.escape(c) for c in name)+r'(?!\w)'
    return bool(name and re.search(pattern,unicodedata.normalize('NFKC',quote).casefold()))


def nominate(left: dict, right: dict) -> dict:
    """Require exact class and source-bound literal names, flag thin evidence and specificity."""
    require(left['ontologyClass']==right['ontologyClass'],'CLASS_DRIFT')
    flags=[]
    if left['versions'] != right['versions']:flags.append('version_metadata_differs_or_missing')
    if left['granularity'] != right['granularity']:flags.append('granularity_metadata_differs')
    if any(not baseline.evidence_features(x)['contextual'] for x in (left,right)):flags.append('thin_context_requires_review')
    if any(any(t in x['granularity'].lower() for t in ('unknown','unresolved','unspecified')) for x in (left,right)):
        flags.append('granularity_unresolved')
    for a in left['labels']:
        for b in right['labels']:
            cue=alias_cue(a,b)
            if not cue:continue
            grounded=[]
            for row,label in ((left,a),(right,b)):
                grounded.append(baseline.evidence_features(row)['literal'] and any(
                    grounded_name(label,e['literalExcerpt']) for e in row['selectedEvidence']))
            if all(grounded):
                return dict(nominated=True,cue=cue,flags=flags,
                    reason='explicit_literal_alias_candidate_not_identity',identityDecision=None)
    return dict(nominated=False,cue=None,flags=flags,reason='no_source_bound_explicit_alias',identityDecision=None)


def control_failures(assessment: dict) -> list[str]:
    """Describe co-occurring failures of the baseline without using approval as a feature."""
    sig=assessment['selectionSignals'];scores=assessment['scores']; reasons=[]
    if not sig['contextualBoth']:reasons.append('context_gate')
    if not sig['reciprocal'] and not(sig['distinctiveSharedTokens'] or sig['sharedLiteralReferences']):reasons.append('corroboration_gate')
    if not(scores['name']>=.85 and scores['evidence']>=.80) and max(scores.values())<.95:reasons.append('score_gate')
    return reasons


def inspect_row(detail: dict, occurrences: dict, selected: bool) -> dict:
    """Keep exact approval exclusion separate from counterfactual positive-control coverage."""
    ids=detail['occurrenceIDs'];a=detail['assessment']
    require(detail['pairKeySha256']==r.candidates.token(ids),'PAIR_HASH_DRIFT')
    left,right=(occurrences[x] for x in ids)
    require(detail['ontologyClass']==left['ontologyClass'] and detail['scope']==r.pair_scope(left,right),'CLASS_OR_SCOPE_DRIFT')
    review=baseline.reconciliation.review_status(left,right)
    require(review==detail['originalPriorReview'],'PRIOR_REVIEW_DRIFT')
    approved=bool(review['sharedMemberships']['approved'])
    require(not approved or not selected,'APPROVED_PAIR_RESUBMISSION')
    require(bool(selected)==bool(a['eligible']['alias_extended']),'BASELINE_SELECTION_DRIFT')
    result=nominate(left,right)
    raw_baseline=bool(a['selectionSignals']['dual'] or a['selectionSignals']['exceptionalSingle'])
    return dict(pairKeySha256=detail['pairKeySha256'],occurrenceIDs=ids,
        ontologyClass=detail['ontologyClass'],scope=detail['scope'],familyPair=detail['sourceFamilyPair'],
        priorStatus=a['priorStatus'],originalReference=detail['originalReference'],
        approvedSubsetIDs=review['sharedMemberships']['approved'],baselineEligible=bool(selected),
        incrementalEligible=not approved and not selected and result['nominated'],
        combinedEligible=not approved and (bool(selected) or result['nominated']),
        alias=result,controlBaselinePass=raw_baseline,controlFailureReasons=control_failures(a) if approved and not raw_baseline else [])


def run(output: Path) -> dict:
    """Stream existing read-only accounting; write only compact differences and diagnostics."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(),'FRESH_OUTPUT_REQUIRED')
    manifest=r.load(SOURCE/'manifest.json');pins=dict(manifest['inputHashes'])
    # Verify only consumed v2 outputs, never read/copy the large review context files.
    for name in ('accounting.sqlite','summary.json','criteria.json'):
        pins[str(SOURCE/name)]=manifest['outputHashes'][name]
    for path in (SOURCE/'manifest.json',CONTRACT,Path(__file__)):
        pins.setdefault(str(path),r.identity.sha(path))
    for path,h in pins.items():r.preflight.pilot.verify(Path(path),h,{})
    occurrences=baseline.reconciliation.load_occurrences(baseline.reconciliation.PREPARED)
    approvals=list(r.rows(r.preflight.approvals.APPROVALS))
    r.preflight.approvals.validate_approvals(r.load(r.preflight.approvals.DOCUMENT),approvals)
    require(len(approvals)==29 and sum(len(x['occurrenceIDs']) for x in approvals)==99,'APPROVAL_CHECKPOINT_DRIFT')
    # Exact evidence/offset verification reuses the existing bounded occurrence reader.
    endpoints=baseline.b.enrich([dict(occurrenceIDs=list(occurrences))],occurrences)
    output.mkdir(parents=True)
    counts=Counter();strata=Counter();reasons=Counter();prior_counts=Counter();controls=[];examples={}
    database=SOURCE/'accounting.sqlite'
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db, (output/'incremental-pairs.jsonl').open('x') as stream:
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA cache_size=-16384')
        for key,selected,data in db.execute('SELECT pairkey,alias_extended,detail FROM pairs ORDER BY pairkey'):
            detail=json.loads(data)
            require(key==detail['pairKeySha256'],'ACCOUNTING_KEY_DRIFT')
            row=inspect_row(detail,occurrences,selected)
            counts['originalPairs']+=1
            counts['baselineEligible']+=int(row['baselineEligible'])
            counts['incrementalEligible']+=int(row['incrementalEligible'])
            counts['combinedEligible']+=int(row['combinedEligible'])
            if row['incrementalEligible']:
                strata[(row['ontologyClass'],row['scope'],row['familyPair'])]+=1
                prior_counts[row['priorStatus']]+=1
                stream.write(r.identity.encoded(row).decode()+'\n')
            if row['approvedSubsetIDs']:
                counts['approvedControlPairs']+=1
                counts['controlsBaselinePass']+=int(row['controlBaselinePass'])
                counts['controlsAliasNominated']+=int(row['alias']['nominated'])
                if not row['controlBaselinePass']:
                    reasons.update(row['controlFailureReasons']);controls.append(row)
            category=('incremental:'+row['alias']['cue']['kind'] if row['incrementalEligible'] else
                      'approved_baseline_miss' if row['controlFailureReasons'] else 'nonselected')
            for key in [(category,row['scope'])]+[(flag,row['scope']) for flag in row['alias']['flags'] if row['alias']['nominated']]:
                if key not in examples:examples[key]=row
    require(counts['originalPairs']==512024 and counts['approvedControlPairs']==250,'PAIR_CHECKPOINT_DRIFT')
    saved=r.load(SOURCE/'summary.json')
    require(counts['baselineEligible']==saved['workload']['alias_extended']['eligiblePairs'],'BASELINE_COUNT_DRIFT')
    counts['unselectedUnresolved']=counts['originalPairs']-counts['approvedControlPairs']-counts['combinedEligible']
    def enriched(row: dict) -> dict:
        """Attach bounded authentic evidence and references only for diagnostic examples."""
        return dict(row,endpoints=[endpoints[x] for x in row['occurrenceIDs']])
    r.write(output/'controls.json',dict(baselineMisses=[enriched(x) for x in controls],failureReasons=dict(reasons),
        caveat='Previously approved positive controls, not representative gold or fitted optimization targets. Approved pairs remain excluded.'))
    r.write(output/'examples.json',dict(cases=[dict(stratum=k,**enriched(v)) for k,v in sorted(examples.items())]))
    summary=dict(version=VERSION,baseline='alias_extended (unapproved comparison policy)',counts=dict(counts),
        controlFailureReasons=dict(reasons),incrementalByPriorStatus=dict(prior_counts),incrementalByClassScopeFamily=[dict(ontologyClass=k[0],scope=k[1],familyPair=k[2],count=n) for k,n in sorted(strata.items())],
        approvalsPreserved=dict(subsets=29,memberships=99),providerCalls=0,identityDecisions=0,
        limitations=['Alias normalization nominates only; same names/acronyms can refer to different implementations.',
            'Only explicit parenthetical aliases are read; no acronym expansions are invented.',
            'Numeric label distinctions are preserved; different releases are not format aliases.',
            'Structured version differences remain visible review flags, not erased or interpreted as nonidentity.',
            'A name must be literal in selected evidence at both endpoints; omitted windows can hide real aliases.',
            'Approved controls are retrospective and nonrepresentative; their recovery is not population accuracy.'])
    r.write(output/'summary.json',summary)
    (output/'summary.md').write_text('# Explicit alias complement (proposal only)\n\n'+json.dumps(dict(counts),indent=2)+
        '\n\nBaseline control failure reasons (overlapping): '+json.dumps(dict(reasons))+ '\n\n'+'\n'.join(summary['limitations'])+'\n')
    for path,h in pins.items():r.preflight.pilot.verify(Path(path),h,{})
    r.write(output/'manifest.json',dict(version=VERSION,inputHashes=pins,outputHashes={p.name:r.identity.sha(p) for p in sorted(output.iterdir())},providerCalls=0))
    return summary


def main() -> None:
    """Run offline with a fresh diagnostic directory; never dispatch a provider request."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'v1')
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        print(json.dumps(run(args.output),sort_keys=True))


if __name__=='__main__':main()
