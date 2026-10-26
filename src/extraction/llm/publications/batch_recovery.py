"""Publications-only delivery recovery over the original scientific queue and journal.

Legacy events use the unchanged Batch validator. New deliveries carry a separate
native-attempt number; transport nonexecution never manufactures a native attempt.
"""
from __future__ import annotations

import base64
import fcntl
from collections import Counter
from typing import Any

from .request_builder import canonical_json, sha256_bytes
from .resumable_production_journal import require

VERSION = 'publications-delivery-recovery/1.0'
ISOLATION_VERSION = 'publications-terminal-usage-isolation/1.0'
RECOVERY_PATH = 'src/extraction/llm/publications/batch_recovery.py'
PREVIOUS_RECOVERY_SHA256 = '1b15dabe6d9aeb3dbb0ddc3d3a595b27df4c0ae9c5affc6c0f21d9cf76e75a7e'
NONEXECUTION = {'credit_balance_exhausted', 'batch_expired'}
CATEGORIES = ('completed_protected', 'never_prepared', 'prepared_not_submitted', 'creation_rejected',
              'provider_nonexecution', 'native_retry', 'terminal_review', 'ambiguous_transport', 'submitted_unsettled')


def nonexecution(receipt: dict) -> str | None:
    """Recognize only explicit per-request nonexecution without a model response."""
    row = receipt['row']
    error = row.get('error')
    if row.get('response') is None and isinstance(error, dict) and error.get('code') in NONEXECUTION:
        return error['code']
    response = row.get('response') or {}
    body = response.get('body')
    if (response.get('status_code') == 429 and isinstance(body, dict) and set(body) == {'error'}
            and isinstance(body['error'], dict) and body['error'].get('code') == 'credit_balance_exhausted'
            and row.get('error') is None):
        return 'credit_balance_exhausted'
    return None


def billing_rejection(evidence: dict) -> bool:
    """Require the preserved HTTP 400 billing rejection, not absence of a Batch."""
    from .batch_transport import decode
    try:
        body = decode(base64.b64decode(evidence['bodyBase64'], validate=True))
        return evidence['status'] == 400 and body['error']['code'] == 'billing_hard_limit_reached'
    except (KeyError, ValueError, TypeError):
        return False


