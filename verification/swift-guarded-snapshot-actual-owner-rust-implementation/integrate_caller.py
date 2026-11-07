from pathlib import Path
p=Path(__file__).parent/'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs';s=p.read_text()
anchor='#[repr(transparent)]\nstruct UnverifiedProfileHeaderV1'
s=s.replace(anchor,'''#[cfg(test)]
impl UnverifiedProfileDigestBytesV1 {
    pub(in crate::experimental_swift_reactor) fn test_prepaid_actual_owner_fixed_claims_v1() -> Self {
        Self { baseline:[1;32],candidate:[2;32],original_input:[3;32],event_schema:[4;32],
            profile_adapter_binary:[5;32],layout_receipt:[6;32],original_validated_snapshot:[7;32],profile_row_body:[8;32] }
    }
}
''' + anchor)
s=s.replace('''        LoaderUsageV1, ReturnedLoaderFilesV1, SelectedValidatedProfileV1,
''','''        LoaderUsageV1, ReturnedLoaderFilesV1, SelectedValidatedProfileV1,
        AdmittedImmutableOwnerV1, AdmittedLoaderCorrespondenceV1, PrepaidCorrelationAttemptV1,
        BootstrapFailureV1, SuppliedLoaderCarrierV1, OwnedCorrelationOutcomeV1,
        OriginalCorrelationRefusalV1, correlate_admitted_loader_v1,
''',1)
s=s.replace('''        LoaderRefused(LoaderFailureV1),
        Leaf''','''        LoaderRefused(LoaderFailureV1),
        CorrelationRefused(OriginalCorrelationRefusalV1),
        Leaf''',1)
# Existing unqualified route is unchanged. The new private route accepts only
# the loader-private pair. All six original components still reserve up front.
a=s.index('    fn invoke_loaded_leaf_once_v1(')
s=s[:a]+'''    fn run_one_admitted_fixture_v1<'a>(account: &'a TrustedHostAccountV1,
        fixture: FrozenFixtureV1<'_>, attempt: PrepaidCorrelationAttemptV1<'_>,
        expected: &AdmittedLoaderCorrespondenceV1<'_>)
        -> Result<PrepaidOwnedV1<'a,OwnedFixtureOutcomeV1>,RefusalV1>
    {
        let quote = host_account_v1::selected_whole_quote_v1()?;
        let reservation = account.reserve_whole_v1(quote)?;
        Ok(reservation.dispatch_v1(|| run_prepaid_admitted_fixture_v1(fixture,attempt,expected)))
    }
    fn run_prepaid_admitted_fixture_v1(fixture: FrozenFixtureV1<'_>,
        attempt: PrepaidCorrelationAttemptV1<'_>, expected: &AdmittedLoaderCorrespondenceV1<'_>)
        -> OwnedFixtureOutcomeV1
    {
        let binding = fixture.binding;
        let (source,build,session,mut rows,mut snapshot) = match setup_files_once_v1(binding) {
            SetupOutcomeV1::Ready { source,build,session,rows,snapshot } => (source,build,session,rows,snapshot),
            refused => return OwnedFixtureOutcomeV1::SetupRefused(refused),
        };
        let cancellation = Cancellation::default();
        let complete_original = load_selected_retained_profile_v1(source,build,session,
            binding.original_validation_budget,&cancellation);
        // Complete LoaderOutcome enters the affine owner BEFORE any admitting
        // or rejecting check. The selected proof cannot reach this leaf alone.
        let original_carrier = SuppliedLoaderCarrierV1::retain_complete_v1(complete_original);
        let correlated = correlate_admitted_loader_v1(attempt,original_carrier,expected);
        let claims = copy_claims_v1(&binding.claims);
        let (primary,files,usage) = match correlated {
            OwnedCorrelationOutcomeV1::LoaderRefused { original,files,usage } =>
                (PrimaryOutcomeV1::LoaderRefused(original),files,usage),
            OwnedCorrelationOutcomeV1::Refused { original,files,usage } =>
                (PrimaryOutcomeV1::CorrelationRefused(original),files,usage),
            OwnedCorrelationOutcomeV1::Correlated { selected,files,usage } => {
                let selected = selected.into_selected_v1();
                (PrimaryOutcomeV1::Leaf(invoke_loaded_leaf_once_v1(selected,binding.product_budget,
                    Instant::now(),cancellation.clone(),&claims,&mut rows,&mut snapshot)),files,usage)
            }
        };
        OwnedFixtureOutcomeV1::Loaded { original_files:files,original_loader_usage:usage,rows,snapshot,
            cancellation_owner:cancellation,claims_owner:claims,primary }
    }

''' + s[a:]
s=s.replace('''        LoaderRefused,
        PreScopeRefused,''','''        LoaderRefused,
        CorrelationRefused,
        PreScopeRefused,''',1)
