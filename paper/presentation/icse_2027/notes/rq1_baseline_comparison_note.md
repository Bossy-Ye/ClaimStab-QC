# RQ1 Baseline Comparison Note

This note summarizes the baseline-comparison asset set for `RQ1`.

Core result:
- the comparison reuses the same `63` comparative claim variants as `02`
- all baselines are evaluated on the same claim-level analysis units

Headline disagreement rates:
- `Metric mean + CI`: `14/27 = 51.9%`
- `Local sensitivity check`: `12/25 = 48.0%`
- `Majority support ratio`: `9/22 = 40.9%`
- `Single baseline (realistic)`: `5/18 = 27.8%`
- `ClaimStab-QC`: `0/13 = 0.0%`

Reading rule:
- a baseline is counted as failing when it is `supportive` but the corresponding claim-validation outcome is not `validated`
- lower false-reassurance rates for narrower heuristics do not mean claim validation has been replaced
- `ClaimStab-QC` remains the only method in this comparison that directly validates claims and supports conservative abstention

Recommended paper use:
- cite `Fig 2` for the disagreement comparison
- cite `Tab 2` for capability dimensions
- cite the detailed disagreement summary in appendix or artifact text
