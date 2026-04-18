# 00 Overview

## Goal

Freeze the ICSE 2027 paper identity, contribution boundaries, and sprint rules before new execution work begins.

## Core Thesis

ClaimStab-QC is a claim-centric validation methodology for quantum software experiments, showing that empirical evaluation often validates outcomes but not conclusions.

## Four Core Contributions

1. Reported claims are treated as first-class validation objects.
2. Admissible perturbation scope is made explicit rather than remaining an implicit assumption.
3. Validation uses conservative tri-decision inference: `stable`, `unstable`, `inconclusive`.
4. The method emits explanatory evidence, not just verdicts.

## Explicit Non-Goals

- full protocol compiler implementation
- full workflow validation layer
- CI / release-gate integration
- TaskPlugin v2 full refactor
- broad platform redesign
- new large algorithm families unless they directly strengthen a core paper claim

## Deferred Strengthening

The following line of work is explicitly deferred until after the core
claim-centric ICSE evidence surface is stable:

- benchmark-backed external validation using scalable circuit suites

If pursued, this must remain:

- an external validation layer
- benchmark-family support for claim-centric analysis
- not a replacement for `02_E1_METRIC_VS_CLAIM`

## Outputs

- frozen thesis sentence
- frozen 4-contribution list
- frozen non-goal list
- one agreed sprint order

## Acceptance Criteria

- [x] Thesis sentence is fixed and used consistently in README / docs / paper drafts.
- [x] Contribution list is fixed to four items.
- [x] Non-goals are explicitly documented and agreed.
- [x] The sprint order is agreed and linked from the backlog index.

## Dependencies

None.

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

This is the control document for the rest of the sprint. If later work conflicts with this file, update this file first.
