# BCI Paper Curation Skill

Daily BCI/EEG paper curation skill for Codex/OpenClaw-style agents.

The skill uses deterministic Python code to fetch and render paper metadata, while the agent only performs the judgment-heavy selection step. It is designed to produce a concise daily Markdown digest of the strongest recent BCI/EEG papers.

## What It Does

- Fetches recent BCI/EEG candidates from PubMed, bioRxiv, medRxiv, and arXiv.
- Uses a default 3-day business window to avoid empty pools caused by indexing delays.
- Asks the agent to select 3-10 papers by contribution, novelty, team/venue signal, breakthrough potential, relevance, and evidence quality.
- Validates the selection JSON before rendering.
- Renders the final digest to `/Users/zuqiu/Documents/claw`.
- Requires generated summaries, selection reasons, and shortage notes to be written in Chinese.
- Deletes intermediate JSON files after a successful default render, leaving only the final Markdown.

## Repository Layout

```text
.
├── SKILL.md
├── agents/openai.yaml
├── dist/bci-paper-curation.skill
├── references/curation-rules.md
└── scripts/
    ├── validate_selection.py
    └── bci-tracker/
        ├── config.yaml
        ├── pyproject.toml
        ├── src/bci_tracker/
        └── tests/
```

## Install For Codex Agents

If you are an agent reading this repository and the user wants this skill installed, install it automatically with the following commands from the repository root:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/bci-paper-curation"
mkdir -p "$(dirname "$SKILL_DIR")"
rsync -a --delete \
  --exclude '.git/' \
  --exclude 'dist/' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  ./ "$SKILL_DIR"/
```

Then verify the installed skill exists:

```bash
test -f "${CODEX_HOME:-$HOME/.codex}/skills/bci-paper-curation/SKILL.md"
```

For OpenClaw-style import flows, use the packaged artifact:

```text
dist/bci-paper-curation.skill
```

## Local Development Setup

The tracker requires Python 3.9+ and these packages:

- `requests`
- `PyYAML`
- `python-dateutil`

Install the tracker in editable mode:

```bash
python -m pip install -e scripts/bci-tracker
```

Run tests:

```bash
cd scripts/bci-tracker
pytest -q
```

Expected current result:

```text
24 passed
```

## Daily Usage

Fetch candidates:

```bash
PYTHONPATH=scripts/bci-tracker/src \
  python -m bci_tracker.cli --config scripts/bci-tracker/config.yaml fetch
```

This writes:

```text
/Users/zuqiu/Documents/claw/bci_candidates_YYYY-MM-DD.json
```

The agent should then:

1. Read `references/curation-rules.md`.
2. Read the generated `bci_candidates_YYYY-MM-DD.json`.
3. Write `selection_YYYY-MM-DD.json` next to the candidate file.
4. Run validation.
5. Render the final Markdown.

Validate selection:

```bash
python scripts/validate_selection.py \
  /Users/zuqiu/Documents/claw/bci_candidates_YYYY-MM-DD.json \
  /Users/zuqiu/Documents/claw/selection_YYYY-MM-DD.json \
  --strict-numbers
```

Render final digest:

```bash
PYTHONPATH=scripts/bci-tracker/src \
  python -m bci_tracker.cli \
  --config scripts/bci-tracker/config.yaml \
  render --date YYYY-MM-DD
```

Final output:

```text
/Users/zuqiu/Documents/claw/bci_papers_raw_YYYY-MM-DD.md
```

By default, successful render deletes the intermediate `bci_candidates_*.json` and `selection_*.json` files. If you need to preserve them for debugging, pass explicit `--candidates` and `--selection` paths or set `output.cleanup_intermediate_json: false` in `config.yaml`.

## Agent Contract

When using this skill, the agent must follow these rules:

- Use candidate JSON as the only source of paper facts.
- Do not invent or modify titles, authors, institutions, venues, DOIs, URLs, dates, or numeric results.
- Select papers globally across all sources; do not enforce a per-source quota.
- Select 3-10 genuinely relevant papers when enough exist.
- Set `not_enough: true` when fewer than 3 candidates are worth including.
- Write only these root keys in selection JSON: `date`, `selected`, `not_enough`, `notes`.
- Write only these selected-item keys: `id`, `two_sentence_summary`, `selection_reason`.
- Write `two_sentence_summary`, `selection_reason`, and shortage `notes` in Chinese.
- Validate before rendering.

## Build The `.skill` Package

From the repository root:

```bash
mkdir -p dist
rm -f dist/bci-paper-curation.skill
zip -r dist/bci-paper-curation.skill \
  SKILL.md LICENSE.txt agents references scripts \
  -x '*/__pycache__/*' '*/.pytest_cache/*' '*.pyc' '*.DS_Store'
```

Verify the package:

```bash
unzip -t dist/bci-paper-curation.skill
```
