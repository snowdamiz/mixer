//! Opt-in experimental-capability-native C composition with the shared registry.
//! Default and guest-only builds do not compile or export this function family.
#[rustfmt::skip]
mod ranges; // root-owned independently prepared pure checked-address helpers
mod api;
pub(crate) mod error;
mod exports;
mod preflight;
pub(crate) mod session;
mod types;
pub use exports::*;
pub use types::*;
#[cfg(test)]
#[path = "../../tests/capability_ffi/internal.rs"]
mod tests;
