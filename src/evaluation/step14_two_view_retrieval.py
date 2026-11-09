"""Versioned Step 14 candidate nomination; never identity adjudication or graph writes."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
from unittest.mock import patch

import yaml
from src.evaluation import step14_embedding_preflight as preflight

identity = preflight.identity
candidates = preflight.candidates
require = preflight.require
VERSION = 'step14-two-view-retrieval/0.1.0'
MODEL = 'text-embedding-3-large'
DIMENSIONS = 3072
ROOT = Path('var/study2_step14/two-view-retrieval')
PREFLIGHT = preflight.ROOT/'v1/manifest.json'
PREFLIGHT_SHA = '8779917e3ab5d086d0605897ffcdd7d3654570b5758ead67023debc2553994d1'
SCOPE = Path('docs/study2_step14_scope_and_completion_decision_v0.1.md')
CONTRACT = Path('docs/study2_step14_two_view_retrieval_v0.1.md')
SCOPES = ('within_artifact', 'within_family_between_artifacts', 'between_families')
VIEWS = ('name', 'evidence')


def load(path: Path) -> dict:
    """Read local JSON only."""
    return json.loads(path.read_bytes())


def write(path: Path, value: dict) -> None:
    """Create an immutable, durable JSON record, including dispatch intents."""
    with path.open('xb') as stream:
        stream.write(identity.encoded(value)+b'\n'); stream.flush(); os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def rows(path: Path):
    """Stream original records without loading full source corpora."""
    yield from preflight.review.json_rows(path)


def digest(text: str) -> str:
    """Hash the exact UTF-8 embedding input."""
    return hashlib.sha256(text.encode()).hexdigest()


def verified_inputs() -> tuple[dict, dict]:
    """Reuse the accepted preflight's direct authority pins without rebuilding it."""
    pins = {}
    preflight.pilot.verify(PREFLIGHT, PREFLIGHT_SHA, pins)
    manifest = load(PREFLIGHT)
    for path, expected in manifest['inputHashes'].items():
        preflight.pilot.verify(Path(path), expected, pins)
    preflight.pilot.verify(Path(preflight.__file__).relative_to(Path.cwd()), manifest['implementationSha256'], pins)
    for path in (SCOPE, CONTRACT, Path('environments/multigranular-kg.yml'), Path(__file__)):
        relative = path.relative_to(Path.cwd()) if path.is_absolute() else path
        preflight.pilot.verify(relative, identity.sha(relative), pins)
    spec = yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())
    require(spec['ontology']['version'] == '0.1.7', 'ONTOLOGY_DRIFT')
    return pins, spec


