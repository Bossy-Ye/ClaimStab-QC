# Compatibility Contract

This document defines the backward-compatibility guarantees for ClaimStab-QC.

## Guaranteed Stable Interfaces
1. CLI entrypoint forms remain valid:
   - `python -m claimstab.cli ...`
   - `python -m claimstab.pipelines.claim_stability_app ...`
   - `python -m claimstab.pipelines.multidevice_app ...`
2. Output artifact names remain stable under run directories:
   - `claim_stability.json`, `rq_summary.json`, `robustness_map.json`, `scores.csv`
   - `combined_summary.json` for multidevice workflows
3. Report path and structure remain stable:
   - `stability_report.html`
4. Evidence protocol compatibility remains stable:
   - `experiments[*].evidence.cep` fields stay schema-compatible
5. Active paper-bundle contract remains stable:
   - `output/paper/evaluation_v2/runs/*`
   - `output/paper/evaluation_v2/derived_paper_evaluation/*`
   - `output/paper/evaluation_v2/pack/figures/*`

## Allowed Changes (Non-breaking)
- Additive JSON fields.
- New optional spec presets and optional scripts.
- New figures and tables in paper-pack output.
- Internal refactors that preserve external behavior.

## Disallowed Changes (Breaking)
- Renaming/removing existing CLI flags or commands.
- Renaming/removing established artifact files.
- Changing meaning of existing decision fields without version bump.
- Mutating CEP required fields in incompatible ways.

## Required Validation Before Merge
```bash
python -m pytest -q
python -m claimstab.scripts.check_refactor_compat --mode all
python -m claimstab.cli validate-spec --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml
python -m claimstab.cli validate-evidence --json output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json
python -m mkdocs build --strict
```

## Rollback Policy
- If compatibility drift is detected, revert the latest offending commit and rerun compatibility checks before any further changes.
