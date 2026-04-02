# W4 Admissibility Inputs

`admissibility_items_v1.csv` is the paper-facing checklist for the W4 admissibility study.
It uses:

- `expected_label` for author-side reference annotations
- `trigger_rule` to record which Q1/Q2/Q3 rule motivates a borderline or non-admissible judgment

The `ratings/` directory is intentionally left empty in version control.
For submission-facing results, collect real independent ratings there as:

- `rater_1.csv`
- `rater_2.csv`
- `rater_3.csv`

Each rating file should contain:

```csv
item_id,label
P01,admissible
P02,non_admissible
```

Do not commit simulated labels as empirical evidence.
When fewer than two real rater files are present, the W4 summarizer reports `pending_human_labels` instead of a kappa value.

In paper text, describe these as `reference labels` or `author-side reference annotations`, not as ground truth.
