import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {mkdtemp,rm,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';
import {killOwnedWorkerd,selectOwnedWorkerd} from '../../../../hosted-worker-controller/test/owned-workerd-identity.mjs';
const require=createRequire(resolve(import.meta.dirname,'../../../../hosted-worker-controller/package.json'));
const {Miniflare,Log,LogLevel}=require('miniflare'),executable=require('workerd').default;
export const cleanup=[];
function observe(){const p=spawnSync('/bin/ps',['-axo','pid=,ppid=,comm='],{encoding:'utf8',timeout:5000,maxBuffer:8388608});if(p.status!==0)throw new Error('review_process_table');const rows=p.stdout.split('\n').filter(s=>s.trim()).map(s=>{const m=s.trim().match(/^(\d+)\s+(\d+)\s+(.+)$/);if(!m)throw new Error('review_process_row');return {pid:Number(m[1]),parentPid:Number(m[2]),command:m[3]};}).filter(r=>r.pid!==p.pid);return selectOwnedWorkerd({ownerPid:process.pid,executable,platform:process.platform,processes:rows});}
function absent(pid){try{process.kill(pid,0);return false;}catch(e){if(e.code==='ESRCH')return true;throw e;}}
export async function harness(){const persist=await mkdtemp(join(tmpdir(),'mixer-pending-correction-review-owned-')),identities=[];
 const options={modules:true,scriptPath:resolve(import.meta.dirname,'../dist/test/worker.js'),modulesRules:[{type:'ESModule',include:['**/*.js'],fallthrough:true},{type:'Text',include:['**/*.sql'],fallthrough:true}],compatibilityDate:'2026-07-30',durableObjects:{PENDING_REGISTRY:{className:'ReviewRegistry',useSQLite:true},PENDING_AUDIT:{className:'ReviewAudit',useSQLite:true},OPERATIONS:{className:'ReviewRecovery',useSQLite:true}},durableObjectsPersist:persist,bindings:{MIXER_PENDING_CONFIG:JSON.stringify({generation:'a'.repeat(64),operationsNamespace:'independent-review-operations',registryNamespace:'independent-review-registry'})},log:new Log(LogLevel.ERROR)};
 let mf=new Miniflare(options),closed=false;
 try{await mf.ready;identities.push(observe());}catch(error){await mf.dispose().catch(()=>{});await rm(persist,{recursive:true,force:true});cleanup.push({persist,setupFailed:true,storageRemoved:await stat(persist).then(()=>false,e=>e.code==='ENOENT')});throw error;}
 return {persist,async call(action,a={}){return (await mf.dispatchFetch('https://excluded.test/__excluded/review',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,...a})})).json();},async scheduled(){return (await mf.getWorker()).scheduled({cron:'* * * * *',scheduledTime:Date.now()});},async restart(){cleanup.push({kind:'SIGKILL',...killOwnedWorkerd(executable)});await mf.dispose().catch(()=>{});mf=new Miniflare(options);await mf.ready;identities.push(observe());},async close(){if(closed)return;closed=true;await mf.dispose();await rm(persist,{recursive:true,force:true});const storageRemoved=await stat(persist).then(()=>false,e=>e.code==='ENOENT'),allOwnedPidsAbsent=identities.every(i=>absent(i.pid));cleanup.push({persist,disposed:true,storageRemoved,ownedProcesses:identities,allOwnedPidsAbsent,ownedTaskCancellationClaimed:false});if(!storageRemoved||!allOwnedPidsAbsent)throw new Error('review_cleanup_failed');}};
}
