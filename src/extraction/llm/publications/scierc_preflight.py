"""Build the unfrozen Step 9 review candidate locally, with no network or dispatch."""

from __future__ import annotations

import json
from pathlib import Path
import tarfile

from .scierc_external_anchor import (
    ARCHIVE_PATH, PROJECT_ROOT, SciERCAnchorError, build_run_manifest,
    canonical_json, parse_processed_document, sha256_bytes, source_freeze,
)
from .publication_artifacts import write_exact


OUTPUT = PROJECT_ROOT / "data/curation/papers/m2/scierc_step9_preflight"
# Fixed, bounded locators observed during the authorized serialization check.
# No frequency analysis or example selection for model prompts is performed.
DIRECTION_LOCATORS = {
    "train": [(1, 1, 1), (1, 1, 2), (2, 0, 0), (2, 4, 0), (3, 3, 0)],
    "dev": [(1, 0, 0), (1, 0, 2), (1, 2, 1), (3, 6, 0), (5, 1, 0)],
}


def directionality_record() -> dict:
    """Verify only ten fixed train/dev direct-relation serialization records.

    Archive verification occurs in the official candidate builder before this
    helper is called by main. Each split is independently hash-checked here.
    Text and annotations remain inside ignored source storage.
    """

    records = []
    authority = source_freeze()
    with tarfile.open(ARCHIVE_PATH, "r:gz") as archive:
        for split, locators in DIRECTION_LOCATORS.items():
            spec = authority["splits"][split]
            payload = archive.extractfile(spec["path"]).read()
            if sha256_bytes(payload) != spec["sha256"]:
                raise SciERCAnchorError("DIRECTION_CHECK_SPLIT_HASH_MISMATCH")
            lines = payload.splitlines()
            for line_number, sentence_index, relation_index in locators:
                row = json.loads(lines[line_number - 1])
                document = parse_processed_document(row)
                relation = row["relations"][sentence_index][relation_index]
                records.append({"split": split, "splitSha256": spec["sha256"],
                    "lineNumber": line_number, "documentID": document.document_id,
                    "sentenceIndex": sentence_index, "relationIndex": relation_index,
                    "relationType": relation[4], "firstSpan": relation[:2],
                    "secondSpan": relation[2:4], "recordSha256": sha256_bytes(canonical_json(row))})
    return {"status": "bounded_serialization_check_only", "providerModelCalls": 0,
        "testGoldAccessed": False, "records": records,
        "interpretation": "first endpoint = source/B; second endpoint = target/A; EVALUATE-FOR measure or criterion -> evaluated entity",
        "semanticAuthority": "guideline 1.2 for four directed labels; researcher definition for EVALUATE-FOR",
        "limits": "not a frequency, performance, or semantic-policy analysis; no examples enter prompt"}


def main() -> None:
    """Write reviewable metadata only; never authorize or invoke inference."""

    manifest = build_run_manifest()
    direction = directionality_record()
    manifest["directionalityRecordSha256"] = sha256_bytes(canonical_json(direction))
    manifest["preflightBuilderSha256"] = sha256_bytes(Path(__file__).read_bytes())
    manifest["sourceRecoveryRecordSha256"] = sha256_bytes((OUTPUT / "scierc_external_anchor_source_recovery_v0.1.0.json").read_bytes())
    manifest["decisionRecordSha256"] = sha256_bytes((PROJECT_ROOT / "docs/scierc_step9_preflight_v0.2.0.md").read_bytes())
    manifest.pop("manifestSha256")
    manifest["manifestSha256"] = sha256_bytes(canonical_json(manifest))
    for name, value in [("scierc_preflight_candidate_v0.2.0.json", manifest),
                        ("scierc_directionality_check_v0.2.0.json", direction)]:
        write_exact(OUTPUT / name, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps({"logicalRequestCount": manifest["logicalRequestCount"],
        "manifestSha256": manifest["manifestSha256"], "status": manifest["status"],
        "accounting": manifest["preflightAccounting"]}, sort_keys=True))


if __name__ == "__main__":
    main()
