//! Original same-ABI foundation tests. No reactor instantiation or invocation.
use super::*;
use crate::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget};
use crate::experimental_wasi::WasiFunction;
use crate::Type;
use std::cell::Cell;

fn uint(mut value: u32, bytes: &mut Vec<u8>) {
    loop {
        let next = value & 0x7f;
        value >>= 7;
        bytes.push(next as u8 | if value == 0 { 0 } else { 0x80 });
        if value == 0 {
            break;
        }
    }
}
fn name(value: &[u8], bytes: &mut Vec<u8>) {
    uint(value.len() as u32, bytes);
    bytes.extend_from_slice(value);
}
fn section(module: &mut Vec<u8>, id: u8, bytes: &[u8]) {
    module.push(id);
    uint(bytes.len() as u32, module);
    module.extend_from_slice(bytes);
}
fn signature(parameters: &[Type], results: &[Type], bytes: &mut Vec<u8>) {
    let ty = |value| match value {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    };
    bytes.push(0x60);
    uint(parameters.len() as u32, bytes);
    bytes.extend(parameters.iter().copied().map(ty));
    uint(results.len() as u32, bytes);
    bytes.extend(results.iter().copied().map(ty));
}
fn proof() -> ValidatedSwiftReactor {
    // Complete ordinary policy: 34 ordered Preview1 imports, 29 definitions,
    // exact indices 35/62, initial memory584 and fixed table46713. Only body
    // content is small. No private/relaxed fixture policy or proof construction.
    let mut module = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![36];
    for import in WasiFunction::ALL {
        signature(import.parameters(), import.results(), &mut types);
    }
    signature(&[], &[], &mut types);
    signature(&[], &[Type::I32], &mut types);
    section(&mut module, 1, &types);
    let mut imports = vec![34];
    for (index, import) in WasiFunction::ALL.into_iter().enumerate() {
        name(b"wasi_snapshot_preview1", &mut imports);
        name(import.name(), &mut imports);
        imports.push(0);
        uint(index as u32, &mut imports);
    }
    section(&mut module, 2, &imports);
    let mut functions = vec![29];
    functions.extend([34; 28]);
    functions.push(35);
    section(&mut module, 3, &functions);
    let mut table = vec![1, 0x70, 1];
    uint(46_713, &mut table);
    uint(46_713, &mut table);
    section(&mut module, 4, &table);
    let mut memory = vec![1, 0];
    uint(584, &mut memory);
    section(&mut module, 5, &memory);
    let mut exports = vec![3];
    for (export, kind, index) in [
        (b"memory".as_slice(), 2, 0),
        (b"_initialize".as_slice(), 0, 35),
        (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
    ] {
        name(export, &mut exports);
        exports.push(kind);
        uint(index, &mut exports);
    }
    section(&mut module, 7, &exports);
    let mut bodies = vec![29];
    for _ in 0..28 {
        bodies.extend_from_slice(&[2, 0, 0x0b]);
    }
    bodies.extend_from_slice(&[4, 0, 0x41, 0, 0x0b]);
    section(&mut module, 10, &bodies);
    validate_swift_reactor(
        &module,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap()
}
fn adopt(budget: SwiftRunBudget) -> (RuntimeControl, AdoptedProof) {
    RuntimeControl::adopt(proof(), budget, Instant::now(), Cancellation::default()).unwrap()
}
fn cursor(stage: SwiftRunStage) -> Cursor {
    Cursor {
        stage,
        function: Some(62),
        offset: Some(201),
    }
}
fn clean(mut control: RuntimeControl, adopted: AdoptedProof) -> SwiftRunUsage {
    control.drop_proof(adopted).unwrap();
    control.finish_owned_cleanup(None)
}
fn assert_empty(usage: SwiftRunUsage) {
    assert_eq!(usage.reservations.combined.current, 0);
    assert_eq!(usage.reservations.live_tickets, 0);
    for category in [
        SwiftReservationCategory::RetainedSource,
        SwiftReservationCategory::RetainedMetadata,
        SwiftReservationCategory::Cache,
        SwiftReservationCategory::State,
        SwiftReservationCategory::Wasi,
        SwiftReservationCategory::Shared,
        SwiftReservationCategory::Construction,
    ] {
        assert_eq!(usage.reservations.category(category).current, 0);
    }
}
fn no_allocations(stats: super::super::allocation_tests::AllocationStats) {
    assert_eq!(stats.allocations, 0);
    assert_eq!(stats.reallocations, 0);
}

#[test]
fn sealed_proof_adoption_is_before_allocation_and_preserves_historical_validation() {
    let proof = proof();
    let validation = proof.usage();
    let token = Cancellation::default();
    let ((control, adopted), stats) = super::super::allocation_tests::measure(|| {
        RuntimeControl::adopt(proof, SwiftRunBudget::default(), Instant::now(), token).unwrap()
    });
    no_allocations(stats);
    let usage = control.usage(None);
    assert_eq!(adopted.proof().observations().memory_minimum, 584);
    assert_eq!(adopted.proof().observations().table_minimum, 46_713);
    assert_eq!(adopted.proof().observations().validated_bodies, 29);
    assert_eq!(usage.validation, validation);
    assert_eq!(
        usage.reservations.retained_source.current,
        validation.source_bytes
    );
    assert_eq!(
        usage.reservations.retained_metadata.current,
        validation.metadata_reserved
    );
    assert_eq!(
        usage.reservations.shared.current,
        size_of::<RuntimeControl>() + Cancellation::requested_backing_layout().size()
    );
    assert_eq!(
        usage.reservations.construction.current,
        foundation_construction_bytes().unwrap()
    );
    assert_eq!(usage.reservations.live_tickets, 5);
    assert_eq!(
        usage.reservations.combined.current,
        validation.source_bytes
            + validation.metadata_reserved
            + usage.reservations.shared.current
            + usage.reservations.construction.current
    );
    assert_eq!(
        usage.reservations.combined.peak,
        usage.reservations.combined.current
    );
    assert_eq!(usage.instruction_fuel, 0);
    assert_eq!(usage.wasi, None);
    let (cleanup, stats) = super::super::allocation_tests::measure(|| clean(control, adopted));
    no_allocations(stats);
    assert!(stats.deallocations > 0);
    assert_empty(cleanup);
    assert_eq!(
        cleanup.reservations.combined.peak,
        usage.reservations.combined.peak
    );
}

#[test]
fn all_seventeen_dimensions_reject_widening_without_allocation_and_drop_real_proof() {
    let max = SwiftRunBudget::default();
    for dimension in 0..17 {
        let mut budget = max;
        match dimension {
            0 => budget.source_bytes += 1,
            1 => budget.metadata_bytes += 1,
            2 => budget.cache_bytes += 1,
            3 => budget.cache_entry_bytes += 1,
            4 => budget.cache_entries += 1,
            5 => budget.active_pins += 1,
            6 => budget.cache_work += 1,
            7 => budget.frames += 1,
            8 => budget.values += 1,
            9 => budget.controls += 1,
            10 => budget.memory_pages += 1,
            11 => budget.state_bytes += 1,
            12 => budget.combined_bytes += 1,
            13 => budget.instruction_fuel += 1,
            14 => budget.execution_work += 1,
            15 => budget.host_calls += 1,
            16 => budget.deadline_ms += 1,
            _ => unreachable!(),
        }
        let proof = proof();
        let source = proof.usage().source_bytes;
        let token = Cancellation::default();
        let (failure, stats) = super::super::allocation_tests::measure(|| {
            RuntimeControl::adopt(proof, budget, Instant::now(), token)
                .err()
                .unwrap()
        });
        no_allocations(stats);
        assert_eq!(
            failure.kind,
            SwiftRunFailureKind::InvalidBudget,
            "dimension {dimension}"
        );
        assert_eq!(failure.attempted, failure.limit + 1);
        assert!(stats.freed_bytes >= source);
        assert_empty(failure.after_cleanup.unwrap());
    }
}

#[test]
fn zero_is_real_in_every_budget_dimension() {
    for dimension in 0..17 {
        let mut budget = SwiftRunBudget::default();
        match dimension {
            0 => budget.source_bytes = 0,
            1 => budget.metadata_bytes = 0,
            2 => budget.cache_bytes = 0,
            3 => budget.cache_entry_bytes = 0,
            4 => budget.cache_entries = 0,
            5 => budget.active_pins = 0,
            6 => budget.cache_work = 0,
            7 => budget.frames = 0,
            8 => budget.values = 0,
            9 => budget.controls = 0,
            10 => budget.memory_pages = 0,
            11 => budget.state_bytes = 0,
            12 => budget.combined_bytes = 0,
            13 => budget.instruction_fuel = 0,
            14 => budget.execution_work = 0,
            15 => budget.host_calls = 0,
            16 => budget.deadline_ms = 0,
            _ => unreachable!(),
        }
        let result =
            RuntimeControl::adopt(proof(), budget, Instant::now(), Cancellation::default());
        let (mut control, adopted) = match result {
            Err(failure) => {
                assert!(matches!(dimension, 0 | 1 | 12 | 16));
                assert_ne!(failure.kind, SwiftRunFailureKind::InvalidBudget);
                assert_empty(failure.after_cleanup.unwrap());
                continue;
            }
            Ok(parts) => parts,
        };
        let at = cursor(SwiftRunStage::Invocation);
        let result = match dimension {
            2 => control
                .admit(SwiftReservationCategory::Cache, 1, at)
                .map(drop),
            3 => control.admit_cache_entry(1, at).map(drop),
            4 => control.add_live(Live::CacheEntries, 1, at),
            5 => control.add_live(Live::ActivePins, 1, at),
            6 => control.work(Work::Cache, 1, at),
            7 => control.add_live(Live::Frames, 1, at),
            8 => control.add_live(Live::Values, 1, at),
            9 => control.add_live(Live::Controls, 1, at),
            10 => control.add_live(Live::MemoryPages, 1, at),
            11 => control
                .admit(SwiftReservationCategory::State, 1, at)
                .map(drop),
            13 => control.instruction(at),
            14 => control.work(Work::Execution, 1, at),
            15 => control.enter_host(at),
            _ => unreachable!(),
        };
        assert_eq!(result.err().unwrap().limit, 0, "dimension {dimension}");
        assert_empty(clean(control, adopted));
    }
    let all_zero = SwiftRunBudget {
        source_bytes: 0,
        metadata_bytes: 0,
        cache_bytes: 0,
        cache_entry_bytes: 0,
        cache_entries: 0,
        active_pins: 0,
        cache_work: 0,
        frames: 0,
        values: 0,
        controls: 0,
        memory_pages: 0,
        state_bytes: 0,
        combined_bytes: 0,
        instruction_fuel: 0,
        execution_work: 0,
        host_calls: 0,
        deadline_ms: 0,
    };
    let failure = RuntimeControl::adopt(proof(), all_zero, Instant::now(), Cancellation::default())
        .err()
        .unwrap();
    assert_eq!(failure.kind, SwiftRunFailureKind::Deadline);
    assert_empty(failure.after_cleanup.unwrap());
}

#[test]
fn failed_adoption_keeps_first_peak_and_reports_zero_only_after_real_drop() {
    let sealed = proof();
    let validation = sealed.usage();
    let budget = SwiftRunBudget {
        metadata_bytes: validation.metadata_reserved - 1,
        ..SwiftRunBudget::default()
    };
    let (failure, stats) = super::super::allocation_tests::measure(|| {
        RuntimeControl::adopt(sealed, budget, Instant::now(), Cancellation::default())
            .err()
            .unwrap()
    });
    // Creating Cancellation in this observation deliberately makes exactly one
    // backing request. Adoption itself was measured allocation-free above.
    assert_eq!(stats.allocations, 1);
    assert_eq!(failure.kind, SwiftRunFailureKind::Adoption);
    assert_eq!(
        failure.resource,
        Some(SwiftRunResource::Reservation(
            SwiftReservationCategory::RetainedMetadata
        ))
    );
    assert_eq!(
        failure.at_failure.reservations.retained_source.current,
        validation.source_bytes
    );
    assert_eq!(failure.at_failure.reservations.retained_metadata.current, 0);
    assert_eq!(
        failure.after_cleanup.unwrap().reservations.combined.peak,
        validation.source_bytes
    );
    assert!(stats.freed_bytes >= validation.source_bytes);
    assert_empty(failure.after_cleanup.unwrap());
}

#[test]
fn each_adoption_boundary_fails_before_allocation_and_exact_narrowing_succeeds() {
    for boundary in 0..5 {
        let sealed = proof();
        let validation = sealed.usage();
        let parts = [
            validation.source_bytes,
            validation.metadata_reserved,
            size_of::<RuntimeControl>(),
            Cancellation::requested_backing_layout().size(),
            foundation_construction_bytes().unwrap(),
        ];
        let before: usize = parts[..boundary].iter().sum();
        let limit = before + parts[boundary] - 1;
        let budget = SwiftRunBudget {
            combined_bytes: limit,
            ..SwiftRunBudget::default()
        };
        let token = Cancellation::default();
        let (failure, stats) = super::super::allocation_tests::measure(|| {
            RuntimeControl::adopt(sealed, budget, Instant::now(), token)
                .err()
                .unwrap()
        });
        no_allocations(stats);
        assert_eq!(
            failure.kind,
            SwiftRunFailureKind::CombinedExhausted,
            "boundary {boundary}"
        );
        assert_eq!(failure.at_failure.reservations.combined.current, before);
        assert_eq!(failure.at_failure.reservations.combined.peak, before);
        assert_eq!(
            failure.after_cleanup.unwrap().reservations.combined.peak,
            before
        );
        assert_empty(failure.after_cleanup.unwrap());
    }
    let sealed = proof();
    let validation = sealed.usage();
    assert!(validation.scratch_peak_reserved > 0);
    let limit = validation.source_bytes
        + validation.metadata_reserved
        + size_of::<RuntimeControl>()
        + Cancellation::requested_backing_layout().size()
        + foundation_construction_bytes().unwrap();
    let budget = SwiftRunBudget {
        source_bytes: validation.source_bytes,
        metadata_bytes: validation.metadata_reserved,
        combined_bytes: limit,
        ..SwiftRunBudget::default()
    };
    let (mut control, adopted) =
        RuntimeControl::adopt(sealed, budget, Instant::now(), Cancellation::default()).unwrap();
    assert_eq!(control.reservations.combined.current, limit);
    let failure = control
        .admit(
            SwiftReservationCategory::Cache,
            1,
            cursor(SwiftRunStage::Cache),
        )
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
    assert_empty(clean(control, adopted));
}

#[test]
fn category_and_combined_admission_are_atomic_and_preserve_simultaneous_peaks() {
    let (mut control, adopted) = adopt(SwiftRunBudget {
        cache_bytes: 10,
        ..SwiftRunBudget::default()
    });
    let baseline = control.reservations.combined.current;
    let ticket = control
        .admit(
            SwiftReservationCategory::Cache,
            8,
            cursor(SwiftRunStage::Cache),
        )
        .unwrap();
    let before = control.reservations;
    let failure = control
        .admit(
            SwiftReservationCategory::Cache,
            3,
            cursor(SwiftRunStage::Cache),
        )
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::CategoryExhausted);
    assert_eq!(control.reservations, before);
    assert_eq!(before.combined.peak, baseline + 8);
    control.drop_reserved([0u8; 8], ticket).unwrap();
    assert_empty(clean(control, adopted));

    let sealed = proof();
    let baseline = sealed.usage().source_bytes
        + sealed.usage().metadata_reserved
        + size_of::<RuntimeControl>()
        + Cancellation::requested_backing_layout().size()
        + foundation_construction_bytes().unwrap();
    let budget = SwiftRunBudget {
        combined_bytes: baseline + 12,
        ..SwiftRunBudget::default()
    };
    let (mut control, adopted) =
        RuntimeControl::adopt(sealed, budget, Instant::now(), Cancellation::default()).unwrap();
    let wasi = control
        .admit(
            SwiftReservationCategory::Wasi,
            8,
            cursor(SwiftRunStage::Wasi),
        )
        .unwrap();
    let before = control.reservations;
    let failure = control
        .admit(
            SwiftReservationCategory::State,
            5,
            cursor(SwiftRunStage::Initialization),
        )
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
    assert_eq!(control.reservations, before);
    assert_eq!(before.state.current, 0);
    assert_eq!(before.wasi.current, 8);
    control.drop_reserved([0u8; 8], wasi).unwrap();
    assert_empty(clean(control, adopted));
}

#[test]
fn checked_byte_overflow_and_release_underflow_never_create_room() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    control.reservations.cache.current = usize::MAX;
    let before = control.reservations;
    let failure = control
        .admit(
            SwiftReservationCategory::Cache,
            1,
            cursor(SwiftRunStage::Cache),
        )
        .unwrap_err();
    assert_eq!(failure.attempted, u64::MAX);
    assert_eq!(control.reservations, before);
    // Undo only the deliberately injected corruption to clean the real proof.
    control.reservations.cache.current = 0;
    assert_empty(clean(control, adopted));

    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let original = control.reservations.combined.current;
    control.reservations.combined.current = usize::MAX;
    let before = control.reservations;
    let failure = control
        .admit(
            SwiftReservationCategory::Cache,
            1,
            cursor(SwiftRunStage::Cache),
        )
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
    assert_eq!(failure.attempted, u64::MAX);
    assert_eq!(control.reservations, before);
    control.reservations.combined.current = original;
    assert_empty(clean(control, adopted));

    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let mut ticket = control
        .admit(
            SwiftReservationCategory::State,
            1,
            cursor(SwiftRunStage::Initialization),
        )
        .unwrap();
    ticket.bytes = 2; // Original fault: impossible through the private API.
    let before = control.reservations;
    assert_eq!(
        control.drop_reserved([0u8; 1], ticket).unwrap_err().kind,
        SwiftRunFailureKind::Invariant
    );
    assert_eq!(control.reservations, before);
    control.drop_proof(adopted).unwrap();
    let after = control.finish_owned_cleanup(None);
    assert_eq!(after.reservations.state.current, 1);
    assert_eq!(after.reservations.combined.current, 1);
    assert_eq!(after.reservations.live_tickets, 1);
}

