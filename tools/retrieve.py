#!/usr/bin/env python3
"""Chunk-level BM25 retrieval over wiki Markdown pages."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from wiki_common import (
    META,
    dump_json,
    iter_wiki_pages,
    now_iso,
    page_info,
    rel,
    sha256_file,
    short_snippet,
    tokenize,
    write_text,
)


INDEX_SCHEMA_VERSION = 2
K1 = 1.5
B = 0.75


def split_sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Body"
    current_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line.lstrip("#").strip() or "Body"
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))
    if not sections and body.strip():
        sections.append(("Body", body.splitlines()))
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections if "\n".join(lines).strip()]


def split_long_text(text: str, max_chars: int = 900) -> list[str]:
    paragraphs = [p.strip() for p in re_split_paragraphs(text) if p.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current.strip())
    return chunks or [text[:max_chars]]


def re_split_paragraphs(text: str) -> list[str]:
    import re

    return re.split(r"\n\s*\n", text)


def build_chunks() -> tuple[list[dict[str, Any]], dict[str, str]]:
    chunks = []
    page_hashes: dict[str, str] = {}
    chunk_no = 0
    for path in iter_wiki_pages(include_meta=False):
        if path.name in {"index.md", "log.md"}:
            continue
        info = page_info(path)
        page_hashes[info["rel"]] = sha256_file(path)
        metadata = "\n".join(
            [
                f"Title: {info['title']}",
                f"Type: {info['type']}",
                f"Summary: {info['summary']}",
                f"Tags: {', '.join(info['tags'])}",
            ]
        )
        for section_heading, section_text in split_sections(info["body"]):
            for part_no, part in enumerate(split_long_text(section_text)):
                weighted_text = "\n".join([metadata, f"Section: {section_heading}", part])
                tokens = tokenize(weighted_text)
                if not tokens:
                    continue
                chunk_id = f"c{chunk_no:06d}"
                chunk_no += 1
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "path": info["rel"],
                        "title": info["title"],
                        "type": info["type"],
                        "summary": info["summary"],
                        "section": section_heading,
                        "part": part_no,
                        "text": part,
                        "weighted_text": weighted_text,
                        "tokens": tokens,
                        "length": len(tokens),
                    }
                )
    return chunks, page_hashes


def build_index_payload() -> dict[str, Any]:
    chunks, page_hashes = build_chunks()
    doc_freq: Counter[str] = Counter()
    for chunk in chunks:
        for token in set(chunk["tokens"]):
            doc_freq[token] += 1
    avgdl = sum(chunk["length"] for chunk in chunks) / max(len(chunks), 1)
    return {
        "schema_version": INDEX_SCHEMA_VERSION,
        "built_at": now_iso(),
        "k1": K1,
        "b": B,
        "chunk_count": len(chunks),
        "avgdl": avgdl,
        "page_hashes": page_hashes,
        "doc_freq": dict(sorted(doc_freq.items())),
        "chunks": chunks,
    }


def cache_paths() -> tuple[Path, Path]:
    return META / "retrieval/bm25-index.json", META / "retrieval/chunks.jsonl"


def cache_is_fresh(payload: dict[str, Any]) -> bool:
    if payload.get("schema_version") != INDEX_SCHEMA_VERSION:
        return False
    current_hashes = {}
    for path in iter_wiki_pages(include_meta=False):
        if path.name in {"index.md", "log.md"}:
            continue
        current_hashes[rel(path)] = sha256_file(path)
    return payload.get("page_hashes") == current_hashes


def load_or_build_index(use_cache: bool = True) -> dict[str, Any]:
    index_path, _ = cache_paths()
    if use_cache and index_path.exists():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            if cache_is_fresh(payload):
                return payload
        except (json.JSONDecodeError, OSError):
            pass
    return build_index_payload()


def write_cache(payload: dict[str, Any] | None = None) -> None:
    payload = payload or build_index_payload()
    index_path, chunks_path = cache_paths()
    cache_payload = dict(payload)
    dump_json(index_path, cache_payload)
    lines = []
    for chunk in payload["chunks"]:
        public_chunk = {key: value for key, value in chunk.items() if key not in {"tokens", "weighted_text"}}
        lines.append(json.dumps(public_chunk, ensure_ascii=False, sort_keys=True))
    write_text(chunks_path, "\n".join(lines) + ("\n" if lines else ""))


def bm25_score(query_terms: list[str], chunk: dict[str, Any], doc_freq: dict[str, int], total: int, avgdl: float) -> float:
    counts = Counter(chunk["tokens"])
    score = 0.0
    dl = max(chunk["length"], 1)
    for term in query_terms:
        tf = counts.get(term, 0)
        if not tf:
            continue
        df = doc_freq.get(term, 0)
        idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
        denom = tf + K1 * (1 - B + B * dl / max(avgdl, 1))
        score += idf * (tf * (K1 + 1)) / denom
    return score


def retrieve(query: str, top: int = 5, use_cache: bool = True) -> list[dict[str, Any]]:
    query_terms = tokenize(query)
    if not query_terms:
        return []
    payload = load_or_build_index(use_cache=use_cache)
    total = max(int(payload.get("chunk_count", 0)), 1)
    avgdl = float(payload.get("avgdl", 1.0))
    doc_freq = {str(k): int(v) for k, v in payload.get("doc_freq", {}).items()}
    scored = []
    query_lower = query.lower()
    for chunk in payload.get("chunks", []):
        score = bm25_score(query_terms, chunk, doc_freq, total, avgdl)
        title_lower = chunk["title"].lower()
        summary_lower = chunk["summary"].lower()
        if query_lower and query_lower in title_lower:
            score += 2.5
        if query_lower and query_lower in summary_lower:
            score += 1.5
        if score <= 0:
            continue
        scored.append(
            {
                "chunk_id": chunk["chunk_id"],
                "path": chunk["path"],
                "title": chunk["title"],
                "type": chunk["type"],
                "summary": chunk["summary"],
                "section": chunk["section"],
                "score": round(score, 4),
                "snippet": short_snippet(chunk["text"], query_terms, size=260),
            }
        )
    best_by_page: dict[str, dict[str, Any]] = {}
    for item in sorted(scored, key=lambda row: (-row["score"], row["path"], row["chunk_id"])):
        existing = best_by_page.get(item["path"])
        if existing is None or item["score"] > existing["score"]:
            best_by_page[item["path"]] = item
    return sorted(best_by_page.values(), key=lambda row: (-row["score"], row["path"]))[:top]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="", help="Query text.")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--build-cache", action="store_true")
    parser.add_argument("--no-cache", action="store_true", help="Ignore existing cache for this query.")
    args = parser.parse_args()

    if args.build_cache:
        write_cache()
        if not args.json:
            print("retrieval cache rebuilt")
        if not args.query:
            return 0

    candidates = retrieve(args.query, top=args.top, use_cache=not args.no_cache)
    payload = {"query": args.query, "strategy": "chunk-bm25", "candidates": candidates}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in candidates:
            print(f"{item['score']:>7}  {item['path']}#{item['section']}  {item['title']}")
            if item["snippet"]:
                print(f"        {item['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
