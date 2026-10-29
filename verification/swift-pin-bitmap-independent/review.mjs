import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import path from 'node:path';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../..'),packet=path.join(root,'verification/swift-dense512-product-integration');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const sealBytes=await fs.readFile(path.join(packet,'seal.json'));
assert.equal(sha(sealBytes),'290909956b188ed46c73c2c73541c8ed60a80788f0d51f9adbca0940579a54f2');
const seal=JSON.parse(sealBytes),m=JSON.parse(await fs.readFile(path.join(packet,'manifest.json')));
let bindings=0;for(const [p,r]of Object.entries(seal.files)){const b=await fs.readFile(path.join(packet,p));assert.equal(b.length,r.bytes,p);assert.equal(sha(b),r.sha256,p);bindings++;}
for(const [p,r]of Object.entries(m.baselineFiles)){const b=await fs.readFile(path.join(root,'vm',p));assert.equal(b.length,r.bytes,p);assert.equal(sha(b),r.sha256,p);bindings++;}
for(const [p,r]of Object.entries(m.protectedFiles)){const b=await fs.readFile(path.join(root,p));assert.equal(b.length,r.bytes,p);assert.equal(sha(b),r.sha256,p);bindings++;}
const digest=rows=>sha(Object.entries(rows).sort(([a],[b])=>a.localeCompare(b)).map(([p,r])=>p+'\0'+r.sha256+'\n').join(''));
// Manifest names are ASCII; byte-order sort used for the producer's closure.
const closure=rows=>sha(Object.keys(rows).sort().map(p=>p+'\0'+rows[p].sha256+'\n').join(''));
assert.equal(closure(m.baselineFiles),'af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b');
assert.equal(closure(m.candidateFiles),'4f9968797133b17520e5387e8ea9870bad779159968357cd31c50abbeb8c8bbd');
const b=await fs.readFile(path.join(packet,'candidate/vm/src/experimental/cache/borrowed.rs'),'utf8');
const c=await fs.readFile(path.join(packet,'candidate/vm/src/experimental_swift_reactor/cache.rs'),'utf8');
const between=(s,a,z)=>{const i=s.indexOf(a),j=s.indexOf(z,i+a.length);assert(i>=0&&j>i);return s.slice(i,j);};
const ordered=(s,...xs)=>{let i=-1;for(const x of xs){const j=s.indexOf(x,i+1);assert(j>i,'missing/reordered '+x);i=j;}};
function contracts(b,c){
  const release=between(b,'pub(crate) fn release<','pub(crate) fn pin<');
  ordered(release,'checked_record::<M>','M::validate_pin_release','operation.release_pin()','slot.set_pins(slot.pins() - 1)','parts.pins[pin.slot()] = PinRecord::default()','M::pin_released');
  assert.equal(release.split('M::pin_released').length-1,1);
  const acquisition=between(b,'fn pin_acquired<','\n}\n');
  ordered(acquisition,'meter.check()','M::resident_insert','parts.slots[index].set(entry)','meter.usage_mut().pin(','parts.pins[pin_slot] = PinRecord','M::pin_published','M::Pin::new','*parts.next_nonce = nonce');
  const checked=between(b,'pub(crate) fn checked_record<','pub(crate) fn view<');
  assert(checked.includes('pin.owner() != parts.owner'));assert(checked.includes('r.nonce != 0 && r.nonce == pin.nonce()'));assert(checked.includes('s.pins() == 0 || s.entry().is_none()'));
  const admit=between(c,'    fn available_pin(','    fn pin_published('),end=between(c,'    fn validate_pin_release(','    fn resident_lookup(');
  ordered(admit,'meter.work(3)?','pins.len() > 64','count_ones()','trailing_zeros()','meter.work(2)?','pins.get(slot)','Ok(slot)');
  assert(admit.includes('record.nonce != 0'));assert(end.includes('pins.len() > 64 || slot >= pins.len()'));assert(end.includes('*scratch.free_pins & (1u64 << slot) != 0'));assert(!end.includes('meter.work(')&&!end.includes('.check()'));
  assert(c.includes('64 => u64::MAX,')&&c.includes('_ => 0,'));assert.equal(c.split('(3, size_of::<DensePinInventory>())').length-1,3);
  ordered(c,'self.control.work(1)?;\n        partial.free_pins = dense_allowed_pins(budget.active_pins)');
  assert(c.includes('*scratch.free_pins &= !(1u64 << slot)'));assert(c.includes('*scratch.free_pins |= 1u64 << slot'));
  return 10;
}
const groups=contracts(b,c),mutations=[];
for(const [name,source,from,to]of [
 ['release-before-authority','b','    if let Err(e) = M::validate_pin_release','    M::pin_released(&mut parts.scratch, pin.slot());\n    if let Err(e) = M::validate_pin_release'],
 ['publication-before-record','b','    M::pin_published(&mut parts.scratch, pin_slot);','    // removed publication'],
 ['stale-nonce-admission','b','r.nonce != 0 && r.nonce == pin.nonce()','r.nonce != 0'],
 ['foreign-owner-admission','b','pin.owner() != parts.owner','false'],
 ['release-width-guard','c','pins.len() > 64 || slot >= pins.len()','slot >= pins.len()'],
 ['64th-bit-lost','c','64 => u64::MAX,','64 => u64::MAX >> 1,'],
 ['inventory-missing','c','(3, size_of::<DensePinInventory>())','(0, size_of::<DensePinInventory>())'],
 ['unchecked-work','c','meter.work(2)?','meter.work(0)?']]){
 const original=source==='b'?b:c;assert(original.includes(from));const changed=original.replace(from,to);let killed=false;try{contracts(source==='b'?changed:b,source==='c'?changed:c);}catch{killed=true;}assert(killed,'source mutation survived '+name);mutations.push(name);
}
const model=vm.runInNewContext(await fs.readFile(path.join(here,'independent-model.js'),'utf8'),Object.create(null),{timeout:10000,contextCodeGeneration:{strings:false,wasm:false}});
const result={schema:1,at:new Date().toISOString(),bindings,sourceContractGroups:groups,killedSourceMutations:mutations,model,tool:'node:vm pure JS with filesystem/hash harness; process/network/session/group/signal/wait APIs unavailable to model',toolVersion:typeof process==='object'?process.version:'unavailable in persistent Node REPL',candidateTreeSHA256:m.candidateTreeSHA256,actualRustRuns:0,scope:'independent source review support only; no runtime or release authority'};
await fs.writeFile(path.join(here,'pure-result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
