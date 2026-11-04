"""Read-only accepted-relation opportunity inventory and lexical pilot queue."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import csv
import json
from pathlib import Path
import socket
from unittest.mock import patch

from src.evaluation import step14_identity_preview as identity
from src.evaluation import step14_semantic_candidates as candidates
from src.evaluation import step14_semantic_review as review
from src.evaluation import step14_identifier_scope_triage as triage

OUTPUT = Path('var/study2_step14/alignment-opportunities/v2')
TRIAGE_PIN = '529ffeddd981461fddeabdaa539a6758cae7a653f3378f1cc4b4aae4574e01d3'
VERSION = 'step14-alignment-opportunities/0.2.0'
ARTIFACTS = {'Paper', 'DatasetResource', 'Repository', 'DocumentationPage'}
PRIORITY_CLASSES = ('Tool', 'Algorithm', 'MLModel', 'ProcessBasedModel', 'ConceptualModel')
TIERS = ('a_explicit_external_target', 'b_strong_record_candidate_to_observed_artifact',
         'c_exact_locator_coincidence_only', 'd_contextual_lexical_unverified', 'e_unresolved_or_ambiguous')
LIMITS = [
    'Inventory only: accepted predicates are never promoted, inferred, retargeted or materialized.',
    'An ontology cross marker is schema metadata, not proof of an independently observed artifact endpoint.',
    'Tier a identifies explicit external reference targets; a separate counter records direct connections to independently observed curated artifacts.',
    'Tier b uses existing unadjudicated strong identifier blocks only. No new identity matches or canonical nodes are created.',
    'Confirmed provenance means recorded evidence plus traceable source family/artifact, not semantic correctness or independent corroboration.',
    'Repeated quotes and multiple mentions/artifacts do not establish independent identity confirmation.',
    'Unknown legacy signature IDs or missing endpoint provenance remain unresolved; no ontology or frozen acceptance correction is made.',
    'Only exact class-compatible existing block peers with distinct recorded source origins count as possible cross-family opportunities.',
    'Lexical pilot cases remain unverified identities; selection is deterministic coverage sampling, not a precision/recall evaluation.',
    'Oversized cross-family blocks are summarized from existing saved summaries; their membership is not expanded.',
    'Step 14A remains skipped. No provider calls, equivalences, new scientific predicates or graph writes.',
]


def walk(value: object):
    """Visit original nested provenance/evidence dictionaries without inference."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def github_root_family(node: dict) -> str | None:
    """Recover only the exact repository_node/metadata_evidence constructor contract."""
    a = node.get('attributes', {}); ev = node.get('evidence', {}); lineage = node.get('internalLineage', {})
    repo_id = a.get('repoId'); full_name = a.get('fullName'); url = a.get('htmlUrl')
    if (node.get('class') == 'Repository' and node.get('inventoryId') == 'A-C01'
            and node.get('curationStatus') == 'curated' and type(repo_id) is int and repo_id > 0
            and node.get('identityRegime') == 'github_numeric_id'
            and node.get('canonicalKey') == f'github-repo-id:{repo_id}'
            and isinstance(full_name, str) and len(full_name.split('/')) == 2 and all(full_name.split('/'))
            and url == 'https://github.com/' + full_name
            and lineage.get('phaseAField') == 'repo root' and lineage.get('phaseAVersion')
            and ev.get('sourceArtifact') == url and ev.get('sourceLocation') == 'https://api.github.com/repos/' + full_name
            and ev.get('extractionMethod') == 'deterministic' and ev.get('evidenceText')
            and ev.get('version') is not None):
        return 'github'
    return None


def support(evidence: object, provenance: dict, reference: dict, family: str | None = None) -> dict:
    """Record documentary origins and quote hashes, not independent truth attestations."""
    families = {family} if family else set(); artifacts = set(); quotes = set()
    for item in walk([evidence, provenance]):
        if isinstance(item.get('family'), str):
            families.add(item['family'])
        for field in ('sourceArtifact', 'sourceArtifactID', 'canonicalPaperID', 'ownerID'):
            if isinstance(item.get(field), str) and item[field]:
                artifacts.add(item[field])
        if isinstance(item.get('evidenceText'), str) and item['evidenceText']:
            quotes.add(candidates.token(item['evidenceText']))
    return dict(families=families, artifacts=artifacts, quotes=quotes, evidence=bool(evidence), references=[reference])


