# Structural Benchmark (GHZ)

This track provides a circuit-level compilation benchmark that is independent of MaxCut and Bernstein-Vazirani.

## Benchmark Design

- **Task**: `ghz`
- **Methods**:
  - `GHZ_Linear` (nearest-neighbor CNOT chain)
  - `GHZ_Star` (star CNOT fanout from qubit 0)
- **Claim type**: ranking
- **Primary metrics**:
  - `circuit_depth` (`lower_is_better`)
  - `two_qubit_count` (`lower_is_better`)

Rationale: on line-like coupling maps, star fanout generally induces more routing overhead than linear chain, making structural claims meaningful under transpilation perturbations.

## Run Command

```bash
PYTHONPATH=. ./venv/bin/python examples/exp_structural_compilation.py --out-dir output/exp_structural_compilation
```

## Spec

`specs/paper_structural.yml`

## Expected Artifacts

- `output/exp_structural_compilation/claim_stability.json`
- `output/exp_structural_compilation/scores.csv`
- `output/exp_structural_compilation/rq_summary.json`
- `output/exp_structural_compilation/stability_report.html` (if report generation is invoked)

