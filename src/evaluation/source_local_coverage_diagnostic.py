"""Read-only scientific coverage diagnosis in bounded shards; never adjudicate or promote."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import json
from pathlib import Path
import re
import socket
from unittest.mock import patch

from src.evaluation import source_local_supplemental_review as review
from src.evaluation.source_local_review_diagnostic import checked_report, read_json
from src.extraction.llm import construction_acceptance as acceptance
from src.extraction.llm.source_local_hub_evidence import regions

ROOT=review.retry.ROOT
SOURCE=Path('var/study2_step13/source-local-supplemental-review/v2')
DEST=Path('var/study2_step13/source-local-coverage-diagnostic/v1')
require,digest,canonical=review.require,review.digest,review.canonical
PROPAGATED=set(acceptance.DEPENDENCY_REASONS)|{'construction_dependency_not_admitted','parent_semantic_acceptance_not_evaluated'}
WRAPPERS={'original_record_not_eligible','original_target_incompatibility','nonreleasable_pending_gates'}


def reasons_at_stages(native, check, decision):
    """Retain simultaneous original stage findings, including gates hidden by precedence."""
    cid=check['candidateID'];row=next(x for x in native['originalReplay']['finalRecords'] if x['candidateID']==cid)
    result=[]
    for reason in decision['blockingReasons']:result.append(dict(stage='construction',reason=reason))
    for f in check.get('findings',[]):
        result.append(dict(stage='candidate_validation',**{k:v for k,v in f.items()
            if k in ('reason','disposition','referenceID','dependencyID','gates','fragmentIndex')}))
    profile=check.get('targetProfileCheck',{})
    for gate in sorted(set(profile.get('pendingGates',[]))|set(profile.get('profileResult',{}).get('missingGates',[]))):
        result.append(dict(stage='target_profile',reason='pending_gate',gate=gate))
    for field in ('parseDiagnostics','replayDiagnostics'):
        for finding in row.get(field,[]):result.append(dict(stage=field,reason=finding.get('reason',str(finding))))
    for i,b in enumerate(check.get('evidenceBindings',[])):
        for d in b.get('binding',{}).get('diagnostics',[]):
            result.append(dict(stage='evidence_binding',fragmentIndex=i,reason=d.get('reason',str(d))))
    return result


def dependency_graph(checks):
    """Reconstruct explicit local candidate/parent/duplicate edges; no name resolution."""
    graph={}
    for cid,c in checks.items():
        row=c['originalCandidate'];deps=set(c.get('dependencies',[]))
        for ref in [row.get('source'),row.get('target'),*row.get('parentPath',[])]:
            if isinstance(ref,dict) and ref.get('referenceType') in ('candidate_node','candidate_edge'):
                deps.add(ref['referenceID'])
        deps.update(d for d in c.get('duplicateOf',[]) if d in checks)
        graph[cid]=sorted(deps)
    return graph


def reachable_roots(cid, graph, local, held):
    """Enumerate held ancestor causes without discarding cycles or unresolved references."""
    seen=set();roots=[];missing=set();cycles=[]
    def visit(current,path):
        if current in path:
            cycles.append(path[path.index(current):]+[current]);return
        if current in seen:return
        seen.add(current)
        if current not in graph:missing.add(current);return
        if current not in held:return
        roots.extend(dict(candidateID=current,reason=r) for r in local[current])
        for dep in graph[current]:visit(dep,path+[current])
    visit(cid,[])
    return dict(rootCauses=roots,missingDependencies=sorted(missing),cycles=cycles)


@lru_cache(maxsize=64)
def source_characteristics(text, family):
    """Measure supplied content and lexical patterns without rendering or altering it."""
    result=dict(characters=len(text),utf8Bytes=len(text.encode()),lines=len(text.splitlines()),
        sourceTextSha256=digest(text.encode()),wordTokens=len(re.findall(r'\S+',text)),
        headings=len(re.findall(r'^\s*#{1,6}\s',text,re.M)),fences=len(re.findall(r'^\s*(```|~~~)',text,re.M)))
    if family=='ciroh_hub':
        marks=Counter(regions(text));result['visibilityCharacters']=dict(marks)
        result['uncertainFraction']=marks['uncertain']/max(1,len(text))
        result['lexicalSignals']={
            'unclosedHtmlVoidTags':len(re.findall(r'<(?:br|hr|img|input|meta|link|source|wbr)\b[^>]*?(?<!/)>',text,re.I)),
            'markdownAutolinks':len(re.findall(r'<https?://[^>]+>',text)),
            'jsxComponents':len(re.findall(r'<[A-Z][\w.]*\b',text)),
            'importExportLines':len(re.findall(r'^\s*(?:import|export)\b',text,re.M)),
            'styleOrEventAttributes':len(re.findall(r'\b(?:style|on[A-Z]\w*)\s*=',text))}
    return result


def evidence_refs(candidate, units, check):
    """Keep compact original evidence references, exact quote hashes and unique offsets."""
    result=[]
    for i,e in enumerate(candidate.get('evidence',[])):
        uid=e['sourceUnitID'];text=units.get(uid,{}).get('text','');quote=e['evidenceText']
        count=text.count(quote) if quote else 0
        b=(check.get('evidenceBindings') or [])
        binding=b[i].get('binding',{}) if i<len(b) else {}
        result.append(dict(fragmentIndex=i,sourceUnitID=uid,quoteSha256=digest(quote.encode()),
            quoteCharacters=len(quote),quoteExcerpt=quote[:180],exactOccurrences=count,
            uniqueOffset=text.find(quote) if count==1 else None,
            literalBindingStatus=binding.get('bindingReport',{}).get('bindingStatus'),
            originalBindingStatus=binding.get('status')))
    return result


def analyze_group(report, prepared):
    """Diagnose existing results without invoking validators or changing any disposition."""
    native=report['nativeValidationView'];body=prepared['requestInputs']['baseContext']['semanticRequest']['request']
    require(native['originalReplay']['requestResult']['request']==body,'SOURCE_CONTEXT_DRIFT')
    require(report['requestID']==prepared['request']['requestID'] and
            report['requestSha256']==prepared['semanticRequest']['requestSha256'],'GROUP_ASSOCIATION_DRIFT')
    raw=bytes.fromhex(report['responseBytesHex']);require(digest(raw)==report['responseSha256'],'RESPONSE_DRIFT')
    payload=json.loads(raw);family=body['artifactFamily'];owner=body['owner']['endpointID'];group=report['groupID'];rid=report['requestID']
    units={u['sourceUnitID']:u for u in body['sourceUnits']};selected=set(body['selectedSourceUnitIDs'])
    checks={c['candidateID']:c for c in native['originalReplay']['validationResult']['candidateChecks']}
    decisions={d['candidateID']:d for d in native['decisions']};graph=dependency_graph(checks)
    held={cid for cid,d in decisions.items() if d['disposition']=='held'}
    local={cid:sorted(set(decisions[cid]['blockingReasons'])-PROPAGATED-WRAPPERS) for cid in held}
    header=dict(requestID=rid,ownerID=owner,family=family,groupID=group,responseSha256=report['responseSha256'])
    held_rows=[];positive=[]
    for cid,c in checks.items():
        candidate=c['originalCandidate'];d=decisions[cid]
        positive.append(dict(candidateID=cid,inventoryId=candidate['inventoryId'],disposition=d['disposition'],
                             sourceUnitIDs=sorted({e['sourceUnitID'] for e in candidate['evidence']})))
        if cid not in held:continue
        trace=reachable_roots(cid,graph,local,held);refs=evidence_refs(candidate,units,c)
        held_rows.append(dict(**header,candidateID=cid,kind=c['kind'],inventoryId=candidate['inventoryId'],
            label=candidate.get('label',candidate.get('methodSurfaceForm')),blockingReasons=d['blockingReasons'],
            reasonsByStage=reasons_at_stages(native,c,d),localRootReasons=local[cid],dependencies=graph[cid],
            dependencyDisposition={x:decisions.get(x,{}).get('disposition','unavailable') for x in graph[cid]},
            dependencyTrace=trace,parentPath=candidate.get('parentPath',[]),
            parentPathStructurallyLinked=c.get('parentPathStructurallyLinked'),
            resolvedEndpoints={k:(c[k] or {}).get('endpointID') for k in ('resolvedEndpoint','resolvedSource','resolvedTarget') if k in c},
            evidence=refs,boundEvidenceCount=len(c.get('boundEvidence',[])),
            shadowLiteralOnly=dict(allFragmentsUnique=bool(refs) and all(e['exactOccurrences']==1 for e in refs),
                allFragmentsSelected=bool(refs) and all(e['sourceUnitID'] in selected for e in refs),
                allFragmentsOriginallyLiteralBound=bool(refs) and all(e['literalBindingStatus']=='bound' for e in refs),
                admissibilityWaived=False,acceptanceChanged=False)))
    absts=[dict(**header,abstentionID=a['abstentionID'],inventoryId=a['inventoryId'],disposition=a['disposition'],
        reason=a['reason'],sourceUnitIDs=a['sourceUnitIDs'],
        citedScopeCharacters=sum(len(units.get(uid,{}).get('text','')) for uid in set(a['sourceUnitIDs'])),
        citedSelectedUnits=bool(a['sourceUnitIDs']) and set(a['sourceUnitIDs'])<=selected) for a in report['abstentions']]
    sources=[dict(sourceUnitID=uid,selected=uid in selected,path=u.get('path'),sourceField=u.get('sourceField'),
        contentKind=u.get('contentKind'),**source_characteristics(u.get('text',''),family)) for uid,u in sorted(units.items())]
    return dict(**header,candidates=dict(nodes=len(payload['candidateNodes']),edges=len(payload['candidateEdges'])),
        decisions=dict(Counter(d['disposition'] for d in decisions.values())),zeroYield=report['zeroYield'],
        held=held_rows,abstentions=absts,positive=positive,sources=sources,
        missingSelectedUnits=sorted(selected-set(units)),unselectedUnits=sorted(set(units)-selected),
        quarantinedAbstentions=len(report['quarantinedAbstentions']))


def shard(part):
    """Process at most 100 saved group reports and their exact pinned prepared bundles."""
    parent,sha=read_json(ROOT/review.retry.QUEUE/'queue-manifest.json');require(sha==review.retry.QUEUE_SHA,'QUEUE_DRIFT')
    entries={e['identity']['requestID']:e for e in parent['requests']}
    paths=sorted((ROOT/SOURCE/'groups').glob('*.json'))[part*100:(part+1)*100];require(paths,'EMPTY_SHARD')
    rows=[];hashes={}
    for path in paths:
        r,sha=checked_report(path);hashes[path.name]=sha;e=entries[r['requestID']]
        p,bsha=read_json(ROOT/review.retry.QUEUE/'queue'/e['bundleFile']);require(bsha==e['bundleSha256'],'BUNDLE_DRIFT')
        require(review.retry.adapter.fingerprint(p)==e['identity'],'IDENTITY_DRIFT')
        rows.append(analyze_group(r,p))
    return dict(part=part,groupHashes=hashes,groups=rows)


def conflict_flags(abstentions, groups):
    """Flag same-owner/target evidence overlap; never equate this with contradiction."""
    positives=defaultdict(list)
    for g in groups:
        for p in g['positive']:
            if p['disposition'] in ('accepted','held','suppressed_duplicate'):
                positives[g['ownerID'],p['inventoryId']].append(dict(requestID=g['requestID'],**p))
    result=[]
    for a in abstentions:
        matches=[p for p in positives[a['ownerID'],a['inventoryId']] if set(p['sourceUnitIDs'])&set(a['sourceUnitIDs'])]
        if matches:result.append(dict(requestID=a['requestID'],abstentionID=a['abstentionID'],ownerID=a['ownerID'],inventoryId=a['inventoryId'],
            overlappingPositiveCount=len(matches),positiveReferences=[{'requestID':p['requestID'],'candidateID':p['candidateID'],'disposition':p['disposition']} for p in matches],
            interpretation='potential_scope_conflict_not_proven_contradiction'))
    return result


def finish():
    """Reconcile all requested totals and synthesize root-cause hypotheses conservatively."""
    destination=ROOT/DEST;require(not (destination/'diagnostic.json').exists() and not (destination/'report.md').exists(),'OUTPUT_ALREADY_EXISTS')
    groups=[g for i in range(11) for g in read_json(destination/'parts'/f'{i:02d}.json')[0]['groups']]
    require(len(groups)==1005 and len({g['requestID'] for g in groups})==1005,'GROUP_COVERAGE_DRIFT')
    # Interpretive gates explicitly releasable by policy are retained as stage findings,
    # but are not counted as independent roots just because an earlier hard failure
    # caused construction to copy all upstream findings into blockingReasons.
    for g in groups:
        local={};held_ids={h['candidateID'] for h in g['held']}
        graph={p['candidateID']:[] for p in g['positive']}
        for h in g['held']:
            allowed=acceptance.RELEASES[h['family']].get(h['inventoryId'],set())
            pending=[f for f in h['reasonsByStage'] if f['stage']=='candidate_validation' and
                     f['reason'] in {'semantic_gate_pending','semantic_gates_pending'}]
            releasable=bool(pending) and all(f.get('gates') and set(f['gates'])<=allowed and
                       f.get('disposition')=='unresolved_condition' for f in pending)
            h['releasableInterpretiveGatesNotIndependentRoot']=releasable
            local[h['candidateID']]=[r for r in h['localRootReasons'] if not
                (releasable and r in {'semantic_gate_pending','semantic_gates_pending'})]
            graph[h['candidateID']]=h['dependencies']
        for h in g['held']:
            h['independentLocalRootReasons']=local[h['candidateID']]
            h['dependencyTrace']=reachable_roots(h['candidateID'],graph,local,held_ids)
    held=[h for g in groups for h in g['held']];absts=[a for g in groups for a in g['abstentions']]
    require(len(held)==1971 and len(absts)==11017,'COUNTS_DRIFT')
    summary,summary_sha=read_json(ROOT/SOURCE/'summary.json')
    require(summary['counts']['unresolvedAssertions']==len(held) and summary['counts']['abstentions']==len(absts),'SUMMARY_DRIFT')
    by_owner=defaultdict(list)
    for g in groups:by_owner[g['ownerID']].append(g)
    zeros=[]
    for owner,gs in sorted(by_owner.items()):
        r,_=checked_report(ROOT/SOURCE/'owners'/(digest(owner.encode())+'.json'))
        if not r['zeroYield']:continue
        candidates=sum(g['candidates']['nodes']+g['candidates']['edges'] for g in gs)
        decisions=Counter()
        for g in gs:decisions.update(g['decisions'])
        abst=sum(len(g['abstentions']) for g in gs)
        pattern=('only_abstentions_no_candidates' if not candidates and abst else 'empty_no_candidates_no_abstentions' if not candidates
                 else 'only_held_candidates' if decisions['held']==candidates else 'other_zero_yield_pattern')
        sources={s['sourceUnitID']:s for g in gs for s in g['sources']}
        zeros.append(dict(ownerID=owner,family=gs[0]['family'],pattern=pattern,candidates=candidates,validAbstentions=abst,
            quarantinedAbstentions=sum(g['quarantinedAbstentions'] for g in gs),decisions=dict(decisions),sources=list(sources.values()),
            missingSelectedUnits=sorted({s for g in gs for s in g['missingSelectedUnits']}),
            unselectedUnits=sorted({s for g in gs for s in g['unselectedUnits']}),
            rootReasons=dict(Counter(r for g in gs for h in g['held'] for r in h['independentLocalRootReasons']))))
    require(len(zeros)==53 and summary['counts']['zeroYieldOwners']==53,'ZERO_YIELD_DRIFT')
    old,_=read_json(ROOT/'var/study2_step13/source-local-review-diagnostic/v1/diagnostic.json')
    cohort={x['ownerID'] for x in old['zeroYieldOwners'] if x['category']=='candidates_present_but_no_accepted_yield'}
    cohort_held=[h for h in held if h['ownerID'] in cohort];require(len(cohort)==14 and len(cohort_held)==610,'COHORT_DRIFT')
    conflicts=conflict_flags(absts,groups)
    reason_table=defaultdict(lambda:dict(count=0,owners=set(),targets=Counter(),familyGroups=Counter(),stageCounts=Counter(),examples=[]))
    for h in held:
        for reason in set(r['reason'] for r in h['reasonsByStage']):
            row=reason_table[reason];row['count']+=1;row['owners'].add(h['ownerID']);row['targets'][h['inventoryId']]+=1
            row['familyGroups'][h['family']+':'+h['groupID']]+=1
            row['stageCounts'].update({r['stage'] for r in h['reasonsByStage'] if r['reason']==reason})
            if len(row['examples'])<4:row['examples'].append(dict(requestID=h['requestID'],candidateID=h['candidateID'],ownerID=h['ownerID']))
    reasons={k:{**v,'owners':sorted(v['owners']),'targets':dict(v['targets']),'familyGroups':dict(v['familyGroups']),'stageCounts':dict(v['stageCounts'])} for k,v in sorted(reason_table.items())}
    hypotheses=[]
    for key,pattern,classification,action in [
        ('MDX_visibility','full_content_not_static_visible','mixed: demonstrated lexical limitation; individual visibility needs inspection','Inspect HTML void tags, autolinks, indentation and unmatched-tag contamination. Correct proven lexical defects only; retain opaque dynamic/code regions and rerun unchanged evidence/parent checks.'),
        ('parent_paths','parent','mixed: structural constraint and possibly downstream visibility loss','Trace each missing parent to its independent evidence and endpoint; never accept a dependent by waiving its path.'),
        ('method_scope','method','intentional scientific constraint / researcher decision','Retain unresolved Method implementation evidence; any semantic expansion requires researcher approval, not label substitution.'),
        ('version_identity','version','identity constraint / possible source-limited coverage','Inspect deterministic own-product records; no surface-label matching or invented identity.'),
        ('evidence_binding','evidence','non-negotiable evidence constraint; possible implementation defects require exact proof','Review literal-binding diagnostics and selected source identity before considering a narrowly proven implementation correction.')]:
        affected=[h for h in held if any(pattern in r['reason'] for r in h['reasonsByStage'])]
        if affected:hypotheses.append(dict(id=key,classification=classification,affectedAssertions=len(affected),affectedOwners=len({h['ownerID'] for h in affected}),
            literalBoundSelectedUniqueSubset=sum(all(h['shadowLiteralOnly'][k] for k in ('allFragmentsUnique','allFragmentsSelected','allFragmentsOriginallyLiteralBound')) for h in affected),
            recoverableAcceptedAssertions='undetermined; affected and literal-bound counts are not admission predictions',risk='A literal match does not prove semantic support, visible content, endpoint identity or a valid parent chain.',recommendation=action))
    abst_strata=Counter((a['family'],a['groupID'],a['inventoryId'],a['disposition']) for a in absts)
    reason_counts=Counter(a['reason'] for a in absts)
    concentration=[]
    for owner,gs in by_owner.items():
        aa=[a for g in gs for a in g['abstentions']];cc=sum(g['candidates']['nodes']+g['candidates']['edges'] for g in gs)
        concentration.append(dict(ownerID=owner,family=gs[0]['family'],abstentions=len(aa),candidates=cc,
            uniqueReasons=len({a['reason'] for a in aa}),uniqueTargets=len({a['inventoryId'] for a in aa})))
    # Intern model-authored reasons/scopes to keep all 11,017 records without repeated long text.
    reason_values=sorted(reason_counts);reason_index={s:i for i,s in enumerate(reason_values)}
    scopes=sorted({tuple(a['sourceUnitIDs']) for a in absts});scope_index={s:i for i,s in enumerate(scopes)}
    compact_abst=[{**{k:v for k,v in a.items() if k not in ('reason','sourceUnitIDs')},'reasonIndex':reason_index[a['reason']],
                  'scopeIndex':scope_index[tuple(a['sourceUnitIDs'])]} for a in absts]
    uncertain=[h for h in held if any('full_content_not_static_visible:uncertain'==r['reason'] for r in h['reasonsByStage'])]
    strata=[]
    for family,group in sorted({(g['family'],g['groupID']) for g in groups}):
        subset=[g for g in groups if (g['family'],g['groupID'])==(family,group)]
        dispositions=Counter()
        for g in subset:dispositions.update(g['decisions'])
        strata.append(dict(family=family,groupID=group,requests=len(subset),
            zeroYieldRequests=sum(g['zeroYield'] for g in subset),
            held=sum(len(g['held']) for g in subset),abstentions=sum(len(g['abstentions']) for g in subset),
            candidateNodes=sum(g['candidates']['nodes'] for g in subset),
            candidateEdges=sum(g['candidates']['edges'] for g in subset),decisions=dict(dispositions)))
    root_summary=dict(independentReasonCounts=dict(Counter(r for h in held for r in h['independentLocalRootReasons'])),
        propagatedOnlyAssertions=sum(not h['independentLocalRootReasons'] and bool(h['dependencyTrace']['rootCauses']) for h in held),
        unclassifiedRootAssertions=sum(not h['dependencyTrace']['rootCauses'] for h in held))
    result=dict(version='source-local-scientific-coverage-diagnostic/1',sourceSummarySha256=summary_sha,
        implementationSha256=digest(Path(__file__).read_bytes()),
        reconciliation=dict(groups=1005,owners=len(by_owner),held=1971,validAbstentions=11017,zeroYieldOwners=53,cohortOwners=14,cohortHeld=610),
        held=held,heldReasonInventory=reasons,rootSummary=root_summary,groupStrata=strata,zeroYieldOwners=zeros,
        queueSha256=review.retry.QUEUE_SHA,
        inputPartHashes={f'{i:02d}.json':digest((destination/'parts'/f'{i:02d}.json').read_bytes()) for i in range(11)},
        cohort=dict(ownerIDs=sorted(cohort),heldAssertions=610,
            reasonCounts=dict(Counter(r for h in cohort_held for r in set(x['reason'] for x in h['reasonsByStage']))),
            sameUncertainVisibilityCauseOutsideCohort=dict(assertions=sum(h['ownerID'] not in cohort for h in uncertain),owners=len({h['ownerID'] for h in uncertain}-cohort))),
        abstentions=dict(records=compact_abst,reasons=reason_values,scopes=scopes,
            strata=[dict(family=k[0],groupID=k[1],inventoryId=k[2],disposition=k[3],count=v) for k,v in sorted(abst_strata.items())],
            mostRepeatedReasons=[dict(reason=k,count=v) for k,v in reason_counts.most_common(25)],
            ownerConcentrations=sorted(concentration,key=lambda x:(-x['abstentions'],x['ownerID'])),potentialScopeConflicts=conflicts),
        sourceScope=dict(missingSelectedUnitGroups=sum(bool(g['missingSelectedUnits']) for g in groups),
            unselectedUnitGroups=sum(bool(g['unselectedUnits']) for g in groups),
            sourceUnitsByOwner={oid:list({s['sourceUnitID']:s for g in gs for s in g['sources']}.values()) for oid,gs in by_owner.items()}),
        contextIndicators=dict(emptyCitedScopes=sum(a['citedScopeCharacters']==0 for a in absts),
            shortCitedScopesUnder200Chars=sum(a['citedScopeCharacters']<200 for a in absts),
            interpretation='Size flags are screening heuristics, not proof of context insufficiency or legitimate absence.'),
        hypotheses=hypotheses,limitations=[
            'Abstentions are model-authored assertions of absence/ambiguity, not measured recall or independently established legitimacy.',
            'Same-target positive/abstention overlap may concern different entities or senses; it is a review flag, not proven contradiction.',
            'Complete selected-unit inclusion does not establish upstream corpus completeness or adequate scientific context.',
            'Root labels are diagnostic classifications over preserved multi-stage reasons; all exact reasons and dependency paths remain available.',
            'Shadow checks only inspect existing literal/identity records; no visibility gate, parent gate or acceptance rule is waived.'],providerCalls=0,acceptanceChanges=0)
    review.retry.files.seal(destination/'diagnostic.json',result)
    lines=['# Scientific coverage and information-loss diagnosis','',
        'Technical validation completion does not establish scientific extraction completion. No acceptance changes were made.','',
        'Reconciled: **1,971 held assertions; 11,017 valid abstentions; 53 zero-yield owners; 1,005 groups / 335 owners**.','',
        '## Demonstrated mechanisms','',
        '- The Hub lexical classifier treats non-self-closing HTML void elements as open containers and marks unclosed stacks uncertain through end-of-source. Mismatched closing tags can mark from offset zero. Synthetic tests establish the mechanism; individual source visibility still requires inspection.',
        '- Parent/dependency losses are traced to held ancestors. Reasons co-occurring on an assertion are preserved, not collapsed to resolutionStatus.',
        '- Abstention overlap flags require scientific review: the same inventory target can legitimately refer to different entities. They do not establish omissions.','',
        'Classifier evidence: `src/extraction/llm/source_local_hub_evidence.py:86-101`. Interpretive release and dependency gates: `src/extraction/llm/construction_acceptance.py`.','',
        '## Group distributions','', 'Counts are diagnostic, not recall estimates; accepted group records may repeat across groups.',
        '','| Family / group | Requests | Held | Abstentions | Zero yield |','|---|---:|---:|---:|---:|',
        *[f"| {x['family']} / {x['groupID']} | {x['requests']} | {x['held']} | {x['abstentions']} | {x['zeroYieldRequests']} |" for x in strata],
        '', '## Independent roots and propagation','',json.dumps(root_summary,indent=2),'',
        '## Prioritized investigation','']
    for h in hypotheses:
        lines.append(f"- **{h['id']}**: {h['affectedAssertions']} assertions / {h['affectedOwners']} owners; {h['literalBoundSelectedUniqueSubset']} have selected, uniquely located, originally literal-bound fragments. {h['recommendation']} Recoverable accepted yield remains undetermined.")
    lines+=['','## Fourteen-owner Hub cohort','',json.dumps(result['cohort'],indent=2),'',
        '## Zero-yield patterns','',json.dumps(dict(Counter(z['family']+':'+z['pattern'] for z in zeros)),indent=2),'',
        '## Frequent multi-stage reasons','', '| Reason | Assertions | Owners |','|---|---:|---:|']
    for reason,v in sorted(reasons.items(),key=lambda x:-x[1]['count'])[:20]:lines.append(f"| {reason} | {v['count']} | {len(v['owners'])} |")
    lines+=['','## Representative evidence pointers','']
    for h in sorted(held,key=lambda x:(x['family'],x['ownerID'],x['candidateID']))[:3]+cohort_held[:3]:
        lines.append(f"- `{h['ownerID']}` / `{h['requestID']}` / `{h['candidateID']}`: {h['blockingReasons']}; evidence refs: "+json.dumps(h['evidence'][:1]))
    lines+=['','## Limits and next decision','',*['- '+s for s in result['limitations']],
        '',f"There are {len(conflicts)} same-owner/target/source-scope abstention overlap flags. Review selected examples against original source spans before considering prompt or policy changes.",
        '', 'First inspect lexical visibility failures with exact offsets; then trace residual parent/endpoint holds; finally audit stratified abstentions, including no-candidate sources. Do not rerun extraction or declare scientific completion from these counts.']
    with (destination/'report.md').open('x') as handle:handle.write('\n'.join(lines)+'\n')
    return result['reconciliation']


def scientific_synthesis(data):
    """Summarize source-linked hypotheses without converting screening counts to yield."""
    held=data['held'];units=data['sourceScope']['sourceUnitsByOwner'];cohort=data['cohort']['ownerIDs']
    categories=[
        ('visibility_uncertain','full_content_not_static_visible:',
         'Mixed implementation limitation and intentional visibility constraint. HTML void-tag/unmatched-close contamination is demonstrated; dynamic, example and code spans require separate scientific review.'),
        ('dataset_identity','exact_source_identifier_required',
         'Intentional exact-identifier constraint. Named-only DatasetResource output may have been better modeled as DatasetMention, but changing the authentic type is not an offline repair.'),
        ('identifier_binding','supplied_identifier_not_bound',
         'Evidence/identity constraint. Inspect exact identifier support; never invent or normalize model identifiers to admit them.'),
        ('authority_identity','full_authority_identity_mismatch',
         'Hard authority/identity conflict. Inspect the supplied endpoint and source; no canonical identity override is justified by this diagnostic.'),
        ('method_resolution','step14_method_resolution_not_authorized',
         'Intentional Method identity policy. Preserve positive unresolved evidence; a change requires researcher authority and must not fabricate a Publication Method.'),
        ('purpose_diagnostics','purpose',
         'Authorized unclassified/ambiguous non-KG diagnostics. Successful validation is expected to retain these holds, not promote them.'),
        ('literal_quote','evidence_quote_unbound',
         'Hard evidence constraint. Candidate output and source require manual inspection; never repair authentic quote text.'),
        ('parent_path','parent_path',
         'Dependency/structural constraint. Trace missing edges and independently supported parents; parent gates cannot be waived.'),
        ('parameter_prose','parameter_explanatory_prose_required',
         'Evidence-form constraint that can be secondary to failed visibility. Inspect both the quote and its visibility ancestor before attributing this to model omission.')]
    hypotheses=[]
    for name,needle,meaning in categories:
        roots={(h['requestID'],h['candidateID']) for h in held if any(needle in r for r in h['independentLocalRootReasons'])}
        impacted=[h for h in held if any((h['requestID'],r['candidateID']) in roots for r in h['dependencyTrace']['rootCauses'])]
        hypotheses.append(dict(category=name,independentAssertions=len(roots),includingDependencyConsequences=len(impacted),
            owners=len({h['ownerID'] for h in impacted}),interpretation=meaning,
            recoverableCoverage='Undetermined: diagnostic upper screening set, not a predicted number of admissible assertions.',
            representatives=[dict(ownerID=h['ownerID'],requestID=h['requestID'],candidateID=h['candidateID'],
                reasons=h['independentLocalRootReasons'],evidence=h['evidence'][:1]) for h in impacted[:2]]))
    cohort_sources=[s for owner in cohort for s in units[owner]]
    zero_sources=[(z,sum(s['characters'] for s in z['sources'])) for z in data['zeroYieldOwners'] if z['pattern']=='only_abstentions_no_candidates']
    ordered=sorted(zero_sources,key=lambda item:(item[1],item[0]['ownerID']))
    samples=[]
    # Deliberately inspect shortest, median and longest rather than infer absence from size.
    for index in (0,len(ordered)//2,len(ordered)-1):
        z,size=ordered[index];samples.append(dict(ownerID=z['ownerID'],family=z['family'],characters=size,
            validAbstentions=z['validAbstentions'],sources=[dict(sourceUnitID=s['sourceUnitID'],sha256=s['sourceTextSha256']) for s in z['sources']]))
    return dict(hypotheses=hypotheses,
        cohortCharacteristics=dict(owners=len(cohort),minimumUncertainFraction=min(s['uncertainFraction'] for s in cohort_sources),
            fullyUncertainSources=sum(s['uncertainFraction']==1 for s in cohort_sources),
            sourcesWithNonSelfClosingVoidTags=sum(s['lexicalSignals']['unclosedHtmlVoidTags']>0 for s in cohort_sources),
            sourcesWithJSXComponents=sum(s['lexicalSignals']['jsxComponents']>0 for s in cohort_sources),
            interpretation='Shared lexical uncertainty is established; these correlated syntax signals do not prove identical causes or renderability.'),
        zeroCandidateSourceSamples=samples,
        positiveAbstentionOverlapExamples=data['abstentions']['potentialScopeConflicts'][:5],
        sourceScope=data['contextIndicators'],
        priority='First investigate static MDX visibility localization, then residual parent/identity holds; review abstentions using source-stratified human inspection before proposing new generation.',
        acceptanceChanges=0,providerCalls=0)


def synthesis():
    """Write a compact additional synthesis, preserving the completed diagnostic records."""
    destination=ROOT/DEST
    require(not (destination/'synthesis.json').exists() and not (destination/'synthesis.md').exists(),'OUTPUT_ALREADY_EXISTS')
    data,sha=read_json(destination/'diagnostic.json');result=scientific_synthesis(data)
    result['diagnosticSha256']=sha
    lines=['# Evidence-backed scientific synthesis','',result['priority'],'',
        '## Source context and zero yield','',
        'No selected units are missing from the prepared group contexts. This establishes selected-input inclusion, not upstream source completeness. All 39 no-candidate owners abstained; their missing output precedes candidate acceptance. In contrast, the 14 held-only owners demonstrate validation-induced loss of model-proposed information.',
        '',json.dumps(result['cohortCharacteristics'],indent=2),'',
        'All 14 cohort pages contain JSX components; 10 also contain non-self-closing HTML void tags. Syntax correlation is not proof that all spans are static. Prioritize exact prose-span inspection, especially FIMserv (`hub:page:103555bceed0fdd50c00`), whose 68 assertions are held and whose entire 11,526-character input is marked uncertain.',
        '', 'The shortest/median/longest no-candidate source samples below distinguish sparse context from longer inputs with unexplained absence. Neither proves a missed ontology assertion:',
        '',json.dumps(result['zeroCandidateSourceSamples'],indent=2),'','## Correction hypotheses and risks','',
        'Counts overlap across hypotheses. Dependency-inclusive counts are screening sets, not recovery estimates. No hypothetical result has been accepted.']
    for row in result['hypotheses']:
        lines += ['',f"### {row['category']}",'',f"{row['independentAssertions']} independent candidate roots; {row['includingDependencyConsequences']} assertions including dependency consequences; {row['owners']} owners. {row['interpretation']} {row['recoverableCoverage']}",
                  '',json.dumps(row['representatives'],indent=2)]
    lines+=['','## Abstention evidence and concentration','',
        f"All 11,017 valid abstentions retain exact authored reasons and cited scopes in diagnostic.json. There are no empty cited scopes; {data['contextIndicators']['shortCitedScopesUnder200Chars']} cite fewer than 200 characters. These are evidence-sufficiency screening flags, not invalid abstentions.",
        '', 'The largest owner totals are 44 abstentions across 44 targets. Repeated negative formulations and near-universal target abstentions may reflect the broad fixed inventory rather than model failure. For example, A-DOM07e has 242 no-evidence abstentions in Hub scientific-occurrences requests. A human source sample is necessary to distinguish genuine rarity from systematic omission.',
        '', 'Most repeated exact authored reasons:', '',json.dumps(data['abstentions']['mostRepeatedReasons'][:8],indent=2),
        '', 'The 66 scope overlaps identify positives and abstentions for the same owner/target/source. Entity-specific absence can coexist with another positive entity; inspect the exact authored reason before treating a flag as a contradiction. Representative references:',
        '',json.dumps(result['positiveAbstentionOverlapExamples'],indent=2),'',
        '## Scientific recommendation','',
        '1. Investigate the proven MDX lexical overreach first using original quotes and offsets. This has the largest demonstrated validation-loss footprint and requires no new generation. Preserve hard exclusions for genuinely dynamic/code-only/uncertain evidence; correct only reproduced localization defects after researcher approval.',
        '2. Trace remaining parent/endpoint constraints after any approved visibility correction. Retain unresolved methods, exact identity conflicts and ambiguous-purpose diagnostics. Mixed prose/example fragments may require an evidence-policy decision, not a parser change.',
        '3. Review a stratified sample of no-candidate owners, short source scopes, high-frequency target absences and scope overlaps. Existing model outputs cannot establish unexpressed positives or empirical recall. Request additional generation only if source-grounded inspection demonstrates omission.',
        '', 'No new model output, shadow acceptance, KG write, or scientific completion claim is made.']
    review.retry.files.seal(destination/'synthesis.json',result)
    with (destination/'synthesis.md').open('x') as handle:handle.write('\n'.join(lines)+'\n')
    return dict(diagnosticSha256=sha,hypotheses=len(result['hypotheses']))


def main():
    """Run one bounded shard or final aggregation; all sockets blocked."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['shard','finish','synthesis']);parser.add_argument('--part',type=int,default=0)
    args=parser.parse_args();require(0<=args.part<=10,'INVALID_SHARD')
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        if args.stage=='synthesis':print(json.dumps(synthesis()))
        elif args.stage=='finish':print(json.dumps(finish()))
        else:
            path=ROOT/DEST/'parts'/f'{args.part:02d}.json';require(not path.exists(),'SHARD_ALREADY_EXISTS')
            value=shard(args.part);path.parent.mkdir(parents=True,exist_ok=True);review.retry.files.seal(path,value)
            print(json.dumps(dict(part=args.part,groups=len(value['groups']))))


if __name__=='__main__':main()
