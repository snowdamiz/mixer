import assert from "node:assert/strict";
import { after, test } from "node:test";
import { build } from "vite";
import solid from "vite-plugin-solid";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// A deliberately small inert DOM substrate for actual Solid DOM code and events.
// It provides no layout, browser, authentication, or visual qualification.
class TestNode {
  constructor(type, name = "", data = "") { this.nodeType=type; this.nodeName=name; this.data=data; this.childNodes=[]; this.parentNode=null; this.attributes=new Map(); this.listeners=new Map(); this.style={setProperty(){},removeProperty(){}}; this.classList={toggle:(name,on)=>{const set=new Set(this.className.split(/\s+/).filter(Boolean));on?set.add(name):set.delete(name);this.className=[...set].join(" ");}}; }
  get ownerDocument(){return document;}
  get firstChild(){return this.childNodes[0]??null;}
  get lastChild(){return this.childNodes.at(-1)??null;}
  get nextSibling(){return this.parentNode?.childNodes[this.parentNode.childNodes.indexOf(this)+1]??null;}
  get previousSibling(){return this.parentNode?.childNodes[this.parentNode.childNodes.indexOf(this)-1]??null;}
  get textContent(){return this.nodeType===3?this.data:this.nodeType===8?"":this.childNodes.map(x=>x.textContent).join("");}
  set textContent(value){for(const x of this.childNodes)x.parentNode=null;this.childNodes=[];if(value!=="")this.appendChild(new TestNode(3,"#text",String(value)));}
  get nodeValue(){return this.data;} set nodeValue(value){this.data=String(value);}
  get className(){return this.getAttribute("class")??"";} set className(v){this.setAttribute("class",v);}
  get href(){return new URL(this.getAttribute("href")??"",document.baseURI).href;}
  get target(){return this.getAttribute("target")??"";}
  get namespaceURI(){return "http://www.w3.org/1999/xhtml";}
  appendChild(node){return this.insertBefore(node,null);}
  insertBefore(node,before){if(node.nodeType===11){for(const child of [...node.childNodes])this.insertBefore(child,before);return node;}if(node===before)return node;node.remove();const index=before===null?this.childNodes.length:this.childNodes.indexOf(before);assert(index>=0);this.childNodes.splice(index,0,node);node.parentNode=this;return node;}
  removeChild(node){const index=this.childNodes.indexOf(node);assert(index>=0);this.childNodes.splice(index,1);node.parentNode=null;return node;}
  replaceChild(next,old){this.insertBefore(next,old);this.removeChild(old);return old;}
  remove(){this.parentNode?.removeChild(this);}
  contains(node){for(let current=node;current;current=current.parentNode)if(current===this)return true;return false;}
  setAttribute(name,value){this.attributes.set(name,String(value));}
  getAttribute(name){return this.attributes.get(name)??null;}
  hasAttribute(name){return this.attributes.has(name);}
  removeAttribute(name){this.attributes.delete(name);}
  setAttributeNS(ns,name,value){this.setAttribute(name,value);} removeAttributeNS(ns,name){this.removeAttribute(name);}
  addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
  removeEventListener(name,fn){this.listeners.get(name)?.delete(fn);}
  cloneNode(deep){const node=new TestNode(this.nodeType,this.nodeName,this.data);node.attributes=new Map(this.attributes);if(deep)for(const child of this.childNodes)node.appendChild(child.cloneNode(true));return node;}
  set innerHTML(html){const target=this.nodeName==="TEMPLATE"?(this.content=new TestNode(11,"#fragment")):this;target.textContent="";const stack=[target];for(const token of html.match(/<!--[\s\S]*?-->|<[^>]+>|[^<]+/g)??[]){if(token.startsWith("<!")){stack.at(-1).appendChild(new TestNode(8,"#comment",token.slice(4,-3)));}else if(token.startsWith("</")){stack.pop();}else if(token.startsWith("<")){const name=token.match(/^<([\w-]+)/)[1];const node=new TestNode(1,name.toUpperCase());for(const match of token.slice(name.length+1,-1).matchAll(/([\w:-]+)(?:="([^"]*)"|='([^']*)'|=([^\s>]+))?/g))node.setAttribute(match[1],decode(match[2]??match[3]??match[4]??""));stack.at(-1).appendChild(node);if(!/^(img|br|hr|input|meta|link|area|source|wbr)$/i.test(name)&&!token.endsWith("/>"))stack.push(node);}else stack.at(-1).appendChild(new TestNode(3,"#text",decode(token)));}}
  click(){if(this.disabled)return;const nodes=[];for(let n=this;n;n=n.parentNode)nodes.push(n);if(!nodes.includes(document))nodes.push(document);nodes.push(window);const event={type:"click",button:0,target:this,currentTarget:document,defaultPrevented:false,cancelBubble:false,preventDefault(){this.defaultPrevented=true;},stopPropagation(){this.cancelBubble=true;},composedPath:()=>nodes};for(const node of nodes)for(const fn of [...(node.listeners?.get("click")??[])])fn(event);}
}
const decode=s=>s.replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&#39;/g,"'");
const root=fileURLToPath(new URL("../",import.meta.url));
await mkdir(join(root,"node_modules/.cache"),{recursive:true});
const output=await mkdtemp(join(root,"node_modules/.cache/application-build-ui-"));
after(()=>rm(output,{recursive:true,force:true}));
await build({root,configFile:false,logLevel:"error",plugins:[solid()],resolve:{conditions:["browser"]},build:{target:"es2022",minify:false,lib:{entry:join(root,"src/build-submission-test-runtime.tsx"),formats:["es"],fileName:"application-ui"},outDir:output,emptyOutDir:false}});
const document=new TestNode(9,"#document");document.baseURI="https://console.example/";document.createElement=name=>new TestNode(1,name.toUpperCase());document.createElementNS=(_,name)=>document.createElement(name);document.createTextNode=text=>new TestNode(3,"#text",String(text));document.createComment=text=>new TestNode(8,"#comment",text);document.importNode=(node,deep)=>node.cloneNode(deep);document.getElementById=id=>walk(document).find(n=>n.getAttribute("id")===id)??null;
const window=new TestNode(0,"window");window.document=document;window.location=new URL(document.baseURI);window.scrollTo=()=>{};window.history={state:{_depth:0},length:1,replaceState(state){this.state=state;}};
const originals=new Map(["document","window","Node"].map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]));
Object.assign(globalThis,{document,window,Node:TestNode});
after(()=>{for(const [key,descriptor]of originals)descriptor?Object.defineProperty(globalThis,key,descriptor):delete globalThis[key];});
const {mount}=await import(pathToFileURL(join(output,"application-ui.js")));
function walk(node){return [node,...node.childNodes.flatMap(walk)];}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const json=value=>new Response(JSON.stringify(value),{headers:{"content-type":"application/json","cache-control":"no-store"}});
const api=await import(pathToFileURL(join(output,"application-ui.js")));
const appScope={organizationId:"org",projectId:"p",applicationId:"app"};
const input=(change={})=>({platform:"ios",sourceInputId:"source-1",sourceSha256:"a".repeat(64),toolchainLockSha256:"b".repeat(64),buildDefinitionSha256:"c".repeat(64),...change});
const page=(inputs=[input()],scope=appScope,nextCursor=null)=>({...scope,inputs,nextCursor});
const selection=(change={})=>({organization_id:"org",project_id:"p",application_id:"app",build_id:"build-"+"d".repeat(64),platform:"ios",source_sha256:"a".repeat(64),toolchain_lock_sha256:"b".repeat(64),build_definition_sha256:"c".repeat(64),...change});
const receipt=(change={})=>({outcome:"applied",selection:selection(),state:"queued",revision:1,...change});
const dto=(change={})=>({...appScope,buildId:"build-"+"d".repeat(64),platform:"ios",sourceSha256:"a".repeat(64),toolchainLockSha256:"b".repeat(64),buildDefinitionSha256:"c".repeat(64),revision:1,state:"queued",attempt:1,maxAttempts:3,failureCode:null,workerCompletionPending:false,...change});
const catalog=(builds=[])=>({...appScope,builds,nextCursor:null});
const response=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{"content-type":"application/json","cache-control":"no-store"}});
const inputPath="/console-api/v1/build-inputs?organization_id=org&project_id=p&application_id=app";
const catalogPath="/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=app";
const csrf="B".repeat(42)+"A";
function fixture(){
 const calls=[];const fetch=(path,options)=>new Promise((resolve,reject)=>calls.push({path:String(path),...options,resolve,reject,used:false}));
 const container=document.createElement("div");document.appendChild(container);const app=mount(container,fetch);
 return {...app,container,calls,text:()=>container.textContent,
 async request(path,method="GET") {for(let i=0;i<100;i++){const call=calls.find(c=>!c.used&&c.path===path&&c.method===method);if(call){call.used=true;assert.equal(call.credentials,"same-origin");assert.equal(call.redirect,"error");assert.equal(call.cache,"no-store");return call;}await new Promise(r=>setTimeout(r,2));}assert.fail("missing request "+method+" "+path+"; "+calls.map(c=>c.method+" "+c.path));},
 button(text){const node=walk(container).find(n=>n.nodeName==="BUTTON"&&n.textContent===text)??walk(container).find(n=>n.nodeName==="BUTTON"&&n.textContent.includes(text));assert(node,"missing button "+text+": "+container.textContent);return node;},
 click(text){this.button(text).click();},
 close(){app.dispose();container.remove();}};
}
async function navigate(f,rows=[]){
 (await f.request("/auth/session")).resolve(response({state:"authenticated",generation:"A".repeat(43),csrf_token:csrf,expires_at:Math.floor(Date.now()/1000)+60}));
 (await f.request("/console-api/v1/orgs")).resolve(response({organizations:[{id:"org",display_name:"Studio",organization_roles:["owner"]}],next_cursor:null}));await flush();
 f.click("Studio");(await f.request("/console-api/v1/projects?organization_id=org")).resolve(response({projects:[{organization_id:"org",id:"p",display_name:"Project",roles:["administrator"]}],next_cursor:null}));await flush();f.click("Project");
 walk(f.container).find(n=>n.nodeName==="A"&&n.textContent.includes("View builds")).click();
 (await f.request("/console-api/v1/applications?organization_id=org&project_id=p")).resolve(response({...appScope,applications:[{applicationId:"app"},{applicationId:"other"}],nextCursor:null,applicationId:undefined}));await flush();
 f.click("Application IDapp");(await f.request(catalogPath)).resolve(response(catalog(rows)));await flush();
}
async function listed(f,rows=[],inputs=[input()]){await navigate(f,rows);f.click("New build");(await f.request(inputPath)).resolve(response(page(inputs)));await flush();}
const inputButton="Input source-1 · Source "+"a".repeat(12);
async function start(f){f.click(inputButton);assert.equal(f.button("Create build").disabled,false);f.click("Create build");return f.request("/console-api/v1/builds","POST");}
function detailPath(s=selection()){return "/console-api/v1/builds?"+new URLSearchParams(s);}
async function committed(f,post,wire=receipt(),detail=dto()){
 post.resolve(response(wire,wire.outcome==="applied"?201:200));const read=await f.request(detailPath(wire.selection));
 const refresh=await f.request(catalogPath);refresh.resolve(response(catalog()));read.resolve(response({build:detail}));await flush();
}
function selectedText(f){return walk(f.container).find(n=>n.getAttribute("aria-label")==="Selected build").textContent;}

