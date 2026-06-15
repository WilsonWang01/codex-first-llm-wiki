#!/usr/bin/env python3
"""Health checks for the Codex-first LLM Wiki."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wiki_common import RAW, REQUIRED_DIRS, REQUIRED_FILES, ROOT, WIKI, extract_frontmatter, iter_wiki_pages, load_json, rel, sha256_file


def check(quick: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    for item in REQUIRED_DIRS:
        if not (ROOT / item).is_dir():
            errors.append(f"missing directory: {item}")

    for item in REQUIRED_FILES:
        if not (ROOT / item).is_file():
            errors.append(f"missing file: {item}")

    manifest_path = ROOT / "meta/manifest.json"
    manifest = {}
    try:
        manifest = load_json(manifest_path, {})
        if not isinstance(manifest, dict):
            errors.append("meta/manifest.json must be a JSON object")
        elif manifest.get("schema_version") != 1:
            warnings.append("meta/manifest.json schema_version is not 1")
        elif not isinstance(manifest.get("sources", {}), dict):
            errors.append("meta/manifest.json sources must be an object")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"invalid manifest json: {exc}")

    wiki_pages = iter_wiki_pages()
    for page in wiki_pages:
        if page.stat().st_size == 0:
            errors.append(f"empty wiki page: {rel(page)}")
        if page.name not in {"index.md", "log.md"}:
            text = page.read_text(encoding="utf-8")
            fm, _ = extract_frontmatter(text)
            if not fm:
                warnings.append(f"missing frontmatter: {rel(page)}")
            elif not fm.get("summary"):
                warnings.append(f"missing summary: {rel(page)}")

    if not quick:
        if isinstance(manifest, dict):
            sources = manifest.get("sources", {})
            if isinstance(sources, dict):
                raw_sources_seen = set()
                manifest_pages_seen = set()
                for source_rel, entry in sorted(sources.items()):
                    source_path = ROOT / source_rel
                    raw_sources_seen.add(source_rel)
                    if not source_path.exists():
                        errors.append(f"manifest source missing: {source_rel}")
                    elif source_path.is_file() and entry.get("hash") and sha256_file(source_path) != entry["hash"]:
                        warnings.append(f"manifest source hash drift: {source_rel}")
                    for key in ["pages_created", "pages_updated"]:
                        values = entry.get(key, [])
                        if not isinstance(values, list):
                            errors.append(f"manifest {source_rel} {key} must be a list")
                            continue
                        for page_rel in values:
                            manifest_pages_seen.add(str(page_rel))
                            page_path = ROOT / str(page_rel)
                            if not page_path.exists():
                                errors.append(f"manifest page missing: {source_rel} -> {page_rel}")
                for raw_path in sorted(RAW.rglob("*.md")):
                    raw_rel = rel(raw_path)
                    if raw_rel not in raw_sources_seen:
                        warnings.append(f"raw markdown not in manifest: {raw_rel}")
                for page in iter_wiki_pages(include_meta=False):
                    if page.name in {"overview.md"}:
                        continue
                    info = extract_frontmatter(page.read_text(encoding="utf-8"))[0]
                    if info.get("type") == "source" and rel(page) not in manifest_pages_seen:
                        warnings.append(f"source wiki page not in manifest outputs: {rel(page)}")

        for item in ["wiki/index.md", "wiki/hot.md", "wiki/log.md"]:
            path = ROOT / item
            if path.exists() and path.stat().st_size < 20:
                warnings.append(f"suspiciously short file: {item}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "wiki_pages": len(wiki_pages),
        "root": str(ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Skip slower content checks.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()

    result = check(quick=args.quick)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if result["ok"] else "FAIL"
        print(f"health: {status}")
        print(f"root: {result['root']}")
        print(f"wiki pages: {result['wiki_pages']}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
