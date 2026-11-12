import assert from "node:assert/strict";
import test from "node:test";
import { createComputed, createRoot, createSignal } from "solid-js";
import { pathToFileURL } from "node:url";
import { join } from "node:path";
import { compileBuildSelectionTests, isBrowserTestChild, runBrowserTests } from "./helpers/build-selection-compiled.mjs";
const browserChild = isBrowserTestChild(import.meta.url);
const output = browserChild ? process.env.MIXER_BUILD_CATALOG_COMPILED : compileBuildSelectionTests();
if (!browserChild) {
  test("BROWSER_WRAPPER: build-selection-binding", { timeout: 75000 }, async () => {
    await runBrowserTests(import.meta.url, output);
  });
} else {
const {createBuildSelectionBinding}=await import(pathToFileURL(join(output,"state/build-selection-binding.js")));
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const workspace=()=>({organizations:{kind:"ready",input:{organizations:[{id:"org",display_name:null,organization_roles:["owner"]}],next_cursor:null}},projects:{kind:"ready",organizationId:"org",input:{projects:[{id:"p",organization_id:"org",display_name:null,roles:["viewer"]}],next_cursor:null}},selectedOrganizationId:"org",selectedProjectId:"p"});
test("actual Solid owner fences reads/actions before effects and disposes owned requests",async()=>{
 let binding,setSession,setWorkspace,dispose,poke;const calls=[];
 const session={kind:"ready",client:{},buildClients:{catalog:{applications:(scope,page,signal)=>{let resolve;const promise=new Promise(r=>resolve=r);calls.push({scope,page,signal,resolve});return promise;},builds:()=>{throw Error("no selection");}},read:{read:()=>{throw Error("no selection");}}}};
 const observed=[];
 createRoot(stop=>{dispose=stop;const [s,ss]=createSignal(session);setSession=ss;const [w,sw]=createSignal(workspace());setWorkspace=sw;const [tick,st]=createSignal(0);poke=()=>st(v=>v+1);
 createComputed(()=>{tick();s();w();if(binding){observed.push(binding.state().applications.kind);binding.controller.selectApplication("app");}});
 binding=createBuildSelectionBinding(s,w);
 });
 await flush();assert.equal(calls.length,1);calls[0].resolve({organizationId:"org",projectId:"p",applications:[{applicationId:"app"}],nextCursor:null});await flush();assert.equal(binding.state().applications.kind,"ready");
 setWorkspace(workspace());assert.equal(observed.at(-1),"loading");await flush();assert.equal(calls.length,2);assert.equal(binding.state().detail.kind,"unselected");
 setSession({kind:"unavailable"});assert.equal(observed.at(-1),"unavailable");await flush();assert(calls[1].signal.aborted);assert.equal(binding.state().applications.kind,"unavailable");
 dispose();poke();binding.controller.firstApplications();assert.equal(calls.length,2);assert.equal(binding.state().applications.kind,"unavailable");
});
}
