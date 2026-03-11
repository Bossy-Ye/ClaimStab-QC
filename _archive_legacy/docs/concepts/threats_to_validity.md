# Threats to Validity

This page states the main validity threats for ClaimStab evaluations and how to interpret them.

## Internal Validity

- **Sampling error in perturbation space**:
  Stability is estimated from sampled configurations, not full enumeration. We report Wilson confidence intervals and use conservative decisions (`stable` only when `CI_low >= p`).
- **Dependence within an instance**:
  Perturbation outcomes inside one benchmark instance are not perfectly i.i.d. We therefore report clustered (instance-level bootstrap) stability alongside pooled estimates.
- **Baseline sensitivity**:
  Flip rate is relative to a baseline configuration. ClaimStab reports naive-vs-ClaimStab disagreement to expose overclaim/underclaim risk from single-point baselines.

## Construct Validity

- **Claim semantics**:
  Ranking claims depend on `delta` (practical margin). Decision claims depend on a deterministic acceptance rule (for example top-k). Distribution claims depend on distance choice and epsilon.
- **Metric direction**:
  Structural metrics (depth, 2Q count) are typically `lower_is_better`; objective metrics are often `higher_is_better`. Specs must state this explicitly.

## External Validity

- **Task representativeness**:
  MaxCut (variational optimization), Bernstein-Vazirani decision benchmark, and GHZ structural benchmark cover different claim classes but are not exhaustive.
- **Hardware realism**:
  Main pipeline targets software-visible perturbations. Device-aware extension uses IBM fake backends and Aer noisy simulation; real-QPU drift is not the primary scope.
- **Toolchain versions**:
  Results depend on versions of Qiskit/transpiler/runtime stack. ClaimStab stores runtime metadata and reproduce commands in run artifacts.

## Conclusion Validity

- **Over-interpretation of point estimates**:
  Point stability without uncertainty can overstate confidence. ClaimStab decisions are CI-driven by design.
- **Cost-quality tradeoff**:
  Tight CI requires enough evaluations. Stability-vs-cost and adaptive sampling outputs should be read together.

