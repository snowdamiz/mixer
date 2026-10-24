#[test]
fn cdr10_old_frame_cleanup_helper_ignores_stale_invocation_cursor() {
    let mut own=owner();let mut prep=Some(own.prepare_frames(cursor()));let mut p=prep.take().unwrap().unwrap();p.enter(34).unwrap();
    p.phase.operation.cursor=Cursor{stage:SwiftRunStage::Invocation,function:Some(999),offset:Some(999999)};
    assert!(!p.remove_live(Live::Values,1));let report=p.drain();let f=report.first_failure.unwrap();
    assert_eq!(f.stage,SwiftRunStage::Cleanup);assert_eq!((f.function,f.offset,f.resource),(None,None,None));assert_eq!((f.attempted,f.limit),(0,0));
    assert!(report.live_unreconciled);assert!(matches!(p.complete(FrameOperationStorage{preparation:prep,entry:None,returned:None,drained:None,controlled:None}),FrameCompletion::Retained(_)));drop(own);
}
