"""Explicit v0.4.1 reconciliation of calibrated family prompts and approved changes."""
from importlib import import_module

DIRECTORIES={'hydroshare':'datasets','github':'coderepos','ciroh_hub':'documents'}


def instructions(family: str, shared: list[str]) -> list[str]:
    """Retain positive Wave B/C criteria, replacing only superseded source/identity rules."""
    c=import_module('src.extraction.llm.'+DIRECTORIES[family]+'.request_contract')
    # Common evidence, duplicate and abstention criteria were never superseded.
    result=list(shared)+list(c.INSTRUCTIONS[1:4])
    if family=='hydroshare':
        result += [c.INSTRUCTIONS[5],c.INSTRUCTIONS[6],
            'Workflow/C-D22 requires a substantive scientific processing sequence. generatedBy/D-17 requires explicit generation provenance and a valid exact reused or evidence-backed source-local Repository endpoint; never invent identifiers.']
        result += list(c.CLARIFICATION_INSTRUCTIONS)+list(c.WAVE_B_INSTRUCTIONS)
    elif family=='github':
        result += [c.INSTRUCTIONS[5],c.INSTRUCTIONS[6],
            'Distinguish repository usesTool/C-C11, mentionsTool/C-C22, usesModel/C-C21, mentionsModel/C-C23 and implementedBy/D-22. usesDataset/C-C15 requires explicit use of the identifiable source-local DatasetResource or named DatasetMention; a URL or incidental name alone does not establish use. A named DatasetMention with no supported stronger relation may remain an independently evidenced occurrence for pipeline-derived D-26.']
        result += list(c.WAVE_B_INSTRUCTIONS)+list(c.WAVE_C_INSTRUCTIONS)
        result=[x.replace('Preserve every existing ModelVersion and implementsMethod condition and unresolved outcome.',
            'Preserve unresolved Method outcomes. ModelVersion requires the v0.4 structured own-product proof; prose or label matches alone cannot release it.') for x in result]
    else:
        result += [c.INSTRUCTIONS[6],c.INSTRUCTIONS[7],c.INSTRUCTIONS[8],
            'Parameter identity/role requires explanatory prose with quoted wording/value when stated; no inferred defaults or configuration-key mining. No cross-page workflow assembly. Explicit source publication citations support source-local Paper and referencePublication; no external DOI lookup, invented identifier or citation enrichment.']
        result += list(c.WAVE_B_INSTRUCTIONS)+list(c.WAVE_C_INSTRUCTIONS)
    # Historical selection language means the complete supplied authority prospectively,
    # not membership in the old reader's selected passages.
    result=[x.replace('selected README prose','supplied complete README prose')
             .replace('selected prose','supplied source prose')
             .replace('selected targets/units','requested targets/supplied complete source units')
             .replace('hidden, dynamic or unselected content','hidden, dynamic or unavailable content') for x in result]
    result += ['Complete supplied authorities govern context coverage; historical reader-selected passages do not restrict it. Source-grounded admissibility still excludes code-only/dynamic/uncertain semantic evidence. DatasetMention and the explicit prospective signature extensions supersede prior corpus-endpoint-only dataset restrictions; no other role criteria are relaxed.']
    result += list(c.LOCATOR_INSTRUCTIONS)
    return result
