"""Offline corrected validation view; frozen v6 authority and v1 decisions stay intact."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch
from src.evaluation import source_local_supplemental_review as old

require,digest,canonical=old.require,old.digest,old.canonical
OUTPUT=Path('var/study2_step13/source-local-supplemental-review/v2')
BASELINE='9679b8dcb1b29be622b781439932b8003285a133'
CHANGED=('src/extraction/llm/source_local_semantics.py','src/extraction/llm/source_local_specialized.py')
POLICY='source-local-derived-validation/0.4.3'


class RegressionStop(BaseException):
    """Stop the review instead of converting a changed historical decision into a failure."""


def load_frozen(repo):
    """Authenticate historical code through Git only for the two explicitly corrected files."""
    root=repo/old.retry.QUEUE;raw=(root/'queue-manifest.json').read_bytes()
    require(digest(raw)==old.retry.QUEUE_SHA,'QUEUE_DRIFT');queue=json.loads(raw)
    for path,sha in {**queue['inputPins'],**queue['implementationPins']}.items():
        raw=(subprocess.check_output(['git','show',BASELINE+':'+path],cwd=repo)
             if path in CHANGED else (repo/path).read_bytes())
        require(digest(raw)==sha,'FROZEN_AUTHORITY_DRIFT:'+path)
    bundles={};lines=[]
    for e in queue['requests']:
        raw=(root/'queue'/e['bundleFile']).read_bytes();require(digest(raw)==e['bundleSha256'],'BUNDLE_DRIFT')
        p=json.loads(raw);rid=e['identity']['requestID']
        require(rid not in bundles and old.retry.adapter.fingerprint(p)==e['identity'],'REQUEST_IDENTITY_DRIFT')
        old.semantic.verify(p);bundles[rid]=p
        item,line=old.retry.adapter.batch.input_line(p,1,old.retry.adapter.fingerprint)
        require(item==e['batchItem'],'BATCH_ITEM_DRIFT');lines.append(line)
    raw=(root/'batch-input.jsonl').read_bytes()
    require(raw==b''.join(lines) and digest(raw)==queue['batchInputSha256'],'BATCH_INPUT_DRIFT')
    return queue,bundles


def checked(path):
    """Verify a previously saved report without regenerating it with new rules."""
    r=json.loads(path.read_bytes())
    require(r['reportSha256']==digest(canonical({k:v for k,v in r.items() if k!='reportSha256'})), 'SAVED_REPORT_DRIFT')
    return r


def supplement(repo, prepared):
    """Reuse v1 supplemental verification against its authenticated historical replay."""
    saved=checked(repo/old.retry.OUTPUT/'semantic-replay.json')
    require(saved['requestID']==old.retry.REQUEST_ID and saved['responseSha256']==
            digest(bytes.fromhex(saved['responseBytesHex'])),'SUPPLEMENT_REPLAY_BINDING_DRIFT')
    # old.load_supplement still verifies all intent, response and outcome fields/hashes.
    # Its historical replay equality check uses the authenticated saved v1 report;
    # every selected response, including this one, is replayed under the new policy below.
    with patch.object(old.retry,'validate_response',return_value=saved):
        return old.load_supplement(repo,prepared)


def assert_same_decisions(prior, current):
    """Compare complete candidate decisions and projections, not just aggregate counts."""
    a=prior['nativeValidationView'];b=current['nativeValidationView']
    for key in ('decisions','projection','unresolvedAssertions','derivedConstructionInput'):
        if a[key]!=b[key]:raise RegressionStop('UNEXPECTED_REGRESSION:'+prior['requestID']+':'+key)
    if prior['abstentions']!=current['abstentions'] or current['quarantinedAbstentions']:
        raise RegressionStop('UNEXPECTED_ABSTENTION_REGRESSION:'+prior['requestID'])


def run(repo=old.retry.ROOT):
    """Validate all 1005 selected responses and require all 997 v1 successes unchanged."""
    dest=repo/OUTPUT;require(not dest.exists(),'OUTPUT_ALREADY_EXISTS')
    queue,bundles=load_frozen(repo)
    receipts,head=old.read_original(repo,bundles)
    response,supp_hashes=supplement(repo,bundles[old.retry.REQUEST_ID])
    selected=old.select(queue['requests'],receipts,response)
    baseline=json.loads((repo/old.OUTPUT/'summary.json').read_bytes())
    failed={f['requestID'] for f in baseline['validationFailures']}
    require(len(failed)==8 and baseline['counts']['successfulValidations']==997,'BASELINE_COUNTS_DRIFT')
    prior_files={p.stem:p for p in (repo/old.OUTPUT/'groups').glob('*.json')}
    require(set(prior_files)=={digest(r.encode()) for r in bundles if r not in failed},'BASELINE_GROUP_COVERAGE_DRIFT')
    original_validate=old.retry.validate_response;compared=set();quarantine=[]
    def validate(prepared, body):
        """Run normal replay and enforce the v1 regression gate for every prior success."""
        rid=prepared['request']['requestID']
        try:report=original_validate(prepared,body)
        except Exception as exc:
            if rid not in failed:raise RegressionStop('PREVIOUS_SUCCESS_NOW_FAILS:'+rid) from exc
            raise
        if rid not in failed:
            prior=checked(prior_files[digest(rid.encode())])
            require(prior['responseSha256']==report['responseSha256'],'AUTHENTIC_RESPONSE_DRIFT')
            assert_same_decisions(prior,report);compared.add(rid)
        quarantine.extend(report['quarantinedAbstentions'])
        return report
    with patch.object(old.retry,'validate_response',side_effect=validate):
        summary=old.derive(queue['requests'],bundles,selected,dest)
    require(len(compared)==997,'INCOMPLETE_REGRESSION_CHECK')
    # The original 14 candidate-bearing zero-yield Hub owners must retain their held decisions.
    diagnostic=json.loads((repo/Path('var/study2_step13/source-local-review-diagnostic/v1/diagnostic.json')).read_bytes())
    held_owners=[r['ownerID'] for r in diagnostic['zeroYieldOwners'] if r['category']=='candidates_present_but_no_accepted_yield']
    require(len(held_owners)==14,'HELD_OWNER_BASELINE_DRIFT')
    for owner in held_owners:
        filename=digest(owner.encode())+'.json'
        before=checked(repo/old.OUTPUT/'owners'/filename);after=checked(dest/'owners'/filename)
        require(before['zeroYield'] and after['zeroYield'] and before['nodes']==after['nodes'] and
                before['edges']==after['edges'],'HELD_OWNER_CHANGED')
    summary.update(validationPolicyVersion=POLICY,quarantinedAbstentions=len(quarantine),
        quarantineReasons=dict(Counter(reason for q in quarantine for reason in q['reasons'])),
        regression=dict(previousSuccessesCompared=997,unexpectedDifferences=0,heldOwnersUnchanged=14),
        recoveredGroups=8-summary['counts']['failedValidations'])
    require(baseline['accounting']['originalBatch']['receiptCosts']=={rid:r['cost'] for rid,r in receipts.items()} and
            baseline['accounting']['originalBatch']['receiptUsage']=={rid:r['usage'] for rid,r in receipts.items()} and
            baseline['accounting']['supplementalLive']['usage']==response['usage'],'ACCOUNTING_DRIFT')
    summary['accounting']=baseline['accounting']
    old_manifest=json.loads((repo/old.OUTPUT/'selection-manifest.json').read_bytes())
    require(old_manifest['journalHead']==head,'BASELINE_JOURNAL_DRIFT')
    require(old_manifest['supplementalFileHashes']==supp_hashes,'SUPPLEMENT_FILES_DRIFT')
    for selection in old_manifest['selection']:
        require(digest(canonical(selected[selection['requestID']]))==selection['responseSha256'],'SELECTION_DRIFT')
    manifest=dict(originalSelection=old_manifest,validationPolicyVersion=POLICY,historicalImplementationCommit=BASELINE,
        correctedImplementationHashes={p:digest((repo/p).read_bytes()) for p in (*CHANGED,'src/evaluation/source_local_supplemental_review_v2.py')},
        baselineSummarySha256=digest((repo/old.OUTPUT/'summary.json').read_bytes()),
        accountingRule='Exact v1 original-Batch and supplemental-live accounting retained separately')
    old.retry.files.seal(dest/'selection-manifest.json',manifest)
    old.retry.files.seal(dest/'quarantined-abstentions.json',dict(records=quarantine,countsAsNoEvidence=False))
    old.retry.files.seal(dest/'summary.json',summary)
    with (dest/'summary.md').open('x') as handle:
        handle.write('# Corrected derived validation review v2\n\n'+json.dumps({k:v for k,v in summary.items() if k!='accounting'},indent=2)+'\n')
    return {k:summary[k] for k in ('counts','decisionDispositions','quarantinedAbstentions','regression','recoveredGroups')}


def main():
    """Researcher-terminal full review; sockets blocked and existing output refused."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')),old.production.ontology_parse_cache():
        print(json.dumps(run(),indent=2))


if __name__=='__main__':main()
