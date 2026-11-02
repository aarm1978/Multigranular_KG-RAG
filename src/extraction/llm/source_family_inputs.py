"""Read accepted local family sources and exact deterministic endpoint catalogs.

No source acquisition, eligibility review, semantic inference or provider IO.
Request grouping is deliberately separate from this source inventory adapter.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from typing import Iterator

from src.extraction.llm.calibration_preflight import MANIFEST_PATH, MANIFEST_SHA256
from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.publications.resumable_production_journal import require
from src.extraction.llm.semantic_target_profiles import get_profile


@lru_cache(maxsize=3)
def profile_for(family: str) -> dict:
    """Cache read-only profile inspection within this new inventory adapter."""
    return get_profile(family)


def snapshots(root: Path) -> tuple[dict, dict]:
    """Verify accepted source/catalog hashes without using calibration selections."""
    raw = (root / MANIFEST_PATH).read_bytes()
    require(digest(raw) == MANIFEST_SHA256, 'SOURCE_CATALOG_AUTHORITY_DRIFT')
    authority = json.loads(raw)
    data, pins = {}, {MANIFEST_PATH: MANIFEST_SHA256}
    for family in ('hydroshare', 'github', 'ciroh_hub'):
        row = next(r for r in authority['requests'] if r['artifactFamily'] == family)
        source = row['sourceSnapshot']
        directory = {'hydroshare': 'datasets', 'github': 'coderepos', 'ciroh_hub': 'documents'}[family]
        graph = next(p for p in authority['acceptedEndpointSnapshots'] if '/' + directory + '/' in p)
        for path, expected in ((source['path'], source['sha256']),
                               (graph, authority['acceptedEndpointSnapshots'][graph])):
            raw = (root / path).read_bytes()
            require(digest(raw) == expected, 'SOURCE_OR_CATALOG_DRIFT:' + path)
            pins[path] = expected
        corpus = json.loads((root / source['path']).read_bytes())
        data[family] = dict(records=corpus[source['arrayField']] if source['arrayField'] else corpus,
                            graph=json.loads((root / graph).read_bytes()), sourceSha256=source['sha256'])
    return data, pins


def catalog(graph: dict, family: str, owner: str, source_artifact: str) -> tuple[list, list]:
    """Project only source-local catalog records supported by the accepted profile."""
    profile = profile_for(family)
    endpoints = []
    for node in graph['nodes']:
        policy = profile['entities'].get(node.get('inventoryId'))
        if (node['id'] != owner and policy and node['class'] == policy['declaration']['name']
                and node.get('evidence', {}).get('sourceArtifact') == source_artifact):
            endpoints.append(dict(endpointID=node['id'], inventoryId=node['inventoryId'],
                                  **{'class': node['class']}, attributes=deepcopy(node.get('attributes', {}))))
    known = {owner, *(e['endpointID'] for e in endpoints)}
    assertions = []
    for edge in graph['edges']:
        policy = profile['relations'].get(edge.get('inventoryId'))
        if (policy and edge['relation'] == policy['declaration']['name']
                and edge['source'] in known and edge['target'] in known
                and edge.get('evidence', {}).get('sourceArtifact') == source_artifact):
            assertions.append(dict(assertionID=edge['id'], inventoryId=edge['inventoryId'],
                                   relation=edge['relation'], sourceID=edge['source'], targetID=edge['target']))
    return sorted(endpoints, key=lambda e: e['endpointID']), sorted(assertions, key=lambda e: e['assertionID'])


def github_production_exclusions(owner: str, reader: dict) -> list[dict]:
    """Exclude only the three inspected ODbL authorities under frozen §4.2.

    This prospective selection overlay leaves original reader records untouched.
    Exact content pins avoid treating a filename as a semantic classifier.
    """
    if owner not in {'github:repo:1052799392', 'github:repo:706266756', 'github:repo:1052790271'}:
        return []
    authorities = [a for a in reader['authorities'] if a['path'] == 'ODbl.md']
    if not authorities:
        return []
    require(len(authorities) == 1 and authorities[0]['rawFileSha256'] ==
            'dddcdfa70ce72d0e964160d2f16ddb22501256089dbf9c775e3eced0d031e658',
            'INSPECTED_ODBL_AUTHORITY_DRIFT:' + owner)
    return [dict(status='not_attempted_authorized_exclusion', reason='license_legal_text_step11_4_2',
                 ownerID=owner, path='ODbl.md', rawFileSha256=authorities[0]['rawFileSha256'],
                 sourceUnitIDs=[u['sourceUnitID'] for u in reader['sourceUnits'] if u['path'] == 'ODbl.md'])]


def accepted_readme_bindings(root: Path) -> dict:
    """Reuse only HS-03/04/07's frozen caller attestations, never acquisition claims."""
    raw = (root / MANIFEST_PATH).read_bytes()
    require(digest(raw) == MANIFEST_SHA256, 'README_BINDING_MANIFEST_DRIFT')
    bindings = {}
    for request_id in ('HS-03', 'HS-04', 'HS-07'):
        rows = [r for r in json.loads(raw)['requests'] if r['requestID'] == request_id]
        require(len(rows) == 1, 'README_BINDING_MISSING_OR_AMBIGUOUS')
        row = rows[0]
        units = [u for u in row['orderedUnits'] if u['sourceField'] == 'README']
        require(row['artifactFamily'] == 'hydroshare' and len(units) == 1,
                'README_BINDING_INVALID')
        unit = units[0]
        require(unit['resource_id'] == row['owner']['resource_id'] and
                unit['snapshotID'] == 'sha256:' + row['sourceSnapshot']['sha256'] and
                unit['sourceVerification'] == 'caller_attested' and
                unit['acquisitionIntegrityStatus'] == 'not_independently_verified',
                'README_BINDING_PROVENANCE_DRIFT')
        key = (unit['resource_id'], unit['source_path'])
        require(key not in bindings, 'README_BINDING_DUPLICATE')
        bindings[key] = dict(requestID=request_id, manifestPath=MANIFEST_PATH,
            manifestSha256=MANIFEST_SHA256, originalSourceUnitID=unit['sourceUnitID'],
            snapshotID=unit['snapshotID'], sourceVersion=unit['sourceVersion'],
            authorityTextSha256=unit['authorityTextSha256'],
            sourceVerification=unit['sourceVerification'],
            acquisitionIntegrityStatus=unit['acquisitionIntegrityStatus'])
    return bindings


