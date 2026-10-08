import { useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClipboardList, ShieldCheck, Building2 } from 'lucide-react'
import { ClaimQueue } from './features/claims/ClaimQueue'
import { ClaimDetail } from './features/claims/ClaimDetail'
import { ReviewQueue, ReviewDetail } from './features/reviews/Reviews'
const client=new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:true}}})
function Workspace(){
  const [path,setPath]=useState(window.location.hash.slice(1)||'/claims')
  useEffect(()=>{const update=()=>{setPath(window.location.hash.slice(1)||'/claims');window.scrollTo(0,0)};window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update)},[])
  const segments=path.split('/').filter(Boolean)
  const page=segments[0]==='reviews'?(segments[1]?<ReviewDetail key={segments[1]} id={segments[1]}/>:<ReviewQueue/>):(segments[1]?<ClaimDetail key={segments[1]} id={segments[1]}/>:<ClaimQueue/>)
  return <div className="workspace"><aside><div className="brand"><Building2 size={22}/><div>Claims desk<small>Enterprise operations</small></div></div><nav aria-label="Main navigation"><a className={segments[0]!=='reviews'?'active':''} href="#/claims"><ClipboardList size={18}/> Claim queue</a><a className={segments[0]==='reviews'?'active':''} href="#/reviews"><ShieldCheck size={18}/> Manager review</a></nav><div className="sidebar-footer">Week 4 reference<small>Local workspace · Trusted manager</small></div></aside><div className="content"><header><span>Expense management</span><span className="environment">LOCAL REFERENCE</span></header><main>{page}</main><footer>Evidence before interpretation. Every decision has a record.</footer></div></div>
}
export default function App(){return <QueryClientProvider client={client}><Workspace/></QueryClientProvider>}
