"""Step 14 queue binding to unchanged Publications Batch journal and transport."""
from __future__ import annotations
import argparse
import base64
from collections import Counter
import json
from pathlib import Path
import socket
from unittest.mock import patch
from src.evaluation import step14_semantic_calibration as c
from src.extraction.llm import source_family_batch as shared
from src.extraction.llm.publications import full_corpus_gpt61_batch as b
from src.extraction.llm.publications import batch_transport as transport
from src.extraction.llm.publications.batch_journal import batch_journal

ROOT=Path('var/study2_step14/production-batch/v1')
DOC=Path('docs/study2_step14_production_recommendations_v0.1.md')
VERSION='step14-production-recommendations/0.1.0'
INSTRUCTIONS=c.p.PROMPT+'\n'+c.CLARIFICATION
CAPACITY=15_000_000_000
encode=b.canonical_json
sha=b.sha256_bytes
require=b.require


def fingerprint(p: dict) -> dict:
    """Bind exact scientific unit, pair membership and provider body."""
    return dict(requestID=p['request']['requestID'],bodySha256=sha(encode(p['body'])),bindingSha256=sha(encode(p['binding'])))


def prepared(uid: str, context: dict, binding: dict) -> dict:
    """Project only the already-approved compact context and selected instructions."""
    require(c.r.candidates.token(context)==binding['contextSha256'],'CONTEXT_DRIFT')
    require(set(binding['pairs'])=={x['id'] for x in context['pairs']},'PAIR_BINDING_DRIFT')
    payload=c.p.project(context);rid='step14:'+uid
    body=dict(model=c.live.MODEL,reasoning={'effort':'medium'},store=False,max_output_tokens=16384,
        instructions=INSTRUCTIONS,input=c.live.encode(payload).decode(),text={'format':{'type':'json_schema','name':'step14_pair_recommendation','strict':True,'schema':c.p.schema_for(uid,payload)}})
    return dict(request={'requestID':rid},body=body,binding=binding)


def packed(lines):
    """Yield whole native JSONL lines under both established operational limits."""
    chunk=[];size=0
    for line in lines:
        require(line.endswith(b'\n') and len(line)<=b.MAX_BYTES,'OVERSIZED_OR_INCOMPLETE_LINE')
        if chunk and (size+len(line)>b.MAX_BYTES or len(chunk)>=b.MAX_REQUESTS):yield b''.join(chunk);chunk=[];size=0
        chunk.append(line);size+=len(line)
    if chunk:yield b''.join(chunk)


