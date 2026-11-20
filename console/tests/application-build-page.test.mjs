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
  click(){if(this.disabled)return;this.dispatch("click");}
  dispatch(type){const nodes=[];for(let n=this;n;n=n.parentNode)nodes.push(n);if(!nodes.includes(document))nodes.push(document);nodes.push(window);const event={type,button:0,target:this,currentTarget:document,defaultPrevented:false,cancelBubble:false,preventDefault(){this.defaultPrevented=true;},stopPropagation(){this.cancelBubble=true;},composedPath:()=>nodes};for(const node of nodes)for(const fn of [...(node.listeners?.get(type)??[])])fn(event);}
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
function fixture(profile, initialPath){const calls=[],waiting=[];let index=0;const fetch=(url,options)=>{
  if (url === "/console-api/v1/workspace-admin" && JSON.parse(options.body).operation === "usage") {
    return Promise.resolve(json({ organization_id: "org", plan: "free", active_projects: 2, project_limit: 3,
      held_builds: 0, build_limit: 2, builds: 0, can_administer: false }));
  }
  return new Promise((resolve,reject)=>{const call={path:String(url),...options,resolve,reject};calls.push(call);waiting.shift()?.(call);});};const container=document.createElement("div");document.appendChild(container);const app=mount(container,fetch,profile,initialPath);return {...app,container,calls,async request(expected, method = "GET"){const call=calls[index++]??await new Promise(resolve=>waiting.push(resolve));assert.equal(call.path,expected);assert.equal(call.method,method);assert.equal(call.credentials,"same-origin");return call;},text:()=>container.textContent,click(text,tag="BUTTON"){const node=walk(container).find(n=>n.nodeName===tag&&n.textContent.includes(text));assert(node,"missing "+tag+" "+text);node.click();return node;},close(){app.dispose();container.remove();}};}
async function admitted(f, organizations = [{id:"org",display_name:"Test studio",organization_roles:["owner"]}]){
  const call = await f.request("/auth/session");
  call.resolve(json({state:"authenticated",generation:"A".repeat(43),csrf_token:"A".repeat(43),expires_at:Math.floor(Date.now()/1000)+60}));
  (await f.request("/console-api/v1/orgs")).resolve(json({organizations,next_cursor:null}));
  await flush();
  f.click("Test studio");
  (await f.request("/console-api/v1/projects?organization_id=org")).resolve(json({projects:[
    {organization_id:"org",id:"p",display_name:"Test project",roles:["viewer"]},
    {organization_id:"org",id:"q",display_name:"Other project",roles:["viewer"]},
  ],next_cursor:null}));
  await flush();
  f.click("Test project");
  f.click("View builds","A");
  return f.request("/console-api/v1/applications?organization_id=org&project_id=p");
}
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

const logsPath = readPath.replace("/builds?", "/build-logs?");
const catalogPath = "/console-api/v1/build-catalog?organization_id=org&project_id=p&application_id=app";
const success = dto({ revision: 4, state: "native_succeeded" });
const cancelled = dto({ revision: 4, state: "cancelled" });
const nativeDetail = {
  ...success,
  artifacts: ["unsigned_native_binary", "debug_symbols", "resource_inventory"].map(kind => ({
    kind, sizeBytes: 5, sha256: "a".repeat(64),
    downloadPath: "/console-api/v1/build-artifacts/" + kind + "?" + readPath.split("?")[1],
  })),
};
const artifactLinks = container => walk(container).filter(node => node.nodeName === "A" && node.hasAttribute("download"));

const command = { event: "build_command_finished", exitCode: 0 };
const compiler = { event: "compiler_finished", exitCode: 0, stdoutBytes: 320, stderrBytes: 80,
  tailTruncated: true, phases: ["compile", "link"] };
const logEnvelope = (build, events = [compiler, command]) => ({ buildLogs: { ...build, events } });

