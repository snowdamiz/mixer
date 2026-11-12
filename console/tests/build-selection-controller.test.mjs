import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";
import { compileBuildSelectionTests, isBrowserTestChild, runBrowserTests } from "./helpers/build-selection-compiled.mjs";
const browserChild = isBrowserTestChild(import.meta.url);
const output = browserChild ? process.env.MIXER_BUILD_CATALOG_COMPILED : compileBuildSelectionTests();
if (!browserChild) {
  test("BROWSER_WRAPPER: build-selection-controller", { timeout: 75000 }, async () => {
    await runBrowserTests(import.meta.url, output);
  });
} else {
const load = path => import(pathToFileURL(join(output, path)));
const { createBuildSelectionController } = await load("state/build-selection-controller.js");
const { createBrowserSessionController } = await load("state/browser-session-controller.js");
const { parseBuildPage } = await load("domain/build-catalog.js");
const { parseBuildRead } = await load("domain/build-read.js");
const { WorkspaceClientError } = await load("api/workspace-client.js");
const flush = () => new Promise(resolve => setImmediate(resolve));
const pending = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return {promise,resolve,reject}; };
const scope = {organizationId:"org",projectId:"p"};
const dto = (change={}) => ({...scope,applicationId:"app",buildId:"b",platform:"ios",sourceSha256:"a".repeat(64),toolchainLockSha256:"b".repeat(64),buildDefinitionSha256:"c".repeat(64),revision:2,state:"queued",attempt:1,maxAttempts:3,failureCode:null,workerCompletionPending:false,...change});
const apps = (ids=["app","empty"],nextCursor=null) => ({...scope,applications:ids.map(applicationId=>({applicationId})),nextCursor});
const builds = (rows=[dto()],applicationId="app",nextCursor=null) => parseBuildPage({...scope,applicationId,builds:rows,nextCursor},{...scope,applicationId});
const workspace = (projectId="p") => ({organizations:{kind:"ready",input:{organizations:[{id:"org",display_name:null,organization_roles:["owner"]}],next_cursor:null}},projects:{kind:"ready",organizationId:"org",input:{projects:[{organization_id:"org",id:projectId,display_name:null,roles:["viewer"]}],next_cursor:null}},selectedOrganizationId:"org",selectedProjectId:projectId});
const selection = row => { const {revision,state,attempt,maxAttempts,failureCode,workerCompletionPending,...value}=row;return value; };
function fixture() {
 const calls=[];const push=(kind,args,signal)=>{const d=pending();calls.push({kind,args,signal,...d});return d.promise;};
 const session={kind:"ready",client:{},buildClients:{catalog:{applications:(s,p,signal)=>push("applications",{s,p},signal),builds:(s,p,signal)=>push("builds",{s,p},signal)},read:{read:(s,signal)=>push("read",s,signal)}}};
 const controller=createBuildSelectionController();controller.setSession(session);controller.setWorkspace(workspace());
 return {controller,session,calls};
}
async function listed(f) {f.calls.at(-1).resolve(apps());await flush();f.controller.selectApplication("app");f.calls.at(-1).resolve(builds());await flush();}
async function detailed(f,row=dto()) {await listed(f);f.controller.selectBuild({buildId:"b",platform:"ios"});f.calls.at(-1).resolve(parseBuildRead({build:row},selection(row)));await flush();}
const json=value=>new Response(JSON.stringify(value),{headers:{"content-type":"application/json","cache-control":"no-store"}});

