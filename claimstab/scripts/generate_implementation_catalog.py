from __future__ import annotations

import argparse
import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClassInfo:
    name: str
    methods: tuple[str, ...]


@dataclass(frozen=True)
class ModuleInfo:
    path: str
    classes: tuple[ClassInfo, ...]
    funcs: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate deterministic implementation catalog markdown.")
    ap.add_argument(
        "--out",
        default="_archive_legacy/docs/generated/implementation_catalog.md",
        help="Output markdown path.",
    )
    return ap.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _tracked_files(root: Path) -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=root, text=True)
    files = [line.strip() for line in out.splitlines() if line.strip()]
    return sorted(rel for rel in files if (root / rel).exists())


def _module_info(root: Path, rel: str) -> ModuleInfo:
    src = (root / rel).read_text(encoding="utf-8")
    mod = ast.parse(src)
    classes: list[ClassInfo] = []
    funcs: list[str] = []
    for node in mod.body:
        if isinstance(node, ast.ClassDef):
            methods = tuple(
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            classes.append(ClassInfo(name=node.name, methods=methods))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(node.name)
    return ModuleInfo(path=rel, classes=tuple(classes), funcs=tuple(funcs))


def _section_files(tracked: list[str], prefix: str) -> list[str]:
    return [f for f in tracked if f.startswith(prefix)]


def _render_file_list(title: str, files: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    if not files:
        lines.append("- _(none)_")
        lines.append("")
        return lines
    for rel in files:
        lines.append(f"- `{rel}`")
    lines.append("")
    return lines


def _render_module_list(title: str, modules: list[ModuleInfo]) -> list[str]:
    lines = [f"## {title}", ""]
    if not modules:
        lines.append("- _(none)_")
        lines.append("")
        return lines
    for mod in modules:
        lines.append(f"### `{mod.path}`")
        if mod.classes:
            lines.append("- Classes:")
            for cls in mod.classes:
                methods = ", ".join(cls.methods) if cls.methods else "-"
                lines.append(f"  - `{cls.name}` (methods: {methods})")
        else:
            lines.append("- Classes: _none_")
        if mod.funcs:
            lines.append(f"- Top-level functions: {', '.join(mod.funcs)}")
        else:
            lines.append("- Top-level functions: _none_")
        lines.append("")
    return lines


def build_catalog_markdown(root: Path) -> str:
    tracked = _tracked_files(root)

    py_files = [f for f in tracked if f.endswith(".py") and (root / f).exists()]
    md_files = [f for f in tracked if f.endswith(".md")]
    yml_files = [f for f in tracked if f.endswith(".yml") or f.endswith(".yaml")]
    json_files = [f for f in tracked if f.endswith(".json")]

    claimstab_modules = sorted(
        (_module_info(root, f) for f in py_files if f.startswith("claimstab/")),
        key=lambda m: m.path,
    )
    example_modules = sorted(
        (_module_info(root, f) for f in py_files if f.startswith("examples/")),
        key=lambda m: m.path,
    )

    lines: list[str] = []
    lines.append("# Implementation Catalog")
    lines.append("")
    lines.append("This page is auto-generated from tracked repository files.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Tracked files: `{len(tracked)}`")
    lines.append(f"- Python files: `{len(py_files)}`")
    lines.append(f"- Markdown files: `{len(md_files)}`")
    lines.append(f"- YAML files: `{len(yml_files)}`")
    lines.append(f"- JSON files: `{len(json_files)}`")
    lines.append("")
    lines.append("## Core Abstractions")
    lines.append("")
    lines.append("- `Claim` evaluators: ranking/decision/distribution in `claimstab/claims/*`.")
    lines.append("- `Perturbation` space and sampling policies in `claimstab/perturbations/*`.")
    lines.append("- `InferencePolicy` implementations in `claimstab/inference/policies.py`.")
    lines.append("- `TraceRecord` / `TraceIndex` / `ExecutionEvent` for auditability in `claimstab/core/*`.")
    lines.append("- `TaskPlugin` extension contract in `claimstab/tasks/base.py`.")
    lines.append("- `Runner` execution path in `claimstab/runners/*`.")
    lines.append("- `ClaimAtlas` publish/validate/compare flow in `claimstab/atlas/*`.")
    lines.append("")
    lines.append("## CLI Surface")
    lines.append("")
    lines.append(
        "- Subcommands: `init-external-task`, `run`, `report`, `validate-spec`, `examples`, "
        "`export-definitions`, `publish-result`, `validate-atlas`, `export-dataset-registry`, `atlas-compare`."
    )
    lines.append("- Entrypoint: `claimstab` via `project.scripts` in `pyproject.toml`.")
    lines.append("")
    lines.append("## Artifact Contract")
    lines.append("")
    lines.append("- Core run outputs: `scores.csv`, `claim_stability.json`, `rq_summary.json`, `stability_report.html`.")
    lines.append("- Reproducibility artifacts: `trace.jsonl`, `events.jsonl`, `cache.sqlite`.")
    lines.append("- Paper package root: `output/paper_artifact/`.")
    lines.append("- Curated presentation roots: `output/presentation/`, `output/presentation_large/`.")
    lines.append("")
    lines.append("## Extension Points")
    lines.append("")
    lines.append("- Task plugins: implement `TaskPlugin` (`instances`, `build`).")
    lines.append("- Inference policies: implement estimate/decision policy interface.")
    lines.append("- Perturbation operators: implement `PerturbationOperator.apply`.")
    lines.append("- Backends/runners: integrate new execution engine in runner layer.")
    lines.append("")

    root_files = [f for f in tracked if "/" not in f]
    lines.extend(_render_file_list("Root Files", root_files))
    lines.extend(_render_file_list(".github", _section_files(tracked, ".github/")))
    lines.extend(_render_file_list("Atlas Files", _section_files(tracked, "atlas/")))
    lines.extend(_render_file_list("Docs Files", _section_files(tracked, "docs/")))
    lines.extend(_render_file_list("Examples Files", _section_files(tracked, "examples/")))
    lines.extend(_render_file_list("Paper Files", _section_files(tracked, "paper/")))
    lines.extend(_render_file_list("Data Files", _section_files(tracked, "data/")))

    lines.extend(
        _render_module_list(
            "ClaimStab Python Modules",
            claimstab_modules,
        )
    )
    lines.extend(
        _render_module_list(
            "Example Python Modules",
            example_modules,
        )
    )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    root = _repo_root()
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_catalog_markdown(root), encoding="utf-8")
    print(f"Wrote implementation catalog: {out}")


if __name__ == "__main__":
    main()