#[test]
fn inline_ticket_inventory_is_exactly_bounded_and_dropped_tickets_keep_charges() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let mut tickets: [Option<ReservationTicket>; MAX_RESERVATION_TICKETS - 5] =
        std::array::from_fn(|_| None);
    let ((), stats) = super::super::allocation_tests::measure(|| {
        for ticket in &mut tickets {
            *ticket = Some(
                control
                    .admit(
                        SwiftReservationCategory::Cache,
                        0,
                        cursor(SwiftRunStage::Cache),
                    )
                    .unwrap(),
            );
        }
        let before = control.reservations;
        let failure = control
            .admit(
                SwiftReservationCategory::Cache,
                0,
                cursor(SwiftRunStage::Cache),
            )
            .unwrap_err();
        assert_eq!(failure.resource, Some(SwiftRunResource::TicketInventory));
        assert_eq!(control.reservations, before);
        for ticket in &mut tickets {
            control.drop_reserved((), ticket.take().unwrap()).unwrap();
        }
    });
    no_allocations(stats);
    assert_eq!(control.reservations.peak_tickets, MAX_RESERVATION_TICKETS);
    assert_empty(clean(control, adopted));

    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let ticket = control
        .admit(
            SwiftReservationCategory::Cache,
            31,
            cursor(SwiftRunStage::Cache),
        )
        .unwrap();
    #[allow(clippy::drop_non_drop)] // Explicitly exercise an omitted refund.
    drop(ticket); // An omitted storage/release must not refund anything.
    control.drop_proof(adopted).unwrap();
    let after = control.finish_owned_cleanup(None);
    assert_eq!(after.reservations.combined.current, 31);
    assert_eq!(after.reservations.cache.current, 31);
    assert_eq!(after.reservations.live_tickets, 1);
}

