from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _infer_two_methods(df: pd.DataFrame) -> Tuple[str, str]:
    methods = sorted(df["method"].dropna().unique().tolist())
    if len(methods) < 2:
        raise ValueError(f"Need >=2 methods in CSV, got: {methods}")
    return methods[0], methods[1]


def _build_diff_matrix(
    df: pd.DataFrame,
    method_a: str,
    method_b: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    df = df.copy()
    df["seed_transpiler"] = df["seed_transpiler"].astype(int)
    df["optimization_level"] = df["optimization_level"].astype(int)
    df["score"] = df["score"].astype(float)

    seeds = np.array(sorted(df["seed_transpiler"].unique().tolist()), dtype=int)
    opts = np.array(sorted(df["optimization_level"].unique().tolist()), dtype=int)

    def pivot(m: str) -> pd.DataFrame:
        sub = df[df["method"] == m]
        if sub.empty:
            raise ValueError(f"Method '{m}' not found in CSV. Available: {sorted(df['method'].unique())}")
        pv = sub.pivot_table(
            index="seed_transpiler",
            columns="optimization_level",
            values="score",
            aggfunc="mean",
        )
        return pv.reindex(index=seeds, columns=opts)

    a_scores = pivot(method_a)
    b_scores = pivot(method_b)
    diff = (a_scores - b_scores).to_numpy(dtype=float)
    return diff, seeds, opts


def plot_heatmap(
    diff: np.ndarray,
    seeds: np.ndarray,
    opts: np.ndarray,
    method_a: str,
    method_b: str,
    out_path: Path,
    title: Optional[str] = None,
    dpi: int = 220,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8))
    im = ax.imshow(diff, aspect="auto")

    ax.set_xlabel("optimization_level")
    ax.set_ylabel("seed_transpiler")
    ax.set_xticks(np.arange(len(opts)))
    ax.set_xticklabels([str(o) for o in opts])
    ax.set_yticks(np.arange(len(seeds)))
    ax.set_yticklabels([str(s) for s in seeds])

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(f"score({method_a}) - score({method_b})")

    if title is None:
        title = f"Score difference heatmap: {method_a} - {method_b}"
    ax.set_title(title)

    if np.isnan(diff).any():
        for r, c in np.argwhere(np.isnan(diff)):
            ax.text(c, r, "NA", ha="center", va="center", fontsize=8)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def plot_scatter(
    df: pd.DataFrame,
    method_a: str,
    method_b: str,
    out_path: Path,
    title: Optional[str] = None,
    dpi: int = 220,
) -> None:
    df = df.copy()
    df["seed_transpiler"] = df["seed_transpiler"].astype(int)
    df["optimization_level"] = df["optimization_level"].astype(int)
    df["score"] = df["score"].astype(float)

    a = df[df["method"] == method_a][["seed_transpiler", "optimization_level", "score"]].rename(
        columns={"score": "a"}
    )
    b = df[df["method"] == method_b][["seed_transpiler", "optimization_level", "score"]].rename(
        columns={"score": "b"}
    )

    merged = a.merge(b, on=["seed_transpiler", "optimization_level"], how="inner")
    if merged.empty:
        raise ValueError("No overlapping (seed,opt) pairs between the two methods.")

    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    ax.scatter(merged["b"].to_numpy(), merged["a"].to_numpy(), s=22)

    mn = float(min(merged["a"].min(), merged["b"].min()))
    mx = float(max(merged["a"].max(), merged["b"].max()))
    ax.plot([mn, mx], [mn, mx], linewidth=1)

    ax.set_xlabel(f"score({method_b})")
    ax.set_ylabel(f"score({method_a})")

    if title is None:
        title = f"Scatter: {method_a} vs {method_b} (paired by seed x opt)"
    ax.set_title(title)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
