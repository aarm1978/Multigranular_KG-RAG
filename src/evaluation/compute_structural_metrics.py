"""Compute schema-agnostic structural metrics for an interim KG snapshot.

The input must use the project's source-agnostic interim format: top-level
``nodes`` and ``edges`` arrays, node records with ``id``, ``class``, and
``attributes``, and edge records with ``source``, ``target``, and ``relation``.

For each labeled snapshot, this script:

1. validates the graph structure;
2. computes information density, its attribute and edge components, relational
   richness, and mention-level or post-consolidation ratios;
3. writes a deterministic trajectory or module-diagnostic JSON record; and
4. rebuilds the human-readable trajectory table only for trajectory records.

The administrative/identifier exclusion set is a public constant so the exact
same counting policy can later be reused for Microsoft GraphRAG snapshots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results/metrics"
SNAPSHOT_SCHEMA_VERSION = "1.2"
EVALUATOR_VERSION = "1.2.0"
METRIC_DECIMAL_PLACES = 6

FILE_INVENTORY_CLASSES = frozenset({"DatasetFile", "File", "RepoFile"})
FILE_INVENTORY_CLASS_INVENTORY_IDS = {
    "DatasetFile": "A-D03",
    "File": "A-C02",
    "RepoFile": "A-C02",
}
FILE_INVENTORY_EDGE_EXCLUSION_RULE = "incident_to_excluded_node"
FILE_INVENTORY_SENSITIVITY_RATIONALE = (
    "File-inventory entities are legitimate KG content and remain in the full graph. "
    "This sensitivity analysis excludes the complete class-defined file-inventory "
    "layer and every edge incident to an excluded node so per-node structural averages "
    "can be interpreted independently of explicit repository and dataset file granularity."
)

# These fields identify, administer, locate, or provenance-track entities rather
# than describe their semantic content. Keep this set fixed across the
# multi-granular KG and GraphRAG comparison unless the evaluation contract is
# explicitly revised. Exact keys are recorded in every snapshot JSON.
GLOBAL_ADMINISTRATIVE_ATTRIBUTE_KEYS = frozenset(
    {
        # Internal graph and source identifiers.
        "id",
        "internalId",
        "nodeId",
        "edgeId",
        "resourceId",
        "hydroshareResourceId",
        "hydroshareUserId",
        "inventoryId",
        "repoId",
        "githubId",
        "paperId",
        "toolId",
        "moduleRoleId",
        "sourceRepoId",
        "fullName",
        "login",
        "email",
        "canonicalName",
        "identityRegime",
        # External identifiers and identity bookkeeping.
        "identifier",
        "identifiers",
        "identifierValue",
        "identifierType",
        "identifierRegime",
        "normalizedValue",
        "doi",
        "orcid",
        "ror",
        "spdxId",
        # Storage and integrity details.
        "checksum",
        "filePath",
        "path",
        "fileName",
        "sizeBytes",
        "bagUrl",
        "downloadUrl",
        # URLs used primarily as identifiers or operational endpoints.
        "url",
        "htmlUrl",
        "profileUrl",
        "homepage",
        "urls",
        "host",
        "launchURL",
        "fundingAgencyUrl",
        "requestUrlBase",
        "requestUrlBaseFile",
        "toolIconUrl",
        # Provenance and pipeline administration.
        "sourceArtifact",
        "sourceLocation",
        "extractionMethod",
        "sourcePath",
        "sourceType",
        "sourceDeclarations",
        "manifestType",
        "originalValue",
        "metricExclusion",
        "rawSource",
        "phaseAField",
        "phaseAVersion",
        "curationStatus",
        "mentionCount",
        # Acquisition and inventory administration.
        "downloaded",
        "contentAvailable",
        "selectionReason",
        "downloadedFileCount",
        "fileTotalCount",
        "selectionReasonHistogram",
        "githubStats",
        "archiveFormat",
        "declaredLicenseMetadata",
        "contributions",
        "contributorType",
        # Administrative timestamps. Domain dates such as start/end remain.
        "createdAt",
        "updatedAt",
        "modifiedAt",
        "timestamp",
        "pushedAt",
    }
)

CLASS_SPECIFIC_ADMINISTRATIVE_ATTRIBUTE_KEYS: dict[str, frozenset[str]] = {
    "ExecutionEnvironment": frozenset({"prefix", "pinnedCount", "pinnedSetEvidence"}),
    "Identifier": frozenset({"idType", "value"}),
    "License": frozenset({"key", "declarationScope", "declarationKind"}),
    "Repository": frozenset({"owner", "forkParent"}),
    "Tool": frozenset(
        {
            "cffVersion",
            "declaredLicenseKind",
            "declaredLicenseSourceValue",
            "repository",
            "repositoryCode",
        }
    ),
}

EXTERNAL_URL_STUB_NOTE = (
    "Because url and host are excluded as identifier/administrative fields, "
    "external-URL stub nodes may have near-zero informative-attribute density. "
    "This is intentional and honest: unresolved stubs are information-poor, "
    "while their incident relations still contribute to structural density."
)

JsonDict = dict[str, Any]


def load_snapshot(path: Path) -> JsonDict:
    """Load a nodes/edges snapshot from JSON."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object at {path}, found {type(data).__name__}")
    return data


