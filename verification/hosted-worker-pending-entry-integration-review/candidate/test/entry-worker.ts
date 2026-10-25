// EXCLUDED FINITE WORKER. Synthetic effects and controls never enter src closure.
import {DurableObject} from 'cloudflare:workers';
import entry from '../src/index.js';
import {MixerWorkerOperation,Env as BaseEnv} from '../src/operation.js';
import {OperationState} from '../src/operation-state.js';
import {MixerPendingRegistryShard} from '../src/pending-registry.js';
import {MixerPendingAuditCoordinator} from '../src/pending-audit.js';
import {Engine} from '../src/engine.js';
import {RegistryContext} from '../src/registry-context.js';
import {Clock} from '../src/clock.js';
import {Provider,Effect,ProviderObservation} from '../src/provider.js';
import {PendingIdentity,RegistrationReceipt,WakeTicket,RegistrationResult} from '../src/public-contract.js';
import {config,registryName,auditName,identity} from '../src/pending-types.js';
import {operationKey} from '../src/principal.js';
import {WireRequest} from '../src/wire.js';
interface Env extends BaseEnv {FOREIGN_OPERATIONS:DurableObjectNamespace;REGISTRY_MODE:string;OUTER_MODE:string;BODY_DELAY:string;RESTORE_DELAY:string}
const json=(v:unknown)=>new Response(JSON.stringify(v??{ok:true}),{headers:{'content-type':'application/json'}});
const delay=(ms:number)=>new Promise<void>(resolve=>setTimeout(resolve,ms));
let events:unknown[]=[];
export class EntryRegistry extends MixerPendingRegistryShard {
 async register(i:PendingIdentity):Promise<RegistrationResult>{
  const mode=(this.env as Env).REGISTRY_MODE;
  if(mode==='capacity'||mode==='conflict'||mode==='unavailable')return {status:mode};
  const r=await super.register(i);
  if(mode==='timeout'||mode==='late')await delay(mode==='timeout'?320:160);
  if(mode==='edge-delay')await delay(230);
  if((r.status==='registered'||r.status==='duplicate')&&['digest','generation','shard','record','extra'].includes(mode)){
   const p={...r.receipt};if(mode==='digest')p.identityDigest='b'.repeat(64);if(mode==='generation')p.namespaceGeneration='b'.repeat(64);if(mode==='shard')p.shard=(p.shard+1)%16;if(mode==='record')p.recordId='short';
   return mode==='extra'?{...r,extra:true} as RegistrationResult:{...r,receipt:p};
  }return r;
 }
}
export {MixerWorkerOperation,MixerPendingAuditCoordinator};
export class EntryOperation extends DurableObject<Env> {
 private state:OperationState;
 constructor(ctx:DurableObjectState,env:Env){super(ctx,env);const restoring=new Proxy(ctx,{get(target,key){if(key==='blockConcurrencyWhile')return (fn:()=>Promise<unknown>)=>ctx.blockConcurrencyWhile(async()=>{await delay(Number(env.RESTORE_DELAY||0));return fn();});const value=Reflect.get(target,key,target);return typeof value==='function'?value.bind(target):value;}});this.state=new OperationState(restoring,env,(_ledger,context)=>this.createEngine(context));}
 private get ledger(){return this.state.ledger;}
 private get engine(){return this.state.engine;}
 async fetch(request:Request){this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS entry_received(value TEXT NOT NULL)');const text=await request.clone().text();this.ctx.storage.sql.exec('INSERT INTO entry_received(value) VALUES(?)',JSON.stringify({text,headers:Object.fromEntries(request.headers)}));return this.state.fetch(request);}
 async enrollExisting(i:PendingIdentity){return this.state.enrollExisting(i);}
 async alarm(){return this.state.alarm();}
 private held:(()=>void)|null=null;
 protected resourceKind(platform:'ios'|'android'):'cloudflare-linux'|'external-macos'{return platform==='ios'?'external-macos':'cloudflare-linux';}
 private setting(){return this.ctx.storage.sql.exec<{value:string}>('SELECT value FROM entry_setting WHERE singleton=1').toArray()[0]?.value??'normal';}
 protected createEngine(context:RegistryContext):Engine{
  this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS entry_counts(kind TEXT PRIMARY KEY,n INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS entry_setting(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL)');
  this.count('engine');
  const clock:Clock={sample:()=>this.setting()==='clock-unavailable'?null:{lowerUs:1900000000000000n,upperUs:1900000000000001n,qualificationId:'entry-fixture-only'}};
  const observation=(e:Effect):ProviderObservation=>({identity:e.identity,state:'inert',instanceId:'entry-instance',bootId:'entry-boot',definitive:false,descendantsGone:false,launchesSettled:false,diagnosticSha256:'d'.repeat(64)});
  const provider:Provider={available:true,kind:p=>this.resourceKind(p),
   launchInert:async(e,signal)=>{this.count('launch');if(this.setting()==='hold')await new Promise<void>((resolve,reject)=>{this.held=resolve;signal.addEventListener('abort',()=>reject(new Error('fixture_abort')),{once:true});});return observation(e);},
   inspect:async e=>{this.count('inspect');return observation(e);},
   stop:async e=>{this.count('stop');return {...observation(e),state:'absent',instanceId:null,bootId:null,definitive:this.setting()!=='stop-pending',descendantsGone:this.setting()!=='stop-pending',launchesSettled:this.setting()!=='stop-pending'};}};
  return new Engine(this.ledger,clock,provider,{async verify(){return false;}},undefined,context);
 }
 private count(kind:string){this.ctx.storage.sql.exec('INSERT INTO entry_counts(kind,n) VALUES(?,1) ON CONFLICT(kind) DO UPDATE SET n=n+1',kind);}
 async recoverKnown(i:PendingIdentity,p:RegistrationReceipt,t:WakeTicket){this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS recovery_calls(value TEXT NOT NULL)');this.ctx.storage.sql.exec('INSERT INTO recovery_calls(value) VALUES(?)',JSON.stringify([i,p,t]));return this.state.recoverKnown(i,p,t);}
 async inspectFixture(){const tables=this.ctx.storage.sql.exec<{name:string}>("SELECT name FROM sqlite_master WHERE type='table'").toArray().map(x=>x.name);return {received:tables.includes('entry_received')?this.ctx.storage.sql.exec<{value:string}>('SELECT value FROM entry_received').toArray().map(x=>JSON.parse(x.value)):[],row:this.ledger.read(),fenced:this.ledger.fenced(),counts:tables.includes('entry_counts')?this.ctx.storage.sql.exec('SELECT * FROM entry_counts ORDER BY kind').toArray():[],recoveries:tables.includes('recovery_calls')?this.ctx.storage.sql.exec<{value:string}>('SELECT value FROM recovery_calls').toArray().map(x=>JSON.parse(x.value)):[],alarm:await this.ctx.storage.getAlarm()};}
 async settingFixture(value:string){this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS entry_setting(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL)');this.ctx.storage.sql.exec('INSERT INTO entry_setting(singleton,value) VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value',value);if(value==='release')this.held?.();}
 async mutateFixture(kind:string){
  if(kind==='malformed-receipt')this.ctx.storage.sql.exec("UPDATE operation SET registration_json='{}'");
  else if(kind==='missing-identity')this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=NULL');
  else if(kind==='extra-identity'){const r=this.ledger.read()!;this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=?',JSON.stringify({...JSON.parse(r.pending_identity_json!),extra:true}));}
  else if(kind==='history')this.ctx.storage.sql.exec("UPDATE operation SET registry_ack_version='9223372036854775807'");
  else if(kind==='max')this.ctx.storage.sql.exec("UPDATE operation SET state_version='9223372036854775807',registry_ack_version='9223372036854775807',track_outbox_json=NULL");
  else if(kind==='migration'){this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=NULL,registration_json=NULL,track_outbox_json=NULL,registry_ack_version=\'0\',effect_barrier_version=NULL,claim_barrier_version=NULL,quarantined=1');}
  else if(kind==='bad-binding'){const row=this.ledger.read()!;this.ctx.storage.sql.exec('UPDATE operation SET binding=?',row.binding+' ');}
  else if(kind==='wrong-immutable-identity'){const row=this.ledger.read()!;this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=?',JSON.stringify({...JSON.parse(row.pending_identity_json!),immutableSha256:'b'.repeat(64)}));}
  else if(kind==='unquarantined-unenrolled')this.ctx.storage.sql.exec("UPDATE operation SET pending_identity_json=NULL,registration_json=NULL,track_outbox_json=NULL,registry_ack_version='0',effect_barrier_version=NULL,claim_barrier_version=NULL,quarantined=0");
  else if(kind==='delete-row')this.ctx.storage.sql.exec('DELETE FROM operation');
  else throw new Error('fixture_mutation');await this.ledger.sync();
 }
 async alarmFixture(){await this.ctx.storage.deleteAlarm();await this.state.alarm();}
 async dropAlarmFixture(){await this.ctx.storage.deleteAlarm();}
 async claimFixture(value:unknown){return this.engine?this.engine.claim(value as never):{granted:false};}
 async reportFixture(value:unknown){return this.engine?this.engine.report(value as never):'rejected';}
}
export class ForeignOperation extends EntryOperation {}
export default {
 async fetch(request:Request,env:Env):Promise<Response>{
  const path=new URL(request.url).pathname;
  if(!path.startsWith('/__entry/'))return entry.fetch(request,env);
  const arg=await request.json() as {action:string;r:WireRequest;i:PendingIdentity;p:RegistrationReceipt;t:WakeTicket;kind:string;value:string;target:string;payload:unknown;bodyText:string;headers:Record<string,string>};
  if(arg.action==='events')return json(events);
  if(arg.action==='production-probe'){const op=env.OPERATIONS.get(env.OPERATIONS.idFromName(await operationKey(arg.r))) as unknown as Record<string,(...a:unknown[])=>Promise<unknown>>;try{return json({result:await op[arg.kind]!(...(arg.payload as unknown[]??[]))});}catch(e){return json({rejected:true,message:String(e)});}}
  if(arg.action==='command'){
   const c=env.OUTER_MODE==='missing'?undefined:env.OUTER_MODE==='bad-generation'?JSON.stringify({...config(env),generation:'A'.repeat(64)}):env.OUTER_MODE==='changed-generation'?JSON.stringify({...config(env),generation:'b'.repeat(64)}):env.OUTER_MODE==='changed-namespace'?JSON.stringify({...config(env),operationsNamespace:'other'}):env.MIXER_PENDING_CONFIG;
   const wrapped={...env,MIXER_PENDING_CONFIG:c,OPERATIONS:{idFromName:(key:string)=>{events.push(['operation-id',key]);return env.OPERATIONS.idFromName(env.OUTER_MODE==='wrong-id'?'wrong':key);},get:(id:DurableObjectId)=>{events.push(['operation-get',id.toString()]);return env.OPERATIONS.get(id);}},PENDING_REGISTRY:{idFromName:(key:string)=>{events.push(['registry-id',key]);return env.PENDING_REGISTRY.idFromName(key);},get:(id:DurableObjectId)=>{const p=env.PENDING_REGISTRY.get(id) as unknown as EntryRegistry;return {register:async(i:PendingIdentity)=>{events.push(['register-start',i]);const r=await p.register(i);events.push(['register-ack',r]);return r;}};}}} as unknown as Env;
   const bytes=new TextEncoder().encode(arg.bodyText??JSON.stringify(arg.r));const d=Number(env.BODY_DELAY);let sent=false;
   const body=d?new ReadableStream<Uint8Array>({async pull(controller){if(sent)return;sent=true;await delay(d);controller.enqueue(bytes);controller.close();}}):bytes;
   const aborter=new AbortController();if(env.OUTER_MODE==='abort-before')aborter.abort();if(env.OUTER_MODE==='abort-during')setTimeout(()=>aborter.abort(),30);const started=performance.now();const response=await entry.fetch(new Request('https://entry.test/internal/mixer-build-worker/v1',{method:'POST',headers:arg.headers??{authorization:request.headers.get('authorization')??'','content-type':'application/json'},body,signal:aborter.signal}),wrapped);
   const entryElapsed=performance.now()-started;if(d)await delay(350);return json({status:response.status,entryElapsed,headers:Object.fromEntries(response.headers),body:await response.json()});
  }
  const key=arg.i?.operationKey??await operationKey(arg.r),id=env.OPERATIONS.idFromName(arg.target==='wrong'?'wrong':key),op=(arg.target==='foreign'?env.FOREIGN_OPERATIONS.get(env.FOREIGN_OPERATIONS.idFromName(key)):env.OPERATIONS.get(id)) as unknown as EntryOperation;
  if(arg.action==='inspect')return json(await op.inspectFixture());
  if(arg.action==='set')return json(await op.settingFixture(arg.value));
  if(arg.action==='mutate')return json(await op.mutateFixture(arg.kind));
  if(arg.action==='recover')return json(await op.recoverKnown(arg.i,arg.p,arg.t));
  if(arg.action==='enroll')return json(await op.enrollExisting(arg.i));
  if(arg.action==='claim')return json(await op.claimFixture(arg.payload));
  if(arg.action==='report')return json(await op.reportFixture(arg.payload));
  if(arg.action==='drop-alarm')return json(await op.dropAlarmFixture());
  if(arg.action==='alarm')return json(await op.alarmFixture());
  if(arg.action==='direct'){const response=await op.fetch(new Request('https://entry.test/internal/mixer-build-worker/v1',{method:'POST',headers:{authorization:request.headers.get('authorization')??'','content-type':'application/json'},body:JSON.stringify(arg.r)}));return json({status:response.status,body:await response.json()});}
  if(arg.action==='register'){const c=config(env),i=await identity(arg.i,c),port=env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(c,i.shard))) as unknown as EntryRegistry;return json(await port.register(i.value));}
  if(arg.action==='reserve'){const port=env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(config(env),arg.p.shard))) as unknown as EntryRegistry;return json(await port.reserve_wake(arg.p.recordId,'0','1'));}
  if(arg.action==='finish'){const port=env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(config(env),arg.p.shard))) as unknown as EntryRegistry;return json(await port.finish_wake(arg.t,{status:'empty_orphan'}));}
  return new Response('{}',{status:404});
 },
 async scheduled(event:ScheduledController,env:Env){await entry.scheduled(event,env);}
};
