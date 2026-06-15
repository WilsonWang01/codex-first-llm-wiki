# Wiki Lint

Use this skill when the user asks to inspect, lint, repair, or health-check the
knowledge vault.

## Workflow

1. Run `python3 tools/health.py`.
2. Run `python3 tools/build_index.py --check`.
3. Run `python3 tools/lint_links.py --write-cache`.
4. Review the generated report under `meta/lint-reports/`.
5. Apply only deterministic fixes unless the user asks for semantic cleanup.

## Checks

- Missing required directories and files.
- Invalid `meta/manifest.json`.
- Empty wiki pages.
- Missing frontmatter.
- Index entries missing or stale.
- Broken Markdown links.
- Broken `[[wikilinks]]`.
- Orphan pages.
- Duplicate titles.
- Pages without sources where sources are expected.

## Auto-Fix Policy

Allowed without extra confirmation:

- Rebuild `wiki/index.md` from frontmatter.
- Write `meta/link-index.json`.
- Add reports under `meta/lint-reports/`.

Report only:

- Content contradictions.
- Semantic duplicates.
- Orphan deletion.
- Page merges or splits.

## Output

Lead with pass/fail status, then list actionable findings. Include the exact
commands run.
