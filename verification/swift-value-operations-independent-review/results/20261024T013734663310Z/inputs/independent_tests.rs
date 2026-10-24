//! Independent native behavior probes; attached only to an archived test harness.
use super::*;
use crate::experimental_swift_reactor::allocation_tests::measure_extended;
use crate::experimental_swift_reactor::execution_tests::{construct_owned, construction_adopt};

fn at() -> Cursor {
    Cursor {
        stage: SwiftRunStage::Invocation,
        function: Some(91),
        offset: Some(711),
    }
}
fn owner(budget: SwiftRunBudget) -> SwiftReactorInstance {
    construct_owned(&mut construction_adopt(budget)).unwrap()
}
fn observe(owner: &SwiftReactorInstance) -> SwiftRunUsage {
    owner
        .control
        .as_ref()
        .unwrap()
        .usage(Some(owner.wasi.as_ref().unwrap().usage()))
}
fn finish_owner(owner: SwiftReactorInstance, retained: Option<SwiftRunFailure>) {
    let mut slot = Some(owner);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut slot));
    let tail = returned.take().unwrap().unwrap();
    let mut outcome = None;
    let mut usage = None;
    // The retained diagnostic lives until the same real header is refunded.
    tail.complete((slot, returned, retained), &mut outcome, &mut usage);
    let usage = usage.unwrap();
    assert_eq!(usage.reservations.combined.current, 0);
    assert_eq!(usage.reservations.live_tickets, 0);
    assert_eq!(usage.live.values.current, 0);
    if let Some(original) = retained {
        assert_eq!(outcome.unwrap().code, original.code);
    }
}

#[test]
fn independent_values_native_random_integer_results_and_exact_work() {
    let mut owner = owner(SwiftRunBudget::default());
    let before = observe(&owner);
    let mut prepared = Some(owner.prepare_value_operation(at()));
    let mut phase = prepared.take().unwrap().unwrap();
    let mut seed = 0xdada_0123_4455_6677u64;
    let mut calls = 0;
    for _ in 0..257 {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        let a = seed as i64;
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        let b = seed as i64;
        for (op, expected) in [
            (0x7c, a.wrapping_add(b)),
            (0x7d, a.wrapping_sub(b)),
            (0x7e, a.wrapping_mul(b)),
            (0x83, a & b),
            (0x84, a | b),
            (0x85, a ^ b),
            (0x86, a.wrapping_shl(b as u32)),
            (0x88, (a as u64).wrapping_shr(b as u32) as i64),
            (0x89, a.rotate_left(b as u32)),
            (0x8a, a.rotate_right(b as u32)),
        ] {
            let (actual, allocations) = measure_extended(Some(0), || {
                phase.push_value(Value::I64(a))?;
                phase.push_value(Value::I64(b))?;
                phase.numeric_value(op, false)?;
                phase.pop_value()
            });
            assert_eq!(actual.unwrap(), Value::I64(expected));
            assert_eq!(allocations.attempts, 0);
            calls += 1;
        }
    }
    phase
        .complete_values(ValueOperationStorage {
            preparation: prepared,
            outcome: None,
        })
        .unwrap();
    let after = observe(&owner);
    assert_eq!(after.execution_work - before.execution_work, calls * 6);
    assert_eq!(after.instruction_fuel, before.instruction_fuel);
    assert_eq!(after.instructions, before.instructions);
    assert_eq!(after.live.values.current, 0);
    assert_eq!(
        after.reservations.construction.current,
        before.reservations.construction.current
    );
    finish_owner(owner, None);
}

