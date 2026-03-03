# ClaimStab Ecosystem

The `ecosystem/` directory is the public contribution hub for tasks, methods, suites, and result packages.

## Goals

- Let contributors add reproducible benchmark assets without editing core framework code.
- Keep contributions machine-validated via metadata schemas.
- Build a shared, versioned pool of reusable ClaimStab artifacts.

## Layout

```text
ecosystem/
  schemas/               # JSON Schemas for contribution metadata
  templates/             # copy-paste YAML templates
  tasks/<task_id>/task.yaml
  methods/<method_id>/method.yaml
  suites/<suite_id>/suite.yaml
  specs/                 # optional shared experiment specs
  results/<result_id>/result.yaml
```

## Validation

```bash
claimstab validate-ecosystem --root ecosystem
```

Validation checks:
- Schema conformance (`task.yaml`, `method.yaml`, `suite.yaml`, `result.yaml`).
- Unique IDs within each collection.
- Cross-reference integrity:
  - `methods[*].task_ids` must exist in `tasks[*].id`
  - `suites[*].task_id` must exist in `tasks[*].id`
  - `results[*].task_id` and `results[*].suite_id` must exist
- Artifact paths in `result.yaml` are checked and reported as warnings when missing.

## Contribution flow

1. Copy a template from `ecosystem/templates/`.
2. Create a new folder under the correct collection.
3. Fill metadata and include reproducibility command.
4. Run `claimstab validate-ecosystem --root ecosystem`.
5. Open PR.

## Naming rules

- IDs should be short, lowercase, and stable (e.g., `maxcut`, `qaoa_p2`, `bv_large`).
- Do not rename existing IDs after merge.
- Add new versions with new IDs (e.g., `maxcut_large_v2`) when breaking semantics.
