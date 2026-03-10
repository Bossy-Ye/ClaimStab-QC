# ClaimStab-QC

ClaimStab-QC is a claim-centric framework for checking whether paper conclusions remain valid under software-visible perturbations in quantum software pipelines.

## Start Here (2-3 Minutes)

If this is your first visit, follow this order:

1. [Quickstart](quickstart.md)
2. [Reproduce](reproduce.md)
3. [Output Directory Map](output_map.md)

Locked ICSE run set:
- [ICSE Experiment Matrix](icse_experiment_matrix.md)

## What ClaimStab Checks

ClaimStab evaluates claim outcomes (not only raw scores) under sampled perturbation configurations and returns conservative decisions:

- `stable`: CI lower bound >= threshold
- `unstable`: CI upper bound < threshold
- `inconclusive`: otherwise

Supported claim types:

- `ranking`
- `decision`
- `distribution`

Canonical schema:
- [claimstab/spec/schema_v1.json](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/claimstab/spec/schema_v1.json)

## Why This Matters

Experimental quantum-software conclusions are often sensitive to compiler/sampling settings. ClaimStab makes this explicit by:

1. defining claims in executable form,
2. evaluating them across perturbation spaces,
3. quantifying uncertainty with confidence intervals,
4. emitting auditable evidence and reproducible artifacts.

## Core Outputs

| File | Purpose |
|---|---|
| `claim_stability.json` | Per-experiment claim outcomes, CI, decisions, and evidence links |
| `rq_summary.json` | Aggregated RQ summaries and diagnostics |
| `robustness_map.json` | Conditional stability cells + robust core/frontier/lockdown summaries |
| `scores.csv` | Raw score/evaluation rows with timing metadata |
| `stability_report.html` | Human-readable report |

## Snapshot

!!! info "Current empirical signal"
    - `compilation_only` tends to be the most stable space.
    - `sampling_only` is the strongest instability driver.
    - `combined_light` still exposes near-tie fragility.

![ClaimStab Pipeline](assets/pipeline.svg)

## Explore / Community Capabilities (Advanced)

These are preserved as future-facing infrastructure assets, but are not required for first-time onboarding:

- [Live Claim Explorer](explorer.md)
- [Dataset Registry (from ClaimAtlas)](dataset_registry.md)
- [ClaimAtlas Guide](atlas.md)
- [Custom Task Quickstart](custom_task_quickstart.md)

## Deep-Dive Links

- [Concepts](concepts/claims.md)
- [Main Results](results/main_results.md)
- [Reproduction Contract](reproduction_contract.md)
- [Compatibility Contract](compatibility_contract.md)
- [ICSE Evidence Map](for_icse.md)
