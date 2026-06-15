#!/usr/bin/env python3
"""Shared helpers for the Codex-first LLM Wiki tools."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
META = ROOT / "meta"

PAGE_TYPES = {
    "source": ("Sources", "sources"),
    "entity": ("Entities", "entities"),
    "concept": ("Concepts", "concepts"),
    "project": ("Projects", "projects"),
    "question": ("Questions", "questions"),
    "synthesis": ("Syntheses", "syntheses"),
}

REQUIRED_DIRS = [
    ".agents/skills/wiki",
    ".agents/skills/wiki-ingest/references",
    ".agents/skills/wiki-query/references",
    ".agents/skills/wiki-lint",
    ".agents/skills/wiki-retrieve",
    "raw/articles",
    "raw/papers",
    "raw/meetings",
    "raw/journals",
    "raw/sessions",
    "wiki/sources",
    "wiki/entities",
    "wiki/concepts",
    "wiki/projects",
    "wiki/questions",
    "wiki/syntheses",
    "meta/retrieval",
    "meta/lint-reports",
    "tools",
]

REQUIRED_FILES = [
    "AGENTS.md",
    ".agents/skills/wiki/SKILL.md",
    ".agents/skills/wiki-ingest/SKILL.md",
    ".agents/skills/wiki-query/SKILL.md",
    ".agents/skills/wiki-lint/SKILL.md",
    ".agents/skills/wiki-retrieve/SKILL.md",
    "wiki/hot.md",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/overview.md",
    "meta/manifest.json",
    "tools/health.py",
    "tools/build_index.py",
    "tools/lint_links.py",
    "tools/retrieve.py",
    "tools/analyze_source.py",
    "tools/batch_ingest.py",
    "tools/ingest.py",
    "tools/ingest_codex_sessions.py",
    "tools/context_pack.py",
    "tools/audit_wiki_quality.py",
]


def now_iso() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def today() -> str:
    return _dt.date.today().isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str, fallback: str = "untitled") -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or fallback


def extract_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    block = text[4:end].strip()
    body = text[end + 4 :].lstrip("\n")
    return parse_simple_yaml(block), body


def parse_simple_yaml(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value in {"[]", ""}:
            data[key] = []
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                data[key] = []
            else:
                data[key] = [
                    item.strip().strip("'\"") for item in inner.split(",") if item.strip()
                ]
        else:
            data[key] = value.strip("'\"")
    return data


def dump_frontmatter(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key in [
        "title",
        "type",
        "summary",
        "status",
        "created",
        "updated",
        "tags",
        "sources",
        "confidence",
    ]:
        value = data.get(key)
        if isinstance(value, list):
            rendered = "[" + ", ".join(json.dumps(str(v), ensure_ascii=False) for v in value) + "]"
        else:
            rendered = json.dumps(str(value), ensure_ascii=False)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def iter_wiki_pages(include_meta: bool = True) -> list[Path]:
    pages = sorted(WIKI.rglob("*.md"))
    if include_meta:
        return pages
    return [p for p in pages if p.name not in {"index.md", "log.md", "hot.md"}]


def page_info(path: Path) -> dict[str, Any]:
    text = read_text(path)
    fm, body = extract_frontmatter(text)
    title = str(fm.get("title") or first_heading(body) or path.stem)
    ptype = str(fm.get("type") or infer_type(path))
    summary = str(fm.get("summary") or "").strip()
    updated = str(fm.get("updated") or "").strip()
    tags = fm.get("tags") if isinstance(fm.get("tags"), list) else []
    sources = fm.get("sources") if isinstance(fm.get("sources"), list) else []
    return {
        "path": path,
        "rel": rel(path),
        "frontmatter": fm,
        "body": body,
        "title": title,
        "type": ptype,
        "summary": summary,
        "updated": updated,
        "tags": tags,
        "sources": sources,
        "text": text,
    }


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def infer_type(path: Path) -> str:
    parts = path.relative_to(WIKI).parts
    if len(parts) == 1:
        return "meta"
    folder = parts[0]
    return {
        "sources": "source",
        "entities": "entity",
        "concepts": "concept",
        "projects": "project",
        "questions": "question",
        "syntheses": "synthesis",
    }.get(folder, "meta")


def source_type(path: Path) -> str:
    try:
        folder = path.relative_to(RAW).parts[0]
    except (ValueError, IndexError):
        return "unknown"
    return folder[:-1] if folder.endswith("s") else folder


def title_from_markdown(path: Path, text: str) -> str:
    fm, body = extract_frontmatter(text)
    if fm.get("title"):
        return str(fm["title"])
    heading = first_heading(body)
    if heading:
        return heading
    return path.stem.replace("-", " ").replace("_", " ").title()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text.lower())


def short_snippet(text: str, terms: list[str], size: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return ""
    lower = compact.lower()
    positions = [lower.find(t.lower()) for t in terms if lower.find(t.lower()) >= 0]
    start = max(min(positions) - size // 3, 0) if positions else 0
    snippet = compact[start : start + size].strip()
    if start > 0:
        snippet = "..." + snippet
    if start + size < len(compact):
        snippet += "..."
    return snippet


def append_log(operation: str, title: str, lines: list[str]) -> None:
    log = WIKI / "log.md"
    current = read_text(log) if log.exists() else "# Wiki Log\n"
    entry = [f"\n## {today()} {operation} | {title}"]
    entry.extend(lines)
    write_text(log, current.rstrip() + "\n" + "\n".join(entry) + "\n")
