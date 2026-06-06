from __future__ import annotations

from typing import Iterable, List

from bci_tracker.schema import Candidate


def enrich_candidates(candidates: Iterable[Candidate]) -> List[Candidate]:
    """Best-effort enrichment hook.

    arXiv affiliations are often missing. The current implementation deliberately
    keeps enrichment non-blocking and records that no network enrichment was done.
    """

    enriched: list[Candidate] = []
    for candidate in candidates:
        if candidate.source == "arxiv" and not candidate.affiliations:
            candidate.raw = {**candidate.raw, "enrich": "not_attempted"}
        enriched.append(candidate)
    return enriched
