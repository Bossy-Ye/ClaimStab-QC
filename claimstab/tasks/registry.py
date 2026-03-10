from __future__ import annotations

import importlib
import importlib.util
import hashlib
import sys
from pathlib import Path
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


def _load_module_from_file(module_ref: str) -> Any:
    path = Path(module_ref).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        raise TaskSpecError(
            f"External task file '{module_ref}' does not exist. "
            "Use an importable module path ('module:ClassName') or a valid file path ('path/to/task.py:ClassName')."
        )
    if not path.is_file():
        raise TaskSpecError(f"External task path '{path}' must point to a Python file.")
    if path.suffix.lower() != ".py":
        raise TaskSpecError(f"External task file '{path}' must end with .py")

    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:16]
    module_name = f"_claimstab_external_{digest}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise TaskSpecError(f"Failed to load module spec from file '{path}'.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise TaskSpecError(f"Failed to execute task module file '{path}': {exc}") from exc
    return module


def _load_module(module_ref: str) -> Any:
    is_path_like = module_ref.endswith(".py") or "/" in module_ref or "\\" in module_ref
    if is_path_like:
        return _load_module_from_file(module_ref)
    try:
        return importlib.import_module(module_ref)
    except Exception as exc:
        raise TaskSpecError(
            f"Failed to import task module '{module_ref}': {exc}. "
            "Use an importable module path ('module:ClassName') or a file path ('path/to/task.py:ClassName')."
        ) from exc


def load_external_task(entrypoint: str) -> type[Any]:
    if ":" not in entrypoint:
        raise TaskSpecError("task.entrypoint must be in 'module:ClassName' or 'path/to/task.py:ClassName' format.")

    module_name, class_name = entrypoint.rsplit(":", 1)
    module_name = module_name.strip()
    class_name = class_name.strip()
    if not module_name or not class_name:
        raise TaskSpecError("task.entrypoint must include both module and class name.")

    module = _load_module(module_name)

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
