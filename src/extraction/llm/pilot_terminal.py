"""Researcher-operated one-request terminal transport. Import never dispatches."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import queue
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from src.extraction.llm.pilot_preflight import build_preflight, canonical, digest, verify_selection, SELECTIONS
from src.extraction.llm.calibration_preflight import load_case, REQUEST_IDS, MANIFEST_SHA256, wave_for


def save(path, data):
    """Create and durably preserve bytes without overwriting an artifact."""
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def load_legacy_selected(root, request_id):
    """Verify stored associations and rebuild the pure envelope, without corpus IO."""
    if request_id not in SELECTIONS:
        raise ValueError('unknown_request')
    folder = root / 'var/study2_step12c/preflight' / request_id
    request = json.loads((folder / 'request-result.json').read_bytes())
    owners = {'HS-01':'7d960b7fdfee480895fd845bade1b75a', 'GH-01':'github:repo:921792119',
              'HUB-01':'hub:page:83a1aceb2c34ed513d83'}
    verify_selection(request, SELECTIONS[request_id], owners[request_id])
    result = build_preflight(request, output_ceiling=32768)
    for filename, key in [('provider-envelope.json','wireBytes'), ('provider-input.txt','inputBytes'),
                          ('semantic-request.json','semanticRequestBytes')]:
        if (folder / filename).read_bytes() != result[key]:
            raise ValueError('stored_preflight_drift')
    metadata = json.loads((folder / 'preflight.json').read_bytes())
    for key in ('semanticRequestSha256','providerInputSha256','providerEnvelopeSha256','schemaSha256'):
        if metadata.get(key) != result[key]:
            raise ValueError('stored_hash_drift')
    return result


def load_selected(root, request_id, *, amendment=None, amendment_sha256=None):
    """Use pinned manifest preflight for every CLI ID; no legacy approval bypass."""
    if amendment is not None or amendment_sha256 is not None:
        if amendment is None or not amendment_sha256:
            raise ValueError('amendment_path_and_digest_required')
        from src.extraction.llm.wave_b_amendment import load_case as load_amended_case
        return load_amended_case(root, request_id, Path(amendment), amendment_sha256)
    return load_case(root, request_id)


def verify_approval(raw, expected_digest, request_id, result):
    """Verify explicit local authorization, expiry, hashes and reserved cost bounds.

    The separately supplied digest pins researcher-reviewed bytes; it is not a
    digital signature or an assertion that model prices have been verified here.
    """
    if digest(raw) != expected_digest:
        raise ValueError('approval_digest_mismatch')
    def unique(pairs):
        """Reject ambiguous approval objects rather than choosing a duplicate."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate_approval_field')
            result[key] = value
        return result
    approval = json.loads(raw, object_pairs_hook=unique)
    version = 'step12c-terminal-approval/2' if 'calibrationManifestSha256' in result else 'step12c-terminal-approval/1'
    if 'executionAmendmentSha256' in result:
        version = 'step12c-terminal-approval/3'
    if approval.get('schemaVersion') != version or approval.get('authorized') is not True:
        raise ValueError('not_authorized')
    for field in ('approvalID','researcher','approvedAt','expiresAt','currency','pricingReference'):
        if not isinstance(approval.get(field), str) or not approval[field].strip():
            raise ValueError('approval_field_missing')
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(approval['approvedAt'].replace('Z','+00:00'))
    end = datetime.fromisoformat(approval['expiresAt'].replace('Z','+00:00'))
    if start.tzinfo is None or end.tzinfo is None or not start <= now < end:
        raise ValueError('approval_time_invalid')
    rows = approval.get('requests')
    if not isinstance(rows, dict) or not rows or set(rows) - set(REQUEST_IDS if version in ('step12c-terminal-approval/2', 'step12c-terminal-approval/3') else SELECTIONS) or request_id not in rows:
        raise ValueError('request_not_approved')
    if any(not isinstance(row, dict) for row in rows.values()):
        raise ValueError('approval_request_malformed')
    caps = [approval.get('totalCostCap')] + [r.get('reservedMaximumCost') for r in rows.values()]
    if any(type(c) not in (int,float) or not math.isfinite(c) or c <= 0 for c in caps) or sum(caps[1:]) > caps[0]:
        raise ValueError('monetary_caps_invalid')
    selected = rows[request_id]
    if type(selected.get('maximumAttempts')) is not int or selected['maximumAttempts'] != 1:
        raise ValueError('one_attempt_required')
    for key in ('semanticRequestSha256','providerEnvelopeSha256'):
        if selected.get(key) != result[key]:
            raise ValueError('approval_request_mismatch')
    if version in ('step12c-terminal-approval/2', 'step12c-terminal-approval/3'):
        verify_wave_and_context(approval, request_id, result, now)
    if version == 'step12c-terminal-approval/3':
        from src.extraction.llm.wave_b_amendment import wave_settings, PRIOR_AMENDMENT_SHA256
        wave = result['calibrationWave']
        settings = wave_settings(wave)
        if (set(rows) - set(settings['ids']) or request_id not in settings['ids']
                or set(approval['waves']) != {wave}
                or approval.get('executionAmendmentSha256') != result['executionAmendmentSha256']
                or selected.get('executionAmendmentSha256') != result['executionAmendmentSha256']
                or approval.get('executionAmendmentVersion') != settings['version']
                or result.get('executionAmendmentVersion') != settings['version']):
            raise ValueError('amendment_approval_mismatch')
        if wave == 'C' and (approval.get('priorExecutionAmendmentSha256') != PRIOR_AMENDMENT_SHA256
                or result.get('priorExecutionAmendmentSha256') != PRIOR_AMENDMENT_SHA256):
            raise ValueError('prior_amendment_approval_mismatch')
        from src.extraction.llm.pilot_wave import CONTEXT_LIMIT
        if selected['contextTokenLimit'] > CONTEXT_LIMIT:
            raise ValueError('published_context_limit_exceeded')
    return approval


