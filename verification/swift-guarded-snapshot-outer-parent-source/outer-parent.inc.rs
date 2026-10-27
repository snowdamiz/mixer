// Source candidate only. Included inside trusted_local_host_account_entry_v1.
// This module supplies no public/exported entry or selected root authority.
mod outer_parent_v1 {
    use super::{
        destroy_returned_fixture_v1, host_account_v1, release_after_retirement_v1,
        run_one_fixture_v1, File, FrozenFixtureV1, LoaderUsageV1,
        OwnedFixtureOutcomeV1, PrepaidOwnedV1, PrimaryOutcomeV1,
        RefusalV1, ReturnedLoaderFilesV1, ReviewedFixtureBindingV1,
        SetupOutcomeV1, UnverifiedProfileDigestBytesV1,
    };
    use super::host_account_v1::UsageV1;
    use crate::Cancellation;

    const SELECTED_SOURCE_BYTES_V1: usize = 1947;
    const SELECTED_SOURCE_SHA256_V1: [u8; 32] = [
        0x98, 0x04, 0x73, 0x85, 0x23, 0xf3, 0x05, 0x3f,
        0x2b, 0x7a, 0x00, 0x93, 0xec, 0xd5, 0xb3, 0x24,
        0xec, 0xf5, 0x4b, 0x1d, 0x43, 0x09, 0x49, 0x93,
        0xcd, 0xb2, 0xee, 0x7d, 0x63, 0x74, 0x78, 0x06,
    ];
    const SELECTED_VALIDATION_LIMITS_V1: [u64; 5] =
        [1947, 1_000_000, 65_536, 1_000_000, 10_000];

    // A future independently reviewed producer must retain these exact actual
    // preimages, not merely a digest that claims they once existed. No values
    // for future build/session/executable/compiler/process identities exist here.
    struct ImmutableIdentityPreimageV1 {
        bytes: &'static [u8],
        sha256: [u8; 32],
    }
    struct ImmutableFixtureIdentitiesV1 {
        source: ImmutableIdentityPreimageV1,
        build: ImmutableIdentityPreimageV1,
        session: ImmutableIdentityPreimageV1,
        executable: ImmutableIdentityPreimageV1,
        compiler: ImmutableIdentityPreimageV1,
        compiler_version: ImmutableIdentityPreimageV1,
        compile_manifest: ImmutableIdentityPreimageV1,
        compile_argv: ImmutableIdentityPreimageV1,
        compile_environment: ImmutableIdentityPreimageV1,
        process_argv: ImmutableIdentityPreimageV1,
        process_environment: ImmutableIdentityPreimageV1,
        review: ImmutableIdentityPreimageV1,
    }
    // Storage is pre-existing P0, including every native Path pointee and all
    // backing reachable through identities/claims. 'static is a lifetime only;
    // it neither prices backing nor grants fixture/root authority. The five
    // path bodies are the exact native encoding of binding.paths in order;
    // the future producer must independently establish that correspondence.
    struct PreexistingImmutableBindingV1 {
        binding: ReviewedFixtureBindingV1,
        native_path_bodies: [&'static [u8]; 5],
        identities: ImmutableFixtureIdentitiesV1,
    }
    // Private, affine one-fixture request. No Clone/Copy, retry, public mint,
    // environment/argv constructor, allocation/leak, or borrowed-output escape.
    struct OneFixtureOuterRequestV1 {
        preexisting: &'static PreexistingImmutableBindingV1,
    }
    enum BindingSelectionRefusalV1 { ImmutableBindingAndP0ReviewPending }
    fn selected_outer_request_v1()
        -> Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>
    {
        // Changing this exact source requires actual immutable identity, full
        // binding/native backing layout, source work and root P0 funding review.
        // The selected source/limits above are constraints, not a fabricated
        // fresh validation, executable, session, path or completed authority.
        Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)
    }

