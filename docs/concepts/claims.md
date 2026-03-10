# Claims

ClaimStab supports claim-centric evaluation with schema-defined claim types.
The canonical source of truth is:
`claimstab/spec/schema_v1.json`.

## Claim Types

Schema v1 supports exactly:

- **Ranking claim** (`type: ranking`): compare method A vs method B with margin `delta` and explicit metric direction.
- **Decision claim** (`type: decision`): check whether a target label remains in `top_k`.
- **Distribution claim** (`type: distribution`): check whether distribution distance to reference is within `epsilon` (for example JS/TVD).

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

## Clarification: Threshold Is a Decision Rule Parameter, Not a Claim Type

`decision_rule.threshold` is the stability acceptance threshold used after CI estimation.
It does not define a separate claim taxonomy entry in schema v1.

## Sampling + CI Are Mandatory
Perturbation spaces are typically too large for exhaustive runs on all instances. ClaimStab uses:
- full-factorial calibration on small setups,
- random-k sampling on larger suites,
- CI-based uncertainty reporting for every claim decision.
