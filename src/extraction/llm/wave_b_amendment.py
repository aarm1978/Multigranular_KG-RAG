"""Explicit offline Wave B execution amendment; no authorization or transport."""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess

from src.extraction.llm import calibration_preflight as base
from src.extraction.llm.pilot_preflight import build_preflight, canonical, digest

VERSION = 'study2-step12c-wave-b-execution/1.0.0'
BASE_CHECKPOINT = 'c0515eb91f7d804bfe255d984ccbf89b60a35ebc'
REQUEST_IDS = tuple(f'{family}-{n:02d}' for family in ('HS', 'GH', 'HUB') for n in (5, 6, 7))
VERSIONS = {'hydroshare': 'hydroshare-request/1.2.0', 'github': 'github-request/1.1.0',
            'ciroh_hub': 'ciroh_hub-request/1.1.0'}
DIRECTORIES = {'hydroshare': 'datasets', 'github': 'coderepos', 'ciroh_hub': 'documents'}
PROJECTION = 'github-provider-input/1.1.0'
PREFLIGHT_DIRECTORY = 'var/study2_step12c/wave-b-preflight/1.0.0'
ASSOCIATION_FIELDS = ('semanticRequestSha256', 'providerInputSha256', 'providerEnvelopeSha256',
                      'schemaSha256', 'requestVersion', 'promptIdentifier',
                      'providerInputProjectionVersion', 'inputByteCount', 'wireByteCount',
                      'unprojectedInputByteCount', 'conservativeInputTokenAllowance')
# Pin the execution and replay boundary as well as the original six reader/contract files.
RUNTIME_FILES = tuple('src/extraction/llm/' + name for name in (
    'wave_b_amendment.py', 'calibration_preflight.py', 'pilot_preflight.py', 'pilot_terminal.py',
    'pilot_wave.py', 'semantic_target_profiles.py', 'coderepos/provider_input.py',
    'coderepos/purpose_validation.py', 'documents/example_context_binding.py',
    'publications/openai_provider.py', 'publications/deterministic_evidence_binding.py'))
RUNTIME_FILES += tuple(f'src/extraction/llm/{family}/{name}.py'
    for family in ('datasets', 'coderepos', 'documents')
    for name in ('source_units', 'request_contract', 'candidate_validation', 'offline_pipeline'))
RUNTIME_FILES += tuple(f'src/extraction/llm/{family}/evidence_binding.py' for family in ('coderepos', 'documents'))


def _old_bytes(root: Path, path: str) -> bytes | None:
    """Read committed baseline bytes, never the index or unrelated working changes."""
    result = subprocess.run(['git', 'show', f'{BASE_CHECKPOINT}:{path}'], cwd=root,
                            capture_output=True, check=False)
    if result.returncode:
        if path == 'src/extraction/llm/wave_b_amendment.py':
            return None
        raise ValueError('baseline_implementation_missing:' + path)
    return result.stdout


def implementation_record(root: Path, manifest: dict) -> dict:
    """Explicitly record and verify historical pins before prospective compatibility."""
    old, new = {}, {}
    for path in sorted(set(RUNTIME_FILES) | set(manifest['implementationFiles'])):
        raw = _old_bytes(root, path)
        old[path] = digest(raw) if raw is not None else None
        new[path] = digest((root / path).read_bytes())
    for path, expected in manifest['implementationFiles'].items():
        if old[path] != expected:
            raise ValueError('historical_implementation_fingerprint_invalid:' + path)
    return {'baselineCheckpoint': BASE_CHECKPOINT, 'old': old, 'new': new,
            'changedFiles': [p for p in old if old[p] != new[p]]}


