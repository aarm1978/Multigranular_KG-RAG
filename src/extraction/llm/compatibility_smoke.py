"""Three fixed Step 13 compatibility attempts; explicit approval, no retries.

Import and dry-run never load credentials or dispatch. The permanent run directory
is the crash/uncertain-outcome barrier; this is deliberately not a resumable runner.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import importlib
import json
import math
import os
from pathlib import Path
from typing import Any

from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.pilot_terminal import save, transport
from src.extraction.llm import calibration_preflight as source_context
from src.extraction.llm.construction_acceptance import replay_and_project
from src.extraction.llm.format_conformance import VERSION, SCHEMA_VERSION
from src.extraction.llm.publications.openai_provider import (
    extract_model_output, load_openai_api_key, validate_provider_response,
)

MANIFEST = 'var/study2_step13/provider-compatibility-offline/ec436be-20261013/compatibility-manifest.json'
MANIFEST_SHA256 = 'bee79a4d0f4ea23318ab19069af9c5b0af43cb4012492077136be7269cdf0245'
STATE = 'var/study2_step13/compatibility-smoke/ec436be-20261013'
IDS = ('COMP-HS-01', 'COMP-GH-01', 'COMP-HUB-01')
FAMILIES = ('hydroshare', 'github', 'ciroh_hub')
PINS = ('semanticRequestSha256', 'providerEnvelopeSha256', 'providerInputSha256', 'schemaSha256')


def strict_json(raw: bytes) -> Any:
    """Reject duplicate keys and nonfinite numbers in authorizations and responses."""
    def pairs(items):
        """Preserve unique JSON keys only."""
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result

    def constant(value):
        """Reject JavaScript-style nonfinite numeric literals."""
        raise ValueError('nonfinite_json_number')

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def sync_directory(path: Path) -> None:
    """Make creation of intent files and attempt directories durable before send."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def persist(path: Path, raw: bytes) -> None:
    """Reuse exclusive durable file storage and additionally sync the parent."""
    save(path, raw)
    sync_directory(path.parent)


def replay_inputs(root: Path, row: dict, files: dict) -> dict:
    """Reuse the frozen reader snapshots and existing family replay signatures."""
    selection = strict_json(files['selection-provenance.json'])
    source = strict_json(files['source-owner.json'])
    if row['family'] == 'hydroshare':
        inputs = source_context.construct_request(root, selection, source, inputs_only=True)
    else:
        body = strict_json(files['semantic-request.json'])
        inputs = {'reader_result': strict_json(files['reader-result.json']),
            'selected_unit_ids': body['selectedSourceUnitIDs'],
            'input_complete': selection['inputCompleteness']['callerInputComplete'],
            'accepted_endpoints': selection['endpointInventories']['acceptedEndpoints'],
            'accepted_assertions': selection['endpointInventories']['acceptedAssertions']}
        if row['family'] == 'github':
            inputs['accepted_repository'] = {k: body['owner'][k] for k in
                ('canonicalArtifactID', 'repo_id', 'full_name', 'frozenCommitSha')}
        else:
            inputs.update(page=source, accepted_page_id=body['owner']['endpointID'],
                          accepted_section_mapping=selection['acceptedSectionMapping'])
    inputs['request_version'] = row['requestVersion']
    return inputs


