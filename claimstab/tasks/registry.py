from __future__ import annotations

import importlib
from typing import Any

from claimstab.tasks.base import TaskPlugin, TaskSpecError

_TASK_REGISTRY: dict[str, type[Any]] = {}


def register_task(name: str, cls: type[Any]) -> None:
    key = name.strip().lower()
    if not key:
        raise TaskSpecError("Task registry name must be non-empty.")
    _TASK_REGISTRY[key] = cls


def get_task_class(name: str) -> type[Any]:
    key = name.strip().lower()
    if key not in _TASK_REGISTRY:
        available = ", ".join(sorted(_TASK_REGISTRY)) if _TASK_REGISTRY else "<none>"
        raise TaskSpecError(f"Unknown task kind '{name}'. Registered tasks: {available}")
    return _TASK_REGISTRY[key]


def load_external_task(entrypoint: str) -> type[Any]:
    if ":" not in entrypoint:
        raise TaskSpecError("task.entrypoint must be in 'module:ClassName' format.")

    module_name, class_name = entrypoint.split(":", 1)
    module_name = module_name.strip()
    class_name = class_name.strip()
    if not module_name or not class_name:
        raise TaskSpecError("task.entrypoint must include both module and class name.")

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise TaskSpecError(f"Failed to import task module '{module_name}': {exc}") from exc

    if not hasattr(module, class_name):
        raise TaskSpecError(f"Task class '{class_name}' not found in module '{module_name}'.")

    cls = getattr(module, class_name)
    if not isinstance(cls, type):
        raise TaskSpecError(f"Entrypoint '{entrypoint}' does not reference a class.")
    return cls


def registered_tasks() -> dict[str, type[Any]]:
    return dict(_TASK_REGISTRY)


def ensure_builtin_tasks_registered() -> None:
    # Import modules with registration side-effects.
    importlib.import_module("claimstab.tasks.maxcut")
    importlib.import_module("claimstab.tasks.bernstein_vazirani")
    importlib.import_module("claimstab.tasks.ghz_structural")
    importlib.import_module("claimstab.tasks.grover")
