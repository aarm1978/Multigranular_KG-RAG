"""Bounded read-only attribution of v3 residual visibility holds; no semantic replay."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import inspect
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch
from src.evaluation import source_local_supplemental_review_v3 as review
from src.extraction.llm import source_local_hub_evidence_v044 as classifier

ROOT=review.old.retry.ROOT
OUTPUT=Path('var/study2_step13/source-local-visibility-residual-diagnostic/v1')
UNCERTAIN='full_content_not_static_visible:uncertain'
MIXED='full_content_not_static_visible:example,prose'
require,digest=review.require,review.digest


def trace_regions(text):
    """Observe original mark calls without replacing the scanner or changing its output."""
    events=[];previous=sys.getprofile()
    def observe(frame,event,arg):
        if event!='call' or frame.f_code.co_name!='mark' or frame.f_code.co_filename!=classifier.__file__:return
        a=frame.f_locals;c=frame.f_back.f_locals
        events.append(dict(start=a['lo'],end=a['hi'],kind=a['kind'],classifierLine=frame.f_back.f_lineno,
            name=c.get('name'),stack=[list(x) for x in c.get('stack',[])],
            operation=inspect.getframeinfo(frame.f_back,context=1).code_context[0].strip()))
    sys.setprofile(observe)
    try:marks=classifier.regions(text)
    finally:sys.setprofile(previous)
    # Replay mark operations only to establish exact attribution, not evidence admissibility.
    rebuilt=['prose']*len(text);writers=[None]*len(text)
    for index,event in enumerate(events):
        lo,hi=event['start'],event['end'];rebuilt[lo:hi]=[event['kind']]*(hi-lo);writers[lo:hi]=[index]*(hi-lo)
    require(rebuilt==marks,'TRACE_ATTRIBUTION_DRIFT')
    return marks,writers,events


def mechanism(event,text):
    """Classify the executed scanner mechanism, not the truth of a proposed assertion."""
    op=event['operation'];start=event['start']
    if 'mark(0,end' in op:return 'mismatched_close_prefix_contamination'
    if 'for _,opening,_ in stack' in op:
        if text.startswith(('<https://','<http://'),start):return 'markdown_autolink_misparsed_as_tag'
        if start and text[start-1]=='\\':return 'escaped_angle_placeholder_misparsed_as_tag'
        return 'unclosed_admonition' if text.startswith(':::',start) else 'unclosed_markup_scope'
    if 'if not opened_safe' in op:
        tag=text[start:text.find('>',start)+1]
        if event['name'] in classifier.STATIC_TAGS:
            return 'closed_html_expression_attributes' if '{' in tag else 'closed_html_unsupported_attributes'
        return 'closed_unknown_component_or_html'
    if 'if not safe:mark(opening' in op:return 'unsupported_admonition'
    if "'example' if closed else 'uncertain'" in op:return 'unclosed_fenced_block'
    if "mark(i,end,'markup' if safe else 'uncertain')" in op:return 'opaque_tag_itself'
    return 'uncertain_syntax_other'


def primary(mechanisms,targets):
    """Use a fixed exclusive priority; retain every co-occurring mechanism separately."""
    order=['markdown_autolink_misparsed_as_tag','escaped_angle_placeholder_misparsed_as_tag','mismatched_close_prefix_contamination','unclosed_admonition','unclosed_markup_scope',
           'unclosed_fenced_block','closed_html_expression_attributes','closed_unknown_component_or_html',
           'closed_html_unsupported_attributes','opaque_tag_itself','unsupported_admonition','uncertain_syntax_other']
    if mechanisms:return next(x for x in order if x in mechanisms)
    return 'mixed_displayed_example_contract_form' if targets in {'A-DC08','C-DC12'} else 'mixed_prose_code_other_target'


def load_inputs():
    """Verify original queue and the completed v3 review references used by this diagnosis."""
    qroot=ROOT/review.old.retry.QUEUE;raw=(qroot/'queue-manifest.json').read_bytes()
    require(digest(raw)==review.old.retry.QUEUE_SHA,'QUEUE_DRIFT');queue=json.loads(raw)
    manifest=json.loads((ROOT/review.OUTPUT/'selection-manifest.json').read_bytes())
    classifier_path=str(Path(classifier.__file__).relative_to(ROOT))
    require(digest(Path(classifier.__file__).read_bytes())==manifest['correctedImplementationHashes'][classifier_path],'CLASSIFIER_IMPLEMENTATION_DRIFT')
    historical_path='src/extraction/llm/source_local_hub_evidence.py'
    require(digest((ROOT/historical_path).read_bytes())==queue['implementationPins'][historical_path],'HISTORICAL_CLASSIFIER_DRIFT')
    comparison=json.loads((ROOT/review.OUTPUT/'comparison.json').read_bytes())
    summary=json.loads((ROOT/review.OUTPUT/'summary.json').read_bytes())
    require(summary['decisionDispositions']=={'accepted':7846,'held':1722,'suppressed_duplicate':41},'V3_COUNTS_DRIFT')
    require(sum(any(r.startswith('full_content_not_static_visible:') for r in h['independentReasons']) for h in comparison['remainingHeld'])==1093,'DIRECT_VISIBILITY_COUNT_DRIFT')
    require(sum(not h['independentReasons'] and any(r['reason'].startswith('full_content_not_static_visible:') for r in h['dependencies']['rootCauses']) for h in comparison['remainingHeld'])==443,'PROPAGATED_VISIBILITY_COUNT_DRIFT')
    selected=[]
    for h in comparison['remainingHeld']:
        reasons={r['reason'] for r in h['reasonsByStage']}
        if UNCERTAIN in reasons or MIXED in reasons:selected.append(h)
    require(sum(UNCERTAIN in {r['reason'] for r in h['reasonsByStage']} for h in selected)==489,'UNCERTAIN_COUNT_DRIFT')
    require(sum(MIXED in {r['reason'] for r in h['reasonsByStage']} for h in selected)==243,'MIXED_COUNT_DRIFT')
    return queue,comparison,selected


def scan(part):
    """Read at most 25 selected group reports; examine exact saved sources and candidates."""
    queue,comparison,selected=load_inputs();by_request=defaultdict(list)
    for h in selected:by_request[h['requestID']].append(h)
    entries={e['identity']['requestID']:e for e in queue['requests']};ids=sorted(by_request)[part*25:(part+1)*25]
    require(bool(ids),'EMPTY_PART');rows=[];sources={};hashes={};cache={}
    for rid in ids:
        entry=entries[rid];raw=(ROOT/review.old.retry.QUEUE/'queue'/entry['bundleFile']).read_bytes()
        require(digest(raw)==entry['bundleSha256'],'BUNDLE_DRIFT');p=json.loads(raw)
        require(review.old.retry.adapter.fingerprint(p)==entry['identity'],'REQUEST_IDENTITY_DRIFT')
        path=ROOT/review.OUTPUT/'groups'/(digest(rid.encode())+'.json');report=review.v2.checked(path)
        hashes[str(path.relative_to(ROOT))]=digest(path.read_bytes())
        require(report['requestID']==rid and digest(bytes.fromhex(report['responseBytesHex']))==report['responseSha256'],'RESPONSE_DRIFT')
        native=report['nativeValidationView'];body=p['requestInputs']['baseContext']['semanticRequest']['request']
        require(body==native['originalReplay']['requestResult']['request'],'SOURCE_CONTEXT_DRIFT')
        units={u['sourceUnitID']:u for u in body['sourceUnits']}
        checks={c['candidateID']:c for c in native['originalReplay']['validationResult']['candidateChecks']}
        decisions={d['candidateID']:d for d in native['decisions']}
        for h in by_request[rid]:
            c=checks[h['candidateID']];require(decisions[h['candidateID']]['disposition']=='held','HELD_ASSOCIATION_DRIFT')
            fragments=[];mechanisms=set()
            for i,e in enumerate(c['originalCandidate']['evidence']):
                uid=e['sourceUnitID'];text=units[uid]['text'];sha=digest(text.encode())
                if sha not in cache:cache[sha]=trace_regions(text)
                marks,writers,events=cache[sha];source_key=uid
                if source_key not in sources:
                    sources[source_key]=dict(ownerID=h['ownerID'],textSha256=sha,characters=len(text),uncertainCharacters=marks.count('uncertain'),
                        uncertainEvents=[dict(eventID=j,**ev,mechanism=mechanism(ev,text),openingExcerpt=text[ev['start']:ev['start']+180],
                            closingExcerpt=text[max(ev['start'],ev['end']-100):ev['end']]) for j,ev in enumerate(events) if ev['kind']=='uncertain'])
                quote=e['evidenceText'];count=text.count(quote) if quote else 0
                binding=c['evidenceBindings'][i]['binding']
                # Reuse only the native literal locator, including authentic locatorAnchor.
                # This is not semantic validation, construction projection or acceptance.
                from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans
                bound,location=bind_evidence_spans({'evidenceSpans':[{k:e[k] for k in ('evidenceText','locatorAnchor') if k in e}]},
                    dict(text=text,startOffsetInDocument=0,canonicalArtifactID=h['ownerID'],sourceUnitID=uid,textHash=sha,sectionID=None,sectionTitleRaw=None))
                require(location==binding['bindingReport'],'LITERAL_BINDING_REPORT_DRIFT')
                offset=bound['evidenceSpans'][0]['startOffsetInDocument'] if location['bindingStatus']=='bound' else None
                eventids=[];kinds={};prose=''
                if offset is not None:
                    positions=range(offset,offset+len(quote));kinds=dict(Counter(marks[k] for k in positions if not text[k].isspace()))
                    eventids=sorted({writers[k] for k in positions if marks[k]=='uncertain' and writers[k] is not None})
                    mechanisms.update(mechanism(events[j],text) for j in eventids)
                    prose=''.join(text[k] if marks[k]=='prose' else ' ' for k in positions).strip()[:300]
                fragments.append(dict(sourceUnitID=uid,sourceTextSha256=sha,evidenceSha256=digest(quote.encode()),
                    originalOffset=offset,endOffset=None if offset is None else offset+len(quote),literalOccurrences=count,
                    bindingStatus=binding.get('bindingReport',{}).get('bindingStatus'),kinds=kinds,uncertainEventIDs=eventids,
                    quoteExcerpt=quote[:320],explanatoryProseExcerpt=prose))
            target=h['inventoryId'];reasons={r['reason'] for r in h['reasonsByStage']}
            category=primary(mechanisms,target) if all(f['originalOffset'] is not None for f in fragments) else 'ambiguous_literal_location'
            nonvisibility=[r for r in h['independentReasons'] if not r.startswith('full_content_not_static_visible:')]
            deps=review.diagnostic.dependency_graph(checks)[h['candidateID']]
            rows.append(dict(requestID=rid,candidateID=h['candidateID'],ownerID=h['ownerID'],groupID=h['groupID'],inventoryId=target,
                population=[name for name,reason in [('uncertain',UNCERTAIN),('mixed',MIXED)] if reason in reasons],
                primary=category,cooccurringMechanisms=sorted(mechanisms),fragments=fragments,
                independentReasons=h['independentReasons'],otherIndependentConditions=nonvisibility,reasonsByStage=h['reasonsByStage'],
                dependencyRoots=h['dependencies'],immediateDependencyDispositions={x:decisions.get(x,{}).get('disposition','missing') for x in deps},
                parentPath=c['originalCandidate'].get('parentPath',[]),parentPathStructurallyLinked=c.get('parentPathStructurallyLinked'),
                semanticValidity='not established by this diagnostic'))
    return dict(part=part,rows=rows,sources=sources,groupHashes=hashes,totalParts=(len(by_request)+24)//25)


GUIDANCE={
 'markdown_autolink_misparsed_as_tag':('A','Narrow technical Markdown-autolink tokenization correction; keep link-only semantic restrictions','No amendment for lexical scope recognition'),
 'escaped_angle_placeholder_misparsed_as_tag':('A','Narrow technical escape recognition; never infer executable behavior from a placeholder','No amendment for lexical scope recognition'),
 'mismatched_close_prefix_contamination':('A/E','Narrow technical localization investigation; no automatic acceptance','No amendment for proven unrelated-prefix overreach; malformed source regions stay held'),
 'closed_html_unsupported_attributes':('B/E','Retain unresolved; any additional static-attribute allowance needs explicit approval','Prospective scope clarification required: CSS visibility is not established'),
 'closed_html_expression_attributes':('C/E','Preserve hold: expression-valued attributes are outside approved visible evidence','Amendment required to expand; not recommended here'),
 'closed_unknown_component_or_html':('C/E','Preserve unknown-visibility hold; distinguish native HTML from custom JSX in case inspection','No blanket component allowance; amendment needed for wider eligibility'),
 'unclosed_admonition':('C/E','Retain malformed-container hold and document missing source boundary','No technical recovery boundary is demonstrated'),
 'unclosed_markup_scope':('C/E','Retain ambiguous malformed/unsupported scope; do not infer a closing boundary','No blanket repair justified'),
 'mixed_displayed_example_contract_form':('B','Narrow target-specific technical correction for documented Example/hasExample evidence form, preserving parent and independent support checks','No amendment to permit the documented form; accepting code-derived meaning would require one and is not recommended'),
 'mixed_prose_code_other_target':('C/E','Keep hold unless original prose independently supports the proposed target; do not repair quotes or infer executed behavior','No general mixed-code relaxation justified'),
}


def finish():
    """Reconcile the complete target population and write compact immutable diagnostics."""
    dest=ROOT/OUTPUT;require(not (dest/'diagnostic.json').exists(),'OUTPUT_ALREADY_EXISTS')
    queue,comparison,selected=load_inputs();parts=sorted((dest/'parts-exact').glob('*.json'))
    values=[json.loads(p.read_bytes()) for p in parts]
    require(values and len(values)==values[0]['totalParts'] and {v['part'] for v in values}==set(range(len(values))),'PART_COVERAGE_DRIFT')
    rows=[r for v in values for r in v['rows']];keys=lambda rs:{(r['requestID'],r['candidateID']) for r in rs}
    require(len(rows)==len(keys(rows)) and keys(rows)==keys(selected),'CANDIDATE_COVERAGE_DRIFT')
    sources={k:v for part in values for k,v in part['sources'].items()};groups=defaultdict(list)
    for r in rows:groups[r['primary']].append(r)
    summaries=[]
    for category,rr in sorted(groups.items()):
        roots=keys(rr);affected=[h for h in comparison['remainingHeld'] if any((h['requestID'],x['candidateID']) in roots for x in h['dependencies']['rootCauses'])]
        summaries.append(dict(primary=category,candidates=len(rr),owners=len({r['ownerID'] for r in rr}),
            targets=dict(Counter(r['inventoryId'] for r in rr)),groups=dict(Counter(r['groupID'] for r in rr)),
            otherIndependentConditions=dict(Counter(c for r in rr for c in r['otherIndependentConditions'])),
            dependencyReachIncludingRoots=len(affected),guidance=GUIDANCE.get(category,('E','Retain unresolved','Not determined'))))
    # One per mechanism, all seven held-only owners, and contrasted mixed targets, <=24 distinct records.
    representatives=[];seen=set()
    def add(row):
        k=(row['requestID'],row['candidateID'])
        if k not in seen and len(representatives)<24:seen.add(k);representatives.append(row)
    for rr in groups.values():add(sorted(rr,key=lambda r:(bool(r['otherIndependentConditions']),r['ownerID'],r['candidateID']))[0])
    cohort=comparison['remainingCandidateBearingZeroYieldOwners'];require(len(cohort)==7,'COHORT_DRIFT')
    for owner in cohort:add(next(r for r in rows if r['ownerID']==owner))
    mixed=[r for r in rows if 'mixed' in r['population']]
    for target in sorted({r['inventoryId'] for r in mixed}):add(next(r for r in mixed if r['inventoryId']==target))
    for r in mixed:
        if r['inventoryId']=='C-DC12' and all(d in {'accepted','suppressed_duplicate'} for d in r['immediateDependencyDispositions'].values()):add(r);break
    result=dict(version='residual-visibility-diagnostic/1',reconciliation=dict(uncertain=sum('uncertain' in r['population'] for r in rows),mixed=len(mixed),
        mixedHasExample=sum(r['inventoryId']=='C-DC12' for r in mixed),distinctCandidates=len(rows),heldOnlyOwners=7,
        heldOnlyOwnerAssertions=sum(h['ownerID'] in cohort for h in comparison['remainingHeld'])),
        primaryClasses=summaries,records=rows,sources=sources,cohortOwners=cohort,
        cohortSummary=[dict(ownerID=o,held=sum(h['ownerID']==o for h in comparison['remainingHeld']),primary=dict(Counter(r['primary'] for r in rows if r['ownerID']==o))) for o in cohort],
        mixedParentScreen=dict(hasExampleWithAllImmediateDependenciesAdmitted=sum(r['inventoryId']=='C-DC12' and all(d in {'accepted','suppressed_duplicate'} for d in r['immediateDependencyDispositions'].values()) for r in mixed),
            interpretation='Dependency disposition is not proof of example attachment, independent semantic support, or recoverability'),
        inputHashes={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in [ROOT/review.OUTPUT/'comparison.json',ROOT/review.OUTPUT/'summary.json',ROOT/review.OUTPUT/'selection-manifest.json',ROOT/review.diagnostic.DEST/'diagnostic.json',Path(__file__),Path(classifier.__file__)]},
        groupHashes={k:v for part in values for k,v in part['groupHashes'].items()},providerCalls=0,replays=0,acceptanceChanges=0)
    require(result['reconciliation']['uncertain']==489 and len(mixed)==243 and result['reconciliation']['mixedHasExample']==124 and result['reconciliation']['heldOnlyOwnerAssertions']==298,'RECONCILIATION_DRIFT')
    review.old.retry.files.seal(dest/'diagnostic.json',result);review.old.retry.files.seal(dest/'representatives.json',representatives)
    return result


def synthesis():
    """Write an evidence-backed bounded synthesis; inspect parent records, never replay them."""
    dest=ROOT/OUTPUT;require(not (dest/'synthesis.md').exists(),'OUTPUT_ALREADY_EXISTS')
    result=json.loads((dest/'diagnostic.json').read_bytes());reps=json.loads((dest/'representatives.json').read_bytes())
    parents=[];cache={}
    for r in result['records']:
        if 'mixed' not in r['population'] or r['inventoryId']!='C-DC12':continue
        rid=r['requestID'];path=ROOT/review.OUTPUT/'groups'/(digest(rid.encode())+'.json')
        if rid not in cache:
            require(digest(path.read_bytes())==result['groupHashes'][str(path.relative_to(ROOT))],'PARENT_REPORT_DRIFT')
            cache[rid]=review.v2.checked(path)['nativeValidationView']
        n=cache[rid];checks={c['candidateID']:c for c in n['originalReplay']['validationResult']['candidateChecks']};decisions={d['candidateID']:d for d in n['decisions']}
        edge=checks[r['candidateID']]['originalCandidate'];source=edge['source'];target=edge['target']
        source_id=source['referenceID'];target_id=target['referenceID'];child=checks.get(target_id,{})
        path_ids=[x['referenceID'] for x in child.get('originalCandidate',{}).get('parentPath',[]) if x['referenceType']=='candidate_edge' and x['referenceID']!=r['candidateID']]
        parents.append(dict(requestID=rid,candidateID=r['candidateID'],ownerID=r['ownerID'],
            sourceParentID=source_id,sourceParentDisposition=decisions.get(source_id,{}).get('disposition','external_or_missing'),
            pathExcludingOwnAttachment={x:decisions.get(x,{}).get('disposition','missing') for x in path_ids},
            targetExampleID=target_id,targetExampleDecision=decisions.get(target_id),targetParentPathStructurallyLinked=child.get('parentPathStructurallyLinked')))
    admitted={'accepted','suppressed_duplicate'}
    stats=dict(total=len(parents),sourceParentAdmitted=sum(p['sourceParentDisposition'] in admitted for p in parents),
        parentAndPathExceptAttachmentAdmitted=sum(p['sourceParentDisposition'] in admitted and all(x in admitted for x in p['pathExcludingOwnAttachment'].values()) for p in parents),
        targetExampleHeld=sum((p['targetExampleDecision'] or {}).get('disposition')=='held' for p in parents))
    review.old.retry.files.seal(dest/'parent-assessment.json',dict(stats=stats,records=parents,interpretation='Mechanical parent-state screening only, not independent evidence or semantic adjudication'))
    lines=['# Residual Hub visibility investigation','',
        '**Decision:** stop broad exploration. A bounded technical follow-up is justified for Markdown escape/autolink tokenization and the Example-specific mixed-evidence form. Retain unknown/dynamic/malformed-scope holds. Do not make an acceptance change from these diagnostic counts.','',
        '## Authority and reconciliation','',
        'Step 11 v0.3 §5.1 (lines 139–144) permits visible prose and contextually relevant displayed fences, excludes runtime/unknown component visibility, and retains exact content_mdx offsets. §5.2 (lines 156–165) permits substantive Example/hasExample only under admitted Procedure/Step paths with independent evidence. Step 13 policy §§2–4 preserves every hard source, evidence, endpoint and parent requirement. The v0.4.1 source-local contract explicitly retains unknown attributes/components and unbalanced syntax; the v0.4.4 overlay only corrects HTML void scopes.','',
        'V3: 7,846 accepted / 1,722 held, with 247 gains and no accepted losses. This diagnosis reconciles **489 exact uncertain holds + 243 exact mixed example/prose holds = 732 distinct candidates**, including all **124 mixed C-DC12** assertions. The seven candidate-bearing zero-yield owners have **298 holds**. These are selected diagnostic populations, not an accuracy denominator.','',
        '## Mutually exclusive mechanism attribution','',
        'Primary attribution follows the final scanner writes on the exact bound evidence spans, with a fixed priority for multi-fragment cases. All co-occurring scanner events, stage findings, independent conditions and dependency roots remain in diagnostic.json. Native literal binding resolves locatorAnchor when quotes repeat. No semantic validator or construction replay was run.','',
        '| Primary mechanism | Candidates | Owners | Dependency reach including roots | Triage |','|---|---:|---:|---:|---|']
    for c in result['primaryClasses']:lines.append(f"| {c['primary']} | {c['candidates']} | {c['owners']} | {c['dependencyReachIncludingRoots']} | {c['guidance'][0]} |")
    lines+=['','A = demonstrated lexer defect; B = evidence-form implementation narrower than contract; C = justified conservative restriction; D = independent semantic/endpoint/parent deficiency (recorded alongside primary cause); E = scientific visibility/support undetermined. Combined labels express uncertainty, not multiple primary counts. Dependency reach overlaps and must not be summed.','',
        '## What is genuinely wrong','',
        '- **Escaped placeholder:** `hub:page:7477148a6b278533859e`, at offset 2049, contains an escaped angle-bracket job identifier. The scanner ignores the escape and pushes a `jobid` container through end-of-page. This affects 44 candidates (51 including dependency reach). Recognizing the escape is a narrow technical correction; it does not authorize interpreting the job command as executed behavior.',
        '- **Autolink:** `hub:page:13c17be1cc196e0f1eb0`, at offset 3805, contains a complete angle-bracket HTTPS autolink. The scanner instead opens a `https` container through end-of-page, affecting 10 candidates. An autolink cannot enclose later prose. Recognize its lexical boundary while retaining the prohibition on using a URL alone as semantic evidence.',
        '- **Backward contamination:** 46 candidates in two owners receive uncertainty from mismatched closing tags. FIMbench ends with unmatched `</content></invoke>`; the scanner marks from offset zero, including unrelated earlier scientific prose. The other page has malformed/nested details/paragraph structure. Broad prefix contamination is demonstrated, but source malformation remains real. Any correction must establish a safe local boundary and keep the malformed region opaque; no blanket ignore-unknown-closing-tags rule is justified.',
        '- **Mixed evidence form:** the binder accepts pure fenced Example context and pure prose separately, but rejects their union before checking the target-specific Example rule. For 145 Example/hasExample candidates (124 relations, 21 nodes), that blanket form rejection is narrower than Step 11. A bounded target-aware fix is justified under the existing contract, with the same parent and independent attachment checks. This is not evidence that all 145 assertions are semantically supported.','',
        '## What is correctly excluded or remains unresolved','',
        'The 92 expression-attribute cases, 18 literal unsupported-attribute cases and 141 closed unknown-container cases are not demonstrated orphan-scope leakage: their quotes are inside the excluded containers. Static text presence does not establish CSS/component visibility. Unknown JSX and runtime expressions remain excluded. Native figure/figcaption/details and custom Tabs must not be conflated; additional supported-container/attribute rules require explicit researcher clarification of the current conservative contract, not automatic promotion.',
        'The 14 opaque-tag cases concern Repository/implementedBy proposals citing component markup, typically GitHubReadme props. Props can identify a repository mechanically, but they are not by themselves the independent visible scientific implementation claim required by the contract. Preserve these holds; no blanket prop-to-assertion conversion.',
        'The unclosed warning admonition accounts for 96 holds. The authoritative source contains no closing :::; guessing where its scope ends would repair source structure. Another 28 cases lie in unresolved markup scope. Missing delimiters and malformed HTML remain genuine ambiguity even when some interior sentences look ordinary.',
        'The 98 other-target mixed quotes include Procedure/Step instructions, tool names, datasets and a repository. Some instructions have useful prose; others require command/configuration interpretation. Keep them separate from Example eligibility. In particular, a displayed synthetic MPI example is not evidence that a scientific experiment was executed, and a wget command is not independent proof of dataset scientific identity. No executed-result claim is established by this diagnostic.','',
        '## Parent and independent blockers','',
        'Every one of the 124 mixed hasExample candidates has at least one held immediate dependency, but that set can include its Example target or attachment cycle. It must not be confused with an independently bad Procedure/Step parent. Reading the actual parent and path records yields:', '',json.dumps(stats,indent=2),'',
        'See parent-assessment.json for each source parent, target Example decision, and parent path excluding the attachment itself. Parameter prose failures can be downstream of opaque visibility and are not automatically independent semantic defects. required_parent_path_unresolved remains an additional hard finding where present. No parent gate was waived.','',
        '## Seven candidate-bearing zero-yield owners','',
        '| Owner | Held | Primary mechanisms |','|---|---:|---|']
    for o in result['cohortSummary']:lines.append(f"| `{o['ownerID']}` | {o['held']} | {o['primary']} |")
    lines+=['','The 73,901-character Community NextGen page is almost entirely inside a div with expression-valued className; two small policy/cloud pages are inside literal className containers; NGIAB content is inside Tabs/TabItem. These almost-entire-page exclusions are explained by wrapper policy, not residual void-tag errors. FIMbench, the details-based image instructions, and the unclosed warning page have the distinct malformed-scope mechanisms above.','',
        '## Bounded representative evidence','',
        f'{len(reps)} deterministically selected records follow. They illustrate mechanisms, plausible recovery opportunities and justified exclusions; this is not independent human validation or a population sample. Full exact references and all fragments are in representatives.json.']
    for index,r in enumerate(reps,1):
        lines += ['',f"### {index}. {r['primary']}", '',f"`{r['ownerID']}` · `{r['requestID']}` · `{r['candidateID']}` · `{r['inventoryId']}`",'']
        for f in r['fragments'][:2]:
            lines.append(f"Source `{f['sourceUnitID']}`, original offsets [{f['originalOffset']}, {f['endOffset']}), evidence SHA-256 `{f['evidenceSha256']}`. Quotation excerpt: {json.dumps(f['quoteExcerpt'][:220])}")
        lines.append('Additional independent conditions: '+str(r['otherIndependentConditions'])+'; parent/dependency dispositions: '+str(r['immediateDependencyDispositions'])+'.')
    lines+=['','## Recommendation and stopping decision','',
        '1. Authorize only two bounded technical corrections first: escape/autolink lexical boundaries, and target-specific mixed prose/displayed-fence evidence for Example/hasExample. Preserve authentic quotations, unsupported dynamic regions, identity, independent evidence and normal parent closure. Such corrections implement the existing contract; no semantic-policy relaxation is needed.',
        '2. Treat unmatched-close localization as a separate, small malformed-source case. Preserve holds until a defensible bounded failure region is demonstrated. Do not silently delete trailing artifacts or infer closing tags.',
        '3. Do not amend policy merely to recover className/Tabs or malformed-warning populations. A prospective explicitly bounded visibility clarification is necessary if the researcher elects to expand supported static wrappers; the present evidence does not justify blanket visibility claims.',
        '4. Stop this investigation here. Mechanisms and source references are sufficient to decide the narrow follow-up; do not launch a renderer, semantic judge, annotation campaign, provider call or further broad audit. Residual scientific support remains unadjudicated. No precision/recall/F1 or Step 13 completion claim is made.']
    with (dest/'synthesis.md').open('x') as handle:handle.write('\n'.join(lines)+'\n')
    return dict(representatives=len(reps),parentAssessment=stats)


def main():
    """Run bounded source scans or aggregation with sockets blocked throughout."""
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['scan','finish','synthesis']);p.add_argument('--part',type=int,default=0);a=p.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        if a.stage=='synthesis':print(json.dumps(synthesis()))
        elif a.stage=='scan':
            path=ROOT/OUTPUT/'parts-exact'/f'{a.part:02d}.json';require(not path.exists(),'OUTPUT_ALREADY_EXISTS')
            value=scan(a.part);path.parent.mkdir(parents=True,exist_ok=True);review.old.retry.files.seal(path,value)
            print(json.dumps(dict(part=a.part,parts=value['totalParts'],candidates=len(value['rows']))))
        else:
            r=finish();print(json.dumps(dict(reconciliation=r['reconciliation'],classes=r['primaryClasses']),indent=2))


if __name__=='__main__':main()
