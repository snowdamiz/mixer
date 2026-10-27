// Appended only to the frozen compile-only initial_profile_v1 module.
// Neither the account, quote nor fixture has a public mint or an exported route.
#[cfg(mixer_bootstrap_one_fixture_v1)]
mod trusted_local_host_account_entry_v1 {
    use super::{File, UnverifiedProfileDigestBytesV1, run_one_loaded_fixture_v1};
    use crate::experimental_swift_reactor::control::{
        SnapshotPreScopeFailureV1, SnapshotScopeFinishV1, SwiftRunBudget,
    };
    use crate::experimental_swift_reactor::retained_profile_loader_v1::{
        load_selected_retained_profile_v1, LoaderFailureV1, LoaderOutcomeV1,
        LoaderUsageV1, ReturnedLoaderFilesV1, SelectedValidatedProfileV1,
    };
    use crate::experimental_swift_reactor::SwiftValidationBudget;
    use crate::Cancellation;
    use std::{fs::OpenOptions, io, path::Path, time::Instant};

    mod host_account_v1 {
        include!("initial_profile_v1/host_account_v1.rs");
    }
    use host_account_v1::{PrepaidOwnedV1, RefusalV1, TrustedHostAccountV1};

    // The future root selects and reviews this immutable binding before P1.
    // No binding or token constructor is selected in this packet. Root must
    // fund this backing as P0 and bind paths/claims/limits/source/tool identities.
    struct ReviewedFixtureBindingV1 {
        paths: [&'static Path; 5],
        claims: UnverifiedProfileDigestBytesV1,
        original_validation_budget: SwiftValidationBudget,
        product_budget: SwiftRunBudget,
    }
    // Not Clone/Copy. Consumed on every success/refusal; no retry entry exists.
    struct FrozenFixtureV1 { binding: &'static ReviewedFixtureBindingV1 }

    enum SetupOutcomeV1 {
        Ready { source: File, build: File, session: File, rows: File, snapshot: File },
        Refused { stage: usize, original: io::Error, files: [Option<File>; 5] },
        InvariantRefused { files: [Option<File>; 5] },
    }

    enum PrimaryOutcomeV1 {
        LoaderRefused(LoaderFailureV1),
        Leaf(Result<SnapshotScopeFinishV1, SnapshotPreScopeFailureV1>),
    }

    enum OwnedFixtureOutcomeV1 {
        SetupRefused(SetupOutcomeV1),
        Loaded {
            original_files: ReturnedLoaderFilesV1,
            original_loader_usage: LoaderUsageV1,
            rows: File,
            snapshot: File,
            cancellation_owner: Cancellation,
            claims_owner: UnverifiedProfileDigestBytesV1,
            primary: PrimaryOutcomeV1,
        },
    }

    fn run_one_fixture_v1<'a>(account: &'a TrustedHostAccountV1, fixture: FrozenFixtureV1)
        -> Result<PrepaidOwnedV1<'a, OwnedFixtureOutcomeV1>, RefusalV1>
    {
        // Actual selected quote currently returns WholeQuotePending. No File,
        // loader, argument producer, shared shell or leaf has been called.
        let quote = host_account_v1::selected_whole_quote_v1()?;
        let reservation = account.reserve_whole_v1(quote)?;
        // Both dimensions are committed before the first selected fixture
        // action. FnOnce consumes this ticket and the sole frozen fixture.
        Ok(reservation.dispatch_v1(|| run_prepaid_fixture_v1(fixture)))
    }

    fn setup_files_once_v1(binding: &ReviewedFixtureBindingV1) -> SetupOutcomeV1 {
        let mut files = [None, None, None, None, None];
        for stage in 0..5 {
            let opened = if stage < 3 {
                File::open(binding.paths[stage])
            } else {
                // Never truncate an existing output. A setup error terminates
                // this one attempt and returns all earlier actual File owners.
                OpenOptions::new().write(true).create_new(true).open(binding.paths[stage])
            };
            match opened {
                Ok(file) => files[stage] = Some(file),
                Err(original) => return SetupOutcomeV1::Refused { stage, original, files },
            }
        }
        match files {
            [Some(source), Some(build), Some(session), Some(rows), Some(snapshot)] =>
                SetupOutcomeV1::Ready { source, build, session, rows, snapshot },
            files => SetupOutcomeV1::InvariantRefused { files },
        }
    }

    fn copy_claims_v1(claims: &UnverifiedProfileDigestBytesV1)
        -> UnverifiedProfileDigestBytesV1
    {
        UnverifiedProfileDigestBytesV1 {
            baseline: claims.baseline, candidate: claims.candidate,
            original_input: claims.original_input, event_schema: claims.event_schema,
            profile_adapter_binary: claims.profile_adapter_binary,
            layout_receipt: claims.layout_receipt,
            original_validated_snapshot: claims.original_validated_snapshot,
            profile_row_body: claims.profile_row_body,
        }
    }

    fn run_prepaid_fixture_v1(fixture: FrozenFixtureV1) -> OwnedFixtureOutcomeV1 {
        let binding = fixture.binding;
        let (source, build, session, mut rows, mut snapshot) = match setup_files_once_v1(binding) {
            SetupOutcomeV1::Ready { source, build, session, rows, snapshot } =>
                (source, build, session, rows, snapshot),
            refused => return OwnedFixtureOutcomeV1::SetupRefused(refused),
        };
        let cancellation = Cancellation::default();
        // Exact original five-limit validator budget is retained independently
        // of the host quote and the fixed product 1B/256MiB limits.
        let LoaderOutcomeV1 { selected, files, usage } = load_selected_retained_profile_v1(
            source, build, session, binding.original_validation_budget, &cancellation,
        );
        let claims = copy_claims_v1(&binding.claims);
        let primary = match selected {
            Err(original) => PrimaryOutcomeV1::LoaderRefused(original),
            Ok(selected) => PrimaryOutcomeV1::Leaf(invoke_loaded_leaf_once_v1(
                selected, binding.product_budget, Instant::now(), cancellation.clone(),
                &claims, &mut rows, &mut snapshot,
            )),
        };
        // No diagnostic flattening, fake proof, scalar carrier, close-success
        // assertion or product-store-triggered host refund. Every typed result
        // remains held under the same external reservation through final Drop.
        OwnedFixtureOutcomeV1::Loaded {
            original_files: files, original_loader_usage: usage, rows, snapshot,
            cancellation_owner: cancellation, claims_owner: claims, primary,
        }
    }

    fn invoke_loaded_leaf_once_v1(
        selected: SelectedValidatedProfileV1,
        budget: SwiftRunBudget,
        started: Instant,
        cancellation: Cancellation,
        claims: &UnverifiedProfileDigestBytesV1,
        rows: &mut File,
        snapshot: &mut File,
    ) -> Result<SnapshotScopeFinishV1, SnapshotPreScopeFailureV1> {
        run_one_loaded_fixture_v1(selected, budget, started, cancellation, claims, rows, snapshot)
    }
}
