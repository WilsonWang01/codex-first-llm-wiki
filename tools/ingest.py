#!/usr/bin/env python3
"""Deterministic source ingest helper for the Codex-first LLM Wiki.

This is intentionally conservative. It creates a traceable source page, updates
manifest/index/log/hot, and can optionally seed concept pages from explicit
frontmatter tags or a structured ingest plan.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from source_plan import build_plan, plan_to_json, validate_plan
from wiki_common import (
    META,
    RAW,
    WIKI,
    append_log,
    dump_frontmatter,
    dump_json,
    extract_frontmatter,
    load_json,
    read_text,
    rel,
    sha256_file,
    slugify,
    source_type,
    title_from_markdown,
    today,
    write_text,
)


def ensure_under_raw(path: Path) -> None:
    try:
        path.resolve().relative_to(RAW.resolve())
    except ValueError as exc:
        raise SystemExit(f"source must be under raw/: {path}") from exc


def bulletize(items: list[str], fallback: str) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    return [f"- {item}" for item in items]


def extract_bullets(body: str, heading: str) -> list[str]:
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
    return lines[:8]


def create_source_page(source: Path, plan: dict) -> Path:
    title = plan["title"]
    slug = slugify(str(plan.get("source_slug") or title), fallback=source.stem)
    target = WIKI / "sources" / f"{slug}.md"
    source_rel = rel(source)
    summary = plan["summary"]
    key_claims = plan.get("key_claims", [])
    entities = plan.get("entities", [])
    concepts = plan.get("concepts", [])
    connections = plan.get("connections", [])
    contradictions = plan.get("contradictions", [])

    frontmatter = {
        "title": title,
        "type": "source",
        "summary": summary,
        "status": "developing",
        "created": today(),
        "updated": today(),
        "tags": plan.get("tags") or concepts,
        "sources": [source_rel],
        "confidence": plan.get("confidence", "medium"),
    }
    content = dump_frontmatter(frontmatter)
    content += f"# {title}\n\n"
    content += "## Summary\n\n"
    content += f"{summary}\n\n"
    content += "## Key Claims\n\n"
    content += "\n".join(bulletize(key_claims, "No explicit key claims extracted.")) + "\n\n"
    content += "## Entities\n\n"
    content += "\n".join(bulletize(entities, "No explicit entities extracted.")) + "\n\n"
    content += "## Concepts\n\n"
    content += "\n".join(bulletize(concepts, "No explicit concepts extracted.")) + "\n\n"
    content += "## Connections\n\n"
    content += "\n".join(bulletize(connections, "No explicit connections extracted.")) + "\n\n"
    content += "## Contradictions\n\n"
    content += "\n".join(bulletize(contradictions, "No contradictions noted.")) + "\n\n"
    content += "## Raw Source\n\n"
    content += f"- [{source_rel}](../../{source_rel})\n"
    write_text(target, content)
    return target


def create_concept_pages(concepts: list[str], source_page: Path, source_title: str) -> list[Path]:
    created_or_updated = []
    for concept in concepts:
        slug = slugify(concept)
        if not slug:
            continue
        path = WIKI / "concepts" / f"{slug}.md"
        link = f"../sources/{source_page.name}"
        if path.exists():
            text = read_text(path)
            if link not in text:
                text = text.rstrip() + f"\n- [{source_title}]({link})\n"
                text = re.sub(r"updated: \"?[^\"\n]+\"?", f"updated: {today()}", text, count=1)
                write_text(path, text + ("\n" if not text.endswith("\n") else ""))
            created_or_updated.append(path)
            continue
        fm = {
            "title": concept,
            "type": "concept",
            "summary": f"Concept seeded from source page {source_title}.",
            "status": "draft",
            "created": today(),
            "updated": today(),
            "tags": [concept],
            "sources": [rel(source_page)],
            "confidence": "low",
        }
        content = dump_frontmatter(fm)
        content += f"# {concept}\n\n"
        content += "## Definition\n\n"
        content += "Draft concept page seeded during source ingest.\n\n"
        content += "## Current Understanding\n\n"
        content += f"- Introduced by [{source_title}]({link}).\n\n"
        content += "## Evidence\n\n"
        content += f"- [{source_title}]({link})\n\n"
        content += "## Related Concepts\n\n- None yet.\n\n"
        content += "## Contradictions\n\n- None noted.\n\n"
        content += "## Open Questions\n\n- Refine this concept after more sources are ingested.\n"
        write_text(path, content)
        created_or_updated.append(path)
    return created_or_updated


def create_entity_pages(entities: list[str], source_page: Path, source_title: str) -> list[Path]:
    created_or_updated = []
    for entity in entities:
        slug = slugify(entity)
        if not slug:
            continue
        path = WIKI / "entities" / f"{slug}.md"
        link = f"../sources/{source_page.name}"
        if path.exists():
            text = read_text(path)
            if link not in text:
                text = text.rstrip() + f"\n- [{source_title}]({link})\n"
                text = re.sub(r"updated: \"?[^\"\n]+\"?", f"updated: {today()}", text, count=1)
                write_text(path, text + ("\n" if not text.endswith("\n") else ""))
            created_or_updated.append(path)
            continue
        fm = {
            "title": entity,
            "type": "entity",
            "summary": f"Entity seeded from source page {source_title}.",
            "status": "draft",
            "created": today(),
            "updated": today(),
            "tags": [entity],
            "sources": [rel(source_page)],
            "confidence": "low",
        }
        content = dump_frontmatter(fm)
        content += f"# {entity}\n\n"
        content += "## Definition\n\n"
        content += "Draft entity page seeded during source ingest.\n\n"
        content += "## Known Facts\n\n"
        content += f"- Mentioned by [{source_title}]({link}).\n\n"
        content += "## Related Sources\n\n"
        content += f"- [{source_title}]({link})\n\n"
        content += "## Related Concepts\n\n- None yet.\n\n"
        content += "## Open Questions\n\n- Clarify this entity after more sources are ingested.\n"
        write_text(path, content)
        created_or_updated.append(path)
    return created_or_updated


def load_plan(plan_path: Path | None, source: Path) -> dict:
    if plan_path:
        plan = json.loads(read_text(plan_path))
    else:
        plan = build_plan(source)
    normalized = validate_plan(plan)
    if normalized["source"] != rel(source):
        normalized["source"] = rel(source)
    return normalized


def ingest(
    source: Path,
    force: bool = False,
    seed_concepts: bool = True,
    seed_entities: bool = True,
    plan_path: Path | None = None,
) -> dict:
    source = source.resolve()
    ensure_under_raw(source)
    if not source.exists() or not source.is_file():
        raise SystemExit(f"source not found: {source}")

    manifest_path = META / "manifest.json"
    manifest = load_json(manifest_path, {"schema_version": 1, "sources": {}})
    manifest.setdefault("schema_version", 1)
    manifest.setdefault("sources", {})

    source_rel = rel(source)
    digest = sha256_file(source)
    previous = manifest["sources"].get(source_rel)
    if previous and previous.get("hash") == digest and not force:
        return {
            "status": "skipped",
            "reason": "unchanged",
            "source": source_rel,
            "pages_created": [],
            "pages_updated": [],
        }

    plan = load_plan(plan_path, source)
    title = plan["title"]
    source_page = create_source_page(source, plan)
    concepts = plan.get("concepts", [])
    entities = plan.get("entities", [])
    concept_pages = create_concept_pages(concepts, source_page, title) if seed_concepts else []
    entity_pages = create_entity_pages(entities, source_page, title) if seed_entities else []

    previous_pages = set(previous.get("pages_created", [])) if previous else set()
    touched = [source_page, *concept_pages, *entity_pages]
    created = [rel(path) for path in touched if rel(path) not in previous_pages]
    updated = [rel(path) for path in touched if rel(path) in previous_pages]

    manifest["sources"][source_rel] = {
        "hash": digest,
        "ingested_at": today(),
        "source_type": source_type(source),
        "title": title,
        "pages_created": sorted(set(created) | {rel(source_page)}),
        "pages_updated": sorted(set(updated)),
        "plan": plan,
        "last_error": None,
    }
    dump_json(manifest_path, manifest)

    hot_path = WIKI / "hot.md"
    hot = read_text(hot_path)
    insertion = f"- {today()}: Ingested `{source_rel}` into `{rel(source_page)}`.\n"
    hot = re.sub(r"(## Recent Changes\n)", "\\1" + insertion, hot, count=1)
    hot = re.sub(r"updated: \"?[^\"\n]+\"?", f"updated: {today()}", hot, count=1)
    write_text(hot_path, hot)

    append_log(
        "ingest",
        title,
        [
            f"- Raw: `{source_rel}`",
            f"- Created: {', '.join(f'`{p}`' for p in sorted(set(created) | {rel(source_page)}))}",
            f"- Updated: {', '.join(f'`{p}`' for p in sorted(set(updated))) if updated else 'none'}",
            "- Notes: Deterministic ingest helper updated manifest and source page.",
        ],
    )

    return {
        "status": "ingested",
        "source": source_rel,
        "pages_created": sorted(set(created) | {rel(source_page)}),
        "pages_updated": sorted(set(updated)),
        "plan": plan,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Source file under raw/.")
    parser.add_argument("--force", action="store_true", help="Ingest even if hash is unchanged.")
    parser.add_argument("--no-concepts", action="store_true", help="Do not seed concept pages from tags.")
    parser.add_argument("--no-entities", action="store_true", help="Do not seed entity pages from the plan.")
    parser.add_argument("--plan", help="Use a reviewed ingest plan JSON file.")
    parser.add_argument("--plan-only", action="store_true", help="Print the generated ingest plan and exit.")
    parser.add_argument("--write-plan", help="Write the generated ingest plan to this path and exit.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if args.plan_only or args.write_plan:
        ensure_under_raw(source)
        payload = plan_to_json(build_plan(source))
        if args.write_plan:
            write_text(Path(args.write_plan), payload)
            print(json.dumps({"status": "planned", "plan": args.write_plan}, ensure_ascii=False))
        else:
            print(payload, end="")
        return 0

    result = ingest(
        source,
        force=args.force,
        seed_concepts=not args.no_concepts,
        seed_entities=not args.no_entities,
        plan_path=Path(args.plan) if args.plan else None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ingest: {result['status']}")
        if result.get("reason"):
            print(f"reason: {result['reason']}")
        print(f"source: {result['source']}")
        if result["pages_created"]:
            print("created:")
            for item in result["pages_created"]:
                print(f"- {item}")
        if result["pages_updated"]:
            print("updated:")
            for item in result["pages_updated"]:
                print(f"- {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
