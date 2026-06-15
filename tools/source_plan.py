#!/usr/bin/env python3
"""Build and validate structured ingest plans for raw source files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from wiki_common import extract_frontmatter, read_text, rel, slugify, title_from_markdown, tokenize


PLAN_SCHEMA_VERSION = 1


def first_paragraph(body: str, limit: int = 260) -> str:
    body = re.sub(r"^#.+$", "", body, flags=re.MULTILINE).strip()
    for block in re.split(r"\n\s*\n", body):
        clean = re.sub(r"\s+", " ", block).strip()
        if clean:
            return clean[:limit]
    return "No summary available."


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def unique(values: list[str], limit: int | None = None) -> list[str]:
    seen = set()
    out = []
    for value in values:
        clean = re.sub(r"\s+", " ", str(value)).strip()
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
        if limit and len(out) >= limit:
            break
    return out


def extract_section_items(body: str, heading: str, limit: int = 10) -> list[str]:
    pattern = re.compile(
        rf"^##+\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##+\s+|\Z)",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(body)
    if not match:
        return []
    lines = []
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if line.startswith(("- ", "* ")):
            lines.append(line[2:].strip())
        elif line and not line.startswith("#"):
            lines.append(line)
    return unique(lines, limit)


def concepts_from_frontmatter(fm: dict[str, Any]) -> list[str]:
    return unique([*as_list(fm.get("tags")), *as_list(fm.get("concepts"))], 8)


def infer_concepts(body: str, fm: dict[str, Any]) -> list[str]:
    explicit = concepts_from_frontmatter(fm)
    section = extract_section_items(body, "Concepts", limit=8)
    if explicit or section:
        return unique([*explicit, *section], 8)
    tokens = [t for t in tokenize(body) if len(t) > 3 and not re.fullmatch(r"\d+", t)]
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, count in ranked if count >= 2][:5]


def build_plan(source: Path) -> dict[str, Any]:
    text = read_text(source)
    fm, body = extract_frontmatter(text)
    title = title_from_markdown(source, text)
    summary = str(fm.get("summary") or first_paragraph(body))
    concepts = infer_concepts(body, fm)
    entities = unique(
        [
            *as_list(fm.get("entities")),
            *extract_section_items(body, "Entities", limit=10),
        ],
        10,
    )
    claims = extract_section_items(body, "Key Claims", limit=10) or extract_section_items(
        body, "Claims", limit=10
    )
    connections = extract_section_items(body, "Connections", limit=10)
    contradictions = extract_section_items(body, "Contradictions", limit=10)
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "source": rel(source),
        "source_slug": slugify(title, fallback=source.stem),
        "title": title,
        "summary": summary,
        "tags": concepts,
        "key_claims": claims,
        "entities": entities,
        "concepts": concepts,
        "connections": connections,
        "contradictions": contradictions,
        "confidence": "medium",
    }


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if int(plan.get("schema_version", 0)) != PLAN_SCHEMA_VERSION:
        raise ValueError(f"unsupported plan schema_version: {plan.get('schema_version')}")
    for key in ["source", "title", "summary"]:
        if not str(plan.get(key, "")).strip():
            raise ValueError(f"plan missing required field: {key}")
    normalized = dict(plan)
    normalized["source_slug"] = str(plan.get("source_slug") or slugify(plan["title"]))
    for key in ["tags", "key_claims", "entities", "concepts", "connections", "contradictions"]:
        normalized[key] = unique(as_list(plan.get(key)), 20)
    normalized["confidence"] = str(plan.get("confidence") or "medium")
    return normalized


def plan_to_json(plan: dict[str, Any]) -> str:
    return json.dumps(validate_plan(plan), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
