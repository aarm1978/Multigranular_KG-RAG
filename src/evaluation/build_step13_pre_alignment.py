"""Evaluation-only Step 13 snapshot; no extraction, semantic alignment or final KG.

Use persisted accepted records only. Missing endpoints/conflicting exact identities
block snapshot publication. Evidence and native records stay in a separate sidecar
so administrative payloads cannot inflate informative-attribute metrics.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
from unittest.mock import patch
from src.evaluation import compute_structural_metrics as metrics
from src.extraction.llm.pilot_preflight import canonical, digest

BASELINE = Path('results/metrics/snapshots/hydroshare_github_hub_publications_deterministic.json')
REVIEW = Path('var/study2_step13/source-local-supplemental-review/v4.1')
PUBLICATIONS = Path('var/study2_step13/publications-gpt61-batch/v1')
VERIFICATION = Path('var/study2_step13/publications-production-verification/v1')
OUTPUT = Path('var/study2_step13/pre-alignment-metrics/v1')
VERSION = 'step13-evaluation-pre-alignment/0.1.1'


def require(condition, reason):
    """Stop rather than infer identities or repair missing graph content."""
    if not condition:
        raise ValueError(reason)


def read(path):
    """Read an existing JSON authority."""
    return json.loads(path.read_bytes())


def checked(path):
    """Verify an existing native report self-hash without semantic replay."""
    result = read(path)
    require(result['reportSha256'] == digest(canonical({k:v for k,v in result.items() if k!='reportSha256'})), 'REPORT_HASH_DRIFT:'+str(path))
    return result


def attributes(candidate):
    """Preserve literal semantic label/attribute keys; do not count evidence as attributes."""
    grouped = {}
    values = candidate.get('attributes', [])
    if isinstance(values, dict):
        values = [dict(attributeName=k, value=v) for k, v in values.items()]
    if candidate.get('label') is not None:
        values = [dict(attributeName='label', value=candidate['label']), *values]
    for item in values:
        # Canonical JSON compares literal values, including their JSON types;
        # sorting representations is ordering only, never semantic normalization.
        value = item['value']
        grouped.setdefault(item['attributeName'], {})[canonical(value)] = deepcopy(value)
    result = {}
    for key, distinct in grouped.items():
        ordered = [distinct[token] for token in sorted(distinct)]
        result[key] = ordered[0] if len(ordered) == 1 else ordered
    return result


class Snapshot:
    """Exact identity join with independent immutable native-record provenance."""
    def __init__(self, baseline, evidence):
        metrics.validate_snapshot(baseline)
        self.nodes = {n['id']:deepcopy(n) for n in baseline['nodes']}
        self.edges = {e['id']:deepcopy(e) for e in baseline['edges']}
        self.evidence = evidence
        self.blockers = []
        self.counts = Counter()
        self.paper_lineage = {}
        for node in baseline['nodes']:
            if node.get('class')=='Paper' and node.get('curationStatus')=='curated':
                local = node.get('internalLineage',{}).get('localPaperId')
                if local is not None:
                    require(str(local) not in self.paper_lineage,'AMBIGUOUS_CURATED_PAPER_LINEAGE')
                    self.paper_lineage[str(local)] = node

    def add(self, kind, record, native, provenance):
        """Reuse exact IDs only; incompatible structural/attribute values block output."""
        store = self.nodes if kind == 'nodes' else self.edges
        prior = store.get(record['id'])
        keys = ('class','inventoryId','attributes') if kind == 'nodes' else ('source','target','relation','inventoryId')
        if prior is not None and any(prior.get(k) != record.get(k) for k in keys):
            self.blockers.append(dict(reason='conflicting_exact_identity',kind=kind,id=record['id'],
                before={k:prior.get(k) for k in keys},after={k:record.get(k) for k in keys},provenance=provenance))
            return
        if prior is None:
            store[record['id']] = record
        self.counts[kind+('_new' if prior is None else '_repeated_exact_id')] += 1
        self.evidence.write(canonical(dict(kind=kind,graphID=record['id'],nativeRecord=native,
            nativeRecordSha256=digest(canonical(native)),provenance=provenance)).decode()+'\n')

    def seed_purposes(self):
        """Materialize only the authorized shared vocabulary, with no LLM evidence."""
        from src.extraction.llm.coderepos.purpose_validation import purpose_vocabulary
        seeds = purpose_vocabulary()
        require(len(seeds) == 6 and len({n['nodeID'] for n in seeds}) == 6,
                'PURPOSE_VOCABULARY_DRIFT')
        for seed in seeds:
            self.add('nodes', dict(id=seed['nodeID'], **{'class': seed['class']},
                inventoryId=seed['inventoryId'],
                attributes={k: seed[k] for k in ('label', 'definition')}), seed,
                dict(authority='src/extraction/llm/coderepos/purpose_validation.py',
                     origin='controlled_vocabulary_seed', contractID=seed['contractID'],
                     schemeID=seed['schemeID'], schemeVersion=seed['schemeVersion']))

    def owner(self, report, provenance):
        """Consume existing exact owner consolidation, preserving all supporting records."""
        for collection in ('nodes','edges'):
            for consolidated in report[collection]:
                projected = None
                if collection == 'nodes':
                    # Only consume identity already established by this owner record.
                    rows = []
                    labels = {}
                    for occurrence in consolidated['records']:
                        native = occurrence['record']; ep = native['resolvedEndpoint']
                        attrs = attributes(native['originalCandidate'])
                        label = attrs.pop('label', None)
                        require(label is None or isinstance(label, str), 'OWNER_LABEL_NOT_LITERAL_STRING')
                        if label is not None:
                            labels[canonical(label)] = label
                        rows.append(dict(id=ep['endpointID'], **{'class': ep['class']},
                                         inventoryId=ep['inventoryId'], attributes=attrs))
                    require(bool(rows), 'EMPTY_OWNER_CONSOLIDATION')
                    require(all(canonical(row) == canonical(rows[0]) for row in rows),
                            'INCOMPATIBLE_OWNER_EXACT_ID_CONSOLIDATION')
                    projected = deepcopy(rows[0])
                    ordered = [labels[key] for key in sorted(labels)]
                    if ordered:
                        projected['attributes']['label'] = ordered[0] if len(ordered) == 1 else ordered
                for occurrence in consolidated['records']:
                    n = occurrence['record']; c = n['originalCandidate']
                    if collection == 'nodes':
                        row = deepcopy(projected)
                    else:
                        row = dict(id=n['sourceLocalCandidateID'],source=n['resolvedSource']['endpointID'],
                            target=n['resolvedTarget']['endpointID'],relation=c['relation'],inventoryId=c['inventoryId'])
                    self.add(collection,row,n,{**provenance,'requestID':occurrence['requestID'],'groupID':occurrence['groupID']})

    def publication(self, projection, provenance, paper_id=None):
        """Preserve request-qualified native IDs; unwrap trusted deterministic references only."""
        rid = projection['requestID']
        require(projection['acceptanceStatus']=='production_accepted','UNACCEPTED_PUBLICATION')
        for n in projection['acceptedNodes']:
            require(n['accepted'] is True and n['nodeID']==rid+'#node#'+n['candidateID'],'PUBLICATION_NODE_ID_DRIFT')
            self.add('nodes',dict(id=n['nodeID'],**{'class':n['className']},inventoryId=n['ontologyClassID'],
                attributes=attributes(n['candidate'])),n,provenance)
        for e in projection['acceptedEdges']:
            require(e['accepted'] is True and e['edgeID']==rid+'#edge#'+e['candidateID'],'PUBLICATION_EDGE_ID_DRIFT')
            endpoints = {}
            for side in ('source','target'):
                ref = e[side+'Endpoint']; refid = ref['referenceID']
                if ref['referenceType']=='candidate_node':
                    endpoint = rid+'#node#'+refid
                    require(e[side+'ID']==endpoint,'PUBLICATION_LOCAL_ENDPOINT_DRIFT')
                elif ref['referenceType']=='deterministic_node':
                    require(bool(ref.get('artifactID')) and e[side+'ID']=='deterministic:'+ref['artifactID']+':'+refid,'PUBLICATION_DETERMINISTIC_REFERENCE_DRIFT')
                    # This is the exact stored deterministic ID, not an identifier lookup.
                    endpoint = refid
                    if endpoint not in self.nodes and refid == ref['artifactID'] == projection['sourceArtifactID']:
                        # Exact inventory lineage, NOT DOI/canonical-key matching.
                        paper = self.paper_lineage.get(str(paper_id))
                        if paper is not None:
                            require(paper['attributes'].get('canonicalArtifactId') == refid
                                and paper['evidence'].get('sourceArtifact') == refid,'PAPER_LINEAGE_AUTHORITY_DRIFT')
                            endpoint = paper['id']
                else:
                    raise ValueError('UNSUPPORTED_PUBLICATION_ENDPOINT')
                endpoints[side] = endpoint
            self.add('edges',dict(id=e['edgeID'],**endpoints,relation=e['relationName'],inventoryId=e['ontologyRelationID']),e,{**provenance,'endpointMapping':{side:dict(nativeID=e[side+'ID'],graphID=endpoints[side]) for side in endpoints},'paperInventoryID':paper_id})

    def finish(self):
        """No placeholder nodes, dropped edges, or semantic repair of orphan endpoints."""
        for edge in self.edges.values():
            for side in ('source','target'):
                if edge[side] not in self.nodes:
                    self.blockers.append(dict(reason='missing_exact_endpoint',edgeID=edge['id'],side=side,endpointID=edge[side]))
        if self.blockers:
            return None
        graph = dict(nodes=sorted(self.nodes.values(),key=lambda n:n['id']),edges=sorted(self.edges.values(),key=lambda e:e['id']))
        metrics.validate_snapshot(graph)
        return graph


def publication_offsets(path, expected_hash, head):
    """Index last durable outcomes, verifying bytes and chain; no native semantic replay."""
    import hashlib
    h=hashlib.sha256();previous='0'*64;seq=0;latest={}
    with path.open('rb') as handle:
        while True:
            offset=handle.tell();line=handle.readline()
            if not line:break
            h.update(line);outer=json.loads(line);r=outer['record']
            require(r['seq']==seq+1 and r['previous']==previous and outer['sha256']==digest(canonical(r)), 'JOURNAL_CHAIN_DRIFT')
            seq=r['seq'];previous=outer['sha256']
            if r['event']=='outcome':latest[r['requestID']]=offset
    require(h.hexdigest()==expected_hash and seq==head['seq'] and previous==head['headSha256'],'JOURNAL_AUTHORITY_DRIFT')
    return latest


def build(repo=Path('.'), output=OUTPUT):
    """Researcher-terminal full transformation; never writes historical metrics or inputs."""
    dest=repo/output
    require(not dest.exists(),'OUTPUT_ALREADY_EXISTS')
    require(dest.resolve().is_relative_to((repo/'var').resolve()),'OUTPUT_MUST_BE_UNDER_IGNORED_VAR')
    pins={}
    def pin(path, expected=None):
        """Record exact input bytes and compare existing authority pins when available."""
        got=metrics.sha256_file(repo/path)
        require(expected is None or got==expected,'INPUT_HASH_DRIFT:'+str(path))
        pins[str(path)]=got
        return got
    baseline_record=read(repo/BASELINE);pin(BASELINE)
    deterministic_path=Path(baseline_record['input']['path']);pin(deterministic_path,baseline_record['input']['sha256'])
    deterministic=metrics.load_snapshot(repo/deterministic_path)
    require(len(deterministic['nodes'])==28406 and len(deterministic['edges'])==32809 and baseline_record['trajectoryOrder']==40,'BASELINE_DRIFT')
    import yaml
    spec=yaml.safe_load((repo/'src/ontology/ontology_spec.yaml').read_text())
    require(spec['ontology']['version']=='0.1.7','ONTOLOGY_VERSION_DRIFT')
    pin(Path('src/ontology/ontology_spec.yaml'))
    pin(Path('src/ontology/ciroh_ontology.owl'),'ac64435ca02a703bdee8168a045a3897d7f6f5be1a8e25e6cdf485c66c85e0fa')
    manifest=read(repo/REVIEW/'selection-manifest.json');summary=read(repo/REVIEW/'summary.json')
    require(summary['counts']['successfulValidations']==1005 and summary['counts']['completeOwners']==335
            and summary['decisionDispositions']['accepted']==9463 and summary['quarantinedAbstentions']==6,'V41_SELECTION_DRIFT')
    for name in ('selection-manifest.json','summary.json','comparison.json'):pin(REVIEW/name)
    pin(Path('docs/study2_v4_1_reviewer_adjudications_v0.1.json'),manifest['adjudicationArtifactSha256'])
    for mapping in ('baselineFileHashes','implementationHashes'):
        for name,sha in manifest[mapping].items():pin(Path(name),sha)
    for name in ('docs/study2_step13_construction_acceptance_policy_v0.1.md','docs/study2_materialized_corpus_evidence_amendment_v0.1.md','src/evaluation/compute_structural_metrics.py','src/evaluation/build_cumulative_snapshot.py','src/extraction/llm/coderepos/purpose_validation.py','src/extraction/llm/semantic_target_profiles.py',__file__):
        path=Path(name)
        if path.is_absolute():path=path.relative_to(repo.resolve())
        pin(path)
    verification=read(repo/VERIFICATION/'verification.json');exceptions=read(repo/VERIFICATION/'exceptions.json')
    pin(VERIFICATION/'verification.json');pin(VERIFICATION/'exceptions.json')
    require(verification['categories']=={'completed_protected':10886,'terminal_review':7} and len(exceptions)==7,'PUBLICATION_COMPLETION_DRIFT')
    for name in ('run-manifest.json','head.json'):pin(PUBLICATIONS/name,verification['inputHashes'][name])
    pubmanifest=read(repo/PUBLICATIONS/'run-manifest.json')
    pubentries={e['identity']['requestID']:e for e in pubmanifest['requests']}
    require(len(pubentries)==10893,'PUBLICATION_MANIFEST_IDENTITIES')
    head=read(repo/PUBLICATIONS/'head.json')
    require(head['seq']==verification['journalSeq'] and head['headSha256']==verification['journalHead'],'PUBLICATION_HEAD_DRIFT')
    offsets=publication_offsets(repo/PUBLICATIONS/'execution.jsonl',verification['inputHashes']['execution.jsonl'],head)
    pins[str(PUBLICATIONS/'execution.jsonl')]=verification['inputHashes']['execution.jsonl']
    require(set(offsets)==set(pubentries),'PUBLICATION_REQUEST_COVERAGE_DRIFT')
    terminal={e['requestID'] for e in exceptions};require(len(terminal)==7 and terminal<=set(offsets),'TERMINAL_ID_DRIFT')
    dest.mkdir(parents=True);totals=Counter();pubcounts=Counter();derived=[]
    with (dest/'native-provenance.jsonl').open('x') as evidence:
        snapshot=Snapshot(deterministic,evidence)
        snapshot.seed_purposes()
        owners=sorted((repo/REVIEW/'owners').glob('*.json'))
        expected_owners={s['ownerID'] for s in manifest['originalSelection']['selection']}
        require(len(owners)==335 and {p.stem for p in owners}=={digest(o.encode()) for o in expected_owners},'OWNER_COVERAGE_DRIFT')
        for path in owners:
            report=checked(path);relative=path.relative_to(repo)
            pin(relative);snapshot.owner(report,dict(path=str(relative),sha256=pins[str(relative)],family=report['artifactFamily']))
            for k in ('nodes','edges','derivedConstructionInputs'):totals[k]+=len(report[k])
            derived.extend(dict(ownerID=report['owner']['endpointID'],originalInput=r,ownerReportSha256=pins[str(relative)]) for r in report['derivedConstructionInputs'])
        require(totals==Counter(nodes=4986,edges=4403,derivedConstructionInputs=407),'V41_OWNER_COUNT_DRIFT')
        with (repo/PUBLICATIONS/'execution.jsonl').open('rb') as handle:
            for rid,offset in sorted(offsets.items()):
                handle.seek(offset);outer=json.loads(handle.readline());native=outer['record']['payload']['native']
                if rid in terminal:continue
                require(native.get('processable') is True,'PUBLICATION_SELECTED_OUTCOME_NOT_PROCESSABLE')
                projection=native['productionResult']['acceptedSemanticProjection']
                require(projection['requestID']==rid and projection['acceptedSemanticProjectionHash']==digest(canonical({k:v for k,v in projection.items() if k!='acceptedSemanticProjectionHash'})),'PUBLICATION_PROJECTION_HASH_DRIFT')
                pubcounts.update(nodes=len(projection['acceptedNodes']),edges=len(projection['acceptedEdges']),requests=1)
                snapshot.publication(projection,dict(family='publications',requestID=rid,journalPath=str(PUBLICATIONS/'execution.jsonl'),byteOffset=offset,recordSha256=outer['sha256'],projectionSha256=projection['acceptedSemanticProjectionHash']),paper_id=pubentries[rid]['paperID'])
    require(pubcounts==Counter(nodes=182255,edges=89021,requests=10886),'PUBLICATION_AGGREGATE_DRIFT')
    graph=snapshot.finish()
    report=dict(version=VERSION,status='blocked' if graph is None else 'evaluation_snapshot_ready_pending_step13_closure',
        inputHashes=pins,ontologyVersion='0.1.7',historicalExtractionAuthoritiesUnchanged=True,
        nativeProvenanceSha256=metrics.sha256_file(dest/'native-provenance.jsonl'),
        ownerInputCounts=dict(totals),publicationOccurrences=dict(pubcounts),mechanicalCounts=dict(snapshot.counts),
        blockers=snapshot.blockers,terminalExceptions=exceptions,derivedConstructionInputCount=len(derived),
        derivedPolicy='407 retained separately, excluded from primary metrics. No new generic-mention consumer or final KG assembly is authorized by this evaluation adapter.',
        identityPolicy='Exact native node/edge ID reuse only; Publication deterministic wrapper resolves through its explicit stored referenceID; curated owning Paper uses exact manifest paperID to deterministic internalLineage.localPaperId with matching source authority, never canonical-key matching. No name, canonical-key, fuzzy or cross-source semantic matching. Request-local Publication repetitions are occurrences, not globally distinct entities.',
        step13HumanReview='pending',trajectoryOrder=50,kgAuthorization=False,providerCalls=0)
    for name,value in [('manifest',report),('derived-construction-inputs',derived)]:
        with (dest/(name+'.json')).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    if graph is None:
        raise ValueError('ENDPOINT_OR_IDENTITY_BLOCKERS: see '+str(dest/'manifest.json'))
    graph.update(snapshot_type='cumulative_pre_alignment',snapshot_schema_version='1.0',
        components=[dict(label='deterministic_order40',path=str(deterministic_path),sha256=pins[str(deterministic_path)],nodes=28406,edges=32809),
            dict(label='step13_accepted_semantic_exact_identity_additions',path=str(output/'manifest.json'),sha256=metrics.sha256_file(dest/'manifest.json'),nodes=len(graph['nodes'])-28406,edges=len(graph['edges'])-32809)],
        evaluationOnly=True,provenanceSidecarSha256=metrics.sha256_file(dest/'native-provenance.jsonl'),authorityManifestSha256=metrics.sha256_file(dest/'manifest.json'))
    with (dest/'snapshot.json').open('x') as f:json.dump(graph,f,ensure_ascii=False,sort_keys=True)
    # Historical snapshot bytes copied only into the ignored draft result tree.
    metric_dir=dest/'metrics'/'snapshots';metric_dir.mkdir(parents=True)
    history_hashes={}
    for path in sorted((repo/'results/metrics/snapshots').glob('*.json')):
        require(read(path)['trajectoryOrder']<=40,'UNEXPECTED_LATER_TRAJECTORY')
        shutil.copyfile(path,metric_dir/path.name)
        history_hashes[str(path.relative_to(repo))]=metrics.sha256_file(path)
        require(metrics.sha256_file(metric_dir/path.name)==history_hashes[str(path.relative_to(repo))],'HISTORICAL_COPY_DRIFT')
    with (dest/'historical-metric-hashes.json').open('x') as f:json.dump(history_hashes,f,indent=2)
    return report


def main():
    """Create only the ignored snapshot; metrics are a separate existing CLI command."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        report=build(Path.cwd(),args.output)
    print(json.dumps({k:report[k] for k in ('status','mechanicalCounts','derivedConstructionInputCount')},indent=2))


if __name__=='__main__':main()
