# 11 Benchmark External Validation

## Goal

Strengthen external validity by showing that the metric-versus-claim discrepancy
is not confined to the original study families, while preserving the paper's
claim-centric design.

## Scope Freeze

- This task is deferred until the core ICSE claim-centric evidence surface is stable.
- It must not replace `02_E1_METRIC_VS_CLAIM`.
- It must not turn the paper into a benchmark-coverage paper.
- Benchmark suites are used only as an external validation layer.

## Problem Framing

Benchmark suites provide circuit families, not ready-made claim schemas.
Therefore this task must proceed in the following order:

1. define comparative claim templates,
2. map benchmark circuit families onto those templates,
3. evaluate claim-level behavior under admissible scope.

Do not invert this order.

## Candidate Benchmark Families

Preferred first wave:

- `GHZ`
- `BV`
- `HS`
- `W-State`
- `VQE`
- one of `QAOA-P` or `QAOA-R`

Defer unless clearly justified:

- `QSVM`
- `TL`

## Inputs

- existing core claim-centric evidence from:
  - [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)
  - [03_E2_BASELINE_COMPARISON.md](./03_E2_BASELINE_COMPARISON.md)
  - [04_E3_SCOPE_ROBUSTNESS.md](./04_E3_SCOPE_ROBUSTNESS.md)
- benchmark-family sources such as:
  - SupermarQ-style application-oriented benchmark circuits
  - MQT Bench generated benchmark families
  - QASMBench-style low-level circuit corpora

## Outputs

- one benchmark-backed external validation dataset
- one compact benchmark-family summary table
- optional one supporting figure
- one short note that explains how benchmark families extend, but do not replace, the original claim-centric study

## Acceptance Criteria

- [ ] The benchmark study is explicitly framed as external validation, not as the main paper design.
- [ ] Every benchmark family is attached to an explicit comparative claim template.
- [ ] At least one result shows that the observed mismatch phenomenon is not confined to the original three-family study.
- [ ] The paper-facing note clearly states that benchmark families are test objects, not the primary analysis unit.
- [ ] The task does not introduce uncontrolled benchmark sprawl.

## Dependencies

- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)
- [03_E2_BASELINE_COMPARISON.md](./03_E2_BASELINE_COMPARISON.md)
- [04_E3_SCOPE_ROBUSTNESS.md](./04_E3_SCOPE_ROBUSTNESS.md)
- [10_PAPER_FRAMING.md](./10_PAPER_FRAMING.md)

## Status

- [x] Not started
- [ ] In progress
- [ ] Done

## Notes

This task exists to improve external validity without sacrificing the paper's
software-engineering methodology identity.

The safe paper-facing sentence is:

> We retain RQ1's core evidence on comparative claim populations, and use
> benchmark-derived scalable circuit families only as an external validation
> layer rather than as a replacement for the claim-centric study design.
