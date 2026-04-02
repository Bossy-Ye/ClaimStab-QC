# Main Results

This page summarizes the current paper evaluation state:

- `evaluation_v2` core bundle under `output/paper/evaluation_v2/`
- `evaluation_v3` strengthening bundle under `output/paper/evaluation_v3/`

## Evaluation Design

The current paper-facing evaluation is organized around one main battleground and several supporting studies:

- `E1`: MaxCut ranking, the primary heterogeneous claim population
- `E2`: GHZ structural ranking calibration
- `E3`: Bernstein-Vazirani decision calibration
- `E4`: Grover distribution fragility case
- `E5`: multi-policy cost/agreement study on an expanded 495-configuration grid
- `S1`: backend-conditioned transpile-only structural portability
- `S2`: boundary-stress pack
- `QEC`: repetition-code portability illustration

The core experiments (`E1`-`E4`, `S2`, `QEC`) are evaluated over small exact scopes:

- `compilation_only_exact`
- `sampling_only_exact`
- `combined_light_exact`

`E5` uses an expanded `sampling_policy_eval` space to make cost tradeoffs non-trivial.

The strengthening bundle adds:

- `W1`: second-family extensions (`VQE/H2` pilot and `Max-2-SAT/QAOA`)
- `W3`: stronger metric-centric baselines for RQ1
- `W4`: admissibility-study checklist plus human-rating summary scaffold
- `W5`: near-boundary policy pack

## Headline Findings

- `E1` yields `25 unstable`, `2 stable`, `0 inconclusive` claim-space-delta variants.
- `E2` yields `4 stable`, `8 inconclusive`.
- `E3` yields `4 stable`.
- `E4` yields `4 unstable`.
- `S2` yields `16 unstable`.
- `QEC` yields `3 stable`, `1 unstable`.
- `E5` shows perfect agreement (`1.0`) for all evaluated policies against `full_factorial`.

## RQ1: Why Claim-Centric Validation Is Needed

`E1` is the strongest necessity signal. Fragility is not a rare edge case in the main MaxCut population: almost every comparative claim variant becomes unstable under admissible perturbations.

By scope, the E1 verdict distribution is:

- `compilation_only_exact`: `2 stable / 7 unstable`
- `sampling_only_exact`: `0 stable / 9 unstable`
- `combined_light_exact`: `0 stable / 9 unstable`

By delta, the distribution is:

- `delta = 0.00`: `1 stable / 8 unstable`
- `delta = 0.01`: `1 stable / 8 unstable`
- `delta = 0.05`: `0 stable / 9 unstable`

The strongest baseline mismatch in the current rerun comes from conventional metric reporting rather than from the stored single-run baseline. Using a fixed 5-run metric summary, `9/9` apparently consistent advantages are still classified as unstable by ClaimStab-QC, yielding a metric-based false-reassurance rate of `1.0`.

The representative mismatch case is:

- claim: `QAOA_p2 > QAOA_p1`
- scope: `compilation_only_exact`
- `delta = 0.05`
- metric view: `mean_diff = 0.1190`, `95% CI = [0.1059, 0.1321]`
- claim-centric view: `stability_hat = 0.7897`, `95% CI = [0.7598, 0.8169]`, verdict = `unstable`

This is the main empirical reason the project argues for claim-centric validation rather than metric-centric reporting alone.

## RQ2: Semantic Discrimination Across Claim Families

ClaimStab-QC does not collapse to a trivial all-unstable pattern.

Aggregated over the completed `evaluation_v2` runs:

- `ranking`: `9 stable / 42 unstable / 8 inconclusive`
- `decision`: `4 stable / 0 unstable / 0 inconclusive`
- `distribution`: `0 stable / 4 unstable / 0 inconclusive`

Interpretation:

- `E3` is the clearest stable control: all four BV decision variants are stable.
- `E4` is the clearest fragile control: all four Grover distribution variants are unstable.
- `E2` is mixed rather than uniformly stable: it becomes inconclusive at higher deltas because the confidence interval overlaps the `tau = 0.95` threshold.
- `S2` does not show abstention in the current rerun; it collapses into direct fragility (`16 unstable`).
- `QEC` is supporting portability evidence only, not a main source of generalization claims.

