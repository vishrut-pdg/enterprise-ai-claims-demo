import type { Claim, ClaimDetail, Review, ReviewDetail, Outcome } from '../types/claims'
const base = import.meta.env.VITE_API_URL ?? '/api'
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(base + path, {...options, headers: {'Content-Type': 'application/json', 'X-Role': 'manager', 'X-Actor': 'local-manager', ...options.headers}})
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed. Refresh and try again.')
  return data as T
}
export const api = {
  claims: () => request<Claim[]>('/claims'),
  claim: (id: string) => request<ClaimDetail>(`/claims/${encodeURIComponent(id)}`),
  process: (id: string, version: number) => request<ClaimDetail>(`/claims/${encodeURIComponent(id)}/process`, {method: 'POST', body: JSON.stringify({expected_version: version})}),
  reviews: () => request<Review[]>('/reviews'),
  review: (id: string) => request<ReviewDetail>(`/reviews/${encodeURIComponent(id)}`),
  decide: (id: string, version: number, decision: string, rationale: string) => request<ReviewDetail>(`/reviews/${encodeURIComponent(id)}/decisions`, {method: 'POST', body: JSON.stringify({expected_version: version, decision, rationale})}),
  memory: (id: string) => request<Outcome[]>(`/claims/${encodeURIComponent(id)}/memory`),
  batch: (ids: string[]) => request<{jobs: {claim_id: string; job_id: string}[]}>('/jobs/assess', {method: 'POST', body: JSON.stringify(ids)}),
}
