LoCoMo cluster sensitivity — post-unblinding diagnostic

All effects are optical-minus-comparator F1 points. H1 compares retrieved optical with full optical; H2 compares retrieved optical with identical-evidence retrieved text. Frozen bootstrap intervals remain primary. Sign tests use only the direction of nonzero conversation effects; t intervals assume independent, approximately normal conversation-level effects. Neither sensitivity is automatically superior with only ten histories.

| Reader | Contrast | Primary effect / 95% CI | +/−/ties | Sign p, greater / two-sided | Leave-one-out effect range | Descriptive t 95% CI |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen2B | H1 | +19.05 [+15.79, +22.46] | 10/0/0 | 0.000977 / 0.001953 | [+17.89, +20.01] | [+14.99, +23.11] |
| Qwen2B | H2 | -11.09 [-14.08, -8.27] | 0/10/0 | 1.000000 / 0.001953 | [-12.07, -9.97] | [-14.63, -7.55] |
| Qwen9B | H1 | +19.33 [+14.99, +22.97] | 10/0/0 | 0.000977 / 0.001953 | [+18.61, +20.90] | [+14.41, +24.24] |
| Qwen9B | H2 | -1.94 [-3.76, -0.13] | 1/9/0 | 0.999023 / 0.021484 | [-2.57, -1.40] | [-4.17, +0.29] |
| GLM | H1 | +6.05 [+2.39, +9.48] | 8/2/0 | 0.054688 / 0.109375 | [+5.19, +7.19] | [+1.73, +10.37] |
| GLM | H2 | -6.66 [-9.86, -3.94] | 0/10/0 | 1.000000 / 0.001953 | [-7.39, -5.39] | [-10.29, -3.04] |

For GLM H1, the direction-only sensitivity does not meet a one-sided 0.05 threshold with eight positive and two negative conversations. This qualifies inferential robustness without replacing the frozen sign-flip result or negating the observed average gain. For Qwen9B H2: the point estimate favors text; the prespecified ±3-point equivalence criterion was not met. Avoid claiming a definitive population-wide text advantage from its borderline interval.
