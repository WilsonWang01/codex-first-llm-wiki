# Wiki Retrieve

Use this skill when the user asks for local candidate retrieval, snippets, or
low-cost search over the wiki.

## Tool

Run:

```bash
python3 tools/retrieve.py "<query>" --top 5
```

Useful options:

```bash
python3 tools/retrieve.py "<query>" --top 10 --json
python3 tools/retrieve.py "<query>" --build-cache
```

## Behavior

The retrieval tool searches `wiki/**/*.md` with chunk-level BM25 and weights:

1. Title, frontmatter summary, and tags.
2. Headings.
3. Body terms and snippets.

It returns candidate path, chunk id, section, score, title, summary, and a short
snippet. It does not return entire pages by default.

## Usage

- Use before opening many full pages.
- Use to find likely duplicates before ingesting.
- Use to support normal query mode.
- Do not treat lexical retrieval as proof. Read cited pages before making strong
  claims.
