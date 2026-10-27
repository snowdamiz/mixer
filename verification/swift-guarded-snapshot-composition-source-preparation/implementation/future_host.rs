
// Compiled in unit mode, deliberately has no test/CLI/export dispatch. A later
// root-selected fresh host can invoke this after exact floor/work/stop release.
#[cfg(test)]
mod future_genuine_composition_v1 {
    use super::*;
    use crate::{Cancellation,experimental_swift_reactor::retained_profile_loader_v1::SelectedValidatedProfileV1};
    use crate::experimental_wasi::{WasiBudget,WasiGrants};
    use std::time::Instant;
    use std::fs::OpenOptions;
    pub(super) fn selected_owned_files_v1(
        selected:SelectedValidatedProfileV1,directory:&std::path::Path,
        wasi:Option<(WasiBudget,WasiGrants)>,
    ){
        // The loader-produced opaque carrier is mandatory. No proof/digest/bool
        // can turn the fixture into authentic selected ingress.
        let mut scope=match selected.into_snapshot_scope_v1(
            selected_initial_profile_v1().budget,Instant::now(),Cancellation::default()){
            Ok(scope)=>scope,
            Err(failure)=>panic!("genuine selected ingress failed: {:?}; retirement {:?}",failure.primary,failure.retirement),
        };
        if let Some((budget,grants))=wasi {
            let attachment=scope.attach_wasi_v1(grants,budget,Instant::now());
            assert!(attachment.construction.is_ok());assert!(attachment.completion.is_ok());
        }
        let mut rows=OpenOptions::new().read(true).write(true).create_new(true).open(directory.join("fresh-primary.rows")).unwrap();
        let mut snapshot=OpenOptions::new().read(true).write(true).create_new(true).open(directory.join("fresh-selected.mixsnb02")).unwrap();
        let claims=UnverifiedProfileDigestBytesV1 {baseline:[1;32],candidate:[2;32],original_input:[3;32],event_schema:[4;32],
            profile_adapter_binary:[5;32],layout_receipt:[6;32],original_validated_snapshot:[7;32],profile_row_body:[8;32]};
        let run=scope.construct_v1(&claims,&mut rows,&mut snapshot);
        let outer=run.outer_v1();
        match &outer.primary {
            InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows:Ok(_)}=>{
                assert_eq!(&header.bytes[..8],b"MIXPRF01");
                std::fs::write(directory.join("fresh-primary.header"),header.bytes).unwrap();
            },_=>panic!("original successful primary was not preserved"),
        }
        match &outer.export {
            SnapshotAttemptV1::Completed(observation)=>{
                assert!(observation.bytes>=2560);assert!(observation.calls>0);
                assert_eq!(snapshot.metadata().unwrap().len(),observation.bytes);
            },_=>panic!("future positive requires separately accepted debit/floor; no success from preparation"),
        }
        assert!(outer.phase_completion.is_ok());
        let finish=run.finish_v1();
        assert!(finish.primary_retirement.adopted_retirement.is_ok());
        assert!(finish.scope_adopted_retirement.is_ok());
        assert!(finish.wasi_retirement.is_ok());
        // Current conservative finalizer is explicitly not healthy cleanup.
        assert_eq!(finish.usage.cleanup_invariant,Some(super::super::super::control::SwiftCleanupInvariant::ConstructionBound));
        assert!(finish.usage.reservations.construction.current>0);
        assert!(finish.usage.reservations.live_tickets>0);
        // File close/custody and release qualification remain the fresh host's
        // independent responsibility; these borrows end at this fixture return.
    }
}
