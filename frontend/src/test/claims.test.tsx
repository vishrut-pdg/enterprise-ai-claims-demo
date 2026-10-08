import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClaimQueue } from '../features/claims/ClaimQueue'
import { ClaimFacts } from '../features/claims/ClaimDetail'
import { ReviewDetail } from '../features/reviews/Reviews'
import { api } from '../api/client'
import type { ClaimDetail } from '../types/claims'
vi.mock('../api/client',()=>({api:{claims:vi.fn(),batch:vi.fn(),review:vi.fn()}}))
function wrap(component:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{component}</QueryClientProvider>)}
const claim:ClaimDetail={id:'CLM-003',title:'Taxi',employee:{name:'Alex',email:'alex@example.test',department:'Sales'},submitted_date:'2026-01-02',amount:'62',currency:'USD',claim_type:'expense',status:'pending_manager_review',version:2,lines:[],assessment:{id:'a',claim_version:1,data:{recommendation:'investigate',confidence:.9,findings:['receipt_required'],evidence_ids:[],explanation:'Missing receipt',unresolved_questions:['Please provide receipt']}},policy:{id:'p',name:'Expense policy',text:'Receipts required',currency:'USD',auto_accept:true,auto_reject:true,rules:[]},findings:[],evidence:[],history:[],executions:[],outcome:null,review:null}
describe('claims UI',()=>{
 it('shows loading',()=>{vi.mocked(api.claims).mockReturnValue(new Promise(()=>{}));wrap(<ClaimQueue/>);expect(screen.getByRole('status')).toHaveTextContent('Loading')})
 it('shows API errors',async()=>{vi.mocked(api.claims).mockRejectedValue(new Error('Backend unavailable'));wrap(<ClaimQueue/>);expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable')})
 it('links claims and displays status',async()=>{vi.mocked(api.claims).mockResolvedValue([claim]);wrap(<ClaimQueue/>);expect(await screen.findByRole('link',{name:/CLM-003/})).toHaveAttribute('href','#/claims/CLM-003')})
 it('separates facts, policy, findings and interpretation',()=>{render(<ClaimFacts claim={claim}/>);for(const name of ['Source facts','Applicable policy','Evidence','Deterministic policy findings','AI assessment'])expect(screen.getByRole('heading',{name})).toBeInTheDocument();expect(screen.getByText('Please provide receipt')).toBeInTheDocument()})
 it('requires rationale for manager decisions',async()=>{vi.mocked(api.review).mockResolvedValue({id:'r',claim_id:claim.id,claim,status:'open',active:true,assigned_role:'manager',reason:'Missing evidence',evidence_ids:[],unresolved_questions:[],decisions:[]});wrap(<ReviewDetail id="r"/>);expect(await screen.findByRole('button',{name:'Accept'})).toBeDisabled();expect(screen.getByRole('button',{name:'Reject'})).toBeDisabled()})
})
