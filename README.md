# Beyond Visual Token Count: Target Inclusion and Reader Recovery

Public paper and reproducibility materials by Göktuğ Aslanoğlu and Viswanadh
Vadlamani. This folder uses neutral paths: `paper/` for the public preprint,
`studies/` for follow-up experiments, and `baseline/` for the original study.
The paper is a **preprint**; this release makes no conference-acceptance claim.

## Reproduce the reported numbers

The `paper/` source, PDF, figures, tables, and bibliography are the public
preprint version. Its current `main.pdf` is byte-identical to the previously
audited public PDF. From this folder, with the packages in
`requirements-analysis.txt` installed, run:

```text
python paper/verify_numbers.py
python paper/build_assets.py
python paper/verify_numbers.py
python -m pytest baseline/v2/tests/test_scoring.py -q
```

The verifier reconciles displayed numbers with frozen analyses, rechecks
source hashes, and recomputes aggregate statistics from per-case scored rows.
To build the PDF, change to `paper/` and run PDFLaTeX, BibTeX, then PDFLaTeX
twice. The included LaTeX style files reproduce the existing paper layout;
they are third-party template files, not part of the MIT code license.

`paper/verification/REPRODUCIBILITY_MANIFEST.md` maps each study to its
authoritative results and describes replay boundaries. Model weights,
upstream benchmark bundles, every rendered input, and complete original
generated-token journals are not redistributed. Fresh GPU inference needs
the pinned models/assets and complete execution archives referenced by the
audits; this compact folder supports paper and numerical reproduction but is
not a one-command full inference rerun.

## Historical identifiers

The original project used conference-named paths and archive filenames.
Those old strings remain inside **unaltered frozen result rows and audit
records** so their hashes and provenance can be checked. The original
conference template is also kept because the paper source uses it. No
conference-only author-guideline check, submission-form abstract, or former
Appendix G is included. The public preprint retains its concise tool-use
note and experimental reproducibility details. `PROVENANCE_MAPPING.json` records each
source path, public path, and before/after hash. See `PUBLIC_RELEASE_AUDIT.json`
for the classified string and file audit; do not interpret a historical
archive label as a publication claim.

## Rights

`LICENSE-CODE` applies MIT only to original Python code. It does not license
the manuscript, scientific evidence, model weights, benchmark material,
fonts, template files, or third-party code. LoCoMo-derived material retains
its Attribution-NonCommercial 4.0 terms; RULER material retains Apache 2.0.
See `paper/third_party/NOTICES.md` and the accompanying upstream licenses.
No project-wide license for the manuscript or evidence is asserted.
