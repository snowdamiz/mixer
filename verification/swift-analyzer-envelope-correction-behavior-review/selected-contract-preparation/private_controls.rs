//! Prepared independent append-only controls; not compiled or run.
//! Private names derive solely from the admitted original immutable review.
//! Exact corrected-source admission and mechanical name mapping remain pending.
use super::*;

const REVIEW_LEAF: u64 = 425;

fn selected_put(bytes: &mut [u8], word: usize, value: u64) {
    bytes[word * 8..word * 8 + 8].copy_from_slice(&value.to_le_bytes());
}

fn selected_initial_state() -> [u64; 12] {
    [0, 0, 0, 0, 0, 1, 33, 0, 0, 0, 0, 0]
}

fn selected_arena() -> Arena {
    let mut result = Arena { bytes: vec![0; ARENA_BYTES] };
    for (index, value) in selected_initial_state().iter().enumerate() {
        selected_put(&mut result.bytes, SCALAR.base / 8 + CELLS[index], *value);
    }
    result
}

fn selected_frame(limited: bool, cap: bool) -> Framing {
    let mut result = Framing::new(5);
    result.complete = !limited;
    result.limited = limited;
    result.flags = u64::from(cap);
    result
}

fn selected_progress(status: u64, reason: u64) -> FixtureEnvelopeProgressV1 {
    let mut result = FixtureEnvelopeProgressV1 {
        reply_valid: 1,
        // Synthetic retained paid counter; this fault seam does not claim actual calls.
        debit: 1006,
        reply: reply(status, reason, &selected_initial_state(), REVIEW_LEAF),
    };
    result.reply.words[2] = 4;
    result.reply.words[3] = 1;
    result.reply.words[6] = 1;
    result.reply.words[7] = 1;
    result.reply.words[8] = 17;
    result.reply.words[11] = 122;
    result.reply.words[12] = 250;
    result
}

fn selected_zero(value: &FixtureEnvelopeObservationV1) {
    assert_eq!([
        value.observed_records(), value.state(), value.phase(), value.mask(),
        value.last_operation(), value.active_operation(), value.requested_function(),
        value.pin_failure(), value.terminal_failure(), value.last_work(),
        value.last_instructions(),
    ], [0; 11]);
    assert!(!value.stored_prefix_validated());
    assert!(!value.full_replay_accepted());
    assert!(!value.semantic_metrics_valid());
}

fn selected_acquire() -> [u64; 16] {
    [1, 1, 0, 1, 101, 211, 17, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, 0, 0, 0, 0]
}

#[test]
fn selected_review_exact_r1_poison_stops_scheduling_before_stale_state() {
    let a = selected_arena();
    let mut p = selected_progress(1, 15);
    p.reply.words[3] = 999;
    assert!(!leaf_pending(&p), "R1: status1/reason15 cannot schedule a later leaf");
    let output = finalize(&p, &selected_frame(false, true), &Ok(true), &a);
    assert_eq!(output.boundary(), &FixtureEnvelopeBoundaryV1::InternalPoisoned);
    assert_eq!(output.reason(), &FixtureEnvelopeReasonV1::InternalPoisoned);
    assert_eq!(output.envelope_debit(), 1006);
    selected_zero(&output);
    // Actual orchestration call-count instrumentation is a separate pending control.
}

#[test]
fn selected_review_poison_cross_product_keeps_zero_extent_and_paid_debit() {
    let a = selected_arena();
    for status in [1, 3] {
        for state in [0, 10, 999] {
            for cap in [false, true] {
                for limited in [false, true] {
                    let mut p = selected_progress(status, 15);
                    p.reply.words[3] = state;
                    assert!(!leaf_pending(&p));
                    let output = finalize(&p, &selected_frame(limited, cap), &Ok(!limited), &a);
                    assert_eq!(output.boundary(), if limited {
                        &FixtureEnvelopeBoundaryV1::AnalysisLimited
                    } else { &FixtureEnvelopeBoundaryV1::InternalPoisoned });
                    assert_eq!(output.reason(), &FixtureEnvelopeReasonV1::InternalPoisoned);
                    assert_eq!(output.envelope_debit(), 1006);
                    selected_zero(&output);
                }
            }
        }
    }
}

