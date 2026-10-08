import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { MessageCircle, X, Send } from 'lucide-react'
import { api } from '../api/client'
import type { ChatTurn } from '../types/claims'
import { Button } from './ui/button'
import { Input } from './ui/input'

type DisplayTurn = ChatTurn & {sources?: string[]}
export function ClaimsAssistant({claimId, embedded=false}: {claimId?: string; embedded?: boolean}) {
  const [open,setOpen]=useState(false)
  const [message,setMessage]=useState('')
  const [turns,setTurns]=useState<DisplayTurn[]>([])
  const log=useRef<HTMLDivElement>(null)
  useEffect(()=>{if(log.current)log.current.scrollTop=log.current.scrollHeight},[turns])
  const mutation=useMutation({mutationFn:({text,history}:{text:string;history:ChatTurn[]})=>api.chat(text,claimId,history),onSuccess:reply=>setTurns(previous=>[...previous,{role:'assistant',content:reply.answer,sources:reply.sources}])})
  function send(text: string) {
    if(!text.trim() || mutation.isPending) return
    const history=turns.slice(-8).map(({role,content})=>({role,content}))
    setTurns(previous=>[...previous,{role:'user',content:text.trim()}])
    setMessage('')
    mutation.mutate({text:text.trim(),history})
  }
  return <div className={embedded ? "assistant-inline" : "assistant-anchor"}>{(open || embedded) && <section className="assistant-panel" aria-label="Claims assistant"><div className="assistant-heading"><div><h2>{embedded ? "Ask about this claim" : "Claims assistant"}</h2><small>{claimId ? `Explaining ${claimId}` : 'Explaining your claim queue'} · Read only</small></div>{!embedded && <Button variant="ghost" size="icon" aria-label="Close assistant" onClick={()=>setOpen(false)}><X size={18}/></Button>}</div><div className="assistant-messages" ref={log} role="log" aria-live="polite">{!turns.length && <p>I can explain claim status, policy and evidence. The AI worker investigates claims and records acceptance or rejection automatically.</p>}{turns.map((turn,index)=><article key={index} className={`chat-${turn.role}`}><strong>{turn.role==='user'?'You':'Assistant'}</strong><p>{turn.content}</p>{turn.sources?.length ? <small>Sources: {turn.sources.map(source=>source.startsWith('CLM-')?<a key={source} href={`#/claims/${source}`}>{source} </a>:<span key={source}>{source} </span>)}</small> : null}</article>)}{mutation.isPending && <p role="status">Finding an answer…</p>}{mutation.error && <p role="alert">{mutation.error.message}</p>}</div><div className="assistant-suggestions">{(claimId?['What evidence is missing?','Explain this claim’s decision']:['Summarize the queue','Which claims were rejected?']).map(text=><button key={text} disabled={mutation.isPending} onClick={()=>send(text)}>{text}</button>)}</div><form onSubmit={event=>{event.preventDefault();send(message)}}><Input aria-label="Ask the claims assistant" autoFocus={!embedded} placeholder="Ask about claims or policy…" value={message} maxLength={1000} onChange={event=>setMessage(event.target.value)}/><Button type="submit" size="icon" aria-label="Send message" disabled={!message.trim() || mutation.isPending}><Send size={16}/></Button></form></section>}{!embedded && <Button className="assistant-toggle" onClick={()=>setOpen(!open)} aria-expanded={open}><MessageCircle size={18}/> {open?'Hide assistant':'Ask assistant'}</Button>}</div>
}
