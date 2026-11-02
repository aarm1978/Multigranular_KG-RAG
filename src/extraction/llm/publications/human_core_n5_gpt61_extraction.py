"""Isolated model-only repeat of the five corrected Pilot 1 Human Core requests.

Default execution verifies offline. Only --execute-live dispatches, from the
researcher's terminal. Historical files are never rewritten; no scoring is run.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import datetime
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from types import SimpleNamespace
from typing import Any, Iterator, Mapping
from unittest.mock import patch

from . import candidate_validation as validator
from . import openai_provider as provider
from . import pilot1_evaluation_execution_runner as historical
from . import production_runner as production
from . import publication_semantic_pipeline as pipeline
from .request_builder import PROJECT_ROOT as ROOT, canonical_json, sha256_bytes

MODEL = 'gpt-6.1-sol'
ONTOLOGY_REVISION = '227f53eca9e6e4f487de06219bf954464ec07ccc'
ONTOLOGY_SHA = 'eac8ec2e0eeec380d05e75c804dc386e9e8aaf8f443b79e20a25a163e513efc5'
LOCAL = ROOT / 'var/publication_human_core_n5_gpt61_extraction_v1'
OUTPUT = ROOT / 'data/curation/papers/m2/publication_human_core_n5_gpt61_extraction'
STREAM_SOURCE = ROOT / 'var/study2_step13/publication-paired-gpt61-streaming/v0.1/recover.py'
UNITS = ('pub:10:sec:0008:unit:0001', 'pub:15:sec:0004:unit:0001',
         'pub:16:sec:0033:unit:0001', 'pub:34:sec:0015:unit:0001',
         'pub:79:sec:0004:unit:0001')


def require(condition: bool, message: str) -> None:
    """Stop without repairing a failed identity or uncertain transport."""
    if not condition:
        raise ValueError(message)


def read(path: Path) -> Any:
    """Read a JSON artifact."""
    return json.loads(path.read_bytes())


def save(path: Path, value: Mapping[str, Any]) -> None:
    """Use the original runner's durable immutable writer."""
    historical._write_immutable(path, value)


def records() -> list[dict[str, Any]]:
    """Select exactly the historical cohort from its verified parent scope."""
    subset, _ = historical.load_frozen_execution_scope()
    require(subset['artifactSha256'] == 'd47d0c592a67c39cb7059d2b9e1cf68844a4f7126527bc5abb3a342446497f94', 'SUBSET_DRIFT')
    rows = [r for r in subset['requests'] if r['executionCohort'] == 'human_core_n5']
    require(tuple(r['primarySourceUnitID'] for r in rows) == UNITS, 'N5_SCOPE_DRIFT')
    return rows


def ontology_bytes() -> bytes:
    """Recover exact frozen v0.1.5 bytes without changing the working ontology."""
    raw = subprocess.check_output(['git', 'show', ONTOLOGY_REVISION + ':src/ontology/ontology_spec.yaml'], cwd=ROOT)
    require(sha256_bytes(raw) == ONTOLOGY_SHA, 'HISTORICAL_ONTOLOGY_DRIFT')
    return raw


def rebuild(record: Mapping[str, Any]) -> dict[str, Any]:
    """Run the original builder and ALL original gates with historical provenance."""
    ontology_bytes()
    original = production._authority

    def authority(profile: Mapping[str, Any]) -> dict[str, Any]:
        """Bind the verified historical ontology digest in the original authority map."""
        value = original(profile)
        value['ontology']['specSha256'] = ONTOLOGY_SHA
        return value

    with patch.object(production, '_authority', authority):
        prepared = historical.prepare_verified_request(record)
    old = read(historical.DEFAULT_LIVE_ROOT / 'requests' / record['requestID'] / 'attempt-01/provider_request.json')
    require(prepared['body'] == old, 'AUTHENTIC_OUTGOING_BODY_DRIFT')
    result = deepcopy(prepared)
    result['body'].update(model=MODEL, stream=True)
    expected = deepcopy(old)
    expected.update(model=MODEL, stream=True)
    require(result['body'] == expected, 'MODEL_ONLY_VARIANT_DRIFT')
    return result


def file_pins(paths: list[Path]) -> dict[str, str]:
    """Hash bytes only; do not rerun historical annotation or evaluation audits."""
    files = set()
    for path in paths:
        if path.is_dir():
            files.update(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        else:
            files.add(path)
    return {str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes()) for p in sorted(files)}


def preserved_pins() -> dict[str, str]:
    """Protect historical curation and original journals by exact byte inventory."""
    m2 = ROOT / 'data/curation/papers/m2'
    paths = [p for p in m2.iterdir() if p != OUTPUT]
    paths += [historical.DEFAULT_LIVE_ROOT, ROOT / 'data/curation/papers/pilot1']
    return file_pins(paths)


