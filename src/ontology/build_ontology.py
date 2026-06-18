"""Generate the CIROH ontology TBox from ``ontology_spec.yaml``.

This script is intentionally a small, deterministic translator from the
machine-readable ontology specification to OWL. It does not run a reasoner,
download ontology imports, or make schema decisions beyond the translation rules
documented in the project AGENTS.md and the specification itself.

Inputs:
    ontology_spec.yaml

Outputs:
    ciroh_ontology.owl
"""

from __future__ import annotations

import types
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from owlready2 import (
    AnnotationProperty,
    DatatypeProperty,
    ObjectProperty,
    Or,
    Thing,
    World,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC_PATH = SCRIPT_DIR / "ontology_spec.yaml"
OUTPUT_PATH = SCRIPT_DIR / "ciroh_ontology.owl"
CIROH_BASE_IRI = "https://w3id.org/ciroh/ontology#"

# These CURIEs denote properties in their source vocabularies. When they appear
# as class anchors, they are recorded as alignment annotations, never as
# rdfs:subClassOf targets.
PROPERTY_ANCHOR_CURIES = {
    "dcterms:temporal",
    "schema:codeRepository",
    "schema:softwareVersion",
    "schema:url",
    "schema:variableMeasured",
}

LITERAL_RANGE_CURIES = {
    "schema:url",
}

XSD_TYPE_MAP = {
    "boolean": bool,
    "bool": bool,
    "integer": int,
    "int": int,
    "float": float,
    "number": float,
    "string": str,
}

OWLREADY_RESERVED_NAMES = {
    "comment",
    "domain",
    "iri",
    "is_a",
    "label",
    "name",
    "range",
}


def load_spec(path: Path) -> dict[str, Any]:
    """Load the YAML ontology specification."""
    with path.open("r", encoding="utf-8") as stream:
        loaded = yaml.safe_load(stream)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected a mapping at the root of {path}")
    return loaded


def as_list(value: Any) -> list[Any]:
    """Return ``value`` as a list while preserving existing lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def split_curie(curie: str) -> tuple[str, str]:
    """Split a CURIE into prefix and local name."""
    if ":" not in curie:
        raise ValueError(f"Expected CURIE, got {curie!r}")
    prefix, local_name = curie.split(":", 1)
    if not prefix or not local_name:
        raise ValueError(f"Invalid CURIE: {curie!r}")
    return prefix, local_name


def is_curie(value: Any) -> bool:
    """Return whether ``value`` looks like a CURIE string."""
    return isinstance(value, str) and ":" in value


def local_name_from_iri(value: str) -> str:
    """Extract the final local name from an absolute IRI."""
    if "#" in value:
        return value.rsplit("#", 1)[1]
    return value.rstrip("/").rsplit("/", 1)[-1]


def sanitize_local_name(value: str) -> str:
    """Return a Python-compatible local name for dynamic owlready2 classes."""
    cleaned = value.replace("-", "_").replace(".", "_").replace("/", "_")
    if not cleaned:
        raise ValueError("Cannot create an OWL entity with an empty local name")
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def is_ciroh_curie(value: Any) -> bool:
    """Return whether ``value`` is a CIROH CURIE."""
    return isinstance(value, str) and value.startswith("ciroh:")


def resolve_curie(curie: str, prefixes: dict[str, str]) -> str:
    """Resolve a CURIE to an absolute IRI."""
    prefix, local_name = split_curie(curie)
    if prefix == "owl" and local_name == "Thing":
        return "http://www.w3.org/2002/07/owl#Thing"
    if prefix not in prefixes:
        raise KeyError(f"Unknown prefix {prefix!r} in CURIE {curie!r}")
    return f"{prefixes[prefix]}{local_name}"


def resolve_iri(value: str, prefixes: dict[str, str]) -> str:
    """Resolve a CURIE or pass through an absolute IRI."""
    if value == "owl:Thing":
        return "http://www.w3.org/2002/07/owl#Thing"
    if is_curie(value) and not value.startswith(("http://", "https://")):
        return resolve_curie(value, prefixes)
    return value


def create_entity(
    ontology: Any,
    iri: str,
    base_class: type,
    prefixes: dict[str, str],
) -> Any:
    """Create or retrieve an OWL entity with the requested IRI."""
    if iri == "http://www.w3.org/2002/07/owl#Thing":
        return Thing

    existing = ontology.world[iri]
    if existing is not None:
        return existing

    namespace_iri = None
    local_name = None
    for base_iri in sorted(prefixes.values(), key=len, reverse=True):
        if iri.startswith(base_iri):
            namespace_iri = base_iri
            local_name = iri[len(base_iri) :]
            break

    if namespace_iri is None or local_name is None:
        if "#" in iri:
            namespace_iri = iri.rsplit("#", 1)[0] + "#"
        else:
            namespace_iri = iri.rstrip("/").rsplit("/", 1)[0] + "/"
        local_name = local_name_from_iri(iri)

    namespace = ontology.get_namespace(namespace_iri)
    python_name = sanitize_local_name(local_name)
    if python_name in OWLREADY_RESERVED_NAMES:
        python_name = f"{python_name}_property"
    with namespace:
        entity = types.new_class(python_name, (base_class,))
    entity.iri = iri
    return entity


def append_unique(target: list[Any], value: Any) -> None:
    """Append ``value`` to ``target`` only if it is not already present."""
    if value not in target:
        target.append(value)


def append_annotation(entity: Any, annotation_property: Any, value: Any) -> None:
    """Append an annotation value if it is not already present."""
    append_unique(annotation_property[entity], value)


def append_comment(entity: Any, comment: str) -> None:
    """Append an rdfs:comment value if it is not already present."""
    append_unique(entity.comment, comment)


def configure_imports(ontology: Any, spec: dict[str, Any]) -> dict[str, str]:
    """Configure owl:imports and return the prefix-to-IRI map."""
    prefixes: dict[str, str] = {}
    for entry in spec.get("prefixes", []):
        prefix = entry["prefix"]
        iri = entry["iri"]
        prefixes[prefix] = iri
        if entry.get("use") == "import":
            import_iri = entry.get("import_iri", iri)
            imported = ontology.world.get_ontology(import_iri)
            append_unique(ontology.imported_ontologies, imported)
    return prefixes


def declare_annotations(ontology: Any) -> dict[str, Any]:
    """Declare CIROH annotation properties used for traceability."""
    with ontology:
        class inventoryId(AnnotationProperty):
            pass

        class reuseAnchor(AnnotationProperty):
            pass

        class alignmentProperty(AnnotationProperty):
            pass

        class allowedValue(AnnotationProperty):
            pass

        class sourceStatus(AnnotationProperty):
            pass

        class sourceKind(AnnotationProperty):
            pass

        class isAbstract(AnnotationProperty):
            pass

    return {
        "inventory_id": inventoryId,
        "reuse_anchor": reuseAnchor,
        "alignment_property": alignmentProperty,
        "allowed_value": allowedValue,
        "source_status": sourceStatus,
        "source_kind": sourceKind,
        "is_abstract": isAbstract,
    }


def should_mint_ciroh_class(class_spec: dict[str, Any]) -> bool:
    """Return whether a spec class should be minted under the CIROH namespace."""
    iri = class_spec["iri"]
    anchor = class_spec.get("anchor") or {}
    anchor_curie = anchor.get("curie")

    if is_ciroh_curie(iri):
        return True
    if iri == "schema:variableMeasured":
        return True
    if anchor_curie in PROPERTY_ANCHOR_CURIES:
        return True
    return anchor.get("relation") != "useDirectly"


def class_iri_for_spec(class_spec: dict[str, Any], prefixes: dict[str, str]) -> str:
    """Return the OWL class IRI to use for a class specification entry."""
    if should_mint_ciroh_class(class_spec):
        return f"{CIROH_BASE_IRI}{class_spec['name']}"
    return resolve_iri(class_spec["iri"], prefixes)


def get_class_reference(
    token: str,
    class_by_name: dict[str, Any],
    prefixes: dict[str, str],
    ontology: Any,
) -> Any:
    """Resolve a class name or CURIE to an owlready2 class object."""
    if token == "owl:Thing":
        return Thing
    if token in class_by_name:
        return class_by_name[token]
    if is_curie(token):
        iri = resolve_iri(token, prefixes)
        return create_entity(ontology, iri, Thing, prefixes)
    raise KeyError(f"Unknown class reference {token!r}")


def make_union_or_single(classes: list[Any]) -> Any:
    """Return a single class or an OWL union class expression."""
    unique_classes: list[Any] = []
    for cls in classes:
        append_unique(unique_classes, cls)
    if not unique_classes:
        return Thing
    if len(unique_classes) == 1:
        return unique_classes[0]
    return Or(unique_classes)


def annotate_common_fields(
    entity: Any,
    entry: dict[str, Any],
    annotations: dict[str, Any],
) -> None:
    """Attach common inventory, status, kind, and note annotations."""
    if entry.get("id"):
        append_annotation(entity, annotations["inventory_id"], entry["id"])
        append_comment(entity, f"Inventory ID: {entry['id']}")
    if entry.get("status"):
        append_annotation(entity, annotations["source_status"], entry["status"])
    if entry.get("kind"):
        append_annotation(entity, annotations["source_kind"], entry["kind"])
    if entry.get("note"):
        append_comment(entity, f"Spec note: {entry['note']}")
    if entry.get("status_note"):
        append_comment(entity, f"Status note: {entry['status_note']}")


def declare_classes(
    ontology: Any,
    spec: dict[str, Any],
    prefixes: dict[str, str],
    annotations: dict[str, Any],
) -> dict[str, Any]:
    """Declare all class entries and return a mapping from spec name to class."""
    class_by_name: dict[str, Any] = {}

    for class_spec in spec.get("classes", []):
        class_iri = class_iri_for_spec(class_spec, prefixes)
        cls = create_entity(ontology, class_iri, Thing, prefixes)
        class_by_name[class_spec["name"]] = cls
        annotate_common_fields(cls, class_spec, annotations)

        if class_spec.get("abstract") is True:
            append_annotation(cls, annotations["is_abstract"], True)
            append_comment(cls, "Abstract class in the CIROH ontology profile.")

        original_iri = class_spec["iri"]
        if resolve_iri(original_iri, prefixes) != class_iri:
            append_comment(cls, f"Spec IRI translated to {class_iri}; original IRI: {original_iri}")
        if original_iri in PROPERTY_ANCHOR_CURIES:
            append_annotation(cls, annotations["alignment_property"], original_iri)
            append_comment(
                cls,
                f"Original property IRI recorded as alignment annotation, not class IRI: {original_iri}",
            )

        anchor = class_spec.get("anchor") or {}
        anchor_curie = anchor.get("curie")
        if anchor_curie:
            append_annotation(cls, annotations["reuse_anchor"], anchor_curie)
            if anchor_curie in PROPERTY_ANCHOR_CURIES:
                append_annotation(cls, annotations["alignment_property"], anchor_curie)
                append_comment(
                    cls,
                    f"Property anchor recorded as alignment annotation, not subclass axiom: {anchor_curie}",
                )

    for class_spec in spec.get("classes", []):
        cls = class_by_name[class_spec["name"]]
        if not should_mint_ciroh_class(class_spec):
            continue

        parent = class_spec.get("parent")
        if parent:
            parent_cls = get_class_reference(parent, class_by_name, prefixes, ontology)
            append_unique(cls.is_a, parent_cls)

        anchor = class_spec.get("anchor") or {}
        anchor_curie = anchor.get("curie")
        if anchor.get("relation") == "subClassOf" and anchor_curie:
            if anchor_curie in PROPERTY_ANCHOR_CURIES:
                continue
            anchor_cls = get_class_reference(anchor_curie, class_by_name, prefixes, ontology)
            append_unique(cls.is_a, anchor_cls)

    return class_by_name


def attribute_python_type(attribute: dict[str, Any]) -> type:
    """Return the Python datatype for a class attribute specification."""
    if attribute.get("values"):
        return str
    declared_type = str(attribute.get("type", "string"))
    return XSD_TYPE_MAP.get(declared_type, str)


def declare_attribute_properties(
    ontology: Any,
    spec: dict[str, Any],
    class_by_name: dict[str, Any],
    prefixes: dict[str, str],
    annotations: dict[str, Any],
) -> dict[str, Any]:
    """Declare data properties for all class attributes."""
    attributes_by_name: dict[str, list[tuple[dict[str, Any], Any]]] = defaultdict(list)
    for class_spec in spec.get("classes", []):
        cls = class_by_name[class_spec["name"]]
        for attribute in class_spec.get("attributes", []):
            attributes_by_name[attribute["name"]].append((attribute, cls))

    properties: dict[str, Any] = {}
    for attribute_name in sorted(attributes_by_name):
        prop_iri = f"{CIROH_BASE_IRI}{attribute_name}"
        prop = create_entity(ontology, prop_iri, DatatypeProperty, prefixes)
        properties[attribute_name] = prop

        domains = [cls for _, cls in attributes_by_name[attribute_name]]
        prop.domain = [make_union_or_single(domains)]

        first_attribute = attributes_by_name[attribute_name][0][0]
        prop.range = [attribute_python_type(first_attribute)]
        append_comment(prop, "Data property generated from class attributes in ontology_spec.yaml.")

        for attribute, cls in attributes_by_name[attribute_name]:
            append_comment(prop, f"Attribute on {cls.name}.")
            if attribute.get("anchor"):
                append_annotation(prop, annotations["reuse_anchor"], attribute["anchor"])
                append_comment(prop, f"Reuse anchor: {attribute['anchor']}")
            if attribute.get("evidence"):
                append_comment(prop, f"Evidence locus: {attribute['evidence']}")
            if attribute.get("note"):
                append_comment(prop, f"Attribute note: {attribute['note']}")
            for value in attribute.get("values", []):
                append_annotation(prop, annotations["allowed_value"], str(value))
                append_comment(prop, f"Allowed value: {value}")

    return properties


def is_literal_range(range_value: Any) -> bool:
    """Return whether a relation range denotes a literal datatype target."""
    ranges = as_list(range_value)
    return any(isinstance(item, str) and item in LITERAL_RANGE_CURIES for item in ranges)


def relation_groups(spec: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group relation entries by their conceptual property name."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relation in spec.get("relations", []):
        grouped[relation["name"]].append(relation)
    return dict(sorted(grouped.items()))


def relation_domains(
    relations: list[dict[str, Any]],
    class_by_name: dict[str, Any],
    prefixes: dict[str, str],
    ontology: Any,
) -> list[Any]:
    """Resolve and merge all domain classes for a relation group."""
    domains: list[Any] = []
    for relation in relations:
        for domain in as_list(relation.get("domain", "owl:Thing")):
            cls = get_class_reference(str(domain), class_by_name, prefixes, ontology)
            append_unique(domains, cls)
    return domains


def relation_ranges(
    relations: list[dict[str, Any]],
    class_by_name: dict[str, Any],
    prefixes: dict[str, str],
    ontology: Any,
) -> list[Any]:
    """Resolve and merge all object-property range classes for a relation group."""
    ranges: list[Any] = []
    for relation in relations:
        for range_value in as_list(relation.get("range", "owl:Thing")):
            if isinstance(range_value, str) and range_value in LITERAL_RANGE_CURIES:
                continue
            cls = get_class_reference(str(range_value), class_by_name, prefixes, ontology)
            append_unique(ranges, cls)
    return ranges


def annotate_relation_group(
    prop: Any,
    relations: list[dict[str, Any]],
    annotations: dict[str, Any],
) -> None:
    """Attach inventory and reuse annotations for a merged relation property."""
    for relation in relations:
        annotate_common_fields(prop, relation, annotations)
        if relation.get("anchor"):
            append_annotation(prop, annotations["reuse_anchor"], relation["anchor"])
            append_comment(prop, f"Reuse anchor: {relation['anchor']}")
        if relation.get("alignment"):
            append_annotation(prop, annotations["alignment_property"], relation["alignment"])
            append_comment(prop, f"Informative alignment: {relation['alignment']}")
        if relation.get("same_as"):
            append_comment(prop, f"Same as inventory relation: {relation['same_as']}")
        if relation.get("maps_to"):
            append_comment(prop, f"Maps to inventory relation: {relation['maps_to']}")
        if relation.get("evidence"):
            append_comment(prop, f"Evidence locus: {relation['evidence']}")
        if relation.get("typed_subproperties"):
            for subproperty in relation["typed_subproperties"]:
                append_comment(prop, f"Typed subproperty reference: {subproperty}")
        if relation.get("inverse_of"):
            append_comment(prop, f"Inverse property: {relation['inverse_of']}")
        if relation.get("subproperty_of"):
            append_comment(prop, f"Subproperty of: {relation['subproperty_of']}")


def apply_cardinality_axioms(
    prop: Any,
    relations: list[dict[str, Any]],
    domains: list[Any],
    ranges: list[Any],
) -> None:
    """Apply relation cardinality restrictions where the specification requests them."""
    if prop.name == "hasEvidence":
        return

    for relation in relations:
        cardinality = relation.get("cardinality")
        if cardinality != "min 1":
            continue
        range_expr = make_union_or_single(ranges) if ranges else Thing
        restriction = prop.min(1, range_expr)
        for domain_cls in domains or [Thing]:
            append_unique(domain_cls.is_a, restriction)


def declare_relations(
    ontology: Any,
    spec: dict[str, Any],
    class_by_name: dict[str, Any],
    prefixes: dict[str, str],
    annotations: dict[str, Any],
) -> dict[str, Any]:
    """Declare merged object and datatype properties for all relations."""
    properties: dict[str, Any] = {}

    for relation_name, relations in relation_groups(spec).items():
        literal_property = any(is_literal_range(relation.get("range")) for relation in relations)
        prop_base = DatatypeProperty if literal_property else ObjectProperty
        prop = create_entity(ontology, f"{CIROH_BASE_IRI}{relation_name}", prop_base, prefixes)
        properties[relation_name] = prop

        domains = relation_domains(relations, class_by_name, prefixes, ontology)
        prop.domain = [make_union_or_single(domains)]

        if literal_property:
            prop.range = [str]
        else:
            ranges = relation_ranges(relations, class_by_name, prefixes, ontology)
            prop.range = [make_union_or_single(ranges)]
            apply_cardinality_axioms(prop, relations, domains, ranges)

        annotate_relation_group(prop, relations, annotations)
        append_comment(prop, "Merged conceptual relation from ontology_spec.yaml.")

    return properties


def require_object_property(prop: Any, property_name: str) -> None:
    """Raise if ``prop`` is not an OWL object property."""
    if not isinstance(prop, type) or not issubclass(prop, ObjectProperty):
        raise TypeError(f"Relation {property_name!r} must be an ObjectProperty for this axiom")


def apply_relation_hierarchy_axioms(
    spec: dict[str, Any],
    relation_properties: dict[str, Any],
) -> None:
    """Apply optional inverse and subproperty axioms from relation entries."""
    for relation in spec.get("relations", []):
        prop_name = relation["name"]
        prop = relation_properties[prop_name]

        inverse_name = relation.get("inverse_of")
        if inverse_name:
            if inverse_name not in relation_properties:
                raise KeyError(f"Unknown inverse_of relation {inverse_name!r} on {prop_name!r}")
            inverse_prop = relation_properties[inverse_name]
            require_object_property(prop, prop_name)
            require_object_property(inverse_prop, inverse_name)
            if prop.inverse_property not in (None, inverse_prop):
                raise ValueError(
                    f"Relation {prop_name!r} already has inverse {prop.inverse_property.name!r}"
                )
            prop.inverse_property = inverse_prop

        parent_name = relation.get("subproperty_of")
        if parent_name:
            if parent_name not in relation_properties:
                raise KeyError(f"Unknown subproperty_of relation {parent_name!r} on {prop_name!r}")
            parent_prop = relation_properties[parent_name]
            require_object_property(prop, prop_name)
            require_object_property(parent_prop, parent_name)
            append_unique(prop.is_a, parent_prop)


def declare_global_data_property(
    ontology: Any,
    name: str,
    domain: Any,
    values: list[Any],
    prefixes: dict[str, str],
    annotations: dict[str, Any],
) -> Any:
    """Declare a global CIROH data property with optional controlled values."""
    prop = create_entity(ontology, f"{CIROH_BASE_IRI}{name}", DatatypeProperty, prefixes)
    prop.domain = [domain]
    prop.range = [str]
    append_comment(prop, "Global data property from ontology_spec.yaml.")
    for value in values:
        append_annotation(prop, annotations["allowed_value"], str(value))
        append_comment(prop, f"Allowed value: {value}")
    return prop


def apply_global_constraints(
    ontology: Any,
    spec: dict[str, Any],
    class_by_name: dict[str, Any],
    relation_properties: dict[str, Any],
    prefixes: dict[str, str],
    annotations: dict[str, Any],
) -> None:
    """Apply global evidence and discourse-unit constraints from the spec."""
    evidence_prop = relation_properties.get("hasEvidence")
    evidence_cls = class_by_name.get("EvidenceSpan")
    if evidence_prop is not None and evidence_cls is not None:
        scoped_kinds = {"artifact", "domain", "discourse", "instructional", "metadata", "agent"}
        target_classes = [
            class_by_name[class_spec["name"]]
            for class_spec in spec.get("classes", [])
            if class_spec.get("kind") in scoped_kinds
            and class_spec["name"] != "EvidenceSpan"
            and should_mint_ciroh_class(class_spec)
        ]
        restriction = evidence_prop.min(1, evidence_cls)
        for target_cls in target_classes:
            append_unique(target_cls.is_a, restriction)
        append_comment(
            evidence_prop,
            "Global constraint: each minted CIROH KG node class must have at least one EvidenceSpan.",
        )
        for prop in relation_properties.values():
            append_comment(
                prop,
                "Global evidence policy: asserted edges require evidence in extracted KG data.",
            )

    discourse_classes = [
        cls
        for class_spec in spec.get("classes", [])
        if class_spec.get("kind") == "discourse"
        for cls in [class_by_name[class_spec["name"]]]
    ]
    discourse_domain = make_union_or_single(discourse_classes) if discourse_classes else Thing

    for constraint in spec.get("global_constraints", []):
        prop_name = constraint.get("property")
        if prop_name == "curationStatus":
            declare_global_data_property(
                ontology,
                prop_name,
                Thing,
                constraint.get("values", []),
                prefixes,
                annotations,
            )
        elif prop_name in {"tendency", "source"}:
            declare_global_data_property(
                ontology,
                prop_name,
                discourse_domain,
                constraint.get("values", []),
                prefixes,
                annotations,
            )


def annotate_ontology_metadata(ontology: Any, spec: dict[str, Any]) -> None:
    """Attach title, version, and generator comments to the ontology."""
    metadata = spec.get("ontology", {})
    if metadata.get("title"):
        append_unique(ontology.metadata.comment, metadata["title"])
    if metadata.get("version"):
        append_unique(ontology.metadata.versionInfo, str(metadata["version"]))
    append_unique(
        ontology.metadata.comment,
        "Generated from src/ontology/ontology_spec.yaml by build_ontology.py.",
    )


def build_ontology(spec_path: Path = SPEC_PATH, output_path: Path = OUTPUT_PATH) -> Path:
    """Build and save the CIROH OWL TBox from the YAML specification."""
    spec = load_spec(spec_path)
    world = World()
    ontology = world.get_ontology(spec["ontology"]["iri"])
    prefixes = configure_imports(ontology, spec)

    with ontology:
        annotations = declare_annotations(ontology)
        class_by_name = declare_classes(ontology, spec, prefixes, annotations)
        attribute_properties = declare_attribute_properties(
            ontology,
            spec,
            class_by_name,
            prefixes,
            annotations,
        )
        relation_properties = declare_relations(
            ontology,
            spec,
            class_by_name,
            prefixes,
            annotations,
        )
        apply_relation_hierarchy_axioms(spec, relation_properties)
        apply_global_constraints(
            ontology,
            spec,
            class_by_name,
            relation_properties,
            prefixes,
            annotations,
        )
        annotate_ontology_metadata(ontology, spec)

    ontology.save(file=str(output_path), format="rdfxml")
    minted_ciroh_classes = {
        class_by_name[class_spec["name"]]
        for class_spec in spec.get("classes", [])
        if should_mint_ciroh_class(class_spec)
        and class_by_name[class_spec["name"]].iri.startswith(CIROH_BASE_IRI)
    }
    referenced_external_classes = {
        class_by_name[class_spec["name"]]
        for class_spec in spec.get("classes", [])
        if not class_by_name[class_spec["name"]].iri.startswith(CIROH_BASE_IRI)
    }
    object_properties = {
        prop
        for prop in relation_properties.values()
        if isinstance(prop, type) and issubclass(prop, ObjectProperty)
    }
    datatype_properties = {
        prop
        for prop in relation_properties.values()
        if isinstance(prop, type) and issubclass(prop, DatatypeProperty)
    }
    datatype_properties.update(attribute_properties.values())
    datatype_properties.update(
        prop
        for prop in ontology.data_properties()
        if prop.iri.startswith(CIROH_BASE_IRI)
    )

    print("Ontology build summary:")
    print(f"  Minted CIROH classes: {len(minted_ciroh_classes)}")
    print(f"  Referenced external classes: {len(referenced_external_classes)}")
    print(f"  Object properties: {len(object_properties)}")
    print(f"  Datatype properties: {len(datatype_properties)}")
    print(f"  owl:imports: {len(ontology.imported_ontologies)}")
    print(
        "  Relation check: isMemberOf and isPartOf separate properties: "
        f"{relation_properties['isMemberOf'] is not relation_properties['isPartOf']}"
    )
    return output_path


def main() -> None:
    """Run the ontology build from the command line."""
    output_path = build_ontology()
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
