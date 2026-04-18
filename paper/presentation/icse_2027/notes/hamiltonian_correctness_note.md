# Hamiltonian Correctness Note

This note summarizes how the algorithm families used in the paper should be
treated from a reviewer-risk perspective.

Primary audit source:
- [audit_report.md](../../../experiments/audits/hamiltonian_correctness/audit_report.md)

## Evidence grading

- `MaxCut`
  - primary Hamiltonian-grounded evidence
  - standard objective / Ising equivalence
  - standard `RZZ` cost construction
  - exact local sanity checks now exist

- `Max-2-SAT`
  - secondary supporting evidence
  - clause-phase semantics now sanity-checked
  - still best described as a QAOA-style pilot rather than a canonical benchmark family

- `VQE/H2`
  - proxy pilot only
  - internally exact for its implemented diagonal proxy
  - not a chemistry-faithful Qiskit Nature ground-state workflow

## Safe paper-facing takeaway

The paper should not present all families as equal in Hamiltonian strength.

The safest structure is:
- use MaxCut as the primary Hamiltonian-grounded battleground
- use Max-2-SAT as cross-family supporting evidence
- use VQE/H2 only as a diagonal proxy pilot
