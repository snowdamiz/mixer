//! Independently authored host-only lifecycle verification; see the remaining-matrix receipt.
use super::*;
use crate::experimental_swift_reactor::execution::frame_operations::tests as frame_tests;
use crate::experimental_swift_reactor::{
    allocation_tests::measure_extended, validate_swift_reactor, SwiftValidationBudget,
};
use crate::experimental_wasi::WasiFunction;
use crate::Cancellation;
use std::cell::Cell;
use std::time::Duration;

thread_local! { static RUNTIME_HOOK: Cell<u8> = const { Cell::new(0) }; }
// These are actual unit-only lifecycle hook bodies, not fixture-only callbacks.
pub(super) fn runtime_after_run(
    phase: &mut FrameOperationPhase<'_>,
    storage: &mut FrameOperationStorage<'_>,
    execution: &mut Result<(), SwiftRunFailure>,
) {
    match RUNTIME_HOOK.with(Cell::get) {
        1 => storage.returned = None,
        2 => storage.returned = Some(Ok(FrameReturn::CallerContinues)),
        3 => storage.returned = Some(Ok(FrameReturn::Outermost(Some(Value::I32(7))))),
        4 => storage.returned = Some(Err(phase.invariant("swift_lifecycle_stored_failure"))),
        5 => *execution = Err(phase.invariant("swift_lifecycle_outer_failure")),
        6 => storage.returned = Some(Ok(FrameReturn::Outermost(None))),
        11 => storage.returned = Some(Ok(FrameReturn::Outermost(Some(Value::I64(7))))),
        12 => phase.terminal(),
        _ => (),
    }
}
pub(super) fn runtime_before_final_check(phase: &mut FrameOperationPhase<'_>) {
    match RUNTIME_HOOK.with(Cell::get) {
        7 => phase.phase.operation.control.cancellation().cancel(),
        8 => std::thread::sleep(
            phase
                .phase
                .operation
                .control
                .deadline()
                .saturating_duration_since(Instant::now())
                + Duration::from_millis(2),
        ),
        _ => (),
    }
}
pub(super) fn runtime_before_completion(
    phase: &mut FrameOperationPhase<'_>,
    pending: &mut SwiftGrowthStorage,
) {
    match RUNTIME_HOOK.with(Cell::get) {
        9 => {
            let ticket = phase
                .phase
                .operation
                .control
                .admit_with_wasi(
                    SwiftReservationCategory::State,
                    PAGE,
                    phase.phase.operation.cursor,
                    Some(phase.phase.operation.wasi.usage()),
                )
                .unwrap();
            pending.transfer.ticket = Some(ticket);
            pending.transfer.next_pages = 1;
            pending
                .transfer
                .replacement
                .try_reserve_exact(PAGE)
                .unwrap();
        }
        10 => phase.phase.push_value(Value::I32(17)).unwrap(),
        13 => phase.enter(36).unwrap(),
        _ => (),
    }
}
struct Hook;
impl Hook {
    fn set(mode: u8) -> Self {
        RUNTIME_HOOK.with(|s| {
            assert_eq!(s.get(), 0);
            s.set(mode);
        });
        Self
    }
}
impl Drop for Hook {
    fn drop(&mut self) {
        RUNTIME_HOOK.with(|s| s.set(0));
        frame_tests::hooks(frame_tests::Hooks::default());
    }
}