def load_bundle(root: Path) -> tuple[dict, dict]:
    """Read and verify existing pins only; never rebuild or modify the 30 artifacts."""
    def pinned(relative, expected):
        """Constrain every manifest path to the repository and verify exact bytes."""
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('unsafe_artifact_path')
        raw = path.read_bytes()
        if digest(raw) != expected:
            raise ValueError('pinned_bytes_changed')
        return raw

    manifest = strict_json(pinned(MANIFEST, MANIFEST_SHA256))
    if (tuple(r['requestID'] for r in manifest['requests']) != IDS
            or tuple(r['family'] for r in manifest['requests']) != FAMILIES):
        raise ValueError('unexpected_smoke_inventory')
    for path, expected in manifest['authorityAndRuntimeFiles'].items():
        pinned(path, expected)
    bundles = {}
    for row in manifest['requests']:
        pinned(row['sourceSnapshot']['path'], row['sourceSnapshot']['sha256'])
        files = {name: pinned(record['path'], record['sha256']) for name, record in row['artifacts'].items()}
        if any(len(files[name]) != record['bytes'] for name, record in row['artifacts'].items()):
            raise ValueError('artifact_size_changed')
        for key, name in zip(PINS, ('semantic-request.json', 'provider-envelope.json', 'provider-input.txt', 'canonical-schema.json')):
            if digest(files[name]) != row[key]:
                raise ValueError('association_mismatch')
        request = strict_json(files['request-result.json'])
        envelope = strict_json(files['provider-envelope.json'])
        if (request['requestSha256'] != row['semanticRequestSha256']
                or source_context.semantic_bytes(request['request']) != files['semantic-request.json']
                or envelope['input'].encode() != files['provider-input.txt']
                or canonical(envelope['text']['format']['schema']) != files['canonical-schema.json']
                or envelope['text']['format']['strict'] is not True
                or {k: envelope[k] for k in row['modelSettings']} != row['modelSettings']):
            raise ValueError('envelope_or_request_mismatch')
        directory = {'hydroshare': 'datasets', 'github': 'coderepos', 'ciroh_hub': 'documents'}[row['family']]
        contract = importlib.import_module(f'src.extraction.llm.{directory}.request_contract')
        rebuilt = contract.build_request(**replay_inputs(root, row, files))
        if rebuilt != request:
            raise ValueError('frozen_context_replay_mismatch')
        bundles[row['requestID']] = files
    return manifest, bundles


def approval_draft(manifest: dict) -> dict:
    """Produce only an unauthorized template; no signature/approval is inferred."""
    return {'schemaVersion': 'step13-compatibility-approval/1', 'authorized': False,
        'approvalID': None, 'researcher': None, 'approvedAt': None, 'expiresAt': None,
        'manifestSha256': MANIFEST_SHA256, 'harnessSha256': digest(Path(__file__).read_bytes()),
        'currency': 'USD', 'pricingReference': None, 'inputUSDPerMillionTokens': None,
        'outputUSDPerMillionTokens': None, 'totalCostCap': None,
        'requests': {r['requestID']: {**{k: r[k] for k in PINS}, 'modelSettings': r['modelSettings'],
            'attempts': 1, 'reservedMaximumCost': None,
            'inputTokenAllowance': r['contextAllowance']['inputTokenAllowance'] + r['contextAllowance']['providerOverheadTokenAllowance'],
            'contextTokenLimit': r['contextAllowance']['historicalPlanningContextTokenLimit'],
            'outputTokenCeiling': r['outputTokenCeiling']} for r in manifest['requests']}}


