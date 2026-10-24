
// Review-only baseline probes. Appended to the isolated original test module.
#[test]
fn cd02_cursorless_cleanup_remains_absent_for_all_actual_live_resources() {
    for resource in [Live::CacheEntries, Live::ActivePins, Live::Frames,
        Live::Values, Live::Controls, Live::MemoryPages] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        let before = control.live;
        let failure = control.remove_live_with_wasi(resource, 1, None).unwrap_err();
        assert_eq!(failure.stage, SwiftRunStage::Cleanup);
        assert_eq!((failure.function, failure.offset, failure.resource), (None, None, None));
        assert_eq!(failure.code, "swift_run_live_underflow");
        assert_eq!(control.live, before);
        assert_eq!(failure.at_failure.cleanup_invariant, Some(SwiftCleanupInvariant::LiveUnderflow));
        let after = control.record_cleanup(None).unwrap();
        let mut original_fields = after;
        original_fields.after_cleanup = None;
        assert_eq!(original_fields, failure);
        assert!(after.after_cleanup.is_some());
        assert_empty(clean(control, adopted));
        println!("CD02 cursorlessResource={resource:?} reportedResource=None reportedStage=Cleanup function=None offset=None unchangedLive=true firstFailurePreserved=true");
    }
}

#[test]
fn cd03_later_live_underflow_only_enriches_cleanup_observation() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let original = control.fail(cursor(SwiftRunStage::Invocation),
        Fault::new(SwiftRunFailureKind::GuestTrap, "cd_original_guest_trap"), None);
    assert_eq!(original.at_failure.cleanup_invariant, None);
    let returned = control.remove_live_with_wasi(Live::Values, 1, None).unwrap_err();
    assert_eq!(returned, original);
    let after = control.record_cleanup(None).unwrap();
    let mut original_fields = after;
    original_fields.after_cleanup = None;
    assert_eq!(original_fields, original);
    assert_eq!(after.after_cleanup.unwrap().cleanup_invariant, Some(SwiftCleanupInvariant::LiveUnderflow));
    assert_empty(clean(control, adopted));
    println!("CD03 originalStage=Invocation originalCode=cd_original_guest_trap atFailureCleanupInvariant=None afterCleanupInvariant=LiveUnderflow noFirstFailureRewrite=true");
}
