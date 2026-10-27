use super::retained_profile_loader_v1::{AdoptionBodyV1, SelectedValidatedProfileV1, LoaderProvenanceV1};
use super::control::{AdoptedProof, RuntimeControl, SwiftRunBudget, SwiftRunFailure};
use super::{ValidatedSwiftReactor, SwiftValidationBudget};
use crate::Cancellation;
use std::time::Instant;
fn bound<T: Clone>() {} fn f() { bound::<LoaderProvenanceV1>(); }