def money(value: Any) -> Decimal:
    """Require a positive finite approved monetary value, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError('monetary_approval_missing')
    amount = Decimal(str(value))
    if not amount.is_finite() or amount <= 0:
        raise ValueError('monetary_approval_invalid')
    return amount


def verify_approval(raw: bytes, expected_sha256: str, manifest: dict) -> dict:
    """Require caller-pinned researcher approval; a digest is not a signature."""
    if not expected_sha256 or digest(raw) != expected_sha256:
        raise ValueError('approval_digest_mismatch')
    approval = strict_json(raw)
    template = approval_draft(manifest)
    if (approval.get('authorized') is not True or approval.get('currency') != 'USD'
            or any(approval.get(k) != template[k] for k in ('schemaVersion', 'manifestSha256', 'harnessSha256'))
            or set(approval.get('requests', {})) != set(IDS)):
        raise ValueError('researcher_authorization_required')
    for key in ('approvalID', 'researcher', 'pricingReference'):
        if not isinstance(approval.get(key), str) or not approval[key].strip():
            raise ValueError('approval_identity_missing')
    start = datetime.fromisoformat(approval['approvedAt'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(approval['expiresAt'].replace('Z', '+00:00'))
    if start.tzinfo is None or end.tzinfo is None or not start <= datetime.now(timezone.utc) < end:
        raise ValueError('approval_not_current')
    input_rate, output_rate = (money(approval[k]) for k in ('inputUSDPerMillionTokens', 'outputUSDPerMillionTokens'))
    reserves = []
    for rid in IDS:
        row, expected = approval['requests'][rid], template['requests'][rid]
        if (any(row.get(k) != expected[k] for k in (*PINS, 'modelSettings'))
                or type(row.get('attempts')) is not int or row['attempts'] != 1):
            raise ValueError('request_approval_mismatch')
        if (any(type(row.get(k)) is not int or row[k] <= 0 for k in ('inputTokenAllowance', 'contextTokenLimit', 'outputTokenCeiling'))
                or row['inputTokenAllowance'] < expected['inputTokenAllowance']
                or row['outputTokenCeiling'] != expected['outputTokenCeiling']
                or row['contextTokenLimit'] < row['inputTokenAllowance'] + row['outputTokenCeiling']):
            raise ValueError('context_approval_invalid')
        reserve = money(row['reservedMaximumCost'])
        bound = (row['inputTokenAllowance'] * input_rate + row['outputTokenCeiling'] * output_rate) / 1000000
        if reserve < bound:
            raise ValueError('reservation_insufficient')
        reserves.append(reserve)
    if sum(reserves) > money(approval['totalCostCap']):
        raise ValueError('budget_insufficient')
    return approval


def record_response(root: Path, attempt: Path, row: dict, files: dict, status: int, raw: bytes, approval: dict) -> None:
    """Preserve response and replay using existing adapters, then gate continuation."""
    persist(attempt / 'response.raw', raw)
    persist(attempt / 'http-result.json', canonical({'httpStatus': status, 'responseSha256': digest(raw)}))
    parsed = strict_json(raw)
    metadata = {k: parsed.get(k) for k in ('id', 'model', 'status', 'created_at', 'usage', 'incomplete_details', 'error')}
    persist(attempt / 'provider-metadata.json', canonical(metadata))
    if status != 200:
        raise ValueError('provider_response_failed')
    validate_provider_response(parsed)
    if not parsed.get('id'):
        raise ValueError('provider_identity_unverified')
    output = extract_model_output(parsed)
    persist(attempt / 'model-output.utf8', output)
    inputs = replay_inputs(root, row, files)
    result = replay_and_project(output, family=row['family'], request_inputs=inputs,
        expected_request_sha256=row['semanticRequestSha256'], conformance_version=VERSION, schema_version=SCHEMA_VERSION)
    persist(attempt / 'acceptance-report.json', result.report_json.encode())
    record = result.to_record()
    replay_raw = source_context.semantic_bytes(record['originalReplay'])
    persist(attempt / 'replay-report.json', replay_raw)
    persist(attempt / 'result-association.json', canonical({'responseSha256': digest(raw), 'modelOutputSha256': digest(output),
        'expectedRequestSha256': row['semanticRequestSha256'], 'replaySha256': digest(replay_raw),
        'acceptanceReportSha256': result.report_sha256, 'projectionSha256': record['projectionSha256']}))
    from jsonschema import Draft202012Validator
    # Structural schema validation only; semantic interpretation stays upstream.
    valid_schema = not list(Draft202012Validator(strict_json(files['canonical-schema.json'])).iter_errors(strict_json(output)))
    persist(attempt / 'schema-check.json', canonical({'canonicalSchemaConformant': valid_schema, 'schemaSha256': row['schemaSha256']}))
    if not valid_schema or record['status'] != 'projection_completed':
        raise ValueError('schema_or_replay_failure')
    if any(r['finalDisposition'] in {'processing_failed', 'rejected_invalid_assertion', 'failed_source_or_evidence_binding', 'needs_review'}
           for r in record['originalReplay']['finalRecords']):
        raise ValueError('original_replay_failure')
    usage = parsed.get('usage') or {}
    input_tokens, output_tokens = usage.get('input_tokens'), usage.get('output_tokens')
    approved = approval['requests'][row['requestID']]
    if (any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens))
            or input_tokens > approved['inputTokenAllowance'] or output_tokens > approved['outputTokenCeiling']):
        raise ValueError('usage_missing_or_exceeds_allowance')
    estimate = (input_tokens * money(approval['inputUSDPerMillionTokens'])
                + output_tokens * money(approval['outputUSDPerMillionTokens'])) / 1000000
    persist(attempt / 'cost-record.json', canonical({'approvedRateUndiscountedCostUSD': str(estimate),
        'reservedMaximumCostUSD': str(approved['reservedMaximumCost']), 'actualBilledCost': None,
        'basis': 'Approved rates applied to genuine usage; cached discounts not assumed.'}))
    if estimate > money(approved['reservedMaximumCost']):
        raise ValueError('cost_reservation_exceeded')


def execute(root: Path, approval_raw: bytes, approval_sha256: str, *, timeout: float = 1800,
            send=transport, key_loader=None) -> None:
    """Consume the fixed batch once, sequentially; every failure prevents redispatch."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('invalid_timeout')
    manifest, bundles = load_bundle(root)
    approval = verify_approval(approval_raw, approval_sha256, manifest)
    state = root / STATE
    if state.exists():
        raise ValueError('existing_run_no_redispatch')
    key = (key_loader or (lambda: load_openai_api_key(env_path=root / '.env')))()
    if not key:
        raise ValueError('credential_unavailable')
    state.parent.mkdir(parents=True, exist_ok=True)
    sync_directory(state.parent.parent)
    state.mkdir()  # Exclusive permanent batch claim; never remove after success or failure.
    sync_directory(state.parent)
    try:
        persist(state / 'approval.json', approval_raw)
        persist(state / 'manifest.json', (root / MANIFEST).read_bytes())
        for row in manifest['requests']:
            if (state / 'STOP').exists():
                raise ValueError('stop_requested')
            # Recheck expiry, all frozen pins and source files before EACH send.
            load_bundle(root)
            approval = verify_approval(approval_raw, approval_sha256, manifest)
            rid = row['requestID']
            attempt = state / rid
            attempt.mkdir()
            sync_directory(state)
            files = bundles[rid]
            persist(attempt / 'intent.json', canonical({'requestID': rid, 'attempt': 1,
                'at': datetime.now(timezone.utc).isoformat(), 'manifestSha256': MANIFEST_SHA256,
                'approvalSha256': approval_sha256, 'harnessSha256': approval['harnessSha256'],
                **{k: row[k] for k in PINS}, 'reservedMaximumCost': approval['requests'][rid]['reservedMaximumCost'],
                'timeoutSeconds': timeout, 'state': 'dispatch_intent_outcome_unknown_until_recorded'}))
            # Intent persistence may take time; recheck authorization and STOP
            # immediately before the irreversible network boundary.
            verify_approval(approval_raw, approval_sha256, manifest)
            if (state / 'STOP').exists():
                raise ValueError('stop_requested')
            # Exact frozen bytes, existing one-POST transport, no rebuilding/retry.
            status, raw = send(files['provider-envelope.json'], key, timeout)
            record_response(root, attempt, row, files, status, raw, approval)
            persist(attempt / 'completed.json', canonical({'state': 'response_replay_and_acceptance_preserved', 'attempt': 1}))
        persist(state / 'completed.json', canonical({'requests': list(IDS), 'attempts': 3, 'retries': 0, 'kgWrites': 0}))
    except BaseException:
        if not (state / 'STOP').exists():
            persist(state / 'STOP', b'Failed or uncertain smoke outcome. No retry or redispatch. Inspect preserved records.\n')
        raise RuntimeError('compatibility smoke STOP; no redispatch') from None


def main() -> None:
    """Expose explicit dry-run/draft/execute modes; default is offline dry-run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', choices=('dry-run', 'draft', 'execute'), default='dry-run')
    parser.add_argument('--approval', type=Path)
    parser.add_argument('--approval-sha256')
    parser.add_argument('--draft-path', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.mode == 'execute':
        if args.approval is None or not args.approval_sha256:
            parser.error('execute requires independently pinned --approval and --approval-sha256')
        execute(root, args.approval.read_bytes(), args.approval_sha256)
    else:
        manifest, _ = load_bundle(root)
        if args.mode == 'draft':
            if args.draft_path is None:
                parser.error('draft requires --draft-path in ignored local storage')
            target = args.draft_path.resolve()
            if not target.is_relative_to((root / 'var/study2_step13').resolve()):
                parser.error('draft must stay under var/study2_step13')
            target.parent.mkdir(parents=True, exist_ok=True)
            persist(target, canonical(approval_draft(manifest)))
        print(json.dumps({'status': 'NOT AUTHORIZED', 'requests': IDS, 'manifestSha256': MANIFEST_SHA256}))


if __name__ == '__main__':
    main()
