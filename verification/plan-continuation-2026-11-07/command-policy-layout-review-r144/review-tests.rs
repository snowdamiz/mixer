use super::{policy::{Policy, SwiftSelection}, cache::{borrowed::*, decode, CacheFailureKind}};
use crate::{Cancellation, Limits, Profile};
use crate::experimental_swift_reactor::{validate_swift_command, validate_swift_reactor,
    execute_swift_command, SwiftValidationBudget, SwiftValidationFailureKind, SwiftRunBudget};
use crate::experimental_wasi::{WasiBudget, WasiGrants};
#[path = "../../tests/swift_reactor_validation_fixture.rs"]
mod fixture;
use fixture::Fixture;

fn command() -> Fixture {
    let mut f = Fixture::default();
    f.memory = vec![1, 0, 1];
    f.table = vec![1, 0x70, 1, 0, 0];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    f
}
fn validate(f: &Fixture) -> super::swift::ValidatedSwiftCommand {
    validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).unwrap()
}

#[test]
fn r144_frozen_limits_and_specialized_layouts() {
    let l = Limits { profile: Profile::TableMemoryV3, functions: 71, types: 23,
        instructions: 113, locals: 19, operand_stack: 29, control_depth: 17,
        memory_pages: 11, table_elements: 31, module_bytes: 1009, ..Default::default() };
    let frozen = Policy::frozen(&l);
    let frozen_command = Policy::<true>::Frozen(&l);
    macro_rules! same { ($($method:ident),*) => { $(assert_eq!(frozen.$method(), frozen_command.$method(), stringify!($method));)* } }
    same!(legacy_imports, floats, tables, module_bytes, functions, types,
        type_parameters_total, parameters_per_signature, parameters_plus_locals,
        local_groups, instructions, operand_stack, control_depth, globals, exports,
        data_segments, element_segments, name_bytes, table_elements, memory_pages);
    assert_eq!(frozen.functions(), 71);
    assert_eq!(frozen.instructions(), 113);
    assert_eq!(std::mem::size_of::<Policy<'_, false>>(), 8);
    assert_eq!(std::mem::size_of::<Policy<'_, true>>(), 8);
    assert_eq!(std::mem::size_of::<SwiftSelection>(), 8);
    assert_eq!(std::mem::size_of::<super::swift::ValidatedSwiftReactor>(), 664);
    assert_eq!(std::mem::size_of::<super::swift::ValidatedSwiftCommand>(), 664);
}

#[test]
fn r144_public_routes_seal_the_selected_entry_and_preserve_abi() {
    let reactor_bytes = Fixture::default().bytes();
    let reactor = validate_swift_reactor(&reactor_bytes, SwiftValidationBudget::default(), &Cancellation::default()).unwrap();
    assert_eq!(reactor.policy_identity(), "swift-reactor-experiment-v1");
    assert!(matches!(SnapshotView::policy(&reactor), SwiftSelection::Reactor));
    assert!(validate_swift_command(&reactor_bytes, SwiftValidationBudget::default(), &Cancellation::default()).is_err());
    let mut f = command();
    f.bodies[0] = vec![0, 0, 0x0b]; // If the runtime substitutes 34, it traps.
    f.exports[1].2 = 35;
    let sealed = validate(&f);
    assert_eq!(sealed.entry_function(), 35);
    assert_eq!(sealed.policy_identity(), "swift-command-diagnostic-v1");
    let (proof, entry) = sealed.into_parts();
    assert_eq!(entry, 35);
    assert!(matches!(SnapshotView::policy(&proof), SwiftSelection::Command { entry: 35 }));
    let borrowed = SwiftPolicy { policy: SnapshotView::policy(&proof), extent: proof.source().len(), parameters: 0 };
    assert_eq!(DecodePolicy::instructions(&borrowed), 16_000_000);
    let report = execute_swift_command(validate(&f), SwiftRunBudget::default(), WasiGrants::default(),
        WasiBudget::default(), Cancellation::default(), &mut vec![], &mut vec![]);
    assert!(report.succeeded(), "{report:?}");
    assert!(report.cleanup_completed);
    assert_eq!(report.after_cleanup.unwrap().reservations.combined.current, 0);
    for index in [0, 33, 62, 63, u32::MAX] {
        f.exports[1].2 = index;
        assert!(validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).is_err(), "entry {index}");
    }
    f.exports[1].2 = 35;
    // Identical fixed memory/table shapes isolate the incompatible export ABI.
    let reactor_shape = Fixture::default();
    f.memory = reactor_shape.memory; f.table = reactor_shape.table;
    assert_eq!(validate_swift_reactor(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).err().unwrap().code, "swift_export_count");
}

#[test]
fn r144_uncalled_body_beyond_old_count_is_fully_checked() {
    let mut f = command();
    f.function_types = vec![34; 80_514];
    f.bodies = vec![vec![0, 0x0b]; 80_514];
    let proof = validate(&f);
    assert_eq!(proof.observations().validated_bodies, 80_514);
    drop(proof);
    assert_eq!(validate_swift_reactor(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).err().unwrap().limit, 79_966);
    for (body, kind) in [(vec![0, 0, 0xff, 0x0b], SwiftValidationFailureKind::Unsupported),
        (vec![0, 0x1a, 0x0b], SwiftValidationFailureKind::Validation)] {
        f.bodies[80_513] = body;
        let e = validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).err().unwrap();
        assert_eq!(e.function, Some(80_547));
        assert_eq!(e.kind, kind, "{e:?}");
        println!("late_uncalled_rejected={e:?}");
    }
}

