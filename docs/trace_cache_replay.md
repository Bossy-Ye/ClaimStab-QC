# Trace, Cache, Replay

This page shows copy-paste commands for the trace/cache/replay workflow.

## 1) Main pipeline with cache + trace + events

```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.claim_stability_app \
  --task maxcut \
  --suite core \
  --space-preset sampling_only \
  --sampling-mode random_k \
  --sample-size 8 \
  --sample-seed 7 \
  --cache-db output/demo_main/cache.sqlite \
  --trace-out output/demo_main/trace.jsonl \
  --events-out output/demo_main/events.jsonl \
  --out-dir output/demo_main
```

## 2) Main pipeline replay (no execution)

```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.claim_stability_app \
  --task maxcut \
  --suite core \
  --space-preset sampling_only \
  --replay-trace output/demo_main/trace.jsonl \
  --out-dir output/demo_main_replay
```

## 3) Multi-device transpile-only with cache + trace + events

```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.multidevice_app \
  --run transpile_only \
  --suite core \
  --sampling-mode random_k \
  --sample-size 2 \
  --sample-seed 1 \
  --transpile-devices FakeManilaV2 \
  --transpile-claim-pairs "QAOA_p1>QAOA_p2" \
  --cache-db output/multidevice_demo/cache.sqlite \
  --trace-out output/multidevice_demo/trace.jsonl \
  --events-out output/multidevice_demo/events.jsonl \
  --out-dir output/multidevice_demo
```

## 4) Multi-device replay (no execution)

```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.multidevice_app \
  --run transpile_only \
  --suite core \
  --transpile-devices FakeManilaV2 \
  --transpile-claim-pairs "QAOA_p1>QAOA_p2" \
  --replay-trace output/multidevice_demo/trace.jsonl \
  --out-dir output/multidevice_demo_replay
```

## What to expect

- `trace.jsonl`: row-level trace records for replay/re-analysis.
- `events.jsonl`: execution event stream.
- `cache.sqlite`: fingerprint-based cell cache.
- Replay mode recomputes claims/reports from trace without rerunning circuits.

## 5) Validate CEP evidence links

```bash
python -m claimstab.cli validate-evidence --json output/demo_main_replay/claim_stability.json
python -m claimstab.cli validate-evidence --json output/multidevice_demo_replay/combined_summary.json --no-trace-check
```