#[test]
fn foreign_release_is_rejected_and_retains_both_ledgers_conservatively() {
    let (mut first, first_proof) = adopt(SwiftRunBudget::default());
    let (mut second, second_proof) = adopt(SwiftRunBudget::default());
    let ticket = first
        .admit(
            SwiftReservationCategory::State,
            24,
            cursor(SwiftRunStage::Initialization),
        )
        .unwrap();
    let first_before = first.reservations;
    let second_before = second.reservations;
    let dropped = Cell::new(false);
    struct Storage<'a>(&'a Cell<bool>);
    impl Drop for Storage<'_> {
        fn drop(&mut self) {
            self.0.set(true);
        }
    }
    let failure = second.drop_reserved(Storage(&dropped), ticket).unwrap_err();
    assert!(dropped.get());
    assert_eq!(failure.code, "swift_run_release_owner");
    assert_eq!(first.reservations, first_before);
    assert_eq!(second.reservations, second_before);
    assert_empty(clean(second, second_proof));
    first.drop_proof(first_proof).unwrap();
    let after = first.finish_owned_cleanup(None);
    assert_eq!(after.reservations.state.current, 24);
    assert_eq!(after.reservations.live_tickets, 1);
}

#[test]
fn aggregate_entry_ticket_moves_without_double_charge_and_partial_storage_drops_before_refund() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let ticket = control
        .admit_cache_entry(16 + 32 + 48, cursor(SwiftRunStage::Cache))
        .unwrap();
    let before = control.reservations;
    // Original synthetic partial-allocation fault: actual two buffers exist;
    // the absent third allocation remains covered until both live buffers drop.
    let first = Vec::<u8>::with_capacity(16);
    let second = Vec::<u8>::with_capacity(32);
    let ticket = std::hint::black_box(ticket);
    assert_eq!(control.reservations, before);
    let failure = control.fail(
        cursor(SwiftRunStage::Cache),
        Fault::new(
            SwiftRunFailureKind::Allocation,
            "synthetic_third_buffer_allocation",
        ),
        None,
    );
    assert_eq!(failure.at_failure.reservations.cache.current, 96);
    let ((), stats) = super::super::allocation_tests::measure(|| {
        control.drop_reserved((first, second), ticket).unwrap();
    });
    no_allocations(stats);
    assert_eq!(stats.deallocations, 2);
    assert_eq!(stats.freed_bytes, 48);
    assert_eq!(control.reservations.cache.current, 0);
    assert_eq!(control.reservations.cache.peak, 96);
    assert_empty(clean(control, adopted));
}

#[test]
fn state_overlap_is_admitted_before_any_replacement_allocation() {
    let (mut control, adopted) = adopt(SwiftRunBudget {
        state_bytes: 127,
        ..SwiftRunBudget::default()
    });
    let old_ticket = control
        .admit(
            SwiftReservationCategory::State,
            64,
            cursor(SwiftRunStage::Initialization),
        )
        .unwrap();
    let old = Vec::<u8>::with_capacity(64);
    let before = control.reservations;
    let (failure, stats) = super::super::allocation_tests::measure(|| {
        control
            .admit(
                SwiftReservationCategory::State,
                64,
                cursor(SwiftRunStage::Invocation),
            )
            .unwrap_err()
    });
    no_allocations(stats);
    assert_eq!(failure.attempted, 128);
    assert_eq!(failure.limit, 127);
    assert_eq!(control.reservations, before);
    control.drop_reserved(old, old_ticket).unwrap();
    assert_empty(clean(control, adopted));
}

#[test]
fn construction_uses_one_ticket_grows_before_phase_and_shrinks_after_actual_drop() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let floor = foundation_construction_bytes().unwrap();
    let count = control.reservations.live_tickets;
    control
        .enlarge_construction(floor + 37, cursor(SwiftRunStage::Initialization))
        .unwrap();
    assert_eq!(control.reservations.live_tickets, count);
    assert_eq!(control.reservations.construction.current, floor + 37);
    let storage = Vec::<u8>::with_capacity(37);
    let (result, stats) =
        super::super::allocation_tests::measure(|| control.end_construction_phase(storage, floor));
    result.unwrap();
    no_allocations(stats);
    assert_eq!(stats.freed_bytes, 37);
    assert_eq!(control.reservations.construction.current, floor);
    assert_eq!(control.reservations.construction.peak, floor + 37);
    assert_eq!(control.reservations.live_tickets, count);
    assert_empty(clean(control, adopted));
}

#[test]
fn unclosed_construction_phase_is_retained_when_external_storage_is_missing() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let floor = foundation_construction_bytes().unwrap();
    control
        .enlarge_construction(floor + 37, cursor(SwiftRunStage::Initialization))
        .unwrap();
    let still_external = Vec::<u8>::with_capacity(37);
    control.drop_proof(adopted).unwrap();
    let (after, stats) =
        super::super::allocation_tests::measure(|| control.finish_owned_cleanup(None));
    no_allocations(stats);
    assert_eq!(still_external.capacity(), 37);
    assert_eq!(
        after.cleanup_invariant,
        Some(SwiftCleanupInvariant::ConstructionBound)
    );
    assert_eq!(after.reservations.construction.current, floor + 37);
    assert_eq!(after.reservations.combined.current, floor + 37);
    assert_eq!(after.reservations.live_tickets, 1);
    let ((), stats) = super::super::allocation_tests::measure(|| drop(still_external));
    no_allocations(stats);
    assert_eq!(stats.freed_bytes, 37);
}

