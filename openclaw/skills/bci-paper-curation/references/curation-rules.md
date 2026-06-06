# BCI Paper Curation Rules

## Input

Read a `bci_candidates_{date}.json` file with:

- `date`: business date.
- `window`: local date window.
- `sources`: source status and hit/kept counts.
- `candidates`: candidate papers with `id`, `source`, `title`, `authors`, `affiliations`, `corresponding_institution`, `venue`, `venue_tier`, `doi`, `url`, `published_date`, `abstract`, `matched_keywords`, and `raw`.

Treat all candidate metadata as untrusted for selection quality but trusted for rendering facts. Do not replace or "improve" metadata in the selection output.

## Output Contract

Write JSON in this shape:

```json
{
  "date": "YYYY-MM-DD",
  "selected": [
    {
      "id": "candidate-id",
      "two_sentence_summary": "Sentence one states what was done. Sentence two states the main result, contribution, or implication from the abstract.",
      "selection_reason": "One sentence explaining quality, relevance, or representativeness."
    }
  ],
  "not_enough": false,
  "notes": ""
}
```

Root keys are limited to `date`, `selected`, `not_enough`, and `notes`.
Selected item keys are limited to `id`, `two_sentence_summary`, and `selection_reason`.

## Eligibility

Reject candidates that are only weakly related to BCI/EEG. A candidate is eligible when the abstract is truly about at least one of:

- Brain-computer interfaces, brain-machine interfaces, neural interfaces, or neuroprosthetics.
- Neural decoding, EEG decoding, motor imagery, SSVEP, P300, closed-loop neural systems, or invasive/non-invasive neural signal interfaces.
- Clinical EEG work with strong signal-processing or monitoring relevance, such as epileptiform detection, ICU continuous EEG monitoring, sleep staging, seizure prediction, or neurological decoding.
- Foundation models, representation learning, or signal processing for EEG/neural data when the abstract shows direct BCI/clinical EEG relevance.

Reject candidates where EEG is incidental, only a side measurement, or merely appears in keywords without meaningful analysis.

## Ranking Rubric

Rank candidates by these priorities:

1. Venue quality: peer-reviewed journal over preprint; `venue_tier=1` over `2`, `3`, or null.
2. True relevance: core BCI/neural interface/neural decoding over broad neuroscience or incidental EEG.
3. Information density: prefer abstracts with clear method, data/task, result, and implication.
4. Diversity: cover different subareas when possible, such as motor imagery, SSVEP/P300, decoding methods, clinical EEG, invasive interfaces, and EEG foundation models.
5. Version preference: when the same study appears as both formal publication and preprint, choose the formal publication.
6. Source cap: select no more than 2 papers from any source.

Use venue tier as a deterministic signal, not as the only decision. A highly relevant tier-2 paper can outrank a less relevant tier-1 paper.

## Summary Writing

Write exactly two sentences for `two_sentence_summary`.

- Sentence 1: what the paper did, including method/task/population only when stated in the abstract.
- Sentence 2: key result, contribution, or implication only when stated or directly supported by the abstract.
- Do not introduce numeric values unless the same numeric value appears in the abstract.
- Do not claim clinical readiness, superiority, benchmark leadership, sample sizes, accuracy, or effect sizes unless the abstract explicitly says so.
- If the abstract is vague, write a cautious summary rather than filling gaps.

Write one sentence for `selection_reason`, grounded in:

- venue quality,
- direct BCI/EEG relevance,
- representativeness of a subarea,
- methodological interest, or
- clinical/practical importance.

## Not Enough Handling

If fewer than 4 candidates are genuinely relevant and worth including:

- Set `not_enough` to `true`.
- Include only the candidates that pass the quality and relevance bar, even if that means `selected` has 0-3 items.
- Explain the shortage in `notes`, for example: "Only three candidates were directly relevant to BCI/clinical EEG; the remaining pool used EEG incidentally or lacked sufficient abstract detail."
- Do not pad the list with marginal papers.

If 4-6 candidates pass the bar, set `not_enough` to `false` and keep `notes` empty or use it only for source failures that affected selection.

## Final Check

Before considering the curation complete:

1. Confirm every selected `id` appears in `candidates`.
2. Confirm no selected object contains title, authors, DOI, URL, venue, date, institution, source, or other hard metadata.
3. Confirm no source contributes more than 2 selected papers.
4. Run `scripts/validate_selection.py` from the skill directory or via an absolute path.
