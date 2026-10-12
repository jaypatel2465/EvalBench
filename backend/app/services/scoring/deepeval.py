from __future__ import annotations

import asyncio
from typing import Any

from app.schemas.domain import GenerationResult, JudgeResult, TestCase


async def evaluate_with_deepeval(case: TestCase, candidate: GenerationResult, judge_model: str | None = None) -> JudgeResult:
    """Run established DeepEval RAG metrics without coupling the rest of EvalBench to it.

    DeepEval is an optional dependency (`pip install -e .[judge]`) because its hosted
    judge requires separate credentials and should never be a hidden local dependency.
    """
    try:
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
        from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    except ImportError as exc:
        raise RuntimeError("DeepEval is not installed; install EvalBench with the 'judge' extra") from exc
    context = [str(chunk.get("text", "")) for chunk in candidate.trace.get("retrieval", {}).get("chunks", [])]
    test_case = LLMTestCase(input=case.input, actual_output=candidate.response, expected_output=case.reference_answer,
        retrieval_context=context or None)
    common: dict[str, Any] = {"async_mode": True}
    if judge_model:
        common["model"] = judge_model
    metrics = [
        GEval(name="Correctness and instruction following", criteria="Judge correctness, relevance, and instruction following against the expected answer.",
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT], **common),
        AnswerRelevancyMetric(**common),
    ]
    if context:
        metrics.append(FaithfulnessMetric(**common))
    await asyncio.gather(*(metric.a_measure(test_case) for metric in metrics))
    scores = {metric.__class__.__name__.removesuffix("Metric").lower(): round(float(metric.score or 0) * 5) for metric in metrics}
    mean_score = max(1, min(5, round(sum(scores.values()) / len(scores))))
    reasons = "; ".join(f"{metric.__class__.__name__}: {metric.reason}" for metric in metrics)
    return JudgeResult(score=mean_score, reason=reasons, dimension_scores=scores)

