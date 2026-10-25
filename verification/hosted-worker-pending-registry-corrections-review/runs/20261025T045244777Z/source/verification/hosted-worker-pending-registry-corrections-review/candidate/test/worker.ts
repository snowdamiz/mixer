// EXCLUDED independent review adapter; owned local SQLite stores only.
import {DurableObject} from 'cloudflare:workers';
import {MixerPendingRegistryShard} from '../src/pending-registry.js';
import {MixerPendingAuditCoordinator} from '../src/pending-audit.js';
import {PendingEnv,config,registryName,auditName,identity} from '../src/pending-types.js';
import type {PendingIdentity,TrackInput,TrackAck,WakeTicket,RecoveryDisposition} from '../src/public-contract.js';
export class ReviewRegistry extends MixerPendingRegistryShard {
 private held:(()=>void)|null=null;
 private hold=false;
 async holdAcknowledgement(value:boolean):Promise<void>{this.hold=value;if(!value){this.held?.();this.held=null;}}
 async track(input:TrackInput):Promise<TrackAck>{const answer=await super.track(input);if(this.hold)await new Promise<void>(resolve=>{this.held=resolve;});return answer;}
 async inspect(id:string):Promise<unknown>{return {meta:this.ctx.storage.sql.exec('SELECT * FROM pending_registry_meta').toArray(),rows:this.ctx.storage.sql.exec('SELECT *,typeof(state_version) AS version_type FROM pending_registry_record WHERE record_id=?',id).toArray()};}
}
export class ReviewAudit extends MixerPendingAuditCoordinator {
 async inspect():Promise<unknown>{const schema=this.ctx.storage.sql.exec<{name:string;sql:string}>("SELECT name,sql FROM sqlite_master WHERE type='table' AND name IN ('pending_audit_meta','pending_audit_summary','pending_audit_completion') ORDER BY name").toArray();const names=new Set(schema.map(r=>r.name));return {schema,meta:names.has('pending_audit_meta')?this.ctx.storage.sql.exec('SELECT * FROM pending_audit_meta').toArray():null,summary:names.has('pending_audit_summary')?this.ctx.storage.sql.exec('SELECT * FROM pending_audit_summary ORDER BY slot').toArray():null,completion:names.has('pending_audit_completion')?this.ctx.storage.sql.exec('SELECT * FROM pending_audit_completion ORDER BY shard').toArray():null};}
 async fault(mode:string):Promise<unknown>{this.ctx.storage.transactionSync(()=>{if(mode==='meta-absent-retained')this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta');else if(mode==='meta-absent-empty-completion-only')this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta;DROP TABLE pending_audit_summary;DELETE FROM pending_audit_completion');else throw new Error('closed_review_fault');});await this.ctx.storage.sync();return this.inspect();}
}
export class ReviewRecovery extends DurableObject<PendingEnv> {
 private held:(()=>void)|null=null;
 private holding=false;
 constructor(ctx:DurableObjectState,env:PendingEnv){super(ctx,env);ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS review_recovery(singleton INTEGER PRIMARY KEY,calls INTEGER NOT NULL,settled INTEGER NOT NULL);INSERT OR IGNORE INTO review_recovery VALUES(1,0,0)');}
 async configure(holding:boolean):Promise<void>{this.holding=holding;}
 async release():Promise<void>{this.held?.();this.held=null;}
 async inspect():Promise<unknown>{return this.ctx.storage.sql.exec('SELECT * FROM review_recovery').toArray()[0];}
 async recoverKnown(i:PendingIdentity,_r:unknown,_t:WakeTicket):Promise<RecoveryDisposition>{await identity(i,config(this.env));this.ctx.storage.sql.exec('UPDATE review_recovery SET calls=calls+1 WHERE singleton=1');await this.ctx.storage.sync();if(this.holding)await new Promise<void>(resolve=>{this.held=resolve;});this.ctx.storage.sql.exec('UPDATE review_recovery SET settled=settled+1 WHERE singleton=1');await this.ctx.storage.sync();return {status:'unavailable'};}
}
export default {
 async fetch(request:Request,env:PendingEnv):Promise<Response>{if(new URL(request.url).pathname!=='/__excluded/review')return new Response('disabled',{status:404});const a=await request.json() as Record<string,unknown>,c=config(env),r=env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(c,0))) as unknown as ReviewRegistry,u=env.PENDING_AUDIT.get(env.PENDING_AUDIT.idFromName(auditName(c))) as unknown as ReviewAudit,o=env.OPERATIONS.get(env.OPERATIONS.idFromName(typeof a.operationKey==='string'?a.operationKey:'review-unused')) as unknown as ReviewRecovery;
  switch(a.action){
   case 'register':return Response.json(await r.register(a.identity as PendingIdentity));
   case 'track':return Response.json(await r.track(a.input as TrackInput));
   case 'reserve':return Response.json(await r.reserve_wake(a.recordId as string,a.version as string,a.runId as string));
   case 'finish':return Response.json(await r.finish_wake(a.ticket as WakeTicket,a.disposition as RecoveryDisposition));
   case 'scan':return Response.json(await r.scan_due({afterAllocationIndex:0},32));
   case 'registry':return Response.json(await r.inspect(a.recordId as string));
   case 'hold-ack':await r.holdAcknowledgement(a.value as boolean);return Response.json({ok:true});
   case 'audit':return Response.json(await u.runScheduled());
   case 'schema':return Response.json(await u.inspect());
   case 'fault':return Response.json(await u.fault(a.mode as string));
   case 'hold-recovery':await o.configure(true);return Response.json({ok:true});
   case 'release-recovery':await o.release();return Response.json({ok:true});
   case 'recovery':return Response.json(await o.inspect());
  }return new Response('disabled',{status:404});
 },
 async scheduled(_event:ScheduledController,env:PendingEnv):Promise<void>{const c=config(env);await (env.PENDING_AUDIT.get(env.PENDING_AUDIT.idFromName(auditName(c))) as unknown as ReviewAudit).runScheduled();}
};