#[test]
fn independent_values_float_bits_and_all_saturating_subopcodes() {
    let mut owner = owner(SwiftRunBudget::default());
    let mut prepared = Some(owner.prepare_value_operation(at()));
    let mut phase = prepared.take().unwrap().unwrap();
    for (op, values, expected) in [
        (
            0x8b,
            &[Value::F32(0xff81_4321)][..],
            Value::F32(0x7f81_4321),
        ),
        (
            0x9a,
            &[Value::F64(0x7ff0_0000_0000_1234)][..],
            Value::F64(0xfff0_0000_0000_1234),
        ),
        (
            0x96,
            &[Value::F32(0), Value::F32(0x8000_0000)][..],
            Value::F32(0x8000_0000),
        ),
        (
            0xa5,
            &[Value::F64(0x8000_0000_0000_0000), Value::F64(0)][..],
            Value::F64(0),
        ),
        (0xa9, &[Value::F32((-0.9f32).to_bits())][..], Value::I32(0)),
        (0xb1, &[Value::F64(0.999f64.to_bits())][..], Value::I64(0)),
    ] {
        let (raw, allocations) = measure_extended(Some(0), || {
            for value in values {
                phase.push_value(*value)?;
            }
            phase.numeric_value(op, false)?;
            phase.pop_value()
        });
        assert_eq!(raw.unwrap(), expected);
        assert_eq!(allocations.attempts, 0);
    }
    for sub in 0..8u8 {
        for kind in 0..3 {
            let signed = sub % 2 == 0;
            let input = if sub % 4 < 2 {
                Value::F32(
                    match kind {
                        0 => f32::NAN,
                        1 => f32::INFINITY,
                        _ => f32::NEG_INFINITY,
                    }
                    .to_bits(),
                )
            } else {
                Value::F64(
                    match kind {
                        0 => f64::NAN,
                        1 => f64::INFINITY,
                        _ => f64::NEG_INFINITY,
                    }
                    .to_bits(),
                )
            };
            let expected = if sub < 4 {
                Value::I32(match (kind, signed) {
                    (0, _) | (2, false) => 0,
                    (1, true) => i32::MAX,
                    (1, false) => -1,
                    _ => i32::MIN,
                })
            } else {
                Value::I64(match (kind, signed) {
                    (0, _) | (2, false) => 0,
                    (1, true) => i64::MAX,
                    (1, false) => -1,
                    _ => i64::MIN,
                })
            };
            let (raw, allocations) = measure_extended(Some(0), || {
                phase.push_value(input)?;
                phase.numeric_value(sub, true)?;
                phase.pop_value()
            });
            assert_eq!(raw.unwrap(), expected);
            assert_eq!(allocations.attempts, 0);
        }
    }
    phase
        .complete_values(ValueOperationStorage {
            preparation: prepared,
            outcome: None,
        })
        .unwrap();
    finish_owner(owner, None);
}

#[test]
fn independent_values_traps_preserve_prefix_then_clear_real_storage() {
    for (inputs, op, expected) in [
        (
            &[Value::I64(13), Value::I64(0)][..],
            0x80,
            "integer_divide_by_zero",
        ),
        (
            &[Value::I64(i64::MIN), Value::I64(-1)][..],
            0x7f,
            "integer_overflow",
        ),
        (
            &[Value::F32(f32::INFINITY.to_bits())][..],
            0xa8,
            "integer_overflow",
        ),
        (
            &[Value::F64(f64::NAN.to_bits())][..],
            0xb1,
            "invalid_conversion_to_integer",
        ),
    ] {
        let mut owner = owner(SwiftRunBudget::default());
        let previous = observe(&owner).reservations.construction.current;
        let mut prepared = Some(owner.prepare_value_operation(at()));
        let mut phase = prepared.take().unwrap().unwrap();
        phase.push_value(Value::I32(0x1234)).unwrap();
        for input in inputs {
            phase.push_value(*input).unwrap();
        }
        let work = phase.operation.control.usage(None).execution_work;
        let (raw, allocations) = measure_extended(Some(0), || phase.numeric_value(op, false));
        let failure = raw.unwrap_err();
        assert_eq!(failure.code, expected);
        assert_eq!(failure.kind, SwiftRunFailureKind::GuestTrap);
        assert_eq!(failure.at_failure.live.values.current, 1);
        assert_eq!(
            failure.at_failure.execution_work,
            work + inputs.len() as u64 + 1
        );
        assert_eq!(failure.at_failure.wasi, Some(phase.operation.wasi.usage()));
        assert_eq!(phase.parts.values.as_slice(), &[Value::I32(0x1234)]);
        assert_eq!(allocations.attempts, 0);
        assert_eq!(phase.pop_value().unwrap_err(), failure);
        let (completion, allocations) = measure_extended(Some(0), || {
            phase.complete_values(ValueOperationStorage {
                preparation: prepared,
                outcome: Some(Err(failure)),
            })
        });
        completion.unwrap();
        assert_eq!(allocations.attempts, 0);
        assert!(owner.state.as_ref().unwrap().values.is_empty());
        assert_eq!(observe(&owner).live.values.current, 0);
        assert_eq!(observe(&owner).reservations.construction.current, previous);
        finish_owner(owner, Some(failure));
    }
}

