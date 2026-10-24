from pathlib import Path
import json,re
from build_overlay import method
HERE=Path(__file__).resolve().parent
VM=Path(json.loads((HERE/'session.json').read_text())['scratch'])/'candidate/vm'
p=VM/'src/experimental/execution/mod.rs';s=p.read_text();b=VM/'src/experimental/execution/borrowed.rs';t=b.read_text()
shared='\n#[allow(unused_macros)]\nmacro_rules! shared_bulk_memory_methods {\n($this:ident, $failure:ty, $leaf:ident, $bulk:ident, $copy:ident, $fill:ident) => {\n'
for name in ['bulk','copy','fill']:
 body=method(s,name);s=s.replace(body,'borrowed::shared_bulk_memory_methods!(self, ExecutionFailure, frozen_bulk_memory_leaf, bulk, copy, fill);' if name=='bulk' else '')
 body=body.replace('fn '+name+'(', 'fn $'+name+'(').replace('ExecutionFailure','$failure').replace('&mut self','&mut $this')
 for old,new in [('self.pop32()','$leaf!(pop32 $this)'),('self.range(', '$leaf!(range $this, '),('self.bulk(', '$this.$bulk('),('self.check()', '$leaf!(check $this)'),('self.memory','$leaf!(memory $this)'),('self.charge(len.div_ceil(64) as u64, false)','$leaf!(charge $this, len.div_ceil(64) as u64)')]:body=body.replace(old,new)
 body=re.sub(r'\bself\b','$this',body);shared+=body+'\n'
shared+='};\n}\n#[allow(unused_imports)]\npub(crate) use shared_bulk_memory_methods;\n'
shared+='''
#[allow(unused_macros)]
macro_rules! frozen_bulk_memory_leaf {
 (pop32 $s:ident) => {$s.pop32()};
 (range $s:ident, $address:expr, $len:expr) => {$s.range($address,$len)};
 (check $s:ident) => {$s.check()};
 (memory $s:ident) => {$s.memory};
 (charge $s:ident, $credits:expr) => {$s.charge($credits,false)};
 (push $s:ident, $value:expr) => {$s.push($value)};
 (pages $s:ident) => {$s.usage.memory_pages};
}
#[allow(unused_imports)]
pub(super) use frozen_bulk_memory_leaf;
#[allow(unused_macros)]
macro_rules! shared_memory_size {
 ($this:ident, $leaf:ident) => {$leaf!(push $this, Value::I32($leaf!(pages $this) as i32))};
}
#[allow(unused_imports)]
pub(crate) use shared_memory_size;
'''
t+=shared;b.write_text(t)
s=s.replace('frozen_memory_leaf};','frozen_memory_leaf, frozen_bulk_memory_leaf};').replace('const CHUNK: usize = 4096;','pub(crate) const CHUNK: usize = 4096;')
s=s.replace('Operation::MemorySize => self.push(Value::I32(self.usage.memory_pages as i32))?,','Operation::MemorySize => borrowed::shared_memory_size!(self, frozen_bulk_memory_leaf)?,')
p.write_text(s)
p=VM/'src/experimental_swift_reactor/frame_operations.rs';s=p.read_text();s=s.replace('// ACCOUNTING_GENERATED_START','#[path = "bulk_memory_operations.rs"]\npub(super) mod bulk_memory_operations;\n// ACCOUNTING_GENERATED_START',1);s=s.replace('Some(bytes) => bytes.checked_add(memory_operations::ACTIVE_BYTES)','Some(bytes) => match bytes.checked_add(memory_operations::ACTIVE_BYTES) { Some(bytes) => bytes.checked_add(bulk_memory_operations::ACTIVE_BYTES), None => None }');p.write_text(s)
p=VM/'src/experimental_swift_reactor/execution.rs';s=p.read_text().replace('Some(header) => header.checked_add(frame_operations::memory_operations::PERMANENT_BYTES)','Some(header) => match header.checked_add(frame_operations::memory_operations::PERMANENT_BYTES) { Some(header) => header.checked_add(frame_operations::bulk_memory_operations::PERMANENT_BYTES), None => None }');p.write_text(s)
p=VM/'src/experimental_swift_reactor/memory_operations.rs';s=p.read_text()
for name in ['memory_pop_value','memory_pop32','memory_push_value']:s=s.replace('    fn '+name+'(', '    pub(super) fn '+name+'(')
# Shared macro expansion applies visibility only to the range method.
s=s.replace('    crate::experimental::execution::borrowed::shared_memory_methods!(', '    crate::experimental::execution::borrowed::shared_memory_methods!(')
# Range is generated; make the macro support a visibility token without changing either body.
p.write_text(s)
p=VM/'src/experimental/execution/borrowed.rs';s=p.read_text().replace('$range:ident, $load:ident, $store:ident) => {','$range:ident, $load:ident, $store:ident, ($($rangevis:tt)*)) => {').replace('fn $range(','$($rangevis)* fn $range(');p.write_text(s)
p=VM/'src/experimental/execution/mod.rs';s=p.read_text().replace('(), range, load, store);','(), range, load, store, ());');p.write_text(s)
p=VM/'src/experimental_swift_reactor/memory_operations.rs';s=p.read_text().replace('memory_load, memory_store\n','memory_load, memory_store, (pub(super))\n');p.write_text(s)
p=VM/'src/experimental_swift_reactor/memory_operations_tests.rs';s=p.read_text().replace('control_operations::ACTIVE_BYTES+ACTIVE_BYTES);','control_operations::ACTIVE_BYTES+ACTIVE_BYTES+super::super::bulk_memory_operations::ACTIVE_BYTES);');p.write_text(s)
(VM/'src/experimental_swift_reactor/bulk_memory_operations.rs').write_text((HERE/'proposal.rs').read_text())
(VM/'src/experimental_swift_reactor/bulk_memory_operations_tests.rs').write_text((HERE/'tests.rs').read_text())

p=VM/'src/experimental_swift_reactor/frame_operations_tests.rs';s=p.read_text().replace('Some(ACTIVE_BYTES + 119576 + control_operations::ACTIVE_BYTES + memory_operations::ACTIVE_BYTES)', 'Some(ACTIVE_BYTES + 119576 + control_operations::ACTIVE_BYTES + memory_operations::ACTIVE_BYTES + bulk_memory_operations::ACTIVE_BYTES)');p.write_text(s)
