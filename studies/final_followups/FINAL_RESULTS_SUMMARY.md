# Final results: all agreed inference complete

All three studies passed their complete-data audits. All 18 crossover quality cells (30 outputs each), nine geometry quality cells (32 outputs each), and 45 systems cells (three warmups plus ten measured invocations each) completed. There were **828 new quality outputs** (540 crossover + 288 geometry), **585 profiling generation invocations and 585 observed top-level profiling forward passes** (135 warmups + 450 measured), and **1,413 total generation invocations**. Profiling observations are not additional task-accuracy samples. Internal quality-generation forward counts were not measured by this profiling counter.

No scientific protocol amendment, outcome-based tuning, exclusion, cap extension or output replacement occurred. The only post-freeze repair concerned locating/uploading the identical audited CPU archive in Drive. The initial lookup failure occurred before inference. Original scientific code, inputs and sample sizes remained frozen. The user's removal of an automatic calendar stop did not alter the scientific design.

## Experiment 1: fixed-budget retrieval

Primary accuracy uses the frozen native single-answer containment metric. Each entry is text / optical correct out of 30 paired base cases. This is a synthetic retrieval study, not an official benchmark score.

| Reader | SHORT | MEDIUM | LONG |
|---|---:|---:|---:|
| Qwen2B | 30 / 27 | 22 / 22 | 18 / 16 |
| Qwen9B | 30 / 30 | 22 / 27 | 18 / 22 |
| GLM | 30 / 30 | 24 / 29 | 19 / 28 |

Primary interaction is (optical minus text at LONG) minus (optical minus text at SHORT). Effects and pointwise paired-bootstrap 95% intervals are percentage points. Primary exact sign-flip tests use a three-reader Holm family; secondary LONG exact McNemar tests use a separate three-reader Holm family.

| Reader | Primary interaction [95% CI] | Primary Holm p | LONG optical minus text [95% CI] | LONG Holm p |
|---|---|---:|---|---:|
| Qwen2B | +3.33 [-20.00, 26.67] | 1.0000 | -6.67 [-30.00, 16.67] | 0.7754 |
| Qwen9B | +13.33 [-10.00, 36.67] | 0.7754 | +13.33 [-10.00, 36.67] | 0.7754 |
| GLM | +30.00 [10.00, 50.00] | 0.0352 | +30.00 [10.00, 50.00] | 0.0352 |

GLM supports a finite-budget optical advantage over this deterministic query-independent hash-retained text policy. No reader meets the frozen descriptive crossover definition requiring text to be strictly better at SHORT and optical strictly better at LONG: GLM and Qwen9B tie at SHORT. GLM's identical primary/secondary contrasts are not independent replications. This is not superiority to full text, an oracle selector, or a retrieval-based text baseline. Thirty paired cases limit precision; the conditional sign-flip inference uses its frozen sign-symmetry assumptions.

## Experiment 2: controlled rendered-block scale

Canonical exact match is the primary score. Content, question, canvas, wrapping, pagination and native input-token counts are fixed within each triplet.

| Reader | 0.55 correct /32 | 0.75 correct /32 | 1.00 correct /32 | Exact Q | Primary Holm p |
|---|---:|---:|---:|---:|---:|
| Qwen2B | 0 | 3 | 2 | 4.6667 | 0.2588 |
| Qwen9B | 3 | 10 | 14 | 10.9412 | 0.0110 |
| GLM | 0 | 4 | 5 | 5.2500 | 0.2588 |

Exact conditional Q tests use Holm across three readers. Only Qwen9B passes. Its 1.00 minus 0.55 contrast is +34.375 percentage points, pointwise 95% CI [15.625, 53.125], with 12 gains and one loss; exact McNemar Holm p=0.0307617 across nine secondary tests. No other secondary contrast passes. All nine contrasts and CER diagnostics appear in the geometry RESULTS.md.

