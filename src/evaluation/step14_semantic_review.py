"""Compact offline dossiers for existing candidates; no alignment adjudication."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable
from copy import deepcopy
import json
from pathlib import Path
import socket
from unittest.mock import patch

import yaml

from src.evaluation import step14_semantic_candidates as candidates
from src.evaluation.step14_identity_preview import encoded, require, sha

INPUT = Path('var/study2_step14/semantic-candidates/v1')
OUTPUT = Path('var/study2_step14/semantic-review/v1')
VERSION = 'step14-semantic-review/0.1.0'
EVIDENCE_LIMIT = 2
EXCERPT_CHARS = 600
FIELD_CHARS = 1200
PROVENANCE_LIMIT = 3
EXCLUDED_FLAGS = {'missing_provenance', 'ontology_class_inventory_mismatch', 'abstract_class_retained_not_retyped'}
LIMITATIONS = [
    'Diagnostic preparation only: no identity decisions, similarity scores, thresholds or equivalences.',
    'Conceptual similarity does not establish implementation identity; generic and trained LSTM occurrences remain distinct pending context review.',
    'Missing detail/version is unknown, not evidence of either identity or difference.',
    'Local literal identifiers and request-local link_existing declarations are never promoted to global identifiers.',
    'Source-family counts use authoritative sourceFamilies, never occurrence-ID prefixes.',
    'Distinct artifact counts use exact recorded artifact IDs, not resolved aliases or independent corroboration. Repeated mentions are not independent evidence.',
    'Multi-family occurrence memberships can contribute to more than one family count. Artifact-to-family pairing is not inferred.',
    'Evidence selection is mechanical, not an assessment of support or an annotation campaign.',
    'Oversized blocks retain complete membership counts/hashes and reconstruction keys; no pairs or selected subsets are generated.',
]


def record_keys(row: dict) -> set[tuple]:
    """Reconstruct the frozen v0.1.0 preparation keys without expanding coverage."""
    if EXCLUDED_FLAGS.intersection(row['preparationFlags']):
        return set()
    result = set()
    if row['lane'] == 'semantic_comparison' and len(row['normalizedLabels']) == 1:
        result.add(('lexical_similarity_only', row['ontologyClass'], row['normalizedLabels'][0]))
    for declaration in row['identifierDeclarations']:
        if declaration.get('evidenceBound') is not False:
            result.add(('identifier_declaration_only', row['ontologyClass'], declaration['scheme'], declaration['value']))
    return result


def reference(row: dict, field: str = '') -> dict:
    """Locate a full original value in the manifest-pinned occurrence file."""
    return dict(file='occurrences.jsonl', occurrenceID=row['occurrenceID'],
                occurrenceSha256=candidates.token(row), jsonPointer=field)


def bounded(value: object, ref: dict, limit: int = FIELD_CHARS) -> dict:
    """Keep small values verbatim and explicitly summarize longer values by reference."""
    text = encoded(value).decode()
    result = dict(reference=ref, valueSha256=candidates.token(value), serializedCharacters=len(text), truncated=len(text) > limit)
    if len(text) <= limit:
        result['value'] = deepcopy(value)
    else:
        result['canonicalJsonExcerpt'] = text[:limit]
    return result


def compact_member(row: dict) -> dict:
    """Preserve recoverable provenance and bounded literal evidence for one occurrence."""
    base = reference(row)
    def ref(field: str) -> dict:
        """Use the same original occurrence hash for all field references."""
        return dict(base, jsonPointer=field)
    evidence = row['evidenceReferences']
    # Stable content order, with original index retained for exact recovery.
    order = sorted(range(len(evidence)), key=lambda i: (encoded(evidence[i]), i))
    excerpts = []
    for index in order[:EVIDENCE_LIMIT]:
        item = evidence[index]; value = item.get('evidenceText')
        text = value if isinstance(value, str) else ''
        metadata = {k: v for k, v in item.items() if k != 'evidenceText'}
        excerpts.append(dict(reference=ref(f'/evidenceReferences/{index}'), evidenceSha256=candidates.token(item),
                             excerpt=text[:EXCERPT_CHARS], originalCharacters=len(text),
                             truncated=len(text) > EXCERPT_CHARS, missingEvidenceText=not bool(text),
                             metadata=bounded(metadata, dict(ref(f'/evidenceReferences/{index}'), projectionExcludedKeys=['evidenceText']))))
    scopes = []
    for d in row['identifierDeclarations']:
        basis = d.get('basis')
        if basis in {'deterministic_entity_own_field', 'C-D04'}:
            scope = 'deterministic_entity_own_identifier'
        elif basis == 'accepted_source_local_candidate':
            scope = 'source_local_literal_declaration'
        elif basis == 'deterministic_geospatial_target':
            scope = 'literal_geographic_declaration_no_namespace_equivalence'
        else:
            scope = 'unsupported_scope_requires_review'
        scopes.append(dict(declaration=deepcopy(d), scopeCategory=scope))
    provenance = row['nativeReferences']
    provenance_indices = sorted(range(len(provenance)), key=lambda i: (encoded(provenance[i]), i))[:PROVENANCE_LIMIT]
    missing = [field for field in ('sourceArtifacts', 'evidenceReferences', 'identifierDeclarations', 'versions', 'labels', 'contextualDescriptions') if not row.get(field)]
    result = dict(occurrenceID=row['occurrenceID'], ontologyClass=row['ontologyClass'], inventoryId=row['inventoryId'],
                  occurrenceReference=base, sourceFamilies=sorted(row['sourceFamilies']), sourceArtifacts=sorted(row['sourceArtifacts']),
                  attributeNames=sorted(row['attributes']),
                  preparationFlags=deepcopy(row['preparationFlags']), missingInformation=missing,
                  granularity=row.get('granularity'), identityDecision='not_assessed',
                  identifierScopeCounts=dict(sorted(Counter(d['scopeCategory'] for d in scopes).items())),
                  identifierDeclarations=bounded(row['identifierDeclarations'], ref('/identifierDeclarations')),
                  evidenceSelection=dict(total=len(evidence), selected=len(excerpts), omitted=len(evidence)-len(excerpts),
                                         rule='first canonical-JSON-sorted evidence records; original array indices preserved'),
                  evidenceExcerpts=excerpts,
                  originalProvenance=dict(total=len(provenance), omitted=len(provenance)-len(provenance_indices),
                      fullReference=ref('/nativeReferences'), selected=[bounded(provenance[i], ref(f'/nativeReferences/{i}')) for i in provenance_indices]),
                  originalSnapshotReference=ref('/originalSnapshotRecord'))
    for field in ('labels', 'versions', 'attributes', 'contextualDescriptions', 'declaredExistingNodeIDs'):
        result[field] = bounded(row.get(field), ref('/' + field))
    return result


def string_set(values: object, reason: str, nonempty: bool = False) -> set[str]:
    """Validate authoritative set-valued provenance without guessing missing members."""
    require(isinstance(values, list) and all(isinstance(v, str) and v for v in values), reason)
    require(len(values) == len(set(values)) and (bool(values) or not nonempty), reason)
    return set(values)


def prepare(occurrences: Iterable[dict], blocks: list[dict], spec: dict, max_block: int) -> dict:
    """Reconcile every original block and summarize all cross-family candidates."""
    require(2 <= max_block <= 128, 'INVALID_BLOCK_CAP')
    classes = {c['name']: c['id'] for c in spec['classes']}
    block_index = {}; potential_members = set()
    for block in blocks:
        key = tuple(block['key'])
        require(len(key) in (3, 4) and all(isinstance(k, str) and k for k in key), 'INVALID_BLOCK_KEY')
        require((key[0] == 'lexical_similarity_only' and len(key) == 3) or
                (key[0] == 'identifier_declaration_only' and len(key) == 4), 'UNSUPPORTED_MECHANISM')
        require(block['blockID'] == candidates.token(key), 'BLOCK_ID_DRIFT')
        require(key not in block_index, 'DUPLICATE_BLOCK')
        require(block.get('equivalenceAsserted') is False, 'UNEXPECTED_EQUIVALENCE')
        block_index[key] = block
        potential_members.update(block['occurrenceIDs'])
    members = defaultdict(set); index = {}; compact = {}
    for row in occurrences:
        nid = row['occurrenceID']
        require(isinstance(nid, str) and bool(nid), 'INVALID_OCCURRENCE_ID')
        require(nid not in index, 'DUPLICATE_OCCURRENCE_ID:' + nid)
        families = string_set(row['sourceFamilies'], 'INVALID_SOURCE_FAMILIES')
        artifacts = string_set(row['sourceArtifacts'], 'INVALID_SOURCE_ARTIFACTS')
        keys = record_keys(row)
        if keys:
            require(classes.get(row['ontologyClass']) == row['inventoryId'], 'ONTOLOGY_CLASS_DRIFT')
            require(bool(families) and bool(artifacts) and bool(row['evidenceReferences']), 'MISSING_MEMBER_PROVENANCE')
        index[nid] = dict(sourceFamilies=families, sourceArtifacts=artifacts)
        for key in keys:
            members[key].add(nid)
        if nid in potential_members:
            compact[nid] = compact_member(row)
    expected_keys = {key for key, ids in members.items() if len(ids) >= 2}
    require(expected_keys == set(block_index), 'BLOCK_SET_MEMBERSHIP_DRIFT')
    dossier = []; oversized = []; classifications = Counter(); coverage_groups = defaultdict(list)
    for key, block in sorted(block_index.items()):
        ids = sorted(members[key]); count = len(ids)
        require(block['memberCount'] == count, 'MEMBER_COUNT_DRIFT')
        require(block['membershipSha256'] == candidates.token(ids), 'MEMBERSHIP_HASH_DRIFT')
        is_oversized = count > max_block
        expected_status = 'oversized_not_expanded' if is_oversized else 'ambiguous_candidates_only'
        require(block['status'] == expected_status, 'BLOCK_STATUS_DRIFT')
        listed = block['occurrenceIDs']
        require(isinstance(listed, list) and len(listed) == len(set(listed)), 'DUPLICATE_BLOCK_MEMBER')
        require(listed == ([] if is_oversized else ids), 'BLOCK_MEMBERSHIP_DRIFT')
        family_counts = Counter(f for nid in ids for f in index[nid]['sourceFamilies'])
        artifacts = sorted({a for nid in ids for a in index[nid]['sourceArtifacts']})
        combination = sorted(family_counts)
        classification = 'oversized' if is_oversized else 'cross_family' if len(combination) > 1 else 'within_family'
        classifications[classification] += 1
        base = dict(blockID=block['blockID'], key=list(key), ontologyClass=key[1], candidateMechanism=key[0],
                    memberCount=count, membershipSha256=block['membershipSha256'], membershipVerified=True,
                    sourceFamilyDistribution=dict(sorted(family_counts.items())), sourceFamilyCombination=combination,
                    sourceFamilySetDistribution=dict(sorted(Counter('|'.join(sorted(index[n]['sourceFamilies'])) for n in ids).items())),
                    distinctSupportingArtifactCount=len(artifacts), sourceArtifactMembershipSha256=candidates.token(artifacts),
                    existingBlockFlags=deepcopy(block['flags']), identityDecision='not_assessed', equivalenceAsserted=False)
        if is_oversized:
            oversized.append(dict(base, classification='oversized', crossFamily=len(combination) > 1,
                                  reconstruction=dict(file='occurrences.jsonl', rule='step14-semantic-candidates/0.1.0', key=list(key)),
                                  pairsGenerated=0, subsetsSelected=False))
        elif classification == 'cross_family':
            dossier.append(dict(base, occurrenceIDs=ids, sourceArtifacts=artifacts, members=[compact[n] for n in ids],
                                uncertainty=LIMITATIONS[:4]))
        for dimension, value in (('class', key[1]), ('candidateMechanism', key[0]), ('sourceFamilyCombination', '|'.join(combination))):
            coverage_groups[(classification, dimension, value)].append((ids, artifacts))
    coverage = []
    for (classification, dimension, value), groups in sorted(coverage_groups.items()):
        coverage.append(dict(classification=classification, dimension=dimension, value=value, blocks=len(groups),
                             memberOccurrences=sum(len(g[0]) for g in groups),
                             distinctOccurrences=len({n for g in groups for n in g[0]}),
                             distinctSupportingArtifacts=len({a for g in groups for a in g[1]})))
    cross_ids = {n for d in dossier for n in d['occurrenceIDs']}
    return dict(dossier=dossier, oversized=oversized, coverage=coverage,
                summary=dict(inputOccurrences=len(index), inputBlocks=len(blocks),
                    classifications={k: classifications[k] for k in ('cross_family', 'within_family', 'oversized')},
                    dossierBlocks=len(dossier), oversizedBlocks=len(oversized),
                    distinctDossierOccurrences=len(cross_ids),
                    distinctDossierSupportingArtifacts=len({a for n in cross_ids for a in index[n]['sourceArtifacts']})))


def json_rows(path: Path) -> Iterable[dict]:
    """Stream existing JSONL records without changing their bytes."""
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            yield json.loads(line)


def verify_inputs(root: Path) -> tuple[dict, dict, dict]:
    """Check the manifest-pinned dataset, reconstruction implementation and ontology."""
    manifest_path = root / 'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    require(manifest['version'] == candidates.VERSION, 'UNSUPPORTED_INPUT_VERSION')
    require(manifest.get('candidatePreparationOnly') is True and manifest.get('equivalencesAsserted') == 0, 'NOT_CANDIDATE_INPUT')
    pins = {str(manifest_path): sha(manifest_path)}
    def check(path: Path, expected: str) -> None:
        """Fail before publishing any output on missing files or byte drift."""
        require(sha(path) == expected, 'INPUT_HASH_DRIFT:' + str(path))
        pins[str(path)] = expected
    for name in ('occurrences.jsonl', 'candidate-blocks.jsonl'):
        check(root / name, manifest['outputHashes'][name])
    for name in ('src/evaluation/step14_semantic_candidates.py', 'src/evaluation/step14_identity_preview.py'):
        check(Path(name), manifest['implementationHashes'][name])
    for name in ('src/ontology/ontology_spec.yaml', 'src/ontology/ciroh_ontology.owl'):
        check(Path(name), manifest['inputHashes'][name])
    spec = yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())
    require(spec['ontology']['version'] == '0.1.7', 'ONTOLOGY_VERSION_DRIFT')
    return manifest, spec, pins


def run(root: Path = INPUT, output: Path = OUTPUT) -> dict:
    """Write four fresh ignored diagnostics only after complete input reconciliation."""
    require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    require(output.resolve().is_relative_to(Path('var/study2_step14/semantic-review').resolve()), 'REVIEW_OUTPUT_REQUIRED')
    manifest, spec, pins = verify_inputs(root)
    result = prepare(json_rows(root / 'occurrences.jsonl'), list(json_rows(root / 'candidate-blocks.jsonl')), spec, manifest['maxBlockSize'])
    require(result['summary']['inputOccurrences'] == manifest['coverage']['preparedOccurrences'], 'OCCURRENCE_COVERAGE_DRIFT')
    actual_statuses = Counter(b['status'] for b in json_rows(root / 'candidate-blocks.jsonl'))
    require(dict(actual_statuses) == manifest['coverage']['blockStatuses'], 'BLOCK_COVERAGE_DRIFT')
    # Detect concurrent edits during reading before creating the output directory.
    for path, expected in pins.items():
        require(sha(Path(path)) == expected, 'INPUT_CHANGED_DURING_REVIEW:' + path)
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in (('review-dossier.jsonl', result['dossier']), ('oversized-summary.jsonl', result['oversized'])):
        with (output / name).open('xb') as handle:
            for row in rows:
                handle.write(encoded(row) + b'\n')
    report = ['# Step 14 semantic review dossier', '', 'Diagnostic preparation only; no adjudication or alignment.', '',
              *[f'- {key}: {json.dumps(value, sort_keys=True)}' for key, value in result['summary'].items()], '',
              '## Coverage', '', '| Classification | Dimension | Value | Blocks | Distinct occurrences | Distinct artifact IDs |',
              '|---|---|---|---:|---:|---:|']
    for c in result['coverage']:
        report.append(f"| {c['classification']} | {c['dimension']} | {c['value'].replace('|', ', ')} | {c['blocks']} | {c['distinctOccurrences']} | {c['distinctSupportingArtifacts']} |")
    report += ['', 'Counts of artifact IDs are documentary coverage, not independent corroboration.', '', '## Limits', '', *['- ' + s for s in LIMITATIONS]]
    (output / 'report.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    record = dict(version=VERSION, diagnosticOnly=True, equivalencesAsserted=0, providerCalls=0, graphWrites=0,
                  inputRoot=str(root), inputHashes=pins, inputManifestTrust='Existing supplied manifest; its hash is recorded, not independently signed.',
                  implementationSha256=sha(Path(__file__)), summary=result['summary'], coverage=result['coverage'],
                  compactLimits=dict(evidenceRecords=EVIDENCE_LIMIT, excerptCharacters=EXCERPT_CHARS,
                                     serializedFieldCharacters=FIELD_CHARS, nativeProvenanceRecords=PROVENANCE_LIMIT),
                  limitations=LIMITATIONS,
                  outputHashes={name: sha(output / name) for name in ('review-dossier.jsonl', 'oversized-summary.jsonl', 'report.md')})
    (output / 'manifest.json').write_bytes(encoded(record) + b'\n')
    return record


def main() -> None:
    """Run from the researcher terminal with networking disabled."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('OFFLINE_ONLY')), patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('OFFLINE_ONLY')):
        run(output=args.output)


if __name__ == '__main__':
    main()
