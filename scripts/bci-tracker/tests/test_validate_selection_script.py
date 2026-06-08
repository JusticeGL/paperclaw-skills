import argparse
import importlib.util
import json
from pathlib import Path


VALIDATOR_PATH = Path(__file__).resolve().parents[2] / "validate_selection.py"
spec = importlib.util.spec_from_file_location("validate_selection", VALIDATOR_PATH)
validate_selection = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validate_selection)


def test_sentence_count_handles_decimals_and_abbreviations():
    assert (
        validate_selection.sentence_count(
            "The model reached 0.5 accuracy. It outperformed baselines."
        )
        == 2
    )
    assert (
        validate_selection.sentence_count(
            "The paper used i.e. Utah arrays in cortex. Decoding worked."
        )
        == 2
    )
    assert (
        validate_selection.sentence_count(
            "The method used e.g. EEG features. It reported 1.5 mm spacing."
        )
        == 2
    )


def test_sentence_count_handles_initialisms():
    assert validate_selection.sentence_count("The study used U.S. data. It validated EEG.") == 2
    assert validate_selection.sentence_count("The study was run in the U.S. It validated EEG.") == 2


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validator_args(candidates, selection):
    return argparse.Namespace(
        candidates=candidates,
        selection=selection,
        total_min=1,
        total_max=10,
        strict_numbers=True,
    )


def candidate_doc():
    return {
        "date": "2026-06-08",
        "candidates": [
            {
                "id": "p1",
                "abstract": "This abstract studies EEG decoding for brain-computer interfaces.",
            }
        ],
    }


def test_validate_accepts_chinese_generated_prose(tmp_path):
    candidates = tmp_path / "candidates.json"
    selection = tmp_path / "selection.json"
    write_json(candidates, candidate_doc())
    write_json(
        selection,
        {
            "date": "2026-06-08",
            "selected": [
                {
                    "id": "p1",
                    "two_sentence_summary": "这项研究分析了用于脑机接口的 EEG 解码方法。摘要显示其贡献在于改进神经信号建模流程。",
                    "selection_reason": "该论文与 BCI 和 EEG 解码主题直接相关。",
                }
            ],
            "not_enough": False,
            "notes": "",
        },
    )

    errors, warnings = validate_selection.validate(validator_args(candidates, selection))

    assert errors == []
    assert warnings == []


def test_validate_rejects_english_generated_prose(tmp_path):
    candidates = tmp_path / "candidates.json"
    selection = tmp_path / "selection.json"
    write_json(candidates, candidate_doc())
    write_json(
        selection,
        {
            "date": "2026-06-08",
            "selected": [
                {
                    "id": "p1",
                    "two_sentence_summary": "This paper studies EEG decoding. It is relevant.",
                    "selection_reason": "It is directly relevant to BCI.",
                }
            ],
            "not_enough": False,
            "notes": "",
        },
    )

    errors, _warnings = validate_selection.validate(validator_args(candidates, selection))

    assert "selected[0].two_sentence_summary must be written in Chinese" in errors
    assert "selected[0].selection_reason must be written in Chinese" in errors
