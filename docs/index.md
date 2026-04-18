# ClaimStab-QC

ClaimStab-QC is a claim-centric validation methodology for quantum software experiments.

Its central claim is that empirical evaluation often validates outcomes, but not conclusions.

The method evaluates reported claims under controlled perturbation spaces and returns conservative verdicts:

- `stable`
- `unstable`
- `inconclusive`

## Use This Site For One Of Three Jobs

### 1. Design And Run Your Own Case

Start here if you want to use ClaimStab as a framework rather than reproduce the paper:

- [Design Your Own Case](design_your_own_case.md)
- [Examples & Outputs](examples.md)
- [Quickstart](quickstart.md)

### 2. Inspect The Paper Evidence

Start here if you are reading the paper, reviewing the artifact, or checking current results:

- [Main Results](results/main_results.md)
- [Figures](results/figures.md)
- [Experiment Matrix](experiment_matrix.md)
- [Reproduce](reproduce.md)

### 3. Use Advanced Publication Surfaces

Only use these after you already know the basic run workflow:

- [ClaimAtlas guide](atlas.md)
- [Dataset Registry](dataset_registry.md)
- [Live Claim Explorer](explorer.md)

## Core Outputs

| File | Purpose |
|---|---|
| `claim_stability.json` | Per-experiment claim outcomes, CI, decisions, and evidence links |
| `rq_summary.json` | Aggregated summaries and diagnostics |
| `robustness_map.json` | Conditional stability cells and compact witness summaries |
| `scores.csv` | Raw evaluation rows |
| `stability_report.html` | Human-readable report |

![ClaimStab Pipeline](assets/pipeline.svg)

## Concepts

- [Claims](concepts/claims.md)
- [Formal Definitions](concepts/formal_definitions.md)
- [Perturbations](concepts/perturbations.md)
- [Compatibility Contract](compatibility_contract.md)
