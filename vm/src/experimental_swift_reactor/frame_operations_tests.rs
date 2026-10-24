//! Real constructed owners, actual cache pins and entry-created frames only.
//! Hooks narrow original budgets or reject actual pre-effect boundaries. No
//! token/frame constructors, ledger rewriting or dispatcher are used here.
use super::*;
use crate::experimental::cache::{borrowed::PinToken, ControlKind};
use crate::experimental_swift_reactor::{
    allocation_tests::measure_extended, validate_swift_reactor, SwiftValidationBudget,
};
use crate::experimental_wasi::WasiFunction;
use crate::Cancellation;
use std::cell::{Cell, RefCell};

#[derive(Clone, Copy)]
pub(super) struct Hooks {
    reject_cache_completion: bool,
    cancel_local: Option<usize>,
    predebit_resource: Option<u8>,
    predebit_ordinal: usize,
    predebit_seen: usize,
    release_mask: u64,
    release_seen: usize,
    release_order: [u32; 64],
    reject_outer_restore: bool,
    push_fault: u8,
    push_room_reject: bool,
}
impl Default for Hooks {
    fn default() -> Self {
        Self {
            reject_cache_completion: false,
            cancel_local: None,
            predebit_resource: None,
            predebit_ordinal: 0,
            predebit_seen: 0,
            release_mask: 0,
            release_seen: 0,
            release_order: [0; 64],
            reject_outer_restore: false,
            push_fault: 0,
            push_room_reject: false,
        }
    }
}
thread_local! {
    static HOOKS: Cell<Hooks> = Cell::new(Hooks::default());
    // Both options own original non-Clone tickets; every temporary replacement
    // returns the actual replaced token and fixtures restore both owners.
    static FOREIGN_HEADER: RefCell<Option<ReservationTicket>> = const { RefCell::new(None) };
    static ORIGINAL_HEADER: RefCell<Option<ReservationTicket>> = const { RefCell::new(None) };
}
fn hooks(hooks: Hooks) {
    HOOKS.with(|slot| slot.set(hooks));
}
pub(super) fn before_cache_completion(phase: &mut CacheOperationPhase<'_>) {
    if HOOKS.with(|slot| slot.get().reject_cache_completion) {
        super::super::super::cache::inspection::replace_operation_restore_bound(phase, 0);
    }
}
pub(super) fn before_local(control: &RuntimeControl, index: usize) {
    if HOOKS.with(|slot| slot.get().cancel_local == Some(index)) {
        control.cancellation().cancel();
    }
}
fn resource_code(resource: Live) -> u8 {
    match resource {
        Live::Values => 0,
        Live::Controls => 1,
        Live::Frames => 2,
        _ => 3,
    }
}
pub(super) fn before_predebit(control: &mut RuntimeControl, resource: Live) -> Option<usize> {
    let selected = HOOKS.with(|slot| {
        let mut hooks = slot.get();
        if hooks.predebit_resource != Some(resource_code(resource)) {
            return false;
        }
        let selected = hooks.predebit_seen == hooks.predebit_ordinal;
        hooks.predebit_seen += 1;
        slot.set(hooks);
        selected
    });
    if !selected {
        return None;
    }
    let live = control.usage(None).live;
    let limit = match resource {
        Live::Values => live.values.current,
        Live::Controls => live.controls.current,
        Live::Frames => live.frames.current,
        _ => unreachable!(),
    };
    Some(control.test_replace_live_limit(resource, limit))
}
pub(super) fn after_predebit(control: &mut RuntimeControl, resource: Live, old: Option<usize>) {
    if let Some(old) = old {
        control.test_replace_live_limit(resource, old);
    }
}
pub(super) fn before_release(cache: &mut SwiftFunctionCache, function: u32) {
    let reject = HOOKS.with(|slot| {
        let mut hooks = slot.get();
        let ordinal = hooks.release_seen;
        assert!(ordinal < 64);
        hooks.release_order[ordinal] = function;
        hooks.release_seen += 1;
        let reject = hooks.release_mask & (1 << ordinal) != 0;
        slot.set(hooks);
        reject
    });
    if reject {
        let foreign = FOREIGN_HEADER
            .with(|slot| slot.borrow_mut().take())
            .expect("held real foreign header");
        let original = super::super::super::cache::inspection::replace_header(cache, Some(foreign));
        ORIGINAL_HEADER.with(|slot| {
            assert!(slot.borrow().is_none());
            *slot.borrow_mut() = original;
        });
    }
}
pub(super) fn after_release(cache: &mut SwiftFunctionCache) {
    if let Some(original) = ORIGINAL_HEADER.with(|slot| slot.borrow_mut().take()) {
        let foreign = super::super::super::cache::inspection::replace_header(cache, Some(original));
        FOREIGN_HEADER.with(|slot| {
            assert!(slot.borrow().is_none());
            *slot.borrow_mut() = foreign;
        });
    }
}
pub(super) fn outer_restore_target(previous: usize) -> usize {
    if HOOKS.with(|slot| slot.get().reject_outer_restore) {
        0
    } else {
        previous
    }
}
pub(super) fn before_result_push(control: &mut RuntimeControl) -> Option<(u8, u64)> {
    HOOKS.with(|slot| {
        let mut hooks = slot.get();
        hooks.push_room_reject = hooks.push_fault == 4;
        slot.set(hooks);
    });
    match HOOKS.with(|slot| slot.get().push_fault) {
        1 => Some((
            1,
            control.test_replace_execution_work_limit(control.usage(None).execution_work),
        )),
        2 => Some((
            2,
            control.test_replace_live_limit(Live::Values, control.usage(None).live.values.current)
                as u64,
        )),
        _ => None,
    }
}
pub(super) fn observed_push_capacity(capacity: usize, length: usize) -> usize {
    HOOKS.with(|slot| {
        let mut hooks = slot.get();
        let reject = hooks.push_room_reject;
        hooks.push_room_reject = false;
        slot.set(hooks);
        if reject {
            length
        } else {
            capacity
        }
    })
}
pub(super) fn after_result_push(control: &mut RuntimeControl, old: Option<(u8, u64)>) {
    match old {
        Some((1, old)) => {
            control.test_replace_execution_work_limit(old);
        }
        Some((2, old)) => {
            control.test_replace_live_limit(Live::Values, old as usize);
        }
        _ => {}
    }
}
fn cursor() -> Cursor {
    Cursor {
        stage: SwiftRunStage::Invocation,
        function: Some(34),
        offset: Some(211),
    }
}
fn usage(owner: &SwiftReactorInstance) -> SwiftRunUsage {
    owner
        .control
        .as_ref()
        .unwrap()
        .usage(Some(owner.wasi.as_ref().unwrap().usage()))
}
fn uint(mut value: u32, out: &mut Vec<u8>) {
    loop {
        let byte = (value & 127) as u8;
        value >>= 7;
        out.push(byte | if value != 0 { 128 } else { 0 });
        if value == 0 {
            break;
        }
    }
}
fn text(value: &[u8], out: &mut Vec<u8>) {
    uint(value.len() as u32, out);
    out.extend_from_slice(value);
}
fn section(id: u8, bytes: &[u8], out: &mut Vec<u8>) {
    out.push(id);
    uint(bytes.len() as u32, out);
    out.extend_from_slice(bytes);
}
fn ty(ty: Type) -> u8 {
    match ty {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
#[derive(Clone)]
struct Function {
    params: Vec<Type>,
    locals: Vec<Type>,
    result: Option<Type>,
    blocks: usize,
}
impl Function {
    fn empty() -> Self {
        Self {
            params: vec![],
            locals: vec![],
            result: None,
            blocks: 0,
        }
    }
}
fn fixture(function: &Function) -> Vec<u8> {
    let mut out = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![37];
    for f in WasiFunction::ALL {
        types.push(0x60);
        uint(f.parameters().len() as u32, &mut types);
        types.extend(f.parameters().iter().copied().map(ty));
        uint(f.results().len() as u32, &mut types);
        types.extend(f.results().iter().copied().map(ty));
    }
    types.extend([0x60, 0, 0, 0x60, 0, 1, 0x7f, 0x60]);
    uint(function.params.len() as u32, &mut types);
    types.extend(function.params.iter().copied().map(ty));
    uint(usize::from(function.result.is_some()) as u32, &mut types);
    if let Some(result) = function.result {
        types.push(ty(result));
    }
    section(1, &types, &mut out);
    let mut imports = vec![34];
    for (i, f) in WasiFunction::ALL.into_iter().enumerate() {
        text(b"wasi_snapshot_preview1", &mut imports);
        text(f.name(), &mut imports);
        imports.push(0);
        uint(i as u32, &mut imports);
    }
    section(2, &imports, &mut out);
    let mut functions = vec![29];
    for index in 0..29 {
        uint(
            if index == 0 || index == 2 {
                36
            } else if index == 28 {
                35
            } else {
                34
            },
            &mut functions,
        );
    }
    section(3, &functions, &mut out);
    let mut table = vec![1, 0x70, 1];
    uint(46713, &mut table);
    uint(46713, &mut table);
    section(4, &table, &mut out);
    let mut memory = vec![1, 0];
    uint(584, &mut memory);
    section(5, &memory, &mut out);
    let mut exports = vec![3];
    for (name, kind, index) in [
        (b"memory".as_slice(), 2, 0),
        (b"_initialize".as_slice(), 0, 35),
        (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
    ] {
        text(name, &mut exports);
        exports.push(kind);
        uint(index, &mut exports);
    }
    section(7, &exports, &mut out);
    let mut code = vec![29];
    for index in 0..29 {
        let mut body = vec![];
        if index == 0 || index == 2 {
            uint(function.locals.len() as u32, &mut body);
            for local in &function.locals {
                body.extend([1, ty(*local)]);
            }
            for _ in 0..function.blocks {
                body.extend([0x02, 0x40]);
            }
            body.extend(std::iter::repeat_n(0x0b, function.blocks));
            if let Some(result) = function.result {
                match result {
                    Type::I32 => body.extend([0x41, 0]),
                    Type::I64 => body.extend([0x42, 0]),
                    Type::F32 => body.extend([0x43, 0, 0, 0, 0]),
                    Type::F64 => body.extend([0x44, 0, 0, 0, 0, 0, 0, 0, 0]),
                }
            }
            body.push(0x0b);
        } else if index == 28 {
            body.extend([0, 0x41, 0, 0x0b]);
        } else {
            body.extend([0, 0x0b]);
        }
        uint(body.len() as u32, &mut code);
        code.extend(body);
    }
    section(10, &code, &mut out);
    out
}
fn owner_with(function: &Function, budget: SwiftRunBudget) -> SwiftReactorInstance {
    hooks(Hooks::default());
    let proof = validate_swift_reactor(
        &fixture(function),
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let mut pair = Some(
        RuntimeControl::adopt(proof, budget, Instant::now(), Cancellation::default()).unwrap(),
    );
    SwiftReactorInstance::construct(
        &mut pair,
        WasiGrants::default(),
        WasiBudget {
            one_transfer_bytes: 64,
            log_bytes: 64,
            ..WasiBudget::default()
        },
        Instant::now(),
        cursor(),
    )
    .unwrap()
}
fn owner() -> SwiftReactorInstance {
    owner_with(&Function::empty(), SwiftRunBudget::default())
}
fn complete<'a>(
    phase: FrameOperationPhase<'a>,
    preparation: Option<Result<FrameOperationPhase<'a>, SwiftRunFailure>>,
) -> FrameCompletion {
    phase.complete(FrameOperationStorage {
        preparation,
        entry: None,
        returned: None,
        drained: None,
    })
}
fn complete_ok<'a>(
    phase: FrameOperationPhase<'a>,
    preparation: Option<Result<FrameOperationPhase<'a>, SwiftRunFailure>>,
) {
    assert!(matches!(
        complete(phase, preparation),
        FrameCompletion::Completed
    ));
}
fn install_foreign(foreign: &mut SwiftReactorInstance) {
    let ticket = super::super::super::cache::inspection::replace_header(
        foreign.cache.as_mut().unwrap(),
        None,
    );
    FOREIGN_HEADER.with(|slot| {
        assert!(slot.borrow().is_none());
        *slot.borrow_mut() = ticket;
    });
}
fn restore_foreign(foreign: &mut SwiftReactorInstance) {
    let ticket = FOREIGN_HEADER.with(|slot| slot.borrow_mut().take());
    assert!(super::super::super::cache::inspection::replace_header(
        foreign.cache.as_mut().unwrap(),
        ticket
    )
    .is_none());
    ORIGINAL_HEADER.with(|slot| assert!(slot.borrow().is_none()));
    hooks(Hooks::default());
}
fn retire(owner: SwiftReactorInstance) {
    hooks(Hooks::default());
    let mut owned = Some(owner);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail = returned.take().unwrap().unwrap();
    let mut failure = None;
    let mut usage = None;
    tail.complete((owned, returned), &mut failure, &mut usage);
    let usage = usage.unwrap();
    assert_eq!(usage.reservations.combined.current, 0);
    assert_eq!(usage.reservations.live_tickets, 0);
    assert_eq!(
        usage.live.values.current
            + usage.live.controls.current
            + usage.live.frames.current
            + usage.live.active_pins.current,
        0
    );
}
fn drain_complete(owner: &mut SwiftReactorInstance) {
    let mut returned = Some(owner.resume_frame_cleanup());
    let mut phase = returned.take().unwrap().unwrap();
    let report = phase.drain();
    assert_eq!(report.retained_frames, 0);
    assert!(!report.retained_entry);
    assert!(!report.live_unreconciled);
    complete_ok(phase, returned);
}
fn pin_ids(phase: &FrameOperationPhase<'_>) -> Vec<(u32, u64, usize, u64)> {
    phase
        .phase
        .parts
        .frames
        .iter()
        .map(|frame| {
            (
                frame.function,
                frame.pin.owner(),
                frame.pin.slot(),
                frame.pin.nonce(),
            )
        })
        .collect()
}

#[test]
fn af01_real_nested_recursive_entry_and_parameter_ownership() {
    let function = Function {
        params: vec![Type::I32, Type::F64],
        locals: vec![Type::I64, Type::F32],
        ..Function::empty()
    };
    let mut owner = owner_with(&function, SwiftRunBudget::default());
    let before = usage(&owner);
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    for function in [34, 36, 34] {
        phase.phase.push_value(Value::I32(7)).unwrap();
        phase.phase.push_value(Value::F64(9)).unwrap();
        phase.enter(function).unwrap();
    }
    assert_eq!(phase.phase.parts.values.len(), 12);
    assert_eq!(phase.phase.parts.controls.len(), 3);
    assert_eq!(phase.phase.parts.frames.len(), 3);
    assert_eq!(phase.phase.parts.cache.usage().active_pins, 3);
    assert_eq!(
        phase
            .phase
            .operation
            .control
            .usage(None)
            .live
            .frames
            .current,
        3
    );
    assert_eq!(
        phase.phase.operation.control.usage(None).execution_work,
        before.execution_work + 3 * (2 + 1 + 3)
    );
    assert_eq!(phase.phase.parts.values[2], Value::I64(0));
    assert_eq!(phase.phase.parts.values[3], Value::F32(0));
    let observed = phase
        .phase
        .operation
        .control
        .usage(Some(phase.phase.operation.wasi.usage()));
    assert_eq!(
        phase.phase.operation.control.budget(),
        SwiftRunBudget::default()
    );
    println!("AF01_DEFAULT state_current={} state_peak={} construction_current={} construction_peak={} combined_current={} combined_peak={} state_limit={} combined_limit={}",observed.reservations.state.current,observed.reservations.state.peak,observed.reservations.construction.current,observed.reservations.construction.peak,observed.reservations.combined.current,observed.reservations.combined.peak,SwiftRunBudget::default().state_bytes,SwiftRunBudget::default().combined_bytes);
    let report = phase.drain();
    assert_eq!(report.retained_frames, 0);
    complete_ok(phase, returned);
    retire(owner);
}
#[test]
fn af02_nested_zero_single_and_outer_results_exact_order() {
    let function = Function {
        locals: vec![Type::I32, Type::I64],
        result: Some(Type::I32),
        ..Function::empty()
    };
    let mut owner = owner_with(&function, SwiftRunBudget::default());
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    phase.enter(35).unwrap();
    phase.enter(34).unwrap();
    phase.phase.push_value(Value::I32(41)).unwrap();
    let before = phase.phase.operation.control.usage(None).execution_work;
    assert!(matches!(
        phase.finish().unwrap(),
        FrameReturn::CallerContinues
    ));
    assert_eq!(phase.phase.parts.values.as_slice(), [Value::I32(41)]);
    assert_eq!(
        phase.phase.operation.control.usage(None).execution_work - before,
        1 + 2 + 1 + 1 + 1
    );
    assert!(matches!(
        phase.finish().unwrap(),
        FrameReturn::Outermost(None)
    ));
    complete_ok(phase, returned);
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    phase.enter(34).unwrap();
    phase.phase.push_value(Value::I32(19)).unwrap();
    assert!(matches!(
        phase.finish().unwrap(),
        FrameReturn::Outermost(Some(Value::I32(19)))
    ));
    assert_eq!(phase.phase.parts.cache.usage().active_pins, 0);
    complete_ok(phase, returned);
    retire(owner);
}
#[test]
fn af03_real_call_depth_and_pin_limits() {
    for (frames, pins, kind) in [
        (2, 8, SwiftRunFailureKind::FrameLimit),
        (8, 2, SwiftRunFailureKind::PinLimit),
    ] {
        let mut owner = owner_with(
            &Function::empty(),
            SwiftRunBudget {
                frames,
                active_pins: pins,
                ..SwiftRunBudget::default()
            },
        );
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        phase.enter(34).unwrap();
        let ids = pin_ids(&phase);
        assert_eq!(phase.enter(34).unwrap_err().kind, kind);
        assert_eq!(pin_ids(&phase), ids);
        assert_eq!(phase.phase.parts.cache.usage().active_pins, 2);
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
}
#[test]
fn af04_actual_255_256_locals_and_real_257_validation_rejection() {
    for total in [255, 256] {
        let function = Function {
            params: vec![Type::I32; 128],
            locals: (0..total - 128)
                .map(|index| [Type::I32, Type::I64, Type::F32, Type::F64][index % 4])
                .collect(),
            ..Function::empty()
        };
        let mut owner = owner_with(&function, SwiftRunBudget::default());
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        for _ in 0..128 {
            phase.phase.push_value(Value::I32(3)).unwrap();
        }
        phase.enter(34).unwrap();
        assert_eq!(phase.phase.parts.values.len(), total);
        for (index, value) in phase.phase.parts.values[128..].iter().enumerate() {
            assert_eq!(*value, Value::zero(function.locals[index]));
        }
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
    let invalid = Function {
        params: vec![Type::I32; 128],
        locals: vec![Type::I32; 129],
        ..Function::empty()
    };
    assert!(validate_swift_reactor(
        &fixture(&invalid),
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
    println!("AF04 invalid257 rejected by real validation before owner construction; actual255/256 frames executed");
}
fn decoded_controls(phase: &mut FrameOperationPhase<'_>, count: usize) {
    assert!(count <= 511);
    for index in 0..count {
        let (kind, end, result) = {
            let frame = phase.phase.parts.frames.last().unwrap();
            let view = phase
                .phase
                .parts
                .cache
                .view(
                    &frame.pin,
                    phase.phase.operation.control,
                    Some(&*phase.phase.operation.wasi),
                )
                .unwrap();
            match view.instructions[index].operation {
                Operation::Block {
                    kind, end, result, ..
                } => (kind, end, result.is_some()),
                _ => panic!("distinct actual decoded block required"),
            }
        };
        assert_eq!(kind, ControlKind::Block);
        phase
            .phase
            .operation
            .control
            .add_live_with_wasi(
                Live::Controls,
                1,
                cursor(),
                Some(phase.phase.operation.wasi.usage()),
            )
            .unwrap();
        phase.phase.parts.controls.push(Control::decoded_fixture(
            kind,
            end,
            phase.phase.parts.values.len(),
            result,
        ));
    }
}
#[test]
fn af05_real_decoded_control_inclusive_and_aggregate_boundaries() {
    let function = Function {
        blocks: 511,
        ..Function::empty()
    };
    for accepted in [false, true] {
        let mut owner = owner_with(&function, SwiftRunBudget::default());
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        for index in 0..8 {
            phase.enter(34).unwrap();
            decoded_controls(&mut phase, if accepted && index == 7 { 510 } else { 511 });
        }
        assert_eq!(
            phase.phase.parts.controls.len(),
            if accepted { 4095 } else { 4096 }
        );
        if accepted {
            phase.enter(36).unwrap();
            assert_eq!(phase.phase.parts.controls.len(), 4096);
        } else {
            assert_eq!(
                phase.enter(36).unwrap_err().kind,
                SwiftRunFailureKind::ControlLimit
            );
        }
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
    let mut owner = owner_with(&function, SwiftRunBudget::default());
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    phase.enter(34).unwrap();
    decoded_controls(&mut phase, 511);
    // Derived defensive corruption: duplicate one real block after the legal
    // inclusive512 depth. A genuine513-depth source rejects validation below.
    decoded_controls(&mut phase, 1);
    assert_eq!(
        phase.enter(36).unwrap_err().code,
        "swift_frame_control_depth"
    );
    phase.drain();
    complete_ok(phase, returned);
    retire(owner);
    let too_deep = Function {
        blocks: 512,
        ..Function::empty()
    };
    assert!(validate_swift_reactor(
        &fixture(&too_deep),
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
}
#[test]
fn af06_every_entry_work_prefix_preserves_caller_and_work() {
    let function = Function {
        locals: vec![Type::I32; 3],
        ..Function::empty()
    };
    for ceiling in 0..=5 {
        let mut owner = owner_with(&function, SwiftRunBudget::default());
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        phase.enter(35).unwrap();
        phase.phase.push_value(Value::I32(73)).unwrap();
        let before = phase.phase.operation.control.usage(None).execution_work;
        let old = phase
            .phase
            .operation
            .control
            .test_replace_execution_work_limit(before + ceiling);
        let result = phase.enter(34);
        phase
            .phase
            .operation
            .control
            .test_replace_execution_work_limit(old);
        if ceiling < 5 {
            assert_eq!(result.unwrap_err().kind, SwiftRunFailureKind::WorkExhausted);
            assert_eq!(phase.phase.parts.values.as_slice(), [Value::I32(73)]);
            assert_eq!(phase.phase.parts.frames.len(), 1);
            assert_eq!(phase.phase.parts.controls.len(), 1);
            assert_eq!(
                phase.phase.operation.control.usage(None).execution_work - before,
                u64::from(ceiling >= 1)
            );
        } else {
            result.unwrap();
        }
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
}
#[test]
fn af07_exact_predebit_faults_and_narrow_capacity_admission() {
    let function = Function {
        locals: vec![Type::I32; 3],
        ..Function::empty()
    };
    for (resource, ordinal) in [(0, 0), (0, 1), (0, 2), (1, 0), (2, 0)] {
        let mut owner = owner_with(&function, SwiftRunBudget::default());
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        hooks(Hooks {
            predebit_resource: Some(resource),
            predebit_ordinal: ordinal,
            ..Hooks::default()
        });
        assert!(phase.enter(34).is_err());
        assert!(phase.phase.parts.values.is_empty());
        assert!(phase.phase.parts.controls.is_empty());
        assert!(phase.phase.parts.frames.is_empty());
        assert_eq!(phase.phase.parts.cache.usage().active_pins, 0);
        assert!(phase.cleanup.entry.is_none());
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
    for budget in [
        SwiftRunBudget {
            values: 2,
            ..SwiftRunBudget::default()
        },
        SwiftRunBudget {
            controls: 0,
            ..SwiftRunBudget::default()
        },
        SwiftRunBudget {
            frames: 0,
            ..SwiftRunBudget::default()
        },
    ] {
        let mut owner = owner_with(&function, budget);
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        assert!(phase.enter(34).is_err());
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
}
#[test]
fn af08_cancellation_at_every_actual_local_check_rolls_back_only_new_effects() {
    let function = Function {
        locals: vec![Type::I32; 4],
        ..Function::empty()
    };
    for index in 0..4 {
        let mut owner = owner_with(&function, SwiftRunBudget::default());
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        phase.enter(35).unwrap();
        phase.phase.push_value(Value::I32(88)).unwrap();
        hooks(Hooks {
            cancel_local: Some(index),
            ..Hooks::default()
        });
        let failure = phase.enter(34).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
        assert_eq!(phase.phase.parts.values.as_slice(), [Value::I32(88)]);
        assert_eq!(phase.phase.parts.controls.len(), 1);
        assert_eq!(phase.phase.parts.frames.len(), 1);
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
}
#[test]
fn af09_real_pin_and_nested_completion_failure_coexist() {
    for pins in [0, 4] {
        let mut owner = owner_with(
            &Function::empty(),
            SwiftRunBudget {
                active_pins: pins,
                ..SwiftRunBudget::default()
            },
        );
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        hooks(Hooks {
            reject_cache_completion: true,
            ..Hooks::default()
        });
        let failure = phase.enter(34).unwrap_err();
        assert!(phase.cleanup.nested_restore.is_some());
        assert!(phase.phase.parts.frames.is_empty());
        assert_eq!(
            failure.kind,
            if pins == 0 {
                SwiftRunFailureKind::PinLimit
            } else {
                SwiftRunFailureKind::Invariant
            }
        );
        assert_eq!(phase.phase.parts.cache.usage().active_pins, 0);
        hooks(Hooks::default());
        let report = phase.drain();
        assert!(report.nested_restore.is_none());
        assert_eq!(report.first_failure.unwrap().code, failure.code);
        complete_ok(phase, returned);
        retire(owner);
    }
}
#[test]
fn af10_entry_guard_rejected_release_retains_actual_pin_and_cleanup_barrier() {
    let mut foreign = owner();
    let mut owner = owner_with(
        &Function {
            locals: vec![Type::I32; 3],
            ..Function::empty()
        },
        SwiftRunBudget::default(),
    );
    install_foreign(&mut foreign);
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    hooks(Hooks {
        cancel_local: Some(1),
        release_mask: 1,
        ..Hooks::default()
    });
    phase.enter(34).unwrap_err();
    assert!(phase.cleanup.entry.as_ref().unwrap().pin.is_some());
    assert_eq!(phase.phase.parts.cache.usage().active_pins, 1);
    assert!(phase.cleanup.entry_attempted);
    let report = phase.drain();
    assert!(report.retained_entry);
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 1);
    assert!(matches!(
        complete(phase, returned),
        FrameCompletion::Retained(_)
    ));
    let mut owned = Some(owner);
    assert!(SwiftReactorInstance::cleanup_owned(&mut owned).is_err());
    assert!(owned.is_some());
    let mut owner = owned.take().unwrap();
    restore_foreign(&mut foreign);
    drain_complete(&mut owner);
    retire(owner);
    retire(foreign);
}
#[test]
fn af11_mixed_releases_keep_same_actual_frames_pins_in_order() {
    let mut foreign = owner();
    let mut owner = owner();
    install_foreign(&mut foreign);
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    for function in [34, 36, 34, 36] {
        phase.enter(function).unwrap();
    }
    let ids = pin_ids(&phase);
    hooks(Hooks {
        release_mask: 0b0101,
        ..Hooks::default()
    });
    let report = phase.drain();
    assert_eq!(report.retained_frames, 2);
    assert_eq!(pin_ids(&phase), vec![ids[1], ids[3]]);
    assert_eq!(phase.cleanup.unvisited, 0);
    assert_eq!(report.live.frames.current, 2);
    assert_eq!(report.live.active_pins.current, 2);
    assert_eq!(
        HOOKS.with(|slot| slot.get().release_order[..4].to_vec()),
        vec![36, 34, 36, 34]
    );
    assert!(matches!(
        complete(phase, returned),
        FrameCompletion::Retained(_)
    ));
    restore_foreign(&mut foreign);
    drain_complete(&mut owner);
    retire(owner);
    retire(foreign);
}
#[test]
fn af12_all_release_rejections_retain_real_headers_frames_and_charges() {
    let mut foreign = owner();
    let mut owner = owner();
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    for _ in 0..3 {
        phase.enter(34).unwrap();
    }
    let ids = pin_ids(&phase);
    let foreign_header = super::super::super::cache::inspection::replace_header(
        foreign.cache.as_mut().unwrap(),
        None,
    );
    let original = super::super::super::cache::inspection::replace_header(
        phase.phase.parts.cache,
        foreign_header,
    );
    let before = phase.phase.operation.control.usage(None).reservations;
    let report = phase.drain();
    assert_eq!(report.retained_frames, 3);
    assert_eq!(pin_ids(&phase), ids);
    assert_eq!(report.live.frames.current, 3);
    assert_eq!(report.live.active_pins.current, 3);
    assert_eq!(
        before.state.current,
        report.usage.reservations.state.current
    );
    assert!(report.cache.pinned_bytes > 0);
    let foreign_header =
        super::super::super::cache::inspection::replace_header(phase.phase.parts.cache, original);
    super::super::super::cache::inspection::replace_header(
        foreign.cache.as_mut().unwrap(),
        foreign_header,
    );
    assert!(matches!(
        complete(phase, returned),
        FrameCompletion::Retained(_)
    ));
    drain_complete(&mut owner);
    retire(owner);
    retire(foreign);
}
#[test]
fn af13_guard_and_multiple_frames_keep_independent_actual_pins() {
    let mut foreign = owner();
    let mut owner = owner();
    install_foreign(&mut foreign);
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    for function in [34, 36, 34] {
        phase.enter(function).unwrap();
    }
    let ids = pin_ids(&phase);
    hooks(Hooks {
        reject_cache_completion: true,
        release_mask: 0b1011,
        ..Hooks::default()
    });
    phase.enter(36).unwrap_err();
    let guard_nonce = phase
        .cleanup
        .entry
        .as_ref()
        .unwrap()
        .pin
        .as_ref()
        .unwrap()
        .nonce();
    let report = phase.drain();
    assert!(report.retained_entry);
    assert_eq!(report.retained_frames, 2);
    assert_eq!(pin_ids(&phase), vec![ids[0], ids[2]]);
    assert_eq!(
        phase
            .cleanup
            .entry
            .as_ref()
            .unwrap()
            .pin
            .as_ref()
            .unwrap()
            .nonce(),
        guard_nonce
    );
    assert_eq!(report.live.active_pins.current, 3);
    assert_eq!(report.live.frames.current, 2);
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 4);
    assert!(matches!(
        complete(phase, returned),
        FrameCompletion::Retained(_)
    ));
    restore_foreign(&mut foreign);
    drain_complete(&mut owner);
    retire(owner);
    retire(foreign);
}
#[test]
fn af14_finish_release_failure_is_processed_suffix_and_never_reinterpreted() {
    let mut foreign = owner();
    let mut owner = owner();
    install_foreign(&mut foreign);
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    for function in [34, 36, 34] {
        phase.enter(function).unwrap();
    }
    hooks(Hooks {
        release_mask: 1,
        ..Hooks::default()
    });
    let failure = phase.finish().unwrap_err();
    assert_eq!(phase.cleanup.unvisited, 2);
    assert_eq!(phase.phase.parts.controls.len(), 2);
    assert_eq!(phase.drain().retained_frames, 1);
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 3);
    assert_eq!(phase.finish().unwrap_err().code, failure.code);
    assert_eq!(phase.enter(34).unwrap_err().code, failure.code);
    assert!(matches!(
        complete(phase, returned),
        FrameCompletion::Retained(_)
    ));
    restore_foreign(&mut foreign);
    drain_complete(&mut owner);
    retire(owner);
    retire(foreign);
}
#[test]
fn af15_failed_result_push_happens_after_callee_release() {
    for fault in [1, 2, 3, 4] {
        let function = Function {
            result: Some(Type::I32),
            ..Function::empty()
        };
        let mut owner = owner_with(&function, SwiftRunBudget::default());
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        phase.enter(35).unwrap();
        if fault == 3 {
            for _ in 0..128 {
                phase.phase.push_value(Value::I32(2)).unwrap();
            }
        }
        phase.enter(34).unwrap();
        phase.phase.push_value(Value::I32(91)).unwrap();
        hooks(Hooks {
            push_fault: if fault == 3 { 0 } else { fault },
            ..Hooks::default()
        });
        let failure = phase.finish().unwrap_err();
        assert_eq!(
            failure.kind,
            if fault == 1 {
                SwiftRunFailureKind::WorkExhausted
            } else {
                SwiftRunFailureKind::ValueLimit
            }
        );
        assert_eq!(phase.phase.parts.frames.len(), 1);
        assert_eq!(phase.phase.parts.cache.usage().active_pins, 1);
        assert_eq!(
            phase.phase.parts.values.len(),
            if fault == 3 { 128 } else { 0 }
        );
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
}
#[test]
fn af16_cleanup_undercount_zero_is_sticky_and_blocks_consuming_cleanup() {
    for resource in [Live::Values, Live::Controls, Live::Frames] {
        let mut owner = owner_with(
            &Function {
                locals: vec![Type::I32],
                ..Function::empty()
            },
            SwiftRunBudget::default(),
        );
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        phase
            .phase
            .operation
            .control
            .remove_live(resource, 1)
            .unwrap();
        let report = phase.drain();
        assert!(report.live_unreconciled);
        assert_eq!(report.retained_frames, 0);
        assert_eq!(
            report.live.values.current + report.live.controls.current + report.live.frames.current,
            0
        );
        assert!(matches!(
            complete(phase, returned),
            FrameCompletion::Retained(_)
        ));
        let mut returned = Some(owner.resume_frame_cleanup());
        let mut phase = returned.take().unwrap().unwrap();
        assert!(phase.drain().live_unreconciled);
        assert!(matches!(
            complete(phase, returned),
            FrameCompletion::Retained(_)
        ));
        let mut owned = Some(owner);
        assert!(SwiftReactorInstance::cleanup_owned(&mut owned).is_err());
        assert!(owned.is_some());
        // Deliberately unrefunded terminal owner remains evidence; there is no
        // ledger repair or successful consuming-cleanup claim for corruption.
        drop(owned);
    }
}
#[test]
fn af17_real_prior_wasi_effect_and_sticky_first_failure() {
    for kind in [
        SwiftRunFailureKind::GuestTrap,
        SwiftRunFailureKind::Cancelled,
        SwiftRunFailureKind::WorkExhausted,
    ] {
        let mut owner = owner();
        owner
            .wasi
            .as_mut()
            .unwrap()
            .dispatch(
                owner.control.as_mut().unwrap(),
                WasiFunction::ArgsSizesGet,
                &[Value::I32(0), Value::I32(4)],
                &mut [0; 8],
                cursor(),
            )
            .unwrap();
        let observed = owner.wasi.as_ref().unwrap().usage();
        assert_eq!(observed.calls, 1);
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        let first = phase.phase.operation.control.fail(
            cursor(),
            Fault::new(kind, "af17_original"),
            Some(phase.phase.operation.wasi.usage()),
        );
        phase
            .phase
            .operation
            .control
            .remove_live(Live::Controls, 1)
            .unwrap();
        let report = phase.drain();
        assert!(report.live_unreconciled);
        let final_failure = report.first_failure.unwrap();
        assert_eq!(first.kind, final_failure.kind);
        assert_eq!(first.code, final_failure.code);
        assert_eq!(first.function, final_failure.function);
        assert_eq!(first.offset, final_failure.offset);
        assert_eq!(first.at_failure.wasi, Some(observed));
        assert_eq!(final_failure.after_cleanup.unwrap().wasi, Some(observed));
        assert!(matches!(
            complete(phase, returned),
            FrameCompletion::Retained(_)
        ));
        drop(owner);
    }
}
#[test]
fn af18_dropped_phase_cleanup_resume_has_no_admission_work_or_value_access() {
    let mut owner = owner();
    let before = usage(&owner).reservations.construction.current;
    {
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        drop((phase, returned));
    }
    let enlarged = usage(&owner).reservations.construction.current;
    assert!(enlarged > before);
    assert!(owner.prepare_frames(cursor()).is_err());
    assert!(owner.prepare_value_operation(cursor()).is_err());
    let used = usage(&owner).execution_work;
    let mut returned = Some(owner.resume_frame_cleanup());
    let mut phase = returned.take().unwrap().unwrap();
    assert!(phase.enter(34).is_err());
    assert!(phase.finish().is_err());
    phase.drain();
    assert_eq!(
        phase.phase.operation.control.usage(None).execution_work,
        used
    );
    complete_ok(phase, returned);
    assert_eq!(usage(&owner).reservations.construction.current, before);
    retire(owner);
}
#[test]
fn af19_exact_fixed_storage_outer_restore_rejection_and_retry() {
    let mut owner = owner();
    let before = usage(&owner).reservations.construction.current;
    let mut preparation = Some(owner.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    let mut entry = Some(phase.enter(34));
    entry.take().unwrap().unwrap();
    let mut returned = Some(phase.finish());
    assert!(matches!(
        returned.take().unwrap().unwrap(),
        FrameReturn::Outermost(None)
    ));
    let mut drained = Some(phase.drain());
    drained.take().unwrap();
    hooks(Hooks {
        reject_outer_restore: true,
        ..Hooks::default()
    });
    let result = phase.complete(FrameOperationStorage {
        preparation,
        entry,
        returned,
        drained,
    });
    assert!(matches!(result, FrameCompletion::RestoreRejected(_)));
    assert_eq!(
        owner.state.as_ref().unwrap().frame_cleanup.disposition,
        FrameDisposition::RestorePending
    );
    assert!(usage(&owner).reservations.construction.current > before);
    hooks(Hooks::default());
    drain_complete(&mut owner);
    assert_eq!(usage(&owner).reservations.construction.current, before);
    retire(owner);
}
#[test]
fn af20_original_provenance_layout_and_consuming_barriers_preserve_owners() {
    // Every rejection starts with a fresh first_failure. A sticky earlier
    // failure cannot conceal a missing later provenance/layout check.
    for path in 0..4 {
        for fault in 0..3 {
            let mut first = owner();
            let mut second = owner();
            if path == 3 {
                let mut slot = Some(first.prepare_frames(cursor()));
                let mut phase = slot.take().unwrap().unwrap();
                phase.enter(34).unwrap();
                drop((phase, slot));
            }
            let pointer = first.state.as_ref().unwrap().memory.as_ptr();
            let before = usage(&first).reservations;
            match fault {
                0 => std::mem::swap(&mut first.wasi, &mut second.wasi),
                1 => std::mem::swap(&mut first.cache, &mut second.cache),
                _ => first.state.as_mut().unwrap().buffers.swap(0, 3),
            }
            let failure = match path {
                0 => first.prepare_frames(cursor()).err().unwrap(),
                1 => first.prepare_value_operation(cursor()).err().unwrap(),
                2 => {
                    let mut owned = Some(first);
                    let failure = SwiftReactorInstance::cleanup_owned(&mut owned)
                        .err()
                        .unwrap();
                    assert!(owned.is_some());
                    first = owned.take().unwrap();
                    failure
                }
                _ => first.resume_frame_cleanup().err().unwrap(),
            };
            assert_eq!(
                failure.code,
                if fault < 2 {
                    "swift_run_reservation_owner"
                } else {
                    "swift_execution_layout_overflow"
                }
            );
            assert_eq!(first.state.as_ref().unwrap().memory.as_ptr(), pointer);
            assert_eq!(
                usage(&first).reservations.construction.current,
                before.construction.current
            );
            match fault {
                0 => std::mem::swap(&mut first.wasi, &mut second.wasi),
                1 => std::mem::swap(&mut first.cache, &mut second.cache),
                _ => first.state.as_mut().unwrap().buffers.swap(0, 3),
            }
            if path == 3 {
                drain_complete(&mut first);
            }
            retire(first);
            retire(second);
        }
    }
    for path in 0..4 {
        for fault in 0..3 {
            let mut first = owner();
            let mut second = owner();
            if path == 3 {
                let mut slot = Some(first.prepare_frames(cursor()));
                let mut phase = slot.take().unwrap().unwrap();
                phase.enter(34).unwrap();
                drop((phase, slot));
            }
            let before = usage(&first).reservations;
            let pointer = first.state.as_ref().unwrap().values.as_ptr();
            let replacement = match fault {
                0 => None,
                1 => second
                    .control
                    .as_mut()
                    .unwrap()
                    .test_replace_construction(None),
                _ => first.state.as_mut().unwrap().buffers[0].take(),
            };
            let mut original = first
                .control
                .as_mut()
                .unwrap()
                .test_replace_construction(replacement);
            if fault == 2 {
                first.state.as_mut().unwrap().buffers[0] = original.take();
            }
            let failure = match path {
                0 => first.prepare_frames(cursor()).err().unwrap(),
                1 => first.prepare_value_operation(cursor()).err().unwrap(),
                2 => {
                    let mut owned = Some(first);
                    let failure = SwiftReactorInstance::cleanup_owned(&mut owned)
                        .err()
                        .unwrap();
                    assert!(owned.is_some());
                    first = owned.take().unwrap();
                    failure
                }
                _ => first.resume_frame_cleanup().err().unwrap(),
            };
            assert_eq!(
                failure.code,
                [
                    "swift_run_missing_construction",
                    "swift_run_construction_owner",
                    "swift_run_construction_layout"
                ][fault]
            );
            assert_eq!(
                failure.at_failure.wasi,
                Some(first.wasi.as_ref().unwrap().usage())
            );
            assert_eq!(
                usage(&first).reservations.construction.current,
                before.construction.current
            );
            assert_eq!(first.state.as_ref().unwrap().values.as_ptr(), pointer);
            if path == 3 {
                assert_eq!(
                    first.state.as_ref().unwrap().frame_cleanup.disposition,
                    FrameDisposition::Active
                );
                assert_eq!(first.state.as_ref().unwrap().frames.len(), 1);
                assert!(matches!(first.lifecycle, Lifecycle::Uninitialized));
            }
            if fault == 2 {
                original = first.state.as_mut().unwrap().buffers[0].take();
            }
            let replaced = first
                .control
                .as_mut()
                .unwrap()
                .test_replace_construction(original);
            match fault {
                0 => assert!(replaced.is_none()),
                1 => assert!(second
                    .control
                    .as_mut()
                    .unwrap()
                    .test_replace_construction(replaced)
                    .is_none()),
                _ => {
                    assert!(first.state.as_ref().unwrap().buffers[0].is_none());
                    first.state.as_mut().unwrap().buffers[0] = replaced;
                }
            }
            if path == 3 {
                drain_complete(&mut first);
            }
            retire(first);
            retire(second);
        }
    }
    for resource in [Live::Values, Live::Controls, Live::Frames, Live::ActivePins] {
        let mut first = owner();
        first
            .control
            .as_mut()
            .unwrap()
            .add_live(resource, 1, cursor())
            .unwrap();
        let mut owned = Some(first);
        let failure = SwiftReactorInstance::cleanup_owned(&mut owned)
            .err()
            .unwrap();
        assert_eq!(failure.code, "swift_execution_cleanup_nonempty");
        assert!(owned.is_some());
        let mut first = owned.take().unwrap();
        first
            .control
            .as_mut()
            .unwrap()
            .remove_live(resource, 1)
            .unwrap();
        retire(first);
    }
}
#[test]
fn af21_warm_paths_refuse_first_allocation_and_cold_decode_is_separate() {
    let function = Function {
        locals: vec![Type::I32; 3],
        result: Some(Type::I32),
        ..Function::empty()
    };
    let mut owner = owner_with(&function, SwiftRunBudget::default());
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    let (_, cold) = measure_extended(None, || phase.enter(34).unwrap());
    assert!(cold.attempts > 0);
    phase.phase.push_value(Value::I32(1)).unwrap();
    phase.finish().unwrap();
    complete_ok(phase, returned);
    let mut returned = Some(owner.prepare_frames(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    let (result, warm) = measure_extended(Some(0), || {
        phase.enter(34)?;
        phase.phase.push_value(Value::I32(3))?;
        phase.enter(34)?;
        phase.phase.push_value(Value::I32(4))?;
        phase.finish()?;
        phase.drain();
        Ok::<_, SwiftRunFailure>(())
    });
    result.unwrap();
    assert_eq!(warm.attempts, 0);
    let (completion, stats) = measure_extended(Some(0), || complete(phase, returned));
    assert!(matches!(completion, FrameCompletion::Completed));
    assert_eq!(stats.attempts, 0);
    println!(
        "AF21 cold decode requests={} warm entry/finish/drain/completion requests=0",
        cold.attempts
    );
    retire(owner);
    for ordinal in 0..cold.attempts {
        let mut owner = owner_with(&function, SwiftRunBudget::default());
        let mut returned = Some(owner.prepare_frames(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        let (result, stats) = measure_extended(Some(ordinal), || phase.enter(34));
        assert_eq!(stats.injected_failures, 1);
        assert_eq!(stats.attempts, ordinal + 1);
        assert_eq!(result.unwrap_err().kind, SwiftRunFailureKind::Allocation);
        phase.drain();
        complete_ok(phase, returned);
        retire(owner);
    }
}
#[test]
fn af22_frozen_accounting_and_value_phase_reservations_stay_distinct() {
    let base = owner();
    let ceiling = usage(&base).reservations.combined.current + FRAME_OPERATION_BYTES.unwrap() - 1;
    retire(base);
    let proof = validate_swift_reactor(
        &fixture(&Function::empty()),
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let mut pair = Some(
        RuntimeControl::adopt(
            proof,
            SwiftRunBudget {
                combined_bytes: ceiling,
                ..SwiftRunBudget::default()
            },
            Instant::now(),
            Cancellation::default(),
        )
        .unwrap(),
    );
    let mut returned = Some(SwiftReactorInstance::construct(
        &mut pair,
        WasiGrants::default(),
        WasiBudget {
            one_transfer_bytes: 64,
            log_bytes: 64,
            ..WasiBudget::default()
        },
        Instant::now(),
        cursor(),
    ));
    let tail = match returned.take().unwrap() {
        Err(ConstructionFailure::Cleanup(tail)) => tail,
        _ => {
            panic!("narrow combined budget rejects actual constructor peak before frame admission")
        }
    };
    let mut failure = None;
    let mut final_usage = None;
    tail.complete((pair, returned), &mut failure, &mut final_usage);
    let failure = failure.unwrap();
    assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
    assert_eq!(final_usage.unwrap().reservations.combined.current, 0);
    println!(
        "AF22_NARROW constructor_rejection combined_limit={} attempted={} frame_admitted=false",
        ceiling, failure.attempted
    );
    assert_eq!(value_operations::VALUE_OPERATION_BYTES, Some(119576));
    const {
        assert!(PERMANENT_BYTES > FROZEN_PERMANENT_BYTES);
    }
    const {
        assert!(ACTIVE_BYTES > FROZEN_ACTIVE_BYTES);
    }
    assert_eq!(FRAME_OPERATION_BYTES, Some(ACTIVE_BYTES + 119576));
    assert_eq!(FROZEN_ACTIVE_BYTES, 240776);
    println!("AF_LAYOUT permanent={} frozen_permanent={} active={} frozen_active={} frame={} value={} state={}",PERMANENT_BYTES,FROZEN_PERMANENT_BYTES,ACTIVE_BYTES,FROZEN_ACTIVE_BYTES,FRAME_OPERATION_BYTES.unwrap(),value_operations::VALUE_OPERATION_BYTES.unwrap(),size_of::<SwiftExecutionState>());
}
