from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Candidate:
    id: str
    source: str
    title: str
    authors: List[str]
    affiliations: List[str]
    corresponding_institution: Optional[str]
    venue: str
    venue_tier: Optional[int]
    doi: Optional[str]
    url: str
    published_date: str
    abstract: str
    matched_keywords: List[str]
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Candidate":
        return cls(
            id=str(data["id"]),
            source=str(data["source"]),
            title=str(data.get("title") or ""),
            authors=list(data.get("authors") or []),
            affiliations=list(data.get("affiliations") or []),
            corresponding_institution=data.get("corresponding_institution"),
            venue=str(data.get("venue") or ""),
            venue_tier=data.get("venue_tier"),
            doi=data.get("doi"),
            url=str(data.get("url") or ""),
            published_date=str(data.get("published_date") or ""),
            abstract=str(data.get("abstract") or ""),
            matched_keywords=list(data.get("matched_keywords") or []),
            raw=dict(data.get("raw") or {}),
        )


def candidate_id(doi: Optional[str], fallback: str) -> str:
    if doi:
        cleaned = doi.strip().lower()
        if cleaned:
            return cleaned
    return fallback
