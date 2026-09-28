# Systems profiling — completed and audited

All 585 planned single-token invocations and 585 top-level model forwards passed audit: 135 warm-ups excluded from summaries, 450 measured runs, 45 cells with ten measured repetitions each. No quality-evaluation calls were added.

## Same complete long source

Medians on A100 40GB, resident BF16/SDPA model, cleared allocator. Times include the frozen preprocessing workflow and one generated token.

| Reader | Full text end-to-end (s) | Optical C2 (s) | Optical C4 (s) | Full text peak (GiB) | C2 peak (GiB) | C4 peak (GiB) |
|---|---:|---:|---:|---:|---:|---:|
| Qwen2B | 1.119 | 1.316 | 0.845 | 5.067 | 4.864 | 4.516 |
| Qwen9B | 2.101 | 1.897 | 1.110 | 19.537 | 18.771 | 18.221 |
| GLM | 0.795 | 1.110 | 0.717 | 20.462 | 20.081 | 19.654 |

At LONG, C2 reduces total allocated peak memory for all three readers. C2 lowers measured combined model prefill time for all three, but after rendering/processing it is faster end-to-end only for Qwen9B; Qwen2B and GLM are slower. C4 has lower measured LONG latency and peak memory for all three readers, but C4 retrieval accuracy is not measured in this new study. No reliability-preserving advantage or Pareto claim follows.

## Same hard-budget setting, long source

| Reader | Budgeted text end-to-end (s) | Optical end-to-end (s) | Text packing (s) | Optical rendering (s) | Text model prefill (s) | Optical model prefill (s) | Text peak (GiB) | Optical peak (GiB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2B | 2.725 | 1.309 | 2.119 | 0.406 | 0.593 | 0.737 | 4.617 | 4.864 |
| Qwen9B | 3.262 | 1.889 | 2.130 | 0.410 | 1.113 | 1.310 | 18.581 | 18.771 |
| GLM | 2.176 | 1.163 | 1.718 | 0.389 | 0.442 | 0.669 | 19.906 | 20.140 |

In the fixed-budget MEDIUM and LONG conditions, optical has lower measured end-to-end latency but higher combined model prefill time and higher allocated peak memory than budgeted text for every reader. The end-to-end difference is substantially driven by the text retention implementation: it repeatedly tokenizes candidate record subsets while packing. At SHORT, text is faster end-to-end and uses less allocated memory.

## Scope and interpretation limits

- These are exact measured workflow comparisons, not proof that optical processing is inherently faster. Optical rendering starts from a precomputed frozen layout plan; layout planning and native side/budget calibration are excluded. Text retention is recomputed inside the measured interval. Reusing the already prepared text or optimizing the packer could materially change the end-to-end ranking; neither alternative was measured and no rerun is proposed.
- Prefill includes the vision encoder, language-model first forward and synchronization/hook overhead. Pipeline TTFT includes representation preparation, native processor and transfer work. Generation length is exactly one token.
- Allocated/reserved GPU peaks include the resident model and any persistent runtime state. Baselines are retained per run. Curves use per-panel scales that need not start at zero; interpret numeric differences, not apparent visual slopes across readers.
- Only predetermined case cross-000 supplies each source length. Ten repetitions describe timing variability for that source on that machine, not ten independent task samples. IQR bands are dispersion summaries, not confidence intervals or significance tests.
- View B uses the same frozen inputs as the crossover study, whose 30-case accuracy estimates are a different sample aggregation. View A full-text/C2/C4 timing points have no corresponding new quality evaluation. Do not attach the original RULER accuracy to them.
- No FLOPs, energy or monetary cost measurements exist. No cross-reader or cross-backend speed generalization, resource-free compression claim, or Pareto claim is warranted.

Full per-cell accounting, preprocessing, processor time, combined prefill, both TTFT definitions, end-to-end time, allocated/reserved peaks, baselines, medians, IQRs and extrema are in analysis.json. FULL_SYSTEMS_TABLE.md gives all 45 cells. Raw repetitions remain in rows.jsonl and immutable checkpoints.

All numerical summaries were independently recomputed; all 135 plotted points and three PDF renders passed review. No scientific protocol amendment or inference rerun was required. Manuscript integration remains gated on completion and audit of the geometry study.
