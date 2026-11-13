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


test("R2240-F2: reselecting created build must retain equal-revision state coherence",async()=>{
 const f=fixture();try{
  await listed(f,[dto()]);const post=await start(f);
  post.resolve(response(receipt(),201));const read=await f.request(detailPath());const refresh=await f.request(catalogPath);
  refresh.resolve(response(catalog([dto()])));read.resolve(response({build:dto({state:'failed',revision:4,failureCode:'compiler_error'})}));await flush();
  assert.match(selectedText(f),/Compilation failed/);
  const row=walk(f.container).find(n=>n.nodeName==='BUTTON'&&n.textContent.includes('build-'+'d'.repeat(64)));assert(row);row.click();
  (await f.request(detailPath())).resolve(response({build:dto({state:'succeeded',revision:4})}));await flush();
  console.log('R2240_OBSERVATION '+JSON.stringify({id:'F2',actualSelectedText:selectedText(f),sameSession:true,sameEightIdentityFields:true,acceptedRevision:4,returnedRevision:4,acceptedState:'failed',returnedState:'succeeded'}));
  assert.doesNotMatch(selectedText(f),/This platform build completed successfully/,'Same immutable selection and revision regressed from accepted Failed to contradictory Succeeded after clicking the current row');
 }finally{f.close();}
});

