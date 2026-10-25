import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {harness,cleanup} from './harness.mjs';
const root=resolve(import.meta.dirname,'../../../..');
const base=JSON.parse(await readFile(resolve(root,'verification/hosted-worker-controller-contract/vectors.json'),'utf8')).cases[0].request;
const sha=s=>createHash('sha256').update(s).digest('hex');
const fixed={namespaceGeneration:'a'.repeat(64),environmentId:base.environment_id,poolId:base.pool_id,controllerId:base.controller_id,platform:base.ref.platform,operationKey:sha(JSON.stringify(['mixer-worker-controller-do-v1',base.environment_id,base.pool_id,base.controller_id,base.operation_id])),operationId:base.operation_id,immutableSha256:base.immutable_sha256};
const result={id:'restored-terminal-outbox-phase-must-match-permanent-row',expected:'fail closed before terminal RPC; registry remains pending; local outbox retained'},h=await harness(base,fixed);
try{
 const registration=await h.call('register');h.receipt=registration.receipt;await h.call('drain',{value:true});await h.call('registry',{command:'mode',mode:'drop_before_once',skip:2});
 await h.call('command',{request:{...base,command:'stop'},receipt:h.receipt});const before=await h.call('raw');assert.equal(before.row.phase,'stopped');assert.equal(JSON.parse(before.row.terminal_json).status,'stopped');assert.equal((await h.call('registry',{command:'raw'})).records[0].pending,1);
 await h.call('reviewMutation',{field:'outboxPhase'});const restored=await h.call('raw');assert.equal(JSON.parse(restored.row.track_outbox_json).terminal.phase,'completed');
 const flush=await h.call('flush'),after=await h.call('raw'),rec=(await h.call('registry',{command:'raw'})).records[0];
 Object.assign(result,{before,restored,flush,after,registry:rec,projection:JSON.parse(rec.projection_json)});
 assert.deepEqual(flush,{flushed:false});assert.equal(rec.pending,1);assert.ok(after.row.track_outbox_json);result.status='passed';
}catch(e){result.status='failed';result.error=e.stack??String(e);}finally{await h.close();}
await writeFile(resolve(import.meta.dirname,'../../snapshot-consistency-report.json'),JSON.stringify({schema:1,status:result.status,results:[result],cleanup},null,2)+'\n');
console.log(JSON.stringify({id:result.id,status:result.status,flush:result.flush,projection:result.projection,localTerminal:result.after?.row.terminal_json,outboxAfter:result.after?.row.track_outbox_json}));if(result.status!=='passed')process.exitCode=1;
