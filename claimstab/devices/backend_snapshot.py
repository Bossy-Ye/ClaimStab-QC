from __future__ import annotations

import hashlib
import json
from typing import Any


def snapshot_from_backend(backend) -> dict[str, Any]:
    """Extract a minimal backend snapshot for reproducible logging."""
    coupling_edges: list[list[int]] = []
    cmap = getattr(backend, "coupling_map", None)
    if cmap is not None:
        try:
            coupling_edges = [[int(a), int(b)] for a, b in cmap.get_edges()]
        except Exception:
            coupling_edges = []

    operation_names: list[str] = []
    try:
        names = list(getattr(backend, "operation_names"))
        operation_names = sorted(str(n) for n in names)
    except Exception:
        target = getattr(backend, "target", None)
        if target is not None:
            try:
                operation_names = sorted(str(n) for n in target.operation_names)
            except Exception:
                operation_names = []

    properties_summary: dict[str, Any] = {}
    props_obj = None
    props_attr = getattr(backend, "properties", None)
    try:
        props_obj = props_attr() if callable(props_attr) else props_attr
    except Exception:
        props_obj = None
    if props_obj is not None:
        properties_summary = {
            "has_properties": True,
            "last_update_date": str(getattr(props_obj, "last_update_date", None)),
            "qubits_count": len(getattr(props_obj, "qubits", []) or []),
            "gates_count": len(getattr(props_obj, "gates", []) or []),
        }
    else:
        properties_summary = {"has_properties": False}

    backend_name_attr = getattr(backend, "name", None)
    backend_name = backend_name_attr() if callable(backend_name_attr) else backend_name_attr

    return {
        "backend_name": str(backend_name),
        "backend_class": backend.__class__.__name__,
        "num_qubits": int(getattr(backend, "num_qubits", 0)),
        "coupling_map_edges": coupling_edges,
        "coupling_map_edge_count": len(coupling_edges),
        "operation_names": operation_names,
        "properties_summary": properties_summary,
    }


def fingerprint(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