def prepare(root: Path) -> dict:
    """Offline immutable production binding and serialized-envelope size preflight."""
    require(not root.exists(),'FRESH_OUTPUT_REQUIRED');pins={}
    c.r.preflight.pilot.verify(c.p.SOURCE/'manifest.json',c.p.SOURCE_SHA,pins)
    queue=c.live.load(c.p.SOURCE/'manifest.json')
    for name,h in queue['outputHashes'].items():c.r.preflight.pilot.verify(c.p.SOURCE/name,h,pins)
    # Preserve historical calibrations without making their recommendations selection inputs.
    for v,expected in (('v1',83),('v2',89),('v3',39)):
        prior=c.ROOT/v
        if v=='v3':
            from src.evaluation import step14_category_calibration as category
            category.verify(prior)
        else:c.verify(prior)
        report=c.live.load(prior/'report.json');stage='development' if v=='v1' else 'held-out'
        require(report['stages'][stage]['matchedPairs']==expected,'CALIBRATION_INCOMPLETE')
        for path in prior.rglob('*'):
            if path.is_file() and path.name!='.execution.lock':pins[str(path)]=c.r.identity.sha(path)
    paired,native,generators=shared.infrastructure()
    modules=(Path(__file__),DOC,Path(shared.__file__),Path(b.__file__),Path(transport.__file__),Path(c.__file__),Path(c.p.__file__),Path(c.live.__file__),Path(c.live.provider.__file__),c.p.SCHEMA,
        Path('src/extraction/llm/publications/batch_journal.py'),Path('src/extraction/llm/publications/resumable_production_journal.py'),Path(b.baseline.__file__))
    for path in modules:pins[str(path)]=c.r.identity.sha(path)
    bindings={x['unitID']:x for x in c.r.rows(c.p.SOURCE/'unit-bindings.jsonl')}
    root.mkdir(parents=True);entries=[];seen=set();files=[];total=0
    def lines():
        """Stream prepared records and exact lines, retaining only compact metadata."""
        nonlocal total
        for row in c.r.rows(c.p.SOURCE/'contexts.jsonl'):
            uid=row['unitID'];p=prepared(uid,row['payload'],bindings[uid]);pairs=set(p['binding']['pairs'].values())
            require(len(pairs)==len(row['payload']['pairs']) and not seen.intersection(pairs),'DUPLICATE_PAIR');seen.update(pairs)
            path=root/'requests'/f'{uid}.json';c.live.save(path,p)
            item,line=b.input_line(p,1,fingerprint);estimate=(len(encode(p['body']))+3)//4;total+=estimate
            entries.append(dict(identity=fingerprint(p),path=str(path),preparedSha256=c.r.identity.sha(path),pairs=len(pairs),customID=item['custom_id'],lineBytes=len(line),localEstimatedInputTokens=estimate,
                estimatedCostUSD=(estimate*1.25+16384*5)/1e6))
            yield line
    for i,data in enumerate(packed(lines()),1):
        path=root/'offline-files'/f'input-{i:06}.jsonl';c.live.write(path,data)
        files.append(dict(path=str(path),bytes=len(data),sha256=sha(data),requests=data.count(b'\n')))
    require(len(entries)==14549,'UNIT_COVERAGE_DRIFT')
    require(len({e['identity']['requestID'] for e in entries})==len(entries),'DUPLICATE_REQUEST')
    preflight=dict(version=VERSION,requests=len(entries),queuedPairs=len(seen),files=files,totalBytes=sum(x['bytes'] for x in files),
        selectedInstructionsSha256=sha(INSTRUCTIONS.encode()),localEstimatedInputTokens=total,
        tokenBasis='ceil(serialized complete provider body UTF-8 bytes / 4), local proxy; not provider counts',
        configuredCapacity=CAPACITY,availableCapacity=None,providerCounts=0,submittedBatches=0,
        readiness='offline_prepared; provider token verification and capacity reconciliation required',
        poolAccounting=c.live.load(c.p.SOURCE/'summary.json'))
    for path,h in pins.items():c.r.preflight.pilot.verify(Path(path),h,{})
    mf=dict(version=VERSION,requests=entries,generatorPins=generators,implementationPins=pins,queuedTokenLimit=CAPACITY,
        meaningfulSampleRequests=100,maximumAttemptsPerRequest=1,kgAuthorized=False,selectedInstructionsSha256=sha(INSTRUCTIONS.encode()),offlineFiles=files)
    c.live.save(root/'run-manifest.json',mf);c.live.save(root/'preflight.json',preflight)
    return preflight


def verify(root: Path) -> dict:
    """Verify immutable implementation, prepared requests, and offline sealed files."""
    m=c.live.load(root/'run-manifest.json');require(m['version']==VERSION,'VERSION_DRIFT')
    require(m['selectedInstructionsSha256']==sha(INSTRUCTIONS.encode()),'INSTRUCTION_DRIFT')
    for path,h in m['implementationPins'].items():c.r.preflight.pilot.verify(Path(path),h,{})
    for e in m['requests']:
        c.r.preflight.pilot.verify(Path(e['path']),e['preparedSha256'],{})
        p=c.live.load(Path(e['path']));require(fingerprint(p)==e['identity'],'REQUEST_DRIFT')
        require(p['body']['instructions']==INSTRUCTIONS,'WRONG_INSTRUCTIONS')
    for f in m['offlineFiles']:c.r.preflight.pilot.verify(Path(f['path']),f['sha256'],{})
    return m


