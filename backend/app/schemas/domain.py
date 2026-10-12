from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CaseCategory(StrEnum):
    FACTUAL = "factual"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    CITATION = "citation_correctness"
    REFUSAL = "refusal"
    AMBIGUITY = "ambiguity"
    ADVERSARIAL = "adversarial"
    FORMATTING = "formatting"
    INSTRUCTION = "instruction_following"


class TestCase(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{2,119}$")
    category: CaseCategory
    input: str = Field(min_length=3, max_length=20_000)
    expected_behavior: str = Field(min_length=3)
    reference_answer: str = ""
    required_facts: list[str] = []
    forbidden_claims: list[str] = []
    expected_format: Literal["text", "json", "markdown", "refusal"] = "text"
    expected_regex: str | None = None
    json_schema: dict[str, Any] | None = None
    expected_citations: list[str] = []
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    tags: list[str] = []
    metadata: dict[str, Any] = {}

    @model_validator(mode="after")
    def validate_intent(self) -> TestCase:
        if not (self.reference_answer or self.required_facts or self.expected_regex or self.expected_format == "refusal"):
            raise ValueError("case requires a reference answer, required fact, regex, or refusal expectation")
        return self


class DatasetMetadata(BaseModel):
    name: str
    version: str
    description: str
    source: str
    created_at: datetime
    license: str = "Public filings; demo dataset metadata under MIT"


class DatasetDocument(BaseModel):
    metadata: DatasetMetadata
    cases: list[TestCase]


class GenerationRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None
    temperature: float = Field(default=0, ge=0, le=2)
    max_tokens: int = Field(default=800, ge=1, le=32_000)
    response_format: str | None = None
    metadata: dict[str, Any] = {}


class GenerationResult(BaseModel):
    response: str = ""
    model: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None
    cost_is_estimate: bool = True
    finish_reason: str | None = None
    provider: str
    error: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = []
    trace: dict[str, Any] = {}


class ScoreResult(BaseModel):
    scorer: str
    value: float = Field(ge=0, le=1)
    passed: bool
    reason: str
    details: dict[str, Any] = {}


class JudgeResult(BaseModel):
    score: int = Field(ge=1, le=5)
    reason: str
    dimension_scores: dict[str, int]


class RunCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    dataset_path: str = "datasets/golden_v1.json"
    models: list[str] = ["mock-baseline"]
    judge_model: str | None = None
    baseline_run_id: str | None = None
    git_sha: str | None = Field(default=None, max_length=64)


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    status: str
    git_sha: str | None
    is_mock: bool
    created_at: datetime
    completed_at: datetime | None
    metrics: dict[str, float | int | None] = {}


class RegressionResult(BaseModel):
    metric: str
    baseline: float
    current: float
    absolute_change: float
    relative_change: float | None
    ci_low: float | None
    ci_high: float | None
    classification: Literal["regression_detected", "possible_regression", "inconclusive", "improvement", "no_material_change"]
    samples: int


class GatePolicy(BaseModel):
    pass_rate_drop: float = Field(default=0.05, ge=0, le=1)
    p95_latency_increase: float = Field(default=0.20, ge=0)
    cost_increase: float = Field(default=0.25, ge=0)
    fail_on_possible: bool = False


class GateDecision(BaseModel):
    decision: Literal["passed", "warned", "failed"]
    reasons: list[str]
    metrics: dict[str, Any]
