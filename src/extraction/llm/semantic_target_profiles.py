"""Read-only implementation projection of frozen Step 11 v0.3 §§2–8.

The contract remains the methodological authority. Only explicit source allowlists
are projected here; declarations, inheritance and signatures come from the frozen
ontology specification. No candidate execution, semantic judgment or KG authority.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any, Mapping

import yaml


CONTRACT_ID = "study2-step11-semantic-contracts/v0.3"
ONTOLOGY_PATH = Path(__file__).resolve().parents[2] / "ontology" / "ontology_spec.yaml"
ONTOLOGY_SHA256 = "47f035081d4e883146a479130c1f4c4751f0c40358fd1a8d154b43b36e34371e"
MODELS = ("A-DOM03a", "A-DOM03b", "A-DOM03c", "A-DOM03d", "A-DOM03e")
ENTITY_IDS = {
    "hydroshare": ("A-DOM04", "A-D12", "A-DOM02", *MODELS, "A-C11", "A-C01"),
    "github": ("A-C07", "A-DOM02", *MODELS, "A-D01", "A-C11", "A-C08", "A-DOM13", "A-C10", "A-P13"),
    "ciroh_hub": ("A-DOM02", *MODELS, "A-D01", "A-P13", "A-C01", "A-DC05", "A-DC06", "A-C11", "A-DC08", "A-DOM12"),
}
RELATIONS = {
    "hydroshare": (("C-D16", "containsVariable"), ("C-D17", "hasMeasurement"), ("C-D18", "usesTool"),
                   ("C-D24", "mentionsTool"), ("C-D25", "usesModel"), ("C-D26", "mentionsModel"),
                   ("C-D22", "explainsWorkflow"), ("D-17", "generatedBy")),
    "github": (("C-C07", "hasPurpose"), ("C-C11", "usesTool"), ("C-C22", "mentionsTool"), ("D-22", "implementedBy"),
               ("C-C21", "usesModel"), ("C-C23", "mentionsModel"), ("C-C15", "usesDataset"),
               ("C-C10", "explainsWorkflow"), ("C-C08", "describesFunction"), ("C-C20", "describesAlgorithm"),
               ("C-C09", "hasModelVersion"), ("C-C16", "implementsMethod")),
    "ciroh_hub": (("C-DC17", "catalogs"), ("C-DC19", "hasComponent"), ("C-DC07", "describesTool"),
                  ("C-DC16", "describesModel"), ("C-DC27", "describesDataset"), ("C-DC28", "describesMethod"),
                  ("D-22", "implementedBy"), ("C-DC20", "hasProcedure"), ("C-DC10", "hasStep"),
                  ("C-DC09", "explainsWorkflow"), ("C-DC12", "hasExample"), ("C-DC11", "hasParameter")),
}
OWNERS = {"hydroshare": "A-D01", "github": "A-C01", "ciroh_hub": "A-DC01"}


def load_ontology() -> dict[str, Any]:
    """Load exact frozen v0.1.6 bytes; never generate or modify the ontology."""
    raw = ONTOLOGY_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ONTOLOGY_SHA256:
        raise ValueError("Frozen ontology specification hash mismatch")
    document = yaml.safe_load(raw)
    if document["ontology"]["version"] != "0.1.6":
        raise ValueError("Expected frozen ontology v0.1.6")
    return document


def _policy(family: str, identifier: str) -> dict[str, Any]:
    """Project only explicit source-specific operational constraints."""
    policy: dict[str, Any] = {"modelAuthorable": True, "mode": "semantic_candidate", "requiredGates": []}
    if (family, identifier) in {("hydroshare", "A-C01"), ("github", "A-D01"),
                                ("ciroh_hub", "A-D01"), ("ciroh_hub", "A-C01")}:
        policy.update(modelAuthorable=False, mode="source_exact_endpoint",
                      identityPolicy="Reuse exact accepted endpoints; only contract-admissible source-scoped stubs, never name-only merging")
    if family == "hydroshare" and identifier in {"A-D12", "C-D17"}:
        policy.update(requiredGates=["explicit_readme_measurement"], evidenceSources=["README"],
                      constraint="Individuating observation context required; variable lists and dataset files do not qualify; zero yield permitted")
    if family == "github" and identifier in {"A-C07", "C-C07"}:
        policy.update(schemeID="ciroh-repository-purpose", schemeVersion="1.0.0",
                      nodeIDPattern="repo-purpose:1.0.0:{category_key}", categoryCount=6,
                      constraint="Exactly six §7 seed instances; no inferred membership or other category")
        if identifier == "A-C07":
            policy.update(modelAuthorable=False, mode="controlled_vocabulary_seed")
        else:
            policy["requiredGates"] = ["repository_specific_purpose_evidence", "approved_category_endpoint"]
    if family == "github" and identifier in {"A-P13", "C-C16"}:
        policy.update(requiredGates=["accepted_publication_method_endpoint", "explicit_method_endpoint_binding"],
                      unresolvedDisposition="unresolved_endpoint_non_KG",
                      reconsideration="After accepted full-corpus Publication production; later materialization requires separately authorized Step 14",
                      constraint="A-P13 Publication discourse occurrence; DOI, name or technique use alone is insufficient")
        if identifier == "A-P13":
            policy.update(modelAuthorable=False, mode="accepted_publication_endpoint")
        else:
            policy["requiredGates"].append("explicit_implementation_evidence")
    if family == "github" and identifier in {"A-C10", "C-C09"}:
        policy.update(requiredGates=["own_repository_product", "explicit_prose_version", "absent_from_deterministic_assertions"],
                      constraint="Exclude dependency, environment/framework and referenced upstream versions")
    if family == "github" and identifier in {"A-C08", "C-C08", "A-DOM13", "C-C20"}:
        policy["requiredGates"] = ["explicit_descriptive_prose"]
    if family == "ciroh_hub" and identifier in {"A-DC08", "A-DOM12", "C-DC12", "C-DC11"}:
        policy.update(mode="parent_dependent", parentClassIDs=["A-DC05", "A-DC06"],
                      parentRelationPaths=[["C-DC20"], ["C-DC20", "C-DC10"]],
                      requiredGates=["accepted_procedure_or_step_parent", "accepted_required_parent_relations", "independent_parent_and_dependent_evidence"],
                      constraint="Hold/suppress dependent when parent or required relation fails; no free-floating discovery")
        if identifier in {"A-DOM12", "C-DC11"}:
            policy["requiredGates"].append("explanatory_parameter_prose")
        else:
            policy["constraint"] += "; displayed snippets may support Example, never inferred code semantics"
    if family == "ciroh_hub" and identifier in {"A-P13", "C-DC28"}:
        policy["requiredGates"] = ["supported_method", "substantive_method_description"]
    return policy


def get_profile(family: str, *, ontology: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return a detached deterministic scope projection, not a new authority.

    Optional supplied ontology must equal the frozen declaration document. This
    fails closed on altered signatures, class IDs or inheritance while keeping the
    specification as the sole source of those definitions.
    """
    if family not in ENTITY_IDS:
        raise ValueError(f"Unsupported source family: {family}")
    spec = load_ontology()
    if ontology is not None and ontology != spec:
        raise ValueError("Supplied ontology differs from frozen v0.1.6")
    classes = {r["id"]: r for r in spec["classes"]}
    relations = {r["id"]: r for r in spec["relations"]}
    if len(classes) != len(spec["classes"]) or len(relations) != len(spec["relations"]):
        raise ValueError("Duplicate ontology inventory IDs")
    entities = {}
    for identifier in ENTITY_IDS[family]:
        if identifier not in classes or classes[identifier].get("abstract", False):
            raise ValueError(f"Invalid profile entity: {identifier}")
        entities[identifier] = {"declaration": deepcopy(classes[identifier]), **_policy(family, identifier)}
    targets = {}
    for identifier, name in RELATIONS[family]:
        if identifier not in relations or relations[identifier]["name"] != name:
            raise ValueError(f"Profile relation ID/name mismatch: {identifier}/{name}")
        targets[identifier] = {"declaration": deepcopy(relations[identifier]), **_policy(family, identifier)}
    return {"artifactFamily": family, "contractID": CONTRACT_ID, "ontologyVersion": "0.1.6",
            "ontologySpecSha256": ONTOLOGY_SHA256, "implementationProjectionOnly": True,
            "ownerClassID": OWNERS[family], "ownerPolicy": "Reuse accepted artifact endpoint; never remint owner",
            "entities": entities, "relations": targets,
            "inactive": {"A-D13": "DataService", "C-D29": "servesDataset"},
            "pipelineDerived": {"D-26": "mentions"}, "superclassAndSuperpropertyAssertions": "pipeline_governed_not_model_authored",
            "abstractPredictions": "forbidden", "identityPolicy": "source_local_except_exact_endpoints_and_approved_purpose_vocabulary",
            "evidencePolicy": "Independent sufficient literal node/edge support; co-occurrence/URLs do not prove stronger roles; no evidence repair",
            "semanticAcceptance": False, "kgAuthorization": False}


