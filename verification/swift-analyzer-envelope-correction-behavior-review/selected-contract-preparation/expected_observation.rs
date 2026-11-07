//! Prepared assertions only. No candidate import, compile or execution yet.
//! A future adapter must populate Snapshot from the actual borrowed getters.

pub const SETUP: u64 = 534;
pub const FINISH: u64 = 47;
pub const LEAF: u64 = 425;
pub const COMBINED_RECORD: u64 = 471;
pub const GUARD: u64 = 112;
pub const SETUP_WRAPPER: u64 = 42;
pub const FINISH_WRAPPER: u64 = 42;
pub const EARLY_ERROR_F05: u64 = 13;

pub struct Snapshot {
    pub boundary: u64,
    pub reason: u64,
    pub extent: [u64; 11],
    pub debit: u64,
    pub stored_prefix_validated: bool,
    pub full_replay_accepted: bool,
    pub semantic_metrics_valid: bool,
}

pub fn reserved_debit(setup_paid: bool, finish_paid: bool, b_paid: u64) -> u64 {
    SETUP * u64::from(setup_paid) + FINISH * u64::from(finish_paid) + LEAF * b_paid
}

pub fn assert_no_authority(value: &Snapshot) {
    assert!(!value.stored_prefix_validated);
    assert!(!value.full_replay_accepted);
    assert!(!value.semantic_metrics_valid);
}

pub fn assert_suppressed(value: &Snapshot, reason: u64, debit: u64) {
    assert_eq!(value.boundary, 0); // Unavailable; separate from leaf/report IDs.
    assert_eq!(value.reason, reason);
    assert_eq!(value.extent, [0; 11]);
    assert_eq!(value.debit, debit);
    assert_no_authority(value);
}

pub fn assert_zero_calls(value: &Snapshot, setup_paid: bool, finish_paid: bool, b_paid: u64) {
    // Use only after successful complete/limited framing was independently checked.
    // Input errors, including paid decode failure, must use assert_input_error.
    // Never infer b_paid from the number of leaf calls.
    assert_suppressed(value, 19, reserved_debit(setup_paid, finish_paid, b_paid));
}

pub fn assert_early_budget_error(value: &Snapshot, admission: &str) {
    let debit = match admission {
        "setup-failed" => 0,
        "finish-failed-after-setup" => 534,
        "guard-failed-after-setup-and-finish" => 581,
        _ => panic!("unknown independent admission expectation"),
    };
    assert_suppressed(value, 18, debit); // FramingLimited, not a partial envelope.
}

pub fn assert_input_error(value: &Snapshot, actual_error: &str, setup_paid: bool, finish_paid: bool, b_paid: u64) {
    let reason = match actual_error {
        "BINDING" => 16,
        "BUDGET" => 18,
        _ => 17,
    };
    assert_suppressed(value, reason, reserved_debit(setup_paid, finish_paid, b_paid));
}

pub fn assert_poison(value: &Snapshot, limited: bool, debit: u64) {
    assert_eq!(value.boundary, if limited { 4 } else { 5 });
    assert_eq!(value.reason, 15);
    assert_eq!(value.extent, [0; 11]);
    assert_eq!(value.debit, debit);
    assert_no_authority(value);
}