def validate_snapshot(data: JsonDict) -> None:
    """Validate required graph fields and endpoint integrity."""
    nodes = data.get("nodes")
    edges = data.get("edges")
    if not isinstance(nodes, list):
        raise ValueError("Snapshot must contain a top-level 'nodes' array")
    if not isinstance(edges, list):
        raise ValueError("Snapshot must contain a top-level 'edges' array")

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"nodes[{index}] must be an object")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError(f"nodes[{index}].id must be a non-empty string")
        if node_id in node_ids:
            raise ValueError(f"Duplicate node ID: {node_id}")
        node_ids.add(node_id)
        class_name = node.get("class")
        if not isinstance(class_name, str) or not class_name:
            raise ValueError(f"nodes[{index}].class must be a non-empty string")
        if class_name in FILE_INVENTORY_CLASSES:
            expected_inventory_id = FILE_INVENTORY_CLASS_INVENTORY_IDS[class_name]
            actual_inventory_id = node.get("inventoryId")
            if actual_inventory_id != expected_inventory_id:
                raise ValueError(
                    f"nodes[{index}] class {class_name!r} must use inventoryId "
                    f"{expected_inventory_id!r}, found {actual_inventory_id!r}"
                )
        attributes = node.get("attributes", {})
        if not isinstance(attributes, dict):
            raise ValueError(f"nodes[{index}].attributes must be an object")

    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"edges[{index}] must be an object")
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not edge_id:
            raise ValueError(f"edges[{index}].id must be a non-empty string")
        if edge_id in edge_ids:
            raise ValueError(f"Duplicate edge ID: {edge_id}")
        edge_ids.add(edge_id)
        relation = edge.get("relation")
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(relation, str) or not relation:
            raise ValueError(f"edges[{index}].relation must be a non-empty string")
        if source not in node_ids:
            raise ValueError(f"edges[{index}].source does not resolve to a node: {source!r}")
        if target not in node_ids:
            raise ValueError(f"edges[{index}].target does not resolve to a node: {target!r}")


