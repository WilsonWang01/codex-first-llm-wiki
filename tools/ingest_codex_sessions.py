#!/usr/bin/env python3
"""Import Codex session JSONL files into raw/sessions and optionally ingest them."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from build_index import render_index
from ingest import ingest
from wiki_common import RAW, WIKI, rel, sha256_file, short_snippet, slugify, today, tokenize, write_text


DEFAULT_SESSION_DIRS = [
    Path.home() / ".codex/sessions",
    Path.home() / ".codex/projects",
]

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{8,})"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]


def redact(text: str) -> str:
    redacted = text
    redacted = SECRET_PATTERNS[0].sub(r"\1=[REDACTED]", redacted)
    redacted = SECRET_PATTERNS[1].sub("[REDACTED_EMAIL]", redacted)
    redacted = re.sub(r"/Users/[^/\s]+", "/Users/[REDACTED_USER]", redacted)
    return redacted


def iter_session_files(paths: list[Path]) -> list[Path]:
    out = []
    for base in paths:
        base = base.expanduser()
        if base.is_file() and base.suffix in {".jsonl", ".json"}:
            out.append(base)
        elif base.is_dir():
            out.extend(sorted(base.rglob("*.jsonl")))
            out.extend(sorted(base.rglob("*.json")))
    return sorted(set(p.resolve() for p in out))


def text_from_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
        return "\n".join(parts)
    if isinstance(content, dict):
        for key in ["text", "content", "message"]:
            if isinstance(content.get(key), str):
                return content[key]
    return ""


def normalize_record(record: dict[str, Any]) -> dict[str, Any] | None:
    role = str(record.get("role") or record.get("type") or record.get("kind") or "").lower()
    text = text_from_content(record.get("content") or record.get("message") or record.get("text"))
    tool = record.get("tool") or record.get("tool_name") or record.get("name")
    timestamp = str(record.get("timestamp") or record.get("created_at") or "")
    if "user" in role:
        return {"role": "user", "text": redact(text), "timestamp": timestamp}
    if "assistant" in role or role in {"agent", "model"}:
        return {"role": "assistant", "text": redact(text), "timestamp": timestamp}
    if "tool" in role or tool:
        return {"role": "tool", "tool": str(tool or "unknown"), "text": redact(text), "timestamp": timestamp}
    if text:
        return {"role": role or "record", "text": redact(text), "timestamp": timestamp}
    return None


def read_session(path: Path) -> list[dict[str, Any]]:
    records = []
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            raw_records = data
        elif isinstance(data, dict):
            raw_records = data.get("messages") or data.get("records") or [data]
        else:
            raw_records = []
        for item in raw_records:
            if isinstance(item, dict):
                normalized = normalize_record(item)
                if normalized:
                    records.append(normalized)
        return records

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            normalized = normalize_record(item)
            if normalized:
                records.append(normalized)
    return records


def record_text(record: dict[str, Any]) -> str:
    if record["role"] == "tool":
        return f"{record.get('tool', '')} {record.get('text', '')}".strip()
    return str(record.get("text", ""))


def session_score(path: Path, records: list[dict[str, Any]], query: str) -> float:
    if not query:
        return 0.0
    terms = tokenize(query)
    if not terms:
        return 0.0
    haystack_title = f"{path.name} {path.parent.name}".lower()
    score = 0.0
    for term in terms:
        if term in haystack_title:
            score += 3.0
    for record in records:
        text = record_text(record).lower()
        if not text:
            continue
        hits = sum(1 for term in terms if term in text)
        if hits:
            weight = 2.0 if record["role"] == "user" else 1.0
            score += hits * weight
    return round(score, 4)


def filter_records_for_query(records: list[dict[str, Any]], query: str, window: int = 1) -> list[dict[str, Any]]:
    terms = tokenize(query)
    if not terms:
        return records
    selected_indexes: set[int] = set()
    for idx, record in enumerate(records):
        text = record_text(record).lower()
        if any(term in text for term in terms):
            for offset in range(-window, window + 1):
                target = idx + offset
                if 0 <= target < len(records):
                    selected_indexes.add(target)
    if not selected_indexes:
        return []
    return [records[idx] for idx in sorted(selected_indexes)]


def query_match_summary(path: Path, records: list[dict[str, Any]], query: str) -> dict[str, Any]:
    score = session_score(path, records, query)
    terms = tokenize(query)
    snippets = []
    for record in records:
        text = record_text(record)
        if text and any(term in text.lower() for term in terms):
            snippets.append(short_snippet(text, terms, size=180))
        if len(snippets) >= 3:
            break
    return {
        "path": str(path),
        "score": score,
        "records": len(records),
        "snippets": snippets,
    }


def summarize_session(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    users = [r for r in records if r["role"] == "user" and r.get("text")]
    assistants = [r for r in records if r["role"] == "assistant" and r.get("text")]
    tools = sorted({r.get("tool", "unknown") for r in records if r["role"] == "tool"})
    first_user = users[0]["text"][:240] if users else ""
    last_user = users[-1]["text"][:240] if users else ""
    title_seed = first_user or path.stem
    return {
        "title": f"Codex Session - {title_seed[:80]}",
        "summary": f"Codex session with {len(users)} user turns, {len(assistants)} assistant turns, and {len(tools)} tool types.",
        "first_user": first_user,
        "last_user": last_user,
        "tool_names": tools,
        "record_count": len(records),
    }


def render_raw_session(path: Path, records: list[dict[str, Any]], query: str = "", selected_count: int | None = None) -> str:
    summary = summarize_session(path, records)
    source_hash = sha256_file(path)
    lines = [
        "---",
        f"title: {json.dumps(summary['title'], ensure_ascii=False)}",
        f"summary: {json.dumps(summary['summary'], ensure_ascii=False)}",
        "tags: [codex-session, agent-history]",
        "concepts: [codex-session, agent-history]",
        "---",
        "",
        f"# {summary['title']}",
        "",
        "## Summary",
        "",
        summary["summary"],
        "",
        "## Key Claims",
        "",
        f"- First user request: {summary['first_user'] or 'Unknown.'}",
        f"- Last user request: {summary['last_user'] or 'Unknown.'}",
        f"- Tool types observed: {', '.join(summary['tool_names']) if summary['tool_names'] else 'none'}",
        "",
        "## Entities",
        "",
        "- Codex",
        "",
        "## Concepts",
        "",
        "- codex-session",
        "- agent-history",
        "",
        "## Connections",
        "",
        "- This source preserves a redacted session summary for future knowledge maintenance.",
        "",
        "## Source Metadata",
        "",
        f"- Original path: `{redact(str(path))}`",
        f"- Original sha256: `{source_hash}`",
        f"- Imported: `{today()}`",
        f"- Query filter: `{redact(query) if query else 'none'}`",
        f"- Selected records: `{selected_count if selected_count is not None else len(records)}`",
        "",
        "## Redacted Transcript",
        "",
    ]
    for idx, record in enumerate(records, start=1):
        if record["role"] == "tool":
            body = f"tool={record.get('tool', 'unknown')}"
        else:
            body = record.get("text", "")
        if not body:
            continue
        lines.extend([f"### {idx}. {record['role']}", "", body[:1200], ""])
    return "\n".join(lines).rstrip() + "\n"


def import_session(path: Path, ingest_wiki: bool = False, force: bool = False, query: str = "") -> dict[str, Any]:
    records = read_session(path)
    if not records:
        return {"status": "skipped", "source": str(path), "reason": "no readable records"}
    selected_records = filter_records_for_query(records, query) if query else records
    if query and not selected_records:
        return {"status": "skipped", "source": str(path), "reason": "no query-relevant records"}
    summary = summarize_session(path, records)
    slug = slugify(f"{path.stem}-{summary['first_user']}", fallback=path.stem)[:80]
    target = RAW / "sessions" / f"codex-{today()}-{slug}.md"
    write_text(target, render_raw_session(path, selected_records, query=query, selected_count=len(selected_records)))
    result: dict[str, Any] = {
        "status": "imported",
        "raw": rel(target),
        "records": len(records),
        "selected_records": len(selected_records),
        "query": query,
    }
    if ingest_wiki:
        ingest_result = ingest(target, force=force)
        write_text(WIKI / "index.md", render_index())
        result["ingest"] = ingest_result
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-file", action="append", help="Specific Codex session JSON/JSONL file.")
    parser.add_argument("--session-dir", action="append", help="Directory to scan for Codex sessions.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--query", help="Rank sessions by query and import only matching transcript windows.")
    parser.add_argument("--dry-run", action="store_true", help="Show ranked sessions without importing.")
    parser.add_argument("--ingest", action="store_true", help="Also ingest imported raw session summaries into wiki.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths = [Path(p) for p in args.session_file or []]
    paths.extend(Path(p) for p in args.session_dir or [])
    if not paths:
        paths = DEFAULT_SESSION_DIRS
    all_files = iter_session_files(paths)
    ranked = []
    if args.query:
        for path in all_files:
            records = read_session(path)
            if not records:
                continue
            summary = query_match_summary(path, records, args.query)
            if summary["score"] > 0:
                ranked.append(summary)
        ranked = sorted(ranked, key=lambda item: (-item["score"], item["path"]))[: args.limit]
        files = [Path(item["path"]) for item in ranked]
    else:
        files = all_files[: args.limit]

    if args.dry_run:
        results = []
    else:
        results = [import_session(path, ingest_wiki=args.ingest, force=args.force, query=args.query or "") for path in files]
    payload = {
        "searched": [str(p) for p in paths],
        "query": args.query or "",
        "ranked": ranked,
        "count": len(results),
        "results": results,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"sessions processed: {len(results)}")
        for result in results:
            print(f"- {result['status']}: {result.get('raw') or result.get('source')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
