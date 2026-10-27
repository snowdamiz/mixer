use super::retained_profile_loader_v1::LoaderProvenanceV1;use super::control::AdoptedProof;fn f(p:&mut AdoptedProof){let _:&mut LoaderProvenanceV1=p.selected_provenance().unwrap();}