s=s.replace('''                    PrimaryOutcomeV1::Leaf(Err(original)) => {''','''                    PrimaryOutcomeV1::CorrelationRefused(original) => {
                        let _complete_selected_or_loader_failure_and_new_original = original;
                        OriginalObservationV1::CorrelationRefused
                    }
                    PrimaryOutcomeV1::Leaf(Err(original)) => {''',1)
# New outer route scopes every borrowed view before consuming original child
# and finally outer acquisition owner. No selected constructor invokes it yet.
a=s.index('    #[cfg(test)]\n    mod tests {',s.index('mod outer_parent_v1'))
s=s[:a]+'''    fn consume_admitted_owner_once_v1(owner: super::AdmittedImmutableOwnerV1<'_>)
        -> Result<(),super::BootstrapFailureV1>
    {
        let attempt_result = {
            let data = owner.scoped_binding_v1();
            let [source,build,session,executable,compiler,compiler_version,compile_manifest,
                compile_argv,compile_environment,process_argv,process_environment,review] = data.identities
                .map(|(bytes,sha256)| ImmutableIdentityPreimageV1 { bytes,sha256 });
            let preexisting = PreexistingImmutableBindingV1 {
                binding: ReviewedFixtureBindingV1 { paths:data.paths,claims:super::copy_claims_v1(data.claims),
                    original_validation_budget:data.validation,product_budget:data.product },
                native_path_bodies:data.retained_paths,
                identities:ImmutableFixtureIdentitiesV1 { source,build,session,executable,compiler,compiler_version,
                    compile_manifest,compile_argv,compile_environment,process_argv,process_environment,review },
            };
            match owner.correlation_scope_v1() {
                Err(original) => Err(original),
                Ok((expected,attempt)) => match host_account_v1::selected_parent_account_v1() {
                    Err(_original_pending_account) => Ok(()),
                    Ok(account) => {
                        let fixture = FrozenFixtureV1 { binding:&preexisting.binding };
                        match super::run_one_admitted_fixture_v1(&account,fixture,attempt,&expected) {
                            Err(_original_pending_quote) => {},
                            Ok(owned_child) => {
                                let borrowed = borrow_original_diagnostics_once_v1(&owned_child);
                                let _observation = observe_borrowed_originals_v1(borrowed);
                                if let Some(original_token) = destroy_returned_fixture_v1(owned_child) {
                                    release_after_retirement_v1(original_token);
                                }
                            }
                        }
                        Ok(())
                    }
                },
            }
        };
        // Every binding/correspondence/result view above ended. The acquired
        // owner and separate cleanup partition still live until this consume.
        crate::experimental_swift_reactor::retained_profile_loader_v1::retire_admitted_owner_v1(owner);
        attempt_result
    }

''' + s[a:]
p.write_text(s)
m=Path(__file__).with_name('owner_module.inc.rs');m.write_text(m.read_text().replace('cache::initial_profile_v1::UnverifiedProfileDigestBytesV1','cache::SnapshotClaimsV1 as UnverifiedProfileDigestBytesV1'))