for(const mode of ["empty catalog","outside first catalog page"]){
 test("authenticated_console_create_selects_admitted_input_and_displays_queued_build: "+mode,async()=>{const f=fixture();try{
  await listed(f,mode==="empty catalog"?[]:Array.from({length:25},(_,i)=>dto({buildId:"a-stored-"+String(i).padStart(2,"0"),revision:0})));
  assert.equal(f.button("Create build").disabled,true);assert.doesNotMatch(f.text(),/branch|main branch/);
  assert.ok(f.text().includes("b".repeat(64)));const duplicate=f.button("Create build");const post=await start(f);duplicate.click();assert.equal(f.calls.filter(c=>c.method==="POST").length,1);
  assert.deepEqual(JSON.parse(post.body),{organization_id:"org",project_id:"p",application_id:"app",platform:"ios",source_input_id:"source-1",source_sha256:"a".repeat(64),toolchain_lock_sha256:"b".repeat(64),build_definition_sha256:"c".repeat(64)});
  assert.match(post.headers["idempotency-key"],/^[a-f0-9-]{36}$/);assert.equal(post.headers["x-mixer-csrf"],csrf);assert.equal(post.headers["content-type"],"application/json");assert.equal(post.headers.origin,undefined);
  assert.equal(f.text().includes(csrf),false);assert.equal(JSON.stringify(f.controller.getSession()).includes(csrf),false);
  await committed(f,post);assert.match(selectedText(f),/Queued/);assert.ok(selectedText(f).includes("build-"+"d".repeat(64)));assert.match(f.text(),/No builds yet/);assert.doesNotMatch(selectedText(f),/Succeeded/);
 }finally{f.close();}});
}

