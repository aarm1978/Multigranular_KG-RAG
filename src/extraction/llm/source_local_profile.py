"""Versioned non-Publication scope; no changes to frozen ontology or replay defaults."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import importlib
import inspect
from typing import Any, Mapping

import yaml

from src.extraction.llm import semantic_target_profiles as legacy
from src.extraction.llm.pilot_preflight import canonical, digest

VERSION = 'study2-source-local-semantics/0.4.1'
INVENTORY = Path(__file__).with_name('nonpublication_semantic_v041.yaml')
POLICY_PATH = Path(__file__).resolve().parents[3] / 'docs/study2_source_local_semantics_v0.4.1.md'


def inventory() -> dict:
    """Read the explicit prospective inventory against the immutable base ontology."""
    data = yaml.safe_load(INVENTORY.read_text())
    if data['version'] != VERSION or data['baseOntologySha256'] != legacy.ONTOLOGY_SHA256:
        raise ValueError('prospective_inventory_authority_mismatch')
    return data


def get_profile(family: str, *, version: str, ontology: Mapping[str, Any] | None = None) -> dict:
    """Project enumerated targets with exact canonical ontology signatures."""
    if version != VERSION:
        raise ValueError('unsupported_prospective_version')
    spec = legacy.load_ontology()
    if ontology is not None and ontology != spec:
        raise ValueError('base_ontology_drift')
    data = inventory(); scope = data['families'][family]
    profile = legacy.get_profile(family)
    classes = {r['id']: r for r in spec['classes']}
    relations = {r['id']: r for r in spec['relations']}
    for group, declarations in [('entities', classes), ('relations', relations)]:
        if len(scope[group]) != len(set(scope[group])):
            raise ValueError('duplicate_target')
        old = profile[group]; profile[group] = {}
        for identifier in scope[group]:
            declaration = deepcopy(declarations[identifier])
            if declaration.get('abstract'):
                raise ValueError('abstract_target')
            policy = deepcopy(old.get(identifier, dict(modelAuthorable=True, mode='semantic_candidate', requiredGates=[])))
            policy['declaration'] = declaration
            if identifier in {'A-D01', 'A-C01', 'A-P01', 'A-P25'}:
                policy.update(modelAuthorable=True, mode='evidence_backed_source_local', requiredGates=[])
                policy.pop('identityPolicy', None)
            profile[group][identifier] = policy
    profile.update(contractID=VERSION, ontologyVersion=spec['ontology']['version'],
                   baseOntologyVersion=spec['ontology']['version'], inventorySha256=digest(INVENTORY.read_bytes()),
                   genericOccurrenceTargets=scope['genericOccurrences'],
                   exclusions=data['exclusions'], identityPolicy='exact_deterministic_or_evidence_scoped_local',
                   implementationProjectionOnly=True)
    return profile


def coverage(family: str, schema: dict) -> dict:
    """Fail if an approved target disappears from the executable provider boundary.

    All inventory entries use the same versioned native-validator dispatcher and
    construction adapter; Method is explicitly unresolved, never falsely covered.
    End-to-end examples test those dispatchers, not just a second allowlist.
    """
    profile = get_profile(family, version=VERSION)
    from src.extraction.llm.construction_acceptance import RELEASES, project_replay
    route = {'hydroshare':('datasets','validate_dataset_candidates'),
             'github':('coderepos','validate_repository_candidates'),
             'ciroh_hub':('documents','validate_hub_candidates')}[family]
    validator=getattr(importlib.import_module('src.extraction.llm.'+route[0]+'.candidate_validation'),route[1])
    if 'profile_version' not in inspect.signature(validator).parameters or 'policy_version' not in inspect.signature(project_replay).parameters:
        raise ValueError('versioned_validation_or_construction_route_missing')
    spec=legacy.load_ontology();classes={c['id']:c for c in spec['classes']};by_iri={c['iri']:c for c in spec['classes']}
    def matches(identifier: str, signature: Any) -> bool:
        """Check that an executable concrete endpoint can inhabit each signature."""
        declaration=classes[identifier];seen=set();names=signature if isinstance(signature,list) else [signature]
        while declaration['id'] not in seen:
            seen.add(declaration['id'])
            if declaration['name'] in names:return True
            declaration=by_iri.get(declaration.get('parent'))
            if declaration is None:return False
        raise ValueError('cyclic_endpoint_inheritance')
    available={*profile['entities'],profile['ownerClassID']}
    generic=next(r for r in spec['relations'] if r['id']=='D-26')
    if ('D-26' in profile['relations'] or not matches(profile['ownerClassID'],generic['domain'])
            or any(i not in profile['entities'] or not matches(i,generic['range']) for i in profile['genericOccurrenceTargets'])):
        raise ValueError('invalid_pipeline_derived_occurrence_route')
    for identifier,record in profile['relations'].items():
        declaration=record['declaration']
        if any(not any(matches(c,declaration[side]) for c in available) for side in ('domain','range')):
            raise ValueError('unreachable_relation_signature:'+identifier)
    for identifier,record in {**profile['entities'],**profile['relations']}.items():
        if family=='github' and identifier in {'A-P13','C-C16'}:continue
        if set(record['requiredGates'])-RELEASES[family].get(identifier,set()):
            raise ValueError('approved_target_missing_construction_release:'+identifier)
    result = {}
    for group, targets in [('candidateNodes', 'entities'), ('candidateEdges', 'relations')]:
        branches = schema['properties'][group]['items']['anyOf']
        actual = {b['properties']['inventoryId']['enum'][0] for b in branches}
        if actual != set(profile[targets]):
            raise ValueError('executable_target_coverage_drift:' + group)
        result[targets] = {i: ('unresolved_positive' if family == 'github' and i in {'A-P13','C-C16'}
                              else 'controlled_endpoint' if i == 'A-C07' else 'structured_version_proof_or_unresolved' if family=='github' and i in {'A-C10','C-C09'} else 'native_validation_and_construction')
                           for i in sorted(actual)}
    result.update(version=VERSION, inventorySha256=profile['inventorySha256'],
                  derivedTargets={'D-26': profile['genericOccurrenceTargets']})
    result['sha256'] = digest(canonical(result))
    return result
