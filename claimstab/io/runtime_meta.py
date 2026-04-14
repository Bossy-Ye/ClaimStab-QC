from __future__ import annotations

import functools
import importlib.util
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any


@functools.cache
def _safe_package_version(pkg: str) -> str | None:
    try:
        return version(pkg)
    except PackageNotFoundError:
        return None
    except Exception:
        return None


@functools.cache
def _safe_find_spec(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False
    except Exception:
        return False


def _safe_git(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None


def collect_runtime_metadata(
    *,
    include_dependencies: bool = True,
    include_environment_flags: bool = True,
    include_git: bool = True,
) -> dict[str, Any]:
    deps: dict[str, str | None] = {}
    if include_dependencies:
        deps = {
            "qiskit": _safe_package_version("qiskit"),
            "qiskit-aer": _safe_package_version("qiskit-aer"),
            "qiskit-ibm-runtime": _safe_package_version("qiskit-ibm-runtime"),
            "iqm-client": _safe_package_version("iqm-client"),
            "numpy": _safe_package_version("numpy"),
            "pandas": _safe_package_version("pandas"),
            "matplotlib": _safe_package_version("matplotlib"),
            "pyyaml": _safe_package_version("pyyaml"),
        }

    env_flags: dict[str, bool | None]
    if include_environment_flags:
        env_flags = {
            "aer_available": _safe_find_spec("qiskit_aer"),
            "ibm_runtime_available": _safe_find_spec("qiskit_ibm_runtime"),
            "iqm_qiskit_available": _safe_find_spec("iqm.qiskit_iqm"),
        }
    else:
        env_flags = {"aer_available": None, "ibm_runtime_available": None, "iqm_qiskit_available": None}

    git_commit: str | None = None
    git_dirty: bool | None = None
    if include_git:
        git_commit = _safe_git(["git", "rev-parse", "HEAD"])
        git_status = _safe_git(["git", "status", "--porcelain"])
        git_dirty = bool(git_status)

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "dependencies": deps,
        "environment_flags": env_flags,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
    }
