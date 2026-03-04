# Claims

ClaimStab supports claim-centric evaluation. The primary target is ranking claims, with additional decision/distribution examples for generality.

## Claim Types
- **Ranking claim**: \(m(Y(x_a)) \ge m(Y(x_b)) + \delta\)
- **Threshold claim**: method performance exceeds a fixed threshold.
- **Decision claim**: output belongs to an algorithmically defined acceptable set.
- **Distribution claim**: distance between observed and reference distributions is bounded by \(\varepsilon\).

## Stability Decision Rule
Stability is estimated from sampled perturbations, not full enumeration.

Let \(\hat{s}\) be estimated stability and \([L,U]\) its confidence interval:
- `stable` if \(L \ge p\)
- `unstable` if \(U < p\)
- `inconclusive` otherwise

This is conservative by construction and prevents overclaiming with small samples.

## Why Delta (\(\delta\)) Matters
For ranking claims, \(\delta\) is a practical effect-size margin, not a tuning trick:
- \(\delta=0\): strict ranking with no margin.
- higher \(\delta\): requires larger practical separation.

For structural metrics (for example circuit depth, two-qubit count), set `higher_is_better: false` so ranking semantics remain correct.

Near-ties are common sources of flip behavior. Delta sweeps expose this directly.

## Sampling + CI Are Mandatory
Perturbation spaces are typically too large for exhaustive runs on all instances. ClaimStab uses:
- full-factorial calibration on small setups,
- random-k sampling on larger suites,
- CI-based uncertainty reporting for every claim decision.
