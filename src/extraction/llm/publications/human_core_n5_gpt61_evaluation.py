"""Post-hoc GPT-6.1 sensitivity using the unchanged frozen Human Core scorer.

Only the prediction records are replaced. This is not a confirmatory Step 7
execution and does not consume researcher judgments or perform semantic review.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket
from typing import Any, Mapping
from unittest.mock import patch

from . import human_core_n5_evaluation as scorer
from . import human_core_n5_gpt61_extraction as extraction
from . import production_acceptance as acceptance
from .request_builder import canonical_json, sha256_bytes

ROOT = extraction.ROOT
OUTPUT = extraction.OUTPUT
VERSION = '1.0.0'
REALIZATION = 'publication-human-core-n5-gpt61-posthoc-v1.0.0'
PREDICTIONS = OUTPUT / 'gpt61_posthoc_strict_prediction_inputs_v1.0.0.json'
RESULT = OUTPUT / 'gpt61_posthoc_strict_evaluation_v1.0.0.json'
REPORT = OUTPUT / 'gpt61_posthoc_strict_evaluation_v1.0.0.md'
BASELINE = scorer.DEFAULT_OUTPUT
require = extraction.require
read = extraction.read


def binding(path: Path) -> dict[str, Any]:
    """Record exact bytes with repository-relative provenance."""
    return {'path': str(path.relative_to(ROOT)), 'sha256': scorer._sha256(path)}


def verify_result(document: Mapping[str, Any], prepared: Mapping[str, Any],
                  manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Verify authentic provider/attempt provenance and rederive only acceptance."""
    request = prepared['request']
    rid = request['requestID']
    require(document['historicalRequestID'] == rid and document['model'] == extraction.MODEL, 'RESULT_IDENTITY_DRIFT')
    require(document['manifestSha256'] == sha256_bytes(canonical_json(manifest)), 'RESULT_MANIFEST_DRIFT')
    extraction.verify_pins(document['localArtifactPins'])
    folder = extraction.LOCAL / 'requests' / rid
    technical = document['technicalResult']
    selection = technical['attemptSelection']
    require(selection == read(folder / 'attempt_selection.json'), 'SELECTION_DRIFT')
    attempts = selection['attempts']
    require(len(attempts) == 1 and selection['selectedAttemptNumber'] == 1, 'UNEXPECTED_SELECTED_ATTEMPT')
    selected = attempts[0]
    require(selected == read(folder / 'attempt-01/lifecycle.json'), 'LIFECYCLE_DRIFT')
    require(selected['status'] == 'processed' and selected['parserResult']['parseStatus'] == 'parsed', 'UNPROCESSABLE_SELECTED_ATTEMPT')
    require(acceptance.run_attempt_controller(lambda number: deepcopy(selected)) == selection, 'PRODUCTION_SELECTION_DRIFT')
    response = read(folder / 'attempt-01/provider_response.json')
    require(response == read(folder / 'authentic_provider_response.json'), 'AUTHENTIC_RESPONSE_DRIFT')
    raw = (folder / 'attempt-01/raw_model_output.json').read_bytes()
    metadata = read(folder / 'attempt-01/provider_metadata.json')
    body = read(folder / 'attempt-01/provider_request.json')
    require(body == prepared['body'], 'PROVIDER_REQUEST_DRIFT')
    with extraction.technical_context():
        extraction.provider.validate_provider_response(response)
    require(extraction.provider.extract_model_output(response) == raw, 'RAW_RESPONSE_DRIFT')
    require(metadata == extraction.provider.provider_response_record(response, body, raw, execution_mode='streaming'), 'PROVIDER_METADATA_DRIFT')
    for field, value in [('providerResponseSha256', canonical_json(response)),
                         ('providerMetadataSha256', canonical_json(metadata)), ('rawOutputSha256', raw)]:
        require(selected[field] == sha256_bytes(value), 'SELECTED_PROVENANCE_DRIFT:' + field)
    expected = {
        'requestedModel': extraction.MODEL, 'requestInputSha256': request['requestInputSha256'],
        'providerInputSha256': sha256_bytes(prepared['providerInput']),
        'modelAuthorableSchemaSha256': sha256_bytes(canonical_json(prepared['schema'])),
        'authorityBundleID': request['authorityBundleID'], 'reasoningEffort': 'medium',
        'maxOutputTokens': 32768, 'store': False,
    }
    require(all(selected[k] == v for k, v in expected.items()), 'SELECTED_REQUEST_IDENTITY_DRIFT')
    projection = technical['acceptedSemanticProjection']
    require(projection == read(folder / 'accepted_semantic_projection.json'), 'PERSISTED_PROJECTION_DRIFT')
    require(projection == acceptance.derive_accepted_semantic_projection(selection, request), 'PRODUCTION_ACCEPTANCE_DRIFT')
    require(projection['sourceUnitID'] == request['primarySourceUnitID'] and
            projection['sourceArtifactID'] == request['sourceArtifactID'], 'PROJECTION_SOURCE_DRIFT')
    # Use the original conversion, which rejects nonaccepted records and missing evidence.
    row = {'requestID': rid, 'executionCohort': 'human_core_n5',
           'acceptedSemanticProjection': projection,
           'providerProvenance': {'responseID': response['id'], 'returnedModel': response['model'],
                                  'status': response['status'], 'selectedAttemptNumber': 1,
                                  'providerResponseSha256': selected['providerResponseSha256'],
                                  'providerMetadataSha256': selected['providerMetadataSha256'],
                                  'rawOutputSha256': selected['rawOutputSha256'],
                                  'providerRequestBodySha256': sha256_bytes(canonical_json(body))}}
    scorer._prediction_records(row, REALIZATION)
    return row


