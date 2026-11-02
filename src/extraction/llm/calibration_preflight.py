"""Pinned Step 12C sample preflight; offline only, never dispatches or loads keys."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.extraction.llm.pilot_preflight import build_preflight, canonical, digest
from src.extraction.llm.coderepos.provider_input import PROJECTION_VERSION

MANIFEST_PATH = 'docs/study2_step12c_calibration_selection_manifest_candidate_v0.2.json'
MANIFEST_SHA256 = '2efbcfc9280888228d06a669c6b26cefe1191d223c61cd1b036ee96215ef49fb'
PREFLIGHT_DIRECTORY = 'var/study2_step12c/calibration-preflight/1.0.0'
REQUEST_IDS = tuple(f'{family}-{i:02d}' for family in ('HS', 'GH', 'HUB') for i in range(1, 11))
ORIGINAL_IDS = ('HS-01', 'GH-01', 'HUB-01')


def semantic_bytes(value: dict) -> bytes:
    """Match the accepted semantic record hashing, separately from wire encoding."""
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def wave_for(request_id: str) -> str:
    """Resolve only a frozen ID, without accepting arbitrary paths or aliases."""
    if request_id not in REQUEST_IDS:
        raise ValueError('unknown_calibration_request')
    number = int(request_id.split('-')[1])
    return 'A' if number <= 4 else 'B' if number <= 7 else 'C'


def projection_for(request_id: str) -> str | None:
    """Original GH-01 stays legacy; all other GitHub IDs explicitly opt in."""
    wave_for(request_id)
    return PROJECTION_VERSION if request_id.startswith('GH-') and request_id != 'GH-01' else None


def _verified_bytes(root: Path, path: str, expected: str) -> bytes:
    """Check exact pinned file bytes; no recovery, downloads or substitution."""
    file = (root / path).resolve()
    if not file.is_relative_to(root.resolve()):
        raise ValueError('unsafe_manifest_path')
    raw = file.read_bytes()
    if digest(raw) != expected:
        raise ValueError('snapshot_drift:' + path)
    return raw


def load_manifest(root: Path) -> dict:
    """Load the exact committed selection freeze and validate routing invariants."""
    manifest = json.loads(_verified_bytes(root, MANIFEST_PATH, MANIFEST_SHA256))
    rows = manifest.get('requests', [])
    if (manifest.get('schemaVersion') != 'study2-step12c-calibration-selection/0.2'
            or [r.get('requestID') for r in rows] != list(REQUEST_IDS)):
        raise ValueError('manifest_request_inventory_mismatch')
    for row in rows:
        rid = row['requestID']
        family, cls, version = ('hydroshare', 'DatasetResource', 'hydroshare-request/1.0.0' if rid == 'HS-01' else 'hydroshare-request/1.1.0') if rid.startswith('HS-') else (
            ('github', 'Repository', 'github-request/1.0.0') if rid.startswith('GH-') else
            ('ciroh_hub', 'DocumentationPage', 'ciroh_hub-request/1.0.0'))
        if (row['artifactFamily'] != family or row['wave'] != wave_for(rid)
                or row['requestVersion'] != version or row['acceptedEndpoint']['class'] != cls
                or row['acceptedEndpoint']['id'] != row['owner']['endpointID']
                or row['selectedSourceUnitIDs'] != [u['sourceUnitID'] for u in row['orderedUnits']]
                or len(set(row['selectedSourceUnitIDs'])) != len(row['orderedUnits'])
                or not row['orderedUnits']):
            raise ValueError('manifest_route_or_selection_mismatch')
    for family in ('hydroshare', 'github', 'ciroh_hub'):
        if len({r['acceptedEndpoint']['id'] for r in rows if r['artifactFamily'] == family}) != 10:
            raise ValueError('manifest_owner_not_distinct')
    return manifest


def construct_request(root: Path, row: dict, source: dict, *, inputs_only: bool = False) -> dict:
    """Use unchanged family builders, explicit versions and frozen inventories."""
    inventories = row['endpointInventories']
    shared = dict(selected_unit_ids=row['selectedSourceUnitIDs'],
                  input_complete=row['inputCompleteness']['callerInputComplete'],
                  accepted_endpoints=inventories['acceptedEndpoints'],
                  accepted_assertions=inventories['acceptedAssertions'])
    if row['artifactFamily'] == 'hydroshare':
        from src.extraction.llm.datasets import request_contract as contract
        from src.extraction.llm.datasets.source_units import build_abstract_source_unit, read_readme_source_units
        owner = row['acceptedEndpoint']['id']
        provenance = {'snapshotID': row['owner']['snapshotID'], 'sourceVersion': row['owner']['sourceVersion']}
        abstract = build_abstract_source_unit(source, accepted_owner_id=owner, provenance=provenance)
        readmes = []
        for item in source['documentation']['readme_files']:
            sections = [{k: s[k] for k in ('startOffsetInAuthority', 'endOffsetInAuthority')}
                        for s in row.get('readmeSections', []) if s['source_path'] == item['source_file']]
            readmes.append(read_readme_source_units(
                {'resource_id': owner, 'source_path': item['source_file'], 'text': item['readme_text_raw']},
                accepted_owner_id=owner, provenance={**provenance, 'sourceVerified': True}, sections=sections))
        if not readmes:
            readmes = [read_readme_source_units(None, accepted_owner_id=owner, provenance=provenance)]
        inputs = dict(accepted_owner_id=owner, trusted_provenance=provenance,
            abstract_results=[abstract], readme_results=readmes, request_version=row['requestVersion'],
            authorized_stubs=inventories['authorizedStubs'], **shared)
        return inputs if inputs_only else contract.build_request(**inputs)
    if row['artifactFamily'] == 'github':
        from src.extraction.llm.coderepos import request_contract as contract
        from src.extraction.llm.coderepos.source_units import read_repository_sources
        reader = read_repository_sources(source, root / 'data/raw/coderepos')
        owner = {'canonicalArtifactID': f"github:repo:{source['repo_id']}", 'repo_id': source['repo_id'],
                 'full_name': source['full_name'], 'frozenCommitSha': source['archive']['frozen_commit_sha']}
        inputs = dict(reader_result=reader, accepted_repository=owner, request_version=row['requestVersion'], **shared)
        return inputs if inputs_only else contract.build_request(**inputs)
    if row['artifactFamily'] == 'ciroh_hub':
        from src.extraction.llm.documents import request_contract as contract
        from src.extraction.llm.documents.source_units import read_page_source_units
        mapping = row['acceptedSectionMapping']
        inputs = dict(page=source, reader_result=read_page_source_units(source, accepted_section_mapping=mapping),
            accepted_page_id=row['acceptedEndpoint']['id'], accepted_section_mapping=mapping, request_version=row['requestVersion'], **shared)
        return inputs if inputs_only else contract.build_request(**inputs)
    raise ValueError('unsupported_manifest_family')


def verify_request(request: dict, row: dict) -> None:
    """Verify full request hash and each ordered selected text/metadata record."""
    if request.get('status') != 'request_ready':
        raise ValueError('selected_source_request_failed')
    body = request['request']
    if (digest(semantic_bytes(body)) != row['semanticRequestSha256']
            or request['requestSha256'] != row['semanticRequestSha256']
            or body['schemaVersion'] != row['requestVersion'] or body['owner'] != row['owner']
            or body['selectedSourceUnitIDs'] != row['selectedSourceUnitIDs']
            or len(body['sourceUnits']) != len(row['orderedUnits'])):
        raise ValueError('semantic_request_or_identity_drift')
    for order, (unit, expected) in enumerate(zip(body['sourceUnits'], row['orderedUnits']), 1):
        for key, value in expected.items():
            if key not in {'selectionOrder', 'selectedTextCharacters', 'selectedTextUtf8Bytes', 'selectedTextSha256'} and unit.get(key) != value:
                raise ValueError('selected_unit_metadata_drift')
        if (expected['selectionOrder'] != order or len(unit['text']) != expected['selectedTextCharacters']
                or len(unit['text'].encode()) != expected['selectedTextUtf8Bytes']
                or digest(unit['text'].encode()) != expected['selectedTextSha256']):
            raise ValueError('selected_text_drift')


def verified_source(root: Path, manifest: dict, row: dict) -> dict:
    """Verify source/authority/endpoint bytes independently of implementation approval."""
    for path, expected in manifest['authorityFiles'].items():
        _verified_bytes(root, path, expected)
    snapshot = row['sourceSnapshot']
    data = json.loads(_verified_bytes(root, snapshot['path'], snapshot['sha256']))
    records = data[snapshot['arrayField']] if snapshot['arrayField'] else data
    source = records[snapshot['arrayIndex']]
    if digest(semantic_bytes(source)) != snapshot['ownerRecordSha256']:
        raise ValueError('owner_snapshot_drift')
    family_directory = {'hydroshare': 'datasets', 'github': 'coderepos', 'ciroh_hub': 'documents'}[row['artifactFamily']]
    graph_path = next(p for p in manifest['acceptedEndpointSnapshots'] if f'/{family_directory}/' in p)
    nodes = json.loads(_verified_bytes(root, graph_path, manifest['acceptedEndpointSnapshots'][graph_path]))['nodes']
    endpoint = row['acceptedEndpoint']
    matches = [n for n in nodes if n.get('id') == endpoint['id']]
    if (len(matches) != 1 or matches[0].get('class') != endpoint['class']
            or digest(semantic_bytes(matches[0])) != endpoint['nodeRecordSha256']):
        raise ValueError('accepted_endpoint_drift')
    return source


def rebuild_request(root: Path, manifest: dict, request_id: str) -> dict:
    """Inspect only one frozen owner and its accepted endpoint; fail on drift."""
    wave_for(request_id)
    row = next(r for r in manifest['requests'] if r['requestID'] == request_id)
    for path, expected in {**manifest['authorityFiles'], **manifest['implementationFiles']}.items():
        _verified_bytes(root, path, expected)
    source = verified_source(root, manifest, row)
    request = construct_request(root, row, source)
    verify_request(request, row)
    if request_id in ORIGINAL_IDS:
        for path, expected in row['preservedArtifacts'].items():
            _verified_bytes(root, path, expected)
        original = json.loads((root / 'var/study2_step12c/preflight' / request_id / 'request-result.json').read_bytes())
        if original != request:
            raise ValueError('historical_request_drift')
    return request


def build_case(root: Path, manifest: dict, request_id: str) -> tuple[dict, dict]:
    """Construct fixed-config preflight with explicit transport projection routing."""
    request = rebuild_request(root, manifest, request_id)
    result = build_preflight(request, output_ceiling=32768, projection_version=projection_for(request_id))
    if request_id in ORIGINAL_IDS:
        old = root / 'var/study2_step12c/preflight' / request_id
        if result['wireBytes'] != (old / 'provider-envelope.json').read_bytes():
            raise ValueError('historical_envelope_drift')
    result.update(calibrationManifestSha256=MANIFEST_SHA256, calibrationRequestID=request_id,
                  calibrationWave=wave_for(request_id), requestVersion=request['request']['schemaVersion'],
                  promptIdentifier=request['request'].get('promptIdentifier'),
                  providerInputProjectionVersion=projection_for(request_id),
                  unprojectedInputByteCount=len(canonical(request['request'])),
                  conservativeInputTokenAllowance=result['inputByteCount'] + result['schemaByteCount'],
                  allowanceMethod='one token per UTF-8 input/schema byte; not measured; additional approved overhead required',
                  executionHold='historical_already_executed' if request_id == 'HS-01' else 'wave_request_context_budget_approval_pending')
    return request, result


def artifact_bytes(request: dict, result: dict) -> dict[str, bytes]:
    """Define durable exact full/request/projected associations, without credentials."""
    meta = {k: v for k, v in result.items() if k not in ('semanticRequestBytes', 'inputBytes', 'wireBytes', 'envelope')}
    return {'request-result.json': canonical(request), 'semantic-request.json': result['semanticRequestBytes'],
            'provider-input.txt': result['inputBytes'], 'provider-envelope.json': result['wireBytes'],
            'preflight.json': canonical(meta)}


def write_case(root: Path, manifest: dict, request_id: str) -> dict:
    """Create separate artifacts exclusively; repeat preparation only verifies bytes."""
    request, result = build_case(root, manifest, request_id)
    expected = artifact_bytes(request, result)
    folder = root / PREFLIGHT_DIRECTORY / request_id
    if folder.exists():
        if any((folder / name).read_bytes() != raw for name, raw in expected.items()):
            raise ValueError('existing_calibration_preflight_drift')
    else:
        from src.extraction.llm.pilot_terminal import save
        folder.mkdir(parents=True, exist_ok=False)
        for name, raw in expected.items():
            save(folder / name, raw)
    return result


def load_case(root: Path, request_id: str) -> dict:
    """Dry-run/execute verification rechecks original sources and stored exact bytes."""
    manifest = load_manifest(root)
    request, result = build_case(root, manifest, request_id)
    folder = root / PREFLIGHT_DIRECTORY / request_id
    for name, raw in artifact_bytes(request, result).items():
        if (folder / name).read_bytes() != raw:
            raise ValueError('stored_calibration_preflight_drift')
    return result


def main() -> None:
    """Prepare offline envelopes only; --all never dispatches any request."""
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--request-id', choices=REQUEST_IDS)
    choice.add_argument('--all', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    manifest = load_manifest(root)
    for rid in REQUEST_IDS if args.all else (args.request_id,):
        result = write_case(root, manifest, rid)
        print(json.dumps({k: result[k] for k in ('calibrationRequestID', 'inputByteCount', 'wireByteCount',
            'unprojectedInputByteCount', 'conservativeInputTokenAllowance', 'executionHold')}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