test("unknown network outcome and explicit retry preserve exact bytes/key; terminal duplicate shows current truth",async()=>{const f=fixture();try{await listed(f);const first=await start(f);first.reject(new Error("private network sentinel"));await flush();assert.match(f.text(),/Submission outcome unknown/);assert.doesNotMatch(f.text(),/private network sentinel/);assert.equal(f.calls.filter(c=>c.method==="POST").length,1);f.click("Retry same submission");const retry=await f.request("/console-api/v1/builds","POST");assert.equal(first.body,retry.body);assert.equal(first.headers["idempotency-key"],retry.headers["idempotency-key"]);await committed(f,retry,receipt({outcome:"duplicate",state:"failed",revision:4}),dto({state:"failed",revision:4,attempt:1,failureCode:"compiler_error"}));assert.match(selectedText(f),/Compilation failed/);assert.doesNotMatch(f.text(),/Queued/);}finally{f.close();}});

test("stopping wait is unknown and manual retry reuses captured submission; late old success cannot select",async()=>{const f=fixture();try{await listed(f);const first=await start(f);f.click("Stop waiting");assert.equal(first.signal.aborted,true);assert.match(f.text(),/Submission outcome unknown/);f.click("Retry same submission");const retry=await f.request("/console-api/v1/builds","POST");assert.equal(first.body,retry.body);assert.equal(first.headers["idempotency-key"],retry.headers["idempotency-key"]);first.resolve(response(receipt({selection:selection({build_id:"build-"+"e".repeat(64)})}),201));await flush();assert.equal(f.calls.some(c=>c.method==="GET"&&c.path.includes("build_id=")),false);await committed(f,retry);assert.match(selectedText(f),/Queued/);}finally{f.close();}});