def journal_type(base: type, verify_outcome: Any, fingerprint: Any) -> type:
    """Extend only Publications journals; source-family journals retain legacy policy."""
    class RecoveryJournal(base):
        """Retain historical indexes and add delivery/native-attempt lineage."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.recovery_migration = None
            self.isolation_migration = None
            self.isolation_enabled = False
            self.latest = {}
            self.nonexecutions = {}
            self.accepted = set()
            self.native_first = {}
            self.current_delivery = {}
            self.outcome_flags = {}

        def number(self, rid: str) -> int:
            """Return the indexed transport sequence, without scanning the corpus."""
            return self.current_delivery.get(rid, 0)

        def creation_rejection(self, jid: str) -> dict | None:
            """Bind a definitive rejection to the currently unresolved creation intent."""
            events = self.jobs[jid]
            if 'submission_rejected' in events and 'submit_intent' in events and 'submitted' not in events:
                return dict(self.job(jid, 'submission_rejected'), intentSha256=
                            sha256_bytes(canonical_json(self.job(jid, 'submit_intent'))))
            if 'submission_error' in events and 'submit_intent' in events and 'submitted' not in events:
                error = self.job(jid, 'submission_error')
                if (error['intentSha256'] == sha256_bytes(canonical_json(self.job(jid, 'submit_intent')))
                        and billing_rejection(error)):
                    return error
            return None

        def category(self, rid: str) -> str:
            """Partition the canonical queue once, without conflating delivery and processing."""
            if rid in self.accepted:
                return 'completed_protected'
            number = self.current_delivery.get(rid)
            if number:
                jid, _ = self.assignments[rid, number]
                events = self.jobs[jid]
                if 'submitted' not in events:
                    if self.creation_rejection(jid) or 'submission_rejected' in events:
                        return 'creation_rejected'
                    if 'submit_intent' in events or ('upload_intent' in events and 'uploaded' not in events):
                        return 'ambiguous_transport'
                    return 'prepared_not_submitted'
                if 'settled' not in events:
                    return 'submitted_unsettled'
                key = rid, number
                if key in self.nonexecutions:
                    return 'provider_nonexecution'
                if key in self.outcomes:
                    return 'native_retry' if self.outcome_flags[key] else 'terminal_review'
                return 'ambiguous_transport'
            return 'prepared_not_submitted' if rid in self.offsets else 'never_prepared'

        def ready(self, rid: str) -> bool:
            """Require terminal delivery evidence before reusing a scientific request."""
            key = rid, self.number(rid)
            if self.isolated_unknown_usage() and self.category(rid) != 'native_retry':
                return False
            return self.category(rid) in ('never_prepared', 'prepared_not_submitted',
                                          'provider_nonexecution', 'native_retry') and (
                key not in self.assignments or 'settled' in self.jobs[self.assignments[key][0]])

        def recovery_blocked(self) -> bool:
            """Isolate only settled overload holds; never erase unknown execution/billing."""
            return bool(self.unknown_usage - self.nonexecutions.keys() - self.isolated_unknown_usage())

        def isolated_unknown_usage(self) -> set:
            """Permit unrelated native retries only; the error request stays terminal and unpriced."""
            if not self.isolation_enabled:
                return set()
            isolated = set()
            for key in self.unknown_usage - self.nonexecutions.keys():
                rid, number = key
                if (self.number(rid) != number or self.category(rid) != 'terminal_review'
                        or key not in self.receipts or key not in self.outcomes):
                    continue
                receipt = self.payload_at(self.receipts[key])
                outcome = self.payload_at(self.outcomes[key])['native']
                response = receipt['row'].get('response') or {}
                body = response.get('body')
                if (response.get('status_code') == 503 and receipt['row'].get('error') is None
                        and isinstance(body, dict) and set(body) == {'error'}
                        and isinstance(body['error'], dict) and body['error'].get('code') == 'server_is_overloaded'
                        and receipt.get('rawModelOutputBase64') is None and receipt.get('usage') is None
                        and receipt['cost']['estimatedUSD'] is None
                        and outcome.get('transportHold') == 'UNKNOWN_USAGE'
                        and outcome.get('processable') is False and outcome.get('retryEligible') is False
                        and outcome.get('productionResult') is None):
                    isolated.add(key)
            return isolated

        def native_number(self, rid: str) -> int:
            """A native retry requires the frozen first processing failure, never a billing error."""
            return 2 if rid in self.native_first else 1

        def delivery_line(self, p: dict, fingerprint: Any) -> tuple[dict, bytes]:
            """Create a new transport identity with the exact persisted scientific body."""
            rid = p['request']['requestID']
            number = self.number(rid) + 1
            native_number = self.native_number(rid)
            identity = fingerprint(p)
            cid = sha256_bytes(canonical_json(dict(identity=identity, delivery=number,
                                                  nativeAttempt=native_number, transport=VERSION)))
            return (dict(rid=rid, number=number, nativeAttempt=native_number,
                         custom_id=cid, identity=identity),
                    canonical_json(dict(custom_id=cid, method='POST', url='/v1/responses', body=p['body'])) + b'\n')

        def validate_event(self, rec: dict) -> None:
            """Validate additive events fully, delegating every historical transition unchanged."""
            event, rid, pay = rec['event'], rec['requestID'], rec['payload']
            if event == 'terminal_usage_isolation_migration':
                require(rid is None and self.recovery_migration is not None and self.isolation_migration is None,
                        'ISOLATION_MIGRATION_TRANSITION')
                previous = self.payload_at(self.recovery_migration)
                require(pay['version'] == ISOLATION_VERSION and pay['manifestSha256'] == self.pin and
                        pay['previousMigrationSha256'] == sha256_bytes(canonical_json(previous)) and
                        pay['previousImplementationPins'] == previous['implementationPins'],
                        'ISOLATION_MIGRATION_BINDING_DRIFT')
                verify_isolation_pins(pay['previousImplementationPins'], pay['implementationPins'])
                return
            if event == 'recovery_migration':
                previous = self.payload_at(self.migration) if self.migration is not None else None
                require(self.seq > 0 and rid is None and self.recovery_migration is None and
                        pay['version'] == VERSION and pay['manifestSha256'] == self.pin and
                        pay['previousMigrationSha256'] == (sha256_bytes(canonical_json(previous)) if previous else None),
                        'RECOVERY_MIGRATION_BINDING_DRIFT')
                require(pay['previousImplementationPins'] == (previous['implementationPins'] if previous else
                        self.manifest['implementationPins']), 'RECOVERY_PREVIOUS_PINS_DRIFT')
                return
            if event in ('creation_absence', 'creation_redelivery'):
                error = self.creation_rejection(rid)
                require(self.recovery_migration is not None and error is not None,
                        'NOT_A_DEFINITIVE_CREATION_REJECTION')
                require(pay['intentSha256'] == error['intentSha256'] and
                        pay['errorSha256'] == sha256_bytes(canonical_json(error)) and
                        pay['inputSha256'] == self.job(rid, 'plan')['sha256'], 'CREATION_RETRY_BINDING_DRIFT')
                if event == 'creation_absence':
                    require(pay['matchingBatchIDs'] == [] and pay['listingComplete'] is True,
                            'CREATION_RECONCILIATION_INCOMPLETE')
                else:
                    require('creation_absence' in self.jobs[rid] and pay['absenceSha256'] ==
                            sha256_bytes(canonical_json(self.job(rid, 'creation_absence'))), 'MISSING_CREATION_RECONCILIATION')
                return
            if event == 'plan' and any('nativeAttempt' in i for i in pay['items']):
                require(self.recovery_migration is not None and rid not in self.jobs and
                        0 < pay['bytes'] <= 20000000 and 0 < len(pay['items']) <= 50000, 'RECOVERY_PLAN_LIMIT')
                seen, total = set(), 0
                for item in pay['items']:
                    r = item['rid']
                    require(r not in seen and r in self.tokens and self.ready(r), 'RECOVERY_REQUEST_NOT_READY')
                    seen.add(r)
                    expected, _ = self.delivery_line(self.prepared(r), fingerprint)
                    require(item == expected and item['nativeAttempt'] in (1, 2), 'DELIVERY_IDENTITY_DRIFT')
                    total += self.tokens[r]
                require(total == pay['tokens'] and total + self.reserved_tokens() <= self.queue_capacity,
                        'RECOVERY_TOKEN_CAPACITY')
                return
            if event == 'outcome' and (rid, pay['number']) in self.assignments:
                _, item = self.assignments[rid, pay['number']]
                if 'nativeAttempt' in item:
                    key = rid, pay['number']
                    require(key in self.receipts and key not in self.outcomes, 'OUTCOME_TRANSITION')
                    receipt = self.payload_at(self.receipts[key])
                    require(pay['receiptSha256'] == sha256_bytes(canonical_json(receipt)) and
                            pay['nativeAttempt'] == item['nativeAttempt'], 'DELIVERY_OUTCOME_BINDING_DRIFT')
                    if nonexecution(receipt):
                        require(pay['native'] == nonexecution_outcome(receipt), 'NONEXECUTION_OUTCOME_DRIFT')
                    else:
                        verify_outcome(self.prepared(rid), receipt, pay['native'], item['nativeAttempt'])
                    return
            super().validate_event(rec)

        def accept(self, rec: dict, digest: str, offset: int) -> None:
            """Index new records without deleting historical costs, receipts or failed outcomes."""
            event, rid, pay = rec['event'], rec['requestID'], rec['payload']
            if event in ('recovery_migration', 'terminal_usage_isolation_migration', 'creation_absence', 'creation_redelivery'):
                self.seq, self.head = rec['seq'], digest
                if event == 'recovery_migration':
                    self.recovery_migration = offset
                elif event == 'terminal_usage_isolation_migration':
                    self.isolation_migration = offset
                    self.isolation_enabled = True
                else:
                    self.jobs[rid][event] = offset
                    if event == 'creation_redelivery':
                        self.jobs[rid].pop('submit_intent')
                        self.jobs[rid].pop('submission_error', None)
                        self.jobs[rid].pop('submission_rejected', None)
                return
            super().accept(rec, digest, offset)
            if event == 'plan':
                for item in pay['items']:
                    self.current_delivery[item['rid']] = item['number']
            elif event == 'superseded':
                for item in self.job(rid, 'plan')['items']:
                    self.current_delivery.pop(item['rid'], None)
            elif event == 'submission_error':
                self.jobs[rid][event] = offset
            elif event == 'receipt':
                code = nonexecution(pay)
                if code:
                    self.nonexecutions[rid, pay['number']] = code
            elif event == 'outcome':
                key = rid, pay['number']
                self.latest[rid] = key
                self.outcome_flags[key] = pay['native']['retryEligible']
                if pay['native']['processable']:
                    self.accepted.add(rid)
                if key not in self.nonexecutions and pay['native'].get('retryEligible'):
                    self.native_first[rid] = offset

        def reconcile_creation(self, jid: str, api: Any, allow_retry: bool) -> bool:
            """Adopt exact accepted identity, or authorize one delivery after definite rejection."""
            from . import full_corpus_gpt61_batch as batch
            error = self.creation_rejection(jid)
            if error is None:
                return False
            intent = self.job(jid, 'submit_intent')
            matches = [b for b in api.listing('batches') if b.get('metadata') == intent['metadata']]
            require(len(matches) <= 1, 'DUPLICATE_REMOTE_BATCH_IDENTITY')
            if matches:
                batch.check_batch_binding(self, jid, matches[0])
                self.append('submitted', jid, matches[0])
                return False
            plan = self.job(jid, 'plan')
            require(sha256_bytes((self.path.parent / plan['filename']).read_bytes()) == plan['sha256'], 'SEALED_INPUT_DRIFT')
            binding = dict(intentSha256=error['intentSha256'], errorSha256=sha256_bytes(canonical_json(error)),
                           inputSha256=plan['sha256'])
            absence = dict(binding, matchingBatchIDs=[], listingComplete=True)
            if 'creation_absence' not in self.jobs[jid] or self.job(jid, 'creation_absence') != absence:
                self.append('creation_absence', jid, absence)
            if allow_retry:
                require(not self.recovery_blocked() and not batch.baseline.anomaly(self), 'COST_OR_EXECUTION_UNCERTAINTY_STOP')
                self.append('creation_redelivery', jid, dict(binding,
                            absenceSha256=sha256_bytes(canonical_json(absence))))
            return not allow_retry

    return RecoveryJournal


def nonexecution_outcome(receipt: dict) -> dict:
    """Record transport disposition only; do not invoke or alter scientific processing."""
    return dict(processable=False, retryEligible=False, productionResult=None,
                transportHold='PROVIDER_CONFIRMED_NONEXECUTION', providerCode=nonexecution(receipt))


def recovery_counts(log: Any) -> dict:
    """Report mutually exclusive queue categories and overlapping cache/billing diagnostics."""
    counts = Counter(log.category(rid) for rid in log.entries)
    never_submitted = sum(counts[k] for k in ('never_prepared', 'prepared_not_submitted', 'creation_rejected'))
    eligible = never_submitted + counts['provider_nonexecution'] + counts['native_retry']
    return dict(queueRequests=len(log.entries), categories={k: counts[k] for k in CATEGORIES},
                completedProtected=counts['completed_protected'], neverSubmitted=never_submitted,
                providerNonexecutionRecoverable=counts['provider_nonexecution'],
                nativeRetryEligible=counts['native_retry'], terminalReviewRequired=counts['terminal_review'],
                expectedUniqueEligible=eligible, requiresRemoteReconciliation=counts['creation_rejected'],
                eligibilityCondition='Credits restored; rejected creation reconciled read-only; no anomaly or unresolved execution uncertainty',
                cachedPrepared=len(log.offsets), cachedTokenCounts=len(log.tokens),
                historicalUnknownUsageAttempts=len(log.unknown_usage),
                unresolvedExecutionUsageAttempts=len(log.unknown_usage - log.nonexecutions.keys()),
                isolatedTerminalUnknownUsageAttempts=len(log.isolated_unknown_usage()),
                dispatchBlockedByExecutionUsage=log.recovery_blocked(),
                dispatchScope='native_retries_only' if log.isolated_unknown_usage() else 'existing_recovery_policy',
                usagePricedUSD=log.spent, finalInvoiceVerified=False,
                billingRecoverable=sum(log.nonexecutions.get(log.latest.get(r)) == 'credit_balance_exhausted'
                    and log.category(r) == 'provider_nonexecution' for r in log.entries),
                rejectedCreationJobs=[j for j in log.jobs if log.creation_rejection(j)])


def verify_isolation_pins(previous: dict, current: dict) -> None:
    """Permit only the pinned predecessor's Publications-only recovery module change."""
    if previous == current:
        return
    require(previous.get(RECOVERY_PATH) == PREVIOUS_RECOVERY_SHA256 and
            {k: v for k, v in previous.items() if k != RECOVERY_PATH} ==
            {k: v for k, v in current.items() if k != RECOVERY_PATH} and RECOVERY_PATH in current,
            'ISOLATION_IMPLEMENTATION_DRIFT')


