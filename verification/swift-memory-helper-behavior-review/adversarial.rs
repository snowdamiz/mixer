// Independent test additions. These call original owners and production methods.
#[test]
fn review_all23_final_range_and_offset() {
 let _bound=Bounds::new();
 let widths=[4,8,4,8,1,1,2,2,1,1,2,2,4,4,4,8,4,8,1,2,1,2,4];
 for (index,w) in widths.into_iter().enumerate(){for outside in [false,true]{
  fixture(true,None,|p|{
   let opcode=0x28+index as u8;let store=opcode>=0x36;let end=p.phase.parts.memory.len();
   let start=end-w+usize::from(outside);let offset=13u32;let address=(start-offset as usize) as i32;
   let value=match opcode{0x37|0x3c..=0x3e=>Value::I64(-1),0x38=>Value::F32(u32::MAX),0x39=>Value::F64(u64::MAX),_=>Value::I32(-1)};
   if store{push(p,&[Value::I32(address),value]);}else{push(p,&[Value::I32(address)]);}
   let before=observed(p);let pins=pin_ids(p);let cap=p.phase.parts.memory.capacity();
   let result=op(p,if store{Operation::Store{opcode,offset}}else{Operation::Load{opcode,offset}});
   assert_eq!(result.is_err(),outside);assert_eq!(pin_ids(p),pins);assert_eq!(p.phase.parts.memory.capacity(),cap);
   assert_eq!(observed(p).reservations,before.reservations);
   if outside {assert_eq!(result.unwrap_err().code,"memory_out_of_bounds");assert!(p.phase.parts.values.is_empty());assert_eq!(&p.phase.parts.memory[end-8..],&[0;8]);assert_eq!(observed(p).execution_work-before.execution_work,if store{2}else{1});}
   else if store {assert!(p.phase.parts.values.is_empty());assert!(p.phase.parts.memory[start..].iter().all(|v|*v==255));assert_eq!(observed(p).execution_work-before.execution_work,(2+w) as u64);}
   else {let expected=match opcode{0x29|0x30..=0x35=>Value::I64(0),0x2a=>Value::F32(0),0x2b=>Value::F64(0),_=>Value::I32(0)};assert_eq!(p.phase.parts.values.as_slice(),&[expected]);assert_eq!(observed(p).execution_work-before.execution_work,(2+w) as u64);}
  });
 }}
 println!("REVIEW final-range all23 forms success/trap 46 original owners; explicit independent widths; nonzero offset");
}
#[test]
fn review_all_store_type_denials_preserve_floor() {
 let _bound=Bounds::new();
 for opcode in 0x36..=0x3e{for wrong in [Value::I32(8),Value::I64(8),Value::F32(8),Value::F64(8)]{
  let right=match opcode{0x37|0x3c..=0x3e=>crate::Type::I64,0x38=>crate::Type::F32,0x39=>crate::Type::F64,_=>crate::Type::I32};if wrong.ty()==right{continue}
  fixture(true,None,|p|{
   push(p,&[Value::I64(0x7788),Value::I32(0),wrong]);p.phase.parts.frames[0].operands=1;
   let before=observed(p);let mut slot=None;p.memory_operation(Operation::Store{opcode,offset:0},&mut slot).unwrap();
   assert_eq!(slot.unwrap().unwrap_err().code,"swift_memory_operand_type");assert_eq!(p.phase.parts.values.as_slice(),&[Value::I64(0x7788),Value::I32(0),wrong]);
   assert_eq!(observed(p).execution_work,before.execution_work);assert_eq!(observed(p).reservations,before.reservations);assert_eq!(&p.phase.parts.memory[..8],&[0;8]);
   p.phase.parts.frames[0].operands=0;
  });
 }}
 println!("REVIEW 27 exact store-type denials preserve caller/local floor, values, bytes and work");
}
#[test]
fn review_pinned_success_requires_take_before_next_decode() {
 let _bound=Bounds::new();
 fixture(true,Some(BODY),|p|{
  push(p,&[Value::I32(0)]);p.phase.parts.frames[0].pc=1;let before=observed(p);let mut s=storage();
  pinned(p,&mut s).unwrap();assert_eq!(s.entry.take(),Some(Ok(())));let success=observed(p);
  assert_eq!(success.instructions-before.instructions,1);assert_eq!(success.instruction_fuel-before.instruction_fuel,1);assert_eq!(success.execution_work-before.execution_work,7);assert_eq!(p.phase.parts.frames[0].pc,2);
  // PC now selects the actual decoded drop. The memory-only caller must reject
  // it before instruction charging and preserve the completed load value.
  pinned(p,&mut s).unwrap();let failure=s.entry.unwrap().unwrap_err();assert_eq!(failure.kind,SwiftRunFailureKind::UnsupportedEnvironment);
  assert_eq!(observed(p).instructions,success.instructions);assert_eq!(observed(p).execution_work,success.execution_work);assert_eq!(p.phase.parts.frames[0].pc,2);assert_eq!(p.phase.parts.values.as_slice(),&[Value::I32(0)]);
  let pins=pin_ids(p);assert!(p.memory_operation(STORE,&mut s.entry).is_err());assert_eq!(s.entry,Some(Err(failure)));assert_eq!(pin_ids(p),pins);assert_eq!(p.invariant("later").code,failure.code);
 });
 println!("REVIEW actual pin selects load then decoded drop; take success, preserve stored failure and exactly-once work/fuel/PC");
}
#[test]
fn review_caller_zero_alloc_and_occupied_precedes_inactive() {
 let _bound=Bounds::new();
 for trap in [false,true]{fixture(true,Some(BODY),|p|{
  push(p,&[Value::I32(if trap{-1}else{0})]);p.phase.parts.frames[0].pc=1;let mut s=storage();
  let (result,stats)=measure_extended(Some(0),||pinned(p,&mut s));assert_eq!(stats.attempts,0);assert_eq!(stats.injected_failures,0);result.unwrap();assert_eq!(s.entry.unwrap().is_err(),trap);
  let old=s.entry;let before=observed(p);let cursor=p.phase.operation.cursor;p.terminal();
  let (result,stats)=measure_extended(Some(0),||pinned(p,&mut s));assert!(result.is_err());assert_eq!(stats.attempts,0);assert_eq!(s.entry,old);assert_eq!((p.phase.operation.cursor.stage,p.phase.operation.cursor.function,p.phase.operation.cursor.offset),(cursor.stage,cursor.function,cursor.offset));
  assert_eq!(observed(p).instructions,before.instructions);assert_eq!(observed(p).execution_work,before.execution_work);assert_eq!(p.phase.parts.frames[0].pc,2);
 });}
 println!("REVIEW actual caller success/trap/occupied routes observe zero allocations under first-request refusal");
}
#[test]
fn review_store_postpop_cleanup_preserves_first_diagnostic() {
 let _bound=Bounds::new();fixture(true,None,|p|{
  push(p,&[Value::I32(0),Value::I32(123)]);let pins=pin_ids(p);let before=observed(p);
  hooks(Hooks{push_fault:5,..Hooks::default()});let mut s=storage();p.memory_operation(STORE,&mut s.entry).unwrap();let failure=s.entry.unwrap().unwrap_err();
  assert_eq!(failure.stage,SwiftRunStage::Cleanup);assert_eq!((failure.function,failure.offset,failure.resource),(None,None,None));assert_eq!(failure.code,"swift_run_live_underflow");assert!(p.cleanup.live_unreconciled);assert_eq!(p.phase.parts.values.as_slice(),&[Value::I32(0)]);assert_eq!(&p.phase.parts.memory[..8],&[0;8]);assert_eq!(pin_ids(p),pins);assert_eq!(observed(p).execution_work-before.execution_work,1);
  assert!(p.memory_operation(LOAD,&mut s.entry).is_err());assert_eq!(s.entry,Some(Err(failure)));assert_eq!(p.invariant("later").code,failure.code);
 });println!("REVIEW store first-pop debt retains absent-cursor Cleanup and original slot; no fabricated restoration");
}
#[test]
fn review_partial_pin_retention_requires_cleanup_reacquisition() {
 let _bound=Bounds::new();FIXTURES.with(|n|n.set(n.get()+2));
 let mut foreign=owner();install_foreign(&mut foreign);let mut own=owner();let original_bound=own.control.as_ref().unwrap().usage(None).reservations.construction.current;
 let mut s=storage();s.preparation=Some(own.prepare_frames(cursor()));let mut p=s.preparation.take().unwrap().unwrap();p.enter(34).unwrap();p.enter(36).unwrap();p.enter(34).unwrap();
 push(&mut p,&[Value::I32(-1)]);p.memory_operation(LOAD,&mut s.entry).unwrap();let failure=s.entry.unwrap().unwrap_err();
 hooks(Hooks{release_mask:1,..Hooks::default()});let first=p.drain();assert_eq!(first.retained_frames,1);let enriched=first.first_failure.unwrap();assert_eq!((enriched.stage,enriched.kind,enriched.code,enriched.function,enriched.offset,enriched.resource),(failure.stage,failure.kind,failure.code,failure.function,failure.offset,failure.resource));assert_eq!(enriched.at_failure,failure.at_failure);assert!(enriched.after_cleanup.is_some());assert_eq!(p.phase.parts.cache.usage().active_pins,1);
 hooks(Hooks::default());assert_eq!(p.drain().retained_frames,1);assert_eq!(p.phase.parts.cache.usage().active_pins,1);assert!(matches!(p.complete(s),FrameCompletion::Retained(_)));
 let mut resumed=Some(own.resume_frame_cleanup());let mut p=resumed.take().unwrap().unwrap();let report=p.drain();assert_eq!(report.retained_frames,0);let enriched=report.first_failure.unwrap();assert_eq!(enriched.code,failure.code);assert_eq!(enriched.at_failure,failure.at_failure);assert!(enriched.after_cleanup.is_some());assert!(!report.live_unreconciled);assert!(matches!(p.complete(FrameOperationStorage{preparation:resumed,..storage()}),FrameCompletion::Completed));
 assert_eq!(own.control.as_ref().unwrap().usage(None).reservations.construction.current,original_bound);restore_foreign(&mut foreign);retire(foreign);retire(own);
 println!("REVIEW deepest release rejected while other original pins drain; sticky original OOB; explicit cleanup-only retry restores bound");
}
