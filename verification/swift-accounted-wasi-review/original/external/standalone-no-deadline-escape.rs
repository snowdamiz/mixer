fn main() { let c = mixer_vm::experimental_wasi::WasiContext::new(Default::default(), Default::default(), Default::default()).unwrap(); let _ = c.deadline; }
