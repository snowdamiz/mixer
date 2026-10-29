//! Original ordinary-ABI synthetic validation and private composition tests.
//! No target reactor memory, initialization or corpus execution is attempted.
use super::*;
use crate::experimental_swift_reactor::allocation_tests::{
    measure, measure_extended, AllocationStats,
};
use crate::experimental_swift_reactor::control::{
    foundation_construction_bytes, AdoptedProof, Live, SwiftCleanupInvariant, SwiftDeadlineOrigin,
    SwiftRunBudget, SwiftRunResource, SwiftRunStage, SwiftRunUsage, Work,
};
use crate::experimental_swift_reactor::{
    validate_swift_reactor, SwiftValidationBudget, ValidatedSwiftReactor,
};
use crate::{Cancellation, Type};
use std::time::Duration;

fn leb(mut n: u32, output: &mut Vec<u8>) {
    loop {
        let low = (n & 127) as u8;
        n >>= 7;
        output.push(low | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return;
        }
    }
}
fn text(value: &[u8], output: &mut Vec<u8>) {
    leb(value.len() as u32, output);
    output.extend_from_slice(value);
}
fn section(id: u8, data: &[u8], output: &mut Vec<u8>) {
    output.push(id);
    leb(data.len() as u32, output);
    output.extend_from_slice(data);
}
fn signature(parameters: &[Type], results: &[Type], output: &mut Vec<u8>) {
    output.push(0x60);
    for types in [parameters, results] {
        leb(types.len() as u32, output);
        for ty in types {
            output.push(match ty {
                Type::I32 => 0x7f,
                Type::I64 => 0x7e,
                Type::F32 => 0x7d,
                Type::F64 => 0x7c,
            });
        }
    }
}
fn proof() -> ValidatedSwiftReactor {
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![36];
    for function in WasiFunction::ALL {
        signature(function.parameters(), function.results(), &mut types);
    }
    signature(&[], &[], &mut types);
    signature(&[], &[Type::I32], &mut types);
    section(1, &types, &mut bytes);
    let mut imports = vec![34];
    for (index, function) in WasiFunction::ALL.into_iter().enumerate() {
        text(b"wasi_snapshot_preview1", &mut imports);
        text(function.name(), &mut imports);
        imports.push(0);
        leb(index as u32, &mut imports);
    }
    section(2, &imports, &mut bytes);
    let mut functions = vec![29];
    functions.extend([34; 28]);
    functions.push(35);
    section(3, &functions, &mut bytes);
    let mut table = vec![1, 0x70, 1];
    leb(46_713, &mut table);
    leb(46_713, &mut table);
    section(4, &table, &mut bytes);
    let mut memory = vec![1, 0];
    leb(584, &mut memory);
    section(5, &memory, &mut bytes);
    let mut exports = vec![3];
    for (name, kind, index) in [
        (b"memory".as_slice(), 2, 0),
        (b"_initialize".as_slice(), 0, 35),
        (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
    ] {
        text(name, &mut exports);
        exports.push(kind);
        leb(index, &mut exports);
    }
    section(7, &exports, &mut bytes);
    let mut code = vec![29];
    for _ in 0..28 {
        code.extend([2, 0, 0x0b]);
    }
    code.extend([4, 0, 0x41, 0, 0x0b]);
    section(10, &code, &mut bytes);
    validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap()
}
fn cursor() -> Cursor {
    Cursor {
        stage: SwiftRunStage::Wasi,
        function: Some(62),
        offset: Some(501),
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
fn small() -> WasiBudget {
    WasiBudget {
        one_transfer_bytes: 1024,
        log_bytes: 1024,
        ..WasiBudget::default()
    }
}
fn adopt(budget: SwiftRunBudget) -> (RuntimeControl, AdoptedProof) {
    RuntimeControl::adopt(proof(), budget, Instant::now(), Cancellation::default()).unwrap()
}
fn construct(
    control: &mut RuntimeControl,
    grants: WasiGrants,
    budget: WasiBudget,
) -> Result<AccountedWasi, SwiftRunFailure> {
    let mut phase = AccountedWasi::prepare(control, cursor())?;
    let result = phase.construct(grants, budget, Instant::now(), cursor());
    phase.complete().unwrap();
    result
}
fn clean(mut control: RuntimeControl, proof: AdoptedProof, owner: AccountedWasi) -> SwiftRunUsage {
    let usage = owner.usage();
    owner.cleanup(&mut control).unwrap();
    assert_eq!(control.usage(Some(usage)).reservations.wasi.current, 0);
    control.drop_proof(proof).unwrap();
    control.finish_owned_cleanup(Some(usage))
}
fn empty(usage: SwiftRunUsage) {
    assert_eq!(usage.reservations.combined.current, 0);
    assert_eq!(usage.reservations.live_tickets, 0);
    assert_eq!(usage.cleanup_invariant, None);
}
fn no_alloc(stats: AllocationStats) {
    assert_eq!(stats.allocations, 0);
    assert_eq!(stats.reallocations, 0);
}

#[test]
fn cache_control_boundaries_retain_actual_dispatch_observations() {
    for point in 0..10 {
        let budget = SwiftRunBudget::default();
        let (mut control, proof) = adopt(budget);
        let mut owner = construct(&mut control, grants(), small()).unwrap();
        let initial = owner.usage();
        let mut memory = [0u8; 8];
        for _ in 0..2 {
            owner
                .dispatch(
                    &mut control,
                    WasiFunction::ArgsSizesGet,
                    &[i(0), i(4)],
                    &mut memory,
                    cursor(),
                )
                .unwrap();
        }
        let observed = owner.checked_usage(&mut control, cursor()).unwrap();
        assert_eq!(observed, owner.usage());
        assert_eq!(observed.calls, 2);
        assert!(observed.work > initial.work && observed.transfer_bytes > initial.transfer_bytes);
        let before = control.usage(Some(observed));
        let ((failure, expected), stats) = measure(|| {
            let wasi = Some(owner.checked_usage(&mut control, cursor()).unwrap());
            match point {
                0 => (
                    control
                        .work_with_wasi(Work::Cache, budget.cache_work + 1, cursor(), wasi)
                        .unwrap_err(),
                    SwiftRunFailureKind::WorkExhausted,
                ),
                1 => (
                    control
                        .admit_with_wasi(
                            SwiftReservationCategory::Cache,
                            budget.cache_bytes + 1,
                            cursor(),
                            wasi,
                        )
                        .unwrap_err(),
                    SwiftRunFailureKind::CategoryExhausted,
                ),
                2 => (
                    control
                        .admit_with_wasi(
                            SwiftReservationCategory::Shared,
                            budget.combined_bytes - before.reservations.combined.current + 1,
                            cursor(),
                            wasi,
                        )
                        .unwrap_err(),
                    SwiftRunFailureKind::CombinedExhausted,
                ),
                3 => (
                    control
                        .admit_cache_entry_with_wasi(budget.cache_entry_bytes + 1, cursor(), wasi)
                        .unwrap_err(),
                    SwiftRunFailureKind::ResourceExhausted,
                ),
                4 => (
                    control
                        .enlarge_construction_with_wasi(budget.combined_bytes, cursor(), wasi)
                        .unwrap_err(),
                    SwiftRunFailureKind::CombinedExhausted,
                ),
                5 => (
                    control
                        .exact_capacity_with_wasi(1, 2, cursor(), wasi)
                        .unwrap_err(),
                    SwiftRunFailureKind::Allocation,
                ),
                6 => (
                    control
                        .add_live_with_wasi(
                            Live::CacheEntries,
                            budget.cache_entries + 1,
                            cursor(),
                            wasi,
                        )
                        .unwrap_err(),
                    SwiftRunFailureKind::ResourceExhausted,
                ),
                7 => (
                    control
                        .remove_live_with_wasi(Live::ActivePins, 1, wasi)
                        .unwrap_err(),
                    SwiftRunFailureKind::Invariant,
                ),
                8 => (
                    control
                        .end_construction_phase_with_wasi((), 0, wasi)
                        .unwrap_err(),
                    SwiftRunFailureKind::Invariant,
                ),
                9 => {
                    control.cancellation().cancel();
                    (
                        control
                            .work_with_wasi(Work::Cache, 1, cursor(), wasi)
                            .unwrap_err(),
                        SwiftRunFailureKind::Cancelled,
                    )
                }
                _ => unreachable!(),
            }
        });
        no_alloc(stats);
        assert_eq!(failure.kind, expected, "boundary {point}");
        assert_eq!(failure.at_failure.wasi, Some(observed), "boundary {point}");
        let after = control.usage(Some(observed));
        assert_eq!(after.reservations, before.reservations);
        assert_eq!(after.live, before.live);
        assert_eq!(after.cache_work, before.cache_work);
        assert_eq!(after.host_calls, before.host_calls);
        // Borrowed preflight remains usable for terminal cleanup; it does not
        // perform a cancellation/work check or replace the first failure.
        assert_eq!(
            owner.checked_usage(&mut control, cursor()).unwrap(),
            observed
        );
        assert_eq!(
            control
                .work_with_wasi(Work::Cache, 0, cursor(), Some(WasiUsage::default()))
                .unwrap_err(),
            failure
        );
        owner.cleanup(&mut control).unwrap();
        control.drop_proof_with_wasi(proof, Some(observed)).unwrap();
        assert_eq!(control.check(cursor()).unwrap_err(), failure);
        let final_usage = control.finish_owned_cleanup(Some(observed));
        assert_eq!(final_usage.reservations.combined.current, 0);
        assert_eq!(final_usage.reservations.live_tickets, 0);
    }
}

#[test]
fn borrowed_wasi_pairing_rejects_foreign_identity_without_mixed_observations() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, grants(), small()).unwrap();
    owner
        .dispatch(
            &mut control,
            WasiFunction::ArgsSizesGet,
            &[i(0), i(4)],
            &mut [0u8; 8],
            cursor(),
        )
        .unwrap();
    let observed = owner.usage();
    let (mut other, other_proof) = adopt(SwiftRunBudget::default());
    let before = control.usage(Some(observed)).reservations;
    let other_before = other.usage(None).reservations;
    let (failure, stats) = measure(|| owner.checked_usage(&mut other, cursor()).unwrap_err());
    no_alloc(stats);
    assert_eq!(stats.deallocations, 0);
    assert_eq!(failure.code, "swift_run_reservation_owner");
    assert_eq!(failure.at_failure.wasi, None);
    assert_eq!(other.usage(None).reservations, other_before);
    assert_eq!(control.usage(Some(observed)).reservations, before);
    assert_eq!(
        owner.checked_usage(&mut control, cursor()).unwrap(),
        observed
    );
    empty(clean(control, proof, owner));
    other.drop_proof(other_proof).unwrap();
    let drained = other.finish_owned_cleanup(None);
    assert_eq!(drained.reservations.combined.current, 0);
    assert_eq!(drained.reservations.live_tickets, 0);
}
fn i(value: u32) -> Value {
    Value::I32(value as i32)
}

#[test]
fn genuine_consumed_abi_proof_preallocation_layout_and_exact_four_capacities() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    assert_eq!(proof.proof().observations().validated_bodies, 29);
    assert_eq!(proof.proof().observations().memory_minimum, 584);
    assert_eq!(proof.proof().observations().table_minimum, 46_713);
    let before = control.usage(None);
    let (owner, stats) = measure(|| construct(&mut control, grants(), small()).unwrap());
    assert_eq!(stats.allocations, 4);
    assert_eq!(stats.reallocations, 0);
    assert_eq!(stats.allocated_bytes, 4096);
    let usage = control.usage(Some(owner.usage()));
    assert_eq!(
        usage.reservations.construction.current,
        before.reservations.construction.current
    );
    assert_eq!(
        usage.reservations.construction.peak,
        before.reservations.construction.current + accounted_construction_bytes().unwrap()
    );
    assert_eq!(
        usage.reservations.wasi.current,
        accounted_header_bytes().unwrap() + 4096
    );
    assert_eq!(
        usage.reservations.live_tickets,
        before.reservations.live_tickets + 5
    );
    assert_eq!(usage.reservations.peak_tickets, 10);
    let context = &owner.context;
    for bytes in [
        &context.scratch,
        &context.rollback,
        &context.stdout,
        &context.stderr,
    ] {
        assert_eq!(bytes.capacity(), 1024);
        assert!(bytes.is_empty());
    }
    assert_eq!(context.deadline, control.deadline());
    let cancellation = Cancellation::default();
    let (standalone, standalone_stats) =
        measure(|| WasiContext::new(grants(), small(), cancellation).unwrap());
    assert_eq!(standalone_stats.allocations, 4);
    assert_eq!(standalone_stats.reallocations, 0);
    assert_eq!(standalone_stats.allocated_bytes, 4096);
    assert_eq!(context.usage(), standalone.usage());
    println!("accounted_wasi_layout context={} context_align={} owner={} owner_align={} ticket={} option_ticket={} phase={} partial={} fixed_header={} construction_extra={} foundation={}", size_of::<WasiContext>(), std::mem::align_of::<WasiContext>(), size_of::<AccountedWasi>(), std::mem::align_of::<AccountedWasi>(), size_of::<ReservationTicket>(), size_of::<Option<ReservationTicket>>(), size_of::<WasiConstructionPhase<'static>>(), size_of::<Partial>(), accounted_header_bytes().unwrap(), accounted_construction_bytes().unwrap(), foundation_construction_bytes().unwrap());
    let (cleanup, stats) = measure(|| clean(control, proof, owner));
    no_alloc(stats);
    assert!(stats.deallocations >= 4);
    empty(cleanup);
}

#[test]
fn every_constructor_cancellation_and_deadline_boundary_drops_actual_partial_buffers() {
    for deadline in [false, true] {
        for index in 0..4 {
            for after in [false, true] {
                let (mut control, proof) = adopt(SwiftRunBudget::default());
                let mut phase = AccountedWasi::prepare(&mut control, cursor()).unwrap();
                if deadline {
                    phase.test.expire_at = Some((index, after));
                } else {
                    phase.test.cancel_at = Some((index, after));
                }
                let budget = if deadline {
                    WasiBudget {
                        deadline_ms: 2,
                        ..small()
                    }
                } else {
                    small()
                };
                let (result, stats) =
                    measure(|| phase.construct(grants(), budget, Instant::now(), cursor()));
                let failure = result.err().unwrap();
                assert_eq!(
                    failure.kind,
                    if deadline {
                        SwiftRunFailureKind::Deadline
                    } else {
                        SwiftRunFailureKind::Cancelled
                    }
                );
                assert_eq!(phase.test.reached, index * 2 + usize::from(after) + 1);
                assert_eq!(stats.allocations, index + usize::from(after));
                assert_eq!(stats.deallocations, stats.allocations);
                assert_eq!(stats.allocated_bytes, stats.freed_bytes);
                assert!(
                    failure.at_failure.reservations.wasi.current
                        >= accounted_header_bytes().unwrap()
                );
                phase.complete().unwrap();
                assert_eq!(control.usage(None).reservations.wasi.current, 0);
                control.drop_proof(proof).unwrap();
                empty(control.finish_owned_cleanup(None));
            }
        }
    }
}

#[test]
fn every_real_allocator_failure_drops_all_earlier_storage_before_refunds() {
    for ordinal in 0..4 {
        let (mut control, proof) = adopt(SwiftRunBudget::default());
        let mut phase = AccountedWasi::prepare(&mut control, cursor()).unwrap();
        let (result, stats) = measure_extended(Some(ordinal), || {
            phase.construct(grants(), small(), Instant::now(), cursor())
        });
        let failure = result.err().unwrap();
        assert_eq!(failure.kind, SwiftRunFailureKind::Allocation);
        assert_eq!(failure.wasi_failure, Some(WasiFailure::Allocation));
        assert_eq!(failure.attempted, 1024);
        assert_eq!(stats.injected_failures, 1);
        assert_eq!(stats.attempts, ordinal + 1);
        assert_eq!(stats.allocations, ordinal + 1);
        assert_eq!(stats.reallocations, 0);
        assert_eq!(stats.deallocations, ordinal);
        assert_eq!(stats.freed_bytes, ordinal * 1024);
        assert_eq!(stats.allocated_bytes, (ordinal + 1) * 1024);
        assert_eq!(phase.control.usage(None).reservations.wasi.current, 0);
        assert!(failure.at_failure.reservations.wasi.current > 0);
        phase.complete().unwrap();
        control.drop_proof(proof).unwrap();
        empty(control.finish_owned_cleanup(None));
    }
}

#[test]
fn unexpected_actual_capacity_is_terminal_and_storage_stays_charged_until_drop() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let ticket = control
        .admit(SwiftReservationCategory::Wasi, 8, cursor())
        .unwrap();
    let mut actual = Vec::<u8>::new();
    actual.try_reserve_exact(9).unwrap();
    let failure = control
        .exact_capacity(8, actual.capacity(), cursor())
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Allocation);
    assert_eq!(failure.resource, Some(SwiftRunResource::ExactCapacity));
    assert_eq!(failure.attempted, 8);
    assert_eq!(failure.observed_capacity, Some(9));
    assert_eq!(control.usage(None).reservations.wasi.current, 8);
    let (result, stats) = measure(|| control.drop_reserved(actual, ticket));
    result.unwrap();
    no_alloc(stats);
    assert_eq!(stats.deallocations, 1);
    assert_eq!(stats.freed_bytes, 9);
    assert_eq!(control.usage(None).reservations.wasi.current, 0);
    control.drop_proof(proof).unwrap();
    empty(control.finish_owned_cleanup(None));
}

