from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .backend_snapshot import fingerprint, snapshot_from_backend
from .ibm_fake import load_fake_backend as load_ibm_fake_backend
from .iqm_fake import load_fake_backend as load_iqm_fake_backend
from .spec import DeviceProfile


@dataclass(frozen=True)
class ResolvedDeviceProfile:
    profile: DeviceProfile
    backend: Any | None
    snapshot: dict[str, Any] | None
    snapshot_fingerprint: str | None


def parse_device_profile(raw: Mapping[str, Any] | None) -> DeviceProfile:
    if not raw:
        return DeviceProfile(enabled=False, provider="none", mode="transpile_only")

    enabled = bool(raw.get("enabled", False))
    provider = str(raw.get("provider", "none"))
    name = raw.get("name")
    mode = str(raw.get("mode", "transpile_only"))
    basis_gates = raw.get("basis_gates")
    coupling_map = raw.get("coupling_map")

    if provider not in {"none", "ibm_fake", "iqm_fake", "generic"}:
        raise ValueError(
            f"Unsupported device provider '{provider}'. Use one of: none, ibm_fake, iqm_fake, generic."
        )
    if mode not in {"transpile_only", "noisy_sim"}:
        raise ValueError(f"Unsupported device mode '{mode}'. Use one of: transpile_only, noisy_sim.")

    parsed_basis = list(basis_gates) if basis_gates is not None else None
    parsed_cmap = [list(edge) for edge in coupling_map] if coupling_map is not None else None
    return DeviceProfile(
        enabled=enabled,
        provider=provider,
        name=str(name) if name is not None else None,
        mode=mode,
        basis_gates=parsed_basis,
        coupling_map=parsed_cmap,
    )


def parse_noise_model_mode(raw_backend: Mapping[str, Any] | None) -> str:
    if not raw_backend:
        return "none"
    value = str(raw_backend.get("noise_model", "none"))
    if value not in {"none", "from_device_profile"}:
        raise ValueError(f"Unsupported backend.noise_model '{value}'. Use one of: none, from_device_profile.")
    return value


def resolve_device_profile(profile: DeviceProfile) -> ResolvedDeviceProfile:
    if not profile.enabled or profile.provider == "none":
        return ResolvedDeviceProfile(
            profile=profile,
            backend=None,
            snapshot=None,
            snapshot_fingerprint=None,
        )

    if profile.provider == "ibm_fake":
        if not profile.name:
            raise ValueError("device_profile.name is required when provider=ibm_fake.")
        backend = load_ibm_fake_backend(profile.name)
        snap = snapshot_from_backend(backend)
        fp = fingerprint(snap)
        return ResolvedDeviceProfile(
            profile=profile,
            backend=backend,
            snapshot=snap,
            snapshot_fingerprint=fp,
        )

    if profile.provider == "iqm_fake":
        if not profile.name:
            raise ValueError("device_profile.name is required when provider=iqm_fake.")
        backend = load_iqm_fake_backend(profile.name)
        snap = snapshot_from_backend(backend)
        fp = fingerprint(snap)
        return ResolvedDeviceProfile(
            profile=profile,
            backend=backend,
            snapshot=snap,
            snapshot_fingerprint=fp,
        )

    if profile.provider == "generic":
        snap = {
            "backend_name": profile.name or "generic_profile",
            "backend_class": "generic",
            "num_qubits": None,
            "coupling_map_edges": profile.coupling_map or [],
            "operation_names": profile.basis_gates or [],
            "properties_summary": {"has_properties": False},
        }
        fp = fingerprint(snap)
        return ResolvedDeviceProfile(
            profile=profile,
            backend=None,
            snapshot=snap,
            snapshot_fingerprint=fp,
        )

    raise ValueError(f"Unsupported device provider '{profile.provider}'.")