test("only matching ready workspace pages admit a project; caller IDs cannot fabricate selection",async()=>{
 const f=fixture();try {
 assert.equal(f.calls.length,1);f.calls[0].resolve(apps());await flush();
 f.controller.selectApplication("forged");f.controller.selectBuild({buildId:"forged",platform:"ios"});assert.equal(f.calls.length,1);
 for(const change of [{projects:{kind:"loading",organizationId:"org"}},{selectedOrganizationId:"other"},{selectedProjectId:"forged"},{organizations:{kind:"ready",input:{organizations:[],next_cursor:null}}}]){
  f.controller.setWorkspace({...workspace(),...change});assert.equal(f.controller.getState().applications.kind,"unselected");
 }
 assert.equal(f.calls.length,1);
 }finally{f.controller.dispose();}
});
test("two applications including one empty lead only stored selection into independently checked queued and failed details",async()=>{
 const f=fixture();try {
 await detailed(f);const state=f.controller.getState();assert.equal(state.detail.kind,"ready");assert.equal(state.detail.snapshot.report.state,"queued");assert.deepEqual(f.calls.at(-1).args,selection(dto()));
 for(const value of [state,state.applications.page,state.applications.page.applications,state.builds.page,state.builds.page.builds,state.detail,state.detail.selection,state.detail.snapshot,state.detail.snapshot.report])assert(Object.isFrozen(value));
 f.controller.refreshSelected();f.calls.at(-1).resolve(parseBuildRead({build:dto({revision:3,state:"failed",failureCode:"compiler_error"})},selection(dto())));await flush();assert.equal(f.controller.getState().detail.snapshot.report.state,"failed");
 f.controller.selectApplication("empty");assert.equal(f.controller.getState().detail.kind,"unselected");f.calls.at(-1).resolve(builds([],"empty"));await flush();assert.equal(f.controller.getState().builds.kind,"empty");
 }finally{f.controller.dispose();}
});
test("applications and build cursors derive from validated current page and clear child selections",async()=>{
 const f=fixture();try {
 f.calls[0].resolve(apps(undefined,"TkVYVA"));await flush();f.controller.selectApplication("app");f.calls.at(-1).resolve(builds(undefined,"app","QlVJTEQ"));await flush();
 f.controller.selectBuild({buildId:"b",platform:"ios"});const old=f.calls.at(-1);f.controller.nextBuilds();assert(old.signal.aborted);assert.equal(f.controller.getState().detail.kind,"unselected");assert.equal(f.calls.at(-1).args.p.cursor,"QlVJTEQ");
 f.calls.at(-1).resolve(builds([]));await flush();f.controller.firstBuilds();assert.deepEqual(f.calls.at(-1).args.p,{});
 f.controller.nextApplications();assert.equal(f.calls.at(-1).args.p.cursor,"TkVYVA");assert.equal(f.controller.getState().selectedApplicationId,undefined);assert.equal(f.controller.getState().builds.kind,"unselected");
 f.calls.at(-1).resolve(apps([]));await flush();assert.equal(f.controller.getState().applications.kind,"empty");f.controller.firstApplications();assert.deepEqual(f.calls.at(-1).args.p,{});
 old.resolve(parseBuildRead({build:dto()},selection(dto())));await flush();assert.equal(f.controller.getState().detail.kind,"unselected");
 }finally{f.controller.dispose();}
});
test("all eight detail identity mismatches and same-selection revision rollback fail closed",async()=>{
 for(const [key,value]of Object.entries({...selection(dto()),revision:0})){
  const f=fixture();try{await listed(f);f.controller.selectBuild({buildId:"b",platform:"ios"});const wrong=dto({[key]:key==="revision"?0:key==="platform"?"android":key.endsWith("Sha256")?"d".repeat(64):"wrong"});
  const snapshot=parseBuildRead({build:wrong},selection(wrong));f.calls.at(-1).resolve(snapshot);await flush();assert.deepEqual(f.controller.getState().detail,{kind:"error",reason:"invalid_response"},key);
  }finally{f.controller.dispose();}
 }
 const f=fixture();try{await detailed(f,dto({revision:4}));f.controller.selectBuild({buildId:"b",platform:"ios"});f.calls.at(-1).resolve(parseBuildRead({build:dto({revision:3})},selection(dto())));await flush();assert.equal(f.controller.getState().detail.reason,"invalid_response");}finally{f.controller.dispose();}
});
test("401,403,404,503 clear applications, build rows and detail, without stale good data",async()=>{
 for(const code of ["unauthenticated","permission_denied","not_found","unavailable"]){const f=fixture();try{await detailed(f);f.controller.refreshSelected();f.calls.at(-1).reject(new WorkspaceClientError(code));await flush();const s=f.controller.getState();assert.notEqual(s.applications.kind,"ready");assert.equal(s.builds.kind,"unselected");assert.equal(s.detail.kind,"unselected");assert.equal(s.selectedApplicationId,undefined);}finally{f.controller.dispose();}}
});
test("late project, application, client and session responses cannot publish",async()=>{
 for(const change of [f=>f.controller.setWorkspace(workspace("other")),f=>f.controller.selectApplication("empty"),f=>f.controller.setSession({...f.session,buildClients:{...f.session.buildClients,read:{read:()=>Promise.reject(Error())}}}),f=>f.controller.setSession({kind:"unavailable"})]){
 const f=fixture();try{await listed(f);f.controller.selectBuild({buildId:"b",platform:"ios"});const old=f.calls.at(-1);change(f);assert(old.signal.aborted);old.resolve(parseBuildRead({build:dto()},selection(dto())));await flush();assert.notEqual(f.controller.getState().detail.kind,"ready");}finally{f.controller.dispose();}}
});
test("abort reentry and listener disposal install new ownership before callbacks and prevent dispatch",async()=>{
 const f=fixture();try{await listed(f);f.controller.selectBuild({buildId:"b",platform:"ios"});const old=f.calls.at(-1);old.signal.addEventListener("abort",()=>{assert.equal(f.controller.getState().detail.kind,"unselected");f.controller.dispose();});const count=f.calls.length;f.controller.selectApplication("empty");assert.equal(f.calls.length,count);old.resolve(parseBuildRead({build:dto()},selection(dto())));await flush();assert.equal(f.controller.getState().applications.kind,"unavailable");}finally{f.controller.dispose();}
 const g=fixture();g.controller.subscribe(()=>{throw Error("observer");});g.controller.subscribe(async()=>{throw Error("observer");});let once=true;g.controller.subscribe(s=>{if(once&&s.applications.kind==="ready"){once=false;g.controller.dispose();}});g.calls[0].resolve(apps());await flush();assert.equal(g.controller.getState().applications.kind,"unavailable");
});
test("same project on a new workspace page clears prior details; malformed internal rows cannot become selectable",async()=>{
 const f=fixture();try{await detailed(f);f.controller.setWorkspace(workspace());assert.equal(f.controller.getState().detail.kind,"unselected");f.calls.at(-1).resolve(apps());await flush();f.controller.selectApplication("app");const bad=builds();const row=bad.builds[0];f.calls.at(-1).resolve({...bad,builds:[{selection:{...row.selection,sourceSha256:"d".repeat(64)},snapshot:row.snapshot}]});await flush();assert.equal(f.controller.getState().builds.reason,"invalid_response");}finally{f.controller.dispose();}
});

