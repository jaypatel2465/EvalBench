from app.schemas.domain import GatePolicy
from app.services.regression import detect_regression, quality_gate, reliability_metrics


def test_bootstrap_detects_large_regression():
    baseline = [1.0] * 95 + [0.0] * 5
    current = [1.0] * 70 + [0.0] * 30
    result = detect_regression(baseline, current, threshold=.05)
    assert result.classification == "regression_detected"
    assert result.absolute_change == -.25
    assert result.ci_high is not None and result.ci_high < 0


def test_small_sample_is_not_overstated():
    result = detect_regression([1, 1, 1], [1, 1, 0], threshold=.05)
    assert result.classification in {"possible_regression", "inconclusive"}


def test_quality_gate_checks_quality_latency_and_cost():
    decision = quality_gate({"pass_rate": .95, "p95_latency_ms": 100, "cost_per_request": .01},
        {"pass_rate": .87, "p95_latency_ms": 130, "cost_per_request": .013}, GatePolicy())
    assert decision.decision == "failed"
    assert len(decision.reasons) == 3


def test_judge_reliability_metrics_include_kappa_and_bias():
    metrics = reliability_metrics([5, 4, 3, 2, 1], [5, 4, 4, 2, 1])
    assert metrics["exact_agreement"] == .8
    assert metrics["mean_absolute_error"] == .2
    assert "cohens_kappa" in metrics and "confusion_matrix" in metrics