#[test]
fn admission_denies_before_payload_allocation_and_preserves_category_vs_combined() {
    let proof = proof();
    let usage = proof.usage();
    let baseline = usage.source_bytes
        + usage.metadata_reserved
        + size_of::<RuntimeControl>()
        + Cancellation::requested_backing_layout().size()
        + foundation_construction_bytes().unwrap();
    let before_payload_limit = baseline
        .max(foundation_construction_bytes().unwrap() + accounted_construction_bytes().unwrap());
    for limit in [
        before_payload_limit,
        baseline
            + accounted_construction_bytes().unwrap()
            + accounted_header_bytes().unwrap()
            + 2048,
    ] {
        let budget = SwiftRunBudget {
            combined_bytes: limit,
            ..SwiftRunBudget::default()
        };
        let (mut control, adopted) = adopt(budget);
        let (result, stats) = measure(|| construct(&mut control, grants(), small()));
        let failure = result.err().unwrap();
        assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
        assert_eq!(failure.resource, Some(SwiftRunResource::Combined));
        assert_eq!(
            stats.allocations,
            if limit == before_payload_limit { 0 } else { 2 }
        );
        assert_eq!(stats.allocations, stats.deallocations);
        assert_eq!(control.usage(None).reservations.wasi.current, 0);
        control.drop_proof(adopted).unwrap();
        empty(control.finish_owned_cleanup(None));
    }
    // Category fails independently, although the default combined budget fits.
    let (mut control, adopted) = adopt(SwiftRunBudget {
        state_bytes: 0,
        ..SwiftRunBudget::default()
    });
    let failure = control
        .admit(SwiftReservationCategory::State, 1, cursor())
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::CategoryExhausted);
    assert_eq!(
        failure.resource,
        Some(SwiftRunResource::Reservation(
            SwiftReservationCategory::State
        ))
    );
    control.drop_proof(adopted).unwrap();
    empty(control.finish_owned_cleanup(None));
}