test("normal route opens retained logs from an already successful native catalog row", { timeout: 3000 }, async () => {
  const f = fixture();
  try {
    (await admitted(f)).resolve(json(apps()));
    await flush();
    f.click("Application IDapp");
    (await f.request(catalogPath)).resolve(json(catalog([nativeDetail])));
    await flush();
    assert.match(f.text(), /b-iosSucceeded/);
    assert.equal(artifactLinks(f.container).length, 0);
    f.click("b-ios");
    const buildRequest = await f.request(readPath);
    assert.equal(artifactLinks(f.container).length, 0);
    const shuffled = nativeDetail.artifacts.map(artifact => {
      const [path, params] = artifact.downloadPath.split("?");
      return { ...artifact, downloadPath: path + "?" + params.split("&").reverse().join("&") };
    });
    buildRequest.resolve(json({ build: { ...nativeDetail, artifacts: shuffled } }));
    await flush();
    assert.match(f.text(), /This platform build completed successfully/);
    const links = artifactLinks(f.container);
    assert.deepEqual(links.map(link => link.textContent), ["Unsigned iOS build", "Debug symbols", "Resource inventory"]);
    assert.deepEqual(links.map(link => link.getAttribute("href")), nativeDetail.artifacts.map(artifact => artifact.downloadPath));
    assert.ok(links.every(link => link.getAttribute("referrerpolicy") === "no-referrer"));
    assert.equal(f.calls.some(call => call.path.startsWith("/console-api/v1/build-logs")), false);
    f.click("View build logs");
    const read = await f.request(logsPath);
    assert.match(f.text(), /Loading build logs/);
    read.resolve(json(logEnvelope(success)));
    await flush();
    const events = walk(f.container).find(node => node.getAttribute("aria-label") === "Build events for attempt 1");
    assert.ok(events);
    assert.match(events.textContent, /Compiler finished \(exit code 0\).*320 bytes on stdout.*80 bytes on stderr.*compile, link.*truncated.*Build command finished \(exit code 0\)/);
    assert.match(f.text(), /This platform build completed successfully/);
    f.click("Refresh build");
    const refresh = await f.request(readPath);
    assert.equal(artifactLinks(f.container).length, 0);
    refresh.resolve(new Response(null, { status: 403 }));
    await flush();
    assert.equal(artifactLinks(f.container).length, 0);
  } finally { f.close(); }
});

test("selected Android build shows its unsigned APK and authenticated driver logs", async () => {
  const readAndroid = readPath.replace("build_id=b-ios&platform=ios", "build_id=c-android&platform=android");
  const artifacts = nativeDetail.artifacts.map(artifact => ({
    ...artifact,
    sizeBytes: artifact.kind === "unsigned_native_binary" ? 27_795_726 : artifact.sizeBytes,
    downloadPath: "/console-api/v1/build-artifacts/" + artifact.kind + "?" + readAndroid.split("?")[1],
  }));
  const android = { ...nativeDetail, artifacts, buildId: "c-android", platform: "android" };
  const f = fixture();
  try {
    (await admitted(f)).resolve(json(apps()));
    await flush();
    f.click("Application IDapp");
    (await f.request(catalogPath)).resolve(json(catalog([android])));
    await flush();
    f.click("c-android");
    (await f.request(readAndroid)).resolve(json({ build: android }));
    await flush();

    const links = artifactLinks(f.container);
    assert.deepEqual(links.map(link => link.textContent), ["Unsigned APK", "Debug symbols", "Resource inventory"]);
    assert.deepEqual(links.map(link => link.getAttribute("href")), artifacts.map(artifact => artifact.downloadPath));
    assert.equal(f.calls.some(call => call.path.startsWith("/console-api/v1/build-logs")), false);
    f.click("View build logs");
    const driver = { ...compiler, event: "android_driver_finished", phases: [] };
    const { artifacts: _artifacts, ...logBuild } = android;
    (await f.request(readAndroid.replace("/builds?", "/build-logs?")))
      .resolve(json(logEnvelope(logBuild, [driver, command])));
    await flush();
    const events = walk(f.container).find(node => node.getAttribute("aria-label") === "Build events for attempt 1");
    assert.match(events?.textContent ?? "", /Android build driver finished \(exit code 0\).*320 bytes on stdout.*80 bytes on stderr.*Build command finished \(exit code 0\)/);
    assert.doesNotMatch(events.textContent, /Compiler finished|Recorded phases/);
  } finally { f.close(); }
});

