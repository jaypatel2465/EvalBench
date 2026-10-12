import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.models.entities import EvaluationResult, EvaluationRun
from app.services.datasets import load_dataset
from app.services.evaluation import EvaluationRunner, ensure_dataset, run_metrics
from app.services.providers.mock import OfflineMockProvider


@pytest.mark.asyncio
async def test_runner_persists_partial_work_and_real_metrics(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    document = load_dataset("datasets/golden_v1.json")
    document.cases = document.cases[:3]
    with Session(engine, expire_on_commit=False) as session:
        dataset = ensure_dataset(session, document)
        run = EvaluationRun(name="test", dataset_id=dataset.id, configuration_snapshot={}, is_mock=True)
        session.add(run); session.commit()
        settings = Settings(database_url="sqlite://", eval_concurrency=2, eval_timeout=1, eval_retries=0)
        await EvaluationRunner(session, settings).execute(run=run, dataset=document,
            providers={"mock-test": (OfflineMockProvider(latency_ms=0), {"parameters": {}})})
        results = session.scalars(select(EvaluationResult).where(EvaluationResult.run_id == run.id)).all()
        assert len(results) == 3
        assert all(result.trace["run_id"] == run.id for result in results)
        assert run_metrics(session, run.id)["total_evaluations"] == 3

