#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 tools/health.py
python3 tools/build_index.py
python3 tools/build_index.py --check
python3 tools/analyze_source.py raw/articles/acceptance-llm-wiki-vs-rag.md --output /tmp/codex_first_wiki_plan_pre.json || true
python3 tools/retrieve.py "Codex first wiki" --top 3 --json >/tmp/codex_first_wiki_retrieve.json
python3 tools/lint_links.py --write-cache --json >/tmp/codex_first_wiki_lint.json

TMP_SOURCE="raw/articles/acceptance-llm-wiki-vs-rag.md"
cat > "$TMP_SOURCE" <<'EOF'
---
title: "LLM Wiki vs RAG"
summary: "LLM Wiki compiles durable knowledge into Markdown, while RAG retrieves source chunks at query time."
tags: [llm-wiki, rag, codex]
---

# LLM Wiki vs RAG

LLM Wiki keeps a compiled knowledge layer that agents can maintain over time.
RAG usually retrieves chunks from raw source material during each query.

## Key Claims
- LLM Wiki reduces repeated reasoning over the same raw source.
- RAG is useful for fresh retrieval but can spend more query-time context.
- Codex benefits from a small hot cache and deterministic index.

## Entities
- Codex

## Concepts
- llm-wiki
- rag
EOF

python3 tools/analyze_source.py "$TMP_SOURCE" --output /tmp/codex_first_wiki_plan.json >/tmp/codex_first_wiki_plan_msg.txt
python3 tools/ingest.py "$TMP_SOURCE" --plan /tmp/codex_first_wiki_plan.json --force --json >/tmp/codex_first_wiki_ingest.json
python3 tools/build_index.py
python3 tools/retrieve.py "LLM Wiki 和 RAG 的区别" --top 5 --build-cache --json >/tmp/codex_first_wiki_after_ingest.json
python3 tools/context_pack.py "LLM Wiki 和 RAG 的区别" --mode normal --json >/tmp/codex_first_wiki_context_pack.json
python3 tools/ingest.py "$TMP_SOURCE" --json >/tmp/codex_first_wiki_skip.json
python3 tools/batch_ingest.py --json >/tmp/codex_first_wiki_delta.json
python3 tools/health.py
python3 tools/lint_links.py --write-cache --json >/tmp/codex_first_wiki_lint_after_ingest.json
python3 tools/audit_wiki_quality.py --write-cache --json >/tmp/codex_first_wiki_quality.json
python3 tools/export_graph.py --html --json >/tmp/codex_first_wiki_graph.json
python3 tools/install_plugin.py --check >/tmp/codex_first_wiki_plugin_check.txt

SESSION_FIXTURE="/tmp/codex_first_wiki_session.jsonl"
cat > "$SESSION_FIXTURE" <<'EOF'
{"type":"user","content":"Please switch LLM Wiki retrieval to chunk BM25 and keep token cost low.","timestamp":"2026-06-16T01:00:00"}
{"type":"assistant","content":"我会实现 chunk-level BM25，并保持本地检索。","timestamp":"2026-06-16T01:01:00"}
{"type":"tool_use","name":"exec_command","content":"python3 tools/retrieve.py --build-cache","timestamp":"2026-06-16T01:02:00"}
EOF

python3 tools/ingest_codex_sessions.py --session-file "$SESSION_FIXTURE" --ingest --force --json >/tmp/codex_first_wiki_session_ingest.json
python3 tools/ingest_codex_sessions.py --session-file "$SESSION_FIXTURE" --query "chunk BM25 token" --dry-run --json >/tmp/codex_first_wiki_session_query_dry.json
python3 tools/ingest_codex_sessions.py --session-file "$SESSION_FIXTURE" --query "chunk BM25 token" --ingest --force --json >/tmp/codex_first_wiki_session_query_ingest.json
python3 tools/build_index.py
python3 tools/retrieve.py "chunk BM25 token 成本" --top 5 --json >/tmp/codex_first_wiki_session_retrieve.json
python3 tools/batch_ingest.py --ingest --limit 1 --json >/tmp/codex_first_wiki_batch_ingest.json

python3 - <<'PY'
import json
from pathlib import Path

ingest = json.loads(Path('/tmp/codex_first_wiki_ingest.json').read_text())
skip = json.loads(Path('/tmp/codex_first_wiki_skip.json').read_text())
retrieval = json.loads(Path('/tmp/codex_first_wiki_after_ingest.json').read_text())
context_pack = json.loads(Path('/tmp/codex_first_wiki_context_pack.json').read_text())
plan = json.loads(Path('/tmp/codex_first_wiki_plan.json').read_text())
delta = json.loads(Path('/tmp/codex_first_wiki_delta.json').read_text())
quality = json.loads(Path('/tmp/codex_first_wiki_quality.json').read_text())
session_ingest = json.loads(Path('/tmp/codex_first_wiki_session_ingest.json').read_text())
session_query_dry = json.loads(Path('/tmp/codex_first_wiki_session_query_dry.json').read_text())
session_query_ingest = json.loads(Path('/tmp/codex_first_wiki_session_query_ingest.json').read_text())
session_retrieval = json.loads(Path('/tmp/codex_first_wiki_session_retrieve.json').read_text())

assert ingest['status'] == 'ingested', ingest
assert skip['status'] == 'skipped', skip
assert plan['schema_version'] == 1 and 'llm-wiki' in plan['concepts'], plan
assert delta['counts']['unchanged'] >= 1, delta
assert any(
    'llm-wiki-vs-rag' in c['path']
    or c['path'] in {'wiki/concepts/rag.md', 'wiki/concepts/llm-wiki.md'}
    for c in retrieval['candidates']
), retrieval
assert retrieval['strategy'] == 'chunk-bm25', retrieval
assert all('chunk_id' in c and 'section' in c for c in retrieval['candidates']), retrieval
assert context_pack['mode'] == 'normal' and context_pack['estimated_tokens'] > 0, context_pack
assert any(e['role'] == 'retrieval-snippet' for e in context_pack['entries']), context_pack
assert quality['report_only'] is True and quality['ok'] is True, quality
assert session_ingest['count'] == 1 and session_ingest['results'][0]['status'] == 'imported', session_ingest
assert session_query_dry['count'] == 0 and session_query_dry['ranked'][0]['score'] > 0, session_query_dry
assert session_query_ingest['count'] == 1 and session_query_ingest['results'][0]['selected_records'] <= session_query_ingest['results'][0]['records'], session_query_ingest
assert any('codex-session' in c['path'] or 'chunk' in c['snippet'].lower() for c in session_retrieval['candidates']), session_retrieval
assert Path('wiki/sources/llm-wiki-vs-rag.md').exists()
assert Path('wiki/concepts/llm-wiki.md').exists()
assert Path('wiki/concepts/rag.md').exists()
assert Path('wiki/entities/codex.md').exists()
assert Path('meta/graph.json').exists()
assert Path('meta/graph.html').exists()
assert Path('meta/retrieval/bm25-index.json').exists()
PY

echo "acceptance: PASS"
