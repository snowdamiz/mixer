// Independent reviewer controls. Append only to the review-owned source copy.
#[test]
fn review_control_warm_growth_overlap_rejects_before_allocator() {
    let body = Function::scalar(&[0x41, 1, 0x40, 0, 0x1a, 0x41, 0, 0x0b], Type::I32);
    let (_, starts) = module(&[(28, body.clone())], &[]);
    for combined in [false, true] {
        let mut o = owner(&[(28, body.clone())]);
        success(&mut o, Request::Initialize);
        assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(0));
        assert_eq!(observed(&o).instructions, 6);
        o.state.as_mut().unwrap().memory[64..72].copy_from_slice(&[1,2,3,4,5,6,7,8]);
        let pointer = o.state.as_ref().unwrap().memory.as_ptr();
        let before = observed(&o);
        let required = if combined {
            before.reservations.combined.current + FRAME_OPERATION_BYTES.unwrap() + 586 * PAGE
        } else { before.reservations.state.current + 586 * PAGE };
        let old = if combined {
            o.control.as_mut().unwrap().test_replace_combined_limit(required - 1)
        } else {
            o.control.as_mut().unwrap().test_replace_state_limit(required - 1)
        };
        let (f, stats) = measure_extended(Some(0), || failed(&mut o, Request::Corpus));
        assert_eq!(stats.attempts, 0);
        assert_eq!(stats.injected_failures, 0);
        assert_eq!(f.kind, if combined {SwiftRunFailureKind::CombinedExhausted} else {SwiftRunFailureKind::CategoryExhausted});
        assert_eq!(f.resource, Some(if combined {SwiftRunResource::Combined} else {SwiftRunResource::Reservation(SwiftReservationCategory::State)}));
        assert_eq!(f.attempted, required as u64);
        assert_eq!(f.limit, (required - 1) as u64);
        assert_eq!((f.stage,f.function,f.offset), (SwiftRunStage::Invocation,Some(62),Some(starts[28] + 2)));
        assert_eq!(f.at_failure.instructions, 8);
        assert_eq!(o.state.as_ref().unwrap().memory.len(), 585 * PAGE);
        assert_eq!(o.state.as_ref().unwrap().memory.as_ptr(), pointer);
        assert_eq!(&o.state.as_ref().unwrap().memory[64..72], &[1,2,3,4,5,6,7,8]);
        assert_eq!(observed(&o).reservations.state.current, before.reservations.state.current);
        assert_eq!(observed(&o).reservations.live_tickets, before.reservations.live_tickets);
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        if combined {o.control.as_mut().unwrap().test_replace_combined_limit(old);} else {o.control.as_mut().unwrap().test_replace_state_limit(old);}
        retire(o);
    }
}

#[test]
fn review_control_postdispatch_cancel_preserves_exact_guest_exit() {
    for invocation in [false, true] {
        for code in [0u32,7,u32::MAX] {
            let mut exit = wasi_call(WasiFunction::ProcExit, &[code as i32], false, if invocation {&[0x41,0]} else {&[]});
            if invocation {exit.result=Some(Type::I32);}
            let mut o=owner(&[(if invocation {28} else {1},exit)]);
            if invocation {success(&mut o,Request::Initialize);}
            o.wasi.as_mut().unwrap().host_test_dispatch(false,true);
            let f=failed(&mut o,if invocation {Request::Corpus} else {Request::Initialize});
            assert!(o.control.as_ref().unwrap().cancellation().is_cancelled());
            assert_eq!(f.kind,SwiftRunFailureKind::GuestExit);
            assert_eq!(f.guest_exit,Some(code));
            assert_eq!(f.stage,if invocation {SwiftRunStage::Invocation} else {SwiftRunStage::Initialization});
            assert_eq!(f.function,Some(if invocation {62} else {35}));
            assert_eq!(observed(&o).host_calls,1);
            assert_eq!(o.wasi.as_ref().unwrap().usage().calls,1);
            let usage=normalized(observed(&o));
            for req in [Request::Initialize,Request::Corpus] {assert!(matches!(request(&mut o,req),Completion::BlockedTerminal));}
            assert_eq!(normalized(observed(&o)),usage);
            assert_eq!(o.control.as_mut().unwrap().record_cleanup(None).unwrap().at_failure,f.at_failure);
            retire(o);
        }
    }
}