def production_readme(readme: dict, owner: str, provenance: dict, bindings: dict) -> dict:
    """Fail closed on absent or mismatched prior attestation; retain source diagnostics.

    The historical full-authority hash checks the original binding, not independent
    acquisition integrity. Original reader provenance remains caller_attested.
    No calibration selections or historical model outputs are reused.
    """
    from src.extraction.llm.datasets.source_units import read_readme_source_units
    path, text = readme.get('source_file'), readme.get('readme_text_raw')
    binding = bindings.get((owner, path))
    text_hash = digest(text.encode('utf-8')) if isinstance(text, str) else None
    verified = (binding is not None and text_hash == binding['authorityTextSha256']
                and provenance['snapshotID'] == binding['snapshotID']
                and provenance.get('sourceVersion') == binding['sourceVersion'])
    result = read_readme_source_units(dict(resource_id=owner, source_path=path, text=text),
        accepted_owner_id=owner, provenance={**provenance, 'sourceVerified': verified})
    decision = dict(resource_id=owner, source_path=path, snapshotID=provenance['snapshotID'],
                    authorityTextSha256=text_hash, acceptedBinding=deepcopy(binding))
    if not verified:
        # Enrich prospective diagnostics only; never edit historical reader artifacts.
        for diagnostic in result['diagnostics']:
            diagnostic.update(decision, status='failed_source_or_evidence_binding',
                authorityDecision='frozen_readme_binding_mismatch' if binding else 'no_accepted_readme_binding')
    else:
        result['productionAuthority'] = dict(decision, status='source_authority_reused')
    return result


