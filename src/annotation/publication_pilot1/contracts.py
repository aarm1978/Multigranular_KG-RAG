"""Read and validate the immutable Publication Pilot 1 screening contracts."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


PROTECTED_HASHES = {
    "data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv": "b950c8f4389d3af36c3c324572c53f4668304e7fd52c1539e079f72c658e232b",
    "data/curation/papers/pilot1/publication_pilot1_selection_policy.yaml": "e977a77da4dc49e6f1ad3a283c60ccb2f2dbf391ac9d2541f60c8dc7d80526c3",
    "schemas/publication_pilot1_screening_record.schema.json": "473e524e679fc19cf267a078cecd09bd21b2e06ddcdb05fdfcc5a8c8a21363f3",
    "schemas/publication_pilot1_unit_routing.schema.json": "49af68b0ab47a5bbd29b6d10c382aee6252a1d5a3c1d0510c13e4673775c329f",
    "data/curation/papers/pilot1/publication_pilot1_target_family_mapping.yaml": "fbf1da8f43174791a160106014975fd7084c18de5df2f14a5203368418f081fe",
    "data/curation/papers/pilot1/publication_pilot1_target_display_catalog.yaml": "06ce672fd0ab66a8faa46bb4a870778c99acebf9cdd242be8b8a0dba493cae96",
    "data/curation/papers/pilot1/publication_pilot1_gate0_policy.yaml": "f9285a4912e55a154d9037e7fa97a6176f1e37194272ec6907ce8af4f10888ae",
}
INVENTORY_HASH = "7a3a4941e6c07deee96b19c7619e0b9c5000ad6fadf5bf17379e37229562b07e"
MANIFEST_HASH = "42684d340af99440d5f72129a5c5299edcb237d77ce2b3d36456b049bee83823"
SCREENING_HANDBOOK_PATH = "docs/publication_pilot1_screening_handbook.md"
SCREENING_HANDBOOK_SHA256 = "c8a8099286871e22616022b5964ef42b10e251601131732968977fcfc3711bc2"
DETERMINISTIC_COLUMN_COUNT = 23
OPEN_UNIT_COUNT = 267
TOTAL_UNIT_COUNT = 358

RECURRING_DISTINCTIONS = (
    "Model/Method/Algorithm/Tool",
    "Finding/Conclusion",
    "ResearchProblem/ResearchGoal",
    "use/mention/reference",
    "EvaluationMetric/Parameter",
)
DENSITIES = ("none", "low", "medium", "high")
ROUTING_COMPLEXITIES = ("low", "medium", "high")
BOOLEAN_FIELDS = (
    "distributedEvidenceLikely",
    "sectionContextUseful",
    "deterministicEndpointLikely",
)
MULTI_FIELDS = (
    "likelyExhaustiveEmptyTargetIDs",
    "likelyRecurringDistinctions",
    "routedNodeOperationalTargetIDs",
    "routedRelationOperationalTargetIDs",
)


class ContractError(ValueError):
    """Report deterministic interface contract validation failures."""


def sha256_file(path: Path) -> str:
    """Return a lowercase SHA-256 digest for ``path``."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_protected_hashes(root: Path) -> dict[str, str]:
    """Validate every protected upstream input and return its observed hash."""

    observed: dict[str, str] = {}
    for relative, expected in PROTECTED_HASHES.items():
        path = root / relative
        if not path.is_file():
            raise ContractError(f"SCREENING_MVP_UPSTREAM_FILE_MISSING:{relative}")
        observed[relative] = sha256_file(path)
        if observed[relative] != expected:
            raise ContractError(f"SCREENING_MVP_BLOCKED_BY_UPSTREAM_DRIFT:{relative}")
    inventory = root / "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"
    manifest = root / "data/curation/papers/pilot1/publication_pilot1_source_unit_manifest.json"
    if sha256_file(inventory) != INVENTORY_HASH:
        raise ContractError("SCREENING_MVP_BLOCKED_BY_UPSTREAM_DRIFT:source_unit_inventory")
    if sha256_file(manifest) != MANIFEST_HASH:
        raise ContractError("SCREENING_MVP_BLOCKED_BY_UPSTREAM_DRIFT:source_unit_manifest")
    handbook = root / SCREENING_HANDBOOK_PATH
    if not handbook.is_file() or sha256_file(handbook) != SCREENING_HANDBOOK_SHA256:
        raise ContractError("SCREENING_FROZEN_HANDBOOK_HASH_MISMATCH")
    observed[SCREENING_HANDBOOK_PATH] = SCREENING_HANDBOOK_SHA256
    return observed


