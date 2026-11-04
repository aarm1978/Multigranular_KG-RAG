"""Provisional shared-reference groups across accepted relations; no graph changes."""
from __future__ import annotations

from collections import Counter, defaultdict
import re
from itertools import chain

from src.evaluation import step14_identity_preview as identity
from src.evaluation import step14_semantic_candidates as candidates
from src.evaluation.step14_identifier_scope_triage import locator

CATEGORIES = {'Paper': 'bibliographic', 'DatasetResource': 'dataset_resource', 'Repository': 'repository',
              'Tool': 'software_dependency', 'Dependency': 'software_dependency'}
# Exact existing predicate names; each occurrence must also satisfy its own inventory signature.
PREDICATES = {'cites', 'references', 'referencesDataset', 'referencesRepository', 'referencePublication',
              'hasCodeRepository', 'usesDataset', 'dependsOn', 'dependsOnRepository', 'usesTool',
              'mentions', 'mentionsTool', 'mentionsDataset', 'implementedBy', 'documents'}
LIMITATIONS = [
    'A/B/C are provisional record-identity, exact-locator and contextual-name evidence tiers, never accepted equivalences.',
    'All five target classes are read from v4, including Dependency; previous semantic-candidate membership is not required.',
    'Exact identifiers are grouped within target class and identifier namespace. No identifier union, URL resolution or fuzzy normalization occurs.',
    'Repository root identity never establishes identical commits, code or implementations. Package declarations without registry/version authority stay C.',
    'Group referrers are distinct traceable corpus artifact IDs, not independent scientific confirmations. Repeated edges/quotes do not increase that count.',
    'Explicit materialized_repository_file mirrors are excluded from referrer counts and reported separately; undocumented mirrors cannot be inferred.',
    'Counts by identifier group overlap when a target has several own identifiers. Accepted-edge denominators are deduplicated separately.',
    'Only the listed existing predicates with compatible signatures enter groups. Other predicates and incompatible/legacy signatures remain counted as exclusions.',
    'Missing/ambiguous source-owner mappings are reported and excluded from distinct referrers, without adjacency or ID-prefix fallback.',
    'Tools DOI scope is the software record, not software implementation or scientific equivalence. No pairwise artifact connections are enumerated.',
]


def target_keys(node: dict, local_literals=(), allow_authoritative: bool = True) -> list[tuple[str, str, str, str]]:
    """Read only established own-ID regimes; keep locators/names in weaker tiers."""
    cls = node['class']; a = node.get('attributes', {}); key = node.get('canonicalKey', '')
    result = set()
    authoritative = (allow_authoritative and bool(node.get('evidence')) and node.get('curationStatus') in {'curated', 'referenced'}
        and not (a.get('provisionalIdentity') or node.get('provisionalIdentity')
                 or a.get('identityScope') == 'source_local' or node.get('identityScope') == 'source_local'))
    for scheme, value in (identity.own_keys(node) if authoritative else ()):
        if scheme in {'doi', 'hydroshare', 'github'} and cls in CATEGORIES:
            result.add(('A', scheme, value, 'entity_own_record'))
    if authoritative and cls in {'Tool', 'Repository'} and node.get('identityRegime') in {'software_doi', 'repository_doi'} and key.startswith('doi:'):
        value = key[4:]
        if re.fullmatch(r'10\.\d{4,9}/\S+', value) and node.get('evidence'):
            result.add(('A', 'doi', value, 'typed_record_not_implementation'))
    urls = {v for k, v in a.items() if k in {'url', 'htmlUrl', 'exactIdentifier', 'identifier'} and isinstance(v, str) and v}
    urls.update(local_literals)
    if authoritative and cls == 'Repository' and node.get('identityRegime') == 'github_repository_url':
        declared = key.removeprefix('url:').removeprefix('github-repo-url:')
        if locator(declared)['category'] == 'github_repository_root' and node.get('evidence'):
            result.add(('A', 'github_repository_root', declared, 'repository_record_not_code_version'))
            urls.discard(declared)
    if cls == 'Dependency' and node.get('identityRegime') == 'ecosystem_package_name':
        ecosystem, name = a.get('ecosystem'), a.get('canonicalName')
        if isinstance(ecosystem, str) and isinstance(name, str) and key == f'package:{ecosystem}:{name}':
            result.add(('C', 'ecosystem_package_name', key, 'registry_and_release_identity_unestablished'))
    if authoritative and cls == 'Repository' and node.get('identityRegime') == 'github_numeric_id':
        from src.evaluation.step14_alignment_opportunities import github_root_family
        if github_root_family(node):
            result.add(('A', 'github_repository_root', a['htmlUrl'], 'repository_record_not_code_version'))
            urls.discard(a['htmlUrl'])
    for url in sorted(urls):
        if locator(url).get('scheme') in {'http', 'https', 's3'}:
            result.add(('B', 'literal_locator', url, locator(url)['category']))
        elif url in local_literals:
            result.add(('B', 'source_local_literal', url, 'literal_not_global_identity'))
    if not result:
        for field in ('label', 'name', 'title'):
            values = a.get(field, [])
            values = [values] if isinstance(values, str) else values if isinstance(values, list) else []
            for value in values:
                if isinstance(value, str) and value.strip():
                    result.add(('C', 'exact_name_only', value, 'context_required'))
    return sorted(result)


