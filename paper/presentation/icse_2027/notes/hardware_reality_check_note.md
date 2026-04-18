## Minimal Hardware Reality Check

This note summarizes the smallest completed real-backend run currently available
for ClaimStab-QC. It is appendix-facing evidence, not a main-paper result.

### Run surface

- task: `BV`
- methods: `BVOracle` only
- claims:
  - `BVOracle top_k=1`
  - `BVOracle top_k=3`
- perturbation preset: `compilation_only_exact`
- sampling policy: `full_factorial`
- backend: `ibm_marrakesh`
- provider: `ibm_runtime`
- shots: `1024`
- run package:
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/output/paper/evaluation_v4/runs/D1_bv_oracle_only_ibm_real`

### Measured result

- both decision claims completed successfully on a real IBM backend
- both claims were `stable` at the aggregate level
- for both claims:
  - `n_claim_evals = 135`
  - `stability_hat = 1.0`
  - `stability_ci_low = 0.9723`
  - `stability_ci_high = 1.0`

Measured runtime from the artifact payload:

- `rows_processed = 135`
- `total_wall_time = 1059.7s`
- `execute_time_ms_mean = 7784.4`

Measured circuit/runtime characteristics from `scores.csv`:

- score:
  - min `0.5459`
  - median `0.9121`
  - max `0.9551`
- transpiled depth:
  - min `7`
  - median `21`
  - max `39`
- two-qubit gates:
  - min `1`
  - median `10`
  - max `17`

### Interpretation

This run supports a narrow claim only:

- the ClaimStab-QC execution path works end-to-end on a real IBM backend for the
  frozen minimal `BV` slice
- under the declared `compilation_only_exact` scope, both `BVOracle` decision
  claims remained preserved at the aggregate level

This run does **not** support broader claims such as:

- broad hardware generalization
- backend-family robustness
- IQM/VTT readiness by itself
- a benchmark-style comparison across real devices

### Important boundary

This run should be treated as a minimal reality check, not as completion of the
target IQM/VTT hardware task.

- the declared target hardware family for `07` remains `IQM / VTT Q50`
- this IBM run is supporting evidence that the same small slice can survive a
  real-backend path
- it does not replace the intended IQM/VTT slice

### Why BV is theoretically deterministic but the measured score is not 1.0

The `BVOracle` circuit is deterministic in the ideal noiseless model: after the
oracle and final Hadamards, the correct hidden string should be measured with
probability `1`.

However, ClaimStab-QC records the observed hardware score as the empirical
success probability of the target label:

- task implementation:
  - `/Users/mac/Documents/GitHub/ClaimStab-QC/claimstab/tasks/bernstein_vazirani.py`
- the metric is:
  - `counts[target_label] / total_shots`

So on real hardware, the score drops below `1.0` whenever noise redistributes
some probability mass away from the ideal hidden string. This can happen due to:

- two-qubit gate infidelity
- readout error
- calibration drift
- transpilation-induced circuit differences across layouts / optimization levels

The decision claims used here are therefore weaker than “perfect deterministic
output”:

- `top_k=1` asks whether the target label is still the top-ranked observed label
- `top_k=3` asks whether the target label remains within the top 3 observed labels

In this run, the measured success probability varied across configurations and
instances, but the target label still remained in the required top-k set across
all evaluated configurations. That is why the aggregate decision verdict is
`stable` even though the raw metric values are below `1.0`.

### Provenance warning

The recorded payload reports:

- `git_commit = d04faa7`
- `git_dirty = true`

This means the run happened from a dirty worktree. For paper citation, either:

- cite it explicitly as an exploratory real-backend check, or
- rerun the same frozen spec from a clean commit before treating it as canonical
  artifact evidence