#[derive(Clone)]
struct Function {
    params: Vec<Type>,
    result: Option<Type>,
    locals: Vec<Type>,
    body: Vec<u8>,
}
impl Function {
    fn void(body: &[u8]) -> Self {
        Self {
            params: vec![],
            result: None,
            locals: vec![],
            body: body.to_vec(),
        }
    }
    fn scalar(body: &[u8], ty: Type) -> Self {
        Self {
            result: Some(ty),
            ..Self::void(body)
        }
    }
}
fn uint(mut n: u32, out: &mut Vec<u8>) {
    loop {
        let b = (n & 127) as u8;
        n >>= 7;
        out.push(b | if n == 0 { 0 } else { 128 });
        if n == 0 {
            break;
        }
    }
}
fn text(bytes: &[u8], out: &mut Vec<u8>) {
    uint(bytes.len() as u32, out);
    out.extend_from_slice(bytes);
}
fn section(id: u8, bytes: &[u8], out: &mut Vec<u8>) {
    out.push(id);
    uint(bytes.len() as u32, out);
    out.extend_from_slice(bytes);
}
fn ty(t: Type) -> u8 {
    match t {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
fn module(spec: &[(usize, Function)], table: &[u32]) -> (Vec<u8>, Vec<usize>) {
    let mut functions = vec![Function::void(&[0x0b]); 29];
    functions[28] = Function::scalar(&[0x41, 0, 0x0b], Type::I32);
    for (index, function) in spec {
        functions[*index] = function.clone();
    }
    let mut out = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![65];
    for f in WasiFunction::ALL {
        types.push(0x60);
        uint(f.parameters().len() as u32, &mut types);
        types.extend(f.parameters().iter().copied().map(ty));
        uint(f.results().len() as u32, &mut types);
        types.extend(f.results().iter().copied().map(ty));
    }
    types.extend([0x60, 0, 0, 0x60, 0, 1, 0x7f]);
    for f in &functions {
        types.push(0x60);
        uint(f.params.len() as u32, &mut types);
        types.extend(f.params.iter().copied().map(ty));
        uint(u32::from(f.result.is_some()), &mut types);
        if let Some(result) = f.result {
            types.push(ty(result));
        }
    }
    section(1, &types, &mut out);
    let mut imports = vec![34];
    for (index, f) in WasiFunction::ALL.into_iter().enumerate() {
        text(b"wasi_snapshot_preview1", &mut imports);
        text(f.name(), &mut imports);
        imports.push(0);
        uint(index as u32, &mut imports);
    }
    section(2, &imports, &mut out);
    let mut declarations = vec![29];
    for index in 0..29 {
        uint(36 + index, &mut declarations);
    }
    section(3, &declarations, &mut out);
    let mut table_section = vec![1, 0x70, 1];
    uint(46713, &mut table_section);
    uint(46713, &mut table_section);
    section(4, &table_section, &mut out);
    let mut memory = vec![1, 0];
    uint(584, &mut memory);
    section(5, &memory, &mut out);
    let globals = [
        4, 0x7f, 1, 0x41, 0, 0x0b, 0x7e, 0, 0x42, 0, 0x0b, 0x7d, 1, 0x43, 0, 0, 0, 0, 0x0b, 0x7c,
        1, 0x44, 0, 0, 0, 0, 0, 0, 0, 0, 0x0b,
    ];
    section(6, &globals, &mut out);
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
    if !table.is_empty() {
        let mut elements = vec![1, 0, 0x41, 0, 0x0b];
        uint(table.len() as u32, &mut elements);
        for function in table {
            uint(*function, &mut elements);
        }
        section(9, &elements, &mut out);
    }
    let mut code = vec![29];
    let mut starts = Vec::new();
    for f in &functions {
        let mut body = vec![];
        uint(f.locals.len() as u32, &mut body);
        for local in &f.locals {
            body.extend([1, ty(*local)]);
        }
        let prefix = body.len();
        body.extend_from_slice(&f.body);
        uint(body.len() as u32, &mut code);
        starts.push(code.len() + prefix);
        code.extend(body);
    }
    let mut length = vec![];
    uint(code.len() as u32, &mut length);
    let begin = out.len() + 1 + length.len();
    for at in &mut starts {
        *at += begin;
    }
    section(10, &code, &mut out);
    let mut data = vec![1, 0, 0x41, 0, 0x0b, 17];
    data.extend([16, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, b'x']);
    section(11, &data, &mut out);
    (out, starts)
}
fn owner_with(
    spec: &[(usize, Function)],
    table: &[u32],
    budget: SwiftRunBudget,
    grants: WasiGrants,
    wasi_budget: WasiBudget,
) -> SwiftReactorInstance {
    frame_tests::hooks(frame_tests::Hooks::default());
    let (bytes, _) = module(spec, table);
    let proof = validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let mut pair = Some(
        RuntimeControl::adopt(proof, budget, Instant::now(), Cancellation::default()).unwrap(),
    );
    SwiftReactorInstance::construct(
        &mut pair,
        grants,
        wasi_budget,
        Instant::now(),
        frame_tests::cursor(),
    )
    .unwrap()
}
fn owner(spec: &[(usize, Function)]) -> SwiftReactorInstance {
    owner_with(
        spec,
        &[],
        SwiftRunBudget::default(),
        WasiGrants::default(),
        WasiBudget::default(),
    )
}
fn observed(owner: &SwiftReactorInstance) -> SwiftRunUsage {
    owner
        .control
        .as_ref()
        .unwrap()
        .usage(owner.wasi.as_ref().map(|wasi| wasi.usage()))
}
fn normalized(mut usage: SwiftRunUsage) -> SwiftRunUsage {
    // These are clock observations at the observer call, not mutated counters.
    usage.elapsed_micros = 0;
    usage.deadline_overshoot_micros = 0;
    usage
}
fn success(owner: &mut SwiftReactorInstance, selected: Request) -> Reply {
    match request(owner, selected) {
        Completion::Completed(reply) => reply,
        _ => panic!("actual operation did not complete"),
    }
}
fn failed(owner: &mut SwiftReactorInstance, selected: Request) -> SwiftRunFailure {
    match request(owner, selected) {
        Completion::PreparationFailed(failure) => failure,
        Completion::Failed {
            failure,
            cleanup: GrowthCompletion::Completed(completion),
        } => failure
            .or(match completion {
                FrameCompletion::Retained(report) | FrameCompletion::RestoreRejected(report) => {
                    report.first_failure
                }
                FrameCompletion::Completed => None,
            })
            .expect("actual sticky failure"),
        _ => panic!("expected actual failed operation with accounted cleanup"),
    }
}
fn retire(mut owner: SwiftReactorInstance) {
    frame_tests::hooks(frame_tests::Hooks::default());
    if owner.state.as_ref().unwrap().frame_cleanup.bound.is_some() {
        frame_tests::drain_complete(&mut owner);
    }
    frame_tests::retire(owner);
}
fn scalar(value: i32) -> Function {
    let mut body = Vec::new();
    i32_const(value, &mut body);
    body.push(0x0b);
    Function::scalar(&body, Type::I32)
}
fn i32_const(mut value: i32, body: &mut Vec<u8>) {
    body.push(0x41);
    loop {
        let byte = (value & 0x7f) as u8;
        value >>= 7;
        let done = (value == 0 && byte & 0x40 == 0) || (value == -1 && byte & 0x40 != 0);
        body.push(byte | if done { 0 } else { 128 });
        if done {
            break;
        }
    }
}
fn wasi_call(
    function: WasiFunction,
    arguments: &[i32],
    drop_result: bool,
    tail: &[u8],
) -> Function {
    let mut body = Vec::new();
    for argument in arguments {
        i32_const(*argument, &mut body);
    }
    body.push(0x10);
    uint(
        WasiFunction::ALL
            .iter()
            .position(|f| *f == function)
            .unwrap() as u32,
        &mut body,
    );
    if drop_result {
        body.push(0x1a);
    }
    body.extend_from_slice(tail);
    body.push(0x0b);
    Function::void(&body)
}
fn state_spec() -> [(usize, Function); 3] {
    // Init: global0=1 and memory[64]=1. Callee36: increment both and return
    // global0. Corpus62: actual indirect call through persistent table[0].
    [
        (
            1,
            Function::void(&[0x41, 1, 0x24, 0, 0x41, 0xc0, 0, 0x41, 1, 0x36, 2, 0, 0x0b]),
        ),
        (
            2,
            Function::scalar(
                &[
                    0x23, 0, 0x41, 1, 0x6a, 0x24, 0, 0x41, 0xc0, 0, 0x23, 0, 0x36, 2, 0, 0x23, 0,
                    0x0b,
                ],
                Type::I32,
            ),
        ),
        (
            28,
            Function::scalar(&[0x41, 0, 0x11, 35, 0, 0x0b], Type::I32),
        ),
    ]
}

#[test]
fn swift_lifecycle_sl01_nonexecuting_preconditions() {
    for mode in 0..4 {
        let mut o = owner(&[]);
        if mode == 0 || mode == 2 {
            assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
        }
        if mode >= 2 {
            o.control.as_ref().unwrap().cancellation().cancel();
        }
        let memory = o.state.as_ref().unwrap().memory.clone();
        let globals = o.state.as_ref().unwrap().globals.clone();
        let table = o.state.as_ref().unwrap().table.clone();
        let before = normalized(observed(&o));
        let (returned, measured) = measure_extended(Some(0), || {
            request(
                &mut o,
                if mode % 2 == 0 {
                    Request::Initialize
                } else {
                    Request::Corpus
                },
            )
        });
        assert!(if mode % 2 == 0 {
            matches!(
                &returned,
                Completion::Rejected(Rejection::AlreadyInitialized)
            )
        } else {
            matches!(&returned, Completion::Rejected(Rejection::NotInitialized))
        });
        drop(returned);
        assert_eq!(measured.attempts, 0);
        assert_eq!(normalized(observed(&o)), before);
        assert_eq!(o.state.as_ref().unwrap().memory, memory);
        assert_eq!(o.state.as_ref().unwrap().globals, globals);
        assert_eq!(o.state.as_ref().unwrap().table, table);
        assert!(o.wasi.as_ref().unwrap().stdout().is_empty());
        retire(o);
    }
    for selected in [Request::Initialize, Request::Corpus] {
        let mut o = owner(&[]);
        o.lifecycle = Lifecycle::Terminal; // Explicit corrupt-without-cause case.
        let before = normalized(observed(&o));
        assert!(matches!(
            request(&mut o, selected),
            Completion::BlockedTerminal
        ));
        assert_eq!(normalized(observed(&o)), before);
        retire(o);
    }
}
#[test]
fn swift_lifecycle_sl02_preparation_original_owners_and_bound() {
    for slot in 0..7 {
        let mut o = owner(&[]);
        let state = o.state.as_mut().unwrap();
        let ticket = if slot == 6 {
            state.execution_header.take()
        } else {
            state.buffers[slot].take()
        };
        let before = observed(&o);
        let failure = failed(&mut o, Request::Initialize);
        assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        assert!(o.state.as_ref().unwrap().frame_cleanup.bound.is_none());
        assert_eq!(observed(&o).instructions, before.instructions);
        assert_eq!(observed(&o).host_calls, before.host_calls);
        assert_eq!(observed(&o).reservations, before.reservations);
        if slot == 6 {
            o.state.as_mut().unwrap().execution_header = ticket;
        } else {
            o.state.as_mut().unwrap().buffers[slot] = ticket;
        }
        retire(o);
    }
    for missing in 0..3 {
        let mut o = owner(&[]);
        let wasi = if missing == 0 { o.wasi.take() } else { None };
        let cache = if missing == 1 { o.cache.take() } else { None };
        let state = if missing == 2 { o.state.take() } else { None };
        assert!(matches!(
            request(&mut o, Request::Initialize),
            Completion::PreparationFailed(_)
        ));
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        if let Some(wasi) = wasi {
            o.wasi = Some(wasi);
        }
        if let Some(cache) = cache {
            o.cache = Some(cache);
        }
        if let Some(state) = state {
            o.state = Some(state);
        }
        retire(o);
    }
    // The absent unique control is the inherited expect precondition, not a
    // recoverable runtime failure. No replacement control is manufactured.
}
#[test]
fn swift_lifecycle_sl03_initializer_runs_exactly_once() {
    let init = wasi_call(
        WasiFunction::FdWrite,
        &[1, 0, 1, 8],
        true,
        &[0x41, 1, 0x24, 0],
    );
    let mut o = owner_with(
        &[(1, init)],
        &[],
        SwiftRunBudget::default(),
        WasiGrants {
            stdout: true,
            ..WasiGrants::default()
        },
        WasiBudget::default(),
    );
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    assert_eq!(o.state.as_ref().unwrap().globals[0], Value::I32(1));
    assert_eq!(o.wasi.as_ref().unwrap().stdout(), b"x");
    for _ in 0..2 {
        assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(0));
    }
    let before = normalized(observed(&o));
    assert!(matches!(
        request(&mut o, Request::Initialize),
        Completion::Rejected(Rejection::AlreadyInitialized)
    ));
    assert_eq!(normalized(observed(&o)), before);
    assert_eq!(o.wasi.as_ref().unwrap().stdout(), b"x");
    retire(o);
}
#[test]
fn swift_lifecycle_sl04_actual_initializer_outcome_shape() {
    for mode in 1..=5 {
        let mut o = owner(&[]);
        let hook = Hook::set(mode);
        let failure = failed(&mut o, Request::Initialize);
        assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        drop(hook);
        retire(o);
    }
    let mut o = owner(&[]);
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    retire(o);
}
#[test]
fn swift_lifecycle_sl05_ready_waits_for_actual_clean_frame_barrier() {
    let mut o = owner(&[]);
    let hook = Hook::set(10);
    match request(&mut o, Request::Initialize) {
        Completion::Failed {
            failure: None,
            cleanup: GrowthCompletion::Completed(FrameCompletion::Retained(report)),
        } => {
            assert_eq!(report.live.values.current, 1);
            assert!(report.bound.is_some());
        }
        _ => panic!("nonempty actual value must retain frame envelope"),
    }
    drop(hook);
    assert!(matches!(o.lifecycle, Lifecycle::Terminal));
    retire(o);
}
#[test]
fn swift_lifecycle_sl06_growth_retention_keeps_original_authority() {
    let mut o = owner(&[]);
    let before = observed(&o).reservations.construction.current;
    let hook = Hook::set(9);
    match request(&mut o, Request::Initialize) {
        Completion::Failed {
            failure: None,
            cleanup:
                GrowthCompletion::Retained {
                    mut phase,
                    mut context,
                    mut growth,
                    mut storage,
                    preparation,
                },
        } => {
            assert_eq!(growth.transfer.replacement.capacity(), PAGE);
            assert!(growth.transfer.ticket.is_some());
            assert!(
                phase
                    .phase
                    .operation
                    .control
                    .usage(None)
                    .reservations
                    .construction
                    .current
                    > before
            );
            release_growth_pending(&mut phase, &mut context, &mut growth).unwrap();
            storage.drained = Some(phase.drain());
            assert!(matches!(
                complete_growth(phase, context, growth, storage, preparation),
                GrowthCompletion::Completed(FrameCompletion::Completed)
            ));
        }
        _ => panic!("exact growth carrier was lost"),
    }
    drop(hook);
    assert!(matches!(o.lifecycle, Lifecycle::Terminal));
    retire(o);
}
#[test]
fn swift_lifecycle_sl07_inner_restore_rejection_never_returns_success() {
    let mut o = owner(&[]);
    frame_tests::hooks(frame_tests::Hooks {
        reject_outer_restore: true,
        ..frame_tests::Hooks::default()
    });
    match request(&mut o, Request::Initialize) {
        Completion::Failed {
            failure: None,
            cleanup: GrowthCompletion::Completed(FrameCompletion::RestoreRejected(report)),
        } => assert!(report.first_failure.is_some()),
        _ => panic!("inner restore rejection cannot publish Initialized"),
    }
    assert!(matches!(o.lifecycle, Lifecycle::Terminal));
    frame_tests::hooks(frame_tests::Hooks::default());
    retire(o);
}
#[test]
fn swift_lifecycle_sl08_initializer_traps_exits_and_denied_service() {
    for init in [
        Function::void(&[0x00, 0x0b]),
        Function::void(&[0x41, 1, 0x41, 0, 0x6d, 0x1a, 0x0b]),
        Function::void(&[0x41, 0x7f, 0x28, 2, 0, 0x1a, 0x0b]),
    ] {
        let mut o = owner(&[(1, init)]);
        assert_eq!(
            failed(&mut o, Request::Initialize).kind,
            SwiftRunFailureKind::GuestTrap
        );
        assert!(matches!(
            request(&mut o, Request::Corpus),
            Completion::BlockedTerminal
        ));
        retire(o);
    }
    for code in [0, 7, -1] {
        let mut o = owner(&[(1, wasi_call(WasiFunction::ProcExit, &[code], false, &[]))]);
        let failure = failed(&mut o, Request::Initialize);
        assert_eq!(failure.kind, SwiftRunFailureKind::GuestExit);
        assert_eq!(failure.guest_exit, Some(code as u32));
        retire(o);
    }
    let mut o = owner(&[(1, wasi_call(WasiFunction::RandomGet, &[64, 8], true, &[]))]);
    // Default denial is a real nonzero errno; it does not confer random access.
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    assert_eq!(o.wasi.as_ref().unwrap().usage().random_bytes, 0);
    retire(o);
}
#[test]
fn swift_lifecycle_sl09_initializer_exact_resource_failures() {
    // The same original work budget covers construction and Initialize.
    // Memory/table/globals + four initializers + data range and payload.
    const CONSTRUCTOR_WORK: u64 = 584 * 65_536 + 46_713 + 4 + 4 * 16 + 1 + 17;
    assert_eq!(CONSTRUCTOR_WORK, 38_319_823);
    let spec = [(1, Function::void(&[0x41, 1, 0x1a, 0x0b]))];
    let (bytes, starts) = module(&spec, &[]);
    let first_opcode = starts[1];

    // Zero lifetime work correctly fails before a runnable owner exists.
    let proof = validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let mut pair = Some(
        RuntimeControl::adopt(
            proof,
            SwiftRunBudget {
                execution_work: 0,
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
        WasiBudget::default(),
        Instant::now(),
        frame_tests::cursor(),
    ));
    let tail = match returned.take().unwrap() {
        Err(crate::experimental_swift_reactor::execution::ConstructionFailure::Cleanup(tail)) => {
            tail
        }
        _ => panic!("expected original constructor cleanup authority"),
    };
    assert!(pair.is_none());
    let failure = tail.tail.failure.expect("actual constructor first failure");
    assert_eq!(failure.stage, SwiftRunStage::Invocation);
    assert_eq!(failure.function, Some(34));
    assert_eq!(failure.offset, Some(211));
    assert_eq!(failure.kind, SwiftRunFailureKind::WorkExhausted);
    assert_eq!(failure.code, "swift_run_work");
    assert_eq!(failure.resource, Some(SwiftRunResource::ExecutionWork));
    assert_eq!((failure.attempted, failure.limit), (38_319_741, 0));
    let mut outcome = None;
    let mut final_usage = None;
    tail.complete((pair, returned), &mut outcome, &mut final_usage);
    let cleaned_failure = outcome.expect("original constructor failure remains authoritative");
    assert_eq!(cleaned_failure.kind, failure.kind);
    assert_eq!(cleaned_failure.code, failure.code);
    assert_eq!(cleaned_failure.resource, failure.resource);
    assert_eq!(cleaned_failure.attempted, failure.attempted);
    assert_eq!(cleaned_failure.limit, failure.limit);
    let cleaned = final_usage.unwrap();
    assert_eq!(cleaned.reservations.combined.current, 0);
    assert_eq!(cleaned.reservations.live_tickets, 0);
    assert_eq!(cleaned.live.frames.current, 0);
    assert_eq!(cleaned.live.values.current, 0);
    assert_eq!(cleaned.live.controls.current, 0);
    assert_eq!(cleaned.live.active_pins.current, 0);
    assert_eq!(cleaned.live.cache_entries.current, 0);
    assert_eq!(cleaned.live.memory_pages.current, 0);

    for dimension in 0..5 {
        let mut budget = SwiftRunBudget::default();
        let (kind, code, resource, attempted, limit, offset) = match dimension {
            0 => {
                budget.instruction_fuel = 0;
                (
                    SwiftRunFailureKind::FuelExhausted,
                    "swift_run_fuel",
                    SwiftRunResource::InstructionFuel,
                    1,
                    0,
                    Some(first_opcode),
                )
            }
            1 => {
                budget.execution_work = CONSTRUCTOR_WORK;
                (
                    SwiftRunFailureKind::WorkExhausted,
                    "swift_run_work",
                    SwiftRunResource::ExecutionWork,
                    CONSTRUCTOR_WORK + 1,
                    CONSTRUCTOR_WORK,
                    None,
                )
            }
            2 => {
                budget.frames = 0;
                (
                    SwiftRunFailureKind::FrameLimit,
                    "swift_frame_depth",
                    SwiftRunResource::Frames,
                    1,
                    0,
                    None,
                )
            }
            3 => {
                budget.values = 0;
                (
                    SwiftRunFailureKind::ValueLimit,
                    "swift_execution_value_capacity",
                    SwiftRunResource::Values,
                    1,
                    0,
                    Some(first_opcode),
                )
            }
            _ => {
                budget.controls = 0;
                (
                    SwiftRunFailureKind::ControlLimit,
                    "swift_frame_control_capacity",
                    SwiftRunResource::Controls,
                    1,
                    0,
                    None,
                )
            }
        };
        let mut o = owner_with(
            &spec,
            &[],
            budget,
            WasiGrants::default(),
            WasiBudget::default(),
        );
        let constructed = observed(&o);
        assert_eq!(constructed.execution_work, CONSTRUCTOR_WORK);
        let bound = constructed.reservations.construction.current;
        let failure = failed(&mut o, Request::Initialize);
        assert_eq!(failure.stage, SwiftRunStage::Initialization);
        assert_eq!(failure.function, Some(35));
        assert_eq!(failure.offset, offset);
        assert_eq!(failure.kind, kind);
        assert_eq!(failure.code, code);
        assert_eq!(failure.resource, Some(resource));
        assert_eq!((failure.attempted, failure.limit), (attempted, limit));
        if dimension == 1 {
            assert_eq!(failure.at_failure.execution_work, CONSTRUCTOR_WORK);
            assert_eq!(failure.at_failure.instructions, 0);
            assert_eq!(failure.at_failure.instruction_fuel, 0);
        }
        if dimension == 0 {
            assert_eq!(failure.at_failure.instructions, 0);
            assert_eq!(failure.at_failure.instruction_fuel, 0);
        }
        assert_eq!(failure.at_failure.host_calls, 0);
        let after = observed(&o);
        assert_eq!(after.live.frames.current, 0);
        assert_eq!(after.live.values.current, 0);
        assert_eq!(after.live.controls.current, 0);
        assert_eq!(after.live.active_pins.current, 0);
        assert_eq!(after.reservations.construction.current, bound);
        assert!(o.state.as_ref().unwrap().frame_cleanup.bound.is_none());
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        retire(o);
    }
    let host_spec = [(
        1,
        wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[]),
    )];
    let (_, host_starts) = module(&host_spec, &[]);
    let mut o = owner_with(
        &host_spec,
        &[],
        SwiftRunBudget {
            host_calls: 0,
            ..SwiftRunBudget::default()
        },
        WasiGrants {
            stdout: true,
            ..WasiGrants::default()
        },
        WasiBudget::default(),
    );
    let failure = failed(&mut o, Request::Initialize);
    assert_eq!(failure.stage, SwiftRunStage::Initialization);
    assert_eq!(failure.function, Some(35));
    // Four original two-byte i32.const arguments precede the call opcode.
    assert_eq!(failure.offset, Some(host_starts[1] + 8));
    assert_eq!(failure.kind, SwiftRunFailureKind::HostCallLimit);
    assert_eq!(failure.code, "swift_run_host_calls");
    assert_eq!(failure.resource, Some(SwiftRunResource::HostCalls));
    assert_eq!((failure.attempted, failure.limit), (1, 0));
    assert_eq!(failure.at_failure.host_calls, 0);
    assert_eq!(o.wasi.as_ref().unwrap().usage().calls, 0);
    assert!(o.wasi.as_ref().unwrap().stdout().is_empty());
    assert!(matches!(o.lifecycle, Lifecycle::Terminal));
    retire(o);
}
#[test]
fn swift_lifecycle_sl10_final_checkpoint_observes_cancel_and_deadline() {
    for mode in [7, 8] {
        let mut o = owner_with(
            &[],
            &[],
            SwiftRunBudget {
                deadline_ms: 1000,
                ..SwiftRunBudget::default()
            },
            WasiGrants::default(),
            WasiBudget::default(),
        );
        let deadline = o.control.as_ref().unwrap().deadline();
        let hook = Hook::set(mode);
        let failure = failed(&mut o, Request::Initialize);
        assert_eq!(
            failure.kind,
            if mode == 7 {
                SwiftRunFailureKind::Cancelled
            } else {
                SwiftRunFailureKind::Deadline
            }
        );
        assert_eq!(failure.stage, SwiftRunStage::Initialization);
        assert_eq!(failure.function, Some(35));
        assert_eq!(o.control.as_ref().unwrap().deadline(), deadline);
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        drop(hook);
        retire(o);
    }
}
#[test]
fn swift_lifecycle_sl11_first_diagnostic_and_terminal_marker() {
    let mut o = owner(&[(1, Function::void(&[0x00, 0x0b]))]);
    let first = failed(&mut o, Request::Initialize);
    let before = normalized(observed(&o));
    assert!(first.offset.is_some());
    for selected in [Request::Initialize, Request::Corpus] {
        assert!(matches!(
            request(&mut o, selected),
            Completion::BlockedTerminal
        ));
    }
    assert_eq!(normalized(observed(&o)), before);
    let actual = o
        .control
        .as_mut()
        .unwrap()
        .record_cleanup(Some(o.wasi.as_ref().unwrap().usage()))
        .unwrap();
    assert_eq!(actual.kind, first.kind);
    assert_eq!(actual.code, first.code);
    assert_eq!(actual.function, first.function);
    assert_eq!(actual.offset, first.offset);
    assert_eq!(actual.at_failure, first.at_failure);
    retire(o);
}
#[test]
fn swift_lifecycle_sl12_persistent_memory_global_and_indirect_table_reads() {
    let mut o = owner_with(
        &state_spec(),
        &[36],
        SwiftRunBudget::default(),
        WasiGrants::default(),
        WasiBudget::default(),
    );
    let memory = o.state.as_ref().unwrap().memory.as_ptr();
    let table = o.state.as_ref().unwrap().table.as_ptr();
    let table_contents = o.state.as_ref().unwrap().table.clone();
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    for expected in [2, 3] {
        assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(expected));
        let state = o.state.as_ref().unwrap();
        assert_eq!(state.globals[0], Value::I32(expected));
        assert_eq!(&state.memory[64..68], &expected.to_le_bytes());
        assert_eq!(state.memory.as_ptr(), memory);
        assert_eq!(state.table.as_ptr(), table);
        assert_eq!(state.table, table_contents);
    }
    retire(o);
    // Guest table mutation is unsupported by the selected MVP vocabulary; do
    // not equate these repeated indirect reads with a mutation test.
    let (bytes, _) = module(
        &[(1, Function::void(&[0x41, 0, 0xd0, 0x70, 0x26, 0, 0x0b]))],
        &[],
    );
    assert!(validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
}
#[test]
fn swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage() {
    let mut o = owner_with(
        &state_spec(),
        &[36],
        SwiftRunBudget::default(),
        WasiGrants::default(),
        WasiBudget::default(),
    );
    let deadline = o.control.as_ref().unwrap().deadline();
    let start = observed(&o);
    assert_eq!(start.live.cache_entries.current, 0);
    // Constructor writes 29 slots, 64 pin records, 512 patches, 192 index cells
    // and eight charged semantic cells for each of 512 scan-plan entries.
    // Publishing the initialized free-pin bitmap costs one additional credit.
    assert_eq!(start.cache_work, 29 + 64 + 1 + 512 + 192 + 512 * 8);
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    let initialized = observed(&o);
    // Resident Cache tickets belong to decoded entries, surviving pin release.
    assert_eq!(
        initialized.reservations.live_tickets - start.reservations.live_tickets,
        1
    );
    assert_eq!(initialized.live.cache_entries.current, 1);
    assert_eq!(initialized.instructions - start.instructions, 6);
    // Cold cost includes 13 probe/publication credits and five credits for
    // successful bitmap pin selection: 108 + 5 + 2*body bytes + 3*instructions + 13.
    // Init35: B14/I6; corpus62: B7/I3; callee36: B19/I9.
    assert_eq!(
        initialized.cache_work - start.cache_work,
        108 + 5 + 2 * 14 + 3 * 6 + 13
    );
    assert_eq!(initialized.cache_work, 5_066);
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(2));
    let first = observed(&o);
    assert_eq!(
        first.reservations.live_tickets - initialized.reservations.live_tickets,
        2
    );
    assert_eq!(first.live.cache_entries.current, 3);
    let first_cache = o.cache.as_ref().unwrap().usage();
    assert_eq!(
        first.cache_work - initialized.cache_work,
        (108 + 5 + 2 * 7 + 3 * 3 + 13) + (108 + 5 + 2 * 19 + 3 * 9 + 13)
    );
    assert_eq!(first.cache_work, 5_406);
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(3));
    let second = observed(&o);
    assert_eq!(
        second.reservations.live_tickets - first.reservations.live_tickets,
        0
    );
    assert_eq!(second.live.cache_entries.current, 3);
    let second_cache = o.cache.as_ref().unwrap().usage();
    // Corpus: const+indirect+end (3); callee: get,const,add,set,const,get,store,get,end (9).
    assert_eq!(first.instructions - initialized.instructions, 12);
    assert_eq!(second.instructions - first.instructions, 12);
    assert!(
        second.execution_work > first.execution_work
            && first.execution_work > initialized.execution_work
    );
    // Resident order35@0,62@1,36@2. Outer pin record0 stays live for callee.
    // Lookup + bitmap pin selection + checked index chain: both 1+5+6.
    assert_eq!(
        second.cache_work - first.cache_work,
        (1 + 5 + 6) + (1 + 5 + 6)
    );
    assert_eq!(second.cache_work, 5_430);
    assert_eq!(second_cache.hits - first_cache.hits, 2);
    assert_eq!(second_cache.misses, first_cache.misses);
    assert_eq!(second_cache.decodes, first_cache.decodes);
    assert_eq!(second_cache.evictions, first_cache.evictions);
    assert_eq!(second_cache.resident_bytes, first_cache.resident_bytes);
    assert_eq!(second_cache.active_pins, first_cache.active_pins);
    assert_eq!(second.host_calls, 0);
    assert_eq!(
        second.reservations.live_tickets,
        first.reservations.live_tickets
    );
    assert_eq!(o.control.as_ref().unwrap().deadline(), deadline);
    retire(o);
}
#[test]
fn swift_lifecycle_sl14_later_calls_share_the_remaining_fuel() {
    let mut o = owner_with(
        &[],
        &[],
        SwiftRunBudget {
            instruction_fuel: 4,
            ..SwiftRunBudget::default()
        },
        WasiGrants::default(),
        WasiBudget::default(),
    );
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized); // end: 1
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(0)); // const,end: 2
    let failure = failed(&mut o, Request::Corpus); // const then exhausted end
    assert_eq!(failure.kind, SwiftRunFailureKind::FuelExhausted);
    assert_eq!(failure.at_failure.instructions, 4);
    assert!(matches!(o.lifecycle, Lifecycle::Terminal));
    retire(o);
}
#[test]
fn swift_lifecycle_sl15_output_suffixes_and_partial_effects() {
    let init = wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[]);
    let mut corpus = wasi_call(WasiFunction::FdWrite, &[2, 0, 1, 8], true, &[0x41, 0]);
    corpus.result = Some(Type::I32);
    let mut o = owner_with(
        &[(1, init), (28, corpus)],
        &[],
        SwiftRunBudget::default(),
        WasiGrants {
            stdout: true,
            stderr: true,
            ..WasiGrants::default()
        },
        WasiBudget::default(),
    );
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    assert_eq!(o.wasi.as_ref().unwrap().stdout(), b"x");
    for length in [1, 2] {
        assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(0));
        assert_eq!(o.wasi.as_ref().unwrap().stderr(), &b"xx"[..length]);
    }
    assert_eq!(o.wasi.as_ref().unwrap().usage().log_bytes, 3);
    retire(o);
    let mut o = owner_with(
        &[(
            1,
            wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[0x00]),
        )],
        &[],
        SwiftRunBudget::default(),
        WasiGrants {
            stdout: true,
            ..WasiGrants::default()
        },
        WasiBudget::default(),
    );
    assert_eq!(
        failed(&mut o, Request::Initialize).kind,
        SwiftRunFailureKind::GuestTrap
    );
    assert_eq!(o.wasi.as_ref().unwrap().stdout(), b"x");
    retire(o);
}
#[test]
fn swift_lifecycle_sl16_i32_result_shape_and_completion() {
    for expected in [0, 7, -19, i32::MAX, i32::MIN] {
        let mut o = owner(&[(28, scalar(expected))]);
        assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
        assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(expected));
        retire(o);
    }
    for mode in [1, 2, 6] {
        let mut o = owner(&[]);
        success(&mut o, Request::Initialize);
        let hook = Hook::set(mode);
        assert_eq!(
            failed(&mut o, Request::Corpus).kind,
            SwiftRunFailureKind::Invariant
        );
        drop(hook);
        retire(o);
    }
    let mut o = owner(&[(28, scalar(7))]);
    success(&mut o, Request::Initialize);
    frame_tests::hooks(frame_tests::Hooks {
        reject_outer_restore: true,
        ..frame_tests::Hooks::default()
    });
    match request(&mut o, Request::Corpus) {
        Completion::Failed {
            failure: None,
            cleanup: GrowthCompletion::Completed(FrameCompletion::RestoreRejected(_)),
        } => (),
        _ => panic!("scalar escaped incomplete restore"),
    }
    frame_tests::hooks(frame_tests::Hooks::default());
    retire(o);
}
#[test]
fn swift_lifecycle_sl17_real_wasi_grants_and_denials() {
    let init = wasi_call(WasiFunction::RandomGet, &[64, 8], true, &[]);
    let mut o = owner_with(
        &[(1, init)],
        &[],
        SwiftRunBudget::default(),
        WasiGrants {
            secure_random: true,
            realtime: true,
            monotonic: true,
            ..WasiGrants::default()
        },
        WasiBudget::default(),
    );
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    assert_eq!(o.wasi.as_ref().unwrap().usage().random_bytes, 8);
    assert_eq!(o.wasi.as_ref().unwrap().usage().calls, 1);
    assert!(o.wasi.as_ref().unwrap().stdout().is_empty());
    retire(o);
    let mut o = owner(&[(
        1,
        wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[]),
    )]);
    success(&mut o, Request::Initialize);
    assert!(o.wasi.as_ref().unwrap().stdout().is_empty());
    assert_eq!(o.wasi.as_ref().unwrap().usage().log_bytes, 0);
    retire(o);
}
#[test]
fn swift_lifecycle_sl18_deepest_first_terminal_cleanup_without_work() {
    let mut o = owner(&[
        (1, Function::void(&[0x10, 36, 0x0b])),
        (2, Function::void(&[0x10, 37, 0x0b])),
        (3, Function::void(&[0x00, 0x0b])),
    ]);
    let failure = failed(&mut o, Request::Initialize);
    assert_eq!(failure.kind, SwiftRunFailureKind::GuestTrap);
    let after = observed(&o);
    assert_eq!(after.live.frames.current, 0);
    assert_eq!(after.live.active_pins.current, 0);
    assert_eq!(after.live.values.current, 0);
    assert_eq!(after.live.controls.current, 0);
    assert_eq!(after.instructions, failure.at_failure.instructions);
    assert_eq!(after.execution_work, failure.at_failure.execution_work);
    assert!(o.state.as_ref().unwrap().frame_cleanup.is_empty());
    retire(o);
}
#[test]
fn swift_lifecycle_sl19_frame_admission_exact_and_one_below_combined() {
    for exact in [false, true] {
        let mut o = owner(&[]);
        let current = observed(&o).reservations.combined.current;
        let envelope = FRAME_OPERATION_BYTES.unwrap();
        let old = o
            .control
            .as_mut()
            .unwrap()
            .test_replace_combined_limit(current + envelope - usize::from(!exact));
        if exact {
            // Entry's cold cache may need additional Combined room; preparation
            // alone exercises the exact frame envelope without inventing success.
            let (mut phase, context) = o
                .prepare_growth_with_goal(frame_tests::cursor(), PreparationGoal::Terminalize)
                .unwrap();
            let report = phase.drain();
            assert_eq!(report.retained_frames, 0);
            assert!(matches!(
                complete_growth(
                    phase,
                    context,
                    SwiftGrowthStorage::empty(),
                    FrameOperationStorage {
                        preparation: None,
                        entry: None,
                        returned: None,
                        drained: Some(report),
                        controlled: None
                    },
                    None
                ),
                GrowthCompletion::Completed(FrameCompletion::Completed)
            ));
        } else {
            let failure = failed(&mut o, Request::Initialize);
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
            assert!(o.state.as_ref().unwrap().frame_cleanup.bound.is_none());
        }
        o.control.as_mut().unwrap().test_replace_combined_limit(old);
        retire(o);
    }
}
#[test]
fn swift_lifecycle_sl20_warm_lifecycle_wrapper_allocates_nothing() {
    let mut o = owner(&[]);
    success(&mut o, Request::Initialize);
    success(&mut o, Request::Corpus);
    let (reply, stats) = measure_extended(Some(0), || request(&mut o, Request::Corpus));
    assert!(matches!(reply, Completion::Completed(Reply::Corpus(0))));
    drop(reply);
    assert_eq!(stats.attempts, 0);
    assert_eq!(stats.allocations, 0);
    retire(o);
}
#[test]
fn swift_lifecycle_sl21_additive_accounting_keeps_original_limits() {
    assert_eq!(MAX_RESERVATION_TICKETS, 86);
    assert_eq!(SwiftRunBudget::default().state_bytes, 128 * 1024 * 1024);
    assert_eq!(SwiftRunBudget::default().combined_bytes, 256 * 1024 * 1024);
    // Exact compiler position/owner/layout identities are checked by the saved
    // compiler packet; this executable row checks actual charged formula joins.
    const {
        assert!(super::PERMANENT_BYTES > 0);
        assert!(super::ACTIVE_BYTES > 0);
    }
    let mut o = owner(&[]);
    let before = observed(&o).reservations.construction.current;
    success(&mut o, Request::Initialize);
    assert_eq!(observed(&o).reservations.construction.current, before);
    retire(o);
}
#[test]
fn swift_lifecycle_sl22_closed_targets_and_strict_validation() {
    let (mut bytes, _) = module(&[], &[]);
    // Unsupported reference-type instruction cannot enter via a syntax-only
    // lifecycle route; complete strict validation rejects the modified fixture.
    let (invalid, _) = module(
        &[(28, Function::scalar(&[0xd0, 0x70, 0x0b], Type::I32))],
        &[],
    );
    assert!(validate_swift_reactor(
        &invalid,
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
    bytes[0] = 1;
    assert!(validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
    let mut o = owner(&[]);
    assert!(matches!(
        request(&mut o, Request::Corpus),
        Completion::Rejected(Rejection::NotInitialized)
    ));
    retire(o);
}
#[test]
fn swift_lifecycle_sl23_preserve_callers_do_not_publish_ready() {
    let mut o = owner(&[]);
    let (mut phase, mut context) = o.prepare_growth(frame_tests::cursor()).unwrap();
    phase.enter(35).unwrap();
    let mut pending = SwiftGrowthStorage::empty();
    let mut storage = FrameOperationStorage {
        preparation: None,
        entry: None,
        returned: None,
        drained: None,
        controlled: None,
    };
    call_dispatch::run(&mut phase, &mut context, &mut pending, &mut storage).unwrap();
    assert!(matches!(
        storage.returned,
        Some(Ok(FrameReturn::Outermost(None)))
    ));
    assert!(matches!(
        call_dispatch::complete(phase, context, pending, storage, None),
        GrowthCompletion::Completed(FrameCompletion::Completed)
    ));
    assert!(matches!(o.lifecycle, Lifecycle::Uninitialized));
    retire(o);
}

// Additive remaining-matrix cases. Expected instruction traces and errno values
// below are authored from the explicit guest programs, not replayed observations.
#[test]
fn swift_lifecycle_sl01_expired_and_missing_control_refusals_are_nonexecuting() {
    for initialized in [false, true] {
        let mut o = owner(&[]);
        if initialized {
            success(&mut o, Request::Initialize);
        }
        let control = o.control.take();
        // Even an unavailable authority cannot be observed on ordinary misuse.
        let (reply, stats) = measure_extended(Some(0), || {
            request(
                &mut o,
                if initialized {
                    Request::Initialize
                } else {
                    Request::Corpus
                },
            )
        });
        assert!(matches!(&reply, Completion::Rejected(_)));
        drop(reply);
        assert_eq!(stats.attempts, 0);
        o.control = control;
        retire(o);
    }
    for initialized in [false, true] {
        let mut o = owner(&[]);
        if initialized {
            success(&mut o, Request::Initialize);
        }
        let before = normalized(observed(&o));
        assert_eq!(before.deadline_origin, SwiftDeadlineOrigin::Run);
        let until = o.control.as_mut().unwrap().test_expire_deadline();
        assert_eq!(normalized(observed(&o)), before);
        assert!(matches!(
            request(
                &mut o,
                if initialized {
                    Request::Initialize
                } else {
                    Request::Corpus
                }
            ),
            Completion::Rejected(_)
        ));
        assert_eq!(normalized(observed(&o)), before);
        let failure = failed(
            &mut o,
            if initialized {
                Request::Corpus
            } else {
                Request::Initialize
            },
        );
        assert_eq!(failure.kind, SwiftRunFailureKind::Deadline);
        assert_eq!(failure.deadline_origin, SwiftDeadlineOrigin::Run);
        assert_eq!(failure.at_failure.instructions, before.instructions);
        assert_eq!(failure.at_failure.host_calls, before.host_calls);
        assert_eq!(o.control.as_ref().unwrap().deadline(), until);
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl02_foreign_original_tickets_and_owners_reject_before_entry() {
    for slot in 0..10 {
        let mut o = owner(&[]);
        let mut foreign = owner(&[]);
        match slot {
            0..=5 => std::mem::swap(
                &mut o.state.as_mut().unwrap().buffers[slot],
                &mut foreign.state.as_mut().unwrap().buffers[slot],
            ),
            6 => std::mem::swap(
                &mut o.state.as_mut().unwrap().execution_header,
                &mut foreign.state.as_mut().unwrap().execution_header,
            ),
            7 => std::mem::swap(&mut o.cache, &mut foreign.cache),
            8 => std::mem::swap(&mut o.wasi, &mut foreign.wasi),
            _ => std::mem::swap(&mut o.state, &mut foreign.state),
        }
        let before = observed(&o);
        let (failure, allocation) =
            measure_extended(Some(0), || failed(&mut o, Request::Initialize));
        assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
        assert_eq!(failure.stage, SwiftRunStage::Initialization);
        assert_eq!(failure.function, Some(35));
        assert_eq!(allocation.attempts, 0);
        assert_eq!(observed(&o).instructions, before.instructions);
        assert_eq!(observed(&o).host_calls, 0);
        assert_eq!(observed(&o).reservations, before.reservations);
        assert!(o.state.as_ref().unwrap().frame_cleanup.bound.is_none());
        match slot {
            0..=5 => std::mem::swap(
                &mut o.state.as_mut().unwrap().buffers[slot],
                &mut foreign.state.as_mut().unwrap().buffers[slot],
            ),
            6 => std::mem::swap(
                &mut o.state.as_mut().unwrap().execution_header,
                &mut foreign.state.as_mut().unwrap().execution_header,
            ),
            7 => std::mem::swap(&mut o.cache, &mut foreign.cache),
            8 => std::mem::swap(&mut o.wasi, &mut foreign.wasi),
            _ => std::mem::swap(&mut o.state, &mut foreign.state),
        }
        retire(o);
        retire(foreign);
    }
}

#[test]
fn swift_lifecycle_sl02_existing_frame_bound_is_preserved_on_rejected_preparation() {
    let mut o = owner(&[]);
    let (mut phase, context) = o.prepare_growth(frame_tests::cursor()).unwrap();
    phase.enter(36).unwrap();
    // End this borrow without claiming completion. Real frame/pin/debt remains.
    drop((phase, context));
    let before = observed(&o);
    let previous = o.state.as_ref().unwrap().frame_cleanup.bound;
    let failure = failed(&mut o, Request::Initialize);
    assert_eq!(failure.code, "swift_frame_prepare_nonempty");
    assert_eq!(observed(&o).reservations, before.reservations);
    assert_eq!(observed(&o).live, before.live);
    assert_eq!(observed(&o).instructions, before.instructions);
    let after = o.state.as_ref().unwrap().frame_cleanup.bound;
    assert_eq!(
        after.map(|b| (b.previous, b.admitted)),
        previous.map(|b| (b.previous, b.admitted))
    );
    retire(o);
}

#[test]
fn swift_lifecycle_sl05_real_frame_control_and_pin_prevent_ready() {
    let mut o = owner(&[]);
    let hook = Hook::set(13);
    match request(&mut o, Request::Initialize) {
        Completion::Failed {
            cleanup: GrowthCompletion::Completed(FrameCompletion::Retained(report)),
            ..
        } => {
            assert_eq!(report.live.frames.current, 1);
            assert_eq!(report.live.controls.current, 1);
            assert_eq!(report.live.active_pins.current, 1);
            assert!(report.bound.is_some());
        }
        _ => panic!("actual entered frame must retain the barrier"),
    }
    assert!(matches!(o.lifecycle, Lifecycle::Terminal));
    drop(hook);
    let before = normalized(observed(&o));
    assert!(matches!(
        request(&mut o, Request::Initialize),
        Completion::BlockedTerminal
    ));
    assert_eq!(normalized(observed(&o)), before);
    retire(o);
}

#[test]
fn swift_lifecycle_sl08_indirect_null_and_signature_traps_terminalize_initializer() {
    for table in [vec![], vec![36]] {
        let mut o = owner_with(
            &[
                (1, Function::void(&[0x41, 0, 0x11, 34, 0, 0x0b])),
                (2, scalar(9)),
            ],
            &table,
            SwiftRunBudget::default(),
            WasiGrants::default(),
            WasiBudget::default(),
        );
        let f = failed(&mut o, Request::Initialize);
        assert_eq!(f.kind, SwiftRunFailureKind::GuestTrap);
        assert_eq!(f.stage, SwiftRunStage::Initialization);
        assert_eq!(f.function, Some(35));
        let before = normalized(observed(&o));
        for selected in [Request::Initialize, Request::Corpus] {
            assert!(matches!(
                request(&mut o, selected),
                Completion::BlockedTerminal
            ));
        }
        assert_eq!(normalized(observed(&o)), before);
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl09_cache_pin_and_nested_frame_limits_fail_closed() {
    for kind in 0..4 {
        let budget = match kind {
            0 => SwiftRunBudget {
                active_pins: 0,
                ..SwiftRunBudget::default()
            },
            1 => SwiftRunBudget {
                cache_entry_bytes: 0,
                ..SwiftRunBudget::default()
            },
            2 => SwiftRunBudget {
                frames: 1,
                ..SwiftRunBudget::default()
            },
            _ => SwiftRunBudget {
                controls: 1,
                ..SwiftRunBudget::default()
            },
        };
        let mut o = owner_with(
            &[(1, Function::void(&[0x10, 36, 0x0b]))],
            &[],
            budget,
            WasiGrants::default(),
            WasiBudget::default(),
        );
        let f = failed(&mut o, Request::Initialize);
        assert_eq!(
            f.kind,
            match kind {
                0 => SwiftRunFailureKind::PinLimit,
                1 => SwiftRunFailureKind::ResourceExhausted,
                2 => SwiftRunFailureKind::FrameLimit,
                _ => SwiftRunFailureKind::ControlLimit,
            }
        );
        assert_eq!(observed(&o).live.frames.current, 0);
        assert_eq!(observed(&o).live.active_pins.current, 0);
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl09_growth_state_and_combined_overlap_fail_before_allocation() {
    for combined in [false, true] {
        let mut o = owner(&[(1, Function::void(&[0x41, 1, 0x40, 0, 0x1a, 0x0b]))]);
        let before = observed(&o);
        let old = if combined {
            o.control.as_mut().unwrap().test_replace_combined_limit(
                before.reservations.combined.current + FRAME_OPERATION_BYTES.unwrap() + 585 * PAGE
                    - 1,
            )
        } else {
            o.control
                .as_mut()
                .unwrap()
                .test_replace_state_limit(before.reservations.state.current + 585 * PAGE - 1)
        };
        // Cache entries need Combined space too. The retained engine's first
        // rejecting category is authoritative; neither route executes growth.
        let f = failed(&mut o, Request::Initialize);
        assert_eq!(
            f.kind,
            if combined {
                SwiftRunFailureKind::CombinedExhausted
            } else {
                SwiftRunFailureKind::CategoryExhausted
            }
        );
        assert_eq!(o.state.as_ref().unwrap().memory.len(), 584 * PAGE);
        assert_eq!(observed(&o).live.memory_pages.current, 584);
        assert_eq!(
            observed(&o).reservations.state.current,
            before.reservations.state.current
        );
        if combined {
            o.control.as_mut().unwrap().test_replace_combined_limit(old);
        } else {
            o.control.as_mut().unwrap().test_replace_state_limit(old);
        }
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl10_preentry_cancel_and_earliest_wasi_deadline() {
    let mut o = owner(&[]);
    o.control.as_ref().unwrap().cancellation().cancel();
    let before = observed(&o);
    let f = failed(&mut o, Request::Initialize);
    assert_eq!(f.kind, SwiftRunFailureKind::Cancelled);
    assert_eq!(observed(&o).instructions, before.instructions);
    assert_eq!(observed(&o).host_calls, 0);
    retire(o);
    let (bytes, _) = module(&[], &[]);
    let proof = validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let started = Instant::now();
    let mut pair = Some(
        RuntimeControl::adopt(
            proof,
            SwiftRunBudget::default(),
            started,
            Cancellation::default(),
        )
        .unwrap(),
    );
    let run_deadline = pair.as_ref().unwrap().0.deadline();
    let mut o = SwiftReactorInstance::construct(
        &mut pair,
        WasiGrants::default(),
        WasiBudget {
            deadline_ms: 20_000,
            ..WasiBudget::default()
        },
        started,
        frame_tests::cursor(),
    )
    .unwrap();
    let carried = o.control.as_ref().unwrap().deadline();
    assert_eq!(carried, started + Duration::from_secs(20));
    assert!(carried < run_deadline);
    let before = normalized(observed(&o));
    assert_eq!(before.deadline_origin, SwiftDeadlineOrigin::Wasi);
    let until = o.control.as_mut().unwrap().test_expire_deadline();
    assert_eq!(normalized(observed(&o)), before);
    let f = failed(&mut o, Request::Initialize);
    assert_eq!(f.kind, SwiftRunFailureKind::Deadline);
    assert_eq!(f.deadline_origin, SwiftDeadlineOrigin::Wasi);
    assert_eq!(f.at_failure.deadline_origin, SwiftDeadlineOrigin::Wasi);
    assert_eq!(f.at_failure.instructions, 0);
    assert_eq!(f.at_failure.host_calls, 0);
    assert_eq!(o.control.as_ref().unwrap().deadline(), until);
    retire(o);
}

#[test]
fn swift_lifecycle_sl11_invocation_first_cause_survives_later_fault_and_cancellation() {
    let spec = [(28, Function::scalar(&[0x00, 0x0b], Type::I32))];
    let (_, starts) = module(&spec, &[]);
    let mut o = owner(&spec);
    success(&mut o, Request::Initialize);
    let first = failed(&mut o, Request::Corpus);
    assert_eq!(first.stage, SwiftRunStage::Invocation);
    assert_eq!(first.function, Some(62));
    assert_eq!(first.offset, Some(starts[28]));
    o.control.as_ref().unwrap().cancellation().cancel();
    let later = o.control.as_mut().unwrap().fail(
        frame_tests::cursor(),
        Fault::new(SwiftRunFailureKind::Invariant, "later_test_fault"),
        None,
    );
    assert_eq!(later.kind, first.kind);
    assert_eq!(later.stage, first.stage);
    assert_eq!(later.function, first.function);
    assert_eq!(later.offset, first.offset);
    assert_eq!(later.at_failure, first.at_failure);
    let before = normalized(observed(&o));
    assert!(matches!(
        request(&mut o, Request::Corpus),
        Completion::BlockedTerminal
    ));
    assert_eq!(normalized(observed(&o)), before);
    retire(o);
}

#[test]
fn swift_lifecycle_sl13_hand_authored_cumulative_host_and_wasi_instruction_trace() {
    let init = wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[]);
    let mut corpus = wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[0x41, 0]);
    corpus.result = Some(Type::I32);
    let mut o = owner_with(
        &[(1, init), (28, corpus)],
        &[],
        SwiftRunBudget::default(),
        WasiGrants {
            stdout: true,
            ..WasiGrants::default()
        },
        WasiBudget::default(),
    );
    // Four constants, call, drop, end; each corpus adds const before end.
    for (selected, instructions, calls, bytes) in [
        (Request::Initialize, 7, 1, b"x".as_slice()),
        (Request::Corpus, 15, 2, b"xx".as_slice()),
        (Request::Corpus, 23, 3, b"xxx".as_slice()),
    ] {
        success(&mut o, selected);
        let actual = observed(&o);
        assert_eq!(actual.instructions, instructions);
        assert_eq!(actual.instruction_fuel, instructions);
        assert_eq!(actual.host_calls, calls);
        let wasi = o.wasi.as_ref().unwrap();
        assert_eq!(wasi.usage().calls, calls);
        assert_eq!(wasi.usage().log_bytes, calls);
        assert_eq!(wasi.stdout(), bytes);
        assert_eq!(
            actual.live.frames.current
                + actual.live.values.current
                + actual.live.controls.current
                + actual.live.active_pins.current,
            0
        );
    }
    retire(o);
}

#[test]
fn swift_lifecycle_sl14_later_host_and_wasi_call_limits_preserve_earlier_output() {
    for wasi_limit in [false, true] {
        for allowance in [1, 2] {
            let init = wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[]);
            let mut corpus = wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[0x41, 0]);
            corpus.result = Some(Type::I32);
            let mut o = owner_with(
                &[(1, init), (28, corpus)],
                &[],
                SwiftRunBudget {
                    host_calls: if wasi_limit { 32768 } else { allowance },
                    ..SwiftRunBudget::default()
                },
                WasiGrants {
                    stdout: true,
                    ..WasiGrants::default()
                },
                WasiBudget {
                    calls: if wasi_limit { allowance } else { 32768 },
                    ..WasiBudget::default()
                },
            );
            success(&mut o, Request::Initialize);
            if allowance == 2 {
                success(&mut o, Request::Corpus);
            }
            let f = failed(&mut o, Request::Corpus);
            assert_eq!(
                f.kind,
                if wasi_limit {
                    SwiftRunFailureKind::Wasi
                } else {
                    SwiftRunFailureKind::HostCallLimit
                }
            );
            assert_eq!(f.stage, SwiftRunStage::Invocation);
            assert_eq!(
                o.wasi.as_ref().unwrap().stdout(),
                &b"xx"[..allowance as usize]
            );
            assert_eq!(o.wasi.as_ref().unwrap().usage().calls, allowance);
            assert!(matches!(o.lifecycle, Lifecycle::Terminal));
            retire(o);
        }
    }
}

#[test]
fn swift_lifecycle_sl14_later_work_cache_and_absolute_deadline_do_not_reset() {
    let mut o = owner(&[]);
    success(&mut o, Request::Initialize);
    let work = observed(&o).execution_work;
    let old = o
        .control
        .as_mut()
        .unwrap()
        .test_replace_execution_work_limit(work);
    let f = failed(&mut o, Request::Corpus);
    assert_eq!(f.kind, SwiftRunFailureKind::WorkExhausted);
    assert_eq!(f.at_failure.execution_work, work);
    assert_eq!(f.at_failure.instructions, 1);
    o.control
        .as_mut()
        .unwrap()
        .test_replace_execution_work_limit(old);
    retire(o);
    // Constructor 4,894; cold no-op init B2/I1:108+5+4+3+13=133.
    // Keep the synthetic limit exactly at completed initialization so the
    // later invocation still fails without resetting cumulative work.
    let mut o = owner_with(
        &[],
        &[],
        SwiftRunBudget {
            cache_work: 5_027,
            ..SwiftRunBudget::default()
        },
        WasiGrants::default(),
        WasiBudget::default(),
    );
    success(&mut o, Request::Initialize);
    assert_eq!(observed(&o).cache_work, 5_027);
    let f = failed(&mut o, Request::Corpus);
    assert_eq!(f.resource, Some(SwiftRunResource::CacheWork));
    assert_eq!(f.at_failure.cache_work, 5_027);
    assert_eq!(f.at_failure.instructions, 1);
    retire(o);
    let mut o = owner(&[]);
    let prepared_deadline = o.control.as_ref().unwrap().deadline();
    success(&mut o, Request::Initialize);
    assert_eq!(o.control.as_ref().unwrap().deadline(), prepared_deadline);
    let before = normalized(observed(&o));
    assert_eq!(before.instructions, 1);
    assert_eq!(before.deadline_origin, SwiftDeadlineOrigin::Run);
    let until = o.control.as_mut().unwrap().test_expire_deadline();
    assert_eq!(normalized(observed(&o)), before);
    let f = failed(&mut o, Request::Corpus);
    assert_eq!(f.kind, SwiftRunFailureKind::Deadline);
    assert_eq!(f.deadline_origin, SwiftDeadlineOrigin::Run);
    assert_eq!(f.at_failure.instructions, 1);
    assert_eq!(f.at_failure.execution_work, before.execution_work);
    assert_eq!(f.at_failure.cache_work, before.cache_work);
    assert_eq!(f.at_failure.host_calls, 0);
    assert_eq!(o.control.as_ref().unwrap().deadline(), until);
    retire(o);
}

#[test]
fn swift_lifecycle_sl15_capture_exhaustion_and_closed_fd_persist_between_calls() {
    let init = wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], true, &[]);
    let mut corpus = wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], false, &[]);
    corpus.result = Some(Type::I32);
    let mut o = owner_with(
        &[(1, init), (28, corpus)],
        &[],
        SwiftRunBudget::default(),
        WasiGrants {
            stdout: true,
            ..WasiGrants::default()
        },
        WasiBudget {
            log_bytes: 2,
            ..WasiBudget::default()
        },
    );
    success(&mut o, Request::Initialize);
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(0));
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(51)); // Preview1 NOSPC.
    assert_eq!(o.wasi.as_ref().unwrap().stdout(), b"xx");
    assert_eq!(o.wasi.as_ref().unwrap().usage().log_bytes, 2);
    assert_eq!(o.wasi.as_ref().unwrap().usage().calls, 3);
    retire(o);
    let init = wasi_call(WasiFunction::FdClose, &[1], true, &[]);
    let mut corpus = wasi_call(WasiFunction::FdWrite, &[1, 0, 1, 8], false, &[]);
    corpus.result = Some(Type::I32);
    let mut o = owner_with(
        &[(1, init), (28, corpus)],
        &[],
        SwiftRunBudget::default(),
        WasiGrants {
            stdout: true,
            ..WasiGrants::default()
        },
        WasiBudget::default(),
    );
    success(&mut o, Request::Initialize);
    for _ in 0..2 {
        assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(8));
    }
    assert!(o.wasi.as_ref().unwrap().stdout().is_empty());
    retire(o);
}