struct ScanMeter { work: u64 }
impl sealed::Meter for ScanMeter {}
impl DecodeMeter for ScanMeter {
    type Failure = &'static str;
    fn error(&mut self, _: CacheFailureKind, code: &'static str) -> Self::Failure { code }
    fn check(&mut self) -> Result<(), Self::Failure> { Ok(()) }
    fn work(&mut self, n: u64) -> Result<(), Self::Failure> { self.work += n; Ok(()) }
    fn set_offset(&mut self, _: usize) {}
    fn exact_capacity(&mut self, n: usize, actual: usize) -> Result<(), Self::Failure> { assert_eq!(n, actual); Ok(()) }
}
fn scan(policy: &impl DecodePolicy, body: &[u8]) -> Result<(), &'static str> {
    let mut controls = [decode::EMPTY_PATCH; 512];
    let mut depth = 0;
    let mut counts = decode::Counts::default();
    let mut meter = ScanMeter { work: 0 };
    decode::scan_borrowed(body, 0, policy, &mut meter,
        decode::PassParts { controls: &mut controls, depth: &mut depth, counts: &mut counts }, None)?;
    assert!(meter.work > body.len() as u64);
    Ok(())
}
#[test]
fn r144_real_decoder_preserves_command_and_frozen_instruction_ceilings() {
    // Scan-only exercises the actual decoder without allocating decoded IR.
    let mut body = vec![1; 8_000_002];
    body[0] = 0; *body.last_mut().unwrap() = 0x0b;
    let reactor = SwiftSelection::Reactor;
    let command = SwiftSelection::Command { entry: 35 };
    let reactor_policy = SwiftPolicy { policy: &reactor, extent: body.len(), parameters: 0 };
    let command_policy = SwiftPolicy { policy: &command, extent: body.len(), parameters: 0 };
    assert_eq!(scan(&reactor_policy, &body), Err("decode_instructions"));
    assert_eq!(scan(&command_policy, &body), Ok(()));
    let mut over = vec![1; 16_000_002];
    over[0] = 0; *over.last_mut().unwrap() = 0x0b;
    let command_policy = SwiftPolicy { policy: &command, extent: over.len(), parameters: 0 };
    assert_eq!(scan(&command_policy, &over), Err("decode_instructions"));
    let limits = Limits { instructions: 2, ..Default::default() };
    let frozen = FrozenPolicy { limits: &limits, extent: 4 };
    assert_eq!(scan(&frozen, &[0, 1, 0x0b]), Ok(()));
    assert_eq!(scan(&frozen, &[0, 1, 1, 0x0b]), Err("decode_instructions"));
}