def check_target(
    family: str, identifier: str, *, model_authored: bool = True,
    relation_name: str | None = None, source_class_id: str | None = None,
    target_class_id: str | None = None, gates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Check declared scope, signatures and explicit caller-attested gate flags.

    Endpoint classes are inventory IDs. Union signatures and declared parent
    chains are read from ontology YAML. Gates must be literal True; this function
    does not verify their semantic truth, evidence, identity or acceptance history.
    Endpoint/seed inspection requires model_authored=False. Unsupported IDs remain
    forbidden even when they occur elsewhere in the ontology.
    """
    profile = get_profile(family)
    result: dict[str, Any] = {"structuralScopePass": False, "semanticAcceptance": False,
                              "kgAuthorization": False, "reasons": [], "missingGates": []}
    record = profile["entities"].get(identifier) or profile["relations"].get(identifier)
    if record is None:
        result["reasons"] = ["inactive_target" if identifier in profile["inactive"] else
                             "pipeline_derived_not_model_authorable" if identifier in profile["pipelineDerived"] else "unsupported_target"]
        return result
    if model_authored and not record["modelAuthorable"]:
        result["reasons"].append("not_model_authorable")
    if identifier in profile["relations"]:
        spec = load_ontology()
        classes = {r["id"]: r for r in spec["classes"]}
        by_iri = {r["iri"]: r for r in spec["classes"]}

        def matches(class_id: str | None, signature: Any) -> bool:
            """Match a concrete source-profile endpoint against ontology unions."""
            if class_id not in classes or class_id not in {*profile["entities"], profile["ownerClassID"]}:
                return False
            declaration = classes[class_id]
            if declaration.get("abstract", False):
                return False
            names = signature if isinstance(signature, list) else [signature]
            seen = set()
            while declaration["id"] not in seen:
                seen.add(declaration["id"])
                if declaration["name"] in names:
                    return True
                parent = declaration.get("parent")
                if parent not in by_iri:
                    return False
                declaration = by_iri[parent]
            raise ValueError("Cyclic ontology parent chain")

        declaration = record["declaration"]
        if relation_name != declaration["name"]:
            result["reasons"].append("relation_name_mismatch")
        if not matches(source_class_id, declaration["domain"]) or not matches(target_class_id, declaration["range"]):
            result["reasons"].append("endpoint_signature_or_scope_mismatch")
    elif relation_name is not None or source_class_id is not None or target_class_id is not None:
        result["reasons"].append("relation_arguments_on_entity")
    if gates is not None and not isinstance(gates, Mapping):
        result["reasons"].append("gate_input_malformed")
        gates = {}
    result["missingGates"] = [g for g in record["requiredGates"] if (gates or {}).get(g) is not True]
    result["structuralScopePass"] = not result["reasons"] and not result["missingGates"]
    return result