test("selected build refuses foreign, repeated, and cross-origin artifact routes", async () => {
  const path = nativeDetail.artifacts[0].downloadPath;
  const invalidPaths = [
    path.replace("build_id=b-ios", "build_id=another-build"),
    path + "&build_id=b-ios",
    "https://foreign.example" + path,
  ];
  for (const invalidPath of invalidPaths) {
    const f = fixture();
    try {
      await listed(f);
      f.click("b-ios");
      const artifacts = nativeDetail.artifacts.map((artifact, index) =>
        index === 0 ? { ...artifact, downloadPath: invalidPath } : artifact);
      (await f.request(readPath)).resolve(json({ build: { ...nativeDetail, artifacts } }));
      await flush();
      assert.match(f.text(), /Could not load a build/);
      assert.equal(artifactLinks(f.container).length, 0);
    } finally { f.close(); }
  }
});

test("cancelled build reads command-only events and recovers from unavailable or malformed logs", { timeout: 3000 }, async () => {
  const f = fixture();
  try {
    await listed(f);
    f.click("b-ios");
    (await f.request(readPath)).resolve(json({ build: cancelled }));
    await flush();
    f.click("View build logs");
    for (const response of [new Response("private sentinel", { status: 404 }),
      new Response("private sentinel", { status: 503 }),
      json(logEnvelope({ ...cancelled, attempt: 2 }, [{ ...command, exitCode: -22 }]))]) {
      (await f.request(logsPath)).resolve(response);
      await flush();
      assert.match(f.text(), /Build logs are unavailable/);
      assert.match(f.text(), /Cancelled/);
      assert.doesNotMatch(f.text(), /private sentinel|Build command finished/);
      f.click("Retry build logs");
    }
    (await f.request(logsPath)).resolve(json(logEnvelope(cancelled, [{ ...command, exitCode: -15 }])));
    await flush();
    assert.match(f.text(), /Build command finished \(exit code -15\)/);
    assert.doesNotMatch(f.text(), /Compiler finished|Build logs are unavailable/);
  } finally { f.close(); }
});

test("refresh clears previous logs and accepts only the new terminal attempt", { timeout: 3000 }, async () => {
  const f = fixture();
  try {
    await listed(f);
    f.click("b-ios");
    (await f.request(readPath)).resolve(json({ build: cancelled }));
    await flush();
    f.click("View build logs");
    (await f.request(logsPath)).resolve(json(logEnvelope(cancelled, [{ ...command, exitCode: -15 }])));
    await flush();
    assert.match(f.text(), /Build command finished \(exit code -15\)/);
    f.click("Refresh build");
    assert.doesNotMatch(f.text(), /Build command finished/);
    const newer = { ...cancelled, revision: 7, attempt: 2 };
    (await f.request(readPath)).resolve(json({ build: newer }));
    await flush();
    f.click("View build logs");
    (await f.request(logsPath)).resolve(json(logEnvelope(cancelled, [{ ...command, exitCode: -15 }])));
    await flush();
    assert.match(f.text(), /Build logs are unavailable/);
    f.click("Retry build logs");
    (await f.request(logsPath)).resolve(json(logEnvelope(newer, [{ ...command, exitCode: -9 }])));
    await flush();
    const events = walk(f.container).find(node => node.getAttribute("aria-label") === "Build events for attempt 2");
    assert.match(events?.textContent ?? "", /Build command finished \(exit code -9\)/);
  } finally { f.close(); }
});

