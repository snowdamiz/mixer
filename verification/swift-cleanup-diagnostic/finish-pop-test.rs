#[test]
fn cdr06_actual_pinned_finish_result_pop_keeps_completing_source() {
    let mut own=body_owner(&[0x41,5,0x0b],true,&[],SwiftRunBudget::default());let mut prep=Some(own.prepare_frames(cursor()));let mut p=prep.take().unwrap().unwrap();p.enter(34).unwrap();p.phase.push_value(Value::I32(5)).unwrap();p.phase.parts.frames[0].pc=1;
    let (instruction,_)=fetched(&mut p);boundary(&mut p,instruction).unwrap();hooks(Hooks{push_fault:5,..Hooks::default()});let failure=p.finish().unwrap_err();hooks(Hooks::default());
    assert_eq!((failure.stage,failure.function,failure.offset,failure.resource),(SwiftRunStage::Invocation,Some(34),Some(instruction.offset),Some(SwiftRunResource::Values)));assert_eq!((failure.attempted,failure.limit),(1,0));assert_eq!(p.phase.parts.frames.len(),1);assert_eq!(p.phase.parts.cache.usage().active_pins,1);assert!(p.phase.parts.values.is_empty());
    // finish's original saved-result error returns before its removal adapter;
    // its original defensive latch is observed by the following cleanup pass.
    let report=p.drain();let mut exact=report.first_failure.unwrap();exact.after_cleanup=None;assert_eq!(exact,failure);let completed=complete(p,prep);drop(completed);drop(own);
}