def is_nonempty(value: Any) -> bool:
    """Return whether an attribute value contains countable information."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def attribute_exclusion_rule(class_name: str, attribute_key: str) -> str | None:
    """Return the fixed exclusion rule for a class/key pair, if any."""
    if attribute_key in GLOBAL_ADMINISTRATIVE_ATTRIBUTE_KEYS:
        return "global_administrative_or_identifier"
    if attribute_key in CLASS_SPECIFIC_ADMINISTRATIVE_ATTRIBUTE_KEYS.get(
        class_name, frozenset()
    ):
        return "class_specific_administrative"
    return None


def count_informative_attributes(class_name: str, attributes: JsonDict) -> int:
    """Count nonempty attribute keys allowed by global and contextual policy."""
    return sum(
        1
        for key, value in attributes.items()
        if attribute_exclusion_rule(class_name, key) is None and is_nonempty(value)
    )


def build_attribute_accounting(nodes: list[JsonDict]) -> JsonDict:
    """Audit every observed class/attribute key under the fixed counting policy."""
    observed: dict[str, Counter[str]] = defaultdict(Counter)
    observed_keys: dict[str, set[str]] = defaultdict(set)
    for node in nodes:
        class_name = str(node["class"])
        for key, value in node.get("attributes", {}).items():
            observed_keys[class_name].add(key)
            if is_nonempty(value):
                observed[class_name][key] += 1

    counted: JsonDict = {}
    excluded: JsonDict = {}
    for class_name in sorted(observed_keys):
        for key in sorted(observed_keys[class_name]):
            count = observed[class_name][key]
            rule = attribute_exclusion_rule(class_name, key)
            if rule is None:
                counted.setdefault(class_name, {})[key] = count
            else:
                excluded.setdefault(class_name, {})[key] = {
                    "count": count,
                    "rule": rule,
                }
    return {"counted": counted, "excluded": excluded}


def build_incident_indexes(
    node_ids: Iterable[str],
    edges: list[JsonDict],
) -> tuple[Counter[str], dict[str, set[str]]]:
    """Build incident-edge counts and distinct incident-relation sets per node.

    A self-loop contributes one incident edge and one relation type to its node.
    """
    incident_edge_counts: Counter[str] = Counter({node_id: 0 for node_id in node_ids})
    incident_relation_types: dict[str, set[str]] = {
        node_id: set() for node_id in node_ids
    }

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        relation = edge["relation"]
        incident_edge_counts[source] += 1
        incident_relation_types[source].add(relation)
        if target != source:
            incident_edge_counts[target] += 1
            incident_relation_types[target].add(relation)

    return incident_edge_counts, incident_relation_types


def round_metric(value: float) -> float:
    """Round a reported metric consistently."""
    return round(value, METRIC_DECIMAL_PLACES)


def safe_average(total: int | float, count: int) -> float:
    """Return a rounded average, using zero for an empty graph."""
    return round_metric(float(total) / count) if count else 0.0


def compute_structural_metrics(data: JsonDict) -> JsonDict:
    """Compute global and per-class density and relational richness."""
    nodes: list[JsonDict] = data["nodes"]
    edges: list[JsonDict] = data["edges"]
    node_ids = [node["id"] for node in nodes]
    incident_counts, incident_types = build_incident_indexes(node_ids, edges)

    attribute_counts = {
        node["id"]: count_informative_attributes(
            str(node["class"]), node.get("attributes", {})
        )
        for node in nodes
    }
    total_attributes = sum(attribute_counts.values())
    total_incident_edges = sum(incident_counts.values())
    total_distinct_relation_types = sum(
        len(incident_types[node_id]) for node_id in node_ids
    )
    node_count = len(nodes)

    average_attributes = safe_average(total_attributes, node_count)
    average_incident_edges = safe_average(total_incident_edges, node_count)

    by_class_nodes: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        by_class_nodes[str(node["class"])].append(str(node["id"]))
    by_entity_type: JsonDict = {}
    for class_name in sorted(by_class_nodes):
        class_node_ids = by_class_nodes[class_name]
        class_node_count = len(class_node_ids)
        class_attributes = sum(attribute_counts[node_id] for node_id in class_node_ids)
        class_incident_edges = sum(incident_counts[node_id] for node_id in class_node_ids)
        class_distinct_relations = sum(
            len(incident_types[node_id]) for node_id in class_node_ids
        )
        class_average_attributes = safe_average(class_attributes, class_node_count)
        class_average_edges = safe_average(class_incident_edges, class_node_count)
        by_entity_type[class_name] = {
            "nodeCount": class_node_count,
            "informationDensity": {
                "combinedAveragePerNode": safe_average(
                    class_attributes + class_incident_edges,
                    class_node_count,
                ),
                "averageInformativeAttributesPerNode": class_average_attributes,
                "averageIncidentEdgesPerNode": class_average_edges,
                "totalInformativeAttributes": class_attributes,
                "totalIncidentEdgeOccurrences": class_incident_edges,
            },
            "relationalRichness": {
                "averageDistinctRelationTypesPerNode": safe_average(
                    class_distinct_relations, class_node_count
                ),
                "totalPerNodeDistinctRelationTypes": class_distinct_relations,
            },
        }

    return {
        "informationDensity": {
            "combinedAveragePerNode": safe_average(
                total_attributes + total_incident_edges, node_count
            ),
            "averageInformativeAttributesPerNode": average_attributes,
            "averageIncidentEdgesPerNode": average_incident_edges,
            "totalInformativeAttributes": total_attributes,
            "totalIncidentEdgeOccurrences": total_incident_edges,
        },
        "relationalRichness": {
            "averageDistinctRelationTypesPerNode": safe_average(
                total_distinct_relation_types, node_count
            ),
            "totalPerNodeDistinctRelationTypes": total_distinct_relation_types,
        },
        "byEntityType": by_entity_type,
    }


def get_mention_count(node: JsonDict, attribute_name: str) -> int:
    """Return a positive mention count, defaulting to one per node."""
    attributes = node.get("attributes", {})
    value = attributes.get(attribute_name, 1)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(
            f"Node {node['id']!r} has invalid {attribute_name!r}: {value!r}; "
            "expected a positive integer"
        )
    return value


def make_ratio_record(unique_entities: int, total_mentions: int) -> JsonDict:
    """Create one consolidation-ratio result record."""
    ratio = float(unique_entities) / total_mentions if total_mentions else 0.0
    return {
        "uniqueCanonicalEntities": unique_entities,
        "totalEntityMentions": total_mentions,
        "ratio": round_metric(ratio),
    }


def compute_consolidation_metrics(
    nodes: list[JsonDict],
    mention_count_attribute: str,
    stage: str,
) -> JsonDict:
    """Compute global and per-class consolidation ratios."""
    unique_by_class: Counter[str] = Counter()
    mentions_by_class: Counter[str] = Counter()

    for node in nodes:
        class_name = node["class"]
        unique_by_class[class_name] += 1
        mentions_by_class[class_name] += get_mention_count(
            node, mention_count_attribute
        )

    total_unique = sum(unique_by_class.values())
    total_mentions = sum(mentions_by_class.values())
    per_type = {
        class_name: make_ratio_record(
            unique_by_class[class_name], mentions_by_class[class_name]
        )
        for class_name in sorted(unique_by_class)
    }

    uses_explicit_mentions = any(
        mention_count_attribute in node.get("attributes", {}) for node in nodes
    )
    interpretation = (
        "explicit_mention_counts"
        if uses_explicit_mentions
        else "mention_level_pre_consolidation"
    )

    return {
        "stage": stage,
        "interpretation": interpretation,
        "mentionCountAttribute": mention_count_attribute,
        "global": make_ratio_record(total_unique, total_mentions),
        "perEntityType": per_type,
    }


def sha256_file(path: Path) -> str:
    """Compute a file's SHA-256 digest without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_sorted_ids(values: Iterable[str]) -> str:
    """Hash sorted IDs joined by newlines with one required final newline."""
    serialized = "\n".join(sorted(values)) + "\n"
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def partition_file_inventory(data: JsonDict) -> tuple[JsonDict, JsonDict]:
    """Build the retained sensitivity graph and deterministic exclusion audit."""
    validate_snapshot(data)
    full_nodes: list[JsonDict] = data["nodes"]
    full_edges: list[JsonDict] = data["edges"]
    full_node_ids = {str(node["id"]) for node in full_nodes}
    full_edge_ids = {str(edge["id"]) for edge in full_edges}

    excluded_nodes = [
        node for node in full_nodes if str(node["class"]) in FILE_INVENTORY_CLASSES
    ]
    excluded_node_ids = {str(node["id"]) for node in excluded_nodes}
    retained_nodes = [
        node for node in full_nodes if str(node["id"]) not in excluded_node_ids
    ]
    retained_node_ids = {str(node["id"]) for node in retained_nodes}

    excluded_edges = [
        edge
        for edge in full_edges
        if str(edge["source"]) in excluded_node_ids
        or str(edge["target"]) in excluded_node_ids
    ]
    excluded_edge_ids = {str(edge["id"]) for edge in excluded_edges}
    retained_edges = [
        edge for edge in full_edges if str(edge["id"]) not in excluded_edge_ids
    ]
    retained_edge_ids = {str(edge["id"]) for edge in retained_edges}

    if retained_node_ids & excluded_node_ids:
        raise ValueError("Retained and excluded node sets overlap")
    if retained_node_ids | excluded_node_ids != full_node_ids:
        raise ValueError("Retained and excluded node sets do not reconcile to full nodes")
    if retained_edge_ids & excluded_edge_ids:
        raise ValueError("Retained and excluded edge sets overlap")
    if retained_edge_ids | excluded_edge_ids != full_edge_ids:
        raise ValueError("Retained and excluded edge sets do not reconcile to full edges")
    for edge in retained_edges:
        source = str(edge["source"])
        target = str(edge["target"])
        if source not in retained_node_ids or target not in retained_node_ids:
            raise ValueError(
                f"Retained edge {edge['id']!r} references an excluded or missing node"
            )

    retained_graph: JsonDict = {"nodes": retained_nodes, "edges": retained_edges}
    validate_snapshot(retained_graph)
    excluded_node_counts = Counter(str(node["class"]) for node in excluded_nodes)
    excluded_edge_counts = Counter(str(edge["relation"]) for edge in excluded_edges)
    audit = {
        "excludedClasses": sorted(FILE_INVENTORY_CLASSES),
        "expectedInventoryIdsByClass": dict(
            sorted(FILE_INVENTORY_CLASS_INVENTORY_IDS.items())
        ),
        "edgeExclusionRule": FILE_INVENTORY_EDGE_EXCLUSION_RULE,
        "excludedNodeCount": len(excluded_nodes),
        "excludedNodeCountsByClass": {
            class_name: excluded_node_counts[class_name]
            for class_name in sorted(FILE_INVENTORY_CLASSES)
        },
        "excludedEdgeCount": len(excluded_edges),
        "excludedEdgeCountsByRelation": dict(sorted(excluded_edge_counts.items())),
        "excludedNodeIdsSha256": sha256_sorted_ids(excluded_node_ids),
        "excludedEdgeIdsSha256": sha256_sorted_ids(excluded_edge_ids),
        "rationale": FILE_INVENTORY_SENSITIVITY_RATIONALE,
    }
    return retained_graph, audit


