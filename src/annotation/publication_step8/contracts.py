"""Bound blinded packages, exact source slices, and visual evidence segments."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from src.extraction.llm.publications.request_builder import canonical_json

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = "data/curation/papers/m2/publication_step8_blinded_adjudication"
PACKAGES = {
    "primary": ("publication_step8b_blinded_primary_review_v1.0.0.json", "112f14e3a9093ce8acc7fd47b06f150a01ba579dac641e7baad1956818fbe2f7"),
    "second": ("publication_step8b_blinded_second_review_v1.1.0.json", "628bb07cfb5dd0a6df59fb367aec6b46492760b356dc380b64637d0e7b063983"),
}
INVENTORY = "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"
INVENTORY_HASH = "7a3a4941e6c07deee96b19c7619e0b9c5000ad6fadf5bf17379e37229562b07e"
TARGET_INVENTORY = "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml"
TARGET_INVENTORY_HASH = "84aa773f0a4931fafc50d27240d784b2c977ef29767f3d9e80f3f4a42ef8e6e0"
JUDGMENTS = ("supported_as_proposed", "not_supported_as_proposed", "insufficient_evidence_to_decide")
DUPLICATE_DECISIONS = ("same_source_local_assertion", "distinct_assertions", "insufficient_evidence_to_resolve_duplicate_status")


class ReviewError(ValueError):
    """Fail closed on an execution boundary or invalid reviewer action."""


def digest(data: bytes) -> str:
    """Compute an exact SHA-256 binding."""

    return hashlib.sha256(data).hexdigest()


def canonical_text(data: bytes) -> str:
    """Apply the frozen source contract's minimal canonical normalization."""

    text = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return "".join(" " if ord(char) < 32 and char not in "\t\n" else char for char in text)


def runtime_hash() -> str:
    """Bind all executable Python and static assets of this interface."""

    folder = Path(__file__).parent
    files = {str(path.relative_to(folder)): digest(path.read_bytes())
             for path in sorted(folder.rglob("*")) if path.suffix in {".py", ".js", ".css", ".html"}}
    return digest(canonical_json(files))


