"""Select immutable Publication semantic authority bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class PublicationAuthorityBundle:
    """Paths and identity for one versioned Publication semantic contract."""

    identifier: str
    candidate_schema_path: Path
    target_inventory_path: Path
    prompt_path: Path
    prompt_version: str
    evidence_contract_path: Path
    evaluation_contract_path: Path
    annotation_contract_path: Path


V014 = PublicationAuthorityBundle(
    "publication-semantic-v0.1.4",
    PROJECT_ROOT / "schemas/publication_candidate_output.schema.json",
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml",
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.7.txt",
    "publication-development-0.1.7",
    PROJECT_ROOT / "docs/publication_evidence_validation_contract.md",
    PROJECT_ROOT / "docs/publication_evaluation_matching_contract.md",
    PROJECT_ROOT / "docs/publication_annotation_adjudication_guidelines.md",
)
V015 = PublicationAuthorityBundle(
    "publication-semantic-v0.1.5",
    PROJECT_ROOT / "schemas/publication_candidate_output_v0.1.1.json",
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml",
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.8.txt",
    "publication-development-0.1.8",
    PROJECT_ROOT / "docs/publication_evidence_validation_contract_v0.1.5.md",
    PROJECT_ROOT / "docs/publication_evaluation_matching_contract_v0.1.5.md",
    PROJECT_ROOT / "docs/publication_annotation_adjudication_guidelines_v0.1.5.md",
)
V015_SCHEMA012 = PublicationAuthorityBundle(
    "publication-semantic-v0.1.5-schema-v0.1.2",
    PROJECT_ROOT / "schemas/publication_candidate_output_v0.1.2.json",
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml",
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.8.txt",
    "publication-development-0.1.8",
    PROJECT_ROOT / "docs/publication_evidence_validation_contract_v0.1.5_schema_v0.1.2.md",
    PROJECT_ROOT / "docs/publication_evaluation_matching_contract_v0.1.5_schema_v0.1.2.md",
    PROJECT_ROOT / "docs/publication_annotation_adjudication_guidelines_v0.1.5.md",
)
V015_SCHEMA013 = PublicationAuthorityBundle(
    "publication-semantic-v0.1.5-schema-v0.1.3",
    PROJECT_ROOT / "schemas/publication_candidate_output_v0.1.3.json",
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml",
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.8.txt",
    "publication-development-0.1.8",
    PROJECT_ROOT / "docs/publication_evidence_validation_contract_v0.1.5_schema_v0.1.3.md",
    PROJECT_ROOT / "docs/publication_evaluation_matching_contract_v0.1.5_schema_v0.1.3.md",
    PROJECT_ROOT / "docs/publication_annotation_adjudication_guidelines_v0.1.5.md",
)

REGISTERED_BUNDLES = (V014, V015, V015_SCHEMA012, V015_SCHEMA013)
V015_SEMANTIC_FAMILY = (V015, V015_SCHEMA012, V015_SCHEMA013)


def is_v015_semantic_family(bundle: PublicationAuthorityBundle) -> bool:
    """Return whether a bundle uses the frozen v0.1.5 target universe."""

    return any(bundle is canonical for canonical in V015_SEMANTIC_FAMILY)


def bundle_for_identifier(identifier: str) -> PublicationAuthorityBundle:
    """Return one recognized immutable authority bundle or fail closed."""

    bundles = {bundle.identifier: bundle for bundle in REGISTERED_BUNDLES}
    try:
        return bundles[identifier]
    except KeyError as exc:
        raise ValueError(f"unknown Publication authority bundle: {identifier}") from exc
