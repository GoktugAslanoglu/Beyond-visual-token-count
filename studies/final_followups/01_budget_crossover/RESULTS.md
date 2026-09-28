# Fixed-budget retrieval results — completed and audited

All 540 planned calls passed audit: 30 base cases x three lengths x two modalities x three readers. No outputs were replaced; no generation reached the 64-token cap.

Primary outcome: native single-answer containment. Each cell contains 30 paired cases.

| Reader | Length | Budgeted text | Efficient optical |
|---|---|---:|---:|
| Qwen2B | short | 30/30 | 27/30 |
| Qwen2B | medium | 22/30 | 22/30 |
| Qwen2B | long | 18/30 | 16/30 |
| Qwen9B | short | 30/30 | 30/30 |
| Qwen9B | medium | 22/30 | 27/30 |
| Qwen9B | long | 18/30 | 22/30 |
| GLM | short | 30/30 | 30/30 |
| GLM | medium | 24/30 | 29/30 |
| GLM | long | 19/30 | 28/30 |

## Prespecified paired tests

Effects and intervals are percentage points. CIs are pointwise 95% paired-bootstrap intervals; p-values are exact two-sided tests, Holm-adjusted separately for the three primary interactions and three secondary LONG comparisons.

| Reader | Interaction: LONG delta minus SHORT delta | 95% CI | Primary Holm p | LONG optical minus text | 95% CI | Secondary Holm p |
|---|---:|---|---:|---:|---|---:|
| Qwen2B | +3.3 | [-20.0, +26.7] | 1.000000 | -6.7 | [-30.0, +16.7] | 0.775391 |
| Qwen9B | +13.3 | [-10.0, +36.7] | 0.775391 | +13.3 | [-10.0, +36.7] | 0.775391 |
| GLM | +30.0 | [+10.0, +50.0] | 0.035156 | +30.0 | [+10.0, +50.0] | 0.035156 |

## Interpretation

GLM shows a statistically supported LONG-regime optical advantage over this predetermined budgeted-text policy: 28/30 versus 19/30, +30 points, interval [+10,+50], Holm p=0.03515625. Its primary interaction also passes, but the identical SHORT outcomes make these related quantities, not two independent replications.

No reader meets the frozen descriptive crossover definition. Qwen9B and GLM tie text at SHORT; Qwen2B starts below text and does not overtake at LONG. Qwen9B has a descriptive LONG optical advantage, but its test and interval do not support a statistical advantage. Qwen2B likewise shows no supported LONG optical advantage or relative improvement. Nonsignificance does not establish equivalence.

This supports a reader-specific finite-budget advantage for GLM on this synthetic retrieval task, relative to hash-retained raw text. It does not establish superiority over text with retrieval, other retention policies, full text at a larger budget, or other tasks/readers. No latency, memory, FLOPs, energy or cost advantage follows. Case n=30 and the primary sign-symmetry assumption limit generalization.

The image includes all source spans while the predetermined text policy removes some complete records at MEDIUM/LONG. This is the intended finite-budget treatment, not matched-evidence retrieval. Realized C and exact budgets are retained per row.

## Figure and provenance

Figure: results/budget_crossover.pdf. All 18 plotted points were independently checked against scored rows; the rendered PDF passed visual review. Exact source-length ranges are in analysis.json. Inputs remain immutable in ../checkpoints/cpu_1790114103802037991/prepared/01_budget_crossover/FREEZE.json. Full output verification and independent scores are recorded in results/audit.json and rows.jsonl.

No scientific protocol amendment was required. A transport-only loading fallback was prepared after a pre-inference file lookup failure; scientific input and execution freezes remained unchanged. The manuscript and cross-study integration remain unchanged until geometry and systems profiling also pass their audits.
