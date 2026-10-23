use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;
fn consume(proof: ValidatedSwiftReactor) { let source = proof.source(); drop(proof); std::hint::black_box(source); }
fn main() {}
