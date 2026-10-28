"""v0.4.1 lexical MDX admissibility over exact full-page authority, without rendering.

This is a conservative visibility check, not a scientific semantic validator.
Unknown components/attributes and executable regions remain opaque. Historical
reader units are used only to verify source provenance, never as a coverage gate.
"""
from copy import deepcopy
import re

from src.extraction.llm.pilot_preflight import digest
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans

VERSION = 'hub-full-authority-admissibility/0.4.1'
STATIC_TAGS = {'p','strong','em','b','i','ul','ol','li','table','thead','tbody','tr','td','th',
               'blockquote','div','span','section','article','a','h1','h2','h3','h4','h5','h6'}


def regions(text: str) -> list[str]:
    """Classify exact character positions; never evaluate expressions or normalize text."""
    marks=['prose']*len(text)
    def mark(lo,hi,kind):
        """Keep lexical region coordinates in the original authority."""
        marks[lo:hi]=[kind]*(hi-lo)
    # Line-level opaque blocks are recognized before inline Markdown/JSX syntax.
    lines=text.splitlines(keepends=True);offsets=[];pos=0
    for line in lines:offsets.append(pos);pos+=len(line)
    offsets.append(pos);i=0
    from src.extraction.llm.documents.source_units import _dynamic_end
    while i<len(lines):
        line=lines[i];start=i;i+=1
        if start==0 and line.strip()=='---':
            while i<len(lines) and lines[i].strip() not in {'---','...'}:i+=1
            i=min(len(lines),i+1);mark(offsets[start],offsets[i],'metadata');continue
        fence=re.match(r'^ {0,3}(`{3,}|~{3,})',line)
        if fence:
            token=fence.group(1)
            while i<len(lines) and not re.fullmatch(r' {0,3}'+re.escape(token[0])+r'{'+str(len(token))+r',}\s*',lines[i]):i+=1
            closed=i<len(lines);i=min(len(lines),i+1)
            mark(offsets[start],offsets[i],'example' if closed else 'uncertain');continue
        if re.match(r'^\s*(?:import|export)\b',line):
            i=_dynamic_end(lines,start);mark(offsets[start],offsets[i],'dynamic');continue
        if line.startswith(('    ','\t')):
            mark(offsets[start],offsets[i],'code');continue
        if re.match(r'^ {0,3}#{1,6}\s',line):mark(offsets[start],offsets[i],'heading')
    stack=[];i=0
    while i<len(text):
        if marks[i] not in {'prose','heading'}:i+=1;continue
        if text.startswith('<!--',i) or text.startswith('{/*',i):
            endtoken='-->' if text.startswith('<!--',i) else '*/}'
            end=text.find(endtoken,i+3);end=len(text) if end<0 else end+len(endtoken)
            mark(i,end,'comment');i=end;continue
        if text[i]=='{':
            # Balanced lexical expression, with quoted strings/comments kept opaque.
            j=i+1;depth=1;quote=None;escape=False
            while j<len(text) and depth:
                c=text[j]
                if quote:
                    if escape:escape=False
                    elif c=='\\':escape=True
                    elif c==quote:quote=None
                elif text.startswith('/*',j):
                    end=text.find('*/',j+2);j=len(text) if end<0 else end+2;continue
                elif text.startswith('//',j):
                    end=text.find('\n',j+2);j=len(text) if end<0 else end;continue
                elif c in '\"\'`':quote=c
                elif c=='{':depth+=1
                elif c=='}':depth-=1
                j+=1
            mark(i,j,'dynamic');i=j;continue
        if text[i]=='`':
            match=re.match(r'`+',text[i:]);token=match.group();end=text.find(token,i+len(token))
            end=len(text) if end<0 else end+len(token)
            mark(i,end,'inline_code');i=end;continue
        if text[i]=='<':
            tag=re.match(r'<(/?)([A-Za-z][\w.-]*)([^<>]*?)>',text[i:],re.S)
            if not tag:
                end=text.find('\n',i);end=len(text) if end<0 else end
                mark(i,end,'uncertain');i=end;continue
            close,name,attrs=tag.groups();end=i+tag.end();selfclose=attrs.rstrip().endswith('/')
            attrs=attrs.rstrip().rstrip('/').strip()
            # Explicitly bounded static attributes; style/hidden/event/expression props are not safe.
            attr_pattern=r'''(?:id|href|title)\s*=\s*(?:"[^"{}<>]*"|'[^'{}<>]*')'''
            safe=name in STATIC_TAGS and not re.sub(attr_pattern,'',attrs).strip()
            if name=='Admonition':safe=not attrs or bool(re.fullmatch(r'''type=["'](?:note|tip|info|warning|danger|caution)["']''',attrs))
            if close:
                if stack and stack[-1][0]==name:
                    _,opening,opened_safe=stack.pop()
                    if not opened_safe:mark(opening,end,'uncertain')
                else:mark(0,end,'uncertain')
            elif not selfclose:stack.append((name,i,safe))
            mark(i,end,'markup' if safe else 'uncertain');i=end;continue
        if (i==0 or text[i-1]=='\n') and text.startswith(':::',i):
            end=text.find('\n',i);end=len(text) if end<0 else end
            line=text[i:end].strip()
            if line==':::' and stack and stack[-1][0]==':::':
                _,opening,safe=stack.pop()
                if not safe:mark(opening,end,'uncertain')
            else:stack.append((':::',i,bool(re.fullmatch(r':::(note|tip|info|warning|danger|caution)(?:\s+[^{}<>]+)?',line))))
            mark(i,end,'markup');i=end;continue
        i+=1
    for _,opening,_ in stack:mark(opening,len(text),'uncertain')
    return marks


