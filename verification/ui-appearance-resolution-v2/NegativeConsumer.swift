import MixerUI
func cannotMutatePlan(_ plan: inout UIResolvedAppearancePlanV2) {
    plan.nodes = []
    plan.environment.generation = 99
}
