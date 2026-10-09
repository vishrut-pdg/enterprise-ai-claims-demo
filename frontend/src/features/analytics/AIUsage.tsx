import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import { RefreshCw } from 'lucide-react'
import { api } from '../../api/client'
import type { UsageRequest, ClaimRun } from '../../types/analytics'
import { DataTable } from '../../components/DataTable'
import { Status, humanize } from '../../components/Status'
import { Button } from '../../components/ui/button'

const number=(value:number|null)=>value===null?'—':value.toLocaleString()
const duration=(value:number|null)=>value===null?'—':`${(value/1000).toFixed(2)} s`
const cost=(value:number|null)=>value===null?'Unavailable':value===0?'$0.00':value<.000001?'< $0.000001':`$${value.toFixed(6)}`
const requestColumns:ColumnDef<UsageRequest>[]=[
  {id:'time',accessorKey:'created_at',header:'Time',cell:({row})=><span>{new Date(row.original.created_at).toLocaleString()}<small>{row.original.historical?'Historical claim usage':'Measured request'}</small></span>},
  {accessorKey:'operation',header:'Activity',cell:({row})=><span>{humanize(row.original.operation)}<small>{row.original.claim_id?<a href={`#/claims/${row.original.claim_id}`}>{row.original.claim_id}</a>:'Queue chat / policy RAG'}</small></span>},
  {id:'model',accessorFn:r=>`${r.provider} ${r.model}`,header:'Provider / model',cell:({row})=><span>{row.original.provider}<small>{row.original.model}</small></span>},
  {accessorKey:'status',header:'Result',cell:({row})=><><Status value={row.original.status}/>{row.original.error_code&&<small>{row.original.error_code}</small>}</>},
  {accessorKey:'duration_ms',header:'Latency',cell:({row})=>duration(row.original.duration_ms)},
  {accessorKey:'input_tokens',header:'Input tokens',cell:({row})=>number(row.original.input_tokens)},
  {accessorKey:'output_tokens',header:'Output + thinking',cell:({row})=>number(row.original.output_tokens)},
  {accessorKey:'cost_usd',header:'Estimated USD',cell:({row})=><span>{cost(row.original.cost_usd)}<small>{row.original.cost_basis}</small></span>},
]
const runColumns:ColumnDef<ClaimRun>[]=[
  {accessorKey:'claim_id',header:'Claim',cell:({row})=><a href={`#/claims/${row.original.claim_id}`}>{row.original.claim_id}</a>},
  {accessorKey:'created_at',header:'Time',cell:({row})=>new Date(row.original.created_at).toLocaleString()},
  {accessorKey:'status',header:'Run result',cell:({row})=><><Status value={row.original.status}/>{row.original.error_code&&<small>{row.original.error_code}</small>}</>},
  {accessorKey:'duration_ms',header:'Recorded latency',cell:({row})=>duration(row.original.duration_ms)},
  {id:'details',header:'Run details',cell:({row})=><details><summary>Trace</summary><small>Run {row.original.run_id}</small><small>{row.original.provider} / {row.original.model}</small><p>{row.original.trajectory.join(' → ')}</p></details>},
]
export function AIUsage(){
  const [days,setDays]=useState(30)
  const [provider,setProvider]=useState('')
  const [tab,setTab]=useState<'requests'|'runs'>('requests')
  const query=useQuery({queryKey:['ai-analytics',days,provider],queryFn:()=>api.analytics(days,provider),refetchInterval:5000})
  return <><div className="page-heading"><div><p className="eyebrow">AI OPERATIONS</p><h1>AI usage & performance</h1><p className="muted">Track claim runs, model requests, latency, token usage and estimated provider spend.</p></div><Button variant="outline" onClick={()=>query.refetch()} disabled={query.isFetching}><RefreshCw size={16} className={query.isFetching?'running-spinner':''}/> Refresh</Button></div>
    <section className="analytics-filters" aria-label="Analytics filters"><label>Period<select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={0}>All time</option></select></label><label>Provider<select value={provider} onChange={e=>setProvider(e.target.value)}><option value="">All providers</option>{['vertex','ollama','btp','mock'].map(p=><option key={p} value={p}>{p}</option>)}</select></label><small>Updates every 5 seconds{query.dataUpdatedAt?` · ${new Date(query.dataUpdatedAt).toLocaleTimeString()}`:''}</small></section>
    {query.isPending?<p role="status">Loading AI usage…</p>:query.error?<p role="alert">{query.error.message}<Button variant="outline" onClick={()=>query.refetch()}>Retry</Button></p>:query.data&&<>
      <div className="metrics analytics-metrics">{[
        ['Completed claim runs',number(query.data.claim_runs.total),`${query.data.claim_runs.succeeded} succeeded · ${query.data.claim_runs.failed} failed`],
        ['Run success rate',query.data.claim_runs.success_rate===null?'—':`${query.data.claim_runs.success_rate}%`,'Run success is separate from an accept/reject decision'],
        ['Average run latency',duration(query.data.claim_runs.average_ms),`P95 ${duration(query.data.claim_runs.p95_ms)}`],
        ['Estimated provider cost',cost(query.data.summary.cost_usd),`${query.data.summary.priced_requests} priced · ${query.data.summary.unpriced_requests} unavailable`],
      ].map(([label,value,note])=><div key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div>
      {!query.data.summary.requests&&<section className="panel analytics-empty"><h2>No AI activity yet</h2><p>Claim processing, clarifying chat and policy embedding activity will appear here as it runs. This page reads recorded usage and does not start processing.</p></section>}
      <section className="panel"><h2>Request usage</h2><div className="usage-facts">{[
        ['Model / embedding requests',number(query.data.summary.requests)],['Succeeded / failed',`${query.data.summary.succeeded} / ${query.data.summary.failed}`],
        ['Reported input tokens',query.data.summary.token_reported_requests?number(query.data.summary.input_tokens):'Unavailable'],['Output including thinking',query.data.summary.token_reported_requests?number(query.data.summary.output_tokens):'Unavailable'],
        ['Reported total tokens',query.data.summary.token_reported_requests?number(query.data.summary.total_tokens):'Unavailable'],['Billable embedding characters',number(query.data.summary.billable_characters)],
        ['Average request latency',duration(query.data.summary.average_ms)],['P95 request latency',duration(query.data.summary.p95_ms)],
      ].map(([label,value])=><div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div><p className="muted">Token counts available for {query.data.summary.token_reported_requests} of {query.data.summary.requests} requests. Missing usage is not counted as zero usage. Mock/local inference has no provider API charge; hosting is excluded.</p></section>
      <section className="panel"><h2>By provider and model</h2>{query.data.models.length?<div className="table-scroll"><table><thead><tr><th>Provider / model</th><th>Requests</th><th>Succeeded / failed</th><th>Average / P95</th><th>Reported tokens</th><th>Estimated USD</th></tr></thead><tbody>{query.data.models.map(m=><tr key={`${m.provider}:${m.model}`}><td><strong>{m.provider}</strong><small>{m.model}</small></td><td>{m.requests}</td><td>{m.succeeded} / {m.failed}</td><td>{duration(m.average_ms)}<small>P95 {duration(m.p95_ms)}</small></td><td>{m.token_reported_requests?number(m.total_tokens):'Unavailable'}<small>{m.token_reported_requests} reporting usage</small></td><td>{cost(m.cost_usd)}<small>{m.unpriced_requests} unpriced</small></td></tr>)}</tbody></table></div>:<p className="muted">No matching providers in this period.</p>}</section>
      <section className="panel"><div className="analytics-tabs" role="group" aria-label="Activity view"><Button variant={tab==='requests'?'default':'outline'} onClick={()=>setTab('requests')} aria-pressed={tab==='requests'}>Model requests</Button><Button variant={tab==='runs'?'default':'outline'} onClick={()=>setTab('runs')} aria-pressed={tab==='runs'}>Claim runs</Button></div><h2>{tab==='requests'?'Recent model requests':'Recent claim runs'}</h2><p className="muted">{tab==='requests'?'Latest 200 requests; totals cover the entire selected period.':'Latest 100 completed claim runs, including failures and retries.'}</p>{tab==='requests'?<DataTable data={query.data.requests} columns={requestColumns} label="AI requests"/>:<DataTable data={query.data.recent_runs} columns={runColumns} label="claim runs"/>}</section>
      <section className="panel analytics-notes"><h2>How these numbers are calculated</h2>{query.data.notes.map(note=><p key={note}>{note}</p>)}<a href={query.data.price_source} target="_blank" rel="noreferrer">Provider pricing source</a><small>Default rate card checked {query.data.pricing_checked_at}. Configure AI_COST_RATES for different models or your contracted rates.</small></section>
    </>}
  </>
}
