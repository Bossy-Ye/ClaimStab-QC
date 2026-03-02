from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Rectangle


def _viz_rc() -> dict[str, object]:
    return {
        "figure.facecolor": "#fbfaf7",
        "axes.facecolor": "#f7f5ef",
        "axes.edgecolor": "#3a3a3a",
        "axes.grid": True,
        "grid.color": "#b6b6b6",
        "grid.linestyle": (0, (1, 3)),
        "grid.linewidth": 0.7,
        "font.family": "DejaVu Sans",
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "axes.labelsize": 10.5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.frameon": True,
        "legend.facecolor": "#f8f7f4",
        "legend.edgecolor": "#8a8a8a",
    }


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
    with plt.rc_context(_viz_rc()):
        nrows, ncols = diff.shape
        width = max(4.6, 1.35 * ncols + 2.2)
        height = max(4.0, 1.05 * nrows + 2.0)
        fig, ax = plt.subplots(figsize=(width, height))

        vmax = float(np.nanmax(np.abs(diff))) if np.isfinite(diff).any() else 1.0
        vmax = max(vmax, 1e-8)
        cmap = LinearSegmentedColormap.from_list(
            "claimstab_div",
            ["#194c7f", "#4f86c6", "#f4f2ee", "#e57f3d", "#8c2d04"],
        )
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
        im = ax.imshow(diff, aspect="auto", cmap=cmap, norm=norm)

        ax.set_xlabel("optimization_level", fontweight="semibold")
        ax.set_ylabel("seed_transpiler", fontweight="semibold")
        ax.set_xticks(np.arange(len(opts)))
        ax.set_xticklabels([str(o) for o in opts])
        ax.set_yticks(np.arange(len(seeds)))
        ax.set_yticklabels([str(s) for s in seeds])
        ax.set_xticks(np.arange(-0.5, len(opts), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(seeds), 1), minor=True)
        ax.grid(which="minor", color="#d7d3c8", linestyle="-", linewidth=0.8)
        ax.tick_params(which="minor", bottom=False, left=False)

        cbar = fig.colorbar(im, ax=ax, shrink=0.92)
        cbar.set_label(f"score({method_a}) - score({method_b})", fontweight="semibold")

        if title is None:
            title = f"Score Difference Heatmap: {method_a} - {method_b}"
        ax.set_title(title, fontfamily="DejaVu Serif")

        for r in range(nrows):
            for c in range(ncols):
                val = diff[r, c]
                if np.isnan(val):
                    # Missing cells shown with hatch texture for visibility in print.
                    ax.add_patch(
                        Rectangle(
                            (c - 0.5, r - 0.5),
                            1.0,
                            1.0,
                            fill=False,
                            hatch="////",
                            edgecolor="#6d6d6d",
                            linewidth=0.0,
                        )
                    )
                    ax.text(c, r, "NA", ha="center", va="center", fontsize=8, color="#4a4a4a")
                else:
                    txt = f"{val:.2f}"
                    txt_color = "#1e1e1e" if abs(val) < 0.55 * vmax else "#ffffff"
                    ax.text(c, r, txt, ha="center", va="center", fontsize=7.8, color=txt_color)

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

    with plt.rc_context(_viz_rc()):
        fig, ax = plt.subplots(figsize=(6.6, 6.0))

        x = merged["b"].to_numpy(dtype=float)
        y = merged["a"].to_numpy(dtype=float)
        delta = y - x
        colors = np.where(delta >= 0.0, "#1f7a8c", "#b85c38")

        ax.scatter(
            x,
            y,
            s=44,
            c=colors,
            alpha=0.84,
            edgecolors="#2d2d2d",
            linewidths=0.45,
            marker="o",
        )

        mn = float(min(merged["a"].min(), merged["b"].min()))
        mx = float(max(merged["a"].max(), merged["b"].max()))
        ax.plot([mn, mx], [mn, mx], linewidth=1.2, color="#484848", linestyle=(0, (5, 3)), label="y = x")

        for opt in sorted(merged["optimization_level"].unique().tolist()):
            sub = merged[merged["optimization_level"] == opt]
            ax.scatter(
                sub["b"].to_numpy(dtype=float),
                sub["a"].to_numpy(dtype=float),
                s=55,
                facecolors="none",
                edgecolors="#5f5f5f",
                linewidths=0.55,
                marker=("^" if int(opt) % 2 else "s"),
                alpha=0.4,
            )

        ax.set_xlabel(f"score({method_b})", fontweight="semibold")
        ax.set_ylabel(f"score({method_a})", fontweight="semibold")

        if title is None:
            title = f"Paired Scatter: {method_a} vs {method_b}"
        ax.set_title(title, fontfamily="DejaVu Serif")
        ax.legend(loc="upper left")

        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