for(const [name,change,status] of [
 ["cross organization",{selection:selection({organization_id:"other"})},201],["cross project",{selection:selection({project_id:"other"})},201],
 ["cross application",{selection:selection({application_id:"other"})},201],["platform",{selection:selection({platform:"android"})},201],
 ["source pin",{selection:selection({source_sha256:"e".repeat(64)})},201],["toolchain pin",{selection:selection({toolchain_lock_sha256:"e".repeat(64)})},201],
 ["definition pin",{selection:selection({build_definition_sha256:"e".repeat(64)})},201],["bad build ID",{selection:selection({build_id:"../secret"})},201],
 ["bad revision",{revision:-1},201],["extra field",{token:"private"},201],["wrong status outcome",{outcome:"duplicate"},201],["wrong 200",{},200],["unknown state",{state:"invented"},201],["applied running",{state:"running"},201]
])test("malformed receipt refuses selection: "+name,async()=>{const f=fixture();try{await listed(f);(await start(f)).resolve(response(receipt(change),status));await flush();assert.match(f.text(),/Submission outcome unknown/);assert.equal(f.calls.some(c=>c.method==="GET"&&c.path.includes("build_id=")),false);}finally{f.close();}});

for(const status of [400,401,403,404,409,503])test("submit refusal "+status+" has closed copy and no detail",async()=>{const f=fixture();try{await listed(f);(await start(f)).resolve(new Response("private server sentinel",{status}));await flush();assert.doesNotMatch(f.text(),/private server sentinel|Succeeded/);assert.equal(f.calls.some(c=>c.path.includes("build_id=")),false);if(status===401)assert.equal(f.controller.getSession().kind,"unavailable");else if(status===503)assert.match(f.text(),/Submission outcome unknown/);else assert.match(f.text(),/read-only|no longer available|refused/);}finally{f.close();}});