#[test]
fn init_and_repeated_call_counters_accumulate_and_cannot_refill() {
    let budget = SwiftRunBudget {
        cache_work: 6,
        execution_work: 9,
        instruction_fuel: 9,
        host_calls: 3,
        ..SwiftRunBudget::default()
    };
    let (mut control, adopted) = adopt(budget);
    for stage in [
        SwiftRunStage::Initialization,
        SwiftRunStage::Invocation,
        SwiftRunStage::Invocation,
    ] {
        let at = cursor(stage);
        control.work(Work::Cache, 2, at).unwrap();
        control.work(Work::Execution, 3, at).unwrap();
        control.instruction(at).unwrap();
        control.instruction(at).unwrap();
        control.charge_fuel(1, at).unwrap();
        control.enter_host(at).unwrap();
    }
    let before = control.usage(None);
    assert_eq!(
        (
            before.cache_work,
            before.execution_work,
            before.instructions,
            before.instruction_fuel,
            before.host_calls
        ),
        (6, 9, 6, 9, 3)
    );
    let failure = control
        .enter_host(cursor(SwiftRunStage::Invocation))
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::HostCallLimit);
    assert_eq!(failure.attempted, 4);
    assert_eq!(control.host_calls, 3);
    assert_eq!(
        control
            .instruction(cursor(SwiftRunStage::Invocation))
            .unwrap_err(),
        failure
    );
    assert_eq!(
        control
            .work(Work::Cache, 0, cursor(SwiftRunStage::Cache))
            .unwrap_err(),
        failure
    );
    assert_empty(clean(control, adopted));
}

#[test]
fn work_fuel_host_and_live_overflow_fail_closed_without_counter_commit() {
    for component in [Work::Cache, Work::Execution] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        match component {
            Work::Cache => control.cache_work = u64::MAX,
            Work::Execution => control.execution_work = u64::MAX,
        }
        let failure = control
            .work(component, 1, cursor(SwiftRunStage::Invocation))
            .unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::WorkExhausted);
        assert_eq!(failure.attempted, u64::MAX);
        assert_empty(clean(control, adopted));
    }
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    control.instruction_fuel = u64::MAX;
    assert_eq!(
        control
            .charge_fuel(1, cursor(SwiftRunStage::Invocation))
            .unwrap_err()
            .kind,
        SwiftRunFailureKind::FuelExhausted
    );
    assert_eq!(control.instruction_fuel, u64::MAX);
    assert_empty(clean(control, adopted));
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    control.host_calls = u64::MAX;
    assert_eq!(
        control
            .enter_host(cursor(SwiftRunStage::Invocation))
            .unwrap_err()
            .kind,
        SwiftRunFailureKind::HostCallLimit
    );
    assert_eq!(control.host_calls, u64::MAX);
    assert_empty(clean(control, adopted));

    for resource in [
        Live::CacheEntries,
        Live::ActivePins,
        Live::Frames,
        Live::Values,
        Live::Controls,
        Live::MemoryPages,
    ] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        let (_, limit, diagnostic, _) = control.live_parts(resource);
        control
            .add_live(resource, limit, cursor(SwiftRunStage::Invocation))
            .unwrap();
        let before = control.live;
        let failure = control
            .add_live(resource, 1, cursor(SwiftRunStage::Invocation))
            .unwrap_err();
        assert_eq!(failure.resource, Some(diagnostic));
        assert_eq!(control.live, before);
        control.remove_live(resource, limit).unwrap();
        assert_eq!(control.live_parts(resource).0.current, 0);
        assert_eq!(control.live_parts(resource).0.peak, limit);
        assert_empty(clean(control, adopted));
    }
}

#[test]
fn shared_cancellation_is_sticky_and_cleanup_ignores_it_without_allocating_or_work() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let token = control.cancellation();
    let ticket = control
        .admit(
            SwiftReservationCategory::State,
            17,
            cursor(SwiftRunStage::Initialization),
        )
        .unwrap();
    let storage = Vec::<u8>::with_capacity(17);
    control
        .add_live(Live::Frames, 1, cursor(SwiftRunStage::Initialization))
        .unwrap();
    control
        .add_live(Live::ActivePins, 1, cursor(SwiftRunStage::Initialization))
        .unwrap();
    token.cancel();
    let at = cursor(SwiftRunStage::Invocation);
    let failure = control.check(at).unwrap_err();
    let (after, stats) = super::super::allocation_tests::measure(|| {
        assert_eq!(control.work(Work::Execution, 1, at).unwrap_err(), failure);
        control.drop_reserved(storage, ticket).unwrap();
        control.remove_live(Live::Frames, 1).unwrap();
        control.remove_live(Live::ActivePins, 1).unwrap();
        let cleanup = control.record_cleanup(None).unwrap();
        assert_eq!(cleanup.at_failure, failure.at_failure);
        assert_eq!(cleanup.offset, failure.offset);
        assert_eq!(cleanup.after_cleanup.unwrap().live.frames.current, 0);
        assert_eq!(cleanup.after_cleanup.unwrap().live.active_pins.current, 0);
        control.drop_proof(adopted).unwrap();
        control.finish_owned_cleanup(None)
    });
    no_allocations(stats);
    assert_eq!(after.execution_work, 0);
    assert_eq!(after.reservations.state.peak, 17);
    assert_empty(after);
}

#[test]
fn cleanup_invariants_are_separate_from_the_immutable_first_terminal_cause() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let mut ticket = control
        .admit(
            SwiftReservationCategory::State,
            1,
            cursor(SwiftRunStage::Initialization),
        )
        .unwrap();
    let original = control.fail(
        cursor(SwiftRunStage::Invocation),
        Fault::new(SwiftRunFailureKind::GuestTrap, "original_guest_trap"),
        None,
    );
    ticket.bytes = 2; // Inject a private ownership fault after terminalization.
    let (after, stats) = super::super::allocation_tests::measure(|| {
        assert_eq!(
            control.drop_reserved([0u8; 1], ticket).unwrap_err(),
            original
        );
        let failure = control.record_cleanup(None).unwrap();
        assert_eq!(failure.at_failure, original.at_failure);
        assert_eq!(failure.kind, SwiftRunFailureKind::GuestTrap);
        assert_eq!(
            failure.after_cleanup.unwrap().cleanup_invariant,
            Some(SwiftCleanupInvariant::ReservationUnderflow)
        );
        control.drop_proof(adopted).unwrap();
        control.finish_owned_cleanup(None)
    });
    no_allocations(stats);
    assert_eq!(
        after.cleanup_invariant,
        Some(SwiftCleanupInvariant::ReservationUnderflow)
    );
    assert_eq!(after.reservations.state.current, 1);
    assert_eq!(after.reservations.live_tickets, 1);
}

#[test]
fn live_cleanup_underflow_retains_counts_and_remaining_cleanup_still_drains() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    control
        .add_live(Live::Frames, 1, cursor(SwiftRunStage::Initialization))
        .unwrap();
    control
        .add_live(Live::ActivePins, 1, cursor(SwiftRunStage::Initialization))
        .unwrap();
    let before = control.live;
    assert_eq!(
        control.remove_live(Live::Frames, 2).unwrap_err().code,
        "swift_run_live_underflow"
    );
    assert_eq!(control.live, before);
    control.remove_live(Live::Frames, 1).unwrap();
    control.remove_live(Live::ActivePins, 1).unwrap();
    let failure = control.record_cleanup(None).unwrap();
    assert_eq!(
        failure.after_cleanup.unwrap().cleanup_invariant,
        Some(SwiftCleanupInvariant::LiveUnderflow)
    );
    assert_eq!(failure.after_cleanup.unwrap().live.frames.current, 0);
    assert_eq!(failure.after_cleanup.unwrap().live.active_pins.current, 0);
    assert_empty(clean(control, adopted));
}