#[test]
fn selected_review_absent_backing_never_projects_candidate_initialization() {
    let a = selected_arena();
    for (status, reason) in [(1, 0), (1, 15), (3, 15)] {
        for cap in [false, true] {
            for limited in [false, true] {
                let mut p = selected_progress(status, reason);
                p.reply_valid = 0;
                p.debit = 581;
                p.reply.words[3] = 999;
                let output = finalize(&p, &selected_frame(limited, cap), &Ok(!limited), &a);
                assert_eq!(output.boundary(), &FixtureEnvelopeBoundaryV1::Unavailable);
                assert_eq!(output.reason(), &FixtureEnvelopeReasonV1::EnvelopeUnavailable);
                assert_eq!(output.envelope_debit(), 581);
                selected_zero(&output);
            }
        }
    }
}

#[test]
fn selected_review_all_underfunded_values_preserve_first_and_later_state() {
    for advanced in [false, true] {
        let mut a = selected_arena();
        let mut candidate = [0u8; 2048];
        if advanced {
            let mut budget = StepBudget { remaining: REVIEW_LEAF, spent: 0 };
            let words = selected_acquire();
            let returned = observe_fixture_envelope_v1(
                &mut a.bytes, &mut candidate,
                &FixtureDecodedRecordV1 { words: &words }, &mut budget,
            );
            assert_eq!(&returned.words[..2], &[1, 0]);
            assert_eq!(returned.words[13], REVIEW_LEAF);
        }
        let before = a.bytes.clone();
        let candidate_before = candidate;
        for remaining in 0..REVIEW_LEAF {
            for malformed in [false, true] {
                let mut words = selected_acquire();
                if malformed { words[1] = u64::MAX; }
                let mut budget = StepBudget { remaining, spent: 0 };
                let returned = observe_fixture_envelope_v1(
                    &mut a.bytes, &mut candidate,
                    &FixtureDecodedRecordV1 { words: &words }, &mut budget,
                );
                assert_eq!(&returned.words[..2], &[2, 1]);
                assert_eq!(returned.words[13], 0);
                assert_eq!(returned.words[2], u64::from(advanced));
                assert_eq!((budget.remaining, budget.spent), (remaining, 0));
                assert_eq!(a.bytes, before);
                assert_eq!(candidate, candidate_before);
                let p = FixtureEnvelopeProgressV1 {
                    reply_valid: 1,
                    debit: if advanced { 1431 } else { 1006 },
                    reply: returned,
                };
                assert!(!leaf_pending(&p));
                let output = finalize(&p, &selected_frame(false, true), &Ok(true), &a);
                assert_eq!(output.boundary(), &FixtureEnvelopeBoundaryV1::Refused);
                assert_eq!(output.reason(), &FixtureEnvelopeReasonV1::Steps);
                assert_eq!(output.envelope_debit(), if advanced { 1431 } else { 1006 });
            }
        }
    }
}

#[test]
fn selected_review_exact_and_one_above_private_funding() {
    for remaining in [425, 426] {
        let mut a = selected_arena();
        let mut candidate = [0u8; 2048];
        let words = selected_acquire();
        let mut budget = StepBudget { remaining, spent: 0 };
        let returned = observe_fixture_envelope_v1(
            &mut a.bytes, &mut candidate,
            &FixtureDecodedRecordV1 { words: &words }, &mut budget,
        );
        assert_eq!(&returned.words[..2], &[1, 0]);
        assert_eq!(returned.words[2], 1);
        assert_eq!(returned.words[13], REVIEW_LEAF);
        assert_eq!((budget.remaining, budget.spent), (remaining - REVIEW_LEAF, REVIEW_LEAF));
    }
}

#[test]
fn selected_review_final_checked_cell_precedes_all_writes() {
    let mut a = selected_arena();
    let before = a.bytes.clone();
    let mut candidate = [0u8; 2048];
    let candidate_before = candidate;
    let truncated = SCALAR.base + 8 * 161 + 7;
    let words = selected_acquire();
    let mut budget = StepBudget { remaining: REVIEW_LEAF, spent: 0 };
    let returned = observe_fixture_envelope_v1(
        &mut a.bytes[..truncated], &mut candidate,
        &FixtureDecodedRecordV1 { words: &words }, &mut budget,
    );
    assert_eq!(&returned.words[..2], &[3, 15]);
    assert_eq!(returned.words[13], REVIEW_LEAF);
    assert_eq!(a.bytes, before);
    assert_eq!(candidate, candidate_before);
}
