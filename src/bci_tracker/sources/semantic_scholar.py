from __future__ import annotations

from typing import Any, Dict, List

from bci_tracker.dates import Window, parse_date
from bci_tracker.http import HttpClient
from bci_tracker.schema import Candidate, candidate_id
from bci_tracker.sources.base import Source, matched_terms


BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


class SemanticScholarSource(Source):
    name = "semantic_scholar"

    def fetch(self, window: Window, cfg: Dict[str, Any]) -> List[Candidate]:
        client = HttpClient(cfg)
        params = {
            "query": "brain-computer interface EEG neural decoding",
            "fields": "title,authors,abstract,venue,publicationDate,externalIds,url",
            "limit": "30",
        }
        response = client.get(BASE_URL, params=params)
        return parse_semantic_scholar(response.json().get("data", []), cfg, window)


def parse_semantic_scholar(records: list[dict[str, Any]], cfg: Dict[str, Any], window: Window | None = None) -> List[Candidate]:
    terms = cfg.get("keywords", {}).get("local_filter_terms", [])
    candidates: list[Candidate] = []
    for record in records:
        title = record.get("title") or ""
        abstract = record.get("abstract") or ""
        found_terms = matched_terms(title, abstract, terms)
        if terms and not found_terms:
            continue
        publication_date = record.get("publicationDate") or ""
        parsed = parse_date(publication_date)
        if window and parsed and not window.contains(parsed):
            continue
        external = record.get("externalIds") or {}
        doi = external.get("DOI") or external.get("doi")
        paper_id = record.get("paperId") or title.lower()
        authors = [a.get("name", "") for a in record.get("authors") or [] if a.get("name")]
        candidates.append(
            Candidate(
                id=candidate_id(doi, f"semantic_scholar:{paper_id}"),
                source="semantic_scholar",
                title=title,
                authors=authors,
                affiliations=[],
                corresponding_institution=None,
                venue=record.get("venue") or "",
                venue_tier=None,
                doi=doi,
                url=record.get("url") or (f"https://doi.org/{doi}" if doi else ""),
                published_date=publication_date,
                abstract=abstract,
                matched_keywords=found_terms,
                raw=record,
            )
        )
    return candidates
