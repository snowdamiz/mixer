// INTERFACE SKETCH ONLY. Not included, compiled, selected or executable.
// Abbreviated opaque types below require private concrete implementations;
// declarations inside this comment are not evidence of a constructor or proof.
// Existing selected_parent_account_v1/selected_outer_request_v1/quote stay Pending.

/*
#[cfg(all(target_os = "macos", mixer_bootstrap_one_fixture_v1))]
mod prepaid_input_owner_v1 {
    use std::{fs::File, path::Path};
    use std::os::unix::ffi::OsStrExt;

    // These fields/call/return frames are externally provided child startup P0.
    // Never parsed from argv/env/input/review or inferred from digest equality.
    struct FixtureBootstrapPolicyV1 {
        acquisition: ReviewedAcquisitionQuoteV1,
        identity_caps: [usize; 12],
        path_caps: [usize; 5],
        packet_cap: usize,
        fd_base: i32,
        // Exact original validation and all17 product limits remain explicit.
        execution_policy: SourceReviewedFixtureExecutionPolicyV1,
    }
    impl FixtureBootstrapPolicyV1 {
        // Private body eventually contains reviewed fixed constants only.
        // No numeric/digest argument; source-root provides authority externally.
        // Not implemented/selected by this proposal.
        fn selected_fixture_v1() -> Self;
    }
    struct ReviewedAcquisitionQuoteV1 {
        // Sum of every work path incl. failure/destruction, all12 body caps,
        // path packet peak,2x5 path caps, allocations/slack/diagnostics,
        // future inline/caller/root/return overlap and inherited File resources.
        acquisition_work: u64,
        cleanup_work: u64, // separately unavailable to acquisition, reserved first
        peak_storage: u64,
    }
    struct BootstrapLedgerV1 { /* private Cell counters + source policy */ }
    impl BootstrapLedgerV1 {
        // Exact private acquisition-root constructor. The source-reviewed fixed
        // policy is constructed inside; there are zero unverified arguments.
        // Its call/return/ledger frames were already externally startup-funded.
        // This does not construct the still-Pending child TrustedHostAccountV1.
        fn from_preexisting_fixture_startup_v1() -> Self;
    }
    struct AcquisitionReservationV1<'r> {
        /* affine, borrowed root; separate operation and cleanup tickets;
           no refund without complete actual carrier retirement */
    }
    struct PaidOperationV1<'r> { /* affine debit before one bounded operation */ }

    // No public trait/provider/callback can construct any opaque paid owner.
    fn reserve_before_any_input_effect_v1<'r>(
        root: &'r BootstrapLedgerV1, quote: ReviewedAcquisitionQuoteV1,
    ) -> Result<AcquisitionReservationV1<'r>, OriginalBootstrapRefusalV1>;

    struct RetainedIdentityFileV1 {
        role: IdentityRoleV1,
        file: File,
        initial: ActualFileIdentity64V1,
        body: ImmutableOwnedBytesV1, // actual full bytes, capacity paid up front
        sha256: [u8; 32],
    }
    struct NativePathBackingV1 {
        native: [ImmutableOwnedBytesV1; 5],
        retained: [ImmutableOwnedBytesV1; 5], // separate owners; no alias credit
    }
    struct AcquiredUnverifiedOwnerV1 {
        identities: [RetainedIdentityFileV1; 12],
        paths: NativePathBackingV1,
        path_packet: RetainedPathPacketFileAndBufferV1,
        original_claims: UnverifiedProfileDigestBytesV1,
        original_policy: SourceReviewedFixtureExecutionPolicyV1,
    }
    struct AdmittedImmutableOwnerV1 {
        actual: AcquiredUnverifiedOwnerV1,
        custody: TrustedLocalLauncherCustodyV1, // not from bytes/digest constructor
    }
    // One affine carrier includes all13 raw/validated/adopted/retired slots,
    // adoption bitmap, every partial File and path-packet owner/buffer. Raw slots
    // without reviewed safe retirement retain the ENTIRE reservation; no close.
    enum AcquisitionOutcomeV1 {
        Acquired(AcquiredUnverifiedOwnerV1),
        Refused { original: OriginalAcquisitionFailureV1,
                  partial: PartialActualOwnersV1 },
    }

    // Source-root private fixture boundary only. A native startup adapter must
    // establish single-thread/no-close-handler,13 valid fixed slots, no prior
    // Rust owner, one-time bitmap, pairwise distinct dev/inode and no FD races
    // before any unsafe conversion. No unchecked rawfd-to-File code is proposed.
    // Adopts13 slots after reservation; metadata/native validation are prepaid.
    // EOF32, block4096; checked actual metadata extents/caps before allocation.
    // Original OS/std errors/partial buffers/files stay inside prepaid outcome.
    fn acquire_inherited_inputs_once_v1(
        paid: AcquisitionReservationV1<'_>, policy: &FixtureBootstrapPolicyV1,
    ) -> PrepaidAcquisitionOutcomeV1;

    // Concrete Darwin bridge, no user callback: actual file/body SHA checks,
    // process observations, external trusted-local custody and review provenance.
    // Before each native effect it consumes the corresponding paid operation.
    // Source146+host11+final closure;5 compiled slots; actual12 full bodies;
    // build/session/process/nonce equality; final same-handle metadata checks.
    fn verify_owned_once_v1(
        paid: &mut AcquisitionReservationV1<'_>,
        acquired: AcquiredUnverifiedOwnerV1,
        custody: TrustedLocalLauncherCustodyV1,
    ) -> Result<AdmittedImmutableOwnerV1, OriginalOwnedAdmissionRefusalV1>;

    // Returns only borrows of the outer actual owner, never self references.
    fn scoped_binding_v1<'p0>(owner: &'p0 AdmittedImmutableOwnerV1)
        -> PreexistingImmutableBindingV1<'p0>;

    // Opaque private derivation from verified LIVE owner state, with the exact
    // reservation/generation and all backing/File borrows retained through the
    // one consuming request. No caller dictionary/parts constructor exists.
    struct AdmittedLoaderCorrespondenceV1<'owner> {
        owner: &'owner AdmittedImmutableOwnerV1,
        validation: SwiftValidationBudget, // all five fields
        source_extent: u64,
        source: [u8; 32], manifest: [u8; 32], build: [u8; 32],
        session: [u8; 32], executable: [u8; 32], nonce: [u8; 32],
        identities: [ActualFileIdentity64V1; 4], // complete eight-field records
    }

    // Fixed ingress/custody program prepaid from the existing operation/storage
    // reservation BEFORE admission is published, with separately reserved cleanup.
    // One attempt+carrier, four File slots, four buffer slots, original error and
    // replay-refusal slots. All quantities/prices/actual layouts remain Pending.
    // The Python host model uses12 synthetic units in each operation/storage
    // dimension, NEVER a native quote or a newly minted cleanup allowance.
    struct PrepaidCorrelationAttemptV1<'r> { /* affine, no public constructor */ }
    struct SuppliedLoaderCarrierV1 { /* candidate OR retained unresolved obligation */ }
    enum OwnedCorrelationOutcomeV1 {
        Correlated { owners: AllOriginalAndSelectedOwnersV1 },
        Refused { original: OriginalCorrelationRefusalV1,
                  owners: AllSafelyCapturedOwnersV1,
                  unresolved: StickyUnresolvedExternalObligationsV1 },
    }
    // The consuming boundary runs BEFORE forbidden legacy expected arguments,
    // copied/foreign/stale view checks, or selected/File/buffer shape checks.
    // Retain carrier first; capture at most4 distinct safe Files and4 paid bodies.
    // Never unsafe-adopt invalid/raw/already-controlled or foreign handles.
    // Retirement consults that captured roster, never unchecked public fields.
    // Missing buffers may refuse yet retire every represented owner. Oversize,
    // unknown, foreign or unsafe ownership sets sticky unresolved retention:
    // no complete retirement token; WHOLE charge remains, no claimed raw close.
    // A replay has only one prepaid refusal slot, no new collection walk/capture
    // or close grant. Further objects/work remain caller-side external obligations;
    // conservative charge retention does not grant unlimited whole-host handling.
    // Fixed capture metadata retires within existing results/carrier steps;
    // ordinary complete distinct-handle model retirement still needs exactly47.
    // No generation change creates tickets, a new attempt, or ownership authority.

    // MINIMUM existing-route-compatible change: called before leaf dispatch.
    // New helper inside loader can read its private provenance, and refuses on
    // any difference from actual admitted source/manifest/build/session/exe/
    // nonce/validation/extent/all4 FileIdentity64 records. Existing opens,
    // hashes/process checks/metadata checks stay. Both complete owner sets paid.
    fn correlate_admitted_loader_v1(
        attempt: PrepaidCorrelationAttemptV1<'_>,
        selected: SuppliedLoaderCarrierV1,
        expected: &AdmittedLoaderCorrespondenceV1<'_>, // private verified-owner derivation only
        rejected_legacy_expected: Option<ForbiddenCallerExpectedArgumentV1>,
    ) -> OwnedCorrelationOutcomeV1;

    // Python synthetic-session schema only: exact top/nested keys, five64-hex
    // digest/nonce strings, exactly5 positive-u64 limits, positive-u64 extent;
    // source identity has exact8 integer fields (no bool/float): unsigned-u64
    // device/inode/length/mode, signed-i64 mtime/mtime_ns/ctime/ctime_ns, regular
    // mode. Validate before equality/expected derivation, compare decoded complete
    // typed source identity+extent with acquired File owner. Negative signed times
    // remain valid. This is NOT a real manifest parser/authentication/native bridge.

    // ALTERNATIVE only: new private execution route moves SAME File owners out
    // outer owner; only output rows/snapshot paths are create_new-opened.
    // Inner path/identity views must end before moving corresponding owners.
    // Implementation should destructure into separate file/backing places first,
    // borrow backing, then move files; no move of a currently borrowed struct.
    struct AdmittedExecutionInputsV1 { source: File, build: File,
        session: File, executable: File, identities: [ActualFileIdentity64V1; 4] }
    fn run_prepaid_admitted_fixture_v1(
        account: &TrustedHostAccountV1,
        inputs: AdmittedExecutionInputsV1,
        fixture: FrozenFixtureV1<'_>,
    ) -> Result<PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>, RefusalV1>;
    fn load_preopened_selected_retained_profile_v1(
        inputs: AdmittedExecutionInputsV1,
        budget: SwiftValidationBudget,
        cancellation: &Cancellation,
    ) -> LoaderOutcomeV1;

    // Entry source sequence, not code supplied by this proposal:
    // external startup P0 -> private zero-argument acquisition ledger/policy
    // constructor -> reserve all
    // acquisition -> adopt/meta/read/own -> verify -> split actual backing/files
    // -> scoped shared binding -> reserve all6 child components
    // -> existing setup/loader opens -> private admitted-owner correlation
    // -> leaf only after complete correlation -> consume result -> end all views
    // SAME-handle loading above is OPTIONAL, a larger unselected route.
    // -> destroy all backing/files/errors/carriers -> return token -> release.
    // Any refusal returns original owners; unwind/no token never refunds.
}
*/
