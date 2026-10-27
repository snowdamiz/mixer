// Independent scratch-only private RuntimeControl tests. Never product source.
#[cfg(test)]
mod independent_phase_retention_v1 {
    use super::*;
    use std::cell::Cell;
    use super::super::cache::independent_phase_complete_v1 as complete;
    const A:usize=SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1;
    fn fixture()->RuntimeControl {
        let started=Instant::now();
        let selected=snapshot_scope_candidate_foundation_v1().unwrap();
        let header=size_of::<RuntimeControl>();
        let backing=Cancellation::requested_backing_layout().size();
        let shared=header.checked_add(backing).unwrap();
        let combined=shared.checked_add(selected).unwrap();
        let c=RuntimeControl {
            owner:1377,budget:SwiftRunBudget::default(),started,deadline:started+Duration::from_secs(30),
            deadline_origin:SwiftDeadlineOrigin::Run,cancellation:Cancellation::default(),
            validation:SwiftValidationUsage::default(),reservations:SwiftReservations {
                shared:SwiftReservationUsage{current:shared,peak:shared},
                construction:SwiftReservationUsage{current:selected,peak:selected},
                combined:SwiftReservationUsage{current:combined,peak:combined},
                live_tickets:3,peak_tickets:3,..SwiftReservations::default()
            },live:SwiftLiveUsage::default(),cache_work:0,execution_work:0,instruction_fuel:0,
            instructions:0,host_calls:0,cleanup_invariant:None,first_failure:None,
            control_header:Some(ReservationTicket{owner:1377,category:SwiftReservationCategory::Shared,bytes:header}),
            cancellation_backing:Some(ReservationTicket{owner:1377,category:SwiftReservationCategory::Shared,bytes:backing}),
            construction:Some(ReservationTicket{owner:1377,category:SwiftReservationCategory::Construction,bytes:selected}),
        };
        assert_eq!((header,std::mem::align_of::<RuntimeControl>()),(1720,8));
        assert_eq!(c.snapshot_foundation_pair_v1(),Ok(selected));
        for ticket in [&c.control_header,&c.cancellation_backing,&c.construction] {
            assert_eq!(c.snapshot_ticket_identity_v1(ticket.as_ref().unwrap()),Ok(()));
        }
        assert_eq!(c.snapshot_storage_preflight_v1(A),Ok(selected));
        c
    }
    fn wasi()->WasiUsage{WasiUsage{calls:43,work:47,transfer_bytes:53,..WasiUsage::default()}}
    fn ticket(c:&RuntimeControl)->(usize,u64,SwiftReservationCategory,usize){
        let t=c.construction.as_ref().unwrap();
        (t as *const ReservationTicket as usize,t.owner,t.category,t.bytes)
    }
    fn fault(c:&RuntimeControl,f:SwiftRunFailure,code:&str,invariant:SwiftCleanupInvariant){
        assert_eq!((f.stage,f.kind),(SwiftRunStage::Cleanup,SwiftRunFailureKind::Invariant));
        assert_eq!(f.code,code);assert_eq!(f.at_failure.cleanup_invariant,Some(invariant));
        assert_eq!(c.cleanup_invariant,Some(invariant));assert_eq!(f.at_failure.wasi,Some(wasi()));
    }
    struct Dropped<'a>(&'a Cell<usize>);
    impl Drop for Dropped<'_>{fn drop(&mut self){self.0.set(self.0.get()+1)}}
    #[test]
    fn same_ticket_complete_keeps_reservation_and_denies_one_more_byte(){
        let mut c=fixture();let before=c.reservations;let prior=ticket(&c);
        let target=c.snapshot_commit_storage_v1(A).unwrap();let committed=c.reservations;
        assert_eq!(ticket(&c),(prior.0,prior.1,prior.2,prior.3+A));
        assert_eq!(committed.construction,SwiftReservationUsage{current:prior.3+A,peak:prior.3+A});
        assert_eq!(committed.combined,SwiftReservationUsage{current:before.combined.current+A,peak:before.combined.peak+A});
        assert_eq!((committed.live_tickets,committed.peak_tickets),(before.live_tickets,before.peak_tickets));
        c.budget.combined_bytes=committed.combined.current;
        assert_eq!(complete(&mut c,target,Some(wasi()),true),Ok(()));
        // Assert after actual completion so the original early-refund operand
        // mutation demonstrably fails on real state, not on a scalar model.
        assert_eq!(ticket(&c),(prior.0,prior.1,prior.2,prior.3+A));
        assert_eq!(c.reservations,committed);assert_eq!(target,prior.3+A);
        assert_eq!(target,1_898_105);
        assert_eq!(c.snapshot_storage_preflight_v1(1),Err(SnapshotAdmissionErrorV1::Storage{
            current:committed.combined.current,additional:1,limit:committed.combined.current}));
        assert_eq!(c.first_failure,None);assert_eq!(c.cleanup_invariant,None);
        assert_eq!((c.execution_work,c.cache_work,c.instructions,c.host_calls),(0,0,0,0));
    }
    #[test]
    fn zero_addition_and_historical_peaks_are_preserved(){
        for additional in [0,A]{let mut c=fixture();
            c.reservations.construction.peak+=A+101;c.reservations.combined.peak+=A+103;
            let before=c.reservations;let old=ticket(&c);let target=c.snapshot_commit_storage_v1(additional).unwrap();
            let committed=c.reservations;assert_eq!(complete(&mut c,target,None,true),Ok(()));
            assert_eq!(c.reservations,committed);assert_eq!(ticket(&c),(old.0,old.1,old.2,old.3+additional));
            assert_eq!((c.reservations.construction.peak,c.reservations.combined.peak),(before.construction.peak,before.combined.peak));
        }
    }
    #[test]
    fn atomic_commit_refuses_storage_missing_owner_category_layout_and_cancellation(){
        for reason in 0..6{let mut c=fixture();let expected=match reason {
            0=>{c.budget.combined_bytes=c.reservations.combined.current+A-1;SnapshotAdmissionErrorV1::Storage{
                current:c.reservations.combined.current,additional:A,limit:c.budget.combined_bytes}},
            1=>{c.construction=None;SnapshotAdmissionErrorV1::Layout},
            2=>{c.construction.as_mut().unwrap().owner=1378;SnapshotAdmissionErrorV1::Owner},
            3=>{c.construction.as_mut().unwrap().category=SwiftReservationCategory::Shared;SnapshotAdmissionErrorV1::Owner},
            4=>{c.reservations.construction.current-=1;SnapshotAdmissionErrorV1::Layout},
            _=>{c.cancellation.cancel();SnapshotAdmissionErrorV1::Stop(SnapshotStopV1::Cancelled)},
        };let before=c.reservations;let prior=c.construction.as_ref().map(|_|ticket(&c));
            assert_eq!(c.snapshot_commit_storage_v1(A),Err(expected));assert_eq!(c.reservations,before);
            assert_eq!(c.construction.as_ref().map(|_|ticket(&c)),prior);
        }
    }
    #[test]
    fn actual_completion_preserves_missing_owner_category_and_both_bounds_with_wasi(){
        for reason in 0..5{let mut c=fixture();let committed=c.snapshot_commit_storage_v1(A).unwrap();
            let (target,code,invariant)=match reason {
                0=>{c.construction=None;(committed,"swift_run_missing_construction",SwiftCleanupInvariant::MissingConstruction)},
                1=>{c.construction.as_mut().unwrap().owner=1378;(committed,"swift_run_construction_owner",SwiftCleanupInvariant::ReservationOwner)},
                2=>{c.construction.as_mut().unwrap().category=SwiftReservationCategory::Shared;(committed,"swift_run_construction_owner",SwiftCleanupInvariant::ReservationOwner)},
                3=>(foundation_construction_bytes().unwrap()-1,"swift_run_construction_phase_bound",SwiftCleanupInvariant::ConstructionBound),
                _=>(committed+1,"swift_run_construction_phase_bound",SwiftCleanupInvariant::ConstructionBound),
            };let before=c.reservations;let prior=c.construction.as_ref().map(|_|ticket(&c));
            let f=complete(&mut c,target,Some(wasi()),true).unwrap_err();fault(&c,f,code,invariant);
            assert_eq!(c.reservations,before);assert_eq!(c.construction.as_ref().map(|_|ticket(&c)),prior);
        }
    }
    #[test]
    fn normalizer_real_shrink_preserves_both_underflow_faults(){
        for construction in [true,false]{let mut c=fixture();let previous=ticket(&c).3;
            c.snapshot_commit_storage_v1(A).unwrap();let prior=ticket(&c);
            if construction{c.reservations.construction.current=A-1}else{c.reservations.combined.current=A-1}
            let before=c.reservations;let drops=Cell::new(0);
            let f=c.end_construction_phase_with_wasi(Dropped(&drops),previous,Some(wasi())).unwrap_err();
            assert_eq!(drops.get(),1);fault(&c,f,"swift_run_release_underflow",SwiftCleanupInvariant::ReservationUnderflow);
            assert_eq!(c.reservations,before);assert_eq!(ticket(&c),prior);
        }
    }
    #[test]
    fn normalizer_destroys_paired_sentinel_on_success_and_missing_ticket(){
        for missing in [false,true]{let mut c=fixture();let target=c.snapshot_commit_storage_v1(A).unwrap();
            if missing{c.construction=None}let drops=Cell::new(0);
            let result=c.end_construction_phase_with_wasi(Dropped(&drops),target,Some(wasi()));
            assert_eq!(drops.get(),1);assert_eq!(result.is_err(),missing);
        }
    }
    #[test]
    fn refused_completion_keeps_fault_and_malformed_ledger(){
        let mut c=fixture();c.construction=None;c.cleanup_invariant=Some(SwiftCleanupInvariant::ReservationUnderflow);
        let before=c.reservations;assert_eq!(complete(&mut c,usize::MAX,Some(wasi()),false),Ok(()));
        assert_eq!(c.reservations,before);assert!(c.construction.is_none());
        assert_eq!(c.cleanup_invariant,Some(SwiftCleanupInvariant::ReservationUnderflow));assert_eq!(c.first_failure,None);
    }
    #[test]
    fn final_conservative_retirement_retains_enlarged_construction_and_wasi(){
        let mut c=fixture();let target=c.snapshot_commit_storage_v1(A).unwrap();
        assert_eq!(complete(&mut c,target,Some(wasi()),true),Ok(()));
        let final_usage=c.finish_owned_cleanup(Some(wasi()));
        assert_eq!(final_usage.cleanup_invariant,Some(SwiftCleanupInvariant::ConstructionBound));
        assert_eq!(final_usage.reservations.construction.current,target);
        assert_eq!(final_usage.reservations.combined.current,target);
        assert_eq!(final_usage.reservations.live_tickets,1);assert_eq!(final_usage.wasi,Some(wasi()));
    }
}
