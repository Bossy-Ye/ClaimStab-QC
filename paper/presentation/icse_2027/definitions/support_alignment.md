# Support Alignment

`support_alignment` is a derived comparison quantity used in the `RQ1`
paper-facing dataset.

It asks whether:
- the metric baseline support polarity, and
- the claim-level validation support polarity

agree at a coarse binary level.

## Binary mapping

For this alignment calculation:
- metric support is positive iff `metric_verdict = positive`
- claim support is positive iff `claim_validation_outcome = validated`

So:
- `validated` = supportive
- `refuted`, `unstable`, and `inconclusive` = non-supportive

## Why this is only a helper quantity

`support_alignment_rate` is useful as a compact descriptive summary.
It is not the main scientific quantity of interest.

The main `RQ1` signal is still:
- false reassurance
- structured mismatch
- the discrepancy matrix

Use this quantity as a supplement, not as the core claim.