#[test]
fn phase_completion_restores_previous_bound_and_omission_never_fakes_zero() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let previous = foundation_construction_bytes().unwrap() + 123;
    control.enlarge_construction(previous, cursor()).unwrap();
    let owner = construct(&mut control, grants(), small()).unwrap();
    assert_eq!(
        control.usage(None).reservations.construction.current,
        previous
    );
    owner.cleanup(&mut control).unwrap();
    control
        .end_construction_phase([0u8; 123], foundation_construction_bytes().unwrap())
        .unwrap();
    control.drop_proof(proof).unwrap();
    empty(control.finish_owned_cleanup(None));

    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let owner = {
        let mut phase = AccountedWasi::prepare(&mut control, cursor()).unwrap();
        phase
            .construct(grants(), small(), Instant::now(), cursor())
            .unwrap()
    };
    owner.cleanup(&mut control).unwrap();
    control.drop_proof(proof).unwrap();
    let observation = control.finish_owned_cleanup(None);
    assert_eq!(
        observation.cleanup_invariant,
        Some(SwiftCleanupInvariant::ConstructionBound)
    );
    assert_eq!(
        observation.reservations.construction.current,
        foundation_construction_bytes().unwrap() + accounted_construction_bytes().unwrap()
    );
    assert_eq!(observation.reservations.live_tickets, 1);
}

