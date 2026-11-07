from pathlib import Path
p=Path(__file__).with_name('owner_module.inc.rs');s=p.read_text()
s=s.replace('struct BootstrapLedgerV1 {','pub(in crate::experimental_swift_reactor) struct BootstrapLedgerV1 {')
s=s.replace('fn from_preexisting_fixture_startup_v1() -> Result<Self, BootstrapFailureV1> {','pub(in crate::experimental_swift_reactor) fn from_preexisting_fixture_startup_v1() -> Result<Self, BootstrapFailureV1> {')
s=s.replace("reservation: AcquisitionReservationV1<'root>, actual: Option<AcquiredUnverifiedOwnerV1<R>>,","reservation: AcquisitionReservationV1<'root>, actual: Option<AcquiredUnverifiedOwnerV1<R>>, retirement_started: bool,")
s=s.replace('PrepaidInputOwnerV1 { reservation: paid, actual: Some(AcquiredUnverifiedOwnerV1 { partial, claims }) }','PrepaidInputOwnerV1 { reservation: paid, actual: Some(AcquiredUnverifiedOwnerV1 { partial, claims }), retirement_started: false }')
s=s.replace('if s.source_bytes == 0 || s.source_bytes != ids[0].bytes', '''if s.source_bytes == 0 || s.budget.source_bytes == 0 || s.budget.metadata_bytes == 0
            || s.budget.scratch_bytes == 0 || s.budget.work_credits == 0 || s.budget.deadline_ms == 0
            || s.source_bytes != ids[0].bytes''')
a=s.index('    pub(in crate::experimental_swift_reactor) struct AdmittedImmutableOwnerV1')
b=s.index('    pub(in crate::experimental_swift_reactor) struct BorrowedOwnerDataV1',a)
s=s[:a]+'''    struct AdmittedImmutableOwnerCoreV1<'root,R> {
        owned: PrepaidInputOwnerV1<'root,R>, expected: LoaderProvenanceV1,
        custody: TrustedLocalLauncherCustodyV1, attempt_taken: Cell<bool>,
    }
    pub(in crate::experimental_swift_reactor) struct AdmittedImmutableOwnerV1<'root>(AdmittedImmutableOwnerCoreV1<'root,File>);
    enum OwnedAdmissionCoreOutcomeV1<'root,R> {
        Admitted(AdmittedImmutableOwnerCoreV1<'root,R>), Refused(PrepaidInputOwnerV1<'root,R>),
    }
    fn complete_admission_core_v1<'root,R>(mut owned: PrepaidInputOwnerV1<'root,R>, custody: TrustedLocalLauncherCustodyV1)
        -> OwnedAdmissionCoreOutcomeV1<'root,R>
    {
        let derived = match owned.actual.as_ref() {
            Some(actual) => derive_provenance_v1(actual, &owned.reservation.root.policy),
            None => Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)),
        };
        let expected = match derived {
            Ok(expected) => expected,
            Err(original) => {
                if let Some(actual) = owned.actual.as_mut() { store_failure_v1(&mut actual.partial,original); }
                return OwnedAdmissionCoreOutcomeV1::Refused(owned);
            }
        };
        let prices = owned.reservation.root.policy.bridge;
        // Entire fixed ingress/call/result/refusal overlap debited from the
        // original acquisition partition BEFORE admission publication.
        if let Err(kind) = owned.reservation.operation_v1(prices.correlation, prices.correlation_storage) {
            if let Some(actual) = owned.actual.as_mut() { store_failure_v1(&mut actual.partial,
                OriginalAcquisitionFailureV1::new(kind,13)); }
            return OwnedAdmissionCoreOutcomeV1::Refused(owned);
        }
        OwnedAdmissionCoreOutcomeV1::Admitted(AdmittedImmutableOwnerCoreV1 {
            owned, expected, custody, attempt_taken: Cell::new(false) })
    }
    fn verify_owned_once_v1<'root>(mut owner: PrepaidInputOwnerV1<'root,File>) -> OwnedAdmissionCoreOutcomeV1<'root,File> {
        let result = match owner.actual.as_ref() {
            Some(actual) => derive_provenance_v1(actual, &owner.reservation.root.policy),
            None => Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)),
        };
        let original = match result { Err(e) => e, Ok(_) => OriginalAcquisitionFailureV1::new(BootstrapFailureV1::CompileClosureAuthorityPending,11) };
        if let Some(actual) = owner.actual.as_mut() { store_failure_v1(&mut actual.partial,original); }
        // No production TrustedLocalLauncherCustodyV1 producer exists.
        OwnedAdmissionCoreOutcomeV1::Refused(owner)
    }
    pub(in crate::experimental_swift_reactor) fn selected_bootstrap_ledger_v1()
        -> Result<BootstrapLedgerV1, BootstrapFailureV1>
    {
        BootstrapLedgerV1::from_preexisting_fixture_startup_v1()
    }
''' + s[b:]
s=s.replace('impl AdmittedImmutableOwnerV1<\'_> {','''impl<R> AdmittedImmutableOwnerCoreV1<'_,R> {
        fn correlation_scope_core_v1(&self)
            -> Result<(AdmittedLoaderCorrespondenceV1<'_>, PrepaidCorrelationAttemptV1<'_>), BootstrapFailureV1>
        {
            if self.attempt_taken.replace(true) { return Err(BootstrapFailureV1::AlreadyAttempted); }
            Ok((AdmittedLoaderCorrespondenceV1 { owner_data: &self.expected },
                PrepaidCorrelationAttemptV1 { expected: &self.expected, live: &self.attempt_taken }))
        }
    }
    impl AdmittedImmutableOwnerV1<'_> {''')
