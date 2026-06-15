#!/usr/bin/env python3
"""Report-only duplicate page and tag taxonomy audit."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import defaultdict
from typing import Any

from wiki_common import META, append_log, dump_json, iter_wiki_pages, now_iso, page_info, rel, today, write_text


STOPWORDS = {"the", "and", "for", "with", "from", "wiki", "source", "session"}


def normalize_label(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[_\s]+", "-", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff-]+", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def token_set(value: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalize_label(value)) if t not in STOPWORDS}


def similarity(a: str, b: str) -> float:
    a_norm = normalize_label(a)
    b_norm = normalize_label(b)
    if not a_norm or not b_norm:
        return 0.0
    seq = difflib.SequenceMatcher(None, a_norm, b_norm).ratio()
    ta = token_set(a)
    tb = token_set(b)
    overlap = len(ta & tb) / max(len(ta | tb), 1) if ta or tb else 0.0
    return round(max(seq, overlap), 4)


def duplicate_candidate(left: dict[str, Any], right: dict[str, Any], threshold: float) -> dict[str, Any] | None:
    left_title = left["title"]
    right_title = right["title"]
    left_norm = normalize_label(left_title)
    right_norm = normalize_label(right_title)
    if not left_norm or not right_norm:
        return None
    same_type = left["type"] == right["type"]
    exact = left_norm == right_norm
    length_ratio = min(len(left_norm), len(right_norm)) / max(len(left_norm), len(right_norm))
    score = similarity(left_title, right_title)
    if not (exact or (same_type and score >= threshold and length_ratio >= 0.67)):
        return None
    return {
        "score": score,
        "same_type": same_type,
        "left": {"path": left["rel"], "title": left_title, "type": left["type"]},
        "right": {"path": right["rel"], "title": right_title, "type": right["type"]},
    }


def analyze(threshold: float = 0.82) -> dict[str, Any]:
    pages = [page_info(path) for path in iter_wiki_pages(include_meta=False)]
    candidates = []
    for i, left in enumerate(pages):
        for right in pages[i + 1 :]:
            if left["path"].name in {"overview.md"} or right["path"].name in {"overview.md"}:
                continue
            candidate = duplicate_candidate(left, right, threshold)
            if candidate:
                candidates.append(candidate)

    tag_variants: dict[str, list[str]] = defaultdict(list)
    tag_usage: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        for tag in page.get("tags", []):
            norm = normalize_label(str(tag))
            if str(tag) not in tag_variants[norm]:
                tag_variants[norm].append(str(tag))
            tag_usage[str(tag)].append(page["rel"])

    variant_groups = {
        norm: sorted(values)
        for norm, values in sorted(tag_variants.items())
        if len(values) > 1
    }
    rare_tags = {
        tag: paths
        for tag, paths in sorted(tag_usage.items())
        if len(paths) == 1 and len(tag_usage) > 3
    }
    return {
        "schema_version": 1,
        "built_at": now_iso(),
        "ok": True,
        "report_only": True,
        "duplicate_candidates": sorted(candidates, key=lambda item: (-item["score"], item["left"]["path"])),
        "tag_variant_groups": variant_groups,
        "rare_tags": rare_tags,
        "page_count": len(pages),
        "tag_count": len(tag_usage),
    }


def write_report(result: dict[str, Any]) -> str:
    path = META / "lint-reports" / f"{today()}-quality.md"
    lines = [
        f"# Wiki Quality Audit {today()}",
        "",
        "- Status: REPORT ONLY",
        f"- Duplicate candidates: {len(result['duplicate_candidates'])}",
        f"- Tag variant groups: {len(result['tag_variant_groups'])}",
        f"- Rare tags: {len(result['rare_tags'])}",
        "",
        "## Duplicate Candidates",
    ]
    if result["duplicate_candidates"]:
        for item in result["duplicate_candidates"]:
            lines.append(
                f"- score={item['score']} `{item['left']['path']}` <-> `{item['right']['path']}`"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Tag Variant Groups"])
    if result["tag_variant_groups"]:
        for norm, variants in result["tag_variant_groups"].items():
            lines.append(f"- `{norm}`: {', '.join(f'`{v}`' for v in variants)}")
    else:
        lines.append("- None")
    lines.extend(["", "## Rare Tags"])
    if result["rare_tags"]:
        for tag, paths in result["rare_tags"].items():
            lines.append(f"- `{tag}`: {', '.join(f'`{p}`' for p in paths)}")
    else:
        lines.append("- None")
    write_text(path, "\n".join(lines) + "\n")
    return rel(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-cache", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.82)
    args = parser.parse_args()

    result = analyze(threshold=args.threshold)
    report = write_report(result)
    result["report"] = report
    if args.write_cache:
        dump_json(META / "quality-audit.json", result)
        append_log(
            "quality",
            "Wiki quality audit",
            [
                f"- Duplicate candidates: {len(result['duplicate_candidates'])}",
                f"- Tag variant groups: {len(result['tag_variant_groups'])}",
                f"- Report: `{report}`",
            ],
        )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("quality audit: PASS (report only)")
        print(f"duplicate candidates: {len(result['duplicate_candidates'])}")
        print(f"tag variant groups: {len(result['tag_variant_groups'])}")
        print(f"rare tags: {len(result['rare_tags'])}")
        print(f"report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
