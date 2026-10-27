// Independent tests in reconstructed real control module. The capture hook
// records the actual final-check/refusal failure before any consuming cleanup.
#[cfg(test)]
static INDEPENDENT_ORIGINAL_PRIMARY_V1: std::sync::Mutex<Option<SwiftRunFailure>> = std::sync::Mutex::new(None);
#[cfg(test)]
mod independent_correction_control_tests {
    use super::*;
    use crate::experimental_swift_reactor::{validate_swift_reactor,SwiftValidationBudget};
    use crate::experimental_wasi::WasiFunction;
    use crate::Type;
    /* ACCEPTED_PROOF_BUILDER */
    fn failed(budget:SwiftRunBudget,boundary:CorrectionBoundaryV1,ticket:Option<ReservationTicket>)
        -> (CorrectionPreScopeFailureV1,SwiftRunFailure) {
        assert!(INDEPENDENT_ORIGINAL_PRIMARY_V1.lock().unwrap().take().is_none());
        let result=RuntimeControl::correction_probe_adopt_body_v1(AdoptionBodyV1::ordinary(proof()),
            budget,Instant::now(),Cancellation::default(),boundary,correction_early_v1(ticket));
        let error=match result {Err(error)=>error,Ok(_)=>panic!("expected actual admission failure")};
        let captured=INDEPENDENT_ORIGINAL_PRIMARY_V1.lock().unwrap().take().unwrap();
        assert_eq!(captured.after_cleanup,None);
        let mut returned=error.primary;returned.after_cleanup=None;
        assert_eq!(returned,captured,"every original primary field must survive cleanup");
        (error,captured)
    }
    #[test]
    fn exact_final_check_primary_and_retained_charge() {
        for boundary in [CorrectionBoundaryV1::FinalCancel,CorrectionBoundaryV1::FinalDeadline] {
            let (error,captured)=failed(SwiftRunBudget::default(),boundary,None);
            let (kind,code)=match boundary {
                CorrectionBoundaryV1::FinalCancel=>(SwiftRunFailureKind::Cancelled,"swift_run_cancelled"),
                CorrectionBoundaryV1::FinalDeadline=>(SwiftRunFailureKind::Deadline,"swift_run_deadline"),
                _=>unreachable!(),
            };
            assert_eq!(captured.kind,kind);assert_eq!(captured.code,code);
            assert_eq!(captured.stage,SwiftRunStage::Adoption);
            assert_eq!(captured.deadline_origin,SwiftDeadlineOrigin::Run);
            assert_eq!((captured.function,captured.offset,captured.resource),(None,None,None));
            assert_eq!((captured.attempted,captured.limit,captured.observed_capacity),(0,0,None));
            assert_eq!((captured.wasi_failure,captured.guest_exit),(None,None));
            let at=captured.at_failure;
            let enlarged=foundation_construction_bytes().unwrap()+size_of::<CorrectionPreScopePlacesV1>();
            assert_eq!(at.reservations.construction.current,enlarged);
            assert_eq!(at.reservations.live_tickets,5);
            assert_eq!(error.retirement,Ok(()));
            let after=error.primary.after_cleanup.unwrap();
            assert_eq!(after.reservations.retained_source.current,0);
            assert_eq!(after.reservations.retained_metadata.current,0);
            assert_eq!(after.reservations.shared.current,0);
            assert_eq!(after.reservations.construction.current,enlarged);
            assert_eq!(after.reservations.construction.peak,at.reservations.construction.peak);
            assert_eq!(after.reservations.combined.current,enlarged);
            assert_eq!(after.reservations.combined.peak,at.reservations.combined.peak);
            assert_eq!(after.reservations.live_tickets,1);
            assert_eq!(after.cleanup_invariant,Some(SwiftCleanupInvariant::ConstructionBound));
            println!("independent final check {:?}: exact primary preserved, retained={} tickets=1 invariant=ConstructionBound",kind,enlarged);
        }
    }
    #[test]
    fn exact_preconstruction_primary_and_actual_ticket_prefixes() {
        for (index,budget) in [SwiftRunBudget {source_bytes:0,..SwiftRunBudget::default()},
            SwiftRunBudget {metadata_bytes:0,..SwiftRunBudget::default()},
            SwiftRunBudget {combined_bytes:foundation_construction_bytes().unwrap()-1,..SwiftRunBudget::default()}]
            .into_iter().enumerate() {
            let (error,captured)=failed(budget,CorrectionBoundaryV1::None,None);
            assert_eq!(captured.at_failure.reservations.construction.current,0);
            if index==0 {
                assert_eq!(captured.resource,Some(SwiftRunResource::Reservation(SwiftReservationCategory::RetainedSource)));
                assert_eq!(captured.at_failure.reservations.live_tickets,0);
            } else if index==1 {
                assert_eq!(captured.resource,Some(SwiftRunResource::Reservation(SwiftReservationCategory::RetainedMetadata)));
                assert!(captured.at_failure.reservations.retained_source.current>0);
                assert_eq!(captured.at_failure.reservations.live_tickets,1);
            } else {
                assert!(captured.at_failure.reservations.retained_source.current>0);
                assert!(captured.at_failure.reservations.retained_metadata.current>0);
                assert_eq!(captured.at_failure.reservations.live_tickets,4);
            }
            let after=error.primary.after_cleanup.unwrap();
            assert_eq!(after.reservations.combined.current,0);
            assert_eq!(after.reservations.live_tickets,0);
            assert_eq!(after.cleanup_invariant,None);
            assert_eq!(error.retirement,Ok(()));
            println!("independent preconstruction {}: exact primary preserved, live ticket prefix={}",index,captured.at_failure.reservations.live_tickets);
        }
    }
    #[test]
    fn foreign_retirement_preserves_captured_primary_and_conservative_foreign_owner() {
        let (mut foreign,adopted)=RuntimeControl::adopt(proof(),SwiftRunBudget::default(),Instant::now(),Cancellation::default()).unwrap();
        let ticket=foreign.admit(SwiftReservationCategory::State,1,Cursor::adoption()).unwrap();
        let (error,captured)=failed(SwiftRunBudget::default(),CorrectionBoundaryV1::FinalCancel,Some(ticket));
        assert_eq!(captured.kind,SwiftRunFailureKind::Cancelled);
        assert_eq!(captured.at_failure.cleanup_invariant,None);
        assert_eq!(error.retirement,Err(captured));
        let after=error.primary.after_cleanup.unwrap();
        assert_eq!(after.cleanup_invariant,Some(SwiftCleanupInvariant::ReservationOwner));
        assert_eq!(after.reservations.combined.current,after.reservations.construction.current);
        assert_eq!(after.reservations.live_tickets,1);
        foreign.drop_proof(adopted).unwrap();
        let foreign_after=foreign.finish_owned_cleanup(None);
        assert_eq!(foreign_after.reservations.state.current,1);
        assert_eq!(foreign_after.reservations.combined.current,1);
        assert_eq!(foreign_after.reservations.live_tickets,1);
        println!("independent retirement: exact original primary retained, actual ReservationOwner fault, foreign state=1 remains charged");
    }
}
