#!/usr/bin/env python3
"""Apply the independently authored private overlay only to owned scratch."""
from pathlib import Path
import shutil,json,re
from run import HERE,SCRATCH
VM=SCRATCH/'candidate/vm'
if VM.exists():shutil.rmtree(VM.parent)
shutil.copytree(SCRATCH/'baseline',VM.parent)
def method(text,name):
 start=text.index('fn '+name+'(');at=text.index('{',start)+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[start:at]
p=VM/'src/experimental/execution/mod.rs';text=p.read_text();original=method(text,'grow')
body=original.replace('fn grow(','fn $grow(').replace('&mut self','&mut $this').replace('ExecutionFailure','$failure')
maximum='''self
            .cache
            .spans()
            .execution_memory()
            .ok_or_else(|| self.invariant())?
            .1
            .min(self.cache.spans().limits().memory_pages)'''
body=body.replace(maximum,'$leaf!(maximum $this)')
body=body.replace('''drop(memory);
            self.usage.state_reserved -= bytes;''','$leaf!{rollback $this, memory, bytes}')
body=body.replace('''self.memory = memory;
        self.usage.state_reserved -= old_bytes;
        self.usage.memory_pages = next;''','$leaf!{commit $this, memory, old_bytes, next}')
for old,new in [('self.work(', '$leaf!(work $this, '),('self.pop32()','$leaf!(pop32 $this)'),('self.usage.memory_pages','$leaf!(pages $this)'),('self.push(', '$leaf!(push $this, '),('self.invariant()','$leaf!(invariant $this)'),('self.allocation(bytes)','$leaf!(allocation $this, bytes)'),('self.check()','$leaf!(check $this)'),('self.memory','$leaf!(memory $this)')]:body=body.replace(old,new)
body=body.replace('$leaf!(check $this)?;\n                memory.resize', '$leaf!(zero_check $this, memory)?;\n                memory.resize')
body=body.replace('$leaf!(check $this)?;\n                let end', '$leaf!(copy_check $this, memory)?;\n                let end')
body=body.replace('$leaf!(check $this)\n', '$leaf!(final_check $this, memory)\n')
body=re.sub(r'\bself\b','$this',body)
shared='\n#[allow(unused_macros)]\nmacro_rules! shared_memory_growth {\n($this:ident,$failure:ty,$leaf:ident,$grow:ident)=>{\n'+body+'\n};\n}\n#[allow(unused_imports)]\npub(crate) use shared_memory_growth;\n'
shared+='''
#[allow(unused_macros)]
macro_rules! frozen_growth_leaf {
 (work $s:ident,$amount:expr $(,)?) => {$s.work($amount)};
 (pop32 $s:ident) => {$s.pop32()};
 (pages $s:ident) => {$s.usage.memory_pages};
 (maximum $s:ident) => {$s.cache.spans().execution_memory().ok_or_else(|| $s.invariant())?.1.min($s.cache.spans().limits().memory_pages)};
 (push $s:ident,$value:expr) => {$s.push($value)};
 (invariant $s:ident) => {$s.invariant()};
 (memory $s:ident) => {$s.memory};
 (allocation $s:ident,$bytes:expr) => {$s.allocation($bytes)};
 (check $s:ident) => {$s.check()};
 (zero_check $s:ident,$memory:ident) => {$s.check()};
 (copy_check $s:ident,$memory:ident) => {$s.check()};
 (final_check $s:ident,$memory:ident) => {$s.check()};
 (rollback $s:ident,$memory:ident,$bytes:ident) => {drop($memory);$s.usage.state_reserved -= $bytes;};
 (commit $s:ident,$memory:ident,$old_bytes:ident,$next:ident) => {$s.memory=$memory;$s.usage.state_reserved -= $old_bytes;$s.usage.memory_pages=$next;};
}
#[allow(unused_imports)]
pub(super) use frozen_growth_leaf;
'''
p.write_text(text.replace(original,'borrowed::shared_memory_growth!(self, ExecutionFailure, frozen_growth_leaf, grow);').replace('frozen_bulk_memory_leaf};','frozen_bulk_memory_leaf, frozen_growth_leaf};'))
p=VM/'src/experimental/execution/borrowed.rs';p.write_text(p.read_text()+shared)
p=VM/'src/experimental_swift_reactor/frame_operations.rs';text=p.read_text().replace('// ACCOUNTING_GENERATED_START','#[path="memory_growth_operations.rs"]\npub(super) mod memory_growth_operations;\n// ACCOUNTING_GENERATED_START',1).replace('Some(bytes) => bytes.checked_add(bulk_memory_operations::ACTIVE_BYTES)','Some(bytes) => match bytes.checked_add(bulk_memory_operations::ACTIVE_BYTES) {Some(bytes)=>bytes.checked_add(memory_growth_operations::ACTIVE_BYTES),None=>None}')
p.write_text(text)
p=VM/'src/experimental_swift_reactor/execution.rs';text=p.read_text().replace('Some(header) => header.checked_add(frame_operations::bulk_memory_operations::PERMANENT_BYTES)','Some(header) => match header.checked_add(frame_operations::bulk_memory_operations::PERMANENT_BYTES) {Some(header)=>header.checked_add(frame_operations::memory_growth_operations::PERMANENT_BYTES),None=>None}');p.write_text(text)
probe=(HERE/'borrow-probe.rs').read_text();prepare=probe[probe.index('impl SwiftReactorInstance'):];proposal=(HERE/'proposal.rs').read_text();proposal=proposal.replace('// ACCOUNTING_START',prepare+'\n// ACCOUNTING_START')
(VM/'src/experimental_swift_reactor/memory_growth_operations.rs').write_text(proposal)
if(HERE/'tests.rs').exists():(VM/'src/experimental_swift_reactor/memory_growth_operations_tests.rs').write_text((HERE/'tests.rs').read_text())

# Accepted test-only accounting expectations acquire the fresh positive component.
p=VM/'src/experimental_swift_reactor/frame_operations_tests.rs';s=p.read_text().replace(' + bulk_memory_operations::ACTIVE_BYTES)', ' + bulk_memory_operations::ACTIVE_BYTES + memory_growth_operations::ACTIVE_BYTES)');p.write_text(s)
p=VM/'src/experimental_swift_reactor/memory_operations_tests.rs';s=p.read_text().replace('+super::super::bulk_memory_operations::ACTIVE_BYTES);','+super::super::bulk_memory_operations::ACTIVE_BYTES+super::super::memory_growth_operations::ACTIVE_BYTES);');p.write_text(s)
p=VM/'src/experimental_swift_reactor/bulk_memory_operations_tests.rs';s=p.read_text().replace('+super::super::memory_operations::ACTIVE_BYTES+ACTIVE_BYTES);','+super::super::memory_operations::ACTIVE_BYTES+ACTIVE_BYTES+super::super::memory_growth_operations::ACTIVE_BYTES);');p.write_text(s)
