
#[test]
fn review_r03_cancelled_success_zero_and_exact_optional_cursor_max_attempt() {
    for live in [Live::CacheEntries, Live::ActivePins, Live::Frames, Live::Values, Live::Controls, Live::MemoryPages] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        let add_cursor = cursor(SwiftRunStage::Invocation);
        control.add_live(live, 3, add_cursor).unwrap();
        control.cancellation().cancel();
        let before = (control.instructions, control.instruction_fuel, control.execution_work);
        let actual_cursor = Cursor { stage: SwiftRunStage::Initialization, function: None, offset: Some(987654) };
        for amount in [0, 1, 2, 0] {
            control.remove_live_at_with_wasi(live, amount, actual_cursor, None).unwrap();
            assert_eq!((control.instructions, control.instruction_fuel, control.execution_work), before);
            assert!(control.first_failure.is_none());
        }
        let original_live = control.live;
        let first = control.remove_live_at_with_wasi(live, usize::MAX, actual_cursor, None).unwrap_err();
        assert_eq!((first.stage, first.function, first.offset), (actual_cursor.stage, actual_cursor.function, actual_cursor.offset));
        assert_eq!((first.attempted, first.limit), (usize::MAX as u64, 0));
        assert_eq!(first.kind, SwiftRunFailureKind::Invariant);
        assert_eq!(control.live, original_live);
        assert_eq!(control.check(add_cursor).unwrap_err(), first);
        let after = control.record_cleanup(None).unwrap();
        let mut exact = after; exact.after_cleanup = first.after_cleanup;
        assert_eq!(exact, first);
        assert!(after.after_cleanup.is_some());
        assert_empty(clean(control, adopted));
    }
    println!("REVIEW_R03 sixResources=true cancelledSuccessAndZero=true missingFunctionPreserved=true stageInitializationPreserved=true maxRepresentableAttemptExact=true noWorkFuelOrInstruction=true");
}
