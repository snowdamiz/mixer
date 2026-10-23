//! Independently authored review probes. Compiled only in the retained snapshot.
use super::*;
use crate::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget};
use crate::experimental_wasi::{WasiFunction, WasiReservations};
use crate::Type;

fn leb(output: &mut Vec<u8>, mut n: usize) {
    while n > 127 {
        output.push((n as u8 & 127) | 128);
        n >>= 7;
    }
    output.push(n as u8);
}
fn text(output: &mut Vec<u8>, name: &str) {
    leb(output, name.len());
    output.extend_from_slice(name.as_bytes());
}
fn part(output: &mut Vec<u8>, id: u8, content: Vec<u8>) {
    output.push(id);
    leb(output, content.len());
    output.extend(content);
}
fn type_code(t: Type) -> u8 {
    match t {
        Type::I32 => 127,
        Type::I64 => 126,
        Type::F32 => 125,
        Type::F64 => 124,
    }
}
fn sealed() -> ValidatedSwiftReactor {
    // Independently assembled valid fixed ABI, with duplicate signatures interned.
    // This tests genuine complete-validation authority, not a forged proof.
    let mut signatures: Vec<Vec<u8>> = Vec::new();
    let mut imports = vec![34];
    for f in WasiFunction::ALL {
        let mut signature = vec![96];
        leb(&mut signature, f.parameters().len());
        signature.extend(f.parameters().iter().copied().map(type_code));
        leb(&mut signature, f.results().len());
        signature.extend(f.results().iter().copied().map(type_code));
        let index = if let Some(index) = signatures.iter().position(|old| old == &signature) {
            index
        } else {
            signatures.push(signature);
            signatures.len() - 1
        };
        text(&mut imports, "wasi_snapshot_preview1");
        text(&mut imports, std::str::from_utf8(f.name()).unwrap());
        imports.push(0);
        leb(&mut imports, index);
    }
    let void = signatures.len();
    signatures.push(vec![96, 0, 0]);
    let result = signatures.len();
    signatures.push(vec![96, 0, 1, 127]);
    let mut types = Vec::new();
    leb(&mut types, signatures.len());
    for signature in signatures {
        types.extend(signature);
    }
    let mut functions = vec![29];
    for index in 0..29 {
        leb(&mut functions, if index == 28 { result } else { void });
    }
    let mut table = vec![1, 112, 1];
    leb(&mut table, 46_713);
    leb(&mut table, 46_713);
    let mut memory = vec![1, 0];
    leb(&mut memory, 584);
    let mut exports = vec![3];
    for (name, kind, index) in [
        ("mixer_fieldlog_corpus_v1", 0, 62),
        ("_initialize", 0, 35),
        ("memory", 2, 0),
    ] {
        text(&mut exports, name);
        exports.push(kind);
        leb(&mut exports, index);
    }
    let mut bodies = vec![29];
    for index in 0..29 {
        // Void definitions execute a nop; corpus returns 7. Neither is executed.
        bodies.extend(if index == 28 {
            &[4, 0, 65, 7, 11][..]
        } else {
            &[3, 0, 1, 11][..]
        });
    }
    let mut bytes = vec![0, 97, 115, 109, 1, 0, 0, 0];
    for (id, content) in [
        (1, types),
        (2, imports),
        (3, functions),
        (4, table),
        (5, memory),
        (7, exports),
        (10, bodies),
    ] {
        part(&mut bytes, id, content);
    }
    validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap()
}
fn at() -> Cursor {
    Cursor {
        stage: SwiftRunStage::Invocation,
        function: Some(62),
        offset: Some(719),
    }
}
fn owner() -> (RuntimeControl, AdoptedProof) {
    RuntimeControl::adopt(
        sealed(),
        SwiftRunBudget::default(),
        Instant::now(),
        Cancellation::default(),
    )
    .unwrap()
}
fn category(index: usize) -> SwiftReservationCategory {
    [
        SwiftReservationCategory::RetainedSource,
        SwiftReservationCategory::RetainedMetadata,
        SwiftReservationCategory::Cache,
        SwiftReservationCategory::State,
        SwiftReservationCategory::Wasi,
        SwiftReservationCategory::Shared,
        SwiftReservationCategory::Construction,
    ][index]
}
fn close(mut control: RuntimeControl, proof: AdoptedProof) -> SwiftRunUsage {
    control.drop_proof(proof).unwrap();
    control.finish_owned_cleanup(None)
}