#[test]
fn deadlines_are_carried_as_earliest_absolute_time_and_real_expiry_is_sticky() {
    let (mut control, adopted) = adopt(SwiftRunBudget {
        deadline_ms: 100,
        ..SwiftRunBudget::default()
    });
    let run = control.deadline();
    let at = cursor(SwiftRunStage::Wasi);
    assert_eq!(
        control
            .carry_wasi_deadline(
                Instant::now(),
                WasiBudget {
                    deadline_ms: 200,
                    ..WasiBudget::default()
                },
                at
            )
            .unwrap(),
        run
    );
    assert_eq!(control.deadline_origin(), SwiftDeadlineOrigin::Run);
    let wasi_start = Instant::now();
    let earlier = control
        .carry_wasi_deadline(
            wasi_start,
            WasiBudget {
                deadline_ms: 5,
                ..WasiBudget::default()
            },
            at,
        )
        .unwrap();
    assert_eq!(earlier, wasi_start + Duration::from_millis(5));
    assert_eq!(control.deadline_origin(), SwiftDeadlineOrigin::Wasi);
    assert_eq!(
        control
            .carry_wasi_deadline(Instant::now(), WasiBudget::default(), at)
            .unwrap(),
        earlier
    );
    std::thread::sleep(Duration::from_millis(12));
    let failure = control.check(at).unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Deadline);
    assert_eq!(failure.deadline_origin, SwiftDeadlineOrigin::Wasi);
    assert!(failure.at_failure.deadline_overshoot_micros > 0);
    assert_eq!(
        control
            .enter_host(cursor(SwiftRunStage::Invocation))
            .unwrap_err(),
        failure
    );
    assert_empty(clean(control, adopted));

    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let failure = control
        .carry_wasi_deadline(
            Instant::now(),
            WasiBudget {
                deadline_ms: 0,
                ..WasiBudget::default()
            },
            at,
        )
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Deadline);
    assert_eq!(failure.deadline_origin, SwiftDeadlineOrigin::Wasi);
    assert_empty(clean(control, adopted));
}

#[test]
fn old_started_time_and_cancelled_constructor_drop_proof_and_return_no_owner() {
    for cancelled in [false, true] {
        let proof = proof();
        let token = Cancellation::default();
        if cancelled {
            token.cancel();
        }
        let started = Instant::now() - Duration::from_millis(20);
        let (failure, stats) = super::super::allocation_tests::measure(|| {
            RuntimeControl::adopt(
                proof,
                SwiftRunBudget {
                    deadline_ms: 1,
                    ..SwiftRunBudget::default()
                },
                started,
                token,
            )
            .err()
            .unwrap()
        });
        no_allocations(stats);
        assert_eq!(
            failure.kind,
            if cancelled {
                SwiftRunFailureKind::Cancelled
            } else {
                SwiftRunFailureKind::Deadline
            }
        );
        assert_empty(failure.after_cleanup.unwrap());
        assert!(stats.deallocations > 0);
    }
}

#[test]
fn capacity_mismatch_and_all_terminal_faults_preserve_original_details_and_cleanup_snapshot() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let ticket = control
        .admit(
            SwiftReservationCategory::Cache,
            8,
            cursor(SwiftRunStage::Cache),
        )
        .unwrap();
    let storage = Vec::<u8>::with_capacity(9);
    let failure = control
        .exact_capacity(8, storage.capacity(), cursor(SwiftRunStage::Cache))
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Allocation);
    assert_eq!(failure.observed_capacity, Some(9));
    assert_eq!(failure.attempted, 8);
    assert_eq!(control.reservations.cache.current, 8);
    control.drop_reserved(storage, ticket).unwrap();
    assert_empty(clean(control, adopted));

    for kind in [
        SwiftRunFailureKind::DecoderMismatch,
        SwiftRunFailureKind::UnsupportedEnvironment,
        SwiftRunFailureKind::GuestTrap,
        SwiftRunFailureKind::GuestExit,
        SwiftRunFailureKind::Wasi,
        SwiftRunFailureKind::Invariant,
    ] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        let mut fault = Fault::new(kind, "original_terminal_test");
        fault.wasi_failure = Some(WasiFailure::InvalidMemory);
        fault.guest_exit = Some(0);
        let observation = WasiUsage {
            calls: 11,
            work: 19,
            transfer_bytes: 23,
            ..WasiUsage::default()
        };
        let failure = control.fail(cursor(SwiftRunStage::Invocation), fault, Some(observation));
        let other = control.fail(
            Cursor::adoption(),
            Fault::new(SwiftRunFailureKind::Invariant, "later_cleanup_failure"),
            None,
        );
        assert_eq!(other, failure);
        assert_eq!(failure.guest_exit, Some(0));
        assert_eq!(failure.wasi_failure, Some(WasiFailure::InvalidMemory));
        assert_eq!(failure.at_failure.wasi, Some(observation));
        assert_eq!(control.host_calls, 0);
        assert_eq!(control.cache_work, 0);
        let after = control.record_cleanup(Some(observation)).unwrap();
        assert_eq!(after.at_failure, failure.at_failure);
        assert_eq!(after.after_cleanup.unwrap().wasi, Some(observation));
        assert_empty(clean(control, adopted));
    }
}

#[test]
fn all_control_activity_after_proof_and_token_acquisition_is_allocation_free() {
    let proof = proof();
    let token = Cancellation::default();
    let (after, stats) = super::super::allocation_tests::measure(|| {
        let (mut control, adopted) =
            RuntimeControl::adopt(proof, SwiftRunBudget::default(), Instant::now(), token).unwrap();
        let at = cursor(SwiftRunStage::Invocation);
        let ticket = control.admit_cache_entry(128, at).unwrap();
        control.work(Work::Cache, 7, at).unwrap();
        control.work(Work::Execution, 11, at).unwrap();
        control.instruction(at).unwrap();
        control.charge_fuel(3, at).unwrap();
        control.enter_host(at).unwrap();
        control.add_live(Live::ActivePins, 1, at).unwrap();
        control.add_live(Live::Frames, 1, at).unwrap();
        control.add_live(Live::Values, 2, at).unwrap();
        control.add_live(Live::Controls, 1, at).unwrap();
        control.exact_capacity(128, 128, at).unwrap();
        control
            .carry_wasi_deadline(Instant::now(), WasiBudget::default(), at)
            .unwrap();
        let same = control.cancellation();
        same.cancel();
        let failure = control.check(at).unwrap_err();
        assert_eq!(
            control
                .admit(SwiftReservationCategory::Wasi, 0, at)
                .unwrap_err(),
            failure
        );
        control.drop_reserved([0u8; 128], ticket).unwrap();
        control.remove_live(Live::ActivePins, 1).unwrap();
        control.remove_live(Live::Frames, 1).unwrap();
        control.remove_live(Live::Values, 2).unwrap();
        control.remove_live(Live::Controls, 1).unwrap();
        control.record_cleanup(None).unwrap();
        control.drop_proof(adopted).unwrap();
        control.finish_owned_cleanup(None)
    });
    no_allocations(stats);
    assert_eq!(
        (
            after.cache_work,
            after.execution_work,
            after.instruction_fuel,
            after.instructions,
            after.host_calls
        ),
        (7, 11, 4, 1, 1)
    );
    assert_empty(after);
}

#[test]
fn optional_observation_chain_is_reserved_before_runtime_work() {
    // Caller plus instruction -> charge_fuel -> check -> fail -> usage, or
    // caller plus drop_proof -> refund -> cleanup_fault -> fail -> usage.
    // Each named by-value argument remains counted through the nested call.
    let observed_chain = size_of::<[Option<WasiUsage>; 6]>();
    let historical_observations = 2 * size_of::<WasiUsage>();
    let extra = observed_chain.checked_sub(historical_observations).unwrap();
    assert!(extra > 0);
    let non_observation_shapes = 3 * size_of::<ValidatedSwiftReactor>()
        + 3 * size_of::<RuntimeControl>()
        + 3 * size_of::<AdoptedProof>()
        + 4 * size_of::<SwiftRunFailure>()
        + 4 * size_of::<SwiftRunUsage>()
        + 6 * size_of::<ReservationTicket>()
        // Isolate observation admission while keeping the separate final-boundary
        // inventory unchanged in both the historical and current formulas.
        + FOUNDATION_FINAL_BOUNDARY_BYTES
        + super::super::execution::CONSTRUCTION_BOOTSTRAP_BYTES;
    let historical_floor = non_observation_shapes + historical_observations;
    let required_floor = non_observation_shapes + observed_chain;
    assert_eq!(foundation_construction_bytes(), Some(required_floor));
    println!(
        "observation chain target={}-{} raw={} raw_align={} optional={} optional_align={} count=6 old_floor={} new_floor={} added={}",
        std::env::consts::ARCH,
        std::env::consts::OS,
        size_of::<WasiUsage>(),
        std::mem::align_of::<WasiUsage>(),
        size_of::<Option<WasiUsage>>(),
        std::mem::align_of::<Option<WasiUsage>>(),
        historical_floor,
        required_floor,
        extra,
    );
    for headroom in [0, extra - 1, extra] {
        let sealed = proof();
        let validation = sealed.usage();
        let before = validation.source_bytes
            + validation.metadata_reserved
            + size_of::<RuntimeControl>()
            + Cancellation::requested_backing_layout().size();
        let budget = SwiftRunBudget {
            combined_bytes: before + historical_floor + headroom,
            ..SwiftRunBudget::default()
        };
        let cancellation = Cancellation::default();
        let (result, stats) = super::super::allocation_tests::measure(|| {
            RuntimeControl::adopt(sealed, budget, Instant::now(), cancellation)
        });
        no_allocations(stats);
        if headroom < extra {
            let failure = result.err().unwrap();
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
            assert_eq!(failure.attempted as usize, before + required_floor);
            assert_eq!(failure.limit as usize, budget.combined_bytes);
            assert_eq!(failure.at_failure.reservations.combined.current, before);
            assert_eq!(failure.at_failure.reservations.construction.current, 0);
            assert_empty(failure.after_cleanup.unwrap());
        } else {
            let (control, adopted) = result.ok().unwrap();
            let usage = control.usage(None);
            assert_eq!(usage.reservations.construction.current, required_floor);
            assert_eq!(usage.reservations.combined.current, budget.combined_bytes);
            assert_eq!(usage.reservations.live_tickets, 5);
            let (after, stats) =
                super::super::allocation_tests::measure(|| clean(control, adopted));
            no_allocations(stats);
            assert_empty(after);
        }
    }
}

