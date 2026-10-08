import { Loader2, CheckCircle2, Play } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  {id:'assessment',accessorFn:c=>c.assessment?.data.recommendation ?? 'not assessed',header:'AI recommendation',cell:({row})=>row.original.assessment ? <Status value={row.original.assessment.data.recommendation}/> : <span className="muted">Not assessed</span>},
]
export function ClaimQueue() {
  const client=useQueryClient()
  const [jobs,setJobs]=useState<BatchJob[]>(()=>{try {const value=JSON.parse(sessionStorage.getItem('week2-batch-jobs') ?? '[]');return Array.isArray(value) ? value.filter(j=>typeof j?.job_id==='string' && typeof j?.claim_id==='string') : []} catch {return []}})
  useEffect(()=>{sessionStorage.setItem('week2-batch-jobs',JSON.stringify(jobs))},[jobs])
  const query=useQuery({queryKey:['claims'],queryFn:api.claims})
  const active=useQuery({queryKey:['active-jobs'],queryFn:async()=>{const result=await api.activeJobs();setJobs(current=>current.length ? current : result.jobs);return result},refetchInterval:5000,retry:1})
  const batch=useMutation({mutationFn:api.batch,onMutate:()=>setJobs([]),onSuccess:result=>setJobs(result.jobs)})
  const progress=useQuery({queryKey:['batch-progress',jobs.map(j=>j.job_id)],queryFn:()=>api.batchStatus(jobs.map(j=>j.job_id)),enabled:jobs.length>0,retry:1,refetchInterval:q=>q.state.error ? false : q.state.data?.jobs.every(j=>['succeeded','failed','not_found'].includes(j.status)) ? false : 1500})
  const complete=progress.data?.jobs.filter(j=>['succeeded','failed','not_found'].includes(j.status)).length ?? 0
  const finished=jobs.length>0 && complete===jobs.length
  useEffect(()=>{if(progress.data){client.invalidateQueries({queryKey:['claims']});client.invalidateQueries({queryKey:['reviews']})}},[progress.data,client])
  if(query.isPending)return <p role="status">Loading claim queue…</p>
  if(query.error)return <p role="alert">{query.error.message}</p>
  const claims=query.data
  return <><div className="page-heading"><div><p className="eyebrow">CLAIMS OPERATIONS</p><h1>Claim queue</h1><p className="muted">Get AI recommendations, then accept or reject every expense in Manager review.</p></div><div className="batch-controls"><Button aria-label={batch.isPending || (jobs.length>0 && !finished) ? 'Running' : finished ? 'Finished' : 'Run'} disabled={active.isPending || !active.data?.worker_available || batch.isPending || (jobs.length>0 && !finished) || finished || !claims.some(c=>c.status==='submitted')} onClick={()=>batch.mutate(claims.filter(c=>c.status==='submitted').map(c=>c.id))}>{batch.isPending || (jobs.length>0 && !finished) ? <><Loader2 className="running-spinner" size={16}/>Running</> : finished ? <><CheckCircle2 size={16}/>Finished</> : <><Play size={16}/>Run</>}</Button>{finished && claims.some(c=>c.status==='submitted') && <Button variant="outline" onClick={()=>{setJobs([]);batch.reset()}}>Start another batch</Button>}<small>{batch.isPending ? 'Submitting assessments…' : jobs.length>0 && !finished ? 'Tracking live worker progress' : finished ? `${complete} jobs finished` : `${claims.filter(c=>c.status==='submitted').length} claims ready for assessment`}</small></div></div>
  {active.error && <p role="alert">{active.error.message}</p>}{active.data && !active.data.worker_available && <div className="action-feedback pending"><strong>Assessment worker is offline</strong><p>Start the demo with <code>./scripts/demo.sh</code> to run queued assessments.</p></div>}<div className="metrics">{[['All claims',claims.length],['Awaiting assessment',claims.filter(c=>c.status==='submitted').length],['Manager review',claims.filter(c=>['pending_manager_review','information_requested'].includes(c.status)).length],['Completed',claims.filter(c=>['accepted','rejected'].includes(c.status)).length]].map(([label,count])=><div key={label}><span>{label}</span><strong>{count}</strong></div>)}</div>
  {batch.error && <p role="alert">{batch.error.message}</p>}{jobs.length>0 && <section className="panel batch-panel"><div role="status"><h2>{finished ? 'Batch processing complete' : 'Batch assessment in progress'}</h2><p aria-live="polite">{progress.data?.jobs.filter(j=>j.status==='in_progress').length ?? 0} running · {progress.data?.jobs.filter(j=>['queued','deferred'].includes(j.status)).length ?? jobs.length} queued</p><p>{complete} of {jobs.length} assessments finished{progress.data?.jobs.some(j=>j.status==='failed') ? ' · Some assessments failed; see details below.' : '.'}</p><progress value={complete} max={jobs.length} aria-label="Batch assessment progress"/></div>{progress.error && <p role="alert">{progress.error.message} <Button variant="outline" onClick={()=>progress.refetch()}>Retry progress check</Button></p>}{progress.data && !progress.data.worker_available && !finished && <p role="alert">Worker offline. Restart the ARQ worker to continue queued assessments.</p>}<ul className="batch-jobs">{jobs.map(job=>{const item=progress.data?.jobs.find(j=>j.job_id===job.job_id);return <li key={job.job_id}><a href={`#/claims/${job.claim_id}`}>{job.claim_id}</a><Status value={item?.status ?? 'queued'}/>{item?.result?.status && <Status value={item.result.status}/>}{item?.error && <span>{item.error}</span>}</li>})}</ul></section>}
  <section className="panel"><DataTable data={claims} columns={columns} label="claims"/></section></>
}
