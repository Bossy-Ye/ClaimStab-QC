# ClaimAtlas Guide

ClaimAtlas is the advanced publication surface for sharing finished ClaimStab runs.

Use it only after you already know how to run your own case:

- [Quickstart](quickstart.md)
- [Design Your Own Case](design_your_own_case.md)

## What It Stores

`publish-result` expects:

- required:
  - `claim_stability.json`
- optional:
  - `scores.csv`
  - `rq_summary.json`
  - `stability_report.html`

If `claim_stability.json` is missing, publish fails.

## Minimal Flow

1. Run a case locally:

```bash
python -m claimstab.cli run \
  --spec examples/community/custom_task_demo/spec_toy.yml \
  --out-dir output/examples/toy_task_demo \
  --report
```

2. Publish it:

```bash
python -m claimstab.cli publish-result \
  --run-dir output/examples/toy_task_demo \
  --atlas-root atlas \
  --contributor your_name
```

3. Validate the registry:

```bash
python -m claimstab.cli validate-atlas --atlas-root atlas
```

4. Refresh the generated registry page if needed:

```bash
python -m claimstab.cli export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md
```

## Useful Links

- [Dataset Registry](dataset_registry.md)
- [GitHub `atlas/index.json`](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/index.json)
- [GitHub `atlas/submissions`](https://github.com/Bossy-Ye/ClaimStab-QC/tree/main/atlas/submissions)
