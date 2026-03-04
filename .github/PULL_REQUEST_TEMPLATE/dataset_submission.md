## ClaimAtlas Dataset Submission

Use this template when your PR adds or updates entries under `atlas/`.

### Submission Identity
- Submission id:
- Contributor:
- Task kind:
- Suite:

### Required Contract
- [ ] `claim_stability.json` included
- [ ] `metadata.json` included
- [ ] `atlas/index.json` updated
- [ ] `claimstab validate-atlas --atlas-root atlas` passes

### What Claim(s) Are Evaluated?
- Claim type(s): ranking / decision / distribution
- Claim text (method pairs, top-k, epsilon, delta):

### What Perturbation Setup?
- Space preset(s):
- Sampling mode / sample size / seed:
- Baseline configuration:

### Reproducibility
- Exact run command:
```bash
# paste command
```
- Environment summary (Python + key package versions):

### Citation / Attribution
- How should this submission be cited?
- Related paper/preprint link (if available):

### Checks
- [ ] I regenerated docs registry page: `claimstab export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md`
- [ ] I verified links on `docs/dataset_registry.md`

