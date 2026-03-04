# Formal Definitions

This page is the normative inference contract for ClaimStab experiments.

## 1) Perturbation Space

Let `Ω` be the space of software-visible perturbation configurations over controllable dimensions (for example transpiler seed, optimization level, layout method, shots, simulator seed).  
Each configuration is `x ∈ Ω`.

## 2) Claim Family and Predicate

Given a claim specification `θ`, ClaimStab defines a binary predicate:

`C_θ(x) ∈ {0, 1}`

where `C_θ(x)=1` means the paper-level claim holds under perturbation `x`.

Supported claim families:
- **Ranking**: relation between methods `A` and `B` with practical margin `δ` (and explicit metric direction).
- **Decision**: selected label/decision satisfies a deterministic acceptance rule (for example top-`k`).
- **Distribution**: distance between observed and reference distributions is within tolerance `ε`.

## 3) Observation Model

For each benchmark instance `i`, ClaimStab evaluates sampled configurations `x_1, ..., x_n` and records per-configuration claim outcomes:

`Y_{i,j} = C_θ(x_j)`.

A **trial** is one `(instance, perturbation configuration)` evaluation of the claim predicate.

## 4) Stability Parameter and Estimator

Population stability:

`s_θ = Pr_{x~Ω}[C_θ(x)=1]`.

From sampled outcomes, pooled estimate:

`ŝ_θ = (1/n) Σ_j Y_j`.

ClaimStab reports Wilson interval `[L, U]` for the binomial proportion.

## 5) Conservative Decision Rule

Given target stability threshold `p` and confidence level `α`:
- `stable` iff `L >= p`
- `unstable` iff `U < p`
- `inconclusive` otherwise

This rule is conservative by construction and prevents overclaiming from optimistic point estimates.

## 6) Clustered (Instance-Level) Stability

To reduce dependence concerns within an instance:
- compute per-instance stability `ŝ_i`,
- aggregate by instance mean,
- bootstrap across instances for clustered CI `[L_c, U_c]`,
- apply the same conservative decision rule.

Both pooled and clustered summaries are reported.

## 7) Sampling Policies

ClaimStab supports:
- **full_factorial**: exhaustive over configured `Ω`.
- **random_k**: fixed-size Monte Carlo sample from `Ω`.
- **adaptive_ci**: progressive sampling until CI width target is reached or budget is exhausted.

## 8) Diagnostic Attribution

For ranking flips, ClaimStab reports factor-level attribution by perturbation dimension:
- per-value flip rates,
- top unstable configurations,
- lock-down recommendations (which knob/value most reduces flips under one-knob fixing).