def process(p: dict,receipt: dict,n: int,first=None) -> dict:
    """Strict native pair validation, no semantic repair, retry or identity approval."""
    result=dict(processable=False,retryEligible=False,status='provider_incomplete_or_failed',identityApproved=False)
    response=receipt['providerResponse'] or {}
    if response.get('status')=='completed' and receipt.get('rawModelOutputBase64'):
        try:
            value=transport.decode(base64.b64decode(receipt['rawModelOutputBase64']))
            validation=c.p.validate(value,p['body']);result.update(processable=True,status='validated_recommendation_only',validation=validation,recommendations=value)
        except (ValueError,KeyError,TypeError) as exc:result.update(status='validation_failed',errorType=type(exc).__name__)
        except Exception as exc:
            from jsonschema import ValidationError
            if not isinstance(exc,ValidationError):raise
            result.update(status='validation_failed',errorType=type(exc).__name__)
    return result


class API(transport.BatchAPI):
    """Native transport with Step 14 top-level instructions included in token counting."""
    def count(self,body: dict) -> dict:
        """Count all model input components; no generation or omitted instructions."""
        payload={k:body[k] for k in ('model','instructions','input','reasoning','text')}
        value=transport.decode(self.request('POST','/responses/input_tokens',encode(payload),safe=True))
        require(value.get('object')=='response.input_tokens' and type(value.get('input_tokens')) is int and value['input_tokens']>0,'INVALID_INPUT_TOKEN_COUNT');return value


def operate(root: Path,mode: str) -> dict:
    """Reuse native journal, reservations, once-only submission and result reconciliation."""
    m=verify(root);paired,native,_=shared.infrastructure()
    def check(p,e):
        require(fingerprint(p)==e['identity'],'PREPARED_DRIFT')
    def outcome(p,receipt,value,n):
        require(value==process(p,receipt,n),'OUTCOME_DRIFT')
    def record(row,p,bid,n):return b.response_record(row,p,paired,bid,n)
    def receipt(p,value):require(value==record(value['row'],p,value['batchID'],value['number']),'RECEIPT_DRIFT')
    Journal=batch_journal(native,check,fingerprint,outcome,receipt)
    data=(root/'run-manifest.json').read_bytes()
    with Journal(root/'execution.jsonl',data,sha(data)) as log:
        if mode=='status':return status(log)
        api=API(c.live.provider.load_openai_api_key())
        if mode=='count':
            for rid,e in log.entries.items():
                if rid not in log.state:log.append('prepared',rid,native.bundle(c.live.load(Path(e['path']))))
                if rid not in log.tokens:
                    p=log.prepared(rid);log.append('token_count',rid,dict(provider=api.count(p['body']),bodySha256=fingerprint(p)['bodySha256']))
        elif mode=='submit':
            require(len(log.tokens)==len(log.entries),'VERIFY_ALL_PROVIDER_TOKENS_FIRST')
            b.submit_all(log,api,lambda e:c.live.load(Path(e['path'])),native,fingerprint)
        elif mode=='collect':
            errors=b.collect_once(log,api,process,record)
            if errors:return dict(status=b.save_status(log),errors=errors)
        b.save_status(log)
        return status(log)


def status(log) -> dict:
    """Add exact validated-pair/category and abstention accounting to native status."""
    counts=Counter();states=Counter()
    for offset in log.outcomes.values():
        out=log.payload_at(offset)['native'];states[out['status']]+=1
        for item in out.get('recommendations',{}).get('assessments',[]):counts[item['recommendation']]+=1
    return dict(b.summary(log),recommendationCategories=dict(counts),validationOutcomes=dict(states),validatedPairs=sum(counts.values()),reservedInputTokens=log.reserved_tokens(),availableCapacityUnverified=True)


def main() -> None:
    """Separate offline preparation/status and explicit researcher network gates."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['prepare','verify','status','count','submit','collect']);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--execute',action='store_true');a=parser.parse_args()
    if a.mode in ('count','submit','collect'):
        require(a.execute,'EXPLICIT_NETWORK_GATE_REQUIRED');result=operate(a.root,a.mode)
    else:
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')),patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
            result=prepare(a.root) if a.mode=='prepare' else operate(a.root,'status') if a.mode=='status' else dict(requests=len(verify(a.root)['requests']),status='verified')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