def verify_pins(pins: Mapping[str, str]) -> None:
    """Fail closed when any pinned input changes or disappears."""
    for relative, digest in pins.items():
        require(sha256_bytes((ROOT / relative).read_bytes()) == digest, 'PIN_DRIFT:' + relative)


def prepare() -> dict[str, Any]:
    """Materialize only isolated offline bindings and a historical ontology snapshot."""
    require(subprocess.run(['git', 'check-ignore', '-q', str(LOCAL)], cwd=ROOT).returncode == 0, 'LOCAL_NOT_IGNORED')
    rows = records()
    prepared = [rebuild(r) for r in rows]
    LOCAL.mkdir(parents=True, exist_ok=True)
    ont = LOCAL / 'ontology_v0.1.5.yaml'
    raw = ontology_bytes()
    if ont.exists():
        require(ont.read_bytes() == raw, 'SNAPSHOT_CONFLICT')
    else:
        with ont.open('xb') as handle:
            handle.write(raw)
    preserved = preserved_pins()
    save(LOCAL / 'preservation.json', preserved)
    dependencies = file_pins([ROOT / 'src/extraction/llm/publications', STREAM_SOURCE, ont])
    # Source inputs and authority files must remain exact before terminal dispatch.
    for p in prepared:
        for unit in [p['request']['sourceUnit'], *p['request']['contextUnits']]:
            source = ROOT / unit['sourceFile']
            dependencies[str(source.relative_to(ROOT))] = sha256_bytes(source.read_bytes())
        for value in p['request']['authorities'].values():
            if isinstance(value, dict) and 'path' in value:
                path = ROOT / value['path']
                dependencies[str(path.relative_to(ROOT))] = sha256_bytes(path.read_bytes())
    save(LOCAL / 'dependencies.json', dependencies)
    usage = [read(historical.DEFAULT_LIVE_ROOT / 'requests' / r['requestID'] / 'attempt-01/provider_metadata.json') for r in rows]
    inputs = sum(x['inputTokens'] for x in usage)
    outputs = sum(x['outputTokens'] for x in usage)
    manifest = {
        'version': 'human-core-n5-gpt61-extraction/1.0.0', 'providerModelCallsDuringPreparation': 0,
        'model': MODEL, 'reasoning': 'medium', 'maxOutputTokens': 32768, 'store': False, 'stream': True,
        'ontologyRevision': ONTOLOGY_REVISION, 'ontologySha256': ONTOLOGY_SHA,
        'preservationSha256': sha256_bytes(canonical_json(preserved)),
        'dependencySha256': sha256_bytes(canonical_json(dependencies)),
        'requests': [{**r, 'gpt61ProviderBodySha256': sha256_bytes(canonical_json(p['body'])),
                      'providerInputSha256': sha256_bytes(p['providerInput'])} for r, p in zip(rows, prepared)],
        'costEstimate': {'historicalInputTokens': inputs, 'historicalOutputTokens': outputs,
                         'inputUSDPerMillion': 2, 'outputUSDPerMillion': 10,
                         'historicalUsageEstimateUSD': (inputs * 2 + outputs * 10) / 1e6,
                         'fiveOutputCapsEstimateUSD': (inputs * 2 + 5 * 32768 * 10) / 1e6,
                         'assumption': 'Standard short-context uncached input; historical tokenization proxy; excludes regional/cache-write premiums; not a billing cap',
                         'pricingSource': 'https://developers.openai.com/api/docs/models/gpt-6.1-sol'},
        'executionPolicy': 'one dispatch per identity; STOP on requested retry, partial response, or uncertain state; resume completed immutable results only',
        'evaluationPerformed': False,
    }
    save(OUTPUT / 'extraction_manifest.json', manifest)
    return manifest


def verify() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify all five reconstructions, frozen preservation and executable pins offline."""
    manifest = read(OUTPUT / 'extraction_manifest.json')
    for name, field in [('preservation', 'preservationSha256'), ('dependencies', 'dependencySha256')]:
        pins = read(LOCAL / (name + '.json'))
        require(sha256_bytes(canonical_json(pins)) == manifest[field], 'BINDING_DRIFT')
        verify_pins(pins)
    require(preserved_pins() == read(LOCAL / 'preservation.json'), 'HISTORICAL_FILE_INVENTORY_DRIFT')
    rows = records()
    require(len(manifest['requests']) == 5, 'MANIFEST_SCOPE_DRIFT')
    prepared = []
    for row, entry in zip(rows, manifest['requests']):
        require(all(entry[k] == v for k, v in row.items()), 'HISTORICAL_RECORD_DRIFT')
        p = rebuild(row)
        require(sha256_bytes(canonical_json(p['body'])) == entry['gpt61ProviderBodySha256'], 'BODY_DRIFT')
        require(sha256_bytes(p['providerInput']) == entry['providerInputSha256'], 'INPUT_DRIFT')
        prepared.append(p)
    return manifest, prepared


def streaming_adapter() -> SimpleNamespace:
    """Reuse exact proven SSE functions, without importing the compact-profile runner.

    AST selection includes only standalone transport helpers; their source file is
    pinned by the execution manifest. No full-corpus builder or routing is imported.
    """
    tree = ast.parse(STREAM_SOURCE.read_text())
    names = {'stamp', 'unique', 'consume', 'transport'}
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    require({n.name for n in functions} == names, 'STREAM_HELPERS_MISSING')
    namespace = dict(datetime=datetime, time=time, socket=socket, json=json, require=require,
                     a=SimpleNamespace(sha=sha256_bytes, canonical_json=canonical_json))
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(STREAM_SOURCE), 'exec'), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in names})


class Journal:
    """Durably retain original SSE transport observations in the isolated local area."""

    def __init__(self, path: Path) -> None:
        """Bind one request's journal."""
        self.path = path

    def append(self, event: str, request_id: str, payload: Mapping[str, Any]) -> None:
        """Flush each authentic transport observation before proceeding."""
        with self.path.open('ab') as handle:
            handle.write(canonical_json({'event': event, 'requestID': request_id, 'payload': payload}) + b'\n')
            handle.flush()
            os.fsync(handle.fileno())


