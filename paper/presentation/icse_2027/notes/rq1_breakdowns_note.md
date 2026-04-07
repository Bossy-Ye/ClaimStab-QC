# RQ1 Structured Breakdowns

This note records the structured `RQ1` breakdowns that should accompany the main
metric-vs-claim result.

Primary source tables:
- [tab_mismatch_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_mismatch_summary.csv)
- [tab_false_reassurance_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_false_reassurance_breakdown.csv)

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

From [tab_mismatch_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_mismatch_summary.csv):

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

From [tab_mismatch_summary.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_mismatch_summary.csv):

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

The current generated table [tab_false_reassurance_breakdown.csv](/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/icse_pack/tables/tab_false_reassurance_breakdown.csv)
already contains the `algorithm_family × scope × delta` surface.

Paper-facing expectation:
- `delta = 0.00`
- `delta = 0.01`
- `delta = 0.05`

This should be summarized in the paper to show that the mismatch is not an
artifact of a single margin choice.

Current note:
- the source data for this breakdown already exists
- a dedicated delta-summary table or small figure is still pending curation

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
- delta breakdown source data: ready
- delta breakdown curated presentation: pending
