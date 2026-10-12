from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any

from app.schemas.domain import GateDecision, GatePolicy, RegressionResult


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def bootstrap_difference(baseline: list[float], current: list[float], iterations: int = 2000, seed: int = 17) -> tuple[float | None, float | None]:
    if len(baseline) < 2 or len(current) < 2:
        return None, None
    rng = random.Random(seed)
    diffs = []
    for _ in range(iterations):
        base_mean = sum(rng.choice(baseline) for _ in baseline) / len(baseline)
        current_mean = sum(rng.choice(current) for _ in current) / len(current)
        diffs.append(current_mean - base_mean)
    return percentile(diffs, 0.025), percentile(diffs, 0.975)


def detect_regression(baseline: list[float], current: list[float], threshold: float = 0.05, metric: str = "pass_rate") -> RegressionResult:
    if not baseline or not current:
        raise ValueError("baseline and current samples cannot be empty")
    base, curr = sum(baseline) / len(baseline), sum(current) / len(current)
    delta = curr - base
    relative = delta / base if base else None
    low, high = bootstrap_difference(baseline, current)
    if delta > threshold and low is not None and low > 0:
        classification = "improvement"
    elif delta <= -threshold and high is not None and high < 0:
        classification = "regression_detected"
    elif delta <= -threshold:
        classification = "possible_regression"
    elif low is not None and low <= 0 <= high:
        classification = "inconclusive"
    else:
        classification = "no_material_change"
    return RegressionResult(metric=metric, baseline=base, current=curr, absolute_change=delta, relative_change=relative,
        ci_low=low, ci_high=high, classification=classification, samples=min(len(baseline), len(current)))


def quality_gate(baseline: dict[str, float], current: dict[str, float], policy: GatePolicy) -> GateDecision:
    failures, warnings = [], []
    pass_drop = baseline.get("pass_rate", 0) - current.get("pass_rate", 0)
    if pass_drop >= policy.pass_rate_drop:
        failures.append(f"Pass rate dropped {pass_drop:.1%} (limit {policy.pass_rate_drop:.1%})")
    for metric, limit, label in (("p95_latency_ms", policy.p95_latency_increase, "P95 latency"), ("cost_per_request", policy.cost_increase, "Cost/request")):
        old, new = baseline.get(metric), current.get(metric)
        if old is not None and new is not None and old > 0:
            change = (new - old) / old
            if change >= limit:
                failures.append(f"{label} increased {change:.1%} (limit {limit:.1%})")
    decision = "failed" if failures else "warned" if warnings else "passed"
    return GateDecision(decision=decision, reasons=failures + warnings or ["All configured quality gates passed"], metrics={"baseline": baseline, "current": current})


def reliability_metrics(human: list[int], judge: list[int]) -> dict[str, Any]:
    if len(human) != len(judge) or not human:
        raise ValueError("human and judge ratings must be equal-length and non-empty")
    n = len(human)
    exact = sum(a == b for a, b in zip(human, judge, strict=True)) / n
    mae = sum(abs(a - b) for a, b in zip(human, judge, strict=True)) / n
    human_counts, judge_counts = Counter(human), Counter(judge)
    expected = sum((human_counts[k] / n) * (judge_counts[k] / n) for k in set(human_counts) | set(judge_counts))
    kappa = (exact - expected) / (1 - expected) if expected < 1 else 1.0
    mean_h, mean_j = sum(human) / n, sum(judge) / n
    covariance = sum((a - mean_h) * (b - mean_j) for a, b in zip(human, judge, strict=True))
    variance = math.sqrt(sum((a - mean_h) ** 2 for a in human) * sum((b - mean_j) ** 2 for b in judge))
    confusion = {str(h): {str(j): sum(a == h and b == j for a, b in zip(human, judge, strict=True)) for j in range(1, 6)} for h in range(1, 6)}
    return {"samples": n, "exact_agreement": exact, "disagreement_rate": 1 - exact, "mean_absolute_error": mae,
        "pearson_correlation": covariance / variance if variance else None, "cohens_kappa": kappa,
        "mean_bias": mean_j - mean_h, "confusion_matrix": confusion, "insufficient_sample": n < 30}

