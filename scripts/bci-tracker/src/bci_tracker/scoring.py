from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from bci_tracker.schema import Candidate


def normalize_venue(venue: str) -> str:
    return re.sub(r"\s+", " ", venue or "").strip().lower()


def tier_map(cfg: Dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    tiers = cfg.get("journal_tiers", {})
    for name in tiers.get("tier1", []):
        result[normalize_venue(name)] = 1
    for name in tiers.get("tier2", []):
        result[normalize_venue(name)] = 2
    return result


def score_candidates(candidates: Iterable[Candidate], cfg: Dict[str, Any]) -> List[Candidate]:
    mapping = tier_map(cfg)
    scored = []
    for candidate in candidates:
        venue_norm = normalize_venue(candidate.venue)
        if venue_norm.startswith("preprint:"):
            candidate.venue_tier = None
        elif venue_norm in mapping:
            candidate.venue_tier = mapping[venue_norm]
        elif candidate.venue:
            candidate.venue_tier = 3
        else:
            candidate.venue_tier = None
        scored.append(candidate)
    return scored
