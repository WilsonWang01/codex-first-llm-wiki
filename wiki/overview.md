---
title: "Overview"
type: meta
summary: "Living synthesis of this Codex-first local Markdown knowledge vault."
status: developing
created: 2026-06-16
updated: 2026-06-16
tags: [wiki, codex]
sources: []
confidence: high
---

# Overview

This vault stores original material under `raw/` and compiled knowledge under
`wiki/`. Codex maintains the wiki by ingesting sources, creating concise source
pages, linking concepts and entities, and keeping low-token query surfaces up to
date.

## Current Scope

- Personal research notes.
- Project knowledge.
- Agent session summaries.
- Reusable syntheses and answered questions.

## Operating Pattern

1. Add source material to `raw/`.
2. Ask Codex to ingest the source with `wiki-ingest`.
3. Query through `wiki-query`, starting from `wiki/hot.md` and `wiki/index.md`.
4. Periodically run `wiki-lint` and rebuild generated indexes.

## Open Decisions

- First real topic areas to ingest.
- Whether to enable optional local embeddings in a later version.
