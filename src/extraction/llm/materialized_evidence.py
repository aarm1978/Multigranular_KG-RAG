"""Opt-in materialized-corpus eligibility; no rendering or semantic adjudication.

Historical entry points remain defaults. The scoped overlay is single-threaded,
restores all dispatch hooks, and never rewrites prepared requests or responses.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from functools import wraps
import json
import re
from pathlib import Path
from unittest.mock import patch
from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans

AUTHORITY = 'study2-materialized-corpus-evidence/0.1.0'
VERSION = 'source-local-materialized-evidence/0.5.0'
CONTRACT = 'docs/study2_materialized_corpus_evidence_amendment_v0.1.md'


def hub_binder(inputs: dict):
    """Verify the historical source authority, then bind original content_mdx offsets."""
    from src.evaluation.hub_full_content_pilot import verified_reader, full_unit_id, _line
    verified = verified_reader(inputs)
    page = inputs['page']; text = page['content_mdx']
    provenance = {k: deepcopy(v) for k, v in verified['authority'].items() if k != 'text'}

    def bind(page_arg, reader, uid, spans, **kwargs):
        """Literal availability is distinct from the validator's pending semantic gates."""
        result = dict(status='failed_source_or_evidence_binding', evidenceSpans=[], diagnostics=[],
                      materializedEvidence=True, evidenceAuthority=AUTHORITY, semanticStatus='not_evaluated')
        if (page_arg != page or uid != full_unit_id(page) or
                kwargs.get('accepted_page_id') != inputs['accepted_page_id']):
            result['diagnostics'] = [dict(reason='full_authority_identity_mismatch', status=result['status'])]
            return result
        if not isinstance(spans, list) or not spans or any(not isinstance(s, dict) or
                set(s)-{'evidenceText', 'locatorAnchor'} for s in spans):
            result['diagnostics'] = [dict(reason='invalid_or_model_authored_evidence_metadata', status=result['status'])]
            return result
        if any(d.get('status') == 'failed_source_or_evidence_binding' for d in reader['diagnostics']):
            result['diagnostics'] = [dict(reason='source_failure_diagnostic', status=result['status'])]
            return result
        bound, report = bind_evidence_spans({'evidenceSpans': spans}, dict(text=text, startOffsetInDocument=0,
            canonicalArtifactID=inputs['accepted_page_id'], sourceUnitID=uid, textHash=digest(text.encode()),
            sectionID=None, sectionTitleRaw=None))
        result['bindingReport'] = report
        if report['bindingStatus'] != 'bound':
            result['diagnostics'] = [dict(reason='evidence_quote_unbound', status=result['status'])]
            return result
        result['status'] = 'evidence_bound'
        for span in bound['evidenceSpans']:
            lo, hi = span['startOffsetInDocument'], span['endOffsetInDocument']
            result['evidenceSpans'].append({**provenance, **span, 'startOffsetInAuthority': lo,
                'endOffsetInAuthority': hi, 'startLine': _line(text, lo), 'endLine': _line(text, hi-1),
                'fullAuthoritySha256': page['content_sha256']})
        return result
    return bind


def github_binding(original, *args, **kwargs):
    """Keep native documentary binding and diagnostics; remove only its format hold."""
    result = original(*args, **kwargs)
    if (result['status'] == 'needs_review' and result['diagnostics'] ==
            [dict(reason='code_only_cannot_establish_semantics')]):
        result = deepcopy(result)
        result.update(status='evidence_bound', diagnostics=[])
    return result


@contextmanager
def overlay():
    """Activate the amended route explicitly; preserve structured ModelVersion binding."""
    from src.extraction.llm import source_local_semantics as local
    from src.extraction.llm.documents import candidate_validation as hub
    from src.evaluation import github_full_document_pilot as github
    native = hub.validate_hub_candidates
    documentary = github.bind_document_evidence

    @wraps(native)
    def validate(*args, **kwargs):
        """Keep all semantic and parent gates; only change evidence-form eligibility."""
        return native(*args, **kwargs, materialized_evidence=True)

    with ExitStack() as stack:
        stack.enter_context(patch.object(local, '_hub_binder', hub_binder))
        stack.enter_context(patch.object(hub, 'validate_hub_candidates', validate))
        stack.enter_context(patch.object(github, 'bind_document_evidence',
            side_effect=lambda *a, **k: github_binding(documentary, *a, **k)))
        yield