test("no admissions disable Create and read-only403 retains usable build catalog",async()=>{for(const mode of ["empty","forbidden"]){const f=fixture();try{await navigate(f,[dto({buildId:"a-stored"})]);f.click("New build");const call=await f.request(inputPath);call.resolve(mode==="empty"?response(page([])):new Response("secret",{status:403}));await flush();if(mode==="empty"){assert.match(f.text(),/No admitted source inputs/);assert.equal(f.button("Create build").disabled,true);}else assert.match(f.text(),/read-only/);assert.match(f.text(),/a-stored/);assert.equal(f.calls.some(c=>c.method==="POST"),false);}finally{f.close();}}});

test("same-generation session revalidation aborts pending submission and fences stale success",async()=>{const f=fixture();try{await listed(f,[],[input(),input({sourceInputId:"source-2",sourceSha256:"e".repeat(64)})]);const pending=await start(f);f.controller.revalidate();assert.equal(pending.signal.aborted,true);(await f.request("/auth/session")).resolve(response({state:"authenticated",generation:"A".repeat(43),csrf_token:csrf,expires_at:Math.floor(Date.now()/1000)+60}));pending.resolve(response(receipt(),201));await flush();assert.equal(f.calls.some(c=>c.path.includes("build_id=")),false);assert.doesNotMatch(f.text(),/Queued/);}finally{f.close();}});

test("application change fences pending input listing and submit even with ignored abort",async()=>{for(const phase of ["list","submit"]){const f=fixture();try{await navigate(f);f.click("New build");const listing=await f.request(inputPath);let late=listing;if(phase==="submit"){listing.resolve(response(page()));await flush();late=await start(f);}f.click("Application IDother");assert.equal(late.signal.aborted,true);late.resolve(response(phase==="list"?page():receipt(),phase==="list"?200:201));await flush();assert.doesNotMatch(f.text(),/Input source-1/);assert.equal(f.calls.some(c=>c.path.includes("build_id=")),false);}finally{f.close();}}});

test("retained client closure cannot submit after same-generation session replacement",async()=>{const calls=[];const owner=api.createBrowserSessionController({fetch:async(path,options)=>{calls.push({path,options});return response({state:"authenticated",generation:"A".repeat(43),csrf_token:csrf,expires_at:Math.floor(Date.now()/1000)+60});}});try{owner.revalidate();await flush();const old=owner.getSession();assert.equal(old.kind,"ready");owner.revalidate();await flush();assert.equal(owner.getSession().kind,"ready");assert.notEqual(old,owner.getSession());await assert.rejects(old.buildClients.create.submit(api.captureBuildAttempt(appScope,input())),{code:"aborted"});assert.equal(calls.length,2);}finally{owner.dispose();}});

test("missing private CSRF prevents session admission and any submission",async()=>{const owner=api.createBrowserSessionController({fetch:async()=>response({state:"authenticated",generation:"A".repeat(43),expires_at:Math.floor(Date.now()/1000)+60})});try{owner.revalidate();await flush();assert.equal(owner.getSession().kind,"unavailable");assert.equal("buildClients" in owner.getSession(),false);}finally{owner.dispose();}});

for(const [name,value] of [["extra source reference",page([input({source_reference:"https://bad"})])],["cross scope",page([input()],{...appScope,organizationId:"other"})],["reordered inputs",page([input({sourceInputId:"z"}),input()])],["26 rows",page(Array.from({length:26},(_,i)=>input({sourceInputId:String(i).padStart(2,"0")})))],["unknown platform",page([input({platform:"web"})])]])test("input listing fails closed: "+name,async()=>{const f=fixture();try{await navigate(f);f.click("New build");(await f.request(inputPath)).resolve(response(value));await flush();assert.match(f.text(),/Admitted inputs are unavailable/);assert.equal(f.calls.some(c=>c.method==="POST"),false);}finally{f.close();}});

