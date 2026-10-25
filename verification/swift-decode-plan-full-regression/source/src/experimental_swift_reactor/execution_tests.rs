//! Layout and ownership prerequisites, deliberately not executor acceptance tests.
use super::allocation_tests::measure;
use super::cache::{
    CacheCleanupTail, CacheConstructionFailure, CacheConstructionPhase, CacheOperationPhase,
    SwiftFunctionCache, SwiftFunctionPin, SwiftReleaseFailure,
};
use super::control::*;
use super::execution::*;
use super::{validate_swift_reactor, SwiftValidationBudget};
use crate::experimental::cache::{DecodedInstruction, FunctionView, Operation};
use crate::experimental::descriptors::{FunctionSpanView, SignatureView};
use crate::experimental::execution::{borrowed::*, Control};
use crate::experimental_wasi::{
    accounted::{AccountedWasi, WasiConstructionPhase},
    WasiBudget, WasiFunction, WasiGrants, WasiUsage,
};
use crate::{Cancellation, Type, Value};
use std::mem::{align_of, offset_of, size_of};
use std::time::Instant;

#[derive(Clone, Copy, Default)]
struct ConstructionHooks {
    checks: usize,
    cancel: Option<usize>,
    capacities: usize,
    capacity: Option<usize>,
    bad_restore: bool,
}
thread_local! { static CONSTRUCTION_HOOKS: std::cell::Cell<ConstructionHooks> = std::cell::Cell::new(ConstructionHooks::default()); }
pub(super) fn construction_checkpoint(control: &RuntimeControl, _: Cursor) {
    CONSTRUCTION_HOOKS.with(|slot| {
        let mut hooks = slot.get();
        if hooks.cancel == Some(hooks.checks) {
            control.cancellation().cancel();
        }
        hooks.checks += 1;
        slot.set(hooks);
    });
}
pub(super) fn construction_capacity(observed: usize) -> usize {
    CONSTRUCTION_HOOKS.with(|slot| {
        let mut hooks = slot.get();
        let corrupt = hooks.capacity == Some(hooks.capacities);
        hooks.capacities += 1;
        slot.set(hooks);
        observed + usize::from(corrupt)
    })
}
pub(super) fn construction_restore_bound(previous: usize) -> usize {
    CONSTRUCTION_HOOKS.with(|slot| if slot.get().bad_restore { 0 } else { previous })
}
#[test]
fn swift_construction_named_layout_supplement() {
    print_construction_layouts();
    assert!(construction_bytes().unwrap() > phase_bytes("construction").unwrap());
}

