#!/usr/bin/env python3
"""Create a structured ingest plan for a raw source file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from source_plan import build_plan, plan_to_json
from wiki_common import RAW, write_text


def ensure_raw(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(RAW.resolve())
    except ValueError as exc:
        raise SystemExit(f"source must be under raw/: {path}") from exc
    if not resolved.is_file():
        raise SystemExit(f"source not found: {path}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Source file under raw/.")
    parser.add_argument("--output", "-o", help="Write plan JSON to this path.")
    args = parser.parse_args()

    source = ensure_raw(Path(args.source))
    payload = plan_to_json(build_plan(source))
    if args.output:
        write_text(Path(args.output), payload)
        print(f"wrote {args.output}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
