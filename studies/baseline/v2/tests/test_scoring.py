import importlib.util
from pathlib import Path
import pytest
from studies.baseline.v2.runtime.scoring import score, token_f1, canonical_answer, ruler_native_aggregate

V2 = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_locomo_oracle", V2 / "vendor/locomo_metrics.py")
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


@pytest.mark.parametrize("prediction,reference", [
    ("", ""), ("the and", "a"), ("Blue", "blue"), ("running cars", "run car"),
    ("red red blue", "red blue blue"), ("answer: Paris\nmore words", "Paris"),
    ("<|begin_of_box|>Paris<|end_of_box|>", "Paris"), ("```Paris```", "Paris"),
    ('{"answer":"Paris"}', "Paris"), ("No information available.", "Paris"),
    ("ABC-123_4", "ABC1234"), ("an\u0301 apple", "apple"),
    ("not mentioned", "not mentioned"), ("23 July, 2023", " 23 July, 2023"),
])
def test_native_locomo_against_extracted_upstream(prediction, reference):
    assert token_f1(prediction, reference) == pytest.approx(oracle.f1_score(prediction, reference))
    for category in (1, 2, 4):
        expected = oracle.f1(prediction, reference) if category == 1 else oracle.f1_score(prediction, reference)
        assert score(prediction, reference, "locomo", category)["native"]["f1"] == pytest.approx(expected)


def test_multihop_native_matching():
    assert score("Berlin, Paris", "Paris, Berlin, Rome", "locomo", 1)["native"]["f1"] == pytest.approx(2/3)


@pytest.mark.parametrize("raw", ["wrong\nABC", "Answer: ABC", '"ABC"', "```ABC```",
                                  '{"answer":"ABC"}', "<think>x</think>ABC",
                                  "<|begin_of_box|>ABC", "ABC\nexplanation"])
def test_no_prediction_repair(raw):
    assert score(raw, "ABC", "controlled")["canonical"]["exact_match"] == 0


def test_views_and_box_boundary():
    raw = "  <|begin_of_box|>ABC<|end_of_box|> \n"
    result = score(raw, "ABC", "controlled")
    assert result["native"]["exact_match"] == 0
    assert result["canonical"]["exact_match"] == 1
    assert canonical_answer("<|begin_of_box|>A<|end_of_box|><|begin_of_box|>B<|end_of_box|>").startswith("<|")
    assert score("abc", "ABC", "controlled")["canonical"]["exact_match"] == 0
    assert score("ABCD", "ABC", "controlled")["canonical"]["cer"] == pytest.approx(1/3)


def test_ruler_native_aggregate_against_primary_source_excerpt():
    # Independent primary-source implementation, NVIDIA Apache-2.0 metric.
    # https://raw.githubusercontent.com/NVIDIA/RULER/main/scripts/eval/synthetic/constants.py
    def string_match_all(preds, refs):
        value = sum([sum([1.0 if r.lower() in pred.lower() else 0.0 for r in ref]) / len(ref) for pred, ref in zip(preds, refs)]) / len(preds) * 100
        return round(value, 2)
    predictions = ["prefix ABC suffix", "wrong", "v1 V2", ""]
    references = [["abc"], ["x"], ["v1", "v2", "v3"], ["x"]]
    assert ruler_native_aggregate(predictions, references) == string_match_all(predictions, references)
    assert ruler_native_aggregate(predictions, references) == 41.67
    row = score("prefix ABC suffix", {"task_id": "niah_single_3", "answers": ["ABC"]}, "ruler")
    assert row["native"]["answer_containment_fraction"] == 1
    assert row["native"]["exact_match"] == 0


def test_ruler_multivalue_has_no_invented_exact_metric():
    result = score("a", {"task_id": "niah_multivalue", "answers": ["a", "b"]}, "ruler")
    assert result["native"] == {"answer_containment_fraction": .5}
    with pytest.raises(ValueError):
        ruler_native_aggregate(["a"], [])
    with pytest.raises(ValueError):
        score("", {"task_id": "vt", "answers": []}, "ruler")