#[test]
fn phase_is_one_shot_and_zero_buffer_budgets_allocate_nothing() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut phase = AccountedWasi::prepare(&mut control, cursor()).unwrap();
    let (owner, stats) = measure(|| {
        phase
            .construct(
                WasiGrants::default(),
                WasiBudget {
                    one_transfer_bytes: 0,
                    log_bytes: 0,
                    ..small()
                },
                Instant::now(),
                cursor(),
            )
            .unwrap()
    });
    no_alloc(stats);
    let failure = phase
        .construct(grants(), small(), Instant::now(), cursor())
        .err()
        .unwrap();
    assert_eq!(failure.code, "swift_run_wasi_construct_once");
    phase.complete().unwrap();
    assert_eq!(owner.context.scratch.capacity(), 0);
    empty(clean(control, proof, owner));
}

#[test]
fn ordinary_errno_and_captures_preserve_standalone_counters_and_memory_exactly() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, grants(), small()).unwrap();
    let mut standalone = WasiContext::new(grants(), small(), Cancellation::default()).unwrap();
    let mut left = [0xa5; 128];
    left[..4].copy_from_slice(&32u32.to_le_bytes());
    left[4..8].copy_from_slice(&5u32.to_le_bytes());
    left[32..37].copy_from_slice(b"hello");
    let mut right = left;
    for (function, args) in [
        (WasiFunction::ArgsSizesGet, vec![i(8), i(12)]),
        (WasiFunction::ArgsGet, vec![i(16), i(24)]),
        (WasiFunction::FdWrite, vec![i(1), i(0), i(1), i(120)]),
        (WasiFunction::FdWrite, vec![i(2), i(0), i(1), i(120)]),
        (WasiFunction::PollOneoff, vec![i(0), i(0), i(0), i(0)]),
        (WasiFunction::FdClose, vec![i(1)]),
        (WasiFunction::FdWrite, vec![i(1), i(0), i(1), i(120)]),
    ] {
        let expected = standalone.dispatch(function, &args, &mut right);
        let (actual, stats) =
            measure(|| owner.dispatch(&mut control, function, &args, &mut left, cursor()));
        no_alloc(stats);
        assert_eq!(actual.map(WasiOutcome::Errno).unwrap(), expected);
        assert_eq!(left, right);
        assert_eq!(owner.usage(), standalone.usage());
        assert_eq!(owner.stdout(), standalone.stdout());
        assert_eq!(owner.stderr(), standalone.stderr());
    }
    assert_eq!(owner.stdout(), b"hello");
    assert_eq!(owner.stderr(), b"hello");
    assert_eq!(control.usage(Some(owner.usage())).host_calls, 7);
    empty(clean(control, proof, owner));
}

