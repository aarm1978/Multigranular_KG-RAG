"""Shared Publication artifact writes, extracted from the DEV durable writer."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Mapping
from .request_builder import canonical_json_file


def write_exact(path: Path, value: bytes) -> None:
    """Persist exact bytes and sync before subsequent semantic processing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def write_durable_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Persist the existing canonical JSON encoding with a trailing line feed."""
    write_exact(path, canonical_json_file(value))
