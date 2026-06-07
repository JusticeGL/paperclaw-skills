from datetime import date
from pathlib import Path

import pytest
import requests

from bci_tracker.dates import compute_window
from bci_tracker.sources.arxiv import build_search_query, get_arxiv_response, parse_arxiv_atom
from bci_tracker.sources.base import SourceError


def test_arxiv_parse_extracts_entry(tmp_path, sample_config):
    atom = (Path(__file__).parent / "fixtures/arxiv.atom").read_text(encoding="utf-8")
    window = compute_window("Asia/Shanghai", 7, today=date(2026, 6, 5))
    candidates = parse_arxiv_atom(atom, sample_config, window)
    assert len(candidates) == 1
    item = candidates[0]
    assert item.id == "2606.00001v1"
    assert item.authors == ["Alex Example"]
    assert item.affiliations == ["Example AI Lab"]
    assert item.raw["categories"] == ["eess.SP"]


def test_arxiv_query_adds_submitted_date_window():
    window = compute_window("Asia/Shanghai", 7, today=date(2026, 6, 5))
    query = build_search_query("cat:eess.SP AND abs:EEG", window)
    assert query == "(cat:eess.SP AND abs:EEG) AND submittedDate:[202605280000 TO 202606062359]"


def test_arxiv_error_feed_is_rejected(tmp_path, sample_config):
    error_feed = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/api/errors#bad_query</id>
        <title>Error</title>
        <summary>bad query syntax</summary>
      </entry>
    </feed>
    """
    with pytest.raises(SourceError, match="bad query syntax"):
        parse_arxiv_atom(error_feed, sample_config)


def test_arxiv_atom_fallback_categories_are_recorded(tmp_path, sample_config):
    atom_feed = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>oai:arXiv.org:2606.00002v1</id>
        <published>2026-06-04T00:00:00Z</published>
        <updated>2026-06-04T00:00:00Z</updated>
        <title>EEG decoding for brain-computer interface control</title>
        <summary>This paper studies EEG decoding for brain-computer interface control.</summary>
        <author><name>Fallback Author</name></author>
        <link href="https://arxiv.org/abs/2606.00002v1" rel="alternate" type="text/html"/>
      </entry>
    </feed>
    """
    window = compute_window("Asia/Shanghai", 7, today=date(2026, 6, 5))
    candidates = parse_arxiv_atom(atom_feed, sample_config, window, fallback_categories=["eess.SP"])
    assert len(candidates) == 1
    assert candidates[0].id == "2606.00002v1"
    assert candidates[0].url == "https://arxiv.org/abs/2606.00002v1"
    assert candidates[0].raw["categories"] == ["eess.SP"]


def test_arxiv_response_retries_request_exceptions(monkeypatch):
    class Response:
        status_code = 200
        text = "<feed/>"
        headers = {}

    class Session:
        def __init__(self):
            self.calls = 0

        def get(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise requests.ReadTimeout("slow arxiv")
            return Response()

    class Client:
        timeout = 1
        session = Session()

        class rate_limiter:
            @staticmethod
            def wait():
                return None

    monkeypatch.setattr("bci_tracker.sources.arxiv.time.sleep", lambda _seconds: None)
    response = get_arxiv_response(Client(), {"search_query": "all:EEG"}, {"retry_delays_seconds": [0]})
    assert response.status_code == 200
    assert Client.session.calls == 2
