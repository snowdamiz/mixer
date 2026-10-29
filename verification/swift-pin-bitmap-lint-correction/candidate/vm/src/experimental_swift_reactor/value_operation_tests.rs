//! Tests invoke the real private owner preparation/completion route. The tiny
//! independently authored reactor fixture retains the complete fixed Swift ABI.
use super::*;
use crate::experimental_swift_reactor::allocation_tests::measure_extended;
use crate::experimental_swift_reactor::execution_tests::{
    construct_owned, construction_adopt, construction_finish,
};

fn cursor() -> Cursor {
    Cursor {
        stage: SwiftRunStage::Invocation,
        function: Some(62),
        offset: Some(177),
    }
}
fn owner(budget: SwiftRunBudget) -> SwiftReactorInstance {
    {
        let mut returned = None;
        construct_owned(&mut construction_adopt(budget), &mut returned);
        returned.unwrap()
    }.unwrap()
}
fn finish(
    phase: ExecutionOperationPhase<'_>,
    preparation: Option<Result<ExecutionOperationPhase<'_>, SwiftRunFailure>>,
) {
    phase
        .complete_values(ValueOperationStorage {
            preparation,
            outcome: None,
        })
        .unwrap();
}
fn usage(owner: &SwiftReactorInstance) -> SwiftRunUsage {
    owner
        .control
        .as_ref()
        .unwrap()
        .usage(Some(owner.wasi.as_ref().unwrap().usage()))
}
fn finish_failed_owner(owner: SwiftReactorInstance, retained: SwiftRunFailure) {
    let mut owned = Some(owner);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail = returned.take().unwrap().unwrap();
    let mut failure = None;
    let mut usage = None;
    // Retained operation diagnostics end before the same header is refunded.
    tail.complete((owned, returned, retained), &mut failure, &mut usage);
    let usage = usage.unwrap();
    assert_eq!(usage.reservations.combined.current, 0);
    assert_eq!(usage.reservations.live_tickets, 0);
    assert_eq!(usage.live.values.current, 0);
    assert_eq!(usage.cleanup_invariant, None);
    assert!(failure.is_some());
}

