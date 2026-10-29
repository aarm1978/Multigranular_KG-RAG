"""Explicit v6 file-only recovery; never mutate native production or create a Batch."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.extraction.llm import source_family_batch as adapter
from src.extraction.llm.publications import batch_transport as transport
from src.extraction.llm.publications import openai_provider
from src.extraction.llm.publications.resumable_production_journal import sync_directory

ROOT = adapter.batch.baseline.ROOT
QUEUE = Path('var/study2_step13/source-local-specialized-production/v6')
SIDECAR = Path('var/study2_step13/source-local-specialized-production/v6-upload-recovery/job-000001')
QUEUE_SHA = 'f3e6a3485800988812befc8d429813f5784bb98a7f2cdc88d9e62f5703dca615'
RUN_SHA = '818c166c26645393622e72b13669582a3d79e8997b296b73a12d5762a66aaef0'
FILE_SHA = '539e6ec0ff6bf3b2f7a1184359b32123787186755ddfdc34346934e33dbba457'
HEAD_SHA = '321c82f362ca8a477911dcd39a845a01062a0a67ab990a2f568a611cad9881b1'
JOB = 'job-000001'
TIMEOUT = 600
require, canonical, digest = adapter.require, adapter.canonical, adapter.digest


class FileOnlyAPI(transport.BatchAPI):
    """Reuse native pagination/multipart encoding with a single long-timeout file POST."""

    def request(self, method, path, data=None, content_type='application/json', safe=False):
        """Allow only file listing/content reads and one non-retried upload operation."""
        listing = method == 'GET' and path.startswith('/files?')
        content = method == 'GET' and re.fullmatch(r'/files/file-[A-Za-z0-9_-]+/content', path)
        require(listing or content or (method == 'POST' and path == '/files' and not safe), 'FILE_ONLY_ENDPOINT_REQUIRED')
        if method == 'GET':
            raw = super().request(method, path, data, content_type, safe=True)
            if listing:
                page = transport.decode(raw)
                require(isinstance(page.get('data'), list) and type(page.get('has_more')) is bool,
                        'INCOMPLETE_FILE_LISTING')
                require(not page['has_more'] or bool(page['data']), 'EMPTY_NONTERMINAL_PAGE')
            return raw
        req = Request('https://api.openai.com/v1/files', data=data, method='POST',
                      headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': content_type})
        try:
            with urlopen(req, timeout=TIMEOUT) as response:
                return response.read()
        except HTTPError as exc:
            raise transport.HTTPFailure(exc.code, exc.read()) from None
        except (OSError, TimeoutError):
            raise ValueError('UPLOAD_OUTCOME_UNCERTAIN; no automatic repeat') from None


@contextmanager
def sealed_job(repo=ROOT):
    """Read-only native replay under an exclusive lock; verify this exact interrupted job."""
    root = repo / QUEUE
    queue_raw = (root / 'queue-manifest.json').read_bytes()
    require(digest(queue_raw) == QUEUE_SHA, 'QUEUE_DRIFT')
    queue = transport.decode(queue_raw)
    for rel, sha in queue['implementationPins'].items():
        require(digest((repo / rel).read_bytes()) == sha, 'PIN_DRIFT:' + rel)
    execution = root / 'execution/batch'
    raw = (execution / 'run-manifest.json').read_bytes()
    require(digest(raw) == RUN_SHA, 'RUN_MANIFEST_DRIFT')
    manifest = transport.decode(raw)
    require(manifest['parentSha256'] == QUEUE_SHA and manifest['transport'] == 'batch', 'RUN_BINDING_DRIFT')
    entries = {e['identity']['requestID']: e for e in queue['requests']}

    def verify(prepared, entry):
        """Bind recorded prepared bytes to the sealed queue without extraction/preflight."""
        original = entries[entry['identity']['requestID']]
        require(adapter.fingerprint(prepared) == original['identity'] == entry['identity'] and
                digest(canonical(prepared) + b'\n') == original['bundleSha256'], 'PREPARED_DRIFT')

    def forbidden(*args):
        """This checkpoint contains no provider receipts or model outcomes."""
        raise ValueError('UNEXPECTED_PROVIDER_OUTCOME')

    _, native, _ = adapter.infrastructure()
    Journal = adapter.batch_journal(native, verify, adapter.fingerprint, forbidden, forbidden)
    log = Journal(execution / 'execution.jsonl', raw, RUN_SHA)
    with log.path.open('rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            require(not log.staging.exists(), 'PENDING_NATIVE_EVENT_STOP')
            log.file = handle
            log.anchor = native.decode(log.checkpoint.read_bytes())
            native.Journal.replay(log)
            require(log.seq == 893 and log.head == HEAD_SHA, 'JOURNAL_CHECKPOINT_DRIFT')
            require(set(log.jobs) == {JOB} and set(log.jobs[JOB]) == {'plan', 'upload_intent'}, 'JOB_STATE_DRIFT')
            plan = log.job(JOB, 'plan'); intent = log.job(JOB, 'upload_intent')
            require(intent == dict(filename=plan['filename'], sha256=plan['sha256']), 'UPLOAD_INTENT_DRIFT')
            require(plan['sha256'] == FILE_SHA and plan['bytes'] == 19977551 and
                    plan['filename'] == 'pub-' + RUN_SHA[:16] + '-' + FILE_SHA + '.jsonl', 'SEALED_PLAN_DRIFT')
            path = execution / plan['filename']
            require(path.stat().st_size == plan['bytes'] and digest(path.read_bytes()) == FILE_SHA, 'SEALED_FILE_DRIFT')
            yield path, dict(queueSha256=QUEUE_SHA, runManifestSha256=RUN_SHA, jobID=JOB,
                journalSeq=893, journalHeadSha256=HEAD_SHA, uploadIntent=intent,
                filename=path.name, bytes=plan['bytes'], sha256=FILE_SHA, timeoutSeconds=TIMEOUT)
        finally:
            log.file = None
            fcntl.flock(handle, fcntl.LOCK_UN)


def durable_directory(path):
    """Persist each newly created directory entry, including the sidecar's parents."""
    if not path.exists():
        durable_directory(path.parent)
        path.mkdir(exist_ok=True)
        sync_directory(path.parent)