class ReviewInputs:
    """Load exactly one reviewer role's accepted package and bounded sources."""

    def __init__(self, role: str, root: Path = ROOT) -> None:
        """Verify tracked packages and source slices before exposing any state."""

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
        self.target_guidance = self._load_target_guidance()
        missing_targets = {item["operationalTarget"]["operationalID"] for item in self.items.values()} - set(self.target_guidance)
        if missing_targets:
            raise ReviewError("REVIEW_TARGET_INVENTORY_MAPPING_ABSENT")
        self.contexts = {unit: sorted({context for item in self.items.values() if item["primarySourceUnitID"] == unit
                                     for context in item["authorizedContextSourceUnitIDs"]}) for unit in self.units}
        allowed = set(self.units) | {context for values in self.contexts.values() for context in values}
        if any(set(values) & set(self.units) for values in self.contexts.values()):
            raise ReviewError("CONTEXT_BECAME_PRIMARY")
        inventory = root / INVENTORY
        if digest(inventory.read_bytes()) != INVENTORY_HASH:
            raise ReviewError("SOURCE_INVENTORY_BINDING_DRIFT")
        records = [json.loads(line) for line in inventory.read_text(encoding="utf-8").splitlines()]
        self.sources = {}
        documents: dict[str, str] = {}
        for row in records:
            unit = row["sourceUnitID"]
            if unit not in allowed:
                continue
            source = root / row["sourceFile"]
            if row["sourceFile"] not in documents:
                documents[row["sourceFile"]] = canonical_text(source.read_bytes())
            document = documents[row["sourceFile"]]
            text = document[row["startOffsetInDocument"]:row["endOffsetInDocument"]]
            if digest(document.encode()) != row["canonicalTextSha256"] or text != row["text"] or digest(text.encode()) != row["textHash"]:
                raise ReviewError("CANONICAL_SOURCE_DRIFT")
            self.sources[unit] = {"sourceUnitID": unit, "text": text, "textHash": row["textHash"],
                                  "sectionTitle": row["sectionTitleRaw"] or row["sectionTitleNormalized"],
                                  "sourceArtifactID": row["canonicalArtifactID"], "startOffsetInDocument": row["startOffsetInDocument"]}
        if set(self.sources) != allowed:
            raise ReviewError("AUTHORIZED_SOURCE_ABSENT")
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
        self.endpoint_bindings = self._current_paper_endpoint_bindings()

    def _load_target_guidance(self) -> dict[str, dict[str, str]]:
        """Load the frozen human-review criterion and boundary for each target."""

        path = self.root / TARGET_INVENTORY
        if not path.is_file() or digest(path.read_bytes()) != TARGET_INVENTORY_HASH:
            raise ReviewError("TARGET_INVENTORY_BINDING_DRIFT")
        try:
            inventory = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ReviewError("TARGET_INVENTORY_INVALID") from exc
        targets = [*inventory.get("node_targets", []), *inventory.get("relation_targets", [])]
        guidance = {
            target.get("operational_id"): {
                "positiveCriterion": target.get("positive_criterion"),
                "boundary": target.get("boundary"),
            }
            for target in targets
        }
        if (len(guidance) != len(targets) or any(not isinstance(key, str) or not isinstance(value["positiveCriterion"], str)
                                                  or not isinstance(value["boundary"], str) for key, value in guidance.items())):
            raise ReviewError("TARGET_INVENTORY_GUIDANCE_INVALID")
        return guidance

    def _current_paper_endpoint_bindings(self) -> dict[str, list[dict[str, str]]]:
        """Retain exact current-paper endpoint IDs for internal deterministic exports."""

        bindings: dict[str, list[dict[str, str]]] = {}
        for item in self.items.values():
            source_id = self.sources[item["primarySourceUnitID"]]["sourceArtifactID"]
            found = []
            for endpoint_name in ("sourceEndpoint", "targetEndpoint"):
                endpoint = item["assertion"].get(endpoint_name, {})
                if endpoint.get("endpointKind") == "deterministic_node" and endpoint.get("exactNodeID") == source_id:
                    found.append({"endpoint": endpoint_name, "exactNodeID": source_id})
            if found:
                bindings[item["judgmentItemID"]] = found
        return bindings

    def verify_package(self) -> None:
        """Recheck the exact accepted package before persistence or export."""

        if not self.package_path.is_file() or digest(self.package_path.read_bytes()) != self.package_hash:
            raise ReviewError("BLINDED_PACKAGE_BINDING_DRIFT")

    def unit(self, unit: str) -> dict[str, Any]:
        """Expose one assigned primary unit and only its authorized context."""

        if unit not in self.units:
            raise ReviewError("UNIT_NOT_ASSIGNED")
        items = [self._reviewer_item(item) for item in self.items.values() if item["primarySourceUnitID"] == unit]
        return {"primarySourceUnitID": unit, "source": self.sources[unit],
                "authorizedContext": [self.sources[context] for context in self.contexts[unit]],
                "items": [{**item, "paragraphContexts": evidence_contexts(item, self.sources)} for item in items],
                "duplicateReviewGroups": [group for group in self.groups.values()
                                          if all(self.items[key]["primarySourceUnitID"] == unit for key in group["judgmentItemIDs"])]}

    def _reviewer_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Project one package item into its blinded reviewer-facing presentation."""

        rendered = deepcopy(item)
        rendered["reviewGuidance"] = self.target_guidance[item["operationalTarget"]["operationalID"]]
        for binding in self.endpoint_bindings.get(item["judgmentItemID"], []):
            endpoint = rendered["assertion"][binding["endpoint"]]
            endpoint.pop("exactNodeID", None)
            endpoint.pop("sourceArtifactID", None)
            endpoint["displayLabel"] = "Current paper"
        return rendered


def evidence_contexts(item: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Render complete intersecting paragraphs with exact code-point highlights.

    Blank lines delimit paragraphs. Each evidence occurrence remains distinct;
    multi-paragraph occurrences yield one bounded segment per paragraph.
    """

    contexts = []
    for ordinal, evidence in enumerate(item["evidenceOccurrences"], 1):
        text = sources[evidence["sourceUnitID"]]["text"]
        start, end = evidence["startOffsetInUnit"], evidence["endOffsetInUnit"]
        boundaries = [0] + [match.end() for match in re.finditer(r"\n[ \t]*\n", text)] + [len(text)]
        assertion = item["assertion"]
        labels = {"label": assertion.get("label")} if item["recordKind"] == "node" else {
            "source": assertion.get("sourceEndpoint", {}).get("label"), "target": assertion.get("targetEndpoint", {}).get("label")}
        for left, right in zip(boundaries, boundaries[1:]):
            if left >= end or right <= start:
                continue
            evidence_left, evidence_right = max(left, start), min(right, end)
            spans = [(evidence_left, evidence_right, "evidence")]
            for kind, label in labels.items():
                if isinstance(label, str) and label:
                    spans.extend((evidence_left + match.start(), evidence_left + match.end(), kind)
                                 for match in re.finditer(re.escape(label), text[evidence_left:evidence_right]))
            cuts = sorted({left, right, *(value for a, b, _ in spans for value in (a, b))})
            segments = [{"text": text[a:b], "highlights": [kind for x, y, kind in spans if x <= a and b <= y]}
                        for a, b in zip(cuts, cuts[1:])]
            contexts.append({"occurrence": ordinal, "sourceUnitID": evidence["sourceUnitID"],
                             "startOffsetInUnit": left, "endOffsetInUnit": right,
                             "renderingKind": "cited_evidence_paragraph",
                             "renderingLabel": f"Cited-evidence paragraph for evidence occurrence {ordinal}",
                             "segments": segments})
    return contexts