// Consume exact sequential dispatch records; an async headers step cannot resolve an older call.
function observedFetch() {
 const calls=[],notifications=new Map();let nextIndex=0;
 return {calls,fetch:(path,init)=>{const d=pending(),call={path,init,...d};const index=calls.length;calls.push(call);notifications.get(index)?.resolve(call);return d.promise;},
 async next(path,method="GET") {const index=nextIndex++;let call=calls[index];if(!call){const notice=pending();notifications.set(index,notice);call=await notice.promise;notifications.delete(index);}assert.equal(call.path,path);assert.equal(call.init.method,method);return call;}};
}
const applicationsPath="/console-api/v1/applications?organization_id=org&project_id=p";
const catalogPath="/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=app";
const detailPath="/console-api/v1/builds?organization_id=org&project_id=p&application_id=app&build_id=b&platform=ios&source_sha256="+"a".repeat(64)+"&toolchain_lock_sha256="+"b".repeat(64)+"&build_definition_sha256="+"c".repeat(64);
test("actual metadata owner yields one frozen bundle whose catalog/read share workspace epoch, 401 and revalidation",async()=>{
 const network=observedFetch(),calls=network.calls;const owner=createBrowserSessionController({fetch:network.fetch});
 try{
 owner.revalidate();(await network.next("/auth/session")).resolve(json({state:"authenticated",generation:"B".repeat(42)+"A",csrf_token:"A".repeat(43),expires_at:Math.floor(Date.now()/1000)+60}));await flush();const s=owner.getSession();assert.equal(s.kind,"ready");assert(Object.isFrozen(s.buildClients));assert(Object.isFrozen(s.buildClients.catalog));assert(Object.isFrozen(s.buildClients.read));
 const a=s.buildClients.catalog.applications(scope,{});(await network.next(applicationsPath)).resolve(json(apps()));assert.deepEqual(await a,apps());const b=s.buildClients.catalog.builds({...scope,applicationId:"app"},{});(await network.next(catalogPath)).resolve(json({...scope,applicationId:"app",builds:[dto()],nextCursor:null}));const page=await b;const d=s.buildClients.read.read(page.builds[0].selection);(await network.next(detailPath)).resolve(json({build:dto()}));assert.equal((await d).revision,2);
 const read=s.buildClients.read.read(selection(dto())), workspaceCall=s.client.organizations();const rejected=assert.rejects(workspaceCall,e=>e.code==="aborted");const readCall=await network.next(detailPath);await network.next("/console-api/v1/orgs");readCall.resolve(new Response(null,{status:401}));await assert.rejects(read,e=>e.code==="unauthenticated");await rejected;assert.equal(owner.getSession().kind,"unavailable");await assert.rejects(s.buildClients.catalog.applications(scope,{}),e=>e.code==="aborted");
 assert.equal(calls.filter(c=>c.path==="/auth/session").length,1);
 }finally{owner.dispose();}
});
test("new catalog and read delegates enforce synchronous and postawait expiry and backwards clocks",async()=>{
 const date=Date.now,desc=Object.getOwnPropertyDescriptor(globalThis,"performance");let wall=1700000000000,mono=100;Date.now=()=>wall;Object.defineProperty(globalThis,"performance",{configurable:true,value:{now:()=>mono}});
 try{for(const method of ["catalog","read"])for(const change of [()=>wall+=60000,()=>mono+=60000,()=>wall--,()=>mono--])for(const post of [false,true]){
 wall=1700000000000;mono=100;const network=observedFetch(),calls=network.calls;const owner=createBrowserSessionController({fetch:network.fetch});try{owner.revalidate();(await network.next("/auth/session")).resolve(json({state:"authenticated",generation:"B".repeat(42)+"A",csrf_token:"A".repeat(43),expires_at:1700000060}));await flush();const s=owner.getSession();const dispatch=()=>method==="catalog"?s.buildClients.catalog.applications(scope,{}):s.buildClients.read.read(selection(dto()));let operation,dispatched;if(post){operation=dispatch();dispatched=await network.next(method==="catalog"?applicationsPath:detailPath);}change();if(!post)operation=dispatch();else dispatched.resolve(json(method==="catalog"?apps():{build:dto()}));await assert.rejects(operation,e=>e.code==="aborted");assert.equal(owner.getSession().kind,"unavailable");}finally{owner.dispose();}}
 }finally{Date.now=date;Object.defineProperty(globalThis,"performance",desc);}
});

