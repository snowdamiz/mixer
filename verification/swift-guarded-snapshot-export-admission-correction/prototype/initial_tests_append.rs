#[cfg(test)]
mod correction_reborrow_tests {
    use super::*;
    use crate::{Cancellation,Type};
    use crate::experimental_swift_reactor::{validate_swift_reactor,SwiftValidationBudget};
    use crate::experimental_wasi::WasiFunction;
    use std::time::Instant;
    /* ACCEPTED_PROOF_BUILDER */
    #[test]
    fn correction_admitted_and_refused_own_same_control_until_consumed() {
        for cancelled in [false,true] {
            let token=Cancellation::default();
            let (mut control,adopted)=RuntimeControl::adopt(proof(),SwiftRunBudget::default(),Instant::now(),token.clone()).unwrap();
            let before=control.usage(None);
            if cancelled {token.cancel();}
            let access=CorrectionAccessV1::signature_witness(&mut control);
            assert_eq!(matches!(&access,CorrectionAccessV1::Refused {..}),cancelled);
            {
                let shared=access.shared_control();
                let owner_view=adopted.proof();
                assert_eq!(shared.usage(None).reservations,before.reservations);
                assert_eq!(shared.usage(None).instructions,before.instructions);
                assert!(owner_view.observations().validated_bodies>0);
            }
            access.complete(CorrectionPhaseStorageV1 {plan:None,temporary_output:None}).unwrap();
            control.drop_proof(adopted).unwrap();
            let after=control.finish_owned_cleanup(None);
            assert_eq!(after.reservations.combined.current,0);
            assert_eq!(after.reservations.live_tickets,0);
            assert_eq!(after.cleanup_invariant,None);
            println!("REBORROW cancelled={} {:?}",cancelled,after);
        }
    }
}
