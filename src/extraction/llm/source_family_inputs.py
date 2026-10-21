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
    data, pins = {}, {}
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


def owners(root: Path, data: dict) -> Iterator[dict]:
    """Yield original reader outputs and source failures, with no request selection."""
    from src.extraction.llm.datasets.source_units import build_abstract_source_unit, read_readme_source_units
    from src.extraction.llm.coderepos.source_units import read_repository_sources
    from src.extraction.llm.documents.source_units import read_page_source_units
    for family, loaded in data.items():
        graph = loaded['graph']
        nodes = {n['id']: n for n in graph['nodes']}
        require(len(nodes) == len(graph['nodes']), 'DUPLICATE_CATALOG_NODE')
        for source in loaded['records']:
            diagnostics = []
            raw_pins = {}
            if family == 'hydroshare':
                owner, cls = source['resource_id'], 'DatasetResource'
                artifact = 'hydroshare:' + owner
                provenance = dict(snapshotID='sha256:' + loaded['sourceSha256'],
                                  sourceVersion=source.get('system_metadata', {}).get('date_last_updated'))
                abstract = build_abstract_source_unit(source, accepted_owner_id=owner, provenance=provenance)
                readmes = [read_readme_source_units(dict(resource_id=owner,
                    source_path=r.get('source_file'), text=r.get('readme_text_raw')),
                    accepted_owner_id=owner, provenance={**provenance, 'sourceVerified': True})
                    for r in source.get('documentation', {}).get('readme_files', [])]
                units = [abstract['unit'].to_record()] if abstract['unit'] is not None else []
                for reader in readmes:
                    units.extend(reader['sourceUnits'])
                    diagnostics.extend(reader['diagnostics'])
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
                       diagnostics=diagnostics, inputComplete=complete, inputs=inputs, rawSourcePins=raw_pins)
