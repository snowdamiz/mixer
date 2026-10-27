#!/usr/bin/env python3
"""Wire the separate admitted final family without touching raw/unadmitted APIs."""
from pathlib import Path
p=Path(__file__).resolve().parent/'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs'
s=p.read_text()
s=s.replace('        OriginalCorrelationRefusalV1, correlate_admitted_loader_v1,','        OriginalCorrelationRefusalV1, correlate_admitted_loader_v1,\n        BootstrapLedgerV1, FixtureLeafArgumentsV1, RootBoundFixtureOutcomeV1, RootBoundPrimaryBorrowV1,')
start=s.index("    fn run_one_admitted_fixture_v1<'a>")
end=s.index('    fn invoke_loaded_leaf_once_v1(',start)
s=s[:start]+'''    // Separate from the unadmitted family: no absent root or invented static
    // reference. Setup originals are bound before the first File operation.
    struct AdmittedFixtureOutcomeV1<'root> {
        payload: AdmittedFixturePayloadV1<'root>,
        root: &'root BootstrapLedgerV1,
    }
    enum AdmittedFixturePayloadV1<'root> {
        SetupRefused(SetupOutcomeV1),
        Loaded(RootBoundFixtureOutcomeV1<'root>),
    }
    fn run_one_admitted_fixture_v1<'child, 'owner, 'root: 'owner, 'expected_root: 'owner>(
        account: &'child TrustedHostAccountV1, fixture: FrozenFixtureV1<'_>,
        attempt: PrepaidCorrelationAttemptV1<'owner, 'root>,
        expected: &AdmittedLoaderCorrespondenceV1<'owner, 'expected_root>,
    ) -> Result<PrepaidOwnedV1<'child, AdmittedFixtureOutcomeV1<'root>>, RefusalV1>
    {
        let quote = host_account_v1::selected_whole_quote_v1()?;
        let reservation = account.reserve_whole_v1(quote)?;
        Ok(reservation.dispatch_v1(|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)))
    }
    fn run_prepaid_admitted_fixture_v1<'owner, 'root: 'owner, 'expected_root: 'owner>(
        fixture: FrozenFixtureV1<'_>, attempt: PrepaidCorrelationAttemptV1<'owner, 'root>,
        expected: &AdmittedLoaderCorrespondenceV1<'owner, 'expected_root>,
    ) -> AdmittedFixtureOutcomeV1<'root>
    {
        let root = attempt.original_root_v1();
        let binding = fixture.binding;
        let (source, build, session, rows, snapshot) = match setup_files_once_v1(binding) {
            SetupOutcomeV1::Ready { source, build, session, rows, snapshot } => (source, build, session, rows, snapshot),
            refused => return AdmittedFixtureOutcomeV1 { payload: AdmittedFixturePayloadV1::SetupRefused(refused), root },
        };
        let cancellation = Cancellation::default();
        let complete_original = load_selected_retained_profile_v1(source, build, session,
            binding.original_validation_budget, &cancellation);
        let original_carrier = SuppliedLoaderCarrierV1::retain_complete_v1(complete_original);
        let correlated = correlate_admitted_loader_v1(attempt, original_carrier, expected);
        let args = FixtureLeafArgumentsV1 { rows, snapshot, cancellation,
            claims: copy_claims_v1(&binding.claims), budget: binding.product_budget, started: Instant::now() };
        let complete = correlated.run_fixture_once_v1(args);
        AdmittedFixtureOutcomeV1 { payload: AdmittedFixturePayloadV1::Loaded(complete), root }
    }
    fn destroy_returned_admitted_fixture_v1<'child, 'root>(
        owned: PrepaidOwnedV1<'child, AdmittedFixtureOutcomeV1<'root>>,
    ) -> Option<DestroyedStorageV1<'child>> {
        // This token contains no root-funded payload after complete destruction.
        owned.destroy_owned_v1()
    }

''' +s[end:]
# Keep original diagnostics and raw APIs for the unadmitted path unchanged.
anchor='    enum RetirementObservationV1 { DestructionTokenReleased, NoDestructionToken }'
start=s.index(anchor)
s=s[:start]+'''    fn observe_admitted_originals_v1(
        owned: &PrepaidOwnedV1<'_, super::AdmittedFixtureOutcomeV1<'_>>,
    ) -> OriginalObservationV1 {
        match owned.inspect_v1() {
            None => OriginalObservationV1::MissingOwnedPayload,
            Some(original) => match &original.payload {
                super::AdmittedFixturePayloadV1::SetupRefused(setup) =>
                    observe_borrowed_originals_v1(Some(BorrowedOriginalDiagnosticsV1::Setup(setup))),
                super::AdmittedFixturePayloadV1::Loaded(complete) => {
                    let _scalar_usage = complete.usage_v1();
                    match complete.primary_v1() {
                        super::RootBoundPrimaryBorrowV1::LoaderRefused(original) => {
                            let _original_loader_failure = original;
                            OriginalObservationV1::LoaderRefused
                        }
                        super::RootBoundPrimaryBorrowV1::CorrelationRefused(original) => {
                            let _original_selection_or_loader_failure = original;
                            OriginalObservationV1::CorrelationRefused
                        }
                        super::RootBoundPrimaryBorrowV1::Leaf(Err(original)) => {
                            let _original_prescope_failure = original;
                            OriginalObservationV1::PreScopeRefused
                        }
                        super::RootBoundPrimaryBorrowV1::Leaf(Ok(original)) => {
                            let _original_finish_and_retirement = original;
                            OriginalObservationV1::LeafReturned
                        }
                    }
                }
            }
        }
    }

''' +s[start:]
s=s.replace('''                                let borrowed = borrow_original_diagnostics_once_v1(&owned_child);
                                let original_observation = observe_borrowed_originals_v1(borrowed);
                                let retirement = match destroy_returned_fixture_v1(owned_child) {''','''                                let original_observation = observe_admitted_originals_v1(&owned_child);
                                let retirement = match super::destroy_returned_admitted_fixture_v1(owned_child) {''')
p.write_text(s)