def owners(root: Path, data: dict) -> Iterator[dict]:
    """Yield original reader outputs and source failures, with no request selection."""
    from src.extraction.llm.datasets.source_units import build_abstract_source_unit
    from src.extraction.llm.coderepos.source_units import read_repository_sources
    from src.extraction.llm.documents.source_units import read_page_source_units
    bindings = accepted_readme_bindings(root) if 'hydroshare' in data else {}
    for family, loaded in data.items():
        graph = loaded['graph']
        nodes = {n['id']: n for n in graph['nodes']}
        require(len(nodes) == len(graph['nodes']), 'DUPLICATE_CATALOG_NODE')
        for source in loaded['records']:
            diagnostics = []
            exclusions = []
            raw_pins = {}
            if family == 'hydroshare':
                owner, cls = source['resource_id'], 'DatasetResource'
                artifact = 'hydroshare:' + owner
                provenance = dict(snapshotID='sha256:' + loaded['sourceSha256'],
                                  sourceVersion=source.get('system_metadata', {}).get('date_last_updated'))
                abstract = build_abstract_source_unit(source, accepted_owner_id=owner, provenance=provenance)
                readmes = [production_readme(r, owner, provenance, bindings)
                    for r in source.get('documentation', {}).get('readme_files', [])]
                units = [abstract['unit'].to_record()] if abstract['unit'] is not None else []
                for reader in readmes:
                    units.extend(reader['sourceUnits'])
                    diagnostics.extend(reader['diagnostics'])
                    if reader.get('productionAuthority'):
                        diagnostics.append(reader['productionAuthority'])
                if abstract.get('diagnostic'):
                    diagnostics.append({**abstract['diagnostic'], 'status': abstract['status']})
                complete = abstract['inputComplete'] and all(r['inputComplete'] for r in readmes)
                inputs = dict(accepted_owner_id=owner, trusted_provenance=provenance,
                              abstract_results=[abstract], readme_results=readmes, authorized_stubs=[])
            elif family == 'github':
                owner, cls = 'github:repo:' + str(source['repo_id']), 'Repository'
                artifact = source['html_url'].rstrip('/') + '/tree/' + source['archive']['frozen_commit_sha']
                reader = read_repository_sources(source, root / 'data/raw/coderepos')
                for authority in reader['authorities']:
                    if authority.get('rawFileSha256'):
                        path = str(Path('data/raw/coderepos') / source['name'] / 'contents' / authority['path'])
                        raw_pins[path] = authority['rawFileSha256']
                units, diagnostics, complete = reader['sourceUnits'], reader['diagnostics'], reader['inputComplete']
                exclusions = github_production_exclusions(owner, reader)
                diagnostics = [*diagnostics, *exclusions]
                inputs = dict(reader_result=reader, accepted_repository=dict(canonicalArtifactID=owner,
                    repo_id=source['repo_id'], full_name=source['full_name'],
                    frozenCommitSha=source['archive']['frozen_commit_sha']))
            else:
                artifact = source['canonical_url']
                owner, cls = 'hub:page:' + digest(artifact.encode())[:20], 'DocumentationPage'
                sections = [dict(heading_ordinal=n['attributes']['ordinal'],
                    source_line=n['attributes']['sourceLine'], raw_text=n['attributes']['rawText'], section_id=n['id'])
                    for n in graph['nodes'] if n['class'] == 'Section'
                    and n.get('attributes', {}).get('pageUrl') == artifact]
                mapping = dict(page_key=source['page_key'], canonical_url=artifact,
                               content_sha256=source['content_sha256'],
                               sections=sorted(sections, key=lambda s: s['heading_ordinal']))
                reader = read_page_source_units(source, accepted_section_mapping=mapping)
                units, diagnostics = reader['sourceUnits'], reader['diagnostics']
                complete = reader['status'] == 'source_read_success' and not diagnostics
                inputs = dict(page=source, reader_result=reader, accepted_page_id=owner,
                              accepted_section_mapping=mapping)
            require(owner in nodes and nodes[owner]['class'] == cls, 'OWNER_CATALOG_MISMATCH:' + owner)
            endpoints, assertions = catalog(graph, family, owner, artifact)
            inputs.update(request_version=family + '-request/1.2.0', input_complete=complete,
                          accepted_endpoints=endpoints, accepted_assertions=assertions)
            yield dict(family=family, ownerID=owner, sourceRecordSha256=digest(canonical(source)),
                       endpointRecordSha256=digest(canonical(nodes[owner])), units=units,
                       excludedSourceUnitIDs=[uid for d in exclusions for uid in d['sourceUnitIDs']],
                       diagnostics=diagnostics, inputComplete=complete, inputs=inputs, rawSourcePins=raw_pins)
