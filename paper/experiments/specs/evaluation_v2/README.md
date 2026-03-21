# Evaluation v2 Specs

These specs stage the rerun layout for the newer RQ1-RQ4 evaluation narrative.

Implemented exact-scope runs:
- `e1_maxcut_main.yml`
- `e2_ghz_structural.yml`
- `e3_bv_decision.yml`
- `e4_grover_distribution.yml`
- `s2_boundary.yml`
- `qec_portability.yml`

Staged but not yet final:
- `s1_multidevice_portability.yml`
  - current multidevice pipeline still needs alignment with the updated portability story

Not yet encoded as a final spec:
- E5 multi-claim policy comparison
  - current repository still has the legacy one-claim adaptive study
  - the 15-claim post hoc stratified selection policy must be finalized before rerun

These specs intentionally use the additive exact-scope presets:
- `compilation_only_exact` (27 configs)
- `sampling_only_exact` (20 configs)
- `combined_light_exact` (30 configs)