def load_verified_predictions() -> dict[str, Any]:
    """Verify all five exact extraction results and retain accepted-only prediction inputs."""
    manifest = read(OUTPUT / 'extraction_manifest.json')
    for name, field in [('preservation', 'preservationSha256'), ('dependencies', 'dependencySha256')]:
        pins = read(extraction.LOCAL / (name + '.json'))
        require(sha256_bytes(canonical_json(pins)) == manifest[field], 'EXTRACTION_BINDING_DRIFT')
        # Finder metadata is not a research artifact; retain the original binding
        # unchanged and verify every scientific file against its original digest.
        checked = {k: v for k, v in pins.items() if Path(k).name != '.DS_Store'} if name == 'preservation' else pins
        extraction.verify_pins(checked)
        if name == 'preservation':
            current = {k: v for k, v in extraction.preserved_pins().items() if Path(k).name != '.DS_Store'}
            require(current == checked, 'HISTORICAL_INVENTORY_DRIFT')
    records = extraction.records()
    require(len(manifest['requests']) == len(records) == 5, 'MANIFEST_SCOPE_DRIFT')
    prepared = []
    for record, entry in zip(records, manifest['requests']):
        require(all(entry[k] == v for k, v in record.items()), 'FROZEN_REQUEST_DRIFT')
        p = extraction.rebuild(record)
        require(sha256_bytes(canonical_json(p['body'])) == entry['gpt61ProviderBodySha256'], 'BODY_DRIFT')
        require(sha256_bytes(p['providerInput']) == entry['providerInputSha256'], 'INPUT_DRIFT')
        prepared.append(p)
    expected = {p['request']['requestID'] + '.json' for p in prepared}
    require({p.name for p in OUTPUT.glob('publication-c1-request-*.json')} == expected, 'RESULT_SCOPE_DRIFT')
    rows = []
    for p in prepared:
        path = OUTPUT / (p['request']['requestID'] + '.json')
        row = verify_result(read(path), p, manifest)
        row['extractionResult'] = binding(path)
        rows.append(row)
    require(tuple(r['acceptedSemanticProjection']['sourceUnitID'] for r in rows) == extraction.UNITS, 'N5_UNITS_DRIFT')
    return {'artifactType': 'publication_human_core_n5_gpt61_posthoc_prediction_inputs',
            'artifactVersion': VERSION, 'realizationID': REALIZATION, 'model': extraction.MODEL,
            'status': 'POST_HOC_MODEL_SENSITIVITY', 'extractionManifest': binding(OUTPUT / 'extraction_manifest.json'),
            'scorer': binding(Path(scorer.__file__)), 'adapter': binding(Path(__file__)),
            'productionAcceptance': binding(Path(acceptance.__file__)),
            'rawProviderResponsesIncluded': False, 'rows': rows}