def combine(items: list[dict]) -> dict:
    """Combine documentary supports while retaining bounded exact recovery references."""
    return dict(families=set().union(*(i['families'] for i in items)),
                artifacts=set().union(*(i['artifacts'] for i in items)),
                quotes=set().union(*(i['quotes'] for i in items)), evidence=any(i['evidence'] for i in items),
                references=sorted([r for i in items for r in i['references']], key=identity.encoded)[:2])


def confirmed(item: dict) -> bool:
    """Test recorded documentary origin completeness, not scientific accuracy."""
    return bool(item['families'] and item['artifacts'] and item['evidence'])


def signature_status(edge: dict, source: dict, target: dict, spec: dict) -> str:
    """Check exact relation signatures with only declared class aliases/ancestry."""
    relations = {r['id']: r for r in spec['relations']}
    r = relations.get(edge.get('inventoryId'))
    if r is None:
        return 'unresolved_legacy_or_unknown_inventory'
    if r['name'] != edge['relation']:
        return 'predicate_inventory_mismatch'
    classes = {c['name']: c for c in spec['classes']}; by_id = {c['id']: c['name'] for c in spec['classes']}
    def canonical(name: str) -> str:
        """Resolve only explicit class same_as aliases."""
        c = classes.get(name, {})
        return by_id.get(c.get('same_as'), name)
    def accepts(name: str, roots: object) -> bool:
        """Accept declared domain/range ancestry and owl:Thing only."""
        roots = roots if isinstance(roots, list) else [roots]
        if 'owl:Thing' in roots:
            return True
        allowed = {canonical(x) for x in roots}; seen = set()
        while name and name not in seen:
            seen.add(name)
            if canonical(name) in allowed:
                return True
            parent = classes.get(name, {}).get('parent', '')
            name = parent.split(':')[-1]
        return False
    return 'compatible' if accepts(source['class'], r['domain']) and accepts(target['class'], r['range']) else 'class_incompatible'


def pilot_queue(dossier: list[dict], incident: dict, limit: int = 30) -> tuple[list[dict], dict]:
    """Round-robin class/family strata, preferring requested classes and supported blocks."""
    lexical = [b for b in dossier if b['candidateMechanism'] == 'lexical_similarity_only']
    eligible = [b for b in lexical if all(m['sourceArtifacts'] and m['sourceFamilies'] and m['evidenceExcerpts'] for m in b['members'])]
    strata = defaultdict(list)
    for b in eligible:
        strata[(b['ontologyClass'], tuple(sorted(b['sourceFamilyCombination'])))].append(b)
    for values in strata.values():
        values.sort(key=lambda b: (not any(incident.get(n) for n in b['occurrenceIDs']), b['blockID']))
    class_order = list(PRIORITY_CLASSES) + sorted({k[0] for k in strata} - set(PRIORITY_CLASSES))
    selected = []; per_class = defaultdict(list)
    for cls in class_order:
        groups = [list(strata[k]) for k in sorted(strata) if k[0] == cls]
        while any(groups):
            for group in groups:
                if group:
                    per_class[cls].append(group.pop(0))
    while len(selected) < limit and any(per_class.values()):
        for cls in class_order:
            if per_class[cls] and len(selected) < limit:
                selected.append(per_class[cls].pop(0))
    rows = []
    for b in selected:
        representatives = []
        for family in sorted(b['sourceFamilyCombination']):
            available = sorted((m for m in b['members'] if family in m['sourceFamilies']), key=lambda m: m['occurrenceID'])
            m = available[0]; e = m['evidenceExcerpts'][0]
            representatives.append(dict(family=family, occurrenceID=m['occurrenceID'], sourceArtifacts=m['sourceArtifacts'],
                excerpt=e['excerpt'][:400], evidenceReference=e['reference'], occurrenceReference=m['occurrenceReference']))
        rows.append(dict(blockID=b['blockID'], ontologyClass=b['ontologyClass'], key=b['key'], memberCount=b['memberCount'],
            occurrenceIDs=b['occurrenceIDs'], membershipSha256=b['membershipSha256'], sourceFamilies=b['sourceFamilyCombination'],
            identityDecision='unadjudicated', representatives=representatives,
            incidentAcceptedPredicates=sorted({p for n in b['occurrenceIDs'] for p in incident.get(n, set())}),
            existingFlags=b['existingBlockFlags'], dossierBlockSha256=candidates.token(b)))
    return rows, dict(lexicalBlocks=len(lexical), evidenceSupportedBlocks=len(eligible), selectedBlocks=len(rows),
        selectedByClass=dict(sorted(Counter(r['ontologyClass'] for r in rows).items())),
        availableByClass=dict(sorted(Counter(b['ontologyClass'] for b in eligible).items())),
        rule='30 maximum; round-robin classes (Tool, Algorithm, MLModel, ProcessBasedModel, ConceptualModel first), then family combinations within class; blocks with incident evidence-backed accepted relations first, blockID tie-break; first occurrence ID per family supplies bounded evidence.')


