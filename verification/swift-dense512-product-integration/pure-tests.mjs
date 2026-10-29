import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
export async function run(repo=path.resolve(here,'../..')) {
  const manifest=JSON.parse(await fs.readFile(path.join(here,'manifest.json'),'utf8'));
  let bindings=0;
  for(const [name,row] of Object.entries(manifest.baselineFiles)) {
    const data=await fs.readFile(path.join(repo,'vm',name));
    assert.equal(data.length,row.bytes,name);assert.equal(sha(data),row.sha256,name);bindings++;
  }
  for(const [name,row] of Object.entries(manifest.protectedFiles)) {
    const data=await fs.readFile(path.join(repo,name));assert.equal(data.length,row.bytes,name);assert.equal(sha(data),row.sha256,name);bindings++;
  }
  const source={};
  for(const name of manifest.overlayPaths) {
    const data=await fs.readFile(path.join(here,'candidate/vm',name));source[name]=data.toString();
    assert.equal(data.length,manifest.candidateFiles[name].bytes,name);assert.equal(sha(data),manifest.candidateFiles[name].sha256,name);bindings++;
  }
  assert.deepEqual(manifest.overlayPaths,['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']);
  const cache=source['src/experimental_swift_reactor/cache.rs'], borrowed=source['src/experimental/cache/borrowed.rs'];
  const validate=(cache,borrowed)=>{
    assert.equal((cache.match(/\(3, size_of::<DensePinInventory>\(\)\),/g)||[]).length,3,'three admitted lifetime inventories');
    assert.equal((cache.match(/pins\.len\(\) > 64 \|\|/g)||[]).length,2,'admission and release limits are 64');
    assert(cache.includes('const RESIDENT_LINKS: usize = 64;'));
    assert(cache.includes('index: Vec<u8>,'),'canonical resident representation');
    assert(cache.includes('self.control.work(1)?;\n        partial.free_pins = dense_allowed_pins(budget.active_pins);'),'precharged initialization');
    assert(borrowed.indexOf('M::validate_pin_release(')<borrowed.indexOf('if let Err(e) = operation.release_pin()'),'validate before release effects');
    assert(borrowed.indexOf('parts.pins[pin.slot()] = PinRecord::default();')<borrowed.indexOf('M::pin_released('),'record before release bit');
    const publishing=borrowed.indexOf('M::pin_published(');
    assert(publishing>borrowed.indexOf('parts.pins[pin_slot] = PinRecord'),'record before publication bit');
    assert(publishing<borrowed.indexOf('let pin = M::Pin::new'),'bit before token exposure');
  };
  validate(cache,borrowed);
  let killedMutations=0;
  for(const [c,b] of [
    [cache.replace('pins.len() > 64 ||','pins.len() > 128 ||'),borrowed],
    [cache.replace('(3, size_of::<DensePinInventory>()),',''),borrowed],
    [cache,borrowed.replace('    M::pin_published(&mut parts.scratch, pin_slot);','')],
  ]) {assert.throws(()=>validate(c,b));killedMutations++;}
  const reviewed=await fs.readFile(path.join(repo,'verification/swift-execution-architecture-correction/dense-mode.rs'),'utf8');
  assert(cache.includes(reviewed.slice(0,reviewed.indexOf('    fn resident_lookup('))),'reviewed 64-pin methods exact');
  const hooks=await fs.readFile(path.join(repo,'verification/swift-execution-architecture-correction/pin-hooks.rs'),'utf8');
  assert(borrowed.includes(hooks),'Frozen defaults exact');
  const modelSource=await fs.readFile(path.join(here,'pin-model.js'),'utf8');
  const model=new vm.Script(modelSource,{filename:'pin-model.js'}).runInNewContext(Object.create(null),{timeout:20000,contextCodeGeneration:{strings:false,wasm:false}});
  return {schema:1,status:'passed',bindingFiles:bindings,sourceContractGroups:10,killedMutations,model,
    baselineTreeSHA256:manifest.baselineTreeSHA256,candidateTreeSHA256:manifest.candidateTreeSHA256,
    realProcessesSignalsGroupsWaitsSockets:0,compilations:0,runtimeRuns:0,localNativeUICaptureRuns:0,
    scope:'source integrity and finite independent model only; actual Rust host tests remain pending'};
}
