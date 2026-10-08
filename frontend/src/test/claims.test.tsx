import { describe, it, expect, vi, beforeEach } from 'vitest'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClaimQueue } from '../features/claims/ClaimQueue'
import { ClaimDetail as ClaimDetailScreen, ClaimFacts } from '../features/claims/ClaimDetail'
import { ReviewDetail } from '../features/reviews/Reviews'
import { ClaimsAssistant } from '../components/ClaimsAssistant'
import { ActionFeedback } from '../components/ActionFeedback'
import { api } from '../api/client'
import type { ClaimDetail } from '../types/claims'
vi.mock('../api/client',()=>({api:{claims:vi.fn(),batch:vi.fn(),activeJobs:vi.fn(),batchStatus:vi.fn(),chat:vi.fn(),decide:vi.fn(),review:vi.fn(),claim:vi.fn(),memory:vi.fn()}}))
beforeEach(()=>{sessionStorage.clear();vi.clearAllMocks();vi.mocked(api.activeJobs).mockResolvedValue({jobs:[],worker_available:true})})
function wrap(component:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{component}</QueryClientProvider>)}
const claim:ClaimDetail={id:'CLM-003',title:'Taxi',employee:{name:'Alex',email:'alex@example.test',department:'Sales'},submitted_date:'2026-01-02',amount:'62',currency:'USD',claim_type:'expense',status:'pending_manager_review',version:2,lines:[],assessment:{id:'a',claim_version:1,data:{confidence:.9,findings:['receipt_required'],evidence_ids:[],summary:'Missing receipt',unresolved_questions:['Please provide receipt']}},policy:{id:'p',name:'Expense policy',text:'Receipts required',currency:'USD',auto_accept:true,auto_reject:true,rules:[]},findings:[],evidence:[],history:[],executions:[],outcome:null,review:null}
describe('claims UI',()=>{
 it('shows loading',()=>{vi.mocked(api.claims).mockReturnValue(new Promise(()=>{}));wrap(<ClaimQueue/>);expect(screen.getByRole('status')).toHaveTextContent('Loading')})
 it('shows API errors',async()=>{vi.mocked(api.claims).mockRejectedValue(new Error('Backend unavailable'));wrap(<ClaimQueue/>);expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable')})
 it('links claims and displays status',async()=>{vi.mocked(api.claims).mockResolvedValue([claim]);wrap(<ClaimQueue/>);expect(await screen.findByRole('link',{name:/CLM-003/})).toHaveAttribute('href','#/claims/CLM-003')})
 it('separates facts, policy, findings and interpretation',()=>{render(<ClaimFacts claim={claim}/>);for(const name of ['Source facts','Applicable policy','Evidence','Policy facts','AI fact summary'])expect(screen.getByRole('heading',{name})).toBeInTheDocument();expect(screen.getByText('Please provide receipt')).toBeInTheDocument()})
 it('requires rationale for manager decisions',async()=>{vi.mocked(api.review).mockResolvedValue({id:'r',claim_id:claim.id,claim,status:'open',active:true,assigned_role:'manager',reason:'Missing evidence',evidence_ids:[],unresolved_questions:[],decisions:[]});wrap(<ReviewDetail id="r"/>);expect(await screen.findByRole('button',{name:'Accept'})).toBeDisabled();expect(screen.getByRole('button',{name:'Reject'})).toBeDisabled();expect(screen.getByRole('button',{name:'Investigate'})).toBeDisabled()})
})

describe('action feedback and assistant',()=>{
 it('explains that fact summary awaits a manager decision',()=>{render(<ActionFeedback claim={claim}/>);expect(screen.getByRole('status')).toHaveTextContent('Fact summary ready');expect(screen.getByRole('status')).toHaveTextContent('awaiting review')})
 it('sends a grounded question and shows cited answer',async()=>{vi.mocked(api.chat).mockResolvedValue({answer:'A receipt is missing.',sources:['CLM-003'],provider:'mock',read_only:true});wrap(<ClaimsAssistant claimId="CLM-003"/>);await userEvent.click(screen.getByRole('button',{name:'Ask assistant'}));await userEvent.type(screen.getByRole('textbox',{name:'Ask the claims assistant'}),'What evidence is missing?');await userEvent.click(screen.getByRole('button',{name:'Send message'}));expect(await screen.findByText('A receipt is missing.')).toBeInTheDocument();expect(api.chat).toHaveBeenCalledWith('What evidence is missing?','CLM-003',[]);expect(screen.getByRole('link',{name:'CLM-003'})).toHaveAttribute('href','#/claims/CLM-003')})
 it('reports failed batch jobs rather than falsely reporting acceptance',async()=>{vi.mocked(api.claims).mockResolvedValue([{...claim,status:'submitted'}]);vi.mocked(api.batch).mockResolvedValue({batch_id:'batch',jobs:[{claim_id:'CLM-003',job_id:'assess:batch:CLM-003'}]});vi.mocked(api.batchStatus).mockResolvedValue({worker_available:true,jobs:[{job_id:'assess:batch:CLM-003',status:'failed',result:null,error:'Assessment failed safely.'}]});wrap(<ClaimQueue/>);await userEvent.click(await screen.findByRole('button',{name:'Run'}));expect(await screen.findByRole('heading',{name:'Batch processing complete'})).toBeInTheDocument();expect(screen.getByText('Assessment failed safely.')).toBeInTheDocument();expect(screen.getByText('failed',{exact:true})).toBeInTheDocument()})
})


describe('batch demo controls',()=>{
 it('transitions Run to Running to Finished',async()=>{
  vi.mocked(api.claims).mockResolvedValue([{...claim,status:'submitted'}])
  let finish!: (value: Awaited<ReturnType<typeof api.batchStatus>>)=>void
  vi.mocked(api.batch).mockResolvedValue({batch_id:'state',jobs:[{claim_id:'CLM-003',job_id:'assess:state:CLM-003'}]})
  vi.mocked(api.batchStatus).mockReturnValue(new Promise(resolve=>{finish=resolve}))
  wrap(<ClaimQueue/>)
  await userEvent.click(await screen.findByRole('button',{name:'Run'}))
  expect(await screen.findByRole('button',{name:'Running'})).toBeDisabled()
  finish({worker_available:true,jobs:[{job_id:'assess:state:CLM-003',status:'succeeded',result:{claim_id:'CLM-003',status:'pending_manager_review'},error:null}]})
  expect(await screen.findByRole('button',{name:'Finished'})).toBeDisabled()
 })
 it('puts a visible assistant in claim detail and removes individual processing',async()=>{
  vi.mocked(api.claim).mockResolvedValue(claim)
  vi.mocked(api.memory).mockResolvedValue([])
  wrap(<ClaimDetailScreen id="CLM-003"/>)
  expect(await screen.findByRole('heading',{name:'Ask about this claim'})).toBeVisible()
  expect(screen.getByRole('textbox',{name:'Ask the claims assistant'})).toBeVisible()
  expect(screen.queryByRole('button',{name:'Assess & process'})).not.toBeInTheDocument()
 })
})


it('recovers active jobs without needing browser storage',async()=>{
 vi.mocked(api.claims).mockResolvedValue([{...claim,status:'submitted'}])
 vi.mocked(api.activeJobs).mockResolvedValue({worker_available:true,jobs:[{job_id:'assess:CLM-003',claim_id:'CLM-003'}]})
 vi.mocked(api.batchStatus).mockResolvedValue({worker_available:true,jobs:[{job_id:'assess:CLM-003',status:'in_progress',result:null,error:null}]})
 wrap(<ClaimQueue/>)
 expect(await screen.findByRole('button',{name:'Running'})).toBeDisabled()
 expect(await screen.findByText('1 running · 0 queued')).toBeVisible()
 expect(api.batch).not.toHaveBeenCalled()
})
