# Extending ClaimStab

ClaimStab is designed around three extension points:
- task adapters
- execution runners
- claim evaluators

Use the templates in `claimstab/templates/` as copy-paste starting points.

## 1) Add a New Task
1. Copy `claimstab/templates/task_skeleton.py`.
2. Implement task-specific `build(method)` and `evaluate(result)` logic.
3. Create or load instances as `ProblemInstance` payloads.
4. Plug task objects into the existing `MatrixRunner` flow.

Tip: keep task outputs scalar and deterministic per run to preserve claim evaluation semantics.

Task spec for built-in plugin:
```yaml
task:
  kind: maxcut
  suite: standard
  params: {}
```

Task spec for external plugin (`module:Class`):
```yaml
task:
  kind: external
  entrypoint: examples.custom_task_demo.toy_task:ToyTask
  suite: toy
  params:
    num_qubits: 6
    num_instances: 3
```

## 2) Add a New Runner / Backend
1. Copy `claimstab/templates/runner_skeleton.py`.
2. Implement one-run execution (`run_one`) with your backend SDK.
3. Return score + optional structural metadata (`transpiled_depth`, `transpiled_size`).
4. Integrate by constructing `MatrixRunner(backend=YourRunner(...))`.

Tip: keep backend dependencies optional/lazy when possible (same pattern as Aer/IBM extras).

## 3) Add a New Claim Type
1. Copy `claimstab/templates/claim_skeleton.py`.
2. Define claim semantics (`holds(...)`).
3. Evaluate over outcomes with `estimate_binomial_rate` + `conservative_stability_decision`.
4. Add tests for both semantics and edge-cases.

Tip: always report estimate + CI + conservative decision (`stable` / `unstable` / `inconclusive`).

## Registries / Discovery
Task plugins are discovered via:
- built-in task registry (`task.kind: maxcut`)
- external import path (`task.kind: external` + `task.entrypoint: module:Class`)

Method plugins are task-defined via `methods[*].kind`; the framework does not hardcode method kinds.

## Minimal Validation Checklist
- unit tests pass for new module
- existing core tests still pass
- JSON output still includes stability estimate + CI + decision
- docs include a runnable command for your extension

Recommended contract checks for task plugins:
- `instances(suite)` returns non-empty `ProblemInstance` list
- `build(instance, method)` returns a circuit with deterministic metric output type
- unsupported `method.kind` raises `TaskSpecError` with clear message
