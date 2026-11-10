#![cfg(feature = "experimental-swift-reactor")]
#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;
use fixture::*;
use mixer_vm::{Cancellation, Limits, Module};
use mixer_vm::experimental_swift_reactor::{validate_swift_command, validate_swift_reactor,
    execute_swift_command, SwiftValidationBudget, SwiftValidationFailureKind,
    SwiftRunBudget, SwiftRunFailureKind};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};

fn command() -> Fixture {
    let mut f = Fixture::default();
    f.memory = vec![1, 0, 1];
    f.table = vec![1, 0x70, 1, 0, 0];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    f
}
fn validate(f: &Fixture) -> mixer_vm::experimental_swift_reactor::ValidatedSwiftCommand {
    validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).unwrap()
}
#[test]
fn new_policy_accepts_more_real_bodies_without_changing_fixed_or_public_policy() {
    let mut f = command();
    f.function_types = vec![34; 80_514];
    f.bodies = vec![vec![0, 0x0b]; 80_514];
    let bytes = f.bytes();
    let proof = validate_swift_command(&bytes, SwiftValidationBudget::default(), &Cancellation::default()).unwrap();
    assert_eq!(proof.observations().validated_bodies, 80_514);
    assert_eq!(proof.policy_identity(), "swift-command-diagnostic-v1");
    let old = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &Cancellation::default()).err().unwrap();
    assert_eq!(old.code, "profile_vector_limit");
    assert_eq!(old.limit, 79_966);
    assert!(Module::decode(&bytes, &Limits::default()).is_err());
    f.function_types = vec![34; 131_039];
    f.bodies = vec![vec![0, 0x0b]; 131_039];
    let e = validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).err().unwrap();
    assert_eq!(e.code, "profile_vector_limit");
}
#[test]
fn uncalled_and_unreachable_invalid_instructions_are_rejected() {
    let mut f = command();
    f.bodies[27] = vec![0, 0, 0xff, 0x0b];
    let e = validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).err().unwrap();
    assert_eq!(e.function, Some(61));
    assert_eq!(e.kind, SwiftValidationFailureKind::Unsupported);
}
#[test]
fn import_signature_namespace_and_command_abi_fail_closed() {
    let mut f = command();
    f.imports[0].0 = b"env".to_vec();
    assert!(validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).is_err());
    let mut f = command(); f.imports[0].3 = 34;
    assert_eq!(validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).err().unwrap().code, "swift_import_abi");
    let mut f = command(); f.exports[1].2 = 62;
    assert_eq!(validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).err().unwrap().code, "swift_command_export_abi");
    let mut f = command(); f.start = Some(34);
    assert!(validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).is_err());
}
#[test]
fn validation_resource_deadline_and_cancellation_bounds_remain_active() {
    let bytes = command().bytes();
    for budget in [SwiftValidationBudget { metadata_bytes: 1, ..Default::default() },
        SwiftValidationBudget { work_credits: 0, ..Default::default() },
        SwiftValidationBudget { deadline_ms: 0, ..Default::default() }] {
        assert!(validate_swift_command(&bytes, budget, &Cancellation::default()).is_err());
    }
    let cancelled = Cancellation::default(); cancelled.cancel();
    assert_eq!(validate_swift_command(&bytes, SwiftValidationBudget::default(), &cancelled).err().unwrap().kind, SwiftValidationFailureKind::Cancelled);
}
#[test]
fn real_fd_write_and_proc_exit_use_bounded_output_and_consuming_cleanup() {
    let mut f = command();
    f.bodies[0] = vec![0, 0x41,1, 0x41,0, 0x41,1, 0x41,16, 0x10,20, 0x10,32, 0x0b];
    let mut data = vec![0u8; 37];
    data[..4].copy_from_slice(&32u32.to_le_bytes()); data[4..8].copy_from_slice(&5u32.to_le_bytes());
    data[32..].copy_from_slice(b"hello");
    let mut segment = vec![0, 0x41, 0, 0x0b]; segment.extend(uint(data.len() as u32)); segment.extend(data);
    f.data = vec![segment];
    let mut stdout = vec![]; let mut stderr = vec![];
    let report = execute_swift_command(validate(&f), SwiftRunBudget::default(), WasiGrants { stdout: true, ..Default::default() },
        WasiBudget::default(), Cancellation::default(), &mut stdout, &mut stderr);
    assert!(report.succeeded(), "{report:?}"); assert_eq!(stdout, b"hello"); assert!(stderr.is_empty());
    assert_eq!(report.calls_by_function[20], 1); assert_eq!(report.calls_by_function[32], 1);
    assert_eq!(report.after_cleanup.unwrap().reservations.combined.current, 0);
    let report = execute_swift_command(validate(&f), SwiftRunBudget::default(), WasiGrants { stdout: true, ..Default::default() },
        WasiBudget { log_bytes: 4, ..Default::default() }, Cancellation::default(), &mut vec![], &mut vec![]);
    assert!(!report.succeeded(), "{report:?}");
    assert_eq!(report.terminal.unwrap().guest_exit, Some(51));
    assert!(report.cleanup_completed);
}
#[test]
fn infinite_guest_stops_at_fuel_and_cleans_frames() {
    let mut f = command(); f.bodies[0] = vec![0, 3, 0x40, 0x0c, 0, 0x0b, 0x0b];
    let report = execute_swift_command(validate(&f), SwiftRunBudget { instruction_fuel: 16, ..Default::default() },
        WasiGrants::default(), WasiBudget::default(), Cancellation::default(), &mut vec![], &mut vec![]);
    assert_eq!(report.terminal.unwrap().kind, SwiftRunFailureKind::FuelExhausted);
    assert!(report.cleanup_completed, "{report:?}");
}

