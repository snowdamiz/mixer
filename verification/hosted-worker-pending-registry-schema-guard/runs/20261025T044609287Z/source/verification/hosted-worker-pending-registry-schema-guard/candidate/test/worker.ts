// EXCLUDED narrow schema-fault fixture. Never deploy or import in production.
import entry,{TestAudit,TestRegistry,FixtureRecovery} from './base-fixture.js';
import {PendingEnv,config,auditName} from '../src/pending-types.js';
export {TestRegistry,FixtureRecovery};
export class GuardAudit extends TestAudit {
 async schemaFault(mode:string):Promise<unknown>{
  // Static, finite controls only; no caller SQL, migration or reset surface.
  this.ctx.storage.transactionSync(()=>{
   switch(mode){
    case 'meta_absent_both_retained':this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta');break;
    case 'meta_absent_summary_only':this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta;DROP TABLE pending_audit_completion');break;
    case 'meta_absent_completion_only':this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta;DROP TABLE pending_audit_summary');break;
    case 'meta_absent_empty_summary':this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta;DROP TABLE pending_audit_completion;DELETE FROM pending_audit_summary');break;
    case 'meta_absent_empty_completion':this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta;DROP TABLE pending_audit_summary;DELETE FROM pending_audit_completion');break;
    case 'meta_absent_both_empty':this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta;DELETE FROM pending_audit_summary;DELETE FROM pending_audit_completion');break;
    case 'meta_present_empty':this.ctx.storage.sql.exec('DELETE FROM pending_audit_meta');break;
    default:throw new Error('fixture_schema_fault_mode');
   }
  });await this.ctx.storage.sync();return this.inspectSchema();
 }
 async inspectSchema():Promise<unknown>{const schema=this.ctx.storage.sql.exec<{name:string;sql:string}>("SELECT name,sql FROM sqlite_master WHERE type='table' AND name IN ('pending_audit_meta','pending_audit_summary','pending_audit_completion') ORDER BY name LIMIT 3").toArray();const names=new Set(schema.map(x=>x.name));return {schema,meta:names.has('pending_audit_meta')?this.ctx.storage.sql.exec('SELECT * FROM pending_audit_meta LIMIT 1').toArray():null,summary:names.has('pending_audit_summary')?this.ctx.storage.sql.exec('SELECT * FROM pending_audit_summary ORDER BY slot LIMIT 32').toArray():null,completion:names.has('pending_audit_completion')?this.ctx.storage.sql.exec('SELECT * FROM pending_audit_completion ORDER BY shard LIMIT 16').toArray():null};}
}
export default {
 async fetch(request:Request,env:PendingEnv):Promise<Response>{const data=await request.clone().json() as Record<string,unknown>;if(data.action==='schemaFault'||data.action==='schemaInspect'){const c=config(env),audit=env.PENDING_AUDIT.get(env.PENDING_AUDIT.idFromName(auditName(c))) as unknown as GuardAudit;return Response.json(data.action==='schemaFault'?await audit.schemaFault(data.mode as string):await audit.inspectSchema());}return entry.fetch(request,env);},
 scheduled:entry.scheduled,
};