def owner_family(node: dict) -> str | None:
    """Use the curated owner's own inline contract, not other artifacts' mentions."""
    from src.evaluation.step14_alignment_opportunities import github_root_family
    return candidates.deterministic_family(node) or github_root_family(node)


def source_registry(graph: dict, origins: dict) -> tuple[dict, set]:
    """Resolve original corpus owners using explicit fields and frozen evidence constructors."""
    aliases = defaultdict(set); roots = defaultdict(set); mirrors = set()
    for n in graph['nodes']:
        if n.get('curationStatus') != 'curated' or n['class'] not in {'Paper', 'DatasetResource', 'Repository', 'DocumentationPage'}:
            continue
        nid=n['id']; a=n.get('attributes', {}); ev=n.get('evidence', {})
        if not ev or not owner_family(n):
            continue
        aliases[nid].add(nid)
        if ev.get('sourceArtifact'):
            aliases[ev['sourceArtifact']].add(nid)
        if n['class'] == 'Paper' and a.get('canonicalArtifactId') and a.get('canonicalArtifactId') == ev.get('sourceArtifact'):
            aliases[a['canonicalArtifactId']].add(nid)
        if n['class'] == 'DatasetResource' and a.get('resourceId') and ev.get('sourceArtifact') == 'hydroshare:' + a['resourceId']:
            aliases[a['resourceId']].add(nid)
        if n['class'] == 'Repository' and n.get('identityRegime') == 'github_numeric_id' and a.get('htmlUrl') == ev.get('sourceArtifact'):
            roots[a['htmlUrl']].add(nid)
    # RepoContext.file_evidence explicitly couples sourceArtifact tree/SHA,
    # sourceLocation blob/SHA/path, and evidence.version. This is not URL guessing.
    for record in chain(graph['nodes'], graph['edges']):
        ev=record.get('evidence', {}); raw=ev.get('sourceArtifact', ''); version=ev.get('version')
        if isinstance(raw, str) and isinstance(version, str) and re.fullmatch(r'[0-9a-f]{40}', version):
            root, sep, suffix=raw.rpartition('/tree/')
            if sep and root in roots and suffix == version and str(ev.get('sourceLocation', '')).startswith(root+'/blob/'+version+'/'):
                aliases[raw].update(roots[root])
    for e in graph['edges']:
        a=e.get('attributes', {})
        if e['relation'] == 'documents' and a.get('mirrorKind') == 'materialized_repository_file' and a.get('repositoryPath') and e.get('evidence'):
            mirrors.add(e['source'])
    return aliases, mirrors


