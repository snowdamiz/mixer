use super::retained_profile_loader_v1::{AdoptionBodyV1, SelectedValidatedProfileV1, LoaderProvenanceV1};
use super::control::{AdoptedProof, RuntimeControl, SwiftRunBudget, SwiftRunFailure};
use super::{ValidatedSwiftReactor, SwiftValidationBudget};
use crate::Cancellation;
use std::time::Instant;
fn f(p: &AdoptedProof) { let _ = RuntimeControl::adopt_body(p.selected_provenance().unwrap(), SwiftRunBudget::default(), Instant::now(), Cancellation::default()); }