function buildRowText(f){return walk(f.container).find(n=>n.nodeName==='BUTTON'&&n.textContent.includes(dto().buildId)).textContent;}
function clickRow(f,buildId=dto().buildId){
 const row=walk(f.container).find(n=>n.nodeName==='BUTTON'&&n.textContent.includes(buildId));assert(row);row.click();
}
const failed=dto({state:'failed',revision:4,failureCode:'compiler_error'});
async function acceptedFailure(f,rows=[dto()]){
 await listed(f,rows);const post=await start(f);
 post.resolve(response(receipt(),201));const read=await f.request(detailPath());const refresh=await f.request(catalogPath);
 refresh.resolve(response(catalog(rows)));read.resolve(response({build:failed}));await flush();
 assert.match(selectedText(f),/Compilation failed/);
}
for(const [name,reply] of [
 ['contradictory equal revision',()=>response({build:dto({state:'succeeded',revision:4})})],
 ['revision rollback',()=>response({build:dto({state:'succeeded',revision:3})})],
 ['identity-mismatched reply',()=>response({build:dto({sourceSha256:'e'.repeat(64),revision:4})})]
])test('R2252: same selection keeps Failed while pending and after '+name,async()=>{
 const f=fixture();try{
  await acceptedFailure(f);clickRow(f);const pending=await f.request(detailPath());
  assert.match(buildRowText(f),/Failed/);assert.doesNotMatch(selectedText(f),/This platform build completed successfully/);
  pending.resolve(reply());await flush();
  assert.match(buildRowText(f),/Failed/);assert.doesNotMatch(selectedText(f),/This platform build completed successfully/);
  clickRow(f);const coherent=await f.request(detailPath());assert.match(buildRowText(f),/Failed/);
  coherent.resolve(response({build:failed}));await flush();assert.match(selectedText(f),/Compilation failed/);
  f.click('Refresh build');(await f.request(detailPath())).resolve(response({build:dto({state:'succeeded',revision:5})}));await flush();
  assert.match(selectedText(f),/This platform build completed successfully/);
 }finally{f.close();}
});
test('R2252: switching builds discards revision and accepted state together',async()=>{
 const f=fixture();try{
  const other=dto({buildId:'build-'+'e'.repeat(64)});await acceptedFailure(f,[dto(),other]);
  clickRow(f,other.buildId);(await f.request(detailPath(selection({build_id:other.buildId})))).resolve(response({build:{...other,state:'succeeded',revision:1}}));await flush();
  assert.match(selectedText(f),/This platform build completed successfully/);assert.doesNotMatch(selectedText(f),/Compilation failed/);
  clickRow(f);(await f.request(detailPath())).resolve(response({build:dto({state:'succeeded',revision:1})}));await flush();
  assert.match(selectedText(f),/This platform build completed successfully/);
 }finally{f.close();}
});
test('R2252: input selection reset discards paired acceptance before the same build is selected',async()=>{
 const f=fixture();try{
  await acceptedFailure(f);f.click('New build');
  (await f.request(inputPath)).resolve(response(page([input(),input({sourceInputId:'source-2',sourceSha256:'e'.repeat(64)})])));await flush();
  f.click('Input source-2 · Source '+'e'.repeat(12));
  assert.match(selectedText(f),/Choose a build/);assert.doesNotMatch(f.text(),/Compilation failed/);
  clickRow(f);(await f.request(detailPath())).resolve(response({build:dto({state:'succeeded',revision:1})}));await flush();
  assert.match(selectedText(f),/This platform build completed successfully/);
 }finally{f.close();}
});
test('R2252: application scope reset fences late reply and discards paired acceptance',async()=>{
 const f=fixture();try{
  await acceptedFailure(f);clickRow(f);const late=await f.request(detailPath());
  f.click('Application IDother');assert.equal(late.signal.aborted,true);
  const otherScope={...appScope,applicationId:'other'};
  (await f.request(catalogPath.replace('application_id=app','application_id=other'))).resolve(response({...otherScope,builds:[],nextCursor:null}));await flush();
  late.resolve(response({build:dto({state:'failed',revision:9,failureCode:'compiler_error'})}));await flush();
  assert.match(selectedText(f),/Choose a build/);assert.doesNotMatch(f.text(),/Compilation failed/);
  f.click('Application IDapp');(await f.request(catalogPath)).resolve(response(catalog([dto()])));await flush();
  clickRow(f);(await f.request(detailPath())).resolve(response({build:dto({state:'succeeded',revision:1})}));await flush();
  assert.match(selectedText(f),/This platform build completed successfully/);
 }finally{f.close();}
});
for(const generation of ['A','B'])test('R2252: session replacement '+generation+' discards acceptance even with late old reply',async()=>{
 const f=fixture();try{
  await acceptedFailure(f);clickRow(f);const late=await f.request(detailPath());
  f.controller.revalidate();assert.equal(late.signal.aborted,true);
  assert.equal(walk(f.container).some(n=>n.getAttribute('aria-label')==='Selected build'),false);
  late.resolve(response({build:dto({state:'failed',revision:9,failureCode:'compiler_error'})}));await flush();
  f.history.set({value:'/workspace',replace:true,scroll:false});await flush();
  (await f.request('/auth/session')).resolve(response({state:'authenticated',generation:generation==='A'?'A'.repeat(43):'B'.repeat(42)+'A',csrf_token:csrf,expires_at:Math.floor(Date.now()/1000)+60}));
  (await f.request('/console-api/v1/orgs')).resolve(response({organizations:[{id:'org',display_name:'Studio',organization_roles:['owner']}],next_cursor:null}));await flush();
  f.click('Studio');(await f.request('/console-api/v1/projects?organization_id=org')).resolve(response({projects:[{organization_id:'org',id:'p',display_name:'Project',roles:['administrator']}],next_cursor:null}));await flush();f.click('Project');
  walk(f.container).find(n=>n.nodeName==='A'&&n.textContent.includes('View builds')).click();
  (await f.request('/console-api/v1/applications?organization_id=org&project_id=p')).resolve(response({organizationId:'org',projectId:'p',applications:[{applicationId:'app'}],nextCursor:null}));await flush();
  f.click('Application IDapp');(await f.request(catalogPath)).resolve(response(catalog([dto()])));await flush();
  clickRow(f);(await f.request(detailPath())).resolve(response({build:dto({state:'succeeded',revision:1})}));await flush();
  assert.match(selectedText(f),/This platform build completed successfully/);
 }finally{f.close();}
});
