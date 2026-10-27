use std::sync::{atomic::AtomicBool, Arc};

// Verbatim frozen product declaration and derives, with the identical standard
// Arc<AtomicBool> type. Exported wrappers force both actual monomorphizations.
#[derive(Clone, Default)]
pub struct Cancellation(Arc<AtomicBool>);

#[no_mangle]
pub fn mixer_probe_cancellation_default() -> Cancellation { Cancellation::default() }

#[no_mangle]
pub fn mixer_probe_cancellation_clone(value: &Cancellation) -> Cancellation { value.clone() }
