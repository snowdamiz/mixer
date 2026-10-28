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
