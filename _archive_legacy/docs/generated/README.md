# Generated Docs Policy

This folder intentionally tracks only canonical generated artifacts used by the project website and release workflow.

Tracked by default:
- `implementation_catalog.md`
- `.gitkeep`

Not tracked by default:
- ad-hoc local summaries (for example `repo_summary.md`, `repo_summary.html`)
- temporary comparison/debug snapshots

If a new generated file should be canonical, add it to the build workflow and reference it in docs navigation before tracking it in git.
