# Design Your Own Case

This is the canonical guide for creating a new ClaimStab case.

Use it to answer four questions:

1. What do I need to provide?
2. What does ClaimStab already provide?
3. When is a YAML spec enough?
4. When do I need a custom external task plugin?

## What ClaimStab Already Provides

If your case fits the normal contract, ClaimStab already provides:

- perturbation presets such as `compilation_only_exact`, `sampling_only_exact`, and `combined_light_exact`
- selection policies such as `full_factorial`, `random_k`, and `adaptive_ci`
- claim inference for:
  - `ranking`
  - `decision`
  - `distribution`
- conservative verdicts:
  - `stable`
  - `unstable`
  - `inconclusive`
- standard outputs:
  - `claim_stability.json`
  - `rq_summary.json`
  - `robustness_map.json`
  - `scores.csv`
  - `stability_report.html`
- evidence validation:
  - `python -m claimstab.cli validate-evidence --json <run_dir>/claim_stability.json`

## What You Must Provide

Every new case needs:

1. a spec YAML
2. a task and method setup
3. one or more claims
4. a perturbation preset or preset list
5. a sampling policy
6. an output directory

## Case Type A: Built-In Task, Spec Only

Use this route when the task already exists and you only need a new combination of:

- task parameters
- methods
- claims
- perturbation presets
- sampling settings

What you provide:

- one new spec file

Run it with:

```bash
python -m claimstab.cli validate-spec --spec <your_spec.yml>
python -m claimstab.cli run --spec <your_spec.yml> --out-dir output/examples/<your_case> --report
python -m claimstab.cli validate-evidence --json output/examples/<your_case>/claim_stability.json
```

Reference:

- `paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml`

## Case Type B: External Task Plugin

Use this route when the task itself is new.

What you provide:

- a Python task class
- a spec with:
  - `task.kind: external`
  - `task.entrypoint: module.path:ClassName`

Task contract:

- `claimstab/tasks/base.py`

Your plugin must provide:

- `instances(...)`
- `build(...)`

`build(...)` should return:

- a circuit
- a metric function from counts to a scalar metric

Working examples:

- `examples/community/custom_task_demo/spec_toy.yml`
- `examples/community/qec_pilot_demo/spec_qec_decoder.yml`
- `examples/community/vqe_pilot_demo/spec_vqe_h2.yml`
- `examples/community/max2sat_pilot_demo/spec_max2sat.yml`

## Case Type C: Paper-Orchestration Script

Only add a paper script when you are doing more than one normal run, for example:

- batch execution over many specs
- paper-only reanalysis of existing outputs
- figure generation
- human-rating summaries

Examples:

- `paper/experiments/scripts/derive_rq1_metric_baselines_v3.py`
- `paper/experiments/scripts/summarize_admissibility_v3.py`
- `paper/experiments/scripts/run_real_hardware_slice_v1.py`

## Recommended Starting Points

- smallest working community run:
  - `examples/community/claim_stability_demo.py`
- smallest external-task example:
  - `examples/community/custom_task_demo/spec_toy.yml`
- lower-is-better external metric:
  - `examples/community/qec_pilot_demo/`
- variational second-family example:
  - `examples/community/vqe_pilot_demo/`

## Output Convention

Community and custom cases should write under:

- `output/examples/<your_case>/`

Paper-only studies should write under:

- `output/paper/evaluation_v2/...`
- `output/paper/evaluation_v3/...`
- `output/paper/evaluation_v4/...`
