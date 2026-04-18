# 01 Repo Convergence

## Goal

Reduce the repository to a clean ICSE-facing surface that retains the GitHub website, community entry points, and paper reproducibility assets, while removing unneeded generated clutter and dead entry points.

## Inputs

- current repo structure
- GitHub Pages docs surface under `docs/`
- community examples under `examples/community/`
- paper assets under `paper/experiments/`

## Outputs

- simplified public entry points
- removed or hidden generated clutter
- clear distinction between:
  - community usage
  - paper reproducibility
  - advanced/atlas surfaces
- repository cleanup note if needed

## Acceptance Criteria

- [x] Root `README.md` only acts as a clear front door and router.
- [x] `docs/index.md` is a website homepage, not a dumping ground.
- [x] GitHub Pages surface remains intact and buildable.
- [x] No tracked generated site output or stale demo artifacts remain.
- [x] No dead community or paper entry points remain in public docs.
- [x] `paper/experiments/README.md` points to the canonical ICSE sprint backlog.

## Dependencies

- [00_OVERVIEW.md](./00_OVERVIEW.md)

## Status

- [ ] Not started
- [ ] In progress
- [x] Done

## Notes

Keep the website. Do not delete `docs/`, `atlas/`, or interactive assets unless they are truly dead.
