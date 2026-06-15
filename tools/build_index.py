#!/usr/bin/env python3
"""Rebuild wiki/index.md from page frontmatter."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from wiki_common import PAGE_TYPES, WIKI, iter_wiki_pages, page_info, rel, today, write_text


def link_for(path: Path) -> str:
    return path.relative_to(WIKI).as_posix()


def render_index() -> str:
    pages = []
    for path in iter_wiki_pages(include_meta=False):
        if path.name in {"index.md", "log.md", "hot.md"}:
            continue
        info = page_info(path)
        pages.append(info)

    grouped = {ptype: [] for ptype in PAGE_TYPES}
    overview = []
    for info in pages:
        if info["path"].name == "overview.md":
            overview.append(info)
        elif info["type"] in grouped:
            grouped[info["type"]].append(info)

    lines = ["# Wiki Index", "", "## Overview"]
    if overview:
        for info in sorted(overview, key=lambda item: item["title"].lower()):
            summary = info["summary"] or "No summary."
            updated = info["updated"] or today()
            lines.append(f"- [{info['title']}]({link_for(info['path'])}) - {summary} Updated: {updated}")
    else:
        lines.append("- [Overview](overview.md) - Living synthesis of this vault.")

    for ptype, (heading, _) in PAGE_TYPES.items():
        lines.extend(["", f"## {heading}"])
        entries = sorted(grouped[ptype], key=lambda item: item["title"].lower())
        for info in entries:
            summary = info["summary"] or "No summary."
            updated = info["updated"] or today()
            lines.append(f"- [{info['title']}]({link_for(info['path'])}) - {summary} Updated: {updated}")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Report drift without writing.")
    args = parser.parse_args()

    index_path = WIKI / "index.md"
    expected = render_index()
    current = index_path.read_text(encoding="utf-8") if index_path.exists() else ""

    if args.check:
        if current == expected:
            print("index: OK")
            return 0
        print("index: DRIFT")
        diff = difflib.unified_diff(
            current.splitlines(),
            expected.splitlines(),
            fromfile=rel(index_path),
            tofile="generated-index",
            lineterm="",
        )
        print("\n".join(diff))
        return 1

    write_text(index_path, expected)
    print(f"rebuilt {rel(index_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
