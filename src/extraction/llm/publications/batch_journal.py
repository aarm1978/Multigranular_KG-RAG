"""Batch state transitions on the existing locked, staged, hash-chained journal."""
from __future__ import annotations
from typing import Any
from .resumable_production_journal import journal_class, require
from .request_builder import canonical_json, sha256_bytes

TERMINAL = {'completed', 'expired', 'failed', 'cancelled'}
ACTIVE = {'validating', 'in_progress', 'finalizing', 'cancelling'}


def batch_journal(native: Any, verify: Any, fingerprint: Any, outcome_verify: Any,
                  receipt_verify: Any = None) -> type:
    """Reuse v0.2 framing/locking and v1 staging/recovery; isolate Batch transitions."""
    base = journal_class(native, verify, outcome_verify)

    class BatchJournal(base):
        """Index requests and jobs without retaining full corpus outputs in memory."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Initialize compact indexes and inherited cost counters."""
            super().__init__(*args, **kwargs)
            self.jobs = {}
            self.assignments = {}
            self.receipts = {}
            self.outcomes = {}
            self.tokens = {}
            self.exact_cost = 0.0
            self.conservative_costs = 0
            self.queue_capacity = self.manifest['queuedTokenLimit']
            self.migration = None

        def job(self, jid: str, event: str) -> dict:
            """Read a job event by durable offset."""
            return self.payload_at(self.jobs[jid][event])

        def number(self, rid: str) -> int:
            """Identify the current native attempt without changing scientific request IDs."""
            return max((n for r, n in self.assignments if r == rid), default=0)

        def validate_event(self, rec: dict) -> None:
            """Fail closed on duplicate scheduling, mismatched receipts, or native drift."""
            event, rid, pay = rec['event'], rec['requestID'], rec['payload']
            if event == 'header':
                require(self.seq == 0 and rid is None and pay == dict(manifestSha256=self.pin,
                        generatorPins=self.manifest['generatorPins']), 'HEADER_DRIFT')
                return
            require(self.seq > 0, 'MISSING_HEADER')
            if event == 'implementation_migration':
                require(rid is None and self.migration is None and
                        pay['version'] == 'unsubmitted-upload-repack/1.0' and
                        pay['manifestSha256'] == self.pin and
                        pay['previousImplementationPins'] == self.manifest['implementationPins'] and
                        pay['maxNewFileBytes'] == 20000000 and
                        set(pay['implementationPins']) == set(pay['previousImplementationPins']),
                        'INVALID_IMPLEMENTATION_MIGRATION')
                return
            if event == 'superseded':
                job = self.jobs[rid]
                require(self.migration is not None and 'plan' in job and
                        not any(e in job for e in ('superseded', 'submit_intent', 'submitted',
                                                  'capacity_retry', 'submission_rejected')),
                        'CANNOT_SUPERSEDE_POTENTIALLY_SUBMITTED_JOB')
                plan = self.job(rid, 'plan')
                require(plan['bytes'] > 20000000 and
                        pay == dict(planSha256=sha256_bytes(canonical_json(plan)),
                                    migrationSha256=sha256_bytes(canonical_json(self.payload_at(self.migration))),
                                    remoteFileDisposition='possibly_uploaded_inert_unsubmitted_input',
                                    releasedInputTokens=plan['tokens']), 'SUPERSESSION_BINDING_DRIFT')
                return
            if event == 'capacity_increase':
                require(rid is None and pay['previous'] == self.queue_capacity and
                        type(pay['new']) is int and pay['new'] > self.queue_capacity and
                        pay['source'] == 'researcher_supplied_operational_capacity' and
                        pay['manifestSha256'] == self.pin, 'INVALID_CAPACITY_INCREASE')
                return
            if event in ('upload_error', 'submission_error'):
                intent = 'upload_intent' if event == 'upload_error' else 'submit_intent'
                require(intent in self.jobs[rid] and pay['intentSha256'] ==
                        sha256_bytes(canonical_json(self.job(rid, intent))), 'HTTP_ERROR_INTENT_DRIFT')
                return
            if event == 'submission_rejected':
                job = self.jobs[rid]
                require('submit_intent' in job and 'submitted' not in job and 'submission_rejected' not in job,
                        'INVALID_SUBMISSION_REJECTION')
                require(pay['capacity'] == self.queue_capacity and pay['status'] in (400, 429) and
                        pay['body']['error']['code'] in ('token_limit_exceeded', 'batch_queue_limit_exceeded'),
                        'NOT_DEFINITIVE_CAPACITY_REJECTION')
                return
            if event == 'capacity_retry':
                require('submission_rejected' in self.jobs[rid] and
                        (pay['trigger'] == 'submit_all_restart' or
                         (pay['trigger'] == 'capacity_increase' and
                          self.queue_capacity > self.job(rid, 'submission_rejected')['capacity'])) and
                        pay['rejectionSha256'] == sha256_bytes(canonical_json(self.job(rid, 'submission_rejected'))),
                        'CAPACITY_RETRY_REQUIRES_INCREASE')
                return
            if event in ('plan', 'upload_intent', 'uploaded', 'submit_intent', 'submitted', 'snapshot', 'downloads', 'settled'):
                if event == 'plan':
                    require(rid not in self.jobs and pay['items'], 'DUPLICATE_OR_EMPTY_JOB')
                    ceiling = 20000000 if self.migration is not None else 190000000
                    require(len(pay['items']) <= 50000 and 0 < pay['bytes'] <= ceiling, 'BATCH_FILE_LIMIT')
                    seen = set()
                    total = 0
                    for item in pay['items']:
                        r, n, cid = item['rid'], item['number'], item['custom_id']
                        require(cid not in seen and (r, n) not in self.assignments, 'DUPLICATE_ASSIGNMENT')
                        seen.add(cid)
                        require(r in self.tokens and self.state[r] in ('prepared', 'retry'), 'REQUEST_NOT_READY')
                        require(n == (2 if self.state[r] == 'retry' else 1), 'RETRY_NUMBER_DRIFT')
                        require(item['identity'] == fingerprint(self.prepared(r)), 'BATCH_IDENTITY_DRIFT')
                        require(cid == sha256_bytes(canonical_json(dict(identity=item['identity'], attempt=n,
                                transport='batch-v1'))), 'CUSTOM_ID_DRIFT')
                        total += self.tokens[r]
                    require(total == pay['tokens'] and total <= self.queue_capacity, 'TOKEN_CAPACITY')
                    require(total + self.reserved_tokens() <= self.queue_capacity, 'AGGREGATE_TOKEN_CAPACITY')
                else:
                    require(rid in self.jobs, 'UNKNOWN_BATCH_JOB')
                    job = self.jobs[rid]
                    require('superseded' not in job, 'SUPERSEDED_JOB_IS_INERT')
                    before = {'upload_intent': 'plan', 'uploaded': 'upload_intent', 'submit_intent': 'uploaded',
                              'submitted': 'submit_intent', 'snapshot': 'submitted', 'downloads': 'snapshot', 'settled': 'downloads'}[event]
                    require(before in job and (event == 'snapshot' or event not in job), 'BATCH_TRANSITION')
                    if event in ('submitted', 'snapshot'):
                        require(pay['input_file_id'] == self.job(rid, 'uploaded')['id'] and
                                pay['metadata'] == self.job(rid, 'submit_intent')['metadata'] and
                                pay['endpoint'] == '/v1/responses' and pay['status'] in ACTIVE | TERMINAL, 'BATCH_REMOTE_BINDING')
                        if event == 'snapshot':
                            require(pay['id'] == self.job(rid, 'submitted')['id'], 'BATCH_ID_DRIFT')
                    if event == 'downloads':
                        require(self.job(rid, 'snapshot')['status'] in TERMINAL, 'NONTERMINAL_RESULTS')
                    if event == 'settled':
                        require(all((i['rid'], i['number']) in self.outcomes for i in self.job(rid, 'plan')['items']), 'MISSING_OUTCOMES')
                return
            require(rid in self.entries, 'UNKNOWN_REQUEST')
            if event == 'prepared':
                require(rid not in self.state, 'REPREPARATION')
                verify(native.unbundle(pay), self.entries[rid])
            elif event == 'token_count':
                require(self.state.get(rid) == 'prepared' and rid not in self.tokens, 'TOKEN_COUNT_TRANSITION')
                require(pay['bodySha256'] == fingerprint(self.prepared(rid))['bodySha256'] and
                        type(pay['provider']['input_tokens']) is int and pay['provider']['input_tokens'] > 0, 'TOKEN_COUNT_BINDING')
            elif event in ('receipt', 'outcome'):
                n = pay['number']
                key = (rid, n)
                require(key in self.assignments, 'UNSUBMITTED_RESULT')
                jid, item = self.assignments[key]
                require('downloads' in self.jobs[jid], 'RESULT_BEFORE_DOWNLOADS')
                if event == 'receipt':
                    require(key not in self.receipts and pay['row']['custom_id'] == item['custom_id'], 'DUPLICATE_OR_WRONG_RESULT')
                    require(pay['batchID'] == self.job(jid, 'submitted')['id'], 'RESULT_BATCH_ID_DRIFT')
                    if receipt_verify is not None:
                        receipt_verify(self.prepared(rid), pay)
                else:
                    require(key in self.receipts and key not in self.outcomes, 'OUTCOME_TRANSITION')
                    receipt = self.payload_at(self.receipts[key])
                    require(pay['receiptSha256'] == sha256_bytes(canonical_json(receipt)), 'OUTCOME_RECEIPT_DRIFT')
                    outcome_verify(self.prepared(rid), receipt, pay['native'], n)
            else:
                raise ValueError('UNKNOWN_BATCH_EVENT')

        def accept(self, rec: dict, digest: str, offset: int) -> None:
            """Rebuild indexes and account once per durable receipt, independent of result order."""
            self.seq, self.head = rec['seq'], digest
            event, rid, pay = rec['event'], rec['requestID'], rec['payload']
            if event == 'header':
                return
            if event == 'implementation_migration':
                self.migration = offset
                return
            if event == 'superseded':
                self.jobs[rid][event] = offset
                for item in self.job(rid, 'plan')['items']:
                    self.assignments.pop((item['rid'], item['number']))
                    self.state[item['rid']] = 'prepared' if item['number'] == 1 else 'retry'
                return
            if event in ('upload_error', 'submission_error'):
                return  # Evidence remains in the chain; the original intent is still uncertain.
            if event == 'capacity_increase':
                self.queue_capacity = pay['new']
                return
            if event == 'submission_rejected':
                self.jobs[rid][event] = offset
                return
            if event == 'capacity_retry':
                # Only indexes advance; all prior intent/rejection bytes remain immutable.
                self.jobs[rid].pop('submission_rejected')
                self.jobs[rid].pop('submit_intent')
                self.jobs[rid][event] = offset
                return
            if event in ('plan', 'upload_intent', 'uploaded', 'submit_intent', 'submitted', 'snapshot', 'downloads', 'settled'):
                self.jobs.setdefault(rid, {})[event] = offset
                if event == 'plan':
                    for item in pay['items']:
                        self.assignments[item['rid'], item['number']] = (rid, item)
                        self.state[item['rid']] = 'pending'
                if event == 'submit_intent':
                    self.started_at = self.started_at or pay['unixTime']
                return
            if event == 'prepared':
                self.offsets[rid] = {'prepared': offset}
                self.state[rid] = 'prepared'
            elif event == 'token_count':
                self.tokens[rid] = pay['provider']['input_tokens']
            elif event == 'receipt':
                key = rid, pay['number']
                self.receipts[key] = offset
                amount = pay['cost']['estimatedUSD']
                if amount is None:
                    self.unknown_usage.add(key)
                else:
                    self.spent += amount
                    if pay['cost']['basis'] == 'reported_cache_details':
                        self.exact_cost += amount
                    elif amount:
                        self.conservative_costs += 1
                    if rid not in self.costed_requests and pay['providerResponse'] is not None:
                        self.costed_requests.add(rid)
                        self.estimated_processed += self.entries[rid]['estimatedCostUSD']
                self.state[rid] = 'received'
            elif event == 'outcome':
                self.outcomes[rid, pay['number']] = offset
                out = pay['native']
                self.state[rid] = 'completion' if out['processable'] else 'retry' if out['retryEligible'] else 'failed'

        def reserved_tokens(self) -> int:
            """Reserve the whole job until its terminal result files are reconciled."""
            return sum(self.job(j, 'plan')['tokens'] for j, events in self.jobs.items()
                       if 'settled' not in events and 'superseded' not in events)

    return BatchJournal
