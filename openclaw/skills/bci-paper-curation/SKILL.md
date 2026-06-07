---
name: bci-paper-curation
description: >
  Select and write daily BCI/EEG paper curation outputs from bci-tracker candidate pools.
  Use when Codex or OpenClaw needs to read bci_candidates_{date}.json, choose representative
  brain-computer interface, neural interface, neural decoding, or clinical EEG papers, rank by
  contribution, novelty, team quality, potential breakthrough value, and field impact, write
  two-sentence summaries and selection reasons, produce selection_{date}.json, or handle weeks
  with too few high-quality relevant papers. This skill only writes judgement text and IDs; it
  never fetches papers or renders final Markdown.
---

# BCI Paper Curation

## Workflow

1. Read the candidate pool JSON from `bci_candidates_{date}.json`.
2. Read `references/curation-rules.md` before ranking candidates; it contains the output contract, selection rubric, and "not enough" handling.
3. Select 3-10 papers when enough genuinely relevant candidates exist. Do not impose a per-source quota; compare all papers together by scientific contribution, innovation, team/reputation signals visible in the metadata, breakthrough potential, field relevance, and abstract quality.
4. Write `selection_{date}.json` next to the candidate file unless the user gives another output path.
5. Put only `date`, `selected`, `not_enough`, and `notes` at the selection root. In each `selected[]` item, put only `id`, `two_sentence_summary`, and `selection_reason`.
6. Run `scripts/validate_selection.py <candidate-json> <selection-json>` and fix any reported errors before continuing to render or report completion.

## Hard Boundaries

- Use the candidate JSON as the only source of facts. Do not invent authors, institutions, DOI, URLs, venues, dates, or quantitative results.
- Let `bci-tracker render` fill all hard metadata from the candidate pool. Do not copy hard metadata into `selection_{date}.json`.
- Base summaries strictly on each candidate's `abstract`. Do not add numbers, claims, or outcomes that are absent from the abstract.
- Mark `not_enough=true` when fewer than 3 candidates are genuinely relevant and worth including. Do not pad the list with weak papers.

## Validation

Use the bundled validator:

```bash
python3 openclaw/skills/bci-paper-curation/scripts/validate_selection.py \
  path/to/bci_candidates_YYYY-MM-DD.json \
  path/to/selection_YYYY-MM-DD.json
```

For stricter numeric checking during review, add `--strict-numbers`; this makes abstract-missing numbers in summaries fatal instead of warnings.