#[test]
fn independent_reference_model_four_thousand_interleaved_reservations() {
    let (mut control, proof) = owner();
    let baseline = control.usage(None).reservations;
    let mut live = [0usize; 7];
    let mut peaks = [0usize; 7];
    for i in 0..7 {
        live[i] = baseline.category(category(i)).current;
        peaks[i] = live[i];
    }
    let mut combined = baseline.combined.current;
    let mut combined_peak = combined;
    let mut count = baseline.live_tickets;
    let mut tickets: [Option<(ReservationTicket, usize, usize)>; 70] =
        std::array::from_fn(|_| None);
    let mut random = 0xa981_f034_250d_ebc3u64;
    let ((), allocations) = super::super::allocation_tests::measure(|| {
        for step in 0..4_000 {
            random ^= random << 13;
            random ^= random >> 7;
            random ^= random << 17;
            let index = random as usize % tickets.len();
            if let Some((ticket, kind, bytes)) = tickets[index].take() {
                control.drop_reserved((), ticket).unwrap();
                live[kind] -= bytes;
                combined -= bytes;
                count -= 1;
            } else {
                let kind = (random >> 12) as usize % 7;
                let bytes = if step % 19 == 0 {
                    0
                } else {
                    (random >> 25) as usize % 1_024
                };
                tickets[index] = Some((
                    control.admit(category(kind), bytes, at()).unwrap(),
                    kind,
                    bytes,
                ));
                live[kind] += bytes;
                peaks[kind] = peaks[kind].max(live[kind]);
                combined += bytes;
                combined_peak = combined_peak.max(combined);
                count += 1;
            }
            let actual = control.usage(None).reservations;
            for i in 0..7 {
                assert_eq!(
                    actual.category(category(i)),
                    &SwiftReservationUsage {
                        current: live[i],
                        peak: peaks[i]
                    }
                );
            }
            assert_eq!(
                actual.combined,
                SwiftReservationUsage {
                    current: combined,
                    peak: combined_peak
                }
            );
            assert_eq!(actual.live_tickets, count);
            assert!(actual.peak_tickets <= MAX_RESERVATION_TICKETS);
        }
        for pending in &mut tickets {
            if let Some((ticket, _, _)) = pending.take() {
                control.drop_reserved((), ticket).unwrap();
            }
        }
    });
    assert_eq!((allocations.allocations, allocations.reallocations), (0, 0));
    let end = close(control, proof);
    assert_eq!(
        (
            end.reservations.combined.current,
            end.reservations.live_tickets
        ),
        (0, 0)
    );
    assert_eq!(end.reservations.combined.peak, combined_peak);
}

#[test]
fn destructor_unwind_cannot_refund_storage_or_construction_early() {
    struct PanickingStorage;
    impl Drop for PanickingStorage {
        fn drop(&mut self) {
            panic!("independent storage destructor fault");
        }
    }
    let (mut control, proof) = owner();
    let ticket = control
        .admit(SwiftReservationCategory::State, 23, at())
        .unwrap();
    let before = control.usage(None).reservations;
    assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(
        || control.drop_reserved(PanickingStorage, ticket)
    ))
    .is_err());
    assert_eq!(control.usage(None).reservations, before);
    let floor = foundation_construction_bytes().unwrap();
    control.enlarge_construction(floor + 41, at()).unwrap();
    let before = control.usage(None).reservations;
    assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(
        || control.end_construction_phase(PanickingStorage, floor)
    ))
    .is_err());
    assert_eq!(control.usage(None).reservations, before);
    let end = close(control, proof);
    assert_eq!(
        (
            end.reservations.state.current,
            end.reservations.combined.current,
            end.reservations.live_tickets
        ),
        (23, 23 + floor + 41, 2)
    );
}

