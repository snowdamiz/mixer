// Independently authored actual phase/State/AccountedWasi integration checks.
use super::super::tests::{
    self as frames, cursor, hooks, install_foreign, pin_ids, restore_foreign, retire, Hooks,
};
use super::*;
use crate::experimental_swift_reactor::{
    allocation_tests::measure_extended, validate_swift_reactor, SwiftValidationBudget,
};
use crate::experimental_wasi::{Errno, Resource, WasiFailure};
use std::cell::Cell;
use std::time::Duration;
thread_local! {
 pub(super) static PC_OVERFLOW:Cell<bool>=const{Cell::new(false)};
 static BEFORE:Cell<u8>=const{Cell::new(0)};
 static REMOVE_DEBT:Cell<bool>=const{Cell::new(false)};
 static FIXTURES:Cell<usize>=const{Cell::new(0)};
 static STEPS:Cell<usize>=const{Cell::new(0)};
}
struct Bounds;
impl Bounds {
    fn new() -> Self {
        reset();
        FIXTURES.with(|x| x.set(0));
        STEPS.with(|x| x.set(0));
        Self
    }
}
impl Drop for Bounds {
    fn drop(&mut self) {
        if !std::thread::panicking() {
            assert!(FIXTURES.with(Cell::get) <= 72);
            assert!(STEPS.with(Cell::get) <= 128);
            println!(
                "HOST_BOUND fixtures={} steps={} maxFixtures=72 maxSteps=128 maxFrames=3",
                FIXTURES.with(Cell::get),
                STEPS.with(Cell::get)
            );
        }
    }
}
fn reset() {
    hooks(Hooks::default());
    PC_OVERFLOW.with(|x| x.set(false));
    BEFORE.with(|x| x.set(0));
    REMOVE_DEBT.with(|x| x.set(false));
}
pub(super) fn before_dispatch(p: &mut FrameOperationPhase<'_>) {
    match BEFORE.with(Cell::get) {
        1 => p.phase.operation.control.cancellation().cancel(),
        2 => {
            std::thread::sleep(
                p.phase
                    .operation
                    .control
                    .deadline()
                    .saturating_duration_since(Instant::now())
                    + Duration::from_millis(2),
            );
            assert!(Instant::now() >= p.phase.operation.control.deadline());
        }
        _ => {}
    }
}
pub(super) fn before_remove(p: &mut FrameOperationPhase<'_>, n: usize) {
    if REMOVE_DEBT.with(Cell::get) {
        p.phase
            .operation
            .control
            .remove_live_with_wasi(Live::Values, n, Some(p.phase.operation.wasi.usage()))
            .unwrap();
    }
}
pub(super) fn before_push(p: &mut FrameOperationPhase<'_>) {
    match BEFORE.with(Cell::get) {
        3 => p.phase.operation.control.cancellation().cancel(),
        4 => p.phase.parts.frames.last_mut().unwrap().operands = usize::MAX,
        _ => {}
    }
}
fn storage<'a>() -> FrameOperationStorage<'a> {
    FrameOperationStorage {
        preparation: None,
        entry: None,
        returned: None,
        drained: None,
        controlled: None,
    }
}
fn observed(p: &FrameOperationPhase<'_>) -> SwiftRunUsage {
    p.phase
        .operation
        .control
        .usage(Some(p.phase.operation.wasi.usage()))
}
const BODY: &[u8] = &[0x41, 0, 0x10, 6, 0x1a, 0x0b];
fn owner(
    budget: SwiftRunBudget,
    wasi: WasiBudget,
    grants: WasiGrants,
    locals: &[Type],
) -> SwiftReactorInstance {
    owner_body(BODY, budget, wasi, grants, locals)
}
fn owner_body(
    body: &[u8],
    budget: SwiftRunBudget,
    wasi: WasiBudget,
    grants: WasiGrants,
    locals: &[Type],
) -> SwiftReactorInstance {
    FIXTURES.with(|x| x.set(x.get() + 1));
    let bytes = frames::control_tests::host_test_bytes(body, false, locals);
    let proof = validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &crate::Cancellation::default(),
    )
    .unwrap();
    let mut pair = Some(
        RuntimeControl::adopt(
            proof,
            budget,
            Instant::now(),
            crate::Cancellation::default(),
        )
        .unwrap(),
    );
    SwiftReactorInstance::construct(&mut pair, grants, wasi, Instant::now(), cursor()).unwrap()
}
fn bare(body: &[u8], enter: bool, action: impl FnOnce(&mut FrameOperationPhase<'_>)) {
    let mut own = owner_body(
        body,
        SwiftRunBudget::default(),
        small(),
        WasiGrants::default(),
        &[],
    );
    let mut prep = Some(own.prepare_frames(cursor()));
    let mut p = prep.take().unwrap().unwrap();
    if enter {
        p.enter(34).unwrap();
    }
    action(&mut p);
    reset();
    assert_eq!(p.drain().retained_frames, 0);
    assert!(matches!(
        host_operation_complete(
            p,
            FrameOperationStorage {
                preparation: prep,
                ..storage()
            }
        ),
        FrameCompletion::Completed
    ));
    retire(own);
}
fn small() -> WasiBudget {
    WasiBudget {
        one_transfer_bytes: 64,
        log_bytes: 64,
        ..WasiBudget::default()
    }
}
fn grants() -> WasiGrants {
    WasiGrants {
        secure_random: true,
        realtime: true,
        monotonic: true,
        stdout: true,
        stderr: true,
    }
}
fn fixture_with(
    budget: SwiftRunBudget,
    wasi: WasiBudget,
    grants: WasiGrants,
    locals: &[Type],
    action: impl FnOnce(&mut FrameOperationPhase<'_>),
) {
    let mut own = owner(budget, wasi, grants, locals);
    let bound = own
        .control
        .as_ref()
        .unwrap()
        .usage(None)
        .reservations
        .construction
        .current;
    let mut prepared = Some(own.prepare_frames(cursor()));
    let mut p = prepared.take().unwrap().unwrap();
    p.enter(34).unwrap();
    action(&mut p);
    reset();
    let report = p.drain();
    assert_eq!(report.retained_frames, 0);
    let done = host_operation_complete(
        p,
        FrameOperationStorage {
            preparation: prepared,
            ..storage()
        },
    );
    if report.live_unreconciled {
        assert!(matches!(done, FrameCompletion::Retained(_)));
        let mut retained = Some(own);
        assert!(SwiftReactorInstance::cleanup_owned(&mut retained).is_err());
        assert!(retained.is_some());
        drop(retained);
        println!("HOST_DEBT original authority deliberately dropped after explicit retained result; no clean receipt");
    } else {
        assert!(matches!(done, FrameCompletion::Completed));
        assert_eq!(
            own.control
                .as_ref()
                .unwrap()
                .usage(None)
                .reservations
                .construction
                .current,
            bound
        );
        retire(own);
    }
}
fn fixture(action: impl FnOnce(&mut FrameOperationPhase<'_>)) {
    fixture_with(
        SwiftRunBudget::default(),
        small(),
        WasiGrants::default(),
        &[],
        action,
    )
}
fn push(p: &mut FrameOperationPhase<'_>, args: &[Value]) {
    for v in args {
        p.phase.push_value(*v).unwrap();
    }
}
fn call(
    p: &mut FrameOperationPhase<'_>,
    function: WasiFunction,
    args: &[Value],
) -> Result<(), SwiftRunFailure> {
    STEPS.with(|x| x.set(x.get() + 1));
    push(p, args);
    let index = WasiFunction::ALL
        .iter()
        .position(|f| *f == function)
        .unwrap() as u32;
    let mut slot = None;
    p.host_operation(index, &mut slot).unwrap();
    slot.unwrap()
}
fn zero(ty: &Type) -> Value {
    match ty {
        Type::I32 => Value::I32(0),
        Type::I64 => Value::I64(0),
        Type::F32 => Value::F32(0),
        Type::F64 => Value::F64(0),
    }
}
fn i(n: u32) -> Value {
    Value::I32(n as i32)
}
#[test]
fn h01_sealed_34_original_descriptors_and_nonimport() {
    let _b = Bounds::new();
    for (index, f) in WasiFunction::ALL.into_iter().enumerate() {
        fixture(|p| {
            let proof = p.phase.parts.cache.proof();
            assert_eq!(proof.execution_imports()[index], f);
            let signature = proof.execution_signature(index as u32).unwrap();
            assert_eq!(signature.params, f.parameters());
            assert_eq!(signature.result.as_slice(), f.results());
            let args = f.parameters().iter().map(zero).collect::<Vec<_>>();
            let pins = pin_ids(p);
            let before = observed(p);
            let result = call(p, f, &args);
            let after = observed(p);
            assert_eq!(after.host_calls - before.host_calls, 1);
            assert_eq!(after.wasi.unwrap().calls - before.wasi.unwrap().calls, 1);
            assert_eq!(pin_ids(p), pins);
            if f == WasiFunction::ProcExit {
                assert_eq!(result.unwrap_err().guest_exit, Some(0));
                assert_eq!(p.phase.parts.values.len(), args.len());
            } else {
                result.unwrap();
                assert_eq!(p.phase.parts.values.len(), 1);
                assert!(matches!(p.phase.parts.values[0], Value::I32(0..=76)));
            }
        });
    }
    for index in [34, 62, u32::MAX] {
        fixture(|p| {
            let before = observed(p);
            let mut slot = None;
            p.host_operation(index, &mut slot).unwrap();
            assert_eq!(slot.unwrap().unwrap_err().code, "swift_host_import_index");
            assert_eq!(observed(p).execution_work, before.execution_work);
            assert_eq!(observed(p).host_calls, before.host_calls);
        });
    }
}
#[test]
fn h02_original_owner_admission_missing_and_foreign() {
    let _b = Bounds::new();
    for foreign in [false, true] {
        for which in 0..10 {
            let mut own = owner(
                SwiftRunBudget::default(),
                small(),
                WasiGrants::default(),
                &[],
            );
            let mut other = owner(
                SwiftRunBudget::default(),
                small(),
                WasiGrants::default(),
                &[],
            );
            let before = own.control.as_ref().unwrap().usage(None);
            let foreign_ticket = if foreign {
                match which {
                    0 => other.wasi.as_mut().unwrap().host_test_header(None),
                    1 => crate::experimental_swift_reactor::cache::inspection::replace_header(
                        other.cache.as_mut().unwrap(),
                        None,
                    ),
                    2 => other.state.as_mut().unwrap().execution_header.take(),
                    3 => other
                        .control
                        .as_mut()
                        .unwrap()
                        .test_replace_construction(None),
                    _ => other.state.as_mut().unwrap().buffers[which - 4].take(),
                }
            } else {
                None
            };
            let original = match which {
                0 => own.wasi.as_mut().unwrap().host_test_header(foreign_ticket),
                1 => crate::experimental_swift_reactor::cache::inspection::replace_header(
                    own.cache.as_mut().unwrap(),
                    foreign_ticket,
                ),
                2 => std::mem::replace(
                    &mut own.state.as_mut().unwrap().execution_header,
                    foreign_ticket,
                ),
                3 => own
                    .control
                    .as_mut()
                    .unwrap()
                    .test_replace_construction(foreign_ticket),
                _ => std::mem::replace(
                    &mut own.state.as_mut().unwrap().buffers[which - 4],
                    foreign_ticket,
                ),
            };
            let failure = match own.prepare_frames(cursor()) {
                Err(f) => f,
                Ok(_) => panic!("foreign owner admitted"),
            };
            assert_eq!(failure.at_failure.execution_work, before.execution_work);
            assert_eq!(failure.at_failure.host_calls, 0);
            assert_eq!(failure.at_failure.wasi.is_some(), which != 0);
            let taken = match which {
                0 => own.wasi.as_mut().unwrap().host_test_header(original),
                1 => crate::experimental_swift_reactor::cache::inspection::replace_header(
                    own.cache.as_mut().unwrap(),
                    original,
                ),
                2 => std::mem::replace(&mut own.state.as_mut().unwrap().execution_header, original),
                3 => own
                    .control
                    .as_mut()
                    .unwrap()
                    .test_replace_construction(original),
                _ => std::mem::replace(
                    &mut own.state.as_mut().unwrap().buffers[which - 4],
                    original,
                ),
            };
            if foreign {
                match which {
                    0 => {
                        assert!(other
                            .wasi
                            .as_mut()
                            .unwrap()
                            .host_test_header(taken)
                            .is_none());
                    }
                    1 => {
                        assert!(
                            crate::experimental_swift_reactor::cache::inspection::replace_header(
                                other.cache.as_mut().unwrap(),
                                taken
                            )
                            .is_none()
                        );
                    }
                    2 => other.state.as_mut().unwrap().execution_header = taken,
                    3 => {
                        assert!(other
                            .control
                            .as_mut()
                            .unwrap()
                            .test_replace_construction(taken)
                            .is_none());
                    }
                    _ => other.state.as_mut().unwrap().buffers[which - 4] = taken,
                }
            } else {
                assert!(taken.is_none());
            }
            retire(own);
            retire(other);
        }
    }
}
#[test]
fn h03_parameter_work_underflow_full_types_and_frame_floors() {
    let _b = Bounds::new();
    bare(BODY, false, |p| {
        push(p, &[i(0)]);
        let before = observed(p);
        let mut s = None;
        p.host_operation(6, &mut s).unwrap();
        assert_eq!(s.unwrap().unwrap_err().code, "swift_host_frame_missing");
        assert_eq!(observed(p).execution_work - before.execution_work, 1);
        assert_eq!(observed(p).host_calls, 0);
        assert_eq!(p.phase.parts.values.as_slice(), &[i(0)]);
    });
    fixture(|p| {
        let before = observed(p);
        let mut s = None;
        p.host_operation(1, &mut s).unwrap();
        assert_eq!(s.unwrap().unwrap_err().code, "swift_host_parameters");
        assert_eq!(observed(p).execution_work - before.execution_work, 2);
        assert_eq!(observed(p).host_calls, 0);
    });
    for bad in 0..3 {
        fixture(|p| {
            let mut args = [i(0), Value::I64(0), i(0)];
            args[bad] = if bad == 1 { i(0) } else { Value::I64(0) };
            let before = observed(p);
            assert_eq!(
                call(p, WasiFunction::ClockTimeGet, &args).unwrap_err().code,
                "swift_host_parameter_type"
            );
            assert_eq!(observed(p).execution_work - before.execution_work, 3 + 3);
            assert_eq!(observed(p).host_calls, 0);
            assert_eq!(p.phase.parts.values.as_slice(), &args);
        });
    }
    for fault in 0..3 {
        fixture(|p| {
            push(p, &[i(0)]);
            let f = &p.phase.parts.frames[0];
            let saved = (f.base, f.operands, f.controls);
            let f = &mut p.phase.parts.frames[0];
            match fault {
                0 => f.operands = 1,
                1 => f.base = 1,
                _ => f.controls = usize::MAX,
            };
            let before = observed(p);
            let mut s = None;
            p.host_operation(6, &mut s).unwrap();
            assert_eq!(s.unwrap().unwrap_err().code, "swift_host_frame_floor");
            assert_eq!(observed(p).execution_work - before.execution_work, 1);
            let f = &mut p.phase.parts.frames[0];
            (f.base, f.operands, f.controls) = saved;
        });
    }
    fixture_with(
        SwiftRunBudget::default(),
        small(),
        WasiGrants::default(),
        &[Type::I32],
        |p| {
            let before = observed(p);
            let mut s = None;
            p.host_operation(6, &mut s).unwrap();
            assert_eq!(s.unwrap().unwrap_err().code, "swift_host_frame_floor");
            assert_eq!(p.phase.parts.values.len(), 1);
            assert_eq!(observed(p).execution_work - before.execution_work, 1);
        },
    );
}
#[test]
fn h04_actual_pinned_prefix_and_occupied_failure() {
    let _b = Bounds::new();
    bare(&[0x10, 34, 0x0b], true, |p| {
        let before = observed(p);
        let pins = pin_ids(p);
        let mut s = storage();
        host_operation_pinned_caller(p, &mut s).unwrap();
        assert_eq!(
            s.entry.unwrap().unwrap_err().code,
            "swift_host_import_index"
        );
        assert_eq!(p.phase.parts.frames[0].pc, 1);
        assert_eq!(observed(p).instructions - before.instructions, 1);
        assert_eq!(observed(p).execution_work - before.execution_work, 1);
        assert_eq!(observed(p).host_calls, 0);
        assert_eq!(pin_ids(p), pins);
    });
    fixture(|p| {
        push(p, &[i(0)]);
        p.phase.parts.frames[0].pc = 1;
        let pins = pin_ids(p);
        let selected = {
            let f = &p.phase.parts.frames[0];
            p.phase
                .parts
                .cache
                .view(
                    &f.pin,
                    p.phase.operation.control,
                    Some(&*p.phase.operation.wasi),
                )
                .unwrap()
                .instructions[1]
        };
        let before = observed(p);
        let mut s = storage();
        host_operation_pinned_caller(p, &mut s).unwrap();
        assert_eq!(s.entry, Some(Ok(())));
        assert_eq!(p.phase.parts.frames[0].pc, 2);
        assert_eq!(pin_ids(p), pins);
        let after = observed(p);
        assert_eq!(
            (
                after.instructions - before.instructions,
                after.instruction_fuel - before.instruction_fuel,
                after.execution_work - before.execution_work
            ),
            (1, 1, 4)
        );
        assert_eq!(
            (
                p.phase.operation.cursor.function,
                p.phase.operation.cursor.offset
            ),
            (Some(34), Some(selected.offset))
        );
    });
    for saved_failed in [false, true] {
        for direct in [false, true] {
            fixture(|p| {
                p.phase.parts.frames[0].pc = 1;
                let mut s = storage();
                let saved = if saved_failed {
                    Err(p.invariant("host_original_failure"))
                } else {
                    Ok(())
                };
                s.entry = Some(saved);
                let before = observed(p);
                let result = if direct {
                    p.host_operation(6, &mut s.entry)
                } else {
                    host_operation_pinned_caller(p, &mut s)
                };
                assert!(result.is_err());
                assert_eq!(s.entry, Some(saved));
                assert_eq!(p.phase.parts.frames[0].pc, 1);
                assert_eq!(observed(p).instructions, before.instructions);
                assert_eq!(observed(p).execution_work, before.execution_work);
            });
        }
    }
    for fault in 0..5 {
        fixture(|p| {
            push(p, &[i(0)]);
            p.phase.parts.frames[0].pc = 1;
            let old = if fault == 3 {
                Some(
                    p.phase
                        .operation
                        .control
                        .test_replace_execution_work_limit(observed(p).execution_work),
                )
            } else {
                None
            };
            match fault {
                0 => p.phase.operation.control.cancellation().cancel(),
                1 => PC_OVERFLOW.with(|x| x.set(true)),
                2 => p.phase.parts.frames[0].pc = usize::MAX,
                4 => p.phase.parts.frames[0].pc = 0,
                _ => {}
            }
            let mut s = storage();
            host_operation_pinned_caller(p, &mut s).unwrap();
            assert!(s.entry.unwrap().is_err());
            assert_eq!(observed(p).host_calls, 0);
            assert_eq!(p.phase.parts.values.len(), 1);
            if let Some(old) = old {
                p.phase
                    .operation
                    .control
                    .test_replace_execution_work_limit(old);
            }
        });
    }
    fixture_with(
        SwiftRunBudget {
            instruction_fuel: 0,
            ..SwiftRunBudget::default()
        },
        small(),
        WasiGrants::default(),
        &[],
        |p| {
            push(p, &[i(0)]);
            p.phase.parts.frames[0].pc = 1;
            let before = observed(p);
            let mut s = storage();
            host_operation_pinned_caller(p, &mut s).unwrap();
            assert_eq!(
                s.entry.unwrap().unwrap_err().kind,
                SwiftRunFailureKind::FuelExhausted
            );
            assert_eq!(p.phase.parts.frames[0].pc, 1);
            assert_eq!(observed(p).execution_work, before.execution_work);
        },
    );
}
#[test]
fn h05_sole_host_entry_zero_exact_overflow_and_cancel() {
    let _b = Bounds::new();
    for limit in [0, 1] {
        fixture_with(
            SwiftRunBudget {
                host_calls: limit,
                ..SwiftRunBudget::default()
            },
            small(),
            WasiGrants::default(),
            &[],
            |p| {
                if limit == 1 {
                    call(p, WasiFunction::FdClose, &[i(0)]).unwrap();
                    assert_eq!(p.phase.pop_value().unwrap(), i(8));
                }
                let failure = call(p, WasiFunction::FdClose, &[i(0)]).unwrap_err();
                assert_eq!(failure.kind, SwiftRunFailureKind::HostCallLimit);
                assert_eq!(observed(p).host_calls, limit);
                assert_eq!(observed(p).wasi.unwrap().calls, limit);
                assert_eq!(failure.attempted, limit + 1);
                assert_eq!(failure.limit, limit);
            },
        );
    }
    fixture(|p| {
        p.phase.operation.control.host_test_counter(u64::MAX);
        let failure = call(p, WasiFunction::FdClose, &[i(0)]).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::HostCallLimit);
        assert_eq!(observed(p).host_calls, u64::MAX);
        assert_eq!(observed(p).wasi.unwrap().calls, 0);
    });
    fixture(|p| {
        push(p, &[i(0)]);
        BEFORE.with(|x| x.set(1));
        let mut s = None;
        p.host_operation(6, &mut s).unwrap();
        assert_eq!(s.unwrap().unwrap_err().kind, SwiftRunFailureKind::Cancelled);
        assert_eq!(observed(p).host_calls, 0);
        assert_eq!(observed(p).wasi.unwrap().calls, 0);
        assert_eq!(p.phase.parts.values.as_slice(), &[i(0)]);
    });
}
#[test]
fn h06_actual_adapter_budget_distinctions() {
    let _b = Bounds::new();
    for resource in [
        Resource::Calls,
        Resource::Work,
        Resource::Transfer,
        Resource::TransferSize,
        Resource::Iovecs,
    ] {
        let mut w = small();
        let (f, args) = match resource {
            Resource::Calls => {
                w.calls = 0;
                (WasiFunction::ArgsSizesGet, vec![i(0), i(4)])
            }
            Resource::Work => {
                w.work = 0;
                (WasiFunction::ArgsSizesGet, vec![i(0), i(4)])
            }
            Resource::Transfer => {
                w.transfer_bytes = 0;
                (WasiFunction::ArgsSizesGet, vec![i(0), i(4)])
            }
            Resource::TransferSize => (WasiFunction::RandomGet, vec![i(0), i(65)]),
            Resource::Iovecs => {
                w.iovecs = 0;
                (WasiFunction::FdWrite, vec![i(1), i(0), i(1), i(16)])
            }
        };
        fixture_with(SwiftRunBudget::default(), w, grants(), &[], |p| {
            let failure = call(p, f, &args).unwrap_err();
            assert_eq!(failure.kind, SwiftRunFailureKind::Wasi);
            assert_eq!(failure.wasi_failure, Some(WasiFailure::Budget(resource)));
            assert_eq!(observed(p).host_calls, 1);
            assert_eq!(
                observed(p).wasi.unwrap().calls,
                u64::from(resource != Resource::Calls)
            );
            assert_eq!(p.phase.parts.values.as_slice(), args.as_slice());
        });
    }
    fixture_with(
        SwiftRunBudget::default(),
        WasiBudget {
            log_bytes: 0,
            ..small()
        },
        grants(),
        &[],
        |p| {
            p.phase.parts.memory[0..8].copy_from_slice(&[32, 0, 0, 0, 1, 0, 0, 0]);
            p.phase.parts.memory[32] = b'x';
            call(p, WasiFunction::FdWrite, &[i(1), i(0), i(1), i(16)]).unwrap();
            assert_eq!(p.phase.parts.values.as_slice(), &[i(Errno::Nospc as u32)]);
            assert!(p.phase.operation.wasi.stdout().is_empty());
        },
    );
}
#[test]
fn h07_before_inside_after_dispatch_cancellation_and_rollback() {
    let _b = Bounds::new();
    for point in 0..3 {
        fixture(|p| {
            p.phase.parts.memory[..8].fill(0xa5);
            match point {
                0 => p.phase.operation.wasi.host_test_dispatch(true, false),
                1 => p.phase.operation.wasi.host_test_cancel_at(1),
                _ => p.phase.operation.wasi.host_test_dispatch(false, true),
            };
            let failure = call(p, WasiFunction::ArgsSizesGet, &[i(0), i(4)]).unwrap_err();
            assert_eq!(observed(p).host_calls, 1);
            assert_eq!(observed(p).wasi.unwrap().calls, 1);
            assert_eq!(
                failure.kind,
                if point == 2 {
                    SwiftRunFailureKind::Cancelled
                } else {
                    SwiftRunFailureKind::Wasi
                }
            );
            if point == 2 {
                assert_eq!(&p.phase.parts.memory[..8], &[1, 0, 0, 0, 6, 0, 0, 0]);
            } else {
                assert_eq!(&p.phase.parts.memory[..8], &[0xa5; 8]);
                assert_eq!(failure.wasi_failure, Some(WasiFailure::Cancelled));
            }
            assert_eq!(p.phase.parts.values.as_slice(), &[i(0), i(4)]);
        });
    }
    for checkpoint in 3..10 {
        fixture(|p| {
            p.phase.parts.memory[..10].fill(0xa5);
            p.phase.operation.wasi.host_test_cancel_at(checkpoint);
            let result = call(p, WasiFunction::ArgsGet, &[i(0), i(4)]);
            if let Err(f) = result {
                assert_eq!(f.wasi_failure, Some(WasiFailure::Cancelled));
                assert_eq!(&p.phase.parts.memory[..10], &[0xa5; 10]);
            } else {
                assert_eq!(&p.phase.parts.memory[..4], &4u32.to_le_bytes());
            }
        });
    }
}
#[test]
fn h08_actual_deadline_origins_and_real_os_postcheck() {
    let _b = Bounds::new();
    for wasi_origin in [false, true] {
        fixture_with(
            SwiftRunBudget {
                deadline_ms: if wasi_origin { 30_000 } else { 500 },
                ..SwiftRunBudget::default()
            },
            WasiBudget {
                deadline_ms: if wasi_origin { 500 } else { 30_000 },
                ..small()
            },
            grants(),
            &[],
            |p| {
                BEFORE.with(|x| x.set(2));
                let failure = call(p, WasiFunction::ClockResGet, &[i(0), i(0)]).unwrap_err();
                assert_eq!(failure.kind, SwiftRunFailureKind::Deadline);
                assert_eq!(
                    failure.deadline_origin,
                    if wasi_origin {
                        SwiftDeadlineOrigin::Wasi
                    } else {
                        SwiftDeadlineOrigin::Run
                    }
                );
                assert!(failure.at_failure.deadline_overshoot_micros > 0);
                assert_eq!(observed(p).host_calls, 0);
                assert_eq!(p.phase.operation.wasi.host_test_services(), 0);
                println!(
                    "HOST_DEADLINE preOS origin={:?} overshootMicros={}",
                    failure.deadline_origin, failure.at_failure.deadline_overshoot_micros
                );
            },
        );
    }
    fixture_with(
        SwiftRunBudget::default(),
        WasiBudget {
            deadline_ms: 500,
            ..small()
        },
        grants(),
        &[],
        |p| {
            p.phase.parts.memory[..8].fill(0xa5);
            p.phase.operation.wasi.host_test_service(8);
            assert!(Instant::now() < p.phase.operation.control.deadline());
            let failure = call(p, WasiFunction::ClockResGet, &[i(0), i(0)]).unwrap_err();
            assert_eq!(failure.kind, SwiftRunFailureKind::Wasi);
            assert_eq!(failure.wasi_failure, Some(WasiFailure::Deadline));
            assert_eq!(failure.deadline_origin, SwiftDeadlineOrigin::Wasi);
            assert_eq!(p.phase.operation.wasi.host_test_services(), 1);
            assert_eq!(&p.phase.parts.memory[..8], &[0xa5; 8]);
            assert_eq!(observed(p).wasi.unwrap().transfer_bytes, 8);
            println!("HOST_OS actual clock result discarded after finite600ms injected postOS delay; calls=1");
        },
    );
    fixture_with(SwiftRunBudget::default(), small(), grants(), &[], |p| {
        p.phase.operation.wasi.host_test_service(9);
        p.phase.parts.memory[..8].fill(0xa5);
        let failure = call(p, WasiFunction::ClockResGet, &[i(0), i(0)]).unwrap_err();
        assert_eq!(failure.wasi_failure, Some(WasiFailure::Cancelled));
        assert_eq!(p.phase.operation.wasi.host_test_services(), 1);
        assert_eq!(&p.phase.parts.memory[..8], &[0xa5; 8]);
    });
}
#[test]
fn h09_official_errno_zero_extended_and_actual_os() {
    let _b = Bounds::new();
    for (f, args, errno) in [
        (WasiFunction::EnvironGet, vec![i(0), i(0)], Errno::Success),
        (WasiFunction::FdClose, vec![i(0)], Errno::Badf),
        (WasiFunction::ArgsSizesGet, vec![i(0), i(0)], Errno::Inval),
        (
            WasiFunction::ArgsSizesGet,
            vec![i(u32::MAX), i(4)],
            Errno::Fault,
        ),
        (
            WasiFunction::PollOneoff,
            vec![i(0), i(0), i(0), i(0)],
            Errno::Notsup,
        ),
        (WasiFunction::RandomGet, vec![i(0), i(8)], Errno::Notcapable),
    ] {
        fixture(|p| {
            let pins = pin_ids(p);
            call(p, f, &args).unwrap();
            assert_eq!(
                p.phase.parts.values.as_slice(),
                &[Value::I32(i32::from(errno as u16))]
            );
            assert_eq!(pin_ids(p), pins);
        });
    }
    fixture_with(SwiftRunBudget::default(), small(), grants(), &[], |p| {
        p.phase.parts.memory[..8].fill(0xa5);
        p.phase.operation.wasi.host_test_service(1);
        call(p, WasiFunction::RandomGet, &[i(0), i(8)]).unwrap();
        assert_eq!(p.phase.parts.values.as_slice(), &[i(Errno::Io as u32)]);
        assert_eq!(&p.phase.parts.memory[..8], &[0xa5; 8]);
        assert_eq!(observed(p).wasi.unwrap().random_bytes, 0);
        assert_eq!(p.phase.operation.wasi.host_test_services(), 1);
    });
    fixture_with(SwiftRunBudget::default(), small(), grants(), &[], |p| {
        let pins = pin_ids(p);
        call(p, WasiFunction::RandomGet, &[i(0), i(32)]).unwrap();
        assert_eq!(p.phase.parts.values.as_slice(), &[i(0)]);
        assert_eq!(observed(p).wasi.unwrap().random_bytes, 32);
        assert_eq!(p.phase.operation.wasi.host_test_services(), 1);
        assert_eq!(pin_ids(p), pins);
        p.phase.pop_value().unwrap();
        call(p, WasiFunction::ClockResGet, &[i(0), i(40)]).unwrap();
        assert_eq!(p.phase.parts.values.as_slice(), &[i(0)]);
        assert_eq!(p.phase.operation.wasi.host_test_services(), 2);
        println!(
            "HOST_OS actual secure-random32 and realtime-resolution1; host={} adapter={}",
            observed(p).host_calls,
            observed(p).wasi.unwrap().calls
        );
    });
}
#[test]
fn h10_exit_exact_unsigned_first_cause_without_result() {
    let _b = Bounds::new();
    for code in [0, 17, u32::MAX] {
        fixture(|p| {
            p.phase.operation.wasi.host_test_dispatch(false, true);
            let failure = call(p, WasiFunction::ProcExit, &[i(code)]).unwrap_err();
            assert_eq!(failure.kind, SwiftRunFailureKind::GuestExit);
            assert_eq!(failure.guest_exit, Some(code));
            assert_eq!(failure.wasi_failure, None);
            assert_eq!(p.phase.parts.values.as_slice(), &[i(code)]);
            let first = failure.at_failure;
            assert_eq!(p.invariant("later").at_failure, first);
            assert_eq!(observed(p).host_calls, 1);
            assert_eq!(observed(p).wasi.unwrap().calls, 1);
        });
    }
}
#[test]
fn h11_typed_fault_precedes_later_postcheck_and_observation() {
    let _b = Bounds::new();
    fixture_with(
        SwiftRunBudget::default(),
        WasiBudget {
            calls: 0,
            ..small()
        },
        grants(),
        &[],
        |p| {
            p.phase.operation.wasi.host_test_dispatch(false, true);
            let failure = call(p, WasiFunction::RandomGet, &[i(0), i(8)]).unwrap_err();
            assert_eq!(failure.kind, SwiftRunFailureKind::Wasi);
            assert_eq!(
                failure.wasi_failure,
                Some(WasiFailure::Budget(Resource::Calls))
            );
            assert_eq!(
                failure.at_failure.wasi,
                Some(p.phase.operation.wasi.usage())
            );
            assert_eq!(failure.at_failure.host_calls, 1);
            assert_eq!(failure.at_failure.wasi.unwrap().calls, 0);
            assert_eq!(p.invariant("post-cancel").code, failure.code);
            let report = p.drain();
            assert_eq!(report.first_failure.unwrap().at_failure, failure.at_failure);
            assert_eq!(report.first_failure.unwrap().code, failure.code);
            assert!(report.first_failure.unwrap().after_cleanup.is_some());
            assert_eq!(report.first_failure.unwrap().at_failure, failure.at_failure);
        },
    );
    fixture_with(SwiftRunBudget::default(), small(), grants(), &[], |p| {
        p.phase.operation.wasi.host_test_service(5);
        p.phase.parts.memory[..8].fill(0xa5);
        let failure = call(p, WasiFunction::RandomGet, &[i(0), i(8)]).unwrap_err();
        assert_eq!(failure.wasi_failure, Some(WasiFailure::Cancelled));
        assert_eq!(observed(p).wasi.unwrap().random_bytes, 8);
        assert_eq!(&p.phase.parts.memory[..8], &[0xa5; 8]);
    });
}
#[test]
fn h12_actual_truncate_reconcile_push_work_capacity_and_predebit() {
    let _b = Bounds::new();
    for fault in [1, 2, 3, 4, 7] {
        fixture(|p| {
            push(p, &[i(0)]);
            hooks(Hooks {
                push_fault: if fault == 7 || fault == 3 { 0 } else { fault },
                ..Hooks::default()
            });
            let original_floor = p.phase.parts.frames[0].operands;
            if fault == 7 {
                BEFORE.with(|x| x.set(3));
            }
            if fault == 3 {
                BEFORE.with(|x| x.set(4));
            }
            let mut s = None;
            p.host_operation(6, &mut s).unwrap();
            let failure = s.unwrap().unwrap_err();
            assert_eq!(
                failure.kind,
                match fault {
                    1 => SwiftRunFailureKind::WorkExhausted,
                    2 | 4 => SwiftRunFailureKind::ValueLimit,
                    7 => SwiftRunFailureKind::Cancelled,
                    _ => SwiftRunFailureKind::Invariant,
                }
            );
            p.phase.parts.frames[0].operands = original_floor;
            assert!(p.phase.parts.values.is_empty());
            assert_eq!(observed(p).live.values.current, 0);
            assert_eq!(observed(p).host_calls, 1);
            assert_eq!(observed(p).wasi.unwrap().calls, 1);
            assert!(!p.cleanup.live_unreconciled);
        });
    }
    for allowed in [0, 1, 2, 3] {
        fixture(|p| {
            push(p, &[i(0)]);
            let before = observed(p);
            let old = p
                .phase
                .operation
                .control
                .test_replace_execution_work_limit(before.execution_work + allowed);
            let mut s = None;
            p.host_operation(6, &mut s).unwrap();
            p.phase
                .operation
                .control
                .test_replace_execution_work_limit(old);
            assert_eq!(s.unwrap().is_ok(), allowed == 3);
            assert_eq!(observed(p).host_calls, u64::from(allowed >= 2));
            assert_eq!(
                p.phase.parts.values.len(),
                usize::from(allowed <= 1 || allowed == 3)
            );
            assert_eq!(observed(p).live.values.current, p.phase.parts.values.len());
        });
    }
}
#[test]
fn h13_posttruncate_live_removal_debt_retained() {
    let _b = Bounds::new();
    fixture(|p| {
        push(p, &[i(0)]);
        REMOVE_DEBT.with(|x| x.set(true));
        let mut s = None;
        p.host_operation(6, &mut s).unwrap();
        let failure = s.unwrap().unwrap_err();
        assert_eq!(failure.code, "swift_run_live_underflow");
        assert_eq!((failure.function, failure.offset), (None, None));
        assert!(p.phase.parts.values.is_empty());
        assert!(p.cleanup.live_unreconciled);
        let bound = observed(p).reservations.construction.current;
        let report = p.drain();
        assert_eq!(report.first_failure.unwrap().at_failure, failure.at_failure);
        assert_eq!(report.first_failure.unwrap().code, failure.code);
        assert!(report.first_failure.unwrap().after_cleanup.is_some());
        assert!(report.live_unreconciled);
        assert_eq!(report.usage.reservations.construction.current, bound);
        assert_eq!(p.invariant("later").at_failure, failure.at_failure);
    });
}
#[test]
fn h14_recursive_pins_and_release_retry_keep_authority() {
    let _b = Bounds::new();
    let mut foreign = owner(
        SwiftRunBudget::default(),
        small(),
        WasiGrants::default(),
        &[],
    );
    install_foreign(&mut foreign);
    let mut own = owner(
        SwiftRunBudget::default(),
        small(),
        WasiGrants::default(),
        &[],
    );
    let bound = own
        .control
        .as_ref()
        .unwrap()
        .usage(None)
        .reservations
        .construction
        .current;
    let mut prepared = Some(own.prepare_frames(cursor()));
    let mut p = prepared.take().unwrap().unwrap();
    for f in [34, 36, 34] {
        p.enter(f).unwrap();
    }
    let pins = pin_ids(&p);
    call(&mut p, WasiFunction::FdClose, &[i(0)]).unwrap();
    assert_eq!(pin_ids(&p), pins);
    assert_eq!(observed(&p).live.active_pins.current, 3);
    hooks(Hooks {
        release_mask: 7,
        ..Hooks::default()
    });
    let report = p.drain();
    assert_eq!(report.retained_frames, 3);
    assert_eq!(pin_ids(&p), pins);
    assert!(observed(&p).reservations.construction.current > bound);
    assert!(matches!(
        host_operation_complete(
            p,
            FrameOperationStorage {
                preparation: prepared,
                ..storage()
            }
        ),
        FrameCompletion::Retained(_)
    ));
    reset();
    let mut prepared = Some(own.resume_frame_cleanup());
    let mut p = prepared.take().unwrap().unwrap();
    assert_eq!(p.drain().retained_frames, 0);
    assert!(matches!(
        host_operation_complete(
            p,
            FrameOperationStorage {
                preparation: prepared,
                ..storage()
            }
        ),
        FrameCompletion::Completed
    ));
    assert_eq!(
        own.control
            .as_ref()
            .unwrap()
            .usage(None)
            .reservations
            .construction
            .current,
        bound
    );
    restore_foreign(&mut foreign);
    retire(own);
    retire(foreign);
}
#[test]
fn h15_real_zero_allocation_interval_and_sole_fixed_outcome() {
    let _b = Bounds::new();
    fixture(|p| {
        call(p, WasiFunction::ArgsSizesGet, &[i(0), i(4)]).unwrap();
        p.phase.pop_value().unwrap();
        push(p, &[i(0), i(4)]);
        let before = observed(p);
        let cap = p.phase.parts.values.capacity();
        let pins = pin_ids(p);
        let mut s = storage();
        let (outer, stats) = measure_extended(Some(0), || p.host_operation(1, &mut s.entry));
        outer.unwrap();
        assert_eq!(s.entry, Some(Ok(())));
        assert_eq!(stats.attempts, 0);
        assert_eq!(stats.allocations, 0);
        assert_eq!(stats.reallocations, 0);
        assert_eq!(p.phase.parts.values.capacity(), cap);
        assert_eq!(pin_ids(p), pins);
        assert_eq!(observed(p).host_calls - before.host_calls, 1);
        assert_eq!(observed(p).reservations, before.reservations);
        println!("HOST_ALLOC interval=actual warmed imported ArgsSizesGet operation only attempts={} allocations={} reallocations={}",stats.attempts,stats.allocations,stats.reallocations);
        s.entry.take().unwrap().unwrap();
        p.phase.pop_value().unwrap();
        push(p, &[i(0)]);
        p.host_operation(6, &mut s.entry).unwrap();
        assert_eq!(s.entry, Some(Ok(())));
    });
    fixture(|p| {
        p.phase.parts.frames[0].pc = 1;
        push(p, &[i(0)]);
        p.phase.operation.wasi.host_test_dispatch(false, true);
        let mut s = storage();
        host_operation_pinned_caller(p, &mut s).unwrap();
        let first = s.entry.unwrap().unwrap_err();
        let before = observed(p);
        let pc = p.phase.parts.frames[0].pc;
        assert!(host_operation_pinned_caller(p, &mut s).is_err());
        assert_eq!(s.entry, Some(Err(first)));
        assert_eq!(p.phase.parts.frames[0].pc, pc);
        assert_eq!(observed(p).instructions, before.instructions);
        assert_eq!(observed(p).host_calls, before.host_calls);
    });
    let mut own = owner(
        SwiftRunBudget::default(),
        small(),
        WasiGrants::default(),
        &[],
    );
    let baseline = own
        .control
        .as_ref()
        .unwrap()
        .usage(None)
        .reservations
        .construction
        .current;
    let mut prep = Some(own.prepare_frames(cursor()));
    let mut p = prep.take().unwrap().unwrap();
    p.enter(34).unwrap();
    call(&mut p, WasiFunction::FdClose, &[i(0)]).unwrap();
    p.drain();
    let retained = observed(&p).reservations.construction.current;
    let mut s = storage();
    s.preparation = prep;
    s.controlled = Some(Ok(false));
    assert!(matches!(
        host_operation_complete(p, s),
        FrameCompletion::Retained(_)
    ));
    assert_eq!(
        own.control
            .as_ref()
            .unwrap()
            .usage(None)
            .reservations
            .construction
            .current,
        retained
    );
    let mut prep = Some(own.resume_frame_cleanup());
    let mut p = prep.take().unwrap().unwrap();
    p.drain();
    assert!(matches!(
        host_operation_complete(
            p,
            FrameOperationStorage {
                preparation: prep,
                ..storage()
            }
        ),
        FrameCompletion::Completed
    ));
    assert_eq!(
        own.control
            .as_ref()
            .unwrap()
            .usage(None)
            .reservations
            .construction
            .current,
        baseline
    );
    retire(own);
}
#[test]
fn h16_positive_accounting_and_scope() {
    let _b = Bounds::new();
    fixture(|p| {
        assert_eq!(SwiftRunBudget::default().state_bytes, 128 * 1024 * 1024);
        assert_eq!(SwiftRunBudget::default().combined_bytes, 256 * 1024 * 1024);
        assert_eq!(MAX_RESERVATION_TICKETS, 86);
        assert!(observed(p).reservations.state.current >= execution_header_bytes().unwrap());
        assert!(observed(p).reservations.construction.current >= FRAME_OPERATION_BYTES.unwrap());
        println!("HOST_ACCOUNT permanent={} active={} header={} envelope={} ticketMax=86 State=134217728 Combined=268435456",size_of::<HostPermanentPositions>(),size_of::<HostActivePositions>(),execution_header_bytes().unwrap(),FRAME_OPERATION_BYTES.unwrap());
    });
}