def project(row: dict, line: int, spec: dict) -> dict:
    """Project literal windows with original evidence pointers, never descriptions."""
    require(candidates.token(row['originalSnapshotRecord']) == row['snapshotRecordSha256'], 'SNAPSHOT_HASH_DRIFT')
    cls = row['ontologyClass']; classes = {c['name']: c for c in spec['classes']}
    active = {'Tool', 'Algorithm', 'Workflow'} | {
        c for c in candidates.descendants(classes, 'ComputationalModel') if not classes[c].get('abstract')}
    labels = sorted(set(candidates.literals(row['labels'])))
    holds = []; flags = list(row['preparationFlags'])
    if row['lane'] != 'semantic_comparison' or cls not in active:
        holds.append('outside_existing_semantic_comparison_lane')
    if cls not in classes or classes[cls]['id'] != row['inventoryId'] or classes[cls].get('abstract'):
        holds.append('incompatible_or_abstract_class')
    if preflight.review.EXCLUDED_FLAGS.intersection(flags):
        holds.append('existing_provenance_or_class_exclusion')
    if len(set(row['sourceFamilies'])) != 1 or not row['sourceArtifacts'] or not row['evidenceReferences']:
        holds.append('missing_or_ambiguous_source_provenance')
    if not labels or not any(s.strip() for s in labels):
        holds.append('missing_labels')
    if any(len(s.strip()) < 3 for s in labels):
        flags.append('short_label_match_requires_context_review')
    if len(labels) > 1:
        flags.append('multiple_original_labels_requires_review')
    if not row['versions']:
        flags.append('version_unspecified_not_identity_or_difference')
    flags.append('granularity_requires_evidence_review')
    options = []
    for index, evidence in enumerate(row['evidenceReferences']):
        quote = evidence.get('evidenceText')
        if not isinstance(quote, str) or not quote.strip():
            continue
        matches = [m for label in labels if label.strip()
                   for m in re.finditer(re.escape(label), quote, re.IGNORECASE)]
        start = max(0, min((m.start() for m in matches), default=0)-160)
        start = min(start, max(0, len(quote)-600)); end = min(len(quote), start+600)
        options.append((not bool(matches), index, dict(
            reference=dict(jsonPointer=f'/evidenceReferences/{index}', evidenceRecordSha256=candidates.token(evidence)),
            fullQuoteSha256=digest(quote), quoteStart=start, quoteEnd=end,
            literalExcerpt=quote[start:end], labelPresent=any(start <= m.start() and m.end() <= end for m in matches))))
    selected = []; used = set()
    for _, _, item in sorted(options):
        if item['literalExcerpt'] not in used and len(selected) < 3:
            selected.append(item); used.add(item['literalExcerpt'])
    if not selected:
        holds.append('missing_literal_evidence')
    elif not any(e['labelPresent'] for e in selected):
        flags.append('weak_context_no_literal_label_match')
    if selected and all(e['literalExcerpt'].strip() in labels for e in selected):
        flags.append('weak_context_label_only')
    prefix = '\n'.join([cls, *labels])
    texts = dict(name=prefix, evidence='\n'.join([prefix, *(e['literalExcerpt'] for e in selected)]))
    # UTF-8 byte count is a conservative upper bound for byte-BPE token counts.
    if any(len(t.encode()) > 8191 for t in texts.values()):
        holds.append('input_exceeds_conservative_8191_byte_limit')
    return dict(occurrenceID=row['occurrenceID'], ontologyClass=cls, inventoryId=row['inventoryId'],
        labels=labels, sourceFamilies=row['sourceFamilies'], sourceArtifacts=row['sourceArtifacts'],
        versions=row['versions'], granularity=row['granularity'], flags=sorted(set(flags)), holds=sorted(set(holds)),
        eligible=not holds, texts=texts, textHashes={v:digest(t) for v,t in texts.items()},
        selectedEvidence=selected, evidenceReferenceCount=len(row['evidenceReferences']),
        originalReference=dict(file=str(preflight.review.INPUT/'occurrences.jsonl'), line=line,
            recordSha256=candidates.token(row), snapshotRecordSha256=row['snapshotRecordSha256'],
            evidencePointer='/evidenceReferences', nativePointer='/nativeReferences', candidatePointer='/originalCandidates'),
        identityDecision=None, automaticMergeEligible=False)


def preview_select(records: list[dict], limit: int = 16) -> list[dict]:
    """Select deterministic diversity representatives, including held/weak contexts."""
    ordered = sorted(records, key=lambda r:digest(r['occurrenceID']))
    selected = {}; covered = set()
    # Mandatory diagnostic strata precede class diversity; no hand-picked IDs.
    for flag in ('weak_context_no_literal_label_match', 'weak_context_label_only',
                 'missing_literal_evidence', 'missing_labels', 'incompatible_or_abstract_class',
                 'multiple_original_labels_requires_review', 'missing_or_ambiguous_source_provenance'):
        match = next((r for r in ordered if flag in r['flags']+r['holds']), None)
        if match and len(selected) < limit: selected[match['occurrenceID']] = match
    versioned = next((r for r in ordered if r['eligible'] and r['versions']), None)
    if versioned and len(selected) < limit: selected[versioned['occurrenceID']] = versioned
    for row in ordered:
        if not row['eligible']: continue
        strata = {('class',row['ontologyClass']), ('family',tuple(row['sourceFamilies']))}
        if strata-covered and len(selected) < limit:
            selected[row['occurrenceID']] = row; covered.update(strata)
    return list(selected.values())


