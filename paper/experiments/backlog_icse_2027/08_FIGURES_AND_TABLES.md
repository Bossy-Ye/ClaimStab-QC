# 08 Figures and Tables

## Goal

Reorganize all paper-facing visuals and tables so they directly support the ICSE methodology thesis.

## ICSE Page-Budget Rule

For the ICSE Research Track, appendix material still consumes main-text page budget.
Therefore, figure placement must be planned across three layers:

1. `main paper`
   - indispensable figures and tables only
2. `appendix inside the paper PDF`
   - compact supporting figures and tables that a reviewer may reasonably inspect during paper reading
3. `artifact / repository`
   - detailed breakdowns, extended sensitivity material, and full reproducibility surfaces

The default bias is:

- if a figure is not necessary for understanding the main claim, move it out of the main paper
- if a detailed breakdown is not necessary for reading flow, move it out of the paper PDF entirely and keep it in the artifact

## Main-Paper Figure Plan

The default ICSE full-paper figure plan is:

1. `Fig 1` headline `RQ1` result
   - source task: `02_E1_METRIC_VS_CLAIM`
   - figure: metric-positive validated vs not-validated bar
   - role: primary headline punch

2. `Fig 2` `RQ1` baseline comparison
   - source task: `03_E2_BASELINE_COMPARISON`
   - figure: validated vs false reassurance across baselines
   - role: blocks the “single weak baseline” reviewer objection

3. `Fig 3` `RQ3` explanatory evidence
   - source task: `05_E4_EXACT_MOS`
   - figure: compact witness-size / exact witness distribution
   - role: shows that failures admit compact sufficient witness sets

4. `Fig 4` `RQ4` practicality
   - source task: `12_RQ4_PRACTICALITY`
   - figure: cost / configuration tradeoff
   - role: shows that validation is practical rather than merely correct

If the paper can support a fifth main figure without overcrowding the main text,
the next candidate is:

5. `Fig 5` `RQ3` scope transport
   - source task: `04_E3_SCOPE_ROBUSTNESS`
   - role: rigor evidence for explicit admissible scope

## Appendix-Default Figures

The following should default to appendix unless the main text has unusual space:

- `02` discrepancy matrix
- `04` scope transport map
- `06` cross-family verdict distribution
- family / scope / delta sensitivity plots
- hardware mini-slice visualization

## Main vs Appendix vs Artifact Placement

### Main paper

Default main-paper figures:

- `Fig 1` headline `RQ1` mismatch bar
- `Fig 2` baseline-supportive validated vs false-reassurance comparison
- `Fig 3` exact witness / MOS explanatory figure
- `Fig 4` cost / configuration tradeoff

Default main-paper tables:

- `Tab 1` compact `RQ1` structural breakdown
- `Tab 2` baseline capability matrix only if the text needs explicit capability dimensions
- `Tab 3` exact witness examples

### Appendix in the paper PDF

Default appendix figures:

- `02` discrepancy matrix
- `04` scope transport map
- one cross-family figure if it materially sharpens the “not a toy artifact” claim

Default appendix tables:

- family / scope / delta breakdown tables
- `RQ3` scope transport summary
- exact-vs-approx status table
- minimal hardware summary table

### Artifact / repository only

Keep these out of the paper PDF unless a reviewer-facing gap appears:

- full detailed breakdown CSVs
- leave-one-family-out sensitivity
- primary-family-only sensitivity
- full reproduction command logs
- audit notes and extended supporting notes
- exploratory candidate figures that informed design choices but are not canonical paper visuals

## Figure Freeze Policy

A figure may become a canonical paper figure only after all of the following hold:

- the underlying dataset schema is frozen
- the supporting table counts match the frozen dataset
- the figure is generated directly from code, not manually edited
- the figure role in the paper is explicit:
  - headline
  - comparison
  - explanation
  - practicality
- the figure has a stable file path under `output/paper/icse_pack/figures/`

Exploratory plots may be produced earlier, but they do not count as accepted paper figures.

## Figure Style Requirements

All canonical paper figures must satisfy:

- Times New Roman
- white background only
- minimal color, at most 2-3 functional colors unless grayscale is clearer
- no gradients, shadows, icons, or infographic styling
- natural-language axis labels, never internal variable names
- one figure = one sentence-level claim
- readable at a glance in under 10 seconds

## Required Main Figures (Legacy Checklist)

1. Metric-vs-claim mismatch figure
2. Claim-family / cross-family verdict distribution
3. Scope robustness / protocol sensitivity
4. Cost / configuration tradeoff

## Required Main Tables

1. Mismatch summary table
2. Baseline capability matrix
3. Exact witness examples
4. Cost summary / policy table

## Outputs

- final figure list
- final table list
- main-vs-appendix placement note
- generation commands for all final visuals

## Acceptance Criteria

- [ ] The main-paper figure set is explicitly frozen as `Fig 1` through `Fig 4`, with `Fig 5` only if space clearly permits.
- [ ] Every figure-producing task states when the canonical paper figure is generated.
- [ ] Every main figure is backed by a frozen dataset and a supporting table.
- [ ] Every main figure supports a single sentence-level claim.
- [ ] No debug-style or exploratory plots remain in the main paper list.
- [ ] Typography, legend behavior, and export format are consistent.
- [ ] All main figures export cleanly to both PNG and PDF.

## Dependencies

- [02_E1_METRIC_VS_CLAIM.md](./02_E1_METRIC_VS_CLAIM.md)
- [03_E2_BASELINE_COMPARISON.md](./03_E2_BASELINE_COMPARISON.md)
- [04_E3_SCOPE_ROBUSTNESS.md](./04_E3_SCOPE_ROBUSTNESS.md)
- [05_E4_EXACT_MOS.md](./05_E4_EXACT_MOS.md)
- [06_E5_CROSS_FAMILY.md](./06_E5_CROSS_FAMILY.md)
- [07_E6_REAL_HARDWARE.md](./07_E6_REAL_HARDWARE.md)
- [12_RQ4_PRACTICALITY.md](./12_RQ4_PRACTICALITY.md)

## Status

- [ ] Not started
- [ ] In progress
- [ ] Done

## Notes

The mismatch figure is the killer figure. Optimize everything around it.
