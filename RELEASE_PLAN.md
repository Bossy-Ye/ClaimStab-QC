# Release Plan (Minimal, ICSE-Aligned)

## Decision

1. GitHub Release: Yes, once readiness gates pass.
2. PyPI: Postpone until post-ICSE stabilization.

## Why GitHub Release First

1. Captures code/docs/artifact state with commit/tag provenance.
2. Supports ICSE artifact review and reproducibility references.
3. Lower operational risk than immediate package-publication promises.

## Why PyPI Is Deferred

1. Interface hardening is still in progress.
2. Optional dependency matrix is non-trivial for first external users.
3. Better to publish after one full ICSE cycle and post-submission cleanup.

## Release Readiness Gates

All must pass:

1. CI green on default branch.
2. `python -m pytest -q` green locally.
3. `python -m mkdocs build --strict` green.
4. `python -m claimstab.scripts.check_refactor_compat --mode all` green.
5. `python -m claimstab.cli validate-spec --spec specs/paper_main.yml` green.
6. `python -m claimstab.cli validate-evidence --json output/presentation_large/large/maxcut_ranking/claim_stability.json` green.

## Minimal Release Checklist

1. Update `CHANGELOG.md` (`[Unreleased]` -> release notes).
2. Confirm docs links and canonical quickstart commands.
3. Tag release commit (`v0.x.y`) and publish GitHub Release notes.
4. Attach pointer to paper-pack/repro commands.
5. Record known limitations and deferred items (including PyPI deferral).

## Release Notes Structure

1. What this release is (ICSE-focused stability/repro release).
2. User-visible changes (CLI/docs/workflow clarity).
3. Compatibility contract and non-breaking statement.
4. Reproduction commands.
5. Known limitations and planned post-ICSE work.
