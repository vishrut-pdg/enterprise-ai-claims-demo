import { useQuery, useMutation } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import { api } from '../../api/client'
import type { Claim } from '../../types/claims'
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
  const query=useQuery({queryKey:['claims'],queryFn:api.claims})
  const batch=useMutation({mutationFn:api.batch})
  if(query.isPending)return <p role="status">Loading claim queue…</p>
  if(query.error)return <p role="alert">{query.error.message}</p>
  const claims=query.data
  return <><div className="page-heading"><div><p className="eyebrow">CLAIMS OPERATIONS</p><h1>Claim queue</h1><p className="muted">Review facts, assess against policy and track each decision.</p></div><Button variant="outline" disabled={batch.isPending || !claims.some(c=>c.status==='submitted')} onClick={()=>batch.mutate(claims.filter(c=>c.status==='submitted').map(c=>c.id))}>Queue batch assessment</Button></div>
  <div className="metrics">{[['All claims',claims.length],['Awaiting assessment',claims.filter(c=>c.status==='submitted').length],['Manager review',claims.filter(c=>['pending_manager_review','information_requested'].includes(c.status)).length],['Completed',claims.filter(c=>['accepted','rejected'].includes(c.status)).length]].map(([label,count])=><div key={label}><span>{label}</span><strong>{count}</strong></div>)}</div>
  {batch.error && <p role="alert">{batch.error.message}</p>}{batch.isSuccess && <p role="status">Batch submitted. Refresh the queue after worker processing.</p>}
  <section className="panel"><DataTable data={claims} columns={columns} label="claims"/></section></>
}
