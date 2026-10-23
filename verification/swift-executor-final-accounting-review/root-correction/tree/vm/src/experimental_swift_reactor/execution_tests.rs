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