def inventory(graph: dict, native_rows, derived_rows, dossier: list[dict], triages: list[dict], oversized: list[dict], spec: dict, owner_origins: dict | None = None) -> dict:
    """Count accepted edges once, preserving every predicate and reporting provenance limits."""
    nodes = {n['id']: n for n in graph['nodes']}; edges = {e['id']: e for e in graph['edges']}
    identity.require(len(nodes) == len(graph['nodes']) and len(edges) == len(graph['edges']), 'DUPLICATE_GRAPH_ID')
    ns = defaultdict(list); es = defaultdict(list); local_identifiers = defaultdict(set)
    for n in nodes.values():
        if n.get('evidence'):
            old_family = candidates.deterministic_family(n)
            item = support(n['evidence'], {}, dict(channel='v4_inline_node', nodeID=n['id']), old_family or github_root_family(n))
            item['legacyFamilies'] = {old_family} if old_family else set()
            ns[n['id']].append(item)
    for e in edges.values():
        if e.get('evidence'):
            es[e['id']].append(support(e['evidence'], {}, dict(channel='v4_inline_edge', edgeID=e['id']), candidates.deterministic_family(e)))
    for row in native_rows:
        n = row['nativeRecord']; gid = row['graphID']; pr = deepcopy(row['provenance'])
        identity.require(candidates.token(n) == row['nativeRecordSha256'], 'NATIVE_HASH_DRIFT')
        if pr.get('path') in (owner_origins or {}):
            pr['ownerID'] = owner_origins[pr['path']]
        store = ns if row['kind'] == 'nodes' else es
        identity.require(gid in (nodes if row['kind'] == 'nodes' else edges), 'NATIVE_GRAPH_ID_MISSING')
        ev = n.get('boundEvidence', n.get('evidenceOccurrences', []))
        if row['kind'] == 'nodes':
            local_identifiers[gid]  # Native occurrences do not gain deterministic own-ID authority.
            exact = n.get('originalCandidate', {}).get('exactIdentifier')
            if isinstance(exact, str) and exact and any(exact in e.get('evidenceText', '') for e in ev):
                local_identifiers[gid].add(exact)
        store[gid].append(support(ev, pr, dict(channel='native-provenance', graphID=gid,
            nativeRecordSha256=row['nativeRecordSha256'], provenanceSha256=candidates.token(row['provenance']))))
    rule_families = {'C-P05': 'publications', 'C-P10': 'publications', 'C-P12-Paper': 'publications',
                     'D26-Paper': 'publications', 'D26-discourse': 'publications',
                     'D26-github': 'github', 'D26-hydroshare': 'hydroshare', 'D26-ciroh_hub': 'ciroh_hub'}
    for row in derived_rows:
        if row['disposition'] != 'emitted':
            continue
        eid = row['edgeID']; identity.require(eid in edges, 'DERIVED_EDGE_MISSING')
        es[eid].append(support(row['evidence'], row['provenance'], dict(channel='derivation-provenance', edgeID=eid,
            recordSha256=candidates.token(row)), rule_families.get(row['rule'])))
    origins = {nid: combine(ns[nid]) for nid in nodes}
    legacy_confirmed = {nid: confirmed(dict(origins[nid], families=set().union(*(i.get('legacyFamilies', i['families']) for i in ns[nid])))) for nid in nodes}
    artifact_families = defaultdict(set)
    for o in origins.values():
        for artifact in o['artifacts']:
            artifact_families[artifact].update(o['families'])
    # Resolve inline edge source-family metadata through its explicit sourceArtifact,
    # never through ID prefixes or graph adjacency.
    for supports in es.values():
        for s in supports:
            if not s['families']:
                s['families'].update(f for a in s['artifacts'] for f in artifact_families[a])
    strong = defaultdict(set); locators = defaultdict(set); lexical = defaultdict(set)
    for b in dossier:
        identity.require(all(n in nodes for n in b['occurrenceIDs']), 'DOSSIER_ENDPOINT_MISSING')
        if b['candidateMechanism'] == 'lexical_similarity_only':
            for n in b['occurrenceIDs']:
                lexical[n].update(b['occurrenceIDs'])
    for b in triages:
        identity.require(all(n in nodes for n in b['occurrenceIDs']), 'TRIAGE_ENDPOINT_MISSING')
        for n in b['occurrenceIDs']:
            if b['provisionalReviewCategory'] == 'strong_record_identity_candidate':
                strong[n].update(b['occurrenceIDs'])
            elif b['identifierScope'].get('source_local_literal_declaration'):
                locators[n].update(b['occurrenceIDs'])
    relations = {r['id']: r for r in spec['relations']}
    class_specs = {c['name']: c for c in spec['classes']}
    target_scope = ARTIFACTS | {'Tool', 'Algorithm', 'Workflow', 'DatasetMention'} | {
        c for c in candidates.descendants(class_specs, 'ComputationalModel') if not class_specs[c].get('abstract')}
    counts = Counter({k: 0 for k in ('acceptedRelationOccurrences', 'potentiallyRelevantTargetOccurrences',
        'directIndependentArtifactConnections', 'possibleCrossFamilyAlignmentOccurrences', 'evidenceProvenanceConfirmed',
        'sourceProvenanceRecoveredByExactRootContract', 'targetProvenanceRecoveredByExactRootContract',
        'bothEndpointProvenanceConfirmed', 'sourceEndpointProvenanceConfirmed', 'targetEndpointProvenanceConfirmed', 'ontologyCrossMarkedOccurrences')}); signature_cache = {}; grouped = {}; incidents = defaultdict(set); quote_edges = defaultdict(set)
    def owner(nid: str) -> bool:
        """Only existing curated artifact records count as independently observed owners."""
        return nodes[nid]['class'] in ARTIFACTS and nodes[nid].get('curationStatus') == 'curated' and confirmed(origins[nid])
    for eid, edge in sorted(edges.items()):
        identity.require(edge['source'] in nodes and edge['target'] in nodes, 'MISSING_ACCEPTED_ENDPOINT')
        s, t = edge['source'], edge['target']; target = nodes[t]; evidence = combine(es[eid])
        signature_key = (edge.get('inventoryId'), edge['relation'], nodes[s]['class'], target['class'])
        if signature_key not in signature_cache:
            signature_cache[signature_key] = signature_status(edge, nodes[s], target, spec)
        status = signature_cache[signature_key]
        source_ok, target_ok = confirmed(origins[s]), confirmed(origins[t])
        evidence_ok = confirmed(evidence)
        for q in evidence['quotes']:
            quote_edges[q].add(eid)
        relation = relations.get(edge.get('inventoryId'), {})
        annotation = relation.get('type', [])
        schema_cross = 'cross' in (annotation if isinstance(annotation, list) else [annotation])
        relevant = target['class'] in target_scope or target.get('curationStatus') == 'referenced' or bool(strong[t] or locators[t] or lexical[t])
        independent = bool(owner(t) and evidence_ok and evidence['families'].isdisjoint(origins[t]['families']) and evidence['artifacts'].isdisjoint(origins[t]['artifacts']))
        def peers(mapping: dict) -> list[str]:
            """Require exact class plus distinct documented source origins; no new matching."""
            return sorted(n for n in mapping[t] if n != t and nodes[n]['class'] == target['class'] and confirmed(origins[n])
                          and evidence['families'].isdisjoint(origins[n]['families']) and evidence['artifacts'].isdisjoint(origins[n]['artifacts']))
        record_peers = [n for n in peers(strong) if owner(n)]
        tier = 'outside_target_scope'; possible_cross = False
        if relevant:
            tier = TIERS[4]
            if evidence_ok and source_ok and target_ok and status == 'compatible':
                if record_peers and not owner(t):
                    tier = TIERS[1]; possible_cross = True
                elif independent or (target['class'] in ARTIFACTS and identity.own_keys(target) and target.get('curationStatus') == 'referenced'):
                    tier = TIERS[0]; possible_cross = independent
                elif peers(locators):
                    tier = TIERS[2]; possible_cross = True
                elif peers(lexical):
                    tier = TIERS[3]; possible_cross = True
        if evidence_ok and status == 'compatible':
            incidents[s].add(edge['relation']); incidents[t].add(edge['relation'])
        counts['acceptedRelationOccurrences'] += 1
        counts['potentiallyRelevantTargetOccurrences'] += relevant
        counts['directIndependentArtifactConnections'] += independent and status == 'compatible' and source_ok
        counts['possibleCrossFamilyAlignmentOccurrences'] += possible_cross
        counts['evidenceProvenanceConfirmed'] += evidence_ok
        counts['bothEndpointProvenanceConfirmed'] += source_ok and target_ok
        counts['sourceProvenanceRecoveredByExactRootContract'] += source_ok and not legacy_confirmed[s]
        counts['targetProvenanceRecoveredByExactRootContract'] += target_ok and not legacy_confirmed[t]
        counts['sourceEndpointProvenanceConfirmed'] += source_ok
        counts['targetEndpointProvenanceConfirmed'] += target_ok
        counts['ontologyCrossMarkedOccurrences'] += schema_cross
        key = (edge['relation'], edge.get('inventoryId', ''), '|'.join(sorted(evidence['families'])) or 'unknown', tier,
               status, source_ok, target_ok, evidence_ok, possible_cross)
        if key not in grouped:
            grouped[key] = dict(predicate=edge['relation'], inventoryId=edge.get('inventoryId'), sourceFamilies=sorted(evidence['families']),
                tier=tier, signatureStatus=status, sourceProvenanceConfirmed=source_ok, targetProvenanceConfirmed=target_ok,
                evidenceProvenanceConfirmed=evidence_ok, possibleCrossFamily=possible_cross, acceptedOccurrences=0, examples=[])
        g = grouped[key]; g['acceptedOccurrences'] += 1
        if len(g['examples']) < 2:
            g['examples'].append(dict(edgeID=eid, sourceID=s, targetID=t, acceptedPredicate=edge['relation'],
                explicitlyIndependentArtifactTarget=independent, recordCandidatePeers=record_peers[:2], recordCandidatePeerCount=len(record_peers),
                evidenceReferences=evidence['references'], sourceReferences=origins[s]['references'], targetReferences=origins[t]['references']))
    total = counts['acceptedRelationOccurrences']
    counts['evidenceProvenanceUnresolved'] = total-counts['evidenceProvenanceConfirmed']
    counts['endpointProvenanceUnresolved'] = total-counts['bothEndpointProvenanceConfirmed']
    counts['sourceEndpointProvenanceUnresolved'] = total-counts['sourceEndpointProvenanceConfirmed']
    counts['targetEndpointProvenanceUnresolved'] = total-counts['targetEndpointProvenanceConfirmed']
    counts['quoteHashesReusedByMultipleEdges'] = sum(len(v)>1 for v in quote_edges.values())
    counts['edgeOccurrencesWithReusedQuote'] = len(set().union(*(v for v in quote_edges.values() if len(v)>1)))
    queue, queue_coverage = pilot_queue(dossier, incidents)
    from src.evaluation.step14_shared_references import shared_references
    hubs = shared_references(graph, origins, {eid: combine(es[eid]) for eid in edges}, signature_cache, local_identifiers)
    counts['curatedRootNodesWithRecoveredProvenance'] = sum(confirmed(origins[n]) and not legacy_confirmed[n] for n in nodes)
    return dict(sharedReferenceGroups=hubs['groups'], sharedReferenceSummary=hubs['summary'],
        summary=dict(sorted(counts.items())), tierCounts={t: sum(g['acceptedOccurrences'] for g in grouped.values() if g['tier']==t) for t in TIERS},
        possibleCrossFamilyByTier={t: sum(g['acceptedOccurrences'] for g in grouped.values() if g['tier']==t and g['possibleCrossFamily']) for t in TIERS},
        relationInventory=[grouped[k] for k in sorted(grouped)], pilotQueue=queue, pilotCoverage=queue_coverage,
        oversizedCrossFamily=[deepcopy(b) for b in sorted(oversized, key=lambda b:b['blockID']) if b['crossFamily']],
        oversizedCoverage=dict(allBlocks=len(oversized), crossFamilyBlocks=sum(b['crossFamily'] for b in oversized), membersExpanded=0))


