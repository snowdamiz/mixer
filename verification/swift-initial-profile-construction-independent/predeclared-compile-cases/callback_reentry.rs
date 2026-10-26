fn independent_callback_reentry(initial:&super::InitialProfileBorrowV1<'_>,out:&mut std::fs::File) {
 let _=super::write_initial_profile_rows_v1(initial,out,|| {});
}
