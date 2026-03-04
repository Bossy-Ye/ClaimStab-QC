from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class ExecutionEvent:
    event_type: str
    timestamp_utc: str
    instance_id: str
    method: str
    metric_name: str
    config: dict[str, Any]
    details: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def build(
        *,
        event_type: str,
        instance_id: str,
        method: str,
        metric_name: str,
        config: Mapping[str, Any],
        details: Mapping[str, Any] | None = None,
    ) -> "ExecutionEvent":
        return ExecutionEvent(
            event_type=event_type,
            timestamp_utc=_utc_now_iso(),
            instance_id=instance_id,
            method=method,
            metric_name=metric_name,
            config={str(k): v for k, v in dict(config).items()},
            details={str(k): v for k, v in dict(details or {}).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(payload: Mapping[str, Any]) -> "ExecutionEvent":
        return ExecutionEvent(
            event_type=str(payload.get("event_type", "")),
            timestamp_utc=str(payload.get("timestamp_utc", _utc_now_iso())),
            instance_id=str(payload.get("instance_id", "")),
            method=str(payload.get("method", "")),
            metric_name=str(payload.get("metric_name", "objective")),
            config=dict(payload.get("config", {}) or {}),
            details=dict(payload.get("details", {}) or {}),
        )


class JsonlEventLogger:
    """Append-only JSONL event sink."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: ExecutionEvent) -> None:
        line = json.dumps(event.to_dict(), sort_keys=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

