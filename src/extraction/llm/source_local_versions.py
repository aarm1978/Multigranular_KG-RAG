"""Exact structured own-product version authority; no prose-label identity inference."""
from __future__ import annotations
from copy import deepcopy
from pathlib import PurePosixPath
import re

import yaml
try:
    import tomllib
except ImportError:
    import tomli as tomllib

from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans

SUPPORTED = {'citation.cff','pyproject.toml','package.json'}


def fields(path: str, text: str) -> tuple[dict, dict]:
    """Parse only own-product root fields and locate their exact literal version value."""
    name=PurePosixPath(path).name.lower();offset=0;section=text
    if name=='citation.cff':
        parsed=yaml.safe_load(text)
        if not isinstance(parsed,dict) or len(re.findall(r'^title:',text,re.M))!=1:
            raise ValueError('ambiguous_structured_product')
        values={'title':parsed.get('title'),'version':parsed.get('version')}
        pattern=r'^version:[ \t]*[\'\"]?([^\r\n\'\"#]+)[\'\"]?[ \t]*$'
    elif name=='pyproject.toml':
        parsed=tomllib.loads(text)
        options=[(k,v) for k,v in [('project',parsed.get('project',{})),('tool.poetry',parsed.get('tool',{}).get('poetry',{}))] if isinstance(v.get('version'),str)]
        if len(options)!=1:
            raise ValueError('ambiguous_or_dynamic_structured_version')
        key,record=options[0];values={'title':record.get('name'),'version':record.get('version')}
        heading=re.search(r'^\['+re.escape(key)+r'\][ \t]*(?:#[^\n]*)?$',text,re.M)
        if heading is None:raise ValueError('structured_section_missing')
        offset=heading.end();next_section=re.search(r'^\s*\[',text[offset:],re.M)
        section=text[offset:offset+next_section.start()] if next_section else text[offset:]
        pattern=r'^[ \t]*version[ \t]*=[ \t]*[\'\"]([^\r\n\'\"]+)[\'\"][ \t]*(?:#[^\n]*)?$'
    elif name=='package.json':
        from src.extraction.llm.publications.batch_transport import decode
        parsed=decode(text.encode())
        if not isinstance(parsed,dict):raise ValueError('structured_package_not_object')
        values={'title':parsed.get('name'),'version':parsed.get('version')}
        # Ambiguous nested occurrences are held rather than assigned an arbitrary offset.
        pattern=r'"version"\s*:\s*"([^"\\]+)"'
    else:raise ValueError('unsupported_structured_version_format')
    if any(not isinstance(v,str) or not v.strip() for v in values.values()):
        raise ValueError('structured_version_fields_missing')
    matches=list(re.finditer(pattern,section,re.M))
    if len(matches)!=1 or matches[0].group(1).strip()!=values['version']:
        raise ValueError('ambiguous_structured_version_literal')
    match=matches[0]
    return values,{'start':offset+match.start(1),'end':offset+match.end(1)}


def unit(authority: dict, owner: dict) -> dict:
    """Expose hash-pinned structured version evidence, not general config/code semantics."""
    path=PurePosixPath(authority.get('path',''))
    if (path.is_absolute() or '..' in path.parts or path.name.lower() not in SUPPORTED
            or authority.get('authorityKind') != 'downloaded_file'
            or authority.get('rawFileSha256') != digest(authority['text'].encode())
            or authority.get('authorityTextSha256') != digest(authority['text'].encode())
            or any(authority.get(k) != owner[k] for k in ('canonicalArtifactID','repo_id','full_name','frozenCommitSha'))):
        raise ValueError('structured_version_authority_invalid')
    values,location=fields(str(path),authority['text'])
    return {**deepcopy(authority),'sourceUnitID':'github:version-authority:'+digest(canonical(authority)),
            'contentKind':'structured_own_product_version','startOffsetInAuthority':0,
            'endOffsetInAuthority':len(authority['text']),'startLine':1,
            'endLine':len(authority['text'].splitlines()),'structuredFields':values,'versionField':location}


def binder(reader: dict, uid: str, spans: list, *, accepted_repository: dict) -> dict:
    """Delegate documentary text; bind exact structured fields without code inference."""
    from src.evaluation.github_full_document_pilot import bind_document_evidence
    found=[u for u in reader['sourceUnits'] if u['sourceUnitID']==uid and u.get('contentKind')=='structured_own_product_version']
    if not found:
        return bind_document_evidence(reader,uid,spans,accepted_repository=accepted_repository)
    if len(found)!=1:
        raise ValueError('ambiguous_version_authority')
    u=found[0];a=next(a for a in reader['versionAuthorities'] if unit(a,accepted_repository)==u)
    bound,report=bind_evidence_spans({'evidenceSpans':spans},dict(text=a['text'],startOffsetInDocument=0,
        canonicalArtifactID=u['canonicalArtifactID'],sourceUnitID=uid,textHash=u['authorityTextSha256'],sectionID=None,sectionTitleRaw=None))
    result=dict(status='evidence_bound' if report['bindingStatus']=='bound' else 'failed_source_or_evidence_binding',
                diagnostics=[] if report['bindingStatus']=='bound' else [dict(reason='evidence_quote_unbound')],evidenceSpans=[])
    for e in bound.get('evidenceSpans',[]):
        result['evidenceSpans'].append({**{k:v for k,v in u.items() if k!='text'},**e,
            'startOffsetInAuthority':e['startOffsetInDocument'],'endOffsetInAuthority':e['endOffsetInDocument']})
    return result