def legacy_request(root: Path, manifest: dict, request_id: str) -> tuple[dict, dict]:
    """Compatibility path only after explicit amendment implementation verification.

    The unamended base.rebuild_request still requires the original file hashes.
    This route independently reconstructs and verifies the exact original request.
    """
    row = next(r for r in manifest['requests'] if r['requestID'] == request_id)
    source = base.verified_source(root, manifest, row)
    inputs = base.construct_request(root, row, source, inputs_only=True)
    contract = importlib.import_module(f'src.extraction.llm.{DIRECTORIES[row["artifactFamily"]]}.request_contract')
    request = contract.build_request(**inputs)
    base.verify_request(request, row)
    return request, inputs


def prospective_case(root: Path, manifest: dict, request_id: str) -> tuple[dict, dict]:
    """Rebuild original selection, then change only approved instruction/version fields."""
    if request_id not in REQUEST_IDS:
        raise ValueError('amendment_wave_b_only')
    legacy, inputs = legacy_request(root, manifest, request_id)
    family = legacy['request']['artifactFamily']
    contract = importlib.import_module(f'src.extraction.llm.{DIRECTORIES[family]}.request_contract')
    inputs['request_version'] = VERSIONS[family]
    request = contract.build_request(**inputs)
    if request.get('status') != 'request_ready':
        raise ValueError('prospective_request_not_ready')
    unchanged = lambda body: {k: v for k, v in body.items() if k not in ('schemaVersion', 'promptIdentifier', 'instructions')}
    if unchanged(request['request']) != unchanged(legacy['request']):
        raise ValueError('amendment_source_or_contract_drift')
    projection = PROJECTION if family == 'github' else None
    result = build_preflight(request, output_ceiling=32768, projection_version=projection)
    previous = build_preflight(legacy, output_ceiling=32768, projection_version=base.projection_for(request_id))
    if result['schemaSha256'] != previous['schemaSha256']:
        raise ValueError('response_schema_drift')
    result.update(calibrationManifestSha256=base.MANIFEST_SHA256, calibrationRequestID=request_id,
        calibrationWave='B', requestVersion=VERSIONS[family], promptIdentifier=contract.WAVE_B_PROMPT_IDENTIFIER,
        providerInputProjectionVersion=projection, unprojectedInputByteCount=len(canonical(request['request'])),
        conservativeInputTokenAllowance=result['inputByteCount'] + result['schemaByteCount'],
        allowanceMethod='one token per UTF-8 input/schema byte; not measured; additional approved overhead required',
        executionHold='wave_a_clearance_amendment_context_budget_approval_pending')
    return request, result


def verify_legacy_associations(root: Path, manifest: dict, *, replay: bool = False) -> list[dict]:
    """Verify all twelve Wave A hashes; optional read-only replay never overwrites reports."""
    rows = []
    for family in ('HS', 'GH', 'HUB'):
        for n in range(1, 5):
            rid = f'{family}-{n:02d}'
            request, inputs = legacy_request(root, manifest, rid)
            previous = root / base.PREFLIGHT_DIRECTORY / rid
            if json.loads((previous / 'request-result.json').read_bytes()) != request:
                raise ValueError('legacy_request_bytes_changed')
            result = build_preflight(request, output_ceiling=32768, projection_version=base.projection_for(rid))
            for name, key in [('semantic-request.json', 'semanticRequestBytes'), ('provider-input.txt', 'inputBytes'),
                              ('provider-envelope.json', 'wireBytes')]:
                if (previous / name).read_bytes() != result[key]:
                    raise ValueError('legacy_preflight_bytes_changed')
            folder = root / 'var/study2_step12c/analysis/wave-A/replays' / rid
            report_raw = (folder / 'replay-report.json').read_bytes()
            report = json.loads(report_raw)
            output = (root / 'var/study2_step12c/terminal' / rid / 'model-output.utf8').read_bytes()
            if (report['requestSha256'] != request['requestSha256'] or report['requestResult'] != request
                    or report['responseSha256'] != digest(output)
                    or (folder / 'replay-report.sha256').read_text().split()[0] != digest(report_raw)):
                raise ValueError('legacy_replay_association_mismatch')
            if replay:
                pipeline = importlib.import_module(f'src.extraction.llm.{DIRECTORIES[request["request"]["artifactFamily"]]}.offline_pipeline')
                actual = pipeline.replay_recorded_response(output, request_inputs=inputs,
                    expected_request_sha256=request['requestSha256'])
                if actual.report_json.encode() != report_raw:
                    raise ValueError('legacy_replay_bytes_changed:' + rid)
            rows.append({'requestID': rid, 'semanticRequestSha256': request['requestSha256'],
                'providerInputSha256': result['providerInputSha256'],
                'providerEnvelopeSha256': result['providerEnvelopeSha256'],
                'modelOutputSha256': digest(output), 'replaySha256': digest(report_raw)})
    return rows


