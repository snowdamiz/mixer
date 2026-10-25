import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';
import {mkdtemp,rm,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {killOwnedWorkerd,selectOwnedWorkerd} from './owned-workerd-identity.mjs';
const require=createRequire(new URL('../../../../hosted-worker-controller/package.json',import.meta.url));
const {Miniflare,Log,LogLevel}=require('miniflare'),workerd=require('workerd').default;
export const cleanup=[];
export const token=Buffer.alloc(32,0x31).toString('base64url');
export const sha=s=>createHash('sha256').update(s).digest('hex');
export const makeIdentity=r=>({namespaceGeneration:'a'.repeat(64),environmentId:r.environment_id,poolId:r.pool_id,controllerId:r.controller_id,platform:r.ref.platform,operationKey:sha(JSON.stringify(['mixer-worker-controller-do-v1',r.environment_id,r.pool_id,r.controller_id,r.operation_id])),operationId:r.operation_id,immutableSha256:r.immutable_sha256});
function owned(){const p=spawnSync('/bin/ps',['-axo','pid=,ppid=,comm='],{encoding:'utf8',timeout:5000,maxBuffer:8388608});if(p.status!==0)throw new Error('process_observation');const processes=p.stdout.trim().split('\n').map(line=>{const m=line.trim().match(/^(\d+)\s+(\d+)\s+(.+)$/);if(!m)throw new Error('process_row');return {pid:Number(m[1]),parentPid:Number(m[2]),command:m[3]};}).filter(x=>x.pid!==p.pid);return selectOwnedWorkerd({ownerPid:process.pid,executable:workerd,platform:process.platform,processes});}
const gone=pid=>{try{process.kill(pid,0);return false;}catch(e){if(e.code==='ESRCH')return true;throw e;}};
export async function harness({registryMode='normal',outerMode='normal',bodyDelay=0,production=false,pendingConfig}={}){
 const persist=await mkdtemp(join(tmpdir(),'mixer-pending-entry-owned-'));
 const options={modules:true,scriptPath:resolve(import.meta.dirname,production?'../dist/src/index.js':'../dist/test/entry-worker.js'),modulesRules:[{type:'ESModule',include:['**/*.js'],fallthrough:true},{type:'Text',include:['**/*.sql'],fallthrough:true}],compatibilityDate:'2026-07-30',durableObjects:{OPERATIONS:{className:production?'MixerWorkerOperation':'EntryOperation',useSQLite:true},PENDING_REGISTRY:{className:production?'MixerPendingRegistryShard':'EntryRegistry',useSQLite:true},PENDING_AUDIT:{className:'MixerPendingAuditCoordinator',useSQLite:true},...(!production?{FOREIGN_OPERATIONS:{className:'ForeignOperation',useSQLite:true}}:{})},durableObjectsPersist:persist,bindings:{MIXER_PRINCIPAL:JSON.stringify({environment_id:'development',pool_id:'native',controller_id:'controller-1',platforms:['ios','android']}),MIXER_POOL_TOKEN_SHA256:sha(token),MIXER_PENDING_CONFIG:pendingConfig??JSON.stringify({generation:'a'.repeat(64),operationsNamespace:'entry-operation-test',registryNamespace:'entry-registry-test'}),REGISTRY_MODE:registryMode,OUTER_MODE:outerMode,BODY_DELAY:String(bodyDelay)},log:new Log(LogLevel.ERROR)};
 let mf=new Miniflare(options),closed=false;const identities=[];
 try{await mf.ready;identities.push(owned());}catch(e){await mf.dispose().catch(()=>{});await rm(persist,{recursive:true,force:true});cleanup.push({persist,setupFailed:true,storageRemoved:true});throw e;}
 async function call(action,arg={}){const response=await mf.dispatchFetch('https://entry.test/__entry/control',{method:'POST',headers:{'content-type':'application/json',authorization:'Bearer '+token},body:JSON.stringify({action,...arg})});return response.json();}
 return {call,persist,
  async command(r,extra={}){if(!production)return call('command',{r,...extra});const response=await mf.dispatchFetch('https://entry.test/internal/mixer-build-worker/v1',{method:'POST',headers:{'content-type':'application/json',authorization:'Bearer '+token},body:JSON.stringify(r)});return {status:response.status,headers:Object.fromEntries(response.headers),body:await response.json()};},
  async scheduled(){const w=await mf.getWorker();return w.scheduled({cron:'* * * * *',scheduledTime:Date.now()});},
  async restart(hard=false){if(hard)cleanup.push({kind:'SIGKILL',...killOwnedWorkerd(workerd)});await mf.dispose().catch(()=>{});mf=new Miniflare(options);await mf.ready;identities.push(owned());},
  async close(){if(closed)return;closed=true;await mf.dispose();await rm(persist,{recursive:true,force:true});const absent=await stat(persist).then(()=>false,e=>e.code==='ENOENT');const processesAbsent=identities.every(i=>gone(i.pid));cleanup.push({persist,disposed:true,storageRemoved:absent,ownedProcesses:identities,allOwnedPidsAbsent:processesAbsent,ownedTaskCancellationClaimed:false});if(!processesAbsent||!absent)throw new Error('cleanup_failed');}
 };
}

export {owned as observeOwned,gone as processGone};