def shared_references(graph: dict, origins: dict, edge_supports: dict,
                      signatures: dict, local_identifiers: dict) -> dict:
    """Group exact keys in linear indexed passes; never enumerate artifact pairs."""
    nodes={n['id']:n for n in graph['nodes']}; aliases, mirrors=source_registry(graph, origins)
    keys={nid:target_keys(n, local_identifiers.get(nid, ()), allow_authoritative=nid not in local_identifiers) for nid,n in nodes.items() if n['class'] in CATEGORIES}
    # Governed own-dataset DOI assertions, already accepted in v4.
    for e in graph['edges']:
        t=nodes[e['target']]; a=t.get('attributes', {})
        if e['relation']=='hasIdentifier' and e.get('inventoryId')=='C-D04' and nodes[e['source']]['class']=='DatasetResource' and t['class']=='Identifier' and a.get('identifierType')=='DOI' and e.get('evidence'):
            value=a.get('identifierValue')
            if isinstance(value,str) and re.fullmatch(r'10\.\d{4,9}/\S+',value):
                keys[e['source']]=sorted(set(keys[e['source']])|{('A','doi',value,'entity_own_record')})
    curated=defaultdict(set)
    for nid, declarations in keys.items():
        if nodes[nid].get('curationStatus')=='curated' and nodes[nid]['class'] in {'Paper','DatasetResource','Repository'}:
            for tier,scheme,value,scope in declarations:
                if tier=='A':curated[(nodes[nid]['class'],scheme,value)].add(nid)
    groups={}; counts=Counter({k:0 for k in ('acceptedEdges','targetClassEligibleEdges','predicateEligibleEdges',
        'signatureExcludedEdges','missingEvidenceEdges','edgesWithoutGroupKey','groupedEdges',
        'edgesWithMissingOrAmbiguousOrigin','edgesWithOnlyMirroredOrigins')})
    for e in sorted(graph['edges'],key=lambda r:r['id']):
        counts['acceptedEdges']+=1; t=nodes[e['target']]; cls=t['class']
        if cls not in CATEGORIES:continue
        counts['targetClassEligibleEdges']+=1
        if e['relation'] not in PREDICATES:continue
        counts['predicateEligibleEdges']+=1
        sigkey=(e.get('inventoryId'),e['relation'],nodes[e['source']]['class'],cls)
        if signatures[sigkey]!='compatible':counts['signatureExcludedEdges']+=1;continue
        support=edge_supports[e['id']]
        if not support['evidence']:counts['missingEvidenceEdges']+=1;continue
        declarations=keys[t['id']]
        if not declarations:counts['edgesWithoutGroupKey']+=1;continue
        counts['groupedEdges']+=1
        raw_origins=set(support['artifacts'])
        # These are original source-declaration fields, never target URLs or labels.
        for d in e.get('attributes', {}).get('sourceDeclarations', []):
            for field in ('sourceArtifact','pageUrl'):
                if isinstance(d.get(field),str):raw_origins.add(d[field])
        resolved=set(); unresolved=set()
        for raw in raw_origins:
            if len(aliases.get(raw,set()))==1:resolved.update(aliases[raw])
            else:unresolved.add(raw)
        if not raw_origins or unresolved:counts['edgesWithMissingOrAmbiguousOrigin']+=1
        mirrored=resolved & mirrors; referrers=resolved-mirrors
        if mirrored and not referrers:counts['edgesWithOnlyMirroredOrigins']+=1
        for tier,scheme,value,scope in declarations:
            key=(cls,tier,scheme,value,scope)
            g=groups.setdefault(key,dict(targets=set(),edges=set(),artifacts=set(),pairs=set(),families=set(),
                predicates=Counter(),versions=set(),missingVersionEdges=0,unresolvedEdges=set(),mirrors=set(),examples=[],quotes=set()))
            g['targets'].add(t['id']);g['edges'].add(e['id']);g['artifacts'].update(referrers)
            g['pairs'].update((a,t['id']) for a in referrers);g['mirrors'].update(mirrored)
            g['families'].update(owner_family(nodes[a]) for a in referrers)
            g['predicates'][e['relation']]+=1;g['quotes'].update(support['quotes'])
            versions={f:v for f,v in t.get('attributes',{}).items() if f in {'version','versionNumber','commitSHA','repositoryRef'} and v not in (None,'')}
            for field in ('versionSpec','ecosystem','extras','marker','depGroup','dependencyKind'):
                if e.get('attributes',{}).get(field) not in (None,''):versions['edge.'+field]=e['attributes'][field]
            if not any(f in versions for f in ('version','versionNumber','commitSHA','repositoryRef','edge.versionSpec')):g['missingVersionEdges']+=1
            if versions:g['versions'].add(identity.encoded(versions))
            if not raw_origins or unresolved:g['unresolvedEdges'].add(e['id'])
            if len(g['examples'])<2:g['examples'].append(dict(edgeID=e['id'],acceptedPredicate=e['relation'],sourceID=e['source'],targetID=t['id'],
                evidenceReferences=support['references'],referringArtifacts=sorted(referrers),unresolvedOriginValues=sorted(unresolved)))
    output=[]
    import json
    for (cls,tier,scheme,value,scope),g in sorted(groups.items()):
        # Singleton-key groups are retained for explicit opportunity denominators.
        artifacts=sorted(g['artifacts']);edges=sorted(g['edges']);targets=sorted(g['targets']);versions=sorted(g['versions'])
        output.append(dict(targetClass=cls,category=CATEGORIES[cls],evidenceTier=tier,identifierScheme=scheme,identifierValue=value,identityScope=scope,
            targetIDs=targets,targetEvidenceReferences=[dict(targetID=t, references=origins[t]['references']) for t in targets[:2]],targetRepresentation='one_shared_graph_node' if len(targets)==1 else 'multiple_existing_nodes_or_stubs',
            distinctOriginatingArtifacts=len(artifacts),originatingArtifactIDs=artifacts,sourceFamilies=sorted(g['families']),
            acceptedReferenceEdgeOccurrences=len(edges),edgeMembershipSha256=candidates.token(edges),
            uniqueArtifactToTargetReferences=len(g['pairs']),uniqueArtifactToProvisionalGroupReferences=len(artifacts),
            sharedByMultipleArtifacts=len(artifacts)>=2,connectionScope='cross_family' if len(artifacts)>=2 and len(g['families'])>1 else 'within_family' if len(artifacts)>=2 else 'not_shared',
            matchingCuratedArtifactIDs=sorted(curated.get((cls,scheme,value),set())) if tier=='A' else [],
            acceptedPredicates=dict(sorted(g['predicates'].items())),versionVariants=[json.loads(v) for v in versions],missingVersionEdgeOccurrences=g['missingVersionEdges'],
            unresolvedOriginEdgeOccurrences=len(g['unresolvedEdges']),excludedMirrorArtifactIDs=sorted(g['mirrors']),
            targetProvenanceUnresolvedIDs=[t for t in targets if not (origins[t]['evidence'] and origins[t]['families'] and origins[t]['artifacts'])],
            distinctQuoteHashes=len(g['quotes']),examples=g['examples'],equivalenceApproved=False))
    strata=Counter((g['category'],g['evidenceTier'],g['connectionScope']) for g in output)
    return dict(groups=output,summary=dict(denominators=dict(counts),groups=len(output),
        sharedGroups=sum(g['sharedByMultipleArtifacts'] for g in output),
        groupsByCategory={c:sum(g['category']==c for g in output) for c in sorted(set(CATEGORIES.values()))},
        groupsByTier={t:sum(g['evidenceTier']==t for g in output) for t in ('A','B','C')},
        acceptedUniqueEdgesInSharedGroups=len(set().union(*(g['edges'] for g in groups.values() if len(g['artifacts'])>=2))),
        coverage=[dict(category=c,tier=t,scope=s,groups=n) for (c,t,s),n in sorted(strata.items())],limitations=LIMITATIONS))
