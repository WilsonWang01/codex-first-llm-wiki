# Wiki Query

Use this skill when the user asks a question that should be answered from this
knowledge vault.

## Required Reference

Read `references/retrieval-policy.md` when choosing query mode or deciding how
many files to inspect.

## Modes

- `quick`: read `wiki/hot.md` and `wiki/index.md` only.
- `normal`: read `wiki/hot.md`, `wiki/index.md`, snippets, and up to 5 relevant
  full pages. This is the default.
- `deep`: read all relevant pages and optionally save a synthesis when the user
  asks for a complete answer.

## Workflow

1. Determine mode from the user request. Default to `normal`.
2. Read `wiki/hot.md`.
3. Read `wiki/index.md`.
4. For `quick`, answer only from those two files and state if evidence is thin.
5. For `normal` or `deep`, run:

   ```bash
   python3 tools/retrieve.py "<question>" --top 5
   ```

6. Read selected snippets and up to 5 full pages in normal mode.
7. Answer with page references.
8. If the wiki does not support an answer, say what is missing.
9. Write a `wiki/questions/` or `wiki/syntheses/` page only when the user asks or
   when deep mode produces durable synthesis worth saving.

## Response Requirements

- Separate known facts from inferences.
- Cite relevant wiki pages by path.
- Keep gaps explicit.
- Do not silently use external web search for vault questions unless the user
  asks for current outside research.

## Cost Discipline

- Do not open every page.
- Do not read raw sources unless a wiki page points to a needed source and the
  user requested deeper verification.
- Prefer `tools/retrieve.py` snippets before full pages.