def _canonical_text(path: Path) -> str:
    """Load source bytes using the frozen minimal canonical-text normalization."""

    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return "".join(" " if ord(char) < 32 and char not in "\t\n" else char for char in text)


@dataclass(frozen=True)
class ContractBundle:
    """Validated immutable worklist, source inventory, and target catalog."""

    root: Path
    headers: tuple[str, ...]
    rows: tuple[Mapping[str, str], ...]
    inventory_by_id: Mapping[str, Mapping[str, Any]]
    targets: tuple[Mapping[str, Any], ...]
    protected_hashes: Mapping[str, str]

    @property
    def deterministic_columns(self) -> tuple[str, ...]:
        """Return the frozen prefix of worklist columns."""

        return self.headers[:DETERMINISTIC_COLUMN_COUNT]

    @property
    def human_columns(self) -> tuple[str, ...]:
        """Return the human-editable suffix of worklist columns."""

        return self.headers[DETERMINISTIC_COLUMN_COUNT:]

    @property
    def open_rows(self) -> tuple[Mapping[str, str], ...]:
        """Return structurally eligible human-screening rows in canonical order."""

        return tuple(row for row in self.rows if is_open(row))

    def target_by_id(self) -> dict[str, Mapping[str, Any]]:
        """Return human-visible targets keyed by operational ID."""

        return {str(target["operationalTargetID"]): target for target in self.targets}

    def load_source_text(self, source_unit_id: str) -> str:
        """Reconstruct and validate an exact Unicode-code-point source-unit slice."""

        record = self.inventory_by_id.get(source_unit_id)
        if record is None:
            raise ContractError(f"SOURCE_UNIT_UNKNOWN:{source_unit_id}")
        path = self.root / str(record["sourceFile"])
        if not path.is_file():
            raise ContractError(f"SOURCE_FILE_NOT_FOUND:{record['sourceFile']}")
        document = _canonical_text(path)
        start, end = int(record["startOffsetInDocument"]), int(record["endOffsetInDocument"])
        sliced = document[start:end]
        if sliced != record["text"]:
            raise ContractError(f"UNIT_TEXT_MISMATCH:{source_unit_id}")
        digest = hashlib.sha256(sliced.encode("utf-8")).hexdigest()
        if digest != record["textHash"]:
            raise ContractError(f"TEXT_HASH_MISMATCH:{source_unit_id}")
        if len(sliced) != int(record["characterCount"]):
            raise ContractError(f"CHARACTER_COUNT_MISMATCH:{source_unit_id}")
        return sliced


def is_open(row: Mapping[str, str]) -> bool:
    """Return whether a worklist row is open for human semantic screening."""

    return row["sourceEligibility"] == "eligible" and row["requestEligible"] == "true"


def load_contracts(root: Path) -> ContractBundle:
    """Load and cross-check all contracts required by the screening interface."""

    root = root.resolve()
    hashes = validate_protected_hashes(root)
    worklist = root / "data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv"
    with worklist.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = tuple(reader.fieldnames or ())
        rows = tuple(dict(row) for row in reader)
    inventory_path = root / "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"
    inventory = tuple(json.loads(line) for line in inventory_path.read_text(encoding="utf-8").splitlines() if line)
    inventory_by_id = {record["sourceUnitID"]: record for record in inventory}
    catalog_path = root / "data/curation/papers/pilot1/publication_pilot1_target_display_catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    targets = tuple(
        target for target in catalog["targets"]
        if target["humanVisible"] and (target["targetKind"] != "node" or target.get("directInstantiation", False))
    )
    if len(rows) != TOTAL_UNIT_COUNT or len(inventory_by_id) != TOTAL_UNIT_COUNT:
        raise ContractError("SCREENING_MVP_UNIT_CARDINALITY_MISMATCH")
    if {row["sourceUnitID"] for row in rows} != set(inventory_by_id):
        raise ContractError("SCREENING_MVP_WORKLIST_INVENTORY_ID_MISMATCH")
    counts = Counter(row["sourceEligibility"] for row in rows)
    if counts != Counter({"eligible": 267, "context_only": 49, "excluded": 39, "needs_review": 3}):
        raise ContractError("SCREENING_MVP_STRUCTURAL_COUNTS_MISMATCH")
    if len([row for row in rows if is_open(row)]) != OPEN_UNIT_COUNT:
        raise ContractError("SCREENING_MVP_OPEN_UNIT_COUNT_MISMATCH")
    return ContractBundle(root, headers, rows, inventory_by_id, targets, hashes)
