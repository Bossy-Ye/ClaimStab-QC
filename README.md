# ClaimStab-QC

ClaimStab-QC is a claim-centric validation harness for testing whether paper-level experimental claims remain stable under software-visible perturbations in quantum toolchains.

## What this repository provides
- `RankingClaim`: declarative claim object (`A >= B + delta` by default)
- `PerturbationSpace`: explicit perturbation knobs (transpiler seed, optimization level, layout, shots, simulator seed)
- `MatrixRunner`: backend runner over methods x perturbation configurations
- Sampling-aware evaluation: full-factorial or random-K perturbation sampling
- Rank-flip evaluation: fraction of perturbations that invert claim truth relative to a declared baseline
- Uncertainty-aware decisions: Wilson confidence intervals + conservative stability decision rule
- Deterministic benchmark suites: `core`, `standard`, `large` (30 instances in `large`)
- Batch evaluation across perturbation spaces and claim pairs
- Failure diagnostics: per-dimension attribution, top unstable configurations, and lock-down recommendations
- Conditional stability analysis: recompute stability under constraints (e.g., `shots=1024`)
- Stability-vs-cost analysis: shots vs stability/flip-rate with CI
- Machine-readable outputs: CSV score matrix and JSON claim summary

## Quickstart
1. Create/activate a virtual environment.
2. Install the package.

```bash
python -m pip install -e .
```

Optional extras:

```bash
python -m pip install -e ".[aer,ibm]"
```

If editable install is unavailable in your environment, run with a local module path:

```bash
PYTHONPATH=. python examples/claim_stability_demo.py
```

Otherwise run normally:

```bash
python examples/claim_stability_demo.py
```

The demo defaults to `BasicSimulator` for portability. To force Aer:

```bash
CLAIMSTAB_SIMULATOR=aer python examples/claim_stability_demo.py
```

Run with random-K sampling and explicit thresholds:

```bash
python examples/claim_stability_demo.py \
  --sampling-mode random_k \
  --sample-size 50 \
  --confidence-level 0.95 \
  --stability-threshold 0.95 \
  --deltas 0.0,0.01,0.05
```

To intentionally stress perturbation sensitivity (usually non-zero flip rates), use execution-level perturbations:

```bash
python examples/claim_stability_demo.py \
  --space-preset sampling_only \
  --method-a QAOA_p2 \
  --method-b RandomBaseline \
  --sampling-mode full_factorial \
  --deltas 0.0,0.01,0.05
```

Why low-shot values (`16/32/64`) are included in `sampling_only`:
- to stress sampling uncertainty explicitly,
- to model common small-shot exploratory runs used in practice,
- to reveal instability failure modes that may be hidden at large shots.

To run a deterministic multi-instance experiment (no random-K sampling) on the standard suite:

```bash
python examples/claim_stability_demo.py \
  --suite standard \
  --space-preset sampling_only \
  --method-a QAOA_p2 \
  --method-b RandomBaseline \
  --sampling-mode full_factorial \
  --deltas 0.0,0.01,0.05 \
  --out-dir output
```

To run deterministic comparative experiments across multiple perturbation spaces and multiple claims:

```bash
python examples/claim_stability_demo.py \
  --suite large \
  --space-presets compilation_only,sampling_only,combined_light \
  --claim-pairs "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline" \
  --sampling-mode full_factorial \
  --deltas 0.0,0.01,0.05 \
  --out-dir output
```

Optional realism spot-check with a lightweight Aer noise model:

```bash
python examples/claim_stability_demo.py \
  --suite standard \
  --space-preset sampling_only \
  --sampling-mode full_factorial \
  --spot-check-noise \
  --backend-engine aer \
  --one-qubit-error 0.001 \
  --two-qubit-error 0.01 \
  --out-dir output
```

## Multi-device demo
Tier-1 (cheap, broad): transpile-only structural metrics across multiple device profiles.

```bash
PYTHONPATH=. python examples/multidevice_demo.py \
  --run transpile_only \
  --suite standard \
  --transpile-space compilation_only \
  --transpile-devices FakeManilaV2,FakeBrisbane,FakePrague \
  --out-dir output
```

Tier-2 (strong, still free): device-informed noisy simulation on 1-2 fake devices.

```bash
PYTHONPATH=. python examples/multidevice_demo.py \
  --run noisy_sim \
  --suite standard \
  --noisy-space sampling_only \
  --noisy-devices FakeManilaV2,FakeBrisbane \
  --out-dir output
```

Optional spec fields (all optional, fully backward compatible):
- `device_profile.enabled/provider/name/mode`
- `backend.noise_model` (`none` or `from_device_profile`)

## Demo output
The demo writes suite-specific files:
- `output/scores.csv`
- `output/claim_stability.json`
- `output/claim_stability.json` includes per-delta factor attribution by perturbation dimension
- `output/claim_stability.json` includes aggregate `stability_hat + CI + decision` and `decision_counts`
- Batch runs include `experiments[]` and comparative `space x claim x delta` rows
- Multi-device runs add `device_profile` metadata, snapshot fingerprints, and per-device summaries

The JSON includes:
- claim definition + delta sweep
- fully specified baseline configuration
- sampling policy and sampled-configuration count
- perturbation-space size
- per-delta confidence intervals and conservative decisions (`stable`, `unstable`, `inconclusive`)
- aggregate stability estimate (`stability_hat`, `stability_ci_low`, `stability_ci_high`) + aggregate decision
- decision counts across instances (`decision_counts`)
- separate claim-truth statistics (`holds_rate_mean`, `holds_rate_ci_low`, `holds_rate_ci_high`)
- per-instance and aggregate summaries
- aggregated diagnostics and top unstable perturbation configurations
- top lock-down recommendations: “fix this knob to improve stability by X”
- auxiliary end-to-end examples for decision and distribution claims

## Paper-ready specs
Template specs are provided in:
- `examples/specs/claim_spec.yaml`
- `examples/specs/perturbation_spec.yaml`

These encode:
- CI-based conservative stability decisions
- full-factorial small-scale + random-K large-scale sampling
- ranking delta-sweep
- algorithmic decision-claim acceptance rules
- distribution-distance sensitivity checks

## Report generation
Generate an HTML report from the JSON artifact:

```bash
python -m claimstab.scripts.generate_stability_report --json output/claim_stability.json
```

This writes:
- `output/stability_report.html`

Report sections include:
- executive summary (3 bullets)
- claim summary table (all claims)
- per-experiment delta sweep with `stability_hat + CI + decision`
- stability-vs-cost (shots) tables (and optional plot)
- top lock-down drivers (which single knob to fix for largest stability gain)
- auxiliary end-to-end decision/distribution claim examples
- reproduce command

To also render plots (environment permitting):

```bash
python -m claimstab.scripts.generate_stability_report --json output/claim_stability.json --with-plots
```

Plot outputs:
- `output/report_assets/delta_sweep_<experiment_index>.png`
- `output/report_assets/factor_attribution_<experiment_index>.png` (when attribution is available)
- `output/report_assets/shots_stability_<experiment_index>.png` (when shots analysis is available)

## Test
```bash
PYTHONPATH=. ./venv/bin/python -m pytest -q
```