#[test]
fn foreign_adopted_proof_drops_but_neither_ledger_refunds_wrong_owner() {
    let (mut first, first_proof) = owner();
    let (second, second_proof) = owner();
    let first_before = first.usage(None).reservations;
    let second_before = second.usage(None).reservations;
    let (failure, allocation) =
        super::super::allocation_tests::measure(|| first.drop_proof(second_proof).unwrap_err());
    assert_eq!(failure.code, "swift_run_release_owner");
    assert_eq!(first.usage(None).reservations, first_before);
    assert_eq!(second.usage(None).reservations, second_before);
    assert_eq!((allocation.allocations, allocation.reallocations), (0, 0));
    assert!(allocation.freed_bytes >= second_before.retained_source.current);
    assert_eq!(close(first, first_proof).reservations.combined.current, 0);
    let second_end = second.finish_owned_cleanup(None);
    assert_eq!(
        second_end.reservations.combined.current,
        second_before.retained_source.current + second_before.retained_metadata.current
    );
    assert_eq!(second_end.reservations.live_tickets, 2);
}

#[test]
fn sticky_failure_blocks_every_effect_seam_but_cleanup_still_drains() {
    let (mut control, proof) = owner();
    let ticket = control
        .admit(SwiftReservationCategory::Cache, 47, at())
        .unwrap();
    control.add_live(Live::Frames, 1, at()).unwrap();
    let first = control.fail(
        at(),
        Fault::new(SwiftRunFailureKind::GuestExit, "independent_first_exit"),
        None,
    );
    let before = control.usage(None);
    let ((), allocation) = super::super::allocation_tests::measure(|| {
        assert_eq!(
            control
                .admit(SwiftReservationCategory::Wasi, 0, at())
                .unwrap_err(),
            first
        );
        assert_eq!(control.admit_cache_entry(0, at()).unwrap_err(), first);
        assert_eq!(
            control.enlarge_construction(usize::MAX, at()).unwrap_err(),
            first
        );
        assert_eq!(control.exact_capacity(1, 2, at()).unwrap_err(), first);
        assert_eq!(control.work(Work::Cache, 0, at()).unwrap_err(), first);
        assert_eq!(control.work(Work::Execution, 0, at()).unwrap_err(), first);
        assert_eq!(control.instruction(at()).unwrap_err(), first);
        assert_eq!(control.charge_fuel(0, at()).unwrap_err(), first);
        assert_eq!(control.enter_host(at()).unwrap_err(), first);
        assert_eq!(control.add_live(Live::Frames, 0, at()).unwrap_err(), first);
        assert_eq!(
            control
                .carry_wasi_deadline(
                    Instant::now(),
                    WasiBudget {
                        calls: u64::MAX,
                        ..WasiBudget::default()
                    },
                    at()
                )
                .unwrap_err(),
            first
        );
        assert_eq!(control.usage(None).reservations, before.reservations);
        assert_eq!(control.usage(None).live, before.live);
        control.drop_reserved((), ticket).unwrap();
        control.remove_live(Live::Frames, 1).unwrap();
    });
    assert_eq!((allocation.allocations, allocation.reallocations), (0, 0));
    let after = control.record_cleanup(None).unwrap();
    assert_eq!(after.at_failure, first.at_failure);
    assert_eq!(after.after_cleanup.unwrap().live.frames.current, 0);
    assert_eq!(close(control, proof).reservations.combined.current, 0);
}

