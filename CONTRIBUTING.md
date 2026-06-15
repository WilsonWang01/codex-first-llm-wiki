# Contributing

Thanks for improving Codex First LLM Wiki.

## Development

Run the full local check before opening a pull request:

```bash
make test
```

Keep changes conservative:

- prefer deterministic local tools over network services;
- preserve plain Markdown as the storage format;
- keep query flows low-token by default;
- do not commit private `raw/`, generated wiki pages, retrieval caches, or lint
  reports.

## Pull Requests

Include:

- what changed;
- why it changed;
- the checks you ran;
- any known limitations.
