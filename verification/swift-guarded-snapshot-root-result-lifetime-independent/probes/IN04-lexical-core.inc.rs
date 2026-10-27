// Placed inside the original private guard test module. Compile-only.
fn independent_core_original_root_escape_v1() {
    let foreign_root = root(); let trace = Rc::new(Trace::default());
    let foreign_owner = admitted(&foreign_root, &trace);
    let returned = {
        let original_root = root(); let owner = admitted(&original_root, &trace);
        let returned = { let (_own, attempt) = owner.correlation_scope_core_v1().unwrap(); let (foreign, _unused) = foreign_owner.correlation_scope_core_v1().unwrap(); correlate_core_v1(attempt, carrier(&owner.expected, &trace), &foreign) };
        drop(assert_correlation_barrier_v1(owner, &trace));
        returned
    };
    match returned.into_result_v1() { Err(held) => { assert_eq!(held.payload.1.selected.as_ref().unwrap().proof.source().len(), 1947); assert_eq!(held.payload.1.files.each_ref().map(|guard|guard.tag), [20,21,22]); }, Ok(_) => panic!("foreign owner accepted") }
    drop(assert_correlation_barrier_v1(foreign_owner, &trace));
}
