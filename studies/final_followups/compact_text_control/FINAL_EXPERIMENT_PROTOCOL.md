# Final experiment protocol: compact static text storage at the GLM LONG operating point

Experiment: `final-compact-storage-glm-long-v2`. Prospective specification; no new model outputs may be generated before the user approves the completed input and execution freeze. This is a local project freeze, not an independently registered preregistration. The historical manuscript and analyses remain immutable during preparation.

## Decision and scientific question

RUN ONE experiment, subject to all input and execution gates. Does full-source optical input retain a generated-answer accuracy advantage over a materially more space-efficient, query-independent textual serialization at a fully query-independent GLM LONG native input ceiling?

The choice of GLM/LONG is informed by the historical positive result. The new cases are independent; the claim concerns replication and baseline robustness at that selected operating point, not an unbiased search across readers or regimes. This is a comparator control in an empirical characterization paper, not a new compression method.

The original 3-source, zero-model development audit found a mean 15.749% capacity gain at the draft ceiling. The final ceiling is recalibrated by the fixed blank-query formula described below; its repeated three-source capacity audit is recorded in development/CAPACITY_REPORT.json. Before inspecting those counts the go/no-go rule was mean increase >=15%, strict increase on each development source. There was one compact format, no accuracy tuning, no source-length search, and zero development model calls. This is a modest but material capacity increase, not evidence of optimized text memory. This gate is not reapplied to choose evaluation cases or altered after their construction.

Primary hypothesis: the paired population mean of native single-answer containment for optical minus compact text is positive on fresh cases from this fixed generator and position mixture. A two-sided exact McNemar test is the sole confirmatory test; direction determines which arm is supported.

Secondary/descriptive questions: Does compact text retain more records and queried records? How much does its observed accuracy change relative to original hash text? Does optical exceed original hash text on the fresh sample? What are recovery rates conditional on audited target inclusion and on omission? How often do formatting, cap hits, or abstention account for failures? These are descriptive; none can replace the primary endpoint.

## Answer-blind draft amendment before any model outputs

Draft v1 used the historical 3,916 ceiling, which had been calibrated to 30 historical questions. A fresh question required 3,917 native tokens during preparation, exceeding it by one. That draft was stopped and preserved in preparation_history/v1; no case was excluded, no response was generated, and no significance/accuracy result was observed. V2 fixes the operational budget definition before launch: 3,844 native vision tokens + 53 measured optical scaffolding tokens for an EMPTY question + 128 fixed future-query tokens = 4,025. Both policies now admit the same fixed future-query reserve. This formula uses no evaluation question, target, or answer.

V2 spends a 2.78% larger total upper bound than the historical 3,916, while preserving the same reader, all 150 source cases, all seeds, optical geometry/vision allocation, serializer, hypotheses, sample size and generation settings. The fresh hash arm anchors this new commitment regime. A positive result would establish robustness at B=4,025, not replicate the historical 3,916 ceiling exactly. No further ceiling adjustment or case replacement is allowed; another gate failure means no launch.

## Reader, snapshots, dependencies

One unmodified reader: `zai-org/GLM-4.6V-Flash`, model, processor, and tokenizer all revision `411bb4d77144a3f03accbf4b780f5acb8b7cde4e`. Every snapshot file and its expected SHA256 is recorded in `environment/GLM_SNAPSHOT.json`. Use a materialized snapshot with regular files (cache symlinks outside the snapshot are rejected). Load locally after checksum verification, `trust_remote_code=False`, fast processor. No floating revisions, remote API calls, quantization, fine-tuning, or alternate readers.

CPU preparation: Python 3.10.10, torch 2.10.0+cpu (or Windows 2.10.0 with torch.version.cuda=None), torchvision 0.25.0+cpu. GPU: CPython 3.13.15 on Linux x86_64, torch 2.10.0+cu128, torchvision 0.25.0+cu128, NVIDIA A100 40GB, BF16, SDPA, batch size one. Shared processor-sensitive packages: transformers 5.3.0, tokenizers 0.22.2, Pillow 12.2.0, numpy 2.2.6, safetensors 0.8.0, huggingface_hub 1.30.0. Historical GPU dependency lock and snapshot inventory accompany the package; actual complete environments are recorded. Analysis pins: scipy 1.15.3, numpy 2.2.6, matplotlib 3.10.9, pytest 9.1.1. Complete versions are recorded in the freeze. CPU and GPU tensor/input equality is mandatory; a runtime difference is not silently accepted.

