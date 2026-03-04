from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping


class CacheStore:
    """Lightweight sqlite-backed cell cache for experiment reuse."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cell_cache (
                fingerprint TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def get(self, fingerprint: str) -> dict[str, Any] | None:
        cur = self._conn.execute(
            "SELECT payload_json FROM cell_cache WHERE fingerprint = ?",
            (fingerprint,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return json.loads(str(row[0]))

    def put(self, fingerprint: str, payload: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO cell_cache (fingerprint, payload_json)
            VALUES (?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET payload_json=excluded.payload_json
            """,
            (fingerprint, json.dumps(dict(payload), sort_keys=True)),
        )
        self._conn.commit()

