# Design Your Own Case

This is the best repository entry point if you want to create your own ClaimStab case.

Use this guide when you are asking:

- Can I add a new experiment with only a YAML spec?
- When do I need a custom external task plugin?
- What does the framework already provide for me?
- Which example should I copy first?

## What The Framework Already Provides

If your case fits the ClaimStab contract, the framework already provides:

- perturbation presets such as `compilation_only_exact`, `sampling_only_exact`, and `combined_light_exact`
- configuration-selection policies such as `full_factorial`, `random_k`, and `adaptive_ci`
- claim inference for `ranking`, `decision`, and `distribution`
- conservative verdicts: `stable`, `unstable`, `inconclusive`
- standard run artifacts:
  - `claim_stability.json`
  - `rq_summary.json`
  - `robustness_map.json`
  - `scores.csv`
  - `stability_report.html`
- evidence validation through `python -m claimstab.cli validate-evidence`

## What You Must Provide

Every new case needs:

1. A YAML spec
2. A task and method setup
3. A claim definition
4. A perturbation preset or preset list
5. A sampling policy
6. An output directory

## Case Type A: Built-in Task, No New Python Needed

Use this route if your task already exists in the repo and you only want a new combination of:

- task parameters
- methods
- claims
- perturbation presets
- sampling settings

What you provide:

- one new spec file

What you run:

```bash
python -m claimstab.cli validate-spec --spec <your_spec.yml>
python -m claimstab.cli run --spec <your_spec.yml> --out-dir <your_output_dir> --report
python -m claimstab.cli validate-evidence --json <your_output_dir>/claim_stability.json
```

Reference example:

- [E1 MaxCut spec](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml)

## Case Type B: New Task Family With An External Plugin

Use this route if the task itself is new.

What you provide:

- a Python task class with `instances(...)` and `build(...)`
- a spec with:
  - `task.kind: external`
  - `task.entrypoint: module.path:ClassName`

What the task plugin must return:

- one executable workflow per `(instance, method)`
- a circuit
- a metric function from counts to a scalar metric

Task contract:

- [task plugin contract](/Users/mac/Documents/GitHub/ClaimStab-QC/claimstab/tasks/base.py)

Reference external examples:

- [QEC pilot spec](/Users/mac/Documents/GitHub/ClaimStab-QC/examples/community/qec_pilot_demo/spec_qec_decoder.yml)
- [VQE pilot spec](/Users/mac/Documents/GitHub/ClaimStab-QC/examples/community/vqe_pilot_demo/spec_vqe_h2.yml)
- [Max-2-SAT pilot spec](/Users/mac/Documents/GitHub/ClaimStab-QC/examples/community/max2sat_pilot_demo/spec_max2sat.yml)

## Case Type C: Paper-Only Batch Study

Only write a custom script if you are doing orchestration beyond one normal run, for example:

- policy comparisons across many claims
- reanalysis over old run outputs
- figure generation
- human-rating summary tables

Reference scripts:

- [RQ4 policy comparison](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/scripts/exp_rq4_evaluation_v2.py)
- [W3 metric baseline derivation](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/scripts/derive_rq1_metric_baselines_v3.py)
- [W4 admissibility summary](/Users/mac/Documents/GitHub/ClaimStab-QC/paper/experiments/scripts/summarize_admissibility_v3.py)

## Recommended Starting Point

If you are new, copy one of these first:

- lightweight built-in run:
  - [claim_stability_demo.py](/Users/mac/Documents/GitHub/ClaimStab-QC/examples/community/claim_stability_demo.py)
- external task with lower-is-better metric:
  - [qec_pilot_demo](/Users/mac/Documents/GitHub/ClaimStab-QC/examples/community/qec_pilot_demo)
- external task with a variational second-family setup:
  - [vqe_pilot_demo](/Users/mac/Documents/GitHub/ClaimStab-QC/examples/community/vqe_pilot_demo)

## Minimal Workflow

```bash
python -m claimstab.cli validate-spec --spec <your_spec.yml>
python -m claimstab.cli run --spec <your_spec.yml> --out-dir output/examples/<your_case> --report
python -m claimstab.cli validate-evidence --json output/examples/<your_case>/claim_stability.json
```

If your goal is dataset publication rather than just local runs, continue with:

- [ClaimAtlas guide](/Users/mac/Documents/GitHub/ClaimStab-QC/docs/atlas.md)

## Output Convention

Community and custom cases should write under:

- `output/examples/<your_case>/`

Paper-only studies should write under:

- `output/paper/evaluation_v2/...`
- `output/paper/evaluation_v3/...`