def prepare(root: Path) -> dict:
    """Generate a reviewable immutable execution record; never create live approval."""
    manifest = base.load_manifest(root)
    fingerprints = implementation_record(root, manifest)
    legacy = verify_legacy_associations(root, manifest, replay=True)
    rows = []
    for rid in REQUEST_IDS:
        original = next(r for r in manifest['requests'] if r['requestID'] == rid)
        request, result = prospective_case(root, manifest, rid)
        old_folder = root / base.PREFLIGHT_DIRECTORY / rid
        rows.append({'requestID': rid, 'baseSelectionRecordSha256': digest(base.semantic_bytes(original)),
            'originalSemanticRequestSha256': original['semanticRequestSha256'],
            'originalPreflightFileSha256': {p.name: digest(p.read_bytes()) for p in sorted(old_folder.iterdir()) if p.is_file()},
            'instructionsSha256': digest(base.semantic_bytes(request['request']['instructions'])),
            **{k: result[k] for k in ASSOCIATION_FIELDS}})
    return {'schemaVersion': VERSION, 'status': 'OFFLINE PREPARED / NOT AUTHORIZED FOR LIVE EXECUTION',
        'authorized': False, 'wave': 'B', 'baseManifestPath': base.MANIFEST_PATH,
        'baseManifestSha256': base.MANIFEST_SHA256, 'implementation': fingerprints,
        'authorityFiles': manifest['authorityFiles'], 'legacyWaveAAssociations': legacy, 'requests': rows,
        'remainingApproval': ['Wave A researcher clearance', 'exact amendment digest', 'individual request hashes',
            'individual and aggregate monetary reservations', 'context allowances and overhead', 'approval validity window'],
        'semanticAcceptance': 'not_evaluated', 'kgAuthorization': False}


def load_amendment(root: Path, path: Path, expected_sha256: str) -> tuple[dict, dict]:
    """Require exact externally selected amendment bytes and all implementation pins."""
    raw = path.read_bytes()
    if not expected_sha256 or digest(raw) != expected_sha256:
        raise ValueError('amendment_digest_mismatch')
    amendment = json.loads(raw)
    manifest = base.load_manifest(root)
    if (amendment.get('schemaVersion') != VERSION or amendment.get('wave') != 'B'
            or amendment.get('authorized') is not False
            or amendment.get('baseManifestSha256') != base.MANIFEST_SHA256
            or amendment.get('baseManifestPath') != base.MANIFEST_PATH
            or amendment.get('authorityFiles') != manifest['authorityFiles']
            or [r.get('requestID') for r in amendment.get('requests', [])] != list(REQUEST_IDS)):
        raise ValueError('amendment_manifest_or_scope_mismatch')
    if amendment.get('implementation') != implementation_record(root, manifest):
        raise ValueError('amendment_implementation_fingerprint_mismatch')
    for row in amendment['requests']:
        original = next(r for r in manifest['requests'] if r['requestID'] == row['requestID'])
        if (row['baseSelectionRecordSha256'] != digest(base.semantic_bytes(original))
                or row['originalSemanticRequestSha256'] != original['semanticRequestSha256']
                or row['requestVersion'] != VERSIONS[original['artifactFamily']]):
            raise ValueError('amendment_selection_or_version_mismatch')
    return manifest, amendment