def prepare(output: Path, preview_only: bool = False) -> dict:
    """Verify frozen inventory and write a fresh preview or full embedding preparation."""
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(), 'FRESH_OUTPUT_REQUIRED')
    pins, spec = verified_inputs(); seen = set(); projected = []; inputs = {}
    for line, row in enumerate(rows(preflight.review.INPUT/'occurrences.jsonl'), 1):
        require(row['occurrenceID'] not in seen, 'DUPLICATE_OCCURRENCE'); seen.add(row['occurrenceID'])
        record = project(row, line, spec); projected.append(record)
        if record['eligible']:
            for view, text in record['texts'].items():
                key = record['textHashes'][view]
                require(key not in inputs or inputs[key] == text, 'TEXT_HASH_COLLISION')
                inputs[key] = text
    expected = load(preflight.review.INPUT/'manifest.json')['coverage']['preparedOccurrences']
    require(len(seen) == expected, 'INVENTORY_COUNT_DRIFT')
    output.mkdir(parents=True)
    write(output/'preview.json', dict(selection='SHA256 occurrence order within diagnostic strata, then eligible class/family diversity; maximum 16',
                                     cases=preview_select(projected)))
    summary = dict(occurrences=len(seen), eligible=sum(r['eligible'] for r in projected), uniqueInputs=len(inputs),
        holds=dict(Counter(h for r in projected for h in r['holds'])),
        flags=dict(Counter(f for r in projected for f in r['flags'])),
        eligibleByClass=dict(Counter(r['ontologyClass'] for r in projected if r['eligible'])),
        eligibleByFamily=dict(Counter(r['sourceFamilies'][0] for r in projected if r['eligible'])),
        utf8ByteTokenUpperBound=sum(len(t.encode()) for t in inputs.values()),
        providerCalls=0, newIdentityDecisions=0, graphWrites=0)
    write(output/'summary.json', summary)
    if not preview_only:
        with (output/'occurrences.jsonl').open('xb') as stream:
            for r in projected:
                # Texts reside once in inputs; exact windows and all original pointers remain.
                stream.write(identity.encoded({k:v for k,v in r.items() if k != 'texts'})+b'\n')
        with (output/'inputs.jsonl').open('xb') as stream:
            for key, text in sorted(inputs.items()):
                stream.write(identity.encoded(dict(textSha256=key, text=text))+b'\n')
    for path, expected in pins.items():
        preflight.pilot.verify(Path(path), expected, {})
    manifest = dict(version=VERSION, model=MODEL, dimensions=DIMENSIONS, previewOnly=preview_only,
        inputHashes=pins, outputHashes={p.name:identity.sha(p) for p in sorted(output.iterdir())}, summary=summary)
    write(output/'manifest.json', manifest)
    return summary


def verify_prepared(root: Path) -> tuple[dict, list[dict], list[dict]]:
    """Fail closed on changed authorities, projections, inputs or implementation."""
    manifest = load(root/'manifest.json')
    require(not manifest['previewOnly'] and manifest['version'] == VERSION, 'PREPARATION_REQUIRED')
    require((manifest['model'],manifest['dimensions']) == (MODEL,DIMENSIONS), 'MODEL_CONFIG_DRIFT')
    for path, expected in manifest['inputHashes'].items():
        preflight.pilot.verify(Path(path), expected, {})
    for name, expected in manifest['outputHashes'].items():
        preflight.pilot.verify(root/name, expected, {})
    inputs = list(rows(root/'inputs.jsonl')); records = list(rows(root/'occurrences.jsonl'))
    require(len({i['textSha256'] for i in inputs}) == len(inputs), 'DUPLICATE_INPUT')
    require(all(digest(i['text']) == i['textSha256'] for i in inputs), 'TEXT_HASH_DRIFT')
    return manifest, inputs, records


def batches(inputs: list[dict]):
    """Stable batches bounded by both item count and conservative token ceiling."""
    batch = []; size = 0
    for item in inputs:
        length = len(item['text'].encode())
        require(0 < length <= 8191, 'INVALID_INPUT_LENGTH')
        if batch and (len(batch) == 64 or size+length > 240000):
            yield batch; batch = []; size = 0
        batch.append(item); size += length
    if batch:
        yield batch


