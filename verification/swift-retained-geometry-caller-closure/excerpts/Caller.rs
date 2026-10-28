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
