"""Materialize pinned GPT-6.1 researcher decisions with frozen secondary-review logic.

Only the historical implementation's population and decision-count guards are
specialized in an isolated namespace. Exact copying, structural validation,
one-to-one checks, endpoint-context checks and rate formulas are reused verbatim.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import inspect
import json
from pathlib import Path
import socket
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from . import human_core_n5_corrected_evaluation_researcher_review as original
from . import human_core_n5_gpt61_secondary_review as instrument
from .request_builder import canonical_json, sha256_bytes

ROOT = instrument.ROOT
AREA = instrument.extraction.OUTPUT
LEDGER = AREA / 'gpt61_posthoc_researcher_judgment_ledger_v1.0.0.json'
LEDGER_REPORT = LEDGER.with_suffix('.md')
LEDGER_SHA = '76b52fcc0139771685e079d61006de9772603ac1c88c04ec931bc29e7d9fa6bb'
INSTRUMENT_SHA = '75c8654292df8f9df2b23a1bf6b4c18359ad74d67cac1b1e91da8c552662b8f4'
IMPLEMENTATION_SHA = '6c8e4d9570ed384c7da3c5f1114622e26262dd95e30cda97f58e118655a0a91d'
BASELINE_SHA = 'ef28c77f05b5647c5f15a963902d3b6188946f40675dbce7f2db2584edc2d2af'
OUTPUT = AREA / 'gpt61_posthoc_secondary_researcher_review_v1.0.0.json'
REPORT = OUTPUT.with_suffix('.md')
POPULATION = dict(zip(original.PASS_CONFIGURATION, (118, 127, 61, 67)))
# These are count assertions from the exact researcher ledger, never judgments
# inferred from evidence. The original function bodies otherwise remain intact.
SUBSTITUTIONS = {
    '_index_source': [('356', '373')],
    '_ledger_entries': [('356', '373')],
    '_validate_materialized': [
        ('[118, 109, 61, 68]', '[118, 127, 61, 67]'),
        ('118/109/61/68', '118/127/61/67'),
        ('"semantic_equivalent": 64, "target_or_class_disagreement": 7, "not_equivalent": 47',
         '"semantic_equivalent": 78, "target_or_class_disagreement": 10, "not_equivalent": 30'),
        ('"supported_as_proposed": 103, "not_supported_as_proposed": 6',
         '"supported_as_proposed": 120, "not_supported_as_proposed": 7'),
        ('"semantic_equivalent": 33, "not_equivalent": 28',
         '"semantic_equivalent": 41, "not_equivalent": 19, "target_or_class_disagreement": 1'),
        ('"supported_as_proposed": 66', '"supported_as_proposed": 65'),
        ('{"P1": 26, "P2": 2}', '{"P1": 17, "P2": 2}'),
        ('P1=26/P2=2', 'P1=17/P2=2'), ('356 researcher', '373 researcher'),
        ('((selected_nodes, 64), (selected_relations, 33))', '((selected_nodes, 78), (selected_relations, 41))'),
    ],
}
require = instrument.require
read = instrument.extraction.read


def binding(path: Path) -> dict[str, Any]:
    """Bind immutable authority bytes using repository-relative paths."""
    return {'path': str(path.relative_to(ROOT)), 'sha256': original._sha256(path), 'modified': False}


def load_authorities() -> tuple[dict[str, Any], dict[str, Any]]:
    """Check researcher authorization and exact GPT-6.1 scientific source bindings."""
    for path, digest in [(LEDGER, LEDGER_SHA), (instrument.OUTPUT, INSTRUMENT_SHA),
                         (Path(original.__file__), IMPLEMENTATION_SHA), (original.OUTPUT, BASELINE_SHA)]:
        require(original._sha256(path) == digest, 'AUTHORITY_DRIFT:' + path.name)
    strict, _ = instrument.load_inputs()
    ledger, source = read(LEDGER), read(instrument.OUTPUT)
    require(ledger['status'] == 'RESEARCHER_CONFIRMED_READY_FOR_MATERIALIZATION', 'LEDGER_NOT_READY')
    require(ledger['model'] == source['model'] == 'gpt-6.1-sol' and
            ledger['analysisRole'] == source['analysisRole'] == 'POST_HOC_MODEL_SENSITIVITY', 'WRONG_MODEL_OR_ROLE')
    require(ledger['sourceInstrument']['sha256'] == INSTRUMENT_SHA and
            ledger['sourceInstrument']['path'] == str(instrument.OUTPUT.relative_to(ROOT)), 'INSTRUMENT_BINDING_DRIFT')
    authorities = ledger['boundAuthorities']
    require(authorities['gpt61StrictEvaluationSha256'] == instrument.STRICT_SHA and
            authorities['gpt61PredictionInputsSha256'] == instrument.PREDICTIONS_SHA and
            authorities['secondaryProtocolSha256'] == instrument.PROTOCOL_SHA and
            authorities['secondaryProtocolVersion'] == 'v0.1.1' and
            authorities['cohort'] == 'human_core_n5' and authorities['excludedCohort'] == 'step5_n6',
            'SCIENTIFIC_AUTHORITY_BINDING_DRIFT')
    require(source['counts']['humanCoreByKind'] == {'node': 118, 'relation': 61} and
            source['counts']['predictionsByKind'] == {'node': 127, 'relation': 67} and
            source['counts']['reviewItems'] == 373, 'INSTRUMENT_POPULATION_DRIFT')
    instrument.assert_neutral(source)
    require(strict['frozenInputs'] == source['endpointContextAuthorities'], 'SOURCE_PROVENANCE_DRIFT')
    return ledger, source


def adapted_sources() -> dict[str, str]:
    """Return pinned historical functions with only explicit cohort/count substitutions."""
    require(original._sha256(Path(original.__file__)) == IMPLEMENTATION_SHA, 'IMPLEMENTATION_DRIFT')
    sources = {}
    for name in ('_index_source', '_ledger_entries', '_validate_and_apply', '_validate_materialized', '_metrics'):
        source = inspect.getsource(getattr(original, name))
        for before, after in SUBSTITUTIONS.get(name, []):
            expected = 2 if before == '356' else 1
            require(source.count(before) == expected, 'UNEXPECTED_FROZEN_FUNCTION:' + name)
            source = source.replace(before, after)
        sources[name] = source
    return sources


def implementation() -> SimpleNamespace:
    """Reuse original functions in a separate namespace; never mutate original globals."""
    namespace = dict(vars(original))
    namespace.update(EXPECTED_POPULATION=POPULATION)
    for name, source in adapted_sources().items():
        exec(compile(source, '<pinned-secondary-review-gpt61-counts>', 'exec'), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in adapted_sources()})


def build_reviewed_artifact() -> dict[str, Any]:
    """Apply exact ledger fields, validate frozen rules and compute only secondary rates."""
    ledger, source = load_authorities()
    reuse = implementation()
    package = reuse._validate_and_apply(ledger, source)
    metrics = reuse._metrics(package)
    require({name: (row['numerator'], row['denominator']) for name, row in metrics.items()} == {
        'humanCoreNodeSemanticRecovery': (78, 118), 'humanCoreRelationSemanticRecovery': (41, 61),
        'correctedNodePredictionSourceSupportedRate': (120, 127),
        'correctedRelationPredictionSourceSupportedRate': (65, 67)}, 'METRIC_COUNT_DRIFT')
    # Independently confirm every ledger-controlled field was copied exactly.
    index = reuse._index_source(package)
    for identity, (pass_name, entry) in reuse._ledger_entries(ledger).items():
        fields = ('researcherDisposition', 'reviewedPredictionRecordKey', 'optionalExplanatoryCode', 'researcherNote') if pass_name.startswith(('A_', 'C_')) else ('predictionSourceSupportJudgment', 'optionalExplanatoryCode', 'researcherNote')
        require(all(field in entry and index[identity][1][field] == entry[field] for field in fields), 'DECISION_COPY_DRIFT')
    baseline = read(original.OUTPUT)['secondaryMetrics']
    package.pop('semanticJudgmentsPerformed', None)
    package.update(
        artifactType='publication_human_core_n5_gpt61_posthoc_secondary_researcher_review', artifactVersion='1.0.0',
        status='RESEARCHER_REVIEW_COMPLETE / POST_HOC_SECONDARY_METRICS_COMPUTED',
        sourceReviewPackage=binding(instrument.OUTPUT), researcherJudgmentLedger=binding(LEDGER),
        researcherLedgerReport=binding(LEDGER_REPORT), reviewProvenance=deepcopy(ledger['reviewProvenance']),
        researcherDecisionCounts=deepcopy(ledger['decisionCounts']),
        researcherJudgmentsMaterialized=373, semanticJudgmentsPerformedByMaterializer=False,
        secondaryMetrics=metrics, providerModelCalls=0, step7CReopened=False,
        materializationImplementation={**binding(Path(original.__file__)), 'countGuardSubstitutions': SUBSTITUTIONS,
                                       'adaptedFunctionsSha256': sha256_bytes(canonical_json(adapted_sources()))},
        comparisonWithFrozenGPT56={'artifact': binding(original.OUTPUT), 'secondaryMetrics': baseline,
                                  'deltaGPT61MinusGPT56': {name: row['value'] - baseline[name]['value'] for name, row in metrics.items()},
                                  'strictEvaluationChanged': False, 'baselineRecomputed': False})
    return package


def render_report(package: dict[str, Any]) -> str:
    """Report materialized secondary rates without reinterpreting researcher decisions."""
    labels = {'humanCoreNodeSemanticRecovery': 'Human Core node semantic recovery',
              'humanCoreRelationSemanticRecovery': 'Human Core relation semantic recovery',
              'correctedNodePredictionSourceSupportedRate': 'Node prediction source-supported rate',
              'correctedRelationPredictionSourceSupportedRate': 'Relation prediction source-supported rate'}
    lines = ['# GPT-6.1 Human Core N=5 — Researcher-confirmed secondary sensitivity', '',
             '**RESEARCHER_REVIEW_COMPLETE / POST_HOC_SECONDARY_METRICS_COMPUTED**', '',
             '| Secondary metric | GPT-6.1 | Frozen GPT-5.6 | Difference (percentage points) |',
             '|---|---:|---:|---:|']
    for name, label in labels.items():
        row = package['secondaryMetrics'][name]
        old = package['comparisonWithFrozenGPT56']['secondaryMetrics'][name]
        lines.append(f"| {label} | {row['numerator']}/{row['denominator']} = {row['value']:.6f} | {old['numerator']}/{old['denominator']} = {old['value']:.6f} | {(row['value']-old['value'])*100:+.4f} |")
    lines += ['', 'All 373 judgments were copied by exact review identity. Selected keys, eligibility, one-to-one assignments and relation endpoint context passed the existing validation rules. Unsupported predictions remain in the source-support denominators: 7 nodes and 2 relations; no insufficient-evidence judgments.', '',
              'These are post-hoc secondary rates, distinct from strict Precision/Recall/F1. Strict results and historical GPT-5.6 artifacts remain unchanged; Step 7C is not reopened.', '',
              'Research provenance (retained verbatim from the ledger):', '', ledger_provenance(package), '',
              'The materializer made no new semantic judgments, provider calls, KG writes or source-support inferences.', '']
    return '\n'.join(lines)


def ledger_provenance(package: dict[str, Any]) -> str:
    """Quote the researcher-declared review scope, without upgrading its authority."""
    return package['reviewProvenance']['mode'] + '. ' + package['reviewProvenance']['researcherDirectReviewScope'] + '.'


def preservation() -> dict[str, str]:
    """Pin all historical and input artifacts before any new output is written."""
    pins = instrument.extraction.preserved_pins()
    pins.update(instrument.extraction.file_pins([p for p in AREA.iterdir() if p.is_file() and p not in (OUTPUT, REPORT)]))
    return pins


def run(verify: bool = False) -> dict[str, Any]:
    """Materialize once or verify deterministic bytes; never overwrite reviewed data."""
    before = preservation()
    package = build_reviewed_artifact()
    outputs = {OUTPUT: canonical_json(package) + b'\n', REPORT: render_report(package).encode()}
    for path, data in outputs.items():
        if path.exists():
            require(path.read_bytes() == data, 'REVIEWED_OUTPUT_CONFLICT:' + path.name)
        else:
            require(not verify, 'MISSING_REVIEWED_OUTPUT:' + path.name)
    require(preservation() == before, 'PRESERVATION_DRIFT')
    for path, data in outputs.items():
        if not path.exists():
            with path.open('xb') as handle:
                handle.write(data)
    require(preservation() == before, 'PRESERVATION_DRIFT')
    return package


def main() -> None:
    """Offline-only deterministic materialization; no live option or credential loading."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_NO_NETWORK')):
        result = run(args.verify)
    print(json.dumps(result['secondaryMetrics'], indent=2))


if __name__ == '__main__':
    main()