def instructions(family: str, shared: list[str]) -> list[str]:
    """Compose a new prompt without mutating calibrated historical instruction tuples."""
    from src.extraction.llm.source_local_prompts import instructions as historical
    rows = historical(family, shared)
    replacements = {
        'Source-grounded admissibility still excludes code-only/dynamic/uncertain semantic evidence.':
            'Literal materialized content is eligible regardless of rendering, wrappers, comments or format.',
        'hidden, dynamic or unavailable content leaves a gap': 'content absent from the materialized source leaves a gap',
        'A displayed fence may support only a literal possible Example with independently supported procedural attachment; never infer its execution, code semantics or parameters.':
            'A materialized example may support an Example with independently supported procedural attachment. Consider literal explanatory content regardless of format; never infer execution, unsupported behavior or parameters from unexplained syntax.',
    }
    for old, new in replacements.items():
        rows = [row.replace(old, new) for row in rows]
    # Retain the requirement for explanation, without making its surface format a gate.
    rows = [re.sub(r'\bprose\b', 'explanatory text', row.replace('prose-grounded', 'explicit-content-grounded')
            .replace('prose-characterized', 'explicitly characterized')) for row in rows]
    rows.append('Evidence authority: '+AUTHORITY+'. Literal content in authorized materialized units, including all tabs, incorporated text, comments, unfamiliar or malformed wrappers and mixed prose/code/configuration, is eligible for consideration. Do not infer absent outputs, execution or scientific results. Interpret hypothetical, planned, conditional, negated, deprecated and commented-out behavior in context, never automatically as current implementation. Exact grounding alone does not establish semantic support. Preserve every independent ontology, identity, endpoint, parent, dependency, duplicate and provenance requirement.')
    return rows


def build(templates: list[dict], **kwargs) -> dict:
    """Prepare a prospective owner context with new prompt and authority hashes only."""
    from src.extraction.llm import source_local_semantics as local
    with patch.object(local, 'family_instructions', instructions):
        prepared = local.build(templates, **kwargs)
    request = deepcopy(prepared['semanticRequest'])
    request['request'].update(promptIdentifier=VERSION, evidenceAuthority=AUTHORITY,
        evidenceAuthoritySha256=digest((Path(__file__).resolve().parents[3]/CONTRACT).read_bytes()))
    request['requestSha256'] = digest(json.dumps(request['request'],ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    with prospective():
        return local.prepare_request(request, deepcopy(prepared['requestInputs']))


def build_specialized(templates: list[dict], **kwargs) -> list[dict]:
    """Use unchanged specialized groups and schemas on the prospective owner context."""
    from src.extraction.llm import source_local_specialized as specialized
    context = build(templates, **kwargs)
    family = context['semanticRequest']['request']['artifactFamily']
    with prospective():
        return [specialized.build(context, group, provider_projection_version=specialized.PROVIDER_PROJECTION_VERSION)
                for group in specialized.inventory(family)]


@contextmanager
def prospective():
    """Explicit preparation/verification context for new envelopes, never historical ones."""
    from src.extraction.llm import source_local_semantics as local, source_local_specialized as specialized
    with patch.object(local, 'family_instructions', instructions), patch.object(specialized, 'VERSION', VERSION), \
            patch.object(specialized, 'CONTRACT', Path(__file__).resolve().parents[3]/CONTRACT):
        yield


def stamp_report(report: dict) -> dict:
    """Label derived authority explicitly and recompute report hashes, not source hashes."""
    report = deepcopy(report)
    if 'nativeValidationView' in report:
        report['nativeValidationView'] = stamp_report(report['nativeValidationView'])
    report.update(validationPolicyVersion=VERSION, evidenceAuthority=AUTHORITY,
        evidenceAuthoritySha256=digest((Path(__file__).resolve().parents[3]/CONTRACT).read_bytes()))
    report.pop('reportSha256', None)
    report['reportSha256'] = digest(canonical(report))
    return report


def replay_specialized(prepared: dict, raw: bytes, *, expected_request_sha256: str) -> dict:
    """Explicit future-envelope replay; historical envelopes use only overlay()."""
    from src.extraction.llm import source_local_specialized as specialized
    with prospective(), overlay():
        return stamp_report(specialized.replay(prepared, raw, expected_request_sha256=expected_request_sha256))
