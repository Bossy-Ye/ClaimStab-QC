# Custom Task Quickstart (5 Minutes)

This is the fastest path for a user with their own problem.

## What You Prepare vs What ClaimStab Handles

You prepare:
1. Task logic in one Python file (`instances` + `build`).
2. Method choices and claim definitions in one spec YAML.

ClaimStab handles:
1. Perturbation matrix execution.
2. Claim stability estimation + confidence intervals.
3. Conservative decisions (`stable` / `unstable` / `inconclusive`).
4. Report generation and dataset publishing.

## Step 1: Generate starter files

```bash
claimstab init-external-task --name my_problem --out-dir examples/my_problem_demo
```

Generated files:
- `examples/my_problem_demo/my_problem_task.py`
- `examples/my_problem_demo/spec_my_problem.yml`

## Step 2: Replace task logic

Edit `my_problem_task.py`:
1. `instances(self, suite)`: return your problem instances.
2. `build(self, instance, method)`: build circuit/workflow and define `metric_fn`.
3. Add your method kinds in the `if method.kind == ...` block.
4. Keep `metric_fn` scalar and deterministic from `counts`.

## Step 3: Run claim-stability evaluation

```bash
claimstab validate-spec --spec examples/my_problem_demo/spec_my_problem.yml
claimstab run --spec examples/my_problem_demo/spec_my_problem.yml --out-dir output/my_problem --report
```

Outputs:
- `output/my_problem/claim_stability.json`
- `output/my_problem/scores.csv`
- `output/my_problem/rq_summary.json`
- `output/my_problem/stability_report.html`

## Step 4: Publish to ClaimAtlas dataset

```bash
claimstab publish-result --run-dir output/my_problem --atlas-root atlas --contributor your_name
claimstab validate-atlas --atlas-root atlas
```

Published record:
- `atlas/submissions/<submission_id>/...`
- `atlas/index.json`

## Common Mistakes (Quick Fixes)

1. `entrypoint import` fails:
`task.entrypoint` must be `module.path:ClassName` and class name must match exactly.

2. Unknown method kind:
ensure each `methods[*].kind` in YAML is handled in your task plugin `build(...)`.

3. Empty outputs:
verify `instances(...)` returns at least one `ProblemInstance`.
