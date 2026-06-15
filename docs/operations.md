# Operations

Common local commands:

```bash
make test
python3 tools/analyze_source.py raw/articles/example.md
python3 tools/ingest.py raw/articles/example.md --plan /tmp/plan.json
python3 tools/batch_ingest.py --json
python3 tools/batch_ingest.py --ingest
python3 tools/retrieve.py "query" --build-cache --json
python3 tools/context_pack.py "query" --mode normal --json
python3 tools/ingest_codex_sessions.py --query "topic" --json
python3 tools/audit_wiki_quality.py --write-cache --json
```

Use `make test` before integrating changes. It runs syntax checks, health,
index rebuild/check, link lint, graph export, plugin manifest validation, and
the acceptance workflow.

For low-token Codex queries, run `context_pack.py` first and read only the
listed hot cache, index, snippets, and page candidates. For Codex history,
prefer `ingest_codex_sessions.py --query "<topic>"` so only relevant session
windows are imported.
