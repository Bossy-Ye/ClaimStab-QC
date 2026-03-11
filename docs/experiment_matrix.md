# Experiment Matrix (Locked)

This matrix defines the canonical experiment set for evaluation and artifact review.

## Scope Classes
- **Core**: required for paper claims and primary figures.
- **Supporting**: broadens external validity but is not required for accepting core methodology claims.

## Core Matrix

| ID | Purpose | Spec / Command | Fixed Controls | Primary Outputs |
|---|---|---|---|---|
| E1 | Ranking prevalence + heterogeneity (MaxCut) | `python -m claimstab.cli run --spec specs/paper_main.yml --out-dir output/presentation_large/large/maxcut_ranking --report` | `random_k`, seed-controlled, spaces = `compilation_only,sampling_only,combined_light` | `claim_stability.json`, `rq_summary.json`, `robustness_map.json`, `stability_report.html` |
| E2 | Structural ranking control (GHZ) | `python -m claimstab.cli run --spec specs/paper_structural.yml --out-dir output/presentation_large/large/ghz_structural --report` | transpile-centric structural metrics | `claim_stability.json`, `rq_summary.json` |
| E3 | Decision-claim control (BV) | `python -m claimstab.cli run --spec specs/paper_decision.yml --out-dir output/presentation_large/large/bv_decision --report` | top-k decision claims, seeded perturbation sampling | `claim_stability.json`, `rq_summary.json` |
| E4 | Distribution-claim stress (Grover) | `python -m claimstab.cli run --spec specs/paper_distribution.yml --out-dir output/presentation_large/large/grover_distribution --report` | JS/TVD distance claims with explicit epsilon | `claim_stability.json`, `rq_summary.json` |
| E5 | Cost-confidence tradeoff | `python examples/exp_rq4_adaptive.py --out output/presentation_large/rq4_adaptive` | full/random_k/adaptive_ci plus tuned adaptive target (`adaptive_ci_tuned`) | `rq4_adaptive_summary.json`, `rq4_adaptive_tuned_summary.json`, RQ4 figures |

## Supporting Matrix

| ID | Purpose | Command | Output |
|---|---|---|---|
| S1 | Device-aware variability | `python -m claimstab.cli run --spec specs/paper_device.yml --out-dir output/multidevice_full` | `combined_summary.json` and per-mode summaries |
| S2 | Boundary challenge pack | `python examples/exp_boundary_challenge.py --out output/presentation_large/boundary` | `claim_stability.json`, `boundary_summary.json` |
| S3 | Optional method-set batch | `python examples/exp_icse_methodset.py --out output/presentation_large/icse_methodset` | per-track runs + `methodset_summary.json` |
| S4 | Synthetic-truth calibration | `python -m claimstab.analysis.synthetic_truth --out output/presentation_large/synthetic_truth.json` | synthetic coverage/decision calibration summary |

## Canonical Packaging

```bash
python -m claimstab.scripts.export_paper_pack \
  --input-root output/presentation_large \
  --out output/paper_pack \
  --which large
```

## Lock Rules
- After the tuned E5 adaptive run is generated, treat E1-E5 as frozen baseline for paper evaluation.
- Keep CLI commands and argument semantics backward compatible.
- Keep JSON/CSV artifact paths and key names backward compatible.
- Additive fields are allowed; destructive renames are not.
- Any behavior-affecting change must pass `check_refactor_compat` and `validate-evidence`.
