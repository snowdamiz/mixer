use super::retained_profile_loader_v1::SelectedValidatedProfileV1;
fn forbidden(bytes: &[u8]) { let _ = SelectedValidatedProfileV1::from_bytes(bytes); }

