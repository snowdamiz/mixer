#[test]
fn cdr17_actual_pinned_host_posttruncate_attribution_preserves_effects() {
    let _b=Bounds::new();
    let body=&[0x41,0,0x41,4,0x10,0,0x1a,0x0b];
    // ArgsSizesGet is import index 0 in the strict proof.
    let mut own=owner_body(body,SwiftRunBudget::default(),small(),WasiGrants::default(),&[]);
    let mut prep=Some(own.prepare_frames(cursor()));let mut p=prep.take().unwrap().unwrap();p.enter(34).unwrap();push(&mut p,&[i(0),i(4)]);p.phase.parts.memory[..8].fill(0xff);p.phase.parts.frames[0].pc=2;
    let actual={let f=&p.phase.parts.frames[0];p.phase.parts.cache.view(&f.pin,p.phase.operation.control,Some(&*p.phase.operation.wasi)).unwrap().instructions[2]};
    let before=observed(&p);REMOVE_DEBT.with(|x|x.set(true));let mut s=storage();host_operation_pinned_caller(&mut p,&mut s).unwrap();reset();
    let failure=s.entry.unwrap().unwrap_err();assert_eq!((failure.stage,failure.function,failure.offset,failure.resource),(SwiftRunStage::Invocation,Some(34),Some(actual.offset),Some(SwiftRunResource::Values)));
    assert_eq!((failure.attempted,failure.limit),(2,0));assert_eq!(&p.phase.parts.memory[..8],&[0;8]);assert!(p.phase.parts.values.is_empty());assert!(p.cleanup.live_unreconciled);
    assert_eq!(observed(&p).host_calls-before.host_calls,1);assert_eq!(failure.at_failure.wasi.unwrap().calls,1);assert_eq!(p.phase.parts.frames[0].pc,3);
    let report=p.drain();let mut exact=report.first_failure.unwrap();exact.after_cleanup=None;assert_eq!(exact,failure);assert!(report.live_unreconciled);assert!(matches!(host_operation_complete(p,FrameOperationStorage{preparation:prep,..s}),FrameCompletion::Retained(_)));drop(own);
}