#[test]
fn measured_named_layouts_are_recorded_without_allocator_or_rss_claims() {
    println!("Swift control foundation target={}-{} control={} align={} proof={} align={} adopted={} align={} ticket={} align={} option_ticket={} usage={} failure={} construction={} cancellation_requested={} cancellation_align={} max_inline_tickets={}",
        std::env::consts::ARCH, std::env::consts::OS,
        size_of::<RuntimeControl>(), std::mem::align_of::<RuntimeControl>(),
        size_of::<ValidatedSwiftReactor>(), std::mem::align_of::<ValidatedSwiftReactor>(),
        size_of::<AdoptedProof>(), std::mem::align_of::<AdoptedProof>(),
        size_of::<ReservationTicket>(), std::mem::align_of::<ReservationTicket>(),
        size_of::<Option<ReservationTicket>>(), size_of::<SwiftRunUsage>(), size_of::<SwiftRunFailure>(),
        foundation_construction_bytes().unwrap(), Cancellation::requested_backing_layout().size(),
        Cancellation::requested_backing_layout().align(), MAX_RESERVATION_TICKETS);
    assert!(
        size_of::<AdoptedProof>()
            >= size_of::<ValidatedSwiftReactor>() + 2 * size_of::<ReservationTicket>()
    );
}

#[test]
fn final_boundary_inventory_is_admitted_before_runtime_work() {
    assert_inventory_admission(FOUNDATION_FINAL_BOUNDARY_BYTES);
}

#[test]
fn construction_bootstrap_is_admitted_before_runtime_work() {
    assert_inventory_admission(super::super::execution::CONSTRUCTION_BOOTSTRAP_BYTES);
}

fn assert_inventory_admission(added: usize) {
    let required = foundation_construction_bytes().unwrap();
    let previous = required.checked_sub(added).unwrap();
    assert!(added > 2 * size_of::<usize>());
    for headroom in [0, added - 1, added] {
        let sealed = proof();
        let validation = sealed.usage();
        let before = validation.source_bytes
            + validation.metadata_reserved
            + size_of::<RuntimeControl>()
            + Cancellation::requested_backing_layout().size();
        let budget = SwiftRunBudget {
            combined_bytes: before + previous + headroom,
            ..SwiftRunBudget::default()
        };
        let cancellation = Cancellation::default();
        let (result, stats) = super::super::allocation_tests::measure(|| {
            RuntimeControl::adopt(sealed, budget, Instant::now(), cancellation)
        });
        no_allocations(stats);
        if headroom < added {
            let failure = result.err().unwrap();
            // Category admission precedes combined admission. The larger
            // constructor bootstrap can itself exceed the entire narrowed
            // budget at zero headroom, before adding the adopted closure.
            if required > budget.combined_bytes {
                assert_eq!(failure.kind, SwiftRunFailureKind::CategoryExhausted);
                assert_eq!(failure.code, "swift_run_category_capacity");
                assert_eq!(
                    failure.resource,
                    Some(SwiftRunResource::Reservation(
                        SwiftReservationCategory::Construction
                    ))
                );
                assert_eq!(failure.attempted as usize, required);
            } else {
                assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
                assert_eq!(failure.code, "swift_run_combined_capacity");
                assert_eq!(failure.resource, Some(SwiftRunResource::Combined));
                assert_eq!(failure.attempted as usize, before + required);
            }
            assert_eq!(failure.limit as usize, budget.combined_bytes);
            assert_eq!(failure.at_failure.reservations.combined.current, before);
            assert_eq!(failure.at_failure.reservations.construction.current, 0);
            assert_eq!(failure.at_failure.instructions, 0);
            assert_eq!(failure.at_failure.host_calls, 0);
            assert_empty(failure.after_cleanup.unwrap());
        } else {
            let (control, adopted) = result.ok().unwrap();
            let usage = control.usage(None);
            assert_eq!(usage.reservations.construction.current, required);
            assert_eq!(usage.reservations.combined.current, budget.combined_bytes);
            assert_eq!(usage.reservations.live_tickets, 5);
            let (after, stats) =
                super::super::allocation_tests::measure(|| clean(control, adopted));
            no_allocations(stats);
            assert_empty(after);
        }
    }
    println!(
        "named-inventory admission previous={previous} additional={added} foundation={required}"
    );
}

#[test]
fn final_boundary_cleanup_preserves_real_observation_and_rejected_charges() {
    use super::super::execution::{execution_header_bytes, ExecutionCleanupTail};
    use crate::experimental_wasi::accounted::AccountedWasi;
    use crate::experimental_wasi::WasiGrants;
    for case in 0..7 {
        let (mut control, proof) = adopt(SwiftRunBudget::default());
        let at = cursor(SwiftRunStage::Invocation);
        let mut phase = AccountedWasi::prepare(&mut control, at).unwrap();
        let mut wasi = phase
            .construct(
                WasiGrants::default(),
                WasiBudget::default(),
                Instant::now(),
                at,
            )
            .unwrap();
        phase.complete().unwrap();
        wasi.dispatch(
            &mut control,
            WasiFunction::ArgsSizesGet,
            &[crate::Value::I32(0), crate::Value::I32(4)],
            &mut [0; 8],
            at,
        )
        .unwrap();
        let observation = wasi.checked_usage(&mut control, at).unwrap();
        assert_eq!(observation.calls, 1);
        wasi.cleanup(&mut control).unwrap();
        control
            .drop_proof_with_wasi(proof, Some(observation))
            .unwrap();
        let bytes = execution_header_bytes().unwrap();
        let mut header = if case == 1 {
            None
        } else {
            Some(
                control
                    .admit(SwiftReservationCategory::State, bytes, at)
                    .unwrap(),
            )
        };
        let mut first = None;
        let (invariant, retained) = match case {
            0 | 1 => (None, 0),
            2 => {
                // Fault injection changes only a ledger observation. It must
                // never refund the still-charged combined bytes or ticket.
                control.reservations.state.current = 0;
                (Some(SwiftCleanupInvariant::ReservationUnderflow), bytes)
            }
            3 => {
                first = Some(control.fail(
                    at,
                    Fault::new(SwiftRunFailureKind::GuestTrap, "test_first_cause"),
                    Some(observation),
                ));
                // Test-only bad owner, after the real first failure was latched.
                header.as_mut().unwrap().owner = 0;
                (Some(SwiftCleanupInvariant::ReservationOwner), bytes)
            }
            4 => {
                control.construction.as_mut().unwrap().bytes += 1;
                (
                    Some(SwiftCleanupInvariant::ConstructionBound),
                    foundation_construction_bytes().unwrap(),
                )
            }
            5 => {
                control.control_header.as_mut().unwrap().owner = 0;
                (
                    Some(SwiftCleanupInvariant::ReservationOwner),
                    size_of::<RuntimeControl>(),
                )
            }
            6 => {
                control.reservations.construction.current -= 1;
                (
                    Some(SwiftCleanupInvariant::ReservationUnderflow),
                    foundation_construction_bytes().unwrap(),
                )
            }
            _ => unreachable!(),
        };
        let tail = ExecutionCleanupTail {
            control,
            header,
            final_wasi: Some(observation),
            failure: first,
        };
        let mut outcome = None;
        let mut usage = None;
        let ((), stats) =
            super::super::allocation_tests::measure(|| tail.complete((), &mut outcome, &mut usage));
        no_allocations(stats);
        let usage = usage.unwrap();
        assert_eq!(usage.wasi, Some(observation));
        assert_eq!(usage.cleanup_invariant, invariant);
        assert_eq!(usage.reservations.combined.current, retained);
        assert_eq!(usage.reservations.live_tickets, usize::from(retained != 0));
        if let Some(first) = first {
            let reported = outcome.unwrap();
            assert_eq!(reported.kind, first.kind);
            assert_eq!(reported.code, first.code);
            assert_eq!(reported.function, first.function);
            assert_eq!(reported.offset, first.offset);
            assert_eq!(reported.at_failure, first.at_failure);
            assert_eq!(reported.after_cleanup.unwrap().cleanup_invariant, invariant);
        } else if case == 2 {
            let reported = outcome.unwrap();
            assert_eq!(reported.code, "swift_run_release_underflow");
            assert_eq!(reported.at_failure.wasi, Some(observation));
            assert_eq!(reported.after_cleanup.unwrap().cleanup_invariant, invariant);
        } else {
            // Finish's invariant is an independent cleanup observation; it
            // does not fabricate a terminal failure after record_cleanup ended.
            assert!(outcome.is_none());
        }
        println!("final-boundary cleanup case={case} retained={retained} invariant={invariant:?} allocations={}", stats.allocations);
    }
}

