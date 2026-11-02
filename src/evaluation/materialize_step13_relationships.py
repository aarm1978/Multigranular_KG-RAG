"""Opt-in evaluation-only post-acceptance relationship consumer; no semantic replay."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
from unittest.mock import patch
import yaml
from src.evaluation import compute_structural_metrics as metrics
from src.evaluation.build_step13_pre_alignment import require, read, checked
from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.publications.semantic_materializer import exact_coordinate_containment

VERSION = 'step13-post-acceptance-relationships/0.1.0'
AUTHORITY = Path('docs/study2_step13_relationship_consumer_v0.1.json')
SOURCE = Path('var/study2_step13/pre-alignment-metrics/v3')
OUTPUT = Path('var/study2_step13/pre-alignment-metrics/v4')
REVIEW = Path('var/study2_step13/source-local-supplemental-review/v4.1')
PUB = Path('src/extraction/llm/publications')


def closure(spec, roots):
    """Expand only declared subclass ancestry."""
    result = set(roots if isinstance(roots, list) else [roots])
    while True:
        old = set(result)
        result.update(c['name'] for c in spec['classes'] if str(c.get('parent', '')).split(':')[-1] in result)
        if old == result:
            return result


def authorities():
    """Verify separate compatibility authority; never patch historical guards."""
    authority = read(AUTHORITY)
    require(authority['version'] == VERSION, 'CONSUMER_AUTHORITY_DRIFT')
    for path, sha in authority['inputHashes'].items():
        require(metrics.sha256_file(Path(path)) == sha, 'AUTHORITY_DRIFT:'+path)
    spec = yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())
    require(spec['ontology']['version'] == '0.1.7', 'ONTOLOGY_VERSION_DRIFT')
    relations = {r['id']: r for r in spec['relations']}
    for identifier, expected in authority['applicableSignatures'].items():
        require({k: relations[identifier][k] for k in ('name','domain','range')} == expected,
                'SIGNATURE_DRIFT:'+identifier)
    historical = read(Path('var/study2_step13/publication-extraction-plan/v0.1/input-pins.json'))
    for path in authority['historicalPublicationPins']:
        require(historical[path] == authority['inputHashes'][path], 'HISTORICAL_PIN_DRIFT')
    inventory = yaml.safe_load((PUB/'publication_target_inventory_v0.1.5.yaml').read_text())
    for row in inventory['relation_targets']:
        if row['operational_id'] in authority['requiredPublicationTargets']:
            require(row['production_responsibility'] == 'pipeline_generated' and
                    row['pilot_treatment'] == 'required_infrastructure', 'INFRASTRUCTURE_AUTHORITY_DRIFT')
    return authority, spec, yaml.safe_load((PUB/'generic_mentions_policy_v0.1.1.yaml').read_text())


class Consumer:
    """Append derived edges only, retaining original graph objects byte-equivalently."""
    def __init__(self, graph, spec, policy, sidecar):
        metrics.validate_snapshot(graph)
        self.graph = graph
        self.nodes = {n['id']: n for n in graph['nodes']}
        self.relations = {r['id']: r for r in spec['relations']}
        self.signatures = {i: (closure(spec,r['domain']), closure(spec,r['range']))
                           for i,r in self.relations.items() if i in {'C-P05','C-P10','C-P12','D-26'}}
        self.discourse = self.signatures['C-P05'][1]
        self.mentionable = self.signatures['D-26'][1]
        self.strong = set(policy['stronger_role_relations']+policy['specialized_subproperties'])
        self.triples = {(e['source'],e['relation'],e['target']) for e in graph['edges']}
        self.pairs = {(e['source'],e['target']) for e in graph['edges']}
        self.suppress = {(e['source'],e['target']) for e in graph['edges'] if e['relation'] in self.strong}
        self.ids = {e['id'] for e in graph['edges']}
        self.derived = []; self.counts = defaultdict(Counter); self.sidecar = sidecar
        incident = {e[k] for e in graph['edges'] for k in ('source','target')}
        self.isolated = set(self.nodes)-incident; self.connected = defaultdict(set)

    def emit(self, rule, inventory, source, target, evidence, provenance, suppress=False):
        """Check signatures/endpoints and exact precedence; retain derivation evidence."""
        self.counts[rule]['candidates'] += 1
        require(source in self.nodes and target in self.nodes, 'MISSING_DERIVED_ENDPOINT')
        domain, ranges = self.signatures[inventory]
        require(self.nodes[source]['class'] in domain and self.nodes[target]['class'] in ranges,
                'DERIVED_SIGNATURE_FAILURE')
        require(bool(evidence), 'MISSING_DERIVATION_EVIDENCE')
        if suppress:
            self.counts[rule]['strongerSuppressed'] += 1
            return
        relation = self.relations[inventory]['name']; triple = (source,relation,target)
        identifier = 'step13:derived:'+digest(canonical([VERSION,inventory,source,target]))
        disposition = 'duplicate' if triple in self.triples else 'emitted'
        if disposition == 'emitted':
            require(identifier not in self.ids, 'DERIVED_ID_COLLISION')
            self.ids.add(identifier); self.triples.add(triple)
            self.derived.append(dict(id=identifier, source=source, target=target,
                                     relation=relation, inventoryId=inventory))
            self.connected[rule].update({source,target}&self.isolated)
        self.counts[rule][disposition] += 1
        self.sidecar.write(canonical(dict(edgeID=identifier, disposition=disposition, rule=rule,
            derivationVersion=VERSION, evidence=evidence, provenance=provenance)).decode()+'\n')

    def publication(self, records, paper):
        """Consume one authentic accepted request scope, with exact owning-Paper lineage."""
        require(paper is not None, 'MISSING_CURATED_PAPER')
        rows = []
        for row in records:
            n = row['nativeRecord']; nid = row['graphID']; pr = row['provenance']
            require(n['accepted'] is True and n['nodeID'] == nid == pr['requestID']+'#node#'+n['candidateID'],
                    'PUBLICATION_IDENTITY_DRIFT')
            require(self.nodes[nid]['class'] == n['className'] and
                    self.nodes[nid]['inventoryId'] == n['ontologyClassID'], 'PUBLICATION_TYPE_DRIFT')
            evidence = [e for e in n['evidenceOccurrences'] if e.get('valid') is True]
            papers = {e.get('canonicalPaperID') for e in evidence}
            require(evidence and papers == {paper['attributes']['canonicalArtifactId']} and
                    paper['evidence']['sourceArtifact'] in papers, 'PUBLICATION_PAPER_EVIDENCE_DRIFT')
            rows.append((nid,n['className'],evidence,dict(pr,candidateID=n['candidateID'],
                        nativeRecordSha256=row['nativeRecordSha256'])))
        for nid,cls,evidence,pr in rows:
            if cls in self.discourse:
                self.emit('C-P05','C-P05',paper['id'],nid,evidence,pr)
            if cls == 'RelatedResearch':
                self.emit('C-P10','C-P10',paper['id'],nid,evidence,pr)
            if cls == 'Limitation':
                self.emit('C-P12-Paper','C-P12',paper['id'],nid,evidence,pr)
            if cls in self.mentionable:
                self.emit('D26-Paper','D-26',paper['id'],nid,evidence,pr,(paper['id'],nid) in self.suppress)
        for di,dc,de,dp in rows:
            if dc not in self.discourse:
                continue
            for ei,ec,ee,ep in rows:
                if ec not in self.mentionable or di == ei:
                    continue
                bindings = [dict(discourseEvidence=d,entityEvidence=e) for d in de for e in ee
                            if exact_coordinate_containment(d,e)]
                if bindings:
                    self.emit('D26-discourse','D-26',di,ei,bindings,
                              dict(discourse=dp,entity=ep),(di,ei) in self.suppress)

    def nonpublication(self, item, group_loader, scopes):
        """Verify every retained input against its accepted projection and literal unit."""
        row = item['originalInput']; supports = row['constructionInputs']; require(supports,'EMPTY_DERIVED_INPUT')
        evidence = []; provenance = []; pair = None; family = None
        for support in supports:
            g = group_loader(support['requestID']); native = g['nativeValidationView']
            require(native['projectionSha256'] == support['requiredAcceptedProjectionSha256'] ==
                    digest(canonical(native['projection'])), 'ACCEPTED_PROJECTION_DRIFT')
            a = support['assertion']
            require(a in native['derivedConstructionInput']['assertions'], 'DERIVED_ASSERTION_DRIFT')
            require(a['assertionID'] == row['assertionID'] and a['targetID'] == row['targetID'] and
                    a['inventoryId'] == 'D-26' and a['relation'] == 'mentions', 'DERIVED_IDENTITY_DRIFT')
            request = native['originalReplay']['requestResult']['request']
            require(request['owner']['endpointID'] == a['sourceID'] == item['ownerID'], 'DERIVED_OWNER_DRIFT')
            current_family = request['artifactFamily']
            require(family is None or family == current_family, 'DERIVED_FAMILY_DRIFT'); family = current_family
            require(a['resolvedTarget']['inventoryId'] in scopes[family]['genericOccurrences'], 'UNAUTHORIZED_GENERIC_TARGET')
            for side in ('Source','Target'):
                ep = a['resolved'+side]; node = self.nodes.get(ep['endpointID'])
                require(node is not None and node['class'] == ep['class'] and
                        node['inventoryId'] == ep['inventoryId'], 'DERIVED_ENDPOINT_DRIFT')
            current = (a['sourceID'],a['targetID'])
            require(pair is None or pair == current, 'DERIVED_PAIR_DRIFT'); pair = current
            units = {u['sourceUnitID']: u for u in request['sourceUnits']}
            for e in a['boundEvidence']:
                require(e['sourceUnitID'] in units, 'UNAUTHORIZED_EVIDENCE_UNIT')
                unit = units[e['sourceUnitID']]; text = unit['text']
                if 'startOffsetInAuthority' in e and 'endOffsetInAuthority' in e:
                    start = e['startOffsetInAuthority'] - unit.get('startOffsetInAuthority', 0)
                    end = e['endOffsetInAuthority'] - unit.get('startOffsetInAuthority', 0)
                    require(0 <= start < end <= len(text) and text[start:end] == e['evidenceText'],
                            'DERIVED_EXACT_OFFSET_FAILURE')
                require(e['evidenceText'] in text and any(c['sourceUnitID'] == e['sourceUnitID'] and
                    c['sourceTextSha256'] == digest(text.encode()) and c['ownerID'] == a['sourceID']
                    for c in a['sourceContainment']), 'DERIVED_CONTAINMENT_FAILURE')
            require(a['boundEvidence'] and a['supportingOccurrences'], 'MISSING_DERIVED_SUPPORT')
            decisions = {d['candidateID']:d for d in native['decisions']}
            for occurrence in a['supportingOccurrences']:
                require(decisions[occurrence['candidateID']] == occurrence['constructionDecision'] and
                        decisions[occurrence['candidateID']]['disposition'] in {'accepted','suppressed_duplicate'},
                        'UNACCEPTED_DERIVED_OCCURRENCE')
            evidence.extend(a['boundEvidence']); provenance.append(support)
        self.emit('D26-'+family,'D-26',*pair,evidence,
                  dict(ownerReportSha256=item['ownerReportSha256'],constructionInputs=provenance),
                  pair in self.pairs or pair[::-1] in self.pairs)


def run(output=OUTPUT):
    """Researcher-terminal materialization; immutable inputs and fresh ignored output only."""
    require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    require(output.resolve().is_relative_to(Path('var').resolve()), 'OUTPUT_MUST_BE_IGNORED_VAR')
    authority,spec,policy = authorities()
    base = read(SOURCE/'manifest.json'); graph = read(SOURCE/'snapshot.json')
    require(metrics.sha256_file(SOURCE/'native-provenance.jsonl') == base['nativeProvenanceSha256'], 'NATIVE_PROVENANCE_DRIFT')
    before = digest(canonical(graph)); origins = defaultdict(set)
    baseline = read(Path('results/metrics/snapshots/hydroshare_github_hub_publications_deterministic.json'))
    for component in baseline['input']['cumulativeProvenance']['components']:
        require(metrics.sha256_file(Path(component['path'])) == component['sha256'], 'BASELINE_COMPONENT_DRIFT')
        for node in metrics.load_snapshot(Path(component['path']))['nodes']:
            origins[node['id']].add(component['label'])
    requests = {r['identity']['requestID']:r for r in read(Path('var/study2_step13/publications-gpt61-batch/v1/run-manifest.json'))['requests']}
    papers = {}
    for node in graph['nodes']:
        if node['class'] == 'Paper' and node.get('curationStatus') == 'curated':
            key = str(node['internalLineage']['localPaperId']); require(key not in papers,'AMBIGUOUS_PAPER_LINEAGE'); papers[key] = node
    output.mkdir(parents=True)
    with (output/'derivation-provenance.jsonl').open('x') as sidecar:
        consumer = Consumer(graph,spec,policy,sidecar); rows = []; rid = None
        with (SOURCE/'native-provenance.jsonl').open() as stream:
            for line in stream:
                row = json.loads(line)
                require(digest(canonical(row['nativeRecord'])) == row['nativeRecordSha256'], 'NATIVE_RECORD_DRIFT')
                if row['kind'] != 'nodes':
                    continue
                family = row['provenance'].get('family','controlled_vocabulary'); origins[row['graphID']].add(family)
                if family != 'publications':
                    continue
                request_id = row['provenance']['requestID']
                if rid is not None and rid != request_id:
                    consumer.publication(rows,papers.get(str(requests[rid]['paperID']))); rows = []
                rid = request_id; rows.append(row)
            if rows:
                consumer.publication(rows,papers.get(str(requests[rid]['paperID'])))
        scopes = yaml.safe_load(Path('src/extraction/llm/nonpublication_semantic_v041.yaml').read_text())['families']
        expected_groups = {}
        def load_group(rid):
            """Verify a persisted group; no response parsing or validation replay."""
            group = checked(REVIEW/'groups'/(digest(rid.encode())+'.json'))
            require(group['reportSha256'] == expected_groups[rid], 'OWNER_GROUP_HASH_DRIFT')
            return group
        for item in read(SOURCE/'derived-construction-inputs.json'):
            path = REVIEW/'owners'/(digest(item['ownerID'].encode())+'.json')
            require(metrics.sha256_file(path) == item['ownerReportSha256'], 'OWNER_REPORT_DRIFT')
            owner = checked(path)
            require(item['originalInput'] in owner['derivedConstructionInputs'], 'OWNER_DERIVED_INPUT_DRIFT')
            expected_groups = {g['requestID']:g['reportSha256'] for g in owner['groupReports']}
            consumer.nonpublication(item,load_group,scopes)
    require(digest(canonical(graph)) == before, 'ORIGINAL_GRAPH_MUTATED')
    audit = read(Path('var/study2_step13/relationship-gap-audit/v1/diagnostic.json'))
    expected_rules = {key.rsplit(':',1)[0] for key in audit['derivationCounts'] if key.endswith(':missing')}
    require(set(consumer.counts) == expected_rules, 'AUDIT_RULE_COVERAGE_DRIFT')
    for rule, counts in consumer.counts.items():
        require(counts['emitted'] == audit['derivationCounts'].get(rule+':missing', 0) and
                counts['strongerSuppressed'] == audit['derivationCounts'].get(rule+':suppressed', 0) and
                counts['duplicate'] == audit['derivationCounts'].get(rule+':existing', 0) +
                audit['derivationCounts'].get(rule+':duplicate', 0),
                'AUDIT_DERIVATION_RECONCILIATION:'+rule)
    added = sorted(consumer.derived,key=lambda e:e['id']); connected = set().union(*consumer.connected.values())
    residual = consumer.isolated-connected
    require(len(consumer.isolated) == audit['isolated'] and len(connected) == audit['potentialUnion'] and
            len(residual) == audit['remainingIsolated'], 'AUDIT_ISOLATION_RECONCILIATION')
    require(set(consumer.nodes) <= set(origins), 'MISSING_ORIGIN')
    summary = dict(version=VERSION,counts={k:dict(v) for k,v in sorted(consumer.counts.items())},
        originalNodes=len(graph['nodes']),originalEdges=len(graph['edges']),derivedEdges=len(added),
        isolatedBefore=len(consumer.isolated),formerlyIsolatedConnected=len(connected),isolatedAfter=len(residual),
        connectedByRule={k:len(v) for k,v in sorted(consumer.connected.items())},
        residualByFamilyClass=dict(sorted(Counter('|'.join(sorted(origins[i]))+':'+consumer.nodes[i]['class'] for i in residual).items())),
        auditReconciliation='matched_pinned_read_only_audit',
        originalRecordsUnchanged=True,providerCalls=0,kgAuthorization=False,
        originalNativeProvenancePath=str(SOURCE/'native-provenance.jsonl'),
        originalNativeProvenanceSha256=base['nativeProvenanceSha256'],
        authoritySha256=metrics.sha256_file(AUTHORITY),inputHashes=authority['inputHashes'],
        implementationSha256=metrics.sha256_file(Path(__file__)),
        derivationProvenanceSha256=metrics.sha256_file(output/'derivation-provenance.jsonl'))
    result = dict(graph,edges=graph['edges']+added,postAcceptanceDerivationVersion=VERSION,
                  derivationProvenanceSha256=summary['derivationProvenanceSha256'])
    result['components'] = graph.get('components', []) + [dict(label=VERSION, path='summary.json',
        sha256=digest(canonical(summary)+b'\n'), nodes=0, edges=len(added))]
    metrics.validate_snapshot(result)
    for name,value in [('summary.json',summary),('snapshot.json',result)]:
        with (output/name).open('xb') as f:
            f.write(canonical(value)+b'\n')
    (output/'summary.md').write_text(f"# Evaluation-only post-acceptance relationships\n\nOriginal nodes/edges unchanged. Added {len(added)} derived edges.\n\nIsolation: {len(consumer.isolated)} → {len(residual)}; {len(connected)} formerly isolated nodes connected.\n\nSee summary.json for per-rule counts and residual classes; these are not accuracy estimates.\n")
    metric_dir = output/'metrics'/'snapshots'; metric_dir.mkdir(parents=True)
    for path in Path('results/metrics/snapshots').glob('*.json'):
        require(read(path)['trajectoryOrder'] <= 40, 'UNEXPECTED_LATER_TRAJECTORY')
        shutil.copyfile(path,metric_dir/path.name)
    return summary


def main():
    """Block network and expose a single explicit offline command."""
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')), patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        result=run(args.output)
    print(json.dumps({k:result[k] for k in ('derivedEdges','isolatedBefore','isolatedAfter')},indent=2))


if __name__ == '__main__':
    main()
