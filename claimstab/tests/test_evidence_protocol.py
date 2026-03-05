from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from claimstab.evidence import (
    build_cep_protocol_meta,
    build_experiment_cep_record,
    validate_evidence_file,
    validate_evidence_payload,
)


def _write_trace(path: Path) -> None:
    row = {
        "suite": "core",
        "space_preset": "sampling_only",
        "instance_id": "g0",
        "method": "A",
        "metric_name": "objective",
        "seed_transpiler": 0,
        "optimization_level": 1,
        "layout_method": "sabre",
        "seed_simulator": 0,
        "shots": 1024,
        "score": 1.0,
        "transpiled_depth": 12,
        "transpiled_size": 18,
        "counts": {"00": 50, "11": 50},
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def _valid_payload(trace_path: Path) -> dict:
    exp = {
        "experiment_id": "sampling_only:A>B",
        "claim": {"type": "ranking", "method_a": "A", "method_b": "B", "deltas": [0.0]},
        "sampling": {
            "suite": "core",
            "space_preset": "sampling_only",
            "mode": "random_k",
            "sample_size": 16,
            "seed": 7,
            "perturbation_space_size": 100,
        },
        "stability_rule": {"threshold": 0.95, "confidence_level": 0.95},
        "backend": {"engine": "basic", "noise_model": "none"},
        "device_profile": {"enabled": False, "provider": "none", "name": None, "mode": "transpile_only"},
        "baseline": {
            "seed_transpiler": 0,
            "optimization_level": 1,
            "layout_method": "sabre",
            "shots": 16,
            "seed_simulator": 0,
        },
        "evidence": {
            "trace_query": {
                "suite": "core",
                "space_preset": "sampling_only",
                "metric_name": "objective",
                "methods": ["A", "B"],
            },
            "artifacts": {
                "trace_jsonl": str(trace_path),
                "events_jsonl": None,
                "cache_db": None,
            },
            "lookup_fields": [
                "suite",
                "space_preset",
                "instance_id",
                "method",
                "metric_name",
                "seed_transpiler",
                "optimization_level",
                "layout_method",
                "shots",
                "seed_simulator",
            ],
        },
    }
    exp["evidence"]["cep"] = build_experiment_cep_record(
        experiment=exp,
        runtime_meta={"git_commit": "abc123", "git_dirty": False, "dependencies": {"qiskit": "2.2.3"}},
        evidence=exp["evidence"],
    )

    return {
        "meta": {
            "artifacts": {
                "trace_jsonl": str(trace_path),
                "events_jsonl": None,
                "cache_db": None,
                "replay_trace": None,
            },
            "evidence_chain": build_cep_protocol_meta(
                lookup_fields=exp["evidence"]["lookup_fields"],
                decision_provenance=(
                    "each experiment includes evidence.trace_query + evidence.cep blocks "
                    "that can be matched against trace records for reproducible decision provenance"
                ),
            ),
        },
        "experiments": [exp],
    }


class TestEvidenceProtocol(unittest.TestCase):
    def test_validate_evidence_payload_passes_with_matching_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            _write_trace(trace_path)
            payload = _valid_payload(trace_path)
            result = validate_evidence_payload(payload, json_path=Path(td) / "claim_stability.json")
            self.assertEqual(result.errors, [])
            self.assertEqual(result.experiments_checked, 1)
            self.assertEqual(result.experiments_with_trace_match, 1)

    def test_validate_evidence_payload_flags_unmatched_query(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            _write_trace(trace_path)
            payload = _valid_payload(trace_path)
            payload["experiments"][0]["evidence"]["trace_query"]["methods"] = ["NotPresent"]
            result = validate_evidence_payload(payload, json_path=Path(td) / "claim_stability.json")
            self.assertGreaterEqual(len(result.errors), 1)
            self.assertTrue(any("no trace records match query" in line for line in result.errors))

    def test_validate_evidence_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            trace_path = td_path / "trace.jsonl"
            payload_path = td_path / "claim_stability.json"
            _write_trace(trace_path)
            payload = _valid_payload(trace_path)
            payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            result = validate_evidence_file(payload_path)
            self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