#[test]
fn independent_values_every_rejected_opcode_is_untouched_and_allocation_free() {
    for saturating in [false, true] {
        for op in 0..=255u8 {
            if if saturating {
                op <= 7
            } else {
                (0x45..=0xc4).contains(&op)
            } {
                continue;
            }
            let mut owner = owner(SwiftRunBudget::default());
            let mut prepared = Some(owner.prepare_value_operation(at()));
            let mut phase = prepared.take().unwrap().unwrap();
            phase.push_value(Value::F64(0x7ff8_0000_0000_1234)).unwrap();
            let work = phase.operation.control.usage(None).execution_work;
            let (raw, allocations) =
                measure_extended(Some(0), || phase.numeric_value(op, saturating));
            let failure = raw.unwrap_err();
            assert_eq!(failure.kind, SwiftRunFailureKind::UnsupportedEnvironment);
            assert_eq!(failure.code, "swift_execution_unsupported_numeric");
            assert_eq!(failure.at_failure.execution_work, work);
            assert_eq!(
                phase.parts.values.as_slice(),
                &[Value::F64(0x7ff8_0000_0000_1234)]
            );
            assert_eq!(allocations.attempts, 0);
            phase
                .complete_values(ValueOperationStorage {
                    preparation: prepared,
                    outcome: Some(Err(failure)),
                })
                .unwrap();
            finish_owner(owner, Some(failure));
        }
    }
}

#[test]
fn independent_values_cancel_after_publication_restores_exact_phase_and_keeps_first_cause() {
    let mut owner = owner(SwiftRunBudget::default());
    let before = observe(&owner);
    let mut prepared = Some(owner.prepare_value_operation(at()));
    let mut phase = prepared.take().unwrap().unwrap();
    phase.push_value(Value::I64(7)).unwrap();
    phase.operation.control.cancellation().cancel();
    let (raw, allocations) = measure_extended(Some(0), || phase.pop_value());
    let failure = raw.unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
    assert_eq!(failure.at_failure.wasi, Some(phase.operation.wasi.usage()));
    assert_eq!(phase.parts.values.as_slice(), &[Value::I64(7)]);
    assert_eq!(allocations.attempts, 0);
    assert_eq!(phase.numeric_value(255, false).unwrap_err(), failure);
    phase
        .complete_values(ValueOperationStorage {
            preparation: prepared,
            outcome: Some(Err(failure)),
        })
        .unwrap();
    let after = observe(&owner);
    assert_eq!(after.live.values.current, 0);
    assert_eq!(after.execution_work, before.execution_work + 1);
    assert_eq!(
        after.reservations.construction.current,
        before.reservations.construction.current
    );
    assert_eq!(owner.prepare_value_operation(at()).err().unwrap(), failure);
    finish_owner(owner, Some(failure));
}

#[test]
fn independent_values_exact_work_boundary_and_cleanup_does_not_spend_work() {
    let baseline = owner(SwiftRunBudget::default());
    let work = observe(&baseline).execution_work;
    finish_owner(baseline, None);
    let mut owner = owner(SwiftRunBudget {
        execution_work: work + 6,
        ..SwiftRunBudget::default()
    });
    let previous = observe(&owner).reservations.construction.current;
    let mut prepared = Some(owner.prepare_value_operation(at()));
    let mut phase = prepared.take().unwrap().unwrap();
    phase.push_value(Value::I32(8)).unwrap();
    phase.push_value(Value::I32(3)).unwrap();
    phase.numeric_value(0x6b, false).unwrap();
    assert_eq!(phase.pop_value().unwrap(), Value::I32(5));
    let failure = phase.push_value(Value::I32(9)).unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::WorkExhausted);
    assert!(phase.parts.values.is_empty());
    assert_eq!(failure.at_failure.execution_work, work + 6);
    phase
        .complete_values(ValueOperationStorage {
            preparation: prepared,
            outcome: Some(Err(failure)),
        })
        .unwrap();
    assert_eq!(observe(&owner).execution_work, work + 6);
    assert_eq!(observe(&owner).reservations.construction.current, previous);
    finish_owner(owner, Some(failure));
}

#[test]
fn independent_values_small_capacity_publication_is_atomic() {
    for capacity in [0, 1, 2, 127, 128, 129] {
        let mut owner = owner(SwiftRunBudget {
            values: capacity,
            ..SwiftRunBudget::default()
        });
        let mut prepared = Some(owner.prepare_value_operation(at()));
        let mut phase = prepared.take().unwrap().unwrap();
        let accepted = capacity.min(128);
        for _ in 0..accepted {
            phase.push_value(Value::I32(1)).unwrap();
        }
        let pointer = phase.parts.values.as_ptr();
        let (raw, allocations) = measure_extended(Some(0), || phase.push_value(Value::I32(2)));
        let failure = raw.unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::ValueLimit);
        assert_eq!(phase.parts.values.len(), accepted);
        assert_eq!(failure.at_failure.live.values.current, accepted);
        assert_eq!(phase.parts.values.as_ptr(), pointer);
        assert_eq!(allocations.attempts, 0);
        phase
            .complete_values(ValueOperationStorage {
                preparation: prepared,
                outcome: Some(Err(failure)),
            })
            .unwrap();
        finish_owner(owner, Some(failure));
    }
}

