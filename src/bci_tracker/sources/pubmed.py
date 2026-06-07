from __future__ import annotations

import html
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any, Dict, List

from bci_tracker.dates import Window, parse_date
from bci_tracker.http import HttpClient
from bci_tracker.schema import Candidate, candidate_id
from bci_tracker.sources.base import Source, matched_terms


BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedSource(Source):
    name = "pubmed"

    def fetch(self, window: Window, cfg: Dict[str, Any]) -> List[Candidate]:
        client = HttpClient(cfg)
        ncbi = cfg.get("ncbi", {})
        term = cfg["keywords"]["pubmed_term"]
        params = {
            "db": "pubmed",
            "datetype": "pdat",
            "mindate": entrez_date(window.start),
            "maxdate": entrez_date(window.end),
            "retmode": "json",
            "retmax": "50",
            "term": term,
            "tool": ncbi.get("tool", "bci_tracker"),
            "email": ncbi.get("email", ""),
        }
        response = client.get(f"{BASE_URL}/esearch.fcgi", params=params)
        ids = response.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        fetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "tool": ncbi.get("tool", "bci_tracker"),
            "email": ncbi.get("email", ""),
        }
        detail = client.get(f"{BASE_URL}/efetch.fcgi", params=fetch_params)
        return filter_window(parse_pubmed_xml(detail.text, cfg), window)


def entrez_date(value: date) -> str:
    return value.strftime("%Y/%m/%d")


def filter_window(candidates: List[Candidate], window: Window) -> List[Candidate]:
    kept = []
    for candidate in candidates:
        parsed = parse_date(candidate.published_date)
        if parsed and window.contains(parsed):
            kept.append(candidate)
    return kept


def text_content(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join(part.strip() for part in element.itertext() if part and part.strip())


def first_text(parent: ET.Element, path: str) -> str:
    return text_content(parent.find(path))


def pubdate(article: ET.Element) -> str:
    pub = article.find(".//JournalIssue/PubDate")
    if pub is None:
        pub = article.find(".//ArticleDate")
    if pub is None:
        return ""
    year = first_text(pub, "Year")
    month = first_text(pub, "Month") or "01"
    day = first_text(pub, "Day") or "01"
    medline = first_text(pub, "MedlineDate")
    if year:
        parsed = parse_date(f"{year} {month} {day}")
        return parsed.isoformat() if parsed else year
    parsed = parse_date(medline)
    return parsed.isoformat() if parsed else medline


def article_ids(article: ET.Element) -> dict[str, str]:
    ids: dict[str, str] = {}
    for item in article.findall(".//ArticleId"):
        id_type = (item.attrib.get("IdType") or "").lower()
        if item.text and id_type:
            ids[id_type] = item.text.strip()
    for item in article.findall(".//ELocationID"):
        id_type = (item.attrib.get("EIdType") or "").lower()
        if item.text and id_type and id_type not in ids:
            ids[id_type] = item.text.strip()
    return ids


def parse_authors(article: ET.Element) -> tuple[list[str], list[str]]:
    authors: list[str] = []
    affiliations: list[str] = []
    for author in article.findall(".//AuthorList/Author"):
        collective = first_text(author, "CollectiveName")
        if collective:
            authors.append(collective)
        else:
            last = first_text(author, "LastName")
            fore = first_text(author, "ForeName") or first_text(author, "Initials")
            name = ", ".join(part for part in [last, fore] if part)
            if name:
                authors.append(name)
        for aff in author.findall("./AffiliationInfo/Affiliation"):
            text = text_content(aff)
            if text and text not in affiliations:
                affiliations.append(text)
    return authors, affiliations


def abstract_text(article: ET.Element) -> str:
    parts = []
    for node in article.findall(".//Abstract/AbstractText"):
        label = node.attrib.get("Label")
        text = text_content(node)
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    return html.unescape(" ".join(parts))


def parse_pubmed_xml(xml_text: str, cfg: Dict[str, Any]) -> List[Candidate]:
    root = ET.fromstring(xml_text)
    terms = cfg.get("keywords", {}).get("local_filter_terms", [])
    candidates: list[Candidate] = []
    for article in root.findall(".//PubmedArticle"):
        medline = article.find("./MedlineCitation")
        article_node = article.find(".//Article")
        if article_node is None:
            continue
        pmid = first_text(article, ".//PMID")
        title = html.unescape(text_content(article_node.find("./ArticleTitle")))
        abstract = abstract_text(article_node)
        authors, affiliations = parse_authors(article_node)
        ids = article_ids(article)
        doi = ids.get("doi")
        url = f"https://doi.org/{urllib.parse.quote(doi, safe='/')}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        venue = first_text(article_node, "./Journal/Title")
        published = pubdate(article_node)
        cid = candidate_id(doi, f"pubmed:{pmid}")
        found_terms = matched_terms(title, abstract, terms)
        if terms and not found_terms:
            found_terms = matched_terms(title, abstract, ["brain-computer interface", "EEG", "neural"])
        candidates.append(
            Candidate(
                id=cid,
                source="pubmed",
                title=title,
                authors=authors,
                affiliations=affiliations,
                corresponding_institution=None,
                venue=venue,
                venue_tier=None,
                doi=doi,
                url=url,
                published_date=published,
                abstract=abstract,
                matched_keywords=found_terms,
                raw={"pmid": pmid, "medline_status": medline.attrib.get("Status") if medline is not None else None},
            )
        )
    return candidates