def portable_path(path: Path) -> str:
    """Return a project-relative path when possible, otherwise the given path."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_input_record(data: JsonDict, input_path: Path) -> JsonDict:
    """Record input provenance, including cumulative component provenance when present."""
    input_record: JsonDict = {
        "path": portable_path(input_path),
        "sha256": sha256_file(input_path),
    }
    if "components" in data:
        components = data.get("components")
        if not isinstance(components, list):
            raise ValueError("Cumulative input components must be an array")
        input_record["cumulativeProvenance"] = {
            "cumulativeBuilderSchemaVersion": data.get("snapshot_schema_version"),
            "snapshotType": data.get("snapshot_type"),
            "componentOrderRule": "lexicographic_by_component_label",
            "components": components,
        }
    return input_record


def build_results_record(
    data: JsonDict,
    input_path: Path,
    label: str,
    display_name: str,
    order: int,
    mention_count_attribute: str,
    consolidation_stage: str,
    record_series: str = "trajectory",
) -> JsonDict:
    """Build the complete deterministic snapshot results record."""
    validate_snapshot(data)
    filtered_data, sensitivity_audit = partition_file_inventory(data)
    full_structural = compute_structural_metrics(data)
    full_consolidation = compute_consolidation_metrics(
        data["nodes"], mention_count_attribute, consolidation_stage
    )
    filtered_structural = compute_structural_metrics(filtered_data)
    filtered_consolidation = compute_consolidation_metrics(
        filtered_data["nodes"], mention_count_attribute, consolidation_stage
    )

    full_variant = {
        "counts": {"nodes": len(data["nodes"]), "edges": len(data["edges"])},
        "metrics": {**full_structural, "consolidation": full_consolidation},
        "attributeAccounting": build_attribute_accounting(data["nodes"]),
    }
    filtered_variant = {
        "counts": {
            "nodes": len(filtered_data["nodes"]),
            "edges": len(filtered_data["edges"]),
        },
        "metrics": {**filtered_structural, "consolidation": filtered_consolidation},
        "attributeAccounting": build_attribute_accounting(filtered_data["nodes"]),
    }
    if sensitivity_audit["excludedNodeCount"] == 0:
        if full_variant != filtered_variant:
            raise ValueError(
                "File-inventory sensitivity must be a no-op when no policy class exists"
            )

    return {
        "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
        "evaluatorVersion": EVALUATOR_VERSION,
        "label": label,
        "displayName": display_name,
        "trajectoryOrder": order,
        "recordSeries": record_series,
        "input": build_input_record(data, input_path),
        "evaluationPolicy": {
            "attributeExclusions": {
                "globalAdministrativeOrIdentifier": sorted(
                    GLOBAL_ADMINISTRATIVE_ATTRIBUTE_KEYS
                ),
                "classSpecificAdministrative": {
                    class_name: sorted(keys)
                    for class_name, keys in sorted(
                        CLASS_SPECIFIC_ADMINISTRATIVE_ATTRIBUTE_KEYS.items()
                    )
                },
            },
            "fileInventorySensitivity": sensitivity_audit,
        },
        "variants": {
            "full": full_variant,
            "fileInventoryExcluded": filtered_variant,
        },
        "methodology": {
            "informationDensityDefinition": (
                "Average per node of nonempty informative attribute keys plus "
                "incident edge instances. Incoming and outgoing edges count; "
                "a self-loop counts once for its node."
            ),
            "informativeAttributeDefinition": (
                "Each nonempty node.attributes key not excluded by the global "
                "or class-specific policy counts once, regardless of value length."
            ),
            "relationalRichnessDefinition": (
                "Average per node of distinct incoming or outgoing relation names."
            ),
            "consolidationRatioDefinition": (
                "Unique canonical entity nodes divided by total extracted entity "
                "mentions, globally and per class. Lower values indicate greater "
                "consolidation, but the ratio does not establish consolidation "
                "quality because erroneous over-merging can also reduce it."
            ),
            "externalUrlStubNote": EXTERNAL_URL_STUB_NOTE,
        },
    }


def validate_label(label: str) -> str:
    """Validate that a snapshot label is safe as a filename and stable key."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", label):
        raise ValueError(
            "Label must start with an alphanumeric character and contain only "
            "letters, numbers, '.', '_', or '-'"
        )
    return label


