import json

from bci_tracker.cli import main


def config_text(output_dir):
    return f"""
timezone: Asia/Shanghai
window_days: 3
sources: {{}}
keywords: {{}}
selection:
  total_min: 1
  total_max: 10
output:
  dir: "{output_dir}"
  candidates_filename: "bci_candidates_{{date}}.json"
  selection_filename: "selection_{{date}}.json"
  final_filename: "bci_papers_raw_{{date}}.md"
  cleanup_intermediate_json: true
"""


def candidate_pool():
    return {
        "date": "2026-06-08",
        "window": {"start": "2026-06-05", "end": "2026-06-08", "tz": "Asia/Shanghai"},
        "sources": {"arxiv": {"status": "ok", "hit": 1, "kept": 1}},
        "candidates": [
            {
                "id": "p1",
                "source": "arxiv",
                "title": "EEG decoding paper",
                "authors": ["Author A"],
                "affiliations": [],
                "corresponding_institution": None,
                "venue": "preprint:arXiv",
                "venue_tier": None,
                "doi": None,
                "url": "https://example.test/p1",
                "published_date": "2026-06-08",
                "abstract": "This abstract studies EEG decoding.",
                "matched_keywords": ["EEG"],
                "raw": {},
            }
        ],
    }


def selection():
    return {
        "date": "2026-06-08",
        "selected": [
            {
                "id": "p1",
                "two_sentence_summary": "This paper studies EEG decoding. It is relevant.",
                "selection_reason": "It is included for a CLI cleanup test.",
            }
        ],
        "not_enough": False,
        "notes": "",
    }


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_default_render_removes_intermediate_json(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(config_text(tmp_path), encoding="utf-8")
    candidates = tmp_path / "bci_candidates_2026-06-08.json"
    selection_file = tmp_path / "selection_2026-06-08.json"
    write_json(candidates, candidate_pool())
    write_json(selection_file, selection())

    assert main(["--config", str(config), "render", "--date", "2026-06-08"]) == 0

    assert not candidates.exists()
    assert not selection_file.exists()
    assert (tmp_path / "bci_papers_raw_2026-06-08.md").exists()


def test_explicit_render_paths_preserve_intermediate_json(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(config_text(tmp_path), encoding="utf-8")
    candidates = tmp_path / "custom_candidates.json"
    selection_file = tmp_path / "custom_selection.json"
    output = tmp_path / "custom.md"
    write_json(candidates, candidate_pool())
    write_json(selection_file, selection())

    assert (
        main(
            [
                "--config",
                str(config),
                "render",
                "--date",
                "2026-06-08",
                "--candidates",
                str(candidates),
                "--selection",
                str(selection_file),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    assert candidates.exists()
    assert selection_file.exists()
    assert output.exists()
