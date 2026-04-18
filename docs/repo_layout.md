# Repository Layout

This repository is organized around four distinct surfaces. Keeping them
separate is a hard rule for future changes.

## 1. Method implementation

Long-lived framework code lives under:

- `claimstab/`
- `docs/concepts/`
- `pyproject.toml`

This surface should remain venue-neutral. Avoid embedding conference names in
module names, package names, or framework-facing filenames.

## 2. Historical experiment provenance

Frozen experiment inputs and their historical rerun scaffolds live under:

- `paper/experiments/specs/evaluation_v2/`
- `paper/experiments/specs/evaluation_v3/`
- `paper/experiments/specs/evaluation_v4/`

These directories preserve how the evidence was produced. They are not the
paper-facing narrative surface.

## 3. Submission-facing editorial surface

Curated manuscript material lives under:

- `paper/presentation/icse_2027/`

This surface may remain venue-specific, but the venue naming must stay confined
to this subtree. It should contain only:

- definitions
- notes
- figure inventories
- table inventories

It must not accumulate raw run directories, exploratory prose, or planning
drafts that are not intended for the submission.

## 4. Local archive and exploratory work

Material that is useful locally but should not be committed belongs in:

- `.local_archive/`

Examples include:

- one-off planning memos
- exploratory pilot branches
- hardware preflight scratch documents
- office documents
- unreviewed manuscript drafts

Anything in `.local_archive/` is explicitly outside the reproducible repo
surface.

## Script naming policy

Paper experiment scripts should reflect **purpose**, not venue.

Recommended prefixes:

- `export_...`
  - canonical paper-facing dataset / figure / table exporters
- `run_...`
  - execution entry points, hardware runners, and profile runners
- `reproduce_...`
  - batch reruns of historical bundles
- `derive_...`
  - legacy or transitional derivations only

Avoid adding new script names that encode conference names such as `icse`.

## Commit boundary

Safe to commit:

- method implementation
- frozen specs
- canonical paper-facing exporters
- curated submission notes / definitions / figure inventories
- repo-structure and hygiene docs

Do not commit:

- `output/`
- `artifacts/`
- `site/`
- `.idea/`
- `*.egg-info/`
- `.local_archive/`
- ad hoc office documents

## Reading order

If you need to understand the current paper state, read in this order:

1. `README.md`
2. `paper/experiments/README.md`
3. `paper/presentation/icse_2027/README.md`
4. `paper/experiments/backlog_icse_2027/README.md`
