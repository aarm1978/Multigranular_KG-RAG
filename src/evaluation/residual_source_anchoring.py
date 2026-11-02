"""Read-only residual source anchoring: no edge emission or semantic adjudication."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import socket
import time
from unittest.mock import patch
import yaml
from src.evaluation.build_step13_pre_alignment import read, checked, require
from src.evaluation.compute_structural_metrics import sha256_file
from src.evaluation.materialize_step13_relationships import closure
from src.extraction.llm.pilot_preflight import canonical, digest

ROOT = Path('var/study2_step13/pre-alignment-metrics/v4')
OUTPUT = Path('var/study2_step13/residual-source-anchoring/v1')
REVIEW = Path('var/study2_step13/source-local-supplemental-review/v4.1')


def classify(family, cls, inventory, eligible, active):
    """Classify mechanical responsibility only; not a semantic-truth decision."""
    if family == 'publications':
        return 'external_bibliographic_stub_unresolved_role'
    if inventory in active:
        return 'possible_missed_authorized_relation_requires_review'
    if cls in eligible:
        return 'evidence_bound_weak_occurrence_outside_active_profile'
    return 'provenance_only_source_anchor'


def audit(output=OUTPUT, max_seconds=None):
    """Inspect exact residual records; time limit aborts before publishing outputs."""
    start=time.monotonic()
    def bounded():
        """Honor the caller's short-check budget without partial scientific claims."""
        require(max_seconds is None or time.monotonic()-start < max_seconds, 'TIME_BUDGET: run without --max-seconds in researcher terminal')
    require(not output.exists(),'OUTPUT_ALREADY_EXISTS')
    require(output.resolve().is_relative_to(Path('var').resolve()),'IGNORED_OUTPUT_REQUIRED')
    summary=read(ROOT/'summary.json');metric=read(ROOT/'metrics/snapshots/step13_semantic_pre_alignment.json')
    require(sha256_file(ROOT/'snapshot.json')==metric['input']['sha256'],'SNAPSHOT_HASH_DRIFT')
    graph=read(ROOT/'snapshot.json');nodes={n['id']:n for n in graph['nodes']}
    incident={e[k] for e in graph['edges'] for k in ('source','target')};isolated=set(nodes)-incident
    require(len(isolated)==summary['isolatedAfter']==472,'RESIDUAL_COUNT_DRIFT');bounded()
    spec=yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())
    require(sha256_file(Path('src/ontology/ontology_spec.yaml'))==summary['inputHashes']['src/ontology/ontology_spec.yaml'],'ONTOLOGY_DRIFT')
    d26=next(r for r in spec['relations'] if r['id']=='D-26');eligible=closure(spec,d26['range']);domains=closure(spec,d26['domain'])
    scope=yaml.safe_load(Path('src/extraction/llm/nonpublication_semantic_v041.yaml').read_text())['families']
    sidecar=Path(summary['originalNativeProvenancePath'])
    require(sha256_file(sidecar)==summary['originalNativeProvenanceSha256'],'SIDECAR_HASH_DRIFT')
    occurrences=defaultdict(list)
    with sidecar.open() as f:
        for i,line in enumerate(f):
            row=json.loads(line)
            if row['kind']=='nodes' and row['graphID'] in isolated:
                require(digest(canonical(row['nativeRecord']))==row['nativeRecordSha256'],'NATIVE_HASH_DRIFT')
                occurrences[row['graphID']].append(row)
            if i%2000==0:bounded()
    # Deterministic residuals are sourced from preserved original component records.
    path=Path('data/interim/papers/publication_nodes_edges.json')
    from src.evaluation.compute_structural_metrics import load_snapshot
    baseline=read(Path('results/metrics/snapshots/hydroshare_github_hub_publications_deterministic.json'))
    component=next(c for c in baseline['input']['cumulativeProvenance']['components'] if c['label']=='publications')
    require(sha256_file(path)==component['sha256'],'DETERMINISTIC_COMPONENT_DRIFT')
    deterministic={n['id']:n for n in load_snapshot(path)['nodes'] if n['id'] in isolated}
    rows=[];group_cache={};owner_cache={};pins={str(ROOT/'snapshot.json'):metric['input']['sha256'],str(ROOT/'summary.json'):sha256_file(ROOT/'summary.json'),str(sidecar):summary['originalNativeProvenanceSha256'],str(path):component['sha256']}
    representative_counts=Counter();representatives=[]
    for nid in sorted(isolated):
        bounded();n=nodes[nid];records=occurrences[nid];evidence=[];source_ids=set();families=set();related=[];refs=[]
        if not records:
            require(nid in deterministic and deterministic[nid]==n,'UNATTRIBUTED_RESIDUAL')
            declarations=n.get('attributes',{}).get('sourceDeclarations',[])
            canonical_sources={d['sourceArtifact'] for d in declarations if d.get('sourceArtifact')}
            source_ids.update(p['id'] for p in graph['nodes'] if p['class']=='Paper' and
                              p.get('attributes',{}).get('canonicalArtifactId') in canonical_sources)
            require(bool(canonical_sources) and bool(source_ids),'BIBLIOGRAPHIC_SOURCE_UNRESOLVED')
            families.add('publications');refs.append(dict(path=str(path),nodeID=nid,nativeSha256=digest(canonical(n))))
            evidence.append(dict(deterministicEvidence=n.get('evidence'),attributes=n.get('attributes')))
        for row in records:
            pr=row['provenance'];native=row['nativeRecord'];family=pr['family'];families.add(family)
            require(family in scope,'UNEXPECTED_SEMANTIC_FAMILY')
            op=pr['path']
            if op not in owner_cache:
                require(sha256_file(Path(op))==pr['sha256'],'OWNER_HASH_DRIFT');owner_cache[op]=checked(Path(op));pins[op]=pr['sha256']
            owner=owner_cache[op];owner_id=owner['owner']['endpointID'];source_ids.add(owner_id)
            require(owner_id in nodes,'MISSING_SOURCE_OWNER')
            rid=pr['requestID'];gp=REVIEW/'groups'/(digest(rid.encode())+'.json')
            if rid not in group_cache:
                g=checked(gp);expected=next(g0['reportSha256'] for g0 in owner['groupReports'] if g0['requestID']==rid)
                require(g['reportSha256']==expected,'OWNER_GROUP_DRIFT');group_cache[rid]=g;pins[str(gp)]=sha256_file(gp)
            g=group_cache[rid];view=g['nativeValidationView'];body=view['originalReplay']['requestResult']['request']
            require(any(c['record']==native for c0 in owner['nodes'] for c in c0['records'] if c['requestID']==rid),'NATIVE_OWNER_ASSOCIATION')
            units={u['sourceUnitID']:u for u in body['sourceUnits']}
            require(native['boundEvidence'],'EMPTY_BOUND_EVIDENCE')
            for ev in native['boundEvidence']:
                unit=units[ev['sourceUnitID']];text=unit['text'];quote=ev['evidenceText']
                lo=ev.get('startOffsetInAuthority');hi=ev.get('endOffsetInAuthority');base=unit.get('startOffsetInAuthority',0)
                require(quote in text,'QUOTE_UNBOUND')
                if lo is not None and hi is not None:
                    require(text[lo-base:hi-base]==quote,'OFFSET_DRIFT')
                else:
                    lo=text.index(quote)+base;hi=lo+len(quote)
                evidence.append(dict(requestID=rid,candidateID=native['originalCandidate']['candidateID'],sourceUnitID=ev['sourceUnitID'],
                    sourceTextSha256=digest(text.encode()),evidenceHash=ev.get('evidenceHash'),quoteSha256=digest(quote.encode()),
                    originalStart=ev.get('startOffsetInAuthority'),originalEnd=ev.get('endOffsetInAuthority'),
                    quote=quote[:500],quoteTruncated=len(quote)>500,context=text[max(0,lo-base-120):min(len(text),hi-base+120)][:900]))
            for check in view['originalReplay']['validationResult']['candidateChecks']:
                if check['kind']=='edge' and any(check.get(k,{}).get('endpointID')==nid for k in ('resolvedSource','resolvedTarget')):
                    decision=next((d for d in view['decisions'] if d['candidateID']==check['candidateID']),None)
                    related.append(dict(requestID=rid,candidateID=check['candidateID'],relation=check['originalCandidate'].get('relation'),decision=decision))
            refs.append(dict(requestID=rid,candidateID=native['originalCandidate']['candidateID'],nativeSha256=row['nativeRecordSha256'],ownerReport=op,groupReport=str(gp)))
        require(len(families)==1,'AMBIGUOUS_ORIGIN');family=next(iter(families))
        category=classify(family,n['class'],n['inventoryId'],eligible,scope.get(family,{}).get('genericOccurrences',[]))
        valid_signature=family!='publications' and n['class'] in eligible and all(nodes[s]['class'] in domains for s in source_ids)
        row=dict(nodeID=nid,family=family,ontologyClass=n['class'],inventoryId=n['inventoryId'],label=n.get('attributes',{}).get('label'),
            primaryClassification=category,sourceArtifactIDs=sorted(source_ids),zeroDegree=True,
            sourceArtifactGraphReachable=False,reachabilityBasis='A zero-degree node has no nonempty directed or undirected path; source provenance is checked separately.',
            sourceBoundProvenanceVerified=bool(records),d26SignatureValid=valid_signature,
            activeD26Permission=n['inventoryId'] in scope.get(family,{}).get('genericOccurrences',[]),
            evidenceReferences=[{k:v for k,v in e.items() if k not in ('quote','context','deterministicEvidence','attributes')} for e in evidence],
            nativeReferences=refs,relatedAuthoredEdges=related,
            interpretation='Pattern triage, not independent semantic validation. No new edge is justified solely by isolation or literal binding.')
        rows.append(row)
        key=(family,n['class'])
        if representative_counts[key]<2:
            representative_counts[key]+=1;representatives.append(dict(row,evidence=evidence))
    counts=Counter(r['primaryClassification'] for r in rows);by=Counter(r['family']+':'+r['ontologyClass'] for r in rows)
    require(dict(by)==summary['residualByFamilyClass'],'RESIDUAL_STRATA_DRIFT')
    result=dict(version='step13-residual-source-anchoring/0.1.0',inputHashes=pins,exactResiduals=len(rows),
        byFamilyClass=dict(sorted(by.items())),classifications=dict(counts),records=rows,
        semanticTruthAdjudicated=False,newEdgesEmitted=0,representativeSelection='First two lexicographically sorted exact IDs per family/class, no semantic screening.',
        limitation='Weak occurrence classification establishes authorized-source literal grounding and profile exclusion, not independently verified node typing or support for a stronger relation.')
    output.mkdir(parents=True)
    for name,value in [('diagnostic.json',result),('representatives.json',representatives)]:
        (output/name).write_bytes(canonical(value)+b'\n')
    write_summary(output,result)
    return result


