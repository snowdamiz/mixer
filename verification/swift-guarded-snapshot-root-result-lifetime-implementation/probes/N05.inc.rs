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

fn ir02_positive_refusal_v1<'root>(owner:AdmittedImmutableOwnerV1<'root>,carrier:SuppliedLoaderCarrierV1,live_refusal:bool)
    -> OwnedCorrelationOutcomeV1<'root> {
    let returned={let(mut expected,attempt)=owner.correlation_scope_v1().unwrap();
        if live_refusal {owner.0.attempt_taken.set(false)} else {expected.association+=1}
        correlate_admitted_loader_v1(attempt,carrier,&expected)};
    retire_admitted_owner_v1(owner);returned
}
fn ir02_negative_v1(root:BootstrapLedgerV1,provider:for<'root> fn(&'root BootstrapLedgerV1)->AdmittedImmutableOwnerV1<'root>,carrier:SuppliedLoaderCarrierV1,live_refusal:bool) {
    let returned={let local_root=root;ir02_positive_refusal_v1(provider(&local_root),carrier,live_refusal)};
    drop(returned);
}
