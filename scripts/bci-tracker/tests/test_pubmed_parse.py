from datetime import date
from pathlib import Path

from bci_tracker.dates import compute_window
from bci_tracker.sources.pubmed import PubMedSource, filter_window, parse_pubmed_xml


def test_pubmed_parse_extracts_core_fields(tmp_path, sample_config):
    xml = (Path(__file__).parent / "fixtures/pubmed_efetch.xml").read_text(encoding="utf-8")
    candidates = parse_pubmed_xml(xml, sample_config)
    assert len(candidates) == 1
    item = candidates[0]
    assert item.id == "10.1000/jne.001"
    assert item.title.startswith("Motor imagery EEG decoding")
    assert item.authors == ["Chen, Wei"]
    assert item.affiliations == ["Neural Engineering Lab, Example University."]
    assert item.venue == "Journal of Neural Engineering"
    assert item.published_date == "2026-06-01"
    assert "SIGNIFICANCE" in item.abstract


def test_pubmed_fetch_uses_absolute_window_dates(monkeypatch, sample_config):
    calls = []

    class Response:
        def json(self):
            return {"esearchresult": {"idlist": []}}

    class Client:
        def __init__(self, cfg):
            pass

        def get(self, url, **kwargs):
            calls.append((url, kwargs["params"]))
            return Response()

    monkeypatch.setattr("bci_tracker.sources.pubmed.HttpClient", Client)
    window = compute_window("Asia/Shanghai", 7, today=date(2026, 6, 5))
    assert PubMedSource().fetch(window, sample_config) == []
    params = calls[0][1]
    assert params["mindate"] == "2026/05/29"
    assert params["maxdate"] == "2026/06/05"
    assert "reldate" not in params


def test_pubmed_numeric_article_date_survives_window_filter(sample_config):
    xml = """<PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation Status="MEDLINE">
          <PMID>1</PMID>
          <Article>
            <ArticleDate><Year>2026</Year><Month>06</Month><Day>01</Day></ArticleDate>
            <ArticleTitle>EEG decoding for brain-computer interface control</ArticleTitle>
            <Abstract><AbstractText>EEG decoding for brain-computer interface control.</AbstractText></Abstract>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>"""
    candidates = parse_pubmed_xml(xml, sample_config)
    assert candidates[0].published_date == "2026-06-01"
    window = compute_window("Asia/Shanghai", 7, today=date(2026, 6, 5))
    assert len(filter_window(candidates, window)) == 1
