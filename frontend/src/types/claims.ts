export type Investigation = {recommendation:'accept'|'reject';confidence:number;findings:string[];evidence_ids:string[];summary:string;limitations:string[]}
export type AssessmentData = { investigation?: Investigation; decision_mode?:string; recommendation: 'accept' | 'reject' | 'investigate'; confidence: number; findings: string[]; evidence_ids: string[]; unresolved_questions: string[]; explanation: string }
export type Assessment = { id: string; claim_version: number; data: AssessmentData }
export type Finding = { id: string; claim_version: number; code: string; severity: string; message: string; evidence_ids: string[] }
export type Evidence = { id: string; filename: string; kind: string; content: string; verified: boolean }
export type History = { id: string; created_at: string; event_type: string; actor: string; run_id: string; data: Record<string, unknown> }
export type Claim = { id: string; title: string; employee: {name: string; email: string; department: string}; submitted_date: string; amount: string; currency: string; claim_type: string; status: string; version: number; assessment: Assessment | null; lines: {id: string; category: string; description: string; amount: string; expense_date: string}[] }
export type Outcome = { id: string; claim_id: string; recommendation: string; final_decision: string; reviewer_rationale: string; reviewed: boolean; created_at: string }
export type ClaimDetail = Claim & { policy: { id: string; name: string; text: string; currency: string; auto_accept: boolean; auto_reject: boolean; rules: {id: string; code: string; parameters: Record<string, unknown>}[] }; evidence: Evidence[]; findings: Finding[]; history: History[]; review: Review | null; outcome: Outcome | null; executions: {id: string; provider: string; model: string; status: string; duration_ms: number; error_code: string | null; trajectory: string[]}[] }
export type Review = { id: string; claim_id: string; status: string; active: boolean; assigned_role: string; reason: string; evidence_ids: string[]; unresolved_questions: string[]; claim: Claim }
export type ReviewDetail = Omit<Review, 'claim'> & { claim: ClaimDetail; decisions: {id: string; actor: string; decision: string; rationale: string; created_at: string}[] }

export type BatchJob = { claim_id: string; job_id: string }
export type BatchResult = { batch_id: string; jobs: BatchJob[] }
export type BatchProgress = { worker_available: boolean; jobs: {job_id: string; status: string; result: {claim_id: string; status: string} | null; error: string | null}[] }
export type ChatTurn = {role: 'user' | 'assistant'; content: string}
export type ChatReply = {answer: string; sources: string[]; read_only: boolean; provider: string}
