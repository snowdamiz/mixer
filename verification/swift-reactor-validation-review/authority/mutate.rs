use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;
fn consume(proof: ValidatedSwiftReactor) { proof.source()[0] = 9; }
fn main() {}
