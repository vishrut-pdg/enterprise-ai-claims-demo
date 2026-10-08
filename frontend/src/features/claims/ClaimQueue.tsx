import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, CheckCircle2 } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'
import { api } from '../../api/client'
import type { Claim, BatchJob } from '../../types/claims'
import { DataTable } from '../../components/DataTable'
import { Status, money } from '../../components/Status'
import { Button } from '../../components/ui/button'
const columns: ColumnDef<Claim>[] = [
  {accessorKey:'id',header:'Claim',cell:({row})=><a href={`#/claims/${row.original.id}`}>{row.original.id}<small>{row.original.title}</small></a>},
  {id:'employee',accessorFn:c=>c.employee.name,header:'Employee'},
  {accessorKey:'submitted_date',header:'Submitted'},
  {id:'amount',accessorFn:c=>Number(c.amount),header:'Amount',cell:({row})=><strong>{money(row.original.amount,row.original.currency)}</strong>},
  {accessorKey:'claim_type',header:'Type'},
  {accessorKey:'status',header:'Status',cell:({row})=><Status value={row.original.status}/>},
  {id:'assessment',accessorFn:c=>c.assessment?.data.recommendation ?? 'not assessed',header:'Assessment',cell:({row})=>row.original.assessment ? <Status value={row.original.assessment.data.recommendation}/> : <span className="muted">Not assessed</span>},
]

export function ClaimQueue() {
  const client=useQueryClient()
  const [jobs,setJobs]=useState<BatchJob[]>(()=>{try {const value=JSON.parse(sessionStorage.getItem('week4-ai-jobs') ?? '[]');return Array.isArray(value) ? value.filter(j=>typeof j?.job_id==='string' && typeof j?.claim_id==='string') : []} catch {return []}})
  useEffect(()=>{sessionStorage.setItem('week4-ai-jobs',JSON.stringify(jobs))},[jobs])
  const query=useQuery({queryKey:['claims'],queryFn:api.claims,refetchInterval:1500})
  const active=useQuery({queryKey:['active-jobs'],queryFn:async()=>{const result=await api.activeJobs();setJobs(current=>{const merged=new Map(current.map(j=>[j.job_id,j]));for(const job of result.jobs)merged.set(job.job_id,job);return [...merged.values()].slice(-100)});return result},refetchInterval:1500,retry:1})
  const progress=useQuery({queryKey:['batch-progress',jobs.map(j=>j.job_id)],queryFn:()=>api.batchStatus(jobs.map(j=>j.job_id)),enabled:jobs.length>0,retry:1,refetchInterval:1500})
  const complete=progress.data?.jobs.filter(j=>['succeeded','failed','not_found'].includes(j.status)).length ?? 0
  useEffect(()=>{if(progress.data)client.invalidateQueries({queryKey:['claims']})},[progress.data,client])
  if(query.isPending)return <p role="status">Loading claim queue…</p>
  if(query.error)return <p role="alert">{query.error.message}</p>
  const claims=query.data
  const pending=claims.filter(c=>!['accepted','rejected'].includes(c.status)).length
  const finished=pending===0 && claims.length>0
  const waitingRetry=pending>0 && active.data?.worker_available && active.data.jobs.length===0 && progress.data?.jobs.some(j=>j.status==='failed')
  return <><div className="page-heading"><div><p className="eyebrow">AUTONOMOUS CLAIMS OPERATIONS</p><h1>Claim queue</h1><p className="muted">AI investigates every claim and records acceptance or rejection automatically.</p></div><div className="autonomy-state" role="status">{finished ? <><CheckCircle2 size={18}/>All claims decided</> : waitingRetry ? <>Waiting for automatic retry</> : active.data?.worker_available ? <><Loader2 className="running-spinner" size={18}/>AI processing</> : <>Waiting for AI worker</>}</div></div>
  {active.error && <p role="alert">{active.error.message}</p>}{active.data && !active.data.worker_available && !finished && <div className="action-feedback pending"><strong>AI worker is offline</strong><p>Start the Week 4 ARQ worker. It discovers undecided claims automatically; no Run button or human approval is required.</p></div>}
  <div className="metrics">{[['All claims',claims.length],['Awaiting AI decision',pending],['Accepted',claims.filter(c=>c.status==='accepted').length],['Rejected',claims.filter(c=>c.status==='rejected').length]].map(([label,count])=><div key={label}><span>{label}</span><strong>{count}</strong></div>)}</div>
  {jobs.length>0 && <section className="panel batch-panel"><h2>{finished ? 'Autonomous processing complete' : 'AI investigation in progress'}</h2><p aria-live="polite">{progress.data?.jobs.filter(j=>j.status==='in_progress').length ?? 0} investigating · {progress.data?.jobs.filter(j=>['queued','deferred'].includes(j.status)).length ?? jobs.length} queued</p><p>{complete} of {jobs.length} tracked jobs finished.</p><progress value={complete} max={jobs.length} aria-label="Autonomous investigation progress"/>{progress.error && <p role="alert">{progress.error.message} <Button variant="outline" onClick={()=>progress.refetch()}>Reconnect progress</Button></p>}<ul className="batch-jobs">{jobs.map(job=>{const item=progress.data?.jobs.find(j=>j.job_id===job.job_id);return <li key={job.job_id}><a href={`#/claims/${job.claim_id}`}>{job.claim_id}</a><Status value={item?.status ?? 'queued'}/>{item?.result?.status && <Status value={item.result.status}/>} {item?.error && <span role="alert">{item.error}</span>}</li>})}</ul><small>Technical failures are retried automatically after a cooldown. The claim remains undecided until the AI can complete its investigation; an outage is not a claim rejection.</small></section>}
  <section className="panel"><DataTable data={claims} columns={columns} label="claims"/></section></>
}

export function DecisionHistory(){
  const query=useQuery({queryKey:['claims'],queryFn:api.claims,refetchInterval:1500})
  if(query.isPending)return <p role="status">Loading decisions…</p>
  if(query.error)return <p role="alert">{query.error.message}</p>
  const decided=query.data.filter(c=>['accepted','rejected'].includes(c.status))
  return <><div className="page-heading"><div><p className="eyebrow">AUTONOMOUS AUDIT</p><h1>Decision history</h1><p className="muted">Final AI decisions. Open a claim to see the investigation, evidence and audit trail.</p></div></div><section className="panel"><DataTable data={decided} columns={columns} label="decisions"/></section></>
}
