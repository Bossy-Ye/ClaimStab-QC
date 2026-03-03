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


def collect_runtime_metadata() -> dict[str, Any]:
    deps = {
        "qiskit": _safe_package_version("qiskit"),
        "qiskit-aer": _safe_package_version("qiskit-aer"),
        "qiskit-ibm-runtime": _safe_package_version("qiskit-ibm-runtime"),
        "numpy": _safe_package_version("numpy"),
        "pandas": _safe_package_version("pandas"),
        "matplotlib": _safe_package_version("matplotlib"),
        "pyyaml": _safe_package_version("pyyaml"),
    }

    git_commit = _safe_git(["git", "rev-parse", "HEAD"])
    git_status = _safe_git(["git", "status", "--porcelain"])

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "dependencies": deps,
        "environment_flags": {
            "aer_available": importlib.util.find_spec("qiskit_aer") is not None,
            "ibm_runtime_available": importlib.util.find_spec("qiskit_ibm_runtime") is not None,
        },
        "git_commit": git_commit,
        "git_dirty": bool(git_status),
    }
