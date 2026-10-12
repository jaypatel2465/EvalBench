from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from app.schemas.domain import GenerationResult, ScoreResult, TestCase


def normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9\s]", " ", text.lower()).split())


def exact_match(case: TestCase, result: GenerationResult) -> ScoreResult | None:
    if not case.reference_answer or "exact-match" not in case.tags:
        return None
    passed = normalize(case.reference_answer) == normalize(result.response)
    return ScoreResult(scorer="exact_match", value=float(passed), passed=passed, reason="Normalized response matches reference" if passed else "Response differs from reference")


def required_facts(case: TestCase, result: GenerationResult) -> ScoreResult | None:
    if not case.required_facts:
        return None
    response = normalize(result.response)
    matched = [fact for fact in case.required_facts if normalize(fact) in response]
    value = len(matched) / len(case.required_facts)
    return ScoreResult(scorer="required_facts", value=value, passed=value == 1, reason=f"Matched {len(matched)}/{len(case.required_facts)} required facts", details={"matched": matched, "missing": [fact for fact in case.required_facts if fact not in matched]})


def forbidden_claims(case: TestCase, result: GenerationResult) -> ScoreResult | None:
    if not case.forbidden_claims:
        return None
    response = normalize(result.response)
    found = [claim for claim in case.forbidden_claims if normalize(claim) in response]
    return ScoreResult(scorer="forbidden_claims", value=float(not found), passed=not found, reason="No forbidden claims" if not found else f"Found {len(found)} forbidden claims", details={"found": found})


def regex_match(case: TestCase, result: GenerationResult) -> ScoreResult | None:
    if not case.expected_regex:
        return None
    try:
        passed = bool(re.search(case.expected_regex, result.response, re.MULTILINE | re.IGNORECASE))
    except re.error as exc:
        return ScoreResult(scorer="regex", value=0, passed=False, reason=f"Invalid dataset regex: {exc}")
    return ScoreResult(scorer="regex", value=float(passed), passed=passed, reason="Pattern matched" if passed else "Expected pattern missing")


def _validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    types: dict[str, type | tuple[type, ...]] = {"object": dict, "array": list, "string": str, "number": (int, float), "integer": int, "boolean": bool, "null": type(None)}
    if expected in types and not isinstance(value, types[expected]):
        return [f"{path} expected {expected}"]
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}.{required} is required")
        for key, child in schema.get("properties", {}).items():
            if key in value:
                errors.extend(_validate_schema(value[key], child, f"{path}.{key}"))
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(_validate_schema(item, schema["items"], f"{path}[{index}]"))
    return errors


def json_schema(case: TestCase, result: GenerationResult) -> ScoreResult | None:
    if case.expected_format != "json" and not case.json_schema:
        return None
    try:
        value = json.loads(result.response)
    except json.JSONDecodeError as exc:
        return ScoreResult(scorer="json_schema", value=0, passed=False, reason=f"Invalid JSON: {exc.msg}")
    errors = _validate_schema(value, case.json_schema or {})
    return ScoreResult(scorer="json_schema", value=float(not errors), passed=not errors, reason="Valid JSON schema" if not errors else "; ".join(errors), details={"errors": errors})


def citation_presence(case: TestCase, result: GenerationResult) -> ScoreResult | None:
    if not case.expected_citations and case.category.value != "citation_correctness":
        return None
    passed = bool(result.citations)
    return ScoreResult(scorer="citation_presence", value=float(passed), passed=passed, reason="Citation present" if passed else "Required citation missing")


def citation_validity(case: TestCase, result: GenerationResult) -> ScoreResult | None:
    if not case.expected_citations:
        return None
    actual = {str(item.get("source_id", "")) for item in result.citations}
    matched = sorted(set(case.expected_citations) & actual)
    value = len(matched) / len(set(case.expected_citations))
    return ScoreResult(scorer="citation_validity", value=value, passed=value == 1, reason=f"Matched {len(matched)}/{len(set(case.expected_citations))} expected sources", details={"expected": case.expected_citations, "actual": sorted(actual)})


SCORERS: tuple[Callable[[TestCase, GenerationResult], ScoreResult | None], ...] = (
    exact_match, required_facts, forbidden_claims, regex_match, json_schema, citation_presence, citation_validity,
)


def score_case(case: TestCase, result: GenerationResult) -> list[ScoreResult]:
    scores = [score for scorer in SCORERS if (score := scorer(case, result)) is not None]
    if not scores:
        scores.append(ScoreResult(scorer="non_empty", value=float(bool(result.response.strip())), passed=bool(result.response.strip()), reason="Response is non-empty" if result.response.strip() else "Empty response"))
    return scores
