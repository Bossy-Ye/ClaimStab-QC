from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from claimstab.tasks.graphs import GraphInstance, core_suite, large_suite, standard_suite
from claimstab.tasks.instances import ProblemInstance


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "suites"


def _load_suite_json(path: Path) -> list[ProblemInstance]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Suite file '{path}' must contain a list.")

    suite: list[ProblemInstance] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError(f"Suite file '{path}' contains a non-object entry.")
        instance_id = str(entry["instance_id"])
        graph_obj = entry.get("graph")
        if not isinstance(graph_obj, dict):
            raise ValueError(f"Suite file '{path}' entry '{instance_id}' missing graph object.")

        graph = GraphInstance(
            graph_id=str(graph_obj.get("graph_id", instance_id)),
            num_nodes=int(graph_obj["num_nodes"]),
            edges=[(int(a), int(b)) for a, b in graph_obj["edges"]],
        )
        suite.append(ProblemInstance(instance_id=instance_id, payload=graph))

    return suite


def load_suite(name: str, *, data_dir: str | Path | None = None) -> list[ProblemInstance]:
    """Load a suite from bundled JSON (if present) or fallback to generated suites."""
    key = name.strip().lower()
    alias = {
        "day1": "core",
        "day2": "standard",
        "day2_large": "large",
    }
    canonical = alias.get(key, key)
    if key in alias:
        print(f"[WARN] Suite alias '{name}' is deprecated; using '{canonical}'.")

    base_dir = Path(data_dir) if data_dir is not None else _default_data_dir()
    candidate = base_dir / f"{canonical}.json"
    if candidate.exists():
        return _load_suite_json(candidate)

    generated: dict[str, Callable[[], list[ProblemInstance]]] = {
        "core": core_suite,
        "standard": standard_suite,
        "large": large_suite,
    }
    if canonical not in generated:
        valid = ", ".join(sorted(generated))
        raise ValueError(f"Unknown suite '{name}'. Use one of: {valid}")
    return generated[canonical]()