def seal(path, value):
    """Create and fsync an immutable sidecar before permitting the next operation."""
    with path.open('xb') as handle:
        handle.write(canonical(value) + b'\n'); handle.flush(); os.fsync(handle.fileno())
    sync_directory(path.parent)


def verify_remote(api, row, binding):
    """Verify metadata and exact downloaded input bytes; never trust a name alone."""
    require(isinstance(row, dict) and row.get('filename') == binding['filename'] and
            row.get('bytes') == binding['bytes'] and row.get('purpose') == 'batch' and
            re.fullmatch(r'file-[A-Za-z0-9_-]+', row.get('id', '')), 'REMOTE_METADATA_DRIFT')
    raw = api.content(row['id'])
    require(len(raw) == binding['bytes'] and digest(raw) == binding['sha256'], 'REMOTE_CONTENT_DRIFT')
    return row['id']


def recover(path, binding, sidecar, api, *, allow_one_upload=False):
    """Reconcile first; a durable intent permits at most one POST across all invocations."""
    durable_directory(sidecar)
    with (sidecar / 'recovery.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        sync_directory(sidecar)
        intent_path = sidecar / 'intent.json'
        if intent_path.exists():
            require(transport.decode(intent_path.read_bytes())['binding'] == binding, 'RECOVERY_INTENT_DRIFT')
        require(not (sidecar / 'outcome.json').exists() or intent_path.exists(), 'ORPHAN_RECOVERY_OUTCOME')
        rows = api.listing('files')
        # Same matching rule as native submit reconciliation; hash verification follows.
        matches = [r for r in rows if r.get('filename') == binding['filename'] and r.get('bytes') == binding['bytes']]
        check_id = uuid.uuid4().hex
        seal(sidecar / ('listing-' + check_id + '.json'), dict(binding=binding, matches=matches,
             listedFiles=len(rows), fullyPaginated=True))
        require(len(matches) <= 1, 'MULTIPLE_MATCHING_FILES_STOP')
        if matches:
            file_id = verify_remote(api, matches[0], binding)
            result = dict(status='verified_reuse', fileID=file_id, binding=binding, batchSubmitted=False)
            seal(sidecar / ('verified-' + check_id + '.json'), result)
            return result
        require(not intent_path.exists(), 'PRIOR_RECOVERY_INTENT_STOP; reconcile only, never repeat POST')
        require(allow_one_upload, 'ZERO_MATCHES; explicit --allow-one-upload required')
        require(path.stat().st_size == binding['bytes'] and digest(path.read_bytes()) == binding['sha256'], 'SEALED_FILE_DRIFT')
        seal(intent_path, dict(binding=binding, action='one_file_upload', listingCheck=check_id, attempts=1))
        try:
            uploaded = api.upload(path)
        except BaseException as exc:
            seal(sidecar / 'outcome.json', dict(binding=binding, status='uncertain', exceptionType=type(exc).__name__))
            raise ValueError('UPLOAD_OUTCOME_UNCERTAIN; recovery intent prohibits another POST') from None
        seal(sidecar / 'outcome.json', dict(binding=binding, status='response_received', response=uploaded))
        file_id = verify_remote(api, uploaded, binding)
        result = dict(status='verified_upload', fileID=file_id, binding=binding, batchSubmitted=False)
        seal(sidecar / ('verified-' + check_id + '.json'), result)
        return result


def main():
    """Researcher-terminal entry point; inspect is offline, recover permits Files only."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['inspect', 'recover'])
    parser.add_argument('--allow-one-upload', action='store_true')
    args = parser.parse_args()
    with sealed_job() as (path, binding):
        if args.operation == 'inspect': result = dict(binding=binding, providerCalls=0)
        else:
            api = FileOnlyAPI(openai_provider.load_openai_api_key())
            result = recover(path, binding, ROOT / SIDECAR, api, allow_one_upload=args.allow_one_upload)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