def binder(inputs: dict):
    """Return a trusted binder with full authority offsets and explicit content role."""
    from src.evaluation.hub_full_content_pilot import verified_reader,full_unit_id,_line
    verified=verified_reader(inputs);page=inputs['page'];text=page['content_mdx'];marks=regions(text)
    provenance={k:deepcopy(v) for k,v in verified['authority'].items() if k!='text'}
    def bind(page_arg,reader,uid,spans,**kwargs):
        """Bind source literals first, then classify their actual lexical region."""
        result=dict(status='evidence_bound',evidenceSpans=[],diagnostics=[],admissibilityVersion=VERSION,explanatoryProse=False)
        def stop(reason,status='needs_review'):
            """Hold without discarding the source quotation or its diagnostics."""
            result.update(status=status,evidenceSpans=[],explanatoryProse=False)
            result['diagnostics'].append(dict(reason=reason,status=status,sourceUnitID=uid));return result
        if page_arg!=page or uid!=full_unit_id(page) or kwargs.get('accepted_page_id')!=inputs['accepted_page_id']:
            return stop('full_authority_identity_mismatch','failed_source_or_evidence_binding')
        if any(d.get('status')=='failed_source_or_evidence_binding' for d in reader['diagnostics']):
            return stop('source_failure_diagnostic','failed_source_or_evidence_binding')
        bound,report=bind_evidence_spans({'evidenceSpans':spans},dict(text=text,startOffsetInDocument=0,
            canonicalArtifactID=inputs['accepted_page_id'],sourceUnitID=uid,textHash=digest(text.encode()),sectionID=None,sectionTitleRaw=None))
        result['bindingReport']=report
        if report['bindingStatus']!='bound':return stop('evidence_quote_unbound','failed_source_or_evidence_binding')
        for span in bound['evidenceSpans']:
            lo,hi=span['startOffsetInDocument'],span['endOffsetInDocument']
            kinds={marks[p] for p in range(lo,hi) if not text[p].isspace()}
            prose=any(marks[p]=='prose' and text[p].isalnum() for p in range(lo,hi))
            if kinds=={'example'}:result['status']='example_context_bound'
            elif kinds-{'prose','heading','inline_code'} or not kinds or (kinds=={'inline_code'}):
                return stop('full_content_not_static_visible:'+','.join(sorted(kinds)))
            result['explanatoryProse'] |= prose
            result['evidenceSpans'].append({**provenance,**span,'startOffsetInAuthority':lo,'endOffsetInAuthority':hi,
                'startLine':_line(text,lo),'endLine':_line(text,hi-1),'admissibilityVersion':VERSION,
                'contentKinds':sorted(kinds),'fullAuthoritySha256':page['content_sha256']})
        return result
    return bind
