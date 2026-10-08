import type { Claim, ClaimDetail, Review, ReviewDetail, Outcome, BatchResult, BatchJob, BatchProgress, ChatTurn, ChatReply } from '../types/claims'
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
  activeJobs: () => request<{jobs:BatchJob[];worker_available:boolean}>('/jobs/active'),
  batchStatus: (ids: string[]) => request<BatchProgress>('/jobs/status?' + ids.map(id => 'job_ids=' + encodeURIComponent(id)).join('&')),
  chat: (message: string, claimId: string | undefined, history: ChatTurn[]) => request<ChatReply>('/chat', {method:'POST', body:JSON.stringify({message, claim_id:claimId, history})}),
  batch: (ids: string[]) => request<BatchResult>('/jobs/assess', {method: 'POST', body: JSON.stringify(ids)}),
}
