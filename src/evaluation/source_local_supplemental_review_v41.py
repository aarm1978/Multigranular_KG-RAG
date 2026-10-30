"""Offline v4.1 reviewer-adjudicated projection; v4 remains the immutable baseline."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import socket
from unittest.mock import patch
from src.evaluation import source_local_supplemental_review_v4 as v4
from src.evaluation import source_local_adjudication as adjudication

v2, old = v4.v2, v4.old
require, digest, canonical = v4.require, v4.digest, v4.canonical
OUTPUT = Path('var/study2_step13/source-local-supplemental-review/v4.1')
ARTIFACT = Path('docs/study2_v4_1_reviewer_adjudications_v0.1.json')


def checks(report):
    """Index the complete native candidate checks, without filtering diagnostics."""
    return {c['candidateID']: c for c in report['nativeValidationView']['originalReplay']['validationResult']['candidateChecks']}


def compare(before, after, entries):
    """Stop on unrelated decisions, changed authentic content or unexplained accepted losses."""
    def guard(condition, reason):
        if not condition:
            raise v2.RegressionStop(reason + ':' + before['requestID'])
    for key in ('requestID', 'requestSha256', 'responseSha256', 'responseBytesHex', 'abstentions', 'quarantinedAbstentions'):
        guard(before[key] == after[key], 'IMMUTABLE_DRIFT:' + key)
    a, b = before['nativeValidationView'], after['nativeValidationView']
    for key in ('deferredSourceRecords', 'deferredEvidenceAssociations'):
        guard(a[key] == b[key], 'PROVENANCE_DRIFT:' + key)
    guard(a['originalReplay']['requestResult'] == b['originalReplay']['requestResult'], 'SOURCE_DRIFT')
    ca, cb = checks(before), checks(after)
    guard(ca.keys() == cb.keys(), 'CANDIDATE_SET_DRIFT')
    for cid in ca:
        for key in ('originalCandidate', 'boundEvidence', 'evidenceBindings', 'sourceLocalCandidateID',
                    'resolvedEndpoint', 'resolvedSource', 'resolvedTarget', 'dependencies'):
            guard(ca[cid].get(key) == cb[cid].get(key), 'CANDIDATE_PROVENANCE_DRIFT:' + cid + ':' + key)
    guard(a['derivedConstructionInput']['assertions'] == b['derivedConstructionInput']['assertions'],
          'UNEXPLAINED_DERIVED_ASSERTION_CHANGE')
    excluded = {e['excluded']['candidateID'] for e in entries}
    roots = excluded | {e['counterpart']['candidateID'] for e in entries}
    graph = v4.diagnostic.dependency_graph(ca)
    closure = set(roots)
    while True:
        expanded = closure | {cid for cid, deps in graph.items() if set(deps) & closure}
        if expanded == closure:
            break
        closure = expanded
    da = {d['candidateID']: d for d in a['decisions']}
    db = {d['candidateID']: d for d in b['decisions']}
    guard(da.keys() == db.keys(), 'DECISION_SET_DRIFT')
    records = lambda n: {r['candidateID']: r for key in ('nodes', 'edges') for r in n['projection'][key]}
    pa, pb = records(a), records(b)
    for cid, record in pa.items():
        if cid in pb:
            guard(v4.normalized(record) == v4.normalized(pb[cid]), 'ACCEPTED_RECORD_DRIFT:' + cid)
        elif cid not in excluded:
            guard(cid in closure and db[cid]['disposition'] == 'held' and
                  'construction_dependency_not_admitted' in db[cid]['blockingReasons'], 'UNEXPLAINED_ACCEPTED_LOSS:' + cid)
    # Native admitted records must have all local dependencies admitted or exactly suppressed.
    admitted = {cid for cid, d in db.items() if d['disposition'] in ('accepted', 'suppressed_duplicate')}
    for cid, record in pb.items():
        guard(set(record['dependencies']) <= admitted, 'INCONSISTENT_DEPENDENCY:' + cid)
    changed = []
    for cid in da:
        if da[cid] == db[cid] and cid not in roots:
            continue
        guard(cid in closure, 'UNRELATED_DECISION_CHANGED:' + cid)
        c = cb[cid]
        changed.append(dict(candidateID=cid, requestID=before['requestID'], groupID=before['groupID'],
            ownerID=b['projection']['owner']['endpointID'], family=b['projection']['artifactFamily'],
            before=da[cid], after=db[cid], cause='reviewer_exclusion' if cid in excluded else
            'duplicate_reconsideration' if cid in roots else 'dependency_consequence',
            dependenciesBefore=graph[cid], dependenciesAfter=v4.diagnostic.dependency_graph(cb)[cid],
            candidateSha256=digest(canonical(c['originalCandidate'])),
            boundEvidenceSha256=digest(canonical(c['boundEvidence'])),
            endpoints={k:c[k] for k in ('resolvedSource','resolvedTarget','resolvedEndpoint') if k in c},
            evidence=[dict(sourceUnitID=s['sourceUnitID'], quoteSha256=digest(s['evidenceText'].encode()),
                quoteExcerpt=s['evidenceText'][:240], startOffset=s['startOffsetInAuthority'],
                endOffset=s['endOffsetInAuthority']) for s in c['boundEvidence']]))
    return changed


def run(repo=old.retry.ROOT):
    """Verify all original authorities; replay only affected groups and reconsolidate owners."""
    dest = repo / OUTPUT
    require(not dest.exists(), 'OUTPUT_ALREADY_EXISTS')
    artifact = json.loads((repo / ARTIFACT).read_bytes())
    require(artifact['authority'] == adjudication.VERSION, 'ADJUDICATION_AUTHORITY_DRIFT')
    for path, sha in artifact['baselineFileHashes'].items():
        require(digest((repo/path).read_bytes()) == sha, 'BASELINE_PIN_DRIFT:' + path)
    baseline_root = repo / v4.OUTPUT
    manifest = json.loads((baseline_root/'selection-manifest.json').read_bytes())
    baseline = json.loads((baseline_root/'summary.json').read_bytes())
    # Retain every existing v2/v3/v4 implementation authority check.
    for root in (v2.OUTPUT, v4.v3.OUTPUT, v4.OUTPUT):
        m = json.loads((repo/root/'selection-manifest.json').read_bytes())
        for path, sha in m['correctedImplementationHashes'].items():
            require(digest((repo/path).read_bytes()) == sha, 'IMPLEMENTATION_DRIFT:' + path)
    with patch.object(v2, 'CHANGED', (*v2.CHANGED, v4.CHANGED_VALIDATOR)):
        queue, bundles = v2.load_frozen(repo)
    require(len(bundles) == 1005, 'REQUEST_COVERAGE_DRIFT')
    owners = {e['ownerID'] for e in queue['requests']}
    require(len(owners) == 335, 'OWNER_COVERAGE_DRIFT')
    for folder, ids in (('groups', bundles), ('owners', owners)):
        require({p.stem for p in (baseline_root/folder).glob('*.json')} ==
                {digest(i.encode()) for i in ids}, 'BASELINE_COVERAGE_DRIFT')
    receipts, head = old.read_original(repo, bundles)
    supplement, hashes = v2.supplement(repo, bundles[old.retry.REQUEST_ID])
    selected = old.select(queue['requests'], receipts, supplement)
    selection = manifest['originalSelection']
    require(selection['journalHead'] == head and selection['supplementalFileHashes'] == hashes, 'SELECTION_DRIFT')
    require(len(selection['selection']) == 1005 and {s['requestID'] for s in selection['selection']} == set(selected), 'SELECTION_COVERAGE_DRIFT')
    for s in selection['selection']:
        require(s['responseID'] == selected[s['requestID']]['id'] and
                s['responseSha256'] == digest(canonical(selected[s['requestID']])), 'RESPONSE_DRIFT')
    accounting = baseline['accounting']
    require(accounting['originalBatch']['receiptCosts'] == {r:v['cost'] for r,v in receipts.items()}
            and accounting['originalBatch']['receiptUsage'] == {r:v['usage'] for r,v in receipts.items()}
            and accounting['supplementalLive']['usage'] == supplement['usage'], 'ACCOUNTING_DRIFT')
    entries = artifact['entries']; seen = set(); changes = []; groups = []; quarantine = []; input_hashes = {}
    native_validate = old.retry.validate_response

    def validate(prepared, response):
        """Reuse immutable v4 groups except explicitly adjudicated request identities."""
        rid = prepared['request']['requestID']; path = baseline_root/'groups'/(digest(rid.encode())+'.json')
        prior = v2.checked(path); input_hashes[str(path.relative_to(repo))] = digest(path.read_bytes())
        texts = [c['text'] for item in response.get('output', []) if item.get('type') == 'message'
                 for c in item['content'] if c.get('type') == 'output_text']
        require(len(texts) == 1 and bytes.fromhex(prior['responseBytesHex']) == texts[0].encode()
                and prior['requestSha256'] == prepared['semanticRequest']['requestSha256']
                and prior['requestID'] == rid, 'V4_AUTHENTIC_ASSOCIATION_DRIFT')
        relevant = [e for e in entries if e['requestID'] == rid]
        current = prior
        if relevant:
            for e in relevant:
                require(e['baselineGroupSha256'] == digest(path.read_bytes()) and
                    e['requestSha256'] == prior['requestSha256'] and e['responseSha256'] == prior['responseSha256'], 'ADJUDICATION_GROUP_DRIFT')
                seen.add(e['adjudicationID'])
            with v4.corrected.overlay():
                reproduced = v4.corrected.stamp_report(native_validate(prepared, response))
                require(reproduced == prior, 'V4_REPRODUCTION_DRIFT')
                with adjudication.overlay(relevant):
                    current = v4.corrected.stamp_report(native_validate(prepared, response))
            changes.extend(compare(prior, current, relevant))
            current['reviewerAdjudication'] = dict(authority=adjudication.VERSION,
                artifactSha256=digest((repo/ARTIFACT).read_bytes()), adjudicationIDs=[e['adjudicationID'] for e in relevant])
            current.pop('reportSha256'); current['reportSha256'] = digest(canonical(current))
        groups.append(dict(requestID=rid, family=prior['nativeValidationView']['projection']['artifactFamily'],
            groupID=prior['groupID'], before=v4.group_counts(prior), after=v4.group_counts(current)))
        quarantine.extend(current['quarantinedAbstentions'])
        return current

    # RegressionStop is a BaseException: never downgrade a regression into a failed group.
    def guarded(prepared, response):
        """Fail the entire derived run on any authority or validation discrepancy."""
        try:
            return validate(prepared, response)
        except Exception as exc:
            raise v2.RegressionStop(str(exc)) from exc

    with patch.object(old.retry, 'validate_response', side_effect=guarded):
        summary = old.derive(queue['requests'], bundles, selected, dest)
    require(seen == {e['adjudicationID'] for e in entries} and len(seen) == len(entries), 'UNAPPLIED_ADJUDICATION')
    require(summary['counts']['successfulValidations'] == 1005 and summary['counts']['completeOwners'] == 335, 'INCOMPLETE_PROJECTION')
    require(quarantine == json.loads((baseline_root/'quarantined-abstentions.json').read_bytes())['records'] and len(quarantine) == 6, 'QUARANTINE_DRIFT')
    owner_changes = []
    affected = {e['excluded']['ownerID'] for e in entries}
    for owner in sorted(owners):
        name = digest(owner.encode())+'.json'; path = baseline_root/'owners'/name
        a, b = v2.checked(path), v2.checked(dest/'owners'/name)
        input_hashes[str(path.relative_to(repo))] = digest(path.read_bytes())
        if owner not in affected:
            require(a == b, 'UNRELATED_OWNER_DRIFT')
        owner_changes.append(dict(ownerID=owner, family=a['artifactFamily'],
            before={k:len(a[k]) for k in ('nodes','edges','derivedConstructionInputs')},
            after={k:len(b[k]) for k in ('nodes','edges','derivedConstructionInputs')}))
    summary.update(accounting=deepcopy(baseline['accounting']), quarantinedAbstentions=6,
                   reviewerAdjudicationAuthority=adjudication.VERSION)
    families = sorted({g['family'] for g in groups})
    comparison = dict(changedDecisions=changes, groups=groups, owners=owner_changes,
        baselineCounts=baseline['counts'], revisedCounts=summary['counts'],
        countDifferences={k:summary['counts'][k]-v for k,v in baseline['counts'].items()},
        familyCounts={f:{side:dict(nodes=sum(g[side]['nodes'] for g in groups if g['family']==f),
            edges=sum(g[side]['edges'] for g in groups if g['family']==f),
            decisions=dict(sum((Counter(g[side]['decisions']) for g in groups if g['family']==f),Counter())),
            ownerNodes=sum(o[side]['nodes'] for o in owner_changes if o['family']==f),
            ownerEdges=sum(o[side]['edges'] for o in owner_changes if o['family']==f))
            for side in ('before','after')} for f in families},
        unrelatedDecisionsIdentical=True, authenticCandidatesAndEvidenceUnchanged=True,
        quarantinedAbstentionsUnchanged=6, accountingUnchanged=True, providerCalls=0,
        interpretation='Explicit post-hoc researcher adjudication, not autonomous extraction success or scientific acceptance')
    comparison['decisionCountDifferences'] = {k:summary['decisionDispositions'].get(k,0)-baseline['decisionDispositions'].get(k,0)
        for k in sorted(set(summary['decisionDispositions']) | set(baseline['decisionDispositions']))}
    comparison['familyCountDifferences'] = {family:{
        **{key:counts['after'][key]-counts['before'][key] for key in ('nodes','edges','ownerNodes','ownerEdges')},
        'decisions':{k:counts['after']['decisions'].get(k,0)-counts['before']['decisions'].get(k,0)
            for k in sorted(set(counts['after']['decisions']) | set(counts['before']['decisions']))}}
        for family,counts in comparison['familyCounts'].items()}
    audit = dict(authority=adjudication.VERSION, adjudicationArtifactSha256=digest((repo/ARTIFACT).read_bytes()),
        baselineFileHashes=artifact['baselineFileHashes'], baselineReportHashes=input_hashes,
        originalSelection=selection, implementationHashes={p:digest((repo/p).read_bytes()) for p in
            ('src/evaluation/source_local_adjudication.py','src/evaluation/source_local_supplemental_review_v41.py')})
    for name, value in [('summary',summary),('comparison',comparison),('selection-manifest',audit),
                        ('quarantined-abstentions',dict(records=quarantine,countsAsNoEvidence=False))]:
        old.retry.files.seal(dest/(name+'.json'),value)
    share = dest/'share'; share.mkdir()
    compact = {k:v for k,v in comparison.items() if k not in ('groups','owners')}
    old.retry.files.seal(share/'comparison.json',compact)
    old.retry.files.seal(share/'adjudications.json',artifact)
    old.retry.files.seal(share/'manifest.json',audit)
    with (share/'synthesis.md').open('x') as f:
        f.write('# v4 → v4.1 reviewer adjudication\n\nPost-hoc scientific correction; independent review remains required.\n\n')
        f.write('Unrelated decisions, authentic candidates, evidence, accounting and six quarantined abstentions preserved.\n\n')
        f.write('| Candidate | v4 | v4.1 | Cause |\n|---|---|---|---|\n')
        for c in changes:
            f.write(f"| {c['candidateID']} | {c['before']['disposition']} | {c['after']['disposition']} | {c['cause']} |\n")
        f.write('\nCount differences (owner and group units remain separate in comparison.json):\n```json\n'+json.dumps(comparison['countDifferences'],indent=2)+'\n```\n')
    return dict(output=str(OUTPUT), counts=summary['counts'], changedDecisions=len(changes))


def main():
    """Researcher-only full projection, with network access explicitly blocked."""
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')), \
         patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')), old.production.ontology_parse_cache():
        print(json.dumps(run(),indent=2))


if __name__ == '__main__':
    main()
