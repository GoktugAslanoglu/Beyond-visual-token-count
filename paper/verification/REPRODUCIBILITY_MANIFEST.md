# Supplementary reproducibility manifest and artifact index

This manifest accompanies the public preprint evidence release. All paths are repository-relative. It relocates implementation and provenance details from the paper PDF without changing the experimental record. The distribution manifest records original and distributed SHA-256 hashes; the numerical ledger maps displayed values to authoritative fields.

## Authoritative analyses and raw records

| Study | Authoritative analysis and supporting record |
|---|---|
| Original LoCoMo, RULER and identifier study | `baseline/audit/scientific_20260920/ANALYSIS.json`; `scored_rows.jsonl`, `condition_summary.csv`, `hypothesis_tests.csv`, `identifier_joint_factor_cells.csv` in the same directory |
| Matched-budget layout intervention | `studies/identifier_followup_results/analysis.json`, `rows.jsonl`, `audit.json`, `FACTOR_BREAKDOWNS.json`, `INDEPENDENT_NUMBER_CHECK.json` |
| LoCoMo cap follow-up | `studies/locomo_cap_followup/results/cap_analysis.json` and `cap_rows.json`; original question identities retained in the full-arm reconstruction |
| Finite-budget retrieval | `studies/final_followups/01_budget_crossover/analysis.json`, `rows.jsonl`, `results/audit.json`, `RESULT_HASHES.json` |
| Controlled scale | `studies/final_followups/02_geometry_mechanism/analysis.json`, `rows.jsonl`, `results/audit.json`, `results/INDEPENDENT_NUMBER_AND_FIGURE_CHECK.json` |
| Systems profiles | `studies/final_followups/03_systems_profile/analysis.json`, `rows.jsonl`, `results/audit.json`, `results/FIGURE_AND_NUMBER_AUDIT.json` |
| Final preservation | `studies/final_followups/FINAL_COMPLETION_AUDIT.json` links the completed studies, input freezes, result hashes and preserved historical artifacts |

Original raw decoded outputs and generated-token journals are preserved in the execution archives indexed by these audits. The distribution contains per-case scored exports and complete secondary analyses, not model weights or every original rendered input and execution journal. Those larger archives remain in the repository; the included hashes/indexes identify them. No claim that every historical audit can run from the compact supplement alone is intended.

## Protocols and native inputs

The layout protocol, development freeze, source/code freezes and environment pins reside in `studies/identifier_followup/`. Its held-out native input freeze and independent checks reside in `studies/checkpoints/cpu_eval_1789993635114781407/`, including `EVAL_FREEZE.json` and `DEEP_INPUT_CHECKS.json`. The preceding development selection is preserved in `studies/checkpoints/dev_recovery1_1789989576901081577/SELECTION.json`.

The conditional cap protocol is preserved in `studies/locomo_cap_followup/protocol.md` and the associated release documents. Original uncapped outputs remain in the sensitivity reconstruction.

Each final study directory has a frozen `PROTOCOL.md`. Authoritative native inputs reside under `studies/final_followups/checkpoints/cpu_1790114103802037991/prepared/`, one subdirectory per study. The checkpoint root retains `LOCAL_INPUT_AUDIT.json`, `NATIVE_INPUT_AUDIT.json`, and `SOURCE_RECONSTRUCTION_CHECK.json`. Top-level preparation `FREEZE.json` records do not replace native processor-input freezes.

## Snapshot identity

