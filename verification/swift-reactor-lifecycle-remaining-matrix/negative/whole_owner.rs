fn whole_owner_while_actual_phase_is_alive(owner: &mut SwiftReactorInstance) {
    let (phase, context) = owner.prepare_growth(frame_tests::cursor()).unwrap();
    owner.lifecycle = Lifecycle::Ready;
    drop((phase, context));
}
