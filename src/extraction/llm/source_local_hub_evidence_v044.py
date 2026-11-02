"""Opt-in 0.4.4 lexical overlay; historical 0.4.1 file and binders remain pinned.

The scanner below is the historical scanner with one structural correction:
lexically complete lowercase HTML void tags cannot open child-content scopes.
The tags themselves remain opaque. Mismatches and unknown scopes stay fail-closed.
"""
from contextlib import contextmanager
import re
from unittest.mock import patch
from src.extraction.llm import source_local_hub_evidence as historical

VERSION = 'hub-lexical-classifier/0.4.4'
_ORIGINAL_BINDER = historical.binder
STATIC_TAGS = historical.STATIC_TAGS
VOID_TAGS = frozenset({'area','base','br','col','embed','hr','img','input','link',
                       'meta','param','source','track','wbr'})


def is_void(name: str, attrs: str) -> bool:
    """Recognize complete static attribute syntax, not attribute admissibility.

Unknown attributes still make the tag opaque. Braces, unfinished quotes and
malformed attribute syntax do not receive the scope correction.
    """
    attribute = r"""[A-Za-z_:][\w:.-]*(?:\s*=\s*(?:"[^"{}<>]*"|'[^'{}<>]*'|[^\s\"'`=<>/{}]+))?"""
    return name in VOID_TAGS and bool(re.fullmatch(r'(?:'+attribute+r'(?:\s+|$))*',attrs))


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
            elif not selfclose and not is_void(name,attrs):stack.append((name,i,safe))
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
    """Preserve the binding-contract version while labeling corrected lexical provenance."""
    with patch.object(historical,'regions',regions):
        bind=_ORIGINAL_BINDER(inputs)
    def corrected_bind(*args,**kwargs):
        """Add explicit interpretation provenance without changing exact span binding."""
        result=bind(*args,**kwargs)
        result['lexicalClassifierVersion']=VERSION
        for span in result['evidenceSpans']:span['lexicalClassifierVersion']=VERSION
        return result
    return corrected_bind


@contextmanager
def overlay():
    """Temporarily reuse the original exact binder with only versioned lexical logic."""
    with patch.object(historical,'binder',binder):
        yield