def migrate(log: Any, current: dict, read_only: bool = False) -> None:
    """Chain the second implementation version to the first; never replace either manifest."""
    old = log.payload_at(log.migration) if log.migration is not None else None
    if old:
        from . import full_corpus_gpt61_batch as batch
        require(old['implementationPins'] == batch.baseline.read(batch.OPERATIONAL_COMPATIBILITY)['publicationsLegacyPins'],
                'RECOVERY_PRIOR_IMPLEMENTATION_DRIFT')
    payload = dict(version=VERSION, manifestSha256=log.pin,
                   previousMigrationSha256=sha256_bytes(canonical_json(old)) if old else None,
                   previousImplementationPins=old['implementationPins'] if old else log.manifest['implementationPins'],
                   implementationPins=current['implementationPins'])
    if log.recovery_migration is not None:
        historical = log.payload_at(log.recovery_migration)
        payload['implementationPins'] = historical['implementationPins']
        require(historical == payload, 'RECOVERY_IMPLEMENTATION_DRIFT')
    elif not read_only:
        log.append('recovery_migration', None, payload)
    verify_isolation_pins(payload['implementationPins'], current['implementationPins'])
    isolation = dict(version=ISOLATION_VERSION, manifestSha256=log.pin,
        previousMigrationSha256=sha256_bytes(canonical_json(payload)),
        previousImplementationPins=payload['implementationPins'], implementationPins=current['implementationPins'])
    if log.isolation_migration is not None:
        require(log.payload_at(log.isolation_migration) == isolation, 'ISOLATION_IMPLEMENTATION_DRIFT')
    elif not read_only:
        log.append('terminal_usage_isolation_migration', None, isolation)
    # Preview applies the validated prospective policy in memory only.
    log.isolation_enabled = True


def preview(Journal: type, native: Any, path: Any, data: bytes, current: dict) -> dict:
    """Replay read-only under a shared lock, including all existing validators and the head anchor."""
    log = Journal(path, data, sha256_bytes(data))
    require(not log.staging.exists(), 'PENDING_EVENT_REQUIRES_NORMAL_LOCKED_RECOVERY')
    with path.open('rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        log.file = handle
        if log.checkpoint.exists():
            log.anchor = native.decode(log.checkpoint.read_bytes())
        native.Journal.replay(log)
        migrate(log, current, read_only=True)
        from . import full_corpus_gpt61_batch as batch
        return dict(recovery_counts(log), journalSeq=log.seq, journalHead=log.head, readOnly=True,
                    compatibilityMigrationRequired=log.isolation_migration is None,
                    compatibilityMigrationVersion=ISOLATION_VERSION, costAnomalyStop=batch.baseline.anomaly(log),
                    schedulableNativeRetries=sum(log.ready(r) and log.category(r) == 'native_retry' for r in log.entries)
                    if not log.recovery_blocked() and not batch.baseline.anomaly(log) else 0)
