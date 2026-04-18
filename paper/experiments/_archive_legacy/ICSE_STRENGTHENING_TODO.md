# ICSE Strengthening TODO

This checklist tracks the next revision wave for ClaimStab-QC.

Execution root for this wave:
- `output/paper/evaluation_v4/`

Primary goals:
- strengthen external validity without overselling the MaxCut result,
- turn admissibility into a protocol + robustness story,
- upgrade MOS from heuristic to exact on the main-paper spaces,
- prepare a real-hardware slice that can be run once credentials are available,
- tighten paper framing where the current evidence is already sufficient.

## Status Board

| ID | Theme | Task | Deliverable | Status |
| --- | --- | --- | --- | --- |
| A1 | External validity | Extend the W3 matched-scope metric baseline analysis to `W1_vqe_pilot` and `W1_max2sat_second_family`. | `output/paper/evaluation_v4/derived_paper_evaluation/RQ1_necessity/cross_family_metric_baselines.{csv,json}` | [x] |
| A2 | External validity | Build a cross-family summary figure comparing MaxCut, Max-2-SAT, and VQE verdict distributions. | `output/paper/evaluation_v4/pack/figures/main/fig_a_cross_family_verdicts.{png,pdf}` | [x] |
| A3 | External validity | Build a small cross-family table with `metric_supportive_count`, `false_reassurance_count`, and `conditional_false_reassurance_rate`. | `output/paper/evaluation_v4/pack/tables/tab_a_cross_family_false_reassurance.csv` | [x] |
| B1 | Admissibility | Replace simulated W4 raters with real labels from 2-3 colleagues. | `paper/experiments/data/admissibility_v1/ratings/rater_*.csv` | [ ] |
| B2 | Admissibility | Re-run W4 on real labels and report pairwise agreement only as protocol-consistency evidence. | `output/paper/evaluation_v4/derived_paper_evaluation/RQ2_semantics/admissibility_pairwise_kappa.csv` | [ ] |
| B3 | Admissibility | Run a scope-robustness analysis on one clear-stable, one clear-unstable, and one near-boundary claim. | `output/paper/evaluation_v4/derived_paper_evaluation/RQ2_semantics/scope_robustness.{csv,json}` | [x] |
| B4 | Admissibility | Add a scope-ablation figure showing verdict transport / flip / abstention under borderline-factor inclusion. | `output/paper/evaluation_v4/pack/figures/main/fig_b_scope_robustness.{png,pdf}` | [x] |
| C1 | MOS exactness | Upgrade main-paper MOS computation to exact subset search for `compilation_only_exact`, `sampling_only_exact`, and `combined_light_exact`. | code change in `claimstab/claims/diagnostics.py` and new `exact_mos` fields in `claim_stability.json` | [x] |
| C2 | MOS exactness | Re-run `evaluation_v2` and `evaluation_v3` diagnostics after exact MOS is enabled. | updated `output/paper/evaluation_v2/...` and `output/paper/evaluation_v3/...` | [x] |
| C3 | MOS exactness | Add a supplement table comparing `exact_mos_size`, `greedy_mos_size`, and overlap. | `output/paper/evaluation_v4/pack/tables/tab_c_exact_vs_greedy_mos.csv` | [x] |
| D0 | Real hardware | Prepare runnable real-hardware scaffold with IBM Runtime token/backend wiring. | `claimstab/runners/qiskit_ibm_runtime.py`, `paper/experiments/scripts/run_real_hardware_slice_v1.py` | [x] |
| D1 | Real hardware | Confirm which academic access path is available: `CSC/VTT Helmi`, `VTT Q50`, or IBM Open Plan. | decision note in this file or a short memo under `paper/experiments/data/` | [ ] |
| D2 | Real hardware | Run BV hardware slice on a real backend. | `output/paper/evaluation_v4/runs/D2_bv_hardware_slice/claim_stability.json` | [ ] |
| D3 | Real hardware | Run VQE/H2 hardware slice on a real backend. | `output/paper/evaluation_v4/runs/D3_vqe_hardware_slice/claim_stability.json` | [ ] |
| D4 | Real hardware | Optional: run Grover hardware slice if queue/runtime budget allows. | `output/paper/evaluation_v4/runs/D4_grover_hardware_slice/claim_stability.json` | [ ] |
| E1 | Framing | Rewrite RQ4 framing to say adaptive policies help most on clear cases, while near-boundary claims remain expensive. | paper text update | [ ] |
| E2 | Framing | Rewrite the abstract / introduction so `false-reassurance = 1.0` is explicitly scoped to the MaxCut E1 population. | paper text update | [ ] |
| E3 | Framing | Rewrite MOS wording to `compact sufficient perturbation subset` / `explanatory witness`, not causal root cause. | paper text update | [ ] |

## Execution Order

### Immediate
- [x] `C1` exact MOS on main-paper spaces
- [x] `A1` cross-family matched-scope metric baseline
- [x] `B3` scope-robustness experiment

### Next
- [ ] `B1` collect real rater CSVs
- [ ] `B2` rerun W4 on real labels
- [x] `A2` and `A3` cross-family figure/table
- [x] `C3` exact-vs-greedy supplement

