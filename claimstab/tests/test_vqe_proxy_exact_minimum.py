from __future__ import annotations

import itertools
import unittest

from examples.community.vqe_pilot_demo.vqe_h2_task import _exact_diagonal_ground_energy, _instance_library


def _basis_energy(coeffs: dict[str, float], bit0: int, bit1: int) -> float:
    z0 = 1.0 if bit0 == 0 else -1.0
    z1 = 1.0 if bit1 == 0 else -1.0
    return coeffs["c0"] + coeffs["z0"] * z0 + coeffs["z1"] * z1 + coeffs["zz"] * z0 * z1


class TestVQEProxyExactMinimum(unittest.TestCase):
    def test_exact_diagonal_ground_energy_matches_bruteforce_basis_enumeration(self) -> None:
        for payload in _instance_library():
            coeffs = payload.z_hamiltonian
            brute_force = min(_basis_energy(coeffs, bit0, bit1) for bit0, bit1 in itertools.product((0, 1), repeat=2))
            self.assertAlmostEqual(_exact_diagonal_ground_energy(coeffs), brute_force, places=12)

    def test_energy_error_is_zero_on_at_least_one_ground_basis_state(self) -> None:
        for payload in _instance_library():
            coeffs = payload.z_hamiltonian
            ground = _exact_diagonal_ground_energy(coeffs)
            errors = []
            for bit0, bit1 in itertools.product((0, 1), repeat=2):
                energy = _basis_energy(coeffs, bit0, bit1)
                errors.append(max(0.0, energy - ground))
            self.assertAlmostEqual(min(errors), 0.0, places=12)


if __name__ == "__main__":
    unittest.main()
