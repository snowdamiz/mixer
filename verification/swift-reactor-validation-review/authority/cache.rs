use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;
use mixer_vm::experimental::cache::{FunctionCache, CacheBudget};
fn consume(proof: ValidatedSwiftReactor) { let _ = FunctionCache::new(proof, CacheBudget::default(), &mixer_vm::Cancellation::default()); }
fn main() {}
