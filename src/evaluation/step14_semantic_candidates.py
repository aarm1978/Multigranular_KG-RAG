"""Bounded offline comparison preparation; no embeddings, equivalence or graph writes."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import socket
import unicodedata
from unittest.mock import patch
from urllib.parse import urlsplit

from src.evaluation import step14_identity_preview as identity

OUTPUT = Path('var/study2_step14/semantic-candidates/v1')
VERSION = 'step14-semantic-candidates/0.1.0'
IDENTITY_CLASSES = {'Paper', 'DatasetResource', 'Repository', 'Person', 'Organization'}
VERSION_FIELDS = ('version', 'versionNumber', 'commitSHA', 'fork', 'forkParent', 'cffVersion')
LIMITATIONS = [
    'Candidates are not equivalences. No automatic identity merge is authorized for any class.',
    'Exact class blocking is conservative; cross-class conceptual comparisons are not generated.',
    'Labels use NFC, casefold and whitespace collapse only; no aliases, stemming or inferred granularity.',
    'Generic architecture and specific implementation can share a lexical block. Granularity stays unspecified; original descriptions supply context for later review.',
    'Missing version/detail is unknown, neither equality nor difference. Explicit version differences are review flags, not entity inequality.',
    'Geoconnex declarations are retained literally; namespace/version equivalence and geographic retyping are not inferred.',
    'Publication link_existing remains a request-context declaration, not a global identifier.',
    'Nonaccepted identity sidecars remain excluded. All original assertions remain in immutable inputs.',
    'Lexical blocking has limited recall; no embeddings, provider calls or scientific relations are produced.',
]


def token(value: object) -> str:
    """Make a deterministic content hash without inventing an entity identifier."""
    return hashlib.sha256(identity.encoded(value)).hexdigest()


def normalize(text: str) -> str:
    """Normalize representation only; retain punctuation and all meaningful tokens."""
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def descendants(classes: dict, parent: str) -> set[str]:
    """Follow only ontology-declared ancestry."""
    found = {parent}
    while True:
        expanded = found | {name for name, c in classes.items() if str(c.get('parent', '')).split(':')[-1] in found}
        if expanded == found:
            return found
        found = expanded


def literals(value: object) -> list[str]:
    """Retain literal strings only; never parse identifiers from free text."""
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [s for v in value for s in literals(v)]
    return []


def deterministic_family(node: dict) -> str | None:
    """Read documented deterministic lineage discriminators, not entity labels."""
    lineage = node.get('internalLineage', {})
    source = node.get('evidence', {}).get('sourceArtifact', '')
    if 'localPaperId' in lineage:
        return 'publications'
    if 'corpusPath' in lineage:
        return 'ciroh_hub'
    if isinstance(source, str) and source.startswith('hydroshare:'):
        return 'hydroshare'
    if 'rawSource' in lineage:
        return 'github'
    return None


def prepare(graph: dict, native_rows: Iterable[dict], spec: dict, max_block: int = 32,
            owners: dict | None = None) -> dict:
    """Preserve selected occurrences and build linear-size, capped candidate blocks."""
    identity.require(2 <= max_block <= 128, 'BLOCK_CAP_MUST_BE_2_TO_128')
    classes = {c['name']: c for c in spec['classes']}
    models = {n for n in descendants(classes, 'ComputationalModel') if not classes[n].get('abstract')}
    geo = descendants(classes, 'HydrologicFeature') | {'NamedPlace', 'Place'}
    comparison = models | {'Tool', 'Algorithm', 'Workflow'}
    selected = IDENTITY_CLASSES | geo | comparison
    nodes = {n['id']: n for n in graph['nodes']}
    identity.require(len(nodes) == len(graph['nodes']), 'DUPLICATE_NODE_ID')
    native = defaultdict(list)
    for row in native_rows:
        if row['kind'] != 'nodes':
            continue
        identity.require(row['graphID'] in nodes, 'SIDECAR_NODE_MISSING')
        identity.require(token(row['nativeRecord']) == row['nativeRecordSha256'], 'NATIVE_HASH_DRIFT')
        if nodes[row['graphID']]['class'] in selected:
            native[row['graphID']].append(row)
    own_dois = defaultdict(list)
    for edge in graph['edges']:
        if edge.get('relation') == 'hasIdentifier' and edge.get('inventoryId') == 'C-D04' and edge.get('evidence'):
            source, target = nodes[edge['source']], nodes[edge['target']]
            a = target.get('attributes', {})
            value = a.get('identifierValue')
            if (source['class'] == 'DatasetResource' and target['class'] == 'Identifier'
                    and a.get('identifierType') == 'DOI' and isinstance(value, str)
                    and re.fullmatch(r'10\.\d{4,9}/\S+', value) and not native[source['id']]):
                own_dois[source['id']].append(dict(scheme='doi', value=value, basis='C-D04', edgeID=edge['id']))
    records = []; exclusions = Counter()
    for nid in sorted(nodes):
        node = nodes[nid]; cls = node['class']
        if cls not in selected:
            exclusions[cls] += 1; continue
        attrs = deepcopy(node.get('attributes', {})); evidence = []; references = []
        families = set(); artifacts = set(); declarations = []; links = []; originals = []
        rows = sorted(native[nid], key=identity.encoded)
        for row in rows:
            record = row['nativeRecord']; pr = row['provenance']
            originals.append(deepcopy(record.get('originalCandidate', record.get('candidate', {}))))
            candidate = originals[-1]
            ev = record.get('boundEvidence', record.get('evidenceOccurrences', []))
            evidence.extend(deepcopy(ev))
            if pr.get('family'):
                families.add(pr['family'])
            owner = (owners or {}).get(pr.get('path'))
            if owner:
                artifacts.add(owner)
            for e in ev:
                for field in ('canonicalPaperID', 'sourceArtifact', 'sourceArtifactID'):
                    if isinstance(e.get(field), str) and e[field]:
                        artifacts.add(e[field])
            references.append(dict(nativeRecordSha256=row['nativeRecordSha256'], provenance=deepcopy(pr)))
            exact = candidate.get('exactIdentifier')
            if cls in {'Paper', 'DatasetResource', 'Repository'} and isinstance(exact, str):
                bound = any(exact in e.get('evidenceText', '') for e in ev)
                declarations.append(dict(scheme='literal_exactIdentifier', value=exact,
                                         basis='accepted_source_local_candidate', evidenceBound=bound,
                                         scope='source_local_no_global_equivalence'))
            if candidate.get('action') == 'link_existing':
                links.append(candidate.get('existingNodeID'))
        if not rows:
            if node.get('evidence'):
                evidence.append(deepcopy(node['evidence']))
                if node['evidence'].get('sourceArtifact'):
                    artifacts.add(node['evidence']['sourceArtifact'])
            family = deterministic_family(node)
            if family:
                families.add(family)
            declarations.extend(dict(scheme=s, value=v, basis='deterministic_entity_own_field')
                                for s, v in sorted(identity.own_keys(node)))
            declarations.extend(own_dois[nid])
            value = attrs.get('identifierValue')
            if cls in geo and attrs.get('identifierRegime') == 'geoconnex-url' and isinstance(value, str):
                parsed = urlsplit(value)
                if parsed.scheme in {'http', 'https'} and parsed.hostname == 'geoconnex.us':
                    declarations.append(dict(scheme='geoconnex-url', value=value,
                                             basis='deterministic_geospatial_target', scope='literal_only_no_namespace_equivalence'))
        reasons = []
        if cls not in classes or node.get('inventoryId') != classes[cls]['id']:
            reasons.append('ontology_class_inventory_mismatch')
        if not evidence or not artifacts or not families:
            reasons.append('missing_provenance')
        if classes.get(cls, {}).get('abstract'):
            reasons.append('abstract_class_retained_not_retyped')
        labels = sorted(set(s for field in ('label', 'name', 'title', 'displayName', 'fullName') for s in literals(attrs.get(field))))
        descriptions = sorted(set(s for field in ('description', 'abstract', 'definition') for s in literals(attrs.get(field))))
        quotes = sorted(set(s for e in evidence for s in literals(e.get('evidenceText'))))
        normalized = sorted({normalize(label) for label in labels})
        if len(normalized) > 1:
            reasons.append('multiple_lexical_labels')
        versions = {f: deepcopy(attrs[f]) for f in VERSION_FIELDS if f in attrs}
        records.append(dict(occurrenceID=nid, ontologyClass=cls, inventoryId=node.get('inventoryId'),
            lane='semantic_comparison' if cls in comparison else 'identity_declaration',
            attributes=attrs, versions=versions, sourceFamilies=sorted(families), sourceArtifacts=sorted(artifacts),
            evidenceReferences=sorted(evidence, key=identity.encoded), nativeReferences=references,
            originalCandidates=originals, originalSnapshotRecord=deepcopy(node), snapshotRecordSha256=token(node),
            identifierDeclarations=sorted(declarations, key=identity.encoded), declaredExistingNodeIDs=sorted(links, key=identity.encoded),
            labels=labels, normalizedLabels=normalized, contextualDescriptions=descriptions,
            embeddingText='\n'.join([cls, *labels, *descriptions, *quotes]),
            granularity='unspecified_requires_context_review', identityDecision='not_assessed',
            automaticMergeEligible=False, preparationFlags=reasons))
    buckets = defaultdict(list)
    for r in records:
        if any(f in r['preparationFlags'] for f in ('missing_provenance', 'ontology_class_inventory_mismatch', 'abstract_class_retained_not_retyped')):
            continue
        if r['lane'] == 'semantic_comparison' and len(r['normalizedLabels']) == 1:
            buckets[('lexical_similarity_only', r['ontologyClass'], r['normalizedLabels'][0])].append(r)
        # Each literal declaration is an independent block, never transitive union.
        for d in r['identifierDeclarations']:
            if d.get('evidenceBound') is False:
                continue
            buckets[('identifier_declaration_only', r['ontologyClass'], d['scheme'], d['value'])].append(r)
    blocks = []
    for key, members in sorted(buckets.items()):
        members = sorted({r['occurrenceID']: r for r in members}.values(), key=lambda r: r['occurrenceID'])
        if len(members) < 2:
            continue
        ids = [r['occurrenceID'] for r in members]
        flags = []
        for field in VERSION_FIELDS:
            values = {identity.encoded(r['versions'][field]) for r in members if r['versions'].get(field) is not None}
            if len(values) > 1:
                flags.append('explicit_version_conflict:' + field)
            if any(r['versions'].get(field) is None for r in members):
                flags.append('unknown_version:' + field)
        oversized = len(ids) > max_block
        blocks.append(dict(blockID=token(key), key=key, memberCount=len(ids),
            occurrenceIDs=[] if oversized else ids, membershipSha256=token(ids),
            status='oversized_not_expanded' if oversized else 'ambiguous_candidates_only',
            flags=flags, equivalenceAsserted=False))
    return dict(records=records, blocks=blocks, coverage=dict(
        inputNodes=len(nodes), preparedOccurrences=len(records), excludedByClass=dict(sorted(exclusions.items())),
        preparedByClass=dict(sorted(Counter(r['ontologyClass'] for r in records).items())),
        preparationFlags=dict(sorted(Counter(f for r in records for f in r['preparationFlags']).items())),
        blockStatuses=dict(sorted(Counter(b['status'] for b in blocks).items()))))


def run(output: Path = OUTPUT, max_block: int = 32) -> dict:
    """Verify original authorities and write fresh ignored comparison artifacts."""
    identity.require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    identity.require(output.resolve().is_relative_to(Path('var/study2_step14/semantic-candidates').resolve()), 'SEMANTIC_OUTPUT_REQUIRED')
    graph, spec, sidecar, pins = identity.verified_inputs()
    identity.require(spec['ontology']['version'] == '0.1.7', 'ONTOLOGY_VERSION_DRIFT')
    owners = {}
    def rows() -> Iterable[dict]:
        """Read native records and resolve only explicit hash-bound owner provenance."""
        with sidecar.open() as handle:
            for line in handle:
                row = json.loads(line); pr = row.get('provenance', {})
                if row['kind'] == 'nodes' and pr.get('path') and pr['path'] not in owners:
                    path = Path(pr['path'])
                    identity.require(identity.sha(path) == pr['sha256'], 'OWNER_HASH_DRIFT')
                    owners[str(path)] = json.loads(path.read_bytes())['owner']['endpointID']
                    pins[str(path)] = pr['sha256']
                yield row
    result = prepare(graph, rows(), spec, max_block, owners)
    manifest = dict(version=VERSION, candidatePreparationOnly=True, embeddingsComputed=0, providerCalls=0,
                    graphWrites=0, equivalencesAsserted=0, maxBlockSize=max_block, inputHashes=pins,
                    implementationHashes={'src/evaluation/step14_semantic_candidates.py': identity.sha(Path(__file__)),
                                          'src/evaluation/step14_identity_preview.py': identity.sha(Path(identity.__file__))},
                    coverage=result['coverage'], limitations=LIMITATIONS)
    output.mkdir(parents=True, exist_ok=False)
    for name, values in (('occurrences.jsonl', result['records']), ('candidate-blocks.jsonl', result['blocks'])):
        with (output / name).open('xb') as handle:
            for value in values:
                handle.write(identity.encoded(value) + b'\n')
    manifest['outputHashes'] = {name: identity.sha(output / name) for name in ('occurrences.jsonl', 'candidate-blocks.jsonl')}
    (output / 'manifest.json').write_bytes(identity.encoded(manifest) + b'\n')
    (output / 'report.md').write_text('# Step 14 semantic candidate preparation\n\n'
        + 'Candidates only; no identity or conceptual equivalence is asserted.\n\n'
        + '\n'.join(f'- {k}: {json.dumps(v, sort_keys=True)}' for k, v in result['coverage'].items())
        + '\n\n## Limitations\n\n' + '\n'.join('- ' + s for s in LIMITATIONS) + '\n')
    return manifest


def main() -> None:
    """Disable network connections during the researcher-terminal offline job."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--max-block-size', type=int, default=32, choices=range(2, 129))
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('OFFLINE_ONLY')), patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('OFFLINE_ONLY')):
        run(args.output, args.max_block_size)


if __name__ == '__main__':
    main()
