from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CleanupEntry:
    path: Path
    reason: str


def _path_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        try:
            total += child.stat().st_size
        except OSError:
            continue
    return total


def _format_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(max(0, num_bytes))
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{value:.1f}TB"


def _collect_targets(repo_root: Path) -> list[CleanupEntry]:
    excluded_roots = {"venv", ".venv", ".git"}
    explicit_dirs = [
        (".pytest_cache", "pytest cache"),
        (".mypy_cache", "mypy cache"),
        (".ruff_cache", "ruff cache"),
        (".idea", "local IDE metadata"),
        ("claimstab_qc.egg-info", "local build metadata"),
        ("site", "generated docs site"),
        ("output/profile_perf", "profiling artifacts"),
        ("output/profile_perf_opt", "profiling artifacts"),
        ("output/sample_problem_demo", "local demo output"),
        ("output/sample_problem_demo_run", "local demo output"),
        ("output/examples/community_portfolio_demo", "local demo output"),
        ("output/examples/atlas_bv_demo", "local demo output"),
    ]

    targets: list[CleanupEntry] = []
    for rel, reason in explicit_dirs:
        path = repo_root / rel
        if path.exists():
            targets.append(CleanupEntry(path=path, reason=reason))

    for pycache in repo_root.rglob("__pycache__"):
        if any(part in excluded_roots for part in pycache.parts):
            continue
        targets.append(CleanupEntry(path=pycache, reason="python bytecode cache"))

    for prof in (repo_root / "output").rglob("*.prof"):
        targets.append(CleanupEntry(path=prof, reason="profiling artifact"))

    dedup: dict[str, CleanupEntry] = {}
    for entry in targets:
        dedup[str(entry.path.resolve())] = entry
    return sorted(dedup.values(), key=lambda e: str(e.path))


def _remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
        return
    path.unlink()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Remove local generated artifacts and caches from the repository workspace.")
    ap.add_argument("--root", default=".", help="Repository root (default: current directory).")
    ap.add_argument("--apply", action="store_true", help="Apply deletions. Without this flag, runs in dry-run mode.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.root).resolve()
    targets = _collect_targets(repo_root)

    total_bytes = sum(_path_size_bytes(entry.path) for entry in targets)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] workspace cleanup targets: {len(targets)} entries, { _format_size(total_bytes) }")
    for entry in targets:
        size = _format_size(_path_size_bytes(entry.path))
        rel = entry.path.resolve().relative_to(repo_root)
        print(f" - {rel} ({entry.reason}, {size})")

    if not args.apply:
        print("No files removed. Re-run with --apply to execute cleanup.")
        return

    removed = 0
    for entry in targets:
        _remove_path(entry.path)
        removed += 1
    print(f"Removed {removed} paths.")


if __name__ == "__main__":
    main()
