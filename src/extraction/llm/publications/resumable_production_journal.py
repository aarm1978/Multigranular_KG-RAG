"""Production extension of the existing single-writer, hash-chained v0.2 journal.

Retains original decode, replay, offset access and lock behavior. Adds bounded
attempt records and transactional single-event staging without modifying history.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .request_builder import canonical_json, sha256_bytes


def require(ok: bool, reason: str) -> None:
    """Fail closed even under optimized Python."""
    if not ok:
        raise ValueError(reason)


def sync_directory(path: Path) -> None:
    """Persist directory entries after staging/rename/unlink operations."""
    descriptor = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def replace_atomic(path: Path, data: bytes) -> None:
    """Replace an operational checkpoint using one flushed temporary file."""
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


def journal_class(native: Any, verify_prepared: Any, verify_outcome: Any) -> type:
    """Extend the pinned native Journal without changing its historical implementation."""
    class ProductionJournal(native.Journal):
        """Durable bounded attempts, exact recovery and cheap verified-completion replay."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Keep only offsets and compact counters in memory."""
            super().__init__(*args, **kwargs)
            self.attempts = {}
            self.spent = 0.0
            self.estimated_processed = 0.0
            self.costed_requests = set()
            self.unknown_usage = set()
            self.started_at = None
            self.checkpoint = self.path.with_name('head.json')
            self.staging = self.path.with_name('pending-event.json')

        def replay(self) -> None:
            """Recover a fully staged last event; never truncate committed journal bytes."""
            if self.staging.exists():
                staged = self.staging.read_bytes()
                try:
                    value = native.decode(staged)
                    require(sha256_bytes(canonical_json(value['record'])) == value['sha256'], 'STAGED_CHECKSUM')
                except (ValueError, KeyError):
                    # An incomplete temporary write precedes journal append/dispatch.
                    self.file.seek(0, 2)
                    size = self.file.tell()
                    if size:
                        self.file.seek(-1, 2)
                        require(self.file.read(1) == b'\n', 'INCOMPLETE_JOURNAL_WITHOUT_VALID_STAGING')
                    self.staging.unlink()
                    sync_directory(self.path.parent)
                else:
                    self.file.seek(0, 2)
                    size = self.file.tell()
                    self.file.seek(max(0, size - len(staged)))
                    tail = self.file.read()
                    if not tail.endswith(staged):
                        # Only an identical staged prefix at the very end can be completed.
                        suffix = tail[tail.rfind(b'\n') + 1:]
                        require(staged.startswith(suffix), 'STAGED_JOURNAL_PREFIX_MISMATCH')
                        self.file.seek(0, 2)
                        self.file.write(staged[len(suffix):])
                        self.file.flush()
                        os.fsync(self.file.fileno())
                    self.staging.unlink()
                    sync_directory(self.path.parent)
            if self.checkpoint.exists():
                checkpoint = native.decode(self.checkpoint.read_bytes())
                self.anchor = checkpoint
            super().replay()

        def __enter__(self) -> Any:
            """Replay under the inherited exclusive lock, then permit evidence-only recovery."""
            super().__enter__()
            self.restart_hold = False
            return self

        def attempt_context(self, rid: str, number: int) -> dict[str, Any]:
            """Read only one attempt's durable payloads by offset."""
            return {name: self.payload_at(offset) for name, offset in self.attempts.get(rid, {}).get(number, {}).items()}

        def prepared(self, rid: str) -> dict[str, Any]:
            """Recover the exact provider bundle rather than regenerate dispatched content."""
            return native.unbundle(self.payload_at(self.offsets[rid]['prepared']))

        def number(self, rid: str) -> int:
            """Return the latest dispatched attempt number."""
            return max(self.attempts.get(rid, {}), default=0)

        def validate_event(self, rec: dict[str, Any]) -> None:
            """Validate every transition and binding without reprocessing completed corpus output."""
            event, rid, payload = rec['event'], rec['requestID'], rec['payload']
            if event == 'header':
                require(self.seq == 0 and rid is None and payload == dict(manifestSha256=self.pin, generatorPins=self.manifest['generatorPins']), 'HEADER_DRIFT')
                return
            require(rid in self.entries and self.seq > 0, 'UNKNOWN_QUEUE_ID')
            number = int(rec['attemptID'].rsplit('/attempt-', 1)[1])
            require(rec['attemptID'] == rid + '/attempt-%02d' % number and number in (1, 2), 'ATTEMPT_ID_DRIFT')
            state = self.state.get(rid)
            if event == 'prepared':
                require(state is None and number == 1, 'PREPARED_REDISPATCH')
                require(all(v == 'completion' for v in self.state.values()), 'UNRESOLVED_PREVIOUS_REQUEST')
                verify_prepared(native.unbundle(payload), self.entries[rid])
            elif event == 'dispatch_intent':
                require((state == 'prepared' and number == 1) or (state == 'retry' and number == 2), 'INVALID_DISPATCH_TRANSITION')
                require(payload['identity'] == self.payload_at(self.offsets[rid]['prepared'])['executionIdentity'], 'DISPATCH_IDENTITY_DRIFT')
            elif event == 'stream_trace':
                require(state == 'dispatch_intent' and number == self.number(rid), 'TRACE_OUTSIDE_ATTEMPT')
            elif event == 'response':
                require(state == 'dispatch_intent' and number == self.number(rid), 'RESPONSE_TRANSITION')
                terminal = self.attempt_context(rid, number).get('terminal', {}).get('terminalEvent', {})
                require(payload['providerResponse'] == terminal.get('response'), 'RESPONSE_TERMINAL_BINDING_DRIFT')
                require(payload['usage'] == payload['providerResponse'].get('usage'), 'USAGE_DRIFT')
                require(payload['pricing'] == self.manifest['pricing'], 'PRICING_DRIFT')
                amount = payload['cost']['estimatedUSD']
                require(payload['cumulativeUsagePricedUSD'] == (self.spent + amount if amount is not None else self.spent), 'CUMULATIVE_COST_DRIFT')
            elif event == 'native_outcome':
                require(state == 'response' and number == self.number(rid), 'OUTCOME_TRANSITION')
                verify_outcome(self.prepared(rid), self.attempt_context(rid, number)['response'], payload, number)
            elif event == 'retry':
                require(state == 'native_outcome' and number == 1 and self.number(rid) == 1, 'RETRY_LIMIT_OR_TRANSITION')
                require(self.attempt_context(rid, 1)['native_outcome']['retryEligible'] is True, 'NOT_NATIVE_RETRY_ELIGIBLE')
            elif event == 'completion':
                require(state == 'native_outcome' and number == self.number(rid), 'COMPLETION_TRANSITION')
                outcome = self.attempt_context(rid, number)['native_outcome']
                require(outcome['processable'] is True and not outcome['retryEligible'], 'UNPROCESSABLE_COMPLETION')
                require(payload == dict(nativeOutcomeSha256=sha256_bytes(canonical_json(outcome)),
                                        identity=self.payload_at(self.offsets[rid]['prepared'])['executionIdentity'],
                                        cumulativeUsagePricedUSD=self.spent), 'COMPLETION_HASH_DRIFT')
            else:
                raise ValueError('UNKNOWN_PRODUCTION_EVENT')

        def accept(self, rec: dict[str, Any], digest: str, offset: int) -> None:
            """Index attempts and cost exactly once while replaying or committing."""
            self.seq, self.head = rec['seq'], digest
            rid, event, payload = rec['requestID'], rec['event'], rec['payload']
            if rid is None:
                return
            self.offsets.setdefault(rid, {})
            if event == 'prepared':
                self.offsets[rid]['prepared'] = offset
                self.state[rid] = event
                return
            number = int(rec['attemptID'].rsplit('/attempt-', 1)[1])
            ctx = self.attempts.setdefault(rid, {}).setdefault(number, {})
            if event == 'stream_trace':
                if 'terminalEvent' in payload:
                    ctx['terminal'] = offset
                if payload.get('type') == 'transport_failure':
                    ctx['transport_failure'] = offset
                return
            ctx[event] = offset
            self.state[rid] = event
            if event == 'dispatch_intent':
                self.started_at = self.started_at or payload['unixTime']
                self.unknown_usage.add((rid, number))
            if event == 'response':
                cost = payload['cost']['estimatedUSD']
                if cost is not None:
                    self.unknown_usage.discard((rid, number))
                    self.spent += cost
                    if rid not in self.costed_requests:
                        self.costed_requests.add(rid)
                        self.estimated_processed += self.entries[rid]['estimatedCostUSD']

        def append(self, event: str, rid: str | None, payload: dict[str, Any], number: int | None = None) -> str:
            """Commit one write-ahead event and checksum checkpoint before any external action."""
            require(self.file is not None and not self.poisoned, 'JOURNAL_CLOSED_OR_POISONED')
            n = number or (max(1, self.number(rid)) if rid else 1)
            rec = dict(seq=self.seq + 1, previous=self.head, event=event, requestID=rid,
                       attemptID=None if rid is None else rid + '/attempt-%02d' % n, payload=payload)
            self.validate_event(rec)
            digest = sha256_bytes(canonical_json(rec))
            data = canonical_json(dict(record=rec, sha256=digest)) + b'\n'
            try:
                # A crash during this staging write cannot precede provider dispatch.
                with self.staging.open('wb') as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                sync_directory(self.path.parent)
                self.file.seek(0, 2)
                offset = self.file.tell()
                self.file.write(data)
                self.file.flush()
                os.fsync(self.file.fileno())
                self.accept(rec, digest, offset)
                summary = dict(completed=sum(v == 'completion' for v in self.state.values()),
                               total=len(self.entries), cumulativeUsagePricedUSD=self.spent,
                               estimatedProcessedUSD=self.estimated_processed,
                               costedRequests=len(self.costed_requests), unknownUsageAttempts=len(self.unknown_usage),
                               startedAt=self.started_at, observedAt=__import__('time').time())
                checkpoint = dict(seq=self.seq, headSha256=self.head, summary=summary,
                                  summarySha256=sha256_bytes(canonical_json(summary)))
                replace_atomic(self.checkpoint, canonical_json(checkpoint) + b'\n')
                self.staging.unlink()
                sync_directory(self.path.parent)
            except BaseException:
                self.poisoned = True
                raise
            return digest

    return ProductionJournal