def verify_wave_and_context(approval, request_id, result, now):
    """Require explicit wave clearance and researcher-attested context/budget bounds."""
    if (approval.get('manifestSha256') != MANIFEST_SHA256
            or result.get('calibrationManifestSha256') != MANIFEST_SHA256
            or result.get('calibrationRequestID') != request_id
            or result.get('calibrationWave') != wave_for(request_id)
            or 'HS-01' in approval['requests']):
        raise ValueError('calibration_approval_identity_mismatch')
    wave = wave_for(request_id)
    waves = approval.get('waves')
    if not isinstance(waves, dict) or not waves or set(waves) - {'A', 'B', 'C'}:
        raise ValueError('wave_approval_missing')
    wave_caps = []
    for name, row in waves.items():
        if not isinstance(row, dict) or type(row.get('authorized')) is not bool:
            raise ValueError('wave_approval_malformed')
        ids = row.get('requestIDs')
        expected = {rid for rid in approval['requests'] if wave_for(rid) == name}
        cap = row.get('reservedCostCap')
        if (not isinstance(ids, list) or any(not isinstance(rid, str) for rid in ids)
                or len(ids) != len(set(ids)) or set(ids) != expected or not ids
                or type(cap) not in (int, float) or not math.isfinite(cap) or cap <= 0
                or sum(approval['requests'][rid]['reservedMaximumCost'] for rid in ids) > cap):
            raise ValueError('wave_inventory_or_budget_invalid')
        wave_caps.append(cap)
    if (sum(wave_caps) > approval['totalCostCap']
            or any(wave_for(rid) not in waves for rid in approval['requests'])
            or wave not in waves or waves[wave]['authorized'] is not True):
        raise ValueError('wave_not_authorized_or_over_budget')
    clearances = approval.get('waveClearances')
    if not isinstance(clearances, dict):
        raise ValueError('wave_clearances_missing')
    for prior in ('A', 'B')[:{'A': 0, 'B': 1, 'C': 2}[wave]]:
        clearance = clearances.get(prior)
        if (not isinstance(clearance, dict) or clearance.get('decision') != 'cleared_for_next_wave'
                or any(not isinstance(clearance.get(k), str) or not clearance[k].strip()
                       for k in ('researcher', 'clearedAt', 'reviewRecordSha256'))):
            raise ValueError('prior_wave_researcher_clearance_required')
        stamp = datetime.fromisoformat(clearance['clearedAt'].replace('Z', '+00:00'))
        fingerprint = clearance['reviewRecordSha256']
        if (stamp.tzinfo is None or stamp > now or len(fingerprint) != 64
                or any(c not in '0123456789abcdef' for c in fingerprint)):
            raise ValueError('prior_wave_clearance_invalid')
    selected = approval['requests'][request_id]
    for key in ('providerInputSha256', 'schemaSha256', 'requestVersion',
                'providerInputProjectionVersion', 'promptIdentifier'):
        if key not in selected or selected[key] != result[key]:
            raise ValueError('calibration_request_version_or_hash_mismatch')
    if selected.get('wave') != wave:
        raise ValueError('request_wave_mismatch')
    values = [selected.get(k) for k in ('inputTokenAllowance', 'providerOverheadTokenAllowance',
                                      'contextTokenLimit', 'outputTokenCeiling')]
    if any(type(value) is not int or value <= 0 for value in values):
        raise ValueError('approved_context_bounds_missing')
    allowance, overhead, context, output = values
    if (output != 32768 or allowance < result['conservativeInputTokenAllowance'] + overhead
            or context < allowance + output):
        raise ValueError('approved_context_bounds_exceeded')


