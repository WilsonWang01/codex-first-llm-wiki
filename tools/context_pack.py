#!/usr/bin/env python3
"""Build a low-token context pack preview for wiki queries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from retrieve import retrieve
from wiki_common import WIKI, page_info, read_text, rel


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4) if text else 0


def file_entry(path: Path, role: str, include_text: bool = False) -> dict[str, Any]:
    text = read_text(path) if path.exists() else ""
    entry: dict[str, Any] = {
        "role": role,
        "path": rel(path),
        "exists": path.exists(),
        "chars": len(text),
        "estimated_tokens": estimate_tokens(text),
    }
    if include_text:
        entry["text"] = text
    return entry


def build_context_pack(query: str, mode: str = "normal", top: int = 5, include_pages: bool = False) -> dict[str, Any]:
    entries: list[dict[str, Any]] = [
        file_entry(WIKI / "hot.md", "hot-cache", include_text=include_pages),
        file_entry(WIKI / "index.md", "index", include_text=include_pages),
    ]
    candidates: list[dict[str, Any]] = []

    if mode in {"normal", "deep"} and query:
        candidates = retrieve(query, top=top)
        for candidate in candidates:
            entries.append(
                {
                    "role": "retrieval-snippet",
                    "path": candidate["path"],
                    "title": candidate["title"],
                    "section": candidate["section"],
                    "chunk_id": candidate["chunk_id"],
                    "score": candidate["score"],
                    "snippet": candidate["snippet"],
                    "chars": len(candidate["snippet"]),
                    "estimated_tokens": estimate_tokens(candidate["snippet"]),
                }
            )

    if mode == "deep":
        seen = set()
        for candidate in candidates:
            if candidate["path"] in seen:
                continue
            seen.add(candidate["path"])
            path = WIKI.parent / candidate["path"]
            if not path.exists():
                continue
            info = page_info(path)
            text = info["text"] if include_pages else ""
            entries.append(
                {
                    "role": "full-page" if include_pages else "page-candidate",
                    "path": candidate["path"],
                    "title": info["title"],
                    "summary": info["summary"],
                    "chars": len(info["text"]),
                    "estimated_tokens": estimate_tokens(info["text"]),
                    **({"text": text} if include_pages else {}),
                }
            )

    total_tokens = sum(int(entry.get("estimated_tokens", 0)) for entry in entries)
    return {
        "query": query,
        "mode": mode,
        "strategy": "hot-index-chunk-bm25",
        "entry_count": len(entries),
        "estimated_tokens": total_tokens,
        "entries": entries,
        "guidance": {
            "quick": "Read only hot.md and index.md.",
            "normal": "Read hot.md, index.md, and retrieval snippets before opening full pages.",
            "deep": "Use page candidates for full-page reads only when synthesis requires it.",
        }[mode],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Context Pack: {payload['query'] or '(no query)'}",
        "",
        f"- Mode: `{payload['mode']}`",
        f"- Strategy: `{payload['strategy']}`",
        f"- Estimated tokens: `{payload['estimated_tokens']}`",
        "",
        "## Entries",
    ]
    for entry in payload["entries"]:
        label = entry.get("title") or entry["path"]
        detail = entry.get("section") or entry.get("role")
        lines.append(
            f"- `{entry['role']}` [{label}]({entry['path']})"
            f" - {detail}; ~{entry.get('estimated_tokens', 0)} tokens"
        )
    lines.extend(["", f"## Guidance", "", payload["guidance"]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--mode", choices=["quick", "normal", "deep"], default="normal")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--include-pages", action="store_true", help="Include full text for entries when requested.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = build_context_pack(args.query, mode=args.mode, top=args.top, include_pages=args.include_pages)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