def validate_response(response: dict, count: int, dimensions: int = DIMENSIONS) -> None:
    """Check indexed finite vectors; do not silently reorder ambiguous data."""
    import math
    require(response.get('model') == MODEL, 'RESPONSE_MODEL_DRIFT')
    data = response['data']
    require(len(data) == count and sorted(x['index'] for x in data) == list(range(count)), 'RESPONSE_INDEX_DRIFT')
    for item in data:
        vector = item['embedding']
        require(len(vector) == dimensions and all(isinstance(x,(float,int)) and math.isfinite(x) for x in vector)
                and sum(x*x for x in vector) > 0, 'INVALID_VECTOR')


def execute_batch(folder: Path, batch: list[dict], preparation_sha: str, create) -> dict:
    """At most one POST per durable intent; completed batches resume without calls."""
    request = dict(model=MODEL, dimensions=DIMENSIONS, encoding_format='float', input=[x['text'] for x in batch])
    binding = dict(preparationSha256=preparation_sha, requestSha256=candidates.token(request),
                   inputHashes=[x['textSha256'] for x in batch], timeoutSeconds=600, maxRetries=0)
    intent = folder/'intent.json'; outcome = folder/'outcome.json'; response_path = folder/'response.json'
    if intent.exists():
        require(load(intent) == binding, 'INTENT_BINDING_DRIFT')
        require(outcome.exists() and load(outcome)['status'] == 'completed', 'UNCERTAIN_BATCH_STOP_NO_REDISPATCH')
        result = load(outcome)
        require(identity.sha(response_path) == result['responseSha256'], 'RESPONSE_HASH_DRIFT')
        validate_response(load(response_path), len(batch)); return result
    require(not outcome.exists() and not response_path.exists(), 'ORPHAN_RECEIPT_STOP')
    folder.mkdir(parents=True, exist_ok=True)
    write(intent, binding)
    try:
        authentic = create(**request)
        response = authentic.model_dump(mode='json')
        write(response_path, response)
        validate_response(response, len(batch))
        result = dict(status='completed', responseSha256=identity.sha(response_path), usage=response.get('usage'),
                      providerRequestID=getattr(authentic,'_request_id',None))
        write(outcome, result); return result
    except Exception as error:
        # Never serialize exception messages, bodies, URLs, headers or credentials.
        safe = dict(status='uncertain_or_invalid_stop', exceptionType=type(error).__name__)
        for name in ('status_code','errno'):
            value = getattr(error,name,None)
            if isinstance(value,int): safe[name] = value
        if not outcome.exists(): write(outcome, safe)
        raise ValueError('EMBEDDING_STOP_SEE_SANITIZED_OUTCOME') from None


def embed(root: Path, max_batches: int | None = None) -> dict:
    """Researcher-only SDK execution; resume completed batches, never uncertain ones."""
    from openai import OpenAI
    from src.extraction.llm.publications.openai_provider import load_openai_api_key
    _, inputs, _ = verify_prepared(root)
    require(bool(inputs), 'NO_ELIGIBLE_INPUTS')
    directory = root/'embeddings'; directory.mkdir(exist_ok=True)
    with (directory/'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with OpenAI(api_key=load_openai_api_key(), timeout=600, max_retries=0,
                    base_url='https://api.openai.com/v1') as client:
            completed = 0; dispatched = 0
            for index, batch in enumerate(batches(inputs)):
                folder = directory/f'batch-{index:06d}'
                existing = (folder/'intent.json').exists()
                if not existing and max_batches is not None and dispatched >= max_batches: break
                execute_batch(folder,batch,identity.sha(root/'manifest.json'),client.embeddings.create)
                completed += 1; dispatched += int(not existing)
    return dict(completedBatches=completed,newBatches=dispatched)


