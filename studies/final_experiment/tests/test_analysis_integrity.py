"""Adversarial offline-analysis fixtures, unrelated to all evaluation cases."""
import copy
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze import analyze_rows


def synthetic_rows():
    rows = []
    for i in range(150):
        position = ("early", "middle", "late")[i // 50]
        for arm in ("optical", "hash_text", "compact_text"):
            optical = arm == "optical"
            vision = 3844 if optical else 0
            rows.append({"case_id": f"invented-analysis-fixture-{i:03}", "arm": arm,
                         "position": position, "success": 0, "target_included": True,
                         "cap_hit": False, "generated_tokens": 1,
                         "canonical_em": 0, "literal_em": 0, "cer": 1.0,
                         "abstention": False, "source_native_tokens": 8000,
                         "stored_native_tokens": 8000 if optical else 3500,
                         "total_input_tokens": 3900, "vision_tokens": vision,
                         "nonvision_input_tokens": 3900 - vision,
                         "records_retained": 400 if optical else 200,
                         "source_records": 400})
    return rows


def set_successes(rows, arm, indices):
    wanted = {f"invented-analysis-fixture-{i:03}" for i in indices}
    for row in rows:
        if row["arm"] == arm and row["case_id"] in wanted:
            row.update(success=1, canonical_em=1, literal_em=1, cer=0.)


def test_reject_missing_output_instead_of_reducing_n():
    with pytest.raises((AssertionError, ValueError)):
        analyze_rows(synthetic_rows()[:-1])


def test_reject_duplicate_even_when_total_rows_is_450():
    rows = synthetic_rows()
    rows[-1] = copy.deepcopy(rows[0])
    with pytest.raises((AssertionError, ValueError)):
        analyze_rows(rows)


def test_reject_missing_arm_disguised_as_an_unknown_arm():
    rows = synthetic_rows()
    rows[-1]["arm"] = "unplanned_text_policy"
    with pytest.raises((AssertionError, ValueError)):
        analyze_rows(rows)


def test_reject_wrong_case_inventory_even_when_cells_unique():
    rows = synthetic_rows()
    rows[-1]["case_id"] = "invented-extra-case"
    with pytest.raises((AssertionError, ValueError)):
        analyze_rows(rows)


@pytest.mark.parametrize("arm,invalid", [("optical", .5), ("compact_text", .5),
                                         ("hash_text", 2), ("hash_text", -1),
                                         ("hash_text", float("nan"))])
def test_reject_nonbinary_success_before_any_numeric_coercion(arm, invalid):
    rows = synthetic_rows()
    next(row for row in rows if row["arm"] == arm)["success"] = invalid
    with pytest.raises((AssertionError, ValueError, TypeError)):
        analyze_rows(rows)


def test_reject_disagreement_between_arms_about_case_stratum():
    rows = synthetic_rows()
    rows[1]["position"] = "late"  # optical says early for the same case
    with pytest.raises((AssertionError, ValueError)):
        analyze_rows(rows)


def test_reject_wrong_position_mixture():
    rows = synthetic_rows()
    for row in rows:
        if row["case_id"] == "invented-analysis-fixture-000":
            row["position"] = "middle"
    with pytest.raises((AssertionError, ValueError)):
        analyze_rows(rows)


@pytest.mark.parametrize("field,invalid", [("target_included", "False"),
                                           ("cap_hit", "False"),
                                           ("abstention", 1),
                                           ("canonical_em", 2),
                                           ("literal_em", -.1),
                                           ("cer", float("nan")),
                                           ("cer", -1.)])
def test_reject_invalid_secondary_data_instead_of_publishing_it(field, invalid):
    rows = synthetic_rows()
    rows[1][field] = invalid
    with pytest.raises((AssertionError, ValueError, TypeError)):
        analyze_rows(rows)


@pytest.mark.parametrize("winning_arm,classification", [
    ("optical", "optical_superiority"), ("compact_text", "compact_text_superiority")])
def test_primary_direction_and_exact_significance_boundary(winning_arm, classification):
    rows = synthetic_rows()
    set_successes(rows, winning_arm, range(5))
    five = analyze_rows(rows)
    assert five["primary"]["p"] == .0625
    assert five["primary"]["classification"] == "inconclusive"
    set_successes(rows, winning_arm, [5])
    six = analyze_rows(rows)
    assert six["primary"]["p"] == .03125
    assert six["primary"]["classification"] == classification
    assert math.copysign(1, six["primary"]["effect"]) == (1 if winning_arm == "optical" else -1)
    assert six["practical_collapse_flag"] is True  # significance need not imply usefulness


def test_zero_discordances_stays_inconclusive_with_nondegenerate_sensitivity():
    rows = synthetic_rows()
    set_successes(rows, "optical", range(150))
    set_successes(rows, "compact_text", range(150))
    result = analyze_rows(rows)
    p = result["primary"]
    assert p["gains"] == p["losses"] == p["effect"] == 0
    assert p["ties"] == 150 and p["p"] == 1 and p["classification"] == "inconclusive"
    assert p["bootstrap"]["degenerate_interval"] is True
    assert p["conservative_ci"]["low"] < 0 < p["conservative_ci"]["high"]
    assert result["no_equivalence_test"] is True


def test_hash_arm_cannot_change_primary_test_or_classification():
    rows = synthetic_rows()
    set_successes(rows, "optical", range(12))
    baseline = analyze_rows(rows)
    set_successes(rows, "hash_text", range(150))
    result = analyze_rows(rows)
    assert result["primary"] == baseline["primary"]
    assert result["primary"]["alpha"] == .05
    assert result["primary"]["multiplicity"] == "one confirmatory contrast"
    assert result["descriptive_differences"] != baseline["descriptive_differences"]
    assert set(result["descriptive_differences"]) == {"optical_minus_hash_text", "compact_minus_hash_text"}


def test_omitted_target_success_is_retained_and_empty_conditionals_are_na():
    rows = synthetic_rows()
    for row in rows:
        if row["arm"] == "hash_text":
            row["target_included"] = False
    set_successes(rows, "hash_text", [0])
    result = analyze_rows(rows)
    summary = result["arms"]["hash_text"]
    assert summary["successes"] == summary["omitted_successes"] == 1
    assert summary["conditional_recovery"] is None
    assert summary["omitted_success_rate"] == 1 / 150
    assert result["arms"]["optical"]["omitted_success_rate"] is None


def test_row_order_does_not_change_paired_estimate():
    rows = synthetic_rows()
    set_successes(rows, "optical", range(20))
    set_successes(rows, "compact_text", range(10, 24))
    assert analyze_rows(rows) == analyze_rows(list(reversed(rows)))


def test_analysis_entry_rejects_scores_bound_to_another_result_audit(tmp_path, monkeypatch):
    import analyze as module
    from experiment_common import put, sha
    put(tmp_path / "FREEZE.json", {"synthetic_fixture": True})
    put(tmp_path / "audit/RESULT_AUDIT.json", {"status": "passed", "freeze_sha256": sha(tmp_path / "FREEZE.json")})
    scores = tmp_path / "scores.json"
    put(scores, {"freeze_sha256": sha(tmp_path / "FREEZE.json"),
                 "audit_sha256": "wrong-audit-identity", "rows": synthetic_rows()})
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "verify_freeze", lambda: None)
    output = tmp_path / "results.json"
    with pytest.raises((AssertionError, ValueError, RuntimeError)):
        module.main(scores, output)
    assert not output.exists()
