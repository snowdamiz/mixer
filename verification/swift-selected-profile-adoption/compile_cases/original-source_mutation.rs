use super::retained_profile_loader_v1::SelectedValidatedProfileV1;
fn forbidden(profile: SelectedValidatedProfileV1) { profile.source()[0] = 1; }

