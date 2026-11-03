"""Offline, additive identity proposals over the frozen Step 13 v4 snapshot."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable
import hashlib
import json
from pathlib import Path
import re
import socket
from unittest.mock import patch

import yaml

ROOT = Path('var/study2_step13/pre-alignment-metrics/v4')
OUTPUT = Path('var/study2_step14/identity-preview/v1')
PINS = {
    'snapshot.json': '1f3e3ca0ba8d6e012652ab986875a994aa2ba700cb0cdd8ddb409d99c6238209',
    'summary.json': '6de09a028ca9dde1f0053b4f0e16f3f239ae2efd5dfa3fc78650bd835b7791c5',
}
RULES = {
    'doi': 'Typed Paper/DatasetResource own canonicalKey or doi; C-D04 hasIdentifier for DatasetResource only.',
    'hydroshare': 'DatasetResource.resourceId or canonicalKey hydroshare:<32 hex>.',
    'github': 'Repository.repoId with github_numeric_id and matching canonicalKey.',
    'orcid': 'Person.orcid or canonicalKey orcid:<identifier>.',
    'ror': 'Organization.ror under identifierRegime ROR.',
}
BLOCKERS = [
    'Geographic IDs: no cross-source governed namespace/version equivalence implemented.',
    'Publication link_existing: retain exact target declaration; request-context endpoint authorization is not reconstructed from the occurrence snapshot.',
    'Publication unresolved-identity sidecars contain nonaccepted POSSIBLE_LOCAL_DUPLICATE candidates; no promotion into accepted v4 content.',
    'Semantic source-local attributes, repository URLs, names, fuzzy matches and unsupported identifier roles remain unresolved.',
    'Exact class equality only; subtype equivalence and missing-versus-present version reconciliation require review.',
]


def encoded(value: object) -> bytes:
    """Canonical bytes for stable preview identifiers and records."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(path: Path) -> str:
    """Hash input bytes without changing them."""
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def require(ok: bool, reason: str) -> None:
    """Fail closed on input or output boundary drift."""
    if not ok:
        raise ValueError(reason)


def own_keys(node: dict) -> set[tuple[str, str]]:
    """Read only typed deterministic identity fields, never citation/source strings."""
    if not node.get('evidence') or node.get('curationStatus') not in ('curated', 'referenced'):
        return set()
    a = node.get('attributes', {})
    if (a.get('provisionalIdentity') or a.get('identityScope') == 'source_local'
            or node.get('provisionalIdentity') or node.get('identityScope') == 'source_local'):
        return set()
    cls = node['class']; key = node.get('canonicalKey', '')
    result = set()
    def add(scheme: str, value: object, pattern: str) -> None:
        """Accept already canonical strings only; no speculative repair."""
        if isinstance(value, str) and re.fullmatch(pattern, value):
            result.add((scheme, value))
    if cls in ('Paper', 'DatasetResource'):
        add('doi', key[4:] if key.startswith('doi:') else None, r'10\.\d{4,9}/\S+')
        add('doi', a.get('doi'), r'10\.\d{4,9}/\S+')
    if cls == 'DatasetResource':
        add('hydroshare', a.get('resourceId'), r'[0-9a-f]{32}')
        add('hydroshare', key[11:] if key.startswith('hydroshare:') else None, r'[0-9a-f]{32}')
    if cls == 'Repository' and node.get('identityRegime') == 'github_numeric_id':
        value = a.get('repoId')
        if type(value) in (str, int) and key == f'github-repo-id:{value}':
            add('github', str(value), r'[1-9][0-9]*')
    if cls == 'Person':
        add('orcid', key[6:] if key.startswith('orcid:') else None, r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]')
        value = a.get('orcid')
        if isinstance(value, str):
            add('orcid', value.removeprefix('https://orcid.org/'), r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]')
    if cls == 'Organization' and a.get('identifierRegime') == 'ROR':
        add('ror', a.get('ror'), r'[a-z0-9]{9}')
    return result