#[test]
fn actual_os_random_clocks_and_default_denials_use_closed_existing_services() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, grants(), small()).unwrap();
    let mut memory = [0xa5; 1024];
    let (result, stats) = measure(|| {
        owner.dispatch(
            &mut control,
            WasiFunction::RandomGet,
            &[i(0), i(512)],
            &mut memory,
            cursor(),
        )
    });
    no_alloc(stats);
    assert_eq!(result.unwrap(), Errno::Success);
    assert_ne!(memory[..512], [0xa5; 512]);
    assert_eq!(owner.usage().random_bytes, 512);
    for clock in [0, 1] {
        assert_eq!(
            owner
                .dispatch(
                    &mut control,
                    WasiFunction::ClockTimeGet,
                    &[i(clock), Value::I64(0), i(512)],
                    &mut memory,
                    cursor()
                )
                .unwrap(),
            Errno::Success
        );
        assert!(u64::from_le_bytes(memory[512..520].try_into().unwrap()) > 0);
        assert_eq!(
            owner
                .dispatch(
                    &mut control,
                    WasiFunction::ClockResGet,
                    &[i(clock), i(512)],
                    &mut memory,
                    cursor()
                )
                .unwrap(),
            Errno::Success
        );
    }
    empty(clean(control, proof, owner));

    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, WasiGrants::default(), small()).unwrap();
    let mut memory = [0xa5; 32];
    for (function, args, errno) in [
        (WasiFunction::RandomGet, vec![i(0), i(8)], Errno::Notcapable),
        (
            WasiFunction::ClockTimeGet,
            vec![i(0), Value::I64(0), i(0)],
            Errno::Notcapable,
        ),
        (WasiFunction::FdClose, vec![i(1)], Errno::Badf),
    ] {
        assert_eq!(
            owner
                .dispatch(&mut control, function, &args, &mut memory, cursor())
                .unwrap(),
            errno
        );
    }
    assert_eq!(memory, [0xa5; 32]);
    assert_eq!(owner.usage().random_bytes, 0);
    assert_eq!(owner.usage().transfer_bytes, 0);
    assert_eq!(owner.usage().calls, 3);
    assert_eq!(owner.usage().failures, 3);
    empty(clean(control, proof, owner));
}

