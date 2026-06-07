from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def sample_config(tmp_path):
    return {
        "timezone": "Asia/Shanghai",
        "window_days": 7,
        "sources": {"pubmed": True, "biorxiv": True, "medrxiv": True, "arxiv": True},
        "keywords": {
            "pubmed_term": "brain-computer interface",
            "arxiv_search_query": "all:brain-computer interface",
            "local_filter_terms": ["brain-computer interface", "BCI", "EEG", "motor imagery", "SSVEP"],
        },
        "biorxiv": {"category": "neuroscience"},
        "journal_tiers": {
            "tier1": ["Brain"],
            "tier2": ["Journal of Neural Engineering", "NeuroImage"],
        },
        "selection": {"total_min": 3, "total_max": 10},
        "ncbi": {"tool": "bci_tracker", "email": "test@example.com"},
        "http": {"rate_limit_per_sec": 1000, "timeout_seconds": 1, "max_retries": 0},
        "output": {
            "dir": str(tmp_path),
            "candidates_filename": "bci_candidates_{date}.json",
            "selection_filename": "selection_{date}.json",
            "final_filename": "bci_papers_raw_{date}.md",
        },
    }