s=s.replace('let actual = self.owned.actual.as_ref().expect("private admitted invariant");','let actual = self.0.owned.actual.as_ref().expect("private admitted invariant");')
s=s.replace('self.owned.reservation.root.policy.validation','self.0.owned.reservation.root.policy.validation').replace('self.owned.reservation.root.policy.product','self.0.owned.reservation.root.policy.product')
s=s.replace('''            if self.attempt_taken.replace(true) { return Err(BootstrapFailureV1::AlreadyAttempted); }
            Ok((AdmittedLoaderCorrespondenceV1 { owner_data: &self.expected },
                PrepaidCorrelationAttemptV1 { expected: &self.expected, live: &self.attempt_taken }))
        }
    }
    // Fixed typed''','''            self.0.correlation_scope_core_v1()
        }
    }
    // Fixed typed''')
s=s.replace('struct OriginalCorrelationRefusalV1 { kind: BootstrapFailureV1 }','struct OriginalCorrelationRefusalV1 { kind: BootstrapFailureV1, retained_selection: Option<Result<SelectedValidatedProfileV1,LoaderFailureV1>> }')
s=s.replace('Refused { original: OriginalCorrelationRefusalV1, carrier: SuppliedLoaderCarrierV1 },','Refused { original: OriginalCorrelationRefusalV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },')
s=s.replace('OriginalCorrelationRefusalV1 { kind }','OriginalCorrelationRefusalV1 { kind, retained_selection: None }')
s=s.replace('''            Err((original, LoaderCarrierCoreV1 { selected, files: [source,build,session], executable, usage })) =>
                OwnedCorrelationOutcomeV1::Refused { original, carrier: SuppliedLoaderCarrierV1 { original: LoaderOutcomeV1 {
                    selected, files: ReturnedLoaderFilesV1 { source,build,session,executable }, usage } } },''','''            Err((mut original, LoaderCarrierCoreV1 { selected, files: [source,build,session], executable, usage })) => {
                original.retained_selection = Some(selected);
                OwnedCorrelationOutcomeV1::Refused { original, files: ReturnedLoaderFilesV1 { source,build,session,executable }, usage }
            }''')
s=s.replace('''        let actual = match owner.actual.as_mut() { Some(v) => v, None => return AcquisitionRetirementOutcomeV1::Retained(owner) };
        // Never close''','''        if owner.retirement_started { return AcquisitionRetirementOutcomeV1::Retained(owner); }
        owner.retirement_started = true;
        let actual = match owner.actual.as_mut() { Some(v) => v, None => return AcquisitionRetirementOutcomeV1::Retained(owner) };
        // Never close''')
s=s.replace('PrepaidInputOwnerV1 { reservation: paid, actual: None }','PrepaidInputOwnerV1 { reservation: paid, actual: None, retirement_started: _ }')
s=s.replace('retire_acquired_owner_core_v1(owner.owned','retire_acquired_owner_core_v1(owner.0.owned')
s=s.replace('BootstrapFailureV1, BorrowedOwnerDataV1,','BootstrapFailureV1, BootstrapLedgerV1, BorrowedOwnerDataV1,').replace('selected_prepaid_input_owner_v1,','selected_bootstrap_ledger_v1,')
p.write_text(s)