#[test]
fn swift_values_original_owner_prepares_completes_and_restores_exact_bound() {
    let mut owner = owner(SwiftRunBudget::default());
    let before = usage(&owner);
    let original_memory = owner.state.as_ref().unwrap().memory.as_ptr();
    let original_values = owner.state.as_ref().unwrap().values.as_ptr();
    let mut returned = Some(owner.prepare_value_operation(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    assert_eq!(phase.parts.memory.as_ptr(), original_memory);
    assert_eq!(phase.parts.values.as_ptr(), original_values);
    assert_eq!(
        phase.previous_bound,
        before.reservations.construction.current
    );
    assert_eq!(
        phase
            .operation
            .control
            .usage(None)
            .reservations
            .construction
            .current,
        phase.previous_bound + value_operation_bytes().unwrap()
    );
    let ((pushed, popped), allocations) = measure_extended(Some(0), || {
        let pushed = phase.push_value(Value::I32(31));
        let popped = phase.pop_value();
        (pushed, popped)
    });
    pushed.unwrap();
    assert_eq!(popped.unwrap(), Value::I32(31));
    assert_eq!(allocations.attempts, 0);
    finish(phase, returned);
    let after = usage(&owner);
    assert_eq!(
        after.reservations.construction.current,
        before.reservations.construction.current
    );
    assert_eq!(after.execution_work, before.execution_work + 2);
    assert_eq!(after.instruction_fuel, before.instruction_fuel);
    assert_eq!(after.instructions, before.instructions);
    assert_eq!(after.live.values.current, 0);
    assert_eq!(after.live.values.peak, 1);
    assert!(matches!(owner.lifecycle, Lifecycle::Uninitialized));
    construction_finish(owner);
}

#[test]
fn swift_values_known_numeric_semantics_and_float_bits_without_allocations() {
    let mut owner = owner(SwiftRunBudget::default());
    let mut returned = Some(owner.prepare_value_operation(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    // Expected results are independent native arithmetic/bit identities.
    for (a, b, opcode, expected) in [
        (
            Value::I32(i32::MAX),
            Value::I32(1),
            0x6a,
            Value::I32(i32::MIN),
        ),
        (Value::I64(-31), Value::I64(9), 0x7c, Value::I64(-22)),
        (Value::I32(-7), Value::I32(3), 0x6d, Value::I32(-2)),
        (Value::I32(-1), Value::I32(1), 0x76, Value::I32(i32::MAX)),
        (
            Value::F32(1.5f32.to_bits()),
            Value::F32(2.25f32.to_bits()),
            0x92,
            Value::F32(3.75f32.to_bits()),
        ),
        (
            Value::F64((-0.0f64).to_bits()),
            Value::F64(0),
            0xa4,
            Value::F64((-0.0f64).to_bits()),
        ),
    ] {
        let (result, allocations) = measure_extended(Some(0), || {
            phase.push_value(a)?;
            phase.push_value(b)?;
            phase.numeric_value(opcode, false)?;
            phase.pop_value()
        });
        assert_eq!(result.unwrap(), expected);
        assert_eq!(allocations.attempts, 0);
        assert!(phase.parts.values.is_empty());
        assert_eq!(phase.operation.control.usage(None).live.values.current, 0);
    }
    for (input, opcode, expected) in [
        (Value::F32(f32::NAN.to_bits()), 0, Value::I32(0)),
        (Value::F64(f64::INFINITY.to_bits()), 6, Value::I64(i64::MAX)),
        (Value::F64(f64::INFINITY.to_bits()), 7, Value::I64(-1)),
    ] {
        phase.push_value(input).unwrap();
        phase.numeric_value(opcode, true).unwrap();
        assert_eq!(phase.pop_value().unwrap(), expected);
    }
    finish(phase, returned);
    construction_finish(owner);
}

#[test]
fn swift_values_every_numeric_shape_and_saturating_shape_executes() {
    let mut owner = owner(SwiftRunBudget::default());
    let mut returned = Some(owner.prepare_value_operation(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    for opcode in 0x45..=0xc4 {
        let (input, count, output) = crate::validate::numeric_type(opcode);
        let value = match input {
            Type::I32 => Value::I32(1),
            Type::I64 => Value::I64(1),
            Type::F32 => Value::F32(1.0f32.to_bits()),
            Type::F64 => Value::F64(1.0f64.to_bits()),
        };
        for _ in 0..count {
            phase.push_value(value).unwrap();
        }
        phase.numeric_value(opcode, false).unwrap();
        assert_eq!(phase.parts.values.len(), 1, "opcode {opcode}");
        assert_eq!(phase.operation.control.usage(None).live.values.current, 1);
        assert_eq!(phase.pop_value().unwrap().ty(), output);
    }
    for opcode in 0..8 {
        let (input, output) = crate::float::saturating_shape(opcode);
        phase.push_value(Value::zero(input)).unwrap();
        phase.numeric_value(opcode, true).unwrap();
        assert_eq!(phase.pop_value().unwrap().ty(), output);
    }
    finish(phase, returned);
    construction_finish(owner);
}

#[test]
fn swift_values_numeric_traps_reconcile_actual_zero_output_before_latching() {
    for (inputs, opcode, code) in [
        (
            vec![Value::I32(9), Value::I32(0)],
            0x6d,
            "integer_divide_by_zero",
        ),
        (
            vec![Value::I32(i32::MIN), Value::I32(-1)],
            0x6d,
            "integer_overflow",
        ),
        (
            vec![Value::F64(f64::NAN.to_bits())],
            0xaa,
            "invalid_conversion_to_integer",
        ),
    ] {
        let mut owner = owner(SwiftRunBudget::default());
        let before = usage(&owner);
        let mut returned = Some(owner.prepare_value_operation(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        for input in &inputs {
            phase.push_value(*input).unwrap();
        }
        let (result, allocations) =
            measure_extended(Some(0), || phase.numeric_value(opcode, false));
        let failure = result.unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::GuestTrap);
        assert_eq!(failure.code, code);
        assert_eq!(failure.function, Some(62));
        assert_eq!(failure.offset, Some(177));
        assert_eq!(failure.at_failure.live.values.current, 0);
        assert_eq!(failure.at_failure.wasi, Some(phase.operation.wasi.usage()));
        assert_eq!(phase.parts.values.len(), 0);
        assert_eq!(allocations.attempts, 0);
        let repeated = phase.push_value(Value::I32(22)).unwrap_err();
        assert_eq!(repeated, failure);
        finish(phase, returned);
        assert_eq!(
            usage(&owner).reservations.construction.current,
            before.reservations.construction.current
        );
        assert_eq!(
            owner.prepare_value_operation(cursor()).err().unwrap(),
            failure
        );
        finish_failed_owner(owner, failure);
    }
}

#[test]
fn swift_values_bad_opcode_type_and_underflow_fail_before_primitive_effects() {
    for (inputs, opcode, saturating) in [
        (vec![Value::I32(4)], 0x44, false),
        (vec![Value::F32(0)], 8, true),
        (vec![Value::I32(4)], 0x6a, false),
        (vec![Value::I32(4), Value::I64(1)], 0x6a, false),
    ] {
        let mut owner = owner(SwiftRunBudget::default());
        let mut returned = Some(owner.prepare_value_operation(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        for value in &inputs {
            phase.push_value(*value).unwrap();
        }
        let before = phase.operation.control.usage(None).execution_work;
        let failure = phase.numeric_value(opcode, saturating).unwrap_err();
        assert!(matches!(
            failure.kind,
            SwiftRunFailureKind::Invariant | SwiftRunFailureKind::UnsupportedEnvironment
        ));
        assert_eq!(&**phase.parts.values, inputs.as_slice());
        assert_eq!(failure.at_failure.execution_work, before);
        finish(phase, returned);
        assert_eq!(usage(&owner).live.values.current, 0);
        finish_failed_owner(owner, failure);
    }
}

#[test]
fn swift_values_operand_ceiling_and_narrow_value_capacity_reject_publication() {
    for (capacity, expected, code) in [
        (16384, 128, "swift_execution_operand_limit"),
        (2, 2, "swift_execution_value_capacity"),
    ] {
        let mut owner = owner(SwiftRunBudget {
            values: capacity,
            ..SwiftRunBudget::default()
        });
        let mut returned = Some(owner.prepare_value_operation(cursor()));
        let mut phase = returned.take().unwrap().unwrap();
        for _ in 0..expected {
            phase.push_value(Value::I32(7)).unwrap();
        }
        let (result, allocations) = measure_extended(Some(0), || phase.push_value(Value::I32(8)));
        let failure = result.unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::ValueLimit);
        assert_eq!(failure.code, code);
        assert_eq!(phase.parts.values.len(), expected);
        assert_eq!(failure.at_failure.live.values.current, expected);
        assert_eq!(allocations.attempts, 0);
        finish(phase, returned);
        assert_eq!(usage(&owner).live.values.current, 0);
        finish_failed_owner(owner, failure);
    }
}

#[test]
fn swift_values_cancelled_operation_cleanup_ignores_terminal_checkpoint() {
    let mut owner = owner(SwiftRunBudget::default());
    let mut returned = Some(owner.prepare_value_operation(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    phase.push_value(Value::I32(7)).unwrap();
    phase.push_value(Value::I32(3)).unwrap();
    phase.operation.control.cancellation().cancel();
    let failure = phase.numeric_value(0x6a, false).unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
    assert_eq!(phase.parts.values.len(), 2);
    finish(phase, returned);
    assert_eq!(usage(&owner).live.values.current, 0);
    assert_eq!(
        owner
            .control
            .as_mut()
            .unwrap()
            .check_with_wasi(cursor(), None)
            .unwrap_err(),
        failure
    );
    finish_failed_owner(owner, failure);
}

#[test]
fn swift_values_live_corruption_fails_closed_and_cleanup_retains_first_failure() {
    let mut owner = owner(SwiftRunBudget::default());
    let mut returned = Some(owner.prepare_value_operation(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    phase.push_value(Value::I32(4)).unwrap();
    // Unit fault injection removes accounting independently of its real payload.
    phase
        .operation
        .control
        .remove_live_with_wasi(Live::Values, 1, Some(phase.operation.wasi.usage()))
        .unwrap();
    let failure = phase.numeric_value(0x45, false).unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
    assert_eq!(phase.parts.values.len(), 1);
    let completion = phase
        .complete_values(ValueOperationStorage {
            preparation: returned,
            outcome: Some(Err(failure)),
        })
        .unwrap_err();
    assert_eq!(completion, failure);
    assert!(owner.state.as_ref().unwrap().values.is_empty());
    assert_eq!(
        usage(&owner).cleanup_invariant,
        Some(SwiftCleanupInvariant::LiveUnderflow)
    );
    // Intentional accounting corruption is an observed invariant, never a pass
    // for ordinary zero-invariant cleanup; consume the real tail explicitly.
    let mut owned = Some(owner);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail = returned.take().unwrap().unwrap();
    let mut outcome = None;
    let mut final_usage = None;
    let code = failure.code;
    tail.complete(
        (owned, returned, failure, completion),
        &mut outcome,
        &mut final_usage,
    );
    assert_eq!(outcome.unwrap().code, code);
    assert_eq!(final_usage.unwrap().reservations.combined.current, 0);
}

#[test]
fn swift_values_preparation_failure_preserves_real_owner() {
    let mut owner = owner(SwiftRunBudget::default());
    let before = usage(&owner);
    let state_pointer = owner.state.as_ref().unwrap().memory.as_ptr();
    owner.control.as_ref().unwrap().cancellation().cancel();
    let failure = owner.prepare_value_operation(cursor()).err().unwrap();
    assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
    assert_eq!(owner.state.as_ref().unwrap().memory.as_ptr(), state_pointer);
    assert_eq!(
        usage(&owner).reservations.construction.current,
        before.reservations.construction.current
    );
    assert!(owner.cache.is_some() && owner.wasi.is_some() && owner.control.is_some());
    finish_failed_owner(owner, failure);
}

#[test]
fn swift_values_work_exhaustion_preserves_operands_and_cleanup_is_free() {
    let baseline = owner(SwiftRunBudget::default());
    let construction_work = usage(&baseline).execution_work;
    construction_finish(baseline);
    let mut owner = owner(SwiftRunBudget {
        execution_work: construction_work + 2,
        ..SwiftRunBudget::default()
    });
    let mut returned = Some(owner.prepare_value_operation(cursor()));
    let mut phase = returned.take().unwrap().unwrap();
    phase.push_value(Value::I32(9)).unwrap();
    phase.push_value(Value::I32(2)).unwrap();
    let failure = phase.numeric_value(0x6a, false).unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::WorkExhausted);
    assert_eq!(failure.at_failure.execution_work, construction_work + 2);
    assert_eq!(
        phase.parts.values.as_slice(),
        &[Value::I32(9), Value::I32(2)]
    );
    finish(phase, returned);
    assert_eq!(usage(&owner).execution_work, construction_work + 2);
    assert_eq!(usage(&owner).live.values.current, 0);
    finish_failed_owner(owner, failure);
}

#[test]
fn swift_values_operation_admission_failure_preserves_all_owners_and_previous_bound() {
    let mut owner = owner(SwiftRunBudget::default());
    let before = usage(&owner);
    let observation = Some(owner.wasi.as_ref().unwrap().usage());
    let remaining = owner.control.as_ref().unwrap().budget().combined_bytes
        - before.reservations.combined.current;
    // Real control admission fills remaining logical reservation room, without
    // fabricating a ticket or changing the original control/budget authority.
    let ticket = owner
        .control
        .as_mut()
        .unwrap()
        .admit_with_wasi(
            SwiftReservationCategory::Shared,
            remaining,
            cursor(),
            observation,
        )
        .unwrap();
    let pointer = owner.state.as_ref().unwrap().values.as_ptr();
    let failure = owner.prepare_value_operation(cursor()).err().unwrap();
    assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
    assert_eq!(owner.state.as_ref().unwrap().values.as_ptr(), pointer);
    assert_eq!(
        usage(&owner).reservations.construction.current,
        before.reservations.construction.current
    );
    owner
        .control
        .as_mut()
        .unwrap()
        .drop_reserved_with_wasi((), ticket, observation)
        .unwrap();
    assert_eq!(
        usage(&owner).reservations.combined.current,
        before.reservations.combined.current
    );
    finish_failed_owner(owner, failure);
}

#[test]
fn swift_values_positive_operation_layout_inventory() {
    println!(
        "value_operation permanent {} active {} phase {} header {} construction {}",
        PERMANENT_BYTES,
        ACTIVE_BYTES,
        value_operation_bytes().unwrap(),
        execution_header_bytes().unwrap(),
        construction_bytes().unwrap()
    );
    assert_eq!(PERMANENT_BYTES, size_of::<PermanentPositions>());
    assert_eq!(ACTIVE_BYTES, size_of::<ActivePositions>() + size_of::<super::super::frame_operations::DiagnosticValuePositions>());
    assert_eq!(
        value_operation_bytes(),
        named_bytes("operation").unwrap().checked_add(ACTIVE_BYTES)
    );
    assert!(std::hint::black_box(PERMANENT_BYTES) > 0 && std::hint::black_box(ACTIVE_BYTES) > 0);
}
