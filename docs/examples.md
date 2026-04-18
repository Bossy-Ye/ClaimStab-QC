# Examples & Outputs

Use [Design Your Own Case](design_your_own_case.md) for the canonical authoring guide.
This page only lists the active examples worth copying.

## Community Examples

### Lightweight demo

```bash
python examples/community/claim_stability_demo.py \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --sample-seed 1
```

Output:

- `output/examples/claim_stability_demo/`

### Custom external task demo

```bash
python -m claimstab.cli run \
  --spec examples/community/custom_task_demo/spec_toy.yml \
  --out-dir output/examples/toy_task_demo \
  --report
```

Output:

- `output/examples/toy_task_demo/`

### QEC pilot demo

```bash
python -m claimstab.cli run \
  --spec examples/community/qec_pilot_demo/spec_qec_decoder.yml \
  --out-dir output/examples/qec_pilot_demo \
  --report
```

### VQE pilot demo

```bash
python -m claimstab.cli run \
  --spec examples/community/vqe_pilot_demo/spec_vqe_h2.yml \
  --out-dir output/examples/vqe_pilot_demo \
  --report
```

### Max-2-SAT pilot demo

```bash
python -m claimstab.cli run \
  --spec examples/community/max2sat_pilot_demo/spec_max2sat.yml \
  --out-dir output/examples/max2sat_pilot_demo \
  --report
```

## Paper Example

```bash
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml \
  --out-dir output/paper/evaluation_v2/runs/E1_maxcut_main \
  --report
```
