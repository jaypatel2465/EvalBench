from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.entities import DatasetVersion, EvaluationResult, EvaluationRun, Failure, JudgeEvaluation, ModelConfiguration, Score, TestCaseRecord
from app.schemas.domain import DatasetDocument, GenerationRequest, GenerationResult, TestCase
from app.services.datasets.manager import dataset_checksum, validate_unique_ids
from app.services.providers.base import ModelProvider, ProviderError
from app.services.scoring import RUBRIC_VERSION, classify_failures, judge_case, score_case

logger = logging.getLogger(__name__)


def ensure_dataset(session: Session, document: DatasetDocument) -> DatasetVersion:
    validate_unique_ids(document.cases)
    checksum = dataset_checksum(document)
    existing = session.scalar(select(DatasetVersion).where(DatasetVersion.checksum == checksum))
    if existing:
        return existing
    row = DatasetVersion(name=document.metadata.name, version=document.metadata.version, checksum=checksum,
        description=document.metadata.description, metadata_json=document.metadata.model_dump(mode="json"))
    session.add(row)
    session.flush()
    for case in document.cases:
        session.add(TestCaseRecord(dataset_id=row.id, external_id=case.id, category=case.category.value, payload=case.model_dump(mode="json")))
    session.commit()
    session.refresh(row)
    return row


def ensure_model_config(session: Session, name: str, provider: ModelProvider, snapshot: dict[str, Any]) -> ModelConfiguration:
    row = session.scalar(select(ModelConfiguration).where(ModelConfiguration.name == name))
    if row:
        return row
    row = ModelConfiguration(name=name, provider=provider.name, model=provider.model, parameters=snapshot.get("parameters", {}),
        pricing=snapshot.get("pricing", {}), is_mock=provider.is_mock)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


class EvaluationRunner:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.cancel_event = asyncio.Event()

    async def execute(self, *, run: EvaluationRun, dataset: DatasetDocument,
                      providers: dict[str, tuple[ModelProvider, dict[str, Any]]],
                      judge_provider: ModelProvider | None = None) -> EvaluationRun:
        semaphore = asyncio.Semaphore(self.settings.eval_concurrency)
        cases_by_id = {row.external_id: row for row in self.session.scalars(select(TestCaseRecord).where(TestCaseRecord.dataset_id == run.dataset_id)).all()}
        configs = {name: ensure_model_config(self.session, name, provider, snapshot) for name, (provider, snapshot) in providers.items()}
        run.status = "running"
        self.session.commit()
        existing = {(row.test_case_id, row.model_config_id): row for row in self.session.scalars(select(EvaluationResult).where(EvaluationResult.run_id == run.id)).all()}
        tasks = []
        for case in dataset.cases:
            for name, (provider, _) in providers.items():
                key = (cases_by_id[case.id].id, configs[name].id)
                if key in existing and existing[key].status in {"passed", "failed"}:
                    continue
                row = existing.get(key) or EvaluationResult(run_id=run.id, test_case_id=key[0], model_config_id=key[1], status="pending")
                if row.id is None:
                    self.session.add(row)
                    self.session.commit()
                tasks.append(self._evaluate(semaphore, row, case, provider, judge_provider))
        if tasks:
            await asyncio.gather(*tasks)
        run.status = "cancelled" if self.cancel_event.is_set() else "completed"
        run.completed_at = datetime.now(UTC)
        self.session.commit()
        return run

    async def _evaluate(self, semaphore: asyncio.Semaphore, row: EvaluationResult, case: TestCase,
                        provider: ModelProvider, judge_provider: ModelProvider | None) -> None:
        if self.cancel_event.is_set():
            return
        async with semaphore:
            row.status = "running"
            self.session.commit()
            request = GenerationRequest(prompt=case.input, metadata={"case_id": case.id, "category": case.category.value,
                "required_facts": case.required_facts, "expected_citations": case.expected_citations, "reference_answer": case.reference_answer})
            generated: GenerationResult | None = None
            error: dict[str, Any] | None = None
            for attempt in range(self.settings.eval_retries + 1):
                try:
                    generated = await asyncio.wait_for(provider.generate(request), timeout=self.settings.eval_timeout)
                    break
                except TimeoutError:
                    error = {"type": "timeout", "message": f"Timed out after {self.settings.eval_timeout}s", "attempt": attempt + 1}
                    retryable = True
                except ProviderError as exc:
                    error = {"type": "provider_error", "message": str(exc), "status_code": exc.status_code, "attempt": attempt + 1}
                    retryable = exc.retryable
                except Exception as exc:
                    error = {"type": "unexpected_error", "message": f"{type(exc).__name__}: {exc}", "attempt": attempt + 1}
                    retryable = False
                if not retryable or attempt >= self.settings.eval_retries:
                    break
                await asyncio.sleep(min(8, .25 * 2**attempt))
            if generated is None:
                row.status = "timeout" if error and error["type"] == "timeout" else "error"
                row.error = error
                failures = classify_failures(case, [], error)
            else:
                scores = score_case(case, generated)
                failures = classify_failures(case, scores)
                row.status = "passed" if not failures else "failed"
                row.response, row.citations = generated.response, generated.citations
                row.latency_ms, row.input_tokens, row.output_tokens = generated.latency_ms, generated.input_tokens, generated.output_tokens
                row.total_tokens, row.estimated_cost = generated.total_tokens, generated.estimated_cost
                row.trace = {"run_id": row.run_id, "test_case_id": case.id, "model": generated.model,
                    "request": request.model_dump(mode="json", exclude={"metadata"}), "retrieval": generated.trace.get("retrieval", {}),
                    "response": generated.response, "citations": generated.citations, "timings": {"latency_ms": generated.latency_ms},
                    "cost": {"estimated_cost": generated.estimated_cost, "is_estimate": generated.cost_is_estimate},
                    "provider_trace": generated.trace, "errors": []}
                for item in scores:
                    self.session.add(Score(result_id=row.id, scorer=item.scorer, value=item.value, passed=item.passed, reason=item.reason, details=item.details))
                if judge_provider:
                    try:
                        judged = await judge_case(case, generated, judge_provider)
                        self.session.add(JudgeEvaluation(result_id=row.id, judge_provider=judge_provider.name,
                            judge_model=judge_provider.model, score=float(judged.score),
                            dimension_scores={key: float(value) for key, value in judged.dimension_scores.items()},
                            reason=judged.reason, rubric_version=RUBRIC_VERSION))
                    except Exception as exc:
                        row.trace["errors"].append({"type": "judge_error", "message": f"{type(exc).__name__}: {exc}"})
            for failure in failures:
                self.session.add(Failure(result_id=row.id, **failure))
            self.session.commit()
            logger.info("evaluation completed", extra={"run_id": row.run_id, "test_case_id": case.id, "provider": provider.name,
                "model": provider.model, "latency_ms": row.latency_ms, "error_state": row.status if row.status in {"error", "timeout"} else None})
