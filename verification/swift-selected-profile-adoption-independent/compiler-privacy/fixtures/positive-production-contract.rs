use super::retained_profile_loader_v1::{AdoptionBodyV1, SelectedValidatedProfileV1, LoaderProvenanceV1};
use super::control::{AdoptedProof, RuntimeControl, SwiftRunBudget, SwiftRunFailure};
use super::{ValidatedSwiftReactor, SwiftValidationBudget};
use crate::Cancellation;
use std::time::Instant;

fn selected(p: SelectedValidatedProfileV1) -> Result<(RuntimeControl, AdoptedProof), SwiftRunFailure> {
    p.adopt(SwiftRunBudget::default(), Instant::now(), Cancellation::default())
}
fn ordinary(p: ValidatedSwiftReactor) -> Result<(RuntimeControl, AdoptedProof), SwiftRunFailure> {
    RuntimeControl::adopt(p, SwiftRunBudget::default(), Instant::now(), Cancellation::default())
}
fn selected_borrow(p: &AdoptedProof) -> Option<&LoaderProvenanceV1> { p.selected_provenance() }
fn ordinary_body(p: ValidatedSwiftReactor) -> AdoptionBodyV1 { AdoptionBodyV1::ordinary(p) }
fn body_borrow(p: &AdoptionBodyV1) -> (&ValidatedSwiftReactor, Option<&LoaderProvenanceV1>) {
    (p.proof(), p.selected_provenance())
}
fn selected_read(p: &SelectedValidatedProfileV1) -> (&[u8], SwiftValidationBudget) {
    (p.source(), p.validation_budget())
}

