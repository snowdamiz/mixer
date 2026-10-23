//! Independent source-review probes. Compiled only into a review-owned copy.
use super::*;
use crate::experimental_swift_reactor::allocation_tests::{measure, measure_extended};
use crate::experimental_swift_reactor::control::{
    foundation_construction_bytes, AdoptedProof, SwiftCleanupInvariant,
    SwiftDeadlineOrigin, SwiftRunBudget, SwiftRunResource, SwiftRunStage,
};
use crate::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget};
use crate::experimental_wasi::tests::review_hooks;
use crate::{Cancellation, Type};

// A separately authored tiny module retains all 34 ordered imports, memory 584,
// fixed table 46713, initialize 35 and corpus 62. It is validated, never executed.
fn unsigned(mut n: u32, out: &mut Vec<u8>) {
    while n >= 128 {
        out.push((n as u8 & 127) | 128);
        n >>= 7;
    }
    out.push(n as u8);
}
fn name(bytes: &[u8], out: &mut Vec<u8>) {
    unsigned(bytes.len() as u32, out);
    out.extend_from_slice(bytes);
}
fn part(id: u8, data: Vec<u8>, out: &mut Vec<u8>) {
    out.push(id);
    unsigned(data.len() as u32, out);
    out.extend(data);
}
fn fresh(run: SwiftRunBudget) -> (RuntimeControl, AdoptedProof) {
    let mut wasm = b"\0asm\x01\0\0\0".to_vec();
    let mut signatures = vec![36];
    for f in WasiFunction::ALL {
        signatures.push(0x60);
        for fields in [f.parameters(), f.results()] {
            unsigned(fields.len() as u32, &mut signatures);
            for field in fields {
                signatures.push(match field {
                    Type::I32 => 0x7f,
                    Type::I64 => 0x7e,
                    Type::F32 => 0x7d,
                    Type::F64 => 0x7c,
                });
            }
        }
    }
    signatures.extend([0x60, 0, 0, 0x60, 0, 1, 0x7f]);
    part(1, signatures, &mut wasm);
    let mut imports = vec![34];
    for (index, f) in WasiFunction::ALL.iter().enumerate() {
        name(b"wasi_snapshot_preview1", &mut imports);
        name(f.name(), &mut imports);
        imports.extend([0, index as u8]);
    }
    part(2, imports, &mut wasm);
    let mut functions = vec![29];
    functions.extend(std::iter::repeat_n(34, 28));
    functions.push(35);
    part(3, functions, &mut wasm);
    let mut table = vec![1, 0x70, 1];
    unsigned(46_713, &mut table);
    unsigned(46_713, &mut table);
    part(4, table, &mut wasm);
    let mut memory = vec![1, 0];
    unsigned(584, &mut memory);
    part(5, memory, &mut wasm);
    let mut exports = vec![3];
    for (label, kind, index) in [
        (b"memory".as_slice(), 2, 0),
        (b"_initialize".as_slice(), 0, 35),
        (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
    ] {
        name(label, &mut exports);
        exports.extend([kind, index]);
    }
    part(7, exports, &mut wasm);
    let mut bodies = vec![29];
    for _ in 0..28 {
        bodies.extend([2, 0, 0x0b]);
    }
    bodies.extend([4, 0, 0x41, 7, 0x0b]);
    part(10, bodies, &mut wasm);
    let proof = validate_swift_reactor(
        &wasm,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    assert_eq!(proof.observations().validated_bodies, 29);
    assert_eq!(proof.observations().memory_minimum, 584);
    assert_eq!(proof.observations().table_minimum, 46_713);
    RuntimeControl::adopt(proof, run, Instant::now(), Cancellation::default()).unwrap()
}
fn at() -> Cursor {
    Cursor { stage: SwiftRunStage::Wasi, function: Some(62), offset: Some(0x876) }
}
fn budget() -> WasiBudget {
    WasiBudget { one_transfer_bytes: 13, log_bytes: 17, ..WasiBudget::default() }
}
fn make(control: &mut RuntimeControl, grants: WasiGrants, b: WasiBudget) -> AccountedWasi {
    let mut phase = AccountedWasi::prepare(control, at()).unwrap();
    let owner = phase.construct(grants, b, Instant::now(), at()).unwrap();
    phase.complete().unwrap();
    owner
}
fn close(mut c: RuntimeControl, p: AdoptedProof, owner: Option<AccountedWasi>) {
    if let Some(owner) = owner { owner.cleanup(&mut c).unwrap(); }
    c.drop_proof(p).unwrap();
    let end = c.finish_owned_cleanup(None);
    assert_eq!(end.reservations.combined.current, 0);
    assert_eq!(end.reservations.live_tickets, 0);
    assert_eq!(end.cleanup_invariant, None);
}
fn scalar(t: &Type, n: u32) -> Value {
    match t {
        Type::I32 => Value::I32(n as i32),
        Type::I64 => Value::I64(n as i64),
        Type::F32 => Value::F32(n),
        Type::F64 => Value::F64(n as u64),
    }
}
fn errno_or_terminal(result: Result<Errno, SwiftRunFailure>) -> WasiOutcome {
    match result {
        Ok(e) => WasiOutcome::Errno(e),
        Err(e) if e.kind == SwiftRunFailureKind::GuestExit => WasiOutcome::Exit(e.guest_exit.unwrap()),
        Err(e) if e.kind == SwiftRunFailureKind::Wasi => WasiOutcome::Failure(e.wasi_failure.unwrap()),
        Err(e) => panic!("unexpected wrapper terminal: {e:?}"),
    }
}

#[test]
fn review_every_descriptor_default_deny_and_invalid_argument_parity() {
    let mut comparisons = 0;
    for f in WasiFunction::ALL {
        for shape in 0..4 {
            let (mut c, p) = fresh(SwiftRunBudget::default());
            let mut owner = make(&mut c, WasiGrants::default(), budget());
            let mut standalone = WasiContext::new(WasiGrants::default(), budget(), Cancellation::default()).unwrap();
            let mut args: Vec<_> = f.parameters().iter().map(|ty| scalar(ty, if shape == 1 { u32::MAX } else { 0 })).collect();
            if shape == 2 { args.push(Value::I32(0)); }
            if shape == 3 && !args.is_empty() { args[0] = if f.parameters()[0] == Type::I32 { Value::I64(0) } else { Value::I32(0) }; }
            let mut left = [0xa5; 128];
            let mut right = left;
            let expected = standalone.dispatch(f, &args, &mut right);
            let (result, stats) = measure(|| owner.dispatch(&mut c, f, &args, &mut left, at()));
            assert_eq!(stats.attempts, 0);
            assert_eq!(errno_or_terminal(result), expected, "function={f:?} shape={shape}");
            assert_eq!(owner.usage(), standalone.usage());
            assert_eq!(left, right);
            assert_eq!(owner.stdout(), standalone.stdout());
            assert_eq!(owner.stderr(), standalone.stderr());
            assert_eq!(c.usage(Some(owner.usage())).host_calls, 1);
            comparisons += 1;
            close(c, p, Some(owner));
        }
    }
    assert_eq!(comparisons, 136);
    println!("independent_default_deny_parity_cases={comparisons}");
}

#[test]
fn review_each_combined_admission_refuses_before_its_nonuniform_allocation() {
    for ordinal in 0..4 {
        let (sample, sample_proof) = fresh(SwiftRunBudget::default());
        let base = sample.usage(None).reservations.combined.current;
        close(sample, sample_proof, None);
        let sizes = [13usize, 13, 17, 17];
        let ceiling = base + accounted_construction_bytes().unwrap()
            + accounted_header_bytes().unwrap() + sizes[..=ordinal].iter().sum::<usize>() - 1;
        let (mut c, p) = fresh(SwiftRunBudget { combined_bytes: ceiling, ..SwiftRunBudget::default() });
        let mut phase = AccountedWasi::prepare(&mut c, at()).unwrap();
        let (result, stats) = measure(|| phase.construct(WasiGrants::default(), budget(), Instant::now(), at()));
        let failure = result.err().unwrap();
        assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
        assert_eq!(failure.resource, Some(SwiftRunResource::Combined));
        assert_eq!(stats.allocations, ordinal);
        assert_eq!(stats.deallocations, ordinal);
        assert_eq!(stats.allocated_bytes, sizes[..ordinal].iter().sum::<usize>());
        assert_eq!(stats.freed_bytes, stats.allocated_bytes);
        assert_eq!(phase.control.usage(None).reservations.wasi.current, 0);
        assert_eq!(failure.at_failure.reservations.wasi.current,
            accounted_header_bytes().unwrap() + sizes[..ordinal].iter().sum::<usize>());
        phase.complete().unwrap();
        close(c, p, None);
    }
}

#[test]
fn review_real_null_at_each_nonuniform_buffer_allocation() {
    for ordinal in 0..4 {
        let sizes = [13usize, 13, 17, 17];
        let (mut c, p) = fresh(SwiftRunBudget::default());
        let mut phase = AccountedWasi::prepare(&mut c, at()).unwrap();
        let (result, stats) = measure_extended(Some(ordinal), || phase.construct(WasiGrants::default(), budget(), Instant::now(), at()));
        let failure = result.err().unwrap();
        assert_eq!(failure.kind, SwiftRunFailureKind::Allocation);
        assert_eq!(failure.wasi_failure, Some(WasiFailure::Allocation));
        assert_eq!(failure.attempted, sizes[ordinal] as u64);
        assert_eq!(stats.attempts, ordinal + 1);
        assert_eq!(stats.injected_failures, 1);
        assert_eq!(stats.deallocations, ordinal);
        assert_eq!(stats.freed_bytes, sizes[..ordinal].iter().sum::<usize>());
        assert_eq!(phase.control.usage(None).reservations.wasi.current, 0);
        phase.complete().unwrap();
        close(c, p, None);
    }
}

#[test]
fn review_zero_capacity_tickets_and_terminal_cleanup_preserve_meters() {
    for transfer in [false, true] {
        let (mut c, p) = fresh(SwiftRunBudget::default());
        let b = if transfer { WasiBudget { log_bytes: 0, ..budget() } }
            else { WasiBudget { one_transfer_bytes: 0, ..budget() } };
        let (mut owner, stats) = measure(|| make(&mut c, WasiGrants::default(), b));
        assert_eq!(stats.allocations, 2);
        assert_eq!(stats.allocated_bytes, if transfer { 26 } else { 34 });
        assert_eq!(c.usage(None).reservations.live_tickets, 10);
        let failure = owner.dispatch(&mut c, WasiFunction::ProcExit, &[Value::I32(0)], &mut [], at()).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::GuestExit);
        let before = c.usage(Some(owner.usage()));
        c.cancellation().cancel();
        let (result, stats) = measure_extended(Some(0), || owner.cleanup(&mut c));
        result.unwrap();
        assert_eq!(stats.attempts, 0);
        assert_eq!(stats.deallocations, 2);
        let after = c.usage(before.wasi);
        assert_eq!(after.wasi, before.wasi);
        assert_eq!(after.host_calls, before.host_calls);
        assert_eq!(after.cache_work, before.cache_work);
        assert_eq!(after.execution_work, before.execution_work);
        assert_eq!(after.instruction_fuel, before.instruction_fuel);
        assert_eq!(after.reservations.wasi.current, 0);
        assert_eq!(c.check(at()).unwrap_err(), failure);
        close(c, p, None);
    }
}

#[test]
fn review_uncompleted_phase_remains_charged_even_without_constructing() {
    for construct in [false, true] {
        let (mut c, p) = fresh(SwiftRunBudget::default());
        let mut phase = AccountedWasi::prepare(&mut c, at()).unwrap();
        let owner = construct.then(|| phase.construct(WasiGrants::default(), budget(), Instant::now(), at()).unwrap());
        drop(phase);
        if let Some(owner) = owner { owner.cleanup(&mut c).unwrap(); }
        c.drop_proof(p).unwrap();
        let end = c.finish_owned_cleanup(None);
        assert_eq!(end.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
        assert_eq!(end.reservations.construction.current,
            foundation_construction_bytes().unwrap() + accounted_construction_bytes().unwrap());
        assert_eq!(end.reservations.live_tickets, 1);
    }
}

#[test]
fn review_every_actual_dispatch_check_cancellation_rolls_back_outputs() {
    let (mut c, p) = fresh(SwiftRunBudget::default());
    let mut reference = make(&mut c, WasiGrants::default(), budget());
    let mut memory = [0xa5; 32];
    reference.dispatch(&mut c, WasiFunction::ArgsGet, &[Value::I32(0), Value::I32(8)], &mut memory, at()).unwrap();
    let checks = review_hooks::checks(&reference.context);
    assert!(checks >= 6);
    close(c, p, Some(reference));
    for point in 0..checks {
        let (mut c, p) = fresh(SwiftRunBudget::default());
        let mut owner = make(&mut c, WasiGrants::default(), budget());
        review_hooks::cancel_at(&owner.context, point);
        let mut memory = [0xa5; 32];
        let (result, stats) = measure(|| owner.dispatch(&mut c, WasiFunction::ArgsGet, &[Value::I32(0), Value::I32(8)], &mut memory, at()));
        let failure = result.unwrap_err();
        assert_eq!(stats.attempts, 0);
        assert_eq!(failure.kind, SwiftRunFailureKind::Wasi);
        assert_eq!(failure.wasi_failure, Some(WasiFailure::Cancelled));
        assert_eq!(memory, [0xa5; 32], "check ordinal {point}");
        assert_eq!(failure.at_failure.wasi, Some(owner.usage()));
        assert_eq!(failure.at_failure.host_calls, 1);
        let frozen = owner.usage();
        let again = owner.dispatch(&mut c, WasiFunction::RandomGet, &[Value::I32(0), Value::I32(8)], &mut memory, at()).unwrap_err();
        assert_eq!(again, failure);
        assert_eq!(owner.usage(), frozen);
        close(c, p, Some(owner));
    }
    println!("independent_actual_dispatch_check_cancellation_ordinals={checks}");
}

#[test]
fn review_real_shared_prior_counters_survive_host_gate_refusal() {
    let (mut c, p) = fresh(SwiftRunBudget { host_calls: 1, ..SwiftRunBudget::default() });
    let mut owner = make(&mut c, WasiGrants::default(), budget());
    let mut memory = [0xa5; 16];
    owner.dispatch(&mut c, WasiFunction::ArgsSizesGet, &[Value::I32(0), Value::I32(4)], &mut memory, at()).unwrap();
    let usage = owner.usage();
    assert_eq!((usage.calls, usage.transfer_bytes), (1, 8));
    let saved = memory;
    let (result, stats) = measure(|| owner.dispatch(&mut c, WasiFunction::ArgsGet, &[Value::I32(0), Value::I32(8)], &mut memory, at()));
    let failure = result.unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::HostCallLimit);
    assert_eq!(failure.at_failure.wasi, Some(usage));
    assert_eq!(failure.at_failure.host_calls, 1);
    assert_eq!(owner.usage(), usage);
    assert_eq!(stats.attempts, 0);
    assert_eq!(memory, saved);
    close(c, p, Some(owner));
}

#[test]
fn review_foreign_dispatch_and_cleanup_cannot_create_free_room() {
    let (mut c, p) = fresh(SwiftRunBudget::default());
    let mut owner = make(&mut c, WasiGrants::default(), budget());
    let (mut foreign, other) = fresh(SwiftRunBudget::default());
    let before = c.usage(None).reservations;
    let foreign_before = foreign.usage(None).reservations;
    let observation = owner.usage();
    let mut memory = [0xa5; 16];
    let failure = owner.dispatch(&mut foreign, WasiFunction::RandomGet, &[Value::I32(0), Value::I32(8)], &mut memory, at()).unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
    assert_eq!(failure.at_failure.wasi, Some(observation));
    assert_eq!(owner.usage(), observation);
    let (result, stats) = measure(|| owner.cleanup(&mut foreign));
    assert!(result.is_err());
    assert_eq!(stats.attempts, 0);
    assert_eq!(stats.deallocations, 4);
    assert_eq!(stats.freed_bytes, 60);
    assert_eq!(c.usage(None).reservations, before);
    assert_eq!(foreign.usage(None).reservations, foreign_before);
    foreign.drop_proof(other).unwrap();
    let foreign_end = foreign.finish_owned_cleanup(None);
    assert_eq!(foreign_end.reservations.combined.current, 0);
    assert_eq!(foreign_end.cleanup_invariant, Some(SwiftCleanupInvariant::ReservationOwner));
    c.drop_proof(p).unwrap();
    let end = c.finish_owned_cleanup(None);
    assert_eq!(end.reservations.wasi.current, accounted_header_bytes().unwrap() + 60);
    assert_eq!(end.reservations.live_tickets, 5);
}

#[test]
fn review_expired_carried_wasi_deadline_fails_before_any_header_or_payload() {
    let (mut c, p) = fresh(SwiftRunBudget::default());
    let mut phase = AccountedWasi::prepare(&mut c, at()).unwrap();
    let earlier = Instant::now().checked_sub(std::time::Duration::from_millis(10)).unwrap();
    let (result, stats) = measure(|| phase.construct(WasiGrants::default(), WasiBudget { deadline_ms: 1, ..budget() }, earlier, at()));
    let failure = result.err().unwrap();
    assert_eq!(failure.kind, SwiftRunFailureKind::Deadline);
    assert_eq!(failure.deadline_origin, SwiftDeadlineOrigin::Wasi);
    assert!(failure.at_failure.deadline_overshoot_micros > 0);
    assert_eq!(stats.attempts, 0);
    assert_eq!(phase.control.usage(None).reservations.wasi.current, 0);
    phase.complete().unwrap();
    close(c, p, None);
}

#[test]
fn review_adapter_terminal_precedes_postdispatch_cancellation() {
    for code in [0u32, 1, u32::MAX] {
        let (mut c, p) = fresh(SwiftRunBudget::default());
        let mut owner = make(&mut c, WasiGrants::default(), budget());
        owner.test.cancel_after = true;
        let (result, stats) = measure(|| owner.dispatch(&mut c, WasiFunction::ProcExit, &[Value::I32(code as i32)], &mut [], at()));
        let failure = result.unwrap_err();
        assert_eq!(stats.attempts, 0);
        assert_eq!(failure.kind, SwiftRunFailureKind::GuestExit);
        assert_eq!(failure.guest_exit, Some(code));
        assert_eq!(failure.at_failure.wasi, Some(owner.usage()));
        assert_eq!(failure.at_failure.host_calls, 1);
        assert_eq!(c.check(at()).unwrap_err(), failure);
        close(c, p, Some(owner));
    }
}

#[test]
fn review_cleanup_first_foreign_control_captures_actual_wasi_observation() {
    let (mut c, p) = fresh(SwiftRunBudget::default());
    let mut owner = make(&mut c, WasiGrants::default(), budget());
    owner.dispatch(&mut c, WasiFunction::ArgsSizesGet,
        &[Value::I32(0), Value::I32(4)], &mut [0xa5; 16], at()).unwrap();
    let actual = owner.usage();
    assert_eq!((actual.calls, actual.transfer_bytes), (1, 8));
    let (mut foreign, other) = fresh(SwiftRunBudget::default());
    let (result, stats) = measure(|| owner.cleanup(&mut foreign));
    let failure = result.unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
    assert_eq!(stats.attempts, 0);
    assert_eq!(stats.deallocations, 4);
    // This is the required immutable first diagnostic, not a later summed snapshot.
    assert_eq!(failure.at_failure.wasi, Some(actual));
    foreign.drop_proof(other).unwrap();
    c.drop_proof(p).unwrap();
}

#[cfg(review_borrow_use)]
fn review_cannot_use_control_before_phase_completion(control: &mut RuntimeControl) {
    let phase = AccountedWasi::prepare(control, at()).unwrap();
    let _ = control.usage(None);
    phase.complete().unwrap();
}

#[cfg(review_borrow_drop)]
fn review_cannot_drop_control_before_phase_completion(mut control: RuntimeControl) {
    let phase = AccountedWasi::prepare(&mut control, at()).unwrap();
    drop(control);
    phase.complete().unwrap();
}
