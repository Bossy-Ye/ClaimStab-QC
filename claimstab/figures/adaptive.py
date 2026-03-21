from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from claimstab.figures.style import PAPER_GRAY_DARK, PAPER_GRAY_LIGHT, PAPER_GRAY_MEDIUM, PAPER_RED_DARK


@dataclass(frozen=True)
class MatrixDiagnosis:
    rows: int
    cols: int
    finite_count: int
    value_min: float
    value_max: float
    value_range: float
    value_std: float


def diagnose_matrix(matrix: np.ndarray) -> MatrixDiagnosis:
    rows, cols = matrix.shape if matrix.ndim == 2 else (0, 0)
    finite = matrix[np.isfinite(matrix)] if matrix.size else np.array([], dtype=float)
    if finite.size == 0:
        return MatrixDiagnosis(rows=rows, cols=cols, finite_count=0, value_min=0.0, value_max=0.0, value_range=0.0, value_std=0.0)
    v_min = float(np.min(finite))
    v_max = float(np.max(finite))
    return MatrixDiagnosis(
        rows=rows,
        cols=cols,
        finite_count=int(finite.size),
        value_min=v_min,
        value_max=v_max,
        value_range=float(v_max - v_min),
        value_std=float(np.std(finite)),
    )


def classify_matrix_encoding(diag: MatrixDiagnosis, *, near_constant_tol: float = 0.01) -> str:
    if diag.finite_count <= 0:
        return "empty"
    if diag.finite_count == 1:
        return "single_value"
    if diag.rows <= 1 or diag.cols <= 1:
        if diag.value_range < near_constant_tol:
            return "strip_constant"
        return "strip"
    if diag.value_range < near_constant_tol:
        return "constant_table"
    return "heatmap"


def plot_ordered_lollipop(
    ax,
    *,
    labels: Sequence[str],
    values: Sequence[float],
    xlabel: str,
    title: str,
    color: str = PAPER_RED_DARK,
):
    rows = sorted([(str(lbl), float(val)) for lbl, val in zip(labels, values)], key=lambda item: item[1])
    if not rows:
        return
    ys = list(range(len(rows)))
    vals = [item[1] for item in rows]
    lbls = [item[0] for item in rows]
    ax.hlines(ys, xmin=0.0, xmax=vals, color=PAPER_GRAY_LIGHT, linewidth=0.9, alpha=0.9)
    ax.plot(vals, ys, "o", color=color, markersize=4.3, markeredgecolor="white", markeredgewidth=0.4)
    ax.set_yticks(ys)
    ax.set_yticklabels(lbls)
    ax.set_xlabel(xlabel)
    if str(title).strip():
        ax.set_title(title, loc="left")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    max_val = max(vals) if vals else 1.0
    x_right = max(0.05, max_val * 1.16)
    ax.set_xlim(left=0.0, right=x_right)
    offset = max(0.01, x_right * 0.012)
    for y, val in zip(ys, vals):
        text_x = min(x_right - offset * 0.2, val + offset)
        ax.text(text_x, y, f"{val:.2f}", va="center", ha="left", fontsize=8.0, color=PAPER_GRAY_DARK)


def plot_compact_table(
    ax,
    *,
    row_labels: Sequence[str],
    col_labels: Sequence[str],
    matrix: np.ndarray,
    title: str,
    note: str | None = None,
):
    ax.axis("off")
    ax.set_title(title, loc="left")
    display = np.where(np.isfinite(matrix), matrix, np.nan)
    cell_text = []
    for i in range(display.shape[0]):
        row = []
        for j in range(display.shape[1]):
            val = display[i, j]
            row.append("NA" if not np.isfinite(val) else f"{float(val):.2f}")
        cell_text.append(row)
    table = ax.table(
        cellText=cell_text,
        rowLabels=[str(v) for v in row_labels],
        colLabels=[str(v) for v in col_labels],
        cellLoc="center",
        rowLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.6)
    table.scale(1.0, 1.14)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#d3d3d3")
        cell.set_linewidth(0.6)
        if r == 0 or c == -1:
            cell.set_facecolor("#f5f5f5")
    if note:
        ax.text(0.0, 0.01, note, transform=ax.transAxes, ha="left", va="bottom", fontsize=8.3, color=PAPER_GRAY_MEDIUM)


def plot_stat_card(
    ax,
    *,
    title: str,
    lines: Sequence[tuple[str, str]],
    note: str | None = None,
):
    ax.axis("off")
    ax.set_title(title, loc="left")
    y = 0.86
    for key, value in lines:
        ax.text(
            0.0,
            y,
            f"{key}: ",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9.2,
            color=PAPER_GRAY_MEDIUM,
            bbox=dict(boxstyle="round,pad=0.16", facecolor="#f7f7f7", edgecolor="#ececec", linewidth=0.5),
        )
        ax.text(0.32, y, str(value), transform=ax.transAxes, ha="left", va="top", fontsize=9.6, color=PAPER_GRAY_DARK)
        y -= 0.13
    if note:
        ax.text(0.0, 0.04, note, transform=ax.transAxes, ha="left", va="bottom", fontsize=8.2, color=PAPER_GRAY_MEDIUM)
