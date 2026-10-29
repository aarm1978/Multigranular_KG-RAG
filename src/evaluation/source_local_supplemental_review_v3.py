"""Offline v3 shadow replay with a pinned, opt-in MDX lexical overlay."""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import socket
from unittest.mock import patch
from src.evaluation import source_local_supplemental_review_v2 as v2
from src.evaluation import source_local_coverage_diagnostic as diagnostic
from src.extraction.llm import source_local_hub_evidence_v044 as corrected

old=v2.old
require,digest,canonical=v2.require,v2.digest,v2.canonical
OUTPUT=Path('var/study2_step13/source-local-supplemental-review/v3')
POLICY='source-local-derived-validation/0.4.4'


def normalized(value):
    """Ignore only declared lexical-version and derived replay-hash provenance changes."""
    if isinstance(value,list):return [normalized(v) for v in value]
    if isinstance(value,dict):
        return {k:normalized(v) for k,v in value.items() if k!='replaySha256' and not
                (k=='lexicalClassifierVersion' and v==corrected.VERSION)}
    return value


def compare_group(before,after):
    """Stop on uncaused decisions or accepted-record drift; retain every explained change."""
    def guard(condition,reason):
        if not condition:raise v2.RegressionStop(reason+':'+before['requestID'])
    for key in ('requestID','requestSha256','responseSha256','responseBytesHex','abstentions','quarantinedAbstentions'):
        guard(before[key]==after[key],'IMMUTABLE_GROUP_DRIFT:'+key)
    a,b=before['nativeValidationView'],after['nativeValidationView']
    guard(a['originalReplay']['requestResult']['request']==b['originalReplay']['requestResult']['request'],'SOURCE_CONTEXT_DRIFT')
    for key in ('deferredSourceRecords',):
        guard(a[key]==b[key],'DEFERRED_DRIFT:'+key)
    checks=lambda n:{c['candidateID']:c for c in n['originalReplay']['validationResult']['candidateChecks']}
    ca,cb=checks(a),checks(b);guard(ca.keys()==cb.keys(),'CANDIDATE_SET_DRIFT')
    for cid in ca:
        for key in ('originalCandidate',):
            guard(ca[cid].get(key)==cb[cid].get(key),'CANDIDATE_IDENTITY_DRIFT:'+cid)
    da={d['candidateID']:d for d in a['decisions']};db={d['candidateID']:d for d in b['decisions']}
    guard(da.keys()==db.keys(),'DECISION_SET_DRIFT')
    family=a['projection']['artifactFamily'];graph=diagnostic.dependency_graph(cb)
    local={cid for cid in ca if normalized(ca[cid]['evidenceBindings'])!=normalized(cb[cid]['evidenceBindings'])}
    associations=lambda n,cid:[x for x in n['deferredEvidenceAssociations'] if x['candidateID']==cid]
    guard(all(x in b['deferredEvidenceAssociations'] for x in a['deferredEvidenceAssociations']),'DEFERRED_ASSOCIATION_LOST')
    guard(all(x in a['deferredEvidenceAssociations'] or x['candidateID'] in local
              for x in b['deferredEvidenceAssociations']),'UNEXPLAINED_DEFERRED_ASSOCIATION')
    def ancestors(cid,seen=None):
        """Find actual changed lexical bindings along unchanged explicit dependencies."""
        seen=set() if seen is None else seen
        if cid in seen:return set()
        seen.add(cid);result={cid} if cid in local else set()
        for dep in graph.get(cid,[]):result.update(ancestors(dep,seen))
        return result
    records=lambda n:{r['candidateID']:r for k in ('nodes','edges') for r in n['projection'][k]}
    pa,pb=records(a),records(b)
    for cid,record in pa.items():
        guard(cid in pb,'PREVIOUSLY_ACCEPTED_LOST:'+cid)
        guard(normalized(record)==normalized(pb[cid]),'PREVIOUSLY_ACCEPTED_CHANGED:'+cid)
    changes=[]
    for cid in da:
        if da[cid]==db[cid] and associations(a,cid)==associations(b,cid):continue
        roots=ancestors(cid)
        guard(family=='ciroh_hub' and bool(roots),'UNEXPLAINED_DECISION_CHANGE:'+cid)
        changes.append(dict(requestID=before['requestID'],groupID=before['groupID'],family=family,
            ownerID=a['projection']['owner']['endpointID'],candidateID=cid,inventoryId=ca[cid]['originalCandidate']['inventoryId'],
            kind=ca[cid]['kind'],before=da[cid],after=db[cid],
            deferredEvidenceAssociationsBefore=associations(a,cid),deferredEvidenceAssociationsAfter=associations(b,cid),
            sourceLocalIdentityBefore=ca[cid].get('sourceLocalCandidateID'),sourceLocalIdentityAfter=cb[cid].get('sourceLocalCandidateID'),
            identityRule='Unchanged native identity from exact bound offsets; previously unbound held identities may change after successful binding',
            cause='independent_lexical_binding' if cid in local else 'downstream_dependency',
            changedBindingCandidates=sorted(roots),evidence=[dict(sourceUnitID=e['sourceUnitID'],
                quoteSha256=digest(e['evidenceText'].encode())) for e in ca[cid]['originalCandidate']['evidence']]))
    if family!='ciroh_hub':guard(a==b,'NON_HUB_REGRESSION')
    return changes


