"""Neutral GPT-6.1 review instrument using the pinned corrected Step 7 builder.

The historical builder has no parameter for prediction denominators. To leave its
frozen source and extraction dependency pins untouched, this adapter specializes
exactly that one count guard in an isolated function namespace. All population,
bucket, endpoint and selection logic executes the original implementation.
No matcher, metric computation or researcher-judgment loader is invoked.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import inspect
import json
from pathlib import Path
import socket
from typing import Any
from unittest.mock import patch

from . import human_core_n5_corrected_evaluation_semantic_equivalence_review as original
from . import human_core_n5_gpt61_evaluation as evaluation
from . import human_core_n5_gpt61_extraction as extraction
from .request_builder import canonical_json, sha256_bytes

ROOT = extraction.ROOT
OUTPUT = extraction.OUTPUT / 'gpt61_posthoc_secondary_review_instrument_v1.0.0.json'
REPORT = OUTPUT.with_suffix('.md')
BUILDER_SHA = '93c2b1931f9ed6b67e65f74dc516cc87760777e724caa0f47e0b76ea8e51a1d9'
STRICT_SHA = '1328acfebe66c024d38cdf7d47016bef6232d856e231f14fc7c9567bde6b8b86'
PREDICTIONS_SHA = 'fecb09407e64dfaea8f2968416d9147a583d1b82313bbc5e3a7109bced73fbdf'
PROTOCOL_SHA = '940499ad028cfadefe00e49f12fb95e5a5b7150047977910e56667f53834f656'
OLD_GUARD = 'prediction_counts != {"node": 109, "relation": 68}'
NEW_GUARD = 'prediction_counts != {"node": 127, "relation": 67}'
items = original.items
validate_selections = original.validate_selections
require = extraction.require


def load_inputs() -> tuple[dict[str, Any], Any]:
    """Bind only published strict/prediction bytes and unchanged frozen reference context."""
    for path, digest in [(Path(original.__file__), BUILDER_SHA), (evaluation.RESULT, STRICT_SHA),
                         (evaluation.PREDICTIONS, PREDICTIONS_SHA), (original.PROTOCOL, PROTOCOL_SHA)]:
        require(original._sha256(path) == digest, 'REVIEW_AUTHORITY_DRIFT:' + path.name)
    original.verify_historical_preservation()
    strict = extraction.read(evaluation.RESULT)
    package = extraction.read(evaluation.PREDICTIONS)
    require(strict['status'] == 'POST_HOC_MODEL_SENSITIVITY' and strict['model'] == extraction.MODEL,
            'WRONG_STRICT_AUTHORITY')
    require(strict['frozenInputs']['canonicalPredictions']['sha256'] == PREDICTIONS_SHA,
            'STRICT_PREDICTION_BINDING_DRIFT')
    frozen = evaluation.scorer.load_frozen_inputs()
    bound = evaluation.prediction_inputs(frozen, package)
    require(bound.provenance == strict['frozenInputs'], 'ENDPOINT_CONTEXT_AUTHORITY_DRIFT')
    for row in package['rows']:
        extraction.verify_pins({row['extractionResult']['path']: row['extractionResult']['sha256']})
    return strict, bound


def adapted_builder_source() -> str:
    """Permit only the explicitly authorized denominator substitution in pinned code."""
    require(original._sha256(Path(original.__file__)) == BUILDER_SHA, 'BUILDER_SOURCE_DRIFT')
    source = inspect.getsource(original.build_package)
    require(source.count(OLD_GUARD) == 1, 'EXPECTED_DENOMINATOR_GUARD_MISSING')
    return source.replace(OLD_GUARD, NEW_GUARD, 1)


def assert_neutral(package: dict[str, Any]) -> None:
    """Check blank reviewer fields and metric values without interpreting any assertion."""
    for item in items(package, 'correspondenceReviewItems'):
        require(all(item[field] is None for field in
                    ('researcherDisposition', 'reviewedPredictionRecordKey', 'optionalExplanatoryCode', 'researcherNote')),
                'NON_NEUTRAL_CORRESPONDENCE')
    for item in items(package, 'predictionSourceSupportReviewItems'):
        require(all(item[field] is None for field in
                    ('predictionSourceSupportJudgment', 'optionalExplanatoryCode', 'researcherNote')),
                'NON_NEUTRAL_SOURCE_SUPPORT')
    metrics = package['secondaryMetricDefinitions']
    require(metrics['humanCoreSemanticRecovery']['values'] is None, 'NON_NEUTRAL_METRIC')
    support = metrics['predictionSourceSupportedRate']
    require(all(support[field] is None for field in ('values', 'unsupportedCounts', 'insufficientCounts')),
            'NON_NEUTRAL_METRIC')
    validate_selections(package)


def build_package() -> dict[str, Any]:
    """Execute existing instrument construction with model-specific input bindings only."""
    strict, inputs = load_inputs()
    namespace = dict(vars(original))
    namespace.update(_load_corrected_strict_result=lambda: deepcopy(strict),
                     load_frozen_inputs=lambda: inputs,
                     STRICT_JSON=evaluation.RESULT, STRICT_REPORT=evaluation.REPORT,
                     STRICT_JSON_SHA256=STRICT_SHA, STRICT_PREDICTIONS_SHA256=PREDICTIONS_SHA)
    source = adapted_builder_source()
    exec(compile(source, '<pinned-corrected-builder-gpt61-denominators>', 'exec'), namespace)
    package = namespace['build_package']()
    # Model labels and bindings do not alter the inherited review-item semantics.
    package.update(artifactType='publication_human_core_n5_gpt61_posthoc_secondary_review_instrument',
                   artifactVersion='1.0.0', model=extraction.MODEL,
                   analysisRole='POST_HOC_MODEL_SENSITIVITY', confirmatoryStep7=False,
                   sourceCommit='22309460eb0b19ee5d99c7d94d099b7b23b64e8f',
                   semanticJudgmentsPerformed=False, historicalResearcherJudgmentsUsed=False,
                   builderReuse={'path': str(Path(original.__file__).relative_to(ROOT)), 'sha256': BUILDER_SHA,
                                 'onlyCodeSubstitution': {'from': OLD_GUARD, 'to': NEW_GUARD},
                                 'adaptedFunctionSha256': sha256_bytes(source.encode())})
    package['modelSpecificStrictEvaluation'] = package.pop('correctedStrictEvaluation')
    package['modelSpecificPredictionAuthority'] = {**package.pop('correctedPredictionAuthority'),
                                                  'path': str(evaluation.PREDICTIONS.relative_to(ROOT)),
                                                  'realizationID': evaluation.REALIZATION}
    metrics = package['secondaryMetricDefinitions']
    metrics['predictionSourceSupportedRate'] = metrics.pop('correctedPredictionSourceSupportedRate')
    metrics['predictionSourceSupportedRate']['numerator'] = 'supported_as_proposed GPT-6.1 predictions'
    package['counts']['modelSpecificPredictionAssertions'] = package['counts'].pop('correctedPredictionAssertions')
    for field, record_field, passes, prefix in [
        ('correspondenceReviewItems', 'humanCoreRecord', {'node': 'A', 'relation': 'C'}, 'gpt61-correspondence'),
        ('predictionSourceSupportReviewItems', 'predictionRecord', {'node': 'B', 'relation': 'D'}, 'gpt61-source-support'),
    ]:
        for item in items(package, field):
            record = item[record_field]
            item['reviewPass'] = passes[record['kind']]
            item['reviewItemID'] = original.prior._item_id(prefix, record['key'])
    passes = Counter(item['reviewPass'] for field in ('correspondenceReviewItems', 'predictionSourceSupportReviewItems')
                     for item in items(package, field))
    require(dict(passes) == {'A': 118, 'B': 127, 'C': 61, 'D': 67}, 'REVIEW_PASS_POPULATION_DRIFT')
    package['reviewPassCounts'] = dict(sorted(passes.items()))
    require(package['counts']['reviewItems'] == 373, 'REVIEW_TOTAL_DRIFT')
    assert_neutral(package)
    return package


def preservation() -> dict[str, str]:
    """Snapshot historical bytes and already-published GPT-6.1 files, without audits."""
    pins = extraction.preserved_pins()
    pins.update(extraction.file_pins([p for p in extraction.OUTPUT.iterdir()
                                      if p.is_file() and p not in (OUTPUT, REPORT)]))
    return pins


def render_report(package: dict[str, Any]) -> str:
    """Summarize the neutral review population and immutable authority bindings."""
    return '\n'.join([
        '# GPT-6.1 Human Core N=5 — Neutral Secondary Review Instrument', '',
        '**RESEARCHER_REVIEW_PENDING — POST-HOC MODEL SENSITIVITY.** Uses the corrected Step 7 builder and frozen protocol v0.1.1; not a new confirmatory Step 7.', '',
        '| Pass | Population | Count |', '|---|---|---:|',
        '| A | Human Core node correspondence | 118 |', '| B | GPT-6.1 node source support | 127 |',
        '| C | Human Core relation correspondence | 61 |', '| D | GPT-6.1 relation source support | 67 |',
        '| Total | All review items | 373 |', '',
        'Strict true positives are included: 32 node pairs and 7 relation pairs, each present in correspondence and independent source-support review.', '',
        'All reviewer dispositions, selected keys, explanatory codes, notes and secondary metric values are null. No judgments, equivalence rescue, source-support inference, scoring or provider calls were performed.', '',
        'Fully qualified model-specific prediction identities, structural candidate buckets, exact relation endpoint context, explanatory-code definitions and global one-to-one validation are inherited from the existing instrument.', '',
        f'Strict evaluation SHA-256: `{STRICT_SHA}`.',
        f'Prediction inputs SHA-256: `{PREDICTIONS_SHA}`.',
        f'Protocol v0.1.1 SHA-256: `{PROTOCOL_SHA}`.', '',
        'Historical protocol population numbers remain unchanged in that document; this model-specific binding uses the authorized GPT-6.1 denominators above. GPT-5.6’s 356-item instrument, judgments, secondary results and Step 7C/Step 8 artifacts are preserved.', '',
    ])


def run(verify: bool = False) -> dict[str, Any]:
    """Write new neutral artifacts once, or verify exact deterministic reproduction."""
    before = preservation()
    package = build_package()
    outputs = {OUTPUT: canonical_json(package) + b'\n', REPORT: render_report(package).encode()}
    for path, data in outputs.items():
        if path.exists():
            require(path.read_bytes() == data, 'REVIEW_OUTPUT_CONFLICT:' + path.name)
        else:
            require(not verify, 'MISSING_REVIEW_OUTPUT:' + path.name)
    require(preservation() == before, 'HISTORICAL_BYTE_DRIFT')
    for path, data in outputs.items():
        if not path.exists():
            with path.open('xb') as handle:
                handle.write(data)
    require(preservation() == before, 'HISTORICAL_BYTE_DRIFT')
    return package


def main() -> None:
    """Run only offline neutral instrument construction; there is no live option."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_NO_NETWORK')):
        package = run(args.verify)
    print(json.dumps({'passes': package['reviewPassCounts'], 'total': package['counts']['reviewItems'],
                      'jsonSha256': original._sha256(OUTPUT), 'reportSha256': original._sha256(REPORT),
                      'providerCalls': 0}, indent=2))


if __name__ == '__main__':
    main()
