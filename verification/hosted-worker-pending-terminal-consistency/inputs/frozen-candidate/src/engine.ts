import {Clock,Interval,validInterval} from "./clock.js";
import {Ledger,Row} from "./ledger.js";
import {Effect,ObjectVerifier,Provider,ProviderObservation,ResourceIdentity} from "./provider.js";
import {BuildResult,decimal,exact,hex,immutableBytes,invalid,Observation,result,sha,text,WireRequest} from "./wire.js";
import type {PendingIdentity,RegistrationReceipt,WakeTicket,RecoveryDisposition,Projection,CoalescedTrackOutbox} from "./vendor/public-contract.js";
import {decimal as registryDecimal,exact as registryExact,ticket as registryTicket,receipt as registryReceipt,wait} from "./vendor/pending-types.js";
import {RegistryContext,checkedContext,identityBytes,matchesRequest,matchesRow,retained,same,unavailableRegistry} from "./registry-context.js";
interface BarrierEffect extends Effect {barrierVersion:string|null}
export interface Hooks {point(name:string):Promise<void>}
const noHooks:Hooks={async point(){}};
const err=(code:"stale"|"unavailable"|"uncertain"):Observation=>({status:"error",code});
const uuid=()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,"0")).join("");
export interface RunnerClaim {identity:ResourceIdentity;instanceId:string;bootId:string;immutableSha256:string}
export interface RunnerReport extends RunnerClaim {operationId:string;claimId:string;result:BuildResult;attestationSha256:string}
export class Engine {
  private inFlight=false;
  constructor(readonly ledger:Ledger,readonly clock:Clock,readonly provider:Provider,readonly verifier:ObjectVerifier,private hooks:Hooks=noHooks,private pending?:RegistryContext){}
  private registry(){return this.pending?.registry??unavailableRegistry;}
  private fence(bytes:string,version:string,reason:string):void{this.ledger.storage.transactionSync(()=>this.ledger.fence(bytes,version,reason));}
  private async checked(identity:PendingIdentity,receipt:RegistrationReceipt){return checkedContext(this.pending,identity,receipt);}
  private trustedKind(platform:unknown):ResourceIdentity['provider']|null{
    try{if(platform!=='ios'&&platform!=='android')return null;const kind=this.provider.kind(platform);return ['unavailable','cloudflare-linux','external-macos'].includes(kind)?kind:null;}catch{return null;}
  }
  private providerMatches(r:Row):boolean{
    try{return r.provider_kind===this.trustedKind((JSON.parse(r.request_json) as WireRequest).ref.platform);}catch{return false;}
  }
  private fenceIdentity(r:Row):string{return this.pending?identityBytes(this.pending.identity):r.pending_identity_json??'[]';}
  // Called within the caller's synchronous ledger transaction. Do not repair or
  // replace a mismatched provider identity, including for durable-stop cleanup.
  private providerFenceInTransaction(r:Row):void{this.ledger.fence(this.fenceIdentity(r),r.state_version,'provider_binding_conflict');}
  private reportBinding(r:Row):string{
    // Delivery-only ack/outbox metadata may advance without changing authority.
    return JSON.stringify([r.operation_id,r.binding,r.binding_hash,r.request_json,r.epoch,r.revision,r.owner,r.expiry_us,r.clock_lower,r.clock_upper,r.clock_qualification,r.clock_floor,r.provider_kind,r.provider_key,r.pending_identity_json,r.registration_json,r.claim_state,r.claim_id,r.instance_id,r.boot_id,r.claim_barrier_version,r.phase,r.effect_id,r.effect_kind,r.effect_request_json,r.effect_state,r.effect_barrier_version,r.launch_dispatched]);
  }
  private trackSnapshotValid(current:Row|null,snapshot:Row,identity:PendingIdentity,bytes:string,mode:'start'|'ack'):boolean{
    const identityBytesFixed=identityBytes(identity);
    if(!current){this.ledger.fence(identityBytesFixed,snapshot.state_version,'track_missing_row');return false;}
    if(!this.providerMatches(current)){this.providerFenceInTransaction(current);return false;}
    if(this.ledger.fenced()||current.quarantined)return false;
    if(!retained(this.pending,current)||!matchesRow(identity,current)||current.operation_id!==snapshot.operation_id||current.binding!==snapshot.binding||current.binding_hash!==snapshot.binding_hash||current.provider_kind!==snapshot.provider_kind||current.provider_key!==snapshot.provider_key||current.pending_identity_json!==snapshot.pending_identity_json||current.registration_json!==snapshot.registration_json){
      this.ledger.fence(identityBytesFixed,current.state_version,'track_binding_changed');return false;
    }
    if(BigInt(current.state_version)<BigInt(snapshot.state_version)||BigInt(current.registry_ack_version)>BigInt(current.state_version)){
      this.ledger.fence(identityBytesFixed,snapshot.state_version,'track_history_regressed');return false;
    }
    // Admitted terminal evidence is permanent. Pending -> terminal at a newer
    // version is normal concurrent progress; rewriting a terminal is not.
    if(snapshot.terminal_json!==null&&(current.terminal_json!==snapshot.terminal_json||current.phase!==snapshot.phase)){
      this.ledger.fence(identityBytesFixed,current.state_version,'track_terminal_changed');return false;
    }
    if(current.state_version===snapshot.state_version&&(current.track_outbox_json!==bytes||current.terminal_json!==snapshot.terminal_json)){
      const alreadyAcked=current.track_outbox_json===null&&current.terminal_json===snapshot.terminal_json&&BigInt(current.registry_ack_version)>=BigInt(snapshot.state_version);
      if(!alreadyAcked){this.ledger.fence(identityBytesFixed,current.state_version,'track_projection_changed');return false;}
      if(mode==='start')return false;
    }
    return mode==='ack'||current.state_version===snapshot.state_version&&current.track_outbox_json===bytes;
  }
  // A single coalesced snapshot is attempted once. Out-of-order acknowledgement
  // may advance exact delivery metadata, but cannot erase a newer projection.
  async flushTrack():Promise<boolean>{
    const snapshot=this.ledger.read();if(!snapshot)return false;
    if(!this.providerMatches(snapshot)){this.fence(this.fenceIdentity(snapshot),snapshot.state_version,'provider_binding_conflict');await this.ledger.sync();return false;}
    if(this.ledger.fenced()||snapshot.quarantined)return false;
    if(!retained(this.pending,snapshot)){
      if(snapshot.registration_json&&this.pending){this.fence(identityBytes(this.pending.identity),snapshot.state_version,'retained_binding_conflict');await this.ledger.sync();}
      return false;
    }
    if(!snapshot.track_outbox_json)return true;
    const bytes=snapshot.track_outbox_json;
    let checked:Awaited<ReturnType<typeof checkedContext>>;
    try{checked=await this.checked(JSON.parse(snapshot.pending_identity_json!),JSON.parse(snapshot.registration_json!));}
    catch{this.fence(identityBytes(this.pending!.identity),snapshot.state_version,'retained_receipt_invalid');await this.ledger.sync();return false;}
    try{
      if(await sha(snapshot.binding)!==checked.identity.immutableSha256){this.fence(checked.bytes,snapshot.state_version,'track_binding_digest');await this.ledger.sync();return false;}
      const outbox=JSON.parse(bytes) as CoalescedTrackOutbox;
      registryExact(outbox,['stateVersion','nextDueUs','terminal']);registryDecimal(outbox.stateVersion);
      if(outbox.stateVersion!==snapshot.state_version)throw new Error('outbox_version');
      let projection:Projection;
      if(outbox.terminal){
        registryExact(outbox.terminal,['phase','exactJson']);
        if(outbox.terminal.exactJson!==snapshot.terminal_json||!['completed','stopped'].includes(outbox.terminal.phase)||outbox.nextDueUs!==null)throw new Error('terminal_outbox');
        projection={kind:'terminal',nextDueUs:null,phase:outbox.terminal.phase,evidenceSha256:await sha(outbox.terminal.exactJson)};
      }else{if(outbox.nextDueUs!==null)registryDecimal(outbox.nextDueUs);projection={kind:'pending',nextDueUs:outbox.nextDueUs};}
      await this.hooks.point('before_track');
      const ready=this.ledger.transaction(current=>this.trackSnapshotValid(current,snapshot,checked.identity,bytes,'start'));
      if(!ready){await this.ledger.sync();return false;}
      // No await between this final synchronous guard and RPC invocation.
      const call=await wait(this.registry().track({receipt:checked.receipt,stateVersion:outbox.stateVersion,projection}),250);
      if(!call.ok){this.ledger.transaction(current=>this.trackSnapshotValid(current,snapshot,checked.identity,bytes,'ack'));await this.ledger.sync();return false;}
      const ack=call.value;
      if(ack.status==='accepted'||ack.status==='duplicate'||ack.status==='stale'){
        registryExact(ack,['status','stateVersion']);registryDecimal(ack.stateVersion);
        if(ack.status!=='stale'&&ack.stateVersion!==outbox.stateVersion)throw new Error('ack_version');
        const valid=(current:Row|null):boolean=>{
          if(!this.trackSnapshotValid(current,snapshot,checked.identity,bytes,'ack'))return false;
          if(BigInt(ack.stateVersion)>BigInt(current!.state_version)){this.ledger.fence(checked.bytes,ack.stateVersion,'registry_ahead');return false;}
          return true;
        };
        if(ack.status==='stale'){this.ledger.transaction(valid);await this.ledger.sync();return false;}
        const clear=this.ledger.acknowledge(ack.stateVersion,bytes,valid);await this.ledger.sync();
        // Local sync can yield too. Do not return success under a newly restored
        // provider/identity/fence even if the earlier ACK transaction was valid.
        const final=this.ledger.transaction(current=>({valid:valid(current),empty:current?.track_outbox_json===null}));
        return clear&&final.valid&&final.empty;
      }
      registryExact(ack,['status']);
      this.ledger.transaction(current=>{
        if(!this.trackSnapshotValid(current,snapshot,checked.identity,bytes,'ack'))return;
        if(ack.status==='conflict')this.ledger.fence(checked.bytes,outbox.stateVersion,'track_conflict');
      });
      await this.ledger.sync();return false;
    }catch{return false;}
  }
  // This private API is called only after the authenticated top-level entry has
  // preregistered the fixed canonical identity. It adds no public HTTP route.
  async commandRegistered(request:WireRequest,resource:ResourceIdentity,identity:PendingIdentity,receipt:RegistrationReceipt):Promise<Observation>{
    try{
      const checked=await this.checked(identity,receipt);
      const prior=this.ledger.read();
      if(prior&&!this.providerMatches(prior)){this.fence(checked.bytes,prior.state_version,'provider_binding_conflict');await this.ledger.sync();return err('unavailable');}
      exact(resource,['provider','key','immutableSha256']);
      if(!matchesRequest(checked.identity,request)||resource.provider!==this.trustedKind(request.ref.platform)||resource.key!==checked.identity.operationKey||resource.immutableSha256!==checked.identity.immutableSha256)return err('unavailable');
      if(prior){
        if(!matchesRow(checked.identity,prior)||prior.pending_identity_json!==JSON.stringify(checked.identity)||prior.registration_json!==JSON.stringify(checked.receipt)){
          this.fence(checked.bytes,prior.state_version,'registered_command_conflict');await this.ledger.sync();return err('unavailable');
        }
        return this.command(request,resource);
      }
      if(this.ledger.fenced())return err('unavailable');
      const response=await wait(this.registry().register(checked.identity),250);
      if(!response.ok||!['registered','duplicate'].includes(response.value.status))return err('unavailable');
      const registered=response.value;
      if(registered.status!=='registered'&&registered.status!=='duplicate')return err('unavailable');
      registryExact(registered,['status','receipt']);
      const proven=await this.checked(checked.identity,registered.receipt);
      if(!same(proven.receipt,checked.receipt))return err('unavailable');
      await this.hooks.point('after_registration_validated');
      return this.commandAdmitted(request,resource,checked);
    }catch{return err('unavailable');}
  }
  private sample(r:Row|null):Interval|null {
    const i=this.clock.sample();if(!validInterval(i))return null;
    if(r&&i.upperUs<BigInt(r.clock_floor)){
      r.quarantined=1;r.phase="quarantined";this.ledger.save(r,"clock_rollback");return null;
    }return i;
  }
  // Preserve the exact accepted interval separately from the maximum historical
  // lower bound. Overlapping uncertainty intervals may move the latest lower
  // bound backwards, but can never ratchet the historical bound backwards.
  // Callers save this with the decision in the same synchronous transaction.
  private acceptTime(r:Row,i:Interval):void {
    r.clock_lower=String(i.lowerUs);r.clock_upper=String(i.upperUs);r.clock_qualification=i.qualificationId;
    if(i.lowerUs>BigInt(r.clock_floor))r.clock_floor=String(i.lowerUs);
  }
  private live(r:Row,i:Interval):boolean {
    const request=JSON.parse(r.request_json) as WireRequest;
    return i.upperUs<BigInt(r.expiry_us)&&i.upperUs<BigInt(request.deadline_ms)*1000n;
  }
  private stop(r:Row):void {
    r.desired="stop";if(r.claim_state==="unissued")r.claim_state="revoked";
    if(r.terminal_json)return;
    r.phase="stop_pending";
    if(r.effect_kind!=="stop"||r.effect_state==="settled"){
      r.effect_id=uuid();r.effect_kind="stop";r.effect_state="prepared";
      r.effect_request_json=r.request_json;
    }
  }
  private due(r:Row,interval:Interval|null):void {
    // Alarms are scheduling hints, not authorization clocks. Avoid converting
    // protocol int64 timestamps into JS number-valued alarm times.
    const delay=Math.min(60_000,1000*2**Math.min(r.failures,6));
    r.next_due_us=String((interval?.upperUs??BigInt(r.clock_upper))+BigInt(delay)*1000n);
  }
  private terminal(r:Row):Observation|null {return r.terminal_json?JSON.parse(r.terminal_json) as Observation:null;}
  private current(r:Row):Observation {
    const terminal=this.terminal(r);if(terminal)return terminal;
    if(r.quarantined)return err("unavailable");
    if(r.phase==="unlaunched"&&r.desired==="none")return {status:"absent"};
    if(r.phase==="running"||r.phase==="claim_consumed")return {status:"running"};
    return err("uncertain");
  }
  async command(request:WireRequest,identity:ResourceIdentity):Promise<Observation>{
    if(!this.ledger.read())return err('unavailable');
    return this.commandAdmitted(request,identity);
  }
  private async commandAdmitted(request:WireRequest,identity:ResourceIdentity,registration?:{identity:PendingIdentity;receipt:RegistrationReceipt;bytes:string}):Promise<Observation>{
    let action=false;
    const admitted=this.ledger.transaction(row=>{
      if(row&&!this.providerMatches(row)){this.providerFenceInTransaction(row);return err('unavailable');}
      if(identity.provider!==this.trustedKind(request.ref.platform))return err('unavailable');
      if(this.ledger.fenced()&&row?.desired!=='stop')return err('unavailable');
      if(!row&&!registration)return err('unavailable');
      if(row&&!retained(this.pending,row))return err('unavailable');
      if(row&&(row.operation_id!==request.operation_id||row.binding_hash!==request.immutable_sha256||row.binding!==immutableBytes(request)))invalid();
      if(row){
        const e=BigInt(request.guard.epoch),old=BigInt(row.epoch),v=BigInt(request.guard.revision),previous=BigInt(row.revision);
        if(e<old||(e===old&&(v<previous||request.guard.owner_id!==row.owner))||
          (e===old&&v===previous&&BigInt(request.guard.expires_at_us)<BigInt(row.expiry_us)))return err("stale");
      }
      const interval=this.sample(row);if(!interval||row?.quarantined)return err("unavailable");
      if(interval.upperUs>=BigInt(request.guard.expires_at_us)||interval.upperUs>=BigInt(request.deadline_ms)*1000n)return err("stale");
      if(request.command==="ensure_started"&&!this.provider.available&&!row?.terminal_json)return err("unavailable");
      const r=row??this.ledger.initial(request,interval,identity);
      if(!row){r.pending_identity_json=JSON.stringify(registration!.identity);r.registration_json=JSON.stringify(registration!.receipt);}
      r.epoch=request.guard.epoch;r.revision=request.guard.revision;r.owner=request.guard.owner_id;r.expiry_us=request.guard.expires_at_us;
      r.request_json=JSON.stringify(request);this.acceptTime(r,interval);
      if(request.command==="stop")this.stop(r);
      else if(request.command==="ensure_started"&&r.desired!=="stop"&&!r.terminal_json&&r.launch_dispatched===0){
        r.desired="run";r.phase="launch_pending";r.effect_kind="launch";r.effect_id=uuid();r.effect_state="prepared";r.effect_request_json=JSON.stringify(request);
      }
      if(!r.terminal_json&&r.desired!=="none"){this.due(r,interval);action=true;}
      if(r.effect_kind&&!r.terminal_json)r.effect_barrier_version=this.ledger.nextVersion(r);
      if(r.claim_state==='consumed'&&!r.terminal_json)r.claim_barrier_version=this.ledger.nextVersion(r);
      this.ledger.save(r,"request");return this.current(r);
    });
    await this.ledger.sync();
    if(!action&&!(admitted.status==='error'&&admitted.code!=='uncertain')){await this.flushTrack();await this.arm();}
    if(action){
      try{await this.arm();await this.hooks.point("after_intent");await this.reconcile();}
      catch{return err("uncertain");}
    }
    // Rejection must not turn into an observation from an unrelated concurrent
    // valid request. Only admitted invocations read the resulting ledger.
    if(admitted.status==="error"&&admitted.code!=="uncertain")return admitted;
    return this.ledger.read()?this.current(this.ledger.read()!):admitted;
  }
  private prepare():BarrierEffect|null {
    return this.ledger.transaction(r=>{
      if(r&&!this.providerMatches(r)){this.providerFenceInTransaction(r);return null;}
      if(!r||r.terminal_json||((r.quarantined||this.ledger.fenced()||!retained(this.pending,r))&&r.desired!=="stop")||!this.provider.available)return null;
      const interval=this.sample(r);
      const request=JSON.parse(r.request_json) as WireRequest;
      if(interval&&interval.lowerUs>=BigInt(request.deadline_ms)*1000n)this.stop(r);
      if(r.desired==="none")return null;
      if(r.desired!=="stop"&&(!interval||!this.live(r,interval)))return null;
      let kind:"launch"|"inspect"|"stop";
      if(r.desired==="stop")kind="stop";
      else if(r.effect_kind==="launch"&&r.effect_state==="prepared"&&r.launch_dispatched===0){
        const issued=r.effect_request_json?JSON.parse(r.effect_request_json) as WireRequest:null;
        if(!issued||!this.sameGuard(r,issued))return null;
        kind="launch";
      }
      else kind="inspect";
      // A marked-dispatched launch is never retried, even if a crash occurred
      // before its provider call. This sacrifices liveness to avoid duplication.
      if(kind==="launch")r.launch_dispatched=1;
      if(interval)this.acceptTime(r,interval);
      const reuse=kind===r.effect_kind&&r.effect_state==="prepared";
      r.effect_id=reuse?r.effect_id:uuid();
      if(!reuse)r.effect_request_json=r.request_json;
      r.effect_kind=kind;r.effect_state="dispatched";
      this.due(r,interval);r.effect_barrier_version=this.ledger.nextVersion(r);this.ledger.save(r,"effect_dispatched");
      return {id:r.effect_id!,kind,barrierVersion:r.effect_barrier_version,identity:this.ledger.identity(r),request:JSON.parse(r.effect_request_json!) as WireRequest};
    });
  }
  private sameGuard(r:Row,request:WireRequest):boolean {
    const g=request.guard;return g.epoch===r.epoch&&g.revision===r.revision&&g.owner_id===r.owner&&g.expires_at_us===r.expiry_us;
  }
  private finalCheck(effect:BarrierEffect):boolean {
    return this.ledger.transaction(r=>{
      if(r&&!this.providerMatches(r)){this.providerFenceInTransaction(r);return false;}
      if(!r||(r.quarantined&&effect.kind!=="stop")||r.terminal_json||r.effect_id!==effect.id||r.effect_kind!==effect.kind)return false;
      if(effect.identity.provider!==r.provider_kind||effect.identity.key!==r.provider_key||effect.identity.immutableSha256!==r.binding_hash)return false;
      if(effect.kind==="stop")return r.desired==="stop";
      if(this.ledger.fenced()||!retained(this.pending,r)||!effect.barrierVersion||r.effect_barrier_version!==effect.barrierVersion||BigInt(r.registry_ack_version)<BigInt(effect.barrierVersion))return false;
      const interval=this.sample(r);
      if(!interval||r.desired!=="run"||!this.sameGuard(r,effect.request)||!this.live(r,interval))return false;
      this.acceptTime(r,interval);this.ledger.save(r,"effect_time_accepted");return true;
    });
  }
  private observation(value:unknown,identity:ResourceIdentity):ProviderObservation|null {
    try{
      exact(value,["identity","state","instanceId","bootId","definitive","descendantsGone","launchesSettled","diagnosticSha256"]);
      exact(value.identity,["provider","key","immutableSha256"]);
      if(value.identity.provider!==identity.provider||value.identity.key!==identity.key||value.identity.immutableSha256!==identity.immutableSha256||!["absent","inert","running","unknown"].includes(value.state as string))return null;
      for(const k of ["definitive","descendantsGone","launchesSettled"])if(typeof value[k]!=="boolean")return null;
      if(value.instanceId!==null)text(value.instanceId);if(value.bootId!==null)text(value.bootId);hex(value.diagnosticSha256);
      if((value.state==="inert"||value.state==="running")&&(!value.instanceId||!value.bootId))return null;
      return value as unknown as ProviderObservation;
    }catch{return null;}
  }
  private accept(effect:BarrierEffect,raw:unknown):void {
    const obs=this.observation(raw,effect.identity);
    this.ledger.transaction(r=>{
      if(r&&!this.providerMatches(r)){this.providerFenceInTransaction(r);return;}
      if(!r||r.effect_id!==effect.id||r.effect_kind!==effect.kind||r.terminal_json)return;
      const interval=this.sample(r);
      if(r.quarantined&&effect.kind!=="stop")return;
      if(interval)this.acceptTime(r,interval);
      if(effect.kind!=="stop"&&!this.sameGuard(r,effect.request)){
        r.effect_state="uncertain";this.due(r,interval);this.ledger.save(r,"stale_effect_observation");return;
      }
      if(!obs){r.effect_state="uncertain";r.failures=Math.min(32,r.failures+1);this.due(r,interval);this.ledger.save(r,"provider_uncertain");return;}
      r.effect_state="settled";r.failures=0;
      if(r.desired==="stop") {
        // Outage cleanup is permitted, but terminal/quiescent admission retains
        // the normal delivery barrier and monotonic qualified clock. An expired
        // run guard cannot prevent stopping; it is deliberately not renewed.
        const terminalReady=!!interval&&!r.quarantined&&!this.ledger.fenced()&&retained(this.pending,r)&&!!effect.barrierVersion&&r.effect_barrier_version===effect.barrierVersion&&BigInt(r.registry_ack_version)>=BigInt(effect.barrierVersion);
        if(terminalReady&&obs.state==="absent"&&obs.definitive&&obs.descendantsGone&&obs.launchesSettled){
          const terminal:Observation=r.pending_result_json?{status:"completed",result:JSON.parse(r.pending_result_json) as BuildResult}:{status:"stopped",diagnostic_sha256:obs.diagnosticSha256};
          r.terminal_json=JSON.stringify(terminal);r.phase=terminal.status==="completed"?"completed":"stopped";r.next_due_us=null;
        }else r.phase="stop_pending";
      } else {
        const sameBoot=(!r.instance_id||r.instance_id===obs.instanceId)&&(!r.boot_id||r.boot_id===obs.bootId);
        if(r.claim_state==="consumed"&&!sameBoot){this.stop(r);r.phase="stop_pending";}
        else if(obs.state==="inert"&&r.claim_state==="unissued"){
          r.instance_id=obs.instanceId;r.boot_id=obs.bootId;r.phase="inert";
        } else if(obs.state==="running"&&r.claim_state==="consumed"&&sameBoot)r.phase="running";
        else if(obs.state==="absent"||obs.state==="unknown")r.phase="uncertain";
        // An unexpected running process without our one-shot claim is killed.
        else if(obs.state==="running"&&r.claim_state!=="consumed")this.stop(r);
      }
      if(!r.terminal_json)this.due(r,interval);this.ledger.save(r,"provider_observed");
    });
  }
  async reconcile():Promise<void>{
    if(this.inFlight)return;this.inFlight=true;
    let effect:BarrierEffect|null=null;
    let workSettled=true;
    let finished=false;
    try{
      await this.arm();
      const intentTracked=await this.flushTrack();
      if(!intentTracked&&this.ledger.read()?.desired!=='stop')return;
      effect=this.prepare();await this.ledger.sync();await this.arm();
      const dispatchTracked=effect?await this.flushTrack():false;
      if(!effect||(!dispatchTracked&&effect.kind!=='stop')||!this.finalCheck(effect))return;
      const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
      try{
        workSettled=false;
        const work=effect.kind==="launch"?this.provider.launchInert(effect,controller.signal):effect.kind==="stop"?this.provider.stop(effect,controller.signal):this.provider.inspect(effect,controller.signal);
        // A noncooperative adapter retains the one owned-call slot until its
        // cleanup is observed; timeout alone is never a resource-release proof.
        const settled=()=>{workSettled=true;if(finished)this.inFlight=false;};
        void work.then(settled,settled);
        const timeout=new Promise<never>((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new Error("provider_timeout"));},2000);});
        await this.hooks.point("after_dispatch");
        const observation=await Promise.race([work,timeout]);
        await this.hooks.point("after_provider_effect");
        this.accept(effect,observation);await this.ledger.sync();await this.flushTrack();
      }finally{controller.abort();if(timer!==undefined)clearTimeout(timer);}
    }catch{
      const id=effect?.id;
      this.ledger.transaction(r=>{if(r&&r.effect_id===id&&!r.terminal_json){r.effect_state="uncertain";r.failures=Math.min(32,r.failures+1);this.due(r,null);this.ledger.save(r,"effect_uncertain");}});
      await this.ledger.sync();
    }finally{finished=true;if(workSettled)this.inFlight=false;await this.arm();}
  }
  async arm():Promise<void>{
    const existing=await this.ledger.storage.getAlarm(),r=this.ledger.read();
    // Even a quiescent registry terminal may have a lost ACK. Its exact local
    // outbox keeps a bounded operation alarm until delivery metadata is durable.
    // Re-read after the await so an older arm cannot erase a newly queued outbox.
    if(!r||(!r.next_due_us&&!r.track_outbox_json)){
      if(existing!==null)await this.ledger.storage.deleteAlarm();return;
    }
    // Platform time remains a wake hint, never authorization.
    const delay=Math.min(60000,1000*2**Math.min(r.failures,6));
    const next=Date.now()+delay;
    if(existing===null||existing>next)await this.ledger.storage.setAlarm(next);
    await this.ledger.sync();
  }
  async alarm():Promise<void>{try{await this.reconcile();}finally{await this.arm();}}
  async recover():Promise<void>{
    // Constructor recovery never overwrites an earlier alarm or dispatches a
    // possibly duplicated launch. An already-marked launch will be inspected.
    this.ledger.transaction(r=>{if(r&&!this.providerMatches(r)){this.providerFenceInTransaction(r);return;}if(r&&r.effect_state==="dispatched"&&!r.terminal_json){r.effect_state="uncertain";this.ledger.save(r,"restart_uncertain");}});
    await this.ledger.sync();await this.flushTrack();await this.arm();
  }
  private validClaim(value:unknown,report=false):boolean {
    try{
      exact(value,report?["identity","instanceId","bootId","immutableSha256","operationId","claimId","result","attestationSha256"]:["identity","instanceId","bootId","immutableSha256"]);
      exact(value.identity,["provider","key","immutableSha256"]);
      if(value.identity.provider!=="cloudflare-linux"&&value.identity.provider!=="external-macos")return false;
      hex(value.identity.key);hex(value.identity.immutableSha256);hex(value.immutableSha256);text(value.instanceId);text(value.bootId);
      if(report){hex(value.operationId);hex(value.claimId,32);hex(value.attestationSha256);}
      return true;
    }catch{return false;}
  }
  async claim(claim:RunnerClaim):Promise<{granted:boolean;claimId?:string}>{
    if(!this.validClaim(claim))return {granted:false};
    await this.hooks.point("before_claim_grant");
    const prospective=this.ledger.transaction(r=>{
      if(r&&!this.providerMatches(r)){this.providerFenceInTransaction(r);return null;}
      if(!r||r.quarantined||this.ledger.fenced()||!retained(this.pending,r)||r.desired!=="run"||r.terminal_json||r.claim_state!=="unissued"||r.phase!=="inert")return null;
      if(claim.immutableSha256!==r.binding_hash||claim.identity.provider!==r.provider_kind||claim.identity.key!==r.provider_key||claim.identity.immutableSha256!==r.binding_hash||claim.instanceId!==r.instance_id||claim.bootId!==r.boot_id)return null;
      const i=this.sample(r);if(!i||!this.live(r,i))return null;
      this.acceptTime(r,i);
      r.claim_state="consumed";r.claim_id=uuid();r.phase="claim_consumed";r.claim_barrier_version=this.ledger.nextVersion(r);this.ledger.save(r,"claim_consumed");
      return {claim_barrier_version:r.claim_barrier_version,operation_id:r.operation_id,binding:r.binding,binding_hash:r.binding_hash,
        epoch:r.epoch,revision:r.revision,owner:r.owner,expiry_us:r.expiry_us,
        provider_kind:r.provider_kind,provider_key:r.provider_key,instance_id:r.instance_id,boot_id:r.boot_id,claim_id:r.claim_id};
    });
    await this.ledger.sync();await this.hooks.point("after_claim_commit");
    if(prospective)await this.flushTrack();
    // Consumption is already durable. This is the grant's linearization point,
    // after every await: compare the exact consumed authority and identity with
    // the current row, then accept the exact final qualified sample atomically.
    // No await follows this decision. The DO's default output gate confirms its
    // final clock-history write before the response becomes externally visible.
    return this.ledger.transaction(r=>{
      if(r&&!this.providerMatches(r)){this.providerFenceInTransaction(r);return {granted:false};}
      if(!prospective||!r||this.ledger.fenced()||!retained(this.pending,r)||!prospective.claim_barrier_version||BigInt(r.registry_ack_version)<BigInt(prospective.claim_barrier_version)||r.desired!=="run"||r.quarantined||r.terminal_json||r.claim_state!=="consumed"||r.phase!=="claim_consumed")return {granted:false};
      for(const key of Object.keys(prospective) as (keyof typeof prospective)[])if(r[key]!==prospective[key])return {granted:false};
      const i=this.sample(r);if(!i||!this.live(r,i))return {granted:false};
      this.acceptTime(r,i);this.ledger.save(r,"claim_grant_time_accepted");
      return {granted:true,claimId:prospective.claim_id};
    });
  }

  async report(report:RunnerReport):Promise<"accepted"|"duplicate"|"rejected">{
    if(!this.validClaim(report,true))return "rejected";
    let parsed:BuildResult;try{parsed=result(report.result);hex(report.attestationSha256);}catch{return "rejected";}
    const hash=await sha(JSON.stringify(report));const r=this.ledger.read();
    if(r&&!this.providerMatches(r)){this.fence(this.fenceIdentity(r),r.state_version,'provider_binding_conflict');await this.ledger.sync();return 'rejected';}
    if(!r||r.quarantined||this.ledger.fenced()||!retained(this.pending,r)||r.claim_state!=="consumed"||report.claimId!==r.claim_id||report.operationId!==r.operation_id||report.immutableSha256!==r.binding_hash||report.identity.key!==r.provider_key||report.identity.provider!==r.provider_kind||report.identity.immutableSha256!==r.binding_hash||report.instanceId!==r.instance_id||report.bootId!==r.boot_id)return "rejected";
    if(r.report_hash)return r.report_hash===hash?"duplicate":"rejected";
    if(r.desired==="stop"||r.terminal_json)return "rejected";
    const version=r.state_version,request=JSON.parse(r.request_json) as WireRequest,authority=this.reportBinding(r);
    try{await this.checked(JSON.parse(r.pending_identity_json!),JSON.parse(r.registration_json!));}catch{return 'rejected';}
    if(!await this.verifier.verify(request,parsed,report.attestationSha256))return "rejected";
    const accepted=this.ledger.transaction(current=>{
      if(current&&!this.providerMatches(current)){this.providerFenceInTransaction(current);return false;}
      if(!current||this.ledger.fenced()||current.quarantined||!retained(this.pending,current)||this.reportBinding(current)!==authority||current.state_version!==version||current.report_hash||current.terminal_json||current.pending_result_json||current.desired!=="run")return false;
      const i=this.sample(current);if(!i||!this.live(current,i))return false;
      this.acceptTime(current,i);
      current.report_hash=hash;current.pending_result_json=JSON.stringify(parsed);this.stop(current);this.due(current,i);this.ledger.save(current,"result_pending_teardown");return true;
    });
    await this.ledger.sync();await this.arm();return accepted?"accepted":"rejected";
  }
  async recoverKnown(identity:PendingIdentity,receipt:RegistrationReceipt,value:WakeTicket):Promise<RecoveryDisposition>{
    let checked:Awaited<ReturnType<typeof checkedContext>>;
    try{
      if(!this.pending)return {status:'unavailable'};
      let t:WakeTicket;
      try{t=registryTicket(value,{generation:this.pending.identity.namespaceGeneration,operationsNamespace:'fixed-operation-binding',registryNamespace:'fixed-registry-binding'});}catch{return {status:'conflict'};}
      if(t.runId==='0'||t.attemptSequence==='0')return {status:'conflict'};
      try{checked=await this.checked(identity,receipt);if(!same(t.receipt,checked.receipt))throw new Error('ticket_receipt_conflict');}
      catch{this.fence(identityBytes(this.pending.identity),t.trackedVersion,'recovery_binding_conflict');await this.ledger.sync();return {status:'quarantined'};}
      const r=this.ledger.read();
      if(this.ledger.fenced())return {status:'quarantined'};
      if(!r){
        if(t.trackedVersion==='0')return {status:'empty_orphan'};
        this.fence(checked.bytes,t.trackedVersion,'positive_missing');await this.ledger.sync();return {status:'quarantined'};
      }
      if(!this.providerMatches(r)||!matchesRow(checked.identity,r)||await sha(r.binding)!==checked.identity.immutableSha256||r.pending_identity_json!==JSON.stringify(checked.identity)||r.registration_json!==JSON.stringify(checked.receipt)||BigInt(r.state_version)<BigInt(t.trackedVersion)){
        this.fence(checked.bytes,t.trackedVersion,'recovery_identity_or_regression');await this.ledger.sync();return {status:'quarantined'};
      }
      // Hashing/validation above may yield: recheck current durable state before
      // any recovery. A concurrent newer local row always wins the old scan.
      const current=this.ledger.read();
      if(!current||!this.providerMatches(current)||!matchesRow(checked.identity,current)||current.binding!==r.binding||current.pending_identity_json!==JSON.stringify(checked.identity)||current.registration_json!==JSON.stringify(checked.receipt)||BigInt(current.state_version)<BigInt(t.trackedVersion)){
        this.fence(checked.bytes,t.trackedVersion,'recovery_changed');await this.ledger.sync();return {status:'quarantined'};
      }
      if(current.quarantined&&current.desired!=='stop')return {status:'quarantined'};
      if(this.inFlight)return {status:'busy'};
      await this.reconcile();
      const after=this.ledger.read();if(!after)return {status:'unavailable'};
      if(!this.providerMatches(after)){this.fence(checked.bytes,after.state_version,'provider_binding_conflict');await this.ledger.sync();return {status:'quarantined'};}
      if(after.terminal_json){
        const json=after.terminal_json,version=after.state_version,phase=(JSON.parse(json) as {status:'completed'|'stopped'}).status;
        const digest=await sha(json);
        await this.hooks.point('before_recovery_terminal_return');
        const last=this.ledger.read();
        if(last&&!this.providerMatches(last)){this.fence(checked.bytes,last.state_version,'provider_binding_conflict');await this.ledger.sync();return {status:'quarantined'};}
        if(this.ledger.fenced()||last?.quarantined)return {status:'quarantined'};
        if(!last||last.state_version!==version||last.terminal_json!==json||last.binding!==after.binding||!matchesRow(checked.identity,last)||last.pending_identity_json!==JSON.stringify(checked.identity)||last.registration_json!==JSON.stringify(checked.receipt))return {status:'unavailable'};
        return {status:'terminal',stateVersion:version,projection:{kind:'terminal',nextDueUs:null,phase,evidenceSha256:digest}};
      }
      if(after.quarantined||this.ledger.fenced())return {status:'quarantined'};
      return {status:'pending',stateVersion:after.state_version};
    }catch{return {status:'conflict'};}
  }
  async enrollExisting(identity:PendingIdentity):Promise<'enrolled'|'missing'|'conflict'|'unavailable'>{
    const prior=this.ledger.read();if(!prior)return 'missing';
    if(!this.providerMatches(prior)){this.fence(this.fenceIdentity(prior),prior.state_version,'provider_binding_conflict');await this.ledger.sync();return 'conflict';}
    try{
      // The maintenance caller explicitly supplies one existing identity. No
      // scan, namespace enumeration, restore authority or quarantine clearing.
      if(!this.pending||identityBytes(identity)!==identityBytes(this.pending.identity)||!matchesRow(identity,prior)||await sha(prior.binding)!==identity.immutableSha256)return 'conflict';
      const result=await wait(this.registry().register(identity),250);if(!result.ok)return 'unavailable';
      const registered=result.value;if(registered.status!=='registered'&&registered.status!=='duplicate')return registered.status==='conflict'?'conflict':'unavailable';
      const checked=await this.checked(identity,registered.receipt);
      const enrolled=this.ledger.transaction(r=>{
        if(r&&!this.providerMatches(r)){this.providerFenceInTransaction(r);return false;}
        if(!r||r.binding!==prior.binding||!matchesRow(checked.identity,r))return false;
        if(r.registration_json&&r.registration_json!==JSON.stringify(checked.receipt))return false;
        if(r.pending_identity_json&&r.pending_identity_json!==JSON.stringify(checked.identity))return false;
        r.pending_identity_json=JSON.stringify(checked.identity);r.registration_json=JSON.stringify(checked.receipt);
        this.ledger.save(r,'explicit_existing_enrollment');return true;
      });
      await this.ledger.sync();if(!enrolled)return 'conflict';await this.flushTrack();return 'enrolled';
    }catch{return 'unavailable';}
  }
  async quarantine():Promise<void>{
    this.ledger.transaction(r=>{if(r){r.quarantined=1;if(!r.terminal_json)r.phase="quarantined";this.ledger.save(r,"restore_quarantine");}});await this.ledger.sync();
  }
}
