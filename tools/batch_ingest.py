#!/usr/bin/env python3
"""Scan raw sources, report manifest deltas, and batch ingest changed files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from build_index import render_index
from ingest import ingest
from wiki_common import META, RAW, WIKI, append_log, dump_json, load_json, rel, sha256_file, write_text


DEFAULT_GLOBS = ["**/*.md", "**/*.markdown", "**/*.txt"]


def iter_sources(patterns: list[str]) -> list[Path]:
    seen = set()
    out = []
    for pattern in patterns:
        for path in RAW.glob(pattern):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            key = path.resolve()
            if key in seen:
                continue
            seen.add(key)
            out.append(path)
    return sorted(out)


def delta(patterns: list[str]) -> dict:
    manifest = load_json(META / "manifest.json", {"schema_version": 1, "sources": {}})
    known = manifest.get("sources", {})
    result = {"new": [], "modified": [], "unchanged": [], "errors": []}
    for path in iter_sources(patterns):
        source_rel = rel(path)
        try:
            digest = sha256_file(path)
        except OSError as exc:
            result["errors"].append({"source": source_rel, "error": str(exc)})
            continue
        entry = known.get(source_rel)
        item = {"source": source_rel, "hash": digest, "title": path.stem}
        if not entry:
            result["new"].append(item)
        elif entry.get("hash") != digest:
            result["modified"].append(item)
        else:
            result["unchanged"].append(item)
    result["counts"] = {key: len(result[key]) for key in ["new", "modified", "unchanged", "errors"]}
    return result


def ingest_delta(patterns: list[str], force: bool = False, limit: int | None = None) -> dict:
    d = delta(patterns)
    candidates = [*(d["new"]), *(d["modified"])]
    if force:
        candidates = [*candidates, *d["unchanged"]]
    if limit is not None:
        candidates = candidates[:limit]

    results = []
    for item in candidates:
        try:
            results.append(ingest(Path(item["source"]), force=force))
        except Exception as exc:  # noqa: BLE001
            results.append({"status": "error", "source": item["source"], "error": str(exc)})

    write_text(WIKI / "index.md", render_index())
    append_log(
        "batch-ingest",
        "Raw source delta",
        [
            f"- New: {len(d['new'])}",
            f"- Modified: {len(d['modified'])}",
            f"- Unchanged: {len(d['unchanged'])}",
            f"- Processed: {len(results)}",
        ],
    )
    return {"delta": d, "processed": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="append", dest="patterns", help="Raw glob to scan. Can repeat.")
    parser.add_argument("--ingest", action="store_true", help="Ingest new/modified files.")
    parser.add_argument("--force", action="store_true", help="Also process unchanged files.")
    parser.add_argument("--limit", type=int, help="Maximum number of files to ingest.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    patterns = args.patterns or DEFAULT_GLOBS
    payload = ingest_delta(patterns, force=args.force, limit=args.limit) if args.ingest else delta(patterns)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        d = payload["delta"] if args.ingest else payload
        print("raw delta:")
        for key in ["new", "modified", "unchanged", "errors"]:
            print(f"- {key}: {len(d[key])}")
        if args.ingest:
            print(f"processed: {len(payload['processed'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
