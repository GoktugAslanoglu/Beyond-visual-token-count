RULER answer-extraction audit

Decision: retain the frozen scorer. All 20 sampled raw-text Qwen responses explicitly state the correct answer but include explanatory prose or Markdown (B=20; A=0; C=0). Full archived responses, not inferred labels, were inspected. All 2,160 RULER scores reproduce under the frozen implementation.

The v2 amendment specifies that the canonical answer removes only a single fully enclosing special box, with otherwise retained response text; EM collapses whitespace. It does not authorize arbitrary answer extraction or removal of Markdown/prose. Thus these rejections are consistent with the declared specification. No correction or rescoring change is justified. Native containment measures answer presence, while EM/CER here also penalize response format. Do not use low Qwen raw EM as proof of failed retrieval.

Sampling was restricted to native-containment-correct/EM-incorrect rows; 20/20 is a characterization of this selected disagreement sample, not a prevalence estimate over all RULER responses.

| Reader | Row | Task | Class |
| --- | --- | --- | --- |
| Qwen2B | ruler-niah_single_1-029 | niah_single_1 | B |
| Qwen2B | ruler-niah_single_1-001 | niah_single_1 | B |
| Qwen2B | ruler-niah_single_1-016 | niah_single_1 | B |
| Qwen2B | ruler-niah_single_2-007 | niah_single_2 | B |
| Qwen2B | ruler-niah_single_2-016 | niah_single_2 | B |
| Qwen2B | ruler-niah_single_3-009 | niah_single_3 | B |
| Qwen2B | ruler-niah_single_3-017 | niah_single_3 | B |
| Qwen2B | ruler-niah_single_3-001 | niah_single_3 | B |
| Qwen2B | ruler-niah_multikey_3-020 | niah_multikey_3 | B |
| Qwen2B | ruler-niah_multikey_3-018 | niah_multikey_3 | B |
| Qwen9B | ruler-niah_single_1-021 | niah_single_1 | B |
| Qwen9B | ruler-niah_single_1-010 | niah_single_1 | B |
| Qwen9B | ruler-niah_single_2-003 | niah_single_2 | B |
| Qwen9B | ruler-niah_single_2-026 | niah_single_2 | B |
| Qwen9B | ruler-niah_single_2-021 | niah_single_2 | B |
| Qwen9B | ruler-niah_single_3-025 | niah_single_3 | B |
| Qwen9B | ruler-niah_single_3-027 | niah_single_3 | B |
| Qwen9B | ruler-niah_multikey_3-016 | niah_multikey_3 | B |
| Qwen9B | ruler-niah_multikey_3-019 | niah_multikey_3 | B |
| Qwen9B | ruler-niah_multikey_3-026 | niah_multikey_3 | B |

Complete references, predictions and reasons are preserved in ruler_extraction_classifications.json. Sample identities and ranking rule are in provenance/AUDIT_SAMPLE_FREEZE.json.
