"""Prospective paired statistics; no model loading or held-out output access.

All contrasts are first minus second. Exact McNemar is the sole primary test.
Bootstrap intervals are descriptive and may degenerate at sample boundaries;
the conservative paired interval supplies a nondegenerate sensitivity interval.
"""
from __future__ import annotations

import argparse
import json
import math
import operator
from pathlib import Path

import numpy as np


def _nonnegative_int(value, name):
    try:
        result = operator.index(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def exact_mcnemar(gains: int, losses: int) -> float:
    """Two-sided conditional exact McNemar, doubled smaller binomial tail."""
    gains = _nonnegative_int(gains, "gains")
    losses = _nonnegative_int(losses, "losses")
    discordant = gains + losses
    if discordant == 0:
        return 1.0
    numerator = 2 * sum(math.comb(discordant, k) for k in range(min(gains, losses) + 1))
    return min(1.0, numerator / (1 << discordant))


def _paired_arrays(first, second):
    first = np.asarray(first)
    second = np.asarray(second)
    if first.ndim != 1 or second.ndim != 1 or len(first) != len(second) or not len(first):
        raise ValueError("Paired binary arrays must be nonempty, one-dimensional, and equally long")
    if not np.isin(first, [0, 1]).all() or not np.isin(second, [0, 1]).all():
        raise ValueError("Both arrays must contain only binary 0/1 scores")
    return first.astype(np.int8), second.astype(np.int8)


def paired_counts(first, second) -> dict:
    first, second = _paired_arrays(first, second)
    gains = int(((first == 1) & (second == 0)).sum())
    losses = int(((first == 0) & (second == 1)).sum())
    return {
        "n": len(first),
        "first_correct": int(first.sum()),
        "second_correct": int(second.sum()),
        "gains": gains,
        "losses": losses,
        "both_correct": int(((first == 1) & (second == 1)).sum()),
        "both_incorrect": int(((first == 0) & (second == 0)).sum()),
        "effect": (gains - losses) / len(first),
        "exact_mcnemar_two_sided_p": exact_mcnemar(gains, losses),
    }


def stratified_paired_bootstrap(first, second, strata, *, seed: int,
                               resamples: int = 50_000, alpha: float = .05) -> dict:
    """Resample paired cases within fixed strata, retaining each stratum's size.

    With the planned 150-case design, each early/middle/late stratum has n=50.
    Strata are equally weighted when equally sized; otherwise their original
    sample weights are preserved. Percentile intervals use linear quantiles.
    """
    first, second = _paired_arrays(first, second)
    strata = list(strata)
    if len(strata) != len(first) or not all(isinstance(s, str) and s for s in strata):
        raise ValueError("Each paired case must have a nonempty string stratum")
    resamples = _nonnegative_int(resamples, "resamples")
    if resamples < 2 or not 0 < alpha < 1:
        raise ValueError("Need at least two resamples and 0 < alpha < 1")
    delta = first - second
    labels = sorted(set(strata))
    groups = [delta[np.array([s == label for s in strata])] for label in labels]
    rng = np.random.default_rng(seed)
    effects = np.empty(resamples, dtype=np.float64)
    # Fixed chunk size is part of deterministic numerical execution.
    for start in range(0, resamples, 1000):
        count = min(1000, resamples - start)
        sums = np.zeros(count, dtype=np.int64)
        for group in groups:
            draws = rng.integers(0, len(group), size=(count, len(group)))
            sums += group[draws].sum(axis=1)
        effects[start:start + count] = sums / len(first)
    low, high = np.quantile(effects, [alpha / 2, 1 - alpha / 2], method="linear")
    return {
        "method": "paired case bootstrap within fixed source-position strata; percentile",
        "effect": float(delta.mean()), "low": float(low), "high": float(high),
        "confidence_level": 1 - alpha, "resamples": resamples, "seed": int(seed),
        "stratum_counts": {label: len(group) for label, group in zip(labels, groups)},
        "degenerate_interval": bool(low == high),
        "caveat": "Pointwise descriptive interval; sample-boundary degeneracy is not population certainty or equivalence.",
    }


def _clopper_pearson(successes, n, alpha):
    from scipy.stats import beta
    low = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, n - successes + 1))
    high = 1.0 if successes == n else float(beta.ppf(1 - alpha / 2, successes + 1, n - successes))
    return low, high


