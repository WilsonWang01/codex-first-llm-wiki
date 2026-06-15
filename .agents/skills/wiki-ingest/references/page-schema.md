# Wiki Page Schema

All non-index wiki pages use YAML frontmatter:

```yaml
---
title: "Page Title"
type: source | entity | concept | project | question | synthesis | meta
summary: "One-sentence summary for index-only retrieval."
status: draft | developing | stable | archived
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
sources: []
confidence: low | medium | high
---
```

## Source Page

Path: `wiki/sources/<slug>.md`

Sections:

- `# Source Title`
- `## Summary`
- `## Key Claims`
- `## Entities`
- `## Concepts`
- `## Connections`
- `## Contradictions`
- `## Raw Source`

## Entity Page

Path: `wiki/entities/<slug>.md`

Sections:

- `# Entity Name`
- `## Definition`
- `## Known Facts`
- `## Related Sources`
- `## Related Concepts`
- `## Open Questions`

## Concept Page

Path: `wiki/concepts/<slug>.md`

Sections:

- `# Concept Name`
- `## Definition`
- `## Current Understanding`
- `## Evidence`
- `## Related Concepts`
- `## Contradictions`
- `## Open Questions`

## Question or Synthesis Page

Path: `wiki/questions/<slug>.md` or `wiki/syntheses/<slug>.md`

Use only when the user asks to save an answer or when a deep synthesis has
long-term value. Cite related wiki pages and source pages.