def write_snapshot_record(record: JsonDict, snapshots_dir: Path) -> Path:
    """Write or replace one labeled snapshot JSON deterministically."""
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    output_path = snapshots_dir / f"{record['label']}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    return output_path


def write_results_record(record: JsonDict, results_dir: Path, record_series: str) -> Path:
    """Write a trajectory snapshot or isolated module diagnostic."""
    destination = "snapshots" if record_series == "trajectory" else "modules"
    return write_snapshot_record(record, results_dir / destination)


def load_snapshot_records(snapshots_dir: Path) -> list[JsonDict]:
    """Load all valid metric snapshot records for trajectory rendering."""
    records: list[JsonDict] = []
    if not snapshots_dir.exists():
        return records
    invalid_schema_paths: list[str] = []
    for path in sorted(snapshots_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
        if not isinstance(record, dict) or "label" not in record:
            raise ValueError(f"Invalid metric snapshot record: {path}")
        if record.get("schemaVersion") != SNAPSHOT_SCHEMA_VERSION:
            invalid_schema_paths.append(path.as_posix())
        records.append(record)
    if invalid_schema_paths:
        raise ValueError(
            f"Trajectory requires metric snapshot schema {SNAPSHOT_SCHEMA_VERSION}; "
            "offending paths: " + ", ".join(invalid_schema_paths)
        )
    return sorted(
        records,
        key=lambda record: (
            int(record.get("trajectoryOrder", 1_000_000)),
            str(record["label"]),
        ),
    )


def format_metric(value: Any) -> str:
    """Format a metric value consistently for Markdown."""
    return f"{float(value):.{METRIC_DECIMAL_PLACES}f}"


def markdown_escape(value: str) -> str:
    """Escape table-sensitive characters in Markdown text."""
    return value.replace("|", "\\|").replace("\n", " ")


def consolidation_display(consolidation: JsonDict) -> str:
    """Format a consolidation result with its interpretation."""
    interpretation = str(consolidation["interpretation"]).replace("_", " ")
    return (
        f"{format_metric(consolidation['global']['ratio'])} "
        f"({markdown_escape(interpretation)})"
    )


def format_delta(filtered_value: Any, full_value: Any) -> str:
    """Format sensitivity-minus-full absolute and percentage deltas."""
    filtered = float(filtered_value)
    full = float(full_value)
    delta = filtered - full
    absolute = f"{delta:+.{METRIC_DECIMAL_PLACES}f}"
    if full == 0.0:
        return f"{absolute} (—)"
    percentage = delta / full * 100.0
    return f"{absolute} ({percentage:+.3f}%)"


def render_variant_table(
    records: list[JsonDict],
    variant_name: str,
    heading: str,
    introduction: str,
) -> list[str]:
    """Render one complete structural-metric variant table."""
    lines = [
        f"## {heading}",
        "",
        introduction,
        "",
        "| Construction point | Nodes | Edges | Information density | "
        "Informative attributes per node | Incident edges per node | "
        "Relational richness | Consolidation ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in records:
        variant = record["variants"][variant_name]
        metrics = variant["metrics"]
        density = metrics["informationDensity"]
        richness = metrics["relationalRichness"]
        lines.append(
            "| {name} | {nodes} | {edges} | {combined} | {attributes} | "
            "{incident} | {richness} | {consolidation} |".format(
                name=markdown_escape(str(record["displayName"])),
                nodes=variant["counts"]["nodes"],
                edges=variant["counts"]["edges"],
                combined=format_metric(density["combinedAveragePerNode"]),
                attributes=format_metric(
                    density["averageInformativeAttributesPerNode"]
                ),
                incident=format_metric(density["averageIncidentEdgesPerNode"]),
                richness=format_metric(
                    richness["averageDistinctRelationTypesPerNode"]
                ),
                consolidation=consolidation_display(metrics["consolidation"]),
            )
        )
    return lines


def render_trajectory_markdown(records: list[JsonDict]) -> str:
    """Render full, sensitivity, and sensitivity-effect trajectory tables."""
    exclusion_keys = ", ".join(
        f"`{key}`" for key in sorted(GLOBAL_ADMINISTRATIVE_ATTRIBUTE_KEYS)
    )
    contextual_keys = "; ".join(
        f"{class_name}: " + ", ".join(f"`{key}`" for key in sorted(keys))
        for class_name, keys in sorted(
            CLASS_SPECIFIC_ADMINISTRATIVE_ATTRIBUTE_KEYS.items()
        )
    )
    lines = [
        "# Structural Metrics Trajectory",
        "",
        "This report implements the cumulative internal trajectory from "
        "`docs/evaluation_decisions.md`. Both variants are always reported. "
        "The full graph is the primary description of the actual KG product; "
        "the filtered view is a sensitivity analysis and does not alter graph content.",
        "",
    ]
    lines.extend(
        render_variant_table(
            records,
            "full",
            "Table A — Full KG",
            "Primary description of the complete deterministic KG at each construction point.",
        )
    )
    lines.append("")
    lines.extend(
        render_variant_table(
            records,
            "fileInventoryExcluded",
            "Table B — File-inventory-excluded sensitivity analysis",
            "Sensitivity analysis only. File-inventory entities remain legitimate content "
            "in the actual KG and are not deleted from graph outputs.",
        )
    )
    lines.extend(
        [
            "",
            "## Table C — Sensitivity effect",
            "",
            "Every delta is `file_inventory_excluded − full`. Parenthesized values are "
            "percentage deltas relative to the full value; `—` indicates a zero denominator.",
            "",
            "| Construction point | Excluded nodes | Excluded edges | Excluded nodes as "
            "percentage of full graph | Delta information density | Delta informative "
            "attributes per node | Delta incident edges per node | Delta relational "
            "richness | Delta consolidation ratio |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for record in records:
        full = record["variants"]["full"]
        filtered = record["variants"]["fileInventoryExcluded"]
        audit = record["evaluationPolicy"]["fileInventorySensitivity"]
        full_density = full["metrics"]["informationDensity"]
        filtered_density = filtered["metrics"]["informationDensity"]
        full_richness = full["metrics"]["relationalRichness"]
        filtered_richness = filtered["metrics"]["relationalRichness"]
        full_consolidation = full["metrics"]["consolidation"]["global"]["ratio"]
        filtered_consolidation = filtered["metrics"]["consolidation"]["global"][
            "ratio"
        ]
        excluded_percentage = (
            float(audit["excludedNodeCount"]) / full["counts"]["nodes"] * 100.0
            if full["counts"]["nodes"]
            else 0.0
        )
        lines.append(
            "| {name} | {excluded_nodes} | {excluded_edges} | {excluded_pct:.6f}% | "
            "{density} | {attributes} | {incident} | {richness} | {consolidation} |".format(
                name=markdown_escape(str(record["displayName"])),
                excluded_nodes=audit["excludedNodeCount"],
                excluded_edges=audit["excludedEdgeCount"],
                excluded_pct=excluded_percentage,
                density=format_delta(
                    filtered_density["combinedAveragePerNode"],
                    full_density["combinedAveragePerNode"],
                ),
                attributes=format_delta(
                    filtered_density["averageInformativeAttributesPerNode"],
                    full_density["averageInformativeAttributesPerNode"],
                ),
                incident=format_delta(
                    filtered_density["averageIncidentEdgesPerNode"],
                    full_density["averageIncidentEdgesPerNode"],
                ),
                richness=format_delta(
                    filtered_richness["averageDistinctRelationTypesPerNode"],
                    full_richness["averageDistinctRelationTypesPerNode"],
                ),
                consolidation=format_delta(
                    filtered_consolidation, full_consolidation
                ),
            )
        )

    lines.extend(
        [
            "",
            "## Counting Policy",
            "",
            "Each nonempty informative attribute key counts once. Incoming and "
            "outgoing edge instances contribute to information density; distinct "
            "incident relation names contribute to relational richness. A self-loop "
            "counts once for its node.",
            "",
            f"**Administrative/identifier exclusion set:** {exclusion_keys}",
            "",
            f"**Class-specific administrative exclusions:** {contextual_keys}",
            "",
            "**File-inventory classes:** `DatasetFile` (A-D03), `File` (A-C02), "
            "and `RepoFile` (A-C02). Excluded edges are derived only from incident "
            "excluded endpoints; relation names and node degrees are not selectors.",
            "",
            f"**External URL stub note:** {EXTERNAL_URL_STUB_NOTE}",
            "",
        ]
    )
    return "\n".join(lines)


def update_trajectory_table(snapshots_dir: Path, table_path: Path) -> None:
    """Rebuild the trajectory Markdown table from all snapshot records."""
    records = load_snapshot_records(snapshots_dir)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.write_text(
        render_trajectory_markdown(records),
        encoding="utf-8",
    )


def print_summary(record: JsonDict, snapshot_path: Path, table_path: Path) -> None:
    """Print the principal metrics and per-class consolidation ratios."""
    print(f"Snapshot: {record['label']} ({record['displayName']})")
    print(f"Input: {record['input']['path']}")
    for variant_name in ("full", "fileInventoryExcluded"):
        variant = record["variants"][variant_name]
        density = variant["metrics"]["informationDensity"]
        richness = variant["metrics"]["relationalRichness"]
        consolidation = variant["metrics"]["consolidation"]
        print(f"Variant: {variant_name}")
        print(f"  Nodes: {variant['counts']['nodes']}")
        print(f"  Edges: {variant['counts']['edges']}")
        print(
            "  Information density: "
            f"{format_metric(density['combinedAveragePerNode'])}"
        )
        print(
            "    Informative attributes per node: "
            f"{format_metric(density['averageInformativeAttributesPerNode'])}"
        )
        print(
            "    Incident edges per node: "
            f"{format_metric(density['averageIncidentEdgesPerNode'])}"
        )
        print(
            "  Relational richness: "
            f"{format_metric(richness['averageDistinctRelationTypesPerNode'])}"
        )
        print(
            "  Consolidation ratio (global): "
            f"{format_metric(consolidation['global']['ratio'])} "
            f"[{consolidation['interpretation']}]"
        )
    sensitivity = record["evaluationPolicy"]["fileInventorySensitivity"]
    print(f"Excluded file-inventory nodes: {sensitivity['excludedNodeCount']}")
    print(f"Excluded incident edges: {sensitivity['excludedEdgeCount']}")
    print(f"Snapshot JSON: {portable_path(snapshot_path)}")
    if record["recordSeries"] == "trajectory":
        print(f"Trajectory table: {portable_path(table_path)}")
    else:
        print("Trajectory table: unchanged (module diagnostic)")
    print(f"Note: {EXTERNAL_URL_STUB_NOTE}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Interim nodes/edges JSON snapshot")
    parser.add_argument(
        "--label",
        required=True,
        help="Stable snapshot key and output filename stem",
    )
    parser.add_argument(
        "--display-name",
        help="Human-readable trajectory row label; defaults to --label",
    )
    parser.add_argument(
        "--order",
        "--trajectory-order",
        type=int,
        default=1_000,
        help="Numeric trajectory order used when rebuilding the Markdown table",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory containing snapshots/ and trajectory.md",
    )
    parser.add_argument(
        "--mention-count-attribute",
        default="mentionCount",
        help="Node attribute containing extracted mention counts after consolidation",
    )
    parser.add_argument(
        "--consolidation-stage",
        "--stage",
        choices=("pre_consolidation", "after_alignment", "after_assembly"),
        default="pre_consolidation",
        help="Trajectory stage recorded with the consolidation metric",
    )
    parser.add_argument(
        "--record-series",
        choices=("trajectory", "module"),
        default="trajectory",
        help="Write an official trajectory snapshot or an isolated module diagnostic",
    )
    return parser.parse_args()


def main() -> None:
    """Run structural metric computation and persist the labeled results."""
    args = parse_args()
    label = validate_label(args.label)
    display_name = args.display_name or label

    data = load_snapshot(args.input)
    validate_snapshot(data)
    record = build_results_record(
        data=data,
        input_path=args.input,
        label=label,
        display_name=display_name,
        order=args.order,
        mention_count_attribute=args.mention_count_attribute,
        consolidation_stage=args.consolidation_stage,
        record_series=args.record_series,
    )

    snapshots_dir = args.results_dir / "snapshots"
    snapshot_path = write_results_record(record, args.results_dir, args.record_series)
    table_path = args.results_dir / "trajectory.md"
    if args.record_series == "trajectory":
        update_trajectory_table(snapshots_dir, table_path)
    print_summary(record, snapshot_path, table_path)


if __name__ == "__main__":
    main()
