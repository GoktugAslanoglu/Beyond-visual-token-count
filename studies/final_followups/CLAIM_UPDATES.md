# Claims after the final round

| Claim area | Decision | Wording supported by the evidence |
|---|---|---|
| Task-, reader- and representation-dependent density/reliability | Strengthened | Visual context compression exhibits a task-, reader- and representation-dependent density-reliability tradeoff. Measured visual-token rate alone does not determine recoverability. |
| Any benefit under finite budgets | Added, qualified | At LONG, GLM achieves 28/30 optical versus 19/30 retained-text retrievals under matched input budgets; the interaction and LONG contrast pass their separate Holm families (p=0.03515625). This applies to the tested hash-retention policy and task. |
| Descriptive crossover | Not established | No reader meets the prespecified strict short-text-win/long-optical-win rule. Do not title the finding a demonstrated crossover. |
| Controlled geometry mechanism | Strengthened for Qwen9B only | At fixed measured input rate, rendered-block scale/occupied area changes Qwen9B exact retrieval (3/32 to 14/32 at endpoints; primary Holm p=0.0110315, endpoint Holm p=0.0307617). |
| Glyph size as sole cause | Not supported | Scaling jointly changes area, resampling and positions. Neither a universal monotonic relationship nor a unique glyph mechanism follows. |
| Earlier layout-package result | Unchanged | Preserve the prior all-reader package effect. The fresh geometry cases cannot be treated as a randomized contrast against the earlier sample. |
| General optical speed or compute benefit | Weakened/restricted | Report hardware- and implementation-specific timings and memory only. Fixed-budget E2E advantages coexist with higher model prefill and peak allocation; packing asymmetry matters. |
| C4 quality-preserving efficiency | Not established | C4 has measured resource benefits in LONG profiles, but corresponding quality was not measured in this study. |
| Historical LoCoMo, identifier and cap findings | Unchanged | Retain prior datasets, scoring rules, estimates and limitations. The final round adds separate evidence and does not replace them. |
| Universal superiority, capacity threshold, energy/cost savings, equivalence | Not supported | Do not infer these claims from reader-specific results, token counts, latency, or nonsignificant tests. |

Recommended synthesis: Visual context compression shows a task-, reader- and representation-dependent density-reliability tradeoff. Geometry can change exact retrieval at fixed measured rate. Under the tested fixed-budget policy, increased optical source coverage compensates for fidelity loss for GLM at LONG, while corresponding evidence is inconclusive for the two Qwen readers. Resource consequences depend on representation, reader and preprocessing implementation.

This updates the scope of an overall statement that no optical advantage was established: the original studies remain unchanged, but the new GLM finite-budget study now supplies a narrow positive result. Do not imply that the old experiment itself changed or that the two GLM tests are independent confirmations.