#[test]
fn swift_lifecycle_sl16_stored_errors_wrong_i64_and_terminal_shape_do_not_escape() {
    for mode in [4, 5, 11, 12] {
        let mut o = owner(&[(28, scalar(73))]);
        success(&mut o, Request::Initialize);
        let hook = Hook::set(mode);
        let f = failed(&mut o, Request::Corpus);
        assert_eq!(f.kind, SwiftRunFailureKind::Invariant);
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        drop(hook);
        retire(o);
    }
}

fn zero_argument_call(function: WasiFunction) -> Function {
    let mut body = Vec::new();
    for parameter in function.parameters() {
        match parameter {
            Type::I32 => body.extend([0x41, 0]),
            Type::I64 => body.extend([0x42, 0]),
            _ => panic!("sealed WASI signature changed"),
        }
    }
    body.push(0x10);
    uint(
        WasiFunction::ALL
            .iter()
            .position(|f| *f == function)
            .unwrap() as u32,
        &mut body,
    );
    if function != WasiFunction::ProcExit {
        body.extend([0x24, 0]);
    }
    body.push(0x0b);
    Function::void(&body)
}
#[test]
fn swift_lifecycle_sl17_all_34_actual_descriptors_remain_sealed_and_default_denied() {
    use WasiFunction::*;
    // All args are typed zero. Overlap errno is intentional for argument output
    // pairs; denial occurs before bad memory for denied OS capabilities.
    for function in WasiFunction::ALL {
        let mut o = owner(&[(1, zero_argument_call(function))]);
        if function == ProcExit {
            let f = failed(&mut o, Request::Initialize);
            assert_eq!(f.kind, SwiftRunFailureKind::GuestExit);
            assert_eq!(f.guest_exit, Some(0));
        } else {
            success(&mut o, Request::Initialize);
            let errno = match function {
                ArgsGet | ArgsSizesGet | EnvironSizesGet => 28,
                EnvironGet => 0,
                ClockResGet | ClockTimeGet | RandomGet => 76,
                PollOneoff => 58,
                _ => 8,
            };
            assert_eq!(
                o.state.as_ref().unwrap().globals[0],
                Value::I32(errno),
                "{function:?}"
            );
        }
        assert_eq!(o.wasi.as_ref().unwrap().usage().calls, 1, "{function:?}");
        assert_eq!(observed(&o).host_calls, 1);
        assert_eq!(o.wasi.as_ref().unwrap().usage().random_bytes, 0);
        assert_eq!(o.wasi.as_ref().unwrap().usage().log_bytes, 0);
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl18_cleanup_under_exhausted_fuel_work_and_cancel_uses_no_allowance() {
    for kind in 0..3 {
        let mut o = owner_with(
            &[
                (1, Function::void(&[0x10, 36, 0x0b])),
                (2, Function::void(&[0x10, 37, 0x0b])),
                (3, Function::void(&[0x41, 1, 0x1a, 0x00, 0x0b])),
            ],
            &[],
            SwiftRunBudget {
                instruction_fuel: if kind == 0 { 2 } else { 100_000_000 },
                ..SwiftRunBudget::default()
            },
            WasiGrants::default(),
            WasiBudget::default(),
        );
        if kind == 1 {
            o.control.as_ref().unwrap().cancellation().cancel();
        }
        let old = if kind == 2 {
            let work = observed(&o).execution_work;
            Some(
                o.control
                    .as_mut()
                    .unwrap()
                    .test_replace_execution_work_limit(work + 4),
            )
        } else {
            None
        };
        let (f, stats) = measure_extended(None, || failed(&mut o, Request::Initialize));
        assert_eq!(
            f.kind,
            match kind {
                0 => SwiftRunFailureKind::FuelExhausted,
                1 => SwiftRunFailureKind::Cancelled,
                _ => SwiftRunFailureKind::WorkExhausted,
            }
        );
        let after = observed(&o);
        assert_eq!(after.instructions, f.at_failure.instructions);
        assert_eq!(after.execution_work, f.at_failure.execution_work);
        assert_eq!(after.host_calls, 0);
        assert_eq!(
            after.live.frames.current
                + after.live.controls.current
                + after.live.values.current
                + after.live.active_pins.current,
            0
        );
        if kind == 1 {
            assert_eq!(stats.attempts, 0);
        }
        if let Some(old) = old {
            o.control
                .as_mut()
                .unwrap()
                .test_replace_execution_work_limit(old);
        }
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl20_cold_cache_allocation_refusals_never_publish_ready() {
    // Nonzero locals, instructions and br_table targets exercise three vectors.
    // Keep every reached refusal, rather than deriving ordinals from a dry run.
    for ordinal in 0..3 {
        let mut init = Function::void(&[0x02, 0x40, 0x41, 0, 0x0e, 1, 0, 0, 0x0b, 0x0b]);
        init.locals = vec![Type::I32];
        let mut o = owner(&[(1, init)]);
        let (result, stats) =
            measure_extended(Some(ordinal), || request(&mut o, Request::Initialize));
        assert_eq!(stats.injected_failures, 1, "ordinal {ordinal}");
        match result {
            Completion::Failed {
                failure: Some(f),
                cleanup: GrowthCompletion::Completed(FrameCompletion::Completed),
            } => assert_eq!(f.kind, SwiftRunFailureKind::Allocation),
            _ => panic!("refused cache allocation escaped"),
        }
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        assert_eq!(observed(&o).live.active_pins.current, 0);
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl06_committed_memory_old_refund_retains_actual_authority() {
    let mut foreign = owner(&[]);
    super::super::tests::lifecycle_foreign_old(foreign.state.as_mut().unwrap().buffers[3].take());
    let mut o = owner(&[(1, Function::void(&[0x41, 1, 0x40, 0, 0x1a, 0x0b]))]);
    let state_before = observed(&o).reservations.state.current;
    match request(&mut o, Request::Initialize) {
        Completion::Failed {
            failure: Some(first),
            cleanup:
                GrowthCompletion::Retained {
                    mut phase,
                    mut context,
                    mut growth,
                    storage,
                    preparation,
                },
        } => {
            assert_eq!(first.code, "swift_run_reservation_owner");
            assert_eq!(phase.phase.parts.memory.len(), 585 * PAGE);
            let usage = phase.phase.operation.control.usage(None);
            assert_eq!(usage.live.memory_pages.current, 585);
            assert_eq!(usage.reservations.state.current, state_before + 585 * PAGE);
            assert_eq!(growth.transfer.old.capacity(), 0);
            assert!(growth.transfer.old_ticket.is_some());
            assert_eq!(growth.pages_debited, 0);
            assert!(context
                .memory_ticket
                .as_ref()
                .unwrap()
                .matches_layout(SwiftReservationCategory::State, 585 * PAGE));
            foreign.state.as_mut().unwrap().buffers[3] =
                super::super::tests::lifecycle_restore_old(&mut growth);
            release_growth_pending(&mut phase, &mut context, &mut growth).unwrap();
            assert_eq!(phase.invariant("later_cleanup_fault").code, first.code);
            assert!(matches!(
                complete_growth(phase, context, growth, storage, preparation),
                GrowthCompletion::Completed(FrameCompletion::Completed)
            ));
        }
        _ => panic!("committed growth refund must retain exact phase and old ticket"),
    }
    assert_eq!(o.state.as_ref().unwrap().memory.len(), 585 * PAGE);
    assert_eq!(observed(&o).reservations.state.current, state_before + PAGE);
    assert!(matches!(o.lifecycle, Lifecycle::Terminal));
    assert!(matches!(
        request(&mut o, Request::Initialize),
        Completion::BlockedTerminal
    ));
    retire(o);
    retire(foreign);
}

#[test]
fn swift_lifecycle_sl10_actual_cache_and_local_entry_checkpoints_cancel() {
    use crate::experimental::cache::borrowed::CacheStep;
    use crate::experimental_swift_reactor::cache_tests;
    for step in [CacheStep::Scan, CacheStep::Build] {
        let mut o = owner(&[]);
        cache_tests::lifecycle_cancel_at_step(step);
        let f = failed(&mut o, Request::Initialize);
        cache_tests::lifecycle_reset_hooks();
        assert_eq!(f.kind, SwiftRunFailureKind::Cancelled);
        assert_eq!(f.at_failure.instructions, 0);
        assert_eq!(observed(&o).live.active_pins.current, 0);
        retire(o);
    }
    let mut init = Function::void(&[0x0b]);
    init.locals = vec![Type::I32; 3];
    let mut o = owner(&[(1, init)]);
    frame_tests::hooks(frame_tests::Hooks {
        cancel_local: Some(1),
        ..frame_tests::Hooks::default()
    });
    let f = failed(&mut o, Request::Initialize);
    assert_eq!(f.kind, SwiftRunFailureKind::Cancelled);
    assert_eq!(f.at_failure.instructions, 0);
    assert_eq!(observed(&o).live.values.current, 0);
    retire(o);
}

#[test]
fn swift_lifecycle_sl10_actual_growth_cancel_and_deadline_roll_back_without_publication() {
    // Growth's original sequence: allocation checks0,1; zeroing starts2;
    // final check follows all585-page zero chunks and584-page copy chunks.
    const FINAL: usize = 2 + 585 * PAGE / 4096 + 584 * PAGE / 4096;
    for (cancel, index) in [(true, 0), (true, 2), (true, FINAL), (false, 2)] {
        let mut o = owner_with(
            &[(1, Function::void(&[0x41, 1, 0x40, 0, 0x1a, 0x0b]))],
            &[],
            SwiftRunBudget {
                deadline_ms: 1000,
                ..SwiftRunBudget::default()
            },
            WasiGrants::default(),
            WasiBudget::default(),
        );
        super::super::tests::lifecycle_checkpoint(
            if cancel { Some(index) } else { None },
            if cancel { None } else { Some(index) },
        );
        let before = observed(&o).reservations.state.current;
        let f = failed(&mut o, Request::Initialize);
        super::super::tests::lifecycle_reset_hooks();
        assert_eq!(
            f.kind,
            if cancel {
                SwiftRunFailureKind::Cancelled
            } else {
                SwiftRunFailureKind::Deadline
            }
        );
        assert_eq!(o.state.as_ref().unwrap().memory.len(), 584 * PAGE);
        assert_eq!(observed(&o).live.memory_pages.current, 584);
        assert_eq!(observed(&o).reservations.state.current, before);
        assert!(matches!(o.lifecycle, Lifecycle::Terminal));
        assert_eq!(observed(&o).execution_work, f.at_failure.execution_work);
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl10_wasi_staging_service_commit_and_dispatch_cancellation() {
    for mode in 0..5 {
        let mut o = owner_with(
            &[(1, wasi_call(WasiFunction::RandomGet, &[64, 64], true, &[]))],
            &[],
            SwiftRunBudget::default(),
            WasiGrants {
                secure_random: true,
                ..WasiGrants::default()
            },
            WasiBudget::default(),
        );
        match mode {
            0 => o.wasi.as_mut().unwrap().host_test_dispatch(true, false),
            1 => o.wasi.as_mut().unwrap().host_test_dispatch(false, true),
            2 => o.wasi.as_mut().unwrap().host_test_cancel_at(0),
            3 => o.wasi.as_mut().unwrap().host_test_cancel_at(3),
            _ => o.wasi.as_mut().unwrap().host_test_service(5),
        }
        let f = failed(&mut o, Request::Initialize);
        assert_eq!(
            f.kind,
            if mode == 1 {
                SwiftRunFailureKind::Cancelled
            } else {
                SwiftRunFailureKind::Wasi
            }
        );
        assert_eq!(
            f.wasi_failure,
            if mode == 1 {
                None
            } else {
                Some(crate::experimental_wasi::WasiFailure::Cancelled)
            }
        );
        let memory = &o.state.as_ref().unwrap().memory[64..128];
        if mode == 1 {
            assert_eq!(o.wasi.as_ref().unwrap().usage().random_bytes, 64);
        } else {
            assert!(memory.iter().all(|b| *b == 0));
        }
        let services = o.wasi.as_ref().unwrap().host_test_services();
        assert!(services <= 1);
        let before = normalized(observed(&o));
        assert!(matches!(
            request(&mut o, Request::Initialize),
            Completion::BlockedTerminal
        ));
        assert_eq!(normalized(observed(&o)), before);
        assert_eq!(o.wasi.as_ref().unwrap().host_test_services(), services);
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl17_partial_random_error_and_real_clock_calls_preserve_contract() {
    let mut init = wasi_call(WasiFunction::RandomGet, &[64, 64], false, &[]);
    // Record returned errno in global0; no success inferred from outer Ok.
    init.body.pop();
    init.body.extend([0x24, 0, 0x0b]);
    let mut o = owner_with(
        &[(1, init)],
        &[],
        SwiftRunBudget::default(),
        WasiGrants {
            secure_random: true,
            ..WasiGrants::default()
        },
        WasiBudget::default(),
    );
    o.wasi.as_mut().unwrap().host_test_service(1);
    success(&mut o, Request::Initialize);
    assert_eq!(o.state.as_ref().unwrap().globals[0], Value::I32(29));
    assert!(o.state.as_ref().unwrap().memory[64..128]
        .iter()
        .all(|b| *b == 0));
    assert_eq!(o.wasi.as_ref().unwrap().host_test_services(), 1);
    assert_eq!(o.wasi.as_ref().unwrap().usage().random_bytes, 0);
    retire(o);
    for clock in [0, 1] {
        // clock_time_get(i32 clock,i64 precision,i32 output), drop errno.
        let body = [0x41, clock, 0x42, 0, 0x41, 0xc0, 0, 0x10, 5, 0x1a, 0x0b];
        let mut o = owner_with(
            &[(1, Function::void(&body))],
            &[],
            SwiftRunBudget::default(),
            WasiGrants {
                realtime: true,
                monotonic: true,
                ..WasiGrants::default()
            },
            WasiBudget::default(),
        );
        success(&mut o, Request::Initialize);
        assert_eq!(o.wasi.as_ref().unwrap().usage().calls, 1);
        assert_eq!(o.wasi.as_ref().unwrap().host_test_services(), 1);
        assert!(
            u64::from_le_bytes(o.state.as_ref().unwrap().memory[64..72].try_into().unwrap()) > 0
        );
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl18_consuming_cleanup_preserves_diagnostic_until_final_refund() {
    let mut o = owner(&[(1, Function::void(&[0x00, 0x0b]))]);
    let first = failed(&mut o, Request::Initialize);
    let mut owned = Some(o);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail = returned.take().unwrap().unwrap();
    assert!(owned.is_none());
    let mut final_failure = None;
    let mut final_usage = None;
    tail.complete(
        (owned, returned, first),
        &mut final_failure,
        &mut final_usage,
    );
    let actual = final_failure.unwrap();
    assert_eq!(actual.kind, first.kind);
    assert_eq!(actual.at_failure, first.at_failure);
    let after = final_usage.unwrap();
    assert_eq!(after.reservations.combined.current, 0);
    assert_eq!(after.reservations.live_tickets, 0);
    assert_eq!(after.live.memory_pages.current, 0);
    assert_eq!(after.live.cache_entries.current, 0);
}

#[test]
fn swift_lifecycle_sl18_rejected_deep_pin_cleanup_retains_then_drains_without_work() {
    let mut foreign = owner(&[]);
    let mut o = owner(&[
        (1, Function::void(&[0x10, 36, 0x0b])),
        (2, Function::void(&[0x10, 37, 0x0b])),
        (3, Function::void(&[0x00, 0x0b])),
    ]);
    frame_tests::install_foreign(&mut foreign);
    frame_tests::hooks(frame_tests::Hooks {
        release_mask: 7,
        ..frame_tests::Hooks::default()
    });
    let first = match request(&mut o, Request::Initialize) {
        Completion::Failed {
            failure: Some(first),
            cleanup: GrowthCompletion::Completed(FrameCompletion::Retained(report)),
        } => {
            assert_eq!(first.kind, SwiftRunFailureKind::GuestTrap);
            assert_eq!(first.function, Some(37));
            assert_eq!(report.retained_frames, 3);
            assert_eq!(report.live.active_pins.current, 3);
            assert_eq!(report.first_failure.unwrap().at_failure, first.at_failure);
            first
        }
        _ => panic!("failed actual pin cleanup must retain three original frames"),
    };
    frame_tests::restore_foreign(&mut foreign);
    o.control.as_ref().unwrap().cancellation().cancel();
    let before = observed(&o);
    let (_, stats) = measure_extended(Some(0), || frame_tests::drain_complete(&mut o));
    assert_eq!(stats.attempts, 0);
    let after = observed(&o);
    assert_eq!(after.instructions, before.instructions);
    assert_eq!(after.execution_work, before.execution_work);
    assert_eq!(after.host_calls, before.host_calls);
    assert_eq!(after.live.active_pins.current, 0);
    let actual = o.control.as_mut().unwrap().record_cleanup(None).unwrap();
    assert_eq!(actual.at_failure, first.at_failure);
    assert_eq!(actual.kind, SwiftRunFailureKind::GuestTrap);
    assert!(matches!(
        request(&mut o, Request::Initialize),
        Completion::BlockedTerminal
    ));
    retire(o);
    retire(foreign);
}

#[test]
fn swift_lifecycle_sl19_misuse_has_no_frame_admission_with_zero_combined_room() {
    for initialized in [false, true] {
        let mut o = owner(&[]);
        if initialized {
            success(&mut o, Request::Initialize);
        }
        let before = observed(&o);
        let old = o
            .control
            .as_mut()
            .unwrap()
            .test_replace_combined_limit(before.reservations.combined.current);
        let (reply, stats) = measure_extended(Some(0), || {
            request(
                &mut o,
                if initialized {
                    Request::Initialize
                } else {
                    Request::Corpus
                },
            )
        });
        assert!(matches!(&reply, Completion::Rejected(_)));
        drop(reply);
        assert_eq!(stats.attempts, 0);
        assert_eq!(normalized(observed(&o)), normalized(before));
        o.control.as_mut().unwrap().test_replace_combined_limit(old);
        retire(o);
    }
}

#[test]
fn swift_lifecycle_sl20_warm_growth_allocation_refusal_preserves_committed_memory() {
    let mut o = owner(&[(
        28,
        Function::scalar(&[0x41, 1, 0x40, 0, 0x1a, 0x41, 0, 0x0b], Type::I32),
    )]);
    success(&mut o, Request::Initialize);
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(0));
    let before = observed(&o);
    assert_eq!(o.state.as_ref().unwrap().memory.len(), 585 * PAGE);
    let (result, stats) = measure_extended(Some(0), || request(&mut o, Request::Corpus));
    match result {
        Completion::Failed {
            failure: Some(f),
            cleanup: GrowthCompletion::Completed(FrameCompletion::Completed),
        } => {
            assert_eq!(f.kind, SwiftRunFailureKind::Allocation);
            assert_eq!(f.code, "swift_growth_allocation");
        }
        _ => panic!("growth allocation refusal cannot return successful corpus result"),
    }
    assert_eq!(stats.attempts, 1);
    assert_eq!(stats.injected_failures, 1);
    assert_eq!(stats.last_size, 586 * PAGE);
    assert_eq!(o.state.as_ref().unwrap().memory.len(), 585 * PAGE);
    assert_eq!(observed(&o).live.memory_pages.current, 585);
    assert_eq!(
        observed(&o).reservations.state.current,
        before.reservations.state.current
    );
    assert!(matches!(o.lifecycle, Lifecycle::Terminal));
    retire(o);
}

#[test]
fn full_regression_observe_lifecycle_fixture_work() {
    let mut o = owner_with(
        &state_spec(),
        &[36],
        SwiftRunBudget::default(),
        WasiGrants::default(),
        WasiBudget::default(),
    );
    let start = observed(&o);
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    let initialized = observed(&o);
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(2));
    let first = observed(&o);
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(3));
    let second = observed(&o);
    println!("REGRESSION_LIFECYCLE work={:?} instructions={:?} host_calls={:?} entries={:?} tickets={:?}", [start.cache_work, initialized.cache_work, first.cache_work, second.cache_work], [start.instructions, initialized.instructions, first.instructions, second.instructions], [start.host_calls, initialized.host_calls, first.host_calls, second.host_calls], [start.live.cache_entries.current, initialized.live.cache_entries.current, first.live.cache_entries.current, second.live.cache_entries.current], [start.reservations.live_tickets, initialized.reservations.live_tickets, first.reservations.live_tickets, second.reservations.live_tickets]);
    retire(o);
    let mut o = owner(&[]);
    let start = observed(&o).cache_work;
    success(&mut o, Request::Initialize);
    println!(
        "REGRESSION_EMPTY_INIT start={start} initialized={}",
        observed(&o).cache_work
    );
    retire(o);
}