#[test]
fn exact_wasi_terminal_failure_and_guest_exit_are_sticky_without_later_work() {
    for exit in [None, Some(0), Some(17)] {
        let (mut control, proof) = adopt(SwiftRunBudget::default());
        let mut owner = construct(&mut control, grants(), small()).unwrap();
        let mut memory = [0xa5; 32];
        let failure = if let Some(code) = exit {
            owner
                .dispatch(
                    &mut control,
                    WasiFunction::ProcExit,
                    &[i(code)],
                    &mut memory,
                    cursor(),
                )
                .unwrap_err()
        } else {
            owner
                .dispatch(
                    &mut control,
                    WasiFunction::ClockTimeGet,
                    &[i(0), i(0), i(0)],
                    &mut memory,
                    cursor(),
                )
                .unwrap_err()
        };
        assert_eq!(
            failure.kind,
            if exit.is_some() {
                SwiftRunFailureKind::GuestExit
            } else {
                SwiftRunFailureKind::Wasi
            }
        );
        assert_eq!(failure.guest_exit, exit);
        assert_eq!(
            failure.wasi_failure,
            if exit.is_none() {
                Some(WasiFailure::InvalidArguments)
            } else {
                None
            }
        );
        assert_eq!(failure.at_failure.wasi, Some(owner.usage()));
        assert_eq!(failure.at_failure.host_calls, 1);
        let before = owner.usage();
        owner.context.cancellation.cancel();
        let (again, stats) = measure(|| {
            owner.dispatch(
                &mut control,
                WasiFunction::RandomGet,
                &[i(0), i(32)],
                &mut memory,
                cursor(),
            )
        });
        no_alloc(stats);
        assert_eq!(again.unwrap_err(), failure);
        assert_eq!(owner.usage(), before);
        assert_eq!(memory, [0xa5; 32]);
        assert_eq!(control.usage(Some(before)).host_calls, 1);
        let (cleanup, stats) = measure(|| clean(control, proof, owner));
        no_alloc(stats);
        empty(cleanup);
    }
}

#[test]
fn every_reachable_wasi_budget_failure_retains_exact_data_and_original_precedence() {
    use super::super::Resource;
    for (budget, function, args, expected) in [
        (
            WasiBudget {
                calls: 0,
                ..small()
            },
            WasiFunction::ArgsSizesGet,
            vec![i(0), i(4)],
            WasiFailure::Budget(Resource::Calls),
        ),
        (
            WasiBudget { work: 0, ..small() },
            WasiFunction::ArgsSizesGet,
            vec![i(0), i(4)],
            WasiFailure::Budget(Resource::Work),
        ),
        (
            WasiBudget {
                transfer_bytes: 0,
                ..small()
            },
            WasiFunction::ArgsSizesGet,
            vec![i(0), i(4)],
            WasiFailure::Budget(Resource::Transfer),
        ),
        (
            WasiBudget {
                one_transfer_bytes: 0,
                ..small()
            },
            WasiFunction::ArgsSizesGet,
            vec![i(0), i(4)],
            WasiFailure::Budget(Resource::TransferSize),
        ),
        (
            WasiBudget {
                iovecs: 0,
                ..small()
            },
            WasiFunction::FdWrite,
            vec![i(1), i(0), i(1), i(28)],
            WasiFailure::Budget(Resource::Iovecs),
        ),
        (
            WasiBudget {
                calls: 0,
                ..small()
            },
            WasiFunction::ClockTimeGet,
            vec![i(0), i(0), i(0)],
            WasiFailure::InvalidArguments,
        ),
    ] {
        let (mut control, proof) = adopt(SwiftRunBudget::default());
        let mut owner = construct(&mut control, grants(), budget).unwrap();
        let mut memory = [0xa5; 32];
        let failure = owner
            .dispatch(&mut control, function, &args, &mut memory, cursor())
            .unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::Wasi);
        assert_eq!(failure.wasi_failure, Some(expected));
        assert_eq!(failure.at_failure.wasi, Some(owner.usage()));
        assert_eq!(failure.at_failure.host_calls, 1);
        assert_eq!(memory, [0xa5; 32]);
        let before = owner.usage();
        let (again, stats) = measure(|| {
            owner.dispatch(
                &mut control,
                WasiFunction::RandomGet,
                &[i(0), i(8)],
                &mut memory,
                cursor(),
            )
        });
        no_alloc(stats);
        assert_eq!(again.unwrap_err(), failure);
        assert_eq!(owner.usage(), before);
        empty(clean(control, proof, owner));
    }
}

