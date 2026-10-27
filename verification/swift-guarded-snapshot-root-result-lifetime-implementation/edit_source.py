#!/usr/bin/env python3
"""Apply the selected two-member accessible-result lifetime change only."""
from pathlib import Path
P=Path(__file__).resolve().parent/'source/vm/src/experimental_swift_reactor'
p=P/'retained_profile_loader_v1.rs'
s=p.read_text()
start=s.index('    pub(in crate::experimental_swift_reactor) struct AdmittedLoaderCorrespondenceV1')
end=s.index('    // Fixed typed actual carrier;',start)
s=s[:start]+'''    // The owner borrow authenticates the one-shot association; the separate
    // original-root borrow funds every accessible returned original payload.
    pub(in crate::experimental_swift_reactor) struct AdmittedLoaderCorrespondenceV1<'owner, 'root: 'owner> {
        owner_data: &'owner LoaderProvenanceV1, association: u64,
        root: &'root BootstrapLedgerV1,
    }
    pub(in crate::experimental_swift_reactor) struct PrepaidCorrelationAttemptV1<'owner, 'root: 'owner> {
        expected: &'owner LoaderProvenanceV1, live: &'owner Cell<bool>, association: u64,
        root: &'root BootstrapLedgerV1,
    }
    impl<'owner, 'root: 'owner> PrepaidCorrelationAttemptV1<'owner, 'root> {
        pub(in crate::experimental_swift_reactor) fn original_root_v1(&self) -> &'root BootstrapLedgerV1 {
            self.root
        }
    }
    impl<'root, R> AdmittedImmutableOwnerCoreV1<'root, R> {
        fn correlation_scope_core_v1<'owner>(&'owner self)
            -> Result<(AdmittedLoaderCorrespondenceV1<'owner, 'root>, PrepaidCorrelationAttemptV1<'owner, 'root>), BootstrapFailureV1>
        {
            // IR01: scope issue permanently retains the entire acquisition
            // charge, including unused, refused, destroyed or forgotten results.
            self.owned.correlation_retirement_blocked.set(true);
            if self.attempt_taken.replace(true) { return Err(BootstrapFailureV1::AlreadyAttempted); }
            let root = self.owned.reservation.root;
            Ok((AdmittedLoaderCorrespondenceV1 { owner_data: &self.expected, association: self.association, root },
                PrepaidCorrelationAttemptV1 { expected: &self.expected, live: &self.attempt_taken, association: self.association, root }))
        }
    }
    impl<'root> AdmittedImmutableOwnerV1<'root> {
        pub(in crate::experimental_swift_reactor) fn scoped_binding_v1(&self) -> BorrowedOwnerDataV1<'_> {
            use std::os::unix::ffi::OsStrExt;
            let actual = self.0.owned.actual.as_ref().expect("private admitted invariant");
            BorrowedOwnerDataV1 { identities: std::array::from_fn(|i| (body_v1(actual, i).expect("admitted body"),
                    owned_file_v1(actual, i).expect("admitted file").sha256.expect("admitted hash"))),
                paths: std::array::from_fn(|i| Path::new(std::ffi::OsStr::from_bytes(
                    actual.partial.paths.native[i].as_ref().expect("admitted path").slice_v1()))),
                retained_paths: std::array::from_fn(|i| actual.partial.paths.retained[i].as_ref().expect("admitted retained path").slice_v1()),
                claims: &actual.claims, validation: self.0.owned.reservation.root.policy.validation,
                product: self.0.owned.reservation.root.policy.product }
        }
        pub(in crate::experimental_swift_reactor) fn correlation_scope_v1<'owner>(&'owner self)
            -> Result<(AdmittedLoaderCorrespondenceV1<'owner, 'root>, PrepaidCorrelationAttemptV1<'owner, 'root>), BootstrapFailureV1>
        {
            self.0.correlation_scope_core_v1()
        }
    }
''' +s[end:]
start=s.index('    pub(in crate::experimental_swift_reactor) struct CorrelatedSelectedProfileV1')
end=s.index('    fn same_provenance_group_v1',start)
s=s[:start]+'''    // Private complete envelopes only. Field order destroys the payload before
    // the ordinary root-reference field. No durable forgotten-root funding is
    // inferred from this accessible-result lifetime relationship.
    struct RootBoundV1<'root, T> { payload: T, root: &'root BootstrapLedgerV1 }
    impl<'root, T, E> RootBoundV1<'root, Result<T, E>> {
        // Private finite transition: both arms retain the exact same reference.
        fn into_result_v1(self) -> Result<RootBoundV1<'root, T>, RootBoundV1<'root, E>> {
            let Self { payload, root } = self;
            match payload {
                Ok(payload) => Ok(RootBoundV1 { payload, root }),
                Err(payload) => Err(RootBoundV1 { payload, root }),
            }
        }
    }
    impl<'root, A, B> RootBoundV1<'root, (A, B)> {
        // Private diagnostic/test partition; neither original becomes unbound.
        fn split_pair_v1(self) -> (RootBoundV1<'root, A>, RootBoundV1<'root, B>) {
            let Self { payload: (first, second), root } = self;
            (RootBoundV1 { payload: first, root }, RootBoundV1 { payload: second, root })
        }
    }
    struct RawSelectedBundleV1 {
        selected: SelectedValidatedProfileV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1,
    }
    struct CorrelatedSelectedProfileV1<'root>(RootBoundV1<'root, RawSelectedBundleV1>);
    struct RootBoundSelectedProfileV1<'root>(RootBoundV1<'root, RawSelectedBundleV1>);
    impl<'root> CorrelatedSelectedProfileV1<'root> {
        fn into_selected_v1(self) -> RootBoundSelectedProfileV1<'root> { RootBoundSelectedProfileV1(self.0) }
    }
    pub(in crate::experimental_swift_reactor) struct OriginalCorrelationRefusalV1 {
        kind: BootstrapFailureV1, retained_selection: Option<Result<SelectedValidatedProfileV1, LoaderFailureV1>>,
    }
    enum RawCorrelationOutcomeV1 {
        Correlated { selected: SelectedValidatedProfileV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
        LoaderRefused { original: LoaderFailureV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
        Refused { original: OriginalCorrelationRefusalV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
    }
    pub(in crate::experimental_swift_reactor) struct OwnedCorrelationOutcomeV1<'root>(RootBoundV1<'root, RawCorrelationOutcomeV1>);

    #[cfg(mixer_bootstrap_one_fixture_v1)]
    pub(in crate::experimental_swift_reactor) struct FixtureLeafArgumentsV1 {
        pub(in crate::experimental_swift_reactor) rows: File,
        pub(in crate::experimental_swift_reactor) snapshot: File,
        pub(in crate::experimental_swift_reactor) cancellation: Cancellation,
        pub(in crate::experimental_swift_reactor) claims: UnverifiedProfileDigestBytesV1,
        pub(in crate::experimental_swift_reactor) budget: SwiftRunBudget,
        pub(in crate::experimental_swift_reactor) started: Instant,
    }
    #[cfg(mixer_bootstrap_one_fixture_v1)]
    enum RawFixturePrimaryV1 {
        LoaderRefused(LoaderFailureV1),
        CorrelationRefused(OriginalCorrelationRefusalV1),
        Leaf(Result<super::super::control::SnapshotScopeFinishV1, super::super::control::SnapshotPreScopeFailureV1>),
    }
    #[cfg(mixer_bootstrap_one_fixture_v1)]
    struct RawFixtureResultV1 {
        primary: RawFixturePrimaryV1,
        original_files: ReturnedLoaderFilesV1, original_loader_usage: LoaderUsageV1,
        rows: File, snapshot: File, cancellation_owner: Cancellation, claims_owner: UnverifiedProfileDigestBytesV1,
    }
    #[cfg(mixer_bootstrap_one_fixture_v1)]
    pub(in crate::experimental_swift_reactor) struct RootBoundFixtureOutcomeV1<'root>(RootBoundV1<'root, RawFixtureResultV1>);
    #[cfg(mixer_bootstrap_one_fixture_v1)]
    pub(in crate::experimental_swift_reactor) enum RootBoundPrimaryBorrowV1<'view> {
        LoaderRefused(&'view LoaderFailureV1),
        CorrelationRefused(&'view OriginalCorrelationRefusalV1),
        Leaf(&'view Result<super::super::control::SnapshotScopeFinishV1, super::super::control::SnapshotPreScopeFailureV1>),
    }
    #[cfg(mixer_bootstrap_one_fixture_v1)]
    impl<'root> RootBoundFixtureOutcomeV1<'root> {
        pub(in crate::experimental_swift_reactor) fn primary_v1<'view>(&'view self) -> RootBoundPrimaryBorrowV1<'view> {
            match &self.0.payload.primary {
                RawFixturePrimaryV1::LoaderRefused(original) => RootBoundPrimaryBorrowV1::LoaderRefused(original),
                RawFixturePrimaryV1::CorrelationRefused(original) => RootBoundPrimaryBorrowV1::CorrelationRefused(original),
                RawFixturePrimaryV1::Leaf(original) => RootBoundPrimaryBorrowV1::Leaf(original),
            }
        }
        pub(in crate::experimental_swift_reactor) fn usage_v1(&self) -> LoaderUsageV1 { self.0.payload.original_loader_usage }
    }
    impl<'root> OwnedCorrelationOutcomeV1<'root> {
        #[cfg(mixer_bootstrap_one_fixture_v1)]
        pub(in crate::experimental_swift_reactor) fn run_fixture_once_v1(self, args: FixtureLeafArgumentsV1)
            -> RootBoundFixtureOutcomeV1<'root>
        {
            let Self(RootBoundV1 { payload, root }) = self;
            let FixtureLeafArgumentsV1 { mut rows, mut snapshot, cancellation, claims, budget, started } = args;
            // Sole fixed consuming operation. Every raw transition is enclosed
            // in this synchronous original-root frame, with no caller callback.
            let (primary, original_files, original_loader_usage, root) = match payload {
                RawCorrelationOutcomeV1::LoaderRefused { original, files, usage } =>
                    (RawFixturePrimaryV1::LoaderRefused(original), files, usage, root),
                RawCorrelationOutcomeV1::Refused { original, files, usage } =>
                    (RawFixturePrimaryV1::CorrelationRefused(original), files, usage, root),
                RawCorrelationOutcomeV1::Correlated { selected, files, usage } => {
                    let complete = CorrelatedSelectedProfileV1(RootBoundV1 {
                        payload: RawSelectedBundleV1 { selected, files, usage }, root,
                    }).into_selected_v1();
                    let RootBoundSelectedProfileV1(RootBoundV1 {
                        payload: RawSelectedBundleV1 { selected, files, usage }, root,
                    }) = complete;
                    // Uses existing visible methods here; cache's sibling raw
                    // helper and module visibility are unchanged. Both original
                    // result arms are captured before this frame returns.
                    let original = match selected.into_snapshot_scope_v1(budget, started, cancellation.clone()) {
                        Err(original) => Err(original),
                        Ok(scope) => {
                            let run = scope.construct_v1(&claims, &mut rows, &mut snapshot);
                            let _ = run.outer_v1();
                            Ok(run.finish_v1())
                        }
                    };
                    (RawFixturePrimaryV1::Leaf(original), files, usage, root)
                }
            };
            RootBoundFixtureOutcomeV1(RootBoundV1 {
                payload: RawFixtureResultV1 { primary, original_files, original_loader_usage,
                    rows, snapshot, cancellation_owner: cancellation, claims_owner: claims }, root,
            })
        }
    }
''' +s[end:]
start=s.index('    fn correlate_core_v1<R>')
end=s.index('    #[must_use]',start)
s=s[:start]+'''    fn correlate_core_v1<'owner, 'root: 'owner, 'expected_root: 'owner, R>(
        attempt: PrepaidCorrelationAttemptV1<'owner, 'root>, carrier: LoaderCarrierCoreV1<R>,
        expected: &AdmittedLoaderCorrespondenceV1<'owner, 'expected_root>,
    ) -> RootBoundV1<'root, Result<LoaderCarrierCoreV1<R>, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<R>)>>
    {
        // The complete original carrier is already owned before any check.
        // Always use the consumed attempt root, including a foreign expected.
        let root = attempt.root;
        let refusal = if !attempt.live.get() || attempt.association != expected.association
            || !std::ptr::eq(attempt.root, expected.root) { Err(BootstrapFailureV1::LiveOwner) }
            else { same_provenance_group_v1(attempt.expected, expected.owner_data) };
        if let Err(kind) = refusal {
            return RootBoundV1 { payload: Err((OriginalCorrelationRefusalV1 { kind, retained_selection: None }, carrier)), root };
        }
        if let Ok(selected) = &carrier.selected {
            if let Err(kind) = same_provenance_group_v1(&selected.provenance, attempt.expected) {
                return RootBoundV1 { payload: Err((OriginalCorrelationRefusalV1 { kind, retained_selection: None }, carrier)), root };
            }
        }
        RootBoundV1 { payload: Ok(carrier), root }
    }
    pub(in crate::experimental_swift_reactor) fn correlate_admitted_loader_v1<'owner, 'root: 'owner, 'expected_root: 'owner>(
        attempt: PrepaidCorrelationAttemptV1<'owner, 'root>, carrier: SuppliedLoaderCarrierV1,
        expected: &AdmittedLoaderCorrespondenceV1<'owner, 'expected_root>,
    ) -> OwnedCorrelationOutcomeV1<'root> {
        let LoaderOutcomeV1 { selected, files, usage } = carrier.original;
        let ReturnedLoaderFilesV1 { source, build, session, executable } = files;
        let complete = LoaderCarrierCoreV1 { selected, files: [source, build, session], executable, usage };
        match correlate_core_v1(attempt, complete, expected).into_result_v1() {
            Ok(RootBoundV1 { payload: LoaderCarrierCoreV1 { selected, files: [source, build, session], executable, usage }, root }) => {
                let files = ReturnedLoaderFilesV1 { source, build, session, executable };
                let payload = match selected {
                    Ok(selected) => RawCorrelationOutcomeV1::Correlated { selected, files, usage },
                    Err(original) => RawCorrelationOutcomeV1::LoaderRefused { original, files, usage },
                };
                OwnedCorrelationOutcomeV1(RootBoundV1 { payload, root })
            }
            Err(RootBoundV1 { payload: (mut original, LoaderCarrierCoreV1 { selected, files: [source, build, session], executable, usage }), root }) => {
                original.retained_selection = Some(selected);
                OwnedCorrelationOutcomeV1(RootBoundV1 { payload: RawCorrelationOutcomeV1::Refused {
                    original, files: ReturnedLoaderFilesV1 { source, build, session, executable }, usage,
                }, root })
            }
        }
    }
''' +s[end:]
s=s.replace('BorrowedOwnerDataV1, SuppliedLoaderCarrierV1, CorrelatedSelectedProfileV1,','BorrowedOwnerDataV1, SuppliedLoaderCarrierV1,')
s += '''\n#[cfg(mixer_bootstrap_one_fixture_v1)]\npub(super) use prepaid_input_owner_v1::{FixtureLeafArgumentsV1, RootBoundFixtureOutcomeV1, RootBoundPrimaryBorrowV1};\n'''
p.write_text(s)
