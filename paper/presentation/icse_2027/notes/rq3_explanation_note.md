# RQ3 Note: Explanation and Validity

`RQ3` has two jobs:
- show that verdicts depend on explicitly declared admissible scope
- show that claim failure can be explained by compact sufficient perturbation subsets

Primary generated sources:
- [scope_robustness.csv](../../../../output/paper/evaluation_v4/derived_paper_evaluation/RQ2_semantics/scope_robustness.csv)
- [fig_b_scope_robustness.png](../../../../output/paper/evaluation_v4/pack/figures/main/fig_b_scope_robustness.png)
- [tab_c_exact_vs_greedy_mos.csv](../../../../output/paper/evaluation_v4/pack/tables/tab_c_exact_vs_greedy_mos.csv)

## Main reading

Scope robustness:
- some claims transport stably across nearby admissible scopes
- some claims remain robustly unstable
- near-boundary claims can flip under small scope changes

Exact MOS:
- where the factor space is tractable, exact minimal overturn sets replace greedy approximations
- this turns diagnostics from informal “important factors” into compact sufficient witness sets

## Safe paper-facing takeaway

ClaimStab-QC provides:
- explanation artifacts, not just verdicts
- and explicit scope sensitivity, not just hidden nuisance assumptions

## Wording caution

Do not describe witness sets as:
- root cause proofs
- causal explanations

Describe them as:
- compact sufficient perturbation subsets
- exact or approximate explanatory witnesses