The historical reference tokenizer, DejaVuSansMono font, renderer, processor measurement, and scoring utilities are reused unchanged and hashed in the dependency manifest. They are not interchangeable with the root project's older optional HF dependency declaration.

## Cases, seeds, separation, and sample size

150 new independent LONG sources, one question each; 50 each with target inserted at 10%, 50%, and 90% of record order. All three arms consume the same underlying source/question per case. The case is the analysis unit; 450 executions are not 450 independent samples. No historical cases enter the new estimate.

Reuse the audited crossover generator algorithm: 1,600 candidate unique 10-uppercase-letter keys and unique seven-digit numeric values per independent stream, format `Record KEY: VALUE`; choose the nearest complete-record prefix to 8,192 reference-Qwen tokens (tolerance 40), insert the target record at its scheduled position. Length is fixed by this rule, never by native target survival or model output. No handpicked records, removal of difficult cases, or length increase to restore an optical advantage. This is synthetic single-key retrieval derived from the existing diagnostic task, not a new official RULER score.

Seeds: development 202609250101; evaluation 202609250102; hash retention 202609250103; launch order 202609250104; bootstrap 202609250105; inference 202609250106; reserved smoke 202609250107. Split identifiers are disjoint. Source construction follows the exact existing SHA256-to-RNG namespace with the new split seed. Validate no duplicate evaluation source hashes and no overlap with the historical crossover or development sources.

Development consists of exactly three source-only probes. No development model accuracy is used. Three separate smoke fixtures may be constructed for CPU, schema, scorer, and mocked runner tests; they cannot enter evaluation. No real model smoke is planned or authorized in this preparation. If a real GPU smoke becomes necessary, it requires a separate documented request before any evaluation execution, and cannot select a serializer, cap, or case.

N=150 permits 450 calls, keeps balanced position groups, and targets moderate paired effects rather than equivalence. `development/POWER.json` enumerates exact McNemar power for n=90/120/150, effects 5/10/15 percentage points, and discordance 0.15/0.25/0.35. These are planning scenarios, not predictions based on new responses. Small differences can remain inconclusive; there is no post-hoc sample-size extension.

## Conditions and source-only commitment

1. `optical`: all original source records, audited L3 full-width word wrapping, four 868x868 RGB PNGs. Full-source inclusion is required, independent of perceptual recovery.
2. `hash_text`: original complete records, SHA256-ranked, greedily retained at the storage budget, then restored to source order.
3. `compact_text`: the same record ranking and same source-only greedy selection rule, but every retained record is serialized as `KEY=VALUE`, one per line, prefixed with exactly `Records (key=number):\n`.

The compact format round-trips every retained key/value pair exactly. It drops repeated syntax uniformly, not fields, values, or query-irrelevant records. It is not lossless preservation of the entire source when records are omitted. Both text policies are simple controls, not optimized textual memory. Compact and original subsets need not be nested because greedy acceptance occurs under separate token counts.

Ranking is SHA256 of retention seed, source/case identifier, and the original record bytes. The ranker/serializer/packer receives records, the source identifier, the fixed budget, and a native token-counting function only. It cannot receive a future question, the identity of its target key, a reference-answer annotation, target position, evidence annotations, inclusion statistics, or outputs. Source key/value fields are processed uniformly without identifying which pair will answer the future query. Hash ranking is applied to original bytes in both arms so the formatting change cannot change rank. Rendering likewise receives source text only. Queries/references are joined after the two textual memories and optical pages have been committed; target inclusion is then audited without changing them. The generator knows the diagnostic target to construct the task, but this information is outside the storage-policy interface.

## Budget definition and native accounting

