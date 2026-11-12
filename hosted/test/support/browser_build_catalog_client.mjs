import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createCookieBuildCatalogClient} from './api/cookie-build-catalog-client.js';
import {createCookieBuildClient} from './api/cookie-build-client.js';
import {summarizeBuildOverview} from './domain/build-overview.js';

const fixture=JSON.parse(await readFile(process.argv[2],'utf8'));
const base=new URL(fixture.url);
assert.equal(base.hostname,'127.0.0.1');
assert.equal(base.protocol,'http:');
assert.match(fixture.cookie,/^[A-Za-z0-9_-]+$/u);
assert(['queued','terminal'].includes(fixture.phase));
const traces=[];
let activeCookie=fixture.cookie;
const transport=async(path,init)=>{
  const url=new URL(path,base);
  assert.equal(url.origin,base.origin);
  assert.equal(init.credentials,'same-origin');
  assert.equal(init.method,'GET');
  assert.equal(init.cache,'no-store');
  assert.equal(init.redirect,'error');
  const headers=new Headers(init.headers);
  assert(!headers.has('authorization'));
  if(activeCookie!==null) headers.set('cookie','__Host-mixer-session='+activeCookie);
  headers.set('origin',fixture.publicOrigin);
  const response=await fetch(url,{...init,headers});
  const wire=await response.clone().json();
  traces.push({path,query:[...url.searchParams.entries()],status:response.status,wire,
    cookieOnly:activeCookie!==null,requestId:response.headers.get('x-request-id'),
    cacheControl:response.headers.get('cache-control')});
  if(response.status===200){
    assert.equal(response.headers.get('cache-control'),'no-store');
    assert.match(response.headers.get('x-request-id'),/^[0-9a-f]{32}$/u);
  }
  return response;
};
const catalog=createCookieBuildCatalogClient({fetch:transport,timeoutMs:30000});
const detail=createCookieBuildClient({fetch:transport,timeoutMs:30000});
const applications=await catalog.applications(fixture.project,{});
assert.equal(applications.applications.length,2);
const pages=[];
for(const row of applications.applications){
  const scope={organizationId:applications.organizationId,projectId:applications.projectId,applicationId:row.applicationId};
  pages.push(await catalog.builds(scope,{}));
}
const empty=pages.filter(page=>page.builds.length===0);
const populated=pages.filter(page=>page.builds.length>0);
assert.equal(empty.length,1);
assert.equal(populated.length,1);
assert.equal(empty[0].nextCursor,null);
assert.equal(populated[0].builds.length,1);
const row=populated[0].builds[0];
assert.equal(Object.keys(row.selection).length,8);
assert(Object.isFrozen(row.selection));
let selection=row.selection;
if(fixture.phase==='terminal'){
  const queued=JSON.parse(await readFile(fixture.previous,'utf8'));
  assert.equal(queued.status,'PASS');
  assert.deepEqual(row.selection,queued.selection);
  selection=queued.selection;
}
const before=traces.length;
const result=await detail.read(selection);
assert.equal(traces.length,before+1);
const actual=traces.at(-1);
assert.equal(new URL(actual.path,base).pathname,'/console-api/v1/builds');
const fields=[['organizationId','organization_id'],['projectId','project_id'],['applicationId','application_id'],
  ['buildId','build_id'],['platform','platform'],['sourceSha256','source_sha256'],
  ['toolchainLockSha256','toolchain_lock_sha256'],['buildDefinitionSha256','build_definition_sha256']];
assert.deepEqual(actual.query,fields.map(([camel,snake])=>[snake,selection[camel]]));
assert.equal(actual.query.length,8);
assert.equal(Object.keys(actual.wire.build).length,14);
assert.deepEqual(result,row.snapshot);
const catalogWire=traces.find(trace=>trace.path.startsWith('/console-api/v1/build-catalog?')&&trace.wire.builds?.length===1);
assert.deepEqual(actual.wire.build,catalogWire.wire.builds[0]);
const {organizationId,projectId,applicationId,...target}=selection;
const overview=summarizeBuildOverview({scope:{organizationId,projectId,applicationId},expected:[target],reports:[result.report]});
assert.equal(overview.reportedCount,1);
assert.equal(overview.builds.length,1);
assert.equal(overview.builds[0].target.platform,selection.platform);
assert.equal(overview.builds[0].observation.state,fixture.phase==='queued'?'queued':'failed');
assert.equal(result.revision,fixture.phase==='queued'?0:2);
if(fixture.phase==='terminal')assert.equal(result.report.failureCode,'compiler_error');
let unauthenticated;
if(fixture.phase==='terminal'){
  activeCookie=null;
  await assert.rejects(detail.read(selection),error=>error.code==='unauthenticated');
  assert.equal(traces.at(-1).status,401);
  unauthenticated={status:401,clientCode:'unauthenticated',afterMeaningfulPositive:true};
}
const output={status:'PASS',phase:fixture.phase,applications,emptyApplication:empty[0],selection,
  catalogSnapshot:row.snapshot,detail:result,dto:actual.wire.build,overview,traces,
  unauthenticated,actualHTTP:true,compiledCatalogAndDetail:true,inferredPlatformPairing:false};
await writeFile(fixture.output,JSON.stringify(output,null,2));
console.log(JSON.stringify({status:'PASS',phase:fixture.phase,requests:traces.length,selectionFields:8,dtoFields:14,state:result.report.state,revision:result.revision}));
