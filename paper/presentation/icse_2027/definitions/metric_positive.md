# Metric-Positive

`metric-positive` is a paper-facing term used only for the frozen comparative
baseline in `RQ1`.

It does **not** mean:
- “the claim is true”
- “the method is definitively better”
- “ClaimStab agrees”

It means only:
- the metric baseline supports the comparative outcome under its own summary rule

## Operational rule

For a claim comparing `A` and `B`, define a configuration-level margin.

If higher is better:
- `margin = score(A) - score(B)`

If lower is better:
- `margin = score(B) - score(A)`

Then:
1. average that margin across instances within each configuration,
2. compute the overall mean across configurations,
3. compute a standard 95% confidence interval on the mean,
4. mark the variant `metric-positive` iff:
   - mean margin > 0, and
   - lower CI bound > 0

## Scope

This term is currently defined only for:
- comparative / ranking claims
- one frozen metric baseline

It should not be reused casually for decision or distribution claims.
