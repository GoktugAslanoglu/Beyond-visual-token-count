Scientific audit — 20–21 September 2026


**Verdict: the mandatory experiment collection is complete, and its saved results pass the integrity, decoding, input-consistency and scoring checks performed here. Scientific interpretation still needs restrictions.** All 13,176 required calls are accounted for. There is no unresolved row-integrity error. The strongest concern is the identifier renderer: severe legibility loss makes its zero-accuracy results a valid failure boundary for this configuration, but a weak basis for isolating entropy effects or making general claims about optical memory. Additional experiments are needed for those broader claims; they are not needed to fill missing calls in the frozen plan.

This audit performed local verification and analysis, not fresh GPU inference. Original archives, predictions, prepared inputs, historical analyses and protocol files were preserved. Every mandatory response was checked programmatically; visual reconstruction was sampled. Integrity means consistency with the available records, not independent attestation of the original hardware run or a guarantee that all scientific threats have been eliminated.

The active design is in [the merged plan](<<REPOSITORY>/iclr/v2/MERGED_PLAN.md>), read with [the v2 amendment](<<REPOSITORY>/iclr/v2/PROTOCOL_AMENDMENT.md>) and the later sealed identifier and RULER contracts. September 6 status pages saying the studies are still planned are historical and stale; they must not be used as evidence that calls are missing. This dated report is an additive status record.

| Study | Items | Arms × readers | Verified calls |
| --- | --- | --- | --- |
| LoCoMo | 500 questions / 10 conversations | 6 × 3 | 9,000 |
| Scoped RULER | 180 cases / 6 tasks | 4 × 3 | 2,160 |
| Identifier | 96 cases / 48 joint factor cells | 7 × 3 | 2,016 |
| Total | 776 items, with study-specific dependence | — | 13,176 |

The pre-outcome review verified the contract references and five pre-generation RULER approvals. A dated release recorded the user’s request to inspect the results. An additive adapter exposed the existing nested RULER contract to the release validator without changing the scientific content. This is a local prospective freeze supported by preserved records, not a claim of externally registered preregistration. Evidence: [PRE_OUTCOME_REVIEW.json](<<REPOSITORY>/iclr/audit/scientific_20260920/PRE_OUTCOME_REVIEW.json>), [UNBLINDING_RELEASE.json](<<REPOSITORY>/iclr/audit/scientific_20260920/UNBLINDING_RELEASE.json>) and [RELEASE_VALIDATION.json](<<REPOSITORY>/iclr/audit/scientific_20260920/RELEASE_VALIDATION.json>).

**What was verified.** The input audit checked 48,941 file references, complete row keys, model/condition pairing, canonical evidence and prompts, processor-reported token counts and image grids, native context reserves, identifier generation constraints, and RULER’s sealed inputs. LoCoMo’s retrieved text and retrieved optical arms share the exact selected evidence; matched-text controls were checked against their declared budget rules. All 13,176 saved input/output journals match their requests and payloads. Both decoded text views reproduce exactly from the generated IDs with the pinned tokenizer files. Available earlier checkpoint row files are unchanged in the final archives.

The frozen scorer was run on every mandatory response. LoCoMo scores were checked against the pinned native metric; all 72 RULER task/reader/arm aggregates independently matched the upstream containment scorer. Identifier sign-test probabilities also matched an independent implementation. The scoring and amendment test suites passed 36 tests. All 3,348 identifier/RULER optical requests passed full source-partition and bounding-box checks; 108 deterministic page reconstructions matched the original pixels exactly. These checks do not imply that every page was manually read or that the GPU processor was independently rerun.

The first audit raised one inventory flag because it treated a Qwen2B LoCoMo setup directory as a response. Inspection confirmed it contains only setup records and no row markers. The original flag is retained, with the resolution in [AUDIT_FLAG_RESOLUTION.json](<<REPOSITORY>/iclr/audit/scientific_20260920/AUDIT_FLAG_RESOLUTION.json>). The final integrity status is [RESULT_AUDIT_RESOLVED.json](<<REPOSITORY>/iclr/audit/scientific_20260920/RESULT_AUDIT_RESOLVED.json>).

**LoCoMo results.** Values below are conversation-macro F1 × 100, using the frozen canonical-answer scorer. Each arm has 500 questions; uncertainty is based on ten conversations. The full machine-readable analysis also reports native question-level F1, categories, support coverage, paired intervals and leave-one-conversation-out estimates.