def prediction_inputs(frozen: scorer.FrozenInputs, package: dict[str, Any]) -> scorer.FrozenInputs:
    """Replace only predictions and their provenance; retain every frozen scoring input."""
    rows = package['rows']
    require(package['realizationID'] == REALIZATION and package['model'] == extraction.MODEL, 'PREDICTION_REALIZATION_DRIFT')
    require(len(rows) == 5 and tuple(r['acceptedSemanticProjection']['sourceUnitID'] for r in rows) == extraction.UNITS, 'PREDICTION_SCOPE_DRIFT')
    predictions = tuple(record for row in rows for record in scorer._prediction_records(row, REALIZATION))
    provenance = deepcopy(frozen.provenance)
    # Remove only the old prediction-specific authority; retain reference/matching bindings.
    for field in ('predictionAuthority', 'realizationFreeze', 'canonicalPredictions'):
        provenance.pop(field)
    provenance.update(predictionAuthority=REALIZATION,
                      canonicalPredictions={'path': str(PREDICTIONS.relative_to(ROOT)),
                                            'sha256': sha256_bytes(canonical_json(package) + b'\n'), 'recordCount': 5},
                      endpointAliasProjection=binding(scorer.GOLD_ROOT / 'publication_human_core_v0.1.5_composite_reference_projection.json'))
    return replace(frozen, predictions=predictions, provenance=provenance)


def evaluate(package: dict[str, Any]) -> dict[str, Any]:
    """Call the frozen compute function, then label the result as post-hoc sensitivity."""
    frozen = scorer.load_frozen_inputs()
    baseline = read(BASELINE)
    require(baseline['frozenInputs'] == frozen.provenance, 'BASELINE_REFERENCE_PROVENANCE_DRIFT')
    inputs = prediction_inputs(frozen, package)
    result = scorer.compute(inputs)
    require(result['aggregate']['nodes']['referenceSupport'] == 118 and
            result['aggregate']['relations']['referenceSupport'] == 61, 'HUMAN_CORE_SUPPORT_DRIFT')
    require(result['scoringOpportunities'] == baseline['scoringOpportunities'], 'SCORING_SCOPE_DRIFT')
    result.update(artifactType='publication_human_core_n5_gpt61_posthoc_strict_evaluation',
                  artifactVersion=VERSION, status='POST_HOC_MODEL_SENSITIVITY',
                  execution='posthoc_model_sensitivity_existing_frozen_strict_matcher',
                  model=extraction.MODEL, confirmatoryStep7=False, semanticEquivalenceReviewPerformed=False,
                  historicalResearcherJudgmentsUsed=False)
    totals = Counter(row.kind for row in inputs.predictions)
    result['predictionScopeAccounting'] = {
        kind: {'allProductionAccepted': totals[record_kind],
               'scoredExtractAndEvaluate': result['aggregate'][kind]['predictionSupport'],
               'excludedOutsideScoringScope': totals[record_kind] - result['aggregate'][kind]['predictionSupport']}
        for kind, record_kind in [('nodes', 'node'), ('relations', 'relation')]}
    result['comparisonWithFrozenGPT56'] = {
        'baseline': binding(BASELINE), 'aggregate': baseline['aggregate'],
        'deltaGPT61MinusGPT56': {
            kind: {key: result['aggregate'][kind][key] - baseline['aggregate'][kind][key]
                   for key in ('TP', 'FP', 'FN', 'predictionSupport', 'precision', 'recall', 'f1')}
            for kind in ('nodes', 'relations')},
        'sameReferencesRoutingOpportunitiesAndAliases': True,
        'baselineRecomputedOrModified': False,
    }
    return result


