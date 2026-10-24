from pathlib import Path
import json,shutil,tarfile,sys
from run import SCRATCH,HERE,b
base=SCRATCH/'draft-reconstruction';shutil.copytree(SCRATCH/'candidate/vm',base,dirs_exist_ok=True)
current=(base/'src/experimental_swift_reactor/memory_operations_tests.rs').read_text()
a=current.index(' let mut foreign=owner();fixture(true,Some(BODY)');z=current.index('\n}\n#[test] fn mm08_post_pop_live_fault',a);current=current[:a]+current[z:]
a=current.index('#[test] fn mm09_held_pin_cleanup()');z=current.index('#[test] fn mm10_actual_live_capacity()',a)
current=current[:a]+'''#[test] fn mm09_held_pin_cleanup(){let _b=Bounds::new();
 let mut foreign=owner();install_foreign(&mut foreign);
 fixture(true,None,|p|{p.enter(36).unwrap();p.enter(34).unwrap();let pins=pin_ids(p);push(p,&[Value::I32(-1)]);assert!(op(p,LOAD).is_err());assert_eq!(pin_ids(p),pins);hooks(Hooks{release_mask:7,..Hooks::default()});let report=p.drain();assert_eq!(report.retained_frames,3);assert_eq!(pin_ids(p),pins);assert_eq!(p.phase.parts.cache.usage().active_pins,3);hooks(Hooks::default());let report=p.drain();assert_eq!(report.retained_frames,3);});
 // A failed drain is deliberately not repeated in-place by the accepted owner;
 // fixture completion above retains pins, so retry must be explicit on owner.
 restore_foreign(&mut foreign);retire(foreign);
}
'''+current[z:]
a=current.index('#[test] fn mm13_no_alloc_warm()');z=current.index('#[test] fn mm14_frozen_parity()',a)
current=current[:a]+'''#[test] fn mm13_no_alloc_warm(){let _b=Bounds::new();for case in 0..6{fixture(true,None,|p|{let address=Value::I32(if case==2{-1}else{0});if case%2==0{push(p,&[address]);}else{push(p,&[address,Value::I32(9)]);}if case==4{let now=observed(p).execution_work;p.phase.operation.control.test_replace_execution_work_limit(now);}if case==5{p.phase.operation.control.cancellation().cancel();}let ((outer,slot),stats)=measure_extended(Some(0),||{let mut s=None;let r=p.memory_operation(if case%2==0{LOAD}else{STORE},&mut s);(r,s)});assert_eq!(stats.attempts,0);assert_eq!(stats.injected_failures,0);outer.unwrap();assert_eq!(slot.unwrap().is_ok(),case<2||case==3);});}}
'''+current[z:]
a=current.index('#[test] fn mm14_frozen_parity()');z=current.index('#[test] fn mm15_deferred_fail_closed()',a)
current=current[:a]+'''#[test] fn mm14_frozen_parity(){let _b=Bounds::new();assert_eq!(width(0x28),4);assert_eq!(width(0x39),8);assert_eq!(crate::experimental_swift_reactor::control::MAX_RESERVATION_TICKETS,86);println!("MM_EXTERNAL frozen39 expansion and executed baseline/candidate integration parity are separately bound by run suite");}
'''+current[z:]
current=current.replace('});\n\n}\n#[test] fn mm08_post_pop_live_fault','});\n}\n#[test] fn mm08_post_pop_live_fault')
p=base/'src/experimental_swift_reactor/frame_operations_tests.rs';p.write_text(p.read_text().replace('Some(ACTIVE_BYTES + 119576 + control_operations::ACTIVE_BYTES + memory_operations::ACTIVE_BYTES)','Some(ACTIVE_BYTES + 119576 + control_operations::ACTIVE_BYTES)'))
with tarfile.open(HERE.parent/'swift-memory-helper-contract/candidate-source.tar.gz')as t:original=t.extractfile('vm/src/experimental_swift_reactor/memory_operations.rs').read().decode()
p=base/'src/experimental_swift_reactor/memory_operations.rs';p.write_text(p.read_text().split('// ACCOUNTING_START')[0]+'// ACCOUNTING_START'+original.split('// ACCOUNTING_START',1)[1])
results=[]
for name in ['draft-test2','draft-test']:
 text=current
 if name=='draft-test':
  text=text.replace("fn pinned<'a>(p: &mut FrameOperationPhase<'a>, s: &mut FrameOperationStorage<'a>)", "fn pinned(p: &mut FrameOperationPhase<'_>, s: &mut FrameOperationStorage<'_>)")
  text=text.replace('let address=Value::I32(if case==2{-1}else{0});if case%2==0{push(p,&[address]);}else{push(p,&[address,Value::I32(9)]);}', 'push(p,if case%2==0{&[Value::I32(if case==2{-1}else{0})]}else{&[Value::I32(0),Value::I32(9)]});')
 (base/'src/experimental_swift_reactor/memory_operations_tests.rs').write_text(text)
 expected=json.loads((HERE/'commands'/name/'source-manifest.json').read_text());actual=b.manifest(base);mismatch=[n for n in set(actual)|set(expected)if actual.get(n)!=expected.get(n)];print(name,mismatch,flush=True)
 if not mismatch:
  dest=HERE/'historical-failed-sources';dest.mkdir(exist_ok=True)
  with tarfile.open(dest/(name+'-source.tar.gz'),'w:gz')as t:
   for n in actual:t.add(base/n,arcname='vm/'+n,recursive=False)
 results.append(dict(command=name,exactSourceReconstructed=not mismatch,sourceClosure=b.digest(actual),expectedSourceClosure=b.digest(expected),mismatches=mismatch))
(HERE/'historical-failed-source-reconstruction.json').write_bytes(b.enc(results))