test("changing build or tenant aborts retained logs and a late response cannot repaint detail", { timeout: 3000 }, async () => {
  const f = fixture();
  try {
    (await admitted(f, [
      { id: "org", display_name: "Test studio", organization_roles: ["owner"] },
      { id: "other", display_name: "Other studio", organization_roles: ["owner"] },
    ])).resolve(json(apps()));
    await flush();
    f.click("Application IDapp");
    (await f.request(catalogPath)).resolve(json(catalog()));
    await flush();
    f.click("b-ios");
    (await f.request(readPath)).resolve(json({ build: cancelled }));
    await flush();
    f.click("View build logs");
    const oldBuild = await f.request(logsPath);
    f.click("c-android");
    assert.ok(oldBuild.signal.aborted);
    (await f.request(readPath.replace("build_id=b-ios&platform=ios", "build_id=c-android&platform=android")))
      .resolve(json({ build: dto({ buildId: "c-android", platform: "android", state: "succeeded" }) }));
    oldBuild.resolve(json(logEnvelope(cancelled)));
    await flush();
    assert.doesNotMatch(f.text(), /Compiler finished|View build logs/);

    f.click("b-ios");
    (await f.request(readPath)).resolve(json({ build: cancelled }));
    await flush();
    f.click("View build logs");
    const oldTenant = await f.request(logsPath);
    f.history.back();
    await flush();
    f.click("Other studio");
    assert.ok(oldTenant.signal.aborted);
    const differentTenant = { organizationId: "other" };
    (await f.request("/console-api/v1/projects?organization_id=other")).resolve(json({ projects: [
      { organization_id: "other", id: "p", display_name: "Other studio project", roles: ["viewer"] },
    ], next_cursor: null }));
    await flush();
    f.click("Other studio project");
    f.click("View builds", "A");
    (await f.request("/console-api/v1/applications?organization_id=other&project_id=p"))
      .resolve(json({ ...apps(), ...differentTenant }));
    await flush();
    f.click("Application IDapp");
    const otherBuild = { ...cancelled, ...differentTenant };
    (await f.request(catalogPath.replace("=org&", "=other&")))
      .resolve(json({ ...catalog([otherBuild]), ...differentTenant }));
    await flush();
    f.click("b-ios");
    (await f.request(readPath.replace("=org&", "=other&"))).resolve(json({ build: otherBuild }));
    await flush();
    f.click("View build logs");
    const next = await f.request(logsPath.replace("=org&", "=other&"));
    oldTenant.resolve(json(logEnvelope(cancelled)));
    await flush();
    assert.match(f.text(), /Loading build logs/);
    assert.doesNotMatch(f.text(), /Compiler finished/);
    next.resolve(json(logEnvelope(otherBuild, [{ ...command, exitCode: -9 }])));
    await flush();
    assert.match(f.text(), /Build command finished \(exit code -9\)/);
  } finally { f.close(); }
});

test("logs honor existing session invalidation", { timeout: 3000 }, async () => {
  const f = fixture();
  try {
    await listed(f);
    f.click("b-ios");
    (await f.request(readPath)).resolve(json({ build: cancelled }));
    await flush();
    f.click("View build logs");
    (await f.request(logsPath)).resolve(new Response("private sentinel", { status: 401 }));
    await flush();
    assert.equal(f.controller.getSession().kind, "unavailable");
    assert.doesNotMatch(f.text(), /Build logs|private sentinel|b-ios/);
  } finally { f.close(); }
});

test("ordinary iOS success retains its detail without a retained-log action", { timeout: 3000 }, async () => {
  const f = fixture();
  try {
    await listed(f);
    f.click("b-ios");
    (await f.request(readPath)).resolve(json({ build: dto({ revision: 4, state: "succeeded" }) }));
    await flush();
    assert.match(f.text(), /This platform build completed successfully/);
    assert.doesNotMatch(f.text(), /Build logs|View build logs/);
    assert.equal(f.calls.some(call => call.path.startsWith("/console-api/v1/build-logs")), false);
  } finally { f.close(); }
});

for (const stage of ["catalog", "detail"]) {
  test(`Android native success is refused in ${stage}`, { timeout: 3000 }, async () => {
    const f = fixture();
    const android = { ...nativeDetail, buildId: "c-android", platform: "android" };
    try {
      if (stage === "catalog") {
        (await admitted(f)).resolve(json(apps()));
        await flush();
        f.click("Application IDapp");
        (await f.request(catalogPath)).resolve(json(catalog([android])));
      } else {
        await listed(f);
        f.click("c-android");
        const detailPath = readPath.replace("build_id=b-ios&platform=ios", "build_id=c-android&platform=android");
        (await f.request(detailPath)).resolve(json({ build: android }));
      }
      await flush();
      assert.match(f.text(), /Could not load a (platform )?build/);
      assert.doesNotMatch(f.text(), /Succeeded|Build logs/);
    } finally { f.close(); }
  });
}

const registrationForm = f => walk(f.container).find(node => node.nodeName === "FORM" &&
  node.getAttribute("aria-label") === "Register application");
const applicationListPath = "/console-api/v1/applications?organization_id=org&project_id=p";