// R1208: retain the accepted floor only while the admitted detail selection survives.
test("retained request_failed detail retries preserve the accepted floor",async()=>{
 const f=fixture();try{
  await detailed(f,dto({revision:4}));const accepted=f.controller.getState();
  f.controller.refreshSelected();f.calls.at(-1).reject(Error("request failed"));await flush();
  assert.deepEqual(f.controller.getState().detail,{kind:"error",reason:"request_failed"});
  assert.strictEqual(f.controller.getState().applications,accepted.applications);assert.strictEqual(f.controller.getState().builds,accepted.builds);
  const before=f.calls.length;f.controller.refreshSelected();assert.equal(f.calls.length,before+1);
  f.calls.at(-1).resolve(parseBuildRead({build:dto({revision:3})},selection(dto())));await flush();
  assert.deepEqual(f.controller.getState().detail,{kind:"error",reason:"invalid_response"});
  f.controller.selectBuild({buildId:"b",platform:"ios"});f.calls.at(-1).resolve(parseBuildRead({build:dto({revision:4})},selection(dto())));await flush();
  assert.equal(f.controller.getState().detail.snapshot.revision,4);
  f.controller.refreshSelected();f.calls.at(-1).resolve(parseBuildRead({build:dto({revision:5})},selection(dto())));await flush();assert.equal(f.controller.getState().detail.snapshot.revision,5);
 }finally{f.controller.dispose();}
});