#[test]
fn independent_values_underflow_and_bad_types_do_not_consume_or_charge_numeric_work() {
    for (inputs, op) in [
        (&[][..], 0x50),
        (&[Value::I64(1)][..], 0x7c),
        (&[Value::I32(1), Value::I64(2)][..], 0x7c),
        (&[Value::I64(1), Value::F64(0)][..], 0xa0),
    ] {
        let mut owner = owner(SwiftRunBudget::default());
        let mut prepared = Some(owner.prepare_value_operation(at()));
        let mut phase = prepared.take().unwrap().unwrap();
        for input in inputs {
            phase.push_value(*input).unwrap();
        }
        let work = phase.operation.control.usage(None).execution_work;
        let failure = phase.numeric_value(op, false).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
        assert_eq!(failure.at_failure.execution_work, work);
        assert_eq!(phase.parts.values.as_slice(), inputs);
        phase
            .complete_values(ValueOperationStorage {
                preparation: prepared,
                outcome: Some(Err(failure)),
            })
            .unwrap();
        finish_owner(owner, Some(failure));
    }
}

#[test]
fn independent_values_repeated_phases_keep_same_owners_bound_and_caller_storage() {
    let mut owner = owner(SwiftRunBudget::default());
    let before = observe(&owner);
    let pointer = owner.state.as_ref().unwrap().values.as_ptr();
    let mut retained_value = None;
    for number in 0..32 {
        let mut prepared = Some(owner.prepare_value_operation(at()));
        let mut phase = prepared.take().unwrap().unwrap();
        phase.push_value(Value::I32(number)).unwrap();
        let mut outcome = Some(phase.pop_value().map(Some));
        retained_value = outcome.take().unwrap().unwrap();
        let (completed, allocations) = measure_extended(Some(0), || {
            phase.complete_values(ValueOperationStorage {
                preparation: prepared,
                outcome,
            })
        });
        completed.unwrap();
        assert_eq!(allocations.attempts, 0);
        assert_eq!(
            observe(&owner).reservations.construction.current,
            before.reservations.construction.current
        );
        assert_eq!(owner.state.as_ref().unwrap().values.as_ptr(), pointer);
        assert_eq!(retained_value, Some(Value::I32(number)));
    }
    let mut slot = Some(owner);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut slot));
    let tail = returned.take().unwrap().unwrap();
    let mut outcome = None;
    let mut usage = None;
    tail.complete((slot, returned, retained_value), &mut outcome, &mut usage);
    assert_eq!(usage.unwrap().reservations.combined.current, 0);
}

#[test]
fn independent_values_excess_live_fault_drops_actual_payload_and_preserves_first_failure() {
    let mut owner = owner(SwiftRunBudget::default());
    let mut prepared = Some(owner.prepare_value_operation(at()));
    let mut phase = prepared.take().unwrap().unwrap();
    phase.push_value(Value::I32(3)).unwrap();
    phase
        .operation
        .control
        .add_live_with_wasi(Live::Values, 1, at(), Some(phase.operation.wasi.usage()))
        .unwrap();
    let failure = phase.numeric_value(0x45, false).unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
    let completed = phase.complete_values(ValueOperationStorage {
        preparation: prepared,
        outcome: Some(Err(failure)),
    });
    assert_eq!(completed.unwrap_err(), failure);
    assert!(owner.state.as_ref().unwrap().values.is_empty());
    // Fault injection deliberately leaves excess accounting. This is an invariant
    // outcome, not ordinary cleanup success; preserve it in the receipt.
    assert_eq!(observe(&owner).live.values.current, 1);
    let mut slot = Some(owner);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut slot));
    let tail = returned.take().unwrap().unwrap();
    let mut outcome = None;
    let mut usage = None;
    tail.complete(
        (slot, returned, failure, completed),
        &mut outcome,
        &mut usage,
    );
    assert_eq!(outcome.unwrap().code, failure.code);
    assert_eq!(usage.unwrap().reservations.combined.current, 0);
}

#[test]
fn independent_values_dropped_uncompleted_phase_retains_charge() {
    let mut owner = owner(SwiftRunBudget::default());
    let previous = observe(&owner).reservations.construction.current;
    let phase = owner.prepare_value_operation(at()).unwrap();
    let scratch = value_operation_bytes().unwrap();
    drop(phase);
    assert_eq!(
        observe(&owner).reservations.construction.current,
        previous + scratch
    );
    finish_owner(owner, None);
}
