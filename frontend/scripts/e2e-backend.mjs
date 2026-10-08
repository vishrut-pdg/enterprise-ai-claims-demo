import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve, join } from 'node:path'
import { spawn, spawnSync } from 'node:child_process'
const directory=mkdtempSync(join(tmpdir(),'claims-e2e-'))
const cwd=resolve('../backend')
const python=join(cwd,'.venv/bin/python')
const env={...process.env,DATABASE_URL:`sqlite:///${join(directory,'claims.db')}`,LLM_PROVIDER:'mock',LLM_MODEL:'e2e-mock'}
for(const args of [['-m','alembic','upgrade','head'],['-m','app.seed']]){
 const result=spawnSync(python,args,{cwd,env,stdio:'inherit'})
 if(result.status!==0){rmSync(directory,{recursive:true,force:true});process.exit(result.status ?? 1)}
}
const child=spawn(python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001'],{cwd,env,stdio:'inherit'})
let stopped=false
const cleanup=()=>{if(!stopped){stopped=true;child.kill('SIGTERM')}}
process.on('SIGTERM',cleanup);process.on('SIGINT',cleanup)
child.on('exit',code=>{rmSync(directory,{recursive:true,force:true});process.exit(code ?? 0)})
