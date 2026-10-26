// Sibling insertion MUST reject these intended private selected types.
use super::initial_profile_v1::{SelectedInitialProfileV1, SelectedLocalStructureV1};
fn independent_private_selection(budget:crate::experimental_swift_reactor::control::SwiftRunBudget,local:SelectedLocalStructureV1) {
 let _=SelectedInitialProfileV1 {budget,local};
}
