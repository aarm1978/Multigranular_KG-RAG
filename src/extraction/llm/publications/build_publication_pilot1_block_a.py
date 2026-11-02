"""Command-line entry point for Publication Pilot 1 Block A.

With no reviewed CSV, this command writes deterministic infrastructure and stops at
the human-screening leakage-control gate.  Pass ``--reviewed-worklist`` only after a
human expert has completed the generated worklist.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.extraction.llm.publications.publication_pilot1_block_a import (
    compile_reviewed_worklist,
    materialize_infrastructure,
)


def main() -> int:
    """Generate infrastructure and optionally compile human-reviewed screening."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--reviewed-worklist", type=Path)
    args = parser.parse_args()
    report = materialize_infrastructure(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.reviewed_worklist is None:
        print("BLOCK_A_HUMAN_SCREENING_REQUIRED")
        return 0
    compiled = compile_reviewed_worklist(args.root, args.reviewed_worklist)
    print(json.dumps(compiled, indent=2, sort_keys=True))
    print("PUBLICATION_PILOT1_BLOCK_A_DEFERRED_ROUTING_CORRECTION_READY_FOR_INDEPENDENT_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
