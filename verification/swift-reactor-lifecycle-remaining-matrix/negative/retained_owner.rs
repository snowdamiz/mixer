fn whole_owner_after_actual_retained_completion(owner: &mut SwiftReactorInstance) {
    match request(owner, Request::Initialize) {
        Completion::Failed {
            cleanup:
                GrowthCompletion::Retained {
                    mut phase,
                    context,
                    growth,
                    storage,
                    preparation,
                },
            ..
        } => {
            owner.lifecycle = Lifecycle::Ready;
            phase.drain();
            drop((phase, context, growth, storage, preparation));
        }
        _ => (),
    }
}
