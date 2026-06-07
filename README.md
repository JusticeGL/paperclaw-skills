# bci-tracker

`bci-tracker` is a deterministic BCI/EEG paper tracking CLI. It fetches recent paper candidates, normalizes them, deduplicates cross-source records, attaches deterministic venue-tier signals, and renders a final Markdown digest from a model-produced `selection_{date}.json`.

The language model is only allowed to write selected IDs, two-sentence summaries, and one-sentence selection reasons. Final metadata is always pulled from the candidate pool during `render`.

## Commands

```bash
python3 -m bci_tracker.cli --config config.yaml fetch
python3 -m bci_tracker.cli --config config.yaml fetch --dry-run
python3 -m bci_tracker.cli --config config.yaml render --date YYYY-MM-DD
```

For local development without installing the package:

```bash
PYTHONPATH=src python3 -m bci_tracker.cli fetch --dry-run
PYTHONPATH=src pytest
```

## OpenClaw

The OpenClaw scenario lives at `openclaw/scenarios/bci-daily-paper-tracker.md`.
The curation skill lives at `openclaw/skills/bci-paper-curation`.
