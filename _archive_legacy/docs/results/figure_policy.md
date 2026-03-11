# Figure Policy (Reusable)

This policy governs result-figure selection for ClaimStab paper and artifact outputs.

## Chart Selection Rules

1. Use **bar charts** only when there are at least three informative categories and visible spread.
2. Use **heatmaps** only when the matrix has real 2D structure and non-trivial variation.
3. Use **dot/lollipop plots** for ranking, sparse category counts, and 1xN/Nx1 matrix projections.
4. Use **compact table/stat-card figures** for single-value, near-constant, or single-category outputs.
5. Use **composite multi-panel figures** when readers must compare the same signal across multiple spaces.
6. If a figure does not reveal a pattern at a glance, move it to **appendix/text summary**.

## Color and Scale Rules

1. Use restrained, academic palettes (muted grayscale + dark accent).
2. Avoid decorative color variation with no analytic value.
3. For bounded [0,1] quantities, use either:
   - full-scale `0..1` when spread is large, or
   - adaptive local bounds when spread is narrow but still meaningful.
4. If a bounded matrix is effectively constant, replace the heatmap with table/strip view.

## Annotation Rules

1. Keep labels short and direct.
2. Annotate values only when they add comparison value.
3. Avoid dense decorative text.
4. Prefer confidence intervals and ranked contrasts over raw decorative markers.

## Paper Placement Rules

1. Main paper: figures that show methodological signal (contrast, uncertainty, interaction, tradeoff).
2. Appendix: control-track or low-variance visuals retained for completeness.
3. Suppress redundant visuals and replace with concise textual summary when needed.
