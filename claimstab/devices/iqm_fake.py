from __future__ import annotations

import importlib


def _fake_backends_module():
    try:
        return importlib.import_module("iqm.qiskit_iqm.fake_backends")
    except Exception as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "IQM fake backend support requires iqm-client with Qiskit support. "
            "Install with: pip install 'claimstab-qc[iqm]'"
        ) from exc


def load_fake_backend(class_or_backend_name: str):
    """
    Load an IQM fake backend by class name or backend name.

    Supported class names follow the iqm-client exports, e.g.:
    - IQMFakeAphrodite
    - IQMFakeApollo
    - IQMFakeDeneb
    """
    mod = _fake_backends_module()

    if hasattr(mod, class_or_backend_name):
        cls = getattr(mod, class_or_backend_name)
        try:
            return cls()
        except TypeError:
            pass

    normalized = str(class_or_backend_name).strip().lower()
    for attr in dir(mod):
        if not attr.startswith("IQMFake") or attr == "IQMFakeBackend":
            continue
        cls = getattr(mod, attr)
        try:
            backend = cls()
        except Exception:
            continue
        backend_name = str(getattr(backend, "name", "")).strip().lower()
        if normalized in {attr.lower(), backend_name}:
            return backend

    raise ValueError(
        f"Could not resolve IQM fake backend '{class_or_backend_name}'. "
        "Use a supported fake backend class name such as IQMFakeAphrodite, "
        "IQMFakeApollo, IQMFakeAdonis, or IQMFakeDeneb."
    )
