import importlib.util
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
