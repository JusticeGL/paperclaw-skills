from bci_tracker.schema import Candidate
from bci_tracker.scoring import score_candidates


def candidate(venue):
    return Candidate(
        id=venue,
        source="pubmed",
        title="title",
        authors=[],
        affiliations=[],
        corresponding_institution=None,
        venue=venue,
        venue_tier=None,
        doi=None,
        url="",
        published_date="2026-06-01",
        abstract="",
        matched_keywords=[],
        raw={},
    )


def test_scoring_assigns_tiers(tmp_path, sample_config):
    scored = score_candidates(
        [candidate("Brain"), candidate("NeuroImage"), candidate("Unknown Journal"), candidate("preprint:arXiv")],
        sample_config,
    )
    assert [item.venue_tier for item in scored] == [1, 2, 3, None]
