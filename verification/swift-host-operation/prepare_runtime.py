#!/usr/bin/env python3
from pathlib import Path
import collect as c
import shutil
s=c.scratch();p=s/'candidate';p.rename(s/'rebased-uncalled-candidate');shutil.copytree(s/'baseline',p)
code=(c.HERE/'operation.rs').read_text()
code=code.replace('let errno = {','#[cfg(test)] host_tests::before_dispatch(self);\n        let errno = {')
code=code.replace('if let Err(failure) = self.phase.operation.control.remove_live_with_wasi(', '#[cfg(test)] host_tests::before_remove(self,params);\n        if let Err(failure) = self.phase.operation.control.remove_live_with_wasi(')
code=code.replace('let pc = match current_pc.checked_add(1)', '#[cfg(test)] let current_pc = if host_tests::PC_OVERFLOW.with(std::cell::Cell::get) { usize::MAX } else { current_pc };\n    let pc = match current_pc.checked_add(1)')
code=code.replace('// CONTRACT_INVENTORY_INSERT','// CONTRACT_INVENTORY_INSERT\n#[cfg(test)] mod host_tests { include!("host_operation_tests.rs"); }')
f=p/'src/experimental_swift_reactor/frame_operations.rs';f.write_text(f.read_text()+'\nmod host_runtime_import {\n'+code+'\n}\n')
shutil.copy2(c.HERE/'tests.rs',p/'src/experimental_swift_reactor/host_operation_tests.rs')
f=p/'src/experimental_swift_reactor/control_operations_tests.rs';f.write_text(f.read_text()+'''\npub(in crate::experimental_swift_reactor::execution::frame_operations) fn host_test_bytes(body:&[u8],result:bool,locals:&[Type])->Vec<u8>{body_fixture(body,result,locals)}\n''')
f=p/'src/experimental_swift_reactor/control.rs';f.write_text(f.read_text()+'''\n#[cfg(test)] impl RuntimeControl {pub(crate) fn host_test_counter(&mut self,value:u64){self.host_calls=value;}}\n''')
f=p/'src/experimental_wasi/accounted.rs';f.write_text(f.read_text()+'''\n#[cfg(test)] impl AccountedWasi {
 pub(crate) fn host_test_header(&mut self,next:Option<ReservationTicket>)->Option<ReservationTicket>{std::mem::replace(&mut self.header,next)}
 pub(crate) fn host_test_dispatch(&mut self,before:bool,after:bool){self.test.cancel_before=before;self.test.cancel_after=after;}
 pub(crate) fn host_test_cancel_at(&mut self,at:usize){self.context.test.host_set_cancel(at);}
 pub(crate) fn host_test_service(&mut self,kind:u8){self.context.test.host_set_service(kind);}
 pub(crate) fn host_test_services(&self)->usize{self.context.test.host_services()}
}\n''')
f=p/'src/experimental_wasi/tests.rs';text=f.read_text().replace('    ExpireClock,','    ExpireClock,\n    SlowRealClock,\n    CancelRealClock,')
text=text.replace('            Service::ClockError => Err(Errno::Io),','''            Service::SlowRealClock => {let result=platform::clock(clock,resolution);std::thread::sleep(Duration::from_millis(600));result},
            Service::CancelRealClock => {let result=platform::clock(clock,resolution);cancellation.cancel();result},
            Service::ClockError => Err(Errno::Io),''')
text+='''\nimpl TestState {
 pub(super) fn host_set_cancel(&self,at:usize){self.cancel_at.set(Some(at));}
 pub(super) fn host_set_service(&mut self,kind:u8){self.service=match kind{1=>Service::PartialRandomError,5=>Service::CancelRandom,8=>Service::SlowRealClock,9=>Service::CancelRealClock,_=>Service::Os};}
 pub(super) fn host_services(&self)->usize{self.services.get()}
}\n''';f.write_text(text)
# Inventory is regenerated before fixed classes/bounds are authored.
c.save('runtime-draft-source-closure.json',dict(sourceTreeSHA256=c.archive('runtime-draft',p)))
print('Runtime draft saved; not executed')
