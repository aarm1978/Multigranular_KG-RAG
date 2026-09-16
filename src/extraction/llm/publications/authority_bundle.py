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


V014 = PublicationAuthorityBundle(
    "publication-semantic-v0.1.4",
    PROJECT_ROOT / "schemas/publication_candidate_output.schema.json",
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml",
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.7.txt",
)
V015 = PublicationAuthorityBundle(
    "publication-semantic-v0.1.5",
    PROJECT_ROOT / "schemas/publication_candidate_output_v0.1.1.json",
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml",
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.8.txt",
)


def bundle_for_identifier(identifier: str) -> PublicationAuthorityBundle:
    """Return one recognized immutable authority bundle or fail closed."""

    bundles = {V014.identifier: V014, V015.identifier: V015}
    try:
        return bundles[identifier]
    except KeyError as exc:
        raise ValueError(f"unknown Publication authority bundle: {identifier}") from exc
