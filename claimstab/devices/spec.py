from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DeviceProfile:
    """
    Optional device target profile.

    Backward compatibility:
    - disabled by default
    - existing experiments remain unchanged unless enabled=True.
    """

    enabled: bool = False
    provider: str = "none"  # none | ibm_fake | iqm_fake | generic
    name: Optional[str] = None
    mode: str = "transpile_only"  # transpile_only | noisy_sim
    basis_gates: Optional[list[str]] = None
    coupling_map: Optional[list[list[int]]] = None
