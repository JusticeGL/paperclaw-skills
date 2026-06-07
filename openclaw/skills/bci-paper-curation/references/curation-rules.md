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

Rank all candidates together. Do not apply a per-source cap or reserve slots for any source. Select the strongest 3-10 papers by these priorities:

1. Scientific contribution: prefer work that advances BCI, EEG decoding, neural interfaces, neuroprosthetics, clinical EEG, or enabling methodology in a meaningful way.
2. Innovation: prefer new paradigms, algorithms, datasets, benchmarks, devices, materials, experimental designs, or translational strategies over incremental applications.
3. Breakthrough potential: prioritize results that could reshape a subfield, unlock a practical bottleneck, or materially improve long-term usability, performance, reliability, autonomy, scalability, or clinical translation.
4. Team and venue signals: use author affiliations, corresponding institution, venue tier, and known institutional signals in the metadata as evidence of research-team strength. Do not invent reputation claims that are not supported by the candidate metadata.
5. True relevance: core BCI/neural interface/neural decoding work outranks broad neuroscience or incidental EEG mentions.
6. Evidence quality and information density: prefer abstracts with clear method, task/data, validation, result, and implication.
7. Version preference: when the same study appears as both formal publication and preprint, choose the formal publication.
8. Portfolio value: after ranking by quality, prefer a final set that gives useful coverage of important subareas, but never include a weaker paper merely for source or topic diversity.

Use venue tier as one deterministic signal, not as the only decision. A breakthrough preprint or tier-2 paper can outrank a less relevant tier-1 paper, but the reason must be grounded in the abstract and metadata.

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

If fewer than 3 candidates are genuinely relevant and worth including:

- Set `not_enough` to `true`.
- Include only the candidates that pass the quality and relevance bar, even if that means `selected` has 0-2 items.
- Explain the shortage in `notes`, for example: "Only two candidates were directly relevant and strong enough to include; the remaining pool used EEG incidentally or lacked sufficient abstract detail."
- Do not pad the list with marginal papers.

If 3-10 candidates pass the bar, set `not_enough` to `false` and keep `notes` empty or use it only for source failures that affected selection.

## Final Check

Before considering the curation complete:

1. Confirm every selected `id` appears in `candidates`.
2. Confirm no selected object contains title, authors, DOI, URL, venue, date, institution, source, or other hard metadata.
3. Confirm the final list reflects the strongest overall contribution, novelty, team/venue signal, breakthrough potential, relevance, and evidence quality.
4. Run `scripts/validate_selection.py` from the skill directory or via an absolute path.
