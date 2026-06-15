#!/usr/bin/env python3
"""Check Markdown links, wikilinks, index drift, and orphans."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from wiki_common import META, ROOT, WIKI, append_log, dump_json, iter_wiki_pages, now_iso, page_info, rel, today, write_text

MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")


def normalize_target(page: Path, target: str) -> Path | None:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    target = target.split("#", 1)[0].strip()
    if not target:
        return None
    return (page.parent / target).resolve()


def wikilink_target(name: str, title_map: dict[str, Path], stem_map: dict[str, Path]) -> Path | None:
    key = name.strip().lower()
    if key in title_map:
        return title_map[key]
    slug = key.replace(" ", "-")
    if slug in stem_map:
        return stem_map[slug]
    return None


def analyze() -> dict:
    pages = iter_wiki_pages()
    title_map: dict[str, Path] = {}
    stem_map: dict[str, Path] = {}
    infos = {}
    duplicate_titles: dict[str, list[str]] = {}

    for page in pages:
        info = page_info(page)
        infos[page] = info
        key = f"{info['type']}::{info['title'].lower()}"
        if key in title_map:
            duplicate_titles.setdefault(key, [rel(title_map[key])]).append(rel(page))
        else:
            title_map[key] = page
        stem_map[page.stem.lower()] = page

    outbound: dict[Path, set[Path]] = {page: set() for page in pages}
    broken = []

    for page in pages:
        text = page.read_text(encoding="utf-8")
        for match in MD_LINK_RE.finditer(text):
            raw = match.group(1)
            target = normalize_target(page, raw)
            if target is None:
                continue
            if target.exists():
                try:
                    if target.relative_to(ROOT).as_posix().startswith("wiki/"):
                        outbound[page].add(target)
                except ValueError:
                    pass
            else:
                broken.append({"page": rel(page), "target": raw, "type": "markdown"})
        for match in WIKILINK_RE.finditer(text):
            raw = match.group(1)
            target = wikilink_target(raw, title_map, stem_map)
            if target:
                outbound[page].add(target)
            else:
                broken.append({"page": rel(page), "target": raw, "type": "wikilink"})

    inbound: dict[Path, set[Path]] = {page: set() for page in pages}
    for src, targets in outbound.items():
        for target in targets:
            if target in inbound:
                inbound[target].add(src)

    orphans = []
    for page in pages:
        if page.name in {"index.md", "log.md", "hot.md", "overview.md"}:
            continue
        if not inbound[page]:
            orphans.append(rel(page))

    missing_frontmatter = [
        rel(page)
        for page, info in infos.items()
        if page.name not in {"index.md", "log.md"} and not info["frontmatter"]
    ]

    source_pages_without_sources = [
        rel(page)
        for page, info in infos.items()
        if info["type"] == "source" and not info.get("sources")
    ]

    pages_payload = {}
    for page in pages:
        pages_payload[rel(page)] = {
            "title": infos[page]["title"],
            "outbound": sorted(rel(p) for p in outbound[page]),
            "inbound": sorted(rel(p) for p in inbound[page]),
            "broken": [item for item in broken if item["page"] == rel(page)],
        }

    return {
        "schema_version": 1,
        "built_at": now_iso(),
        "ok": not broken and not missing_frontmatter,
        "broken_links": broken,
        "orphans": sorted(orphans),
        "duplicate_titles": duplicate_titles,
        "missing_frontmatter": missing_frontmatter,
        "source_pages_without_sources": source_pages_without_sources,
        "pages": pages_payload,
    }


def write_report(result: dict) -> Path:
    report_path = META / "lint-reports" / f"{today()}-lint.md"
    lines = [
        f"# Wiki Lint Report {today()}",
        "",
        f"- Status: {'PASS' if result['ok'] else 'FAIL'}",
        f"- Broken links: {len(result['broken_links'])}",
        f"- Orphans: {len(result['orphans'])}",
        f"- Duplicate titles: {len(result['duplicate_titles'])}",
        f"- Missing frontmatter: {len(result['missing_frontmatter'])}",
        "",
        "## Broken Links",
    ]
    if result["broken_links"]:
        for item in result["broken_links"]:
            lines.append(f"- `{item['page']}` -> `{item['target']}` ({item['type']})")
    else:
        lines.append("- None")
    lines.extend(["", "## Orphans"])
    if result["orphans"]:
        for item in result["orphans"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- None")
    lines.extend(["", "## Duplicate Titles"])
    if result["duplicate_titles"]:
        for title, paths in sorted(result["duplicate_titles"].items()):
            lines.append(f"- `{title}`: {', '.join(f'`{p}`' for p in paths)}")
    else:
        lines.append("- None")
    lines.extend(["", "## Missing Frontmatter"])
    if result["missing_frontmatter"]:
        for item in result["missing_frontmatter"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- None")
    write_text(report_path, "\n".join(lines) + "\n")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-cache", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    result = analyze()
    report_path = write_report(result)
    if args.write_cache:
        dump_json(
            META / "link-index.json",
            {
                "schema_version": result["schema_version"],
                "built_at": result["built_at"],
                "pages": result["pages"],
            },
        )
    if args.report or args.write_cache:
        append_log(
            "lint",
            "Wiki link lint",
            [
                f"- Broken links: {len(result['broken_links'])}",
                f"- Orphans: {len(result['orphans'])}",
                f"- Report: `{rel(report_path)}`",
            ],
        )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"lint: {'PASS' if result['ok'] else 'FAIL'}")
        print(f"broken links: {len(result['broken_links'])}")
        print(f"orphans: {len(result['orphans'])}")
        print(f"duplicate titles: {len(result['duplicate_titles'])}")
        print(f"missing frontmatter: {len(result['missing_frontmatter'])}")
        print(f"report: {rel(report_path)}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
