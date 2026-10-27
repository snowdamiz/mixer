use super::retained_profile_loader_v1::{AdoptionBodyV1, SelectedValidatedProfileV1, LoaderProvenanceV1};
use super::control::{AdoptedProof, RuntimeControl, SwiftRunBudget, SwiftRunFailure};
use super::{ValidatedSwiftReactor, SwiftValidationBudget};
use crate::Cancellation;
use std::time::Instant;
fn f(p: &mut AdoptedProof, other: AdoptedProof) { let q = p.selected_provenance(); let _ = std::mem::replace(p, other); std::hint::black_box(q); }
