# Release Notes Template

Use this template for GitHub Releases during the ICSE-focused phase.

## Release Summary

- Version:
- Date:
- Scope:
- Positioning: ICSE-first clarity/reproducibility release.

## Why This Release

- What reviewer/newcomer pain points this release addresses.
- What remains intentionally deferred.

## User-Visible Changes

1. Documentation / onboarding updates
2. CI / reliability updates
3. Compatibility / contract updates
4. Website information architecture updates (if any)

## Compatibility Statement

- CLI command/flag compatibility: unchanged / changed (explain)
- Output artifact compatibility: unchanged / changed (explain)
- Evidence schema compatibility: unchanged / changed (explain)

## Reproduction Commands

```bash
python -m claimstab.cli validate-spec --spec specs/paper_main.yml
python -m claimstab.cli run --spec specs/paper_main.yml --out-dir output/presentation_large/large/maxcut_ranking --report
python -m claimstab.cli validate-evidence --json output/presentation_large/large/maxcut_ranking/claim_stability.json
```

## Validation Gates Status

- [ ] CI green
- [ ] pytest green
- [ ] mkdocs build strict green
- [ ] compatibility guardrails green
- [ ] spec validation green
- [ ] evidence validation smoke green

## Known Limitations / Deferred Work

1. PyPI publication deferred.
2. Advanced platform features deferred.
3. Any remaining CI/platform caveats.
