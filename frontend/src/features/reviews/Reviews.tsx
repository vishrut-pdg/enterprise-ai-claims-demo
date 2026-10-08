import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import { api } from '../../api/client'
import type { Review } from '../../types/claims'
import { DataTable } from '../../components/DataTable'
import { Status, money, humanize } from '../../components/Status'
import { Button } from '../../components/ui/button'
import { Textarea } from '../../components/ui/textarea'
import { ClaimFacts, ProcessingHistory } from '../claims/ClaimDetail'
const columns:ColumnDef<Review>[]=[
  {id:'claim',accessorFn:r=>r.claim.id,header:'Claim',cell:({row})=><a href={`#/reviews/${row.original.id}`}>{row.original.claim.id}<small>{row.original.claim.title}</small></a>},
  {id:'employee',accessorFn:r=>r.claim.employee.name,header:'Employee'},
  {id:'amount',accessorFn:r=>Number(r.claim.amount),header:'Amount',cell:({row})=>money(row.original.claim.amount,row.original.claim.currency)},
  {accessorKey:'reason',header:'AI recommendation'},
  {accessorKey:'assigned_role',header:'Assigned role'},
  {accessorKey:'status',header:'Status',cell:({row})=><Status value={row.original.status}/>},
]
export function ReviewQueue(){
  const query=useQuery({queryKey:['reviews'],queryFn:api.reviews})
  const [closed,setClosed]=useState(false)
  if(query.isPending)return <p role="status">Loading manager reviews…</p>
  if(query.error)return <p role="alert">{query.error.message}</p>
  return <><div className="page-heading"><div><p className="eyebrow">MANAGER APPROVAL</p><h1>Manager review queue</h1><p className="muted">Review AI advice and accept or reject every expense claim.</p></div><label><input type="checkbox" checked={closed} onChange={e=>setClosed(e.target.checked)}/> Include closed reviews</label></div><section className="panel"><DataTable data={query.data.filter(r=>closed || r.active)} columns={columns} label="reviews"/></section></>
}
export function ReviewDetail({id}:{id:string}){
  const client=useQueryClient()
  const [rationale,setRationale]=useState('')
  const [feedback,setFeedback]=useState('')
  const query=useQuery({queryKey:['review',id],queryFn:()=>api.review(id)})
  const mutation=useMutation({mutationFn:(decision:string)=>api.decide(id,query.data!.claim.version,decision,rationale.trim()),onSuccess:(_,decision)=>{setRationale('');setFeedback(`Manager decision recorded. Claim ${decision==='accept'?'accepted':'rejected'}. Your decision and rationale have been recorded.`);client.invalidateQueries()},onError:()=>client.invalidateQueries({queryKey:['review',id]})})
  if(query.isPending)return <p role="status">Loading manager review…</p>
  if(query.error)return <p role="alert">{query.error.message}</p>
  const review=query.data
  return <><a className="back" href="#/reviews">← Manager review queue</a><div className="page-heading"><div><p className="eyebrow">MANAGER REVIEW · {review.claim.id}</p><h1>{review.claim.title}</h1><Status value={review.status}/></div><a href={`#/claims/${review.claim.id}`}>View claim</a></div>
  {feedback && <div className="action-feedback" role="status">{feedback}</div>}<section className="panel investigation"><h2>AI recommendation</h2><p>{review.reason}</p><p><strong>Recommended decision: {review.claim.assessment?.data.recommendation ?? 'Not available'}</strong> · This is advice; only your action decides the claim.</p>{review.unresolved_questions.map(q=><p key={q}>• {q}</p>)}<small>Evidence references: {review.evidence_ids.join(', ') || 'None supplied'}</small></section><ClaimFacts claim={review.claim}/>
  <section className="panel"><h2>Manager decision</h2><p className="muted">Record the evidence and rationale supporting your decision. All actions are audited.</p>{review.active?<><label htmlFor="rationale">Reviewer rationale</label><Textarea id="rationale" placeholder="Explain your decision…" value={rationale} onChange={e=>setRationale(e.target.value)}/><div className="actions">{['accept','reject'].map(decision=><Button key={decision} variant={decision==='reject'?'destructive':decision==='accept'?'default':'outline'} disabled={rationale.trim().length<3 || mutation.isPending} onClick={()=>mutation.mutate(decision)}>{mutation.isPending && mutation.variables===decision ? 'Recording…' : humanize(decision).replace(/^./,c=>c.toUpperCase())}</Button>)}</div></>:<p>This review is closed. <Status value={review.claim.status}/></p>}{mutation.error && <p role="alert">{mutation.error.message}</p>}</section>
  <section className="panel"><h2>Review history</h2>{review.decisions.length?review.decisions.map(d=><article className="review-decision" key={d.id}><Status value={d.decision}/><span>{d.actor} · {new Date(d.created_at).toLocaleString()}</span><p>{d.rationale}</p></article>):<p className="muted">No manager actions recorded.</p>}</section><ProcessingHistory claim={review.claim}/></>
}
