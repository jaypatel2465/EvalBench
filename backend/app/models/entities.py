from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    checksum: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    cases: Mapped[list[TestCaseRecord]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("name", "version", name="uq_dataset_name_version"),)


class TestCaseRecord(Base):
    __tablename__ = "test_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    dataset: Mapped[DatasetVersion] = relationship(back_populates="cases")
    __table_args__ = (UniqueConstraint("dataset_id", "external_id", name="uq_case_dataset_external"),)


class ModelConfiguration(Base):
    __tablename__ = "model_configurations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(160))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    pricing: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    git_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    configuration_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    baseline_run_id: Mapped[str | None] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dataset: Mapped[DatasetVersion] = relationship()
    results: Mapped[list[EvaluationResult]] = relationship(back_populates="run", cascade="all, delete-orphan")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), index=True)
    model_config_id: Mapped[int] = mapped_column(ForeignKey("model_configurations.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    run: Mapped[EvaluationRun] = relationship(back_populates="results")
    test_case: Mapped[TestCaseRecord] = relationship()
    model_config: Mapped[ModelConfiguration] = relationship()
    scores: Mapped[list[Score]] = relationship(back_populates="result", cascade="all, delete-orphan")
    failures: Mapped[list[Failure]] = relationship(back_populates="result", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("run_id", "test_case_id", "model_config_id", name="uq_result_work_item"),)


class Score(Base):
    __tablename__ = "scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("evaluation_results.id"), index=True)
    scorer: Mapped[str] = mapped_column(String(80), index=True)
    value: Mapped[float] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[EvaluationResult] = relationship(back_populates="scores")


class Failure(Base):
    __tablename__ = "failures"
    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("evaluation_results.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[EvaluationResult] = relationship(back_populates="failures")


class Regression(Base):
    __tablename__ = "regressions"
    id: Mapped[int] = mapped_column(primary_key=True)
    baseline_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    current_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    metric: Mapped[str] = mapped_column(String(80), index=True)
    baseline_value: Mapped[float] = mapped_column(Float)
    current_value: Mapped[float] = mapped_column(Float)
    absolute_change: Mapped[float] = mapped_column(Float)
    relative_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification: Mapped[str] = mapped_column(String(32), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class JudgeEvaluation(Base):
    __tablename__ = "judge_evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("evaluation_results.id"), index=True)
    judge_provider: Mapped[str] = mapped_column(String(40))
    judge_model: Mapped[str] = mapped_column(String(160))
    score: Mapped[float] = mapped_column(Float)
    dimension_scores: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text)
    rubric_version: Mapped[str] = mapped_column(String(40))
    human_rating: Mapped[float | None] = mapped_column(Float, nullable=True)


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(String(500))
    checksum: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