test("workspace-builds owner registers and refreshes an empty project through the actual form", { timeout: 3000 }, async () => {
  const f = fixture("workspace-builds");
  try {
    (await admitted(f)).resolve(json(apps([])));
    await flush();
    const form = registrationForm(f);
    assert.ok(form);
    const input = walk(form).find(node => node.nodeName === "INPUT");
    input.value = "example.fixture.app";
    input.dispatch("input");
    form.dispatch("submit");
    const post = await f.request("/console-api/v1/applications", "POST");
    const payload = { organization_id: "org", project_id: "p", application_id: "example.fixture.app" };
    assert.deepEqual(JSON.parse(post.body), payload);
    assert.equal(post.headers["x-mixer-csrf"], "A".repeat(43));
    form.dispatch("submit");
    assert.equal(f.calls.filter(call => call.method === "POST").length, 1);
    post.resolve(new Response(JSON.stringify(payload), {
      status: 201, headers: { "content-type": "application/json", "cache-control": "no-store" },
    }));
    (await f.request(applicationListPath)).resolve(json(apps([payload.application_id])));
    await flush();
    assert.match(f.text(), /example.fixture.app/);
    assert.equal(registrationForm(f), undefined);
  } finally { f.close(); }
});

test("registration is hidden for a viewer, outside the opt-in profile, and on empty continuation pages", { timeout: 3000 }, async () => {
  for (const [profile, role] of [[undefined, "owner"], ["workspace-manage", "owner"], ["workspace-builds", "viewer"]]) {
    const f = fixture(profile);
    try {
      (await admitted(f, [{ id: "org", display_name: "Test studio", organization_roles: [role] }]))
        .resolve(json(apps([])));
      await flush();
      assert.equal(registrationForm(f), undefined, `${profile ?? "default"} / ${role}`);
      assert.ok(f.calls.every(call => call.method === "GET"));
    } finally { f.close(); }
  }
  const f = fixture("workspace-builds");
  try {
    (await admitted(f)).resolve(json(apps(["existing"], "TkVYVA")));
    await flush();
    assert.equal(registrationForm(f), undefined);
    f.click("More applications");
    (await f.request(applicationListPath + "&cursor=TkVYVA")).resolve(json(apps([])));
    await flush();
    assert.equal(registrationForm(f), undefined);
    f.click("First applications");
    (await f.request(applicationListPath)).resolve(json(apps(["existing"])));
    await flush();
    assert.match(f.text(), /existing/);
  } finally { f.close(); }
});

const releaseTarget = {
  organizationId: "org", projectId: "p", applicationId: "app", environmentId: "prod",
  platform: "ios", runtimeFingerprint: "a".repeat(64), channel: "beta",
};
const publishedRelease = {
  releaseId: "committed-release", sequence: "18446744073709551615", rolloutBasisPoints: 3750,
  manifestSha256: "b".repeat(64), payloadSha256: "c".repeat(64),
  details: {
    sourceCommit: "d".repeat(40), payloadBytes: 61, artifactKeyId: "artifact-v3", assignmentKeyId: "assignment-v3",
    action: "rollback", capabilities: [
      { id: "network.http.v1", permissions: ["network.https"] },
      { id: "storage.keyValue.v1", permissions: ["storage.appPrivate"] },
    ],
  },
};
const releaseQuery = channel =>
  "organization_id=org&project_id=p&application_id=app&environment_id=prod&platform=ios&runtime_fingerprint="
  + releaseTarget.runtimeFingerprint + "&channel=" + channel;
const releaseRoute = channel => "/releases?" + releaseQuery(channel);
const releaseEndpoint = channel => "/console-api/v1/release-head?" + releaseQuery(channel) + "&view=details";
const releaseCalls = f => f.calls.filter(call => call.path.startsWith("/console-api/v1/release-head?"));
const go = (f, value) => f.history.set({ value, replace: false, scroll: false });
const publish = (channel, release = publishedRelease) => json({
  kind: "published", target: { ...releaseTarget, channel }, release,
});
const releaseStatus = f => walk(f.container).find(node => node.getAttribute("role") === "status")?.textContent;
const admitReleaseSession = async f => {
  (await f.request("/auth/session")).resolve(json({
    state: "authenticated", generation: "A".repeat(43), csrf_token: "A".repeat(43),
    expires_at: Math.floor(Date.now() / 1000) + 60,
  }));
  await flush();
};