#[test]
fn shared_boundaries_capture_wasi_observation_in_the_immutable_first_failure() {
    let observation = WasiUsage {
        calls: 11,
        work: 19,
        transfer_bytes: 23,
        ..WasiUsage::default()
    };
    for kind in [
        SwiftRunFailureKind::Cancelled,
        SwiftRunFailureKind::Deadline,
        SwiftRunFailureKind::HostCallLimit,
    ] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        match kind {
            SwiftRunFailureKind::Cancelled => control.cancellation.cancel(),
            SwiftRunFailureKind::Deadline => control.deadline = Instant::now(),
            SwiftRunFailureKind::HostCallLimit => control.host_calls = control.budget.host_calls,
            _ => unreachable!(),
        }
        let before = control.host_calls;
        let at = cursor(SwiftRunStage::Invocation);
        let failure = control
            .enter_host_with_wasi(at, Some(observation))
            .unwrap_err();
        assert_eq!(failure.kind, kind);
        assert_eq!(failure.function, at.function);
        assert_eq!(failure.offset, at.offset);
        assert_eq!(failure.at_failure.wasi, Some(observation));
        assert_eq!(control.host_calls, before);
        assert_eq!(control.check(at).unwrap_err(), failure);
        assert_eq!(
            control
                .check_with_wasi(at, Some(WasiUsage::default()))
                .unwrap_err(),
            failure
        );
        assert_empty(clean(control, adopted));
    }
}

#[test]
fn component_owner_check_neither_transfers_nor_refunds_foreign_storage() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let (mut other, other_proof) = adopt(SwiftRunBudget::default());
    let at = cursor(SwiftRunStage::Invocation);
    let ticket = control
        .admit(SwiftReservationCategory::Wasi, 31, at)
        .unwrap();
    let before = control.reservations;
    let other_before = other.reservations;
    control.check_reservation_owner(&ticket, at, None).unwrap();
    let observation = WasiUsage {
        calls: 7,
        ..WasiUsage::default()
    };
    let failure = other
        .check_reservation_owner(&ticket, at, Some(observation))
        .unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
    assert_eq!(failure.at_failure.wasi, Some(observation));
    assert_eq!(
        failure.at_failure.cleanup_invariant,
        Some(SwiftCleanupInvariant::ReservationOwner)
    );
    assert_eq!(control.reservations, before);
    assert_eq!(other.reservations, other_before);
    assert_eq!(other.check(at).unwrap_err(), failure);
    control.drop_reserved([0u8; 31], ticket).unwrap();
    assert_empty(clean(control, adopted));
    assert_empty(clean(other, other_proof));
}

#[test]
fn adopted_preflight_checks_both_original_tickets_without_consuming_authority() {
    let (mut control, mut adopted) = adopt(SwiftRunBudget::default());
    let (mut other, mut other_proof) = adopt(SwiftRunBudget::default());
    let at = cursor(SwiftRunStage::Cache);
    let original = control.reservations;
    let foreign = other.reservations;
    control.check_adopted_owner(&adopted, at, None).unwrap();
    // Test-only corruption: the valid source ticket must not hide a foreign
    // metadata ticket. Both real owners remain intact and can be restored.
    std::mem::swap(&mut adopted.metadata, &mut other_proof.metadata);
    let (failure, stats) = super::super::allocation_tests::measure(|| {
        control.check_adopted_owner(&adopted, at, None).unwrap_err()
    });
    no_allocations(stats);
    assert_eq!(stats.deallocations, 0);
    assert_eq!(failure.code, "swift_run_reservation_owner");
    assert_eq!(control.reservations, original);
    assert_eq!(other.reservations, foreign);
    std::mem::swap(&mut adopted.metadata, &mut other_proof.metadata);
    control.check_adopted_owner(&adopted, at, None).unwrap();
    other.check_adopted_owner(&other_proof, at, None).unwrap();
    let failure = other.check_adopted_owner(&adopted, at, None).unwrap_err();
    assert_eq!(failure.code, "swift_run_reservation_owner");
    assert_eq!(other.reservations, foreign);
    assert_empty(clean(control, adopted));
    assert_empty(clean(other, other_proof));
}

#[test]
fn checked_actual_wasi_pairing_preserves_same_owner_ledger_fault_observation() {
    use crate::experimental_wasi::accounted::AccountedWasi;
    use crate::experimental_wasi::{WasiBudget, WasiGrants};
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let at = cursor(SwiftRunStage::Cache);
    let mut phase = AccountedWasi::prepare(&mut control, at).unwrap();
    let mut owner = phase
        .construct(
            WasiGrants::default(),
            WasiBudget::default(),
            Instant::now(),
            at,
        )
        .unwrap();
    phase.complete().unwrap();
    owner
        .dispatch(
            &mut control,
            WasiFunction::ArgsSizesGet,
            &[crate::Value::I32(0), crate::Value::I32(4)],
            &mut [0u8; 8],
            at,
        )
        .unwrap();
    let observation = owner.usage();
    assert_eq!(observation.calls, 1);
    let before = control.reservations;
    // Test-only damaged accounting does not change the actual header identity.
    // The first invariant must therefore retain this real owner's counters.
    control.reservations.wasi.current = 0;
    let (failure, stats) = super::super::allocation_tests::measure(|| {
        owner.checked_usage(&mut control, at).unwrap_err()
    });
    no_allocations(stats);
    assert_eq!(stats.deallocations, 0);
    assert_eq!(failure.code, "swift_run_reservation_underflow");
    assert_eq!(failure.at_failure.wasi, Some(observation));
    control.reservations = before;
    assert_eq!(owner.checked_usage(&mut control, at).unwrap(), observation);
    owner.cleanup(&mut control).unwrap();
    control
        .drop_proof_with_wasi(adopted, Some(observation))
        .unwrap();
    assert_eq!(control.check(at).unwrap_err(), failure);
    assert_empty(control.finish_owned_cleanup(Some(observation)));
}

