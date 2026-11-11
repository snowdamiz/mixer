import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {pathToFileURL} from "node:url";
const fixture=JSON.parse(await readFile(process.argv[2],"utf8"));
const base=new URL("./",import.meta.url);
const {createCookieBuildClient}=await import(new URL("api/cookie-build-client.js",base));
const {summarizeBuildOverview}=await import(new URL("domain/build-overview.js",base));
const rows=[];
try{
 for(const phase of [fixture.phase]){
  assert(Number.isInteger(fixture.port)&&fixture.port>0&&fixture.port<=65535);
  assert.match(fixture.cookie,/^[A-Za-z0-9_-]+$/);
  const d=fixture.dto;assert.equal(Object.keys(d).length,14);
  const selection=Object.fromEntries(["organizationId","projectId","applicationId","buildId","platform","sourceSha256","toolchainLockSha256","buildDefinitionSha256"].map(k=>[k,d[k]]));
  let requestCount=0;let wire;
  const client=createCookieBuildClient({fetch:async(path,init)=>{
   requestCount++;assert(path.startsWith("/console-api/v1/builds?"));assert.equal(init.credentials,"same-origin");assert.equal(init.method,"GET");assert.equal(init.cache,"no-store");assert.equal(init.redirect,"error");
   const headers=new Headers(init.headers);assert(!headers.has("authorization"));headers.set("cookie","__Host-mixer-session="+fixture.cookie);
   const response=await fetch("http://127.0.0.1:"+fixture.port+path,{...init,headers});
   assert.equal(response.status,200);assert.equal(response.headers.get("cache-control"),"no-store");assert.match(response.headers.get("x-request-id"),/^[0-9a-f]{32}$/);
   wire=await response.clone().json();assert.deepEqual(wire,{build:d});return response;
  }});
  const result=await client.read(selection);assert.equal(requestCount,1);assert.equal(result.revision,d.revision);
  const {revision,failureCode,...report}=d;const expected={...report,...(failureCode===null?{}:{failureCode})};assert.deepEqual(result.report,expected);
  const {organizationId,projectId,applicationId,...target}=selection;
  const display=summarizeBuildOverview({scope:{organizationId,projectId,applicationId},expected:[target],reports:[result.report]});
  assert.equal(display.reportedCount,1);assert.equal(display.builds[0].observation.state,d.state);assert.equal(display.builds[0].observation.attempt,d.attempt);assert.equal(display.builds[0].observation.maxAttempts,d.maxAttempts);
  assert(Object.isFrozen(result)&&Object.isFrozen(result.report));
  assert.equal(d.revision,phase==="queued"?0:2);assert.equal(d.attempt,1);assert.equal(d.maxAttempts,2);assert.equal(d.state,phase==="queued"?"queued":"failed");
  rows.push({phase,dto:d,result,display,actualHTTP:true,cookieOnly:true});

 }
 console.log(JSON.stringify({status:"PASS",rows}));
 console.log("R1134 real PKCE-cookie -> compiled cookie client -> real private GET -> summarizeBuildOverview: queued + terminal PASS");
}catch(e){console.error(e);process.exitCode=1;}
