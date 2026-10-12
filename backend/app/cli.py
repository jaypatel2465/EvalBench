from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Annotated

import typer
import yaml
from sqlalchemy import desc, select

from app.db.base import SessionLocal, create_schema
from app.models.entities import EvaluationRun
from app.services.datasets import dataset_stats, diff_datasets, load_dataset
from app.services.evaluation import EvaluationRunner, ensure_dataset, run_metrics, run_samples
from app.services.providers import build_provider
from app.services.regression import detect_regression

app = typer.Typer(help="EvalBench — LLM product regression and quality intelligence.", no_args_is_help=True)
dataset_app = typer.Typer(help="Validate, inspect, and compare versioned golden datasets.")
app.add_typer(dataset_app, name="dataset")


@app.command()
def init() -> None:
    """Initialize the configured database schema."""
    create_schema()
    typer.echo("EvalBench database initialized.")


@dataset_app.command("validate")
def dataset_validate(path: Path = typer.Argument(Path("datasets/golden_v1.json"))) -> None:
    document = load_dataset(path)
    typer.echo(f"Valid: {document.metadata.name} {document.metadata.version} ({len(document.cases)} cases)")


@dataset_app.command("stats")
def stats(path: Path = typer.Argument(Path("datasets/golden_v1.json"))) -> None:
    typer.echo(json.dumps(dataset_stats(load_dataset(path)), indent=2))


@dataset_app.command("diff")
def diff(old: Path, new: Path) -> None:
    typer.echo(json.dumps(diff_datasets(load_dataset(old), load_dataset(new)), indent=2))


def _git_sha() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


@app.command("run")
def run_command(dataset: Path = typer.Option(Path("datasets/golden_v1.json")), models: Path = typer.Option(Path("configs/models.yaml")),
                model: Annotated[list[str] | None, typer.Option("--model")] = None,
                judge_model: Annotated[str | None, typer.Option("--judge-model")] = None,
                name: str = "CLI evaluation") -> None:
    """Execute a dataset × model-configuration matrix and persist every result."""
    create_schema()
    document = load_dataset(dataset)
    configs = {item["name"]: item for item in yaml.safe_load(models.read_text(encoding="utf-8"))["models"]}
    selected = model or ["mock-baseline"]
    selected_names = [*selected, *([judge_model] if judge_model else [])]
    unknown = sorted(set(selected_names) - configs.keys())
    if unknown:
        raise typer.BadParameter(f"unknown models: {', '.join(unknown)}")
    with SessionLocal() as session:
        dataset_row = ensure_dataset(session, document)
        providers = {key: (build_provider(configs[key]), configs[key]) for key in selected}
        judge_provider = build_provider(configs[judge_model]) if judge_model else None
        snapshot = {key: configs[key] for key in selected}
        if judge_model:
            snapshot["judge"] = configs[judge_model]
        row = EvaluationRun(name=name, dataset_id=dataset_row.id, git_sha=_git_sha(), configuration_snapshot=snapshot,
            is_mock=all(provider.is_mock for provider, _ in providers.values()))
        session.add(row)
        session.commit()
        asyncio.run(EvaluationRunner(session).execute(run=row, dataset=document, providers=providers, judge_provider=judge_provider))
        typer.echo(json.dumps({"run_id": row.id, "mode": "Mock Provider / Offline Demo" if row.is_mock else "production", "metrics": run_metrics(session, row.id)}, indent=2))


@app.command()
def compare(baseline: str, current: str) -> None:
    with SessionLocal() as session:
        output = {"baseline": run_metrics(session, baseline), "current": run_metrics(session, current),
            "regression": detect_regression(run_samples(session, baseline), run_samples(session, current)).model_dump()}
        typer.echo(json.dumps(output, indent=2))


@app.command()
def regressions(baseline: str, current: str, threshold: float = 0.05) -> None:
    with SessionLocal() as session:
        typer.echo(detect_regression(run_samples(session, baseline), run_samples(session, current), threshold).model_dump_json(indent=2))


@app.command()
def export(run_id: str, output: Path = Path("evalbench-export.json")) -> None:
    with SessionLocal() as session:
        run = session.get(EvaluationRun, run_id)
        if not run:
            raise typer.BadParameter("run not found")
        output.write_text(json.dumps({"run_id": run_id, "configuration": run.configuration_snapshot, "metrics": run_metrics(session, run_id)}, indent=2), encoding="utf-8")
        typer.echo(f"Exported {output}")


if __name__ == "__main__":
    app()
