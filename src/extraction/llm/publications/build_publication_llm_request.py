"""Build one deterministic approved-development Publication extraction request."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.request_builder import (  # noqa: E402
    RequestBuildError,
    build_development_request,
    canonical_json_file,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the publication-specific development request CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-unit-id", required=True)
    parser.add_argument("--operational-target", action="append", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Build and write one canonical development request."""

    args = build_argument_parser().parse_args(argv)
    try:
        request = build_development_request(
            args.source_unit_id, args.operational_target, run_id=args.run_id
        )
        output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json_file(request))
    except (OSError, KeyError, TypeError, RequestBuildError) as exc:
        print(f"publication request build failed: {exc}", file=sys.stderr)
        return 1
    print(f"request ID: {request['requestID']}")
    print(f"request SHA-256: {request['requestInputSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
