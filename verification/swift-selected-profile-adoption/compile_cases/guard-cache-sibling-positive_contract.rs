#[cfg(mixer_initial_profile_external_contract)]
fn positive(cache:&super::SwiftFunctionCache) { let _: &super::ValidatedSwiftReactor=cache.proof(); }
#[cfg(not(mixer_initial_profile_external_contract))]
fn positive(initial:&super::InitialProfileBorrowV1<'_>,file:&mut std::fs::File) {
 let _:Result<super::ProfileRowsObservationV1,super::ProfileAdapterErrorV1>=super::write_initial_profile_rows_v1(initial,file);
 let _:fn(&super::InitialProfileBorrowV1<'_>,&super::UnverifiedProfileDigestBytesV1)->Result<super::UnverifiedProfileHeaderV1,super::ProfileHeaderErrorV1>=super::header::encode_profile_header_v1;
}

