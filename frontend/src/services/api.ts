import type { Failure, Run } from '../types'

const API = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? `Request failed (${response.status})`)
  return response.json() as Promise<T>
}

export const api = {
  runs: () => request<Run[]>('/api/runs'),
  run: (id: string) => request<Run>(`/api/runs/${id}`),
  failures: (id: string, query = '') => request<Failure[]>(`/api/runs/${id}/failures${query}`),
  models: () => request<Record<string, unknown>[]>('/api/models'),
  datasets: () => request<Record<string, unknown>[]>('/api/datasets'),
  regressions: (current?: string, baseline?: string) => request<Record<string, unknown>[]>(`/api/regressions${current && baseline ? `?current_run_id=${current}&baseline_run_id=${baseline}` : ''}`),
  comparisons: (ids: string[]) => request<{ runs: { run: Run; metrics: Run['metrics'] }[] }>(`/api/comparisons?${ids.map(id => `run_ids=${id}`).join('&')}`),
  reliability: () => request<Record<string, unknown>>('/api/judge-reliability'),
}

