import {DurableObject} from 'cloudflare:workers';
import type {AuditSummary,PendingAuditCoordinator,PendingRegistryShard,KnownOperationRecovery,PendingPage,ScannedPending,RecoveryDisposition,WakeTicket} from './public-contract.js';
import {PendingEnv,PendingConfig,config,auditName,registryName,next,wait,integer,exact,identity,receipt,decimal,ticket,disposition,same,encoder} from './pending-types.js';
interface Meta extends Record<string,SqlStorageValue>{run_sequence:string;next_shard:number;cursors:string;current_json:string|null}
const schema=`CREATE TABLE IF NOT EXISTS pending_audit_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version INTEGER NOT NULL CHECK(version=1),config TEXT NOT NULL,run_sequence TEXT NOT NULL,next_shard INTEGER NOT NULL CHECK(next_shard BETWEEN 0 AND 15),cursors TEXT NOT NULL,current_json TEXT);
CREATE TABLE IF NOT EXISTS pending_audit_summary(slot INTEGER PRIMARY KEY CHECK(slot BETWEEN 0 AND 31),receipt_json TEXT NOT NULL);`;
interface Current {summary:AuditSummary;interrupted:boolean}
export class MixerPendingAuditCoordinator extends DurableObject<PendingEnv> implements PendingAuditCoordinator {
 private c:PendingConfig|null=null;private available=false;private active=false;private unresolvedWake:Promise<unknown>|null=null;
 constructor(ctx:DurableObjectState,env:PendingEnv){super(ctx,env);try{const c=config(env);this.c=c;if(!ctx.id.equals(env.PENDING_AUDIT.idFromName(auditName(c))))throw new Error('pending_namespace');
  ctx.storage.transactionSync(()=>{const exists=ctx.storage.sql.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_audit_meta'").toArray();if(exists.length){const rows=ctx.storage.sql.exec<{version:number;config:string}>('SELECT version,config FROM pending_audit_meta').toArray();if(rows.length!==1||rows[0]!.version!==1||rows[0]!.config!==JSON.stringify(c))throw new Error('pending_schema_config');}
   ctx.storage.sql.exec(schema);ctx.storage.sql.exec("INSERT OR IGNORE INTO pending_audit_meta(singleton,version,config,run_sequence,next_shard,cursors) VALUES(1,1,?,'0',0,?)",JSON.stringify(c),JSON.stringify(Array(16).fill(0)));
   const m=this.meta();decimal(m.run_sequence);integer(m.next_shard,0,15);this.cursors(m);
  });this.available=true;
 }catch{this.available=false;}}
 private meta():Meta{return this.ctx.storage.sql.exec<Meta>('SELECT run_sequence,next_shard,cursors,current_json FROM pending_audit_meta WHERE singleton=1').toArray()[0]!;}
 private cursors(m:Meta):number[]{const a=JSON.parse(m.cursors) as unknown[];if(!Array.isArray(a)||a.length!==16)throw new Error('pending_cursors');return a.map(v=>integer(v,0,4096));}
 private archive(current:string):void{const c=JSON.parse(current) as Current;const run=decimal(c.summary.runId);const slot=Number(BigInt(run)%32n);this.ctx.storage.sql.exec('INSERT INTO pending_audit_summary(slot,receipt_json) VALUES(?,?) ON CONFLICT(slot) DO UPDATE SET receipt_json=excluded.receipt_json',slot,current);}
 private checkpoint(run:string,shard:number,cursor:number|undefined,s:AuditSummary,interrupted=false):boolean{return this.ctx.storage.transactionSync(()=>{const m=this.meta();if(m.run_sequence!==run)return false;const cursors=this.cursors(m);if(cursor!==undefined)cursors[shard]=cursor;this.ctx.storage.sql.exec('UPDATE pending_audit_meta SET next_shard=?,cursors=?,current_json=? WHERE singleton=1',(shard+1)%16,JSON.stringify(cursors),JSON.stringify({summary:s,interrupted}));return true;});}
 private async page(v:unknown):Promise<PendingPage>{const p=exact(v,['records','wrapped']);if(!Array.isArray(p.records)||p.records.length>32||typeof p.wrapped!=='boolean'||encoder.encode(JSON.stringify(v)).length>65536)throw new Error('pending_page');const seen=new Set<number>();const out:ScannedPending[]=[];for(const x of p.records){const r=exact(x,['identity','receipt','stateVersion','needsAttention','skipVisits']);const i=await identity(r.identity,this.c!),p=receipt(r.receipt,this.c!);if(i.digest!==p.identityDigest||i.shard!==p.shard||typeof r.needsAttention!=='boolean'||seen.has(p.allocationIndex))throw new Error('pending_page');seen.add(p.allocationIndex);out.push({identity:i.value,receipt:p,stateVersion:decimal(r.stateVersion),needsAttention:r.needsAttention,skipVisits:integer(r.skipVisits,0,7)});}return {records:out,wrapped:p.wrapped};}
 async runScheduled():Promise<AuditSummary>{const empty=(status:AuditSummary['status']):AuditSummary=>({status,runId:null,pages:0,examined:0,wakesStarted:0,needsAttention:status==='unavailable'});if(!this.available)return empty('unavailable');if(this.active||this.unresolvedWake)return empty('busy');this.active=true;
  const started=performance.now(),remaining=()=>Math.max(0,24000-(performance.now()-started));let summary=empty('bounded'),run:string|null=null;
  try{
   const initial=this.ctx.storage.transactionSync(()=>{const m=this.meta(),n=next(m.run_sequence);if(m.current_json)this.archive(m.current_json);summary={...summary,runId:n};this.ctx.storage.sql.exec('UPDATE pending_audit_meta SET run_sequence=?,current_json=? WHERE singleton=1',n,JSON.stringify({summary,interrupted:true}));return {run:n,start:m.next_shard,cursors:this.cursors(m)};});run=initial.run;
   // The local SQLite output gate is also bounded by the same elapsed budget.
   if(!(await wait(this.ctx.storage.sync(),Math.min(250,remaining()))).ok){summary.needsAttention=true;return summary;}
   let halted=false;
   for(let offset=0;offset<16&&!halted;offset++){
    if(summary.pages>=16||summary.examined>=512||summary.wakesStarted>=8||remaining()<250){halted=true;break;}
    const shard=(initial.start+offset)%16,port=this.env.PENDING_REGISTRY.get(this.env.PENDING_REGISTRY.idFromName(registryName(this.c!,shard))) as unknown as PendingRegistryShard;
    // Persist shard rotation before any remote wait, even on a failed page.
    if(!this.checkpoint(run,shard,undefined,summary,true))throw new Error('pending_run_stale');
    summary.pages++;
    const call=await wait(port.scan_due({afterAllocationIndex:initial.cursors[shard]!},32),250);let page:PendingPage;
    if(!call.ok){summary.needsAttention=true;this.checkpoint(run,shard,undefined,summary,true);continue;}
    try{page=await this.page(call.value);}catch{summary.needsAttention=true;this.checkpoint(run,shard,undefined,summary,true);continue;}
    for(const record of page.records){
     // Reserve + maximum recovery wait + finish must all fit before a wake.
     if(summary.examined>=512||summary.wakesStarted>=8||remaining()<3000){halted=true;break;}
     if(record.receipt.shard!==shard)throw new Error('pending_page_shard');
     summary.examined++;summary.needsAttention ||= record.needsAttention;
     if(!this.checkpoint(run,shard,record.receipt.allocationIndex,summary,true))throw new Error('pending_run_stale');
     const reserved=await wait(port.reserve_wake(record.receipt.recordId,record.stateVersion,run),250);
     if(!reserved.ok){summary.needsAttention=true;continue;}
     const r=reserved.value;exact(r,r.status==='reserved'?['status','ticket']:['status']);
     if(r.status!=='reserved'){if(!['duplicate','stale','backoff','terminal','unavailable'].includes(r.status))throw new Error('pending_reservation');if(r.status==='unavailable')summary.needsAttention=true;continue;}
     const t=ticket(r.ticket,this.c!);if(t.runId!==run||t.trackedVersion!==record.stateVersion||!same(t.receipt,record.receipt))throw new Error('pending_ticket');
     if(remaining()<2750){summary.needsAttention=true;halted=true;break;}
     // Count before starting; local checkpoint precedes identity-only recovery.
     summary.wakesStarted++;if(!this.checkpoint(run,shard,record.receipt.allocationIndex,summary,true))throw new Error('pending_run_stale');
     const operation=this.env.OPERATIONS.get(this.env.OPERATIONS.idFromName(record.identity.operationKey)) as unknown as KnownOperationRecovery;
     let settled=false;const wake=Promise.resolve().then(()=>operation.recoverKnown(record.identity,record.receipt,t));
     this.unresolvedWake=wake;void wake.then(()=>{settled=true;if(this.unresolvedWake===wake)this.unresolvedWake=null;},()=>{settled=true;if(this.unresolvedWake===wake)this.unresolvedWake=null;});
     const result=await wait(wake,Math.min(2500,remaining()-250));
     if(!result.ok&&!settled){summary.needsAttention=true;halted=true;break;}
     let d:RecoveryDisposition={status:'unavailable'};if(result.ok){try{d=disposition(result.value);}catch{summary.needsAttention=true;}}
     if(!result.ok||!['pending','terminal'].includes(d.status))summary.needsAttention=true;
     if(remaining()<250){summary.needsAttention=true;halted=true;break;}
     const finished=await wait(port.finish_wake(t,d),250);if(!finished.ok||finished.value!=='accepted')summary.needsAttention=true;
    }
    this.checkpoint(run,shard,undefined,summary,true);
   }
   summary.status=halted?'bounded':'finished';
   this.ctx.storage.transactionSync(()=>{const m=this.meta();if(m.run_sequence===run){const value=JSON.stringify({summary,interrupted:false});this.ctx.storage.sql.exec('UPDATE pending_audit_meta SET current_json=? WHERE singleton=1',value);this.archive(value);}});
   if(remaining()>=250){if(!(await wait(this.ctx.storage.sync(),250)).ok)summary.needsAttention=true;}else summary.needsAttention=true;
   return summary;
  }catch{summary.status='unavailable';summary.needsAttention=true;if(run!==null){try{this.ctx.storage.transactionSync(()=>{const m=this.meta();if(m.run_sequence===run)this.ctx.storage.sql.exec('UPDATE pending_audit_meta SET current_json=? WHERE singleton=1',JSON.stringify({summary,interrupted:true}));});}catch{}}
   return summary;
  }finally{this.active=false;}
 }
}
