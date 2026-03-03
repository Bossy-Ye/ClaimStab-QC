from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow, TaskSpecError
from claimstab.tasks.instances import ProblemInstance
from claimstab.tasks.registry import register_task


@dataclass(frozen=True)
class BVInstance:
    hidden_string: str


def _legacy_default_hidden_strings() -> list[str]:
    # Backward-compatible 4-bit defaults used by the old BV plugin version.
    return ["0001", "0011", "0101", "0110", "1001", "1010", "1100", "1111"]


def _generate_hidden_strings_for_n(n_qubits: int, count: int) -> list[str]:
    if n_qubits <= 0:
        raise TaskSpecError("BV task requires n_qubits > 0.")
    if count <= 0:
        return []
    # Deterministic generator: avoids all-zero secret and spreads bit patterns.
    modulus = 1 << n_qubits
    max_unique = modulus - 1
    need = min(count, max_unique)
    out: list[str] = []
    seen: set[int] = set()
    x = 1
    step = 2 * n_qubits + 1
    while len(out) < need:
        x = (x + step) % modulus
        if x == 0:
            x = 1
        if x in seen:
            x = (x * 3 + 1) % modulus
            if x == 0:
                x = 1
            if x in seen:
                continue
        seen.add(x)
        out.append(format(x, f"0{n_qubits}b"))
    return out


class BernsteinVaziraniTaskPlugin:
    """Built-in BV task plugin for decision-claim evaluation."""

    name = "bv"

    def __init__(
        self,
        *,
        n_qubits: int = 4,
        hidden_strings: list[str] | None = None,
        min_qubits: int = 4,
        max_qubits: int = 10,
        instances_per_qubit: int = 4,
    ) -> None:
        if hidden_strings is not None:
            filtered = [str(s).strip() for s in hidden_strings if isinstance(s, str) and s.strip()]
            if not filtered:
                raise TaskSpecError("BV task requires at least one hidden string.")
            for token in filtered:
                if any(ch not in {"0", "1"} for ch in token):
                    raise TaskSpecError(f"Invalid hidden string '{token}'. Expected binary string.")
            self.hidden_strings = filtered
            self.variable_pool = False
            self.legacy_n_qubits = int(n_qubits)
            self.min_qubits = min(len(s) for s in filtered)
            self.max_qubits = max(len(s) for s in filtered)
            self.instances_per_qubit = 1
            return

        if n_qubits > 0 and (min_qubits == max_qubits == n_qubits):
            self.hidden_strings = _legacy_default_hidden_strings()
            self.variable_pool = False
            self.legacy_n_qubits = int(n_qubits)
            self.min_qubits = int(n_qubits)
            self.max_qubits = int(n_qubits)
            self.instances_per_qubit = 1
            return

        if min_qubits <= 0 or max_qubits < min_qubits:
            raise TaskSpecError("BV task requires 0 < min_qubits <= max_qubits.")
        if instances_per_qubit <= 0:
            raise TaskSpecError("BV task requires instances_per_qubit > 0.")
        self.variable_pool = True
        self.legacy_n_qubits = int(n_qubits)
        self.min_qubits = int(min_qubits)
        self.max_qubits = int(max_qubits)
        self.instances_per_qubit = int(instances_per_qubit)
        self.hidden_strings = []

    def instances(self, suite: str) -> list[ProblemInstance]:
        name = suite.strip().lower()
        if self.variable_pool:
            if name in {"core", "toy"}:
                target_total = 20
            elif name in {"standard"}:
                target_total = 24
            elif name in {"large"}:
                target_total = 30
            else:
                target_total = 20
            selected: list[str] = []
            n_values = list(range(self.min_qubits, self.max_qubits + 1))
            if not n_values:
                raise TaskSpecError("BV task has no qubit-length range.")
            per_length = max(1, target_total // len(n_values))
            for n in n_values:
                selected.extend(_generate_hidden_strings_for_n(n, min(self.instances_per_qubit, per_length)))
            # Keep unique while preserving order.
            selected = list(dict.fromkeys(selected))
            # Top up deterministically until target_total.
            idx = 0
            while len(selected) < target_total:
                n = n_values[idx % len(n_values)]
                extra = _generate_hidden_strings_for_n(n, per_length + 2)
                candidate = extra[-1]
                if candidate not in selected:
                    selected.append(candidate)
                else:
                    fallback = _generate_hidden_strings_for_n(n, per_length + 3)[-2]
                    if fallback not in selected:
                        selected.append(fallback)
                idx += 1
            selected = selected[:target_total]
        else:
            if name in {"core", "standard", "toy"}:
                selected = self.hidden_strings[: min(5, len(self.hidden_strings))]
            elif name in {"large"}:
                selected = self.hidden_strings
            else:
                selected = self.hidden_strings[: min(5, len(self.hidden_strings))]

        out: list[ProblemInstance] = []
        for idx, hidden in enumerate(selected):
            out.append(
                ProblemInstance(
                    instance_id=f"bv_{idx}",
                    payload=BVInstance(hidden_string=hidden),
                    meta={"target_label": hidden},
                )
            )
        return out

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        if not isinstance(payload, BVInstance):
            raise TaskSpecError("BV task received unsupported instance payload.")
        hidden = payload.hidden_string

        if method.kind in {"bv", "bernstein_vazirani"}:
            circuit = self._build_bv_oracle(hidden)
        elif method.kind in {"random", "random_baseline"}:
            circuit = self._build_random_baseline(num_qubits=len(hidden))
        else:
            raise TaskSpecError(f"BV task does not support method kind '{method.kind}'.")

        target = hidden

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(counts.values())
            if total <= 0:
                return 0.0
            return float(counts.get(target, 0)) / float(total)

        return BuiltWorkflow(circuit=circuit, metric_fn=metric_fn)

    def _build_bv_oracle(self, hidden: str) -> QuantumCircuit:
        n = len(hidden)
        anc = n
        qc = QuantumCircuit(n + 1, n)
        qc.x(anc)
        qc.h(anc)
        for q in range(n):
            qc.h(q)
        # Qiskit bitstrings are little-endian; reverse hidden string for qubit indexing.
        for q, bit in enumerate(reversed(hidden)):
            if bit == "1":
                qc.cx(q, anc)
        for q in range(n):
            qc.h(q)
        qc.measure(range(n), range(n))
        return qc

    def _build_random_baseline(self, *, num_qubits: int) -> QuantumCircuit:
        n = int(num_qubits)
        qc = QuantumCircuit(n, n)
        for q in range(n):
            qc.h(q)
        qc.measure(range(n), range(n))
        return qc


register_task("bv", BernsteinVaziraniTaskPlugin)