    enum OriginalObservationV1 {
        SetupReadyInRefusal,
        SetupRefused,
        SetupInvariantRefused,
        LoaderRefused,
        PreScopeRefused,
        LeafReturned,
        MissingOwnedPayload,
    }
    // Every member is a shared borrow of an original owner in the charged
    // wrapper. This view cannot outlive that wrapper and contains no callback.
    // Original error/proof/File ownership never moves into an observation.
    enum BorrowedOriginalDiagnosticsV1<'a> {
        Setup(&'a SetupOutcomeV1),
        Loaded {
            original_files: &'a ReturnedLoaderFilesV1,
            original_loader_usage: &'a LoaderUsageV1,
            rows: &'a File,
            snapshot: &'a File,
            cancellation_owner: &'a Cancellation,
            claims_owner: &'a UnverifiedProfileDigestBytesV1,
            primary: &'a PrimaryOutcomeV1,
        },
    }
    fn borrow_original_diagnostics_once_v1<'a>(
        owned: &'a PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>,
    ) -> Option<BorrowedOriginalDiagnosticsV1<'a>> {
        // The sole inspect_v1 occurrence. No cloning, formatting, mutable
        // access, diagnostic source callbacks, file calls or allocation.
        match owned.inspect_v1() {
            None => None,
            Some(OwnedFixtureOutcomeV1::SetupRefused(original)) =>
                Some(BorrowedOriginalDiagnosticsV1::Setup(original)),
            Some(OwnedFixtureOutcomeV1::Loaded {
                original_files, original_loader_usage, rows, snapshot,
                cancellation_owner, claims_owner, primary,
            }) => Some(BorrowedOriginalDiagnosticsV1::Loaded {
                original_files, original_loader_usage, rows, snapshot,
                cancellation_owner, claims_owner, primary,
            }),
        }
    }
    fn observe_borrowed_originals_v1(
        borrowed: Option<BorrowedOriginalDiagnosticsV1<'_>>,
    ) -> OriginalObservationV1 {
        // A finite discrimination is observation only. Every full original
        // typed diagnostic and resource remains in the same charged payload.
        match borrowed {
            None => OriginalObservationV1::MissingOwnedPayload,
            Some(BorrowedOriginalDiagnosticsV1::Setup(original)) => match original {
                SetupOutcomeV1::Ready { .. } => OriginalObservationV1::SetupReadyInRefusal,
                SetupOutcomeV1::Refused { original, files, .. } => {
                    let _original_error_and_file_owners = (original, files);
                    OriginalObservationV1::SetupRefused
                }
                SetupOutcomeV1::InvariantRefused { files } => {
                    let _original_file_owners = files;
                    OriginalObservationV1::SetupInvariantRefused
                }
            },
            Some(BorrowedOriginalDiagnosticsV1::Loaded {
                original_files, original_loader_usage, rows, snapshot,
                cancellation_owner, claims_owner, primary,
            }) => {
                let _original_owners = (original_files, original_loader_usage,
                    rows, snapshot, cancellation_owner, claims_owner);
                match primary {
                    PrimaryOutcomeV1::LoaderRefused(original) => {
                        let _original_loader_failure = original;
                        OriginalObservationV1::LoaderRefused
                    }
                    PrimaryOutcomeV1::Leaf(Err(original)) => {
                        let _original_prescope_failure = original;
                        OriginalObservationV1::PreScopeRefused
                    }
                    PrimaryOutcomeV1::Leaf(Ok(original)) => {
                        let _original_finish_and_retirement = original;
                        OriginalObservationV1::LeafReturned
                    }
                }
            }
        }
    }

    enum RetirementObservationV1 { DestructionTokenReleased, NoDestructionToken }
    // These result places and their scalar usage copies are independently P0.
    // A release observation is no claim of healthy File close/flush/cleanup.
    enum OuterResultV1 {
        BindingPending(BindingSelectionRefusalV1),
        AccountRefused(RefusalV1),
        EntryRefused { original: RefusalV1, before: UsageV1, after: UsageV1 },
        Returned {
            original_observation: OriginalObservationV1,
            retirement: RetirementObservationV1,
            before: UsageV1,
            while_original_payload_owned: UsageV1,
            after_retirement: UsageV1,
        },
    }
    fn run_selected_one_fixture_outer_v1() -> OuterResultV1 {
        let request = match selected_outer_request_v1() {
            Ok(request) => request,
            Err(original) => return OuterResultV1::BindingPending(original),
        };
        consume_outer_request_v1(request)
    }
    fn consume_outer_request_v1(request: OneFixtureOuterRequestV1) -> OuterResultV1 {
        // Before reaching this function, independently provisioned P0 must
        // already cover this frame, policy/account/quote places and all late
        // return/token/result places. Child admission cannot fund this frame.
        let account = match host_account_v1::selected_parent_account_v1() {
            Ok(account) => account,
            Err(original) => return OuterResultV1::AccountRefused(original),
        };
        let before = account.usage_v1();
        let fixture = FrozenFixtureV1 { binding: &request.preexisting.binding };
        let owned = match run_one_fixture_v1(&account, fixture) {
            Ok(owned) => owned,
            Err(original) => {
                let after = account.usage_v1();
                return OuterResultV1::EntryRefused { original, before, after };
            }
        };
        let while_original_payload_owned = account.usage_v1();
        let original_observation = {
            // The sole borrowed view ends before consuming the actual owner.
            let borrowed = borrow_original_diagnostics_once_v1(&owned);
            observe_borrowed_originals_v1(borrowed)
        };
        let retirement = match destroy_returned_fixture_v1(owned) {
            Some(destroyed) => {
                // Both payload and carrier destruction returned first. Token
                // release is mandatory on this normal Some route, exactly once.
                release_after_retirement_v1(destroyed);
                RetirementObservationV1::DestructionTokenReleased
            }
            // No token: no release, no retry and no false healthy-close claim.
            None => RetirementObservationV1::NoDestructionToken,
        };
        let after_retirement = account.usage_v1();
        OuterResultV1::Returned {
            original_observation, retirement, before,
            while_original_payload_owned, after_retirement,
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        #[test]
        fn selected_outer_binding_remains_pending() {
            assert!(matches!(selected_outer_request_v1(),
                Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)));
            assert!(matches!(run_selected_one_fixture_outer_v1(),
                OuterResultV1::BindingPending(_)));
        }
        #[test]
        fn selected_constraints_match_original_source_selection() {
            assert_eq!(SELECTED_SOURCE_BYTES_V1, 1947);
            assert_eq!(SELECTED_VALIDATION_LIMITS_V1,
                [1947, 1_000_000, 65_536, 1_000_000, 10_000]);
            assert_eq!(SELECTED_SOURCE_SHA256_V1[0..4], [0x98, 0x04, 0x73, 0x85]);
        }
    }
}