def conservative_paired_ci(first, second, *, alpha: float = .05) -> dict:
    """Bonferroni CP bounds for P(gain)-P(loss), accounting for fixed strata.

    For pooled independent identically distributed pairs, simultaneous CP
    intervals for the two multinomial margins guarantee at least 1-alpha
    coverage. The study fixes positions in equal strata: callers wanting an
    interval for the stratified estimand should use stratified_conservative_ci.
    No independence of gain and loss indicators within a pair is assumed.
    """
    if not 0 < alpha < 1:
        raise ValueError("Need 0 < alpha < 1")
    counts = paired_counts(first, second)
    gl, gh = _clopper_pearson(counts["gains"], counts["n"], alpha / 2)
    ll, lh = _clopper_pearson(counts["losses"], counts["n"], alpha / 2)
    return {
        "method": "Bonferroni Clopper-Pearson paired gain/loss margin bounds",
        "effect": counts["effect"], "low": max(-1.0, gl - lh), "high": min(1.0, gh - ll),
        "confidence_level": 1 - alpha, "gain_interval": [gl, gh], "loss_interval": [ll, lh],
        "caveat": "Conservative sensitivity interval; not a second hypothesis test or an equivalence assessment.",
    }


def stratified_conservative_ci(first, second, strata, *, alpha: float = .05) -> dict:
    """Simultaneous CP margin bounds in every fixed stratum, then weighted sum.

    Allocates alpha/(2*K) to each of the two margins in each of K strata.
    The union bound gives at least nominal coverage for the stratified mean
    difference without assuming identical probabilities across positions.
    """
    first, second = _paired_arrays(first, second)
    strata = list(strata)
    if len(strata) != len(first) or not all(isinstance(s, str) and s for s in strata):
        raise ValueError("Each paired case must have a nonempty string stratum")
    if not 0 < alpha < 1:
        raise ValueError("Need 0 < alpha < 1")
    labels = sorted(set(strata))
    intervals = {}
    low = high = 0.0
    for label in labels:
        indices = np.array([s == label for s in strata])
        result = conservative_paired_ci(first[indices], second[indices], alpha=alpha / len(labels))
        weight = float(indices.sum()) / len(first)
        low += weight * result["low"]
        high += weight * result["high"]
        intervals[label] = {"n": int(indices.sum()), "weight": weight, **result}
    return {
        "method": "Bonferroni Clopper-Pearson simultaneous gain/loss bounds within fixed strata",
        "effect": float((first - second).mean()), "low": low, "high": high,
        "confidence_level": 1 - alpha, "strata": intervals,
        "caveat": "Conservative boundary sensitivity, potentially wide; not a second confirmatory test or an equivalence assessment.",
    }


def exact_mcnemar_power(n: int, effect: float, discordance: float, *, alpha: float = .05) -> float:
    """Analytic power by enumerating all multinomial gain/loss/concordance counts.

    P(gain)=(discordance+effect)/2; P(loss)=(discordance-effect)/2.
    Equivalent stable evaluation conditions on M~Binomial(n,discordance), then
    G|M~Binomial(M,P(gain)/discordance). Rejection uses the exact primary test.
    Homogeneous independent pairs are a planning scenario, not a fitted model.
    """
    from scipy.stats import binom
    n = _nonnegative_int(n, "n")
    if not n or not -1 <= effect <= 1 or not 0 <= discordance <= 1 or abs(effect) > discordance or not 0 < alpha < 1:
        raise ValueError("Invalid sample size, effect, discordance, or alpha")
    if discordance == 0:
        return 0.0
    conditional_gain = (discordance + effect) / (2 * discordance)
    power = 0.0
    for m in range(n + 1):
        rejection = np.array([exact_mcnemar(g, m - g) <= alpha for g in range(m + 1)])
        if rejection.any():
            conditional = float(binom.pmf(np.arange(m + 1), m, conditional_gain)[rejection].sum())
            power += float(binom.pmf(m, n, discordance)) * conditional
    return min(1.0, max(0.0, power))


def write_power_grid(path) -> dict:
    rows = []
    for n in [90, 120, 150]:
        for effect in [.05, .10, .15]:
            for discordance in [.15, .25, .35]:
                if abs(effect) <= discordance:
                    rows.append({"n": n, "effect": effect, "discordance": discordance,
                                 "p_gain": (discordance + effect) / 2,
                                 "p_loss": (discordance - effect) / 2,
                                 "power": exact_mcnemar_power(n, effect, discordance)})
    result = {
        "status": "prospective-analytic-planning-no-model-outputs",
        "method": "Enumerate multinomial discordances; two-sided exact McNemar alpha=0.05",
        "assumption": "Independent homogeneous paired binary outcomes; scenarios are hypothetical, not estimated from held-out answers.",
        "selected_design": {"n": 150, "strata": {"early": 50, "middle": 50, "late": 50}},
        "caveat": "Small effects may remain inconclusive. More calls are not authorized after observing outcomes.",
        "scenarios": rows,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write prospective exact power scenarios without model inference")
    parser.add_argument("--power-output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "development" / "POWER.json")
    args = parser.parse_args()
    write_power_grid(args.power_output)
    print(f"Wrote prospective power grid: {args.power_output}")
