// COMPILE ONLY; never invoked. Exactly one intended boundary.

fn ir02_positive_child_v1<'child,'root>(account:&'child TrustedHostAccountV1,fixture:FrozenFixtureV1<'_>,owner:AdmittedImmutableOwnerV1<'root>)
    -> Result<PrepaidOwnedV1<'child,AdmittedFixtureOutcomeV1<'root>>,RefusalV1> {
    let returned={let(expected,attempt)=owner.correlation_scope_v1().unwrap();
        run_one_admitted_fixture_v1(account,fixture,attempt,&expected)};
    crate::experimental_swift_reactor::retained_profile_loader_v1::retire_admitted_owner_v1(owner);returned
}

fn ir02_negative_v1(root:BootstrapLedgerV1,provider:for<'root> fn(&'root BootstrapLedgerV1)->AdmittedImmutableOwnerV1<'root>,account:&TrustedHostAccountV1,fixture:FrozenFixtureV1<'_>) {
    let returned={let local_root=root;ir02_positive_child_v1(account,fixture,provider(&local_root))};
    if let Ok(child)=&returned {let _original=child.inspect_v1();}
    drop(returned);
}
