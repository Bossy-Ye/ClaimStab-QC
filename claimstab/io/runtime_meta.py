from __future__ import annotations

import importlib.util
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any


def _safe_package_version(pkg: str) -> str | None:
    try:
        return version(pkg)
    except PackageNotFoundError:
        return None
    except Exception:
        return None


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
            "numpy": _safe_package_version("numpy"),
            "pandas": _safe_package_version("pandas"),
            "matplotlib": _safe_package_version("matplotlib"),
            "pyyaml": _safe_package_version("pyyaml"),
        }

    env_flags: dict[str, bool | None]
    if include_environment_flags:
        env_flags = {
            "aer_available": importlib.util.find_spec("qiskit_aer") is not None,
            "ibm_runtime_available": importlib.util.find_spec("qiskit_ibm_runtime") is not None,
        }
    else:
        env_flags = {"aer_available": None, "ibm_runtime_available": None}

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
