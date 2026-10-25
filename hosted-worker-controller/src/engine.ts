import {Clock,Interval,validInterval} from "./clock.js";
import {Ledger,Row} from "./ledger.js";
import {Effect,ObjectVerifier,Provider,ProviderObservation,ResourceIdentity} from "./provider.js";
import {BuildResult,decimal,exact,hex,immutableBytes,invalid,Observation,result,sha,text,WireRequest} from "./wire.js";
export interface Hooks {point(name:string):Promise<void>}
const noHooks:Hooks={async point(){}};
const err=(code:"stale"|"unavailable"|"uncertain"):Observation=>({status:"error",code});
const uuid=()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,"0")).join("");
export interface RunnerClaim {identity:ResourceIdentity;instanceId:string;bootId:string;immutableSha256:string}
export interface RunnerReport extends RunnerClaim {operationId:string;claimId:string;result:BuildResult;attestationSha256:string}
export class Engine {
  private inFlight=false;
  constructor(readonly ledger:Ledger,readonly clock:Clock,readonly provider:Provider,readonly verifier:ObjectVerifier,private hooks:Hooks=noHooks){}
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
    let action=false;
    const admitted=this.ledger.transaction(row=>{
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
      r.epoch=request.guard.epoch;r.revision=request.guard.revision;r.owner=request.guard.owner_id;r.expiry_us=request.guard.expires_at_us;
      r.request_json=JSON.stringify(request);this.acceptTime(r,interval);
      if(request.command==="stop")this.stop(r);
      else if(request.command==="ensure_started"&&r.desired!=="stop"&&!r.terminal_json&&r.launch_dispatched===0){
        r.desired="run";r.phase="launch_pending";r.effect_kind="launch";r.effect_id=uuid();r.effect_state="prepared";r.effect_request_json=JSON.stringify(request);
      }
      if(!r.terminal_json&&r.desired!=="none"){this.due(r,interval);action=true;}
      this.ledger.save(r,"request");return this.current(r);
    });
    await this.ledger.sync();
    if(action){
      try{await this.arm();await this.hooks.point("after_intent");await this.reconcile();}
      catch{return err("uncertain");}
    }
    // Rejection must not turn into an observation from an unrelated concurrent
    // valid request. Only admitted invocations read the resulting ledger.
    if(admitted.status==="error"&&admitted.code!=="uncertain")return admitted;
    return this.ledger.read()?this.current(this.ledger.read()!):admitted;
  }
  private prepare():Effect|null {
    return this.ledger.transaction(r=>{
      if(!r||r.terminal_json||(r.quarantined&&r.desired!=="stop")||!this.provider.available)return null;
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
      this.due(r,interval);this.ledger.save(r,"effect_dispatched");
      return {id:r.effect_id!,kind,identity:this.ledger.identity(r),request:JSON.parse(r.effect_request_json!) as WireRequest};
    });
  }
  private sameGuard(r:Row,request:WireRequest):boolean {
    const g=request.guard;return g.epoch===r.epoch&&g.revision===r.revision&&g.owner_id===r.owner&&g.expires_at_us===r.expiry_us;
  }
  private finalCheck(effect:Effect):boolean {
    return this.ledger.transaction(r=>{
      if(!r||(r.quarantined&&effect.kind!=="stop")||r.terminal_json||r.effect_id!==effect.id||r.effect_kind!==effect.kind)return false;
      if(effect.kind==="stop")return r.desired==="stop";
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
  private accept(effect:Effect,raw:unknown):void {
    const obs=this.observation(raw,effect.identity);
    this.ledger.transaction(r=>{
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
        if(obs.state==="absent"&&obs.definitive&&obs.descendantsGone&&obs.launchesSettled){
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
    let effect:Effect|null=null;
    let workSettled=true;
    let finished=false;
    try{
      await this.arm();effect=this.prepare();await this.ledger.sync();await this.arm();if(!effect||!this.finalCheck(effect))return;
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
        this.accept(effect,observation);await this.ledger.sync();
      }finally{controller.abort();if(timer!==undefined)clearTimeout(timer);}
    }catch{
      const id=effect?.id;
      this.ledger.transaction(r=>{if(r&&r.effect_id===id&&!r.terminal_json){r.effect_state="uncertain";r.failures=Math.min(32,r.failures+1);this.due(r,null);this.ledger.save(r,"effect_uncertain");}});
      await this.ledger.sync();
    }finally{finished=true;if(workSettled)this.inFlight=false;await this.arm();}
  }
  async arm():Promise<void>{
    const r=this.ledger.read();if(!r?.next_due_us){if(await this.ledger.storage.getAlarm()!==null)await this.ledger.storage.deleteAlarm();return;}
    // Relative scheduling uses platform time only as a wake hint. Authorization
    // always samples the qualified Clock after acquiring the ledger transaction.
    const delay=Math.min(60000,1000*2**Math.min(r.failures,6));
    const next=Date.now()+delay;
    const existing=await this.ledger.storage.getAlarm();
    if(existing===null||existing>next)await this.ledger.storage.setAlarm(next);
    await this.ledger.sync();
  }
  async alarm():Promise<void>{try{await this.reconcile();}finally{await this.arm();}}
  async recover():Promise<void>{
    // Constructor recovery never overwrites an earlier alarm or dispatches a
    // possibly duplicated launch. An already-marked launch will be inspected.
    this.ledger.transaction(r=>{if(r&&r.effect_state==="dispatched"&&!r.terminal_json){r.effect_state="uncertain";this.ledger.save(r,"restart_uncertain");}});
    await this.ledger.sync();await this.arm();
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
      if(!r||r.quarantined||r.desired!=="run"||r.terminal_json||r.claim_state!=="unissued"||r.phase!=="inert")return null;
      if(claim.immutableSha256!==r.binding_hash||claim.identity.provider!==r.provider_kind||claim.identity.key!==r.provider_key||claim.identity.immutableSha256!==r.binding_hash||claim.instanceId!==r.instance_id||claim.bootId!==r.boot_id)return null;
      const i=this.sample(r);if(!i||!this.live(r,i))return null;
      this.acceptTime(r,i);
      r.claim_state="consumed";r.claim_id=uuid();r.phase="claim_consumed";this.ledger.save(r,"claim_consumed");
      return {operation_id:r.operation_id,binding:r.binding,binding_hash:r.binding_hash,
        epoch:r.epoch,revision:r.revision,owner:r.owner,expiry_us:r.expiry_us,
        provider_kind:r.provider_kind,provider_key:r.provider_key,instance_id:r.instance_id,boot_id:r.boot_id,claim_id:r.claim_id};
    });
    await this.ledger.sync();await this.hooks.point("after_claim_commit");
    // Consumption is already durable. This is the grant's linearization point,
    // after every await: compare the exact consumed authority and identity with
    // the current row, then accept the exact final qualified sample atomically.
    // No await follows this decision. The DO's default output gate confirms its
    // final clock-history write before the response becomes externally visible.
    return this.ledger.transaction(r=>{
      if(!prospective||!r||r.desired!=="run"||r.quarantined||r.terminal_json||r.claim_state!=="consumed"||r.phase!=="claim_consumed")return {granted:false};
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
    if(!r||r.quarantined||r.claim_state!=="consumed"||report.claimId!==r.claim_id||report.operationId!==r.operation_id||report.immutableSha256!==r.binding_hash||report.identity.key!==r.provider_key||report.identity.provider!==r.provider_kind||report.identity.immutableSha256!==r.binding_hash||report.instanceId!==r.instance_id||report.bootId!==r.boot_id)return "rejected";
    if(r.report_hash)return r.report_hash===hash?"duplicate":"rejected";
    if(r.desired==="stop"||r.terminal_json)return "rejected";
    const version=r.state_version,request=JSON.parse(r.request_json) as WireRequest;
    if(!await this.verifier.verify(request,parsed,report.attestationSha256))return "rejected";
    const accepted=this.ledger.transaction(current=>{
      if(!current||current.state_version!==version||current.report_hash||current.desired!=="run"||current.quarantined)return false;
      const i=this.sample(current);if(!i||!this.live(current,i))return false;
      this.acceptTime(current,i);
      current.report_hash=hash;current.pending_result_json=JSON.stringify(parsed);this.stop(current);this.due(current,i);this.ledger.save(current,"result_pending_teardown");return true;
    });
    await this.ledger.sync();await this.arm();return accepted?"accepted":"rejected";
  }
  async quarantine():Promise<void>{
    this.ledger.transaction(r=>{if(r){r.quarantined=1;r.phase="quarantined";this.ledger.save(r,"restore_quarantine");}});await this.ledger.sync();
  }
}
