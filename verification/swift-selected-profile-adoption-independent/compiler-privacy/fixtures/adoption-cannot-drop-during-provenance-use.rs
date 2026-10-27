use super::retained_profile_loader_v1::{AdoptionBodyV1, SelectedValidatedProfileV1, LoaderProvenanceV1};
use super::control::{AdoptedProof, RuntimeControl, SwiftRunBudget, SwiftRunFailure};
use super::{ValidatedSwiftReactor, SwiftValidationBudget};
use crate::Cancellation;
use std::time::Instant;
fn f(c: &mut RuntimeControl, p: AdoptedProof) { let q = p.selected_provenance(); let _ = c.drop_proof(p); std::hint::black_box(q); }
