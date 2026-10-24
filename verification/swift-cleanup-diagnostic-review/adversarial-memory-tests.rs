
// Independent review-only overlay. Product helpers and Hooks are unchanged.
#[test]
fn review_r01_different_pinned_function_offset_nested_failure_and_success() {
    let _b = Bounds::new();
    let body = &[0x01, 0x01, 0x41, 7, 0x28, 2, 3, 0x1a, 0x0b];
    for fail in [false, true] {
        fixture(true, Some(body), |p| {
            push(p, &[Value::I32(123)]);
            p.enter(36).unwrap();
            p.phase.parts.memory[10..14].copy_from_slice(&0x12345678i32.to_le_bytes());
            push(p, &[Value::I32(7)]);
            p.phase.parts.frames[1].pc = 3;
            p.phase.operation.cursor = Cursor { stage: SwiftRunStage::Invocation, function: Some(999), offset: Some(999999) };
            let actual = {
                let f = &p.phase.parts.frames[1];
                (f.function, p.phase.parts.cache.view(&f.pin, p.phase.operation.control, Some(&*p.phase.operation.wasi)).unwrap().instructions[3])
            };
            assert_eq!(actual.0, 36);
            assert_ne!(actual.1.offset, 1713);
            assert!(matches!(actual.1.operation, Operation::Load { opcode: 0x28, offset: 3 }));
            p.phase.operation.wasi.dispatch(p.phase.operation.control, crate::experimental_wasi::WasiFunction::ArgsSizesGet, &[Value::I32(0), Value::I32(4)], &mut [0; 8], cursor()).unwrap();
            let wasi = p.phase.operation.wasi.usage();
            let before = observed(p);
            let pins = pin_ids(p);
            let memory = p.phase.parts.memory[10..14].to_vec();
            if fail { hooks(Hooks { push_fault: 5, ..Hooks::default() }); }
            let mut s = storage();
            pinned(p, &mut s).unwrap();
            hooks(Hooks::default());
            assert_eq!(p.phase.parts.frames[0].pc, 0);
            assert_eq!(p.phase.parts.frames[1].pc, 4);
            assert_eq!(pin_ids(p), pins);
            assert_eq!(p.phase.parts.memory[10..14], memory);
            assert_eq!((p.phase.operation.cursor.function, p.phase.operation.cursor.offset), (Some(36), Some(actual.1.offset)));
            if fail {
                let first = s.entry.unwrap().unwrap_err();
                assert_eq!((first.stage, first.function, first.offset, first.resource), (SwiftRunStage::Invocation, Some(36), Some(actual.1.offset), Some(SwiftRunResource::Values)));
                assert_eq!((first.code, first.attempted, first.limit), ("swift_run_live_underflow", 1, 0));
                assert_eq!(first.at_failure.wasi, Some(wasi));
                assert_eq!(first.at_failure.cleanup_invariant, Some(SwiftCleanupInvariant::LiveUnderflow));
                assert_eq!(p.phase.parts.values.as_slice(), &[Value::I32(123)]);
                assert_eq!((observed(p).instructions - before.instructions, observed(p).instruction_fuel - before.instruction_fuel, observed(p).execution_work - before.execution_work), (1, 1, 2));
                p.phase.operation.control.cancellation().cancel();
                assert_eq!(p.phase.operation.control.check(cursor()).unwrap_err(), first);
                for _ in 0..2 {
                    let report = p.drain();
                    let after = report.first_failure.unwrap();
                    let mut exact = after;
                    exact.after_cleanup = first.after_cleanup;
                    assert_eq!(exact, first);
                    assert!(after.after_cleanup.is_some());
                    assert!(report.live_unreconciled);
                    assert_eq!(report.retained_frames, 0);
                }
                println!("REVIEW_R01 nestedFrames=2 actualFunction={} actualOffset={} outerPC=0 nextPC=4 attempted=1 available=0 wasiCalls={} fullFirstFailureAndAtFailureExact=true", actual.0, actual.1.offset, wasi.calls);
            } else {
                assert_eq!(s.entry, Some(Ok(())));
                assert_eq!(p.phase.parts.values.as_slice(), &[Value::I32(123), Value::I32(0x12345678)]);
                assert_eq!(observed(p).live.values.current, 2);
                assert_eq!((observed(p).instructions - before.instructions, observed(p).instruction_fuel - before.instruction_fuel, observed(p).execution_work - before.execution_work), (1, 1, 7));
                assert!(!p.cleanup.live_unreconciled);
            }
        });
    }
}

#[test]
fn review_r02_nested_stale_cursor_cleanup_preserves_first_observation_and_debt() {
    let _b = Bounds::new();
    fixture(true, Some(&[0x01, 0x0b]), |p| {
        p.enter(36).unwrap();
        let pins = pin_ids(p);
        p.phase.operation.cursor = Cursor { stage: SwiftRunStage::Invocation, function: Some(36), offset: Some(812345) };
        assert!(!p.remove_live(Live::Values, 7));
        let first = p.phase.operation.control.check(cursor()).unwrap_err();
        assert_eq!((first.stage, first.function, first.offset, first.resource, first.attempted, first.limit), (SwiftRunStage::Cleanup, None, None, None, 0, 0));
        let at_failure = first.at_failure;
        assert_eq!(pin_ids(p), pins);
        assert_eq!(at_failure.cleanup_invariant, Some(SwiftCleanupInvariant::LiveUnderflow));
        // A later contextual failure with a real but different cursor cannot
        // mutate the legacy diagnostic or its immutable failure observation.
        let actual = { let f=&p.phase.parts.frames[1]; (f.function,p.phase.parts.cache.view(&f.pin,p.phase.operation.control,Some(&*p.phase.operation.wasi)).unwrap().instructions[0].offset) };
        let returned = p.phase.operation.control.remove_live_at_with_wasi(Live::Values, 9, Cursor { stage: SwiftRunStage::Invocation, function: Some(actual.0), offset: Some(actual.1) }, Some(p.phase.operation.wasi.usage())).unwrap_err();
        assert_eq!(returned, first);
        p.phase.operation.control.cancellation().cancel();
        for _ in 0..2 {
            let report=p.drain(); let after=report.first_failure.unwrap(); let mut exact=after;exact.after_cleanup=first.after_cleanup;
            assert_eq!(exact,first);assert_eq!(after.at_failure,at_failure);assert!(after.after_cleanup.is_some());assert!(report.live_unreconciled);
        }
        println!("REVIEW_R02 nestedLegacyStage=Cleanup absentFunctionOffsetResource=true zeroAttemptLimit=true laterActualFunction={} laterActualOffset={} firstFailureExact=true", actual.0, actual.1);
    });
}
