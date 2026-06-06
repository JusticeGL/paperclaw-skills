from __future__ import annotations

import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import requests

from bci_tracker.dates import Window, to_local_date
from bci_tracker.http import HttpClient
from bci_tracker.schema import Candidate
from bci_tracker.sources.base import Source, SourceError, matched_terms


BASE_URL = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"


class ArxivSource(Source):
    name = "arxiv"

    def fetch(self, window: Window, cfg: Dict[str, Any]) -> List[Candidate]:
        client = HttpClient(cfg)
        arxiv_cfg = cfg.get("arxiv", {})
        params = {
            "search_query": build_search_query(cfg["keywords"]["arxiv_search_query"], window),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": "0",
            "max_results": str(arxiv_cfg.get("max_results", 50)),
        }
        try:
            response = get_arxiv_response(client, params, arxiv_cfg)
            return parse_arxiv_atom(response.text, cfg, window)
        except SourceError as exc:
            if not arxiv_cfg.get("rss_fallback", True):
                raise
            fallback = fetch_atom_fallback(client, cfg, window, arxiv_cfg)
            for candidate in fallback:
                candidate.raw = {**candidate.raw, "fallback": "arxiv_atom_feed", "api_error": str(exc)}
            return fallback


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def arxiv_id_from_url(url: str) -> str:
    if url.startswith("oai:arXiv.org:"):
        return url.rsplit(":", 1)[-1]
    return url.rstrip("/").split("/")[-1]


def build_search_query(base_query: str, window: Window) -> str:
    compact = clean_text(base_query)
    start = window.padded_start.strftime("%Y%m%d") + "0000"
    end = window.padded_end.strftime("%Y%m%d") + "2359"
    return f"({compact}) AND submittedDate:[{start} TO {end}]"


def retry_delays(arxiv_cfg: Dict[str, Any]) -> list[float]:
    configured = arxiv_cfg.get("retry_delays_seconds")
    if configured is None:
        return [3.0, 10.0, 30.0]
    return [float(value) for value in configured]


def get_arxiv_response(client: HttpClient, params: Dict[str, str], arxiv_cfg: Dict[str, Any]):
    delays = retry_delays(arxiv_cfg)
    initial_delay = float(arxiv_cfg.get("initial_delay_seconds", 0))
    timeout = float(arxiv_cfg.get("timeout_seconds", client.timeout))
    if initial_delay > 0:
        time.sleep(initial_delay)

    last_status = None
    last_text = ""
    last_error = ""
    attempts = len(delays) + 1
    for attempt in range(attempts):
        client.rate_limiter.wait()
        try:
            response = client.session.get(BASE_URL, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt == attempts - 1:
                break
            time.sleep(delays[attempt])
            continue
        last_status = response.status_code
        last_text = response.text[:300]
        if response.status_code == 200:
            return response
        if response.status_code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
            break
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            delay = float(retry_after)
        else:
            delay = delays[attempt]
        time.sleep(delay)
    detail = f"status={last_status}, body={last_text!r}" if last_status else f"error={last_error}"
    raise SourceError(f"arXiv API failed after {attempts} attempts: {detail}")


def feed_categories(arxiv_cfg: Dict[str, Any]) -> list[str]:
    configured = arxiv_cfg.get("rss_categories")
    if configured:
        return [str(item) for item in configured]
    return ["eess.SP", "cs.HC", "q-bio.NC", "cs.LG"]


def fetch_atom_fallback(
    client: HttpClient,
    cfg: Dict[str, Any],
    window: Window,
    arxiv_cfg: Dict[str, Any],
) -> list[Candidate]:
    categories = feed_categories(arxiv_cfg)
    url = "https://rss.arxiv.org/atom/" + "+".join(categories)
    response = client.get(url)
    return parse_arxiv_atom(response.text, cfg, window, fallback_categories=categories)


def is_error_feed(root: ET.Element) -> str | None:
    entries = root.findall(f"{ATOM}entry")
    if len(entries) != 1:
        return None
    title = clean_text(entries[0].findtext(f"{ATOM}title")).lower()
    entry_id = clean_text(entries[0].findtext(f"{ATOM}id")).lower()
    if title == "error" or "/api/errors" in entry_id:
        return clean_text(entries[0].findtext(f"{ATOM}summary")) or "arXiv API returned an error feed"
    return None


def parse_arxiv_atom(
    xml_text: str,
    cfg: Dict[str, Any],
    window: Window | None = None,
    fallback_categories: list[str] | None = None,
) -> List[Candidate]:
    root = ET.fromstring(xml_text)
    error = is_error_feed(root)
    if error:
        raise SourceError(f"arXiv API error: {error}")
    terms = cfg.get("keywords", {}).get("local_filter_terms", [])
    candidates: list[Candidate] = []
    for entry in root.findall(f"{ATOM}entry"):
        entry_id = clean_text(entry.findtext(f"{ATOM}id"))
        title = clean_text(entry.findtext(f"{ATOM}title"))
        abstract = clean_text(entry.findtext(f"{ATOM}summary"))
        found_terms = matched_terms(title, abstract, terms)
        if terms and not found_terms:
            continue
        published_raw = clean_text(entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated"))
        local_date = to_local_date(published_raw, window.tz if window else "Asia/Shanghai")
        if window and local_date and not window.contains(local_date):
            continue
        authors: list[str] = []
        affiliations: list[str] = []
        for author in entry.findall(f"{ATOM}author"):
            name = clean_text(author.findtext(f"{ATOM}name"))
            if name:
                authors.append(name)
            aff = clean_text(author.findtext(f"{ARXIV}affiliation"))
            if aff and aff not in affiliations:
                affiliations.append(aff)
        pdf_url = ""
        abs_url = entry_id if entry_id.startswith("http") else ""
        for link in entry.findall(f"{ATOM}link"):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href", "")
            elif link.attrib.get("rel") == "alternate" and link.attrib.get("href"):
                abs_url = link.attrib["href"]
        categories = [node.attrib.get("term", "") for node in entry.findall(f"{ATOM}category")]
        if not categories and fallback_categories:
            categories = list(fallback_categories)
        arxiv_id = arxiv_id_from_url(entry_id)
        candidates.append(
            Candidate(
                id=arxiv_id,
                source="arxiv",
                title=title,
                authors=authors,
                affiliations=affiliations,
                corresponding_institution=None,
                venue="preprint:arXiv",
                venue_tier=None,
                doi=None,
                url=abs_url or f"https://arxiv.org/abs/{urllib.parse.quote(arxiv_id)}",
                published_date=local_date.isoformat() if local_date else published_raw[:10],
                abstract=abstract,
                matched_keywords=found_terms,
                raw={"pdf_url": pdf_url, "categories": categories, "published": published_raw},
            )
        )
    return candidates