#[test]
fn invalid_wasi_budget_precedes_buffer_admission_and_actual_cleanup_preserves_counters() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let (result, stats) = measure(|| {
        construct(
            &mut control,
            grants(),
            WasiBudget {
                calls: 32_769,
                ..small()
            },
        )
    });
    no_alloc(stats);
    let failure = result.err().unwrap();
    assert_eq!(failure.kind, SwiftRunFailureKind::InvalidBudget);
    assert_eq!(failure.wasi_failure, Some(WasiFailure::InvalidBudget));
    assert_eq!(control.usage(None).reservations.wasi.current, 0);
    control.drop_proof(proof).unwrap();
    empty(control.finish_owned_cleanup(None));

    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, grants(), small()).unwrap();
    let mut memory = [0xa5; 8];
    owner
        .dispatch(
            &mut control,
            WasiFunction::ArgsSizesGet,
            &[i(0), i(4)],
            &mut memory,
            cursor(),
        )
        .unwrap();
    let wasi = owner.usage();
    let before = control.usage(Some(wasi));
    owner.context.cancellation.cancel();
    let (result, stats) = measure(|| owner.cleanup(&mut control));
    result.unwrap();
    no_alloc(stats);
    assert_eq!(stats.deallocations, 4);
    assert_eq!(stats.freed_bytes, 4096);
    let after = control.usage(Some(wasi));
    assert_eq!(after.host_calls, before.host_calls);
    assert_eq!(after.execution_work, before.execution_work);
    assert_eq!(after.cache_work, before.cache_work);
    assert_eq!(after.instruction_fuel, before.instruction_fuel);
    assert_eq!(after.wasi, before.wasi);
    assert_eq!(after.reservations.wasi.current, 0);
    control.drop_proof(proof).unwrap();
    empty(control.finish_owned_cleanup(Some(wasi)));
}

#[test]
fn foreign_control_cannot_enter_context_or_change_its_authoritative_counters() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, grants(), small()).unwrap();
    let (mut foreign, foreign_proof) = adopt(SwiftRunBudget::default());
    let wasi = owner.usage();
    let mut memory = [0xa5; 8];
    let (result, stats) = measure(|| {
        owner.dispatch(
            &mut foreign,
            WasiFunction::ArgsSizesGet,
            &[i(0), i(4)],
            &mut memory,
            cursor(),
        )
    });
    no_alloc(stats);
    let failure = result.unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
    assert_eq!(failure.code, "swift_run_reservation_owner");
    assert_eq!(failure.at_failure.wasi, Some(wasi));
    assert_eq!(failure.at_failure.host_calls, 0);
    assert_eq!(owner.usage(), wasi);
    assert_eq!(memory, [0xa5; 8]);
    foreign.drop_proof(foreign_proof).unwrap();
    assert_eq!(
        foreign.finish_owned_cleanup(None).cleanup_invariant,
        Some(SwiftCleanupInvariant::ReservationOwner)
    );
    empty(clean(control, proof, owner));
}

#[test]
fn cleanup_first_foreign_owner_fault_preserves_the_last_actual_wasi_observation() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, grants(), small()).unwrap();
    let mut memory = [0xa5; 8];
    assert_eq!(
        owner
            .dispatch(
                &mut control,
                WasiFunction::ArgsSizesGet,
                &[i(0), i(4)],
                &mut memory,
                cursor()
            )
            .unwrap(),
        Errno::Success
    );
    let wasi = owner.usage();
    assert_eq!(wasi.calls, 1);
    let owned_before = control.usage(Some(wasi));
    let (mut foreign, foreign_proof) = adopt(SwiftRunBudget::default());
    let foreign_before = foreign.usage(None);
    let (result, stats) = measure(|| owner.cleanup(&mut foreign));
    no_alloc(stats);
    assert_eq!((stats.deallocations, stats.freed_bytes), (4, 4096));
    let failure = result.unwrap_err();
    assert_eq!(failure.stage, SwiftRunStage::Cleanup);
    assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
    assert_eq!(failure.code, "swift_run_release_owner");
    assert_eq!(failure.at_failure.wasi, Some(wasi));
    assert_eq!(
        failure.at_failure.cleanup_invariant,
        Some(SwiftCleanupInvariant::ReservationOwner)
    );
    assert_eq!(
        foreign.usage(Some(wasi)).reservations,
        foreign_before.reservations
    );
    assert_eq!(
        foreign.usage(Some(wasi)).host_calls,
        foreign_before.host_calls
    );
    assert_eq!(
        control.usage(Some(wasi)).reservations,
        owned_before.reservations
    );
    assert_eq!(foreign.check(cursor()).unwrap_err(), failure);
    foreign.drop_proof(foreign_proof).unwrap();
    assert_eq!(
        foreign
            .finish_owned_cleanup(Some(wasi))
            .reservations
            .combined
            .current,
        0
    );
    control.drop_proof(proof).unwrap();
    let retained = control.finish_owned_cleanup(Some(wasi));
    assert_eq!(
        retained.reservations.wasi.current,
        owned_before.reservations.wasi.current
    );
    assert_eq!(retained.reservations.live_tickets, 5);
}

