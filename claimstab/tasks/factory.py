from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import TaskPlugin, TaskSpecError
from claimstab.tasks.registry import ensure_builtin_tasks_registered, get_task_class, load_external_task


@dataclass(frozen=True)
class TaskConfig:
    kind: str
    suite: str
    params: dict[str, Any]
    entrypoint: str | None = None


def _default_methods(task_kind: str = "maxcut") -> list[MethodSpec]:
    task_key = task_kind.strip().lower()
    if task_key == "bv":
        return [
            MethodSpec(name="BVOracle", kind="bv"),
            MethodSpec(name="RandomBaseline", kind="random_baseline"),
        ]
    if task_key == "grover":
        return [
            MethodSpec(name="GroverOracle", kind="grover"),
            MethodSpec(name="UniformBaseline", kind="uniform"),
        ]
    if task_key == "ghz":
        return [
            MethodSpec(name="GHZ_Linear", kind="ghz_linear"),
            MethodSpec(name="GHZ_Star", kind="ghz_star"),
            MethodSpec(name="RandomBaseline", kind="random_baseline"),
        ]
    return [
        MethodSpec(name="QAOA_p1", kind="qaoa", params={"p": 1}),
        MethodSpec(name="QAOA_p2", kind="qaoa", params={"p": 2}),
        MethodSpec(name="RandomBaseline", kind="random_baseline"),
    ]


def parse_task_config(raw_task: dict[str, Any] | None, *, default_suite: str = "core") -> TaskConfig:
    if not raw_task:
        return TaskConfig(kind="maxcut", suite=default_suite, params={})
    if not isinstance(raw_task, dict):
        raise TaskSpecError("task must be a mapping/object in spec.")

    kind = str(raw_task.get("kind", "maxcut")).strip()
    if not kind:
        raise TaskSpecError("task.kind must be non-empty.")
    suite = str(raw_task.get("suite", default_suite)).strip() or default_suite
    params = raw_task.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise TaskSpecError("task.params must be an object.")
    entrypoint = raw_task.get("entrypoint")
    if entrypoint is not None:
        entrypoint = str(entrypoint)

    return TaskConfig(kind=kind, suite=suite, params=dict(params), entrypoint=entrypoint)


def make_task(raw_task: dict[str, Any] | None, *, default_suite: str = "core") -> tuple[TaskPlugin, str]:
    ensure_builtin_tasks_registered()
    cfg = parse_task_config(raw_task, default_suite=default_suite)

    if cfg.kind.lower() == "external":
        if not cfg.entrypoint:
            raise TaskSpecError("task.kind=external requires task.entrypoint='module:Class' or 'path/to/task.py:Class'.")
        cls = load_external_task(cfg.entrypoint)
    else:
        cls = get_task_class(cfg.kind)

    try:
        task = cls(**cfg.params)
    except TypeError:
        # Fallback for plugins expecting a single params object.
        try:
            task = cls(cfg.params)
        except Exception as exc:
            raise TaskSpecError(f"Failed to initialize task '{cfg.kind}': {exc}") from exc
    except Exception as exc:
        raise TaskSpecError(f"Failed to initialize task '{cfg.kind}': {exc}") from exc

    if not hasattr(task, "instances") or not callable(getattr(task, "instances")):
        raise TaskSpecError("Task plugin must implement instances(suite) -> list[ProblemInstance].")
    if not hasattr(task, "build") or not callable(getattr(task, "build")):
        raise TaskSpecError("Task plugin must implement build(instance, method).")

    return task, cfg.suite


def parse_methods(raw_spec: dict[str, Any], *, task_kind: str = "maxcut") -> list[MethodSpec]:
    raw_methods = raw_spec.get("methods")
    if raw_methods is None:
        return _default_methods(task_kind=task_kind)
    if not isinstance(raw_methods, list) or not raw_methods:
        raise TaskSpecError("methods must be a non-empty list when provided.")

    methods: list[MethodSpec] = []
    for idx, raw in enumerate(raw_methods):
        if not isinstance(raw, dict):
            raise TaskSpecError(f"methods[{idx}] must be an object.")
        name = raw.get("name")
        kind = raw.get("kind")
        if not isinstance(name, str) or not name.strip():
            raise TaskSpecError(f"methods[{idx}].name must be a non-empty string.")
        if not isinstance(kind, str) or not kind.strip():
            raise TaskSpecError(f"methods[{idx}].kind must be a non-empty string.")
        params = raw.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise TaskSpecError(f"methods[{idx}].params must be an object.")
        legacy_p = raw.get("p")
        methods.append(MethodSpec(name=name.strip(), kind=kind.strip(), params=dict(params), p=legacy_p))

    names = [m.name for m in methods]
    if len(names) != len(set(names)):
        raise TaskSpecError("Method names must be unique.")
    return methods
