import json

import pytest

from bci_tracker.render import RenderError, render_markdown


def pool():
    candidates = []
    for idx, source in enumerate(["pubmed", "pubmed", "arxiv", "biorxiv"], start=1):
        candidates.append(
            {
                "id": f"p{idx}",
                "source": source,
                "title": f"Title {idx}",
                "authors": ["Author A"],
                "affiliations": ["Lab A"],
                "corresponding_institution": None,
                "venue": "Journal of Neural Engineering" if source == "pubmed" else f"preprint:{source}",
                "venue_tier": 2 if source == "pubmed" else None,
                "doi": f"10.1/p{idx}",
                "url": f"https://doi.org/10.1/p{idx}",
                "published_date": "2026-06-01",
                "abstract": "This abstract studies BCI and EEG decoding.",
                "matched_keywords": ["BCI", "EEG"],
                "raw": {},
            }
        )
    return {
        "date": "2026-06-05",
        "window": {"start": "2026-05-29", "end": "2026-06-05", "tz": "Asia/Shanghai"},
        "sources": {
            "pubmed": {"status": "ok", "hit": 2, "kept": 2},
            "arxiv": {"status": "ok", "hit": 1, "kept": 1},
            "biorxiv": {"status": "ok", "hit": 1, "kept": 1},
        },
        "candidates": candidates,
    }


def cfg(tmp_path):
    return {
        "timezone": "Asia/Shanghai",
        "selection": {"total_min": 4, "total_max": 6, "per_source_cap": 2},
        "output": {"dir": str(tmp_path), "final_filename": "out_{date}.md"},
    }


def selection(ids):
    return {
        "date": "2026-06-05",
        "selected": [
            {
                "id": cid,
                "title": "FORGED TITLE",
                "url": "https://forged.example",
                "two_sentence_summary": "Did BCI work. It matters.",
                "selection_reason": "Relevant.",
            }
            for cid in ids
        ],
        "not_enough": False,
        "notes": "",
    }


def test_render_ignores_forged_metadata(tmp_path):
    text = render_markdown(pool(), selection(["p1", "p2", "p3", "p4"]), cfg(tmp_path))
    assert "FORGED TITLE" not in text
    assert "https://forged.example" not in text
    assert "Title 1" in text
    assert "https://doi.org/10.1/p1" in text


def test_render_rejects_unknown_id(tmp_path):
    with pytest.raises(RenderError, match="not found"):
        render_markdown(pool(), selection(["p1", "p2", "p3", "missing"]), cfg(tmp_path))


def test_render_rejects_source_cap(tmp_path):
    data = pool()
    data["candidates"].append({**data["candidates"][0], "id": "p5", "doi": "10.1/p5", "source": "pubmed"})
    with pytest.raises(RenderError, match="cap"):
        render_markdown(data, selection(["p1", "p2", "p3", "p4", "p5"]), cfg(tmp_path))
