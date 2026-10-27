// Independent actual-control/access diagnostics. Never executes the ABI adapter,
// real wrapper, header/rows helper, or exporter. Real sole-guard helper compiles.
#[cfg(test)]
mod independent_correction_access_tests {
    use super::*;
    use crate::{Cancellation,Type};
    use crate::experimental_swift_reactor::{validate_swift_reactor,SwiftValidationBudget};
    use crate::experimental_wasi::WasiFunction;
    use std::time::Instant;
    /* ACCEPTED_PROOF_BUILDER */
    fn stable(mut usage:SwiftRunUsage)->SwiftRunUsage {
        usage.elapsed_micros=0;usage.deadline_overshoot_micros=0;usage
    }
    #[test]
    fn exact_access_diagnostics_and_all_nonclock_state_preserved() {
        for mode in 0..4 {
            let token=Cancellation::default();
            let (mut control,adopted)=RuntimeControl::adopt(proof(),SwiftRunBudget::default(),Instant::now(),token.clone()).unwrap();
            let existing=if mode==2 {
                token.cancel();Some(control.check(CONSTRUCTION_CURSOR_V1).unwrap_err())
            } else {None};
            if mode==1 {token.cancel();}
            if mode==3 {control.test_expire_deadline();}
            let before=stable(control.usage(None));
            let identity=&control as *const RuntimeControl;
            let access=CorrectionAccessV1::signature_witness(&mut control);
            match (&access,mode) {
                (CorrectionAccessV1::Admitted {previous,..},0)=>assert_eq!(*previous,before.reservations.construction.current),
                (CorrectionAccessV1::Refused {error,..},1)=>assert_eq!(*error,AError::Stop(Stop::Cancelled)),
                (CorrectionAccessV1::Refused {error,..},2)=>assert_eq!(*error,AError::Stop(Stop::Existing(existing.unwrap()))),
                (CorrectionAccessV1::Refused {error,..},3)=>assert_eq!(*error,AError::Stop(Stop::Deadline(before.deadline_origin))),
                _=>panic!("wrong actual access variant"),
            }
            {
                let view=access.shared_control();
                assert_eq!(view as *const RuntimeControl,identity);
                assert_eq!(stable(view.usage(None)),before);
            }
            access.complete(CorrectionPhaseStorageV1 {plan:None,temporary_output:None}).unwrap();
            assert_eq!(stable(control.usage(None)),before);
            let recorded=control.record_cleanup(None);
            if let Some(mut failure)=recorded {
                failure.after_cleanup=None;assert_eq!(Some(failure),existing);
            } else {assert!(existing.is_none());}
            control.drop_proof(adopted).unwrap();
            let after=control.finish_owned_cleanup(None);
            assert_eq!(after.reservations.combined.current,0);
            assert_eq!(after.reservations.live_tickets,0);
            assert_eq!(after.cleanup_invariant,None);
            println!("independent access mode={}: exact variant/diagnostic, same original control, every nonclock usage field unchanged",mode);
        }
    }
}
