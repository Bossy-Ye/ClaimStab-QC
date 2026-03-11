# Naive Baseline Policy Note

ClaimStab reports two naive baselines side-by-side to preserve comparability and improve practical interpretation.

## Policies

1. `naive_baseline` (`legacy_strict_all`)
- Historical policy used in prior runs.
- Interprets naive as strict baseline-only success: all baseline checks must hold.

2. `naive_baseline_realistic` (`default_researcher_v1`)
- New policy approximating common default practice.
- Uses observed hold rate with a fixed acceptance threshold (default `>= 2/3`) when multiple evaluations are available.

## Why both are reported

1. Backward compatibility:
- Existing historical numbers remain comparable via `naive_baseline`.

2. Practical relevance:
- `naive_baseline_realistic` better reflects how researchers often decide with a small number of runs/seeds.

3. Transparent interpretation:
- Reports and RQ summaries now include both policy outcomes, avoiding silent metric shifts.

