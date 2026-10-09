export type UsageSummary = {
  requests:number; succeeded:number; failed:number; success_rate:number|null;
  input_tokens:number; output_tokens:number; thinking_tokens:number; total_tokens:number;
  billable_characters:number; token_reported_requests:number; priced_requests:number;
  unpriced_requests:number; cost_usd:number|null; average_ms:number|null; p95_ms:number|null
}
export type UsageRequest = {
  id:string; run_id:string; claim_id:string|null; operation:string; provider:string; model:string;
  status:string; duration_ms:number|null; created_at:string; error_code:string|null;
  cost_usd:number|null; cost_basis:string; historical:boolean;
  input_tokens:number|null; output_tokens:number|null; thinking_tokens:number|null;
  total_tokens:number|null; billable_characters:number|null
}
export type ClaimRun = {
  id:string; claim_id:string; run_id:string; provider:string; model:string; status:string;
  duration_ms:number; created_at:string; error_code:string|null; trajectory:string[]
}
export type AIAnalytics = {
  days:number; provider:string|null; currency:string; summary:UsageSummary;
  claim_runs:{total:number;succeeded:number;failed:number;success_rate:number|null;average_ms:number|null;p95_ms:number|null};
  models:(UsageSummary & {provider:string;model:string})[];
  requests:UsageRequest[]; recent_runs:ClaimRun[]; notes:string[]; price_source:string;
  pricing_checked_at:string; history_limit:number
}