Fixed common upper bound B= 4,025 reader-native total input tokens, derived as 3,844 vision tokens + 53 empty-question optical scaffolding tokens + 128 fixed future-query tokens; no padding and no claim of equal tokens actually consumed. This is not a disk-byte or physical storage budget. No cross-reader allocation claim is tested.

Storage fit is `native_full_text_chat_tokens(memory, empty_question) + 128 <= 4025`. The 128-token fixed future-query reserve is established before any evaluation queries. The empty-question count includes system message, chat template, MEMORY/QUESTION scaffolding, separators, and generation prompt. All real queries must satisfy the reserve, and all completed native inputs must fit B and the model context with the 64-token output reserve. If either fails, preparation stops for the entire design; do not discard a case or enlarge B. A valid unused reserve is intentionally not reclaimed after seeing a question.

This improves the old operational definition: the historical fit predicate used actual question overhead and its ceiling was calibrated to historical queries. Here no actual query is consulted during storage. Therefore the hash arm is a fresh replication under a stricter pre-query commitment, not a byte-identical replication of old inputs. Both textual arms share this rule. The overhead reserve may leave unused input capacity; report actual counts and reserve slack. Primary attribution concerns the complete representation policies under this stated ceiling, not pure modality alone.

Native measurement uses the pinned real AutoProcessor, no token estimates. Total is the full input_ids length; count image placeholder ID occurrences and verify equality to sum(prod(image_grid_thw)/merge_size^2). Four optical pages must contribute exactly 3,844 vision tokens, with patch_size=14, merge_size=2, and recorded per-page grids. Nonvision is total minus vision. Save all IDs, complete rendered chat, grid, tensor shapes/dtypes/SHA256, source-native token count, stored-native token count, and image hashes. Source token counts are diagnostics, not an additive split of the native templated total (BPE boundaries matter).

## Renderer, serializer, generation

Reuse `runtime/legacy/core.py` L3_fullwidth_wordwrap, font size 12, margins 24, line-height ascent+descent+2, four pages, smallest feasible native base canvas from the audited search. Newlines map one-for-one to spaces with exact source-span bookkeeping. Resize complete pages to 868 with Pillow LANCZOS. No highlighting, crop, selective magnification, query-adaptive layout, or extra source access. Validate complete contiguous source-span coverage, every line's text, font glyph support, rendered ink bounds strictly inside the canvas, and deterministic PNG reproduction.

Use the frozen system prompt from the existing processor module: answer using only supplied memory, return only the answer, otherwise return No information available. Keep the existing question template. Greedy decoding, do_sample=False, num_beams=1, use_cache=True, max_new_tokens=64, thinking disabled by the native chat template, disable_compile=True, return_dict_in_generate=True, output_scores=False. Inherit and record the complete pinned generation configuration, including EOS IDs. Save generated IDs, verbatim decoded answers with and without special tokens, stream journal, elapsed generation time, cap-hit status, and execution environment. No scoring or answer printing during inference.

## Outcomes and statistics

Primary: native case-insensitive containment of the one reference seven-digit answer in the raw decoded response (binary), exactly the existing scoped RULER scorer. Raw substring containment can accept extra prose or another longer string; this known limitation is preserved rather than selecting a friendlier new metric. Canonical EM, literal EM, character error rate, abstention, and cap hits are diagnostics.

Primary contrast: optical minus compact-text success, n=150 paired cases. Exact two-sided McNemar: conditional on discordant pairs, use twice the smaller Binomial(m,0.5) tail, capped at1; all-tied p=1. Alpha=.05. The conditional null makes discordant signs exchangeable; equality within each position stratum is sufficient. Exactness is not claimed for arbitrary pooled mean-zero heterogeneous cases. Only one confirmatory comparison, hence no multiplicity correction is needed (a family of one). Do not add historical tests or descriptive hash comparisons as independent confirmations; do not mine readers, positions, or metrics.

Report gain/loss/tie counts, effect in percentage points, and a 95% paired percentile bootstrap interval, 50,000 resamples, seed 202609250105. Resample whole triplets independently within each 50-case position stratum, then average with equal stratum weight. Pointwise interval, not simultaneous. Boundary bootstrap intervals can degenerate; also show a conservative interval constructed from stratum-specific Bonferroni Clopper-Pearson gain/loss intervals (6 probabilities), and never treat a zero-width bootstrap as population certainty. Neither interval defines equivalence. Primary direction plus McNemar p alone governs superiority; intervals convey precision.

