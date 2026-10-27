// COMPILE ONLY; never invoked. Exactly one intended boundary.

// Paired control: genuine File facade, original owner supplied as input. This
// compiles without acquiring Files or constructing an admitted owner.
fn ir02_positive_correlate_v1<'root>(owner:AdmittedImmutableOwnerV1<'root>,carrier:SuppliedLoaderCarrierV1)
    -> OwnedCorrelationOutcomeV1<'root> {
    let returned={let(expected,attempt)=owner.correlation_scope_v1().unwrap();
        correlate_admitted_loader_v1(attempt,carrier,&expected)};
    retire_admitted_owner_v1(owner);
    returned
}

fn ir02_positive_final_v1<'root>(owner:AdmittedImmutableOwnerV1<'root>,carrier:SuppliedLoaderCarrierV1,args:FixtureLeafArgumentsV1)
    -> RootBoundFixtureOutcomeV1<'root> {
    ir02_positive_correlate_v1(owner,carrier).run_fixture_once_v1(args)
}
fn ir02_positive_scalar_v1(value:&RootBoundFixtureOutcomeV1<'_>)->LoaderUsageV1 {value.usage_v1()}

fn ir02_negative_v1(value:&mut OwnedCorrelationOutcomeV1<'_>) {let _mutable=std::ops::DerefMut::deref_mut(value);}
