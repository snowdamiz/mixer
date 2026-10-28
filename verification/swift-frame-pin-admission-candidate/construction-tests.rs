#[test]
fn framepin_campaign_integrated_constructor_failures() {
    assert_eq!((SwiftRunBudget::default().frames, SwiftRunBudget::default().active_pins), (128, 128));
    swift_construction_every_integrated_allocation_ordinal();
    swift_construction_each_state_capacity_rejects_without_growth();
    construction_hooks(ConstructionHooks::default());
    println!("FRAMEPIN integrated_constructor_allocation_failures=15 state_capacity_failures=6 cleanup_zero=true");
}
