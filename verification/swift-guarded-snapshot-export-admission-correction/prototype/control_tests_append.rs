#[derive(Clone,Copy)]
enum CorrectionBoundaryV1 { None, FinalCancel, FinalDeadline }
fn correction_early_v1(ticket:Option<ReservationTicket>)->CorrectionEarlyStorageV1 {
    CorrectionEarlyStorageV1 {ingress_body:None,profile:CorrectionFoundationProfileV1::Snapshot,
        scope_return:None,caller_return:None,cleanup_return:None,retirement_ticket:ticket}
}
// These controls invoke the reconstructed original admission body only, not any
// initial-profile wrapper, exporter, launcher, or frozen runner.
#[cfg(test)]
mod correction_early_tests {
    use super::*;
    use crate::experimental_swift_reactor::{validate_swift_reactor,SwiftValidationBudget};
    use crate::experimental_wasi::WasiFunction;
    use crate::Type;
    // The runner inserts the unchanged accepted-source proof builder here.
    /* ACCEPTED_PROOF_BUILDER */
    fn failed(budget:SwiftRunBudget,boundary:CorrectionBoundaryV1,ticket:Option<ReservationTicket>)
        ->CorrectionPreScopeFailureV1 {
        match RuntimeControl::correction_probe_adopt_body_v1(AdoptionBodyV1::ordinary(proof()),
            budget,Instant::now(),Cancellation::default(),boundary,correction_early_v1(ticket)) {
            Err(error)=>error,Ok(_)=>panic!("negative boundary did not fail"),
        }
    }
    #[test]
    fn correction_before_construction_failure_keeps_primary_and_zero() {
        for budget in [SwiftRunBudget {source_bytes:0,..SwiftRunBudget::default()},
            SwiftRunBudget {metadata_bytes:0,..SwiftRunBudget::default()},
            SwiftRunBudget {combined_bytes:foundation_construction_bytes().unwrap()-1,..SwiftRunBudget::default()}] {
            let error=failed(budget,CorrectionBoundaryV1::None,None);
            assert_eq!(error.primary.stage,SwiftRunStage::Adoption);
            assert!(error.retirement.is_ok());
            assert_eq!(error.primary.at_failure.reservations.construction.current,0);
            let after=error.primary.after_cleanup.unwrap();
            assert_eq!(after.reservations.combined.current,0);
            assert_eq!(after.reservations.live_tickets,0);
            assert_eq!(after.cleanup_invariant,None);
            println!("PRE_CONSTRUCTION {:?}",error.primary);
        }
    }
    #[test]
    fn correction_final_check_cancel_and_deadline_retain_real_charge() {
        for boundary in [CorrectionBoundaryV1::FinalCancel,CorrectionBoundaryV1::FinalDeadline] {
            let error=failed(SwiftRunBudget::default(),boundary,None);
            let expected=match boundary {CorrectionBoundaryV1::FinalCancel=>SwiftRunFailureKind::Cancelled,
                CorrectionBoundaryV1::FinalDeadline=>SwiftRunFailureKind::Deadline,_=>unreachable!()};
            assert_eq!(error.primary.kind,expected);
            assert_eq!(error.primary.stage,SwiftRunStage::Adoption);
            assert!(error.retirement.is_ok());
            let construction=error.primary.at_failure.reservations.construction.current;
            assert_eq!(construction,foundation_construction_bytes().unwrap()+size_of::<CorrectionPreScopePlacesV1>());
            let after=error.primary.after_cleanup.unwrap();
            assert_eq!(after.reservations.construction.current,construction);
            assert_eq!(after.reservations.combined.current,construction);
            assert_eq!(after.reservations.live_tickets,1);
            assert_eq!(after.cleanup_invariant,Some(SwiftCleanupInvariant::ConstructionBound));
            println!("FINAL_CHECK_RETAINED {:?}",error.primary);
        }
    }
    #[test]
    fn correction_retirement_failure_preserves_actual_primary() {
        let (mut foreign,adopted)=RuntimeControl::adopt(proof(),SwiftRunBudget::default(),Instant::now(),Cancellation::default()).unwrap();
        let ticket=foreign.admit(SwiftReservationCategory::State,1,Cursor::adoption()).unwrap();
        let error=failed(SwiftRunBudget::default(),CorrectionBoundaryV1::FinalCancel,Some(ticket));
        assert_eq!(error.primary.kind,SwiftRunFailureKind::Cancelled);
        assert_eq!(error.primary.code,"swift_run_cancelled");
        assert_eq!(error.primary.at_failure.cleanup_invariant,None);
        // refund's error is the unchanged original first failure; the independent
        // cleanup invariant records the foreign-ticket retirement fault.
        let retirement=error.retirement.unwrap_err();
        let mut expected=error.primary;expected.after_cleanup=None;
        assert_eq!(retirement,expected);
        let after=error.primary.after_cleanup.unwrap();
        assert_eq!(after.cleanup_invariant,Some(SwiftCleanupInvariant::ReservationOwner));
        assert!(after.reservations.construction.current>foundation_construction_bytes().unwrap());
        assert_eq!(after.reservations.combined.current,after.reservations.construction.current);
        // The genuine foreign owner remains conservatively charged for its lost
        // ticket; no fixture repairs or counterfeit refunds are performed.
        foreign.drop_proof(adopted).unwrap();
        let foreign_after=foreign.finish_owned_cleanup(None);
        assert_eq!(foreign_after.reservations.state.current,1);
        assert_eq!(foreign_after.reservations.combined.current,1);
        println!("RETIREMENT_ERROR primary={:?} retirement={:?} foreign={:?}",error.primary,retirement,foreign_after);
    }
}