def run(output: Path = OUTPUT) -> dict:
    """Verify existing authorities and consume saved records only in the terminal run."""
    identity.require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    identity.require(output.resolve().is_relative_to(Path('var/study2_step14/alignment-opportunities').resolve()), 'OPPORTUNITY_OUTPUT_REQUIRED')
    graph, spec, sidecar, pins = identity.verified_inputs()
    identity.require(spec['ontology']['version'] == '0.1.7', 'ONTOLOGY_VERSION_DRIFT')
    rm, _, review_pins = triage.inputs(triage.ROOT); pins.update(review_pins)
    def check(path: Path, expected: str) -> None:
        """Extend immutable provenance without rebuilding earlier diagnostics."""
        identity.require(identity.sha(path) == expected, 'INPUT_HASH_DRIFT:' + str(path)); pins[str(path)] = expected
    check(triage.OUTPUT / 'manifest.json', TRIAGE_PIN)
    tm = json.loads((triage.OUTPUT / 'manifest.json').read_bytes())
    identity.require(tm['version'] == triage.VERSION, 'TRIAGE_VERSION_DRIFT')
    for path, expected in tm['inputHashes'].items():
        if path in pins:
            identity.require(pins[path] == expected, 'INPUT_AUTHORITY_CHAIN_DRIFT')
    check(Path('src/evaluation/step14_identifier_scope_triage.py'), tm['implementationSha256'])
    check(triage.OUTPUT / 'identifier-triage.jsonl', tm['outputHashes']['identifier-triage.jsonl'])
    check(triage.ROOT / 'oversized-summary.jsonl', rm['outputHashes']['oversized-summary.jsonl'])
    owners = {}
    def native():
        """Resolve explicit owner provenance while streaming immutable native rows."""
        for row in review.json_rows(sidecar):
            pr = row['provenance']
            if pr.get('path') and pr['path'] not in owners:
                path = Path(pr['path']); check(path, pr['sha256'])
                owners[str(path)] = json.loads(path.read_bytes())['owner']['endpointID']
            yield row
    result = inventory(graph, native(), review.json_rows(identity.ROOT / 'derivation-provenance.jsonl'),
        list(review.json_rows(triage.ROOT / 'review-dossier.jsonl')), list(review.json_rows(triage.OUTPUT / 'identifier-triage.jsonl')),
        list(review.json_rows(triage.ROOT / 'oversized-summary.jsonl')), spec, owners)
    for path, expected in pins.items():
        identity.require(identity.sha(Path(path)) == expected, 'INPUT_CHANGED_DURING_DIAGNOSTIC:' + path)
    output.mkdir(parents=True, exist_ok=False)
    groups = result.pop('sharedReferenceGroups')
    with (output / 'shared-reference-hubs.jsonl').open('xb') as handle:
        for group in groups:
            handle.write(identity.encoded(group) + b'\n')
    (output / 'inventory.json').write_bytes(identity.encoded(result) + b'\n')
    with (output / 'pilot-review-queue.tsv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle, delimiter='\t'); writer.writerow(['blockID','class','families','members','acceptedPredicates','boundedEvidenceAndPointers','identityDecision'])
        for row in result['pilotQueue']:
            writer.writerow([row['blockID'], row['ontologyClass'], ','.join(row['sourceFamilies']), row['memberCount'],
                             ','.join(row['incidentAcceptedPredicates']), identity.encoded(row['representatives']).decode(), 'unadjudicated'])
    report = ['# Cross-artifact alignment opportunity diagnostic', '', 'Read-only inventory of accepted relation occurrences; no alignment decisions.', '',
              *[f'- {k}: {v}' for k,v in result['summary'].items()], '', '## Evidence tiers', '',
              *[f'- {k}: {v}' for k,v in result['tierCounts'].items()], '', 'Possible cross-family counts by tier (not accepted alignments):', '',
              *[f'- {k}: {v}' for k,v in result['possibleCrossFamilyByTier'].items()], '', '## Pilot queue', '',
              json.dumps(result['pilotCoverage'], sort_keys=True), '', '## Oversized blocks', '', json.dumps(result['oversizedCoverage'], sort_keys=True),
              '', '## Relation denominators', '', '| Predicate | Source family set | Accepted occurrences |', '|---|---|---:|']
    denominators = Counter()
    for r in result['relationInventory']:
        denominators[(r['predicate'], ','.join(r['sourceFamilies']) or 'unknown')] += r['acceptedOccurrences']
    report += [f'| {p} | {f} | {n} |' for (p,f),n in sorted(denominators.items())]
    shared = result['sharedReferenceSummary']
    report += ['', '## Exact GitHub provenance recovery', '',
        'Curated repository roots may omit optional rawSource. v2 requires the recorded numeric ID, canonical key, fullName/htmlUrl, repo-root lineage and metadata evidence to agree exactly. Recovery counters measure endpoint occurrences, not new alignments. Historical hasFile signature exclusions remain unchanged.',
        '', '## Shared external-reference hubs', '',
        *[f'- {k}: {v}' for k,v in shared['denominators'].items()],
        f"- Provisional groups: {shared['groups']}; shared groups: {shared['sharedGroups']}; distinct accepted edges in shared groups: {shared['acceptedUniqueEdgesInSharedGroups']}",
        '', '| Category | Tier | Referrer scope | Groups |', '|---|---|---|---:|',
        *[f"| {r['category']} | {r['tier']} | {r['scope']} | {r['groups']} |" for r in shared['coverage']],
        '', 'Category totals (including zeros): '+json.dumps(shared['groupsByCategory'],sort_keys=True),
        '', 'Tier totals (including zeros): '+json.dumps(shared['groupsByTier'],sort_keys=True),
        '', *['- '+s for s in shared['limitations']]]
    report += ['', '## Limitations', '', *['- '+s for s in LIMITS]]
    (output / 'report.md').write_text('\n'.join(report)+'\n', encoding='utf-8')
    manifest = dict(version=VERSION, diagnosticOnly=True, graphWrites=0, providerCalls=0, inputHashes=pins,
        implementationSha256=identity.sha(Path(__file__)), sharedReferenceImplementationSha256=identity.sha(Path('src/evaluation/step14_shared_references.py')),
        sharedReferenceSummary=result['sharedReferenceSummary'], summary=result['summary'], tierCounts=result['tierCounts'], possibleCrossFamilyByTier=result['possibleCrossFamilyByTier'], pilotCoverage=result['pilotCoverage'],
        outputHashes={n:identity.sha(output/n) for n in ('inventory.json','pilot-review-queue.tsv','report.md','shared-reference-hubs.jsonl')}, limitations=LIMITS)
    (output / 'manifest.json').write_bytes(identity.encoded(manifest)+b'\n')
    return manifest


def main() -> None:
    """Expose only the offline researcher-terminal diagnostic."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT);args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('OFFLINE_ONLY')), patch.object(socket.socket,'connect_ex',side_effect=RuntimeError('OFFLINE_ONLY')):
        run(args.output)


if __name__ == '__main__':
    main()