def group_counts(report):
    """Count candidate decisions separately from accepted node/edge group records."""
    n=report['nativeValidationView']
    return dict(decisions=dict(Counter(d['disposition'] for d in n['decisions'])),
                nodes=len(n['projection']['nodes']),edges=len(n['projection']['edges']))


def remaining_roots(report):
    """Preserve all held stage reasons and trace independently blocking ancestors."""
    n=report['nativeValidationView'];checks={c['candidateID']:c for c in n['originalReplay']['validationResult']['candidateChecks']}
    held={d['candidateID']:d for d in n['decisions'] if d['disposition']=='held'}
    graph=diagnostic.dependency_graph(checks);local={};stages={}
    family=n['projection']['artifactFamily']
    for cid,d in held.items():
        c=checks[cid];stages[cid]=diagnostic.reasons_at_stages(n,c,d)
        roots=set(d['blockingReasons'])-diagnostic.PROPAGATED-diagnostic.WRAPPERS
        gates=[f for f in c['findings'] if f['reason'] in {'semantic_gate_pending','semantic_gates_pending'}]
        allowed=diagnostic.acceptance.RELEASES[family].get(c['originalCandidate']['inventoryId'],set())
        if gates and all(f.get('gates') and set(f['gates'])<=allowed and f.get('disposition')=='unresolved_condition' for f in gates):
            roots-={'semantic_gate_pending','semantic_gates_pending'}
        local[cid]=sorted(roots)
    return [dict(requestID=report['requestID'],candidateID=cid,inventoryId=checks[cid]['originalCandidate']['inventoryId'],
        family=family,groupID=report['groupID'],ownerID=n['projection']['owner']['endpointID'],independentReasons=local[cid],reasonsByStage=stages[cid],
        dependencies=diagnostic.reachable_roots(cid,graph,local,set(held))) for cid in sorted(held)]


