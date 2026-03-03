# Dataset Registry

This page lists current ClaimAtlas submissions with problem/task, algorithms, claims, and perturbation settings.

_Generated at 2026-03-03T14:32:50+00:00 from `atlas/index.json`._

## Submission Overview

| Submission | Task | Suite | Claim Types | Spaces | Contributor |
|---|---|---|---|---|---|
| `bv_demo_working_example` | `bv` | `core` | `decision` | `sampling_only` | `codex_demo` |
| `outside_user_portfolio_v1` | `portfolio_allocation` | `core` | `ranking` | `sampling_only, combined_light` | `outside_user_demo` |

## Submission `bv_demo_working_example`

- Title: BV Atlas Demo
- Created (UTC): 2026-03-03T13:48:24+00:00
- Task: `bv`
- Suite: `core`
- Claim types: `decision`
- Algorithms (methods): `BVOracle, RandomBaseline`

Claims:
- `decision: BVOracle, top_k=1, label_key=target_label`
- `decision: BVOracle, top_k=3, label_key=target_label`

Perturbation / Sampling settings:

| space_preset | mode | sample_size | seed | sampled_with_baseline | perturbation_space_size |
|---|---:|---:|---:|---:|---:|
| `sampling_only` | `random_k` | `10` | `7` | `11` | `100` |

Reference baseline configuration:

```json
{
  "seed_transpiler": 0,
  "optimization_level": 1,
  "layout_method": "sabre",
  "shots": 16,
  "seed_simulator": 0
}
```

Artifacts:
- `claim_stability.json`: [atlas/submissions/bv_demo_working_example/claim_stability.json](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/bv_demo_working_example/claim_stability.json)
- `metadata.json`: [atlas/submissions/bv_demo_working_example/metadata.json](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/bv_demo_working_example/metadata.json)
- `rq_summary.json`: [atlas/submissions/bv_demo_working_example/rq_summary.json](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/bv_demo_working_example/rq_summary.json)
- `scores.csv`: [atlas/submissions/bv_demo_working_example/scores.csv](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/bv_demo_working_example/scores.csv)
- `stability_report.html`: [atlas/submissions/bv_demo_working_example/stability_report.html](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/bv_demo_working_example/stability_report.html)

## Submission `outside_user_portfolio_v1`

- Title: Outside User Portfolio Demo
- Created (UTC): 2026-03-03T14:12:21+00:00
- Task: `portfolio_allocation`
- Suite: `core`
- Claim types: `ranking`
- Algorithms (methods): `Conservative, RiskAware, UniformMix`

Claims:
- `ranking: RiskAware > UniformMix, deltas=[0.0, 0.02]`
- `ranking: UniformMix > Conservative, deltas=[0.0, 0.02]`

Perturbation / Sampling settings:

| space_preset | mode | sample_size | seed | sampled_with_baseline | perturbation_space_size |
|---|---:|---:|---:|---:|---:|
| `sampling_only` | `random_k` | `20` | `11` | `21` | `100` |
| `combined_light` | `random_k` | `20` | `11` | `21` | `720` |

Reference baseline configuration:

```json
{
  "seed_transpiler": 0,
  "optimization_level": 1,
  "layout_method": "sabre",
  "shots": 16,
  "seed_simulator": 0
}
```

Artifacts:
- `claim_stability.json`: [atlas/submissions/outside_user_portfolio_v1/claim_stability.json](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/outside_user_portfolio_v1/claim_stability.json)
- `metadata.json`: [atlas/submissions/outside_user_portfolio_v1/metadata.json](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/outside_user_portfolio_v1/metadata.json)
- `rq_summary.json`: [atlas/submissions/outside_user_portfolio_v1/rq_summary.json](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/outside_user_portfolio_v1/rq_summary.json)
- `scores.csv`: [atlas/submissions/outside_user_portfolio_v1/scores.csv](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/outside_user_portfolio_v1/scores.csv)
- `stability_report.html`: [atlas/submissions/outside_user_portfolio_v1/stability_report.html](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/submissions/outside_user_portfolio_v1/stability_report.html)

## How To Add New Dataset Rows

1. `claimstab run --spec <your_spec.yml> --out-dir output/<run_name> --report`
2. `claimstab publish-result --run-dir output/<run_name> --atlas-root atlas --contributor <you>`
3. Rebuild docs after regenerating this page.

