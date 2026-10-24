// Independently authored contextual and legacy control oracles.
#[test]
fn cdr07_all_six_contextual_live_resources_use_available_count() {
    for (live,resource) in [(Live::CacheEntries,SwiftRunResource::CacheEntries),
        (Live::ActivePins,SwiftRunResource::ActivePins),(Live::Frames,SwiftRunResource::Frames),
        (Live::Values,SwiftRunResource::Values),(Live::Controls,SwiftRunResource::Controls),
        (Live::MemoryPages,SwiftRunResource::MemoryPages)] {
        for available in [0,2] {
            let (mut control, adopted)=adopt(SwiftRunBudget::default());
            let c=Cursor{stage:SwiftRunStage::Invocation,function:Some(47),offset:Some(9876)};
            control.add_live(live,available,c).unwrap();
            let before=control.live;
            let failure=control.remove_live_at_with_wasi(live,available+1,c,None).unwrap_err();
            assert_eq!((failure.stage,failure.function,failure.offset),(c.stage,c.function,c.offset));
            assert_eq!((failure.resource,failure.attempted,failure.limit),(Some(resource),(available+1)as u64,available as u64));
            assert_eq!(failure.kind,SwiftRunFailureKind::Invariant);
            assert_eq!(failure.at_failure.cleanup_invariant,Some(SwiftCleanupInvariant::LiveUnderflow));
            assert_eq!((failure.observed_capacity,failure.wasi_failure,failure.guest_exit),(None,None,None));
            assert_eq!(control.live,before);
            control.remove_live(live,available).unwrap();
            assert_empty(clean(control,adopted));
        }
    }
}
#[test]
fn cdr08_success_and_zero_removal_match_original_six_resources() {
    for live in [Live::CacheEntries,Live::ActivePins,Live::Frames,Live::Values,Live::Controls,Live::MemoryPages] {
        let (mut old,oa)=adopt(SwiftRunBudget::default());
        let (mut new,na)=adopt(SwiftRunBudget::default());
        let c=cursor(SwiftRunStage::Invocation);
        old.add_live(live,3,c).unwrap();new.add_live(live,3,c).unwrap();
        for amount in [0,1,2,0] {
            let before=(new.instructions,new.instruction_fuel,new.execution_work);
            old.remove_live_with_wasi(live,amount,None).unwrap();
            new.remove_live_at_with_wasi(live,amount,c,None).unwrap();
            assert_eq!(old.live,new.live);
            assert_eq!((new.instructions,new.instruction_fuel,new.execution_work),before);
            assert!(new.first_failure.is_none());assert!(new.cleanup_invariant.is_none());
        }
        assert_empty(clean(old,oa));assert_empty(clean(new,na));
    }
}
#[test]
fn cdr09_first_failure_is_immutable_through_both_removals_and_cleanup() {
    for contextual in [false,true] {
        let (mut control,adopted)=adopt(SwiftRunBudget::default());
        let c=Cursor{stage:SwiftRunStage::Invocation,function:Some(71),offset:Some(33)};
        let original=control.fail(c,Fault::new(SwiftRunFailureKind::GuestTrap,"cdr_original")
            .limit(SwiftRunResource::MemoryPages,7,6),None);
        let c2=Cursor{stage:SwiftRunStage::Entry,function:Some(1),offset:Some(2)};
        let returned=if contextual {control.remove_live_at_with_wasi(Live::Values,9,c2,None)}
            else {control.remove_live_with_wasi(Live::Controls,2,None)}.unwrap_err();
        assert_eq!(returned,original);
        let after=control.record_cleanup(None).unwrap();let mut exact=after;exact.after_cleanup=None;
        assert_eq!(exact,original);assert_eq!(original.at_failure.cleanup_invariant,None);
        assert_eq!(after.after_cleanup.unwrap().cleanup_invariant,Some(SwiftCleanupInvariant::LiveUnderflow));
        assert_empty(clean(control,adopted));
    }
}
#[test]
fn cdr10_legacy_six_resources_stay_cursorless() {
    for live in [Live::CacheEntries,Live::ActivePins,Live::Frames,Live::Values,Live::Controls,Live::MemoryPages] {
        let (mut control,adopted)=adopt(SwiftRunBudget::default());
        let failure=control.remove_live_with_wasi(live,1,None).unwrap_err();
        assert_eq!(failure.stage,SwiftRunStage::Cleanup);
        assert_eq!((failure.function,failure.offset,failure.resource),(None,None,None));
        assert_eq!((failure.attempted,failure.limit),(0,0));
        assert_empty(clean(control,adopted));
    }
}
#[test]
fn cdr13_contextual_success_failure_refuse_first_allocation() {
    use crate::experimental_swift_reactor::allocation_tests::measure_extended;
    for fail in [false,true] {
        let (mut control,adopted)=adopt(SwiftRunBudget::default());
        let c=cursor(SwiftRunStage::Invocation);control.add_live(Live::Values,1,c).unwrap();
        let (result,stats)=measure_extended(Some(0),||control.remove_live_at_with_wasi(Live::Values,if fail{2}else{1},c,None));
        assert_eq!(result.is_err(),fail);assert_eq!(stats.attempts,0);assert_eq!(stats.injected_failures,0);
        if fail {control.remove_live(Live::Values,1).unwrap();}
        assert_empty(clean(control,adopted));
    }
}