def run(repo=old.retry.ROOT):
    """Replay authentic responses normally under the overlay, never re-project v2 decisions."""
    dest=repo/OUTPUT;require(not dest.exists(),'OUTPUT_ALREADY_EXISTS')
    # No pinned file changes: reuse all existing historical queue/code authority checks.
    queue,bundles=v2.load_frozen(repo)
    baseline_root=repo/v2.OUTPUT
    baseline=json.loads((baseline_root/'summary.json').read_bytes())
    baseline_manifest=json.loads((baseline_root/'selection-manifest.json').read_bytes())
    require({p.stem for p in (baseline_root/'groups').glob('*.json')}=={digest(r.encode()) for r in bundles},'V2_GROUP_COVERAGE_DRIFT')
    expected_owners={e['ownerID'] for e in queue['requests']}
    require(len(expected_owners)==335 and {p.stem for p in (baseline_root/'owners').glob('*.json')}==
            {digest(o.encode()) for o in expected_owners},'V2_OWNER_COVERAGE_DRIFT')
    diag=json.loads((repo/diagnostic.DEST/'diagnostic.json').read_bytes())
    require(diag['sourceSummarySha256']==digest((baseline_root/'summary.json').read_bytes()),'DIAGNOSTIC_BASELINE_DRIFT')
    for path,sha in baseline_manifest['correctedImplementationHashes'].items():
        require(digest((repo/path).read_bytes())==sha,'V2_IMPLEMENTATION_DRIFT:'+path)
    require(baseline['counts']['successfulValidations']==1005 and baseline['counts']['completeOwners']==335 and
            baseline['quarantinedAbstentions']==6,'V2_BASELINE_DRIFT')
    receipts,head=old.read_original(repo,bundles)
    supplement,supp_hashes=v2.supplement(repo,bundles[old.retry.REQUEST_ID])
    selected=old.select(queue['requests'],receipts,supplement)
    selection=baseline_manifest['originalSelection']
    require(selection['journalHead']==head and selection['supplementalFileHashes']==supp_hashes,'SELECTION_AUTHORITY_DRIFT')
    require(len(selection['selection'])==1005 and {s['requestID'] for s in selection['selection']}==set(selected),'SELECTION_COVERAGE_DRIFT')
    for s in selection['selection']:
        require(s['responseID']==selected[s['requestID']]['id'] and s['responseSha256']==digest(canonical(selected[s['requestID']])),'RESPONSE_SELECTION_DRIFT')
    accounting=baseline['accounting']
    require(accounting['originalBatch']['receiptCosts']=={r:v['cost'] for r,v in receipts.items()} and
        accounting['originalBatch']['receiptUsage']=={r:v['usage'] for r,v in receipts.items()} and
        accounting['supplementalLive']['usage']==supplement['usage'],'ACCOUNTING_DRIFT')
    changes=[];groups=[];remaining=[];quarantine=[];baseline_hashes={}
    validate_original=old.retry.validate_response
    def validate(prepared,response):
        """Execute full schema/semantic replay before comparing immutable v2 results."""
        rid=prepared['request']['requestID'];path=baseline_root/'groups'/(digest(rid.encode())+'.json')
        try:
            prior=v2.checked(path);baseline_hashes[str(path.relative_to(repo))]=digest(path.read_bytes())
            current=validate_original(prepared,response)
        except Exception as exc:raise v2.RegressionStop('PREVIOUS_SUCCESS_NOW_FAILS:'+rid) from exc
        changes.extend(compare_group(prior,current));remaining.extend(remaining_roots(current))
        quarantine.extend(current['quarantinedAbstentions'])
        groups.append(dict(requestID=rid,ownerID=prepared['binding']['ownerID'] if 'ownerID' in prepared['binding'] else prior['nativeValidationView']['projection']['owner']['endpointID'],
            family=prior['nativeValidationView']['projection']['artifactFamily'],groupID=prior['groupID'],
            before=group_counts(prior),after=group_counts(current)))
        return current
    with corrected.overlay(),patch.object(old.retry,'validate_response',side_effect=validate):
        summary=old.derive(queue['requests'],bundles,selected,dest)
    require(summary['counts']['successfulValidations']==1005 and summary['counts']['completeOwners']==335,'V3_INCOMPLETE')
    require(quarantine==json.loads((baseline_root/'quarantined-abstentions.json').read_bytes())['records'],'QUARANTINE_DRIFT')
    owners=[]
    for owner in sorted({e['ownerID'] for e in queue['requests']}):
        filename=digest(owner.encode())+'.json';path=baseline_root/'owners'/filename
        a=v2.checked(path);b=v2.checked(dest/'owners'/filename)
        baseline_hashes[str(path.relative_to(repo))]=digest(path.read_bytes())
        def identities(r,key):
            """Native consolidation identity: exact endpoint or typed directed triple."""
            rows=[x['records'][0]['record'] for x in r[key]]
            return {x['resolvedEndpoint']['endpointID'] if key=='nodes' else
                (x['originalCandidate']['inventoryId'],x['resolvedSource']['endpointID'],x['resolvedTarget']['endpointID']) for x in rows}
        for key in ('nodes','edges'):require(identities(a,key)<=identities(b,key),'OWNER_ACCEPTED_IDENTITY_LOST')
        owners.append(dict(ownerID=owner,family=a['artifactFamily'],before={k:len(a[k]) for k in ('nodes','edges','derivedConstructionInputs')},
            after={k:len(b[k]) for k in ('nodes','edges','derivedConstructionInputs')},beforeZeroYield=a['zeroYield'],afterZeroYield=b['zeroYield'],
            candidateBearing=any(r['nativeValidationView']['decisions'] for r in b['groupReports'])))
    recovered=[c for c in changes if c['before']['disposition']=='held' and c['after']['disposition']=='accepted']
    cohort=set(diag['cohort']['ownerIDs'])
    require(len(cohort)==14 and sum(o['beforeZeroYield'] for o in owners)==53,'COHORT_DRIFT')
    comparison=dict(groupCountingUnit='Request-local candidate decisions; no cross-group deduplication',
        ownerCountingUnit='Native exact endpoint/typed-triple consolidation; derived D-26 inputs reported separately',
        groups=groups,owners=owners,changedDecisions=changes,heldToAccepted=len(recovered),acceptedToHeld=0,
        groupAcceptedRecordTotals={side:{key:sum(g[side][key] for g in groups) for key in ('nodes','edges')} for side in ('before','after')},
        decisionTransitions=dict(Counter(c['before']['disposition']+'->'+c['after']['disposition'] for c in changes)),
        recoveriesByCause=dict(Counter(c['cause'] for c in recovered)),
        recoveriesByFamilyTargetGroup=[dict(family=k[0],inventoryId=k[1],groupID=k[2],count=v) for k,v in sorted(Counter((c['family'],c['inventoryId'],c['groupID']) for c in recovered).items())],
        cohortOwnersGainingYield=sum(o['ownerID'] in cohort and o['beforeZeroYield'] and not o['afterZeroYield'] for o in owners),
        zeroYieldOwnersGainingYield=sum(o['beforeZeroYield'] and not o['afterZeroYield'] for o in owners),
        remainingCandidateBearingZeroYieldOwners=[o['ownerID'] for o in owners if o['afterZeroYield'] and o['candidateBearing']],
        remainingHeld=remaining,remainingIndependentReasonCounts=dict(Counter(r for h in remaining for r in h['independentReasons'])),
        baselineCounts=baseline['counts'],baselineDecisions=baseline['decisionDispositions'],
        integrity=dict(authenticResponsesUnchanged=True,originalCandidatesUnchanged=True,acceptedRecordsPreserved=True,
            exactEndpointsPreserved=True,quarantinedAbstentions=6,accountingUnchanged=True),
        interpretation='Rule-induced information recovery, not precision, recall, F1 or scientific completion',providerCalls=0,kgAuthorization=False)
    summary.update(validationPolicyVersion=POLICY,lexicalClassifierVersion=corrected.VERSION,accounting=deepcopy(accounting),quarantinedAbstentions=6)
    paths=('src/extraction/llm/source_local_hub_evidence_v044.py','src/evaluation/source_local_supplemental_review_v3.py')
    manifest=dict(originalSelection=selection,baselineManifestSha256=digest((baseline_root/'selection-manifest.json').read_bytes()),
        baselineSummarySha256=digest((baseline_root/'summary.json').read_bytes()),baselineReportHashes=baseline_hashes,
        historicalAuthorityRule='Unmodified v2.load_frozen verifies original queue and historical code pins before overlay',
        correctedImplementationHashes={p:digest((repo/p).read_bytes()) for p in paths},validationPolicyVersion=POLICY)
    for name,value in [('selection-manifest',manifest),('summary',summary),('comparison',comparison),
                       ('quarantined-abstentions',dict(records=quarantine,countsAsNoEvidence=False))]:
        old.retry.files.seal(dest/(name+'.json'),value)
    compact={k:v for k,v in comparison.items() if k not in ('groups','owners','changedDecisions','remainingHeld')}
    compact['v3Counts']=summary['counts'];compact['v3Decisions']=summary['decisionDispositions']
    with (dest/'comparison.md').open('x') as f:f.write('# v2 → v3 lexical shadow review\n\nNo acceptance-policy change or accuracy claim.\n\n```json\n'+json.dumps(compact,indent=2)+'\n```\n')
    return compact


def main():
    """Researcher-terminal corpus replay only; all socket connections blocked."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')),old.production.ontology_parse_cache():
        print(json.dumps(run(),indent=2))


if __name__=='__main__':main()