#[test]
fn runtime_preentry_and_postdispatch_failures_capture_exact_context_observation() {
    for point in 0..4 {
        let budget = if point == 0 {
            SwiftRunBudget {
                host_calls: 0,
                ..SwiftRunBudget::default()
            }
        } else {
            SwiftRunBudget::default()
        };
        let (mut control, proof) = adopt(budget);
        let mut owner = construct(&mut control, grants(), small()).unwrap();
        if point == 1 {
            owner.context.cancellation.cancel();
        }
        if point == 2 {
            owner.test.cancel_after = true;
        }
        if point == 3 {
            owner.test.cancel_before = true;
        }
        let mut memory = [0xa5; 32];
        let failure = owner
            .dispatch(
                &mut control,
                WasiFunction::ArgsSizesGet,
                &[i(0), i(4)],
                &mut memory,
                cursor(),
            )
            .unwrap_err();
        assert_eq!(failure.at_failure.wasi, Some(owner.usage()));
        assert_eq!(failure.at_failure.host_calls, u64::from(point >= 2));
        match point {
            0 => {
                assert_eq!(failure.kind, SwiftRunFailureKind::HostCallLimit);
                assert_eq!(owner.usage().calls, 0);
            }
            1 => {
                assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
                assert_eq!(owner.usage().calls, 0);
            }
            2 => {
                assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
                assert_eq!(owner.usage().calls, 1);
                assert_eq!(memory[..4], 1u32.to_le_bytes());
            }
            _ => {
                assert_eq!(failure.kind, SwiftRunFailureKind::Wasi);
                assert_eq!(failure.wasi_failure, Some(WasiFailure::Cancelled));
                assert_eq!(memory, [0xa5; 32]);
            }
        }
        empty(clean(control, proof, owner));
    }
}

#[test]
fn earliest_run_or_wasi_deadline_is_inside_real_context_checks_and_commit() {
    for wasi_first in [false, true] {
        let run = SwiftRunBudget {
            deadline_ms: if wasi_first { 30_000 } else { 20 },
            ..SwiftRunBudget::default()
        };
        let (mut control, proof) = adopt(run);
        let mut owner = construct(
            &mut control,
            grants(),
            WasiBudget {
                deadline_ms: if wasi_first { 20 } else { 30_000 },
                ..small()
            },
        )
        .unwrap();
        assert_eq!(owner.context.deadline, control.deadline());
        assert_eq!(
            control.deadline_origin(),
            if wasi_first {
                SwiftDeadlineOrigin::Wasi
            } else {
                SwiftDeadlineOrigin::Run
            }
        );
        owner.context.scratch.resize(8, 7);
        owner.context.rollback.resize(8, 0);
        std::thread::sleep(Duration::from_millis(25));
        assert_eq!(owner.context.check(), Err(WasiFailure::Deadline));
        let mut memory = [0xa5; 8];
        assert!(matches!(
            owner
                .context
                .commit(&mut memory, &[Span { start: 0, end: 8 }]),
            Err(super::super::Fault::Terminal(WasiFailure::Deadline))
        ));
        assert_eq!(memory, [0xa5; 8]);
        let failure = owner
            .dispatch(
                &mut control,
                WasiFunction::RandomGet,
                &[i(0), i(8)],
                &mut memory,
                cursor(),
            )
            .unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::Deadline);
        assert_eq!(failure.at_failure.wasi, Some(owner.usage()));
        assert_eq!(failure.at_failure.host_calls, 0);
        empty(clean(control, proof, owner));
    }
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(
        &mut control,
        grants(),
        WasiBudget {
            deadline_ms: 2,
            ..small()
        },
    )
    .unwrap();
    owner.test.expire_before = true;
    let mut memory = [0xa5; 8];
    let failure = owner
        .dispatch(
            &mut control,
            WasiFunction::ClockResGet,
            &[i(0), i(0)],
            &mut memory,
            cursor(),
        )
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Wasi);
    assert_eq!(failure.wasi_failure, Some(WasiFailure::Deadline));
    assert_eq!(failure.deadline_origin, SwiftDeadlineOrigin::Wasi);
    assert_eq!(failure.at_failure.host_calls, 1);
    assert_eq!(memory, [0xa5; 8]);
    empty(clean(control, proof, owner));
}
