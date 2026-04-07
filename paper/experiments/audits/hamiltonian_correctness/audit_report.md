# Hamiltonian Correctness Audit

Reviewer-oriented audit for the algorithm families used in the claim-level validation study.

Scope of this audit:
- `MaxCut` task
- `Max-2-SAT` task
- `VQE/H2` pilot task
- ranking semantics / claim evaluation logic

This audit is intentionally conservative. A family is classified as:
- `primary Hamiltonian-grounded evidence` only if the problem objective, binary encoding, circuit cost construction, and small-instance sanity checks all align cleanly;
- `secondary supporting evidence` if the implementation is mathematically defensible and sanity-checked, but still less canonical or more heuristic than the primary family;
- `proxy pilot` if the implementation is internally coherent but should not be described as a full benchmark for the intended scientific domain.

## External sources used

Official documentation:
- Qiskit Optimization, *Max-Cut and Traveling Salesman Problem*:
  [https://qiskit-community.github.io/qiskit-optimization/tutorials/06_examples_max_cut_and_tsp.html](https://qiskit-community.github.io/qiskit-optimization/tutorials/06_examples_max_cut_and_tsp.html)
- IBM Quantum / Qiskit API, `RZZGate`:
  [https://qiskit.qotlabs.org/docs/api/qiskit/qiskit.circuit.library.RZZGate](https://qiskit.qotlabs.org/docs/api/qiskit/qiskit.circuit.library.RZZGate)
- IBM Quantum / Qiskit API, `CPhaseGate`:
  [https://qiskit.qotlabs.org/docs/api/qiskit/qiskit.circuit.library.CPhaseGate](https://qiskit.qotlabs.org/docs/api/qiskit/qiskit.circuit.library.CPhaseGate)
- Qiskit Nature, *Ground state solvers*:
  [https://qiskit-community.github.io/qiskit-nature/tutorials/03_ground_state_solvers.html](https://qiskit-community.github.io/qiskit-nature/tutorials/03_ground_state_solvers.html)

Canonical papers:
- Farhi, Goldstone, Gutmann, *A Quantum Approximate Optimization Algorithm* (2014):
  [https://arxiv.org/abs/1411.4028](https://arxiv.org/abs/1411.4028)
- Peruzzo et al., *A variational eigenvalue solver on a quantum processor* (2014):
  [https://arxiv.org/abs/1304.3061](https://arxiv.org/abs/1304.3061)

Local code and sanity artifacts:
- `claimstab/tasks/maxcut.py`
- `examples/community/max2sat_pilot_demo/max2sat_task.py`
- `examples/community/vqe_pilot_demo/vqe_h2_task.py`
- `claimstab/claims/ranking.py`
- `claimstab/tasks/tests/test_maxcut_hamiltonian_sanity.py:22-59`
- `claimstab/tests/test_max2sat_clause_sanity.py:27-72`
- `claimstab/tests/test_vqe_proxy_exact_minimum.py:15-30`

## Shared claim semantics

All three families are evaluated through the same ranking-claim semantics:
- higher-is-better claims hold iff `m(A) >= m(B) + delta`
- lower-is-better claims hold iff `m(A) <= m(B) - delta`

Local reference:
- `claimstab/claims/ranking.py:20-69`

Judgment:
- status: theoretically defined and implementation-supported
- evidence type: direct code reference

## Family 1: MaxCut

### Problem and encoding

Objective:
- maximize cut value

Official Max-Cut-to-Ising mapping:
- Qiskit Optimization rewrites Max-Cut using `x_i -> (1 - Z_i)/2` and states that the problem is equivalent to minimizing an Ising Hamiltonian.
- Source: Qiskit Optimization tutorial, lines 210-215

Local implementation:
- `claimstab/tasks/maxcut.py:42-47` loads the graph structure
- `claimstab/tasks/maxcut.py:148-160` computes the expected cut value directly from sampled bitstrings

Judgment:
- status: theoretically proven
- evidence type: official Qiskit documentation + direct code reference

### Cost unitary

Official gate semantics:
- `RZZGate(theta) = exp(-i * theta/2 * Z⊗Z)`
- Source: IBM/Qiskit `RZZGate` docs, lines 11-25

Local implementation:
- `claimstab/tasks/maxcut.py:112-123`
- each edge applies `qc.rzz(2 * gamma, i, j)`

Therefore:
- each edge contributes `exp(-i * gamma * Z_i Z_j)`
- the omitted identity term from `(I - Z_i Z_j)/2` changes only the global phase / energy offset, not the optimizer landscape or ordering of bitstrings

Judgment:
- status: theoretically proven and implementation-supported
- evidence type: official gate documentation + direct code reference

### Small-instance sanity

Added audit test:
- `claimstab/tasks/tests/test_maxcut_hamiltonian_sanity.py:22-59`

What it checks:
- exact brute-force equality `cut(x) = (|E| - sum_ij z_i z_j)/2`
- argmax-cut assignments equal argmin-Ising-energy assignments
- the task circuit uses one `RZZ(2*gamma)` per edge with the expected bound angle

Observed result:
- test suite passed

Judgment:
- status: implementation-supported and brute-force validated
- evidence type: exact brute-force sanity result

### Classification

`MaxCut = primary Hamiltonian-grounded evidence`

Reason:
- standard objective
- standard binary encoding
- standard Ising form
- cost unitary directly matches the intended ZZ interaction
- exact brute-force sanity added locally

Confidence level:
- high

## Family 2: Max-2-SAT

### Problem and encoding

Objective:
- maximize the number of satisfied clauses

Local implementation:
- formulas are stored explicitly in `examples/community/max2sat_pilot_demo/max2sat_task.py:25-93`
- the evaluation metric is expected satisfied-clause count:
  - `examples/community/max2sat_pilot_demo/max2sat_task.py:172-187`

Judgment:
- status: implementation-supported
- evidence type: direct code reference

### Clause-phase semantics

Local implementation:
- clause phase gadget: `examples/community/max2sat_pilot_demo/max2sat_task.py:128-140`
- `cp(gamma)` is the Qiskit `CPhaseGate`

Official gate semantics:
- `CPhaseGate` has matrix `diag(1, 1, 1, e^{i theta})`
- Source: IBM/Qiskit `CPhaseGate` docs, lines 11-24

Derivation:
- the code flips non-negated literals before applying `cp(gamma)`
- this maps the unique unsatisfied assignment of the clause to `|11>`
- therefore the clause unitary is an exact diagonal phase gadget for the unsatisfied-clause projector, up to the sign convention absorbed into `gamma`

Important caveat:
- this establishes exact projector semantics for each clause gadget
- it does **not** by itself establish that the fixed positive `gamma` schedule is a canonical QAOA optimization workflow

Judgment:
- status: mathematically established for the implemented clause projector
- evidence type: official gate documentation + direct code reference + exact derivation

### Small-instance sanity

Added audit test:
- `claimstab/tests/test_max2sat_clause_sanity.py:27-72`

What it checks:
- for all four literal-polarity patterns on a 2-variable clause, the implemented gadget applies phase `e^{i gamma}` iff the clause is unsatisfied
- for every 4-variable pilot instance, exhaustive assignment enumeration verifies that maximizing satisfied clauses is identical to minimizing unsatisfied clauses

Observed result:
- test suite passed

Judgment:
- status: implementation-supported and brute-force validated
- evidence type: exact brute-force sanity result

### Classification

`Max-2-SAT = secondary supporting evidence`

Reason:
- the clause metric is explicit and correct
- the implemented clause-phase gadget is now sanity-checked as an exact unsatisfied-projector phase gadget
- however, the family remains less canonical than MaxCut in this repository because it is a fixed-parameter QAOA-style pilot rather than a standard, fully justified benchmark construction

Confidence level:
- medium

What we do **not** claim:
- we do not claim this family is a fully canonical or officially documented Qiskit Max-2-SAT workflow
- we do not claim the fixed positive `gamma` choices are theoretically optimal

## Family 3: VQE/H2 pilot

### Workflow realism

Expected chemistry-ground-state workflow in Qiskit Nature:
- define a molecular problem via a driver such as `PySCFDriver`
- map it with a qubit mapper such as `JordanWignerMapper`
- solve it with a `GroundStateEigensolver`
- optionally use `VQE(Estimator(), ansatz, optimizer)`
- Source: Qiskit Nature ground-state solver tutorial, lines 326-356 and 412-418

Canonical VQE reference:
- Peruzzo et al. (2014)

Local implementation:
- `examples/community/vqe_pilot_demo/vqe_h2_task.py:68-76`
- the task explicitly says it is a lightweight diagonal energy proxy and not a full multi-term Hamiltonian VQE implementation or a Qiskit Nature ground-state workflow

Judgment:
- status: not chemistry-faithful
- evidence type: official Qiskit Nature documentation + direct code reference

### Implemented Hamiltonian and metric

Local implementation:
- the proxy Hamiltonian is diagonal in the computational basis:
  - `examples/community/vqe_pilot_demo/vqe_h2_task.py:30-35`
  - `examples/community/vqe_pilot_demo/vqe_h2_task.py:147-153`
- metric is `energy_error = max(0, energy - ground_energy)`

Applied patch during this audit:
- `ground_energy` is now computed exactly by enumerating all four Z-basis eigenstates:
  - `examples/community/vqe_pilot_demo/vqe_h2_task.py:47-65`
  - used at `examples/community/vqe_pilot_demo/vqe_h2_task.py:128-129`

This makes the proxy internally exact for its own diagonal Hamiltonian, but it still does not make the task a chemistry-faithful benchmark.

Judgment:
- status: implementation-supported as a diagonal proxy only
- evidence type: direct code reference + exact brute-force sanity result

### Small-instance sanity

Added audit test:
- `claimstab/tests/test_vqe_proxy_exact_minimum.py:15-30`

What it checks:
- the exact proxy ground energy equals brute-force enumeration over the four computational basis states
- at least one basis state achieves zero `energy_error`

Observed result:
- test suite passed

Judgment:
- status: brute-force validated as a diagonal proxy
- evidence type: exact brute-force sanity result

### Classification

`VQE/H2 = proxy pilot only`

Reason:
- the task is not built from a chemistry driver, qubit mapper, estimator-driven VQE loop, or `GroundStateEigensolver`
- it uses a hand-crafted diagonal proxy Hamiltonian
- after the exact-minimum patch it is internally coherent, but it still should not be described as a full VQE or chemistry-ground-state benchmark

Confidence level:
- high for the proxy classification

What we do **not** claim:
- we do not claim this family is a Qiskit Nature-style ground-state workflow
- we do not claim it is a chemistry-faithful benchmark

## Final classification

| Family | Final classification | Why |
|---|---|---|
| MaxCut | primary Hamiltonian-grounded evidence | canonical Ising mapping, standard `RZZ` cost unitary, exact local sanity checks |
| Max-2-SAT | secondary supporting evidence | clause metric is explicit and the clause-phase gadget is now sanity-checked, but the family remains a fixed-parameter QAOA-style pilot |
| VQE/H2 | proxy pilot only | internally exact as a diagonal proxy after patching, but not a chemistry-faithful Qiskit Nature ground-state workflow |

## Conservative paper-facing guidance

Recommended wording:
- MaxCut: primary Hamiltonian-grounded family
- Max-2-SAT: secondary family with exact local clause-projector sanity checks
- VQE/H2: diagonal energy proxy pilot

Avoid these phrasings:
- “all families are equally Hamiltonian-grounded”
- “VQE/H2 is a chemistry-faithful benchmark”
- “Max-2-SAT is a fully canonical benchmark family” without qualification

## Patch status and remaining suggestions

Applied in this audit:
- added exact diagonal minimum for the VQE proxy
- added implementation comments clarifying MaxCut and Max-2-SAT operator semantics
- added three sanity test modules

Remaining suggested follow-ups:
- promote the MaxCut and Max-2-SAT sanity checks into appendix-facing figures or tables
- relabel paper-facing VQE outputs as `VQE/H2 diagonal proxy` wherever the current text suggests a full VQE benchmark
- keep MaxCut as the main Hamiltonian-grounded battleground in the paper narrative