class NoRedirect(HTTPRedirectHandler):
    """Never forward authorization to a redirected endpoint."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Reject redirects; preserve their HTTP response as an error."""
        return None


def transport(wire, key, timeout):
    """One synchronous POST of exact bytes; no retries, redirects or polling."""
    request = Request('https://api.openai.com/v1/responses', data=wire,
                      headers={'Authorization':'Bearer ' + key, 'Content-Type':'application/json'}, method='POST')
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def execute(root, request_id, approval_raw, approval_digest, *, timeout=1800, progress_interval=15,
            send=transport, key_loader=None, progress=print, wave_token=None,
            amendment=None, amendment_sha256=None):
    """Dispatch exactly once after approval; ambiguous/crashed attempts block all IDs."""
    if request_id == 'HS-01':
        raise ValueError('historical_request_not_dispatchable')
    from src.extraction.llm.publications.openai_provider import extract_model_output, load_openai_api_key
    if not math.isfinite(timeout) or not math.isfinite(progress_interval) or timeout <= 0 or progress_interval <= 0:
        raise ValueError('invalid_timing')
    route = {} if amendment is None and amendment_sha256 is None else dict(amendment=amendment, amendment_sha256=amendment_sha256)
    result = load_selected(root, request_id, **route)
    amendment_raw = Path(amendment).read_bytes() if amendment is not None else None
    if amendment_raw is not None and digest(amendment_raw) != result['executionAmendmentSha256']:
        raise ValueError('amendment_digest_mismatch')
    verify_approval(approval_raw, approval_digest, request_id, result)
    # Credential absence must not consume the single approved attempt.
    key = (key_loader or (lambda: load_openai_api_key(env_path=root / '.env')))()
    if not key:
        raise ValueError('credential_unavailable')
    state = root / 'var/study2_step12c/terminal'
    state.mkdir(parents=True, exist_ok=True)
    lock = state / 'dispatch.lock'
    lock.mkdir()  # atomic global lock, survives process crash
    attempt = state / request_id  # one attempt per frozen request, across approvals
    try:
        wave_lock = state / 'wave.lock'
        if wave_lock.exists():
            if wave_token is None or (wave_lock / 'owner').read_text() != wave_token:
                raise ValueError('wave_dispatch_in_progress')
        elif wave_token is not None:
            raise ValueError('wave_lock_missing')
        if (state / 'STOP').exists():
            raise ValueError('dispatch_blocked')
        attempt.mkdir()
    except BaseException:
        lock.rmdir()
        raise
    started = time.monotonic()

    def event(status, **fields):
        """Append credential-free lifecycle facts and flush before proceeding."""
        with (attempt / 'events.jsonl').open('ab') as stream:
            stream.write(canonical({'event':status,'at':datetime.now(timezone.utc).isoformat(),
                                    'elapsedSeconds':round(time.monotonic()-started,3), **fields}) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())

    dispatched = False
    try:
        save(attempt / 'approval.json', approval_raw)
        if amendment_raw is not None:
            save(attempt / 'execution-amendment.json', amendment_raw)
        save(attempt / 'provider-envelope.json', result['wireBytes'])
        save(attempt / 'provider-input.txt', result['inputBytes'])
        save(attempt / 'semantic-request.json', result['semanticRequestBytes'])
        save(attempt / 'association.json', canonical({k:result[k] for k in
             ('semanticRequestSha256','providerEnvelopeSha256','providerInputSha256','schemaSha256',
              'calibrationManifestSha256','calibrationRequestID','calibrationWave','requestVersion',
              'promptIdentifier','providerInputProjectionVersion','executionAmendmentSha256',
              'executionAmendmentVersion','priorExecutionAmendmentSha256') if k in result}))
        event('prepared', requestID=request_id, approvalSha256=approval_digest, timeoutSeconds=timeout)
        replies = queue.Queue()

        def worker():
            """Return raw transport bytes; never write files or retry in a worker."""
            try:
                replies.put(('response', send(result['wireBytes'], key, timeout)))
            except BaseException:
                replies.put(('ambiguous', None))

        event('dispatch_started')
        dispatched = True
        threading.Thread(target=worker, daemon=True).start()
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('ambiguous_transport')
            try:
                kind, data = replies.get(timeout=min(progress_interval,remaining))
                break
            except queue.Empty:
                elapsed = round(time.monotonic()-started,1)
                progress(f'{request_id}: awaiting response; elapsed {elapsed}s (no retry)')
                event('waiting')
        if kind != 'response':
            raise TimeoutError('ambiguous_transport')
        status, raw = data
        save(attempt / 'response.raw', raw)  # durable before parsing/extraction
        event('response_preserved', httpStatus=status, responseSha256=digest(raw), responseBytes=len(raw))
        parsed = json.loads(raw)
        metadata = {k:parsed.get(k) for k in ('id','model','status','created_at','usage','incomplete_details','error')}
        metadata.update(httpStatus=status, responseSha256=digest(raw))
        save(attempt / 'provider-metadata.json', canonical(metadata))
        try:
            output = extract_model_output(parsed)
        except (ValueError, RuntimeError, TypeError, AttributeError):
            output = None
        if output is not None:
            save(attempt / 'model-output.utf8', output)
        outcome = 'response_recorded' if status == 200 and parsed.get('status') == 'completed' and output is not None else 'response_requires_review'
        event(outcome, semanticReplay='not_run')
        if outcome != 'response_recorded':
            save(state / 'STOP', b'response requires researcher review; no further dispatch\n')
        return outcome
    except BaseException:
        if dispatched and not (state / 'STOP').exists():
            save(state / 'STOP', b'ambiguous or incomplete attempt; no further dispatch\n')
        event('stopped', disposition='ambiguous_or_incomplete' if dispatched else 'not_dispatched')
        raise RuntimeError('pilot stopped; inspect local lifecycle artifacts; no retry') from None
    finally:
        lock.rmdir()


