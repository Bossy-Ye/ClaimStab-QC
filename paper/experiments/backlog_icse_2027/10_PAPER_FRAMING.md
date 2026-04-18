# 10 Paper Framing

## Goal

Make the paper read as a software-engineering methodology paper, not a framework/toolkit paper.

## Required Framing Changes

- abstract:
  - scope the strongest mismatch claims correctly
  - foreground conclusions vs outcomes
- introduction:
  - state the software-engineering problem first
  - keep quantum as the stress-test domain
- results:
  - organize by methodological claims, not by dataset chronology
- discussion / threats:
  - explicitly separate what the method proves from what remains future work

## Outputs

- final abstract
- final 4-contribution list
- final RQ1-RQ4 framing notes
- final wording note for threats and future work

## Acceptance Criteria

- [ ] The paper no longer reads like a framework or toolkit introduction.
  - This must be demonstrated in the committed manuscript-facing prose, not in
    local scratch drafts.
- [ ] The phrase "validate outcomes, not conclusions" is reflected in abstract, intro, and RQ1.
  - The committed submission-facing prose and `docs/results/main_results.md`
    must agree on this framing.
- [x] Cross-family evidence is framed as methodological support, not breadth-for-breadth's-sake.
  - The MaxCut `E1` `1.0` false-reassurance rate is explicitly scoped to
    the MaxCut `E1` population; the cross-family `14/27 = 51.9%` rate is
    presented as evidence that the phenomenon is "structural but
    population-dependent", not as a universality claim. Language must remain
    consistent across the committed paper-facing prose and the public
    results summaries.
- [ ] Future-work items such as protocol compiler / workflow layer are explicitly deferred.
  - `README.md` and the final threats/discussion prose must carry the same
    deferred-scope language.

## Paper-facing Scoping Rules (Locked)

These scoping rules are now invariants of the paper-facing framing and
must survive any future rewrite of the abstract, introduction, or results
sections:

- The `1.0` false-reassurance rate is conditional on the MaxCut `E1`
  population. The unified cross-family rate is `14/27 = 51.9%`.
- Exact minimal sufficient perturbation subsets are "compact sufficient
  perturbation subsets" or "explanatory witnesses", never "causal root
  causes".
- RQ4 cost comparisons are "same-agreement, different-cost" comparisons.
  Adaptive policies help most on clear cases and remain expensive near the
  decision boundary (`W5` near-boundary budget jumps: `adaptive_ci` `57 ->
  257`; `adaptive_ci_tuned` `17 -> 65`).
- `S1` is a backend-conditioned transpile-only structural portability
  study across IBM fake backends, not a full noisy-device replay.
- `W4` is a protocol-consistency scaffold with "author-side reference
  annotations". Inter-rater agreement (kappa) is reported only when real
  external raters are present.

## Dependencies

- [00_OVERVIEW.md](./00_OVERVIEW.md)
- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)
- [03_E2_BASELINE_COMPARISON.md](./03_E2_BASELINE_COMPARISON.md)
- [04_E3_SCOPE_ROBUSTNESS.md](./04_E3_SCOPE_ROBUSTNESS.md)
- [05_E4_EXACT_MOS.md](./05_E4_EXACT_MOS.md)
- [06_E5_CROSS_FAMILY.md](./06_E5_CROSS_FAMILY.md)
- [07_E6_REAL_HARDWARE.md](./07_E6_REAL_HARDWARE.md)

## Status

- [ ] Not started
- [x] In progress
- [ ] Done

## Artifacts

- [docs/results/main_results.md](../../../docs/results/main_results.md)
- [docs/results/evaluation_readiness.md](../../../docs/results/evaluation_readiness.md)

## Notes

This is the final integrator task. Do not mark it done until the committed
submission-facing prose is frozen and reviewed.
