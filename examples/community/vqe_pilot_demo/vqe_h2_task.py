from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow, TaskSpecError
from claimstab.tasks.instances import ProblemInstance


@dataclass(frozen=True)
class VQEH2Payload:
    bond_length: float
    z_hamiltonian: dict[str, float]
    theta_hea: float
    theta_uccsd: float


def _instance_library() -> list[VQEH2Payload]:
    payloads: list[VQEH2Payload] = []
    for bond_length, theta_hea, theta_uccsd in [
        (0.55, 0.56, 0.92),
        (0.75, 0.62, 0.98),
        (0.95, 0.68, 1.04),
        (1.15, 0.72, 1.10),
        (1.35, 0.76, 1.16),
        (1.55, 0.80, 1.20),
    ]:
        z_hamiltonian = {
            "c0": -0.85 - 0.05 * bond_length,
            "z0": 0.18 + 0.03 * (bond_length - 1.0),
            "z1": 0.14 - 0.02 * (bond_length - 1.0),
            "zz": 0.56 + 0.03 * abs(bond_length - 1.1),
        }
        payloads.append(
            VQEH2Payload(
                bond_length=bond_length,
                z_hamiltonian=z_hamiltonian,
                theta_hea=theta_hea,
                theta_uccsd=theta_uccsd,
            )
        )
    return payloads


class VQEH2PilotTask:
    """Lightweight VQE-style H2 pilot with a diagonal energy proxy.

    This pilot stays within the current ClaimStab task contract by using a
    single measurement circuit per (instance, method) and computing an energy
    error metric from observed bitstring frequencies. It is a chemistry-flavored
    supporting case, not a full multi-term Hamiltonian VQE implementation.
    """

    name = "vqe_h2_pilot"

    def __init__(self, num_instances: int = 6) -> None:
        self.num_instances = int(num_instances)
        if self.num_instances <= 0:
            raise TaskSpecError("num_instances must be >= 1")

    def instances(self, suite: str) -> list[ProblemInstance]:
        library = _instance_library()
        if str(suite).strip().lower() == "large":
            count = min(len(library), max(self.num_instances, 6))
        else:
            count = min(len(library), self.num_instances)

        out: list[ProblemInstance] = []
        for idx, payload in enumerate(library[:count]):
            out.append(
                ProblemInstance(
                    instance_id=f"vqe_h2_{suite}_{idx}",
                    payload=payload,
                    meta={
                        "instance_type": "vqe_h2_pilot",
                        "bond_length": payload.bond_length,
                    },
                )
            )
        return out

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        if not isinstance(payload, VQEH2Payload):
            raise TaskSpecError("VQEH2PilotTask got unsupported payload.")

        qc = QuantumCircuit(2)

        if method.kind == "vqe_hf":
            qc.x(0)
        elif method.kind == "vqe_hea":
            qc.x(0)
            qc.ry(payload.theta_hea, 1)
        elif method.kind == "vqe_uccsd":
            qc.x(0)
            qc.ry(payload.theta_uccsd, 1)
            qc.cx(1, 0)
            qc.ry(-0.18 * payload.theta_uccsd, 1)
            qc.cx(1, 0)
        else:
            raise TaskSpecError(f"Unsupported VQE method kind: {method.kind}")

        qc.measure_all()
        coeffs = payload.z_hamiltonian
        ground_energy = (
            coeffs["c0"]
            - abs(coeffs["z0"])
            - abs(coeffs["z1"])
            - abs(coeffs["zz"])
        )

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(counts.values())
            if total <= 0:
                return 1.0

            exp_z0 = 0.0
            exp_z1 = 0.0
            exp_zz = 0.0
            for bitstring, shot_count in counts.items():
                bits = [int(bit) for bit in bitstring[::-1]]
                z0 = 1.0 if bits[0] == 0 else -1.0
                z1 = 1.0 if bits[1] == 0 else -1.0
                weight = shot_count / total
                exp_z0 += weight * z0
                exp_z1 += weight * z1
                exp_zz += weight * z0 * z1
            energy = (
                coeffs["c0"]
                + coeffs["z0"] * exp_z0
                + coeffs["z1"] * exp_z1
                + coeffs["zz"] * exp_zz
            )
            return max(0.0, energy - ground_energy)

        return BuiltWorkflow(circuit=qc, metric_fn=metric_fn)

    def build_with_config(self, instance: ProblemInstance, method: MethodSpec, _config) -> BuiltWorkflow:
        return self.build(instance, method)
