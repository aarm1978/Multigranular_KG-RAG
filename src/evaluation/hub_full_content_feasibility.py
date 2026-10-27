"""Offline full-content Hub feasibility; no selection, new contract or provider IO."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import socket
import subprocess
import tempfile
from unittest.mock import patch

from src.evaluation.source_family_production_verification import file_hash, checked_prepared
from src.evaluation.semantic_coverage_diagnosis import require, sha, rows
from src.extraction.llm.pilot_preflight import canonical, digest

ROOT = Path(__file__).resolve().parents[2]
CORPUS = Path('data/interim/documents/ciroh_hub_corpus.json')
REPORTS = Path('var/study2_step13/source-family-production-verification/v1')
QUEUE = Path('var/study2_step13/source-families-gpt61-batch/v1')
OUTPUT = Path('var/study2_step13/hub-full-content-feasibility/v1')
LIMITATIONS = ('Complete content_mdx is measured without semantic filtering or MDX execution. '
    'Offline tokens and additive request sizes are estimates, not exact provider usage. '
    'Observed envelopes describe the existing contract, not a proposed full-content contract. '
    'Historical packaging thresholds are planning heuristics, not model context limits. '
    'No eligibility, scientific completeness, extraction quality or KG authorization is asserted.')


def tokenizer() -> tuple:
    """Use an installed cached encoding (o200k, else cl100k proxy); never download."""
    try:
        import tiktoken
        import tiktoken.load
        from importlib.metadata import version
    except ImportError as error:
        return None, dict(available=False, reason=str(error), interpretation='No tokenizer dependency installed; no download attempted.')
    unavailable = {}
    for name in ('o200k_base', 'cl100k_base'):
        try:
            with patch.object(tiktoken.load, 'read_file', side_effect=RuntimeError('TOKENIZER_CACHE_UNAVAILABLE')):
                encoding = tiktoken.get_encoding(name)
            return (lambda text: len(encoding.encode(text, disallowed_special=()))), dict(
                available=True, package='tiktoken', version=version('tiktoken'), encoding=encoding.name,
                interpretation='offline proxy encoding estimate; model-specific compatibility and provider framing unverified')
        except (OSError, RuntimeError, ValueError) as error:
            unavailable[name] = type(error).__name__ + ': ' + str(error)
    return None, dict(available=False, reasons=unavailable,
                      interpretation='No network installation/download attempted; byte heuristics remain available.')


def sizes(text: str, count=None) -> dict:
    """Count unchanged Unicode code points, UTF-8 bytes and optional offline tokens."""
    size = len(text.encode('utf-8'))
    return dict(unicodeCharacters=len(text), utf8Bytes=size,
                offlineTokens=count(text) if count else None,
                byteHeuristicTokens={str(ratio): math.ceil(size / ratio) for ratio in (4, 3, 2)})


def distribution(values: list) -> dict:
    """Use linear interpolation at (n-1)*p, including small synthetic populations."""
    values = sorted(v for v in values if v is not None)
    if not values:
        return dict(count=0, min=None, median=None, P90=None, P95=None, max=None)
    def percentile(p: float):
        """Return the explicitly defined interpolated empirical percentile."""
        index = (len(values)-1)*p
        lo, hi = math.floor(index), math.ceil(index)
        return values[lo] + (values[hi]-values[lo])*(index-lo)
    return dict(count=len(values), min=values[0], median=percentile(.5), P90=percentile(.9),
                P95=percentile(.95), max=values[-1])


def page_inventory(pages: list, count=None) -> list:
    """Check identities and exact hashes without invoking the semantic reader."""
    seen = {k:set() for k in ('page_key', 'canonical_url', 'corpus_path')}
    result = []
    for page in pages:
        for field in seen:
            value = page.get(field)
            require(isinstance(value, str) and bool(value.strip()), 'MISSING_OR_MALFORMED_PAGE_IDENTITY:' + field)
            require(value not in seen[field], 'DUPLICATE_PAGE_IDENTITY:' + field)
            seen[field].add(value)
        require(isinstance(page.get('content_mdx'), str), 'MISSING_OR_MALFORMED_CONTENT:' + page['page_key'])
        text = page['content_mdx']
        try:
            measured = sizes(text, count)
            actual = sha(text)
        except UnicodeEncodeError as error:
            raise ValueError('MALFORMED_UNICODE_CONTENT:' + page['page_key']) from error
        require(actual == page.get('content_sha256'), 'CONTENT_SHA256_DRIFT:' + page['page_key'])
        result.append(dict(pageKey=page['page_key'], canonicalURL=page['canonical_url'],
            corpusPath=page['corpus_path'], sourcePath=page.get('source_path'),
            ownerID='hub:page:' + sha(page['canonical_url'])[:20], contentSha256=actual,
            physicalFileSha256AsRecorded=page.get('file_sha256'), physicalAcquisitionReverified=False,
            emptyContent=not text, whitespaceOnly=bool(text) and not text.strip(), **measured))
    require(len({r['ownerID'] for r in result}) == len(result), 'DUPLICATE_OWNER_IDENTITY')
    return sorted(result, key=lambda r:(r['pageKey'], r['ownerID']))


def reconcile(pages: list, owners: list, requests: list, entries: list) -> dict:
    """Reconcile exact owner/request sets and distinguish responses from requests."""
    source_ids = {p['ownerID'] for p in pages}
    coverage = {r['ownerID']:r for r in owners}
    require(len(coverage)==len(owners) and set(coverage)==source_ids, 'PRODUCTION_PAGE_IDENTITY_DRIFT')
    queued = {r['identity']['requestID']:r for r in entries}
    recorded = {r['requestID']:r for r in requests}
    require(len(queued)==len(entries) and len(recorded)==len(requests) and queued.keys()==recorded.keys(),
            'PRODUCTION_REQUEST_IDENTITY_DRIFT')
    grouped = {owner:[] for owner in source_ids}
    for rid, record in recorded.items():
        entry = queued[rid]
        require(record['ownerID'] in source_ids and record['ownerID']==entry['ownerID'] and
                record['identity']==entry['identity'] and record['bundleSha256']==entry['bundleSha256'],
                'PRODUCTION_REQUEST_ASSOCIATION_DRIFT')
        require((record['state']=='completion') == record['processable'], 'COMPLETION_PROCESSABILITY_DRIFT')
        require(len({r['number'] for r in record['deliveries']}) == len(record['deliveries']), 'DUPLICATE_DELIVERY')
        grouped[record['ownerID']].append(record)
    for page in pages:
        owner = coverage[page['ownerID']]
        require(owner['family']=='ciroh_hub' and owner['ownerID']==owner['sealedCoverage']['ownerID'], 'SEALED_OWNER_DRIFT')
        selected = grouped[page['ownerID']]
        require(owner['requests']==len(selected), 'OWNER_REQUEST_COUNT_DRIFT')
        group_ids = [g['requestID'] for g in owner['sealedCoverage']['groups'] if g.get('requestID')]
        require(len(group_ids)==len(set(group_ids)) and set(group_ids)=={r['requestID'] for r in selected}, 'COVERAGE_REQUEST_DRIFT')
        page['production'] = dict(requestIDs=sorted(r['requestID'] for r in selected), requests=len(selected),
            completedRequests=sum(r['state']=='completion' for r in selected),
            processableRequests=sum(r['processable'] for r in selected),
            recordedResponseDeliveries=sum(len(r['deliveries']) for r in selected),
            providerCompletedResponses=sum(d.get('responseStatus')=='completed' for r in selected for d in r['deliveries']),
            readerAdmittedUnits=len(owner['sealedCoverage']['readerSourceUnitIDs']),
            sealedGroups=owner['sealedCoverage']['groups'], sourceDiagnostics=owner['sealedCoverage']['diagnostics'],
            noRequestExplanation=('no_reader_admitted_units' if not owner['sealedCoverage']['readerSourceUnitIDs'] else
                                  'reader_units_present_but_no_sealed_request') if not selected else None)
    no_requests = [p for p in pages if not p['production']['requests']]
    extra = sum(max(0, p['production']['requests']-1) for p in pages)
    return dict(pages=len(pages), requests=len(requests), pagesWithRequests=len(pages)-len(no_requests),
        pagesWithoutRequests=len(no_requests), additionalRequestsBeyondOnePerRepresentedPage=extra,
        completedRequests=sum(p['production']['completedRequests'] for p in pages),
        recordedResponseDeliveries=sum(p['production']['recordedResponseDeliveries'] for p in pages),
        providerCompletedResponses=sum(p['production']['providerCompletedResponses'] for p in pages),
        difference=len(pages)-len(requests),
        equation='pages - requests = pagesWithoutRequests - additionalRequestsBeyondOnePerRepresentedPage',
        noRequestPages=[{k:p[k] for k in ('pageKey','ownerID','corpusPath','production')} for p in no_requests])


def overhead(prepared: dict, count=None) -> dict:
    """Measure stored fixed fields and an approximate non-text envelope baseline."""
    body = deepcopy(prepared['body'])
    require(isinstance(body['input'], str), 'UNSUPPORTED_PERSISTED_INPUT_SHAPE')
    payload = json.loads(body['input'])
    fields = ('instructions','responseContract','targetProfile','contractID','promptIdentifier','schemaVersion')
    require(all(k in payload for k in fields), 'PERSISTED_FIXED_FIELDS_UNAVAILABLE')
    fixed = {k:payload[k] for k in fields}
    fixed['providerTextFormat'] = body['text']
    wire = canonical(fixed).decode('utf-8')
    for unit in payload['sourceUnits']:
        unit['text'] = ''
    body['input'] = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',',':'))
    return dict(fixedPromptSchemaSha256=digest(canonical(fixed)), fixedPromptSchema=sizes(wire,count),
                nonTextEnvelopeBaseline=sizes(canonical(body).decode('utf-8'),count), model=body['model'],
                interpretation='observed existing envelope with source-unit text emptied for size arithmetic only; not a sendable prospective request')


def analyze(repo: Path, reports: Path, queue: Path, count=None, estimator=None) -> tuple:
    """Read only original Hub sources, report records and pinned persisted envelopes."""
    inputs = [reports/n for n in ('verification.json','family-owner.jsonl','requests.jsonl')]
    inputs += [queue/'queue-manifest.json', repo/CORPUS]
    hashes = {str(p.relative_to(repo)):file_hash(p) for p in inputs}
    verification = json.loads(inputs[0].read_text())
    require(hashes[str(CORPUS)] == verification['persistedSourcePins'][str(CORPUS)], 'FROZEN_CORPUS_HASH_DRIFT')
    require(file_hash(inputs[3]) == verification['inputHashes']['queue-manifest.json'], 'SEALED_QUEUE_HASH_DRIFT')
    corpus = json.loads(inputs[4].read_text())
    pages = page_inventory(corpus['pages'], count)
    manifest = json.loads(inputs[3].read_text())
    owners = [r for _,r in rows(inputs[1]) if r['family']=='ciroh_hub']
    requests = [r for _,r in rows(inputs[2]) if r['family']=='ciroh_hub']
    entries = [r for r in manifest['requests'] if r['family']=='ciroh_hub']
    sealed = {r['ownerID']:r for r in manifest['coverage'] if r['family']=='ciroh_hub'}
    require(len(sealed)==len(owners), 'SEALED_COVERAGE_COUNT_DRIFT')
    for owner in owners:
        require(owner['sealedCoverage']==sealed.get(owner['ownerID']), 'SEALED_COVERAGE_DRIFT')
    for source in corpus['pages']:
        owner = 'hub:page:'+sha(source['canonical_url'])[:20]
        require(sealed.get(owner,{}).get('sourceRecordSha256')==digest(canonical(source)), 'SOURCE_RECORD_ASSOCIATION_DRIFT')
    reconciliation = reconcile(pages, owners, requests, entries)
    baselines, fixed = {}, {}
    for entry in sorted(entries, key=lambda e:e['identity']['requestID']):
        require(Path(entry['bundleFile']).name==entry['bundleFile'], 'UNSAFE_BUNDLE_PATH')
        path = queue/'queue'/entry['bundleFile']
        require(file_hash(path)==entry['bundleSha256'], 'PERSISTED_BUNDLE_HASH_DRIFT')
        hashes[str(path.relative_to(repo))]=entry['bundleSha256']
        prepared=json.loads(path.read_text())
        checked_prepared(prepared,entry)
        estimate=overhead(prepared,count)
        baselines.setdefault(entry['ownerID'],[]).append(estimate['nonTextEnvelopeBaseline'])
        fixed[estimate['fixedPromptSchemaSha256']]=estimate['fixedPromptSchema']
    all_baselines=[b for values in baselines.values() for b in values]
    sizing=manifest['sizing']
    for page in pages:
        baseline=baselines.get(page['ownerID'],all_baselines)
        approximate={}
        for field in ('utf8Bytes','offlineTokens'):
            values=[b[field]+page[field] for b in baseline if b[field] is not None and page[field] is not None]
            approximate[field]=dict(low=min(values),high=max(values)) if values else None
        page['completeRequestApproximation']=dict(additiveRanges=approximate,
            baselineBasis='same-owner historical envelopes' if page['ownerID'] in baselines else 'all-Hub observed baseline range',
            caveat='full authority plus non-text baseline; prospective unit metadata, JSON escaping and tokenizer boundary effects differ')
        page['potentialMechanicalSplit']=dict(
            exceedsHistoricalTextPlanningBytes=page['utf8Bytes']>sizing['maxSelectedTextBytes'],
            exceedsHistoricalEnvelopePlanningBytes=bool(approximate['utf8Bytes'] and approximate['utf8Bytes']['high']>sizing['maxEnvelopeBytes']),
            verifiedModelContextLimit=None, decision='review only; no splitting performed')
    for path,expected in hashes.items():
        require(file_hash(repo/path)==expected,'INPUT_CHANGED_DURING_PREFLIGHT:'+path)
    largest=sorted(pages,key=lambda p:(-p['utf8Bytes'],p['pageKey']))[:10]
    summary=dict(version='hub-full-content-feasibility/1.0',limitations=LIMITATIONS,inputHashes=hashes,
        implementationSha256=file_hash(Path(__file__)),expectedPages=242,observedPages=len(pages),
        expectedPageCountMatches=len(pages)==242, emptyPages=sum(p['emptyContent'] for p in pages),
        whitespaceOnlyPages=sum(p['whitespaceOnly'] for p in pages),
        estimator=estimator or {'available':False}, percentileDefinition='linear interpolation at (n-1)*p',
        sizes={field:distribution([p[field] for p in pages]) for field in ('unicodeCharacters','utf8Bytes','offlineTokens')},
        byteHeuristicTokenDistributions={str(ratio):distribution([p['byteHeuristicTokens'][str(ratio)] for p in pages]) for ratio in (4,3,2)},
        largestPages=[{k:p[k] for k in ('pageKey','ownerID','corpusPath','unicodeCharacters','utf8Bytes','offlineTokens','potentialMechanicalSplit')} for p in largest],
        historicalPlanningThresholds=sizing, fixedPromptSchemaVariants=fixed,
        potentialMechanicalSplitPages=[dict(pageKey=p['pageKey'],ownerID=p['ownerID'],**p['potentialMechanicalSplit']) for p in pages
            if p['potentialMechanicalSplit']['exceedsHistoricalTextPlanningBytes'] or p['potentialMechanicalSplit']['exceedsHistoricalEnvelopePlanningBytes']],
        observedNonTextEnvelopeBytes=distribution([b['utf8Bytes'] for b in all_baselines]),
        prospectiveExactRequestSize=None, verifiedModelContextLimit=None,
        unavailableMeasurements=['exact prospective request serialization','provider token usage for full-content requests','verified model context limit'],
        reconciliation=reconciliation)
    return pages,summary


def run(repo: Path, reports: Path, queue: Path, output: Path) -> None:
    """Publish three new ignored artifacts only after all offline checks pass."""
    repo,reports,queue,output=map(Path.resolve,(repo,reports,queue,output))
    require(output==repo/OUTPUT or (repo/OUTPUT) in output.parents,'OUTPUT_OUTSIDE_FEASIBILITY_V1')
    require(not output.exists(),'OUTPUT_ALREADY_EXISTS')
    require(reports.is_relative_to(repo) and queue.is_relative_to(repo),'INPUT_OUTSIDE_REPOSITORY')
    require(subprocess.run(['git','check-ignore','-q',str(output/'summary.json')],cwd=repo).returncode==0,'OUTPUT_MUST_BE_IGNORED')
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')), \
         patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')), \
         patch.object(socket,'create_connection',side_effect=RuntimeError('OFFLINE_ONLY')):
        count,estimator=tokenizer()
        pages,summary=analyze(repo,reports,queue,count,estimator)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.feasibility-',dir=output.parent) as temporary:
        stage=Path(temporary)
        (stage/'pages.jsonl').write_text(''.join(json.dumps(p,sort_keys=True,ensure_ascii=False)+'\n' for p in pages),encoding='utf-8')
        (stage/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n',encoding='utf-8')
        r=summary['reconciliation']
        lines=['# CIROH Hub full-content feasibility','',LIMITATIONS,'',
            f"Pages: {r['pages']} (expected 242); requests: {r['requests']}; completed requests: {r['completedRequests']}; provider-completed response deliveries: {r['providerCompletedResponses']}.",
            f"Page/request difference: {r['difference']} = {r['pagesWithoutRequests']} pages without requests - {r['additionalRequestsBeyondOnePerRepresentedPage']} additional requests for represented pages.",'',
            'Offline estimator: '+json.dumps(summary['estimator'],sort_keys=True),'',
            '| Measure | Min | Median | P90 | P95 | Max |','|---|---:|---:|---:|---:|---:|']
        for name,stats in summary['sizes'].items():
            lines.append('| '+name+' | '+' | '.join(str(stats[k]) for k in ('min','median','P90','P95','max'))+' |')
        for ratio,stats in summary['byteHeuristicTokenDistributions'].items():
            lines.append('| byte heuristic: UTF-8 bytes / '+ratio+' | '+' | '.join(str(stats[k]) for k in ('min','median','P90','P95','max'))+' |')
        lines+=['','Largest pages (UTF-8 bytes):']
        lines += [f"- {p['pageKey']}: {p['utf8Bytes']} bytes; {p['unicodeCharacters']} characters; estimated tokens {p['offlineTokens']}." for p in summary['largestPages']]
        lines+=['',f"Potential mechanical-split review targets: {len(summary['potentialMechanicalSplitPages'])}; these exceed historical planning margins, not a verified model limit.",'','Pages without sealed requests:']
        lines += [f"- {p['pageKey']} ({p['ownerID']}): {p['production']['noRequestExplanation']}; diagnostic reasons {dict(Counter(d.get('reason','unspecified') for d in p['production']['sourceDiagnostics']))}." for p in r['noRequestPages']]
        lines+=['','Historical planning thresholds (not model limits): '+json.dumps(summary['historicalPlanningThresholds'],sort_keys=True),
                '', 'Fixed prompt/schema variants and non-text envelope baselines are measured from pinned original bundles; per-page additive request ranges are in pages.jsonl.',
                'Unavailable: exact prospective request size, provider usage and a verified model context limit. No prospective extraction contract was created.']
        (stage/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        require(not output.exists(),'OUTPUT_ALREADY_EXISTS')
        stage.rename(output)


def main() -> None:
    """Run only when explicitly invoked by the researcher."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports',type=Path,default=REPORTS)
    parser.add_argument('--queue',type=Path,default=QUEUE)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    run(ROOT,args.reports,args.queue,args.output)
    print(args.output/'summary.md')


if __name__=='__main__':
    main()
