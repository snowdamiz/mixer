import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const here=import.meta.dirname;
const bindings=JSON.parse(await readFile(join(here,'bindings.json'),'utf8'));
const {createHarness,cleanupReceipts}=await import(pathToFileURL(join(bindings.scratch,'hosted-worker-controller/test/acceptance-driver.mjs')));
const packet=JSON.parse(await readFile(join(bindings.scratch,'verification/hosted-worker-controller-contract/vectors.json'),'utf8'));
const r=structuredClone(packet.cases[0].request);r.command='ensure_started';
let h;const evidence=[];let error=null;
try{
  h=await createHarness({fixture:r,nowUs:'1900000000000000',errorUs:'1',clockQualified:true});
  await h.control('hold',{value:true});const start=performance.now();
  const launched=await h.command(r);assert.equal(launched.body.observation.code,'uncertain');assert(performance.now()-start>=1800);
  const stopped=structuredClone(r);stopped.command='stop';stopped.guard.epoch='2';stopped.guard.owner_id='successor';
  await h.command(stopped);await h.reconcile();await h.reconcile();
  const beforeRelease=await h.raw();assert.equal(h.calls().length,1);assert.equal(beforeRelease.row.desired,'stop');assert.equal(beforeRelease.row.terminal_json,null);
  evidence.push({phase:'timed-out-but-noncooperative-call-pending',calls:h.calls(),desired:beforeRelease.row.desired,terminal:beforeRelease.row.terminal_json});
  await h.control('release',{});await h.reconcile();
  assert.equal(h.calls().filter(c=>c.kind==='launch').length,1);assert.equal(h.calls().filter(c=>c.kind==='stop').length,1);
  await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});await h.reconcile();
  assert.equal((await h.snapshot()).terminal.status,'stopped');evidence.push({phase:'after-owned-completion-and-drain',calls:h.calls(),snapshot:await h.snapshot()});
}catch(e){error={name:e.name,message:e.message,stack:e.stack};process.exitCode=1;}
finally{await h?.close();}
const report={status:error?'failed':'passed',scope:'local-workerd-SQLite-with-independent-noncooperative-synthetic-provider',frozen_source_tree_sha256:bindings.source_tree_sha256,evidence,error,cleanup:cleanupReceipts};
await writeFile(join(here,'noncooperative-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
