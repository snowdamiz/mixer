//! Experimental complete validation under a fixed Swift reactor policy.
//!
//! A successful proof is not executable and does not attest an artifact digest,
//! package admission, signature, runtime readiness or Swift behavior.
#[cfg(test)]
pub(crate) mod allocation_tests;
mod cache;
#[cfg(test)]
mod cache_tests;
pub(crate) mod control;

pub use crate::experimental::swift::{
    validate_swift_reactor, SwiftReactorObservations, SwiftValidationBudget,
    SwiftValidationFailure, SwiftValidationFailureKind, SwiftValidationResource,
    SwiftValidationUsage, ValidatedSwiftReactor,
};

mod execution;
#[cfg(test)]
mod execution_tests;

// Isolated diagnostic prerequisite; no public export.
#[deny(warnings)]
mod diagnostic_profile;

#[cfg(mixer_initial_profile_layout_probe)]
pub(crate) fn emit_initial_profile_layout_v1() { cache::emit_initial_profile_layout_v1(); }
