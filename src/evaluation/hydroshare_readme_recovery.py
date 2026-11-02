"""Prospective HydroShare-only README recovery; offline preparation/status by default.

Only --submit/--collect are researcher-terminal provider modes. Original queues,
bindings and journals are read-only. No historical acquisition attestation is
created. Each successor keeps the complete abstract and every snapshot README.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import io
import json
from pathlib import Path
import socket
import subprocess
import tempfile
from typing import Any, Iterator
from unittest.mock import patch

from src.extraction.llm import source_family_batch as adapter
from src.extraction.llm import source_family_queue as packaging
from src.extraction.llm.datasets.source_units import read_readme_source_units
from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.publications.resumable_production_journal import require
from src.evaluation import source_family_production_verification as verification

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = Path('var/study2_step13/source-families-gpt61-batch/v1')
DEFAULT_ROOT = Path('var/study2_step13/hydroshare-readme-recovery/v2')
SOURCE = 'data/interim/datasets/ciroh_hydroshare_corpus.json'
NOTEBOOK = 'notebooks/exploration/datasets/HydroShareTest.ipynb'
ORIGINAL_PINS = {
    str(ORIGINAL / 'queue-manifest.json'): '3a25faa87329a5d6462a3546c10dc377b1a26c67299cdab9961fbac5826f4df6',
    str(ORIGINAL / 'production/run-manifest.json'): 'b9c5fb6accb4068442acca998a3627f182e48f5c43bb810fb7279e64a94a602f',
    SOURCE: '51453913c034c49c1751db1f111ebdc7d2c87e4cd6f8ce8573aee29d91338992',
    NOTEBOOK: 'b3df9deae863afe04ab9eb7546d042b0a98d00c9c370de2d974e2777b686739b',
}
VERSION = 'hydroshare-readme-recovery/1.0'
READ_POLICY = 'open(path, "r", encoding="utf-8", errors="replace"); newline=None'


@contextmanager
def offline() -> Iterator[None]:
    """Disallow all sockets during source preparation and local verification."""
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_ONLY')):
        yield


def read_json(path: Path) -> Any:
    """Reuse strict duplicate-key rejection without executing a provider client."""
    return adapter.batch.batch_transport.decode(path.read_bytes())


def check_pins(pins: dict, repo: Path = ROOT) -> None:
    """Check only explicitly pinned artifacts; never rebuild historical requests."""
    for relative, sha in pins.items():
        path = (repo / relative).resolve()
        require(path.is_relative_to(repo.resolve()), 'PIN_OUTSIDE_REPOSITORY')
        require(verification.file_hash(path) == sha, 'PIN_DRIFT:' + relative)


def implementation_pins(repo: Path = ROOT) -> dict:
    """Pin this overlay and its unchanged HydroShare/shared execution dependencies."""
    paths = [Path(__file__), repo / 'src/evaluation/source_family_production_verification.py']
    paths.extend((repo / 'src/extraction/llm/datasets').glob('*.py'))
    names = ('source_family_batch.py', 'source_family_queue.py', 'pilot_preflight.py',
             'format_conformance.py', 'format_conformance_core.py', 'construction_acceptance.py',
             'semantic_target_profiles.py')
    paths.extend(repo / 'src/extraction/llm' / name for name in names if (repo / 'src/extraction/llm' / name).exists())
    paths.extend(repo / 'src/extraction/llm/publications' / name for name in
        ('batch_journal.py', 'resumable_production_journal.py', 'batch_transport.py', 'full_corpus_gpt61_batch.py',
         'full_corpus_gpt61_production.py', 'production_acceptance.py', 'openai_provider.py',
         'request_builder.py', 'deterministic_evidence_binding.py'))
    paths.extend(repo / name for name in ('src/ontology/ontology_spec.yaml',
        'docs/study2_step11_source_specific_semantic_contracts_v0.3.md',
        'docs/study2_step11_format_conformance_amendment_v1.0.0.md',
        'docs/handoffs/STUDY2_STEP12_COMPLETION_ACCEPTANCE.md',
        'docs/handoffs/STUDY2_STEP13_1_OFFLINE_IMPLEMENTATION_ACCEPTANCE.md',
        'docs/study2_step13_construction_acceptance_policy_v0.1.md'))
    return {str(p.relative_to(repo)): verification.file_hash(p) for p in sorted(set(paths))}


def physical_comparison(readme: dict, owner: str, repo: Path = ROOT) -> dict:
    """Compare exact notebook-decoded text, keeping byte and text hashes distinct."""
    name, text = readme['source_file'], readme['readme_text_raw']
    require(isinstance(name, str) and Path(name).name == name and name not in ('.', '..'), 'UNSAFE_README_PATH')
    require(isinstance(text, str) and bool(text.strip()), 'NONEMPTY_README_REQUIRED')
    require(readme['readme_char_count'] == len(text), 'SNAPSHOT_CHARACTER_COUNT_DRIFT')
    relative = Path('data/raw/datasets') / owner / name
    path = repo / relative
    require(path.resolve().is_relative_to((repo / 'data/raw/datasets' / owner).resolve()), 'UNSAFE_PHYSICAL_PATH')
    result = dict(physicalPath=relative.as_posix(), readPolicy=READ_POLICY,
        snapshotCharacters=len(text), snapshotTextSha256=digest(text.encode()),
        physicalBytesSha256=None, physicalByteCount=None, decodedTextSha256=None, decodedCharacters=None,
        acquisitionIntegrityStatus='not_independently_verified')
    if not path.exists():
        require(not path.is_symlink(), 'BROKEN_PHYSICAL_SYMLINK')
        return {**result, 'comparison': 'physical_file_absent', 'historicalAcquisitionVerified': False}
    require(path.is_file(), 'PHYSICAL_README_NOT_FILE')
    raw = path.read_bytes()
    with io.TextIOWrapper(io.BytesIO(raw), encoding='utf-8', errors='replace', newline=None) as handle:
        decoded = handle.read()
    require(decoded == text and len(decoded) == readme['readme_char_count'], 'PHYSICAL_SNAPSHOT_MISMATCH:' + str(relative))
    result.update(comparison='exact_decoded_text_match', physicalBytesSha256=digest(raw),
        physicalByteCount=len(raw), decodedTextSha256=digest(decoded.encode()), decodedCharacters=len(decoded),
        crlfCount=raw.count(b'\r\n'), loneCRCount=raw.count(b'\r') - raw.count(b'\r\n'),
        replacementCharacterCount=decoded.count('\ufffd'), historicalAcquisitionVerified=False)
    return result


def reader_from_binding(readme: dict, owner: str, provenance: dict, binding: dict) -> dict:
    """Apply only an exact prospective binding using unchanged native evidence IDs."""
    require(binding['ownerID'] == owner and binding['source_path'] == readme['source_file'] and
            binding['snapshotID'] == provenance['snapshotID'] and
            binding['sourceVersion'] == provenance.get('sourceVersion') and
            binding['authorityTextSha256'] == digest(readme['readme_text_raw'].encode()) and
            binding['characters'] == len(readme['readme_text_raw']) and
            binding['attestationScope'] == 'prospective_recovery_only' and
            binding['sourceVerification'] == 'caller_attested' and
            binding['acquisitionIntegrityStatus'] == 'not_independently_verified', 'RECOVERY_BINDING_DRIFT')
    result = read_readme_source_units(dict(resource_id=owner, source_path=readme['source_file'],
        text=readme['readme_text_raw']), accepted_owner_id=owner,
        provenance={**provenance, 'sourceVerified': True},
        expected_authority_text_sha256=binding['authorityTextSha256'])
    require(result['status'] == 'source_read_success' and result['inputComplete'] and
            len(result['sourceUnits']) == 1, 'RECOVERY_READ_FAILED')
    require(result['sourceUnits'][0]['sourceUnitID'] == binding['sourceUnitID'], 'SOURCE_UNIT_ID_DRIFT')
    return result


def make_binding(readme: dict, source: dict, provenance: dict, repo: Path = ROOT) -> dict:
    """Pin a new attestation without relabeling an old source verification decision."""
    owner = source['resource_id']
    text = readme['readme_text_raw']
    comparison = physical_comparison(readme, owner, repo)
    native = read_readme_source_units(dict(resource_id=owner, source_path=readme['source_file'], text=text),
        accepted_owner_id=owner, provenance={**provenance, 'sourceVerified': True},
        expected_authority_text_sha256=digest(text.encode()))
    require(len(native['sourceUnits']) == 1, 'EXPECTED_FULL_README_UNIT')
    return dict(ownerID=owner, source_path=readme['source_file'], snapshotID=provenance['snapshotID'],
        sourceVersion=provenance.get('sourceVersion'), authorityTextSha256=digest(text.encode()), characters=len(text),
        sourceUnitID=native['sourceUnits'][0]['sourceUnitID'], attestationScope='prospective_recovery_only',
        sourceVerification='caller_attested', acquisitionIntegrityStatus='not_independently_verified',
        physicalComparison=comparison)


def discover(repo: Path = ROOT) -> tuple[dict, dict, dict, list, dict]:
    """Read the 42 sealed HydroShare bundles; identify exactly the original omissions."""
    check_pins(ORIGINAL_PINS, repo)
    parent = read_json(repo / ORIGINAL / 'queue-manifest.json')
    run = read_json(repo / ORIGINAL / 'production/run-manifest.json')
    require(digest(canonical(parent)) == run['parentSha256'] and parent['requests'] == run['requests'], 'ORIGINAL_QUEUE_DRIFT')
    entries = [e for e in parent['requests'] if e['family'] == 'hydroshare']
    require(len(entries) == 42 and len({e['ownerID'] for e in entries}) == 42, 'ORIGINAL_HYDROSHARE_COUNT_DRIFT')
    status_path = repo / ORIGINAL / 'production/status.json'
    stored_status = read_json(status_path)
    require(digest(adapter.batch.canonical_json(stored_status['summary'])) == stored_status['sha256'], 'ORIGINAL_STATUS_HASH_DRIFT')
    hs_status = stored_status['summary']['families']['hydroshare']
    require(hs_status['requests'] == hs_status['completed'] == 42 and hs_status['failed'] == 0, 'ORIGINAL_COMPLETION_STATUS_DRIFT')
    sources = {r['resource_id']: r for r in read_json(repo / SOURCE)}
    coverage = {o['ownerID']: o for o in parent['coverage'] if o['family'] == 'hydroshare'}
    require(set(coverage) == {e['ownerID'] for e in entries}, 'ORIGINAL_OWNER_COVERAGE_DRIFT')
    affected, bindings, pins = [], [], dict(ORIGINAL_PINS)
    for relative in (ORIGINAL / 'production/status.json', ORIGINAL / 'production/head.json'):
        pins[relative.as_posix()] = verification.file_hash(repo / relative)
    for entry in entries:
        owner = entry['ownerID']
        bundle_path = ORIGINAL / 'queue' / entry['bundleFile']
        require(Path(entry['bundleFile']).name == entry['bundleFile'], 'UNSAFE_BUNDLE_PATH')
        pins[bundle_path.as_posix()] = entry['bundleSha256']
        check_pins({bundle_path.as_posix(): entry['bundleSha256']}, repo)
        original = read_json(repo / bundle_path)
        verification.checked_prepared(original, entry)  # stored associations only; no reconstruction
        source, cov = sources[owner], coverage[owner]
        require(digest(canonical(source)) == cov['sourceRecordSha256'] == entry['coverage']['sourceRecordSha256'],
                'ORIGINAL_SOURCE_RECORD_DRIFT')
        readmes = source['documentation']['readme_files']
        require(len({r['source_file'] for r in readmes}) == len(readmes), 'DUPLICATE_README_PATH')
        admitted = {u['source_path'] for u in original['semanticRequest']['request']['sourceUnits'] if u['sourceField'] == 'README'}
        missing = [r for r in readmes if r['readme_text_raw'].strip() and r['source_file'] not in admitted]
        omitted_paths = {d['source_path'] for d in cov['diagnostics'] if d.get('reason') == 'readme_source_not_verified'}
        require({r['source_file'] for r in missing} == omitted_paths, 'OMISSION_DIAGNOSTICS_DRIFT')
        if not missing:
            continue
        require(not admitted and len(missing) == len(readmes), 'UNEXPECTED_MIXED_OWNER_REQUIRES_REVIEW')
        provenance = original['requestInputs']['trusted_provenance']
        require(provenance == dict(snapshotID='sha256:' + ORIGINAL_PINS[SOURCE],
                sourceVersion=source.get('system_metadata', {}).get('date_last_updated')), 'SOURCE_VERSION_DRIFT')
        rows = [make_binding(r, source, provenance, repo) for r in readmes]
        bindings.extend(rows)
        affected.append(dict(ownerID=owner, source=source, original=original, entry=entry, coverage=cov, bindings=rows))
    require(len(affected) == 20 and len(bindings) == 21, 'EXPECTED_20_OWNERS_21_READMES')
    require([r['ownerID'] for r in affected if len(r['bindings']) == 2] == ['7477452a93e04b1099a3879353c2253a'],
            'DUAL_README_OWNER_DRIFT')
    overlay = dict(version=VERSION, sourcePath=SOURCE, sourceSha256=ORIGINAL_PINS[SOURCE],
        notebookPath=NOTEBOOK, notebookSha256=ORIGINAL_PINS[NOTEBOOK], readPolicy=READ_POLICY,
        attestationScope='prospective_recovery_only', authorization='researcher-directed Step 13 HydroShare README recovery',
        historicalBindingsUnchanged=True, historicalAcquisitionVerified=False, bindings=bindings,
        originalProductionCheckpoint=dict(hydroshareStatus=hs_status,
            head=read_json(repo / ORIGINAL / 'production/head.json'),
            journalBytes=(repo / ORIGINAL / 'production/execution.jsonl').stat().st_size,
            verificationScope='persisted checkpoint references; original journal not replayed'))
    return parent, run, overlay, affected, pins


def successor(item: dict, overlay_sha: str) -> tuple[dict, dict]:
    """Build one whole-owner successor using original abstract/catalog and new README bindings."""
    original, source = item['original'], item['source']
    inputs = adapter.unpack_inputs(original['requestInputs'])
    before = deepcopy(inputs)
    provenance = inputs['trusted_provenance']
    inputs['readme_results'] = [reader_from_binding(r, item['ownerID'], provenance, b)
        for r, b in zip(source['documentation']['readme_files'], item['bindings'])]
    require(len(inputs['readme_results']) == len(item['bindings']) == len(source['documentation']['readme_files']),
            'README_COVERAGE_GAP')
    abstract_units = [r['unit'].to_record() for r in inputs['abstract_results'] if r.get('unit') is not None]
    require(len(abstract_units) == 1 and abstract_units[0]['text'] == source['abstract'], 'FULL_ABSTRACT_REQUIRED')
    original_units = original['semanticRequest']['request']['sourceUnits']
    require(abstract_units == [u for u in original_units if u['sourceField'] == 'abstract'], 'ABSTRACT_IDENTITY_DRIFT')
    units = abstract_units + [u for r in inputs['readme_results'] for u in r['sourceUnits']]
    inputs['input_complete'] = all(r['inputComplete'] for r in inputs['abstract_results'] + inputs['readme_results'])
    require(inputs['input_complete'], 'RECOVERY_SOURCE_INCOMPLETE')
    owner = dict(family='hydroshare', ownerID=item['ownerID'], inputs=inputs, units=units,
        sourceRecordSha256=item['coverage']['sourceRecordSha256'],
        endpointRecordSha256=item['coverage']['endpointRecordSha256'])
    groups = list(packaging.requests(owner))
    require(len(groups) == 1 and groups[0][0] is not None, 'RECOVERY_SIZE_OR_REQUEST_HOLD:' + str(groups))
    prepared, coverage = groups[0]
    body = prepared['semanticRequest']['request']
    require(body['sourceUnits'] == units and body['selectedSourceUnitIDs'] == [u['sourceUnitID'] for u in units] and
            body['sourceCompleteness']['inputComplete'] and not coverage['exceptionalSplit'], 'FULL_CONTEXT_SELECTION_DRIFT')
    for name in ('accepted_endpoints', 'accepted_assertions', 'authorized_stubs', 'trusted_provenance', 'request_version'):
        require(inputs.get(name) == before.get(name), 'UNRELATED_SUCCESSOR_CHANGE:' + name)
    for name in ('instructions', 'promptIdentifier', 'responseContract', 'targetProfile', 'schemaVersion', 'owner'):
        require(body.get(name) == original['semanticRequest']['request'].get(name), 'SCIENTIFIC_POLICY_DRIFT:' + name)
    require(prepared['request']['requestID'] != original['request']['requestID'], 'SUCCESSOR_ID_COLLISION')
    lineage = dict(version=VERSION, overlaySha256=overlay_sha,
        originalRequestID=original['request']['requestID'], originalIdentity=item['entry']['identity'],
        originalBundleSha256=item['entry']['bundleSha256'], attestationScope='prospective_recovery_only')
    # Keep overlay lineage in the sealed entry, preserving the native bundle format.
    cost = packaging.costs(prepared)
    identity = adapter.fingerprint(prepared)
    entry = dict(identity=identity, family='hydroshare', ownerID=item['ownerID'], coverage=coverage,
        bundleFile=digest(canonical(identity)) + '.json', bundleSha256=digest(canonical(prepared) + b'\n'),
        estimatedCostUSD=cost['costUSD']['pooled'], cost=cost, recoveryProvenance=lineage,
        rawSourcePins={b['physicalComparison']['physicalPath']: b['physicalComparison']['physicalBytesSha256']
                       for b in item['bindings'] if b['physicalComparison']['physicalBytesSha256'] is not None})
    verification.checked_prepared(prepared, entry)
    return prepared, entry


def assert_isolated(folder: Path, repo: Path = ROOT) -> None:
    """All writes must stay in a new ignored recovery subtree, never an original root."""
    folder = folder.resolve()
    allowed = (repo / 'var/study2_step13/hydroshare-readme-recovery').resolve()
    require(allowed in folder.parents and folder != allowed, 'ISOLATED_RECOVERY_SUBDIRECTORY_REQUIRED')
    require(subprocess.run(['git', 'check-ignore', '-q', str(folder / 'queue-manifest.json')], cwd=repo).returncode == 0,
            'RECOVERY_MUST_BE_GIT_IGNORED')


def prepare(folder: Path) -> dict:
    """Seal the successor queue offline; allocate an empty isolated execution journal."""
    assert_isolated(folder)
    if folder.exists():
        return load_queue(folder, None)[0]['summary']
    parent, original_run, overlay, affected, historical_pins = discover()
    overlay_wire = canonical(overlay) + b'\n'
    overlay_sha = digest(overlay_wire)
    bundles = [successor(item, overlay_sha) for item in affected]
    requests = [entry for _, entry in bundles]
    ids = {e['identity']['requestID'] for e in requests}
    require(len(ids) == 20 and not ids & {e['identity']['requestID'] for e in parent['requests']}, 'REQUEST_ID_COLLISION')
    summary = dict(owners=20, addedReadmes=21, requests=len(requests), selectedUnits=sum(
        len(e['coverage']['selectedSourceUnitIDs']) for e in requests), sizeHolds=0,
        completeContexts=True, uniqueSuccessorRequests=True, historicalRequestsReconstructed=0,
        originalHydroShareBundlesInspected=42, physicalFilesMatched=sum(b['physicalComparison']['comparison'] ==
        'exact_decoded_text_match' for b in overlay['bindings']),
        physicalFilesAbsent=sum(b['physicalComparison']['comparison'] == 'physical_file_absent' for b in overlay['bindings']),
        byteAndTextHashesDiffer=sum(b['physicalComparison']['physicalBytesSha256'] not in (None, b['authorityTextSha256'])
                                  for b in overlay['bindings']),
        maxEnvelopeBytes=max(len(canonical(p['body'])) for p, _ in bundles),
        maxSelectedTextBytes=max(sum(len(u['text'].encode()) for u in p['semanticRequest']['request']['sourceUnits'])
                                 for p, _ in bundles),
        costUSD={scenario: sum(e['cost']['costUSD'][scenario] for e in requests)
                 for scenario in ('low', 'pooled', 'high', 'outputCeiling')},
        costBasis=packaging.costs(bundles[0][0])['basis'], providerCalls=0, offlineReady=True,
        livePrerequisites=['explicit researcher-terminal --submit', 'sealed queue SHA-256',
                           'operational token capacity'])
    manifest = dict(version=VERSION, artifactFamily='hydroshare', originalArtifactPins=historical_pins,
        bindingOverlaySha256=overlay_sha, implementationPins=implementation_pins(),
        generatorPins=original_run['generatorPins'], pricing=adapter.batch.PRICING,
        sizing=packaging.SIZING, requests=requests, summary=summary, kgAuthorization=False,
        originalOperationalQueueCapacity=original_run['queuedTokenLimit'],
        lineage='successor context recovery; original outcomes retained; no merging or supersession of assertions')
    check_pins(historical_pins)
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.prepare-', dir=folder.parent) as temporary:
        stage = Path(temporary)
        (stage / 'queue').mkdir()
        (stage / 'production').mkdir()
        (stage / 'binding-overlay.json').write_bytes(overlay_wire)
        for prepared, entry in bundles:
            (stage / 'queue' / entry['bundleFile']).write_bytes(canonical(prepared) + b'\n')
        (stage / 'queue-manifest.json').write_bytes(canonical(manifest) + b'\n')
        (stage / 'production/execution.jsonl').touch()
        write_preflight(stage, summary, overlay)
        require(not folder.exists(), 'RECOVERY_OUTPUT_ALREADY_EXISTS')
        stage.rename(folder)
    check_pins(historical_pins)
    return summary


def write_preflight(stage: Path, summary: dict, overlay: dict) -> None:
    """Write the same concise offline summary for initial and operational sealing."""
    (stage / 'preflight.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    lines = ['# HydroShare README recovery preflight', '',
             'Prospective caller attestation only; historical acquisition remains not independently verified.', '',
             '20 affected owners / 21 README paths / 20 complete successor requests / 41 selected units.', '',
             '| Owner | Original README path | Characters | Physical comparison |', '|---|---|---:|---|']
    for binding in overlay['bindings']:
        lines.append(f"| {binding['ownerID']} | {binding['source_path']} | {binding['characters']} | "
                     f"{binding['physicalComparison']['comparison']} |")
    lines.extend(['', 'Cost scenarios (USD): ' + json.dumps(summary['costUSD'], sort_keys=True), '',
                  'The empty production journal is allocated. Its immutable run manifest and header are initialized '
                  'only on terminal submission with operational token capacity. No provider calls have been made.', ''])
    (stage / 'preflight.md').write_text('\n'.join(lines))


ACCEPTED_PREFLIGHT_SHA256 = '4418b51789372c9e4d44d8f5ed96108965d5ba4c8fb829c5505f7d1794f3d9cf'


def refresh_preflight(source: Path, destination: Path) -> dict:
    """Reseal accepted, unexecuted artifacts after relocation; never reread raw sources."""
    assert_isolated(source)
    assert_isolated(destination)
    require(source.resolve() != destination.resolve() and not destination.exists(), 'NEW_RECOVERY_ROOT_REQUIRED')
    wire = (source / 'queue-manifest.json').read_bytes()
    require(digest(wire) == ACCEPTED_PREFLIGHT_SHA256, 'ACCEPTED_PREFLIGHT_PIN_DRIFT')
    manifest = adapter.batch.batch_transport.decode(wire)
    # Only the entry point and cost gate changed; every scientific dependency stays pinned.
    old_pins = dict(manifest['implementationPins'])
    require(old_pins.pop('src/extraction/llm/hydroshare_readme_recovery.py', None) is not None,
            'LEGACY_ENTRY_POINT_PIN_REQUIRED')
    current_pins = implementation_pins()
    unchanged = dict(current_pins)
    unchanged.pop('src/evaluation/hydroshare_readme_recovery.py')
    require(old_pins == unchanged, 'RECOVERY_DEPENDENCY_DRIFT')
    overlay_wire = (source / 'binding-overlay.json').read_bytes()
    require(digest(overlay_wire) == manifest['bindingOverlaySha256'], 'OVERLAY_PIN_DRIFT')
    overlay = adapter.batch.batch_transport.decode(overlay_wire)
    summary = manifest['summary']
    require((summary['requests'], summary['owners'], summary['addedReadmes'], summary['selectedUnits'],
             summary['sizeHolds']) == (20, 20, 21, 41, 0), 'ACCEPTED_COVERAGE_DRIFT')
    bundles = {}
    for entry in manifest['requests']:
        name = entry['bundleFile']
        require(Path(name).name == name and name not in bundles, 'UNSAFE_OR_DUPLICATE_BUNDLE_PATH')
        data = (source / 'queue' / name).read_bytes()
        require(digest(data) == entry['bundleSha256'], 'SUCCESSOR_BUNDLE_DRIFT')
        bundles[name] = data
    require(len(bundles) == 20, 'ACCEPTED_REQUEST_COUNT_DRIFT')
    manifest['implementationPins'] = current_pins
    manifest['operationalPredecessorQueueSha256'] = digest(wire)
    summary.pop('twoAttemptPlanningReserveUSD', None)
    summary['livePrerequisites'] = ['explicit researcher-terminal --submit', 'sealed queue SHA-256',
                                    'operational token capacity']
    # Use the same controller lock as execution; a started predecessor cannot be cloned.
    with (source / 'production/controller.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (source / 'production/run-manifest.json').exists() and
                (source / 'production/execution.jsonl').read_bytes() == b'', 'PREDECESSOR_ALREADY_STARTED')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.refresh-', dir=destination.parent) as temporary:
            stage = Path(temporary)
            (stage / 'queue').mkdir()
            (stage / 'production').mkdir()
            (stage / 'binding-overlay.json').write_bytes(overlay_wire)
            for name, data in bundles.items():
                (stage / 'queue' / name).write_bytes(data)
            (stage / 'queue-manifest.json').write_bytes(canonical(manifest) + b'\n')
            (stage / 'production/execution.jsonl').touch()
            write_preflight(stage, summary, overlay)
            require(not destination.exists(), 'RECOVERY_OUTPUT_ALREADY_EXISTS')
            stage.rename(destination)
    return dict(summary=summary, queueSha256=verification.file_hash(destination / 'queue-manifest.json'))


def load_queue(folder: Path, expected_sha: str | None) -> tuple[dict, dict]:
    """Verify the sealed recovery pins and complete coverage before status or execution."""
    assert_isolated(folder)
    wire = (folder / 'queue-manifest.json').read_bytes()
    if expected_sha is not None:
        require(digest(wire) == expected_sha, 'RECOVERY_QUEUE_PIN_DRIFT')
    manifest = read_json(folder / 'queue-manifest.json')
    require(manifest['version'] == VERSION and manifest['artifactFamily'] == 'hydroshare' and
            len(manifest['requests']) == len({e['ownerID'] for e in manifest['requests']}) == 20 and
            all(e['family'] == 'hydroshare' for e in manifest['requests']), 'RECOVERY_SCOPE_DRIFT')
    require(manifest['implementationPins'] == implementation_pins(), 'RECOVERY_IMPLEMENTATION_DRIFT')
    check_pins(manifest['originalArtifactPins'])
    overlay_wire = (folder / 'binding-overlay.json').read_bytes()
    require(digest(overlay_wire) == manifest['bindingOverlaySha256'], 'OVERLAY_PIN_DRIFT')
    overlay = read_json(folder / 'binding-overlay.json')
    require(len(overlay['bindings']) == 21 and len({b['ownerID'] for b in overlay['bindings']}) == 20 and
            len({(b['ownerID'], b['source_path']) for b in overlay['bindings']}) == 21, 'OVERLAY_COVERAGE_DRIFT')
    for entry in manifest['requests']:
        prepared = load_bundle(folder, entry)
        expected = [b for b in overlay['bindings'] if b['ownerID'] == entry['ownerID']]
        units = prepared['semanticRequest']['request']['sourceUnits']
        require([u['sourceUnitID'] for u in units if u['sourceField'] == 'README'] ==
                [b['sourceUnitID'] for b in expected] and len(units) == len(expected) + 1,
                'SEALED_SUCCESSOR_CONTEXT_DRIFT')
        for binding, reader in zip(expected, prepared['requestInputs']['readme_results']):
            authority = reader['authority']
            require(authority['authorityTextSha256'] == binding['authorityTextSha256'] and
                    authority['sourceVerification'] == 'caller_attested' and
                    authority['acquisitionIntegrityStatus'] == 'not_independently_verified' and
                    digest(authority['text'].encode()) == binding['authorityTextSha256'], 'SEALED_ATTESTATION_DRIFT')
    return manifest, overlay


def load_bundle(folder: Path, entry: dict) -> dict:
    """Read a sealed successor and physical pins without reconstructing source selection."""
    require(Path(entry['bundleFile']).name == entry['bundleFile'], 'UNSAFE_BUNDLE_PATH')
    wire = (folder / 'queue' / entry['bundleFile']).read_bytes()
    require(digest(wire) == entry['bundleSha256'], 'SUCCESSOR_BUNDLE_DRIFT')
    prepared = adapter.batch.batch_transport.decode(wire)
    verification.checked_prepared(prepared, entry)
    check_pins(entry['rawSourcePins'])
    return prepared


def journal_class(manifest: dict) -> tuple[Any, type, Any]:
    """Reuse native framing/recovery with stored-outcome checks, never a new retry loop."""
    paired, native = verification.infrastructure(manifest['generatorPins'])
    native.bundle = deepcopy

    def verify_receipt(prepared: dict, receipt: dict) -> None:
        """Recheck original provider wrapper, metadata and priced usage."""
        require(receipt == adapter.batch.response_record(receipt['row'], prepared, paired,
                receipt['batchID'], receipt['number']), 'RECEIPT_DRIFT')

    cls = adapter.batch_journal(native, verification.checked_prepared, adapter.fingerprint,
                                 verification.checked_outcome, verify_receipt)
    return native, cls, paired


def status(folder: Path, expected_sha: str | None) -> dict:
    """Read local state offline, without journal recovery writes or provider polling."""
    manifest, _ = load_queue(folder, expected_sha)
    root = folder / 'production'
    if not (root / 'run-manifest.json').exists():
        require((root / 'execution.jsonl').stat().st_size == 0, 'UNBOUND_NONEMPTY_JOURNAL')
        return dict(preflight=manifest['summary'], journal='allocated_empty', completed=0, pending=20,
                    queueSha256=verification.file_hash(folder / 'queue-manifest.json'),
                    bindingOverlaySha256=manifest['bindingOverlaySha256'])
    run = read_json(root / 'run-manifest.json')
    require(run['parentSha256'] == verification.file_hash(folder / 'queue-manifest.json') and
            run['requests'] == manifest['requests'], 'RECOVERY_RUN_ASSOCIATION_DRIFT')
    native, cls, _ = journal_class(manifest)
    with verification.read_only_log(root, native, cls, (root / 'run-manifest.json').read_bytes()) as log:
        result = adapter.batch.summary(log)
        result.update(journalSeq=log.seq, journalHead=log.head)
        return result


def operate(folder: Path, expected_sha: str, mode: str, capacity: int | None) -> dict:
    """Terminal-only dispatch/collection, reusing native Batch attempts and recovery."""
    require(mode in ('submit', 'collect') and bool(expected_sha), 'EXPLICIT_TERMINAL_MODE_AND_QUEUE_PIN_REQUIRED')
    with offline():
        manifest, _ = load_queue(folder, expected_sha)
        native, cls, paired = journal_class(manifest)
    root = folder / 'production'
    # Serialize run initialization too; never replace an established run manifest.
    with (root / 'controller.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = root / 'run-manifest.json'
        if not path.exists():
            require(mode == 'submit', 'NO_SUBMITTED_RECOVERY_RUN')
            require(type(capacity) is int and capacity > 0, 'EXPLICIT_OPERATIONAL_TOKEN_CAPACITY_REQUIRED')
            require((root / 'execution.jsonl').stat().st_size == 0, 'UNBOUND_NONEMPTY_JOURNAL')
            run = dict(version=VERSION, parentSha256=expected_sha, generatorPins=manifest['generatorPins'],
                implementationPins=manifest['implementationPins'], requests=manifest['requests'],
                queuedTokenLimit=capacity, pricing=manifest['pricing'],
                maximumAttemptsPerRequest=2, meaningfulSampleRequests=min(100, len(manifest['requests'])),
                kgAuthorization=False, bindingOverlaySha256=manifest['bindingOverlaySha256'])
            with path.open('xb') as handle:
                handle.write(adapter.batch.canonical_json(run) + b'\n')
        else:
            run = read_json(path)
            require(run['parentSha256'] == expected_sha and run['requests'] == manifest['requests'], 'RECOVERY_RUN_DRIFT')
            require(capacity is None or capacity == run['queuedTokenLimit'], 'PINNED_CAPACITY_DRIFT')
        wire = path.read_bytes()
        with cls(root / 'execution.jsonl', wire, digest(wire)) as log:
            # The native bounded retry controller remains the only attempt policy.
            def process(prepared: dict, receipt: dict, number: int, first: dict | None) -> dict:
                """Run unchanged acceptance only for newly collected authentic outcomes."""
                with offline():
                    return adapter.process(prepared, receipt, number, first)

            def record(row: dict, prepared: dict, bid: str, number: int) -> dict:
                """Reuse original provider metadata and cost recording."""
                return adapter.batch.response_record(row, prepared, paired, bid, number)

            def rebuild(entry: dict) -> dict:
                """Load only a sealed successor; no historical reconstruction."""
                with offline():
                    return load_bundle(folder, entry)

            api = adapter.batch.batch_transport.BatchAPI(adapter.batch.baseline.provider.load_openai_api_key())
            try:
                if mode == 'collect':
                    errors = adapter.batch.collect_once(log, api, process, record)
                    require(not errors, 'RECOVERY_COLLECTION_ERRORS:' + json.dumps(errors))
                else:
                    log.disposition = adapter.batch.submit_all(log, api, rebuild, native, adapter.fingerprint, 1)
                return adapter.batch.summary(log)
            finally:
                if not log.poisoned:
                    adapter.batch.save_status(log)


def main() -> None:
    """Expose preparation/status separately from explicit researcher-terminal API modes."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ('prepare', 'refresh-preflight', 'status', 'submit', 'collect'):
        modes.add_argument('--' + name, action='store_true')
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--queue-sha256')
    parser.add_argument('--queued-token-limit', type=int)
    parser.add_argument('--from-root', type=Path)
    args = parser.parse_args()
    folder = args.root.resolve()
    if args.refresh_preflight:
        require(args.from_root is not None, 'PREDECESSOR_ROOT_REQUIRED')
        with offline():
            result = refresh_preflight(args.from_root.resolve(), folder)
    elif args.prepare or args.status:
        with offline():
            result = prepare(folder) if args.prepare else status(folder, args.queue_sha256)
    else:
        result = operate(folder, args.queue_sha256, 'submit' if args.submit else 'collect',
                         args.queued_token_limit)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
