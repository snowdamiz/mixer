// Actual owner controls. Charges are O(1), not synthetic guest completion.
#[test]
fn framepin_campaign_observation_window_guards_remain_finite_and_cumulative() {
    let budget = SwiftRunBudget::default();
    assert_eq!(budget.deadline_ms, 1_200_000);
    assert_eq!(WasiBudget::default().deadline_ms, 1_200_000);
    // Existing executable control proves earliest absolute deadline, sticky
    // expiry and zero-WASI denial; phases cannot obtain a fresh window.
    deadlines_are_carried_as_earliest_absolute_time_and_real_expiry_is_sticky();
    all_seventeen_dimensions_reject_widening_without_allocation_and_drop_real_proof();
    zero_is_real_in_every_budget_dimension();
    init_and_repeated_call_counters_accumulate_and_cannot_refill();
    work_fuel_host_and_live_overflow_fail_closed_without_counter_commit();
    for (component, limit, resource) in [
        (Work::Cache, 4_000_000_000, SwiftRunResource::CacheWork),
        (Work::Execution, 16_000_000_000, SwiftRunResource::ExecutionWork),
    ] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        control.work(component, limit - 1, cursor(SwiftRunStage::Initialization)).unwrap();
        control.work(component, 1, cursor(SwiftRunStage::Invocation)).unwrap();
        let before = control.usage(None);
        let failure = control.work(component, 1, cursor(SwiftRunStage::Invocation)).unwrap_err();
        assert_eq!(failure.resource, Some(resource));
        assert_eq!((failure.attempted, failure.limit), (limit + 1, limit));
        assert_eq!(control.usage(None).cache_work, before.cache_work);
        assert_eq!(control.usage(None).execution_work, before.execution_work);
        assert_eq!(control.work(component, 0, cursor(SwiftRunStage::Invocation)).unwrap_err(), failure);
        assert_empty(clean(control, adopted));
    }
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    control.charge_fuel(3_999_999_999, cursor(SwiftRunStage::Initialization)).unwrap();
    control.charge_fuel(1, cursor(SwiftRunStage::Invocation)).unwrap();
    let failure = control.charge_fuel(1, cursor(SwiftRunStage::Invocation)).unwrap_err();
    assert_eq!(failure.resource, Some(SwiftRunResource::InstructionFuel));
    assert_eq!((failure.attempted, failure.limit), (4_000_000_001, 4_000_000_000));
    assert_eq!(control.usage(None).instruction_fuel, 4_000_000_000);
    assert_empty(clean(control, adopted));
    println!("COMPLETION deadline_ms=1200000 wasi_deadline_ms=1200000 earliest_absolute=true sticky_expiry=true cleanup_zero=true");
    println!("CACHEWINDOW scalar_limits=4000000000,4000000000,16000000000 cumulative=true above_max_rejected=true overflow_rejected=true cleanup_zero=true");
}