test("security and availability failures erase retained detail retry ownership",async()=>{
 for(const code of ["unauthenticated","unavailable","permission_denied","not_found"]){
  const f=fixture();try{
   await detailed(f,dto({revision:4}));f.controller.refreshSelected();f.calls.at(-1).reject(new WorkspaceClientError(code));await flush();
   const count=f.calls.length;f.controller.refreshSelected();f.controller.selectBuild({buildId:"b",platform:"ios"});assert.equal(f.calls.length,count,code);
   const state=f.controller.getState();assert.equal(state.builds.kind,"unselected");assert.equal(state.detail.kind,"unselected");assert.equal(state.selectedApplicationId,undefined);
  }finally{f.controller.dispose();}
 }
});

test("catalog failures never retain detail ownership",async()=>{
 for(const stage of ["applications","builds"])for(const error of [Error("request failed"),new TypeError("invalid response")]){
  const f=fixture();try{
   if(stage==="builds"){f.calls[0].resolve(apps());await flush();f.controller.selectApplication("app");}
   f.calls.at(-1).reject(error);await flush();const count=f.calls.length;f.controller.refreshSelected();assert.equal(f.calls.length,count);
   assert.deepEqual(f.controller.getState()[stage],{kind:"error",reason:error instanceof TypeError?"invalid_response":"request_failed"});assert.equal(f.controller.getState().detail.kind,"unselected");
  }finally{f.controller.dispose();}
 }
});

test("explicit workspace session application and page resets admit a new revision floor",async()=>{
 for(const reset of ["workspace","session","application","build-page","application-page"]){
  const f=fixture();try{
   f.calls[0].resolve(apps(undefined,"TkVYVA"));await flush();f.controller.selectApplication("app");f.calls.at(-1).resolve(builds(undefined,"app","QlVJTEQ"));await flush();
   f.controller.selectBuild({buildId:"b",platform:"ios"});f.calls.at(-1).resolve(parseBuildRead({build:dto({revision:4})},selection(dto())));await flush();
   f.controller.refreshSelected();f.calls.at(-1).reject(new TypeError());await flush();
   if(reset==="workspace")f.controller.setWorkspace(workspace());
   if(reset==="session"){f.controller.setSession({...f.session});f.controller.setWorkspace(workspace());}
   if(reset==="application"){f.controller.selectApplication("empty");f.calls.at(-1).resolve(builds([],"empty"));await flush();f.controller.selectApplication("app");}
   if(reset==="build-page")f.controller.nextBuilds();
   if(reset==="application-page")f.controller.nextApplications();
   assert.equal(f.controller.getState().detail.kind,"unselected",reset);
   const count=f.calls.length;f.controller.refreshSelected();assert.equal(f.calls.length,count,reset);
   if(["workspace","session","application-page"].includes(reset)){f.calls.at(-1).resolve(apps());await flush();f.controller.selectApplication("app");}
   f.calls.at(-1).resolve(builds());await flush();f.controller.selectBuild({buildId:"b",platform:"ios"});f.calls.at(-1).resolve(parseBuildRead({build:dto({revision:3})},selection(dto())));await flush();assert.equal(f.controller.getState().detail.snapshot.revision,3,reset);
  }finally{f.controller.dispose();}
 }
 const f=fixture();await detailed(f,dto({revision:4}));f.controller.refreshSelected();f.calls.at(-1).reject(Error());await flush();f.controller.dispose();const count=f.calls.length;f.controller.refreshSelected();f.controller.selectBuild({buildId:"b",platform:"ios"});assert.equal(f.calls.length,count);assert.equal(f.controller.getState().detail.kind,"unselected");
});

