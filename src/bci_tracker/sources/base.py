from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from bci_tracker.dates import Window
from bci_tracker.schema import Candidate


class SourceError(RuntimeError):
    pass


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self, window: Window, cfg: Dict[str, Any]) -> List[Candidate]:
        raise NotImplementedError


def matched_terms(title: str, abstract: str, terms: list[str]) -> list[str]:
    text = f"{title} {abstract}".lower()
    found = []
    for term in terms:
        if term.lower() in text:
            found.append(term)
    return found
