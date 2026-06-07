from bci_tracker.dedup import dedup_candidates
from bci_tracker.schema import Candidate


def candidate(**overrides):
    data = {
        "id": "x",
        "source": "biorxiv",
        "title": "A BCI study",
        "authors": [],
        "affiliations": [],
        "corresponding_institution": None,
        "venue": "preprint:bioRxiv",
        "venue_tier": None,
        "doi": "10.1/test",
        "url": "https://doi.org/10.1/test",
        "published_date": "2026-06-01",
        "abstract": "short",
        "matched_keywords": ["BCI"],
        "raw": {},
    }
    data.update(overrides)
    return Candidate(**data)


def test_dedup_prefers_formal_publication_over_preprint():
    preprint = candidate(source="biorxiv", venue="preprint:bioRxiv")
    formal = candidate(source="pubmed", venue="Journal of Neural Engineering", abstract="longer formal abstract")
    result = dedup_candidates([preprint, formal])
    assert len(result) == 1
    assert result[0].source == "pubmed"
    assert result[0].raw["also_seen_as"][0]["source"] == "biorxiv"


def test_dedup_merges_near_title_without_doi():
    a = candidate(id="arxiv:1", doi=None, title="Representation learning for EEG BCI decoding")
    b = candidate(id="arxiv:2", doi=None, title="Representation learning for EEG BCI decoding")
    assert len(dedup_candidates([a, b])) == 1
