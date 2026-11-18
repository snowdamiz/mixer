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
await build({root,configFile:false,logLevel:"error",plugins:[solid()],resolve:{conditions:["browser"]},build:{target:"es2022",minify:false,lib:{entry:join(root,"tests/application-build-page-runtime.tsx"),formats:["es"],fileName:"application-ui"},outDir:output,emptyOutDir:false}});
const document=new TestNode(9,"#document");document.baseURI="https://console.example/";document.createElement=name=>new TestNode(1,name.toUpperCase());document.createElementNS=(_,name)=>document.createElement(name);document.createTextNode=text=>new TestNode(3,"#text",String(text));document.createComment=text=>new TestNode(8,"#comment",text);document.importNode=(node,deep)=>node.cloneNode(deep);document.getElementById=id=>walk(document).find(n=>n.getAttribute("id")===id)??null;
const window=new TestNode(0,"window");window.document=document;window.location=new URL(document.baseURI);window.scrollTo=()=>{};window.history={state:{_depth:0},length:1,replaceState(state){this.state=state;}};
const originals=new Map(["document","window","Node"].map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]));
Object.assign(globalThis,{document,window,Node:TestNode});
after(()=>{for(const [key,descriptor]of originals)descriptor?Object.defineProperty(globalThis,key,descriptor):delete globalThis[key];});
const {mount}=await import(pathToFileURL(join(output,"application-ui.js")));
function walk(node){return [node,...node.childNodes.flatMap(walk)];}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const json=value=>new Response(JSON.stringify(value),{headers:{"content-type":"application/json","cache-control":"no-store"}});
const scope={organizationId:"org",projectId:"p"};
const dto=(change={})=>({...scope,applicationId:"app",buildId:"b-ios",platform:"ios",sourceSha256:"a".repeat(64),toolchainLockSha256:"b".repeat(64),buildDefinitionSha256:"c".repeat(64),revision:2,state:"queued",attempt:1,maxAttempts:3,failureCode:null,workerCompletionPending:false,...change});
const apps=(ids=["app","empty"],nextCursor=null,projectId="p")=>({...scope,projectId,applications:ids.map(applicationId=>({applicationId})),nextCursor});
const catalog=(rows=[dto(),dto({buildId:"c-android",platform:"android",state:"running",workerCompletionPending:true})],applicationId="app",nextCursor=null)=>({...scope,applicationId,builds:rows,nextCursor});
function fixture(){const calls=[],waiting=[];let index=0;const fetch=(url,options)=>new Promise((resolve,reject)=>{const call={path:String(url),...options,resolve,reject};calls.push(call);waiting.shift()?.(call);});const container=document.createElement("div");document.appendChild(container);const app=mount(container,fetch);return {...app,container,calls,async request(expected){const call=calls[index++]??await new Promise(resolve=>waiting.push(resolve));assert.equal(call.path,expected);assert.equal(call.method,"GET");assert.equal(call.credentials,"same-origin");return call;},text:()=>container.textContent,click(text,tag="BUTTON"){const node=walk(container).find(n=>n.nodeName===tag&&n.textContent.includes(text));assert(node,"missing "+tag+" "+text);node.click();return node;},close(){app.dispose();container.remove();}};}
async function admitted(f){const call=await f.request("/auth/session");call.resolve(json({state:"authenticated",generation:"A".repeat(43),csrf_token:"A".repeat(43),expires_at:Math.floor(Date.now()/1000)+60}));(await f.request("/console-api/v1/orgs")).resolve(json({organizations:[{id:"org",display_name:"Test studio",organization_roles:["owner"]}],next_cursor:null}));await flush();f.click("Test studio");(await f.request("/console-api/v1/projects?organization_id=org")).resolve(json({projects:[{organization_id:"org",id:"p",display_name:"Test project",roles:["viewer"]},{organization_id:"org",id:"q",display_name:"Other project",roles:["viewer"]}],next_cursor:null}));await flush();f.click("Test project");f.click("View builds","A");return f.request("/console-api/v1/applications?organization_id=org&project_id=p");}
async function listed(f){(await admitted(f)).resolve(json(apps()));await flush();f.click("Application IDapp");(await f.request("/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=app")).resolve(json(catalog()));await flush();}
const readPath="/console-api/v1/builds?organization_id=org&project_id=p&application_id=app&build_id=b-ios&platform=ios&source_sha256="+"a".repeat(64)+"&toolchain_lock_sha256="+"b".repeat(64)+"&build_definition_sha256="+"c".repeat(64);

