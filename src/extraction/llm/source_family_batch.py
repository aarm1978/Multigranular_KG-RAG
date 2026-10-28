"""Offline-testable Batch adapters for accepted non-Publication semantic requests.

All provider operations belong to an explicitly invoked researcher-terminal
controller. This module imports the Publications infrastructure read-only.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
from typing import Any

from src.extraction.llm import construction_acceptance as acceptance
from src.extraction.llm import format_conformance as conformance
from src.extraction.llm.coderepos.provider_input import WAVE_C_PROJECTION_VERSION as PROJECTION_VERSION
from src.extraction.llm.datasets.source_units import AbstractSourceUnit
from src.extraction.llm.publications import full_corpus_gpt61_batch as batch
from src.extraction.llm.publications import production_acceptance as attempts
from src.extraction.llm.publications.batch_journal import batch_journal
from src.extraction.llm.publications.resumable_production_journal import require
from src.extraction.llm.pilot_preflight import canonical, digest


def pack_inputs(inputs: dict) -> dict:
    """Serialize the accepted HydroShare dataclass without losing its exact fields."""
    result = deepcopy(inputs)
    for row in result.get('abstract_results', []):
        if isinstance(row.get('unit'), AbstractSourceUnit):
            row['unit'] = asdict(row['unit'])
    return result


def unpack_inputs(inputs: dict) -> dict:
    """Restore only the known, trusted abstract-unit slot for native replay."""
    result = deepcopy(inputs)
    for row in result.get('abstract_results', []):
        if isinstance(row.get('unit'), dict):
            row['unit'] = AbstractSourceUnit(**row['unit'])
    return result


def prepare(request: dict, inputs: dict) -> dict:
    """Pin the accepted semantic request separately from the new model envelope."""
    if request['request'].get('contractID') == 'study2-source-local-semantics/0.4.0':
        from src.extraction.llm.source_local_semantics import prepare_request
        return prepare_request(request, inputs)
    family = request['request']['artifactFamily']
    require(family in conformance.DIRECTORIES, 'UNSUPPORTED_FAMILY')
    require(request['request']['schemaVersion'] == family + '-request/1.2.0', 'PROMPT_VERSION_DRIFT')
    preflight = conformance.build_conformant_preflight(
        request, schema_version=conformance.SCHEMA_VERSION,
        projection_version=PROJECTION_VERSION if family == 'github' else None)
    body = deepcopy(preflight['envelope'])
    body['model'] = 'gpt-6.1-sol'
    require(body['reasoning'] == {'effort': 'medium'} and body['store'] is False
            and 'tools' not in body and body['max_output_tokens'] == 32768
            and body['text']['format']['strict'] is True, 'ENVELOPE_DRIFT')
    rid = family + ':' + request['requestSha256']
    return dict(request={'requestID': rid}, semanticRequest=request,
                requestInputs=pack_inputs(inputs), body=body,
                binding=dict(providerEnvelopeSha256=digest(canonical(body)),
                             providerInputSha256=preflight['providerInputSha256'],
                             schemaSha256=preflight['schemaSha256'],
                             modelSha256=digest(canonical({'model': body['model']})),
                             sourceSha256=digest(canonical(request['request']['sourceUnits'])),
                             conformanceVersion=conformance.VERSION,
                             schemaVersion=conformance.SCHEMA_VERSION))


def fingerprint(p: dict) -> dict:
    """Bind source, replay inputs, semantic request and exact provider envelope."""
    return dict(requestID=p['request']['requestID'],
                requestSha256=p['semanticRequest']['requestSha256'],
                bodySha256=digest(canonical(p['body'])),
                replayInputsSha256=digest(canonical(p['requestInputs'])),
                bindingSha256=digest(canonical(p['binding'])))


def verify_prepared(p: dict, entry: dict) -> None:
    """Rebuild the accepted envelope; never infer provenance from model output."""
    require(fingerprint(p) == entry['identity'], 'REQUEST_IDENTITY_DRIFT')
    require(p == prepare(p['semanticRequest'], unpack_inputs(p['requestInputs'])), 'PREPARED_DRIFT')


def process(p: dict, receipt: dict, number: int, first: dict | None = None,
            *, compatibility: bool = False) -> dict:
    """Project exact recorded output and reuse the existing bounded retry controller."""
    body, row = receipt['providerResponse'], receipt['row']
    code, report = None, None
    if receipt['cost']['estimatedUSD'] is None:
        return dict(processable=False, retryEligible=False, transportHold='UNKNOWN_USAGE',
                    attempt=None, productionResult=None)
    if body is None:
        require((row.get('error') or {}).get('code') == 'batch_expired', 'UNRESOLVED_BATCH_ERROR')
        code = 'API_ERROR'
    elif body.get('model') != 'gpt-6.1-sol' or body.get('service_tier') not in ('default', 'batch'):
        return dict(processable=False, retryEligible=False, transportHold='MODEL_OR_TIER_DRIFT',
                    attempt=None, productionResult=None)
    elif receipt.get('metadataError'):
        return dict(processable=False, retryEligible=False, transportHold=receipt['metadataError'],
                    attempt=None, productionResult=None)
    elif (row.get('response') or {}).get('status_code') != 200 or row.get('error'):
        code = 'API_ERROR'
    elif body.get('status') == 'incomplete':
        code = 'TOKEN_LIMIT' if (body.get('incomplete_details') or {}).get('reason') == 'max_output_tokens' else None
    elif body.get('status') == 'completed' and receipt.get('rawModelOutputBase64') is not None:
        raw = base64.b64decode(receipt['rawModelOutputBase64'], validate=True)
        if p['binding'].get('version') == 'study2-source-local-semantics/0.4.0':
            from src.extraction.llm.source_local_semantics import replay
            report = replay(p, raw, expected_request_sha256=p['semanticRequest']['requestSha256'])
        else:
            sealed = acceptance.replay_and_project(raw,
                family=p['semanticRequest']['request']['artifactFamily'],
                request_inputs=unpack_inputs(p['requestInputs']),
                expected_request_sha256=p['semanticRequest']['requestSha256'],
                conformance_version=conformance.VERSION, schema_version=conformance.SCHEMA_VERSION)
            report = sealed.to_record()
        reasons = report['originalReplay']['parseResult']['diagnostics']
        if any(r.get('reason') == 'response_invalid_json' for r in reasons):
            code = 'INVALID_JSON'
    processable = report is not None and report['status'] == 'projection_completed'
    policy_id, policy_path = acceptance.POLICY_ID, acceptance.POLICY_PATH
    if p['binding'].get('version') == 'study2-source-local-semantics/0.4.0':
        from src.extraction.llm.source_local_profile import VERSION, POLICY_PATH
        policy_id, policy_path = VERSION, POLICY_PATH
    attempt = dict(attemptNumber=number, requestInputSha256=p['semanticRequest']['requestSha256'],
        providerInputSha256=p['binding']['providerInputSha256'], authorityBundleID=policy_id,
        requestedModel='gpt-6.1-sol', reasoningEffort='medium', maxOutputTokens=32768,
        modelAuthorableSchemaSha256=p['binding']['schemaSha256'], provider='openai',
        toolConfiguration='none', store=False,
        parserResult=dict(parseStatus='parsed' if processable else 'processing_failed', processingCode=code))

    class DeferredRetry(Exception):
        """A native retry decision is journaled before a later Batch dispatch."""

    def recorded(n: int) -> dict:
        """Supply existing attempt records, never invoke a provider during replay."""
        if n == number:
            return attempt
        if n == 1 and first is not None:
            return first
        raise DeferredRetry()

    retry, selection = False, None
    try:
        selection = attempts.run_attempt_controller(recorded)
    except DeferredRetry:
        require(number == 1, 'RETRY_STATE_DRIFT')
        retry = not compatibility
    return dict(processable=processable, retryEligible=retry, attempt=attempt,
                attemptSelection=selection, productionResult=report,
                productionResultSha256=digest(canonical(report)) if report is not None else None,
                provenance=dict(identity=fingerprint(p), responseSha256=digest(canonical(receipt)),
                                policySha256=digest(policy_path.read_bytes())))


def infrastructure() -> tuple[Any, Any, dict]:
    """Reuse the verified existing local journal and cost adapter without their runners."""
    paired, stream, native, _ = batch.baseline.dependencies()
    adapter = SimpleNamespace(Journal=native.Journal, decode=native.decode,
                              bundle=deepcopy, unbundle=deepcopy)
    return paired, adapter, stream.versions()


def journal_type(paired: Any, native: Any, *, compatibility: bool = False) -> type:
    """Bind shared durable state transitions to these families' exact native records."""
    def verify_receipt(p: dict, receipt: dict) -> None:
        """Recompute usage/metadata from the preserved authentic result wrapper."""
        require(receipt == batch.response_record(receipt['row'], p, paired,
                receipt['batchID'], receipt['number']), 'RECEIPT_DRIFT')

    def verify_outcome(p: dict, receipt: dict, outcome: dict, n: int) -> None:
        """Verify native projection and lineage without repeating provider work."""
        # Attempt two's selection includes the first recorded attempt; its full
        # immutable-identity comparison was performed before appending the outcome.
        first = None
        selection = outcome.get('attemptSelection')
        if n == 2 and selection:
            first = selection['attempts'][0]
        require(outcome == process(p, receipt, n, first, compatibility=compatibility), 'OUTCOME_DRIFT')

    return batch_journal(native, verify_prepared, fingerprint, verify_outcome, verify_receipt)
