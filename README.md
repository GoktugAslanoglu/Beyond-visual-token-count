# Beyond Visual Token Count: Target Inclusion and Reader Recovery

Public reproducibility materials by Göktuğ Aslanoğlu and Viswanadh
Vadlamani. `baseline/` contains the original study, and `studies/` contains
the follow-up experiments.

## Results and code

The repository includes protocols, model and processor identifiers, per-case
scored records, aggregate analyses, and audit reports. Start with the
[original study analysis](baseline/audit/scientific_20260920/ANALYSIS.json),
the [layout follow-up](studies/identifier_followup_results/analysis.json),
the [budget](studies/final_followups/01_budget_crossover/analysis.json),
[geometry](studies/final_followups/02_geometry_mechanism/analysis.json),
[systems](studies/final_followups/03_systems_profile/analysis.json), and
[compact-text control](studies/final_followups/compact_text_control/analysis/RESULTS.json) studies.
The manuscript PDF and LaTeX source are not part of this repository.

With the packages in `requirements-analysis.txt` installed, run
`python -m pytest baseline/v2/tests/test_scoring.py -q` to check the released
scoring implementation.

The scored records support reanalysis without new model inference. Model
weights, upstream benchmark bundles, every rendered input, and complete
generated-token journals are not redistributed. A full GPU rerun requires
those assets and the execution archives identified in the study audits.

## Rights

`LICENSE-CODE` applies MIT only to original Python code. It does not license
scientific evidence, model weights, benchmark material, fonts, or third-party
code. LoCoMo-derived material retains its Attribution-NonCommercial 4.0 terms;
RULER material retains Apache 2.0. See [third-party notices](third_party/NOTICES.md)
and the accompanying upstream licenses. No project-wide license for the
evidence is asserted.