Secondary reports are descriptive only: two other pairwise effects, three arm accuracies, inclusion fractions and counts, successes among included/omitted targets (NA when denominator 0), retained record fractions and serialized-native-token size ratios (the latter are not original-source coverage), source/budget ratio, actual native counts, position summaries, caps, EM/CER. No inferential claims from uncorrected secondary p-values; the analysis should omit their tests.

## Failures, exclusions, interruptions, and violations

All 150 cases and all 450 calls are required for the confirmatory report. There are no scientific exclusions, no trimming, no case replacements, and no success-conditioned retry. Empty or malformed model answers and capped outputs remain scored as generated. Cap hits are not rerun with a larger cap. A missing/incomplete output is an execution failure, not a scored answer.

Preparation fails on any leakage, duplicate/overlap, span loss, clipping, budget/context excess, asset/code hash mismatch, grid error, nondeterminism, scorer/statistic/schema failure, or inability to reproduce native tensors. No model calls may begin until every case passes. A failure may be repaired only before any evaluation output, followed by a new documented freeze and user review; never silently patch a frozen package.

Launch in seeded case blocks, balancing arm order with a three-arm rotation. Persist START before each invocation and fsync the token journal. Resume may skip only integrity-verified COMPLETE calls. If START exists without COMPLETE, the invocation may have emitted an answer: stop and record an incomplete study, do not regenerate that cell. An interruption between complete cells can resume the fixed order without looking at answers. No reduced-n confirmatory claim; partial data are at most explicitly incomplete descriptive diagnostics. Stop after 450 calls or 7,200 cumulative GPU-run seconds. No extra experimental arm after results.

Protocol violations include any target-aware storage, reuse of development/historical cases in estimates, changing source lengths/seed/cap/scorer/arm after outputs, skipping failures, looking at answers to decide continuation, unauthorized snapshot/runtime changes, budget mismatch, or executing before approval. They invalidate confirmatory status; do not conceal them by exclusion. If clean launch cannot be restored prospectively before outputs, RUN NOTHING.

## Claims and manuscript action

The exhaustive result/claim matrix is in `CLAIM_MATRIX.md`. Always report this study if validly completed, including negative or inconclusive findings. Its primary endpoint is confirmatory within the chosen GLM/LONG follow-up; hash comparisons and inclusion decomposition are descriptive. It is not an independently motivated discovery across readers.

Place one paragraph in Section 5, a compact paired results/inclusion table in Appendix E, and detailed protocol in reproducibility materials. No change to the matched-layout claims or Figure 1(b). Figure 1(c) keeps the historical data; if the new result removes its apparent practical force, its caption and neighboring scope statement must mention the new boundary. Abstract changes only to keep its highlighted finite-budget sentence balanced with material new evidence; no universal optical-superiority claim. No manuscript files are edited during preparation.

Rebuttal expansion, if requested, can prospectively add readers, lengths, or richer deterministic storage policies using this interface. The present result provides a calibrated baseline and auditable inputs, not permission to pool a later adaptive expansion as one preregistered study.

## Release and approval

`FINAL_EXPERIMENT_PROTOCOL.md` is a byte-identical named copy of this protocol. `FREEZE.json` binds protocol, claim matrix, configuration, code, tests, cases, inputs, assets, native validation reports, source dependencies, environment records, and manifest. The freeze records that outputs/raw and outputs/scored contain no new results. The runner fails closed without a separate user approval record binding the exact protocol and freeze hashes. No approval file is created during this task. The final output must state held-out inference started: NO.

CPU preparation note: the empty-question chat scaffold is compiled once and fed to the same pinned native tokenizer backend. All 2,898 greedy candidate counts across the three development sources matched the original native counter exactly. Per-case processor tensors and complete inputs are independently reconstructed. CPU worker boundaries change resource use only; they do not select cases or change scientific parameters.
