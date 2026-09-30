"""Materialize the bounded prospective Publication v0.1.5 routing correction.

This module is deliberately upstream of provider dispatch and canonical semantic
processing.  It derives a new routing authority from the frozen v0.1.5 target
inventory, source-unit inventory, and historical routing artifact without reading
source prose, annotations, evaluation outputs, or provider artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    canonical_json_file,
    load_yaml_object,
    sha256_bytes,
)


MIGRATION_VERSION = "publication-v015-routing-migration/0.1.0"
ROUTING_SCHEMA_VERSION = "0.1.3"
ARTIFACT_VERSION = "0.1.0"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data/curation/papers/m2/publication_v015_routing_migration"
BASE_ROUTING_PATH = PROJECT_ROOT / "data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl"
SOURCE_INVENTORY_PATH = PROJECT_ROOT / "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"
TARGET_INVENTORY_PATH = PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml"
ROUTING_OUTPUT_NAME = "publication_v015_corrected_unit_routing_v0.1.0.jsonl"
AUTHORITY_OUTPUT_NAME = "publication_v015_corrected_routing_authority_v0.1.0.json"
PREFLIGHT_OUTPUT_NAME = "publication_v015_corrected_routing_preflight_v0.1.0.json"

ORGANIZATION_TARGET = "PUB-N-A-AG02-ORGANIZATION-PROSE"
AGENT_BASED_MODEL_TARGET = "PUB-N-A-DOM03E-AGENTBASEDMODEL"
HAS_COMPONENT_TARGET = "PUB-R-C-P34-HASCOMPONENT"
EXISTING_MODEL_NODE_TARGETS = frozenset(
    {
        "PUB-N-A-DOM03A-PROCESSBASEDMODEL",
        "PUB-N-A-DOM03B-CONCEPTUALMODEL",
        "PUB-N-A-DOM03C-STATISTICALMODEL",
        "PUB-N-A-DOM03D-MLMODEL",
    }
)
TOOL_TARGETS = frozenset({"PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE"})
AGENT_BASED_MODEL_RELATION_TARGETS = frozenset(
    {
        "PUB-R-C-P13-USESMODEL-PAPER-BRANCH",
        "PUB-R-C-P13-USESMODEL-METHOD-BRANCH",
        "PUB-R-C-P14-APPLIESTO",
        "PUB-R-C-P23-MENTIONSMODEL",
        "PUB-R-C-P26-EVALUATES",
        "PUB-R-C-P27-HASPARAMETER",
    }
)
DELTA_NODE_TARGETS = frozenset({ORGANIZATION_TARGET, AGENT_BASED_MODEL_TARGET})
DELTA_RELATION_TARGETS = frozenset({HAS_COMPONENT_TARGET})
DELTA_TARGETS = DELTA_NODE_TARGETS | DELTA_RELATION_TARGETS
PRODUCTION_RECORD_TYPES = frozenset({"journal_article", "book_chapter"})


class RoutingMigrationError(ValueError):
    """Report a failure to derive the bounded routing correction safely."""


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a nonempty JSONL authority artifact as object rows."""

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise RoutingMigrationError(f"invalid JSONL authority: {path}")
    return rows


