#!/usr/bin/env python3
import collect as c
from pathlib import Path
import shutil
p=c.HERE;vm=c.source('candidate');c.archive('historical-second-runtime',vm)
for n in['inventory-schema.json','function-manifest.json','closure-captures.json','positive-positions.rs','candidate.patch','changed-files.json','frozen-identity.json','actual-closure-layouts.json','negative-borrows.json']:
 if(p/n).exists():shutil.copy2(p/n,p/('historical-second-'+n))
f=vm/'src/experimental_swift_reactor/frame_operations.rs';t=f.read_text();needle='let old = super::tests::before_result_push(self.phase.operation.control);';assert t.count(needle)==1;t=t.replace(needle,needle+'\n            host_tests::before_push(self);');f.write_text(t)
f=vm/'src/experimental_swift_reactor/host_operation_tests.rs';t=f.read_text();needle='fn storage<';at=t.index(needle);t=t[:at]+'''pub(super) fn before_push(p: &mut FrameOperationPhase<'_>) {
    match BEFORE.with(Cell::get) {
        3 => p.phase.operation.control.cancellation().cancel(),
        4 => p.phase.parts.frames.last_mut().unwrap().operands = usize::MAX,
        _ => {}
    }
}
'''+t[at:]
t=t.replace('for fault in [1, 2, 4, 7] {','for fault in [1, 2, 3, 4, 7] {')
t=t.replace('push_fault: fault,','push_fault: if fault == 7 || fault == 3 { 0 } else { fault },')
needle='''            let mut s = None;
            p.host_operation(6, &mut s).unwrap();
            assert!(s.unwrap().is_err());'''
replacement='''            let original_floor = p.phase.parts.frames[0].operands;
            if fault == 7 { BEFORE.with(|x| x.set(3)); }
            if fault == 3 { BEFORE.with(|x| x.set(4)); }
            let mut s = None;
            p.host_operation(6, &mut s).unwrap();
            let failure = s.unwrap().unwrap_err();
            assert_eq!(failure.kind, match fault { 1 => SwiftRunFailureKind::WorkExhausted, 2 | 4 => SwiftRunFailureKind::ValueLimit, 7 => SwiftRunFailureKind::Cancelled, _ => SwiftRunFailureKind::Invariant });
            p.phase.parts.frames[0].operands = original_floor;'''
assert t.count(needle)==1;t=t.replace(needle,replacement);f.write_text(t);(p/'tests.rs').write_text(t)
c.archive('third-runtime-draft',vm)
for label in['baseline','candidate']:(c.scratch()/('metadata-'+label)).rename(c.scratch()/('historical-second-accounted-metadata-'+label))