test("Releases waits for a session and displays only the committed head from an exact cookie GET", { timeout: 5000 }, async () => {
  const f = fixture(undefined, releaseRoute("beta"));
  try {
    assert.equal(releaseStatus(f), "Console session unavailable.");
    assert.equal(releaseCalls(f).length, 0);
    await admitReleaseSession(f);
    const [read] = releaseCalls(f);
    assert.equal(read.path, releaseEndpoint("beta"));
    assert.equal(read.method, "GET");
    assert.equal(read.credentials, "same-origin");
    assert.equal(read.redirect, "error");
    assert.equal(read.cache, "no-store");
    assert.equal(read.referrerPolicy, "no-referrer");
    assert.deepEqual(read.headers, { accept: "application/json" });
    assert.equal(read.body, undefined);
    assert.equal(releaseStatus(f), "Loading release head…");
    read.resolve(publish("beta"));
    await flush();
    assert.equal(releaseStatus(f), "Published release");
    const fields = walk(f.container).filter(node => node.nodeName === "DD").map(node => node.textContent);
    assert.deepEqual(fields, [
      ...Object.values(releaseTarget), publishedRelease.releaseId, publishedRelease.sequence, "3750",
      publishedRelease.manifestSha256, publishedRelease.payloadSha256, publishedRelease.details.sourceCommit,
      "61 bytes", "artifact-v3", "assignment-v3", "Rollback", "Compatibility checked when this head was committed.",
      "network.http.v1network.httpsstorage.keyValue.v1storage.appPrivate",
    ]);
    assert.doesNotMatch(f.text(), /Checks passed|Checks incomplete|Sign off|Publish release|Rollback available/);
    assert.equal(walk(f.container).some(node => node.nodeName === "BUTTON"), false);
  } finally { f.close(); }
});

test("Releases rejects incomplete, duplicate, unknown, and malformed query fields before sending a read", { timeout: 5000 }, async () => {
  const f = fixture(undefined, "/releases");
  try {
    await admitReleaseSession(f);
    assert.match(releaseStatus(f), /Open a release link/);
    const query = releaseQuery("beta");
    for (const invalid of [
      query.replace("environment_id=prod&", ""),
      query + "&channel=beta",
      query + "&%63hannel=beta",
      query.replace("channel=beta", "extra=beta"),
      query.replace("channel=beta", "channel=%FF"),
      query.replace("channel=beta", "channel=%25"),
      query.replace("platform=ios", "platform=web"),
      query.replace("organization_id=org", "organization_id=*"),
      query.replace("a".repeat(64), "A".repeat(64)),
      query.replace("a".repeat(64), "a".repeat(64) + "%0A"),
      query + "&",
    ]) {
      go(f, "/releases?" + invalid);
      await flush();
      assert.equal(releaseStatus(f), "This release link does not specify a valid target.", invalid);
    }
    assert.equal(releaseCalls(f).length, 0);
  } finally { f.close(); }
});

test("Releases drops delayed HTTP replies after URL and console-session changes", { timeout: 5000 }, async () => {
  const f = fixture(undefined, releaseRoute("beta"));
  try {
    await admitReleaseSession(f);
    const [staleTarget] = releaseCalls(f);
    go(f, releaseRoute("stable"));
    await flush();
    const [, stable] = releaseCalls(f);
    assert.equal(stable.path, releaseEndpoint("stable"));
    assert.equal(staleTarget.signal.aborted, true);
    stable.resolve(json({ kind: "empty", target: { ...releaseTarget, channel: "stable" } }));
    await flush();
    staleTarget.resolve(publish("beta"));
    await flush();
    assert.equal(releaseStatus(f), "No release has been published to this target.");
    assert.doesNotMatch(f.text(), /committed-release|18446744073709551615/);

    go(f, releaseRoute("beta"));
    await flush();
    const [, , staleSession] = releaseCalls(f);
    f.controller.revalidate();
    assert.equal(staleSession.signal.aborted, true);
    assert.equal(releaseStatus(f), "Console session unavailable.");
    staleSession.resolve(publish("beta"));
    f.calls.at(-1).resolve(json({ state: "unauthenticated", csrf_token: "A".repeat(43) }));
    await flush();
    assert.equal(releaseStatus(f), "Sign in to view this release.");
    assert.doesNotMatch(f.text(), /committed-release|18446744073709551615/);
    assert.equal(releaseCalls(f).length, 3);
  } finally { f.close(); }
});

