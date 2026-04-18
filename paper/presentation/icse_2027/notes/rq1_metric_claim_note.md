# RQ1 Note: Metric vs Claim

`RQ1` evaluates whether a metric baseline that appears to support a comparative
outcome also validates the reported claim under admissible operational
variability.

The current paper-facing comparison surface is restricted to:
- comparative / ranking claims,
- one frozen metric baseline,
- three algorithm families:
  - MaxCut QAOA
  - Max-2-SAT QAOA
  - VQE/H2 diagonal proxy pilot

It is not intended to stand for all claim families or all evaluation baselines.

## Current core result

Across `63` comparative claim variants:
- `27` are metric-positive
- among those metric-positive variants:
  - `13` are claim-validated
  - `13` are claim-unstable
  - `1` is claim-inconclusive

This yields:
- conditional false-reassurance rate = `14 / 27 = 51.9%`

## Interpretation

The result supports the paper's central methodological point:

> empirical evaluation can statistically support outcomes without explicitly
> validating conclusions.

The strongest mismatch is concentrated in the MaxCut battleground, while the
cross-family breakdown shows that the phenomenon is population-dependent rather
than universal.

## Paper-facing caution

Do not write this result as:
- a universal statement about all claim families
- a universal statement about all baselines
- a newly introduced inference engine

Write it as:
- a unified paper-facing comparison surface over comparative claims
- under one frozen metric baseline
- showing direct metric-claim discrepancy
