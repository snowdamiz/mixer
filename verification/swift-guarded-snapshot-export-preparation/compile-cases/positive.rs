fn positive(g:&crate::experimental_swift_reactor::InitialProfileBorrowV1<'_>,f:&mut std::fs::File) {
 let _=crate::experimental::swift::snapshot_export_preparation_v1::borrow_logical_snapshot_v1(g);
 let _=crate::experimental::swift::snapshot_export_preparation_v1::export_signature_v1(g,f);
 let _signature: for<'a,'b> fn(&'a crate::experimental_swift_reactor::InitialProfileBorrowV1<'b>,&mut std::fs::File)->Result<crate::experimental::swift::snapshot_export_preparation_v1::PreparationObservationV1,crate::experimental::swift::snapshot_export_preparation_v1::PreparationErrorV1>=crate::experimental::swift::snapshot_export_preparation_v1::export_signature_v1;
}
