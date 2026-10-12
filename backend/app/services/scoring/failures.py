from __future__ import annotations

from typing import Any

from app.schemas.domain import ScoreResult, TestCase


def classify_failures(case: TestCase, scores: list[ScoreResult], error: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if error:
        category = "timeout" if error.get("type") == "timeout" else "provider_failure"
        return [{"category": category, "severity": "high", "reason": error.get("message", category), "evidence": error}]
    mapping = {
        "required_facts": "missing_information", "forbidden_claims": "unsupported_claim", "exact_match": "wrong_answer",
        "regex": "formatting_failure", "json_schema": "formatting_failure", "citation_presence": "citation_failure",
        "citation_validity": "citation_failure", "non_empty": "irrelevant_answer",
    }
    failures = []
    for score in scores:
        if not score.passed:
            category = mapping.get(score.scorer, "wrong_answer")
            if case.category.value == "retrieval" and score.scorer == "required_facts":
                category = "retrieval_failure"
            if case.category.value == "refusal":
                category = "refusal_error"
            failures.append({"category": category, "severity": "high" if score.value == 0 else "medium", "reason": score.reason, "evidence": score.details})
    return failures

