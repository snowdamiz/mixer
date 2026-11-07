fn forbidden(initial:&super::InitialProfileBorrowV1<'_>) {
 let _=super::write_initial_profile_rows_v1(initial,|_|Ok(0usize));
}
