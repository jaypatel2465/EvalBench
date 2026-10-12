export type Metrics = {
  total_evaluations: number; completed: number; pass_rate: number; failure_rate: number; quality_score: number;
  average_latency_ms: number | null; p95_latency_ms: number | null; cost_per_1k: number | null;
  failures_by_category: Record<string, number>; models: Record<string, ModelMetrics>; error_count: number;
}
export type ModelMetrics = { evaluations: number; pass_rate: number; p95_latency_ms: number | null; cost_per_request: number | null }
export type Run = { id: string; name: string; status: string; git_sha: string | null; is_mock: boolean; dataset_version: string;
  created_at: string; completed_at: string | null; metrics: Metrics; dataset?: { name: string; version: string; checksum: string } }
export type Failure = { id: number; category: string; severity: string; reason: string; test_case_id: string; model: string;
  input: string; expected_behavior: string; reference_answer: string; response: string; citations: unknown[]; trace: Record<string, unknown>;
  latency_ms: number | null; total_tokens: number | null; estimated_cost: number | null;
  scores: { scorer: string; value: number; passed: boolean; reason: string }[] }
