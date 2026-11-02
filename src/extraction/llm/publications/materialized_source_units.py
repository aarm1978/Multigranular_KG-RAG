"""Prospective Publication source-unit eligibility; frozen units remain untouched."""
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch
from . import source_units as historical
from ..materialized_evidence import AUTHORITY

VERSION = 'publication-materialized-source-units/0.1.0'


@contextmanager
def overlay():
    """Remove code-format exclusions only; keep boundaries and non-format safeguards."""
    eligibility = historical._eligibility
    metadata = historical._block_metadata

    def eligible(role, blocks):
        """No code execution or equation/table/visual interpretation is inferred."""
        result = eligibility(role, blocks)
        if result == ('excluded', ['source_code_without_explanatory_prose'], False):
            return 'eligible', [], True
        return result

    def block_metadata(blocks, has_explanatory_prose):
        """Make literal code available, preserving independent source-quality failures."""
        rows = deepcopy(metadata(blocks, has_explanatory_prose))
        for block, row in zip(blocks, rows):
            if block.kind == 'code' and not block.visual_only and not block.needs_review and not row['blockExclusionReasons']:
                row.update(evidenceEligible=True, blockEligibility='eligible')
        return rows

    with patch.object(historical, '_eligibility', eligible), patch.object(historical, '_block_metadata', block_metadata), \
            patch.object(historical, 'CONTRACT_VERSION', VERSION):
        yield


def build_document_units(record, raw, phase_schema, phase_version):
    """Return new units with explicit authority, without writing or replacing any files."""
    with overlay():
        units, report = historical.build_document_units(record, raw, phase_schema, phase_version)
    report = {**report, 'evidenceAuthority': AUTHORITY, 'prospectiveSourceUnitVersion': VERSION}
    return units, report
