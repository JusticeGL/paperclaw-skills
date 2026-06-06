from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, List

from bci_tracker.dates import parse_date
from bci_tracker.schema import Candidate


def normalize_title(title: str) -> str:
    text = title.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_preprint(candidate: Candidate) -> bool:
    return candidate.venue.lower().startswith("preprint:")


def preferred(existing: Candidate, incoming: Candidate) -> Candidate:
    if is_preprint(existing) and not is_preprint(incoming):
        return incoming
    if is_preprint(incoming) and not is_preprint(existing):
        return existing
    if len(incoming.abstract or "") > len(existing.abstract or ""):
        return incoming
    return existing


def merge_records(primary: Candidate, secondary: Candidate) -> Candidate:
    also_seen = list(primary.raw.get("also_seen_as", []))
    also_seen.append(secondary.to_dict())
    primary.raw = {**primary.raw, "also_seen_as": also_seen}
    for attr in ["authors", "affiliations", "matched_keywords"]:
        merged = []
        for value in getattr(primary, attr) + getattr(secondary, attr):
            if value not in merged:
                merged.append(value)
        setattr(primary, attr, merged)
    if not primary.doi and secondary.doi:
        primary.doi = secondary.doi
    if not primary.url and secondary.url:
        primary.url = secondary.url
    if not primary.corresponding_institution and secondary.corresponding_institution:
        primary.corresponding_institution = secondary.corresponding_institution
    return primary


def dates_near(a: Candidate, b: Candidate, max_days: int = 30) -> bool:
    da = parse_date(a.published_date)
    db = parse_date(b.published_date)
    if not da or not db:
        return True
    return abs((da - db).days) <= max_days


def title_match(a: Candidate, b: Candidate, threshold: float = 0.94) -> bool:
    ta = normalize_title(a.title)
    tb = normalize_title(b.title)
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    return SequenceMatcher(None, ta, tb).ratio() >= threshold and dates_near(a, b)


def dedup_candidates(candidates: Iterable[Candidate]) -> List[Candidate]:
    by_doi: dict[str, Candidate] = {}
    no_doi: list[Candidate] = []

    for candidate in candidates:
        if candidate.doi:
            key = candidate.doi.strip().lower()
            if key in by_doi:
                chosen = preferred(by_doi[key], candidate)
                other = candidate if chosen is by_doi[key] else by_doi[key]
                by_doi[key] = merge_records(chosen, other)
            else:
                by_doi[key] = candidate
        else:
            no_doi.append(candidate)

    merged = list(by_doi.values())
    for candidate in no_doi:
        matched = False
        for idx, existing in enumerate(merged):
            if title_match(existing, candidate):
                chosen = preferred(existing, candidate)
                other = candidate if chosen is existing else existing
                merged[idx] = merge_records(chosen, other)
                matched = True
                break
        if not matched:
            merged.append(candidate)

    return sorted(merged, key=lambda c: (c.published_date, c.title), reverse=True)
