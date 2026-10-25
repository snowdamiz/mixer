// EXCLUDED VERIFICATION ENTRY. Never deploy this Worker or its DO export.
import {DurableObject} from "cloudflare:workers";
import {Clock,Interval} from "../src/clock.js";
import {Engine,Hooks,RunnerReport} from "../src/engine.js";
import {Ledger} from "../src/ledger.js";
import {ingress,operationKey,PrincipalEnv} from "../src/principal.js";
import {Effect,ObjectVerifier,Provider,ProviderObservation} from "../src/provider.js";
import {errorResponse,parseJSON,reply} from "../src/wire.js";

interface Env extends PrincipalEnv {OPERATIONS:DurableObjectNamespace}
interface ClockSetting {nowUs:string;errorUs:string;qualified:boolean}
interface Settings {clock:ClockSetting;fault:{point:string;behavior:string}|null;observation:Partial<ProviderObservation>|null;objectVerified:boolean;barrier:boolean;holdProvider:boolean;clockSequence:ClockSetting[];alarmTicks:number}
const defaults=():Settings=>({clock:{nowUs:"1900000000000000",errorUs:"1",qualified:true},fault:null,observation:null,objectVerified:false,barrier:false,holdProvider:false,clockSequence:[],alarmTicks:0});
const json=(v:unknown)=>new Response(JSON.stringify(v),{headers:{"Content-Type":"application/json"}});
class TestStore {
  constructor(readonly sql:SqlStorage){sql.exec("CREATE TABLE IF NOT EXISTS test_settings(singleton INTEGER PRIMARY KEY CHECK(singleton=1),value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS test_calls(sequence INTEGER PRIMARY KEY AUTOINCREMENT,value TEXT NOT NULL)");}
  get():Settings {const r=this.sql.exec<{value:string}>("SELECT value FROM test_settings WHERE singleton=1").toArray()[0];return r?JSON.parse(r.value):defaults();}
  set(s:Settings):void {this.sql.exec("INSERT INTO test_settings(singleton,value) VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value",JSON.stringify(s));}
  call(e:Effect):void{this.sql.exec("INSERT INTO test_calls(value) VALUES(?)",JSON.stringify({kind:e.kind,providerKey:e.identity.key,effectId:e.id}));}
}
class SyntheticClock implements Clock {
  constructor(private store:TestStore){}
  sample():Interval|null {
    const s=this.store.get();const c=s.clockSequence.shift()??s.clock;if(s.clockSequence.length||c!==s.clock)this.store.set(s);
    if(!c.qualified)return null;return {lowerUs:BigInt(c.nowUs)-BigInt(c.errorUs),upperUs:BigInt(c.nowUs)+BigInt(c.errorUs),qualificationId:"synthetic-verification-only"};
  }
}
class FixtureHooks implements Hooks {
  barrierResolve:(()=>void)|null=null;
  constructor(private store:TestStore){}
  async point(point:string):Promise<void>{
    const s=this.store.get();if(s.fault?.point!==point)return;
    const {behavior}=s.fault;s.fault=null;
    if(behavior==="barrier"){s.barrier=true;this.store.set(s);await new Promise<void>(resolve=>{this.barrierResolve=resolve;});return;}
    this.store.set(s);const error=new Error("injected_fault");error.name="InjectedFault";throw error;
  }
}
class FixtureProvider implements Provider {
  readonly available=true;private resolveHold:(()=>void)|null=null;
  constructor(private store:TestStore){}
  kind(platform:"ios"|"android"):"cloudflare-linux"|"external-macos"{return platform==="ios"?"external-macos":"cloudflare-linux";}
  observe(e:Effect):ProviderObservation {
    const partial=this.store.get().observation;
    return {identity:e.identity,state:"inert",instanceId:"instance-1",bootId:"boot-1",definitive:false,descendantsGone:false,launchesSettled:false,diagnosticSha256:"d".repeat(64),...partial};
  }
  async inspect(e:Effect):Promise<ProviderObservation>{this.store.call(e);return this.observe(e);}
  async launchInert(e:Effect,signal:AbortSignal):Promise<ProviderObservation>{
    this.store.call(e);
    if(this.store.get().holdProvider)await new Promise<void>((resolve,reject)=>{
      this.resolveHold=resolve; // Independent fixture: deliberately ignores AbortSignal.
    });
    return this.observe(e);
  }
  async stop(e:Effect):Promise<ProviderObservation>{this.store.call(e);return {...this.observe(e),state:"absent",instanceId:null,bootId:null};}
  release():void {this.resolveHold?.();this.resolveHold=null;}
}
class FixtureVerifier implements ObjectVerifier {constructor(private store:TestStore){} async verify():Promise<boolean>{return this.store.get().objectVerified;}}
export class TestOperation extends DurableObject<Env> {
  private ledger:Ledger;private engine:Engine;private store:TestStore;private hooks:FixtureHooks;private provider:FixtureProvider;
  constructor(ctx:DurableObjectState,env:Env){
    super(ctx,env);this.ledger=new Ledger(ctx.storage);this.store=new TestStore(ctx.storage.sql);this.hooks=new FixtureHooks(this.store);this.provider=new FixtureProvider(this.store);
    this.engine=new Engine(this.ledger,new SyntheticClock(this.store),this.provider,new FixtureVerifier(this.store),this.hooks);
    ctx.blockConcurrencyWhile(()=>this.engine.recover());
  }
  async fetch(request:Request):Promise<Response>{
    const path=new URL(request.url).pathname;
    if(path.startsWith("/__test/")){
      const action=path.slice(8),arg=request.method==="POST"?await request.json() as Record<string,unknown>:{};
      const row=this.ledger.read();
      try{
        switch(action){
          case "init": {const s=defaults();s.clock=arg.clock as ClockSetting;this.store.set(s);return json({ok:true});}
          case "snapshot":return json(row?{exists:true,desired:row.desired,epoch:row.epoch,revision:row.revision,owner:row.owner,expiryUs:row.expiry_us,providerKey:row.provider_key,phase:row.phase,claimState:row.claim_state,terminal:row.terminal_json?JSON.parse(row.terminal_json):null}:{exists:false});
          case "parse":try{parseJSON(Uint8Array.from(arg.bytes as number[]));return json({accepted:true});}catch{return json({accepted:false});}
          case "raw":return json({row,sqlTypes:this.ctx.storage.sql.exec("SELECT typeof(epoch) AS epoch,typeof(revision) AS revision,typeof(expiry_us) AS expiry,typeof(state_version) AS state_version FROM operation").toArray(),audit:this.ctx.storage.sql.exec("SELECT COUNT(*) AS count FROM audit").toArray(),alarm:await this.ctx.storage.getAlarm(),settings:this.store.get()});
          case "calls":return json(this.ctx.storage.sql.exec<{value:string}>("SELECT value FROM test_calls ORDER BY sequence").toArray().map(x=>JSON.parse(x.value)));
          case "clock": {const s=this.store.get();s.clock=arg as unknown as ClockSetting;this.store.set(s);return json({ok:true});}
          case "sequence": {const s=this.store.get();s.clockSequence=arg.sequence as ClockSetting[];this.store.set(s);return json({ok:true});}
          case "inject": {const s=this.store.get();s.fault=arg as unknown as Settings["fault"];this.store.set(s);return json({ok:true});}
          case "hold": {const s=this.store.get();s.holdProvider=!!arg.value;this.store.set(s);return json({ok:true});}
          case "release":this.hooks.barrierResolve?.();this.provider.release();return json({ok:true});
          case "deliver": {const s=this.store.get();s.observation=arg as Partial<ProviderObservation>;this.store.set(s);this.provider.release();return json({ok:true});}
          case "reconcile":await this.engine.reconcile();return json({ok:true});
          case "alarm":await this.engine.alarm();return json({ok:true});
          case "claim":return json(row?await this.engine.claim({identity:this.ledger.identity(row),immutableSha256:row.binding_hash,instanceId:arg.instanceId as string,bootId:arg.bootId as string}):{granted:false});
          case "rawClaim":return json(await this.engine.claim(arg as unknown as import("../src/engine.js").RunnerClaim));
          case "objects":{const s=this.store.get();s.objectVerified=!!arg.value;this.store.set(s);return json({ok:true});}
          case "report":return json({status:await this.engine.report(arg as unknown as RunnerReport)});
          case "quarantine":await this.engine.quarantine();return json({ok:true});
          case "rollback": {
            const before=this.ledger.read();try{this.ledger.transaction(r=>{if(r){r.owner="rolled-back";this.ledger.save(r,"rollback_test");}throw new Error("rollback");});}catch{}
            return json({before,after:this.ledger.read()});
          }
        }
      }catch(error){if(error instanceof Error&&error.name==="InjectedFault")return json({fault:true});return json({rejected:true});}
      return errorResponse(404);
    }
    const checked=await ingress(request,this.env);if(checked instanceof Response)return checked;
    try{
      const r=checked.r;
      return reply(r,await this.engine.command(r,{provider:this.provider.kind(r.ref.platform),key:await operationKey(r),immutableSha256:r.immutable_sha256}));
    }catch{return errorResponse(400);}
  }
  async alarm():Promise<void>{const s=this.store.get();s.alarmTicks++;this.store.set(s);await this.engine.alarm();}
}
export default {
  async fetch(request:Request,env:Env):Promise<Response>{
    // Test control is isolated in this entry, never imported by src/index.ts.
    if(!new URL(request.url).pathname.startsWith("/__test/")){
      const checked=await ingress(request,env);if(checked instanceof Response)return checked;
      request=new Request(request.url,{method:"POST",headers:request.headers,body:checked.bytes});
    }
    return env.OPERATIONS.get(env.OPERATIONS.idFromName("test-operation")).fetch(request);
  }
};
