// Compile this SAME file at both placements; the internal signature clause
// uses the explicitly recorded cfg only for the internal placement.
fn independent_positive_context() {
 let _=std::mem::size_of::<crate::experimental_swift_reactor::cache::SwiftFunctionCache>();
 let _=std::mem::size_of::<crate::experimental_swift_reactor::control::RuntimeControl>();
}
#[cfg(mixer_initial_profile_contract_internal)]
const _: fn(
 &mut Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
 &mut crate::experimental_swift_reactor::control::RuntimeControl,
 Option<&crate::experimental_wasi::accounted::AccountedWasi>,
 crate::experimental_swift_reactor::control::AdoptedProof,
 &super::SelectedInitialProfileV1, &super::UnverifiedProfileDigestBytesV1,
 &mut std::fs::File,
) -> super::InitialProfileConstructionOutcomeV1 = super::construct_with_initial_profile_v1;
