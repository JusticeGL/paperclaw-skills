from pathlib import Path

from bci_tracker.sources.pubmed import parse_pubmed_xml


def test_pubmed_parse_extracts_core_fields(tmp_path, sample_config):
    xml = Path("tests/fixtures/pubmed_efetch.xml").read_text(encoding="utf-8")
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
