// New refusal/view lifetime controls. Exact accepted scalar/guard definitions are
// inserted before this body by prepare.py. Referenced components are stand-ins.
#[derive(Debug)]
struct RuntimeControl { identity: u64, retired: usize }
struct SwiftFunctionCache;
struct AccountedWasi;
#[derive(Debug, PartialEq, Eq)]
enum Refusal { ExistingFailure(u64), Storage }
enum BorrowOwner<'c> {
    Admitted { control: &'c mut RuntimeControl, captured: usize },
    Refused { control: &'c mut RuntimeControl, error: Refusal },
}
impl BorrowOwner<'_> {
    fn shared(&self) -> &RuntimeControl {
        match self {
            Self::Admitted { control, .. } | Self::Refused { control, .. } => control,
        }
    }
    fn complete(self, actual_storage: DropWitness<'_>) -> Option<Refusal> {
        drop(actual_storage);
        match self {
            Self::Admitted { control, captured } => { control.retired += captured; None }
            Self::Refused { control, error } => { control.retired += 1; Some(error) }
        }
    }
}
struct DropWitness<'a>(&'a std::cell::Cell<bool>);
impl Drop for DropWitness<'_> { fn drop(&mut self) { self.0.set(true); } }
fn scalars() -> InitialProfileScalarsV1 {
    InitialProfileScalarsV1 { source_extent: 0, type_count: 0, slot_limit: 0,
        pin_limit: 0, initial_nonce: 0, cache_base: 0, cache_capacity: 0, entry_limit: 0 }
}
fn observe_header<'a>(initial: &InitialProfileBorrowV1<'a>) -> &'a RuntimeControl { initial.control }
fn observe_rows(initial: &InitialProfileBorrowV1<'_>) -> u64 { initial.control.identity }
fn positive(control: &mut RuntimeControl, admitted: bool, error: Refusal) {
    let cache = SwiftFunctionCache;
    let wasi = AccountedWasi;
    // The bool chooses a reduced language-control branch only. It is never an
    // admission/cancellation oracle, budget authority, or actual Mixer path.
    let owner = if admitted {
        BorrowOwner::Admitted { control, captured: 7 }
    } else {
        BorrowOwner::Refused { control, error }
    };
    let dropped = std::cell::Cell::new(false);
    {
        // ONE literal for BOTH branch variants; exact accepted guard fields.
        let initial = InitialProfileBorrowV1 { cache: &cache,
            control: owner.shared(), wasi: Some(&wasi), scalars: scalars() };
        let view = observe_header(&initial);
        assert!(std::ptr::eq(view, owner.shared()));
        assert_eq!(view.identity, 42);
        assert_eq!(observe_rows(&initial), 42);
        assert!(!dropped.get());
    }
    let refusal = owner.complete(DropWitness(&dropped));
    assert!(dropped.get());
    if admitted {
        assert_eq!(control.retired, 7);
        assert_eq!(refusal, None);
    } else {
        assert_eq!(control.retired, 1);
        assert_eq!(refusal, Some(Refusal::ExistingFailure(91)));
    }
}
#[cfg(live_view_negative)]
fn live_view_crosses_complete(control: &mut RuntimeControl) {
    let cache = SwiftFunctionCache;
    let owner = BorrowOwner::Admitted { control, captured: 7 };
    let initial = InitialProfileBorrowV1 { cache: &cache,
        control: owner.shared(), wasi: None, scalars: scalars() };
    let view = observe_header(&initial);
    // Dropping the guard alone does not end the derived reference.
    drop(initial);
    let dropped = std::cell::Cell::new(false);
    owner.complete(DropWitness(&dropped));
    assert_eq!(view.identity, 42);
}
#[test]
fn admitted_variant_uses_one_guard_then_consumes() {
    positive(&mut RuntimeControl { identity: 42, retired: 0 }, true, Refusal::Storage);
}
#[test]
fn refused_variant_retains_exact_error_and_uses_same_guard_then_consumes() {
    positive(&mut RuntimeControl { identity: 42, retired: 0 }, false, Refusal::ExistingFailure(91));
}
