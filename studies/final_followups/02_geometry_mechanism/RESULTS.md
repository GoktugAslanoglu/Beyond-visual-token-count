# Controlled geometry-scale results — completed and audited

All 288 planned quality calls passed audit: 32 fresh cases x three scales x three readers. Source content, line wrapping, pagination, question, canvas and native input-token counts are fixed within each reader/case triplet. The treatment uniformly scales the rendered block and occupied area.

| Reader | Scale 0.55 EM /32 | Scale 0.75 EM /32 | Scale 1.00 EM /32 | Exact Q statistic | Raw primary p | Holm primary p |
|---|---:|---:|---:|---:|---:|---:|
| Qwen2B | 0 | 3 | 2 | 4.666667 | 0.22222222 | 0.25880201 |
| Qwen9B | 3 | 10 | 14 | 10.941176 | 0.00367717 | 0.01103150 |
| GLM | 0 | 4 | 5 | 5.250000 | 0.12940101 | 0.25880201 |

Qwen9B passes the prespecified three-reader primary family. Qwen2B and GLM do not; their nonsignificance is not evidence of equivalence or zero effect. Qwen2B accuracy is not monotone in the tested scales.

## Secondary paired comparisons

Effects/intervals are percentage points; gains/losses count paired cases. Holm adjustment covers all nine secondary comparisons. CIs are pointwise paired-bootstrap intervals, not multiplicity-adjusted.

| Reader | Comparison | Effect | 95% CI | Gains / losses | Holm p |
|---|---|---:|---|---:|---:|
| Qwen2B | scale_1.00 minus scale_0.55 | +6.250 | [+0.000, +15.625] | 2 / 0 | 1.00000000 |
| Qwen2B | scale_1.00 minus scale_0.75 | -3.125 | [-9.375, +0.000] | 0 / 1 | 1.00000000 |
| Qwen2B | scale_0.75 minus scale_0.55 | +9.375 | [+0.000, +21.875] | 3 / 0 | 1.00000000 |
| Qwen9B | scale_1.00 minus scale_0.55 | +34.375 | [+15.625, +53.125] | 12 / 1 | 0.03076172 |
| Qwen9B | scale_1.00 minus scale_0.75 | +12.500 | [-9.375, +34.375] | 8 / 4 | 1.00000000 |
| Qwen9B | scale_0.75 minus scale_0.55 | +21.875 | [+6.250, +37.500] | 8 / 1 | 0.31250000 |
| GLM | scale_1.00 minus scale_0.55 | +15.625 | [+3.125, +28.125] | 5 / 0 | 0.43750000 |
| GLM | scale_1.00 minus scale_0.75 | +3.125 | [-12.500, +18.750] | 4 / 3 | 1.00000000 |
| GLM | scale_0.75 minus scale_0.55 | +12.500 | [+3.125, +25.000] | 4 / 0 | 0.75000000 |

Only Qwen9B scale 1.00 minus 0.55 passes the secondary family: +34.375 points, interval [+15.625,+53.125], 12 gains/1 loss, Holm p=0.03076171875. An omnibus difference does not establish a monotonic law, and glyph size is not uniquely isolated from occupied area, resampling and location changes produced by uniform scaling.

## CER and generation limits

CER is edit distance divided by reference length; extra output can make it exceed 1. It is a diagnostic, not the primary outcome.

| Reader | CER at 0.55 | CER at 0.75 | CER at 1.00 | Cap hits at 0.55 / 0.75 / 1.00 |
|---|---:|---:|---:|---|
| Qwen2B | 1.962240 | 1.131510 | 1.260417 | 4 / 1 / 2 |
| Qwen9B | 1.006510 | 0.355469 | 0.135417 | 2 / 1 / 0 |
| GLM | 1.638021 | 0.945312 | 0.520833 | 0 / 0 / 0 |

Ten responses reached the frozen 64-token cap (Qwen2B 7, Qwen9B 3, GLM 0). They are retained and scored under the same rules. No cap extension, outcome replacement or exclusion occurred. The effect concerns exact recovery under this decoding configuration and is not a pure measurement of visual perception.

## Scientific conclusion

Strengthen the mechanism claim only to a controlled rendered-block scale/occupied-area effect for Qwen9B in this task. Preserve the earlier matched-budget layout-package finding for all three readers. This new intervention does not establish that scale alone explains the earlier package effect in Qwen2B or GLM. Do not compare the earlier and fresh-case percentages as if they were a randomized treatment contrast.

The frozen exact-Q dynamic-programming p-values were independently reproduced with multinomial allocation enumeration. Counts and all nine figure points were verified; the PDF render passed visual review. See results/INDEPENDENT_NUMBER_AND_FIGURE_CHECK.json and results/geometry_scale.pdf. No scientific protocol amendment was required. All final-round inference is now complete.
