# Experiment Matrix

This matrix defines the active `evaluation_v2` experiment set for evaluation and artifact review.
Older output roots under `output/presentations/large` and `output/paper/{artifact,pack,multidevice}` have been retired.

## Scope Classes
- **Core**: required for paper claims and primary figures.
- **Supporting**: broadens external validity but is not required for accepting core methodology claims.

## Active Matrix

| ID | Purpose | Spec / Command | Fixed Controls | Primary Outputs |
|---|---|---|---|---|
| E1 | Main empirical battleground (MaxCut) | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml --out-dir output/paper/evaluation_v2/runs/E1_maxcut_main --report` | `full_factorial`, exact scopes = `compilation_only_exact,sampling_only_exact,combined_light_exact` | `claim_stability.json`, `rq_summary.json`, `robustness_map.json`, `stability_report.html` |
| E2 | Structural ranking calibration (GHZ) | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e2_ghz_structural.yml --out-dir output/paper/evaluation_v2/runs/E2_ghz_structural --report` | `full_factorial`, exact compilation/mixed scopes | `claim_stability.json`, `rq_summary.json` |
| E3 | Decision-claim calibration (BV) | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e3_bv_decision.yml --out-dir output/paper/evaluation_v2/runs/E3_bv_decision --report` | `full_factorial`, exact execution/mixed scopes | `claim_stability.json`, `rq_summary.json` |
| E4 | Distribution-claim fragility case (Grover) | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e4_grover_distribution.yml --out-dir output/paper/evaluation_v2/runs/E4_grover_distribution --report` | `full_factorial`, exact execution/mixed scopes | `claim_stability.json`, `rq_summary.json` |
| E5 | Multi-claim policy comparison | `python paper/experiments/scripts/exp_rq4_evaluation_v2.py --out output/paper/evaluation_v2/runs/E5_policy_comparison` | expanded 495-config `sampling_policy_eval`; reference = `full_factorial` | `rq4_policy_summary.json`, RQ4 figures |
| S1 | Backend-conditioned structural portability | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/s1_multidevice_portability.yml --out-dir output/paper/evaluation_v2/runs/S1_multidevice_portability` | transpile-only structural portability across five fake backends | `combined_summary.json` |
| S2 | Boundary challenge pack | `python paper/experiments/scripts/exp_boundary_challenge.py --spec paper/experiments/specs/evaluation_v2/s2_boundary.yml --out output/paper/evaluation_v2/runs/S2_boundary` | `full_factorial`, exact execution/mixed scopes | `claim_stability.json`, `boundary_summary.json` |
| QEC | Supporting portability illustration | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/qec_portability.yml --out-dir output/paper/evaluation_v2/runs/QEC_portability --report` | `full_factorial`, exact execution/mixed scopes | `claim_stability.json`, `robustness_map.json` |

## Supporting Studies

| ID | Purpose | Command | Output |
|---|---|---|---|
| S4 | Synthetic-truth calibration | `python -m claimstab.analysis.synthetic_truth --out output/paper/evaluation_v2/derived_paper_evaluation/RQ4_practicality/synthetic_truth.json` | synthetic coverage/decision calibration summary |
| S5 | Mutation sanity check | `python paper/experiments/scripts/exp_mutation_sanity.py --run-dir output/paper/evaluation_v2/runs/E1_maxcut_main --out output/paper/evaluation_v2/derived_paper_evaluation/RQ2_semantics/mutation_sanity_summary.json` | `mutation_sanity_summary.json` |

## Evaluation v2 Orchestration

```bash
python paper/experiments/scripts/reproduce_evaluation_v2.py --layout-only
python paper/experiments/scripts/reproduce_evaluation_v2.py
```

## Lock Rules
- Keep `output/paper/evaluation_v2/` as the active paper output root.
- Keep CLI commands and argument semantics backward compatible.
- Additive fields are allowed; destructive renames of core artifact keys are not.
- Any behavior-affecting change must pass `check_refactor_compat` and `validate-evidence`.