test("actual Solid handlers navigate workspace → applications → stored row → queued detail → failed refresh",async()=>{const f=fixture();try{await listed(f);assert.match(f.text(),/iOS.*b-ios.*Queued.*Android.*c-android.*Running/);f.click("b-ios");const read=await f.request(readPath);assert.doesNotMatch(f.text(),/1 of 1 platforms reported/);read.resolve(json({build:dto()}));await flush();assert.match(f.text(),/1 of 1 platforms reported/);const detail=walk(f.container).find(n=>n.getAttribute("aria-label")==="Selected build");assert.match(detail.textContent,/Queued/);assert.doesNotMatch(detail.textContent,/Android|c-android/);assert.equal(walk(f.container).some(n=>n.nodeName==="INPUT"),false);f.click("Refresh build");const refresh=await f.request(readPath);assert.doesNotMatch(f.text(),/1 of 1 platforms reported/);refresh.resolve(json({build:dto({revision:3,state:"failed",failureCode:"compiler_error"})}));await flush();assert.match(detail.textContent,/Compilation failed/);const rows=walk(f.container).find(n=>n.getAttribute("aria-label")==="Platform builds");assert.match(rows.textContent,/iOSb-iosFailed/);assert.doesNotMatch(rows.textContent,/Queued/);assert.match(rows.textContent,/Androidc-androidRunning/);f.click("Application IDempty");assert.doesNotMatch(f.text(),/Compilation failed/);(await f.request("/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=empty")).resolve(json(catalog([],"empty")));await flush();assert.match(f.text(),/No builds yet/);assert.doesNotMatch(f.text(),/Could not load|Succeeded/);}finally{f.close();}});

test("opaque current application/build cursors and first-page actions clear selection without inventing rows",async()=>{const f=fixture();try{(await admitted(f)).resolve(json(apps(undefined,"TkVYVA")));await flush();f.click("More applications");(await f.request("/console-api/v1/applications?organization_id=org&project_id=p&cursor=TkVYVA")).resolve(json(apps([])));await flush();assert.match(f.text(),/No applications yet/);f.click("First applications");(await f.request("/console-api/v1/applications?organization_id=org&project_id=p")).resolve(json(apps()));await flush();f.click("Application IDapp");(await f.request("/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=app")).resolve(json(catalog(undefined,"app","QlVJTEQ")));await flush();f.click("More builds");(await f.request("/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=app&cursor=QlVJTEQ")).resolve(json(catalog([],"app")));await flush();assert.match(f.text(),/No builds yet/);f.click("First builds");await f.request("/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=app");}finally{f.close();}});

test("pending application, project, route, and session changes discard old detail and never retarget requests",async()=>{const f=fixture();try{await listed(f);f.click("b-ios");const old=await f.request(readPath);f.click("Application IDempty");const empty=await f.request("/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=empty");assert.equal(old.signal.aborted,true);old.resolve(json({build:dto({state:"succeeded"})}));empty.resolve(json(catalog([],"empty")));await flush();assert.doesNotMatch(f.text(),/1 of 1 platforms reported|This platform build completed successfully/);f.history.back();await flush();f.click("Other project");f.click("View builds","A");const other=await f.request("/console-api/v1/applications?organization_id=org&project_id=q");other.resolve(json(apps([],null,"q")));await flush();assert.match(f.text(),/Other project/);assert.doesNotMatch(f.text(),/b-ios/);f.controller.revalidate();const auth=await f.request("/auth/session");assert.doesNotMatch(f.text(),/Other project|Application IDapp/);auth.resolve(json({state:"unauthenticated",csrf_token:"A".repeat(43)}));await flush();assert.match(f.text(),/Sign in to continue/);f.click("Check session");await f.request("/auth/session");}finally{f.close();}});

