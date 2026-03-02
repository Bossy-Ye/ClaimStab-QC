from __future__ import annotations

from dataclasses import dataclass
from math import log2, sqrt
from typing import Callable, Mapping


Distribution = dict[str, float]


@dataclass(frozen=True)
class DistributionClaimResult:
    epsilon: float
    primary_distance: str
    primary_value: float
    primary_holds: bool
    sanity_distance: str
    sanity_value: float
    sanity_holds: bool
    distances_agree: bool



def normalize_counts(counts: Mapping[str, int]) -> Distribution:
    total = sum(int(v) for v in counts.values())
    if total <= 0:
        raise ValueError("counts total must be > 0")
    return {str(k): float(v) / float(total) for k, v in counts.items()}



def _union_support(p: Mapping[str, float], q: Mapping[str, float]) -> list[str]:
    return sorted(set(p.keys()) | set(q.keys()))



def tvd_distance(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    keys = _union_support(p, q)
    return 0.5 * sum(abs(float(p.get(k, 0.0)) - float(q.get(k, 0.0))) for k in keys)



def _kl_divergence(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    eps = 1e-12
    val = 0.0
    for k in _union_support(p, q):
        pk = float(p.get(k, 0.0))
        qk = float(q.get(k, 0.0))
        if pk <= 0.0:
            continue
        val += pk * log2(pk / max(qk, eps))
    return val



def js_distance(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    m: Distribution = {}
    for k in _union_support(p, q):
        m[k] = 0.5 * float(p.get(k, 0.0)) + 0.5 * float(q.get(k, 0.0))
    js_div = 0.5 * _kl_divergence(p, m) + 0.5 * _kl_divergence(q, m)
    return sqrt(max(js_div, 0.0))



def get_distance_fn(name: str) -> Callable[[Mapping[str, float], Mapping[str, float]], float]:
    key = name.lower()
    if key == "tvd":
        return tvd_distance
    if key == "js":
        return js_distance
    raise ValueError(f"Unsupported distance '{name}'. Use one of: tvd, js")



def evaluate_distribution_claim(
    observed_counts: Mapping[str, int],
    reference_counts: Mapping[str, int],
    *,
    epsilon: float,
    primary_distance: str = "tvd",
    sanity_distance: str = "js",
) -> DistributionClaimResult:
    if epsilon < 0.0:
        raise ValueError(f"epsilon must be >= 0, got {epsilon}")

    p = normalize_counts(observed_counts)
    q = normalize_counts(reference_counts)

    primary_fn = get_distance_fn(primary_distance)
    sanity_fn = get_distance_fn(sanity_distance)

    primary_value = float(primary_fn(p, q))
    sanity_value = float(sanity_fn(p, q))

    primary_holds = primary_value <= epsilon
    sanity_holds = sanity_value <= epsilon

    return DistributionClaimResult(
        epsilon=epsilon,
        primary_distance=primary_distance,
        primary_value=primary_value,
        primary_holds=primary_holds,
        sanity_distance=sanity_distance,
        sanity_value=sanity_value,
        sanity_holds=sanity_holds,
        distances_agree=(primary_holds == sanity_holds),
    )
