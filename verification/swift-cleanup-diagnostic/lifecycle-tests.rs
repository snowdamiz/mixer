#[test]
fn cdr11_contextual_cause_exact_through_pin_retry_and_cleanup_reacquisition() {
    let _b=Bounds::new();let mut foreign=owner();install_foreign(&mut foreign);
    let mut own=body_owner(BODY,false,&[],SwiftRunBudget::default());let mut prep=Some(own.prepare_frames(cursor()));let mut p=prep.take().unwrap().unwrap();
    p.enter(34).unwrap();p.enter(36).unwrap();p.enter(34).unwrap();push(&mut p,&[Value::I32(0)]);p.phase.parts.frames[2].pc=1;
    hooks(Hooks{push_fault:5,..Hooks::default()});let mut s=storage();pinned(&mut p,&mut s).unwrap();hooks(Hooks::default());let first=s.entry.unwrap().unwrap_err();let pins=pin_ids(&p);
    p.phase.operation.control.cancellation().cancel();hooks(Hooks{release_mask:7,..Hooks::default()});
    for _ in 0..2 {let report=p.drain();assert_eq!(report.retained_frames,3);assert_eq!(pin_ids(&p),pins);let mut exact=report.first_failure.unwrap();exact.after_cleanup=None;assert_eq!(exact,first);assert!(report.live_unreconciled);}
    assert!(matches!(p.complete(FrameOperationStorage{preparation:prep,..s}),FrameCompletion::Retained(_)));hooks(Hooks::default());
    let mut resumed=Some(own.resume_frame_cleanup());let mut p=resumed.take().unwrap().unwrap();let report=p.drain();assert_eq!(report.retained_frames,0);let after=report.first_failure.unwrap();let mut exact=after;exact.after_cleanup=None;assert_eq!(exact,first);assert!(after.after_cleanup.is_some());assert!(report.live_unreconciled);
    assert!(matches!(p.complete(FrameOperationStorage{preparation:resumed,..storage()}),FrameCompletion::Retained(_)));let mut owned=Some(own);assert!(SwiftReactorInstance::cleanup_owned(&mut owned).is_err());assert!(owned.is_some());drop(owned);restore_foreign(&mut foreign);retire(foreign);
}
