//! Independently authored binary fixtures execute the admitted production loop.
use super::super::tests as frame_tests;
use super::*;
use crate::experimental_swift_reactor::{
    allocation_tests::measure_extended, validate_swift_reactor, SwiftValidationBudget,
};
use crate::experimental_wasi::WasiFunction;
use crate::Cancellation;
use std::cell::Cell;
thread_local! {
    pub(super) static PC_OVERFLOW:Cell<bool>=const {Cell::new(false)};
    static CHECK_COUNT:Cell<usize>=const {Cell::new(0)};
    static CANCEL_AT:Cell<Option<usize>>=const {Cell::new(None)};
}
pub(super) fn checkpoint(control: &RuntimeControl) {
    let at = CHECK_COUNT.with(|n| {
        let at = n.get();
        n.set(at + 1);
        at
    });
    if CANCEL_AT.with(Cell::get) == Some(at) {
        control.cancellation().cancel();
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
    (out, starts)
}
fn owner(
    spec: &[(usize, Function)],
    table: &[u32],
    budget: SwiftRunBudget,
) -> (SwiftReactorInstance, Vec<usize>) {
    frame_tests::hooks(frame_tests::Hooks::default());
    PC_OVERFLOW.with(|x| x.set(false));
    CHECK_COUNT.with(|x| x.set(0));
    CANCEL_AT.with(|x| x.set(None));
    let (bytes, starts) = module(spec, table);
    let proof = validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let mut pair = Some(
        RuntimeControl::adopt(proof, budget, Instant::now(), Cancellation::default()).unwrap(),
    );
    let owner = SwiftReactorInstance::construct(
        &mut pair,
        WasiGrants::default(),
        WasiBudget::default(),
        Instant::now(),
        frame_tests::cursor(),
    )
    .unwrap();
    (owner, starts)
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
fn usage(p: &FrameOperationPhase<'_>) -> SwiftRunUsage {
    p.phase
        .operation
        .control
        .usage(Some(p.phase.operation.wasi.usage()))
}
fn execute(
    spec: &[(usize, Function)],
    table: &[u32],
    budget: SwiftRunBudget,
    action: impl for<'a> FnOnce(
        &mut FrameOperationPhase<'a>,
        &mut SwiftGrowthContext<'a>,
        &mut SwiftGrowthStorage,
        &mut FrameOperationStorage<'a>,
        &[usize],
    ),
) {
    let (mut owner, starts) = owner(spec, table, budget);
    let mut preparation = Some(owner.prepare_growth(frame_tests::cursor()));
    let (mut phase, mut context) = preparation.take().unwrap().unwrap();
    phase.enter(34).unwrap();
    let mut pending = SwiftGrowthStorage::empty();
    let mut storage = storage();
    action(
        &mut phase,
        &mut context,
        &mut pending,
        &mut storage,
        &starts,
    );
    PC_OVERFLOW.with(|x| x.set(false));
    CANCEL_AT.with(|x| x.set(None));
    frame_tests::hooks(frame_tests::Hooks::default());
    growth::release_growth_pending(&mut phase, &mut context, &mut pending).unwrap();
    if !phase.phase.parts.frames.is_empty() || phase.cleanup.entry.is_some() {
        let report = phase.drain();
        assert_eq!(report.retained_frames, 0);
        assert!(!report.retained_entry);
        assert!(!report.live_unreconciled);
        storage.drained = Some(report);
    }
    assert!(matches!(
        complete(phase, context, pending, storage, preparation),
        GrowthCompletion::Completed(FrameCompletion::Completed)
    ));
    assert!(!matches!(owner.lifecycle, Lifecycle::Ready));
    frame_tests::retire(owner);
}
fn result(s: &FrameOperationStorage<'_>) -> Option<Value> {
    match s.returned.as_ref().unwrap() {
        Ok(FrameReturn::Outermost(value)) => *value,
        other => panic!("unexpected outcome {other:?}"),
    }
}
fn failure(s: &FrameOperationStorage<'_>) -> SwiftRunFailure {
    *s.returned.as_ref().unwrap().as_ref().unwrap_err()
}
#[test]
fn swift_dispatch_cd01_original_authority() {
    for index in 0..7 {
        let (mut o, _) = owner(&[], &[], SwiftRunBudget::default());
        if index == 6 {
            let ticket = o.state.as_mut().unwrap().execution_header.take();
            let before = o.control.as_ref().unwrap().usage(None);
            assert!(o.prepare_growth(frame_tests::cursor()).is_err());
            assert_eq!(
                o.control.as_ref().unwrap().usage(None).instructions,
                before.instructions
            );
            o.state.as_mut().unwrap().execution_header = ticket;
        } else {
            let ticket = o.state.as_mut().unwrap().buffers[index].take();
            assert!(o.prepare_growth(frame_tests::cursor()).is_err());
            o.state.as_mut().unwrap().buffers[index] = ticket;
        }
        frame_tests::retire(o);
    }
}
#[test]
fn swift_dispatch_cd02_single_prefix() {
    for fuel in [0, 1, 2, 3] {
        execute(
            &[(0, Function::scalar(&[0x41, 7, 0x01, 0x0b], Type::I32))],
            &[],
            SwiftRunBudget {
                instruction_fuel: fuel,
                ..SwiftRunBudget::default()
            },
            |p, c, g, s, starts| {
                let before = usage(p);
                run(p, c, g, s).unwrap();
                let after = usage(p);
                assert_eq!(after.instructions - before.instructions, fuel.min(3));
                assert_eq!(
                    after.instruction_fuel - before.instruction_fuel,
                    fuel.min(3)
                );
                if fuel < 3 {
                    let f = failure(s);
                    assert_eq!(f.kind, SwiftRunFailureKind::FuelExhausted);
                    assert_eq!(
                        f.offset,
                        Some(starts[0] + if fuel == 0 { 0 } else { fuel as usize + 1 })
                    );
                } else {
                    assert_eq!(result(s), Some(Value::I32(7)));
                    assert_eq!(after.execution_work - before.execution_work, 10);
                }
            },
        );
    }
    execute(
        &[(0, Function::void(&[0x01, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            PC_OVERFLOW.with(|x| x.set(true));
            let before = usage(p);
            run(p, c, g, s).unwrap();
            assert_eq!(failure(s).code, "swift_dispatch_pc_overflow");
            assert_eq!(usage(p).instructions - before.instructions, 1);
            assert_eq!(usage(p).execution_work - before.execution_work, 1);
        },
    );
}
#[test]
fn swift_dispatch_cd03_slot_publication() {
    for slot in 0..4 {
        execute(
            &[(0, Function::void(&[0x01, 0x0b]))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                match slot {
                    0 => s.entry = Some(Ok(())),
                    1 => s.returned = Some(Ok(FrameReturn::Outermost(None))),
                    2 => s.controlled = Some(Ok(false)),
                    _ => s.drained = Some(p.drain()),
                };
                let before = usage(p);
                assert!(run(p, c, g, s).is_err());
                assert_eq!(usage(p).instructions, before.instructions);
                assert_eq!(usage(p).execution_work, before.execution_work);
                if slot == 2 {
                    assert_eq!(s.controlled, Some(Ok(false)));
                    s.controlled.take();
                }
            },
        );
    }
}
#[test]
fn swift_dispatch_cd04_direct_defined() {
    let main = Function::scalar(&[0x41, 9, 0x10, 36, 0x0b], Type::I32);
    let callee = Function {
        params: vec![Type::I32],
        result: Some(Type::I32),
        locals: vec![Type::I64, Type::F32],
        body: vec![0x20, 0, 0x41, 1, 0x6a, 0x0b],
    };
    execute(
        &[(0, main), (2, callee)],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            let before = usage(p);
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(10)));
            assert_eq!(usage(p).instructions - before.instructions, 7);
            assert_eq!(usage(p).live.frames.current, 0);
            assert_eq!(usage(p).live.active_pins.current, 0);
        },
    );
}
#[test]
fn swift_dispatch_cd05_recursive_pins() {
    execute(
        &[(0, Function::void(&[0x10, 34, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(failure(s).kind, SwiftRunFailureKind::FrameLimit);
            assert_eq!(p.phase.parts.frames.len(), 64);
            assert_eq!(p.phase.parts.cache.usage().active_pins, 64);
            assert_eq!(usage(p).instructions, 64);
        },
    );
}
#[test]
fn swift_dispatch_cd06_indirect_structure() {
    let main = Function::scalar(&[0x41, 11, 0x41, 0, 0x11, 38, 0, 0x0b], Type::I32);
    let callee = Function {
        params: vec![Type::I32],
        result: Some(Type::I32),
        locals: vec![],
        body: vec![0x20, 0, 0x0b],
    };
    execute(
        &[(0, main), (2, callee.clone()), (3, callee)],
        &[37],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(11)));
        },
    );
}
#[test]
fn swift_dispatch_cd07_indirect_table() {
    for (selector, code) in [
        (-1, "table_out_of_bounds"),
        (46713, "table_out_of_bounds"),
        (0, "indirect_call_null"),
    ] {
        let mut body = vec![0x41];
        if selector == -1 {
            body.push(0x7f);
        } else if selector == 0 {
            body.push(0);
        } else {
            uint(selector as u32, &mut body);
        }
        body.extend([0x11, 34, 0, 0x0b]);
        execute(
            &[(0, Function::void(&body))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(failure(s).code, code);
                assert!(p.phase.parts.values.is_empty());
                assert_eq!(p.phase.parts.frames.len(), 1);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd08_indirect_import() {
    let function = WasiFunction::ArgsSizesGet;
    let index = WasiFunction::ALL
        .iter()
        .position(|f| *f == function)
        .unwrap() as u8;
    for indirect_call in [false, true] {
        let body = if indirect_call {
            vec![0x41, 8, 0x41, 12, 0x41, 0, 0x11, index, 0, 0x0b]
        } else {
            vec![0x41, 8, 0x41, 12, 0x10, index, 0x0b]
        };
        execute(
            &[(0, Function::scalar(&body, Type::I32))],
            &[u32::from(index)],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), Some(Value::I32(0)));
                assert_eq!(usage(p).host_calls, 1);
                assert_eq!(usage(p).live.frames.peak, 1);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd09_entry_completion() {
    execute(
        &[(0, Function::void(&[0x10, 36, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            frame_tests::hooks(frame_tests::Hooks {
                reject_cache_completion: true,
                ..Default::default()
            });
            run(p, c, g, s).unwrap();
            assert!(s.returned.as_ref().unwrap().is_err());
            assert!(p.cleanup.entry.is_none());
            assert_eq!(p.phase.parts.cache.usage().active_pins, 1);
            assert!(p.cleanup.nested_restore.is_some());
        },
    );
}
#[test]
fn swift_dispatch_cd10_function_return() {
    for (ty, constant) in [
        (Type::I32, vec![0x41, 9]),
        (Type::I64, vec![0x42, 9]),
        (Type::F32, vec![0x43, 0, 0, 0, 0x80]),
        (Type::F64, vec![0x44, 0, 0, 0, 0, 0, 0, 0, 0x80]),
    ] {
        for explicit in [false, true] {
            let mut body = constant.clone();
            if explicit {
                body.push(0x0f);
            }
            body.push(0x0b);
            execute(
                &[
                    (0, Function::scalar(&[0x10, 36, 0x0b], ty)),
                    (2, Function::scalar(&body, ty)),
                ],
                &[],
                SwiftRunBudget::default(),
                |p, c, g, s, _| {
                    run(p, c, g, s).unwrap();
                    assert_eq!(result(s).unwrap().ty(), ty);
                    assert_eq!(usage(p).live.values.current, 0);
                    assert!(p.phase.parts.frames.is_empty());
                },
            );
        }
    }
}
#[test]
fn swift_dispatch_cd11_return_failure() {
    execute(
        &[(0, Function::scalar(&[0x41, 7, 0x0b], Type::I32))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            let base = usage(p).execution_work;
            let previous = p
                .phase
                .operation
                .control
                .test_replace_execution_work_limit(base + 8);
            run(p, c, g, s).unwrap();
            assert_eq!(failure(s).kind, SwiftRunFailureKind::WorkExhausted);
            assert!(p.phase.parts.values.is_empty());
            p.phase
                .operation
                .control
                .test_replace_execution_work_limit(previous);
        },
    );
}
#[test]
fn swift_dispatch_cd12_scalar_arms() {
    for (condition, expected) in [(0, 2), (1, 1)] {
        let body = [
            0x01, 0x41, 55, 0x1a, 0x41, 1, 0x41, 2, 0x41, condition, 0x1b, 0x0b,
        ];
        execute(
            &[(0, Function::scalar(&body, Type::I32))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), Some(Value::I32(expected)));
            },
        );
    }
    execute(
        &[(0, Function::void(&[0x00, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, starts| {
            run(p, c, g, s).unwrap();
            assert_eq!(failure(s).code, "unreachable");
            assert_eq!(failure(s).offset, Some(starts[0]));
        },
    );
}
#[test]
fn swift_dispatch_cd13_local_arms() {
    let f = Function {
        params: vec![],
        result: Some(Type::I32),
        locals: vec![Type::I32],
        body: vec![0x41, 17, 0x21, 0, 0x20, 0, 0x22, 0, 0x0b],
    };
    execute(
        &[(0, f)],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(17)));
        },
    );
}
#[test]
fn swift_dispatch_cd14_global_arms() {
    execute(
        &[(
            0,
            Function::scalar(&[0x41, 17, 0x24, 0, 0x23, 0, 0x0b], Type::I32),
        )],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(17)));
            assert_eq!(p.phase.parts.globals[0], Value::I32(17));
        },
    );
}
#[test]
fn swift_dispatch_cd15_all_control() {
    for selector in [0, 1, 2] {
        let body = [
            0x02, 0x7f, 0x41, 9, 0x41, selector, 0x0e, 1, 0, 0, 0x0b, 0x0b,
        ];
        execute(
            &[(0, Function::scalar(&body, Type::I32))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), Some(Value::I32(9)));
            },
        );
    }
    for condition in [0, 1] {
        let body = [
            0x41, condition, 0x04, 0x7f, 0x41, 1, 0x05, 0x41, 2, 0x0b, 0x0b,
        ];
        execute(
            &[(0, Function::scalar(&body, Type::I32))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(
                    result(s),
                    Some(Value::I32(if condition == 0 { 2 } else { 1 }))
                );
            },
        );
    }
}
#[test]
fn swift_dispatch_cd16_numeric_memory() {
    execute(
        &[(
            0,
            Function::scalar(
                &[
                    0x41, 0, 0x41, 31, 0x36, 2, 0, 0x41, 0, 0x28, 2, 0, 0x41, 1, 0x6a, 0x0b,
                ],
                Type::I32,
            ),
        )],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(32)));
            assert_eq!(&p.phase.parts.memory[..4], &31i32.to_le_bytes());
        },
    );
    execute(
        &[(
            0,
            Function::scalar(&[0x41, 1, 0x41, 0, 0x6d, 0x0b], Type::I32),
        )],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(failure(s).kind, SwiftRunFailureKind::GuestTrap);
        },
    );
}
#[test]
fn swift_dispatch_cd17_bulk_growth() {
    execute(
        &[(
            0,
            Function::scalar(
                &[
                    0x41, 0, 0x41, 17, 0x41, 8, 0xfc, 11, 0, 0x41, 2, 0x41, 0, 0x41, 6, 0xfc, 10,
                    0, 0, 0x41, 0, 0x40, 0, 0x1a, 0x3f, 0, 0x0b,
                ],
                Type::I32,
            ),
        )],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(584)));
            assert_eq!(&p.phase.parts.memory[..8], &[17; 8]);
        },
    );
}
#[test]
fn swift_dispatch_cd18_growth_completion() {
    execute(
        &[(0, Function::scalar(&[0x41, 1, 0x40, 0, 0x0b], Type::I32))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(584)));
            assert_eq!(p.phase.parts.memory.len(), 585 * PAGE);
            assert!(c
                .memory_ticket
                .as_ref()
                .unwrap()
                .matches_layout(SwiftReservationCategory::State, 585 * PAGE));
            assert!(g.transfer.ticket.is_none());
            assert!(g.transfer.old_ticket.is_none());
        },
    );
}
#[test]
fn swift_dispatch_cd19_host_outcomes() {
    let index = WasiFunction::ALL
        .iter()
        .position(|f| *f == WasiFunction::ProcExit)
        .unwrap() as u8;
    for exit in [0, 7] {
        execute(
            &[(0, Function::void(&[0x41, exit, 0x10, index, 0x0b]))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(failure(s).kind, SwiftRunFailureKind::GuestExit);
                assert_eq!(failure(s).guest_exit, Some(u32::from(exit)));
                assert_eq!(usage(p).host_calls, 1);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd20_first_cause() {
    execute(
        &[(0, Function::void(&[0x00, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            let first = failure(s);
            p.phase.operation.control.cancellation().cancel();
            let second = p.invariant("later_failure");
            assert_eq!(first.code, second.code);
            assert_eq!(first.at_failure, second.at_failure);
        },
    );
}
#[test]
fn swift_dispatch_cd21_terminal_drain() {
    execute(
        &[
            (0, Function::void(&[0x10, 36, 0x0b])),
            (2, Function::void(&[0x10, 37, 0x0b])),
            (3, Function::void(&[0x00, 0x0b])),
        ],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(p.phase.parts.frames.len(), 3);
            let first = failure(s);
            let report = p.drain();
            assert_eq!(report.retained_frames, 0);
            assert_eq!(report.first_failure.unwrap().code, first.code);
            assert_eq!(p.phase.parts.cache.usage().active_pins, 0);
            s.drained = Some(report);
        },
    );
}
#[test]
fn swift_dispatch_cd22_allocation_accounting() {
    execute(
        &[
            (0, Function::scalar(&[0x41, 3, 0x10, 36, 0x0b], Type::I32)),
            (
                2,
                Function {
                    params: vec![Type::I32],
                    result: Some(Type::I32),
                    locals: vec![],
                    body: vec![0x20, 0, 0x41, 4, 0x6a, 0x0b],
                },
            ),
        ],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            let mut warm = p.acquire_pin(36);
            assert!(warm.failure.is_none());
            assert!(p.release(warm.pin.take().unwrap(), 36).is_ok());
            let (_, stats) = measure_extended(Some(0), || run(p, c, g, s).unwrap());
            assert_eq!(stats.attempts, 0);
            assert_eq!(result(s), Some(Value::I32(7)));
            println!(
                "CD22_WARM attempts={} alloc={} realloc={} frame={} header={} ticketsMax={}",
                stats.attempts,
                stats.allocations,
                stats.reallocations,
                FRAME_OPERATION_BYTES.unwrap(),
                execution_header_bytes().unwrap(),
                MAX_RESERVATION_TICKETS
            );
        },
    );
}
#[test]
fn swift_dispatch_cd23_frozen_regression() {
    assert_eq!(MAX_RESERVATION_TICKETS, 86);
    assert_eq!(SwiftRunBudget::default().state_bytes, 128 * 1024 * 1024);
    assert_eq!(SwiftRunBudget::default().combined_bytes, 256 * 1024 * 1024);
    execute(
        &[(0, Function::void(&[0x01, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), None);
        },
    );
}
#[test]
fn swift_dispatch_cd24_meaningful_program() {
    let index = WasiFunction::ALL
        .iter()
        .position(|f| *f == WasiFunction::ArgsSizesGet)
        .unwrap() as u8;
    let body = vec![
        0x41, 0, 0x41, 10, 0x10, 36, 0x22, 0, 0x36, 2, 0, 0x41, 1, 0x40, 0, 0x1a, 0x20, 0, 0x41,
        24, 0x10, index, 0x04, 0x40, 0x00, 0x05, 0x01, 0x0b, 0x41, 0, 0x28, 2, 0, 0x0b,
    ];
    let main = Function {
        params: vec![],
        result: Some(Type::I32),
        locals: vec![Type::I32],
        body,
    };
    let callee = Function {
        params: vec![Type::I32],
        result: Some(Type::I32),
        locals: vec![],
        body: vec![0x20, 0, 0x41, 2, 0x6c, 0x0b],
    };
    execute(
        &[(0, main), (2, callee)],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            let before = usage(p);
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(20)));
            assert_eq!(&p.phase.parts.memory[..4], &20i32.to_le_bytes());
            assert_eq!(&p.phase.parts.memory[20..28], &[1, 0, 0, 0, 6, 0, 0, 0]);
            assert_eq!(p.phase.parts.memory.len(), 585 * PAGE);
            assert_eq!(usage(p).host_calls, 1);
            assert_eq!(usage(p).instructions - before.instructions, 21);
            assert_eq!(usage(p).live.active_pins.current, 0);
            println!("CD24_TRACE diagnosticUnqualified=true result=20 memoryI32=20 argcWriteAt=20 pages=585 imports=34 table=46713 instructions={} hostCalls=1 pins=0",usage(p).instructions-before.instructions);
        },
    );
}
#[test]
fn swift_dispatch_cd01_missing_owner_preflight() {
    for index in 0..3 {
        let (mut o, _) = owner(&[], &[], SwiftRunBudget::default());
        let before = o.control.as_ref().unwrap().usage(None).reservations;
        let code = match index {
            0 => {
                let saved = o.wasi.take();
                let failure = o.prepare_growth(frame_tests::cursor()).err().unwrap();
                o.wasi = saved;
                failure.code
            }
            1 => {
                let saved = o.cache.take();
                let failure = o.prepare_growth(frame_tests::cursor()).err().unwrap();
                o.cache = saved;
                failure.code
            }
            _ => {
                let saved = o.state.take();
                let failure = o.prepare_growth(frame_tests::cursor()).err().unwrap();
                o.state = saved;
                failure.code
            }
        };
        assert_eq!(
            code,
            [
                "swift_dispatch_wasi_missing",
                "swift_dispatch_cache_missing",
                "swift_dispatch_state_missing"
            ][index]
        );
        assert_eq!(o.control.as_ref().unwrap().usage(None).reservations, before);
        assert!(o.state.as_ref().unwrap().frame_cleanup.is_empty());
        frame_tests::retire(o);
    }
}
#[test]
fn swift_dispatch_cd01_missing_control_outside_admitted_construction() {
    let (mut o, _) = owner(&[], &[], SwiftRunBudget::default());
    let control = o.control.take();
    assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let _ = o.prepare_growth(frame_tests::cursor());
    }))
    .is_err());
    o.control = control;
    frame_tests::retire(o);
    println!("CD01_BOUNDARY missing control is private corruption outside admitted construction; panic is not admitted rejection behavior");
}
#[test]
fn swift_dispatch_cd02_work_reject_before_pc() {
    execute(
        &[(0, Function::void(&[0x01, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            let before = usage(p);
            let old = p
                .phase
                .operation
                .control
                .test_replace_execution_work_limit(before.execution_work);
            run(p, c, g, s).unwrap();
            assert_eq!(failure(s).kind, SwiftRunFailureKind::WorkExhausted);
            assert_eq!(usage(p).instructions - before.instructions, 1);
            assert_eq!(p.phase.parts.frames[0].pc, 0);
            p.phase
                .operation
                .control
                .test_replace_execution_work_limit(old);
        },
    );
}
#[test]
fn swift_dispatch_cd03_preparation_preserved() {
    execute(
        &[(0, Function::void(&[0x01, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            let first = p.invariant("dispatch_preparation_prior");
            s.preparation = Some(Err(first));
            let before = usage(p);
            let failure = run(p, c, g, s).unwrap_err();
            assert_eq!(failure.code, first.code);
            assert!(matches!(s.preparation, Some(Err(_))));
            assert_eq!(usage(p).instructions, before.instructions);
        },
    );
}
#[test]
fn swift_dispatch_cd02_prefix_call_return_grow() {
    for (body, fuel, expected_pc, expected_values) in [
        (vec![0x10, 36, 0x0b], 0, 0, 0),
        (vec![0x0f, 0x0b], 0, 0, 0),
        (vec![0x41, 0, 0x11, 34, 0, 0x0b], 1, 1, 1),
        (vec![0x41, 0, 0x40, 0, 0x1a, 0x0b], 1, 1, 1),
    ] {
        execute(
            &[(0, Function::void(&body))],
            &[36],
            SwiftRunBudget {
                instruction_fuel: fuel,
                ..SwiftRunBudget::default()
            },
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(failure(s).kind, SwiftRunFailureKind::FuelExhausted);
                assert_eq!(p.phase.parts.frames.len(), 1);
                assert_eq!(p.phase.parts.frames[0].pc, expected_pc);
                assert_eq!(p.phase.parts.values.len(), expected_values);
                assert_eq!(usage(p).host_calls, 0);
                assert_eq!(p.phase.parts.memory.len(), 584 * PAGE);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd04_mixed_parameters_and_rejected_argument_regions() {
    let callee = Function {
        params: vec![Type::I32, Type::I64, Type::F32, Type::F64],
        result: Some(Type::I32),
        locals: vec![Type::I32, Type::I64],
        body: vec![0x20, 0, 0x0b],
    };
    let body = [
        0x41, 19, 0x42, 7, 0x43, 0, 0, 0, 0x80, 0x44, 0, 0, 0, 0, 0, 0, 0, 0x80, 0x10, 36, 0x0b,
    ];
    execute(
        &[(0, Function::scalar(&body, Type::I32)), (2, callee)],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(19)));
            assert_eq!(usage(p).live.values.peak, 7);
        },
    );
    for wrong in [false, true] {
        let callee = Function {
            params: vec![Type::I32],
            result: None,
            locals: vec![],
            body: vec![0x0b],
        };
        execute(
            &[(0, Function::void(&[0x41, 1, 0x10, 36, 0x0b])), (2, callee)],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                p.phase.parts.frames[0].pc = 1;
                if wrong {
                    p.phase.push_value(Value::I64(7)).unwrap();
                }
                run(p, c, g, s).unwrap();
                assert_eq!(
                    failure(s).code,
                    if wrong {
                        "swift_frame_parameter_type"
                    } else {
                        "swift_dispatch_parameters"
                    }
                );
                assert_eq!(p.phase.parts.frames.len(), 1);
                assert_eq!(p.phase.parts.cache.usage().active_pins, 1);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd05_mutual_recursion_and_narrow_limit() {
    for limit in [1, 2, 63, 64] {
        execute(
            &[
                (0, Function::void(&[0x10, 36, 0x0b])),
                (2, Function::void(&[0x10, 34, 0x0b])),
            ],
            &[],
            SwiftRunBudget {
                frames: limit,
                ..SwiftRunBudget::default()
            },
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(failure(s).kind, SwiftRunFailureKind::FrameLimit);
                assert_eq!(p.phase.parts.frames.len(), limit);
                assert_eq!(p.phase.parts.cache.usage().active_pins, limit);
                assert_eq!(usage(p).live.frames.peak, limit);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd06_signature_mismatch_scalar_and_result() {
    for (actual_param, actual_result) in [
        (Type::I64, Some(Type::I32)),
        (Type::F32, Some(Type::I32)),
        (Type::F64, Some(Type::I32)),
        (Type::I32, None),
        (Type::I32, Some(Type::I64)),
    ] {
        let expected = Function {
            params: vec![Type::I32],
            result: Some(Type::I32),
            locals: vec![],
            body: vec![0x20, 0, 0x0b],
        };
        let body = if actual_result == Some(Type::I64) {
            vec![0x42, 0, 0x0b]
        } else if actual_result.is_some() {
            vec![0x41, 0, 0x0b]
        } else {
            vec![0x0b]
        };
        let actual = Function {
            params: vec![actual_param],
            result: actual_result,
            locals: vec![],
            body,
        };
        execute(
            &[
                (
                    0,
                    Function::scalar(&[0x41, 1, 0x41, 0, 0x11, 38, 0, 0x0b], Type::I32),
                ),
                (2, expected),
                (3, actual),
            ],
            &[37],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(failure(s).code, "indirect_call_type_mismatch");
                assert_eq!(usage(p).live.frames.peak, 1);
                assert_eq!(usage(p).host_calls, 0);
                assert_eq!(p.phase.parts.values.as_slice(), &[Value::I32(1)]);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd07_invalid_table_descriptor_and_selector_shapes() {
    for fault in 0..3 {
        execute(
            &[(0, Function::void(&[0x41, 0, 0x11, 34, 0, 0x0b]))],
            &[36],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                if fault == 0 {
                    p.phase.parts.table[0] = Some(u32::MAX);
                } else {
                    p.phase.parts.frames[0].pc = 1;
                    if fault == 1 {
                        p.phase.push_value(Value::I64(0)).unwrap();
                    }
                }
                run(p, c, g, s).unwrap();
                assert_eq!(
                    failure(s).code,
                    match fault {
                        0 => "swift_dispatch_actual_type",
                        1 => "swift_dispatch_i32",
                        _ => "swift_execution_value_invariant",
                    }
                );
                assert_eq!(p.phase.parts.frames.len(), 1);
                assert_eq!(usage(p).host_calls, 0);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd08_import_rejects_before_host() {
    let index = WasiFunction::ALL
        .iter()
        .position(|f| *f == WasiFunction::ArgsSizesGet)
        .unwrap() as u32;
    execute(
        &[(0, Function::void(&[0x41, 0, 0x11, 34, 0, 0x0b]))],
        &[index],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(failure(s).code, "indirect_call_type_mismatch");
            assert_eq!(usage(p).host_calls, 0);
            assert_eq!(p.phase.parts.frames.len(), 1);
        },
    );
}
#[test]
fn swift_dispatch_cd09_local_debits_and_cancel() {
    for fault in 0..4 {
        let callee = Function {
            params: vec![],
            result: None,
            locals: vec![Type::I32, Type::I64],
            body: vec![0x0b],
        };
        execute(
            &[(0, Function::void(&[0x10, 36, 0x0b])), (2, callee)],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                frame_tests::hooks(if fault == 3 {
                    frame_tests::Hooks {
                        cancel_local: Some(1),
                        ..Default::default()
                    }
                } else {
                    frame_tests::Hooks {
                        predebit_resource: Some(fault),
                        predebit_ordinal: 0,
                        ..Default::default()
                    }
                });
                run(p, c, g, s).unwrap();
                assert!(s.returned.as_ref().unwrap().is_err());
                assert_eq!(p.phase.parts.frames.len(), 1);
                assert!(p.cleanup.entry.is_none());
            },
        );
    }
}
#[test]
fn swift_dispatch_cd10_missing_and_wrong_result() {
    for wrong in [false, true] {
        execute(
            &[(0, Function::scalar(&[0x41, 1, 0x0b], Type::I32))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                p.phase.parts.frames[0].pc = 1;
                if wrong {
                    p.phase.push_value(Value::I64(1)).unwrap();
                }
                run(p, c, g, s).unwrap();
                assert!(s.returned.as_ref().unwrap().is_err());
                assert_eq!(p.phase.parts.frames.len(), 1);
                if wrong {
                    assert_eq!(failure(s).code, "swift_dispatch_result_type");
                }
            },
        );
    }
}
#[test]
fn swift_dispatch_cd13_local_guards_use_declarations() {
    for fault in 0..3 {
        let main = Function {
            params: vec![],
            result: Some(Type::I32),
            locals: vec![Type::I32],
            body: if fault == 0 {
                vec![0x20, 0, 0x0b]
            } else {
                vec![0x41, 1, 0x22, 0, 0x0b]
            },
        };
        execute(
            &[(0, main)],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                if fault == 0 {
                    p.phase.parts.values[0] = Value::I64(1);
                } else {
                    p.phase.parts.frames[0].pc = 1;
                    if fault == 2 {
                        p.phase.push_value(Value::I64(1)).unwrap();
                    }
                }
                run(p, c, g, s).unwrap();
                assert_eq!(
                    failure(s).code,
                    match fault {
                        0 => "swift_dispatch_local_value_type",
                        1 => "swift_dispatch_tee_floor",
                        _ => "swift_dispatch_local_write_type",
                    }
                );
            },
        );
    }
}
#[test]
fn swift_dispatch_cd14_missing_and_wrong_global_slot() {
    for wrong in [false, true] {
        execute(
            &[(0, Function::scalar(&[0x23, 3, 0x0b], Type::F64))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                let saved = if wrong {
                    Some(std::mem::replace(
                        &mut p.phase.parts.globals[3],
                        Value::I32(9),
                    ))
                } else {
                    p.phase.parts.globals.pop()
                };
                run(p, c, g, s).unwrap();
                assert_eq!(
                    failure(s).code,
                    if wrong {
                        "swift_dispatch_global_read_type"
                    } else {
                        "swift_dispatch_global_slot"
                    }
                );
                if wrong {
                    p.phase.parts.globals[3] = saved.unwrap();
                } else {
                    p.phase.parts.globals.push(saved.unwrap());
                }
            },
        );
    }
}
#[test]
fn swift_dispatch_cd15_loop_and_branches() {
    let counter = Function {
        params: vec![],
        result: Some(Type::I32),
        locals: vec![Type::I32],
        body: vec![
            0x41, 3, 0x21, 0, 0x03, 0x40, 0x20, 0, 0x41, 1, 0x6b, 0x22, 0, 0x0d, 0, 0x0b, 0x20, 0,
            0x0b,
        ],
    };
    execute(
        &[(0, counter)],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(0)));
        },
    );
    for conditional in [false, true] {
        let body = if conditional {
            vec![0x02, 0x7f, 0x41, 7, 0x41, 1, 0x0d, 0, 0x0b, 0x0b]
        } else {
            vec![0x02, 0x7f, 0x41, 7, 0x0c, 0, 0x0b, 0x0b]
        };
        execute(
            &[(0, Function::scalar(&body, Type::I32))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), Some(Value::I32(7)));
            },
        );
    }
}
#[test]
fn swift_dispatch_cd16_float_bits_and_saturation() {
    for (ty, body, expected) in [
        (
            Type::F32,
            vec![0x43, 0, 0, 0, 0x80, 0x0b],
            Value::F32(0x80000000),
        ),
        (
            Type::F64,
            vec![0x44, 0, 0, 0, 0, 0, 0, 0, 0x80, 0x0b],
            Value::F64(0x8000000000000000),
        ),
        (
            Type::I32,
            vec![0x43, 0, 0, 0xc0, 0x7f, 0xfc, 0, 0x0b],
            Value::I32(0),
        ),
    ] {
        execute(
            &[(0, Function::scalar(&body, ty))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), Some(expected));
            },
        );
    }
}
#[test]
fn swift_dispatch_cd17_maximum_denial() {
    execute(
        &[(0, Function::scalar(&[0x41, 1, 0x40, 0, 0x0b], Type::I32))],
        &[],
        SwiftRunBudget {
            memory_pages: 584,
            ..SwiftRunBudget::default()
        },
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(result(s), Some(Value::I32(-1)));
            assert_eq!(p.phase.parts.memory.len(), 584 * PAGE);
            assert!(g.transfer.ticket.is_none());
        },
    );
}
#[test]
fn swift_dispatch_cd20_cancel_before_fetch_and_scan() {
    for at in [0, 1, 2] {
        execute(
            &[(0, Function::void(&[0x10, 36, 0x0b]))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                CHECK_COUNT.with(|x| x.set(0));
                CANCEL_AT.with(|x| x.set(Some(at)));
                run(p, c, g, s).unwrap();
                assert_eq!(failure(s).kind, SwiftRunFailureKind::Cancelled);
                assert_eq!(usage(p).host_calls, 0);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd21_rejected_release_one_attempt_and_reacquire() {
    let (mut own, _) = owner(
        &[
            (0, Function::void(&[0x10, 36, 0x0b])),
            (2, Function::void(&[0x10, 37, 0x0b])),
            (3, Function::void(&[0x00, 0x0b])),
        ],
        &[],
        SwiftRunBudget::default(),
    );
    let (mut foreign, _) = owner(&[], &[], SwiftRunBudget::default());
    frame_tests::install_foreign(&mut foreign);
    let mut prep = Some(own.prepare_growth(frame_tests::cursor()));
    let (mut p, mut c) = prep.take().unwrap().unwrap();
    p.enter(34).unwrap();
    let mut g = SwiftGrowthStorage::empty();
    let mut s = storage();
    run(&mut p, &mut c, &mut g, &mut s).unwrap();
    let first = failure(&s);
    frame_tests::hooks(frame_tests::Hooks {
        release_mask: 7,
        ..Default::default()
    });
    let report = p.drain();
    assert_eq!(report.retained_frames, 3);
    assert_eq!(p.drain().retained_frames, 3);
    s.drained = Some(report);
    frame_tests::hooks(Default::default());
    growth::release_growth_pending(&mut p, &mut c, &mut g).unwrap();
    assert!(matches!(
        complete(p, c, g, s, prep),
        GrowthCompletion::Completed(FrameCompletion::Retained(_))
    ));
    assert_eq!(report.first_failure.unwrap().code, first.code);
    frame_tests::drain_complete(&mut own);
    frame_tests::restore_foreign(&mut foreign);
    frame_tests::retire(own);
    frame_tests::retire(foreign);
}
#[test]
fn swift_dispatch_cd16_all_scalar_memory_shapes() {
    for opcode in 0x28..=0x35 {
        let expected = match opcode {
            0x28 | 0x2c | 0x2e => Value::I32(-1),
            0x2d => Value::I32(255),
            0x2f => Value::I32(65535),
            0x29 | 0x30 | 0x32 | 0x34 => Value::I64(-1),
            0x31 => Value::I64(255),
            0x33 => Value::I64(65535),
            0x35 => Value::I64(i64::from(u32::MAX)),
            0x2a => Value::F32(u32::MAX),
            0x2b => Value::F64(u64::MAX),
            _ => unreachable!(),
        };
        execute(
            &[(
                0,
                Function::scalar(&[0x41, 1, opcode, 0, 0, 0x0b], expected.ty()),
            )],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                p.phase.parts.memory[1..9].fill(255);
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), Some(expected));
            },
        );
    }
    for opcode in 0x36..=0x3e {
        let (mut constant, width) = match opcode {
            0x36 => (vec![0x41, 0x7f], 4),
            0x37 => (vec![0x42, 0x7f], 8),
            0x38 => (vec![0x43, 255, 255, 255, 255], 4),
            0x39 => (vec![0x44, 255, 255, 255, 255, 255, 255, 255, 255], 8),
            0x3a => (vec![0x41, 0x7f], 1),
            0x3b => (vec![0x41, 0x7f], 2),
            0x3c => (vec![0x42, 0x7f], 1),
            0x3d => (vec![0x42, 0x7f], 2),
            0x3e => (vec![0x42, 0x7f], 4),
            _ => unreachable!(),
        };
        let mut body = vec![0x41, 1];
        body.append(&mut constant);
        body.extend([opcode, 0, 0, 0x0b]);
        execute(
            &[(0, Function::void(&body))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), None);
                assert_eq!(p.phase.parts.memory[0], 0);
                assert_eq!(&p.phase.parts.memory[1..1 + width], &[255; 8][..width]);
                assert_eq!(p.phase.parts.memory[1 + width], 0);
            },
        );
    }
    for opcode in 0..8 {
        let input = if [0, 1, 4, 5].contains(&opcode) {
            vec![0x43, 0, 0, 0xc0, 0x7f]
        } else {
            vec![0x44, 0, 0, 0, 0, 0, 0, 0xf8, 0x7f]
        };
        let ty = if opcode < 4 { Type::I32 } else { Type::I64 };
        let mut body = input;
        body.extend([0xfc, opcode, 0x0b]);
        execute(
            &[(0, Function::scalar(&body, ty))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(
                    result(s),
                    Some(if ty == Type::I32 {
                        Value::I32(0)
                    } else {
                        Value::I64(0)
                    })
                );
            },
        );
    }
}
#[test]
fn swift_dispatch_cd12_select_invalid_shapes_preserve_operands() {
    for fault in 0..3 {
        execute(
            &[(
                0,
                Function::scalar(&[0x41, 1, 0x41, 2, 0x41, 0, 0x1b, 0x0b], Type::I32),
            )],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                p.phase.parts.frames[0].pc = 3;
                p.phase.push_value(Value::I32(1)).unwrap();
                p.phase
                    .push_value(if fault == 1 {
                        Value::I64(2)
                    } else {
                        Value::I32(2)
                    })
                    .unwrap();
                if fault != 0 {
                    p.phase
                        .push_value(if fault == 2 {
                            Value::I64(0)
                        } else {
                            Value::I32(0)
                        })
                        .unwrap();
                }
                let values = p.phase.parts.values.len();
                run(p, c, g, s).unwrap();
                assert_eq!(
                    failure(s).code,
                    if fault == 0 {
                        "swift_dispatch_select_count"
                    } else {
                        "swift_dispatch_select_type"
                    }
                );
                assert_eq!(p.phase.parts.values.len(), values);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd18_old_refund_retains_committed_authority() {
    let (mut foreign, _) = owner(&[], &[], SwiftRunBudget::default());
    execute(
        &[(0, Function::scalar(&[0x41, 1, 0x40, 0, 0x0b], Type::I32))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, starts| {
            let before = usage(p);
            let dispatched = {
                let mut guard = growth::dispatch_old_refund(&mut foreign, g);
                run(p, c, guard.growth(), s)
            };
            dispatched.unwrap();
            let first = failure(s);
            assert_eq!(first.code, "swift_run_reservation_owner");
            assert_eq!(first.offset, Some(starts[0] + 2));
            assert_eq!(p.phase.parts.memory.len(), 585 * PAGE);
            assert_eq!(usage(p).live.memory_pages.current, 585);
            assert!(g.transfer.old_ticket.is_some());
            assert_eq!(g.transfer.old.capacity(), 0);
            assert_eq!(g.pages_debited, 0);
            assert!(c
                .memory_ticket
                .as_ref()
                .unwrap()
                .matches_layout(SwiftReservationCategory::State, 585 * PAGE));
            assert_eq!(
                usage(p).reservations.state.current,
                before.reservations.state.current + 585 * PAGE
            );
            growth::release_growth_pending(p, c, g).unwrap();
            assert!(g.transfer.old_ticket.is_none());
            assert_eq!(
                usage(p).reservations.state.current,
                before.reservations.state.current + PAGE
            );
            assert_eq!(p.invariant("after_old_refund").code, first.code);
        },
    );
    frame_tests::retire(foreign);
}
#[test]
fn swift_dispatch_cd18_pending_wrapper_blocks_completion() {
    let (mut own, _) = owner(
        &[(0, Function::void(&[0x01, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
    );
    let mut preparation = Some(own.prepare_growth(frame_tests::cursor()));
    let (mut p, c) = preparation.take().unwrap().unwrap();
    p.enter(34).unwrap();
    let mut g = SwiftGrowthStorage::empty();
    let s = storage();
    g.transfer.old.try_reserve_exact(1).unwrap();
    let before = usage(&p).reservations;
    let retained = complete(p, c, g, s, preparation);
    match retained {
        GrowthCompletion::Retained {
            mut phase,
            mut context,
            mut growth,
            mut storage,
            preparation,
        } => {
            assert_eq!(usage(&phase).reservations, before);
            assert_eq!(phase.phase.parts.frames.len(), 1);
            growth::release_growth_pending(&mut phase, &mut context, &mut growth).unwrap();
            storage.drained = Some(phase.drain());
            assert!(matches!(
                complete(phase, context, growth, storage, preparation),
                GrowthCompletion::Completed(FrameCompletion::Completed)
            ));
        }
        _ => panic!("pending growth wrapper discarded"),
    };
    frame_tests::retire(own);
}
#[test]
fn swift_dispatch_cd17_growth_rejects_actual_state_combined_and_cancellation() {
    for dimension in 0..2 {
        execute(
            &[(0, Function::scalar(&[0x41, 1, 0x40, 0, 0x0b], Type::I32))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                let before = usage(p);
                let old = if dimension == 0 {
                    p.phase
                        .operation
                        .control
                        .test_replace_state_limit(before.reservations.state.current)
                } else {
                    p.phase
                        .operation
                        .control
                        .test_replace_combined_limit(before.reservations.combined.current)
                };
                run(p, c, g, s).unwrap();
                assert!(matches!(
                    failure(s).kind,
                    SwiftRunFailureKind::CategoryExhausted | SwiftRunFailureKind::CombinedExhausted
                ));
                assert_eq!(p.phase.parts.memory.len(), 584 * PAGE);
                assert_eq!(
                    usage(p).reservations.state.current,
                    before.reservations.state.current
                );
                assert!(g.transfer.ticket.is_none());
                if dimension == 0 {
                    p.phase.operation.control.test_replace_state_limit(old);
                } else {
                    p.phase.operation.control.test_replace_combined_limit(old);
                }
            },
        );
    }
    // Existing growth checkpoint sequence: pre-allocation, post-capacity, zero
    // chunks, copy chunks, final completion. These fixed ordinals enter each region.
    for at in [2, 2 + 585 * PAGE / 4096, 2 + (585 + 584) * PAGE / 4096] {
        execute(
            &[(0, Function::scalar(&[0x41, 1, 0x40, 0, 0x0b], Type::I32))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                let before = usage(p);
                {
                    let _guard = growth::dispatch_growth_check(at, false);
                    run(p, c, g, s).unwrap();
                }
                assert_eq!(failure(s).kind, SwiftRunFailureKind::Cancelled);
                assert_eq!(p.phase.parts.memory.len(), 584 * PAGE);
                assert_eq!(
                    usage(p).reservations.state.current,
                    before.reservations.state.current
                );
                assert_eq!(usage(p).live.memory_pages.current, 584);
                assert!(g.transfer.ticket.is_none());
            },
        );
    }
}
#[test]
fn swift_dispatch_cd22_exact_and_one_byte_below_frame() {
    for exact in [false, true] {
        let (mut own, _) = owner(&[], &[], SwiftRunBudget::default());
        let previous = own
            .control
            .as_ref()
            .unwrap()
            .usage(None)
            .reservations
            .construction
            .current;
        let target = own
            .control
            .as_ref()
            .unwrap()
            .usage(None)
            .reservations
            .combined
            .current
            + FRAME_OPERATION_BYTES.unwrap()
            - usize::from(!exact);
        let old = own
            .control
            .as_mut()
            .unwrap()
            .test_replace_combined_limit(target);
        let prep = own.prepare_growth(frame_tests::cursor());
        if exact {
            let (p, c) = prep.unwrap();
            assert!(matches!(
                complete(p, c, SwiftGrowthStorage::empty(), storage(), None),
                GrowthCompletion::Completed(FrameCompletion::Completed)
            ));
        } else {
            assert_eq!(
                prep.err().unwrap().kind,
                SwiftRunFailureKind::CombinedExhausted
            );
        }
        own.control
            .as_mut()
            .unwrap()
            .test_replace_combined_limit(old);
        assert_eq!(
            own.control
                .as_ref()
                .unwrap()
                .usage(None)
                .reservations
                .construction
                .current,
            previous
        );
        frame_tests::retire(own);
    }
}
#[test]
fn swift_dispatch_cd01_foreign_owners_and_memory_layout() {
    for fault in 0..10 {
        let (mut own, _) = owner(&[], &[], SwiftRunBudget::default());
        let (mut other, _) = owner(&[], &[], SwiftRunBudget::default());
        let before = own.control.as_ref().unwrap().usage(None);
        match fault {
            0 => std::mem::swap(&mut own.wasi, &mut other.wasi),
            1 => std::mem::swap(&mut own.cache, &mut other.cache),
            2 => std::mem::swap(
                &mut own.state.as_mut().unwrap().execution_header,
                &mut other.state.as_mut().unwrap().execution_header,
            ),
            3..=8 => std::mem::swap(
                &mut own.state.as_mut().unwrap().buffers[fault - 3],
                &mut other.state.as_mut().unwrap().buffers[fault - 3],
            ),
            _ => {
                own.state.as_mut().unwrap().memory.pop();
            }
        }
        let failure = own.prepare_growth(frame_tests::cursor()).err().unwrap();
        assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
        assert_eq!(
            own.control.as_ref().unwrap().usage(None).instructions,
            before.instructions
        );
        assert_eq!(
            own.control.as_ref().unwrap().usage(None).reservations,
            before.reservations
        );
        match fault {
            0 => std::mem::swap(&mut own.wasi, &mut other.wasi),
            1 => std::mem::swap(&mut own.cache, &mut other.cache),
            2 => std::mem::swap(
                &mut own.state.as_mut().unwrap().execution_header,
                &mut other.state.as_mut().unwrap().execution_header,
            ),
            3..=8 => std::mem::swap(
                &mut own.state.as_mut().unwrap().buffers[fault - 3],
                &mut other.state.as_mut().unwrap().buffers[fault - 3],
            ),
            _ => own.state.as_mut().unwrap().memory.push(0),
        }
        frame_tests::retire(own);
        frame_tests::retire(other);
    }
}
#[test]
fn swift_dispatch_cd11_caller_result_push_rejections() {
    for fault in [1, 2, 4] {
        execute(
            &[
                (0, Function::scalar(&[0x10, 36, 0x0b], Type::I32)),
                (2, Function::scalar(&[0x41, 7, 0x0b], Type::I32)),
            ],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                frame_tests::hooks(frame_tests::Hooks {
                    push_fault: fault,
                    ..Default::default()
                });
                run(p, c, g, s).unwrap();
                assert!(s.returned.as_ref().unwrap().is_err());
                assert_eq!(p.phase.parts.frames.len(), 1);
                assert_eq!(p.phase.parts.cache.usage().active_pins, 1);
                assert!(p.phase.parts.values.is_empty());
            },
        );
    }
}
#[test]
fn swift_dispatch_cd14_all_mutable_scalar_globals() {
    for (index, ty, constant, expected) in [
        (0, Type::I32, vec![0x41, 0x7f], Value::I32(-1)),
        (
            2,
            Type::F32,
            vec![0x43, 0, 0, 0, 0x80],
            Value::F32(0x80000000),
        ),
        (
            3,
            Type::F64,
            vec![0x44, 0, 0, 0, 0, 0, 0, 0, 0x80],
            Value::F64(0x8000000000000000),
        ),
    ] {
        let mut body = constant;
        body.extend([0x24, index, 0x10, 36, 0x0b]);
        let getter = Function::scalar(&[0x23, index, 0x0b], ty);
        execute(
            &[(0, Function::scalar(&body, ty)), (2, getter)],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), Some(expected));
                assert_eq!(p.phase.parts.globals[index as usize], expected);
            },
        );
    }
    // An immutable global write is rejected by the sealed validator, before owners.
    let (bytes, _) = module(&[(0, Function::void(&[0x42, 0, 0x24, 1, 0x0b]))], &[]);
    assert!(validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
}
#[test]
fn swift_dispatch_cd13_region_and_checked_base() {
    for fault in 0..3 {
        let main = Function {
            params: vec![],
            result: Some(Type::I32),
            locals: vec![Type::I32],
            body: vec![0x20, 0, 0x0b],
        };
        execute(
            &[(0, main)],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                let original = (
                    p.phase.parts.frames[0].base,
                    p.phase.parts.frames[0].operands,
                );
                if fault == 0 {
                    p.phase.parts.frames[0].base = usize::MAX;
                } else if fault == 1 {
                    p.phase.parts.frames[0].operands = 0;
                } else {
                    p.phase.parts.frames[0].base = 1;
                }
                run(p, c, g, s).unwrap();
                assert!(s.returned.as_ref().unwrap().is_err());
                (
                    p.phase.parts.frames[0].base,
                    p.phase.parts.frames[0].operands,
                ) = original;
            },
        );
    }
}
#[test]
fn swift_dispatch_cd17_bulk_overlap_zero_and_bounds() {
    for (destination, source, length, expected) in [
        (2, 0, 6, [0, 1, 0, 1, 2, 3, 4, 5]),
        (0, 2, 6, [2, 3, 4, 5, 6, 7, 6, 7]),
        (0, 0, 0, [0, 1, 2, 3, 4, 5, 6, 7]),
    ] {
        let body = [
            0x41,
            destination,
            0x41,
            source,
            0x41,
            length,
            0xfc,
            10,
            0,
            0,
            0x0b,
        ];
        execute(
            &[(0, Function::void(&body))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                p.phase.parts.memory[..8].copy_from_slice(&[0, 1, 2, 3, 4, 5, 6, 7]);
                run(p, c, g, s).unwrap();
                assert_eq!(result(s), None);
                assert_eq!(&p.phase.parts.memory[..8], &expected);
            },
        );
    }
    for operation in [
        vec![0x41, 0x7f, 0x41, 0, 0x41, 1, 0xfc, 10, 0, 0, 0x0b],
        vec![0x41, 0x7f, 0x41, 7, 0x41, 1, 0xfc, 11, 0, 0x0b],
    ] {
        execute(
            &[(0, Function::void(&operation))],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                let first = p.phase.parts.memory[0];
                run(p, c, g, s).unwrap();
                assert_eq!(failure(s).kind, SwiftRunFailureKind::GuestTrap);
                assert_eq!(p.phase.parts.memory[0], first);
            },
        );
    }
}
#[test]
fn swift_dispatch_cd19_high_unsigned_exit_and_errno() {
    let exit = WasiFunction::ALL
        .iter()
        .position(|f| *f == WasiFunction::ProcExit)
        .unwrap() as u8;
    execute(
        &[(0, Function::void(&[0x41, 0x7f, 0x10, exit, 0x0b]))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(failure(s).guest_exit, Some(u32::MAX));
            assert_eq!(usage(p).host_calls, 1);
        },
    );
    let close = WasiFunction::ALL
        .iter()
        .position(|f| *f == WasiFunction::FdClose)
        .unwrap() as u8;
    execute(
        &[(
            0,
            Function::scalar(&[0x41, 0x7f, 0x10, close, 0x0b], Type::I32),
        )],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            run(p, c, g, s).unwrap();
            assert_eq!(
                result(s),
                Some(Value::I32(
                    crate::experimental_wasi::Errno::Badf as u16 as i32
                ))
            );
            assert_eq!(usage(p).host_calls, 1);
        },
    );
}
#[test]
fn swift_dispatch_cd22_cache_and_growth_allocations_separate() {
    for growing in [false, true] {
        let main = if growing {
            Function::scalar(&[0x41, 1, 0x40, 0, 0x0b], Type::I32)
        } else {
            Function::scalar(&[0x10, 36, 0x0b], Type::I32)
        };
        execute(
            &[
                (0, main),
                (2, Function::scalar(&[0x41, 7, 0x0b], Type::I32)),
            ],
            &[],
            SwiftRunBudget::default(),
            |p, c, g, s, _| {
                let (_, stats) = measure_extended(None, || run(p, c, g, s).unwrap());
                assert!(stats.attempts > 0);
                assert_eq!(result(s), Some(Value::I32(if growing { 584 } else { 7 })));
                if growing {
                    assert_eq!(stats.allocations, 1);
                    assert_eq!(stats.allocated_bytes, 585 * PAGE);
                }
                println!(
                    "CD22_COLD growth={} attempts={} alloc={} bytes={} realloc={}",
                    growing,
                    stats.attempts,
                    stats.allocations,
                    stats.allocated_bytes,
                    stats.reallocations
                );
            },
        );
    }
}
#[test]
fn swift_dispatch_cd18_fixture_unwind_restores_original_hook_owners() {
    let (mut foreign, _) = owner(&[], &[], SwiftRunBudget::default());
    execute(
        &[(0, Function::scalar(&[0x41, 1, 0x40, 0, 0x0b], Type::I32))],
        &[],
        SwiftRunBudget::default(),
        |p, c, g, s, _| {
            let panic = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                let mut guard = growth::dispatch_old_refund(&mut foreign, g);
                run(p, c, guard.growth(), s).unwrap();
                panic!("fixture-only unwind after admitted run");
            }));
            assert!(panic.is_err());
            assert!(foreign.state.as_ref().unwrap().buffers[3].is_some());
            assert!(g
                .transfer
                .old_ticket
                .as_ref()
                .unwrap()
                .matches_layout(SwiftReservationCategory::State, 584 * PAGE));
            growth::release_growth_pending(p, c, g).unwrap();
        },
    );
    frame_tests::retire(foreign);
}
#[test]
fn swift_dispatch_cd06_exact_long_scan_schedule() {
    for params in [64, 65] {
        for step in 0..=if params == 64 { 5 } else { 6 } {
            let cancel = if step == 0 {
                None
            } else {
                Some(params + 1 + step)
            };
            let callee = Function {
                params: vec![Type::I32; params],
                result: Some(Type::I32),
                locals: vec![],
                body: vec![0x20, (params - 1) as u8, 0x0b],
            };
            let mut body = vec![];
            for _ in 0..params {
                body.extend([0x41, 1]);
            }
            body.extend([0x41, 0, 0x11, 38, 0, 0x0b]);
            execute(
                &[(0, Function::scalar(&body, Type::I32)), (2, callee)],
                &[36],
                SwiftRunBudget::default(),
                |p, c, g, s, _| {
                    CHECK_COUNT.with(|x| x.set(0));
                    CANCEL_AT.with(|x| x.set(cancel));
                    let before = usage(p);
                    run(p, c, g, s).unwrap();
                    CANCEL_AT.with(|x| x.set(None));
                    if let Some(at) = cancel {
                        assert_eq!(failure(s).kind, SwiftRunFailureKind::Cancelled);
                        assert_eq!(CHECK_COUNT.with(Cell::get), at + 1);
                        assert_eq!(p.phase.parts.frames.len(), 1);
                        assert_eq!(p.phase.parts.cache.usage().active_pins, 1);
                    } else {
                        assert_eq!(result(s), Some(Value::I32(1)));
                        assert_eq!(
                            usage(p).instructions - before.instructions,
                            params as u64 + 5
                        );
                        assert_eq!(
                            CHECK_COUNT.with(Cell::get),
                            if params == 64 { 74 } else { 76 }
                        );
                    }
                },
            );
        }
    }
}
#[test]
fn swift_dispatch_cd20_actual_deadline_before_fetch() {
    execute(
        &[(0, Function::void(&[0x01, 0x0b]))],
        &[],
        SwiftRunBudget {
            deadline_ms: 1000,
            ..SwiftRunBudget::default()
        },
        |p, c, g, s, _| {
            let before = usage(p);
            std::thread::sleep(
                p.phase
                    .operation
                    .control
                    .deadline()
                    .saturating_duration_since(Instant::now())
                    + std::time::Duration::from_millis(2),
            );
            run(p, c, g, s).unwrap();
            let f = failure(s);
            assert_eq!(f.kind, SwiftRunFailureKind::Deadline);
            assert_eq!(usage(p).instructions, before.instructions);
            assert_eq!(usage(p).execution_work, before.execution_work);
            assert_eq!(f.deadline_origin, SwiftDeadlineOrigin::Run);
            assert!(f.at_failure.deadline_overshoot_micros > 0);
        },
    );
}
#[test]
fn swift_dispatch_cd22_exact_header_admission_before_constructor() {
    for below in [false, true] {
        let (bytes, _) = module(&[], &[]);
        let proof = validate_swift_reactor(
            &bytes,
            SwiftValidationBudget::default(),
            &Cancellation::default(),
        )
        .unwrap();
        let header = execution_header_bytes().unwrap();
        let (mut control, proof) = RuntimeControl::adopt(
            proof,
            SwiftRunBudget {
                state_bytes: header - usize::from(below),
                ..SwiftRunBudget::default()
            },
            Instant::now(),
            Cancellation::default(),
        )
        .unwrap();
        let before = control.usage(None);
        let (result, stats) = measure_extended(Some(0), || {
            control.admit(
                SwiftReservationCategory::State,
                header,
                frame_tests::cursor(),
            )
        });
        assert_eq!(stats.attempts, 0);
        if below {
            let f = result.err().unwrap();
            assert_eq!(f.kind, SwiftRunFailureKind::CategoryExhausted);
            assert_eq!(
                control.usage(None).reservations.state.current,
                before.reservations.state.current
            );
        } else {
            let ticket = result.unwrap();
            assert_eq!(control.usage(None).reservations.state.current, header);
            control.drop_reserved_with_wasi((), ticket, None).unwrap();
        }
        control.drop_proof(proof).unwrap();
        assert_eq!(
            control
                .finish_owned_cleanup(None)
                .reservations
                .combined
                .current,
            0
        );
    }
}
