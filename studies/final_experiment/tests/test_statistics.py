"""Independent arithmetic and design checks; all arrays are invented fixtures."""
import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import binom

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analysis_utils import (conservative_paired_ci, exact_mcnemar, exact_mcnemar_power,
                            paired_counts, stratified_conservative_ci,
                            stratified_paired_bootstrap)


def test_exact_mcnemar_matches_independent_sign_enumeration():
    # Count all equiprobable signs independently, without binomial-tail code.
    for discordant in range(13):
        differences = [abs(sum(signs)) for signs in itertools.product((-1, 1), repeat=discordant)]
        for gains in range(discordant + 1):
            observed = abs(2 * gains - discordant)
            expected = sum(d >= observed for d in differences) / len(differences)
            assert exact_mcnemar(gains, discordant - gains) == pytest.approx(expected, abs=1e-15)


def test_exact_mcnemar_known_discreteness_and_symmetry():
    assert exact_mcnemar(0, 0) == 1
    assert exact_mcnemar(5, 0) == .0625
    assert exact_mcnemar(6, 0) == .03125
    assert exact_mcnemar(10, 1) == .01171875
    assert exact_mcnemar(1, 10) == exact_mcnemar(10, 1)
    assert exact_mcnemar(25, 25) == 1
    with pytest.raises(ValueError):
        exact_mcnemar(-1, 0)
    with pytest.raises(ValueError):
        exact_mcnemar(1.5, 0)


def test_pairing_and_direction_are_preserved():
    first, second = [1, 1, 1, 0, 0], [0, 0, 1, 1, 0]
    result = paired_counts(first, second)
    assert result["gains"] == 2 and result["losses"] == 1
    assert result["both_correct"] == 1 and result["both_incorrect"] == 1
    assert result["effect"] == .2
    assert paired_counts(second, first)["effect"] == -.2
    with pytest.raises(ValueError):
        paired_counts([1, 0], [1])
    with pytest.raises(ValueError):
        paired_counts([2], [0])
    with pytest.raises(ValueError):
        paired_counts([], [])


def test_stratified_bootstrap_keeps_fixed_case_weights():
    # Every stratum is homogeneous. Resampling across strata would create
    # spurious variability; within-stratum resampling must return exactly 0.
    first = [1] * 50 + [0] * 50 + [1] * 50
    second = [0] * 50 + [1] * 50 + [1] * 50
    strata = ["early"] * 50 + ["middle"] * 50 + ["late"] * 50
    result = stratified_paired_bootstrap(first, second, strata, seed=173, resamples=50_000)
    assert result["stratum_counts"] == {"early": 50, "late": 50, "middle": 50}
    assert result["low"] == result["high"] == result["effect"] == 0
    assert result["degenerate_interval"] is True
    sensitivity = stratified_conservative_ci(first, second, strata)
    assert sensitivity["low"] < 0 < sensitivity["high"]


def test_bootstrap_is_deterministic_and_reverses_contrast():
    first = [1, 1, 1, 0, 0] * 6
    second = [0, 0, 1, 1, 0] * 6
    strata = ["early"] * 10 + ["middle"] * 10 + ["late"] * 10
    a = stratified_paired_bootstrap(first, second, strata, seed=902, resamples=2000)
    b = stratified_paired_bootstrap(first, second, strata, seed=902, resamples=2000)
    reverse = stratified_paired_bootstrap(second, first, strata, seed=902, resamples=2000)
    assert a == b
    assert a["low"] == pytest.approx(-reverse["high"])
    assert a["high"] == pytest.approx(-reverse["low"])
    assert a["low"] < a["high"]
    with pytest.raises(ValueError):
        stratified_paired_bootstrap(first, second, ["early"], seed=1)


def test_cp_intervals_do_not_degenerate_at_no_discordance():
    n = 150
    pooled = conservative_paired_ci([1] * n, [1] * n)
    # Each CP marginal gets alpha/2; upper endpoint at zero successes is
    # 1-(alpha/4)**(1/n), an independent closed-form boundary identity.
    high = 1 - (.05 / 4) ** (1 / n)
    assert pooled["low"] == pytest.approx(-high)
    assert pooled["high"] == pytest.approx(high)
    strata = ["early"] * 50 + ["middle"] * 50 + ["late"] * 50
    stratified = stratified_conservative_ci([1] * n, [1] * n, strata)
    expected = 1 - (.05 / 12) ** (1 / 50)
    assert stratified["low"] == pytest.approx(-expected)
    assert stratified["high"] == pytest.approx(expected)
    assert stratified["low"] < pooled["low"] < 0 < pooled["high"] < stratified["high"]


def test_cp_extreme_difference_remains_uncertain():
    result = conservative_paired_ci([1] * 50, [0] * 50)
    assert 0 < result["low"] < result["effect"] == result["high"] == 1
    reverse = conservative_paired_ci([0] * 50, [1] * 50)
    assert reverse["low"] == -result["high"]
    assert reverse["high"] == pytest.approx(-result["low"])


def _direct_multinomial_power(n, effect, discordance):
    pg, pl, pc = (discordance + effect) / 2, (discordance - effect) / 2, 1 - discordance
    result = 0.
    # Direct three-category probability sum, independent from conditional
    # binomial decomposition used by the production power implementation.
    for gains in range(n + 1):
        for losses in range(n - gains + 1):
            concordant = n - gains - losses
            if exact_mcnemar(gains, losses) <= .05:
                coefficient = math.factorial(n) // (math.factorial(gains) * math.factorial(losses) * math.factorial(concordant))
                result += coefficient * pg ** gains * pl ** losses * pc ** concordant
    return result


@pytest.mark.parametrize("effect,discordance", [(.05, .15), (.10, .35), (.15, .15), (0., .25), (-.10, .25)])
def test_power_matches_independent_multinomial_enumeration(effect, discordance):
    expected = _direct_multinomial_power(12, effect, discordance)
    assert exact_mcnemar_power(12, effect, discordance) == pytest.approx(expected, abs=1e-13)


def test_power_boundary_and_null_control():
    # With losses impossible, six or more gains reject the two-sided exact test.
    assert exact_mcnemar_power(20, .15, .15) == pytest.approx(binom.sf(5, 20, .15), abs=1e-13)
    assert exact_mcnemar_power(90, 0., .25) <= .05
    assert exact_mcnemar_power(90, .10, .25) == pytest.approx(exact_mcnemar_power(90, -.10, .25))
    assert exact_mcnemar_power(90, 0., 0.) == 0
    with pytest.raises(ValueError):
        exact_mcnemar_power(90, .20, .15)
