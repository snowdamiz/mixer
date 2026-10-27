// Separately hashed private control-only fixture overlay. Not source144/product.
#[cfg(test)]
mod phase_retention_controls_v1 {
    use super::*;
    use std::cell::Cell;
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    const A:usize=SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1;
    fn fixture()->RuntimeControl {
        let started=Instant::now();
        let bytes=snapshot_scope_candidate_foundation_v1().expect("selected const");
        let header=size_of::<RuntimeControl>();assert_eq!(header,1720);assert_eq!(std::mem::align_of::<RuntimeControl>(),8);
        let backing=Cancellation::requested_backing_layout().size();
        let shared=header+backing;
        let construction=SwiftReservationUsage{current:bytes,peak:bytes};
        let control=RuntimeControl{
            owner:42,budget:SwiftRunBudget::default(),started,deadline:started+Duration::from_secs(30),
            deadline_origin:SwiftDeadlineOrigin::Run,cancellation:Cancellation::default(),
            validation:SwiftValidationUsage::default(),reservations:SwiftReservations{
                shared:SwiftReservationUsage{current:shared,peak:shared},construction,
                combined:SwiftReservationUsage{current:shared+bytes,peak:shared+bytes},
                live_tickets:3,peak_tickets:3,..SwiftReservations::default()
            },live:SwiftLiveUsage::default(),cache_work:0,execution_work:0,instruction_fuel:0,instructions:0,
            host_calls:0,cleanup_invariant:None,first_failure:None,
            control_header:Some(ReservationTicket{owner:42,category:SwiftReservationCategory::Shared,bytes:header}),
            cancellation_backing:Some(ReservationTicket{owner:42,category:SwiftReservationCategory::Shared,bytes:backing}),
            construction:Some(ReservationTicket{owner:42,category:SwiftReservationCategory::Construction,bytes}),
        };
        assert_eq!(control.snapshot_foundation_pair_v1(),Ok(bytes));
        assert_eq!(control.snapshot_ticket_identity_v1(control.control_header.as_ref().unwrap()),Ok(()));
        assert_eq!(control.snapshot_ticket_identity_v1(control.cancellation_backing.as_ref().unwrap()),Ok(()));
        assert_eq!(control.snapshot_ticket_identity_v1(control.construction.as_ref().unwrap()),Ok(()));
        assert_eq!(control.reservations.combined.current,shared+bytes);
        assert_eq!(control.reservations.live_tickets,3);
        assert_eq!(control.budget.combined_bytes,256*1024*1024);
        assert_eq!(control.budget.execution_work,1_000_000_000);
        // Exercise the actual preflight, without charging work or invoking an ingress.
        assert_eq!(control.snapshot_storage_preflight_v1(A),Ok(bytes));
        control
    }
    fn wasi()->WasiUsage{WasiUsage{calls:17,work:23,transfer_bytes:31,..WasiUsage::default()}}
    struct Dropped<'a>(&'a Cell<bool>);
    impl Drop for Dropped<'_>{fn drop(&mut self){self.0.set(true)}}
    fn assert_failure(control:&RuntimeControl,f:SwiftRunFailure,code:&str,kind:SwiftCleanupInvariant){
        assert_eq!(f.stage,SwiftRunStage::Cleanup);assert_eq!(f.kind,SwiftRunFailureKind::Invariant);
        assert_eq!(f.code,code);assert_eq!(f.at_failure.cleanup_invariant,Some(kind));
        assert_eq!(control.cleanup_invariant,Some(kind));assert_eq!(f.at_failure.wasi,Some(wasi()));
    }
    #[test]
    fn admitted_retains_A_same_ticket_current_and_peaks(){
        let mut c=fixture();let old=c.reservations;let selected=c.construction.as_ref().unwrap().bytes;
        let address=c.construction.as_ref().unwrap() as *const ReservationTicket as usize;
        let retained=c.snapshot_commit_storage_v1(A).unwrap();
        assert_eq!(retained,selected+A);assert_eq!(retained,1_898_105);
        let ticket=c.construction.as_ref().unwrap();
        assert_eq!(ticket as *const ReservationTicket as usize,address);
        assert_eq!((ticket.owner,ticket.category,ticket.bytes),(42,SwiftReservationCategory::Construction,retained));
        assert_eq!(c.reservations.construction,SwiftReservationUsage{current:retained,peak:retained});
        assert_eq!(c.reservations.combined,SwiftReservationUsage{current:old.combined.current+A,peak:old.combined.peak+A});
        assert_eq!((c.reservations.live_tickets,c.reservations.peak_tickets),(3,3));
        let committed=c.reservations;assert_eq!(complete(&mut c,retained,Some(wasi()),true),Ok(()));
        assert_eq!(c.reservations,committed);assert_eq!(c.construction.as_ref().unwrap().bytes,retained);
        assert_eq!(c.construction.as_ref().unwrap() as *const ReservationTicket as usize,address);
        assert_eq!(c.first_failure,None);assert_eq!(c.cleanup_invariant,None);assert_eq!(c.execution_work,0);
        let final_usage=c.finish_owned_cleanup(Some(wasi()));
        assert_eq!(final_usage.cleanup_invariant,Some(SwiftCleanupInvariant::ConstructionBound));
        assert_eq!(final_usage.reservations.construction.current,retained);
        assert_eq!(final_usage.reservations.combined.current,retained);
        assert_eq!(final_usage.reservations.live_tickets,1);assert_eq!(final_usage.wasi,Some(wasi()));
    }
    #[test]
    fn prior_higher_peaks_remain(){
        let mut c=fixture();c.reservations.construction.peak+=A+19;c.reservations.combined.peak+=A+29;
        let peaks=(c.reservations.construction.peak,c.reservations.combined.peak);
        let retained=c.snapshot_commit_storage_v1(A).unwrap();assert_eq!(complete(&mut c,retained,None,true),Ok(()));
        assert_eq!((c.reservations.construction.peak,c.reservations.combined.peak),peaks);
    }
    #[test]
    fn missing_ticket_completion_preserves_error_and_wasi(){
        let mut c=fixture();let retained=c.snapshot_commit_storage_v1(A).unwrap();c.construction=None;
        let before=c.reservations;let f=complete(&mut c,retained,Some(wasi()),true).unwrap_err();
        assert_failure(&c,f,"swift_run_missing_construction",SwiftCleanupInvariant::MissingConstruction);
        assert_eq!(c.reservations,before);
    }
    #[test]
    fn owner_and_category_completion_faults_preserved(){
        for wrong_owner in [true,false]{let mut c=fixture();let retained=c.snapshot_commit_storage_v1(A).unwrap();
            let ticket=c.construction.as_mut().unwrap();if wrong_owner{ticket.owner=43}else{ticket.category=SwiftReservationCategory::Shared}
            let before=c.reservations;let f=complete(&mut c,retained,Some(wasi()),true).unwrap_err();
            assert_failure(&c,f,"swift_run_construction_owner",SwiftCleanupInvariant::ReservationOwner);
            assert_eq!(c.reservations,before);
        }
    }
    #[test]
    fn both_completion_bounds_preserved(){
        for low in [true,false]{let mut c=fixture();let retained=c.snapshot_commit_storage_v1(A).unwrap();
            let target=if low{foundation_construction_bytes().unwrap()-1}else{retained+1};let before=c.reservations;
            let f=complete(&mut c,target,Some(wasi()),true).unwrap_err();
            assert_failure(&c,f,"swift_run_construction_phase_bound",SwiftCleanupInvariant::ConstructionBound);
            assert_eq!(c.reservations,before);
        }
    }
    #[test]
    fn category_and_combined_underflow_checks_preserved_on_real_shrink(){
        // A same-target completion has difference zero. To execute existing
        // checked_sub failure branches, deliberately ask the unchanged normalizer
        // for a real shrink against one malformed counter at a time.
        for category in [true,false]{let mut c=fixture();let selected=c.construction.as_ref().unwrap().bytes;
            let retained=c.snapshot_commit_storage_v1(A).unwrap();assert_eq!(retained-selected,A);
            if category{c.reservations.construction.current=A-1}else{c.reservations.combined.current=A-1}
            let before=c.reservations;let dropped=Cell::new(false);
            let f=c.end_construction_phase_with_wasi(Dropped(&dropped),selected,Some(wasi())).unwrap_err();
            assert!(dropped.get());assert_failure(&c,f,"swift_run_release_underflow",SwiftCleanupInvariant::ReservationUnderflow);
            assert_eq!(c.reservations,before);assert_eq!(c.construction.as_ref().unwrap().bytes,retained);
        }
    }
    #[test]
    fn storage_is_dropped_before_missing_fault_and_success(){
        for missing in [true,false]{let mut c=fixture();let retained=c.snapshot_commit_storage_v1(A).unwrap();
            if missing{c.construction=None}let dropped=Cell::new(false);
            let result=c.end_construction_phase_with_wasi(Dropped(&dropped),retained,Some(wasi()));
            assert!(dropped.get());assert_eq!(result.is_err(),missing);
        }
    }
    #[test]
    fn refused_completion_drops_storage_without_touching_ledger_or_fault(){
        let mut c=fixture();let before=c.reservations;let bytes=c.construction.as_ref().unwrap().bytes;
        assert_eq!(complete(&mut c,0,Some(wasi()),false),Ok(()));assert_eq!(c.reservations,before);
        assert_eq!(c.construction.as_ref().unwrap().bytes,bytes);assert_eq!(c.first_failure,None);
    }
    #[test]
    fn commit_storage_refusal_is_atomic(){
        let mut c=fixture();let before=c.reservations;let bytes=c.construction.as_ref().unwrap().bytes;
        c.budget.combined_bytes=before.combined.current+A-1;
        assert_eq!(c.snapshot_commit_storage_v1(A),Err(SnapshotAdmissionErrorV1::Storage{
            current:before.combined.current,additional:A,limit:before.combined.current+A-1}));
        assert_eq!(c.reservations,before);assert_eq!(c.construction.as_ref().unwrap().bytes,bytes);
    }
    #[test]
    fn commit_missing_owner_layout_and_cancellation_refusals_are_atomic(){
        for fault in 0..4{let mut c=fixture();let expected=match fault{
            0=>{c.construction=None;SnapshotAdmissionErrorV1::Layout},
            1=>{c.construction.as_mut().unwrap().owner=43;SnapshotAdmissionErrorV1::Owner},
            2=>{c.reservations.construction.current-=1;SnapshotAdmissionErrorV1::Layout},
            _=>{c.cancellation.cancel();SnapshotAdmissionErrorV1::Stop(SnapshotStopV1::Cancelled)},
        };let before=c.reservations;let ticket=c.construction.as_ref().map(|x|(x.owner,x.category,x.bytes));
            assert_eq!(c.snapshot_commit_storage_v1(A),Err(expected));assert_eq!(c.reservations,before);
            assert_eq!(c.construction.as_ref().map(|x|(x.owner,x.category,x.bytes)),ticket);
        }
    }
}
