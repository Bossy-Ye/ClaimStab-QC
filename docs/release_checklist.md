# Release Checklist (GitHub First)

This checklist defines minimal readiness for a GitHub Release in the current submission phase.

## Release Policy

1. Publish GitHub Releases when gates pass.
2. Defer PyPI publication until post-submission hardening.

## Readiness Gates (All Required)

1. CI status is green on target release commit.
2. Local tests pass:

```bash
./.venv/bin/python -m pytest -q
```

3. Docs build passes strictly:

```bash
./.venv/bin/python -m mkdocs build --strict
```

4. Compatibility guardrails pass:

```bash
./.venv/bin/python -m claimstab.scripts.check_refactor_compat --mode all
```

5. Canonical spec validation passes:

```bash
./.venv/bin/python -m claimstab.cli validate-spec --spec specs/paper_main.yml
```

6. Evidence validation smoke passes:

```bash
./.venv/bin/python -m claimstab.cli validate-evidence --json output/presentation_large/large/maxcut_ranking/claim_stability.json
```

## Release Packaging Scope (Minimal)

1. Source code at tagged commit.
2. Updated docs and compatibility contract references.
3. Changelog entries for user-visible changes.
4. Reproduction command pointers (main + paper-pack).

## Publication Steps

1. Freeze release commit on main.
2. Tag version (`v0.x.y`).
3. Draft GitHub Release notes using template.
4. Publish release.
5. Verify links and reproduction commands once from clean checkout.

## Explicitly Deferred

1. PyPI publication.
2. New long-term API guarantees beyond current compatibility contract.
3. Platformization work (dashboards, broad service surface).