def main():
    """Explicit dry-run or single-ID execute; never infer authorization."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['dry-run','execute'])
    parser.add_argument('--request-id', required=True, choices=list(REQUEST_IDS))
    parser.add_argument('--amendment', type=Path)
    parser.add_argument('--amendment-sha256')
    parser.add_argument('--approval', type=Path)
    parser.add_argument('--approval-sha256')
    parser.add_argument('--timeout', type=float, default=1800)
    parser.add_argument('--progress-interval', type=float, default=15)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    route = {} if args.amendment is None and args.amendment_sha256 is None else dict(amendment=args.amendment, amendment_sha256=args.amendment_sha256)
    if args.mode == 'dry-run':
        result = load_selected(root,args.request_id, **route)
        print(json.dumps({k:v for k,v in result.items() if k.endswith('Sha256') or k in ('authorization','outputTokenCeiling','calibrationRequestID','calibrationWave',
                'inputByteCount','wireByteCount','conservativeInputTokenAllowance','executionHold')},indent=2))
        return
    if args.approval is None or not args.approval_sha256:
        parser.error('execute requires --approval and --approval-sha256')
    print(execute(root,args.request_id,args.approval.read_bytes(),args.approval_sha256,
                  timeout=args.timeout,progress_interval=args.progress_interval, **route))


if __name__ == '__main__':
    main()
