from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_claim_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{p} must contain a JSON object.")
    return payload


def comparative_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    if not isinstance(rows, list):
        rows = []
    return pd.DataFrame(rows)


def rq_dataframe(payload: dict[str, Any]) -> dict[str, pd.DataFrame]:
    rq = payload.get("rq_summary", {})
    out: dict[str, pd.DataFrame] = {}
    if isinstance(rq, dict):
        rq2 = rq.get("rq2_drivers", {})
        out["rq2_drivers"] = pd.DataFrame(rq2.get("all_dimensions", []) if isinstance(rq2, dict) else [])
        rq3 = rq.get("rq3_cost_tradeoff", {})
        out["rq3_cost"] = pd.DataFrame(rq3.get("stability_vs_cost_rows", []) if isinstance(rq3, dict) else [])
    return out


def load_scores_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)
