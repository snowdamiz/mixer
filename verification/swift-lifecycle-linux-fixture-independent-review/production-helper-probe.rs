// Independent negative compiler control, appended only to an owned source copy.
// A same-module caller must still be unable to reach a cfg(test)-only method.
#[allow(dead_code)]
fn review_ordinary_build_must_not_have_expiry_helper(control: &mut RuntimeControl) {
    control.test_expire_deadline();
}