test("403, 404, 503 and 401 contract refusals render closed customer copy with no private response text",async()=>{for(const [status,label]of [[403,"Build access unavailable"],[404,"Selection no longer available"],[503,"Build data unavailable"],[401,"Build data unavailable"]]){const f=fixture();try{const call=await admitted(f);call.resolve(new Response("SQL-cookie-private-sentinel",{status}));await flush();assert.ok(f.text().includes(label),status+" "+f.text());assert.doesNotMatch(f.text(),/SQL-cookie-private-sentinel|Application IDapp|b-ios/);if(status===401)assert.equal(f.controller.getSession().kind,"unavailable");}finally{f.close();}}});


const rejectedRefreshes = [{revision:2},{organizationId:"other"},{projectId:"other"},{applicationId:"other"},
  {buildId:"other"},{platform:"android"},{sourceSha256:"d".repeat(64)},
  {toolchainLockSha256:"d".repeat(64)},{buildDefinitionSha256:"d".repeat(64)}];
for (const change of rejectedRefreshes) for (const checkpoint of ["pending", "rejected"]) {
  test(`accepted Failed revision4 remains current at ${checkpoint} refresh: ${Object.keys(change)[0]}`, async () => {
    const f = fixture();
    try {
      await listed(f); f.click("b-ios");
      (await f.request(readPath)).resolve(json({build:dto({revision:4,state:"failed",failureCode:"compiler_error"})}));
      await flush();
      const rows = () => walk(f.container).find(n => n.getAttribute("aria-label") === "Platform builds").textContent;
      assert.match(rows(), /iOSb-iosFailed/);
      f.click("Refresh build"); const request = await f.request(readPath);
      assert.match(f.text(), /Loading a build/);
      if (checkpoint === "rejected") {
        request.resolve(json({build:dto({revision:5,state:"succeeded",...change})}));
        await flush(); assert.match(f.text(), /Could not load a build/);
      }
      assert.match(rows(), /iOSb-iosFailed/, `${checkpoint}: last accepted outcome must remain visible`);
      assert.doesNotMatch(rows(), /Queued|Succeeded/);
      assert.match(rows(), /Androidc-androidRunning/);
      assert.doesNotMatch(f.text(), /This platform build completed successfully/);
    } finally { f.close(); }
  });
}

test("changing selected build drops its observation and never blends a late refresh", async () => {
  const f = fixture();
  try {
    await listed(f); f.click("b-ios");
    (await f.request(readPath)).resolve(json({build:dto({revision:4,state:"failed",failureCode:"compiler_error"})}));
    await flush(); f.click("Refresh build"); const late = await f.request(readPath);
    f.click("c-android");
    const next = await f.request(readPath.replace("build_id=b-ios&platform=ios", "build_id=c-android&platform=android"));
    const rows = () => walk(f.container).find(n => n.getAttribute("aria-label") === "Platform builds").textContent;
    assert.equal(late.signal.aborted, true);
    assert.match(rows(), /iOSb-iosQueued/); assert.doesNotMatch(rows(), /Failed/);
    late.resolve(json({build:dto({revision:9,state:"failed",failureCode:"compiler_error"})}));
    next.resolve(json({build:dto({buildId:"c-android",platform:"android",revision:3,state:"succeeded"})}));
    await flush(); assert.match(rows(), /iOSb-iosQueued/); assert.match(rows(), /Androidc-androidSucceeded/);
    assert.doesNotMatch(rows(), /Failed/);
  } finally { f.close(); }
});

test("late failed detail after application or session generation change cannot repaint current row",async()=>{for(const reset of ["application","session"]){const f=fixture();try{await listed(f);f.click("b-ios");(await f.request(readPath)).resolve(json({build:dto({revision:4,state:"failed",failureCode:"compiler_error"})}));await flush();f.click("Refresh build");const late=await f.request(readPath);if(reset==="application"){f.click("Application IDempty");(await f.request("/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=empty")).resolve(json(catalog([],"empty")));}else{f.controller.revalidate();(await f.request("/auth/session")).resolve(json({state:"unauthenticated",csrf_token:"A".repeat(43)}));}late.resolve(json({build:dto({revision:9,state:"failed",failureCode:"compiler_error"})}));await flush();assert.equal(late.signal.aborted,true);assert.doesNotMatch(f.text(),/Compilation failed|b-ios/);}finally{f.close();}}});
