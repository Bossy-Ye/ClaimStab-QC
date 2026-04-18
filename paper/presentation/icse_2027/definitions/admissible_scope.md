# Admissible Scope

`Admissible scope` is the declared set of operational variations under which a
reported claim is expected to preserve its meaning.

This term is central to the methodology.

## What it includes

Examples of admissible perturbation dimensions include:
- transpiler randomness
- optimization level
- layout strategy
- shot budget
- simulator seed
- selected backend-conditioned execution settings

## What it does not mean

An admissible scope is not:
- every possible experimental change
- a hidden nuisance range
- a post hoc excuse for any verdict

It is a declared validation object that must remain visible and interpretable.

## Paper-facing caution

The paper should not claim that admissibility is fully automated or uniquely
determined. The strongest defensible position is:

- admissibility is made explicit,
- structured,
- reviewable,
- and analyzable for robustness

This is why scope robustness appears as a methodological result rather than an
implementation detail.
