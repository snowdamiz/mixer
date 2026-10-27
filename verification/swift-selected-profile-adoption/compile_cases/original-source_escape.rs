use super::retained_profile_loader_v1::SelectedValidatedProfileV1;
fn forbidden(profile: SelectedValidatedProfileV1) -> &'static [u8] { profile.source() }

