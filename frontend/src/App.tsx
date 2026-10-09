import { AIUsage } from './features/analytics/AIUsage'
import { useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClipboardList, History, Building2, ChartNoAxesCombined } from 'lucide-react'
import { ClaimsAssistant } from './components/ClaimsAssistant'
import { ClaimQueue } from './features/claims/ClaimQueue'
import { ClaimDetail } from './features/claims/ClaimDetail'
import { DecisionHistory } from './features/claims/ClaimQueue'
const client=new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:true}}})
function Workspace(){
  const [path,setPath]=useState(window.location.hash.slice(1)||'/claims')
  useEffect(()=>{const update=()=>{setPath(window.location.hash.slice(1)||'/claims');window.scrollTo(0,0)};window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update)},[])
  const segments=path.split('/').filter(Boolean)
  const selectedClaim=segments[0]==='claims'?segments[1]:undefined
  const page=segments[0]==='analytics'?<AIUsage/>:segments[0]==='decisions'?<DecisionHistory/>:(segments[1]?<ClaimDetail key={segments[1]} id={segments[1]}/>:<ClaimQueue/>)
  return <div className="workspace"><aside><div className="brand"><Building2 size={22}/><div>Claims desk<small>Enterprise operations</small></div></div><nav aria-label="Main navigation"><a className={segments[0]==='claims'?'active':''} href="#/claims"><ClipboardList size={18}/> Claim queue</a><a className={segments[0]==='decisions'?'active':''} href="#/decisions"><History size={18}/> Decision history</a><a className={segments[0]==='analytics'?'active':''} href="#/analytics"><ChartNoAxesCombined size={18}/> AI usage & performance</a></nav><div className="sidebar-footer">Week 4<small>Autonomous AI · Accept or reject</small></div></aside><div className="content"><header><span>Expense management</span><span className="environment">WEEK 4</span></header><main>{page}</main><footer>Evidence before interpretation. Every decision has a record.</footer>{segments[0]!=='claims' || !selectedClaim ? <ClaimsAssistant key={path+':'+(selectedClaim ?? '')} claimId={selectedClaim}/> : null}</div></div>
}
export default function App(){return <QueryClientProvider client={client}><Workspace/></QueryClientProvider>}
