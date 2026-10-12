from app.schemas.domain import GenerationResult, TestCase
from app.services.scoring.rules import score_case


def case(**overrides):
    values = {"id": "sec-test", "category": "citation_correctness", "input": "What was revenue?",
        "expected_behavior": "Answer from evidence", "reference_answer": "$10 billion", "required_facts": ["$10 billion"],
        "forbidden_claims": ["$12 billion"], "expected_citations": ["doc-1"]}
    return TestCase.model_validate({**values, **overrides})


def generated(response: str, citations=None):
    return GenerationResult(response=response, model="test", provider="mock", latency_ms=1, citations=citations or [])


def test_composable_rules_pass_grounded_answer():
    scores = score_case(case(), generated("Revenue was $10 billion.", [{"source_id": "doc-1"}]))
    assert scores
    assert all(score.passed for score in scores)
    assert {score.scorer for score in scores} == {"required_facts", "forbidden_claims", "citation_presence", "citation_validity"}


def test_rules_report_missing_fact_forbidden_claim_and_bad_citation():
    scores = score_case(case(), generated("Revenue was $12 billion.", [{"source_id": "wrong"}]))
    failed = {score.scorer for score in scores if not score.passed}
    assert failed == {"required_facts", "forbidden_claims", "citation_validity"}


def test_json_schema_validation():
    test_case = case(category="formatting", expected_format="json", required_facts=[], forbidden_claims=[], expected_citations=[],
        json_schema={"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}}})
    assert score_case(test_case, generated('{"answer":"ok"}'))[0].passed
    assert not score_case(test_case, generated('{"wrong":1}'))[0].passed

