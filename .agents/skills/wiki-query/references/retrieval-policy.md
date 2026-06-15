# Retrieval Policy

## Order

1. `wiki/hot.md`
2. `wiki/index.md`
3. `tools/retrieve.py` snippets
4. Selected full pages
5. Raw source only for deep verification

## Normal Mode Limits

- At most 5 full wiki pages.
- Prefer high-score retrieval candidates.
- Prefer pages whose frontmatter summary directly matches the question.
- Stop early when the answer is sufficiently supported.

## Deep Mode

Use deep mode only when the user says `deep`, `全面`, `完整综合`, or requests a
saved synthesis. Deep mode may read more pages, rebuild retrieval caches, and
write `wiki/syntheses/` output.

## Evidence Quality

- `high`: multiple source pages or stable synthesis support the answer.
- `medium`: one strong page or a developing concept supports the answer.
- `low`: hot/index mention only, or indirect inference.

State confidence when the answer affects future decisions.
