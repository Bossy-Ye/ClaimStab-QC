# Formal Definitions

ClaimStab models reproducibility as claim stability under software-visible perturbations.

## Perturbation Space

Let `Ω` be the perturbation space over controllable dimensions (for example: transpiler seed, optimization level, layout method, shots, simulator seed).  
Each perturbation configuration is `x ∈ Ω`.

## Claim Predicate

For a claim specification, define a binary predicate:

`C(x) ∈ {0, 1}`

where `C(x)=1` means the claim holds under perturbation `x`.

Examples:
- Ranking claim: relation between methods under margin `δ` is preserved.
- Decision claim: expected output label is in top-`k`.
- Distribution claim: distance to reference distribution is below `ε`.

## Stability

True stability is:

`s = Pr_{x~Ω}(C(x)=1)`

Since full enumeration is usually infeasible, ClaimStab estimates `s` via sampling.

## Estimation and Conservative Decision

From sampled outcomes `{C(x_i)}`:
- `ŝ = (# holds) / n`
- Wilson confidence interval: `[L, U]`

Conservative decision rule:
- `stable` iff `L >= p`
- `unstable` iff `U < p`
- `inconclusive` otherwise

where `p` is the target stability threshold.

## Clustered (Instance-Level) Stability

For benchmark suites with multiple instances, ClaimStab also reports clustered stability:
- compute stability per instance,
- bootstrap across instances to obtain CI,
- apply the same conservative decision rule.

This reduces concerns about dependence between perturbation samples within an instance.