def pair_scope(left: dict, right: dict) -> str | None:
    """Use exact authoritative memberships, never labels or ID-prefix guesses."""
    if left['occurrenceID'] == right['occurrenceID'] or left['ontologyClass'] != right['ontologyClass']:
        return None
    if set(left['sourceArtifacts']) & set(right['sourceArtifacts']): return SCOPES[0]
    if left['sourceFamilies'] == right['sourceFamilies']: return SCOPES[1]
    return SCOPES[2]


def pair_flags(left: dict, right: dict) -> list[str]:
    """Surface version/granularity ambiguity without deciding identity or difference."""
    flags = ['identity_and_granularity_review_required']
    if left['versions'] and right['versions'] and left['versions'] != right['versions']:
        flags.append('structured_versions_differ_no_automatic_identity')
    if not left['versions'] or not right['versions']: flags.append('version_unspecified')
    return flags


def neighbors(records: list[dict], vectors, indices: dict, top_k: int, query_block: int, target_block: int):
    """Exact cosine top-k separately per view/scope, with bounded score matrices."""
    import numpy as np
    require(top_k > 0 and query_block > 0 and target_block > 0, 'POSITIVE_RETRIEVAL_SETTINGS_REQUIRED')
    groups = defaultdict(list)
    for row in records:
        if row['eligible']: groups[row['ontologyClass']].append(row)
    for cls in sorted(groups):
        group = sorted(groups[cls], key=lambda r:r['occurrenceID'])
        for qstart in range(0,len(group),query_block):
            query = group[qstart:qstart+query_block]
            best = defaultdict(list); pools = Counter()
            qv = {v:np.asarray(vectors[[indices[r['textHashes'][v]] for r in query]]) for v in VIEWS}
            for tstart in range(0,len(group),target_block):
                target = group[tstart:tstart+target_block]
                scores = {v:qv[v] @ np.asarray(vectors[[indices[r['textHashes'][v]] for r in target]]).T for v in VIEWS}
                for qi, left in enumerate(query):
                    scopes = [pair_scope(left,right) for right in target]
                    for scope in SCOPES:
                        eligible = [j for j,s in enumerate(scopes) if s == scope]; pools[qi,scope] += len(eligible)
                        for view in VIEWS:
                            options = best[qi,scope,view]+[(float(scores[view][qi,j]),tstart+j) for j in eligible]
                            best[qi,scope,view] = sorted(options,key=lambda x:(-x[0],x[1]))[:top_k]
            for qi, left in enumerate(query):
                for scope in SCOPES:
                    chosen = sorted({j for view in VIEWS for _,j in best[qi,scope,view]})
                    output = []
                    for j in chosen:
                        right = group[j]
                        scores = {v:float(np.dot(vectors[indices[left['textHashes'][v]]],vectors[indices[right['textHashes'][v]]])) for v in VIEWS}
                        output.append(dict(queryID=left['occurrenceID'], targetID=right['occurrenceID'],
                            ontologyClass=cls, scope=scope, scores=scores,
                            nominatedBy=[v for v in VIEWS if any(k == j for _,k in best[qi,scope,v])],
                            queryReference=left['originalReference'], targetReference=right['originalReference'],
                            queryTextHashes=left['textHashes'], targetTextHashes=right['textHashes'],
                            flags=pair_flags(left,right), identityDecision=None, automaticMergeEligible=False))
                    yield dict(queryID=left['occurrenceID'],scope=scope,poolSize=pools[qi,scope],candidates=output)


