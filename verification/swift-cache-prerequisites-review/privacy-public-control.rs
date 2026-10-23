use mixer_vm::experimental_swift_reactor::{ValidatedSwiftReactor, SwiftValidationBudget};
fn inspect(p: &ValidatedSwiftReactor) { let _ = (p.source(), p.usage(), p.observations()); let _ = SwiftValidationBudget::default(); }