def render_report(result: dict[str, Any]) -> str:
    """Render strict metrics without semantic-equivalence interpretation."""
    lines = ['# GPT-6.1 Human Core N=5 — POST-HOC MODEL SENSITIVITY', '',
             'Strict evaluation with the unchanged frozen Human Core matcher. This is not a new confirmatory Step 7.', '',
             '| Model | Kind | TP | FP | FN | Reference | Scored predictions | Precision | Recall | F1 |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for model, aggregate in [('GPT-5.6 (frozen corrected Step 7B)', result['comparisonWithFrozenGPT56']['aggregate']), ('GPT-6.1 (post-hoc)', result['aggregate'])]:
        for kind, row in aggregate.items():
            values = [str(row[k]) for k in ('TP', 'FP', 'FN', 'referenceSupport', 'predictionSupport')]
            values += [f'{row[k]:.6f}' for k in ('precision', 'recall', 'f1')]
            lines.append('| ' + ' | '.join([model, kind, *values]) + ' |')
    lines += ['', 'Only original unit-specific `extract_and_evaluate` opportunities are scored; `extract_and_monitor` is excluded. Reference support remains 118 nodes and 61 relations.', '']
    for kind, counts in result['predictionScopeAccounting'].items():
        lines.append(f"- {kind}: {counts['allProductionAccepted']} production accepted; {counts['scoredExtractAndEvaluate']} scored; {counts['excludedOutsideScoringScope']} outside scoring scope.")
    lines += ['', '## Per-unit strict counts', '']
    for unit, kinds in result['byUnit'].items():
        lines.append('- `' + unit + '` — ' + '; '.join(f"{kind}: TP={m['TP']} FP={m['FP']} FN={m['FN']}" for kind, m in kinds.items()) + '.')
    lines += ['', 'The JSON companion retains per-target metrics, scoring opportunities, matched pairs and unmatched records. The prediction-input package preserves the exact accepted projections and selected-provider provenance.', '',
              'No semantic-equivalence review, historical judgment transfer, adjudication, provider calls or KG writes were performed. Historical references, GPT-5.6 Step 7 and Step 8 artifacts remain unchanged.', '']
    return '\n'.join(lines)


def run(verify_only: bool = False) -> dict[str, Any]:
    """Generate immutable versioned artifacts, or reproduce and compare them offline."""
    before = extraction.preserved_pins()
    package = load_verified_predictions()
    result = evaluate(package)
    report = render_report(result).encode()
    outputs = {PREDICTIONS: canonical_json(package) + b'\n', RESULT: canonical_json(result) + b'\n', REPORT: report}
    for path, data in outputs.items():
        if path.exists():
            require(path.read_bytes() == data, 'EVALUATION_ARTIFACT_DRIFT:' + path.name)
        else:
            require(not verify_only, 'MISSING_EVALUATION_ARTIFACT:' + path.name)
    for path, data in outputs.items():
        if not path.exists():
            with path.open('xb') as handle:
                handle.write(data)
    require(extraction.preserved_pins() == before, 'HISTORICAL_PRESERVATION_DRIFT')
    return result


def main() -> None:
    """Always offline; no credential loading or provider-dispatch option."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_NO_NETWORK')):
        result = run(args.verify)
    print(json.dumps({'status': result['status'], 'aggregate': result['aggregate'],
                      'predictionScopeAccounting': result['predictionScopeAccounting'], 'providerCalls': 0}, indent=2))


if __name__ == '__main__':
    main()
