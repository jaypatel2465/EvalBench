from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.db.base import get_db
from app.models.entities import DatasetVersion, EvaluationResult, EvaluationRun, Failure, JudgeEvaluation, ModelConfiguration, Regression
from app.schemas.domain import RunCreate
from app.services.datasets import load_dataset
from app.services.evaluation import EvaluationRunner, ensure_dataset, run_metrics, run_samples
from app.services.providers import build_provider
from app.services.regression import detect_regression, reliability_metrics

router = APIRouter(prefix="/api")


def _load_model_configs(path: Path = Path("configs/models.yaml")) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise HTTPException(503, f"model configuration not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {item["name"]: item for item in data.get("models", [])}


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


@router.post("/runs", status_code=201)
async def create_run(payload: RunCreate, session: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        dataset = load_dataset(payload.dataset_path)
        dataset_row = ensure_dataset(session, dataset)
        available = _load_model_configs()
        selected_names = [*payload.models, *([payload.judge_model] if payload.judge_model else [])]
        missing = sorted(set(selected_names) - available.keys())
        if missing:
            raise HTTPException(422, f"unknown model configurations: {', '.join(missing)}")
        providers = {name: (build_provider(available[name]), available[name]) for name in payload.models}
        judge_provider = build_provider(available[payload.judge_model]) if payload.judge_model else None
        snapshot = {name: available[name] for name in payload.models}
        if payload.judge_model:
            snapshot["judge"] = available[payload.judge_model]
        run = EvaluationRun(name=payload.name, dataset_id=dataset_row.id, git_sha=payload.git_sha,
            baseline_run_id=payload.baseline_run_id, configuration_snapshot=snapshot,
            is_mock=all(provider.is_mock for provider, _ in providers.values()))
        session.add(run)
        session.commit()
        session.refresh(run)
        await EvaluationRunner(session).execute(run=run, dataset=dataset, providers=providers, judge_provider=judge_provider)
        return {"run_id": run.id, "status": run.status, "metrics": run_metrics(session, run.id)}
    except HTTPException:
        raise
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/runs")
def list_runs(limit: int = Query(50, ge=1, le=200), session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    runs = session.scalars(select(EvaluationRun).order_by(desc(EvaluationRun.created_at)).limit(limit)).all()
    return [{"id": row.id, "name": row.name, "status": row.status, "git_sha": row.git_sha, "is_mock": row.is_mock,
        "dataset_version": row.dataset.version, "created_at": row.created_at, "completed_at": row.completed_at,
        "metrics": run_metrics(session, row.id)} for row in runs]


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_db)) -> dict[str, Any]:
    row = session.get(EvaluationRun, run_id)
    if not row:
        raise HTTPException(404, "run not found")
    return {"id": row.id, "name": row.name, "status": row.status, "git_sha": row.git_sha, "is_mock": row.is_mock,
        "dataset": {"name": row.dataset.name, "version": row.dataset.version, "checksum": row.dataset.checksum},
        "configuration_snapshot": row.configuration_snapshot, "baseline_run_id": row.baseline_run_id,
        "created_at": row.created_at, "completed_at": row.completed_at, "metrics": run_metrics(session, row.id)}


@router.get("/runs/{run_id}/metrics")
def get_metrics(run_id: str, session: Session = Depends(get_db)) -> dict[str, Any]:
    if not session.get(EvaluationRun, run_id):
        raise HTTPException(404, "run not found")
    return run_metrics(session, run_id)


@router.get("/runs/{run_id}/failures")
def get_failures(run_id: str, category: str | None = None, severity: str | None = None,
                 search: str | None = None, session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    statement = select(Failure).join(EvaluationResult).where(EvaluationResult.run_id == run_id).options(
        selectinload(Failure.result).selectinload(EvaluationResult.test_case),
        selectinload(Failure.result).selectinload(EvaluationResult.model_config),
        selectinload(Failure.result).selectinload(EvaluationResult.scores))
    if category:
        statement = statement.where(Failure.category == category)
    if severity:
        statement = statement.where(Failure.severity == severity)
    rows = session.scalars(statement).all()
    output = []
    for row in rows:
        case = row.result.test_case.payload
        if search and search.lower() not in (case["input"] + " " + (row.result.response or "")).lower():
            continue
        output.append({"id": row.id, "result_id": row.result_id, "category": row.category, "severity": row.severity,
            "reason": row.reason, "evidence": row.evidence, "test_case_id": row.result.test_case.external_id,
            "model": row.result.model_config.name, "input": case["input"], "expected_behavior": case["expected_behavior"],
            "reference_answer": case.get("reference_answer", ""), "response": row.result.response,
            "citations": row.result.citations, "trace": row.result.trace, "latency_ms": row.result.latency_ms,
            "total_tokens": row.result.total_tokens, "estimated_cost": row.result.estimated_cost,
            "scores": [{"scorer": score.scorer, "value": score.value, "passed": score.passed, "reason": score.reason} for score in row.result.scores]})
    return output


@router.get("/models")
def list_models(session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    configured = _load_model_configs()
    persisted = {row.name: row for row in session.scalars(select(ModelConfiguration)).all()}
    settings = get_settings()
    key_status = {"openai": bool(settings.openai_api_key), "anthropic": bool(settings.anthropic_api_key),
        "google": bool(settings.google_api_key), "ollama": True, "mock": True, "target_api": True}
    return [{**config, "configured": key_status.get(config["provider"], False), "used_in_runs": name in persisted,
        "mode": "Mock Provider / Offline Demo" if config["provider"] == "mock" else "production"} for name, config in configured.items()]


@router.get("/datasets")
def list_datasets(session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = session.scalars(select(DatasetVersion).order_by(desc(DatasetVersion.created_at))).all()
    return [{"id": row.id, "name": row.name, "version": row.version, "checksum": row.checksum,
        "description": row.description, "case_count": len(row.cases), "created_at": row.created_at} for row in rows]


@router.get("/regressions")
def regressions(current_run_id: str | None = None, baseline_run_id: str | None = None,
                session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    if current_run_id and baseline_run_id:
        result = detect_regression(run_samples(session, baseline_run_id), run_samples(session, current_run_id))
        return [result.model_dump()]
    rows = session.scalars(select(Regression).order_by(desc(Regression.id)).limit(100)).all()
    return [{column.name: getattr(row, column.name) for column in row.__table__.columns} for row in rows]


@router.get("/comparisons")
def comparisons(run_ids: list[str] = Query(default=[]), session: Session = Depends(get_db)) -> dict[str, Any]:
    if not run_ids:
        run_ids = list(session.scalars(select(EvaluationRun.id).order_by(desc(EvaluationRun.created_at)).limit(5)).all())
    return {"runs": [{"run": get_run(run_id, session), "metrics": run_metrics(session, run_id)} for run_id in run_ids]}


@router.get("/judge-reliability")
def judge_reliability(session: Session = Depends(get_db)) -> dict[str, Any]:
    rows = session.scalars(select(JudgeEvaluation).where(JudgeEvaluation.human_rating.is_not(None))).all()
    if not rows:
        return {"samples": 0, "status": "insufficient_data", "limitations": "Add human ratings to the validation subset before interpreting judge reliability."}
    metrics = reliability_metrics([round(row.human_rating or 0) for row in rows], [round(row.score) for row in rows])
    disagreements = [{"result_id": row.result_id, "human": row.human_rating, "judge": row.score, "reason": row.reason}
        for row in rows if round(row.human_rating or 0) != round(row.score)]
    return {**metrics, "disagreements": disagreements[:30], "limitations": "Agreement measures consistency with this labeled subset, not correctness or general validity."}
