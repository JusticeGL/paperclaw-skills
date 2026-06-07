import json
from datetime import date
from pathlib import Path

from bci_tracker.dates import compute_window
from bci_tracker.sources.biorxiv import parse_cshl_records


def test_biorxiv_parse_filters_by_local_terms(tmp_path, sample_config):
    data = json.loads((Path(__file__).parent / "fixtures/biorxiv.json").read_text(encoding="utf-8"))
    window = compute_window("Asia/Shanghai", 7, today=date(2026, 6, 5))
    candidates = parse_cshl_records(data["collection"], "biorxiv", sample_config, window)
    assert len(candidates) == 1
    assert candidates[0].source == "biorxiv"
    assert candidates[0].corresponding_institution == "Example Institute of Neuroscience"
    assert candidates[0].venue == "preprint:bioRxiv"
