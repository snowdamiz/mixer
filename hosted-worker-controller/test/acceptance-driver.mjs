import {Miniflare,Log,LogLevel} from "miniflare";
import {createHash} from "node:crypto";
import {mkdtemp,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,resolve} from "node:path";
import {killOwnedWorkerd} from "./owned-workerd-identity.mjs";

export const cleanupReceipts=[];
const token=Buffer.alloc(32,0x31).toString("base64url");
const digest=createHash("sha256").update(token).digest("hex");
const project=resolve(import.meta.dirname,"..");
export function options(persist,production=false){return {
  modules:true,scriptPath:join(project,"dist",production?"src/index.js":"test/worker.js"),
  modulesRules:[{type:"ESModule",include:["**/*.js"],fallthrough:true},{type:"Text",include:["**/*.sql"],fallthrough:true}],
  compatibilityDate:"2026-07-30",durableObjects:{OPERATIONS:{className:production?"MixerWorkerOperation":"TestOperation",useSQLite:true}},
  durableObjectsPersist:persist,bindings:{MIXER_PRINCIPAL:JSON.stringify({environment_id:"development",pool_id:"native",controller_id:"controller-1",platforms:["ios","android"]}),MIXER_POOL_TOKEN_SHA256:digest},
  log:new Log(LogLevel.ERROR),
};}
export async function createHarness({fixture,nowUs,errorUs,clockQualified}){
  const persist=await mkdtemp(join(tmpdir(),"mixer-controller-owned-"));
  let mf=new Miniflare(options(persist));let closed=false;
  try{await mf.ready;}catch(error){await mf.dispose().catch(()=>{});await rm(persist,{recursive:true,force:true});cleanupReceipts.push({persist,setupFailed:true,disposed:true,storageRemoved:true});throw error;}
  async function request(path,value){
    const response=await mf.dispatchFetch("https://controller.test/__test/"+path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(value??{})});
    const data=await response.json();if(data?.fault){const e=new Error("injected_fault");e.name="InjectedFault";throw e;}return data;
  }
  await request("init",{clock:{nowUs,errorUs,qualified:clockQualified}});
  let pendingClock=null;
  async function drainClock(){if(pendingClock){await pendingClock;pendingClock=null;}}
  async function rawCommand(bytes,{credential="valid",headers={}}={}){
    await drainClock();const response=await mf.dispatchFetch("https://controller.test/internal/mixer-build-worker/v1",{
      method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+(credential==="valid"?token:Buffer.alloc(32,0x32).toString("base64url")),...headers},body:bytes});
    return {httpStatus:response.status,body:await response.json(),headers:Object.fromEntries(response.headers)};
  }
  const h={
    command:(r,opts)=>rawCommand(new TextEncoder().encode(JSON.stringify(r)),opts),rawCommand,
    snapshot:()=>request("snapshot"),raw:()=>request("raw"),
    _calls:[],calls(){return this._calls;},
    setClock(c){pendingClock=request("clock",c);},
    async restart(){await drainClock();await mf.dispose();mf=new Miniflare(options(persist));await mf.ready;this._calls=await request("calls");},
    async close(){if(closed)return;closed=true;await drainClock();await mf.dispose();await rm(persist,{recursive:true,force:true});cleanupReceipts.push({persist,disposed:true,storageRemoved:true});},
    async inject(point,behavior){await request("inject",{point,behavior});},
    reconcile:()=>request("reconcile"),claim:c=>request("claim",c),
    deliverProvider:v=>request("deliver",v),fireAlarm:()=>request("alarm"),
    control:request,fixture,persist,
    async hardRestart(){
      // Kill only a direct child of this harness Node process whose executable
      // is our exact installed workerd binary. Never target by broad name.
      const workerd=(await import("workerd")).default.default;
      const identity=killOwnedWorkerd(workerd);
      cleanupReceipts.push({ownedPid:identity.pid,...identity});
      try{await mf.dispose();}catch{}mf=new Miniflare(options(persist));await mf.ready;this._calls=await request("calls");
    }
  };
  // Provider history is independently read from SQLite after each mutation.
  for(const name of ["command","rawCommand","reconcile","claim","deliverProvider","fireAlarm","control"]){
    const method=h[name].bind(h);h[name]=async(...args)=>{await drainClock();try{return await method(...args);}finally{h._calls=await request("calls");}};
  }
  // Frozen runner calls inject synchronously; preserve FIFO control delivery
  // before the next command without giving production an injection override.
  const inject=h.inject.bind(h);h.inject=(point,behavior)=>{pendingClock=inject(point,behavior);return pendingClock;};
  return h;
}
