# Codex First LLM Wiki

A local Markdown knowledge base manager optimized for Codex and other coding agents.
It keeps durable knowledge in plain files, uses deterministic Python tooling, and
keeps query context small through hot-cache, index, and chunk-level BM25 retrieval.

## What It Provides

- Codex-first operating instructions in `AGENTS.md`.
- Agent skills for ingest, query, lint, and retrieval under `.agents/skills/`.
- Deterministic Markdown ingest from `raw/` into linked `wiki/` pages.
- Chunk-level BM25 retrieval without external services.
- Low-token context packs before asking an agent to read full pages.
- Codex session import with redaction and query-driven selection.
- Link linting, manifest health checks, graph export, and report-only quality audit.
- Optional Codex plugin manifest in `.codex-plugin/plugin.json`.

## Repository Privacy Model

The repository is safe to publish because private knowledge content is ignored by
default:

- `raw/**` stores original personal material and is ignored except `.gitkeep`.
- generated wiki pages under `wiki/sources`, `wiki/entities`, `wiki/concepts`,
  `wiki/projects`, `wiki/questions`, and `wiki/syntheses` are ignored except
  `.gitkeep`.
- generated caches and reports under `meta/retrieval`, `meta/lint-reports`,
  `meta/link-index.json`, `meta/graph.*`, and `meta/quality-audit.json` are
  ignored.

Starter files such as `wiki/overview.md`, `wiki/hot.md`, `wiki/index.md`,
`wiki/log.md`, and `meta/manifest.json` remain tracked.

## Quick Start

```bash
make test
```

Add a Markdown source:

```bash
cp your-note.md raw/articles/
python3 tools/analyze_source.py raw/articles/your-note.md --output /tmp/wiki-plan.json
python3 tools/ingest.py raw/articles/your-note.md --plan /tmp/wiki-plan.json
python3 tools/build_index.py
```

Retrieve context:

```bash
python3 tools/context_pack.py "your query" --mode normal
python3 tools/retrieve.py "your query" --top 5 --json
```

Import relevant Codex sessions:

```bash
python3 tools/ingest_codex_sessions.py --query "topic keywords" --ingest --limit 5
```

## Common Commands

```bash
make health
make index
make lint
make quality
make graph
```

## Install As A Local Codex Plugin

```bash
python3 tools/install_plugin.py --check
python3 tools/install_plugin.py
```

See `docs/codex-plugin-install.md` and `docs/operations.md` for details.

## Requirements

- Python 3.10+
- GNU Make
- No required external Python packages

## License

MIT. See `LICENSE`.
