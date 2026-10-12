from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import EvaluationResult, EvaluationRun
from app.services.regression.statistics import percentile


def run_metrics(session: Session, run_id: str) -> dict[str, Any]:
    results = session.scalars(select(EvaluationResult).where(EvaluationResult.run_id == run_id).options(selectinload(EvaluationResult.scores), selectinload(EvaluationResult.failures))).all()
    total = len(results)
    completed = [result for result in results if result.status in {"passed", "failed"}]
    passed = sum(result.status == "passed" for result in results)
    latencies = [result.latency_ms for result in completed if result.latency_ms is not None]
    costs = [result.estimated_cost for result in completed if result.estimated_cost is not None]
    tokens = [result.total_tokens for result in completed if result.total_tokens is not None]
    score_values = [score.value for result in completed for score in result.scores]
    failures = Counter(failure.category for result in results for failure in result.failures)
    by_model: dict[str, list[EvaluationResult]] = defaultdict(list)
    for result in results:
        by_model[result.model_config.name].append(result)
    models = {}
    for name, items in by_model.items():
        item_latency = [item.latency_ms for item in items if item.latency_ms is not None]
        item_cost = [item.estimated_cost for item in items if item.estimated_cost is not None]
        models[name] = {"evaluations": len(items), "pass_rate": sum(item.status == "passed" for item in items) / len(items),
            "p95_latency_ms": percentile(item_latency, .95), "cost_per_request": sum(item_cost) / len(item_cost) if item_cost else None}
    return {"total_evaluations": total, "completed": len(completed), "pass_rate": passed / len(completed) if completed else 0,
        "failure_rate": 1 - passed / len(completed) if completed else 0, "quality_score": sum(score_values) / len(score_values) if score_values else 0,
        "average_latency_ms": sum(latencies) / len(latencies) if latencies else None, "p50_latency_ms": percentile(latencies, .5),
        "p95_latency_ms": percentile(latencies, .95), "p99_latency_ms": percentile(latencies, .99) if len(latencies) >= 20 else None,
        "cost_per_request": sum(costs) / len(costs) if costs else None, "cost_per_1k": 1000 * sum(costs) / len(costs) if costs else None,
        "total_tokens": sum(tokens) if tokens else None, "error_count": sum(result.status in {"error", "timeout"} for result in results),
        "failures_by_category": dict(failures), "models": models}


def run_samples(session: Session, run_id: str) -> list[float]:
    statuses = session.scalars(select(EvaluationResult.status).where(EvaluationResult.run_id == run_id, EvaluationResult.status.in_(["passed", "failed"]))).all()
    return [1.0 if status == "passed" else 0.0 for status in statuses]