test("strict JSON rejects duplicate keys and escaped duplicate keys before projection",()=>{assert.throws(()=>api.parseSubmissionJSON('{"outcome":"applied","outcome":"duplicate"}'));assert.throws(()=>api.parseSubmissionJSON('{"state":1,"st\\u0061te":2}'));});

test("created receipt revision floor and equal-revision state coherence reject detail rollback",async()=>{for(const change of [{revision:0},{state:"running"}]){const f=fixture();try{await listed(f);const post=await start(f);await committed(f,post,receipt(),dto(change));assert.doesNotMatch(selectedText(f),/1 of 1 platforms reported/);assert.match(selectedText(f),/Could not load/);}finally{f.close();}}});

test("unknown attempt input change drops old identity, warns and captures a distinct new submission",async()=>{const f=fixture();try{await listed(f,[],[input(),input({sourceInputId:"source-2",sourceSha256:"e".repeat(64)})]);const old=await start(f);f.click("Stop waiting");f.click("Input source-2 · Source "+"e".repeat(12));assert.match(f.text(),/earlier submission may have committed/);f.click("Create build");const next=await f.request("/console-api/v1/builds","POST");assert.notEqual(old.headers["idempotency-key"],next.headers["idempotency-key"]);assert.equal(JSON.parse(next.body).source_input_id,"source-2");assert.equal(JSON.parse(next.body).source_sha256,"e".repeat(64));old.resolve(response(receipt(),201));await flush();assert.equal(f.calls.some(c=>c.path.includes("build_id=")),false);}finally{f.close();}});

test("selecting an existing build aborts pending submit and fences late created selection",async()=>{const f=fixture();try{await listed(f,[dto({buildId:"a-stored"})]);const post=await start(f);const row=walk(f.container).find(n=>n.nodeName==="BUTTON"&&n.textContent.includes("a-stored"));row.click();assert.equal(post.signal.aborted,true);post.resolve(response(receipt(),201));await flush();assert.equal(f.calls.filter(c=>c.method==="GET"&&c.path.includes("build_id=")).length,1);assert.ok(f.calls.find(c=>c.path.includes("build_id=")).path.includes("build_id=a-stored"));assert.match(f.text(),/earlier submission may have committed/);}finally{f.close();}});

test("fixed25 input pagination derives only returned Android choices and clears old selection",async()=>{const f=fixture();try{await navigate(f);f.click("New build");const rows=Array.from({length:25},(_,i)=>input({platform:"android",sourceInputId:"input-"+String(i).padStart(2,"0")}));const request=await f.request(inputPath);assert.equal(request.headers["x-mixer-csrf"],undefined);assert.equal(request.body,undefined);request.resolve(response(page(rows,appScope,"bmV4dA")));await flush();const fieldsets=walk(f.container).filter(n=>n.nodeName==="LEGEND").map(n=>n.textContent);assert.deepEqual(fieldsets,["Android"]);f.click("Input input-00 · Source "+"a".repeat(12));assert.equal(f.button("Create build").disabled,false);f.click("More admitted inputs");const next=await f.request(inputPath+"&cursor=bmV4dA");next.resolve(response(page([input({sourceInputId:"last-input"})])));await flush();assert.equal(f.button("Create build").disabled,true);assert.doesNotMatch(f.text(),/input-00/);assert.equal(f.calls.some(c=>c.method==="POST"),false);}finally{f.close();}});

