// EXCLUDED finite verification entry. No production route or qualified provider.
import {DurableObject} from 'cloudflare:workers';
import {Engine,Hooks,RunnerReport} from '../src/engine.js';
import {Ledger} from '../src/ledger.js';
import type {Clock} from '../src/clock.js';
import type {Effect,Provider,ProviderObservation} from '../src/provider.js';
import {decode,WireRequest} from '../src/wire.js';
import type {PendingIdentity,RegistrationReceipt,TrackInput,TrackAck,WakeTicket} from '../src/vendor/public-contract.js';
import {MixerPendingRegistryShard,RegistryPort} from '../src/vendor/pending-registry.js';
import {PendingEnv,config,registryName} from '../src/vendor/pending-types.js';
interface Env extends PendingEnv {FIXTURE_IDENTITY:string}
interface Settings {clock:string;qualified:boolean;drained:boolean;fault:string|null;blocked:boolean}
const defaults=():Settings=>({clock:'1900000000000000',qualified:true,drained:false,fault:null,blocked:false});
const response=(v:unknown)=>new Response(JSON.stringify(v),{headers:{'Content-Type':'application/json'}});
class Store {
 constructor(readonly sql:SqlStorage){sql.exec('CREATE TABLE IF NOT EXISTS fixture_settings(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS fixture_calls(sequence INTEGER PRIMARY KEY AUTOINCREMENT,value TEXT NOT NULL)');}
 get():Settings {const r=this.sql.exec<{value:string}>('SELECT value FROM fixture_settings WHERE singleton=1').toArray()[0];return r?JSON.parse(r.value):defaults();}
 set(v:Settings){this.sql.exec('INSERT INTO fixture_settings VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value',JSON.stringify(v));}
}
class SyntheticClock implements Clock {constructor(private s:Store){}sample(){const s=this.s.get();return s.qualified?{lowerUs:BigInt(s.clock)-1n,upperUs:BigInt(s.clock)+1n,qualificationId:'excluded-pending-registry-engine-fixture'}:null;}}
class FixtureHooks implements Hooks {resolve:(()=>void)|null=null;constructor(private s:Store){}async point(name:string){const s=this.s.get();if(s.fault!==name)return;s.fault=null;s.blocked=true;this.s.set(s);await new Promise<void>(resolve=>{this.resolve=resolve;});}}
class FixtureProvider implements Provider {
 readonly available=true;constructor(private s:Store){}kind(){return 'cloudflare-linux' as const;}
 async perform(e:Effect):Promise<ProviderObservation>{
  this.s.sql.exec('INSERT INTO fixture_calls(value) VALUES(?)',JSON.stringify({kind:e.kind,id:e.id,identity:e.identity}));
  const stop=e.kind==='stop',drain=this.s.get().drained;
  return {identity:e.identity,state:stop?'absent':'inert',instanceId:stop?null:'instance-1',bootId:stop?null:'boot-1',definitive:stop&&drain,descendantsGone:stop&&drain,launchesSettled:stop&&drain,diagnosticSha256:'d'.repeat(64)};
 }
 launchInert(e:Effect){return this.perform(e);}inspect(e:Effect){return this.perform(e);}stop(e:Effect){return this.perform(e);}
}
export class TestRegistry extends MixerPendingRegistryShard {
 private releaseAck:(()=>void)|null=null;
 private setting(){const r=this.ctx.storage.sql.exec<{value:string}>('SELECT value FROM fixture_registry WHERE singleton=1').toArray()[0];return r?JSON.parse(r.value) as {mode:string;skip:number;blocked:boolean}:{mode:'normal',skip:0,blocked:false};}
 private set(v:unknown){this.ctx.storage.sql.exec('INSERT INTO fixture_registry VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value',JSON.stringify(v));}
 constructor(ctx:DurableObjectState,env:PendingEnv){super(ctx,env);ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS fixture_registry(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL)');}
 async register(i:PendingIdentity){if(this.setting().mode==='register_unavailable')return {status:'unavailable' as const};const r=await super.register(i);if(this.setting().mode==='register_lost')return {status:'unavailable' as const};return r;}
 async track(a:TrackInput):Promise<TrackAck>{
  const s=this.setting();if(s.mode==='unavailable')return {status:'unavailable'};
  if(s.skip>0){s.skip--;this.set(s);return super.track(a);}
  if(s.mode==='drop_before_once'){this.set({mode:'normal',skip:0,blocked:false});return {status:'unavailable'};}
  if(s.mode==='lost_once'){this.set({mode:'normal',skip:0,blocked:false});await super.track(a);return {status:'unavailable'};}
  if(s.mode==='hold_after_once'||s.mode==='hold_before_once'){
   this.set({mode:'normal',skip:0,blocked:true});
   const result=s.mode==='hold_after_once'?await super.track(a):null;
   await new Promise<void>(resolve=>{this.releaseAck=resolve;});
   return result??super.track(a);
  }
  return super.track(a);
 }
 async fixture(action:string,arg:Record<string,unknown>){
  if(action==='mode'){this.set({mode:arg.mode,skip:arg.skip??0,blocked:false});return {ok:true};}
  if(action==='release'){this.releaseAck?.();this.releaseAck=null;return {ok:true};}
  return {settings:this.setting(),records:this.ctx.storage.sql.exec('SELECT * FROM pending_registry_record ORDER BY allocation_index').toArray()};
 }
}
export class TestOperation extends DurableObject<Env> {
 private ledger:Ledger;private engine:Engine;private store:Store;private hooks:FixtureHooks;private provider:FixtureProvider;private identity:PendingIdentity;
 constructor(ctx:DurableObjectState,env:Env){
  super(ctx,env);this.identity=JSON.parse(env.FIXTURE_IDENTITY);this.ledger=new Ledger(ctx.storage);this.store=new Store(ctx.storage.sql);this.hooks=new FixtureHooks(this.store);this.provider=new FixtureProvider(this.store);
  this.engine=new Engine(this.ledger,new SyntheticClock(this.store),this.provider,{async verify(){return true;}},this.hooks,{identity:this.identity,registry:new RegistryPort(env)});
  ctx.blockConcurrencyWhile(()=>this.engine.recover());
 }
 async fixture(action:string,arg:Record<string,unknown>):Promise<unknown>{
  const resource={provider:'cloudflare-linux' as const,key:this.identity.operationKey,immutableSha256:this.identity.immutableSha256};
  switch(action){
   case 'command':{const r=await decode(new TextEncoder().encode(JSON.stringify(arg.request)));return this.engine.commandRegistered(r,resource,(arg.identity??this.identity) as PendingIdentity,arg.receipt as RegistrationReceipt);}
   case 'plain':{const r=await decode(new TextEncoder().encode(JSON.stringify(arg.request)));return this.engine.command(r,resource);}
   case 'defaultUnavailable':{const r=await decode(new TextEncoder().encode(JSON.stringify(arg.request)));return new Engine(this.ledger,new SyntheticClock(this.store),this.provider,{async verify(){return true;}}).commandRegistered(r,resource,this.identity,arg.receipt as RegistrationReceipt);}
   case 'raw':return {row:this.ledger.read(),fence:this.ctx.storage.sql.exec('SELECT * FROM registry_quarantine').toArray(),calls:this.ctx.storage.sql.exec<{value:string}>('SELECT value FROM fixture_calls ORDER BY sequence').toArray().map(r=>JSON.parse(r.value)),settings:this.store.get(),schema:this.ctx.storage.sql.exec('SELECT version FROM controller_schema').toArray()};
   case 'clock':{const s=this.store.get();s.clock=arg.now as string;s.qualified=arg.qualified!==false;this.store.set(s);return {ok:true};}
   case 'drain':{const s=this.store.get();s.drained=arg.value===true;this.store.set(s);return {ok:true};}
   case 'inject':{const s=this.store.get();s.fault=arg.point as string;s.blocked=false;this.store.set(s);return {ok:true};}
   case 'release':this.hooks.resolve?.();this.hooks.resolve=null;return {ok:true};
   case 'reconcile':await this.engine.reconcile();return {ok:true};
   case 'flush':return {flushed:await this.engine.flushTrack()};
   case 'claim':{const r=this.ledger.read();return r?this.engine.claim({identity:this.ledger.identity(r),immutableSha256:r.binding_hash,instanceId:'instance-1',bootId:'boot-1'}):{granted:false};}
   case 'report':{const r=this.ledger.read();if(!r)return {status:'rejected'};return {status:await this.engine.report({identity:this.ledger.identity(r),immutableSha256:r.binding_hash,instanceId:r.instance_id!,bootId:r.boot_id!,claimId:r.claim_id!,operationId:r.operation_id,result:{outcome:'failed',class:'compiler',code:'compiler_error',diagnostic_sha256:'a'.repeat(64)},attestationSha256:'a'.repeat(64)} as RunnerReport)};}
   case 'recoverKnown':return this.engine.recoverKnown((arg.identity??this.identity) as PendingIdentity,arg.receipt as RegistrationReceipt,arg.ticket as WakeTicket);
   case 'enroll':return {status:await this.engine.enrollExisting((arg.identity??this.identity) as PendingIdentity)};
   case 'quarantine':await this.engine.quarantine();return {ok:true};
   case 'deleteRow':this.ctx.storage.sql.exec('DELETE FROM operation');await this.ledger.sync();return {ok:true};
   case 'regress':this.ctx.storage.sql.exec("UPDATE operation SET state_version='0',track_outbox_json=NULL");await this.ledger.sync();return {ok:true};
   case 'legacy':{
    const before=this.ledger.read();this.ctx.storage.transactionSync(()=>{
     for(const k of ['pending_identity_json','registration_json','registry_ack_version','effect_barrier_version','claim_barrier_version','track_outbox_json'])this.ctx.storage.sql.exec('ALTER TABLE operation DROP COLUMN '+k);
     if(arg.version===1)this.ctx.storage.sql.exec('ALTER TABLE operation DROP COLUMN clock_floor');
     this.ctx.storage.sql.exec('DROP TABLE registry_quarantine');this.ctx.storage.sql.exec('DROP TABLE controller_schema');this.ctx.storage.sql.exec('CREATE TABLE controller_schema(version INTEGER NOT NULL)');this.ctx.storage.sql.exec('INSERT INTO controller_schema VALUES(?)',arg.version as number);
    });new Ledger(this.ctx.storage);return {before,after:this.ledger.read()};
   }
   case 'partialMetadata':{
    this.ctx.storage.sql.exec('DROP TABLE controller_schema');let unavailable=false;try{new Ledger(this.ctx.storage);}catch{unavailable=true;}return {unavailable,row:this.ledger.read(),fence:this.ledger.fenced()};
   }
   case 'missingSafetyTable':{this.ctx.storage.sql.exec('DROP TABLE registry_quarantine');try{new Ledger(this.ctx.storage);return {unavailable:false};}catch{return {unavailable:true};}}
  }
  throw new Error('fixture_action');
 }
 // Alarm delivery is suppressed in this excluded fixture; explicit reconciles
 // exercise engine recovery while automatic independent audit remains separate.
 async alarm(){}
}
export default {async fetch(request:Request,env:Env){
 if(new URL(request.url).pathname!=='/__test/engine'||request.method!=='POST')return new Response('excluded fixture only',{status:404});
 try{
 const a=await request.json() as Record<string,unknown>,action=a.action as string,identity=JSON.parse(env.FIXTURE_IDENTITY) as PendingIdentity;
 const shard=env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(config(env),parseInt(identity.operationKey[0]!,16)))) as unknown as TestRegistry;
 if(action==='register')return response(await new RegistryPort(env).register(identity));
 if(action==='registry')return response(await shard.fixture(a.command as string,a));
 if(action==='reserve')return response(await shard.reserve_wake(a.recordId as string,a.version as string,a.runId as string));
 if(action==='forceTrack')return response(await shard.track(a.input as unknown as TrackInput));
 const operation=env.OPERATIONS.get(env.OPERATIONS.idFromName(identity.operationKey)) as unknown as TestOperation;
 return response(await operation.fixture(action,a));
 }catch(e){return response({fixtureError:e instanceof Error?e.message:'unknown'});}
}};