### In Parallel
- [ ] `D1` choose actual hardware path
- [ ] `D2` BV hardware slice
- [ ] `D3` VQE hardware slice
- [ ] `D4` Grover hardware slice if budget permits

## Real-Hardware Slice Commands

The hardware scaffold is ready. Once you have a valid token and backend name, run one of these:

```bash
cd <repo_root>
export IBM_QUANTUM_TOKEN="<your token>"
export CLAIMSTAB_IBM_BACKEND="<backend name>"
./venv/bin/python paper/experiments/scripts/run_real_hardware_slice_v1.py \
  --spec paper/experiments/specs/evaluation_v4/d1_bv_hardware_slice.yml \
  --out-dir output/paper/evaluation_v4/runs/D2_bv_hardware_slice
```

```bash
cd <repo_root>
export IBM_QUANTUM_TOKEN="<your token>"
export CLAIMSTAB_IBM_BACKEND="<backend name>"
./venv/bin/python paper/experiments/scripts/run_real_hardware_slice_v1.py \
  --spec paper/experiments/specs/evaluation_v4/d1_vqe_hardware_slice.yml \
  --out-dir output/paper/evaluation_v4/runs/D3_vqe_hardware_slice
```

```bash
cd <repo_root>
export IBM_QUANTUM_TOKEN="<your token>"
export CLAIMSTAB_IBM_BACKEND="<backend name>"
./venv/bin/python paper/experiments/scripts/run_real_hardware_slice_v1.py \
  --spec paper/experiments/specs/evaluation_v4/d1_grover_hardware_slice.yml \
  --out-dir output/paper/evaluation_v4/runs/D4_grover_hardware_slice
```

Optional environment variables:
- `CLAIMSTAB_IBM_CHANNEL` default: `ibm_quantum_platform`
- `CLAIMSTAB_IBM_INSTANCE` for an explicit instance / CRN
- `CLAIMSTAB_IBM_ACCOUNT_NAME` if you want to reuse a saved named account

To inspect visible backends first:

```bash
cd <repo_root>
export IBM_QUANTUM_TOKEN="<your token>"
./venv/bin/python paper/experiments/scripts/run_real_hardware_slice_v1.py --list-backends
```

## Paper Framing Tasks

These are writing tasks, not new experiments, but they should be tracked in the same revision checklist.

### Abstract / Introduction
- [ ] Scope `false-reassurance = 1.0` explicitly to the MaxCut E1 population.
- [ ] Mention that behavior is population-dependent across MaxCut, Max-2-SAT, and VQE.

### RQ1
- [ ] Add cross-family metric-baseline comparison, not just MaxCut.
- [ ] State clearly that the gap is about question framing, not only sample size.

### RQ2 / W4
- [ ] Describe W4 as `protocol-consistency` evidence.
- [ ] Use `author-side reference annotations`, never `ground truth`.
- [ ] Add a sentence that verdicts are relative to the declared admissibility protocol.

### RQ3
- [ ] Replace causal language with `compact sufficient perturbation subset` / `explanatory witness`.
- [ ] State that exact subset search is used on the main-paper spaces once C1 is complete.

### RQ4
- [ ] Write that adaptive policies are most efficient on clear cases.
- [ ] Write that near-boundary claims remain expensive under a conservative decision rule.

## Completed This Round

- [x] `A1/A2/A3`
  - outputs:
    - `output/paper/evaluation_v4/derived_paper_evaluation/RQ1_necessity/cross_family_metric_baselines.csv`
    - `output/paper/evaluation_v4/pack/tables/tab_a_cross_family_false_reassurance.csv`
    - `output/paper/evaluation_v4/pack/figures/main/fig_a_cross_family_verdicts.png`
  - headline:
    - MaxCut conditional false-reassurance rate = `1.0`
    - Max-2-SAT conditional false-reassurance rate = `0.2778`
    - VQE conditional false-reassurance rate = `0.0556`

- [x] `B3/B4`
  - outputs:
    - `output/paper/evaluation_v4/derived_paper_evaluation/RQ2_semantics/scope_robustness.csv`
    - `output/paper/evaluation_v4/pack/figures/main/fig_b_scope_robustness.png`
  - headline:
    - clear stable case transports across scopes
    - clear unstable case remains unstable across scopes
    - near-boundary VQE case flips from `stable` to `unstable` under scope broadening

- [x] `C1/C2/C3`
  - code:
    - `claimstab/claims/diagnostics.py`
    - `claimstab/pipelines/main_execution.py`
    - `claimstab/results/report_renderers.py`
    - `claimstab/analysis/rq.py`
  - rerun packs:
    - `output/paper/evaluation_v2/runs/E1_maxcut_main`
    - `output/paper/evaluation_v2/runs/E2_ghz_structural`
    - `output/paper/evaluation_v2/runs/S2_boundary`
    - `output/paper/evaluation_v2/runs/QEC_portability`
    - `output/paper/evaluation_v3/runs/W1_vqe_pilot`
    - `output/paper/evaluation_v3/runs/W1_max2sat_second_family`
  - supplement table:
    - `output/paper/evaluation_v4/pack/tables/tab_c_exact_vs_greedy_mos.csv`
