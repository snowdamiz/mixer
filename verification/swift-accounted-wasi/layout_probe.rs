//! Original external consumer of the unchanged public standalone WASI surface.
use mixer_vm::experimental_wasi::{WasiBudget, WasiContext, WasiFunction, WasiGrants};
use mixer_vm::{Cancellation, Value};

fn main() {
    let budget = WasiBudget {
        one_transfer_bytes: 1024,
        log_bytes: 1024,
        ..WasiBudget::default()
    };
    let mut context =
        WasiContext::new(WasiGrants::default(), budget, Cancellation::default()).unwrap();
    let before = context.usage();
    let mut memory = [0xa5; 8];
    let outcome = context.dispatch(
        WasiFunction::ArgsSizesGet,
        &[Value::I32(0), Value::I32(4)],
        &mut memory,
    );
    let after = context.usage();
    println!(
        "{{\"context_size\":{},\"context_align\":{},\"initial_fixed\":{},\"initial_staging\":{},\"initial_rollback\":{},\"initial_stdout\":{},\"initial_stderr\":{},\"initial_current\":{},\"initial_peak\":{},\"calls\":{},\"work\":{},\"transfer\":{},\"failures\":{},\"stdout_len\":{},\"stderr_len\":{},\"memory\":{:?},\"outcome\":\"{:?}\"}}",
        std::mem::size_of::<WasiContext>(),
        std::mem::align_of::<WasiContext>(),
        before.reservations.fixed_state_bytes,
        before.reservations.staging_bytes,
        before.reservations.rollback_bytes,
        before.reservations.stdout_bytes,
        before.reservations.stderr_bytes,
        before.reservations.current_bytes,
        before.reservations.peak_bytes,
        after.calls,
        after.work,
        after.transfer_bytes,
        after.failures,
        context.stdout().len(),
        context.stderr().len(),
        memory,
        outcome,
    );
}
