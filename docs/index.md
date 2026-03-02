# ClaimStab-QC

ClaimStab-QC is a claim-validation suite for quantum software experiments: it checks whether paper-level conclusions remain true under software-visible perturbations, and reports statistically conservative stability decisions.

## Abstract
Experimental claims in quantum software are often reported as point outcomes from one configuration. ClaimStab-QC reframes evaluation at the claim level: for each claim, we estimate stability under sampled perturbations, compute confidence intervals, and make conservative decisions (`stable`, `unstable`, `inconclusive`). This enables reproducibility-focused reporting beyond single-run metrics.

## Key Idea
Evaluate claims, not just scores.

Given a stability threshold \(p\), a claim is considered stable only when:

\[
\text{CI}_{\text{low}}(\hat{s}) \ge p
\]

where \(\hat{s}\) is the estimated stability rate under sampled perturbation configurations.

## How It Works
1. Define claim semantics (`A >= B + δ`, threshold, decision, distribution).
2. Define perturbation space and sampling policy.
3. Run methods across sampled configurations.
4. Compute claim flips/holds and Wilson confidence intervals.
5. Emit conservative decisions plus diagnostics and report artifacts.

## Results Snapshot
!!! info "Key Results"
    - `compilation_only` is the strongest regime for stability.
    - `sampling_only` is the weakest regime and major instability driver.
    - `combined_light` remains unstable for close method comparisons (e.g., `QAOA_p2` vs `QAOA_p1`).

| Scenario | Observation |
|---|---|
| Best observed | `compilation_only`, `QAOA_p1 > RandomBaseline`, `delta=0.0`, stability ≈ `0.9958` |
| Worst observed | `sampling_only`, `QAOA_p2 > QAOA_p1`, `delta=0.05`, flip-rate ≈ `0.2831` |

![ClaimStab Pipeline](assets/pipeline.svg)

## Project Links
- [GitHub Repository](https://github.com/Bossy-Ye/ClaimStab-QC)
- [Quickstart](quickstart.md)
- [Interactive Playground](playground.md)
- [Examples & Outputs](examples.md)
- [Reproduce](reproduce.md)
- [Results](results/main_results.md)
- [Cite](cite.md)
