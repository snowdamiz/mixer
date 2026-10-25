import {DurableObject} from 'cloudflare:workers';
import {UnavailableClock} from './clock.js';
import {Engine} from './engine.js';
import {Ledger} from './ledger.js';
import {ingress,PrincipalEnv} from './principal.js';
import {UnavailableObjectVerifier,UnavailableProvider} from './provider.js';
import {errorResponse,reply,sha} from './wire.js';
import type {PendingIdentity,RegistrationReceipt,WakeTicket,RecoveryDisposition,KnownOperationRecovery} from './public-contract.js';
import {PendingEnv,PendingConfig,exact,ticket,identityBytes} from './pending-types.js';
import {RegistryContext,checkedContext,matchesRow} from './registry-context.js';
import {budget,Budget,config,identity,pendingIdentity,registration,registryPort,same} from './entry-context.js';
export interface Env extends PrincipalEnv,PendingEnv {}
export class MixerWorkerOperation extends DurableObject<Env> implements KnownOperationRecovery {
 protected readonly ledger:Ledger;protected engine:Engine|null=null;
 private c:PendingConfig|null=null;private selected:string|null=null;private initialization:Promise<void>|null=null;private failed=false;
 constructor(ctx:DurableObjectState,env:Env){
  super(ctx,env);this.ledger=new Ledger(ctx.storage);
  try{this.c=config(env);}catch{this.failed=true;}
  const row=this.ledger.read();
  if(row&&(row.pending_identity_json!==null||row.registration_json!==null)){
   // A retained row must carry the entire exact pair. Invalid bytes remain fenced.
   ctx.blockConcurrencyWhile(async()=>{try{
    if(!this.c||row.pending_identity_json===null||row.registration_json===null)throw new Error('retained_pair');
    const i=await identity(JSON.parse(row.pending_identity_json),this.c);
    const context={identity:i.value,registry:registryPort(env,this.c,i.value)};
    const checked=await checkedContext(context,i.value,JSON.parse(row.registration_json));
    if(row.pending_identity_json!==JSON.stringify(checked.identity)||row.registration_json!==JSON.stringify(checked.receipt)||!matchesRow(i.value,row)||await sha(row.binding)!==i.value.immutableSha256)throw new Error('retained_invalid');
    await this.initialize(i.value);await this.engine!.recover();
   }catch{this.failed=true;this.ledger.storage.transactionSync(()=>this.ledger.fence('[]','0','entry_retained_invalid',true));await this.ledger.sync();}});
  }
 }
 // Subclasses in excluded verification fixtures may compose finite test effects.
 // Production has no configuration path to select a provider or qualified clock.
 protected resourceKind(_platform:'ios'|'android'):'unavailable'|'cloudflare-linux'|'external-macos'{return 'unavailable';}
 protected createEngine(context:RegistryContext):Engine{return new Engine(this.ledger,new UnavailableClock(),new UnavailableProvider(),new UnavailableObjectVerifier(),undefined,context);}
 private async checkedTarget(value:PendingIdentity,b?:Budget):Promise<PendingIdentity>{if(this.failed||!this.c)throw new Error('entry_unavailable');const i=await identity(value,this.c);b?.check();if(!this.ctx.id.equals(this.env.OPERATIONS.idFromName(i.value.operationKey)))throw new Error('entry_operation_namespace');return i.value;}
 private async initialize(value:PendingIdentity,b?:Budget):Promise<Engine>{
  const i=await this.checkedTarget(value,b),bytes=identityBytes(i);b?.check();
  if(this.selected!==null&&this.selected!==bytes)throw new Error('entry_context_conflict');
  if(this.initialization){await this.initialization;b?.check();if(this.selected!==bytes||!this.engine)throw new Error('entry_context_conflict');return this.engine;}
  this.selected=bytes;
  // Set the slot synchronously before any yield. It is never reset per request.
  this.initialization=Promise.resolve().then(()=>{if(this.failed||!this.c)throw new Error('entry_unavailable');this.engine=this.createEngine({identity:i,registry:registryPort(this.env,this.c,i)});});
  try{await this.initialization;b?.check();return this.engine!;}catch(e){this.failed=true;throw e;}
 }
 async fetch(request:Request):Promise<Response>{
  const b=budget(request.signal);let timer:ReturnType<typeof setTimeout>|undefined;
  const work=async():Promise<Response>=>{try{
   const checked=await ingress(request,this.env);b.check();if(checked instanceof Response)return checked;if(!this.c||this.failed)return errorResponse(503);
   const i=await pendingIdentity(checked.r,this.c,b);b.check();await this.checkedTarget(i.value,b);b.check();
   const row=this.ledger.read();let p:RegistrationReceipt;
   if(row?.registration_json&&row.pending_identity_json){const context={identity:i.value,registry:registryPort(this.env,this.c,i.value)},retained=await checkedContext(context,JSON.parse(row.pending_identity_json),JSON.parse(row.registration_json));b.check();if(row.pending_identity_json!==JSON.stringify(retained.identity)||row.registration_json!==JSON.stringify(retained.receipt)||!matchesRow(i.value,row))throw new Error('retained_invalid');p=retained.receipt;}
   else{p=await registration(this.env,this.c,i.value,b);b.check();}
   const engine=await this.initialize(i.value,b);b.check();
   const observation=await engine.commandRegistered(checked.r,{provider:this.resourceKind(checked.r.ref.platform),key:i.value.operationKey,immutableSha256:i.value.immutableSha256},i.value,p);b.check();return reply(checked.r,observation);
  }catch{return errorResponse(503);}};
  try{return await Promise.race([work(),new Promise<Response>(resolve=>{timer=setTimeout(()=>resolve(errorResponse(503)),4000);})]);}finally{if(timer!==undefined)clearTimeout(timer);}
 }
 async recoverKnown(value:PendingIdentity,p:RegistrationReceipt,t:WakeTicket):Promise<RecoveryDisposition>{try{
  const i=await this.checkedTarget(value);if(!this.c)return {status:'unavailable'};
  const context={identity:i,registry:registryPort(this.env,this.c,i)},checked=await checkedContext(context,i,p),wake=ticket(t,this.c);
  if(wake.runId==='0'||wake.attemptSequence==='0'||!same(wake.receipt,checked.receipt))return {status:'conflict'};
  const engine=await this.initialize(i);return await engine.recoverKnown(i,checked.receipt,wake);
 }catch{return {status:'conflict'};}}
 async enrollExisting(value:PendingIdentity):Promise<'enrolled'|'missing'|'conflict'|'unavailable'>{try{const i=await this.checkedTarget(value);if(!this.ledger.read())return 'missing';const engine=await this.initialize(i);return await engine.enrollExisting(i);}catch{return 'conflict';}}
 async alarm():Promise<void>{if(this.failed)return;if(this.initialization)await this.initialization;if(this.engine)await this.engine.alarm();}
}
