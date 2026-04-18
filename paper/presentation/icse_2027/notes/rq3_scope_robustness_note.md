# RQ3 Scope Robustness Note

This note summarizes the paper-facing scope-robustness asset set.

Core result:
- the analysis fixes three representative archetypes:
  - one robust stable case
  - one robust unstable case
  - one boundary-sensitive case

Transport classes:
- `robustly stable`: the verdict remains stable across nearby admissible scopes
- `robustly unstable`: the verdict remains unstable across nearby admissible scopes
- `boundary-sensitive`: the verdict flips under nearby scope broadening

Current cases:
- `Clear stable: GHZ_Linear > GHZ_Star` -> robustly stable
- `Clear unstable: QAOA_p2 > QAOA_p1` -> robustly unstable
- `Near-boundary: VQE_HEA > VQE_HF` -> boundary-sensitive

Recommended paper use:
- use the transport map as the main `RQ3` scope figure
- use the compact summary table in appendix or artifact-facing prose
- emphasize that explicit admissible scope is a methodological input whose effect can be characterized rather than hidden
