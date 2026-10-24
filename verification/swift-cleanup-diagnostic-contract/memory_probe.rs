
// Review-only baseline probe. Appended to the isolated original test module.
#[test]
fn cd01_actual_pinned_load_preserves_absent_cleanup_origin() {
    let _bound = Bounds::new();
    fixture(true, Some(BODY), |phase| {
        phase.phase.operation.wasi.dispatch(
            phase.phase.operation.control,
            crate::experimental_wasi::WasiFunction::ArgsSizesGet,
            &[Value::I32(0), Value::I32(4)],
            &mut [0; 8], cursor(),
        ).unwrap();
        let wasi = phase.phase.operation.wasi.usage();
        assert_eq!(wasi.calls, 1);
        push(phase, &[Value::I32(0)]);
        phase.phase.parts.frames[0].pc = 1;
        let actual = {
            let frame = &phase.phase.parts.frames[0];
            let view = phase.phase.parts.cache.view(
                &frame.pin, phase.phase.operation.control,
                Some(&*phase.phase.operation.wasi),
            ).unwrap();
            (frame.function, view.instructions[frame.pc])
        };
        assert_eq!(actual.1.operation, LOAD);
        hooks(Hooks { push_fault: 5, ..Hooks::default() });
        let mut returned = storage();
        pinned(phase, &mut returned).unwrap();
        hooks(Hooks::default());
        let failure = returned.entry.unwrap().unwrap_err();
        let current = phase.phase.operation.cursor;
        assert_eq!(current.stage, SwiftRunStage::Invocation);
        assert_eq!((current.function, current.offset), (Some(actual.0), Some(actual.1.offset)));
        assert_eq!(failure.code, "swift_run_live_underflow");
        assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
        assert_eq!(failure.stage, SwiftRunStage::Cleanup);
        assert_eq!((failure.function, failure.offset, failure.resource), (None, None, None));
        assert_eq!(failure.at_failure.wasi, Some(wasi));
        assert_eq!(failure.at_failure.cleanup_invariant, Some(SwiftCleanupInvariant::LiveUnderflow));
        assert!(failure.after_cleanup.is_none());
        assert!(phase.phase.parts.values.is_empty());
        assert_eq!(failure.at_failure.live.values.current, 0);
        assert!(phase.cleanup.live_unreconciled);
        phase.phase.operation.control.cancellation().cancel();
        assert_eq!(phase.phase.operation.control.check(current).unwrap_err(), failure);
        let report = phase.drain();
        let after = report.first_failure.unwrap();
        let mut original_fields = after;
        original_fields.after_cleanup = None;
        assert_eq!(original_fields, failure);
        assert!(after.after_cleanup.is_some());
        assert!(report.live_unreconciled);
        assert_eq!(report.retained_frames, 0);
        let again = phase.drain().first_failure.unwrap();
        let mut original_fields = again;
        original_fields.after_cleanup = None;
        assert_eq!(original_fields, failure);
        println!("CD01 actualFunction={} actualOffset={} actualStage={:?} reportedStage={:?} function={:?} offset={:?} resource={:?} code={} attempted={} limit={} wasiCalls={} postPopValues={} firstFailurePreserved=true atFailurePreserved=true afterCleanupAdded=true debtRetained=true",
            actual.0, actual.1.offset, current.stage, failure.stage, failure.function,
            failure.offset, failure.resource, failure.code, failure.attempted,
            failure.limit, wasi.calls, phase.phase.parts.values.len());
    });
}
