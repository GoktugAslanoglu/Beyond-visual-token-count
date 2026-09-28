Scientific audit evidence and reproduction notes

Start with [SCIENTIFIC_AUDIT.md](<<REPOSITORY>/iclr/audit/scientific_20260920/SCIENTIFIC_AUDIT.md>). This audit began on 20 September 2026 and was finalized on 21 September (Europe/Istanbul). The directory name preserves its start date. It is an additive audit: original inputs, predictions, archives and prospective scientific rules were not edited.

The scope is the active plan's 13,176 required responses, the 2,710-response historical reconciliation, 25 development/repeat result files, 228 smoke responses and 26 synthetic timing responses. These sets overlap in historical/development copies and are NOT to be added into one independent sample. Test-fixture copies and intermediate checkpoints are not new experiments. No independent GPU replication was performed.

The audit used the actual nine final result archives catalogued in `iclr/audit/completion_20260920/completion_audit.json`, plus the sealed input manifests and earlier archives named in the evidence reports. Some archives remain in `<LOCAL_USER>/Downloads`. The workspace, those archives and the pinned tokenizer assets are prerequisites; this directory alone is not a self-contained public reproduction release. Source data redistribution was not performed.

The evidence chain is:

1. `PRE_OUTCOME_REVIEW.json`, `RULER_RELEASE_CONTRACT.json`, `UNBLINDING_RELEASE.json`, `RELEASE_VALIDATION.json`: checked scientific contracts and the dated outcome-inspection release. `preflight.py` created these once using exclusive writes; do not rerun it over an existing release or backdate a release.
2. `INPUT_AUDIT.json`, `RESULT_AUDIT.json`, `scored_rows.jsonl`: exhaustive mandatory input, archive, journal and scorer checks from `verify_results.py`. The first result audit retains a setup-directory false-positive flag for transparency.
3. `DECODING_AND_LINEAGE.json`, `AUDIT_FLAG_RESOLUTION.json`, `RESULT_AUDIT_RESOLVED.json`: pinned-tokenizer decoding, checkpoint history and the explicit resolution from `verify_lineage.py`. Use the resolved report for final status; the original failed flag is not an unresolved data defect.
4. `ANALYSIS.json`, `condition_summary.csv`, `hypothesis_tests.csv`: primary and labeled secondary estimates from `analyze.py`. Hypothesis family, cluster structure and 50,000 bootstrap repetitions are retained. A boundary bootstrap interval is not a claim of zero uncertainty outside the observed sample.
5. `GEOMETRY_AND_METHOD_DIAGNOSTICS.json`: all 3,348 identifier/RULER optical-request source partitions plus 108 sampled pixel-exact rerenders from `diagnostics.py`; independent native RULER aggregate and identifier sign-test checks.
6. `SUPPLEMENTARY_DIAGNOSTICS.json`, `identifier_joint_factor_cells.csv`: post-unblinding descriptive paired contrasts, task sensitivity, formatting checks and complete joint factor cells from `supplementary_diagnostics.py`. These are not added to the primary six-test family.
7. `LEGACY_REAUDIT.json`: rerun of the preserved legacy audit; historical defects remain explicit. `DEVELOPMENT_REAUDIT.json`: archived file hashes, rescored development outputs, duplicate copies and the failed ExactStrip gate. `ENGINEERING_REAUDIT.json`: independent smoke/timing archive and token checks from `verify_engineering.py`; engineering scores are not paper performance evidence.
8. `scoring_tests.xml`: 36 passed frozen scorer/amendment tests. `AUDIT_ENVIRONMENT.json`: CPU audit software versions, separate from original GPU environment records.

To reproduce the primary analysis from the existing verified per-row export, run the following from the workspace root. These scripts update audit-derived outputs only and require the indicated source evidence. Make a separate copy for an independent replication if you want to retain these exact audit files.

```text
python -B iclr/audit/scientific_20260920/analyze.py
python -B iclr/audit/scientific_20260920/supplementary_diagnostics.py
python -B iclr/audit/scientific_20260920/build_report.py
```

For full evidence replay, run `verify_results.py`, followed by `verify_lineage.py`, before the analysis commands. The first script deliberately reproduces the original inventory flag and the second resolves it with explicit archive inspection. `diagnostics.py` and `verify_engineering.py` replay their separate checks. The release files must already exist and still verify. Do not interpret a rerun of these CPU scripts as a new GPU experiment.

The focused tests were:

```text
python -m pytest iclr/v2/tests/test_scoring.py iclr/stage04c_identifier_amended_20260913/test_amendments.py
```

The original legacy re-audit command was:

```text
python -B -u iclr/prepare.py audit --output audit/scientific_20260920/LEGACY_REAUDIT.json
```

`AUDIT_FILE_MANIFEST.json` records the size and SHA-256 of each top-level audit file except itself and the final verification record. `FINAL_VERIFICATION.json` records final row-count, table-count, reference-link, archive-hash and protected-file checks. A file hash demonstrates consistency with a recorded file; it cannot by itself establish provenance from an independent source.