def retrieve(root: Path, output: Path, top_k: int, query_block: int, target_block: int) -> dict:
    """Build a local normalized memmap and nominate neighbors, never canonical IDs."""
    import numpy as np
    require(output.resolve().is_relative_to(ROOT.resolve()) and not output.exists(), 'FRESH_OUTPUT_REQUIRED')
    _, inputs, records = verify_prepared(root)
    require(bool(inputs), 'NO_ELIGIBLE_INPUTS')
    require(top_k > 0 and query_block > 0 and target_block > 0, 'POSITIVE_RETRIEVAL_SETTINGS_REQUIRED')
    # Verify all outcomes before creating output; missing/uncertain batches are blockers.
    receipts = []
    for i,batch in enumerate(batches(inputs)):
        folder = root/'embeddings'/f'batch-{i:06d}'
        require((folder/'intent.json').exists(), 'INCOMPLETE_EMBEDDINGS')
        execute_batch(folder,batch,identity.sha(root/'manifest.json'),lambda **kw: (_ for _ in ()).throw(AssertionError('OFFLINE')))
        receipts.append(dict(batch=i,responseSha256=identity.sha(folder/'response.json'),outcomeSha256=identity.sha(folder/'outcome.json')))
    output.mkdir(parents=True)
    matrix = np.lib.format.open_memmap(output/'normalized.npy',mode='w+',dtype='float32',shape=(len(inputs),DIMENSIONS))
    offset = 0
    for i,batch in enumerate(batches(inputs)):
        response = load(root/'embeddings'/f'batch-{i:06d}'/'response.json')
        values = np.asarray([r['embedding'] for r in sorted(response['data'],key=lambda r:r['index'])],dtype=np.float64)
        values /= np.linalg.norm(values,axis=1,keepdims=True)
        matrix[offset:offset+len(batch)] = values; offset += len(batch)
    matrix.flush(); counts = {s:Counter() for s in SCOPES}
    indices = {item['textSha256']:i for i,item in enumerate(inputs)}
    with (output/'candidates.jsonl').open('xb') as stream:
        for result in neighbors(records,matrix,indices,top_k,query_block,target_block):
            stat = counts[result['scope']]; stat['queries'] += 1
            stat['queriesWithPeers'] += int(result['poolSize']>0)
            stat['directedEligiblePairs'] += result['poolSize']; stat['directedNominations'] += len(result['candidates'])
            for row in result['candidates']: stream.write(identity.encoded(row)+b'\n')
    summary = dict(version=VERSION,preparationSha256=identity.sha(root/'manifest.json'),receipts=receipts,
        topKPerViewPerScope=top_k,queryBlock=query_block,targetBlock=target_block,numpyVersion=np.__version__,
        scopes={s:dict(c) for s,c in counts.items()},newIdentityDecisions=0,graphWrites=0,
        note='Directed nominations; two view unions and reverse directions are not independent identity evidence.',
        outputHashes={p.name:identity.sha(p) for p in sorted(output.iterdir())})
    write(output/'summary.json',summary)
    (output/'summary.md').write_text('# Step 14 two-view candidate retrieval\n\n'
        'Exact-class directed nominations only; no identity decisions or canonical mappings.\n\n'
        '| Scope | Queries | Queries with peers | Directed eligible pairs | Nominations |\n'
        '|---|---:|---:|---:|---:|\n'+''.join(f"| {s} | {c['queries']} | {c['queriesWithPeers']} | {c['directedEligiblePairs']} | {c['directedNominations']} |\n" for s,c in counts.items()))
    return summary


def main() -> None:
    """Separate offline preview/preparation/retrieval from explicit terminal execution."""
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command',required=True)
    for name in ('preview','prepare'):
        p = sub.add_parser(name); p.add_argument('--output',type=Path,required=True)
    p = sub.add_parser('embed'); p.add_argument('--root',type=Path,required=True)
    p.add_argument('--execute',action='store_true'); p.add_argument('--max-new-batches',type=int)
    p = sub.add_parser('retrieve'); p.add_argument('--root',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--top-k',type=int,default=10); p.add_argument('--query-block',type=int,default=32); p.add_argument('--target-block',type=int,default=512)
    args = parser.parse_args()
    if args.command == 'embed':
        require(args.execute, 'EXPLICIT_EXECUTION_REQUIRED')
        require(args.max_new_batches is None or args.max_new_batches>0,'POSITIVE_BATCH_LIMIT_REQUIRED')
        print(json.dumps(embed(args.root,args.max_new_batches),sort_keys=True)); return
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE')), patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE')):
        if args.command in ('preview','prepare'): result = prepare(args.output,args.command=='preview')
        else: result = retrieve(args.root,args.output,args.top_k,args.query_block,args.target_block)
        print(json.dumps(result,sort_keys=True))


if __name__ == '__main__':
    main()