for(const [name,make] of [
 ["duplicate wire field",()=>new Response('{"outcome":"applied","outcome":"applied","selection":'+JSON.stringify(selection())+',"state":"queued","revision":1}',{status:201,headers:{"content-type":"application/json","cache-control":"no-store"}})],
 ["oversized body",()=>new Response("x".repeat(32769),{status:201,headers:{"content-type":"application/json","cache-control":"no-store"}})],
 ["media type",()=>new Response(JSON.stringify(receipt()),{status:201,headers:{"content-type":"text/html","cache-control":"no-store"}})],
 ["missing no-store",()=>new Response(JSON.stringify(receipt()),{status:201,headers:{"content-type":"application/json"}})],
 ["content-length overflow",()=>new Response(JSON.stringify(receipt()),{status:201,headers:{"content-type":"application/json","cache-control":"no-store","content-length":"32769"}})],
 ["invalid UTF8",()=>new Response(new Uint8Array([255]),{status:201,headers:{"content-type":"application/json","cache-control":"no-store"}})]
])test("bounded POST response fails closed to unknown: "+name,async()=>{const f=fixture();try{await listed(f);(await start(f)).resolve(make());await flush();assert.match(f.text(),/Submission outcome unknown/);assert.equal(f.calls.some(c=>c.path.includes("build_id=")),false);}finally{f.close();}});

test("creation deadline bounds an uncooperative fetch and manual retry retains key/body",async()=>{const calls=[];const owner=api.createBrowserSessionController({timeoutMs:10,fetch:(path,options)=>{if(path==="/auth/session")return Promise.resolve(response({state:"authenticated",generation:"A".repeat(43),csrf_token:csrf,expires_at:Math.floor(Date.now()/1000)+60}));calls.push({path,...options});return new Promise(()=>{});}});try{owner.revalidate();await flush();const session=owner.getSession();assert.equal(session.kind,"ready");const attempt=api.captureBuildAttempt(appScope,input());await assert.rejects(session.buildClients.create.submit(attempt),{code:"unavailable"});await assert.rejects(session.buildClients.create.submit(attempt),{code:"unavailable"});assert.equal(calls.length,2);assert.equal(calls[0].signal.aborted,true);assert.equal(calls[0].body,calls[1].body);assert.equal(calls[0].headers["idempotency-key"],calls[1].headers["idempotency-key"]);}finally{owner.dispose();}});

test("input listing401 invalidates active session; disposal aborts pending create and late success stays inert",async()=>{for(const mode of ["unauthorized","dispose"]){const f=fixture();try{await navigate(f);f.click("New build");const listing=await f.request(inputPath);if(mode==="unauthorized"){listing.resolve(new Response("private",{status:401}));await flush();assert.equal(f.controller.getSession().kind,"unavailable");}else{listing.resolve(response(page()));await flush();const pending=await start(f);f.controller.dispose();assert.equal(pending.signal.aborted,true);pending.resolve(response(receipt(),201));await flush();assert.equal(f.calls.some(c=>c.path.includes("build_id=")),false);}}finally{f.close();}}});

test("caller attempt body, key and accessors fail closed before POST; snapshot survives caller mutation",async()=>{const calls=[];let resolvePost;const owner=api.createBrowserSessionController({fetch:(path,options)=>{calls.push({path,...options});if(path==="/auth/session")return Promise.resolve(response({state:"authenticated",generation:"A".repeat(43),csrf_token:csrf,expires_at:Math.floor(Date.now()/1000)+60}));return new Promise(resolve=>{resolvePost=resolve;});}});try{owner.revalidate();await flush();const session=owner.getSession();assert.equal(session.kind,"ready");const attempt=api.captureBuildAttempt(appScope,input());for(const invalid of [{...attempt,body:attempt.body.replace('"org"','"other"')},{...attempt,key:"header\r\ninjection"},{...attempt,extra:true},{...attempt,get key(){throw Error("accessor must not run");}}])await assert.rejects(session.buildClients.create.submit(invalid),{code:"invalid_request"});assert.equal(calls.length,1);const mutable={...attempt,scope:{...attempt.scope},input:{...attempt.input}};const pending=session.buildClients.create.submit(mutable);mutable.scope.organizationId="other";mutable.input.sourceSha256="f".repeat(64);mutable.body="changed";resolvePost(response(receipt(),201));const committed=await pending;assert.equal(committed.selection.organizationId,"org");assert.equal(committed.selection.sourceSha256,"a".repeat(64));assert.equal(calls[1].body,attempt.body);}finally{owner.dispose();}});

test("caller CSRF factory options cannot manufacture private admission",()=>{assert.throws(()=>api.createBrowserSessionController({csrf_token:csrf}),{code:"invalid_request"});});
