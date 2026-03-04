import tempfile
import unittest
from pathlib import Path

from claimstab.cache.store import CacheStore
from claimstab.core.trace import TraceIndex, TraceRecord
from claimstab.runners.matrix_runner import ScoreRow


class TestTraceAndCache(unittest.TestCase):
    def _row(self) -> ScoreRow:
        return ScoreRow(
            instance_id="g1",
            seed_transpiler=1,
            optimization_level=2,
            transpiled_depth=12,
            transpiled_size=22,
            method="M1",
            score=0.75,
            metric_name="objective",
            seed_simulator=7,
            shots=256,
            layout_method="sabre",
            circuit_depth=12,
            two_qubit_count=5,
            swap_count=1,
            counts={"00": 40, "11": 60},
        )

    def test_trace_roundtrip(self) -> None:
        row = self._row()
        rec = TraceRecord.from_score_row(suite="core", space_preset="sampling_only", row=row)
        rebuilt = rec.to_score_row()
        self.assertEqual(rebuilt.instance_id, row.instance_id)
        self.assertEqual(rebuilt.method, row.method)
        self.assertEqual(rebuilt.score, row.score)
        self.assertEqual(rebuilt.shots, row.shots)
        self.assertEqual(rebuilt.seed_simulator, row.seed_simulator)
        self.assertEqual(rebuilt.counts, row.counts)

    def test_trace_index_save_load_jsonl(self) -> None:
        row = self._row()
        rec = TraceRecord.from_score_row(suite="core", space_preset="baseline", row=row)
        idx = TraceIndex(records=[rec])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.jsonl"
            idx.save_jsonl(path)
            loaded = TraceIndex.load_jsonl(path)
            self.assertEqual(len(loaded.records), 1)
            self.assertEqual(loaded.records[0].suite, "core")
            self.assertEqual(loaded.records[0].space_preset, "baseline")
            self.assertEqual(loaded.records[0].method, "M1")

    def test_cache_store_put_get(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = CacheStore(Path(td) / "cache.sqlite")
            try:
                store.put("abc", {"score": 0.5, "x": 1})
                payload = store.get("abc")
                self.assertIsNotNone(payload)
                assert payload is not None
                self.assertEqual(payload["score"], 0.5)
                self.assertEqual(payload["x"], 1)
                self.assertIsNone(store.get("missing"))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