test("Releases aborts on live workspace selection changes and when left", { timeout: 5000 }, async () => {
  const f = fixture();
  try {
    await admitReleaseSession(f);
    (await f.request("/console-api/v1/orgs")).resolve(json({
      organizations: [{ id: "org", display_name: "Test studio", organization_roles: ["owner"] }], next_cursor: null,
    }));
    await flush();
    f.click("Test studio");
    (await f.request("/console-api/v1/projects?organization_id=org")).resolve(json({
      projects: [
        { organization_id: "org", id: "p", display_name: "Test project", roles: ["viewer"] },
        { organization_id: "org", id: "q", display_name: "Other project", roles: ["viewer"] },
      ], next_cursor: null,
    }));
    await flush();
    f.click("Test project");
    go(f, releaseRoute("beta"));
    const old = await f.request(releaseEndpoint("beta"));
    f.selectProject({ organizationId: "org", projectId: "q" });
    assert.equal(old.signal.aborted, true);
    old.resolve(publish("beta"));
    await flush();
    assert.equal(releaseStatus(f), "This release target is outside your selected workspace.");
    assert.equal(releaseCalls(f).length, 1);
    assert.doesNotMatch(f.text(), /committed-release/);

    f.selectProject({ organizationId: "org", projectId: "p" });
    const current = await f.request(releaseEndpoint("beta"));
    go(f, "/workspace");
    await flush();
    assert.equal(current.signal.aborted, true);
  } finally { f.close(); }
});

test("Releases handles access denials, unavailable responses, and invalid successful bodies without disclosure", { timeout: 5000 }, async () => {
  const f = fixture(undefined, "/releases");
  try {
    await admitReleaseSession(f);
    const privateText = "private-response-sentinel";
    const cases = [
      [new Response(privateText, { status: 403 }), "You cannot access this release target."],
      [new Response(privateText, { status: 404 }), "You cannot access this release target."],
      [new Response(privateText, { status: 503 }), "Release head unavailable."],
      [json({ kind: "empty", target: releaseTarget, release: publishedRelease }), "Release head unavailable."],
      [new Response('{"kind":"published","kind":"empty","target":' + JSON.stringify(releaseTarget) + '}', {
        headers: { "content-type": "application/json" },
      }), "Release head unavailable."],
      [json({ kind: "empty", target: { ...releaseTarget, channel: "other" } }), "Release head unavailable."],
      [json({ kind: "published", target: releaseTarget, release: { ...publishedRelease, signature: privateText } }), "Release head unavailable."],
    ];
    for (const sequence of [5, "0", "01", "+1", "1\n", "18446744073709551616"]) {
      cases.push([publish("beta", { ...publishedRelease, sequence }), "Release head unavailable."]);
    }
    const { details, ...summary } = publishedRelease;
    cases.push([publish("beta", summary), "Release head unavailable."]);
    for (const invalid of [
      { sourceCommit: "f".repeat(39) }, { sourceCommit: "F".repeat(40) },
      { payloadBytes: 0 }, { payloadBytes: 4_194_305 }, { payloadBytes: 1.5 }, { payloadBytes: "61" },
      { artifactKeyId: "artifact with spaces" }, { assignmentKeyId: "" }, { action: "delete" },
      { payload: privateText }, { capabilities: [{ id: "network.http.v1", permissions: ["storage.appPrivate"] }] },
      { capabilities: [{ id: "custom.v1", permissions: [] }] },
      { capabilities: [{ id: "network.http.v1", permissions: [], origins: [privateText] }] },
      { capabilities: [details.capabilities[0], details.capabilities[0]] },
      { capabilities: details.capabilities.toReversed() },
    ]) {
      cases.push([publish("beta", { ...publishedRelease, details: { ...details, ...invalid } }), "Release head unavailable."]);
    }
    for (const [index, [response, expected]] of cases.entries()) {
      go(f, releaseRoute("beta"));
      await flush();
      releaseCalls(f)[index].resolve(response);
      await flush();
      assert.equal(releaseStatus(f), expected);
      assert.doesNotMatch(f.text(), /private-response-sentinel|committed-release/);
      go(f, "/releases");
      await flush();
    }
    go(f, releaseRoute("beta"));
    await flush();
    releaseCalls(f).at(-1).resolve(new Response(privateText, { status: 401 }));
    await flush();
    assert.equal(f.controller.getSession().kind, "unavailable");
    assert.equal(releaseStatus(f), "Console session unavailable.");
    assert.doesNotMatch(f.text(), /private-response-sentinel/);
  } finally { f.close(); }
});
