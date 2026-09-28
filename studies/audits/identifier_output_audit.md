Identifier output and geometry audit

All 20 stratified GLM samples are the instructed abstention “No information available”, sometimes enclosed in the special box. This is not a safety refusal, and not an attempted identifier with a few corrupted characters. Whole-population response frequencies are retained in identifier_output_audit.json; sample membership was fixed before this detailed inspection.

The table compares the same C=2/four-page setting. Width is the median maximum line bounding-box width divided by page width, not an ink-coverage fraction. Effective size is font em height after processor resizing, not visible height of each glyph.

| Study | Reader | Effective font em pixels | Text width/page width |
| --- | --- | --- | --- |
| Identifier | Qwen2B | 4.14–4.52 | 12.28% |
| Identifier | Qwen9B | 4.14–4.52 | 12.28% |
| Identifier | GLM | 3.51–3.76 | 12.28% |
| RULER | Qwen2B | 8.40–8.96 | 77.92% |
| RULER | Qwen9B | 8.40–8.96 | 77.92% |
| RULER | GLM | 6.86–7.84 | 77.92% |

The contrast supports treating the original identifier floor as configuration-specific. It does not by itself establish the causal contribution of geometry: the datasets also differ in content, prompts and retrieval task. The follow-up is designed to intervene on layout while holding source and measured budget fixed.

| Sample row | Condition | Classification |
| --- | --- | --- |
| identifier-007 | optical_c2_p2 | Instructed abstention |
| identifier-056 | optical_c2_p2 | Instructed abstention |
| identifier-000 | optical_c2_p2 | Instructed abstention |
| identifier-060 | optical_c2_p2 | Instructed abstention |
| identifier-088 | optical_c2_p2 | Instructed abstention |
| identifier-008 | optical_c2_p4 | Instructed abstention |
| identifier-054 | optical_c2_p4 | Instructed abstention |
| identifier-059 | optical_c2_p4 | Instructed abstention |
| identifier-021 | optical_c2_p4 | Instructed abstention |
| identifier-052 | optical_c2_p4 | Instructed abstention |
| identifier-042 | optical_c4_p2 | Instructed abstention |
| identifier-078 | optical_c4_p2 | Instructed abstention |
| identifier-028 | optical_c4_p2 | Instructed abstention |
| identifier-015 | optical_c4_p2 | Instructed abstention |
| identifier-056 | optical_c4_p2 | Instructed abstention |
| identifier-025 | optical_c4_p4 | Instructed abstention |
| identifier-058 | optical_c4_p4 | Instructed abstention |
| identifier-084 | optical_c4_p4 | Instructed abstention |
| identifier-051 | optical_c4_p4 | Instructed abstention |
| identifier-024 | optical_c4_p4 | Instructed abstention |