| Condition | Qwen2B | Qwen9B | GLM |
| --- | --- | --- | --- |
| Full text | 48.45 | 53.04 | 48.31 |
| Full optical C=2 | 9.84 | 15.95 | 24.84 |
| Retrieved text | 39.98 | 37.22 | 37.55 |
| Retrieved optical | 28.89 | 35.28 | 30.89 |
| Text matched to full optical | 48.34 | 49.77 | 44.01 |
| Text matched to retrieved optical | 40.74 | 39.11 | 39.35 |

Retrieval plus the selected optical rendering improves over the full optical package in all three readers (H1). This tests the whole package: selection, evidence amount, page geometry and budget change together. It does not identify retrieval alone as the causal mechanism.

| Reader | H1 gain, F1 points | Paired 95% interval | Holm-adjusted p |
| --- | --- | --- | --- |
| Qwen2B | +19.05 | [15.79, 22.46] | 0.002930 |
| Qwen9B | +19.33 | [14.99, 22.97] | 0.002930 |
| GLM | +6.05 | [2.39, 9.48] | 0.008789 |

On exactly the same selected evidence, retrieved optical scores below retrieved text for all readers. None of the H2 95% intervals lies wholly within the prespecified ±3 F1-point equivalence region. Qwen9B’s smaller gap is not evidence of equivalence, and its interval is still below zero. These are secondary estimates; they are not new multiplicity-adjusted discoveries.

| Reader | Optical minus same-evidence text | Paired 95% interval | Equivalence established? |
| --- | --- | --- | --- |
| Qwen2B | -11.09 | [-14.08, -8.27] | No |
| Qwen9B | -1.94 | [-3.76, -0.13] | No |
| GLM | -6.66 | [-9.86, -3.94] | No |

Both budget-matched text controls also have higher point estimates than their corresponding optical arms. Matched budget does not imply identical evidence; among the retrieved comparisons, the unmatched retrieved text/optical pair is the declared equal-evidence comparison. The data do not establish an accuracy advantage for optical rendering over these text controls.

The selector includes all annotated support for 269/500 questions, has incomplete support for 229, and has unresolved support annotations for 2. Mean support recall among the 498 resolvable questions is 59.08%. The two annotation issues remain unknown rather than being silently scored as retrieval failures; all 500 questions remain in outcome scoring. Conditional optical F1 is higher with complete annotated support, but this is descriptive and can reflect question difficulty and annotation quality.

**Identifier results.** Values are canonical exact-match percentages, with 96 paired cases per arm. The scorer collapses whitespace and applies the frozen canonical-answer rule; literal raw matching is separately available in per-row scores. CER and every joint factor cell are retained in the supplementary files.

| Condition | Qwen2B | Qwen9B | GLM |
| --- | --- | --- | --- |
| Raw text | 93.75 | 96.88 | 96.88 |
| C=0.8, 2 pages | 0.00 | 3.12 | 0.00 |
| C=0.8, 4 pages | 13.54 | 22.92 | 0.00 |
| C=2, 2 pages | 0.00 | 0.00 | 0.00 |
| C=2, 4 pages | 0.00 | 0.00 | 0.00 |
| C=4, 2 pages | 0.00 | 0.00 | 0.00 |
| C=4, 4 pages | 0.00 | 0.00 | 0.00 |

All four compressed optical arms together produce **0 correct responses in 1,152 calls**. The reference identifier does not appear anywhere in any of those raw outputs, so the floor is not explained just by extra prose rejected by exact-match scoring. Raw text recovers 90/96, 93/96 and 93/96 cases. H3 supports raw exceeding the mean compressed optical score under this design:

| Reader | Raw − compressed optical, points | Paired 95% interval | Holm-adjusted p |
| --- | --- | --- | --- |
| Qwen2B | +93.75 | [90.62, 96.87] | 3.23e-27 |
| Qwen9B | +96.88 | [94.79, 98.96] | 6.06e-28 |
| GLM | +96.88 | [94.79, 98.96] | 6.06e-28 |

The identifier renderer preserves hard line breaks from short filler sentences. It creates a tall text column inside a square canvas and downsamples the square. Across compressed arms, effective font em height is approximately 2.10–4.52 pixels for Qwen and 1.78–3.76 pixels for GLM. The median maximum text bounding-box width is only about 6.23% of page width with two pages and 12.28% with four. This width statistic is not a percentage of ink coverage, and font em height is not directly the visible height of every character. No missing source spans or pre-resize clipping were found.

