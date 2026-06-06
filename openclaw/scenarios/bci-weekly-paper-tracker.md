---
name: bci-weekly-paper-tracker
description: Run weekly or manual BCI/EEG paper tracking with deterministic fetching/rendering and ChatGPT 5.4 curation.
model: chatgpt-5.4
tools:
  - shell
  - filesystem
schedule: manual_or_weekly
---

# BCI Weekly Paper Tracker

Use this OpenClaw scenario to run the BCI paper tracking pipeline end to end.

## Procedure

1. Start in the `bci-tracker` project root.
2. Run `bci-tracker fetch` with `config.yaml`. Confirm it writes `bci_candidates_{date}.json`.
3. Use `$bci-paper-curation` from `openclaw/skills/bci-paper-curation` to read the candidate pool and write `selection_{date}.json`.
4. Run the skill validator:

   ```bash
   python3 openclaw/skills/bci-paper-curation/scripts/validate_selection.py \
     path/to/bci_candidates_{date}.json \
     path/to/selection_{date}.json
   ```

5. Run `bci-tracker render` only after validation passes.
6. Report only a concise execution summary: candidate count, selected count, failed or skipped sources, whether `not_enough` was triggered, and final Markdown path.

## Guardrails

- Do not paste the full rendered paper digest into chat unless the user explicitly asks.
- Do not hand-edit final Markdown for factual metadata; fix candidates or selection and re-run render.
- If fetch partially fails, continue with available candidates and ensure the final report names failed or skipped sources.
- If validation fails, fix `selection_{date}.json` before rendering.