def write_summary(output, result):
    """Render compact pattern conclusions without judging every semantic assertion."""
    lines = ['# Residual source-anchoring review', '',
        'All 472 exact IDs reconcile with v4. This is deterministic provenance/profile triage, not independent semantic evaluation. No relationships are emitted.', '',
        '| Primary mechanical classification | Count |', '|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in result['classifications'].items()]
    lines += ['', '## Findings and proposed boundaries', '',
        '445 accepted occurrences have verified literal evidence and original source offsets, but their class is outside the active family generic-occurrence profile. D-26 domain/range is valid for these owner/target types. This identifies a potential weak-occurrence amendment, not permission to assert a stronger role. No blanket mentions expansion is implemented or recommended without researcher approval.',
        'Four Hub nodes (three Procedures and one Paper) have a provenance anchor but are outside the D-26 range. Procedure attachment requires independently supported C-DC20 hasProcedure and dependency paths; Paper citation requires C-DC26 referencePublication evidence. Do not substitute generic mentions or inherit another candidate’s edge evidence.',
        '23 deterministic Publication Tool nodes are typed external/bibliographic stubs. Their exact source declarations and owning Paper references are preserved. Publication deterministic mapping N10 explicitly forbids a Paper→Tool edge from bibliographic presence alone. The prose-LLM D-26 production route does not automatically apply to these deterministic reference records. A separately approved documentary-reference rule would be methodological work, not an existing-rule bug fix.',
        'No missed active D-26 instance was identified. There is no demonstrated previously authorized deterministic relation that can simply be materialized for these residuals. Stronger semantic relations may be plausible in representative context, but were not authored/admitted independently. Model omission is not a missing deterministic consumer.',
        'No population count of genuinely unsupported or incorrectly typed nodes is established by this check. Literal binding does not certify semantic typing, factual truth, or current/executed behavior. Such cases remain unresolved rather than being classified as valid by default.', '',
        '## Source reachability', '',
        'All 472 have degree zero and therefore no nonempty directed or undirected graph path from any distinct source-artifact node. This follows exactly from incidence; a general graph search adds nothing. 449 semantic nodes retain verified owner/request/source-unit provenance; 23 deterministic Tool stubs retain typed source declarations. Provenance is separate from graph reachability and does not authorize an edge. Arbitrary connectedness would not prove origin.', '',
        '## Independent retained blockers', '']
    for row in result['records']:
        if row['relatedAuthoredEdges']:
            lines.append(f"- `{row['nodeID']}` ({row['family']} / {row['ontologyClass']}): " + '; '.join(f"{e['candidateID']}: {e['relation']} / {e['decision']['disposition'] if e['decision'] else 'unknown'} / {','.join(e['decision']['blockingReasons']) if e['decision'] else 'unknown'}" for e in row['relatedAuthoredEdges']))
    lines += ['', '## Pattern-specific prospective rules for researcher review', '',
        '- Hub: weak owner occurrences of Repository (147), Tool (141), DatasetResource (41), DatasetMention (14), Concept (1): 344. D-26 signatures are valid but all five classes are excluded from the active Hub generic profile. Preserve stronger describes/uses/citation distinctions. A prospective explicit fallback amendment is required.',
        '- GitHub: Repository (80), DatasetResource (7), Tool (2): 89. D-26 signatures are valid but these classes are outside the active GitHub fallback profile. A URL alone does not establish usesDataset/usesTool. ForcingProcessor has an independently unbound usesTool edge that must stay held.',
        '- HydroShare: Variable (12). D-26 signature is valid, but the current generic profile omits Variable. Existing containsVariable requires actual dataset-content support, not variables mentioned in linked models or notebook descriptions. A weak-mention amendment would be separate from containsVariable.',
        '- Three Hub Procedures and one Hub Paper: preserve source provenance. Contextual hasProcedure/referencePublication review is needed before any relation could be added; neither class supports D-26.',
        '- Deterministic Publication Tools: retain stubs and documented deferred roles unless a separate reference policy is approved.', '',
        '## Recommendation', '',
        'Preserve v4 and the 472 residuals. Keep order-50 promotion separate. If the researcher wants source anchoring in the primary graph, first decide whether it is provenance infrastructure or a weak semantic-mention policy. Approve only explicitly enumerated family targets and retain independent evidence/precedence gates. No existing-rule repair is demonstrated by this audit. Step 13 remains CLOSED; Step 14 implementation has not begun.', '',
        'Representatives are the first two sorted IDs per family/class, without semantic screening. See representatives.json for bounded quotes/context and diagnostic.json for every exact ID, original offsets, evidence hashes, request/candidate IDs, source IDs and retained edge decisions. Source checks use authentic hash-linked selected source units preserved in the original requests, without fetching or rebuilding sources. No independent source-corpus rematerialization was performed.']
    (output/'synthesis.md').write_text('\n'.join(lines)+'\n')


def main():
    """Run with a bounded optional deadline and no network access."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT);parser.add_argument('--max-seconds',type=float)
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        result=audit(args.output,args.max_seconds)
    print(json.dumps({k:result[k] for k in ('exactResiduals','classifications','byFamilyClass')},indent=2))


if __name__=='__main__':main()