The C=0.8 expanded-input controls also mostly fail: four-page Qwen2B gets 13/96, four-page Qwen9B 22/96, two-page Qwen9B 3/96, and the other expanded arms zero. A broad mechanism claim therefore needs a demonstrated readable optical positive control and a more efficient full-evidence layout at comparable measured budgets. The observed layout is a plausible contributor, not a causal effect established by this audit. A floor across compressed conditions cannot establish absence of entropy, length, position, distractor or page-count effects. The complete 1,008 joint-factor cells are descriptive and contain only two cases each.

**Scoped RULER results.** Values are native answer-containment percentages, equally averaged over the six selected tasks. Each arm has 180 cases. C=0.8 is optical expansion; C=2/4 are measured compression targets. These are not the full official RULER aggregate and not literal transcription accuracies.

| Condition | Qwen2B | Qwen9B | GLM |
| --- | --- | --- | --- |
| Raw text | 90.64 | 99.17 | 100.00 |
| Optical C=0.8 | 74.56 | 83.72 | 72.39 |
| Optical C=2 | 46.11 | 55.64 | 33.56 |
| Optical C=4 | 5.44 | 8.06 | 1.50 |

Compression is associated with substantial degradation within every tested reader. Native containment can give credit to verbose answers containing the target, even when exact transcription fails. For example, Qwen2B raw receives 100% containment on niah_single_1 but 0% canonical exact match. The report therefore retains task-level native scores, strict EM/CER on the four single-answer tasks, and paired task-stratified diagnostic contrasts. The native VT prompt includes a worked example: describe the study as training-free under benchmark-native prompting, rather than uniformly zero-shot.

**Uncertainty and run limitations.** Primary analyses use 50,000 resamples and the frozen statistics seed. LoCoMo resamples conversations; H1 enumerates all 1,024 sign flips and assumes appropriate null symmetry/exchangeability, without randomized assignment of modality. Identifier uses the later prospective exact one-sided sign test and pair-preserving resampling within each two-instance factor cell. The sign test addresses the direction of nonzero case contrasts, while the reported effect is the mean score difference. Holm adjustment covers the six H1/H3 tests. H2 follows its separate prespecified interval rule. Additional tables and geometry checks are explicitly secondary/post-unblinding diagnostics.

Only ten existing LoCoMo histories support conversation-level inference. The 96 identifier cases provide two observations per joint factor cell. RULER cases are conditional on six synthetic templates and overlapping source/background material; task-stratified intervals do not account for all uncertainty about new tasks or corpora. Source-style grouped means and leave-one-task-out contrasts are sensitivity descriptions, not estimates from independent source populations. An empirical bootstrap interval of [0,0] or [1,1] at a floor/ceiling does not mean zero population uncertainty. Do not interpret these intervals as proof that future successes/failures are impossible. Single-seed greedy generation does not estimate repeat-run or stochastic-generation variability.

Saved outputs reaching the generation cap remain scored exactly as collected. Caps are part of the evaluated protocol and can affect comparisons; they are not evidence of archive corruption or a reason to selectively retry poor answers. Counts below are per reader within each study:

| Study | Reader | Capped / all calls | Percent |
| --- | --- | --- | --- |
| Identifier | Qwen2B | 19 / 672 | 2.83% |
| Identifier | Qwen9B | 5 / 672 | 0.74% |
| Identifier | GLM | 0 / 672 | 0.00% |
| LoCoMo | Qwen2B | 155 / 3000 | 5.17% |
| LoCoMo | Qwen9B | 144 / 3000 | 4.80% |
| LoCoMo | GLM | 16 / 3000 | 0.53% |
| RULER | Qwen2B | 177 / 720 | 24.58% |
| RULER | Qwen9B | 243 / 720 | 33.75% |
| RULER | GLM | 1 / 720 | 0.14% |

Runtime/configuration records were checked where saved. The initial 300-row Qwen2B LoCoMo checkpoint lacks a separate environment record comparable to later continuations; its pinned launch code and input/output journals remain available. No fresh model-weight execution or independent reproduction of every processor tensor was performed. Public benchmark use also does not establish absence of model pretraining contamination. Hardware latency, memory and token-count observations do not establish equal compute or energy. Generation timing includes token-journal I/O, and the 26-call synthetic timing calibration supports engineering estimates only.

