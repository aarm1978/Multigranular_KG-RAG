"""Correct the unused secondary review instrument without executing strict scoring."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from . import human_core_n5_semantic_equivalence_review as prior
from .human_core_n5_evaluation import load_historical_c1_inputs, _record_view, _node_indexes, _endpoint_identity

PROTOCOL = prior.PROJECT_ROOT / 'docs/publication_human_core_posthoc_semantic_equivalence_sensitivity_protocol_v0.1.1.md'
OUTPUT = prior.GOLD_ROOT / 'publication_human_core_n5_posthoc_semantic_equivalence_review_package_v0.1.1.json'
REPORT = OUTPUT.with_suffix('.md')
PRESERVED = (
    (prior.STRICT_JSON, prior.STRICT_JSON_SHA256),
    (prior.STRICT_REPORT, prior.STRICT_REPORT_SHA256),
    (prior.PROTOCOL_PATH, '357ef538422d46c17110a9efd7f90b1c4434c6c469062979c45ccf2d8ffd98f8'),
    (prior.DEFAULT_OUTPUT, 'c2555229fa6d12e268deaba1643791cef70e3d8bd43d50e51084057ca32425ef'),
    (prior.DEFAULT_REPORT, '163e091f9afbdf883f50eaea6172a12b0fe7b701edff4db7c275d511fb36f42d'),
)
CODES = dict(zip(prior.OPTIONAL_EXPLANATORY_CODES, (
    'evidence-boundary equivalence', 'different-local-occurrence equivalence',
    'assignment/competition artifact', 'semantically questionable strict TP',
    'genuine extraction miss', 'unsupported/spurious C1 prediction',
    'source-supported C1 assertion absent from Human Core', 'target/class disagreement',
    'endpoint-propagated relation disagreement', 'genuine relation miss',
)))


def verify_preservation() -> None:
    """Fail closed if strict or unused pre-review artifacts have changed."""
    for path, digest in PRESERVED:
        if prior._sha256(path) != digest:
            raise prior.ReviewPackageError(f'preserved artifact changed: {path}')


def items(package: dict, field: str) -> list[dict]:
    """Flatten one review population in deterministic group order."""
    return [item for unit in package['reviewGroupsByUnitAndOperationalTarget']
            for target in unit['targets'] for item in target[field]]


def validate_selections(package: dict) -> None:
    """Validate pending or selected keys and global uniqueness without judging semantics."""
    predictions = package['predictionRecordsByKey']
    used: set[str] = set()
    references: set[str] = set()
    for item in items(package, 'correspondenceReviewItems'):
        reference = item['humanCoreRecord']
        if reference['key'] in references:
            raise prior.ReviewPackageError('duplicate Human Core identity')
        references.add(reference['key'])
        disposition, selected = item['researcherDisposition'], item['reviewedC1RecordKey']
        if disposition is not None and disposition not in prior.CORRESPONDENCE_DISPOSITIONS:
            raise prior.ReviewPackageError('unknown correspondence disposition')
        if disposition == 'semantic_equivalent' and selected is None:
            raise prior.ReviewPackageError('semantic_equivalent requires a selected C1 key')
        if selected is None:
            continue
        prediction = predictions.get(selected)
        if prediction is None or prediction['sourceUnitID'] != reference['sourceUnitID']:
            raise prior.ReviewPackageError('selected C1 key does not resolve in the same unit')
        if disposition != 'target_or_class_disagreement' and not prior._same_structural_bucket(reference, prediction):
            raise prior.ReviewPackageError('selected C1 record is ineligible for correspondence')
        if disposition == 'semantic_equivalent':
            if selected in used:
                raise prior.ReviewPackageError('semantic-equivalent selections are not one-to-one')
            used.add(selected)


def build_package() -> dict[str, Any]:
    """Build the corrected instrument with unchanged strict populations and blank judgments."""
    verify_preservation()
    package = prior.build_package()
    inputs = load_historical_c1_inputs()
    all_records = list(inputs.references + inputs.predictions)
    records = {record.key: record for record in all_records}
    node_index = _node_indexes(all_records)

    def enrich(view: dict) -> dict:
        """Expose exact endpoint context, including nodes outside scored populations."""
        if view['kind'] != 'relation':
            return view
        relation = records[view['key']]
        contexts = {}
        for role in ('source', 'target'):
            endpoint = relation.value[role]
            identity = _endpoint_identity(relation, endpoint, node_index, inputs.routes, inputs.baseline_aliases)
            node = records.get(identity[1]) if identity[0] == 'node' else None
            contexts[role] = {
                'authoredEndpoint': endpoint,
                'stableEndpointIdentity': list(identity),
                'record': _record_view(node) if node else None,
                'resolution': 'exact_node_record' if node else 'deterministic_identity_context',
                'deterministicContext': None if node else {
                    'referenceID': endpoint['referenceID'], 'artifactID': endpoint.get('artifactID'),
                    'label': None, 'operationalTargetID': None, 'ontologyClassID': None,
                    'evidence': [],
                },
            }
        return {**view, 'endpointContext': contexts}

    predictions = {}
    matched_keys = set()
    for item in items(package, 'correspondenceReviewItems'):
        item['reviewedC1RecordKey'] = None
        item['humanCoreRecord'] = enrich(item['humanCoreRecord'])
        item['plausibleSameTargetClassCandidates'] = [enrich(v) for v in item['plausibleSameTargetClassCandidates']]
        if item['strictC1Record']:
            item['strictC1Record'] = enrich(item['strictC1Record'])
            prediction = item['strictC1Record']
            predictions[prediction['key']] = prediction
            matched_keys.add(prediction['key'])
    for item in items(package, 'c1OnlySourceSupportReviewItems'):
        prediction = enrich(item['c1Record'])
        predictions[prediction['key']] = prediction
    predictions = dict(sorted(predictions.items()))
    for unit in package['reviewGroupsByUnitAndOperationalTarget']:
        for target in unit['targets']:
            del target['c1OnlySourceSupportReviewItems']
            target['predictionSourceSupportReviewItems'] = [
                {
                    'reviewItemID': prior._item_id('prediction-source-support', key),
                    'reviewItemType': 'independent_prediction_source_support',
                    'strictMatchStatus': 'strict_true_positive' if key in matched_keys else 'strict_c1_only',
                    'c1Record': prediction,
                    **prior._reviewer_fields('prediction_support'),
                }
                for key, prediction in predictions.items()
                if prediction['sourceUnitID'] == unit['sourceUnitID']
                and prediction['operationalTargetID'] == target['operationalTargetID']
                and prediction['kind'] == target['kind']
            ]
    references = items(package, 'correspondenceReviewItems')
    support = items(package, 'predictionSourceSupportReviewItems')
    ref_counts = dict(Counter(item['humanCoreRecord']['kind'] for item in references))
    pred_counts = dict(Counter(item['c1Record']['kind'] for item in support))
    if ref_counts != {'node': 118, 'relation': 61} or pred_counts != {'node': 102, 'relation': 59}:
        raise prior.ReviewPackageError('review population differs from fixed denominators')
    package.update({
        'artifactVersion': '0.1.1',
        'predictionRecordsByKey': predictions,
        'protocol': {
            **package['protocol'], 'path': str(PROTOCOL.relative_to(prior.PROJECT_ROOT)),
            'sha256': prior._sha256(PROTOCOL), 'explanatoryCodeDefinitions': CODES,
        },
        'unusedPreReviewInstrument': {
            'version': '0.1.0', 'researcherJudgmentsOccurred': False,
            'status': 'UNUSED_PRE_REVIEW_INSTRUMENT',
            'preservedArtifacts': [{'path': str(path.relative_to(prior.PROJECT_ROOT)), 'sha256': digest}
                                   for path, digest in PRESERVED[2:]],
        },
        'endpointContextAuthorities': inputs.provenance,
        'secondaryMetricDefinitions': {
            'status': 'FIXED_BEFORE_REVIEW',
            'humanCoreSemanticRecovery': {
                'numerator': 'one-to-one researcher-confirmed semantic_equivalent Human Core records',
                'denominators': ref_counts, 'values': None,
            },
            'c1SourceSupportedPredictionRate': {
                'numerator': 'supported_as_proposed C1 predictions',
                'denominators': pred_counts, 'values': None,
                'unsupportedCounts': None, 'insufficientCounts': None,
            },
            'computationGate': 'All researcher judgments complete and global one-to-one selections validated',
        },
        'counts': {**package['counts'], 'reviewItems': len(references) + len(support),
                   'candidateGroups': len(references), 'predictionSourceSupportReviewItems': len(support),
                   'humanCoreByKind': ref_counts, 'predictionsByKind': pred_counts},
    })
    validate_selections(package)
    verify_preservation()
    return package


def render_report(package: dict) -> str:
    """Render a deterministic index with metric definitions and review instructions."""
    lines = ['# Secondary sensitivity review instrument v0.1.1', '',
             'Review pending. Step 7 remains PRE-FREEZE. v0.1.0 is preserved as an unused pre-review instrument.', '',
             'Select reviewedC1RecordKey for each semantic-equivalent correspondence. Global one-to-one selection is required.',
             'Review source support independently for every C1 prediction, including strict TPs.',
             'For target_or_class_disagreement, an exact same-unit C1 key may document the disagreement; it cannot recover a cross-target/class match.', '',
             'Human-Core semantic recovery: confirmed one-to-one equivalents / 118 nodes or 61 relations.',
             'C1 source-supported prediction rate: supported_as_proposed / 102 nodes or 59 relations; report unsupported and insufficient separately.',
             'Both metrics remain unset until researcher review is complete. See the bound protocol and endpoint context in JSON.', '',
             '## Populations', '', json.dumps(package['counts'], sort_keys=True), '', '## Unit / target index', '']
    for unit in package['reviewGroupsByUnitAndOperationalTarget']:
        lines.extend([f"### {unit['sourceUnitID']}", ''])
        for target in unit['targets']:
            lines.append(f"- {target['operationalTargetID']}: {len(target['correspondenceReviewItems'])} correspondence; {len(target['predictionSourceSupportReviewItems'])} support items.")
        lines.append('')
    return '\n'.join(lines)


def main() -> None:
    """Materialize new outputs without overwriting any review instrument."""
    if OUTPUT.exists() or REPORT.exists():
        raise prior.ReviewPackageError('v0.1.1 output already exists')
    package = build_package()
    OUTPUT.write_text(json.dumps(package, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text(render_report(package), encoding='utf-8')
    verify_preservation()


if __name__ == '__main__':
    main()
