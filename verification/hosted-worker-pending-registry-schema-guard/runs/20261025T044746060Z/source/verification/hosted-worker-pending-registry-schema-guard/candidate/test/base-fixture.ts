// EXCLUDED COMPONENT FIXTURE. Never deploy, import from production, or infer
// operation-engine behavior from the synthetic identity-only recovery adapter.
import {DurableObject} from 'cloudflare:workers';
import {MixerPendingRegistryShard} from '../src/pending-registry.js';
import {MixerPendingAuditCoordinator} from '../src/pending-audit.js';
import type {PendingIdentity,RegistrationReceipt,RegistrationResult,TrackInput,TrackAck,ScanCursor,PendingPage,WakeReservation,WakeTicket,RecoveryDisposition,AuditSummary} from '../src/public-contract.js';
import {PendingEnv,config,registryName,auditName,identity,identityBytes,integer,sha} from '../src/pending-types.js';
const sleep=(ms:number)=>new Promise<void>(resolve=>setTimeout(resolve,ms));
interface Setting {mode:string;milliseconds:number}
export class TestRegistry extends MixerPendingRegistryShard {
 private held:(()=>void)|null=null;
 constructor(ctx:DurableObjectState,env:PendingEnv){super(ctx,env);ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS fixture_registry(singleton INTEGER PRIMARY KEY CHECK(singleton=1),value TEXT NOT NULL)");}
 private setting():Setting{const r=this.ctx.storage.sql.exec<{value:string}>('SELECT value FROM fixture_registry WHERE singleton=1').toArray()[0];return r?JSON.parse(r.value):{mode:'none',milliseconds:0};}
 async configure(s:Setting):Promise<void>{this.ctx.storage.sql.exec('INSERT INTO fixture_registry(singleton,value) VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value',JSON.stringify(s));await this.ctx.storage.sync();}
 async release():Promise<void>{this.held?.();this.held=null;await this.configure({mode:'none',milliseconds:0});}
 private async fault(name:string):Promise<void>{const s=this.setting();if(s.mode===name+'_throw')throw new Error('fixture_fault');if(s.mode===name+'_delay')await sleep(s.milliseconds);if(s.mode===name+'_hold')await new Promise<void>(resolve=>{this.held=resolve;});}
 async register(i:PendingIdentity):Promise<RegistrationResult>{await this.fault('register_before');const r=await super.register(i);await this.fault('register_ack');return r;}
 async track(a:TrackInput):Promise<TrackAck>{const r=await super.track(a);await this.fault('track_ack');return r;}
 async scan_due(c:ScanCursor,n:number):Promise<PendingPage>{await this.fault('scan');return super.scan_due(c,n);}
 async reserve_wake(id:string,v:string,run:string):Promise<WakeReservation>{const r=await super.reserve_wake(id,v,run);await this.fault('reserve_ack');return r;}
 async finish_wake(t:WakeTicket,d:RecoveryDisposition):Promise<'accepted'|'stale'|'unavailable'>{await this.fault('finish_before');const r=await super.finish_wake(t,d);await this.fault('finish_ack');return r;}
 async inspect(recordId:string|null):Promise<unknown>{return {meta:this.ctx.storage.sql.exec('SELECT * FROM pending_registry_meta').toArray(),count:this.ctx.storage.sql.exec('SELECT COUNT(*) AS n FROM pending_registry_record').toArray(),row:recordId?this.ctx.storage.sql.exec('SELECT *,typeof(state_version) AS version_type,typeof(attempt_sequence) AS sequence_type FROM pending_registry_record WHERE record_id=?',recordId).toArray()[0]??null:null};}
 async counterMax(recordId:string):Promise<void>{this.ctx.storage.sql.exec("UPDATE pending_registry_record SET attempt_sequence='9223372036854775807',skip_visits=0,failures=32,needs_attention=1 WHERE record_id=?",recordId);await this.ctx.storage.sync();}
 async schemaConflict():Promise<void>{this.ctx.storage.sql.exec("UPDATE pending_registry_meta SET config='conflicting-fixture-config' WHERE singleton=1");await this.ctx.storage.sync();}
}
export class TestAudit extends MixerPendingAuditCoordinator {
 async inspect():Promise<unknown>{return {meta:this.ctx.storage.sql.exec('SELECT * FROM pending_audit_meta').toArray(),completions:this.ctx.storage.sql.exec('SELECT shard,value FROM pending_audit_completion ORDER BY shard').toArray(),ring:this.ctx.storage.sql.exec('SELECT * FROM pending_audit_summary ORDER BY slot').toArray()};}
 async completionFault(mode:string):Promise<void>{this.ctx.storage.sql.exec('DROP TRIGGER IF EXISTS fixture_completion_write_failure;DROP TRIGGER IF EXISTS fixture_completion_clear_failure');if(mode==='write')this.ctx.storage.sql.exec("CREATE TRIGGER fixture_completion_write_failure BEFORE UPDATE ON pending_audit_completion WHEN NEW.value IS NOT NULL BEGIN SELECT RAISE(ABORT,'fixture_completion_write');END");else if(mode==='clear')this.ctx.storage.sql.exec("CREATE TRIGGER fixture_completion_clear_failure BEFORE UPDATE ON pending_audit_completion WHEN NEW.value IS NULL AND OLD.value IS NOT NULL BEGIN SELECT RAISE(ABORT,'fixture_completion_clear');END");else if(mode!=='none')throw new Error('fixture_fault_mode');await this.ctx.storage.sync();}
 async counterMax():Promise<void>{this.ctx.storage.sql.exec("UPDATE pending_audit_meta SET run_sequence='9223372036854775807' WHERE singleton=1");await this.ctx.storage.sync();}
}
export class FixtureRecovery extends DurableObject<PendingEnv> {
 private releaseHold:(()=>void)|null=null;
 constructor(ctx:DurableObjectState,env:PendingEnv){super(ctx,env);ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS fixture_recovery(singleton INTEGER PRIMARY KEY CHECK(singleton=1),mode TEXT NOT NULL,calls INTEGER NOT NULL,settled INTEGER NOT NULL,last_identity TEXT,last_receipt TEXT,last_ticket TEXT);INSERT OR IGNORE INTO fixture_recovery(singleton,mode,calls,settled) VALUES(1,'pending',0,0)");}
 async configure(mode:string):Promise<void>{if(!['pending','empty_orphan','quarantined','unavailable','hold','hold_unavailable','hold_reject','reject','delay2100'].includes(mode))throw new Error('fixture_mode');this.ctx.storage.sql.exec('UPDATE fixture_recovery SET mode=? WHERE singleton=1',mode);await this.ctx.storage.sync();}
 async recoverKnown(i:PendingIdentity,r:RegistrationReceipt,t:WakeTicket):Promise<RecoveryDisposition>{await identity(i,config(this.env));this.ctx.storage.sql.exec('UPDATE fixture_recovery SET calls=calls+1,last_identity=?,last_receipt=?,last_ticket=? WHERE singleton=1',JSON.stringify(i),JSON.stringify(r),JSON.stringify(t));await this.ctx.storage.sync();const {mode}=this.ctx.storage.sql.exec<{mode:string}>('SELECT mode FROM fixture_recovery WHERE singleton=1').toArray()[0]!;if(mode==='hold'||mode==='hold_unavailable'||mode==='hold_reject')await new Promise<void>(resolve=>{this.releaseHold=resolve;});if(mode==='delay2100')await sleep(2100);this.ctx.storage.sql.exec('UPDATE fixture_recovery SET settled=settled+1 WHERE singleton=1');await this.ctx.storage.sync();if(mode==='reject'||mode==='hold_reject')throw new Error('fixture_recovery_rejected');if(mode==='hold_unavailable')return {status:'unavailable'};return mode==='empty_orphan'||mode==='quarantined'||mode==='unavailable'?{status:mode}:{status:'pending',stateVersion:t.trackedVersion};}
 async release():Promise<void>{this.releaseHold?.();this.releaseHold=null;}
 async inspect():Promise<unknown>{return this.ctx.storage.sql.exec('SELECT * FROM fixture_recovery').toArray()[0];}
}
const json=(v:unknown)=>new Response(JSON.stringify(v),{headers:{'content-type':'application/json'}});
export default {
 async fetch(req:Request,env:PendingEnv):Promise<Response>{if(new URL(req.url).pathname!=='/__test/components')return new Response('disabled',{status:404});const a=await req.json() as Record<string,unknown>;const c=config(env);const shard=()=>env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(c,integer(a.shard,0,15)))) as unknown as TestRegistry;const audit=()=>env.PENDING_AUDIT.get(env.PENDING_AUDIT.idFromName(auditName(c))) as unknown as TestAudit;const recovery=()=>env.OPERATIONS.get(env.OPERATIONS.idFromName(a.operationKey as string)) as unknown as FixtureRecovery;
  try{switch(a.action){
   case 'hash':{const i=await identity(a.identity,c);return json({bytes:identityBytes(i.value),digest:i.digest,shard:i.shard});}
   case 'register':return json(await shard().register(a.identity as PendingIdentity));
   case 'track':return json(await shard().track(a.input as TrackInput));
   case 'scan':return json(await shard().scan_due(a.cursor as ScanCursor,a.limit as number));
   case 'reserve':return json(await shard().reserve_wake(a.recordId as string,a.version as string,a.runId as string));
   case 'finish':return json(await shard().finish_wake(a.ticket as WakeTicket,a.disposition as RecoveryDisposition));
   case 'registryInspect':return json(await shard().inspect(a.recordId as string|null));
   case 'registryConfigure':await shard().configure(a.setting as unknown as Setting);return json({ok:true});
   case 'registryRelease':await shard().release();return json({ok:true});
   case 'registryMax':await shard().counterMax(a.recordId as string);return json({ok:true});
   case 'registryConflict':await shard().schemaConflict();return json({ok:true});
   case 'audit':return json(await audit().runScheduled());
   case 'auditInspect':return json(await audit().inspect());
   case 'auditMax':await audit().counterMax();return json({ok:true});
   case 'auditCompletionFault':await audit().completionFault(a.mode as string);return json({ok:true});
   case 'recoveryConfigure':await recovery().configure(a.mode as string);return json({ok:true});
   case 'recoveryRelease':await recovery().release();return json({ok:true});
   case 'recoveryInspect':return json(await recovery().inspect());
   // Closed batch registers only known valid identities; no raw SQL/capacity override.
   case 'registerBatch':{const list=a.identities as PendingIdentity[];if(!Array.isArray(list)||list.length>64)throw new Error('batch_limit');const results=[];for(const i of list)results.push(await shard().register(i));return json(results);}
  }}catch(error){return json({rejected:true,error:error instanceof Error?error.message:'unknown'});}return new Response('disabled',{status:404});
 },
 async scheduled(_event:ScheduledController,env:PendingEnv,_ctx:ExecutionContext):Promise<void>{const c=config(env);await (env.PENDING_AUDIT.get(env.PENDING_AUDIT.idFromName(auditName(c))) as unknown as TestAudit).runScheduled();}
};
