"""Read-only identifier-scope diagnostics over the pinned cross-family dossier."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import csv
import json
from pathlib import Path
import re
import socket
from unittest.mock import patch
from urllib.parse import urlsplit

import yaml

from src.evaluation import step14_semantic_review as review
from src.evaluation.step14_identity_preview import encoded, require, sha

ROOT = Path('var/study2_step14/semantic-review/v1')
OUTPUT = Path('var/study2_step14/identifier-scope-triage/v1')
MANIFEST_SHA256 = '2ef9062cac151ed73342e39793cbedd76e4e631ca37a3e2c3b448d95bf59ae69'
VERSION = 'step14-identifier-scope-triage/0.1.0'
RELATION_CAP = 32
LIMITS = [
    'All categories are unadjudicated diagnostic recommendations; no equivalence, canonical ID or graph assertion is produced.',
    'Entity identity, reference-target identity and conceptual identity are separate. Conceptual identity is outside this identifier-only pass.',
    'Matching local literals establish locator coincidence only, not versions, implementation identity or scientific-content identity.',
    'Locator categories describe syntax, not live content. No URL is resolved; query strings, fragments and path case are preserved.',
    'Description/label variation is a review cue, not proof of contradiction. Missing versions alone do not invalidate record identity.',
    'Repeated quotations, mirrored documentation and multiple artifacts never count as independent identity confirmation.',
    'Evidence reuse checks cover only saved excerpts/full evidence hashes. Omitted or truncated evidence is explicitly incomplete.',
    'Truncated declarations or versions are unresolved; no full occurrence dataset or lexical/oversized membership is expanded.',
]


def digest(value: object) -> str:
    """Reuse the established deterministic JSON hash."""
    return review.candidates.token(value)


def value(member: dict, field: str) -> object | None:
    """Read only complete, hash-consistent bounded dossier values."""
    wrapper = member[field]
    if wrapper['truncated']:
        return None
    require('value' in wrapper and digest(wrapper['value']) == wrapper['valueSha256'], 'DOSSIER_FIELD_HASH_DRIFT')
    return wrapper['value']


def locator(raw: str) -> dict:
    """Classify explicit locator syntax without canonicalization or content lookup."""
    result = dict(raw=raw, category='unknown_literal', relationshipKeys=[])
    if re.fullmatch(r'10\.\d{4,9}/\S+', raw):
        return dict(result, category='doi_identifier', relationshipKeys=[['doi', raw]])
    if re.fullmatch(r'[0-9a-f]{32}', raw):
        return dict(result, category='hydroshare_resource_id_syntax', relationshipKeys=[['hydroshare', raw]])
    try:
        u = urlsplit(raw)
        port = u.port
    except ValueError:
        return result
    if u.scheme not in {'http', 'https', 's3'} or not u.netloc or u.username or port:
        return result
    host = u.hostname; parts = [p for p in u.path.split('/') if p]
    result.update(scheme=u.scheme, host=host, path=u.path, query=u.query, fragment=u.fragment)
    if u.query or u.fragment:
        return dict(result, category='query_or_fragment_locator_requires_context')
    # No path decoding, case folding, dot-segment resolution or reference parsing.
    if any(p in {'.', '..'} for p in parts) or '%' in u.path or '//' in u.path:
        return dict(result, category='encoded_or_nonliteral_path_requires_context')
    if host == 'github.com' and len(parts) >= 2:
        if len(parts) == 2:
            clone = parts[1].endswith('.git')
            repo = parts[1][:-4] if clone else parts[1]
            return dict(result, category='github_clone_url' if clone else 'github_repository_root',
                        relationshipKeys=[['github', parts[0], repo]] if repo else [])
        if len(parts) >= 4 and parts[2] == 'tree':
            return dict(result, category='github_branch_tree_path')
        if len(parts) >= 5 and parts[2] in {'blob', 'raw'}:
            return dict(result, category='github_specific_file_path')
        return dict(result, category='github_other_path_requires_context')
    if host in {'hydroshare.org', 'www.hydroshare.org'} and len(parts) == 2 and parts[0] == 'resource' and re.fullmatch(r'[0-9a-f]{32}', parts[1]):
        return dict(result, category='hydroshare_resource_url', relationshipKeys=[['hydroshare', parts[1]]])
    if host in {'doi.org', 'dx.doi.org'} and re.fullmatch(r'10\.\d{4,9}/\S+', u.path.lstrip('/')):
        return dict(result, category='doi_resolver_url', relationshipKeys=[['doi', u.path[1:]]])
    if u.scheme == 's3' or (host and (host.endswith('.s3.amazonaws.com') or host == 's3.amazonaws.com')):
        key_parts = parts[1:] if host == 's3.amazonaws.com' else parts
        return dict(result, category='object_store_bucket_root' if not key_parts else
                    'object_store_directory_prefix' if u.path.endswith('/') else 'object_store_specific_key_syntax')
    last = parts[-1].lower() if parts else ''
    if last in {'index', 'index.html', 'index.htm', 'catalog', 'catalog.html'}:
        return dict(result, category='index_or_catalog_path')
    if last in {'registry', 'registries', 'portal', 'portals'}:
        return dict(result, category='registry_or_portal_path')
    if re.search(r'\.(zip|tar|gz|tgz|nc|csv|json|parquet|h5|hdf5|tif|tiff|pdf)$', last):
        return dict(result, category='specific_download_path_syntax')
    return dict(result, category='directory_or_site_root_syntax' if u.path.endswith('/') or not parts else 'generic_url_requires_context')


def triage(block: dict, classes: dict[str, str]) -> dict:
    """Recommend a scope category while retaining every original block member."""
    key = block['key']; ids = block['occurrenceIDs']; members = sorted(block['members'], key=lambda m: m['occurrenceID'])
    require(len(key) == 4 and key[0] == block['candidateMechanism'] == 'identifier_declaration_only', 'INVALID_IDENTIFIER_BLOCK')
    require(block['blockID'] == digest(key), 'BLOCK_ID_DRIFT')
    require(ids == sorted(set(ids)) and ids == [m['occurrenceID'] for m in members], 'MEMBERSHIP_DRIFT')
    require(len(ids) == block['memberCount'] and digest(ids) == block['membershipSha256'], 'MEMBERSHIP_HASH_DRIFT')
    require(block.get('equivalenceAsserted') is False and block['ontologyClass'] == key[1], 'BLOCK_CONTRACT_DRIFT')
    families = Counter(f for m in members for f in review.string_set(m['sourceFamilies'], 'INVALID_FAMILIES', True))
    require(dict(families) == block['sourceFamilyDistribution'] and len(families) > 1, 'FAMILY_DISTRIBUTION_DRIFT')
    risks = set(); scopes = Counter(); member_views = []; matching_all = True
    labels = set(); descriptions = set(); version_values = defaultdict(set); quotes = defaultdict(set); hashes = defaultdict(set)
    for m in members:
        nid = m['occurrenceID']
        require(m['occurrenceReference']['occurrenceID'] == nid, 'OCCURRENCE_REFERENCE_DRIFT')
        if m['ontologyClass'] != key[1] or m['inventoryId'] != classes.get(key[1]):
            risks.add('incompatible_ontology_class')
        declarations = value(m, 'identifierDeclarations')
        matches = [] if declarations is None else [d for d in declarations if d.get('scheme') == key[2] and d.get('value') == key[3]]
        if declarations is None:
            risks.add('truncated_identifier_declarations'); matching_all = False
        elif not matches:
            raise ValueError('DECLARATION_KEY_DRIFT')
        own = bool(matches) and all(d.get('basis') in {'deterministic_entity_own_field', 'C-D04'} and d.get('scope') in (None, 'entity_own') for d in matches)
        local = bool(matches) and all(d.get('basis') == 'accepted_source_local_candidate' and d.get('evidenceBound') is True for d in matches)
        scope = 'deterministic_entity_own_identifier' if own else 'source_local_literal_declaration' if local else 'unsupported_or_incomplete_scope'
        scopes[scope] += 1
        if m.get('preparationFlags'):
            risks.add('existing_preparation_flags_require_review')
        if scope == 'unsupported_or_incomplete_scope':
            risks.add('unsupported_or_incomplete_scope')
        if declarations:
            competing = {d['value'] for d in declarations if d.get('scheme') == key[2] and d.get('basis') in {'deterministic_entity_own_field', 'C-D04'}}
            if len(competing) > 1:
                risks.add('conflicting_entity_own_identifiers')
        for field, destination in (('labels', labels), ('contextualDescriptions', descriptions)):
            current = value(m, field)
            if current is None:
                risks.add('truncated_' + field)
            elif current:
                destination.add(encoded(current))
        versions = value(m, 'versions')
        if versions is None:
            risks.add('truncated_versions')
        elif not versions or all(v in (None, '') for v in versions.values()):
            risks.add('missing_version_information')
        if isinstance(versions, dict):
            for field, v in versions.items():
                if v not in (None, ''):
                    version_values[field].add(encoded(v))
        if m.get('granularity') in (None, 'unspecified_requires_context_review'):
            risks.add('referent_granularity_requires_context')
        if m['evidenceSelection']['omitted']:
            risks.add('evidence_reuse_check_incomplete')
        for e in m['evidenceExcerpts']:
            hashes[e['evidenceSha256']].update(m['sourceFamilies'])
            if e['excerpt']:
                quotes[(e['excerpt'], e['truncated'])].update(m['sourceFamilies'])
            if e['truncated']:
                risks.add('evidence_reuse_check_incomplete')
        if not m['evidenceExcerpts']:
            risks.add('missing_evidence_excerpt')
        member_views.append(dict(occurrenceID=nid, sourceFamilies=deepcopy(m['sourceFamilies']), sourceArtifacts=deepcopy(m['sourceArtifacts']),
            identifierScope=scope, occurrenceReference=deepcopy(m['occurrenceReference']),
            identifierDeclarations=deepcopy(m['identifierDeclarations']), labels=deepcopy(m['labels']), versions=deepcopy(m['versions']),
            contextualDescriptions=deepcopy(m['contextualDescriptions']), evidenceReferences=deepcopy(m['evidenceExcerpts']),
            originalProvenance=deepcopy(m['originalProvenance']), preparationFlags=deepcopy(m['preparationFlags']),
            missingInformation=deepcopy(m['missingInformation'])))
    if len(labels) > 1:
        risks.add('divergent_labels')
    if len(descriptions) > 1:
        risks.add('potentially_conflicting_description_variants')
    if any(len(v) > 1 for v in version_values.values()) or any(f.startswith('explicit_version_conflict:') for f in block['existingBlockFlags']):
        risks.add('explicit_version_conflict_requires_review')
    if any(len(f) > 1 for f in hashes.values()) or any(len(f) > 1 for (_, truncated), f in quotes.items() if not truncated):
        risks.add('duplicated_evidence_across_families')
    if any(len(f) > 1 for (_, truncated), f in quotes.items() if truncated):
        risks.add('shared_truncated_excerpt_not_proven_full_duplicate')
    syntax = locator(key[3])
    unresolved_locator = syntax['category'] in {'unknown_literal', 'object_store_bucket_root', 'object_store_directory_prefix', 'index_or_catalog_path', 'registry_or_portal_path', 'directory_or_site_root_syntax'} or syntax['category'].endswith('requires_context')
    if unresolved_locator:
        risks.add('locator_referent_scope_requires_context')
    authority_compatible = ((key[2] == 'doi' and key[1] in {'Paper', 'DatasetResource'} and syntax['category'] == 'doi_identifier') or
                            (key[2] == 'hydroshare' and key[1] == 'DatasetResource' and syntax['category'] == 'hydroshare_resource_id_syntax'))
    material = {'incompatible_ontology_class', 'conflicting_entity_own_identifiers', 'explicit_version_conflict_requires_review',
                'truncated_identifier_declarations', 'truncated_versions', 'unsupported_or_incomplete_scope', 'missing_evidence_excerpt'}
    if scopes['deterministic_entity_own_identifier'] and not authority_compatible:
        risks.add('authoritative_identifier_class_or_scheme_outside_strong_rule')
    strong = matching_all and scopes['deterministic_entity_own_identifier'] == len(members) and authority_compatible
    if risks.intersection(material):
        category = 'unresolved_requires_context'
    elif strong:
        category = 'strong_record_identity_candidate'
    elif matching_all and scopes['source_local_literal_declaration'] and not unresolved_locator:
        category = 'exact_locator_candidate_only'
    else:
        category = 'unresolved_requires_context'
    return dict(blockID=block['blockID'], key=deepcopy(key), ontologyClass=key[1], occurrenceIDs=deepcopy(ids),
        memberCount=len(ids), membershipSha256=block['membershipSha256'], sourceFamilyDistribution=dict(sorted(families.items())),
        sourceFamilies=sorted(families), identifierScope=dict(sorted(scopes.items())), syntacticLocator=syntax,
        provisionalReviewCategory=category, riskFlags=sorted(risks), existingBlockFlags=deepcopy(block['existingBlockFlags']),
        members=member_views, possibleCrossBlockRelationships=[],
        identityLevels=dict(entityIdentity='unadjudicated', referenceTargetIdentity='unadjudicated_locator_evidence_only', conceptualIdentity='outside_identifier_pass'),
        sourceReference=dict(file='review-dossier.jsonl', blockID=block['blockID'], blockSha256=digest(block)), equivalencesApproved=0)


def relationships(records: list[dict]) -> None:
    """Annotate only indexed URL/identifier syntax pairs, never semantic equivalence."""
    groups = defaultdict(list)
    for r in records:
        for key in r['syntacticLocator']['relationshipKeys']:
            groups[tuple(key)].append(r)
    allowed = {
        'hydroshare': {'hydroshare_resource_id_syntax', 'hydroshare_resource_url'},
        'doi': {'doi_identifier', 'doi_resolver_url'},
        'github': {'github_repository_root', 'github_clone_url'},
    }
    for key, group in sorted(groups.items()):
        group = sorted(group, key=lambda r: r['blockID'])
        if len(group) > RELATION_CAP:
            for r in group:
                r['riskFlags'] = sorted(set(r['riskFlags']) | {'oversized_syntactic_relation_group_not_expanded'})
            continue
        for r in group:
            for other in group:
                cats = {r['syntacticLocator']['category'], other['syntacticLocator']['category']}
                if r is other or cats != allowed[key[0]]:
                    continue
                r['possibleCrossBlockRelationships'].append(dict(otherBlockID=other['blockID'],
                    kind=key[0] + '_literal_path_relationship_requires_review', syntaxKey=list(key),
                    compatibleClass=r['ontologyClass'] == other['ontologyClass'], equivalenceImplied=False))


def prepare(blocks: list[dict], spec: dict) -> dict:
    """Filter existing dossier records without discovering or expanding candidates."""
    classes = {c['name']: c['id'] for c in spec['classes']}
    require(len({b['blockID'] for b in blocks}) == len(blocks), 'DUPLICATE_BLOCK_ID')
    records = [triage(b, classes) for b in blocks if b['candidateMechanism'] == 'identifier_declaration_only']
    records.sort(key=lambda r: r['blockID']); relationships(records)
    return dict(records=records, summary=dict(inputDossierBlocks=len(blocks), identifierBlocks=len(records),
        skippedNonIdentifierBlocks=len(blocks)-len(records), categoryCounts=dict(sorted(Counter(r['provisionalReviewCategory'] for r in records).items())),
        memberOccurrences=sum(r['memberCount'] for r in records), distinctOccurrences=len({n for r in records for n in r['occurrenceIDs']}),
        distinctRecordedArtifacts=len({a for r in records for m in r['members'] for a in m['sourceArtifacts']}),
        riskCounts=dict(sorted(Counter(f for r in records for f in r['riskFlags']).items()))))


def inputs(root: Path) -> tuple[dict, dict, dict]:
    """Pin the existing manifest and verify only consumed inputs and authority links."""
    pins = {}
    def check(path: Path, expected: str) -> None:
        """Fail closed on changed or missing input bytes."""
        require(sha(path) == expected, 'INPUT_HASH_DRIFT:' + str(path)); pins[str(path)] = expected
    check(root / 'manifest.json', MANIFEST_SHA256)
    manifest = json.loads((root / 'manifest.json').read_bytes())
    require(manifest['version'] == review.VERSION and manifest['diagnosticOnly'] is True and manifest['equivalencesAsserted'] == 0, 'REVIEW_MANIFEST_CONTRACT_DRIFT')
    check(root / 'review-dossier.jsonl', manifest['outputHashes']['review-dossier.jsonl'])
    check(Path('src/evaluation/step14_semantic_review.py'), manifest['implementationSha256'])
    upstream = Path(manifest['inputRoot']) / 'manifest.json'
    check(upstream, manifest['inputHashes'][str(upstream)])
    candidate_manifest = json.loads(upstream.read_bytes())
    require(candidate_manifest['version'] == review.candidates.VERSION, 'UPSTREAM_VERSION_DRIFT')
    for name in ('occurrences.jsonl', 'candidate-blocks.jsonl'):
        require(candidate_manifest['outputHashes'][name] == manifest['inputHashes'][str(upstream.parent / name)], 'MANIFEST_CHAIN_DRIFT')
    for path in ('src/ontology/ontology_spec.yaml', 'src/ontology/ciroh_ontology.owl'):
        require(candidate_manifest['inputHashes'][path] == manifest['inputHashes'][path], 'ONTOLOGY_PIN_CHAIN_DRIFT')
        check(Path(path), manifest['inputHashes'][path])
    spec = yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())
    require(spec['ontology']['version'] == '0.1.7', 'ONTOLOGY_VERSION_DRIFT')
    return manifest, spec, pins


def run(root: Path = ROOT, output: Path = OUTPUT) -> dict:
    """Publish a fresh ignored triage preview, never overwrite existing diagnostics."""
    require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    require(output.resolve().is_relative_to(Path('var/study2_step14/identifier-scope-triage').resolve()), 'TRIAGE_OUTPUT_REQUIRED')
    manifest, spec, pins = inputs(root)
    result = prepare(list(review.json_rows(root / 'review-dossier.jsonl')), spec)
    require(result['summary']['inputDossierBlocks'] == manifest['summary']['dossierBlocks'], 'DOSSIER_COVERAGE_DRIFT')
    for path, expected in pins.items():
        require(sha(Path(path)) == expected, 'INPUT_CHANGED_DURING_TRIAGE')
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'identifier-triage.jsonl').open('xb') as handle:
        for row in result['records']:
            handle.write(encoded(row) + b'\n')
    priority = {'unresolved_requires_context': 0, 'exact_locator_candidate_only': 1, 'strong_record_identity_candidate': 2}
    with (output / 'review-queue.tsv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, delimiter='\t'); writer.writerow(['blockID', 'category', 'class', 'exactLocator', 'members', 'families', 'riskFlags', 'possibleRelationships'])
        for r in sorted(result['records'], key=lambda r: (priority[r['provisionalReviewCategory']], -len(r['riskFlags']), r['blockID'])):
            writer.writerow([r['blockID'], r['provisionalReviewCategory'], r['ontologyClass'], r['key'][3], r['memberCount'], ','.join(r['sourceFamilies']), ';'.join(r['riskFlags']), len(r['possibleCrossBlockRelationships'])])
    (output / 'report.md').write_text('# Identifier-scope triage PREVIEW\n\nNo accepted identity decisions.\n\n' + '\n'.join(f'- {k}: {json.dumps(v, sort_keys=True)}' for k, v in result['summary'].items()) + '\n\n## Limits\n\n' + '\n'.join('- ' + s for s in LIMITS) + '\n', encoding='utf-8')
    record = dict(version=VERSION, diagnosticOnly=True, equivalencesApproved=0, providerCalls=0, inputRoot=str(root), inputHashes=pins,
        implementationSha256=sha(Path(__file__)), summary=result['summary'], limitations=LIMITS,
        outputHashes={name: sha(output / name) for name in ('identifier-triage.jsonl', 'review-queue.tsv', 'report.md')})
    (output / 'manifest.json').write_bytes(encoded(record) + b'\n')
    return record


def main() -> None:
    """Run offline in the researcher terminal."""
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('OFFLINE_ONLY')), patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('OFFLINE_ONLY')):
        run(output=args.output)


if __name__ == '__main__':
    main()