@contextmanager
def technical_context() -> Iterator[None]:
    """Bind historical ontology and truthful new model metadata only within this run."""
    with ExitStack() as stack:
        stack.enter_context(patch.object(validator, 'ONTOLOGY_SPEC_PATH', LOCAL / 'ontology_v0.1.5.yaml'))
        for module in (production, pipeline, provider):
            stack.enter_context(patch.object(module, 'REQUESTED_MODEL', MODEL))
        yield


def execute_one(p: Mapping[str, Any], folder: Path, call: Any) -> dict[str, Any]:
    """Reuse original parser/validator/acceptance; refuse any sixth/retry dispatch."""
    count = 0

    def once(body: Mapping[str, Any], budget: int) -> Any:
        """Allow one exact dispatch, leaving the original acceptance policy intact."""
        nonlocal count
        require(count == 0, 'RETRY_REQUIRES_SEPARATE_RESEARCHER_DECISION')
        require(body == p['body'] and budget == 32768, 'DISPATCH_DRIFT')
        count += 1
        return call(body, budget)

    with technical_context():
        return production.execute_with_provider_fixture(p, once, artifact_root=folder)


def execute_live() -> None:
    """Researcher terminal only: five bounded requests with no automatic retries."""
    with (LOCAL / 'writer.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_VERIFICATION')):
            manifest, prepared = verify()
        transport = streaming_adapter()
        key = None
        for p in prepared:
            rid = p['request']['requestID']
            folder = LOCAL / 'requests' / rid
            result_path = OUTPUT / (rid + '.json')
            if result_path.exists():
                result = read(result_path)
                verify_pins(result['localArtifactPins'])
                require(result['manifestSha256'] == sha256_bytes(canonical_json(manifest)), 'RESULT_BINDING_DRIFT')
                require(production._terminal_request(folder), 'TERMINAL_RESULT_MISSING')
                continue
            require(not folder.exists(), 'UNCERTAIN_OR_UNEXPORTED_REQUEST_STOP:' + rid)
            verify_pins(read(LOCAL / 'preservation.json'))
            verify_pins(read(LOCAL / 'dependencies.json'))
            if key is None:
                key = provider.load_openai_api_key()
            folder.mkdir(parents=True)
            log = Journal(folder / 'stream.jsonl')

            def call(body: Mapping[str, Any], budget: int) -> dict[str, Any]:
                """Retain authentic response before provider validation or parsing."""
                response = transport.transport(provider, log, rid, key, body)
                save(folder / 'authentic_provider_response.json', response)
                provider.validate_provider_response(response)
                raw = provider.extract_model_output(response)
                metadata = provider.provider_response_record(response, body, raw, execution_mode='streaming')
                return dict(rawOutput=raw, providerMetadata=metadata, providerResponse=response)

            result = execute_one(p, folder, call)
            save(result_path, {'historicalRequestID': rid, 'model': MODEL,
                              'manifestSha256': sha256_bytes(canonical_json(manifest)),
                              'technicalResult': result, 'localArtifactPins': file_pins([folder]),
                              'evaluationPerformed': False})
            print('TECHNICALLY PROCESSED', rid, flush=True)
        verify_pins(read(LOCAL / 'preservation.json'))


def main() -> None:
    """Default offline verification; never load credentials except explicit live mode."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--execute-live', action='store_true')
    args = parser.parse_args()
    if args.execute_live:
        execute_live()
    else:
        with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_NO_NETWORK')):
            manifest = prepare() if args.prepare else verify()[0]
        print(json.dumps({'verifiedRequests': len(manifest['requests']), 'providerCalls': 0,
                          'costEstimate': manifest['costEstimate']}, indent=2))


if __name__ == '__main__':
    main()
