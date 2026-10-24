// Independently authored adversarial probes, appended only to review overlay.
#[test]
fn review01_new_layout_rejection_drops_allocation_then_retains_actual_ticket() {
    let _bound=Bounds::new();
    fixture(|phase,context,growth| {
        growth.transfer.next_pages=1;
        let ticket=phase.phase.operation.control.admit_with_wasi(SwiftReservationCategory::State,PAGE,phase.phase.operation.cursor,Some(phase.phase.operation.wasi.usage())).unwrap();
        growth.transfer.ticket=Some(ticket);
        growth.transfer.replacement.try_reserve_exact(PAGE).unwrap();
        growth.transfer.replacement.resize(PAGE,0x5a);
        growth.transfer.next_pages=2; // Actual N still proves only one page.
        let before=observed(phase);
        let (result,stats)=measure_extended(None,||release_growth_pending(phase,context,growth));
        assert_eq!(result.unwrap_err().code,"swift_growth_ticket_layout");
        assert_eq!(stats.deallocations,1);assert_eq!(stats.freed_bytes,PAGE);
        assert_eq!(growth.transfer.replacement.capacity(),0);
        assert!(growth.transfer.ticket.as_ref().unwrap().matches_layout(SwiftReservationCategory::State,PAGE));
        assert_eq!(observed(phase).reservations,before.reservations);
        growth.transfer.next_pages=1;
        phase.phase.operation.control.cancellation().cancel();
        release_growth_pending(phase,context,growth).unwrap();
        assert!(growth.vacant());
        assert_eq!(observed(phase).reservations.state.current,before.reservations.state.current-PAGE);
        assert_eq!(observed(phase).reservations.live_tickets,before.reservations.live_tickets-1);
    });
}

#[test]
fn review02_old_layout_rejection_retains_charge_then_retry_ignores_cancel() {
    let _bound=Bounds::new();
    fixture(|phase,context,growth| {
        growth.transfer.old_pages=1;
        growth.transfer.old_ticket=Some(phase.phase.operation.control.admit_with_wasi(SwiftReservationCategory::State,PAGE,phase.phase.operation.cursor,Some(phase.phase.operation.wasi.usage())).unwrap());
        growth.transfer.old.try_reserve_exact(PAGE).unwrap();
        growth.transfer.old.resize(PAGE,0x91);
        growth.transfer.old_pages=2;
        let before=observed(phase);
        let (result,stats)=measure_extended(None,||release_growth_pending(phase,context,growth));
        assert_eq!(result.unwrap_err().code,"swift_growth_ticket_layout");
        assert_eq!(stats.deallocations,1);assert_eq!(stats.freed_bytes,PAGE);
        assert!(growth.transfer.old_ticket.is_some());assert_eq!(growth.transfer.old.capacity(),0);
        assert_eq!(observed(phase).reservations,before.reservations);
        growth.transfer.old_pages=1;phase.phase.operation.control.cancellation().cancel();
        release_growth_pending(phase,context,growth).unwrap();
        assert!(growth.vacant());
        assert_eq!(observed(phase).live.memory_pages,before.live.memory_pages);
        assert_eq!(observed(phase).reservations.state.current,before.reservations.state.current-PAGE);
    });
}

#[test]
fn review03_original_owner_failure_precedes_envelope_and_allocator() {
    let _bound=Bounds::new();
    for foreign in [false,true] {
        FIXTURES.with(|x|x.set(x.get()+2));
        let mut own=body_owner(BODY,false,&[],SwiftRunBudget::default());
        let mut other=body_owner(BODY,false,&[],SwiftRunBudget::default());
        let original=own.state.as_mut().unwrap().buffers[3].take();
        if foreign {own.state.as_mut().unwrap().buffers[3]=other.state.as_mut().unwrap().buffers[3].take();}
        let before=own.control.as_ref().unwrap().usage(None);
        let (result,stats)=measure_extended(Some(0),||own.prepare_growth(cursor()));
        assert!(result.is_err());drop(result);
        assert_eq!(stats.attempts,0);
        assert!(own.state.as_ref().unwrap().frame_cleanup.bound.is_none());
        assert_eq!(own.control.as_ref().unwrap().usage(None).reservations,before.reservations);
        if foreign {other.state.as_mut().unwrap().buffers[3]=own.state.as_mut().unwrap().buffers[3].take();}
        own.state.as_mut().unwrap().buffers[3]=original;
        retire(own);retire(other);
    }
}

