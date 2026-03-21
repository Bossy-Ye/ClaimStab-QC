from __future__ import annotations

import math
from dataclasses import dataclass

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow, TaskSpecError
from claimstab.tasks.instances import ProblemInstance


@dataclass(frozen=True)
class RepetitionPayload:
    distance: int
    physical_error_rate: float
    logical_value: int


def _flip_rotation_angle(physical_error_rate: float) -> float:
    return 2.0 * math.asin(math.sqrt(physical_error_rate))


def _decode_majority(bits: list[int]) -> int:
    threshold = (len(bits) // 2) + 1
    return 1 if sum(bits) >= threshold else 0


def _decode_window(bits: list[int], *, window_size: int) -> int:
    if window_size <= 0 or window_size > len(bits) or window_size % 2 == 0:
        raise TaskSpecError("window_size must be a positive odd integer no larger than the code distance.")
    start = (len(bits) - window_size) // 2
    return _decode_majority(bits[start : start + window_size])


class RepetitionCodeDecoderTask:
    """External QEC-style supporting case based on a small repetition code.

    The circuit encodes a logical 0/1 into a repetition block, injects a fixed
    synthetic bit-flip rate via RX rotations, and measures all code qubits.
    Methods differ only in the decoder used to turn the measured codeword into a
    logical prediction. The reported scalar is a logical-error-rate-style metric:
    lower is better.
    """

    name = "qec_decoder_pilot"

    def __init__(
        self,
        distance: int = 5,
        physical_error_rate: float = 0.15,
        num_instances: int = 8,
        decoder_window: int = 3,
    ) -> None:
        self.distance = int(distance)
        self.physical_error_rate = float(physical_error_rate)
        self.num_instances = int(num_instances)
        self.decoder_window = int(decoder_window)

        if self.distance < 3 or self.distance % 2 == 0:
            raise TaskSpecError("distance must be an odd integer >= 3 for the repetition-code pilot.")
        if not (0.0 <= self.physical_error_rate < 0.5):
            raise TaskSpecError("physical_error_rate must satisfy 0.0 <= p < 0.5.")
        if self.num_instances <= 0:
            raise TaskSpecError("num_instances must be >= 1.")
        if self.decoder_window <= 0 or self.decoder_window > self.distance or self.decoder_window % 2 == 0:
            raise TaskSpecError("decoder_window must be a positive odd integer no larger than distance.")

    def instances(self, suite: str) -> list[ProblemInstance]:
        count = self.num_instances
        suite_name = str(suite).strip().lower()
        if suite_name == "large":
            count = max(count, 12)
        out: list[ProblemInstance] = []
        for idx in range(count):
            logical_value = idx % 2
            payload = RepetitionPayload(
                distance=self.distance,
                physical_error_rate=self.physical_error_rate,
                logical_value=logical_value,
            )
            out.append(
                ProblemInstance(
                    instance_id=f"qec_decoder_{suite}_{idx}",
                    payload=payload,
                    meta={
                        "instance_type": "qec_decoder_pilot",
                        "distance": self.distance,
                        "physical_error_rate": self.physical_error_rate,
                        "logical_value": logical_value,
                    },
                )
            )
        return out

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        if not isinstance(payload, RepetitionPayload):
            raise TaskSpecError("RepetitionCodeDecoderTask got unsupported payload.")

        n = payload.distance
        qc = QuantumCircuit(n)
        if payload.logical_value == 1:
            qc.x(range(n))
        qc.rx(_flip_rotation_angle(payload.physical_error_rate), range(n))
        qc.measure_all()

        window_size = int(method.params.get("window_size", self.decoder_window))

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(counts.values())
            if total == 0:
                return 1.0

            logical_error_rate = 0.0
            for bitstring, shot_count in counts.items():
                bits = [int(bit) for bit in bitstring[::-1]]
                if method.kind == "global_majority":
                    decoded = _decode_majority(bits)
                elif method.kind == "window_majority":
                    decoded = _decode_window(bits, window_size=window_size)
                elif method.kind == "single_readout":
                    decoded = bits[n // 2]
                else:
                    raise TaskSpecError(f"Unsupported decoder kind: {method.kind}")

                if decoded != payload.logical_value:
                    logical_error_rate += shot_count / total
            return logical_error_rate

        return BuiltWorkflow(circuit=qc, metric_fn=metric_fn)

    def build_with_config(self, instance: ProblemInstance, method: MethodSpec, _config) -> BuiltWorkflow:
        return self.build(instance, method)
