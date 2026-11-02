"""Distribution-only input adapter for a bounded Step 8 reviewer source envelope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import (INVENTORY_HASH, PACKAGE_ROOT, PACKAGES, TARGET_INVENTORY, ReviewError,
                        ReviewInputs, digest, evidence_contexts)


SCOPED_SOURCE_PATH = "data/curation/papers/m2/publication_step8_distribution_scoped_source_v1.0.1.json"


class ScopedReviewInputs:
    """Expose accepted blinded inputs using only distribution-scoped source text.

    This adapter deliberately does not read the full Pilot 1 inventory or raw paper
    Markdown.  It retains the original inventory and document hashes solely as
    immutable provenance bindings embedded in the scoped artifact.
    """

    def __init__(self, role: str, root: Path) -> None:
        """Verify a role package and its exact locally bundled source envelope."""

        if role not in PACKAGES:
            raise ReviewError("INVALID_REVIEW_ROLE")
        self.role, self.root = role, root
        name, self.package_hash = PACKAGES[role]
        self.package_path = root / PACKAGE_ROOT / name
        self.verify_package()
        self.package = json.loads(self.package_path.read_text(encoding="utf-8"))
        self.units = list(self.package["primarySourceUnitIDs"])
        self.items = {item["judgmentItemID"]: item for item in self.package["judgmentItems"]}
        self.groups = {group["duplicateReviewGroupID"]: group for group in self.package["duplicateReviewGroups"]}
        if len(self.items) != len(self.package["judgmentItems"]) or len(set(self.units)) != len(self.units):
            raise ReviewError("PACKAGE_IDENTITY_NOT_UNIQUE")
        self.target_guidance = ReviewInputs._load_target_guidance(self)
        missing_targets = {item["operationalTarget"]["operationalID"] for item in self.items.values()} - set(self.target_guidance)
        if missing_targets:
            raise ReviewError("REVIEW_TARGET_INVENTORY_MAPPING_ABSENT")
        self.contexts = {unit: sorted({context for item in self.items.values() if item["primarySourceUnitID"] == unit
                                       for context in item["authorizedContextSourceUnitIDs"]}) for unit in self.units}
        if any(set(values) & set(self.units) for values in self.contexts.values()):
            raise ReviewError("CONTEXT_BECAME_PRIMARY")
        self.sources = self._load_sources()
        self._verify_evidence()
        self.endpoint_bindings = ReviewInputs._current_paper_endpoint_bindings(self)

    def verify_package(self) -> None:
        """Recheck the immutable accepted blinded package before every action."""

        if not self.package_path.is_file() or digest(self.package_path.read_bytes()) != self.package_hash:
            raise ReviewError("BLINDED_PACKAGE_BINDING_DRIFT")

    def _load_sources(self) -> dict[str, dict[str, Any]]:
        """Load a self-hashed closure containing exactly primary and context units."""

        path = self.root / SCOPED_SOURCE_PATH
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ReviewError("DISTRIBUTION_SCOPED_SOURCE_INVALID") from exc
        artifact_hash = payload.pop("artifactSha256", None)
        if artifact_hash != digest(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")):
            raise ReviewError("DISTRIBUTION_SCOPED_SOURCE_BINDING_DRIFT")
        if payload.get("artifactType") != "publication_step8_distribution_scoped_sources" or payload.get("artifactVersion") != "1.0.1":
            raise ReviewError("DISTRIBUTION_SCOPED_SOURCE_INVALID")
        provenance = payload.get("fullInventoryProvenance")
        if not isinstance(provenance, dict) or provenance.get("sha256") != INVENTORY_HASH:
            raise ReviewError("DISTRIBUTION_SOURCE_PROVENANCE_DRIFT")
        expected = set(self.units) | {context for values in self.contexts.values() for context in values}
        if payload.get("primarySourceUnitIDs") != self.units or set(payload.get("authorizedContextSourceUnitIDs", [])) != expected - set(self.units):
            raise ReviewError("DISTRIBUTION_SOURCE_SCOPE_DRIFT")
        records = payload.get("sourceUnits")
        if not isinstance(records, list):
            raise ReviewError("DISTRIBUTION_SCOPED_SOURCE_INVALID")
        sources: dict[str, dict[str, Any]] = {}
        required = {"sourceUnitID", "sourceArtifactID", "sectionID", "sectionTitle", "startOffsetInDocument",
                    "endOffsetInDocument", "text", "textHash", "canonicalTextSha256", "originalSourceFileSha256"}
        for row in records:
            if not isinstance(row, dict) or set(row) != required or not all(isinstance(row[key], str) for key in required - {"startOffsetInDocument", "endOffsetInDocument"}):
                raise ReviewError("DISTRIBUTION_SCOPED_SOURCE_INVALID")
            unit = row["sourceUnitID"]
            if unit in sources or unit not in expected or not isinstance(row["startOffsetInDocument"], int) or not isinstance(row["endOffsetInDocument"], int):
                raise ReviewError("DISTRIBUTION_SOURCE_SCOPE_DRIFT")
            if (row["startOffsetInDocument"] < 0 or row["endOffsetInDocument"] - row["startOffsetInDocument"] != len(row["text"])
                    or digest(row["text"].encode()) != row["textHash"]):
                raise ReviewError("CANONICAL_SOURCE_DRIFT")
            sources[unit] = {"sourceUnitID": unit, "text": row["text"], "textHash": row["textHash"],
                             "sectionTitle": row["sectionTitle"], "sourceArtifactID": row["sourceArtifactID"],
                             "startOffsetInDocument": row["startOffsetInDocument"]}
        if set(sources) != expected:
            raise ReviewError("AUTHORIZED_SOURCE_ABSENT")
        self.source_inventory_hash = digest(path.read_bytes())
        return sources

    def _verify_evidence(self) -> None:
        """Preserve the accepted coordinate and source-artifact evidence contract."""

        for item in self.items.values():
            primary = item["primarySourceUnitID"]
            if primary not in self.units:
                raise ReviewError("UNKNOWN_PRIMARY_UNIT")
            for occurrence in item["evidenceOccurrences"]:
                unit = occurrence["sourceUnitID"]
                if unit not in {primary, *item["authorizedContextSourceUnitIDs"]}:
                    raise ReviewError("EVIDENCE_OUTSIDE_ITEM_SCOPE")
                row = self.sources[unit]
                start, end = occurrence["startOffsetInUnit"], occurrence["endOffsetInUnit"]
                if (not 0 <= start < end <= len(row["text"]) or row["text"][start:end] != occurrence["evidenceText"]
                        or row["textHash"] != occurrence["sourceUnitTextHash"] or row["sourceArtifactID"] != occurrence["sourceArtifactID"]
                        or occurrence["startOffsetInDocument"] != start + row["startOffsetInDocument"]
                        or occurrence["endOffsetInDocument"] != end + row["startOffsetInDocument"]):
                    raise ReviewError("EVIDENCE_COORDINATE_OR_TEXT_DRIFT")

    def unit(self, unit: str) -> dict[str, Any]:
        """Return the identical reviewer projection constrained to this source envelope."""

        if unit not in self.units:
            raise ReviewError("UNIT_NOT_ASSIGNED")
        items = [ReviewInputs._reviewer_item(self, item) for item in self.items.values() if item["primarySourceUnitID"] == unit]
        return {"primarySourceUnitID": unit, "source": self.sources[unit],
                "authorizedContext": [self.sources[context] for context in self.contexts[unit]],
                "items": [{**item, "paragraphContexts": evidence_contexts(item, self.sources)} for item in items],
                "duplicateReviewGroups": [group for group in self.groups.values()
                                          if all(self.items[key]["primarySourceUnitID"] == unit for key in group["judgmentItemIDs"])]}
