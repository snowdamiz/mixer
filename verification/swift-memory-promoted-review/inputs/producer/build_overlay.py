#!/usr/bin/env python3
"""Build a private source overlay only, from accepted control closure121."""
from pathlib import Path
import hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
BASE_DIGEST='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(vm):
 paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for d in ['src','tests','include']:paths += sorted(p for p in (vm/d).rglob('*') if p.is_file())
 return {str(p.relative_to(vm)):sha(p) for p in paths}
def digest(m):return hashlib.sha256(enc(m)).hexdigest()
def method(s,name):
 a=s.index('fn '+name+'(');b=s.index('{',a);i=b+1;n=1
 while n:n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
def build(vm):
 owner=vm/'src/experimental/execution/mod.rs';o=owner.read_text();b=vm/'src/experimental/execution/borrowed.rs';s=b.read_text()
 rangebody=method(o,'range');load=method(o,'load');store=method(o,'store')
 for name,body in [('range',rangebody),('load',load),('store',store)]:
  replacement='borrowed::shared_memory_methods!(self, ExecutionFailure, frozen_memory_leaf, (), range, load, store);' if name=='range' else ''
  o=o.replace(body,replacement)
 # Lift only the exact existing method bodies; Frozen expansion must reproduce.
 shared='\n#[allow(unused_macros)]\nmacro_rules! shared_memory_methods {\n    ($this:ident, $failure:ty, $leaf:ident, ($($mutable:tt)*), $range:ident, $load:ident, $store:ident) => {\n'
 for name,body in [('range',rangebody),('load',load),('store',store)]:
  body=body.replace('fn '+name+'(', 'fn $'+name+'(').replace('ExecutionFailure','$failure')
  if name=='range':body=body.replace('&self','&$($mutable)* $this')
  else:body=body.replace('&mut self','&mut $this')
  body=body.replace('self.range(', '$this.$range(')
  for old,new in [('self.pop32()','$leaf!(pop32 $this)'),('self.pop()','$leaf!(pop $this)'),('self.push(value)','$leaf!(push $this, value)'),('self.memory','$leaf!(memory $this)'),('self.invariant()','$leaf!(invariant $this)'),('self.trap("memory_out_of_bounds")','$leaf!(trap $this)')]:body=body.replace(old,new)
  body=re.sub(r'\bself\b','$this',body)
  shared+=body+'\n'
 shared+='    };\n}\n#[allow(unused_imports)]\npub(crate) use shared_memory_methods;\n'
 leaf='''
#[allow(unused_macros)]
macro_rules! frozen_memory_leaf {
 (pop $s:ident) => { $s.pop() };
 (pop32 $s:ident) => { $s.pop32() };
 (push $s:ident, $v:expr) => { $s.push($v) };
 (memory $s:ident) => { $s.memory };
 (invariant $s:ident) => { $s.invariant() };
 (trap $s:ident) => { $s.trap("memory_out_of_bounds") };
}
#[allow(unused_imports)]
pub(super) use frozen_memory_leaf;
'''
 s+=shared+leaf;b.write_text(s)
 o=o.replace('use borrowed::{control_record, frozen_control_leaf, shared_control_methods};','use borrowed::{control_record, frozen_control_leaf, shared_control_methods, frozen_memory_leaf};')
 o=o.replace("fn width(op: u8) -> usize {", "pub(crate) fn width(op: u8) -> usize {")
 owner.write_text(o)
 f=vm/'src/experimental_swift_reactor/frame_operations.rs';t=f.read_text()
 t=t.replace('// ACCOUNTING_GENERATED_START','#[path = "memory_operations.rs"]\npub(super) mod memory_operations;\n// ACCOUNTING_GENERATED_START',1)
 t=t.replace('Some(bytes) => bytes.checked_add(control_operations::ACTIVE_BYTES),','Some(bytes) => match bytes.checked_add(control_operations::ACTIVE_BYTES) { Some(bytes) => bytes.checked_add(memory_operations::ACTIVE_BYTES), None => None },')
 f.write_text(t)
 e=vm/'src/experimental_swift_reactor/execution.rs';t=e.read_text();t=t.replace('Some(header) => header.checked_add(frame_operations::control_operations::PERMANENT_BYTES), None => None,','Some(header) => match header.checked_add(frame_operations::control_operations::PERMANENT_BYTES) { Some(header) => header.checked_add(frame_operations::memory_operations::PERMANENT_BYTES), None => None }, None => None,');e.write_text(t)
 (vm/'src/experimental_swift_reactor/memory_operations.rs').write_text((HERE/'proposal.rs').read_text())
 return manifest(vm)
