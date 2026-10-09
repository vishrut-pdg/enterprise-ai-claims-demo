import { describe, it, expect, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AIUsage } from '../features/analytics/AIUsage'
import { api } from '../api/client'
import type { AIAnalytics } from '../types/analytics'
vi.mock('../api/client',()=>({api:{analytics:vi.fn()}}))
function show(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><AIUsage/></QueryClientProvider>)}
const data:AIAnalytics={days:30,provider:null,currency:'USD',summary:{requests:1,succeeded:0,failed:1,success_rate:0,input_tokens:0,output_tokens:0,thinking_tokens:0,total_tokens:0,billable_characters:0,token_reported_requests:0,priced_requests:0,unpriced_requests:1,cost_usd:null,average_ms:100,p95_ms:100},claim_runs:{total:1,succeeded:0,failed:1,success_rate:0,average_ms:100,p95_ms:100},models:[],requests:[],recent_runs:[],history_limit:200,price_source:'https://cloud.google.com/vertex-ai/generative-ai/pricing',pricing_checked_at:'2026-10-09',notes:['Unknown usage is unavailable.']}
describe('AI usage page',()=>{
 it('shows loading and backend errors',async()=>{vi.mocked(api.analytics).mockRejectedValue(new Error('Analytics unavailable'));show();expect(screen.getByRole('status')).toHaveTextContent('Loading');expect(await screen.findByRole('alert')).toHaveTextContent('Analytics unavailable')})
 it('shows failures and unavailable cost instead of a false zero, filters and switches history',async()=>{vi.mocked(api.analytics).mockResolvedValue(data);show();expect(await screen.findByText('0 succeeded · 1 failed')).toBeVisible();expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(1);await userEvent.selectOptions(screen.getByLabelText('Period'),'0');await userEvent.selectOptions(screen.getByLabelText('Provider'),'vertex');expect(api.analytics).toHaveBeenCalledWith(0,'vertex');await userEvent.click(screen.getByRole('button',{name:'Claim runs'}));expect(screen.getByRole('heading',{name:'Recent claim runs'})).toBeVisible()})
 it('shows an empty state',async()=>{vi.mocked(api.analytics).mockResolvedValue({...data,summary:{...data.summary,requests:0}});show();expect(await screen.findByRole('heading',{name:'No AI activity yet'})).toBeVisible()})
})
