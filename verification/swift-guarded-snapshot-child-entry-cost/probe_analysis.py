#!/usr/bin/env python3
"""Analyze existing compile-only IR. This file invokes no compiler or code."""
from pathlib import Path
import hashlib,json,re
D=Path(__file__).resolve().parent
ir=(D/'cancellation-backing-probe.ll').read_text();stdout=(D/'probe.stdout').read_text()
def region(comment):
    at=ir.index(comment);start=ir.index('define ',at);end=ir.index('\n}\n',start)+3
    return ir[start:end]
arcdefault=region('; <alloc::sync::Arc<core::sync::atomic::Atomic<bool>> as core::default::Default>::default')
arcclone=region('; <alloc::sync::Arc<core::sync::atomic::Atomic<bool>> as core::clone::Clone>::clone')
globalclone=region('; <alloc::alloc::Global as core::clone::Clone>::clone')
boxnew=region('; alloc::boxed::box_new_uninit')
allocator=region('; <alloc::alloc::Global>::alloc_impl_runtime')
assert '`alloc::sync::ArcInner<std::sync::atomic::Atomic<bool>>`: 24 bytes, alignment: 8 bytes' in stdout
assert re.search(r'box_new_uninit[^\n]*\(i64 8, i64 24\)',arcdefault)
assert re.search(r'alloc_impl_runtime[^\n]*\(i64 %layout.0, i64 %layout.1, i1 zeroext false\)',boxnew)
assert '__rust_alloc(i64 %layout.1, i64 %layout.0)' in allocator
assert 'atomicrmw add' in arcclone and 'llvm.trap()' in arcclone
assert 'call ' not in globalclone and 'invoke ' not in globalclone
assert not any(v in arcclone for v in ('___rust_alloc','alloc_impl_runtime','box_new_uninit'))
proof=dict(schema=1,requested_default_allocation=dict(bytes=24,alignment=8,count=1),clone_new_allocation_count=0,toolchain='rustc1.99.0 b940084d7 aarch64-apple-darwin opt0/unwind',unit='Qualified requested allocator layout, separate from authored source scalar/call actions.',equivalence='Identical frozen product #[derive(Clone, Default)] pub struct Cancellation(Arc<AtomicBool>); identical standard type and exact compiler binary.',evidence=dict(layout_line=stdout.splitlines()[0],Arc_default=arcdefault,Box_new=boxnew,allocator=allocator,Arc_clone=arcclone,Global_clone=globalclone),limitations=['Standalone production LLVM-IR probe, not whole product146 metadata or runtime receipt.','Native request size/alignment and no-clone-allocation are observed in exact instantiated IR; allocator actual footprint/overhead, hidden retries, kernel work, CPU/RSS/time are excluded.','Allocation failure calls the standard allocation error handler; no recoverability or healthy cleanup evidence is claimed.','The requested24-byte backing remains retained under original/clone owners until their actual destruction; no parent funding or refund follows.'],IR_sha256=hashlib.sha256(ir.encode()).hexdigest(),compiler_or_product_executed_by_analysis=False)
(D/'probe-analysis.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(backing_request=24,alignment=8,clone_new_allocation_count=0,executed=False)))
