# ClaimAtlas (Public Results Dataset)

ClaimAtlas is the shared dataset layer for ClaimStab-QC.

Public browsing:
- Website: https://bossy-ye.github.io/ClaimStab-QC/dataset_registry/
- GitHub index: https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/index.json
- GitHub submissions: https://github.com/Bossy-Ye/ClaimStab-QC/tree/main/atlas/submissions

Goal:
- users run their own tasks/methods with ClaimStab,
- publish resulting artifacts,
- grow a public, queryable stability dataset over time.

Each published entry should answer four questions:
1. What claim(s) were evaluated?
2. What perturbation policy was used?
3. What result/decision was obtained?
4. How can others cite and reproduce this submission?

## Structure

```text
atlas/
  index.json                  # global submission index
  submissions/
    <submission_id>/
      metadata.json
      claim_stability.json
      scores.csv              # optional
      rq_summary.json         # optional
      stability_report.html   # optional
```

## Publish Workflow

1. Run any ClaimStab experiment:

```bash
claimstab run --spec paper/experiments/specs/paper_main.yml --out-dir output/paper_main --report
```

2. Publish outputs into ClaimAtlas:

```bash
claimstab publish-result \
  --run-dir output/paper_main \
  --atlas-root atlas \
  --contributor your_name
```

3. Validate index and artifacts:

```bash
claimstab validate-atlas --atlas-root atlas
```

This workflow supports built-in and external tasks (`task.entrypoint`) equally.

## Submission Contract

For every new `atlas/submissions/<id>/` package:
- required: `claim_stability.json`, `metadata.json`
- recommended: `scores.csv`, `rq_summary.json`, `stability_report.html`
- metadata should include:
  - `claim_summaries`
  - `sampling_summary`
  - `reproduce_command`
  - `how_to_cite`

PR checklist template:
- `.github/PULL_REQUEST_TEMPLATE/dataset_submission.md`