def build_case(root: Path, request_id: str, path: Path, expected_sha256: str) -> tuple[dict, dict]:
    """Verify amendment association and reconstruct every transmitted byte for one ID."""
    manifest, amendment = load_amendment(root, path, expected_sha256)
    request, result = prospective_case(root, manifest, request_id)
    row = next(r for r in amendment['requests'] if r['requestID'] == request_id)
    if any(result[k] != row[k] for k in ASSOCIATION_FIELDS) or row['instructionsSha256'] != digest(base.semantic_bytes(request['request']['instructions'])):
        raise ValueError('amendment_request_or_envelope_mismatch')
    for name, expected in row['originalPreflightFileSha256'].items():
        base._verified_bytes(root, f'{base.PREFLIGHT_DIRECTORY}/{request_id}/{name}', expected)
    result.update(executionAmendmentSha256=expected_sha256, executionAmendmentVersion=VERSION)
    return request, result


def case_folder(root: Path, request_id: str, amendment_sha256: str) -> Path:
    """Artifacts are separate from historical files; attempts remain at original ID paths."""
    return root / PREFLIGHT_DIRECTORY / amendment_sha256 / request_id


def write_case(root: Path, request_id: str, path: Path, expected_sha256: str) -> dict:
    """Exclusively create or byte-verify preflight artifacts; never refresh in place."""
    from src.extraction.llm.pilot_terminal import save
    request, result = build_case(root, request_id, path, expected_sha256)
    folder = case_folder(root, request_id, expected_sha256)
    artifacts = base.artifact_bytes(request, result)
    artifacts['execution-amendment.json'] = path.read_bytes()
    if folder.exists():
        if any((folder / name).read_bytes() != raw for name, raw in artifacts.items()):
            raise ValueError('stored_amendment_preflight_drift')
    else:
        folder.mkdir(parents=True, exist_ok=False)
        for name, raw in artifacts.items():
            save(folder / name, raw)
    return result


def load_case(root: Path, request_id: str, path: Path, expected_sha256: str) -> dict:
    """Dry-run/terminal verification requires pre-existing exact immutable artifacts."""
    request, result = build_case(root, request_id, path, expected_sha256)
    artifacts = base.artifact_bytes(request, result)
    artifacts['execution-amendment.json'] = path.read_bytes()
    for name, raw in artifacts.items():
        if (case_folder(root, request_id, expected_sha256) / name).read_bytes() != raw:
            raise ValueError('stored_amendment_preflight_drift')
    return result


def main() -> None:
    """Prepare a new unapproved record, or verify/write nine offline envelopes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'preflight', 'verify-legacy'))
    parser.add_argument('--amendment', type=Path, required=True)
    parser.add_argument('--amendment-sha256')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.mode == 'prepare':
        from src.extraction.llm.pilot_terminal import save
        raw = json.dumps(prepare(root), indent=2, ensure_ascii=True).encode() + b'\n'
        save(args.amendment, raw)
        print(digest(raw))
        return
    if not args.amendment_sha256:
        parser.error('explicit --amendment-sha256 required')
    if args.mode == 'verify-legacy':
        manifest, amendment = load_amendment(root, args.amendment, args.amendment_sha256)
        if verify_legacy_associations(root, manifest, replay=True) != amendment['legacyWaveAAssociations']:
            raise ValueError('legacy_association_drift')
        print('12 legacy requests, envelopes and replay hashes match; no historical writes')
        return
    for rid in REQUEST_IDS:
        result = write_case(root, rid, args.amendment, args.amendment_sha256)
        print(json.dumps({'requestID': rid, **{k: result[k] for k in ASSOCIATION_FIELDS}}, sort_keys=True))


if __name__ == '__main__':
    main()
