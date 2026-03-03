# Ecosystem Hub

ClaimStab's `ecosystem/` directory is the contribution layer for reusable research assets.

## What can be contributed

- Tasks (`ecosystem/tasks/<task_id>/task.yaml`)
- Methods (`ecosystem/methods/<method_id>/method.yaml`)
- Suites (`ecosystem/suites/<suite_id>/suite.yaml`)
- Result packages (`ecosystem/results/<result_id>/result.yaml`)

## Why this exists

- Keep contributions standardized and machine-verifiable.
- Make external tasks/methods discoverable and reproducible.
- Allow artifact reuse across papers and benchmarks.

## Validate before PR

```bash
claimstab validate-ecosystem --root ecosystem
```

Validation includes:
- Schema checks for all metadata files.
- ID uniqueness.
- Cross-reference checks (`task_id`, `suite_id`).
- Artifact path existence warnings for result packages.

## Recommended PR checklist

1. Copy a template from `ecosystem/templates/`.
2. Add metadata file under the correct collection path.
3. Include a runnable command in `result.yaml` if contributing results.
4. Run `claimstab validate-ecosystem --root ecosystem`.
5. Add/adjust docs if introducing a new task family.