## RQ3: Diagnostic Value

The strongest diagnostic evidence comes from the ranking experiments (`E1` and `S2`).

Dominant perturbation drivers follow the declared scope:

- in `compilation_only_exact`, the main drivers are `layout_method` and `seed_transpiler`
- in `sampling_only_exact`, the main drivers are `seed_simulator` and `shots`
- in `combined_light_exact`, `seed_simulator` remains dominant, with compilation factors still visible

Driver explanations are reasonably consistent across neighboring unstable variants:

- `E1` top-driver consistency: `0.8333`
- `S2` top-driver consistency: `0.9444`

The current repository now materializes exact MOS objects on the main-paper exact spaces (`compilation_only_exact`, `sampling_only_exact`, `combined_light_exact`).

Supplementary comparison outputs live under:

- `output/paper/evaluation_v4/pack/tables/tab_c_exact_vs_greedy_mos.csv`

These should still be written as compact sufficient perturbation subsets / explanatory witnesses, not as causal root-cause claims.

## RQ4: Cost-efficiency and Practicality

`E5` is now a substantive result rather than a placeholder.

Across the 9 available MaxCut ranking claim-pair/delta variants on the expanded 495-configuration grid:

- `full_factorial`: `495` selected configurations
- `random_k_32`: `33`
- `random_k_64`: `65`
- `adaptive_ci`: `57`
- `adaptive_ci_tuned`: `17`

All five strategies agree with the `full_factorial` reference on every evaluated variant (`agreement = 1.0`).

The strongest practical result is therefore:

- `adaptive_ci_tuned` preserves all reference decisions at a fraction of the cost

`S1` should be described carefully. The current completed output is a backend-conditioned transpile-only structural portability study, not a full noisy-device claim-centric rerun. Within that controlled scope it is fully stable:

- `90/90 stable` rows across five fake IBM backends and two structural metrics

## Scope Caveat

## Strengthening Additions (`evaluation_v3`)

- `W1 VQE/H2 pilot`: `15 stable / 2 unstable / 1 inconclusive`
- `W1 Max-2-SAT`: `13 stable / 4 unstable / 1 inconclusive`
- `W3 matched-scope metric baseline`: `9/9` metric-supportive E1 variants remain false reassurance
- `W3 sensitivity`: the metric false-reassurance rate stays at `1.0` from `10` through `495` sampled configurations on the expanded grid
- `W5 near-boundary`: adaptive policies remain correct but consume much more budget (`adaptive_ci`: `57 -> 257`; `adaptive_ci_tuned`: `17 -> 65`)
- `W4`: the repository now includes an 18-item admissibility checklist with author-side reference labels and explicit Q1/Q2/Q3 trigger rules for borderline cases such as noise scaling and 10x shot budgets, plus a human-rating summary pipeline

The default repository state intentionally does not report a submission-facing kappa value. Inter-rater agreement should only be reported after collecting real external ratings; otherwise W4 should be described as a checklist and analysis scaffold, not as completed human-subject evidence.

Conditional robustness is not the same as correctness.

All `stable`, `unstable`, and `inconclusive` outcomes reported here are relative to:

- the formalized claim specification
- the declared perturbation scope
- the configured decision threshold and confidence rule

This is especially important for the MaxCut ranking results: a stable verdict means the claim relation is robust under the declared scope, not that the natural-language conclusion has been universally proven true.

## Artifact Entry Points

- core summary root: `output/paper/evaluation_v2/README.md`
- strengthening summary root: `output/paper/evaluation_v3/README.md`
- core raw runs: `output/paper/evaluation_v2/runs/`
- strengthening runs: `output/paper/evaluation_v3/runs/`
- core derived tables: `output/paper/evaluation_v2/derived_paper_evaluation/`
- strengthening derived tables: `output/paper/evaluation_v3/derived_paper_evaluation/`
- strengthening figure pack: `output/paper/evaluation_v3/pack/figures/`
