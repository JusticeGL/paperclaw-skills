from __future__ import annotations

from typing import Any, Dict, List

from bci_tracker.dates import Window, parse_date
from bci_tracker.http import HttpClient
from bci_tracker.schema import Candidate, candidate_id
from bci_tracker.sources.base import Source, matched_terms


BASE_URL = "https://api.biorxiv.org"


class _CshlSource(Source):
    server = ""
    name = ""

    def fetch(self, window: Window, cfg: Dict[str, Any]) -> List[Candidate]:
        candidates, total = self._fetch_pages(window, cfg, with_category=True)
        if self.server == "biorxiv" and total == 0:
            candidates, _ = self._fetch_pages(window, cfg, with_category=False)
        return candidates

    def _fetch_pages(self, window: Window, cfg: Dict[str, Any], with_category: bool) -> tuple[List[Candidate], int]:
        client = HttpClient(cfg)
        all_records: list[dict[str, Any]] = []
        cursor = 0
        while True:
            url = f"{BASE_URL}/details/{self.server}/{window.padded_start.isoformat()}/{window.padded_end.isoformat()}/{cursor}/json"
            params = {}
            if self.server == "biorxiv" and with_category:
                category = cfg.get("biorxiv", {}).get("category")
                if category:
                    params["category"] = str(category).replace(" ", "_").lower()
            response = client.get(url, params=params)
            data = response.json()
            records = data.get("collection") or []
            if not records:
                break
            all_records.extend(records)
            if len(records) < 100:
                break
            cursor += 100
        return parse_cshl_records(all_records, self.server, cfg, window), len(all_records)


class BioRxivSource(_CshlSource):
    server = "biorxiv"
    name = "biorxiv"


class MedRxivSource(_CshlSource):
    server = "medrxiv"
    name = "medrxiv"


def parse_authors(authors: str | None) -> list[str]:
    if not authors:
        return []
    return [part.strip() for part in authors.split(";") if part.strip()]


def parse_cshl_records(
    records: list[dict[str, Any]],
    server: str,
    cfg: Dict[str, Any],
    window: Window | None = None,
) -> List[Candidate]:
    terms = cfg.get("keywords", {}).get("local_filter_terms", [])
    candidates: list[Candidate] = []
    for record in records:
        title = (record.get("title") or "").strip()
        abstract = (record.get("abstract") or "").strip()
        found_terms = matched_terms(title, abstract, terms)
        if terms and not found_terms:
            continue
        published_date = str(record.get("date") or "")
        parsed = parse_date(published_date)
        if window and parsed and not window.contains(parsed):
            continue
        doi = (record.get("doi") or "").strip() or None
        venue = f"preprint:{'bioRxiv' if server == 'biorxiv' else 'medRxiv'}"
        published = record.get("published")
        if published and published != "NA":
            venue = str(published)
        url = f"https://doi.org/{doi}" if doi else str(record.get("url") or "")
        candidates.append(
            Candidate(
                id=candidate_id(doi, f"{server}:{record.get('version', '')}:{title.lower()}"),
                source=server,
                title=title,
                authors=parse_authors(record.get("authors")),
                affiliations=[],
                corresponding_institution=record.get("author_corresponding_institution") or None,
                venue=venue,
                venue_tier=None,
                doi=doi,
                url=url,
                published_date=published_date,
                abstract=abstract,
                matched_keywords=found_terms,
                raw=record,
            )
        )
    return candidates