| Reader | Exact model/processor snapshot revision |
|---|---|
| Qwen/Qwen3.5-2B | `15852e8c16360a2fea060d615a32b45270f8a8fc` |
| Qwen/Qwen3.5-9B | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` |
| zai-org/GLM-4.6V-Flash | `411bb4d77144a3f03accbf4b780f5acb8b7cde4e` |

Full tokenizer, processor, configuration, font and weight checksums appear in `studies/final_followups/runtime/legacy/environment/ASSET_PINS.json` and reader-specific snapshot manifests. CPU/GPU lock files retain dependency identities. A pin check establishes consistency with recorded bytes, not absence of benchmark exposure during training.

## Audit coverage and historical exceptions

The original scientific audit checks 48,941 file references, verifies generated-token decoding and native scoring, checks source partitions for 3,348 optical identifier/RULER requests, and reproduces 108 sampled renders. Original audit files preserve decoding/lineage, input checks, resolved inventory flags, geometry diagnostics, supplementary diagnostics, engineering verification, and final verification.

The layout input audit checks all 576 held-out requests and reproduces 1,728 image pages. Output audits check journals, decoding, pins and inventory completeness. All 247 cap reruns are independently rescored and preserve the original generated prefixes.

Final input checks cover 873 native processor tensors, 2,340 rendered pages and 122 source-case reconstructions. The scale test is independently checked by exact multinomial enumeration. Systems verification includes 3,240 numerical checks. Final preservation checks 103 source-freeze entries, ten execution-freeze entries and 13 historical completion artifacts. These are verification counts, not independent experimental samples.

Contemporaneous execution records retain `complete-unverified`; later integrity and study audits establish verification. The original inventory flag has a preserved lineage resolution. A layout cache compatibility repair did not change pinned bytes, inputs or inference settings. A final archive-lookup repair changed transport of the same audited CPU archive before inference. Neither was a scientific protocol amendment. Historical development failures and repair records remain preserved.

## Hash linkage and replay boundaries

Final source-freeze SHA-256: `673143fa3b67d577f43a644ec54d6e0da8a89a02c3bcd880b34426f4249afcf2`.

Final execution-freeze SHA-256: `4c16c8ec4c75746a99cd6fe3cdc28238f83ef02b1ff68c3caaf7a450998af76f`.

`FINAL_COMPLETION_AUDIT.json` links analysis files, scored rows, native freezes, audits and original figures. The manuscript's `evidence_manifest.json` preserves exact original analysis hashes. The source supplement normalized local user paths, private storage URLs and email strings only in distributed copies; original and distributed hashes are separate. Hashes alone do not establish scientific correctness.

In this release's `paper/` directory, `build_assets.py` regenerates numerical definitions, tables and figures; `verify_numbers.py` reconciles them with authoritative results and recomputes aggregate statistics from preserved scored rows. LaTeX/BibTeX rebuild the paper without model inference. Historical full decoding/input audits additionally need their indexed execution archives and pinned assets. Systems timing boundaries, including precomputed optical plans and recomputed text packing, are documented in Appendix F and the profiling protocol.


## Descriptive additions

The asset builder derives realized RULER densities and native counts, LONG paired budget discordances, and LONG allocated peaks above each invocation's resident baseline from preserved rows. Results and source hashes are in evidence/derived.json and independently recomputed by the numerical verifier; authoritative analyses are unchanged.

The report meta_geometry_input_check.json records source strings, native counts, placeholder IDs, grids, patch sizes and merge sizes across 144 layout pairs, with hashes of the original request/measurement files. This is a saved-metadata comparison, not a new processor or model execution. The compact report is distributed; full native-input records remain in the original repository.


## Fresh compact-storage follow-up

The later GLM LONG control is separate from the historical final-round studies above. `studies/final_experiment/PROTOCOL.md`, `CLAIM_MATRIX.md`, `config.json`, `FREEZE.json`, and `manifest.json` specify and bind its prospective design. Model, processor and tokenizer use the GLM snapshot in the identity table above. Development, evaluation, retention, order, bootstrap, inference and smoke seeds are respectively 202609250101 through 202609250107. Three development sources passed the preset 15% capacity gate before inference; evaluation has 150 new sources, 50 per position, and 450 complete calls.

The answer-blind preparation amendment to B=4,025 is recorded in the protocol and stopped `preparation_history/v1` draft. The revised ceiling is 2.78% above historical B=3,916 and uses a fixed 128-token future-query reserve. The comparison is neither exact token matching nor byte-identical replication of old inputs.

Authoritative results are `analysis/RESULTS.json`; all per-case scored records are `outputs/scored/scores.json`. `audit/RESULT_AUDIT.json`, `CHECKPOINT_IMPORT.json`, and `RESULT_CROSSCHECK.json` verify completion, approval/freeze linkage, native input identities, durable generated-token journals and independent scoring/test agreement. `analysis/COMPLETION.json` records the manuscript as unmodified at the time of experiment audit; this historical statement precedes the present integration and is preserved. Inputs, full output records and journals remain in the repository and the returned checkpoint. The supplement supplies all scored rows, frozen specifications, audit reports and result aggregates, rather than model weights and complete rendered-image inventories.

Scientific freeze SHA-256: `75081a7bad4075b5e23964bcffdd53595e2b9178b5f438ef959499cd17700ccf`.
Protocol SHA-256: `a10ea07f8fb5cf77f90dbc8821e7d8c731270325836c9576837725f898a2c318`.
Returned checkpoint SHA-256: `e8f3a23fcc460fabe5d3b317444761c0623d9a1eb68ac6fae363d2518db24b42`.

`build_assets.py` derives only the added capacity, budget and count summaries from preserved scored rows; `verify_numbers.py` independently checks all arm counts, native accounting, position summaries and the primary exact test. `evidence/compact_derived.json` records its source hashes. No further model inference is needed. The original geometry figures and historical finite-budget coordinates remain unchanged; no new systems comparison is claimed.
