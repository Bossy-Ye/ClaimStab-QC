# RQ1 Structured Breakdowns

This note records the structured `RQ1` breakdowns that should accompany the main
metric-vs-claim result.

Primary source tables:
- [tab_mismatch_summary.csv](../../../../output/paper/icse_pack/tables/tab_mismatch_summary.csv)
- [tab_false_reassurance_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_false_reassurance_breakdown.csv)
- [tab_rq1_family_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_family_breakdown.csv)
- [tab_rq1_scope_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_scope_breakdown.csv)
- [tab_rq1_delta_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_delta_breakdown.csv)
- [tab_rq1_primary_family_sensitivity.csv](../../../../output/paper/icse_pack/tables/tab_rq1_primary_family_sensitivity.csv)
- [tab_rq1_leave_one_family_out_sensitivity.csv](../../../../output/paper/icse_pack/tables/tab_rq1_leave_one_family_out_sensitivity.csv)

## Why these breakdowns matter

The overall `RQ1` result is strong, but it should not be presented as an
undifferentiated aggregate. Reviewers will reasonably ask whether the mismatch
phenomenon is driven by:
- a single algorithm family,
- a single perturbation scope,
- or a single practical margin choice.

The role of this note is to keep the paper-facing interpretation conservative
and explicit.

## Overall result

Across `63` comparative claim variants:
- `27` are metric-positive
- `13` are claim-validated
- `14` are not validated:
  - `13` unstable
  - `1` inconclusive

So the current conditional false-reassurance rate is:
- `14 / 27 = 51.9%`

## Breakdown by algorithm family

From [tab_rq1_family_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_family_breakdown.csv):

- `MaxCut QAOA`
  - `27` variants total
  - `9` metric-positive
  - `9` false-reassurance cases
  - conditional false-reassurance rate = `100.0%`

- `Max-2-SAT QAOA`
  - `18` variants total
  - `18` metric-positive
  - `5` false-reassurance cases
  - conditional false-reassurance rate = `27.8%`

- `VQE/H2`
  - `18` variants total
  - `0` metric-positive
  - no false-reassurance denominator

Interpretation:
- the strongest mismatch is concentrated in the primary MaxCut battleground
- the phenomenon is not universal in the same form across all families
- cross-family evidence should be written as population-dependent, not uniform

## Breakdown by perturbation scope

From [tab_rq1_scope_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_scope_breakdown.csv):

- `compilation_only_exact`
  - `27` variants
  - `12` metric-positive
  - `5` false-reassurance cases
  - conditional false-reassurance rate = `41.7%`

- `sampling_only_exact`
  - `9` variants
  - `3` metric-positive
  - `3` false-reassurance cases
  - conditional false-reassurance rate = `100.0%`

- `combined_light_exact`
  - `27` variants
  - `12` metric-positive
  - `6` false-reassurance cases
  - conditional false-reassurance rate = `50.0%`

Interpretation:
- the mismatch is not confined to a single admissible scope
- execution/sampling-only variants are especially fragile in the current `RQ1` surface
- combined scopes remain important because they preserve the mismatch even when multiple operational dimensions vary together

## Breakdown by delta

From [tab_rq1_delta_breakdown.csv](../../../../output/paper/icse_pack/tables/tab_rq1_delta_breakdown.csv):

- `delta = 0.00`
  - `21` variants
  - `9` metric-positive
  - `4` false-reassurance cases
  - conditional false-reassurance rate = `44.4%`

- `delta = 0.01`
  - `21` variants
  - `9` metric-positive
  - `5` false-reassurance cases
  - conditional false-reassurance rate = `55.6%`

- `delta = 0.05`
  - `21` variants
  - `9` metric-positive
  - `5` false-reassurance cases
  - conditional false-reassurance rate = `55.6%`

Interpretation:
- the mismatch is not confined to a single practical margin choice
- the delta trend is qualitatively stable across the current three-point margin sweep

## Sensitivity checks

From [tab_rq1_primary_family_sensitivity.csv](../../../../output/paper/icse_pack/tables/tab_rq1_primary_family_sensitivity.csv):

- `MaxCut` primary-family-only:
  - `27` variants
  - `9` metric-positive
  - `9` false-reassurance cases
  - conditional false-reassurance rate = `100.0%`

From [tab_rq1_leave_one_family_out_sensitivity.csv](../../../../output/paper/icse_pack/tables/tab_rq1_leave_one_family_out_sensitivity.csv):

- leave out `VQE/H2`
  - `45` variants
  - `27` metric-positive
  - `14` false-reassurance cases
  - conditional false-reassurance rate = `51.9%`

- leave out `Max-2-SAT QAOA`
  - `45` variants
  - `9` metric-positive
  - `9` false-reassurance cases
  - conditional false-reassurance rate = `100.0%`

Interpretation:
- the main `RQ1` conclusion does not depend on the weakest proxy family
- the primary MaxCut battleground alone remains sufficient to recover the central mismatch

## Recommended paper wording

Safe wording:

> The mismatch is strongest in the MaxCut battleground but remains visible across
> multiple comparative families and admissible scopes, indicating that the
> phenomenon is structural rather than tied to a single experimental slice.

Unsafe wording:

- “all families behave the same way”
- “all scopes yield the same false-reassurance rate”
- “the mismatch is universal”

## Presentation guidance

Main paper:
- one sentence on family heterogeneity
- one sentence on scope heterogeneity
- one compact table or appendix reference

Appendix:
- include the full family/scope/delta breakdown table

## Status

- family breakdown: ready
- scope breakdown: ready
- delta breakdown: ready
- primary-family-only sensitivity: ready
- leave-one-family-out sensitivity: ready
