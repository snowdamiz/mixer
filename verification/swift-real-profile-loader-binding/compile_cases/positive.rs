use super::retained_profile_loader_v1::SelectedValidatedProfileV1;
fn borrow(profile: &SelectedValidatedProfileV1) -> &[u8] { profile.source() }
