fn independent_normalize_usage(mut u: super::super::control::SwiftRunUsage) -> super::super::control::SwiftRunUsage {
    u.elapsed_micros=0;
    u.deadline_overshoot_micros=0;
    u.validation.elapsed_micros=0;
    u
}
fn independent_normalize_failure(mut f: SwiftRunFailure) -> SwiftRunFailure {
    f.at_failure=independent_normalize_usage(f.at_failure);
    f.after_cleanup=f.after_cleanup.map(independent_normalize_usage);
    f
}
fn independent_selected_controls(selected: SelectedValidatedProfileV1, case: &str) {
    use super::super::control::*;
    if let Some(field)=case.strip_prefix("independent-parity-") {
        let proof=validate_swift_reactor(&fixture(), SwiftValidationBudget::default(), &Cancellation::default()).unwrap();
        let mut budget=SwiftRunBudget::default();
        let ordinary_cancel=Cancellation::default();
        let selected_cancel=Cancellation::default();
        match field {
            "source"=>budget.source_bytes=0,
            "metadata"=>budget.metadata_bytes=0,
            "combined"=>budget.combined_bytes=0,
            "invalid"=>budget.source_bytes+=1,
            "cancelled"=>{ordinary_cancel.cancel();selected_cancel.cancel();},
            "deadline"=>budget.deadline_ms=0,
            _=>panic!("independent field"),
        }
        let ordinary=match RuntimeControl::adopt(proof,budget,Instant::now(),ordinary_cancel) {
            Err(f)=>f,Ok(_)=>panic!("ordinary refusal expected"),
        };
        let selected=match selected.adopt(budget,Instant::now(),selected_cancel) {
            Err(f)=>f,Ok(_)=>panic!("selected refusal expected"),
        };
        assert_eq!(independent_normalize_failure(ordinary),independent_normalize_failure(selected));
        let after=selected.after_cleanup.unwrap();
        assert_eq!((after.reservations.combined.current,after.reservations.live_tickets,after.cleanup_invariant),(0,0,None));
        println!("SELECTED_OUTCOME\t{case}\tindependent_direct_full_failure_payload_parity_except_elapsed");
        return;
    }
    if let Some(field)=case.strip_prefix("independent-refund-") {
        let expected=test_provenance_encoding_v1(selected.test_provenance_v1());
        let (control,adopted)=selected.adopt(SwiftRunBudget::default(),Instant::now(),Cancellation::default()).unwrap();
        assert_eq!(test_provenance_encoding_v1(adopted.selected_provenance().unwrap()),expected);
        super::super::control::independent_refund_faults(control,adopted,field);
        println!("SELECTED_OUTCOME\t{case}\tindependent_synthetic_ticket_fault_quarantined");
        return;
    }
    if let Some(edge)=case.strip_prefix("independent-boundary-") {
        let validation=selected.proof.usage();
        let floor=foundation_construction_bytes().unwrap();
        let before=validation.source_bytes+validation.metadata_reserved+std::mem::size_of::<RuntimeControl>()+Cancellation::requested_backing_layout().size();
        let combined=before+floor;
        let combined=match edge {"below"=>combined-1,"equal"=>combined,"above"=>combined+1,_=>panic!("edge")};
        let budget=SwiftRunBudget {combined_bytes:combined,..SwiftRunBudget::default()};
        match selected.adopt(budget,Instant::now(),Cancellation::default()) {
            Err(f)=>{
                assert_eq!(edge,"below");assert_eq!(f.kind,SwiftRunFailureKind::CombinedExhausted);
                assert_eq!(f.attempted as usize,before+floor);assert_eq!(f.limit as usize,combined);
                assert_eq!(f.at_failure.reservations.combined.current,before);
                assert_eq!(f.at_failure.reservations.construction.current,0);
                let after=f.after_cleanup.unwrap();assert_eq!((after.reservations.combined.current,after.reservations.live_tickets),(0,0));
            },
            Ok((mut control,adopted))=>{
                assert_ne!(edge,"below");assert!(adopted.selected_provenance().is_some());
                let usage=control.usage(None);assert_eq!(usage.reservations.construction.current,floor);
                assert_eq!(usage.reservations.combined.current,before+floor);
                control.drop_proof(adopted).unwrap();let after=control.finish_owned_cleanup(None);
                assert_eq!((after.reservations.combined.current,after.reservations.live_tickets,after.cleanup_invariant),(0,0,None));
            },
        }
        println!("SELECTED_OUTCOME\t{case}\tindependent_actual_selected_floor_boundary\t{before}\t{floor}\t{combined}");
        return;
    }
    assert_eq!(case,"independent-narrowed");
    assert_eq!(selected.validation_budget(),SwiftValidationBudget {source_bytes:1947,metadata_bytes:1000000,scratch_bytes:65536,work_credits:1000000,deadline_ms:10000});
    super::super::cache::test_selected_initial_outcome_v1(selected,"encoded");
    println!("SELECTED_OUTCOME\t{case}\tindependent_all_five_narrowed_limits_through_actual_cache");
}