def _artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return one canonical artifact with a self-hash."""

    result = dict(payload)
    result["artifactSha256"] = sha256_bytes(canonical_json(result))
    return result


def _write_immutable(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a canonical artifact once, rejecting divergent replacement bytes."""

    content = canonical_json_file(dict(payload))
    if path.exists() and path.read_bytes() != content:
        raise RoutingMigrationError(f"ROUTING_MIGRATION_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_jsonl_immutable(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write canonical JSONL once, rejecting divergent replacement bytes."""

    content = b"".join(canonical_json(dict(row)) + b"\n" for row in rows)
    if path.exists() and path.read_bytes() != content:
        raise RoutingMigrationError(f"ROUTING_MIGRATION_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _target_rows(profile: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Index the v0.1.5 node and relation operational rows."""

    return {
        str(row["operational_id"]): dict(row)
        for row in [*profile["node_targets"], *profile["relation_targets"]]
    }


def _assert_frozen_delta_authority(rows: Mapping[str, Mapping[str, Any]]) -> None:
    """Fail closed unless the accepted v0.1.5 delta has its exact authority shape."""

    for target_id in DELTA_TARGETS:
        row = rows.get(target_id)
        if row is None:
            raise RoutingMigrationError(f"V015_DELTA_TARGET_MISSING:{target_id}")
        if row.get("production_responsibility") != "llm" or row.get("emission_mode") != "llm_candidate":
            raise RoutingMigrationError(f"V015_DELTA_TARGET_NOT_MODEL_AUTHORABLE:{target_id}")
    if rows[ORGANIZATION_TARGET].get("pilot_treatment") != "extract_and_evaluate":
        raise RoutingMigrationError("V015_ORGANIZATION_TREATMENT_DRIFT")
    if rows[AGENT_BASED_MODEL_TARGET].get("pilot_treatment") != "extract_and_evaluate":
        raise RoutingMigrationError("V015_AGENT_BASED_MODEL_TREATMENT_DRIFT")
    if rows[HAS_COMPONENT_TARGET].get("pilot_treatment") != "extract_and_evaluate":
        raise RoutingMigrationError("V015_HAS_COMPONENT_TREATMENT_DRIFT")
    for target_id in AGENT_BASED_MODEL_RELATION_TARGETS:
        signatures = rows[target_id].get("operational_signatures", [])
        if "AgentBasedModel" not in json.dumps(signatures, sort_keys=True):
            raise RoutingMigrationError(f"V015_AGENT_BASED_MODEL_SIGNATURE_MISSING:{target_id}")
    component = rows[HAS_COMPONENT_TARGET].get("operational_signatures", [])
    if "AgentBasedModel" not in json.dumps(component, sort_keys=True) or "Tool" not in json.dumps(component, sort_keys=True):
        raise RoutingMigrationError("V015_HAS_COMPONENT_SIGNATURE_DRIFT")


def _is_open_source(source: Mapping[str, Any]) -> bool:
    """Return whether one frozen source unit remains prospectively request-eligible."""

    return source.get("eligibility") == "eligible" and source.get("requestEligible") is True


def _append_once(values: Sequence[str], target_id: str) -> list[str]:
    """Append one target without changing the order of existing routing decisions."""

    return list(values) if target_id in values else [*values, target_id]


def _migration_target_ids(route: Mapping[str, Any], source: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Derive only the accepted delta targets for one existing routing row.

    Organization is globally cross-category for every eligible source unit.  The
    AgentBasedModel target is activated only where the historical routing already
    opened a concrete model target or a model-relation channel.  hasComponent is
    activated only where the historical routing already opened a Tool/model endpoint
    channel.  These rules use routing metadata only; they never classify prose.
    """

    if not _is_open_source(source):
        return [], []
    nodes = set(route["eligibleNodeOperationalTargetIDs"])
    relations = set(route["eligibleRelationOperationalTargetIDs"])
    model_channel = bool(nodes & EXISTING_MODEL_NODE_TARGETS or relations & AGENT_BASED_MODEL_RELATION_TARGETS)
    composition_channel = bool(nodes & (EXISTING_MODEL_NODE_TARGETS | TOOL_TARGETS) or relations & AGENT_BASED_MODEL_RELATION_TARGETS)
    node_delta = [ORGANIZATION_TARGET]
    if model_channel:
        node_delta.append(AGENT_BASED_MODEL_TARGET)
    return node_delta, [HAS_COMPONENT_TARGET] if composition_channel else []


def _non_delta_projection(route: Mapping[str, Any]) -> dict[str, Any]:
    """Project the fields whose values must remain byte-for-value unchanged."""

    return {
        "sourceUnitID": route["sourceUnitID"],
        "eligibleNodeOperationalTargetIDs": [
            target_id for target_id in route["eligibleNodeOperationalTargetIDs"] if target_id not in DELTA_NODE_TARGETS
        ],
        "eligibleRelationOperationalTargetIDs": [
            target_id for target_id in route["eligibleRelationOperationalTargetIDs"] if target_id not in DELTA_RELATION_TARGETS
        ],
        "humanScreenedNodeOperationalTargetIDs": list(route["humanScreenedNodeOperationalTargetIDs"]),
        "humanScreenedRelationOperationalTargetIDs": list(route["humanScreenedRelationOperationalTargetIDs"]),
        "structurallyUnavailableOperationalTargets": list(route["structurallyUnavailableOperationalTargets"]),
        "contextFlags": dict(route["contextFlags"]),
        "deterministicEndpointRefs": list(route["deterministicEndpointRefs"]),
        "sourceConversionStatus": route["sourceConversionStatus"],
    }


def derive_corrected_routing(
    *,
    base_routing_path: Path = BASE_ROUTING_PATH,
    source_inventory_path: Path = SOURCE_INVENTORY_PATH,
    target_inventory_path: Path = TARGET_INVENTORY_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Derive corrected routing rows and their standalone routing authority record."""

    base_routes = _load_jsonl(base_routing_path)
    inventory = {str(row["sourceUnitID"]): row for row in _load_jsonl(source_inventory_path)}
    if len(inventory) != len(base_routes) or set(inventory) != {str(row["sourceUnitID"]) for row in base_routes}:
        raise RoutingMigrationError("ROUTING_AND_SOURCE_INVENTORY_BINDING_DRIFT")
    profile = load_yaml_object(target_inventory_path)
    rows = _target_rows(profile)
    _assert_frozen_delta_authority(rows)

    corrected: list[dict[str, Any]] = []
    application_counts: Counter[str] = Counter()
    for base in base_routes:
        route = dict(base)
        node_delta, relation_delta = _migration_target_ids(route, inventory[route["sourceUnitID"]])
        nodes = list(route["eligibleNodeOperationalTargetIDs"])
        relations = list(route["eligibleRelationOperationalTargetIDs"])
        for target_id in node_delta:
            nodes = _append_once(nodes, target_id)
            application_counts[target_id] += 1
        for target_id in relation_delta:
            relations = _append_once(relations, target_id)
            application_counts[target_id] += 1
        primary = [
            target_id
            for target_id in [*nodes, *relations]
            if rows[target_id].get("pilot_treatment") in {"extract_and_evaluate", "extract_and_monitor"}
        ]
        changed = bool(node_delta or relation_delta)
        route.update(
            {
                "routingSchemaVersion": ROUTING_SCHEMA_VERSION,
                "routingVersion": MIGRATION_VERSION,
                "routingStatus": "routed" if _is_open_source(inventory[route["sourceUnitID"]]) and primary else route["routingStatus"],
                "routingBasis": "frozen_routing_plus_v015_authority_delta" if changed else route["routingBasis"],
                "eligibleNodeOperationalTargetIDs": nodes,
                "eligibleRelationOperationalTargetIDs": relations,
                "primaryEligibleOperationalTargetIDs": sorted(primary),
                "menuDiagnostics": {
                    **dict(route["menuDiagnostics"]),
                    "nodeTargetCount": len(nodes),
                    "relationTargetCountBeforeEndpointFiltering": len(relations),
                },
                "v015RoutingMigration": {
                    "migrationVersion": MIGRATION_VERSION,
                    "baseRoutingVersion": base["routingVersion"],
                    "baseRoutingSha256": sha256_bytes(canonical_json(base)),
                    "addedNodeOperationalTargetIDs": node_delta,
                    "addedRelationOperationalTargetIDs": relation_delta,
                },
            }
        )
        corrected.append(route)

    baseline_projection = [_non_delta_projection(route) for route in base_routes]
    corrected_projection = [_non_delta_projection(route) for route in corrected]
    if baseline_projection != corrected_projection:
        raise RoutingMigrationError("NON_DELTA_ROUTING_DRIFT")
    routing_bytes = b"".join(canonical_json(row) for row in corrected)
    authority = _artifact(
        {
            "artifactType": "publication_v015_corrected_routing_authority",
            "artifactVersion": ARTIFACT_VERSION,
            "routingVersion": MIGRATION_VERSION,
            "routingSchemaVersion": ROUTING_SCHEMA_VERSION,
            "status": "prospective_routing_correction_no_provider_execution",
            "purpose": "bounded_v015_migration_correction",
            "providerModelCalls": 0,
            "canonicalDownstreamProcessing": {
                "semanticPipeline": "publication-semantic-pipeline/1.0.0",
                "evidenceFailureIsolation": "publication-evidence-failure-isolation/1.0.0",
                "modified": False,
            },
            "authorities": {
                "baseRouting": {"path": str(base_routing_path.relative_to(PROJECT_ROOT)), "sha256": sha256_bytes(base_routing_path.read_bytes()), "routingVersion": base_routes[0]["routingVersion"]},
                "sourceInventory": {"path": str(source_inventory_path.relative_to(PROJECT_ROOT)), "sha256": sha256_bytes(source_inventory_path.read_bytes())},
                "targetInventory": {"path": str(target_inventory_path.relative_to(PROJECT_ROOT)), "sha256": sha256_bytes(target_inventory_path.read_bytes()), "profileID": profile["profile_id"], "ontologyVersion": profile["ontology"]["version"]},
            },
            "acceptedDelta": {
                "globallyEligibleNodeTarget": ORGANIZATION_TARGET,
                "modelChannelNodeTarget": AGENT_BASED_MODEL_TARGET,
                "compositionChannelRelationTarget": HAS_COMPONENT_TARGET,
                "agentBasedModelEnabledRelationTargetIDs": sorted(AGENT_BASED_MODEL_RELATION_TARGETS),
                "unchangedTargetsWereNotAdded": True,
                "mentionsRemainsPipelineDerived": True,
            },
            "routing": {"path": str((OUTPUT_DIRECTORY / ROUTING_OUTPUT_NAME).relative_to(PROJECT_ROOT)), "sha256": sha256_bytes(routing_bytes), "recordCount": len(corrected), "applicationCounts": dict(sorted(application_counts.items()))},
            "nonDeltaRoutingProof": {"baselineProjectionSha256": sha256_bytes(canonical_json(baseline_projection)), "correctedProjectionSha256": sha256_bytes(canonical_json(corrected_projection)), "unchanged": True},
        }
    )
    return corrected, authority


def build_preflight(
    corrected: Sequence[Mapping[str, Any]], authority: Mapping[str, Any], *, source_inventory_path: Path = SOURCE_INVENTORY_PATH
) -> dict[str, Any]:
    """Summarize corrected routing opportunities without constructing provider requests."""

    inventory = {str(row["sourceUnitID"]): row for row in _load_jsonl(source_inventory_path)}
    production_rows = [
        row for row in corrected
        if _is_open_source(inventory[str(row["sourceUnitID"])])
        and inventory[str(row["sourceUnitID"])].get("recordType") in PRODUCTION_RECORD_TYPES
    ]
    all_open_rows = [row for row in corrected if _is_open_source(inventory[str(row["sourceUnitID"])])]
    target_ids = [ORGANIZATION_TARGET, AGENT_BASED_MODEL_TARGET, HAS_COMPONENT_TARGET, *sorted(AGENT_BASED_MODEL_RELATION_TARGETS)]
    def opportunities(rows: Sequence[Mapping[str, Any]], target_id: str) -> int:
        return sum(target_id in [*row["eligibleNodeOperationalTargetIDs"], *row["eligibleRelationOperationalTargetIDs"]] for row in rows)
    return _artifact(
        {
            "artifactType": "publication_v015_corrected_routing_preflight",
            "artifactVersion": ARTIFACT_VERSION,
            "status": "deterministic_routing_preflight_complete_no_provider_execution",
            "providerModelCalls": 0,
            "correctedRoutingAuthority": {"path": str((OUTPUT_DIRECTORY / AUTHORITY_OUTPUT_NAME).relative_to(PROJECT_ROOT)), "sha256": authority["artifactSha256"], "routingSha256": authority["routing"]["sha256"]},
            "routingPopulation": {"totalSourceUnits": len(corrected), "openSourceUnits": len(all_open_rows), "routedOpenSourceUnits": sum(row["routingStatus"] == "routed" for row in all_open_rows), "nextProductionEligibleJournalOrBookUnits": len(production_rows)},
            "opportunityCounts": {"allOpenSourceUnits": {target_id: opportunities(all_open_rows, target_id) for target_id in target_ids}, "nextProductionEligibleJournalOrBookUnits": {target_id: opportunities(production_rows, target_id) for target_id in target_ids}},
            "nonDeltaRoutingProof": dict(authority["nonDeltaRoutingProof"]),
            "readyForSeparateProductionRequestPreflight": True,
        }
    )


def materialize(output_directory: Path = OUTPUT_DIRECTORY) -> dict[str, Any]:
    """Materialize the corrected routing authority and deterministic preflight."""

    corrected, authority = derive_corrected_routing()
    preflight = build_preflight(corrected, authority)
    _write_jsonl_immutable(output_directory / ROUTING_OUTPUT_NAME, corrected)
    _write_immutable(output_directory / AUTHORITY_OUTPUT_NAME, authority)
    _write_immutable(output_directory / PREFLIGHT_OUTPUT_NAME, preflight)
    return {"authority": authority, "preflight": preflight, "routingPath": output_directory / ROUTING_OUTPUT_NAME}


def main(argv: Sequence[str] | None = None) -> int:
    """Materialize the no-network routing correction from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, default=OUTPUT_DIRECTORY)
    args = parser.parse_args(argv)
    result = materialize(args.output_directory)
    print(json.dumps({"authoritySha256": result["authority"]["artifactSha256"], "preflightSha256": result["preflight"]["artifactSha256"], "routingPath": str(result["routingPath"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
