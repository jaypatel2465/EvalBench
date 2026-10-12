from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import yaml

from app.db.base import SessionLocal, create_schema
from app.models.entities import EvaluationRun
from app.services.datasets import load_dataset
from app.services.evaluation import EvaluationRunner, ensure_dataset, run_metrics
from app.services.providers import build_provider
from scripts.build_demo_assets import build


async def seed() -> dict:
    build()
    create_schema()
    document = load_dataset("datasets/golden_v1.json")
    configs = {item["name"]: item for item in yaml.safe_load(Path("configs/models.yaml").read_text(encoding="utf-8"))["models"]}
    output = {}
    with SessionLocal() as session:
        dataset = ensure_dataset(session, document)
        for name, label, baseline_id in (("mock-baseline", "Demo baseline", None), ("mock-degraded", "Known prompt regression", "baseline")):
            config = configs[name]
            provider = build_provider(config)
            run = EvaluationRun(name=label, dataset_id=dataset.id, configuration_snapshot={name: config}, is_mock=True,
                baseline_run_id=output.get("baseline", {}).get("run_id") if baseline_id else None)
            session.add(run); session.commit()
            await EvaluationRunner(session).execute(run=run, dataset=document, providers={name: (provider, config)})
            key = "baseline" if name == "mock-baseline" else "current"
            output[key] = {"run_id": run.id, "metrics": run_metrics(session, run.id)}
    Path("examples").mkdir(exist_ok=True)
    Path("examples/demo_runs.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute real offline demo evaluations and persist their computed metrics.")
    parser.parse_args()
    result = asyncio.run(seed())
    print(json.dumps(result, indent=2))