#[test]
fn wasi_observation_does_not_drive_admission_or_duplicate_counters() {
    let (mut control, proof) = owner();
    let artificial = WasiUsage {
        calls: u64::MAX,
        work: u64::MAX,
        transfer_bytes: u64::MAX,
        random_bytes: u64::MAX,
        log_bytes: u64::MAX,
        failures: u64::MAX,
        reservations: WasiReservations {
            current_bytes: u64::MAX,
            peak_bytes: u64::MAX,
            ..WasiReservations::default()
        },
    };
    let before = control.usage(Some(artificial));
    assert_eq!(before.wasi, Some(artificial));
    assert_eq!(control.usage(None).wasi, None);
    let ticket = control
        .admit(SwiftReservationCategory::Wasi, 1, at())
        .unwrap();
    control.work(Work::Execution, 3, at()).unwrap();
    control.enter_host(at()).unwrap();
    let observation = control.usage(Some(artificial));
    assert_eq!(observation.host_calls, 1);
    assert_eq!(observation.execution_work, 3);
    assert_eq!(observation.cache_work, 0);
    assert_eq!(
        observation.reservations.combined.current,
        before.reservations.combined.current + 1
    );
    assert_eq!(observation.wasi, Some(artificial));
    let mut fault = Fault::new(SwiftRunFailureKind::Wasi, "independent_wasi_fault");
    fault.wasi_failure = Some(WasiFailure::InvalidMemory);
    let first = control.fail(at(), fault, Some(artificial));
    assert_eq!(first.at_failure.wasi, Some(artificial));
    assert_eq!(first.wasi_failure, Some(WasiFailure::InvalidMemory));
    assert_eq!(control.check(at()).unwrap_err(), first);
    control.drop_reserved((), ticket).unwrap();
    let end = close(control, proof);
    assert_eq!(end.reservations.combined.current, 0);
    assert_eq!(end.wasi, None);
}

#[test]
fn selected_wasi_deadline_never_reopens_when_later_budget_arrives() {
    let (mut control, proof) = owner();
    let origin = Instant::now();
    let earlier = control
        .carry_wasi_deadline(
            origin,
            WasiBudget {
                deadline_ms: 15,
                ..WasiBudget::default()
            },
            at(),
        )
        .unwrap();
    assert_eq!(earlier, origin + Duration::from_millis(15));
    for extra in [16, 30, 29_999, 30_000] {
        assert_eq!(
            control
                .carry_wasi_deadline(
                    origin,
                    WasiBudget {
                        deadline_ms: extra,
                        ..WasiBudget::default()
                    },
                    at()
                )
                .unwrap(),
            earlier
        );
    }
    std::thread::sleep(Duration::from_millis(25));
    let first = control.check(at()).unwrap_err();
    assert_eq!(first.kind, SwiftRunFailureKind::Deadline);
    assert_eq!(first.deadline_origin, SwiftDeadlineOrigin::Wasi);
    assert!(first.at_failure.deadline_overshoot_micros > 0);
    assert_eq!(
        control
            .carry_wasi_deadline(Instant::now(), WasiBudget::default(), at())
            .unwrap_err(),
        first
    );
    assert_eq!(close(control, proof).reservations.combined.current, 0);
}

#[test]
fn omitted_construction_phase_end_cannot_refund_an_external_live_buffer() {
    let (mut control, proof) = owner();
    let floor = foundation_construction_bytes().unwrap();
    control.enlarge_construction(floor + 181, at()).unwrap();
    let storage = Vec::<u8>::with_capacity(181);
    let end = close(control, proof);
    assert_eq!(storage.capacity(), 181); // Actual phase storage still exists.
    assert_eq!(end.reservations.construction.current, floor + 181);
    assert_eq!(end.reservations.combined.current, floor + 181);
    assert_eq!(end.reservations.live_tickets, 1);
    assert!(end.cleanup_invariant.is_some());
    drop(storage);
}