#[test]
fn swift_executor_layout_all_eight_phase_shapes() {
    macro_rules! row {
        ($t:ty) => {
            println!(
                "layout {} {} {}",
                stringify!($t),
                size_of::<$t>(),
                align_of::<$t>()
            );
        };
    }
    macro_rules! fields { ($t:ty; $($f:ident),+) => {$({ println!("offset {} {} {}", stringify!($t), stringify!($f), offset_of!($t,$f)); })+}; }
    row!(SwiftExecutionState);
    row!(SwiftReactorInstance);
    row!(Lifecycle);
    row!(SwiftFrame);
    row!(Control);
    row!(Value);
    row!(Vec<Value>);
    row!(Vec<Control>);
    row!(Vec<SwiftFrame>);
    row!(Vec<u8>);
    row!(Vec<Option<u32>>);
    row!(Option<u32>);
    row!([Option<ReservationTicket>; 6]);
    row!(ReservationTicket);
    row!(Option<ReservationTicket>);
    row!(RuntimeControl);
    row!(SwiftFunctionCache);
    row!(AccountedWasi);
    row!(Option<SwiftExecutionState>);
    row!(Option<RuntimeControl>);
    row!(Option<SwiftFunctionCache>);
    row!(Option<AccountedWasi>);
    row!(ExecutionParts<'static, SwiftMode>);
    row!(SwiftExecutionOperation<'static>);
    row!(ExecutionConstructionPhase<'static>);
    row!(ExecutionOperationPhase<'static>);
    row!(PartialState);
    row!(PartialInstance);
    row!(EntryGuard);
    row!(ScalarReader<'static>);
    row!(SelectedInstruction);
    row!(GrowthTransfer);
    row!(ExecutionCleanupTail);
    row!(HeaderCompletionParts);
    row!(ScalarBorrowInventory);
    row!(CallerDiagnostics);
    row!(SwiftFunctionPin);
    row!(SwiftReleaseFailure);
    row!(CacheCleanupTail<'static>);
    row!(CacheConstructionPhase<'static>);
    row!(CacheOperationPhase<'static>);
    row!(WasiConstructionPhase<'static>);
    row!(CacheConstructionFailure);
    row!(SwiftRunFailure);
    row!(Option<SwiftRunFailure>);
    row!(Result<(),SwiftRunFailure>);
    row!(SwiftRunUsage);
    row!(Option<SwiftRunUsage>);
    row!(WasiUsage);
    row!(Option<WasiUsage>);
    row!(Fault);
    row!(Cursor);
    row!(Cancellation);
    row!(FunctionView<'static>);
    row!(FunctionSpanView<'static>);
    row!(SignatureView<'static>);
    row!(DecodedInstruction);
    row!(Operation);
    row!(Option<Result<SwiftExecutionState, SwiftRunFailure>>);
    row!(Option<Result<SwiftReactorInstance, SwiftRunFailure>>);
    row!(Option<Result<SwiftFunctionCache, CacheConstructionFailure>>);
    row!(Option<Result<AccountedWasi, SwiftRunFailure>>);
    row!(Result<ExecutionConstructionPhase<'static>, SwiftRunFailure>);
    row!(Result<ExecutionOperationPhase<'static>, SwiftRunFailure>);
    row!(Result<FunctionView<'static>, SwiftRunFailure>);
    row!(Option<Result<SwiftFunctionPin, SwiftRunFailure>>);
    row!(Result<(),SwiftReleaseFailure>);
    row!(Result<Option<Value>, SwiftRunFailure>);
    row!(Result<Vec<u8>, SwiftRunFailure>);
    row!(Result<ReservationTicket,SwiftRunFailure>);
    row!(Option<Result<ExecutionCleanupTail, SwiftRunFailure>>);
    row!(Option<Result<CacheCleanupTail<'static>, SwiftRunFailure>>);
    row!(std::ops::Range<usize>);
    row!(std::collections::TryReserveError);
    row!(Result<HeaderCompletionParts,SwiftRunFailure>);
    fields!(SwiftExecutionState; memory,table,globals,values,controls,frames,buffers,execution_header);
    fields!(SwiftReactorInstance; control,cache,wasi,state,lifecycle);
    fields!(SwiftFrame; function,pc,base,operands,controls,result,pin);
    fields!(ExecutionParts<'static,SwiftMode>; cache,memory,table,globals,values,controls,frames);
    fields!(SwiftExecutionOperation<'static>; control,wasi,cursor);
    fields!(ExecutionConstructionPhase<'static>; control,cache,wasi,cursor,previous_bound,constructed);
    fields!(ExecutionOperationPhase<'static>; parts,operation,previous_bound);
    fields!(PartialState; state,next_arena);
    fields!(PartialInstance; control,cache,wasi,state);
    fields!(EntryGuard; pin,values_debited,controls_debited,frame_debited);
    fields!(ScalarReader<'static>; bytes,at,absolute_offset);
    fields!(SelectedInstruction; instruction,branch_target,cursor);
    fields!(GrowthTransfer; replacement,ticket,old,old_ticket,old_pages,next_pages,copied);
    fields!(ExecutionCleanupTail; control,header,final_wasi,failure);
    fields!(HeaderCompletionParts; control,header,final_wasi);
    fields!(CallerDiagnostics; failure,usage,observation);
    fields!(ScalarBorrowInventory; control,cache,wasi,state,phase,pin,view,initializer,signature,
        values,memory,indices,cursor,fault,capacity,requested,observed,index,length,base,operands,
        controls,frame_count,value_count,control_count,destination,source,end,chunk_end,copied,
        absolute_function,type_index,table_index,branch_depth,old_pages,next_pages,delta_pages,
        opcode,value,selected,reserve_error);
    fields!(Fault; kind,code,resource,attempted,limit,observed_capacity,wasi_failure,guest_exit);
    fields!(Cursor; stage,function,offset);
    fields!(DecodedInstruction; operation,offset);
    fields!(FunctionView<'static>; function,type_index,body_offset,locals,instructions,branch_targets);
    fields!(FunctionSpanView<'static>; absolute_index,type_index,body_offset,body);
    fields!(SignatureView<'static>; params,result);
    for r in terms() {
        println!(
            "term {}|{}|{}|{}|{}",
            r.phase, r.binding, r.shape, r.count, r.bytes
        );
        assert!(r.count.checked_mul(r.bytes).is_some());
    }
    for phase in ["construction", "operation", "growth", "cleanup"] {
        println!("bound {} {}", phase, phase_bytes(phase).unwrap());
    }
    println!(
        "bound execution_header {}",
        execution_header_bytes().unwrap()
    );
    println!(
        "bound foundation {}",
        foundation_construction_bytes().unwrap()
    );
    // Each present payload is disjoint; all Option tags and owner alignment
    // remain charged in the positive exclusive residual, never free capacity.
    let nested = size_of::<RuntimeControl>()
        + size_of::<SwiftFunctionCache>()
        + size_of::<AccountedWasi>()
        + size_of::<SwiftExecutionState>();
    assert!(size_of::<SwiftReactorInstance>() >= nested);
    println!(
        "bound exclusive_owner_residual {}",
        size_of::<SwiftReactorInstance>() - nested
    );
    assert_eq!(
        size_of::<Option<SwiftRunFailure>>(),
        size_of::<SwiftRunFailure>()
    );
    assert_eq!(
        size_of::<Result<(), SwiftRunFailure>>(),
        size_of::<SwiftRunFailure>()
    );
    assert_eq!(
        size_of::<Option<SwiftRunUsage>>(),
        size_of::<SwiftRunUsage>()
    );
    assert_eq!(
        size_of::<Option<ReservationTicket>>(),
        size_of::<ReservationTicket>()
    );
    assert_eq!(
        size_of::<ExecutionParts<'static, SwiftMode>>(),
        7 * size_of::<usize>()
    );
}

#[test]
fn swift_executor_layout_checked_arenas_and_growth_overlap() {
    let arena = arena_bytes(16384, 4096, 64, 584, 46713, 5273).unwrap();
    assert_eq!(
        arena,
        [
            16384 * size_of::<Value>(),
            4096 * size_of::<Control>(),
            64 * size_of::<SwiftFrame>(),
            584 * 65536,
            46713 * size_of::<Option<u32>>(),
            5273 * size_of::<Value>()
        ]
    );
    assert_eq!(arena_bytes(0, 0, 0, 0, 0, 0), Some([0; 6]));
    for index in 0..6 {
        let mut args = [0; 6];
        args[index] = usize::MAX;
        assert!(arena_bytes(args[0], args[1], args[2], args[3], args[4], args[5]).is_none());
    }
    assert_eq!(767usize * 65536 + 768usize * 65536, 100597760);
    println!("arena {:?}", arena);
}

#[test]
fn swift_executor_layout_six_requested_vector_shapes_allocate_exactly() {
    let (state, stats) = measure(|| {
        let mut state = SwiftExecutionState {
            memory: Vec::new(),
            table: Vec::new(),
            globals: Vec::new(),
            values: Vec::new(),
            controls: Vec::new(),
            frames: Vec::new(),
            buffers: std::array::from_fn(|_| None),
            execution_header: None,
            frame_cleanup: Default::default(),
        };
        // This is a storage-layout witness with no initialization/dispatch.
        state.values.try_reserve_exact(16).unwrap();
        state.controls.try_reserve_exact(8).unwrap();
        state.frames.try_reserve_exact(2).unwrap();
        state.memory.try_reserve_exact(65536).unwrap();
        state.table.try_reserve_exact(3).unwrap();
        state.globals.try_reserve_exact(4).unwrap();
        state
    });
    assert_eq!(
        [
            state.values.capacity(),
            state.controls.capacity(),
            state.frames.capacity(),
            state.memory.capacity(),
            state.table.capacity(),
            state.globals.capacity()
        ],
        [16, 8, 2, 65536, 3, 4]
    );
    assert_eq!(stats.allocations, 6);
    assert_eq!(stats.reallocations, 0);
    let bytes: usize = arena_bytes(16, 8, 2, 1, 3, 4).unwrap().iter().sum();
    assert_eq!(stats.allocated_bytes, bytes);
    assert!(state.buffers.iter().all(Option::is_none));
    assert!(state.execution_header.is_none());
    println!(
        "vector witness allocations={} requested={} capacities=16,8,2,65536,3,4",
        stats.allocations, bytes
    );
    drop(state);
}

#[test]
fn swift_executor_layout_selection_and_static_lifetime_compile() {
    fn cache_reborrow(phase: &mut ExecutionOperationPhase<'_>) {
        with_cache_operation(phase, |parts, op| {
            let nested =
                parts
                    .cache
                    .prepare_operation(&mut *op.control, Some(&*op.wasi), op.cursor);
            if let Ok(nested) = nested {
                let _ = nested.complete(());
            }
        });
    }
    fn parts_association<'a>(
        parts: ExecutionParts<'a, SwiftMode>,
        op: SwiftExecutionOperation<'a>,
    ) -> (
        ExecutionParts<'a, SwiftMode>,
        <SwiftMode as ExecutionMode>::Operation<'a>,
    ) {
        (parts, op)
    }
    std::hint::black_box(cache_reborrow as fn(&mut ExecutionOperationPhase<'_>));
    std::hint::black_box(parts_association);
    let owned = {
        let instructions = [DecodedInstruction {
            operation: Operation::Nop,
            offset: 7,
        }];
        let targets = [9];
        let view = FunctionView {
            function: 35,
            type_index: 34,
            body_offset: 7,
            locals: &[],
            instructions: &instructions,
            branch_targets: &targets,
        };
        SelectedInstruction {
            instruction: view.instructions[0],
            branch_target: Some(view.branch_targets[0]),
            cursor: Cursor::adoption(),
        }
    };
    assert_eq!(owned.instruction.operation, Operation::Nop);
    assert_eq!(owned.branch_target, Some(9));
}

// Same sealed ABI, 29 definitions; only complete validation/adoption occurs.
fn fixture() -> Vec<u8> {
    fn uint(mut x: u32, out: &mut Vec<u8>) {
        loop {
            let b = (x & 127) as u8;
            x >>= 7;
            out.push(b | if x != 0 { 128 } else { 0 });
            if x == 0 {
                return;
            }
        }
    }
    fn text(x: &[u8], out: &mut Vec<u8>) {
        uint(x.len() as u32, out);
        out.extend_from_slice(x);
    }
    fn section(id: u8, x: Vec<u8>, out: &mut Vec<u8>) {
        out.push(id);
        uint(x.len() as u32, out);
        out.extend(x);
    }
    fn ty(t: Type) -> u8 {
        match t {
            Type::I32 => 0x7f,
            Type::I64 => 0x7e,
            Type::F32 => 0x7d,
            Type::F64 => 0x7c,
        }
    }
    let mut out = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![36];
    for function in WasiFunction::ALL {
        types.push(0x60);
        uint(function.parameters().len() as u32, &mut types);
        types.extend(function.parameters().iter().copied().map(ty));
        uint(function.results().len() as u32, &mut types);
        types.extend(function.results().iter().copied().map(ty));
    }
    types.extend([0x60, 0, 0, 0x60, 0, 1, 0x7f]);
    section(1, types, &mut out);
    let mut imports = vec![34];
    for (index, function) in WasiFunction::ALL.into_iter().enumerate() {
        text(b"wasi_snapshot_preview1", &mut imports);
        text(function.name(), &mut imports);
        imports.push(0);
        uint(index as u32, &mut imports);
    }
    section(2, imports, &mut out);
    let mut functions = vec![29];
    functions.extend((0..29).map(|index| if index == 28 { 35 } else { 34 }));
    section(3, functions, &mut out);
    let mut table = vec![1, 0x70, 1];
    uint(46713, &mut table);
    uint(46713, &mut table);
    section(4, table, &mut out);
    let mut memory = vec![1, 0];
    uint(584, &mut memory);
    section(5, memory, &mut out);
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
    section(7, exports, &mut out);
    let mut code = vec![29];
    for index in 0..29 {
        let bytes: &[u8] = if index == 28 {
            &[0, 0x41, 0, 0x0b]
        } else {
            &[0, 0x0b]
        };
        uint(bytes.len() as u32, &mut code);
        code.extend(bytes);
    }
    section(10, code, &mut out);
    out
}
fn adopted() -> (RuntimeControl, AdoptedProof) {
    let proof = validate_swift_reactor(
        &fixture(),
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    RuntimeControl::adopt(
        proof,
        SwiftRunBudget::default(),
        Instant::now(),
        Cancellation::default(),
    )
    .unwrap()
}
fn actual_final_observation(control: &mut RuntimeControl) -> Option<WasiUsage> {
    let cursor = Cursor::adoption();
    let mut phase = AccountedWasi::prepare(control, cursor).unwrap();
    let mut wasi = phase
        .construct(
            WasiGrants::default(),
            WasiBudget::default(),
            Instant::now(),
            cursor,
        )
        .unwrap();
    phase.complete().unwrap();
    wasi.dispatch(
        control,
        WasiFunction::ArgsSizesGet,
        &[Value::I32(0), Value::I32(4)],
        &mut [0; 8],
        cursor,
    )
    .unwrap();
    let observation = wasi.checked_usage(control, cursor).unwrap();
    wasi.cleanup(control).unwrap();
    Some(observation)
}

fn construction_cursor() -> Cursor {
    Cursor {
        stage: SwiftRunStage::Initialization,
        function: None,
        offset: None,
    }
}
fn construction_hooks(hooks: ConstructionHooks) {
    CONSTRUCTION_HOOKS.with(|slot| slot.set(hooks));
}
fn construction_fixture() -> Vec<u8> {
    fn uint(mut value: u32, out: &mut Vec<u8>) {
        loop {
            let byte = (value & 127) as u8;
            value >>= 7;
            out.push(byte | if value == 0 { 0 } else { 128 });
            if value == 0 {
                return;
            }
        }
    }
    fn section(id: u8, payload: &[u8], out: &mut Vec<u8>) {
        out.push(id);
        uint(payload.len() as u32, out);
        out.extend(payload);
    }
    fn uint_at(bytes: &[u8], at: &mut usize) -> usize {
        let mut value = 0;
        let mut shift = 0;
        loop {
            let byte = bytes[*at];
            *at += 1;
            value |= ((byte & 127) as usize) << shift;
            if byte & 128 == 0 {
                return value;
            }
            shift += 7;
        }
    }
    let original = fixture();
    let mut out = original[..8].to_vec();
    let mut at = 8;
    while at < original.len() {
        let start = at;
        let id = original[at];
        at += 1;
        let len = uint_at(&original, &mut at);
        at += len;
        if id == 7 {
            let globals = [
                vec![0x7f, 1, 0x41, 0x7f, 0x0b],
                vec![0x7e, 0, 0x42, 0x7e, 0x0b],
                vec![0x7d, 0, 0x43, 0x34, 0x12, 0xc0, 0x7f, 0x0b],
                vec![0x7c, 0, 0x44, 0, 0, 0, 0, 0, 0, 0, 0x80, 0x0b],
            ];
            let mut payload = vec![4];
            for global in globals {
                payload.extend(global);
            }
            section(6, &payload, &mut out);
        }
        if id == 10 {
            // Retained source order: the later element overwrites the first.
            section(
                9,
                &[2, 0, 0x41, 0, 0x0b, 2, 34, 35, 0, 0x41, 1, 0x0b, 1, 62],
                &mut out,
            );
        }
        out.extend_from_slice(&original[start..at]);
    }
    // Overlap and a zero-length range exactly at the memory boundary.
    let mut data = vec![
        3, 0, 0x41, 0, 0x0b, 4, b'a', b'b', b'c', b'd', 0, 0x41, 2, 0x0b, 2, b'X', b'Y', 0, 0x41,
    ];
    // Positive signed-LEB of 584*65536, followed by end and zero count.
    let mut value = 584u32 * 65536;
    loop {
        let byte = (value & 127) as u8;
        value >>= 7;
        let more = value != 0 || byte & 64 != 0;
        data.push(byte | if more { 128 } else { 0 });
        if !more {
            break;
        }
    }
    data.extend([0x0b, 0]);
    section(11, &data, &mut out);
    out
}
pub(super) fn construction_adopt(budget: SwiftRunBudget) -> Option<(RuntimeControl, AdoptedProof)> {
    construction_adopt_bytes(&construction_fixture(), budget)
}
fn construction_adopt_bytes(
    bytes: &[u8],
    budget: SwiftRunBudget,
) -> Option<(RuntimeControl, AdoptedProof)> {
    let proof = validate_swift_reactor(
        bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    Some(RuntimeControl::adopt(proof, budget, Instant::now(), Cancellation::default()).unwrap())
}
fn construction_wasi_budget() -> WasiBudget {
    WasiBudget {
        one_transfer_bytes: 64,
        log_bytes: 64,
        ..WasiBudget::default()
    }
}
pub(super) fn construct_owned(
    pair: &mut Option<(RuntimeControl, AdoptedProof)>,
) -> Result<SwiftReactorInstance, ConstructionFailure> {
    SwiftReactorInstance::construct(
        pair,
        WasiGrants::default(),
        construction_wasi_budget(),
        Instant::now(),
        construction_cursor(),
    )
}
fn construct_failed(mut pair: Option<(RuntimeControl, AdoptedProof)>) -> SwiftRunFailure {
    let mut returned = Some(construct_owned(&mut pair));
    let tail = match returned.take().unwrap() {
        Err(ConstructionFailure::Cleanup(tail)) => tail,
        _ => panic!("expected destructive constructor failure"),
    };
    assert!(pair.is_none());
    let mut outcome = None;
    let mut usage = None;
    tail.complete((pair, returned), &mut outcome, &mut usage);
    let mut failure = outcome.expect("constructor latched first failure");
    failure.after_cleanup = usage;
    failure
}
pub(super) fn construction_finish(owner: SwiftReactorInstance) -> SwiftRunUsage {
    let mut owned = Some(owner);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail = returned
        .take()
        .unwrap()
        .unwrap_or_else(|e| panic!("cleanup {}", e.code));
    let mut failure = None;
    let mut usage = None;
    tail.complete((owned, returned), &mut failure, &mut usage);
    let usage = usage.unwrap();
    assert_eq!(usage.reservations.combined.current, 0);
    assert_eq!(usage.reservations.live_tickets, 0);
    assert_eq!(usage.live.memory_pages.current, 0);
    assert_eq!(usage.live.active_pins.current, 0);
    assert_eq!(usage.live.cache_entries.current, 0);
    assert_eq!(usage.cleanup_invariant, None);
    usage
}

#[test]
fn swift_construction_composed_original_proof_six_arenas_and_cleanup() {
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget::default());
    let source = pair.as_ref().unwrap().1.proof().source().as_ptr();
    let validation = pair.as_ref().unwrap().1.proof().usage();
    let floor = pair
        .as_ref()
        .unwrap()
        .0
        .usage(None)
        .reservations
        .construction
        .current;
    let (owner, allocations) = measure(|| construct_owned(&mut pair).unwrap());
    assert!(pair.is_none());
    drop(pair);
    assert!(matches!(owner.lifecycle, Lifecycle::Uninitialized));
    let state = owner.state.as_ref().unwrap();
    assert_eq!(state.values.capacity(), 16384);
    assert_eq!(state.controls.capacity(), 4096);
    assert_eq!(state.frames.capacity(), 64);
    assert_eq!(state.memory.capacity(), 584 * 65536);
    assert_eq!(state.table.capacity(), 46713);
    assert_eq!(state.globals.capacity(), 4);
    assert_eq!(
        state.values.len() + state.controls.len() + state.frames.len(),
        0
    );
    assert_eq!(&state.memory[..5], b"abXY\0");
    assert!(state.memory[4..].iter().all(|byte| *byte == 0));
    assert_eq!(&state.table[..3], &[Some(34), Some(62), None]);
    assert_eq!(
        state.globals,
        [
            Value::I32(-1),
            Value::I64(-2),
            Value::F32(0x7fc01234),
            Value::F64(0x8000000000000000)
        ]
    );
    assert_eq!(
        owner.cache.as_ref().unwrap().proof().source().as_ptr(),
        source
    );
    assert_eq!(owner.cache.as_ref().unwrap().proof().usage(), validation);
    let usage = owner
        .control
        .as_ref()
        .unwrap()
        .usage(owner.wasi.as_ref().map(AccountedWasi::usage));
    assert_eq!(usage.reservations.construction.current, floor);
    assert_eq!(usage.live.memory_pages.current, 584);
    assert_eq!(usage.instructions, 0);
    assert_eq!(usage.instruction_fuel, 0);
    assert_eq!(usage.host_calls, 0);
    assert_eq!(
        usage.execution_work,
        (584 * 65536 + 46713 + 4 + 64 + 5 + 6 + 3) as u64
    );
    assert_eq!(
        usage.reservations.retained_source.current,
        validation.source_bytes
    );
    assert_eq!(allocations.allocations, 15);
    assert_eq!(allocations.reallocations, 0);
    let (usage, cleanup) = measure(|| construction_finish(owner));
    assert_eq!(cleanup.allocations + cleanup.reallocations, 0);
    assert_eq!(cleanup.deallocations, 25); // 15 payloads + 10 adopted/foundation backing allocations.
    assert!(usage.reservations.combined.peak > usage.reservations.state.peak);
    println!(
        "construction allocations {} bytes {} cleanup_deallocations {} peak {}",
        allocations.allocations,
        allocations.allocated_bytes,
        cleanup.deallocations,
        usage.reservations.combined.peak
    );
}

#[test]
fn swift_construction_every_integrated_allocation_ordinal() {
    use super::allocation_tests::measure_extended;
    for ordinal in 0..15 {
        construction_hooks(ConstructionHooks::default());
        let pair = construction_adopt(SwiftRunBudget::default());
        let (failure, stats) = measure_extended(Some(ordinal), || construct_failed(pair));
        assert_eq!(stats.injected_failures, 1, "ordinal {ordinal}");
        assert_eq!(stats.attempts, ordinal + 1, "ordinal {ordinal}");
        assert_eq!(stats.reallocations, 0);
        assert_eq!(failure.kind, SwiftRunFailureKind::Allocation);
        let after = failure.after_cleanup.unwrap();
        assert_eq!(
            after.reservations.combined.current, 0,
            "ordinal {ordinal} {}",
            failure.code
        );
        assert_eq!(after.reservations.live_tickets, 0, "ordinal {ordinal}");
        assert_eq!(after.live.memory_pages.current, 0);
        assert_eq!(after.cleanup_invariant, None);
        assert_eq!(
            stats.deallocations,
            ordinal + 10,
            "adopted/foundation backing and prior payloads at {ordinal}"
        );
    }
}

#[test]
fn swift_construction_each_state_capacity_rejects_without_growth() {
    for ordinal in 0..6 {
        construction_hooks(ConstructionHooks {
            capacity: Some(ordinal),
            ..ConstructionHooks::default()
        });
        let pair = construction_adopt(SwiftRunBudget::default());
        let (failure, stats) = measure(|| construct_failed(pair));
        assert_eq!(failure.code, "swift_run_unexpected_capacity");
        assert_eq!(
            failure.observed_capacity,
            Some(failure.attempted as usize + 1)
        );
        assert_eq!(failure.resource, Some(SwiftRunResource::ExactCapacity));
        assert_eq!(stats.attempts, 10 + ordinal);
        assert_eq!(stats.reallocations, 0);
        assert_eq!(
            failure.after_cleanup.unwrap().reservations.combined.current,
            0
        );
    }
    construction_hooks(ConstructionHooks::default());
}

#[test]
fn swift_construction_zero_stack_capacities_and_memory_minimum() {
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget {
        frames: 0,
        values: 0,
        controls: 0,
        ..SwiftRunBudget::default()
    });
    let (owner, stats) = measure(|| construct_owned(&mut pair).unwrap());
    drop(pair);
    let state = owner.state.as_ref().unwrap();
    assert_eq!(
        state.frames.capacity() + state.values.capacity() + state.controls.capacity(),
        0
    );
    assert_eq!(stats.allocations, 12);
    construction_finish(owner);
    let pair = construction_adopt(SwiftRunBudget {
        memory_pages: 583,
        ..SwiftRunBudget::default()
    });
    let (failure, stats) = measure(|| construct_failed(pair));
    assert_eq!(failure.code, "swift_execution_memory_minimum");
    assert_eq!((failure.attempted, failure.limit), (584, 583));
    assert_eq!(stats.allocations, 9); // Cache and WASI only; no State allocation.
    assert_eq!(failure.at_failure.reservations.state.current, 0);
    assert_eq!(
        failure.after_cleanup.unwrap().reservations.combined.current,
        0
    );
}

#[test]
fn swift_construction_terminal_before_take_preserves_owner_and_first_cause() {
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget::default());
    let first = pair.as_mut().unwrap().0.fail(
        construction_cursor(),
        Fault::new(SwiftRunFailureKind::GuestTrap, "construction_prior"),
        None,
    );
    let (returned, stats) = measure(|| construct_owned(&mut pair));
    let failure = match returned {
        Err(ConstructionFailure::Rejected(failure)) => failure,
        _ => panic!("expected intact-pair rejection"),
    };
    drop(returned);
    assert_eq!(failure, first);
    assert!(pair.is_some());
    assert_eq!(
        stats.allocations + stats.deallocations + stats.reallocations,
        0
    );
    let (mut control, proof) = pair.take().unwrap();
    control.drop_proof(proof).unwrap();
    control
        .end_construction_phase(pair, foundation_construction_bytes().unwrap())
        .unwrap();
    let usage = control.finish_owned_cleanup(None);
    assert_eq!(usage.reservations.combined.current, 0);
}

#[test]
fn swift_construction_category_and_combined_admission_precede_allocation() {
    for (budget, kind, attempts) in [
        (
            SwiftRunBudget {
                state_bytes: 0,
                ..SwiftRunBudget::default()
            },
            SwiftRunFailureKind::CategoryExhausted,
            9,
        ),
        (
            SwiftRunBudget {
                combined_bytes: 32 * 1024 * 1024,
                ..SwiftRunBudget::default()
            },
            SwiftRunFailureKind::CombinedExhausted,
            12,
        ),
    ] {
        construction_hooks(ConstructionHooks::default());
        let pair = construction_adopt(budget);
        let (failure, stats) = measure(|| construct_failed(pair));
        println!("REGRESSION_ADMISSION kind={kind:?} attempts={} expected={attempts}", stats.attempts);
        assert_eq!(failure.kind, kind);
        assert_eq!(stats.attempts, attempts);
        assert_eq!(stats.reallocations, 0);
        assert_eq!(
            failure.after_cleanup.unwrap().reservations.combined.current,
            0
        );
        assert_eq!(failure.after_cleanup.unwrap().reservations.live_tickets, 0);
    }
}

#[test]
fn swift_construction_base_work_prefixes_and_selected_cancellation_boundaries() {
    let base = (584 * 65536 + 46713 + 4) as u64;
    for limit in [
        0,
        base - 1,
        base,
        base + 15,
        base + 16,
        base + 63,
        base + 64,
        base + 77,
    ] {
        construction_hooks(ConstructionHooks::default());
        let pair = construction_adopt(SwiftRunBudget {
            execution_work: limit,
            ..SwiftRunBudget::default()
        });
        let failure = construct_failed(pair);
        assert_eq!(failure.kind, SwiftRunFailureKind::WorkExhausted);
        assert!(failure.at_failure.execution_work <= limit);
        assert_eq!(failure.at_failure.live.memory_pages.current, 0);
        assert!(failure.at_failure.wasi.is_some());
        assert_eq!(
            failure.after_cleanup.unwrap().reservations.combined.current,
            0
        );
    }
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget::default());
    let owner = construct_owned(&mut pair).unwrap();
    drop(pair);
    let count = CONSTRUCTION_HOOKS.with(|slot| slot.get().checks);
    construction_finish(owner);
    // Bounded construction-only samples; the frozen all-prefix interpreter
    // qualification remains pending. These hit allocation/zero/table/final loops.
    for ordinal in [0, 1, 2, 12, 15, 1000, 10000, count - 2, count - 1] {
        construction_hooks(ConstructionHooks {
            cancel: Some(ordinal),
            ..ConstructionHooks::default()
        });
        let pair = construction_adopt(SwiftRunBudget::default());
        let failure = construct_failed(pair);
        assert_eq!(
            failure.kind,
            SwiftRunFailureKind::Cancelled,
            "check {ordinal}"
        );
        assert_eq!(
            CONSTRUCTION_HOOKS.with(|slot| slot.get().checks),
            ordinal + 1
        );
        assert_eq!(failure.at_failure.live.memory_pages.current, 0);
        assert_eq!(
            failure.after_cleanup.unwrap().reservations.combined.current,
            0
        );
        assert_eq!(failure.after_cleanup.unwrap().reservations.live_tickets, 0);
    }
    construction_hooks(ConstructionHooks::default());
    println!("construction real check boundaries {count}; selected cancellation samples 9");
}

#[test]
fn swift_construction_real_wasi_terminal_cleanup_and_intact_foreign_preflight() {
    construction_hooks(ConstructionHooks::default());
    let mut first =
        Some(construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap());
    {
        let owner = first.as_mut().unwrap();
        owner
            .wasi
            .as_mut()
            .unwrap()
            .dispatch(
                owner.control.as_mut().unwrap(),
                WasiFunction::ArgsSizesGet,
                &[Value::I32(0), Value::I32(4)],
                &mut [0; 8],
                construction_cursor(),
            )
            .unwrap();
        let observation = owner.wasi.as_ref().unwrap().usage();
        assert_eq!(observation.calls, 1);
        owner.control.as_mut().unwrap().fail(
            construction_cursor(),
            Fault::new(SwiftRunFailureKind::GuestTrap, "construction_actual_wasi"),
            Some(observation),
        );
    }
    let mut second =
        Some(construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap());
    std::mem::swap(
        &mut first.as_mut().unwrap().wasi,
        &mut second.as_mut().unwrap().wasi,
    );
    let before = first
        .as_ref()
        .unwrap()
        .control
        .as_ref()
        .unwrap()
        .usage(None);
    let (failure, stats) = measure(|| {
        SwiftReactorInstance::cleanup_owned(&mut first)
            .err()
            .unwrap()
    });
    assert_eq!(failure.code, "construction_actual_wasi");
    assert!(first.is_some());
    let after = first
        .as_ref()
        .unwrap()
        .control
        .as_ref()
        .unwrap()
        .usage(None);
    assert_eq!(before.reservations, after.reservations);
    assert_eq!(
        stats.allocations + stats.reallocations + stats.deallocations,
        0
    );
    std::mem::swap(
        &mut first.as_mut().unwrap().wasi,
        &mut second.as_mut().unwrap().wasi,
    );
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut first));
    let tail = returned
        .take()
        .unwrap()
        .unwrap_or_else(|e| panic!("{}", e.code));
    let mut failure = None;
    let mut usage = None;
    let (_, stats) = measure(|| tail.complete((first, returned), &mut failure, &mut usage));
    assert_eq!(stats.allocations + stats.reallocations, 0);
    let failure = failure.unwrap();
    assert_eq!(failure.code, "construction_actual_wasi");
    assert_eq!(failure.at_failure.wasi.unwrap().calls, 1);
    assert_eq!(usage.unwrap().wasi.unwrap().calls, 1);
    assert_eq!(usage.unwrap().reservations.combined.current, 0);
    construction_finish(second.take().unwrap());
}

#[test]
fn swift_construction_cleanup_rejects_nonempty_state_before_take() {
    construction_hooks(ConstructionHooks::default());
    let mut owned =
        Some(construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap());
    owned
        .as_mut()
        .unwrap()
        .state
        .as_mut()
        .unwrap()
        .values
        .push(Value::I32(7));
    let before = owned
        .as_ref()
        .unwrap()
        .control
        .as_ref()
        .unwrap()
        .usage(None)
        .reservations;
    let (failure, stats) = measure(|| {
        SwiftReactorInstance::cleanup_owned(&mut owned)
            .err()
            .unwrap()
    });
    assert_eq!(failure.code, "swift_execution_cleanup_nonempty");
    assert!(owned.is_some());
    assert_eq!(
        owned.as_ref().unwrap().state.as_ref().unwrap().values,
        [Value::I32(7)]
    );
    assert_eq!(
        owned
            .as_ref()
            .unwrap()
            .control
            .as_ref()
            .unwrap()
            .usage(None)
            .reservations,
        before
    );
    assert_eq!(
        stats.allocations + stats.reallocations + stats.deallocations,
        0
    );
    owned
        .as_mut()
        .unwrap()
        .state
        .as_mut()
        .unwrap()
        .values
        .clear();
    construction_finish(owned.take().unwrap());
}

#[test]
fn swift_construction_failed_outer_restore_drains_actual_components() {
    construction_hooks(ConstructionHooks {
        bad_restore: true,
        ..ConstructionHooks::default()
    });
    let pair = construction_adopt(SwiftRunBudget::default());
    let (failure, stats) = measure(|| construct_failed(pair));
    assert_eq!(failure.code, "swift_run_construction_phase_bound");
    assert_eq!(stats.allocations, 15);
    assert_eq!(stats.deallocations, 25);
    let after = failure.after_cleanup.unwrap();
    assert_eq!(after.reservations.state.current, 0);
    assert_eq!(after.reservations.cache.current, 0);
    assert_eq!(after.reservations.wasi.current, 0);
    assert_eq!(
        after.reservations.retained_source.current + after.reservations.retained_metadata.current,
        0
    );
    assert_eq!(after.live.memory_pages.current, 0);
    assert_eq!(after.reservations.live_tickets, 1);
    assert_eq!(
        after.reservations.combined.current,
        foundation_construction_bytes().unwrap() + construction_bytes().unwrap()
    );
    assert_eq!(
        after.cleanup_invariant,
        Some(SwiftCleanupInvariant::ConstructionBound)
    );
    construction_hooks(ConstructionHooks::default());
}

#[test]
fn swift_construction_retained_minimum_and_padded_signed_constants() {
    fn uint(mut n: usize, out: &mut Vec<u8>) {
        loop {
            let b = (n & 127) as u8;
            n >>= 7;
            out.push(b | if n == 0 { 0 } else { 128 });
            if n == 0 {
                return;
            }
        }
    }
    fn uint_at(bytes: &[u8], at: &mut usize) -> usize {
        let mut n = 0;
        let mut shift = 0;
        loop {
            let b = bytes[*at];
            *at += 1;
            n |= ((b & 127) as usize) << shift;
            if b & 128 == 0 {
                return n;
            }
            shift += 7;
        }
    }
    construction_hooks(ConstructionHooks::default());
    let source = construction_fixture();
    let mut fixture = source[..8].to_vec();
    let mut at = 8;
    while at < source.len() {
        let id = source[at];
        at += 1;
        let count = uint_at(&source, &mut at);
        let end = at + count;
        fixture.push(id);
        if id == 6 {
            let mut globals = vec![8];
            globals.extend_from_slice(&source[at + 1..end]);
            globals.extend([0x7f, 0, 0x41, 0x80, 0x80, 0x80, 0x80, 0x78, 0x0b]);
            globals.extend([0x7e, 0, 0x42]);
            globals.extend([0x80; 9]);
            globals.extend([0x7f, 0x0b]);
            globals.extend([0x7f, 0, 0x41, 0xff, 0xff, 0xff, 0xff, 0x7f, 0x0b]);
            globals.extend([0x7e, 0, 0x42, 0xfe]);
            globals.extend([0xff; 8]);
            globals.extend([0x7f, 0x0b]);
            uint(globals.len(), &mut fixture);
            fixture.extend(globals);
        } else {
            uint(count, &mut fixture);
            fixture.extend_from_slice(&source[at..end]);
        }
        at = end;
    }
    let mut pair = construction_adopt_bytes(&fixture, SwiftRunBudget::default());
    let owner = construct_owned(&mut pair).unwrap();
    drop(pair);
    assert_eq!(
        &owner.state.as_ref().unwrap().globals[4..],
        &[
            Value::I32(i32::MIN),
            Value::I64(i64::MIN),
            Value::I32(-1),
            Value::I64(-2)
        ]
    );
    construction_finish(owner);
}

#[test]
fn swift_construction_checked_scalar_rejects_exact_first_byte() {
    for (bytes, ty, code, offset) in [
        (&[0xff][..], Type::I32, "swift_execution_scalar_opcode", 900),
        (
            &[0x41, 0, 0x0b][..],
            Type::F32,
            "swift_execution_scalar_type",
            900,
        ),
        (
            &[0x41, 0, 0][..],
            Type::I32,
            "swift_execution_scalar_end",
            902,
        ),
        (
            &[0x41, 0, 0x0b, 0][..],
            Type::I32,
            "swift_execution_scalar_trailing",
            903,
        ),
        (
            &[0x44, 0, 0][..],
            Type::F64,
            "swift_execution_scalar_eof",
            903,
        ),
        (
            &[0x41, 0x80, 0x80, 0x80, 0x80, 0x08, 0x0b][..],
            Type::I32,
            "swift_execution_scalar_signed",
            905,
        ),
    ] {
        construction_hooks(ConstructionHooks::default());
        let mut owner =
            construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap();
        let (failure, stats) = measure(|| {
            scalar_constant_probe(
                bytes,
                900,
                ty,
                owner.control.as_mut().unwrap(),
                owner.wasi.as_ref().unwrap(),
            )
            .err()
            .unwrap()
        });
        assert_eq!((failure.code, failure.offset), (code, Some(offset)));
        assert_eq!(stats.allocations + stats.reallocations, 0);
        construction_finish(owner);
    }
}

#[test]
fn swift_construction_state_phase_is_one_shot_and_restores_exact_outer_bound() {
    construction_hooks(ConstructionHooks::default());
    let mut owner = construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap();
    let floor = owner
        .control
        .as_ref()
        .unwrap()
        .usage(None)
        .reservations
        .construction
        .current;
    let mut phase = SwiftExecutionState::prepare(
        owner.control.as_mut().unwrap(),
        owner.cache.as_ref().unwrap(),
        owner.wasi.as_ref().unwrap(),
        construction_cursor(),
    )
    .unwrap();
    let first = phase
        .construct()
        .err()
        .expect("second State cannot double initial live pages");
    assert_eq!(first.resource, Some(SwiftRunResource::MemoryPages));
    assert_eq!((first.attempted, first.limit), (1168, 768));
    let (second, stats) = measure(|| phase.construct().err().unwrap());
    assert_eq!(first, second);
    assert_eq!(
        stats.allocations + stats.reallocations + stats.deallocations,
        0
    );
    phase.complete(()).unwrap();
    assert_eq!(
        owner
            .control
            .as_ref()
            .unwrap()
            .usage(None)
            .reservations
            .construction
            .current,
        floor
    );
    assert_eq!(
        owner
            .control
            .as_ref()
            .unwrap()
            .usage(None)
            .live
            .memory_pages
            .current,
        584
    );
    construction_finish(owner);
}

#[test]
fn swift_executor_layout_final_header_success_consumes_storage_before_refund() {
    use std::sync::atomic::{AtomicBool, Ordering};
    struct Returned<'a>(&'a AtomicBool);
    impl Drop for Returned<'_> {
        fn drop(&mut self) {
            self.0.store(true, Ordering::SeqCst);
        }
    }
    let (mut control, proof) = adopted();
    let header = control
        .admit(
            SwiftReservationCategory::State,
            execution_header_bytes().unwrap(),
            Cursor::adoption(),
        )
        .unwrap();
    control.drop_proof(proof).unwrap();
    let marker = AtomicBool::new(false);
    let mut outcome = None;
    let mut usage = None;
    let tail = {
        let final_wasi = actual_final_observation(&mut control);
        ExecutionCleanupTail {
            control,
            header: Some(header),
            final_wasi,
            failure: None,
        }
    };
    let (_, stats) = measure(|| tail.complete(Returned(&marker), &mut outcome, &mut usage));
    assert!(marker.load(Ordering::SeqCst));
    assert!(outcome.is_none());
    let usage = usage.unwrap();
    assert_eq!(usage.wasi.unwrap().calls, 1);
    assert_eq!(usage.reservations.combined.current, 0);
    assert_eq!(usage.reservations.live_tickets, 0);
    assert_eq!(stats.allocations, 0);
    assert_eq!(stats.reallocations, 0);
    println!(
        "boundary success combined={} tickets={} allocations={}",
        usage.reservations.combined.current, usage.reservations.live_tickets, stats.allocations
    );
}

#[test]
fn swift_executor_layout_final_header_rejection_preserves_original_charge() {
    let (mut control, proof) = adopted();
    let (mut other, other_proof) = adopted();
    let bytes = execution_header_bytes().unwrap();
    let original = control
        .admit(SwiftReservationCategory::State, bytes, Cursor::adoption())
        .unwrap();
    let foreign = other
        .admit(SwiftReservationCategory::State, bytes, Cursor::adoption())
        .unwrap();
    control.drop_proof(proof).unwrap();
    other.drop_proof(other_proof).unwrap();
    // Test-only intentional ownership loss. The original charge must remain;
    // no test can manufacture a matching replacement token or erase the ledger.
    drop(original);
    let tail = {
        let final_wasi = actual_final_observation(&mut control);
        ExecutionCleanupTail {
            control,
            header: Some(foreign),
            final_wasi,
            failure: None,
        }
    };
    let mut outcome = None;
    let mut usage = None;
    let (_, stats) = measure(|| tail.complete((), &mut outcome, &mut usage));
    let failure = outcome.unwrap();
    let usage = usage.unwrap();
    assert_eq!(usage.wasi.unwrap().calls, 1);
    assert_eq!(failure.code, "swift_run_release_owner");
    assert_eq!(
        usage.cleanup_invariant,
        Some(SwiftCleanupInvariant::ReservationOwner)
    );
    assert_eq!(usage.reservations.state.current, bytes);
    assert_eq!(usage.reservations.combined.current, bytes);
    assert_eq!(usage.reservations.live_tickets, 1);
    assert_eq!(stats.allocations, 0);
    assert_eq!(stats.reallocations, 0);
    let other_usage = other.finish_owned_cleanup(None);
    assert_eq!(other_usage.reservations.state.current, bytes);
    println!(
        "boundary rejected code={} retained={} tickets={} allocations={}",
        failure.code, bytes, usage.reservations.live_tickets, stats.allocations
    );
}

#[test]
fn swift_executor_layout_cancellation_backing_observed() {
    let layout = Cancellation::requested_backing_layout();
    let (_, stats) = measure(|| {
        let a = Cancellation::default();
        let b = a.clone();
        a.cancel();
        assert!(b.is_cancelled());
        drop((a, b));
    });
    assert_eq!(stats.allocations, 1);
    assert_eq!(stats.reallocations, 0);
    assert_eq!(stats.allocated_bytes, layout.size());
    assert_eq!(stats.last_align, layout.align());
    assert_eq!(stats.deallocations, 1);
    println!(
        "cancellation backing={} align={} allocations={} handle={}",
        layout.size(),
        layout.align(),
        stats.allocations,
        size_of::<Cancellation>()
    );
}


#[test]
fn full_regression_observe_integrated_fixture_shapes() {
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget::default());
    let (owner, stats) = measure(|| construct_owned(&mut pair).unwrap());
    drop(pair);
    let (usage, cleanup) = measure(|| construction_finish(owner));
    println!("REGRESSION_INTEGRATED stats={stats:?} cleanup={cleanup:?} final_tickets={} final_combined={}", usage.reservations.live_tickets, usage.reservations.combined.current);
    for ordinal in 0..stats.attempts {
        let pair = construction_adopt(SwiftRunBudget::default());
        let (failure, observed) =
            super::allocation_tests::measure_extended(Some(ordinal), || construct_failed(pair));
        let after = failure.after_cleanup.unwrap();
        println!("REGRESSION_INTEGRATED_ALLOCATION ordinal={ordinal} stats={observed:?} code={} combined={} tickets={}", failure.code, after.reservations.combined.current, after.reservations.live_tickets);
        assert_eq!(observed.injected_failures, 1);
        assert_eq!(observed.attempts, ordinal + 1);
        assert_eq!(after.reservations.combined.current, 0);
        assert_eq!(after.reservations.live_tickets, 0);
    }
    for ordinal in 0..6 {
        construction_hooks(ConstructionHooks {
            capacity: Some(ordinal),
            ..ConstructionHooks::default()
        });
        let pair = construction_adopt(SwiftRunBudget::default());
        let (failure, observed) = measure(|| construct_failed(pair));
        println!("REGRESSION_INTEGRATED_CAPACITY ordinal={ordinal} stats={observed:?} attempted={} observed={:?}", failure.attempted, failure.observed_capacity);
        assert_eq!(failure.code, "swift_run_unexpected_capacity");
        assert_eq!(
            failure.after_cleanup.unwrap().reservations.combined.current,
            0
        );
    }
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget {
        frames: 0,
        values: 0,
        controls: 0,
        ..SwiftRunBudget::default()
    });
    let (owner, stats) = measure(|| construct_owned(&mut pair).unwrap());
    drop(pair);
    println!("REGRESSION_ZERO_STACK stats={stats:?}");
    construction_finish(owner);
    let pair = construction_adopt(SwiftRunBudget {
        memory_pages: 583,
        ..SwiftRunBudget::default()
    });
    let (failure, stats) = measure(|| construct_failed(pair));
    println!(
        "REGRESSION_BEFORE_STATE stats={stats:?} code={}",
        failure.code
    );
    assert_eq!(failure.code, "swift_execution_memory_minimum");
    assert_eq!(
        failure.after_cleanup.unwrap().reservations.combined.current,
        0
    );
    construction_hooks(ConstructionHooks {
        bad_restore: true,
        ..ConstructionHooks::default()
    });
    let pair = construction_adopt(SwiftRunBudget::default());
    let (failure, stats) = measure(|| construct_failed(pair));
    println!(
        "REGRESSION_FAILED_RESTORE stats={stats:?} code={}",
        failure.code
    );
    assert_eq!(failure.code, "swift_run_construction_phase_bound");
    construction_hooks(ConstructionHooks::default());
}
