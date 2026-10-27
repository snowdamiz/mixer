use super::retained_profile_loader_v1::LoaderProvenanceV1;use super::control::AdoptedProof;fn f(p:AdoptedProof)->Option<&'static LoaderProvenanceV1>{p.selected_provenance()}