#[test]
fn review04_operand_floor_prefix_survives_positive_commit() {
    let _bound=Bounds::new();
    fixture(|phase,context,growth| {
        phase.phase.push_value(Value::I64(0x123456789)).unwrap();
        phase.phase.parts.frames[0].operands=1;
        phase.phase.parts.memory[PAGE-1]=0xa7;
        let before=observed(phase);
        op(phase,context,growth,1).unwrap();
        assert_eq!(phase.phase.parts.values.as_slice(),&[Value::I64(0x123456789),Value::I32(584)]);
        assert_eq!(phase.phase.parts.memory[PAGE-1],0xa7);
        assert!(phase.phase.parts.memory[584*PAGE..].iter().all(|v|*v==0));
        assert_eq!(observed(phase).instruction_fuel,before.instruction_fuel);
        assert_eq!(observed(phase).live.memory_pages.current,585);
        assert!(context.memory_ticket.as_ref().unwrap().matches_layout(SwiftReservationCategory::State,585*PAGE));
        phase.phase.parts.frames[0].operands=0;
    });
}

#[test]
fn review05_pending_actual_vec_forces_retained_exact_envelope() {
    let _bound=Bounds::new();
    FIXTURES.with(|x|x.set(x.get()+1));
    let mut own=body_owner(BODY,false,&[],SwiftRunBudget::default());
    let before=own.control.as_ref().unwrap().usage(None).reservations.construction.current;
    let mut prep=Some(own.prepare_growth(cursor()));let (phase,context)=prep.take().unwrap().unwrap();
    let mut growth=SwiftGrowthStorage::empty();growth.transfer.replacement.try_reserve_exact(PAGE).unwrap();
    let pointer=growth.transfer.replacement.as_ptr();
    let retained=complete_growth(phase,context,growth,frame_storage(),prep);
    let (mut phase,mut context,mut growth,storage,prep)=match retained {
        GrowthCompletion::Retained{phase,context,growth,storage,preparation}=>(phase,context,growth,storage,preparation),
        _=>panic!("nonempty actual transfer allocation must retain all wrappers"),
    };
    assert_eq!(growth.transfer.replacement.as_ptr(),pointer);
    assert_eq!(observed(&phase).reservations.construction.current,before+FRAME_OPERATION_BYTES.unwrap());
    phase.phase.operation.control.cancellation().cancel();
    release_growth_pending(&mut phase,&mut context,&mut growth).unwrap();phase.drain();
    assert!(matches!(complete_growth(phase,context,growth,storage,prep),GrowthCompletion::Completed(FrameCompletion::Completed)));
    assert_eq!(own.control.as_ref().unwrap().usage(None).reservations.construction.current,before);retire(own);
}

#[test]
fn review06_allocate_page_admission_failure_never_calls_allocator() {
    let _bound=Bounds::new();
    fixture(|phase,context,growth| {
        let old=phase.phase.operation.control.review_replace_memory_pages_limit(584);
        let before=observed(phase);let pointer=phase.phase.parts.memory.as_ptr();
        let mut execution=SwiftGrowthExecution{phase,context,storage:growth};
        let (result,stats)=measure_extended(Some(0),||execution.allocate(585*PAGE));
        assert!(result.is_err());drop(result);assert_eq!(stats.attempts,0);
        assert_eq!(execution.phase.phase.parts.memory.as_ptr(),pointer);
        let after=observed(execution.phase);
        assert_eq!(after.reservations.state.current,before.reservations.state.current);
        assert_eq!(after.reservations.combined.current,before.reservations.combined.current);
        assert_eq!(after.reservations.live_tickets,before.reservations.live_tickets);
        assert!(after.reservations.state.peak>=before.reservations.state.current+585*PAGE);
        assert_eq!(observed(execution.phase).live.memory_pages.current,584);
        assert!(execution.storage.vacant());
        execution.phase.phase.operation.control.review_replace_memory_pages_limit(old);
    });
}

#[test]
fn review07_all_refund_predicates_reject_before_take_and_retry_exact_ticket() {
    let _bound=Bounds::new();
    for fault in 0..4 {
        fixture(|phase,context,growth| {
            growth.transfer.next_pages=1;
            growth.transfer.ticket=Some(phase.phase.operation.control.admit_with_wasi(SwiftReservationCategory::State,PAGE,phase.phase.operation.cursor,Some(phase.phase.operation.wasi.usage())).unwrap());
            let saved=phase.phase.operation.control.review_refund_corruption(fault,None);
            let before=observed(phase);
            assert_eq!(release_growth_pending(phase,context,growth).unwrap_err().code,if fault==0{"swift_run_reservation_owner"}else{"swift_run_reservation_underflow"});
            assert!(growth.transfer.ticket.as_ref().unwrap().matches_layout(SwiftReservationCategory::State,PAGE));
            assert_eq!(observed(phase).reservations,before.reservations);
            // Test-only restoration of the exact corrupt scalar snapshot; this
            // is not a product recovery path or debt reconciliation.
            phase.phase.operation.control.review_refund_corruption(fault,Some(saved));
            phase.phase.operation.control.cancellation().cancel();
            release_growth_pending(phase,context,growth).unwrap();assert!(growth.vacant());
        });
    }
}
