import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve, join } from 'node:path'
import { spawn, spawnSync } from 'node:child_process'
const directory=mkdtempSync(join(tmpdir(),'claims-e2e-'))
const cwd=resolve('../backend')
const python=join(cwd,'.venv/bin/python')
const vertex=process.env.DEMO_TEST_VERTEX==='1'
const env={...process.env,DATABASE_URL:`sqlite:///${join(directory,'claims.db')}`,DECISION_MODE:'autonomous',RAG_ENABLED:vertex?'true':'false',LLM_PROVIDER:vertex?'vertex':'mock',LLM_MODEL:vertex?'gemini-2.5-flash':'e2e-mock',ARQ_QUEUE_NAME:`claims-e2e-${directory.split('/').at(-1)}`}
for(const args of [['-m','alembic','upgrade','head'],['-m','app.seed'],...(vertex?[['-m','app.rag.index']]:[])]){
 const result=spawnSync(python,args,{cwd,env,stdio:'inherit'})
 if(result.status!==0){rmSync(directory,{recursive:true,force:true});process.exit(result.status ?? 1)}
}
const worker=spawn(python,['-m','arq','app.jobs.worker.WorkerSettings'],{cwd,env,stdio:'inherit'})
const child=spawn(python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001'],{cwd,env,stdio:'inherit'})
let stopped=false
const cleanup=()=>{if(!stopped){stopped=true;child.kill('SIGTERM');worker.kill('SIGTERM')}}
process.on('SIGTERM',cleanup);process.on('SIGINT',cleanup)
child.on('exit',code=>{worker.kill('SIGTERM');rmSync(directory,{recursive:true,force:true});process.exit(code ?? 0)})
