from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from claimstab.tests.helpers_characterization import normalize_payload, run_main_smoke, run_multidevice_smoke


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "characterization"


@dataclass(frozen=True)
class DiffResult:
    mode: str
    equal: bool
    diff_paths: tuple[str, ...]

    def summary(self) -> str:
        if self.equal:
            return f"[{self.mode}] PASS"
        preview = ", ".join(self.diff_paths[:8])
        suffix = "" if len(self.diff_paths) <= 8 else f" ... (+{len(self.diff_paths) - 8} more)"
        return f"[{self.mode}] FAIL: {preview}{suffix}"


def _compare_recursive(left: Any, right: Any, path: str, out: list[str]) -> None:
    if type(left) is not type(right):
        out.append(path)
        return
    if isinstance(left, dict):
        left_keys = set(left.keys())
        right_keys = set(right.keys())
        for key in sorted(left_keys - right_keys):
            out.append(f"{path}.{key} (missing-right)")
        for key in sorted(right_keys - left_keys):
            out.append(f"{path}.{key} (missing-left)")
        for key in sorted(left_keys & right_keys):
            _compare_recursive(left[key], right[key], f"{path}.{key}", out)
        return
    if isinstance(left, list):
        if len(left) != len(right):
            out.append(f"{path} (len {len(left)} != {len(right)})")
            return
        for idx, (left_item, right_item) in enumerate(zip(left, right)):
            _compare_recursive(left_item, right_item, f"{path}[{idx}]", out)
        return
    if left != right:
        out.append(path)


def compare_normalized_artifacts(left_json: dict[str, Any], right_json: dict[str, Any], mode: str) -> DiffResult:
    diffs: list[str] = []
    _compare_recursive(left_json, right_json, path="$", out=diffs)
    return DiffResult(mode=mode, equal=not diffs, diff_paths=tuple(diffs))


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _run_case(*, case: str, repo_root: Path) -> DiffResult:
    if case == "main_maxcut":
        payload = run_main_smoke(repo_root=repo_root, task="maxcut")
        normalized = normalize_payload(payload, kind="main")
        expected = _load_fixture("main_maxcut_randomk.json")
        return compare_normalized_artifacts(normalized, expected, mode=case)

    if case == "main_bv":
        payload = run_main_smoke(
            repo_root=repo_root,
            task="bv",
            extra_args=[
                "--sampling-mode",
                "adaptive_ci",
                "--target-ci-width",
                "0.10",
                "--max-sample-size",
                "16",
                "--min-sample-size",
                "4",
                "--step-size",
                "4",
            ],
        )
        normalized = normalize_payload(payload, kind="main")
        expected = _load_fixture("main_bv_adaptive.json")
        return compare_normalized_artifacts(normalized, expected, mode=case)

    if case == "multidevice":
        if importlib.util.find_spec("qiskit_ibm_runtime") is None:
            return DiffResult(mode=case, equal=True, diff_paths=("SKIP: qiskit_ibm_runtime unavailable",))
        payload = run_multidevice_smoke(repo_root=repo_root)
        normalized = normalize_payload(payload, kind="multidevice")
        expected = _load_fixture("multidevice_transpile_only.json")
        return compare_normalized_artifacts(normalized, expected, mode=case)

    raise ValueError(f"Unsupported case: {case}")


def _iter_cases(mode: str) -> Iterable[str]:
    if mode == "all":
        return ("main_maxcut", "main_bv", "multidevice")
    return (mode,)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Check refactor artifact compatibility against characterization fixtures")
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--mode", choices=["all", "main_maxcut", "main_bv", "multidevice"], default="all")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    failures: list[DiffResult] = []

    for case in _iter_cases(args.mode):
        result = _run_case(case=case, repo_root=repo_root)
        print(result.summary())
        if not result.equal:
            failures.append(result)

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