Ten 64-token cap hits remain unchanged: seven Qwen2B, three Qwen9B, zero GLM. The result describes exact recovery under the frozen decoder. Uniform scaling changes occupied area, glyph size, resampling and physical positions together; it does not isolate glyph height or prove a universal monotonic law. Qwen2B is nonmonotonic, and nonsignificance in two readers is not equivalence. Earlier layout-package findings remain separate evidence.

## Experiment 3: systems measurements

LONG medians on A100 40GB, BF16, batch one and one decoded token. E2E includes representation construction, processor, transfer and model execution, excluding model loading. Peak allocated memory includes the resident model. All 45 cells, IQRs and accounting are in FULL_SYSTEMS_TABLE.md.

| Reader | Same-source full-text / C2 / C4 E2E (s) | Same-source full-text / C2 / C4 peak (GiB) | Fixed-budget text / optical E2E (s) | Fixed-budget text / optical peak (GiB) |
|---|---|---|---|---|
| Qwen2B | 1.119 / 1.316 / 0.845 | 5.067 / 4.864 / 4.516 | 2.725 / 1.309 | 4.617 / 4.864 |
| Qwen9B | 2.101 / 1.897 / 1.110 | 19.537 / 18.771 / 18.221 | 3.262 / 1.889 | 18.581 / 18.771 |
| GLM | 0.795 / 1.110 / 0.717 | 20.462 / 20.081 / 19.654 | 2.176 / 1.163 | 19.906 / 20.140 |

Same-source LONG C2 lowers measured prefill and peak memory for all readers but lowers E2E only for Qwen9B. C4 LONG lowers measured E2E and peak for all readers; its task quality was not evaluated here. Under fixed budgets, optical is faster E2E at MEDIUM/LONG but has higher model prefill and allocated peak than retained text. Text packing repeatedly tokenizes candidates; optical rendering starts from a frozen precomputed layout plan. Thus the E2E advantage depends on this implementation and excludes optical layout planning/calibration. It does not establish an inherent optical speed advantage. Cached or optimized text packing was not measured.

These are repeated timings for one predetermined case per length, not independent task samples. IQRs describe run dispersion, not confidence intervals over tasks. Prefill includes vision encoding and instrumentation. No FLOPs, energy or monetary savings were measured; no quality-preserving Pareto advantage is established.

## Audit and closure

All three full-study audits passed. Independent verification covered 873 native processor tensors, 2,340 exact rendered pages, 122 source-case reconstructions, all output inventories and model pins, and the final figures. Geometry exact-Q probabilities were reproduced using a separate multinomial-enumeration algorithm. Systems QA included 3,240 numerical checks. All five final PDFs passed visual inspection. Final preservation checks verified 103 source-freeze entries, ten execution-freeze entries and all 13 historical completion artifacts unchanged.

Raw RUN_COMPLETE.json files correctly retain their original complete-unverified status; the subsequent INTEGRITY_AUDIT.json files and study results/audit.json records supply verification. Initial per-study FREEZE.json files describe the prospective preparation stage; authoritative native freezes are in checkpoints/cpu_1790114103802037991/prepared/<study>/FREEZE.json.

**The inference phase is closed. No further inference is scientifically necessary to complete these agreed studies.** Paper integration, formatting and final editorial review remain; this record does not assert submission readiness. The historical manuscript has not been rewritten.

## Deliverables

- [ARTIFACT_INDEX.md](<REPOSITORY>/final_iclr/final_followups/ARTIFACT_INDEX.md)
- [CLAIM_UPDATES.md](<REPOSITORY>/final_iclr/final_followups/CLAIM_UPDATES.md)
- [MANUSCRIPT_INTEGRATION.md](<REPOSITORY>/final_iclr/final_followups/MANUSCRIPT_INTEGRATION.md)
- [03_systems_profile/FULL_SYSTEMS_TABLE.md](<REPOSITORY>/final_iclr/final_followups/03_systems_profile/FULL_SYSTEMS_TABLE.md)
- [FINAL_COMPLETION_AUDIT.json](<REPOSITORY>/final_iclr/final_followups/FINAL_COMPLETION_AUDIT.json)
