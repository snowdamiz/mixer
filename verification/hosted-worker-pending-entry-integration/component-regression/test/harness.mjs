import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {mkdtemp,rm,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';
import {killOwnedWorkerd,selectOwnedWorkerd} from '../../../../hosted-worker-controller/test/owned-workerd-identity.mjs';
const require=createRequire(resolve(import.meta.dirname,'../../../../hosted-worker-controller/package.json'));
const {Miniflare,Log,LogLevel}=require('miniflare');
const workerd=require('workerd').default;
export const cleanup=[];
function owned(){const p=spawnSync('/bin/ps',['-axo','pid=,ppid=,comm='],{encoding:'utf8',timeout:5000,maxBuffer:8388608});if(p.status!==0)throw new Error('process_observation_failed');const processes=p.stdout.trim().split('\n').map(line=>{const m=line.trim().match(/^(\d+)\s+(\d+)\s+(.+)$/);if(!m)throw new Error('process_row');return {pid:Number(m[1]),parentPid:Number(m[2]),command:m[3]};}).filter(x=>x.pid!==p.pid);return selectOwnedWorkerd({ownerPid:process.pid,executable:workerd,platform:process.platform,processes});}
function gone(pid){try{process.kill(pid,0);return false;}catch(e){if(e.code==='ESRCH')return true;throw e;}}
export async function harness(){
 const persist=await mkdtemp(join(tmpdir(),'mixer-pending-components-owned-'));
 const options={modules:true,scriptPath:resolve(import.meta.dirname,'../dist/test/worker.js'),modulesRules:[{type:'ESModule',include:['**/*.js'],fallthrough:true},{type:'Text',include:['**/*.sql'],fallthrough:true}],compatibilityDate:'2026-07-30',durableObjects:{PENDING_REGISTRY:{className:'TestRegistry',useSQLite:true},PENDING_AUDIT:{className:'TestAudit',useSQLite:true},OPERATIONS:{className:'FixtureRecovery',useSQLite:true}},durableObjectsPersist:persist,bindings:{MIXER_PENDING_CONFIG:JSON.stringify({generation:'a'.repeat(64),operationsNamespace:'component-operation-test',registryNamespace:'component-registry-test'})},log:new Log(LogLevel.ERROR)};
 let mf=new Miniflare(options),closed=false;const identities=[];
 try{await mf.ready;identities.push(owned());}catch(e){await mf.dispose().catch(()=>{});await rm(persist,{recursive:true,force:true});cleanup.push({persist,setupFailed:true,storageRemoved:true});throw e;}
 async function call(action,arg={}){const r=await mf.dispatchFetch('https://excluded.test/__test/components',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,...arg})});return r.json();}
 return {call,persist,
  async scheduled(){const w=await mf.getWorker();return w.scheduled({cron:'* * * * *',scheduledTime:Date.now()});},
  async publicFetch(){return (await mf.dispatchFetch('https://excluded.test/internal/mixer-build-worker/v1',{method:'POST',body:'{}'})).status;},
  async restart(hard=false){if(hard){const identity=killOwnedWorkerd(workerd);cleanup.push({kind:'SIGKILL',...identity});}await mf.dispose().catch(()=>{});mf=new Miniflare(options);await mf.ready;identities.push(owned());},
  async close(){if(closed)return;closed=true;await mf.dispose();await rm(persist,{recursive:true,force:true});const absent=await stat(persist).then(()=>false,e=>e.code==='ENOENT');const processesAbsent=identities.every(i=>gone(i.pid));cleanup.push({persist,disposed:true,storageRemoved:absent,ownedProcesses:identities,allOwnedPidsAbsent:processesAbsent,ownedTaskCancellationClaimed:false});if(!processesAbsent)throw new Error('owned_process_cleanup_failed');if(!absent)throw new Error('storage_cleanup_failed');}
 };
}
