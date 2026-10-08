import type { ClaimDetail } from '../types/claims'
export function ActionFeedback({claim}: {claim: ClaimDetail}) {
  const pending = claim.status === 'pending_manager_review'
  return <div className="action-feedback" role="status"><strong>{pending ? 'Assessment complete. Recommendation ready.' : `Assessment complete. Claim ${claim.status}.`}</strong><p>{pending ? 'The AI recommendation is awaiting review. Accept or reject this expense in Manager review.' : 'The decision and outcome have been recorded in processing history.'}</p>{claim.review && <a href={`#/reviews/${claim.review.id}`}>Continue to manager review →</a>}</div>
}
