import { useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { ClipboardList, ShieldCheck, Building2 } from 'lucide-react'
import { api } from './api/client'
import { ClaimsAssistant } from './components/ClaimsAssistant'
import { ClaimQueue } from './features/claims/ClaimQueue'
import { ClaimDetail } from './features/claims/ClaimDetail'
import { ReviewQueue, ReviewDetail } from './features/reviews/Reviews'
const client=new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:true}}})
function Workspace(){
  const [path,setPath]=useState(window.location.hash.slice(1)||'/claims')
  useEffect(()=>{const update=()=>{setPath(window.location.hash.slice(1)||'/claims');window.scrollTo(0,0)};window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update)},[])
  const segments=path.split('/').filter(Boolean)
  const reviewContext=useQuery({queryKey:['review',segments[1]],queryFn:()=>api.review(segments[1]),enabled:segments[0]==='reviews' && Boolean(segments[1])})
  const selectedClaim=segments[0]==='claims'?segments[1]:reviewContext.data?.claim.id
  const page=segments[0]==='reviews'?(segments[1]?<ReviewDetail key={segments[1]} id={segments[1]}/>:<ReviewQueue/>):(segments[1]?<ClaimDetail key={segments[1]} id={segments[1]}/>:<ClaimQueue/>)
  return <div className="workspace"><aside><div className="brand"><Building2 size={22}/><div>Claims desk<small>Enterprise operations</small></div></div><nav aria-label="Main navigation"><a className={segments[0]!=='reviews'?'active':''} href="#/claims"><ClipboardList size={18}/> Claim queue</a><a className={segments[0]==='reviews'?'active':''} href="#/reviews"><ShieldCheck size={18}/> Manager review</a></nav><div className="sidebar-footer">Week 1<small>Local workspace · Trusted manager</small></div></aside><div className="content"><header><span>Expense management</span><span className="environment">WEEK 1</span></header><main>{page}</main><footer>Evidence before interpretation. Every expense is decided by a manager.</footer>{segments[0]!=='claims' || !selectedClaim ? <ClaimsAssistant key={path+':'+(selectedClaim ?? '')} claimId={selectedClaim}/> : null}</div></div>
}
export default function App(){return <QueryClientProvider client={client}><Workspace/></QueryClientProvider>}