#[test]
fn instruction_and_bulk_fuel_failures_retain_actual_wasi_counters() {
    use crate::experimental_wasi::accounted::AccountedWasi;
    use crate::experimental_wasi::{WasiBudget, WasiGrants};
    for instruction in [false, true] {
        for case in 0..=5 {
            if !instruction && case == 5 {
                continue;
            }
            let (mut control, adopted) = adopt(SwiftRunBudget::default());
            let at = cursor(SwiftRunStage::Invocation);
            let mut phase = AccountedWasi::prepare(&mut control, at).unwrap();
            let mut owner = phase
                .construct(
                    WasiGrants::default(),
                    WasiBudget::default(),
                    Instant::now(),
                    at,
                )
                .unwrap();
            phase.complete().unwrap();
            owner
                .dispatch(
                    &mut control,
                    WasiFunction::ArgsSizesGet,
                    &[crate::Value::I32(0), crate::Value::I32(4)],
                    &mut [0u8; 8],
                    at,
                )
                .unwrap();
            let observation = owner.usage();
            assert_eq!(observation.calls, 1);
            assert_eq!(observation.transfer_bytes, 8);
            assert!(observation.work > 0);
            match case {
                0 => (),
                1 => control.cancellation.cancel(),
                2 => control.deadline = Instant::now(),
                3 => control.instruction_fuel = control.budget.instruction_fuel,
                // Test-only damaged counter states exercise checked overflow;
                // no fabricated proof, replacement context or guest execution.
                4 => control.instruction_fuel = u64::MAX,
                5 => control.instructions = u64::MAX,
                _ => unreachable!(),
            }
            let before = control.usage(Some(observation));
            let credits = if instruction { 1 } else { 7 };
            let (result, stats) = super::super::allocation_tests::measure(|| {
                let actual = owner.checked_usage(&mut control, at).unwrap();
                if instruction {
                    control.instruction_with_wasi(at, Some(actual))
                } else {
                    control.charge_fuel_with_wasi(credits, at, Some(actual))
                }
            });
            no_allocations(stats);
            assert_eq!(stats.deallocations, 0);
            assert_eq!(owner.usage(), observation);
            assert_eq!(control.host_calls, 1);
            assert_eq!(control.reservations, before.reservations);
            if case == 0 {
                result.unwrap();
                assert_eq!(control.instruction_fuel, credits);
                assert_eq!(control.instructions, u64::from(instruction));
            } else {
                let failure = result.unwrap_err();
                assert_eq!(
                    failure.kind,
                    match case {
                        1 => SwiftRunFailureKind::Cancelled,
                        2 => SwiftRunFailureKind::Deadline,
                        3 | 4 => SwiftRunFailureKind::FuelExhausted,
                        5 => SwiftRunFailureKind::Invariant,
                        _ => unreachable!(),
                    }
                );
                assert_eq!(failure.at_failure.wasi, Some(observation));
                assert_eq!(failure.function, at.function);
                assert_eq!(failure.offset, at.offset);
                assert_eq!(failure.at_failure.host_calls, 1);
                assert_eq!(control.instructions, before.instructions);
                // Existing order charges one fuel before checking instruction
                // count overflow; all other rejected boundaries commit neither.
                let charged = before.instruction_fuel + u64::from(case == 5);
                assert_eq!(control.instruction_fuel, charged);
                assert_eq!(failure.at_failure.instruction_fuel, charged);
                if case == 3 || case == 4 {
                    assert_eq!(failure.code, "swift_run_fuel");
                    assert_eq!(failure.resource, Some(SwiftRunResource::InstructionFuel));
                    assert_eq!(
                        failure.attempted,
                        before.instruction_fuel.saturating_add(credits)
                    );
                    assert_eq!(failure.limit, control.budget.instruction_fuel);
                }
                if case == 5 {
                    assert_eq!(failure.code, "swift_run_instruction_overflow");
                }
                let ((), stats) = super::super::allocation_tests::measure(|| {
                    assert_eq!(control.instruction(at).unwrap_err(), failure);
                    assert_eq!(control.charge_fuel(0, at).unwrap_err(), failure);
                    assert_eq!(
                        control
                            .instruction_with_wasi(at, Some(WasiUsage::default()))
                            .unwrap_err(),
                        failure
                    );
                    assert_eq!(
                        control
                            .charge_fuel_with_wasi(credits, at, None)
                            .unwrap_err(),
                        failure
                    );
                });
                no_allocations(stats);
                assert_eq!(stats.deallocations, 0);
                assert_eq!(control.instruction_fuel, charged);
                assert_eq!(control.instructions, before.instructions);
                assert_eq!(owner.usage(), observation);
            }
            owner.cleanup(&mut control).unwrap();
            control
                .drop_proof_with_wasi(adopted, Some(observation))
                .unwrap();
            let after = control.finish_owned_cleanup(Some(observation));
            assert_eq!(after.wasi, Some(observation));
            assert_empty(after);
        }
    }
}

// Independently authored contextual and legacy control oracles.
#[test]
fn cdr07_all_six_contextual_live_resources_use_available_count() {
    for (live,resource) in [(Live::CacheEntries,SwiftRunResource::CacheEntries),
        (Live::ActivePins,SwiftRunResource::ActivePins),(Live::Frames,SwiftRunResource::Frames),
        (Live::Values,SwiftRunResource::Values),(Live::Controls,SwiftRunResource::Controls),
        (Live::MemoryPages,SwiftRunResource::MemoryPages)] {
        for available in [0,2] {
            let (mut control, adopted)=adopt(SwiftRunBudget::default());
            let c=Cursor{stage:SwiftRunStage::Invocation,function:Some(47),offset:Some(9876)};
            control.add_live(live,available,c).unwrap();
            let before=control.live;
            let failure=control.remove_live_at_with_wasi(live,available+1,c,None).unwrap_err();
            assert_eq!((failure.stage,failure.function,failure.offset),(c.stage,c.function,c.offset));
            assert_eq!((failure.resource,failure.attempted,failure.limit),(Some(resource),(available+1)as u64,available as u64));
            assert_eq!(failure.kind,SwiftRunFailureKind::Invariant);
            assert_eq!(failure.at_failure.cleanup_invariant,Some(SwiftCleanupInvariant::LiveUnderflow));
            assert_eq!((failure.observed_capacity,failure.wasi_failure,failure.guest_exit),(None,None,None));
            assert_eq!(control.live,before);
            control.remove_live(live,available).unwrap();
            assert_empty(clean(control,adopted));
        }
    }
}
#[test]
fn cdr08_success_and_zero_removal_match_original_six_resources() {
    for live in [Live::CacheEntries,Live::ActivePins,Live::Frames,Live::Values,Live::Controls,Live::MemoryPages] {
        let (mut old,oa)=adopt(SwiftRunBudget::default());
        let (mut new,na)=adopt(SwiftRunBudget::default());
        let c=cursor(SwiftRunStage::Invocation);
        old.add_live(live,3,c).unwrap();new.add_live(live,3,c).unwrap();
        for amount in [0,1,2,0] {
            let before=(new.instructions,new.instruction_fuel,new.execution_work);
            old.remove_live_with_wasi(live,amount,None).unwrap();
            new.remove_live_at_with_wasi(live,amount,c,None).unwrap();
            assert_eq!(old.live,new.live);
            assert_eq!((new.instructions,new.instruction_fuel,new.execution_work),before);
            assert!(new.first_failure.is_none());assert!(new.cleanup_invariant.is_none());
        }
        assert_empty(clean(old,oa));assert_empty(clean(new,na));
    }
}
#[test]
fn cdr09_first_failure_is_immutable_through_both_removals_and_cleanup() {
    for contextual in [false,true] {
        let (mut control,adopted)=adopt(SwiftRunBudget::default());
        let c=Cursor{stage:SwiftRunStage::Invocation,function:Some(71),offset:Some(33)};
        let original=control.fail(c,Fault::new(SwiftRunFailureKind::GuestTrap,"cdr_original")
            .limit(SwiftRunResource::MemoryPages,7,6),None);
        let c2=Cursor{stage:SwiftRunStage::Initialization,function:Some(1),offset:Some(2)};
        let returned=if contextual {control.remove_live_at_with_wasi(Live::Values,9,c2,None)}
            else {control.remove_live_with_wasi(Live::Controls,2,None)}.unwrap_err();
        assert_eq!(returned,original);
        let after=control.record_cleanup(None).unwrap();let mut exact=after;exact.after_cleanup=None;
        assert_eq!(exact,original);assert_eq!(original.at_failure.cleanup_invariant,None);
        assert_eq!(after.after_cleanup.unwrap().cleanup_invariant,Some(SwiftCleanupInvariant::LiveUnderflow));
        assert_empty(clean(control,adopted));
    }
}
#[test]
fn cdr10_legacy_six_resources_stay_cursorless() {
    for live in [Live::CacheEntries,Live::ActivePins,Live::Frames,Live::Values,Live::Controls,Live::MemoryPages] {
        let (mut control,adopted)=adopt(SwiftRunBudget::default());
        let failure=control.remove_live_with_wasi(live,1,None).unwrap_err();
        assert_eq!(failure.stage,SwiftRunStage::Cleanup);
        assert_eq!((failure.function,failure.offset,failure.resource),(None,None,None));
        assert_eq!((failure.attempted,failure.limit),(0,0));
        assert_empty(clean(control,adopted));
    }
}
#[test]
fn cdr13_contextual_success_failure_refuse_first_allocation() {
    use crate::experimental_swift_reactor::allocation_tests::measure_extended;
    for fail in [false,true] {
        let (mut control,adopted)=adopt(SwiftRunBudget::default());
        let c=cursor(SwiftRunStage::Invocation);control.add_live(Live::Values,1,c).unwrap();
        let (result,stats)=measure_extended(Some(0),||control.remove_live_at_with_wasi(Live::Values,if fail{2}else{1},c,None));
        assert_eq!(result.is_err(),fail);assert_eq!(stats.attempts,0);assert_eq!(stats.injected_failures,0);
        if fail {control.remove_live(Live::Values,1).unwrap();}
        assert_empty(clean(control,adopted));
    }
}