def prepare(graph: dict, native_rows: Iterable[dict], classes: dict[str, str]) -> dict:
    """Produce review-only components, withholding entire conflicting components."""
    nodes = {n['id']: n for n in graph['nodes']}
    require(len(nodes) == len(graph['nodes']), 'DUPLICATE_NODE_ID')
    refs = defaultdict(list); semantic = set(); links = defaultdict(list)
    for row in native_rows:
        if row['kind'] != 'nodes':
            continue
        nid = row['graphID']; require(nid in nodes, 'SIDECAR_NODE_MISSING')
        native = row['nativeRecord']; semantic.add(nid)
        require(hashlib.sha256(encoded(native)).hexdigest() == row['nativeRecordSha256'], 'NATIVE_HASH_DRIFT')
        refs[nid].append({'nativeRecordSha256': row['nativeRecordSha256'], 'provenance': row['provenance']})
        candidate = native.get('candidate', {})
        if candidate.get('action') == 'link_existing':
            links[nid].append(candidate.get('existingNodeID'))
    keys = {nid: own_keys(n) if nid not in semantic else set() for nid, n in nodes.items()}
    for e in graph['edges']:
        if e.get('relation') != 'hasIdentifier' or e.get('inventoryId') != 'C-D04' or not e.get('evidence'):
            continue
        source, target = nodes[e['source']], nodes[e['target']]
        if source['id'] in semantic or target['id'] in semantic:
            continue
        a = target.get('attributes', {})
        value = a.get('identifierValue')
        if (source['class'] == 'DatasetResource' and target['class'] == 'Identifier'
                and a.get('identifierType') == 'DOI' and isinstance(value, str)
                and re.fullmatch(r'10\.\d{4,9}/\S+', value)):
            keys[source['id']].add(('doi', value))
    buckets = defaultdict(set)
    for nid, values in keys.items():
        for key in values:
            buckets[key].add(nid)
    adjacency = defaultdict(set)
    for ids in buckets.values():
        first = min(ids)
        for nid in ids:
            adjacency[first].add(nid); adjacency[nid].add(first)
    groups = []; conflicts = []; mapping = {}; visited = set()
    for start in sorted(adjacency):
        if start in visited:
            continue
        pending = [start]; members = set()
        while pending:
            nid = pending.pop()
            if nid not in members:
                members.add(nid); pending.extend(adjacency[nid] - members)
        visited.update(members)
        reasons = []
        signatures = {(nodes[n]['class'], nodes[n].get('inventoryId')) for n in members}
        if len(signatures) != 1 or any(classes.get(nodes[n]['class']) != nodes[n].get('inventoryId') for n in members):
            reasons.append('class_or_artifact_role_conflict')
        union = sorted({key for n in members for key in keys[n]})
        counts = Counter(s for s, _ in union)
        if any(v > 1 for v in counts.values()):
            reasons.append('contradictory_own_identifiers')
        # These are entity version/fork fields, never acquisition/evidence versions.
        for field in ('version', 'versionNumber', 'commitSHA', 'fork', 'forkParent'):
            values = {encoded(nodes[n].get('attributes', {}).get(field)) for n in members}
            if len(values) > 1:
                reasons.append('version_or_fork_unresolved:' + field)
        group = {'occurrenceIDs': sorted(members), 'identifiers': union,
                 'sourceArtifacts': sorted({str(nodes[n].get('evidence', {}).get('sourceArtifact'))
                                            for n in members if nodes[n].get('evidence', {}).get('sourceArtifact')})}
        if reasons:
            conflicts.append(dict(group, reasons=reasons)); continue
        if len(members) > 1:
            canonical = 'step14-preview:' + hashlib.sha256(encoded([sorted(signatures), union])).hexdigest()
            groups.append(dict(group, proposedCanonicalID=canonical))
            mapping.update({n: canonical for n in members})
    conflict_ids = {n for c in conflicts for n in c['occurrenceIDs']}
    rows = []
    for nid in sorted(nodes):
        reason = ('exact_identity_proposal' if nid in mapping else 'identity_conflict' if nid in conflict_ids
                  else 'publication_link_existing_requires_context' if nid in links
                  else 'no_exact_peer' if keys[nid] else 'unsupported_or_source_local_identity')
        rows.append(dict(occurrenceID=nid, proposedCanonicalID=mapping.get(nid), status=reason,
                         snapshotRecordSha256=hashlib.sha256(encoded(nodes[nid])).hexdigest(),
                         nativeReferences=sorted(refs[nid], key=encoded),
                         declaredExistingNodeIDs=sorted(links[nid], key=encoded)))
    return dict(previewOnly=True, graphWritten=False, providerCalls=0, mappings=rows, matches=groups,
                conflicts=conflicts, counts=dict(sorted(Counter(r['status'] for r in rows).items())),
                ruleCoverage={k: dict(description=v, eligibleOccurrences=sum(any(s == k for s, _ in values) for values in keys.values())) for k, v in RULES.items()},
                blockers=BLOCKERS)


def run(output: Path = OUTPUT) -> dict:
    """Verify frozen inputs and write a fresh ignored preview, never a graph."""
    require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    require(output.resolve().is_relative_to(Path('var/study2_step14').resolve()), 'STEP14_OUTPUT_REQUIRED')
    pins = {}
    def check(path: Path, expected: str) -> None:
        """Record and verify immutable inputs before consuming them."""
        require(sha(path) == expected, 'INPUT_HASH_DRIFT:' + str(path)); pins[str(path)] = expected
    for name, expected in PINS.items():
        check(ROOT / name, expected)
    summary = json.loads((ROOT / 'summary.json').read_bytes())
    sidecar = Path(summary['originalNativeProvenancePath'])
    check(sidecar, summary['originalNativeProvenanceSha256'])
    check(ROOT / 'derivation-provenance.jsonl', summary['derivationProvenanceSha256'])
    spec_path = Path('src/ontology/ontology_spec.yaml')
    check(spec_path, summary['inputHashes'][str(spec_path)])
    owl = Path('src/ontology/ciroh_ontology.owl'); check(owl, summary['inputHashes'][str(owl)])
    spec = yaml.safe_load(spec_path.read_text())
    with sidecar.open() as handle:
        native = (json.loads(line) for line in handle)
        result = prepare(json.loads((ROOT / 'snapshot.json').read_bytes()), native,
                         {c['name']: c['id'] for c in spec['classes']})
    result['inputHashes'] = pins
    result['implementationSha256'] = sha(Path(__file__))
    output.mkdir(parents=True, exist_ok=False)
    (output / 'preview.json').write_bytes(encoded(result) + b'\n')
    lines = ['# Step 14 identity PREVIEW', '', 'No graph, assertion, source record or historical authority was changed.', '',
             f"Proposed groups: {len(result['matches'])}; conflicting groups: {len(result['conflicts'])}.", '',
             *[f'- {k}: {v}' for k, v in result['counts'].items()], '', '## Rule coverage', '',
             *[f'- {k}: {v["eligibleOccurrences"]} eligible occurrences. {v["description"]}' for k, v in result['ruleCoverage'].items()],
             '', '## Researcher review / unimplemented rules', '', *['- ' + b for b in BLOCKERS]]
    (output / 'report.md').write_text('\n'.join(lines) + '\n')
    return result


def main() -> None:
    """Run only from the researcher terminal with network entry points disabled."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('OFFLINE_ONLY')), patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('OFFLINE_ONLY')):
        run(args.output)


if __name__ == '__main__':
    main()
