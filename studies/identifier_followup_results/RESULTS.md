# Completed identifier layout follow-up

All 576 held-out outputs passed complete verification before scoring. Together with the 36 development outputs, the planned identifier follow-up is complete: 612 generation calls. The initial setup failure generated no answers. Original results remain unchanged.

## Exact retrieval results

Each cell is correct answers out of 48 held-out cases. Canonical exact match is the frozen primary outcome; whitespace and the narrowly specified enclosing box are normalized, but explanations are not removed.

| Condition | Qwen2B | Qwen9B | GLM |
|---|---:|---:|---:|
| Raw text | 47/48 (97.9%) | 46/48 (95.8%) | 48/48 (100%) |
| Original C2 layout | 0/48 | 0/48 | 0/48 |
| Efficient C2 layout | 6/48 (12.5%) | 21/48 (43.8%) | 7/48 (14.6%) |
| Enlarged-image control | 17/48 (35.4%) | 35/48 (72.9%) | 29/48 (60.4%) |

Original and efficient C2 share identical measured input budgets for each case/reader; their image pixels differ. The efficient layout is the prospectively selected L3 full-width word-wrapping renderer. The enlarged control spends additional vision tokens and is not a matched-budget comparison.

## Prespecified primary contrasts

| Reader | Efficient minus original, points | Stratified paired 95% bootstrap interval | Gains / losses | Exact two-sided p | Holm-adjusted p |
|---|---:|---|---|---:|---:|
| Qwen2B | +12.50 | [6.25, 18.75] | 6 / 0 | 0.03125 | 0.03125 |
| Qwen9B | +43.75 | [35.42, 52.08] | 21 / 0 | 0.0000009537 | 0.0000028610 |
| GLM | +14.58 | [10.42, 18.75] | 7 / 0 | 0.015625 | 0.03125 |

All three comparisons pass the frozen Holm procedure. Six gains can pass for Qwen2B because the preceding two ordered hypotheses pass their stricter Holm steps; no test rule was changed. All intervals use the frozen 50,000 resamples within 24 two-instance cells. They are conditional on this small fixed design and do not describe universal task uncertainty or support interaction claims.

## What the controls establish

All readers meet the raw-control criterion of at least 42/48. The task and scoring pipeline can therefore succeed on the same held-out content in text form. This argues against a general inability to answer these questions or a uniformly wrong reference file. It does not prove the entire software is error-free, nor completely isolate perception from reasoning under image input.

No reader meets the enlarged-image success criterion of at least 36/48. Qwen9B misses by one answer; the threshold remains unchanged. The enlarged regime improves observed exact recovery but does not establish the prespecified useful-readable regime. Geometry thresholds describe eligibility, not guaranteed recognition.

The matched-budget results support a scoped constructive claim: changing this source-preserving layout improves exact retrieval for these three readers on these held-out cases. They do not establish a universal compression threshold, optical equivalence to text, or a compute/energy advantage. The layout intervention also changes whitespace appearance and pagination, so do not attribute the effect solely to font height.

## Rechecking the low development scores

The development results remain 0/12, 1/12 and 1/12. L3 was selected by the frozen font-size tie-break, not because it demonstrated high development accuracy. Development and evaluation have distinct frozen question/filler templates, so a change from development to evaluation accuracy is not itself an intervention estimate.

Post-hoc response diagnostics show Qwen2B still produces key-only answers in 17/48 efficient-C2 cases, while target containment is 13/48 versus primary exact match 6/48. In the enlarged Qwen9B arm, containment is 36/48 but exact match is 35/48; we do not use containment to rescue the failed success criterion. These diagnostics explain response behavior and do not replace the registered-in-repository metrics.

## Remaining work

The separate conditional LoCoMo cap diagnostic (126+121 calls at 256 tokens) has not run. Its scientific trigger was established before these results and execution remains conditional on the shared GPU budget and September 23 cutoff. After it is verified, update the final manuscript sensitivity discussion. Formatting, bibliography, anonymization, supplementary hashes and final submission checks also remain.

Machine-readable results: analysis.json; audited rows: rows.jsonl; complete-output gate: audit.json; independent counts/exact-test arithmetic: INDEPENDENT_NUMBER_CHECK.json. Per-reader archive integrity audits and the complete CPU input audit remain under final_iclr/checkpoints/.