{
 const {createRoot,createSignal}=await import("solid-js");
 const {createBuildSelectionBinding}=await load("state/build-selection-binding.js");
 async function actualOwnerFixture(){
  const net=observedFetch(),owner=createBrowserSessionController({fetch:net.fetch});
  owner.revalidate();(await net.next("/auth/session")).resolve(json({state:"authenticated",generation:"B".repeat(42)+"A",csrf_token:"A".repeat(43),expires_at:Math.floor(Date.now()/1000)+60}));await flush();
  const session=owner.getSession();assert.equal(session.kind,"ready");assert(Object.isFrozen(session));assert(Object.isFrozen(session.buildClients));
  let binding,dispose,unsubscribe,setDirectory;
  createRoot(stop=>{dispose=stop;const [current,setCurrent]=createSignal(session),[directory,setCurrentDirectory]=createSignal(workspace());setDirectory=setCurrentDirectory;unsubscribe=owner.subscribe(value=>setCurrent(value));binding=createBuildSelectionBinding(current,directory);});
  async function respond(path,response){const call=await net.next(path);call.resolve(response);await flush();return call;}
  async function list(){await respond(applicationsPath,json(apps()));binding.controller.selectApplication("app");await respond(catalogPath,json({...scope,applicationId:"app",builds:[dto()],nextCursor:null}));}
  async function detail(revision){binding.controller.selectBuild({buildId:"b",platform:"ios"});return respond(detailPath,json({build:dto({revision})}));}
  return {net,owner,session,binding,setDirectory,respond,list,detail,close:()=>{unsubscribe();dispose();owner.dispose();}};
 }
 test("actual Solid owner catalog and transport preserve revision floor after invalid detail",async()=>{
  const f=await actualOwnerFixture();try{
   await f.list();const acceptedCall=await f.detail(4);const accepted=f.binding.state();assert.equal(accepted.detail.snapshot.revision,4);
   const row=accepted.builds.page.builds[0];assert.equal(row.snapshot.revision,2);assert(Object.isFrozen(row.selection));assert.deepEqual(accepted.detail.selection,row.selection);
   f.binding.controller.refreshSelected();const failedCall=await f.respond(detailPath,json({build:{...dto(),revision:"invalid"}}));
   const afterError=f.binding.state();assert.deepEqual(afterError.detail,{kind:"error",reason:"invalid_response"});assert.strictEqual(afterError.applications,accepted.applications);assert.strictEqual(afterError.builds,accepted.builds);assert.strictEqual(afterError.builds.page.builds[0],row);assert.strictEqual(f.owner.getSession(),f.session);assert.equal(afterError.selectedApplicationId,"app");
   const callsBeforeRefresh=f.net.calls.length;f.binding.controller.refreshSelected();const refreshedCall=await f.respond(detailPath,json({build:dto({revision:3})}));assert.equal(f.net.calls.length,callsBeforeRefresh+1);assert.deepEqual(f.binding.state().detail,{kind:"error",reason:"invalid_response"});
   const olderCall=await f.detail(3);const afterOlder=f.binding.state();assert.strictEqual(afterOlder.applications,accepted.applications);assert.strictEqual(afterOlder.builds,accepted.builds);assert.strictEqual(f.owner.getSession(),f.session);
   assert.notEqual(afterOlder.detail.kind,'ready','P2: same admitted immutable selection regressed from accepted revision 4 to revision 3 after invalid_response; fail() erased revision floor while retaining current catalog and session');
   assert.deepEqual(afterOlder.detail,{kind:"error",reason:"invalid_response"});
   await f.detail(4);assert.equal(f.binding.state().detail.snapshot.revision,4);await f.detail(5);assert.equal(f.binding.state().detail.snapshot.revision,5);
   assert.equal(f.net.calls.filter(call=>call.path==="/auth/session").length,1);assert.equal(f.net.calls.filter(call=>call.path===applicationsPath).length,1);assert.equal(f.net.calls.filter(call=>call.path===catalogPath).length,1);
   for(const call of [failedCall,refreshedCall,olderCall])assert.equal(call.path,acceptedCall.path);
   assert.strictEqual(f.binding.state().applications,accepted.applications);assert.strictEqual(f.binding.state().builds,accepted.builds);
  }finally{f.close();}
 });
 test("actual HTTP500 clears retry ownership and explicit workspace reset permits revision3",async()=>{
  const f=await actualOwnerFixture();try{
   await f.list();await f.detail(4);f.binding.controller.refreshSelected();await f.respond(detailPath,new Response(null,{status:500}));
   assert.deepEqual(f.binding.state(),{applications:{kind:"unavailable"},builds:{kind:"unselected"},detail:{kind:"unselected"}});assert.strictEqual(f.owner.getSession(),f.session);
   const count=f.net.calls.length;f.binding.controller.selectBuild({buildId:"b",platform:"ios"});f.binding.controller.refreshSelected();await flush();assert.equal(f.net.calls.length,count);
   f.setDirectory(workspace());await flush();await f.list();await f.detail(3);assert.equal(f.binding.state().detail.snapshot.revision,3);
  }finally{f.close();}
 });
}
}
