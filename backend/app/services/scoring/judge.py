from __future__ import annotations

import json

from app.schemas.domain import GenerationRequest, GenerationResult, JudgeResult, TestCase
from app.services.providers.base import ModelProvider

RUBRIC_VERSION = "sec-rag-rubric-v1"
RUBRIC = """Score the answer from 1 (unacceptable) to 5 (excellent) on correctness, relevance,
faithfulness, instruction_following, and citation_quality. Use only the reference and supplied evidence.
Return JSON with score, reason, and dimension_scores. Do not reward unsupported detail."""


async def judge_case(case: TestCase, candidate: GenerationResult, provider: ModelProvider) -> JudgeResult:
    prompt = f"{RUBRIC}\n\nQuestion: {case.input}\nExpected behavior: {case.expected_behavior}\nReference: {case.reference_answer}\nCandidate: {candidate.response}\nCitations: {json.dumps(candidate.citations)}"
    judged = await provider.generate(GenerationRequest(prompt=prompt, temperature=0, response_format="json"))
    try:
        return JudgeResult.model_validate_json(judged.response)
    except Exception as exc:
        raise ValueError(f"judge returned invalid structured output: {exc}") from exc

