---
name: bci-paper-curation
description: Select, validate, and render daily BCI/EEG paper digests from deterministic candidate pools. Use for workflows that need to fetch today's brain-computer interface, EEG decoding, neural interface, neural decoding, clinical EEG, PubMed, bioRxiv, medRxiv, arXiv, or Semantic Scholar papers; rank papers by contribution, novelty, team quality, breakthrough potential, and field impact; curate the strongest 3-10 papers; write selection JSON; validate summaries; or render the final Markdown digest.
---

# BCI Paper Curation

## Workflow

1. Use the bundled tracker in `scripts/bci-tracker` for deterministic fetch and render work.
2. Use `scripts/bci-tracker/config.yaml` as the default config template. It defaults to a 3-day business window and writes outputs to `/Users/zuqiu/Documents/claw`.
3. Fetch candidates with the tracker:

   ```bash
   PYTHONPATH=/path/to/skill/scripts/bci-tracker/src \
     python -m bci_tracker.cli --config /path/to/config.yaml fetch
   ```

4. Read the generated `bci_candidates_{date}.json`.
5. Read `references/curation-rules.md` before ranking candidates.
6. Select 3-10 genuinely relevant papers when enough exist. Do not impose a per-source quota; compare all papers together by scientific contribution, innovation, team/reputation signals visible in the metadata, breakthrough potential, field relevance, and abstract quality.
7. Write `selection_{date}.json` next to the candidate file unless the user gives another output path.
8. Put only `date`, `selected`, `not_enough`, and `notes` at the selection root. In each `selected[]` item, put only `id`, `two_sentence_summary`, and `selection_reason`.
9. Validate the selection:

   ```bash
   python /path/to/skill/scripts/validate_selection.py \
     /path/to/bci_candidates_YYYY-MM-DD.json \
     /path/to/selection_YYYY-MM-DD.json
   ```

10. Render only after validation passes:

    ```bash
    PYTHONPATH=/path/to/skill/scripts/bci-tracker/src \
      python -m bci_tracker.cli --config /path/to/config.yaml render --date YYYY-MM-DD
    ```

    A successful default render removes the intermediate candidate and selection JSON files, leaving the final Markdown in the output directory. Explicit `--candidates` or `--selection` paths are preserved for debugging.

## Boundaries

- Use the candidate JSON as the only source of paper facts.
- Do not invent or overwrite authors, institutions, DOI, URLs, venues, dates, or quantitative results.
- Let `bci-tracker render` fill all hard metadata from the candidate pool.
- Base summaries strictly on each candidate's `abstract`.
- Do not add numbers, claims, outcomes, sample sizes, accuracy, effect sizes, or clinical-readiness claims unless they appear in the abstract.
- Set `not_enough=true` when fewer than 3 candidates are genuinely relevant and worth including. Do not pad the list with weak papers.

## Bundled Resources

- `scripts/bci-tracker/`: deterministic Python CLI for fetching candidates and rendering final Markdown.
- `scripts/validate_selection.py`: structural and prose-contract validator for `selection_{date}.json`.
- `references/curation-rules.md`: detailed selection rubric, summary rules, and not-enough handling.

## Dependencies

The bundled tracker requires Python 3.9+ and these packages: `requests`, `PyYAML`, and `python-dateutil`. For local development or testing, install the bundled project with:

```bash
python -m pip install -e /path/to/skill/scripts/bci-tracker
```
