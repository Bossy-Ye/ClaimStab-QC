# Community Examples

This directory contains the public-facing, lightweight examples that are safest to point new users to.

## Canonical Public Entry Points

- `claim_stability_demo.py`
  Thin wrapper around the standard CLI app; writes by default to `output/examples/claim_stability_demo/`.
- `multidevice_demo.py`
  Thin wrapper around the multidevice pipeline; writes by default to `output/examples/multidevice_demo/`.
- `qec_pilot_demo/`
  External repetition-code-style decoder comparison example used as a portability illustration.

## Recommended Commands

Lightweight claim-stability demo:

```bash
python examples/community/claim_stability_demo.py \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --sample-seed 1
```

QEC portability demo:

```bash
python -m claimstab.cli run \
  --spec examples/community/qec_pilot_demo/spec_qec_decoder.yml \
  --out-dir output/examples/qec_pilot_demo \
  --report
```

Multidevice demo:

```bash
python examples/community/multidevice_demo.py --run transpile_only --suite standard
```

## Scope Notes

- Older Atlas/community-contribution scaffolds remain in the repository for reference, but some of their historical spec defaults are no longer part of the canonical public workflow.
- If you need a guaranteed working public entrypoint, use the three commands above.
