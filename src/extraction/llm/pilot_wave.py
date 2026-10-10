"""Offline Wave A draft preparation and explicitly approved sequential transport."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
import os
from pathlib import Path
from uuid import uuid4

from src.extraction.llm import pilot_terminal as terminal
from src.extraction.llm.calibration_preflight import REQUEST_IDS, MANIFEST_SHA256, wave_for
from src.extraction.llm.pilot_preflight import canonical, digest

MODEL_REFERENCE = 'https://developers.openai.com/api/docs/models/gpt-5.6-sol'
CONTEXT_LIMIT = 1_050_000  # Published model specification, checked 2026-10-09.
OUTPUT_LIMIT = 32768
HASH_VERSION_FIELDS = ('semanticRequestSha256', 'providerEnvelopeSha256', 'providerInputSha256',
                       'schemaSha256', 'requestVersion', 'providerInputProjectionVersion', 'promptIdentifier')
STATE_DIRECTORY = 'var/study2_step12c/terminal'


def wave_ids(wave: str) -> tuple[str, ...]:
    """Return the complete frozen wave in family/ID order, excluding historical HS-01."""
    if wave not in ('A', 'B', 'C'):
        raise ValueError('unknown_wave')
    return tuple(rid for rid in REQUEST_IDS if rid != 'HS-01' and wave_for(rid) == wave)


def prepare_wave_a(root: Path, overhead: int = 4096) -> dict:
    """Verify existing frozen preflights and propose an unauthorized approval v2 draft."""
    if type(overhead) is not int or overhead <= 0:
        raise ValueError('positive_overhead_required')
    rows = {}
    for rid in wave_ids('A'):
        result = terminal.load_selected(root, rid)
        allowance = result['conservativeInputTokenAllowance'] + overhead
        if allowance + OUTPUT_LIMIT > CONTEXT_LIMIT:
            raise ValueError('published_context_limit_exceeded')
        # Standard uncached rates; reserve cache-write uplift as well. Long-context
        # pricing is triggered conservatively by the allowance, not guessed usage.
        input_rate, output_rate = (10, 30) if allowance > 272000 else (5, 20)
        dollars = (Decimal(allowance * input_rate + OUTPUT_LIMIT * output_rate) / 1000000)
        reserve = dollars.quantize(Decimal('.01'), rounding=ROUND_CEILING)
        rows[rid] = {k: result[k] for k in HASH_VERSION_FIELDS}
        rows[rid].update(wave='A', maximumAttempts=1, reservedMaximumCost=float(reserve),
            inputTokenAllowance=allowance, providerOverheadTokenAllowance=overhead,
            contextTokenLimit=CONTEXT_LIMIT, outputTokenCeiling=OUTPUT_LIMIT)
    total = int(sum(Decimal(str(row['reservedMaximumCost'])) for row in rows.values()).to_integral_value(rounding=ROUND_CEILING))
    return dict(schemaVersion='step12c-terminal-approval/2', status='DRAFT / NOT AUTHORIZED',
        authorized=False, approvalID='', researcher='', approvedAt='', expiresAt='', currency='USD',
        pricingReference=MODEL_REFERENCE, manifestSha256=MANIFEST_SHA256, totalCostCap=total,
        requests=rows, waves={'A': dict(authorized=False, requestIDs=list(rows), reservedCostCap=total)},
        waveClearances={}, reservationBasis={
            'checkedOn': '2026-10-09', 'model': 'gpt-5.6-sol', 'contextReference': MODEL_REFERENCE,
            'inputAllowance': 'one token per input/schema UTF-8 byte plus proposed overhead; not measured',
            'standardUsdPerMillion': {'input': 4, 'cacheWrite': 5, 'output': 20},
            'longContextAboveInputTokens': 272000,
            'longContextUsdPerMillion': {'input': 8, 'cacheWrite': 10, 'output': 30},
            'pricingReviewRequired': True,
            'scope': 'Proposed standard-service USD reservation, rounded up per request; no cache discount. '
                     'Researcher must verify current account tier, surcharges, prices and overhead before authorization.'})


def verify_wave(root: Path, wave: str, raw: bytes, sha256: str, **route) -> dict:
    """Check every member before dispatch, retaining the existing v2 approval authority."""
    if route and wave not in ('B', 'C'):
        raise ValueError('amendment_wave_b_only_or_wave_c_only')
    ids = wave_ids(wave)
    results = {}
    for rid in ids:
        result = terminal.load_selected(root, rid, **route)
        approval = terminal.verify_approval(raw, sha256, rid, result)
        if (approval['schemaVersion'] != ('step12c-terminal-approval/3' if route else 'step12c-terminal-approval/2')
                or set(approval['waves'][wave]['requestIDs']) != set(ids)):
            raise ValueError('complete_wave_approval_required')
        row = approval['requests'][rid]
        if row['contextTokenLimit'] > CONTEXT_LIMIT:
            raise ValueError('published_context_limit_exceeded')
        results[rid] = result
    return results


def confirm_recorded(attempt: Path, result: dict, approval: bytes) -> str:
    """Confirm durable response facts/associations; never evaluate semantic content."""
    from src.extraction.llm.publications.openai_provider import extract_model_output
    for filename, expected in [('approval.json', approval), ('provider-envelope.json', result['wireBytes']),
            ('provider-input.txt', result['inputBytes']), ('semantic-request.json', result['semanticRequestBytes'])]:
        if (attempt / filename).read_bytes() != expected:
            raise ValueError('recorded_artifact_mismatch')
    association = json.loads((attempt / 'association.json').read_bytes())
    for key in (*HASH_VERSION_FIELDS, 'calibrationManifestSha256', 'calibrationRequestID', 'calibrationWave'):
        if association.get(key) != result[key]:
            raise ValueError('recorded_association_mismatch')
    if 'executionAmendmentSha256' in result:
        for key in ('executionAmendmentSha256', 'executionAmendmentVersion'):
            if association.get(key) != result[key]:
                raise ValueError('recorded_amendment_mismatch')
        if ('priorExecutionAmendmentSha256' in result
                and association.get('priorExecutionAmendmentSha256') != result['priorExecutionAmendmentSha256']):
            raise ValueError('recorded_prior_amendment_mismatch')
        if digest((attempt / 'execution-amendment.json').read_bytes()) != result['executionAmendmentSha256']:
            raise ValueError('recorded_amendment_mismatch')
    raw = (attempt / 'response.raw').read_bytes()
    metadata = json.loads((attempt / 'provider-metadata.json').read_bytes())
    parsed = json.loads(raw)
    events = [json.loads(line) for line in (attempt / 'events.jsonl').read_bytes().splitlines()]
    preserved = [event for event in events if event['event'] == 'response_preserved']
    if (any(metadata.get(key) != parsed.get(key) for key in
            ('id', 'model', 'status', 'created_at', 'usage', 'incomplete_details', 'error'))
            or len(preserved) != 1 or preserved[0]['responseSha256'] != digest(raw)
            or preserved[0]['responseBytes'] != len(raw) or preserved[0]['httpStatus'] != 200
            or events[0].get('approvalSha256') != digest(approval)):
        raise ValueError('recorded_metadata_mismatch')
    if (metadata['responseSha256'] != digest(raw) or metadata['httpStatus'] != 200
            or metadata['status'] != 'completed' or parsed.get('status') != 'completed'
            or events[-1]['event'] != 'response_recorded'
            or (attempt / 'model-output.utf8').read_bytes() != extract_model_output(parsed)):
        raise ValueError('recorded_response_mismatch')
    return parsed['status']


def execute_wave(root: Path, wave: str, raw: bytes, sha256: str, *, timeout: float = 1800,
                 progress_interval: float = 15, progress=print, amendment=None, amendment_sha256=None, **transport_options) -> Path:
    """Invoke the existing executor sequentially; stop on the first nonconfirmed result."""
    route = {} if amendment is None and amendment_sha256 is None else dict(amendment=amendment, amendment_sha256=amendment_sha256)
    results = verify_wave(root, wave, raw, sha256, **route)  # No credentials, locks or attempts yet.
    state = root / STATE_DIRECTORY
    state.mkdir(parents=True, exist_ok=True)
    lock = state / 'wave.lock'
    lock.mkdir()  # Exclusive across all waves; survives hard crash, never auto-recovered.
    token = uuid4().hex
    folder = state / 'waves' / wave / sha256
    summary = dict(schemaVersion='step12c-wave-transport/1', wave=wave, approvalSha256=sha256,
        manifestSha256=MANIFEST_SHA256, requestIDs=list(results), attempts=[],
        remainingUnattemptedIDs=list(results), status='preparing', semanticReview='not_run')
    if route:
        summary['executionAmendmentSha256'] = amendment_sha256
        first_result = next(iter(results.values()))
        if 'priorExecutionAmendmentSha256' in first_result:
            summary['priorExecutionAmendmentSha256'] = first_result['priorExecutionAmendmentSha256']

    def checkpoint():
        """Append a durable summary snapshot, including in-flight/ambiguous attempts."""
        summary['at'] = datetime.now(timezone.utc).isoformat()
        with (folder / 'summary.jsonl').open('ab') as stream:
            stream.write(canonical(summary) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())

    created = False
    try:
        terminal.save(lock / 'owner', token.encode())
        folder.mkdir(parents=True)  # Same reviewed wave cannot resume or overwrite a prior run.
        created = True
        terminal.save(folder / 'approval.json', raw)
        checkpoint()
        if (state / 'STOP').exists() or (state / 'dispatch.lock').exists():
            raise ValueError('dispatch_blocked')
        if any((state / rid).exists() for rid in results):
            raise ValueError('existing_attempt_no_skip_or_recovery')
        for rid, result in results.items():
            if (state / 'STOP').exists():
                raise ValueError('dispatch_blocked')
            attempt = state / rid
            entry = dict(requestID=rid, outcome='in_flight', responseStatus=None,
                         artifactPath=str(attempt.relative_to(root)))
            summary['attempts'].append(entry)
            summary['remainingUnattemptedIDs'].remove(rid)
            summary['status'] = 'running'
            checkpoint()
            progress(f'{wave}: starting {rid}; {len(summary["remainingUnattemptedIDs"])} remain')
            try:
                outcome = terminal.execute(root, rid, raw, sha256, timeout=timeout,
                    progress_interval=progress_interval, progress=progress, wave_token=token, **route, **transport_options)
                entry['outcome'] = outcome
                if outcome != 'response_recorded':
                    raise ValueError('response_not_confirmed')
                entry['responseStatus'] = confirm_recorded(attempt, result, raw)
                if (state / 'STOP').exists():
                    raise ValueError('dispatch_blocked')
            except BaseException as error:
                entry['exceptionType'] = type(error).__name__
                metadata_path = attempt / 'provider-metadata.json'
                if metadata_path.exists():
                    try:
                        status = json.loads(metadata_path.read_bytes()).get('status')
                        entry['responseStatus'] = status if status in ('completed', 'incomplete', 'failed', 'cancelled', 'queued', 'in_progress') else 'unknown'
                    except (ValueError, OSError, AttributeError):
                        entry['responseStatus'] = 'unreadable'
                entry['outcome'] = 'stopped' if entry['outcome'] in ('in_flight', 'response_recorded') else entry['outcome']
                entry['artifactExists'] = attempt.exists()
                if attempt.exists() and not (state / 'STOP').exists():
                    terminal.save(state / 'STOP', b'wave attempt unconfirmed; researcher inspection required\n')
                raise
            checkpoint()
            progress(f'{rid}: response_recorded (semantic review remains separate)')
        summary['status'] = 'wave_responses_recorded'
    except BaseException:
        summary['status'] = 'stopped'
        # Do not persist arbitrary exception strings: transports may contain secrets.
        if created and (folder / 'summary.jsonl').exists() and not (folder / 'summary.json').exists():
            checkpoint()
            terminal.save(folder / 'summary.json', canonical(summary))
        raise RuntimeError(f'wave stopped; inspect {folder / "summary.jsonl"}; no retry') from None
    else:
        checkpoint()
        terminal.save(folder / 'summary.json', canonical(summary))
    finally:
        (lock / 'owner').unlink(missing_ok=True)
        lock.rmdir()
    return folder / 'summary.json'


def main():
    """Prepare an unauthorized draft or explicitly execute one reviewed wave."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare-wave-a', 'execute'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--wave', choices=('A', 'B', 'C'))
    parser.add_argument('--amendment', type=Path)
    parser.add_argument('--amendment-sha256')
    parser.add_argument('--approval', type=Path)
    parser.add_argument('--approval-sha256')
    parser.add_argument('--timeout', type=float, default=1800)
    parser.add_argument('--progress-interval', type=float, default=15)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.mode == 'prepare-wave-a':
        if args.output is None:
            parser.error('prepare-wave-a requires --output (a new ignored local path)')
        draft = prepare_wave_a(root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        terminal.save(args.output, json.dumps(draft, indent=2, ensure_ascii=True).encode() + b'\n')
        print(f'DRAFT / NOT AUTHORIZED: {args.output}')
    else:
        if args.wave is None or args.approval is None or not args.approval_sha256:
            parser.error('execute requires --wave, --approval and --approval-sha256')
        print(execute_wave(root, args.wave, args.approval.read_bytes(), args.approval_sha256,
                          timeout=args.timeout, progress_interval=args.progress_interval,
                          amendment=args.amendment, amendment_sha256=args.amendment_sha256))


if __name__ == '__main__':
    main()
