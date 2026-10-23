// Independently authored control-boundary probes; appended only to the frozen
// review build. No target module is instantiated or executed.
fn review_normalize(mut usage: SwiftRunUsage) -> SwiftRunUsage {
    usage.elapsed_micros = 0;
    usage.deadline_overshoot_micros = 0;
    usage.validation.elapsed_micros = 0;
    usage
}

fn review_apply(control: &mut RuntimeControl, instruction: bool, observed: bool) -> Result<(), SwiftRunFailure> {
    let at = cursor(SwiftRunStage::Invocation);
    match (instruction, observed) {
        (true, true) => control.instruction_with_wasi(at, None),
        (true, false) => control.instruction(at),
        (false, true) => control.charge_fuel_with_wasi(7, at, None),
        (false, false) => control.charge_fuel(7, at),
    }
}

#[test]
fn review_none_wrapper_parity_and_layout() {
    println!("review layouts control={} failure={} usage={}", size_of::<RuntimeControl>(), size_of::<SwiftRunFailure>(), size_of::<SwiftRunUsage>());
    for instruction in [false, true] {
        for case in 0..6 {
            if !instruction && case == 5 { continue; }
            let mut runs = Vec::new();
            for observed in [false, true] {
                let (mut control, adopted) = adopt(SwiftRunBudget::default());
                match case {
                    0 => (),
                    1 => control.cancellation.cancel(),
                    2 => control.deadline = Instant::now(),
                    3 => control.instruction_fuel = control.budget.instruction_fuel,
                    4 => control.instruction_fuel = u64::MAX,
                    5 => control.instructions = u64::MAX,
                    _ => unreachable!(),
                }
                let result = review_apply(&mut control, instruction, observed).map_err(|mut failure| {
                    failure.at_failure = review_normalize(failure.at_failure);
                    failure
                });
                let usage = review_normalize(control.usage(None));
                runs.push((result, usage));
                assert_empty(clean(control, adopted));
            }
            assert_eq!(runs[0], runs[1]);
        }
    }
}

#[test]
fn review_actual_wasi_precedence_and_sticky_failure() {
    use crate::experimental_wasi::accounted::AccountedWasi;
    use crate::experimental_wasi::{WasiBudget, WasiGrants};
    for instruction in [false, true] {
        for case in 0..3 {
            let (mut control, adopted) = adopt(SwiftRunBudget::default());
            let at = cursor(SwiftRunStage::Invocation);
            let mut phase = AccountedWasi::prepare(&mut control, at).unwrap();
            let mut owner = phase.construct(WasiGrants::default(), WasiBudget::default(), Instant::now(), at).unwrap();
            phase.complete().unwrap();
            owner.dispatch(&mut control, WasiFunction::ArgsSizesGet, &[crate::Value::I32(0), crate::Value::I32(4)], &mut [0u8; 8], at).unwrap();
            let actual = owner.checked_usage(&mut control, at).unwrap();
            assert_eq!(actual.calls, 1);
            assert_eq!(actual.transfer_bytes, 8);
            let existing = if case == 2 {
                Some(control.fail(at, Fault::new(SwiftRunFailureKind::GuestTrap, "review_existing_fault"), Some(actual)))
            } else { None };
            control.instruction_fuel = u64::MAX;
            control.instructions = u64::MAX;
            control.deadline = Instant::now();
            if case != 1 { control.cancellation.cancel(); }
            let before = review_normalize(control.usage(Some(actual)));
            let (failure, stats) = super::super::allocation_tests::measure(|| {
                if instruction { control.instruction_with_wasi(at, Some(actual)).unwrap_err() }
                else { control.charge_fuel_with_wasi(7, at, Some(actual)).unwrap_err() }
            });
            no_allocations(stats);
            assert_eq!(stats.deallocations, 0);
            assert_eq!(failure.kind, match case { 0 => SwiftRunFailureKind::Cancelled, 1 => SwiftRunFailureKind::Deadline, _ => SwiftRunFailureKind::GuestTrap });
            if let Some(first) = existing { assert_eq!(failure, first); }
            assert_eq!(failure.at_failure.wasi, Some(actual));
            assert_eq!(control.instruction_with_wasi(at, None).unwrap_err(), failure);
            assert_eq!(control.charge_fuel_with_wasi(0, at, None).unwrap_err(), failure);
            assert_eq!(review_normalize(control.usage(Some(actual))), before);
            assert_eq!(owner.usage(), actual);
            owner.cleanup(&mut control).unwrap();
            control.drop_proof_with_wasi(adopted, Some(actual)).unwrap();
            assert_empty(control.finish_owned_cleanup(Some(actual)));
        }
    }
}

#[test]
fn review_zero_bulk_and_max_arithmetic_boundaries() {
    let at = cursor(SwiftRunStage::Invocation);
    for case in 0..5 {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        control.budget.instruction_fuel = 0;
        match case {
            0 => (),
            1 => control.cancellation.cancel(),
            2 => control.deadline = Instant::now(),
            3 => control.instruction_fuel = 1,
            4 => { control.budget.instruction_fuel = u64::MAX; control.instruction_fuel = u64::MAX; },
            _ => unreachable!(),
        }
        let result = control.charge_fuel_with_wasi(0, at, None);
        match case {
            0 | 4 => result.unwrap(),
            1 => assert_eq!(result.unwrap_err().kind, SwiftRunFailureKind::Cancelled),
            2 => assert_eq!(result.unwrap_err().kind, SwiftRunFailureKind::Deadline),
            3 => assert_eq!(result.unwrap_err().kind, SwiftRunFailureKind::FuelExhausted),
            _ => unreachable!(),
        }
        assert_eq!(control.instructions, 0);
        assert_empty(clean(control, adopted));
    }
    for instruction in [false, true] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        control.budget.instruction_fuel = u64::MAX;
        if instruction {
            control.instruction_fuel = u64::MAX - 1;
            control.instruction_with_wasi(at, None).unwrap();
            assert_eq!(control.instructions, 1);
        } else {
            control.charge_fuel_with_wasi(u64::MAX, at, None).unwrap();
        }
        assert_eq!(control.instruction_fuel, u64::MAX);
        control.charge_fuel_with_wasi(0, at, None).unwrap();
        let failure = if instruction { control.instruction_with_wasi(at, None).unwrap_err() }
            else { control.charge_fuel_with_wasi(1, at, None).unwrap_err() };
        assert_eq!(failure.kind, SwiftRunFailureKind::FuelExhausted);
        assert_eq!(failure.attempted, u64::MAX);
        assert_eq!(failure.limit, u64::MAX);
        assert_eq!(control.instruction_fuel, u64::MAX);
        assert_eq!(control.instructions, u64::from(instruction));
        assert_empty(clean(control, adopted));
    }
}
