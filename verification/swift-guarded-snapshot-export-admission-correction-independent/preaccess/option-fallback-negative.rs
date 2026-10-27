#![allow(dead_code)]
#[repr(C)]
struct InitialProfileScalarsV1 {
    source_extent:u64, type_count:u64, slot_limit:u64, pin_limit:u64,
    initial_nonce:u64, cache_base:u64, cache_capacity:u64, entry_limit:u64,
}
struct InitialProfileBorrowV1<'a> {
    cache:&'a SwiftFunctionCache, control:&'a RuntimeControl, wasi:Option<&'a AccountedWasi>,
    scalars:InitialProfileScalarsV1,
}
// Refusal fallback counterexample missing from the previous admitted-only probe.
// Exact accepted scalar/guard definitions are inserted by prepare.py; component
// types are stand-ins and begin() is unexecuted. No actual admission is claimed.
struct RuntimeControl;
struct SwiftFunctionCache;
struct AccountedWasi;
struct Phase<'a> { control: &'a mut RuntimeControl }
impl Phase<'_> {
    fn shared(&self) -> &RuntimeControl { self.control }
    fn complete(self) {}
}
impl RuntimeControl {
    fn begin(&mut self) -> Result<Phase<'_>, ()> { Err(()) }
}
fn observe(_: &InitialProfileBorrowV1<'_>) {}
fn rejected_option_fallback(control: &mut RuntimeControl, cache: &SwiftFunctionCache) {
    let phase = match control.begin() { Ok(phase) => Some(phase), Err(()) => None };
    let shared = match phase.as_ref() { Some(phase) => phase.shared(), None => &*control };
    let initial = InitialProfileBorrowV1 { cache, control: shared, wasi: None,
        scalars: InitialProfileScalarsV1 { source_extent: 0, type_count: 0, slot_limit: 0,
            pin_limit: 0, initial_nonce: 0, cache_base: 0, cache_capacity: 0, entry_limit: 0 } };
    observe(&initial);
    drop(initial);
    if let Some(phase) = phase { phase.complete(); }
}