**Historical and development evidence.** The legacy re-audit reconciles all 2,710 reported responses and verifies archived bundle hashes and the scorer-version bridge. Original protected file inventories match the prior audit. The known historical defects remain documented: stale tables/analysis, an 18-row Qwen2B block absent from the submitted supplement but recovered locally, first-line versus full-response scoring drift, and incomplete revision/seed metadata. Old figures should not be copied into the new paper without the audited scorer label and provenance. This audit does not retroactively repair or strengthen the workshop submission.

The development audit covers 25 result/repeat files and identifies byte-identical copies so they are not counted as additional independent observations. Clean ExactStrip v2 scores 14/18 versus 12/18 for uniform rendering, with 5 paired gains and 3 losses (two-sided exact McNemar p=0.7265625). It fails all declared gates: overall 14/18 versus the required 15, paths 1/3 versus 2, protected 8/9 versus 9. It remains development-only and is not an established successful method.

All 228 historical smoke rows and 26 timing rows were rechecked for archive/file integrity, exact token decoding, output journals and input counts; the timing input/output journals, shape matching and arithmetic also pass. Smoke score labels retain their historical independent scoring validation rather than being regenerated in this engineering recheck. These engineering/development records are excluded from the 13,176-call scientific analyses. Evidence: [LEGACY_REAUDIT.json](<<REPOSITORY>/iclr/audit/scientific_20260920/LEGACY_REAUDIT.json>), [DEVELOPMENT_REAUDIT.json](<<REPOSITORY>/iclr/audit/scientific_20260920/DEVELOPMENT_REAUDIT.json>) and [ENGINEERING_REAUDIT.json](<<REPOSITORY>/iclr/audit/scientific_20260920/ENGINEERING_REAUDIT.json>).

**What remains before stronger claims or submission.**

1. For a scoped empirical paper, retain all failed/negative results and restrict conclusions to these readers, datasets, rendering layouts and generation budgets. Update manuscript tables, claims and status text from this audit; this audit does not certify an unreviewed final manuscript.
2. Before claiming an entropy-specific mechanism, a general exact-state limitation, or competitive optical rendering, run a prospectively specified legibility-positive control and an efficient, source-preserving layout comparison. Use separate development cases to tune the layout, then new held-out cases for confirmatory conclusions. Reusing these now-inspected cases is acceptable only as a labeled post-hoc diagnostic.
3. For broad conversational generalization, the plan’s cleaned LongMemEval-S extension is still valuable. Dense retrieval, no-memory/truncation controls, repeated controlled timing and a faithful published-method comparison remain conditional extensions; none is silently counted as complete here.
4. Preserve the audit’s distinction between equivalent evidence, equivalent measured input budget and equivalent compute. Do not claim optical accuracy superiority over the tested text controls, uniform zero-shot prompting, general scaling laws, precise factor thresholds, or a successful ExactStrip method from these data.

No additional inference is required to complete the mandatory call inventory. The additional controls in item 2 are needed if the intended paper keeps broader mechanism or competitiveness claims. The current evidence can instead support a narrower, transparent failure-boundary study.

All per-condition estimates and intervals: [condition_summary.csv](<<REPOSITORY>/iclr/audit/scientific_20260920/condition_summary.csv>). Primary test results: [hypothesis_tests.csv](<<REPOSITORY>/iclr/audit/scientific_20260920/hypothesis_tests.csv>). Complete analysis: [ANALYSIS.json](<<REPOSITORY>/iclr/audit/scientific_20260920/ANALYSIS.json>). Every scored mandatory response: [scored_rows.jsonl](<<REPOSITORY>/iclr/audit/scientific_20260920/scored_rows.jsonl>). Joint factor cells: [identifier_joint_factor_cells.csv](<<REPOSITORY>/iclr/audit/scientific_20260920/identifier_joint_factor_cells.csv>). Secondary paired RULER and formatting checks: [SUPPLEMENTARY_DIAGNOSTICS.json](<<REPOSITORY>/iclr/audit/scientific_20260920/SUPPLEMENTARY_DIAGNOSTICS.json>). Geometry and sampled pixel reconstruction: [GEOMETRY_AND_METHOD_DIAGNOSTICS.json](<<REPOSITORY>/iclr/audit/scientific_20260920/GEOMETRY_AND_METHOD_DIAGNOSTICS.json>). Reproduction notes and file inventory: [README.md](<<REPOSITORY>/iclr/audit/scientific_20260920/README.md>).
