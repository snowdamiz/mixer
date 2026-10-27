"""Only proposed missing compiler subcases; no invocation at import."""
PROBES={
    'C01-clone':('inline','''
    fn missing_clone_requirement_v1<T:Clone>(_:T) {}
    fn missing_clone_sites_v1(reservation:AcquisitionReservationV1<'_>,attempt:PrepaidCorrelationAttemptV1<'_>) {
        missing_clone_requirement_v1(reservation);
        missing_clone_requirement_v1(attempt);
    }
''',['E0277','AcquisitionReservationV1','PrepaidCorrelationAttemptV1','Clone']),
    'C03-correspondence':('inline','''
    fn missing_correspondence_borrow_v1(owner:AdmittedImmutableOwnerV1<'_>) {
        let (expected,_attempt)=owner.correlation_scope_v1().unwrap();
        retire_admitted_owner_v1(owner);
        let _live_correspondence=expected.owner_data.source_extent;
    }
''',['E0505','owner','borrow']),
    'C04-proof-source':('inline','''
    fn missing_proof_source_escape_v1(selected:SelectedValidatedProfileV1)->&'static [u8] {
        selected.proof.source()
    }
''',['E0515','selected.proof']),
    'C04-root-reservation':('inline','''
    fn missing_root_reservation_escape_v1<'root>(paid:AcquisitionReservationV1<'root>)->AcquisitionReservationV1<'static> {
        paid
    }
''',['lifetime may not live long enough',"'root","'static"]),
    'C05-expected-fields':('loader','''
fn missing_sibling_expected_fields_v1(provenance:LoaderProvenanceV1) {
    let _expected=AdmittedLoaderCorrespondenceV1 {owner_data:&provenance,association:1};
}
''',['E0451','owner_data','association','private']),
    'C05-admitted-constructor':('loader','''
fn missing_sibling_admitted_constructor_v1(owner:AdmittedImmutableOwnerV1<'_>) {
    let _constructed=AdmittedImmutableOwnerV1(owner);
}
''',['E0423','AdmittedImmutableOwnerV1','private']),
}
