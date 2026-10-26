//! Producer-authored private guard matrices derived from the accepted Q table.
//! These deliberately seed Q; they are not public-from-empty fixture passes.
use super::*;

fn guard_fixture(slots: u64) -> Fixture {
    Fixture {
        cap: 1,
        mask: 33,
        extent: 1000,
        types: 2,
        slots,
        pins: slots,
        base: 0,
        capacity: 10,
        entry: 10,
    }
}
fn guard_progress(stage: u64) -> Progress {
    let mut q = [1, 10, 1, stage, 1, 1, 1, 3, 0, 2, 1, 0, 0, 0, 0, 1];
    if stage >= 8 {
        q[11] = 1;
    }
    if stage >= 9 {
        q[12] = 1;
    }
    Progress {
        calls: 1,
        latch: 0,
        q,
    }
}
fn guard_framing() -> Framing {
    let mut s = Framing::new(1);
    s.framed = 1;
    s.complete = true;
    s.flags = 1;
    s
}
fn guard_paid() -> Paid {
    Paid {
        setup: 1,
        finish: 1,
        records: 1,
    }
}
fn cap_observation() -> FixtureEnvelopeObservationV1 {
    env_observation(
        FixtureEnvelopeBoundaryV1::CapCutUnknownTail,
        FixtureEnvelopeReasonV1::Observed,
    )
}
fn guard_words(p: &Progress, f: &Fixture) -> [u64; 32] {
    full(&projection(
        p,
        &guard_paid(),
        &guard_framing(),
        &Ok(true),
        &cap_observation(),
        Some(f),
    ))
}
fn visible_guard_words(p: &Progress) -> [u64; 32] {
    let q = &p.q;
    let stage = q[3];
    let mut w = [0; 32];
    w[0] = 2;
    w[2] = 1;
    w[3] = q[0];
    w[5] = q[0];
    w[6] = q[1];
    w[7] = q[2];
    w[8] = if stage != 0 { q[4] } else { 0 };
    w[9] = if stage != 0 { q[5] } else { ABSENT };
    w[10] = q[6];
    w[11] = q[7];
    w[12] = q[8];
    w[13] = q[9];
    w[14] = if (3..=10).contains(&stage) {
        q[5] & 511
    } else {
        ABSENT
    };
    if (6..=10).contains(&stage) {
        w[15] = q[10];
        w[16] = q[11];
        w[17] = q[12];
    }
    w[18] = if stage == 7 || stage == 8 {
        q[13]
    } else {
        ABSENT
    };
    w[19] = if (6..=10).contains(&stage) && q[15] == 1 {
        q[14]
    } else {
        ABSENT
    };
    w[21] = 8448;
    w[22] = 1;
    w[23] = 1;
    w[24] = 1;
    w[25] = 1;
    w
}
fn suppressed_guard_words(boundary: u64, reason: u64) -> [u64; 32] {
    let mut w = [0; 32];
    w[0] = boundary;
    w[1] = reason;
    w[21] = 8448;
    w[22] = 1;
    w[23] = 1;
    w
}
fn assert_guard(p: &Progress, f: &Fixture, visible: bool) {
    assert_eq!(shape_q(&p.q, p.calls, p.terminal(), 1, f), visible);
    assert_eq!(
        guard_words(p, f),
        if visible {
            visible_guard_words(p)
        } else {
            suppressed_guard_words(5, 16)
        }
    );
}

#[test]
fn private_all_eleven_stage_baselines_keep_exact_full32() {
    let mut checks = 0;
    for slots in [1, 3, 64] {
        let f = guard_fixture(slots);
        for stage in 0..=10 {
            assert_guard(&guard_progress(stage), &f, true);
            checks += 1;
        }
    }
    println!("CORRECTION_PRIVATE_STAGE_BASELINES={checks} PUBLIC_REACHABILITY_CREDIT=0");
}
#[test]
fn private_inactive_masks_and_feasibility_are_not_validated() {
    let f = guard_fixture(3);
    let values = [0, 1, 3, 1 << 63, ABSENT];
    let mut checks = 0;
    for stage in 0..=5 {
        for selected in values {
            for taken in values {
                for committed in values {
                    for feasible in [0, 1, 2, ABSENT] {
                        let mut p = guard_progress(stage);
                        p.q[10] = selected;
                        p.q[11] = taken;
                        p.q[12] = committed;
                        p.q[13] = ABSENT;
                        p.q[14] = ABSENT;
                        p.q[15] = feasible;
                        if stage == 0 {
                            p.q[4] = ABSENT;
                            p.q[5] = ABSENT;
                        }
                        assert_guard(&p, &f, true);
                        checks += 1;
                    }
                }
            }
        }
    }
    assert_eq!(checks, 3000);
    println!("CORRECTION_PRIVATE_INACTIVE_FULL32={checks} PUBLIC_REACHABILITY_CREDIT=0");
}
#[test]
fn private_planned_masks_bool_and_destination_boundaries_remain_enforced() {
    let mut checks = 0;
    for slots in [1, 3, 64] {
        let f = guard_fixture(slots);
        for stage in 6..=10 {
            let base = guard_progress(stage);
            if slots < 64 {
                let mut p = guard_progress(stage);
                p.q[10] = 1 << slots;
                assert_guard(&p, &f, false);
                checks += 1;
            }
            let mut p = guard_progress(stage);
            p.q[10] = 1;
            p.q[11] = 2;
            p.q[12] = 0;
            assert_guard(&p, &f, false);
            checks += 1;
            let mut p = guard_progress(stage);
            p.q[11] = 0;
            p.q[12] = 1;
            assert_guard(&p, &f, false);
            checks += 1;
            for feasible in [2, ABSENT] {
                let mut p = guard_progress(stage);
                p.q[15] = feasible;
                assert_guard(&p, &f, false);
                checks += 1;
            }
            for destination in [slots, ABSENT] {
                let mut p = guard_progress(stage);
                p.q[14] = destination;
                assert_guard(&p, &f, false);
                checks += 1;
            }
            let mut p = guard_progress(stage);
            p.q[15] = 0;
            p.q[14] = ABSENT;
            p.q[13] = ABSENT;
            assert_guard(&p, &f, stage != 7 && stage != 8);
            checks += 1;
            assert_guard(&base, &f, true);
            checks += 1;
            if stage != 7 && stage != 8 {
                let mut p = guard_progress(stage);
                p.q[13] = ABSENT;
                assert_guard(&p, &f, true);
                checks += 1;
            }
            if slots == 64 {
                let mut p = guard_progress(stage);
                p.q[10] = ABSENT;
                p.q[11] = ABSENT;
                p.q[12] = ABSENT;
                assert_guard(&p, &f, true);
                checks += 1;
            }
        }
    }
    println!("CORRECTION_PRIVATE_PLANNED_BOUNDARIES={checks} PUBLIC_REACHABILITY_CREDIT=0");
}
#[test]
fn private_pending_requires_true_feasible_selected_slot_and_valid_destination() {
    let mut checks = 0;
    for slots in [1, 3, 64] {
        let f = guard_fixture(slots);
        for stage in [7, 8] {
            for pending in [0, slots - 1, slots, ABSENT] {
                for selected in [0, 1, 1 << (slots - 1)] {
                    for destination in [0, slots - 1, slots, ABSENT] {
                        for feasible in [0, 1, 2, ABSENT] {
                            let mut p = guard_progress(stage);
                            p.q[10] = selected;
                            p.q[11] = 0;
                            p.q[12] = 0;
                            p.q[13] = pending;
                            p.q[14] = destination;
                            p.q[15] = feasible;
                            let visible = feasible == 1
                                && destination < slots
                                && pending < slots
                                && (selected & (1 << pending)) != 0;
                            assert_guard(&p, &f, visible);
                            checks += 1;
                        }
                    }
                }
            }
        }
    }
    assert_eq!(checks, 1152);
    println!("CORRECTION_PRIVATE_PENDING_FULL32={checks} PUBLIC_REACHABILITY_CREDIT=0");
}
#[test]
fn private_initial_snapshot_and_terminal_precedence_keep_the_fixed_read_sets() {
    let f = guard_fixture(3);
    let mut p = guard_progress(0);
    p.q[0] = 0;
    p.q[1] = 0;
    p.q[2] = 0;
    p.q[4] = ABSENT;
    p.q[5] = ABSENT;
    p.q[6] = 0;
    p.q[7] = 0;
    p.q[8] = 0;
    p.q[9] = 1;
    p.q[10..16].fill(ABSENT);
    p.latch_terminal(6);
    assert!(shape_q(&p.q, 1, 6, 1, &f));
    let mut expected = visible_guard_words(&p);
    expected[0] = 3;
    expected[1] = 6;
    expected[4] = 1;
    assert_eq!(guard_words(&p, &f), expected);
    let mut p = guard_progress(7);
    p.q[15] = 0;
    p.q[13] = ABSENT;
    p.q[14] = ABSENT;
    let s = guard_framing();
    let paid = guard_paid();
    for (boundary, reason, want_b, want_r) in [
        (
            FixtureEnvelopeBoundaryV1::Refused,
            FixtureEnvelopeReasonV1::Stage,
            3,
            4,
        ),
        (
            FixtureEnvelopeBoundaryV1::Unavailable,
            FixtureEnvelopeReasonV1::EnvelopeUnavailable,
            0,
            5,
        ),
        (
            FixtureEnvelopeBoundaryV1::InternalPoisoned,
            FixtureEnvelopeReasonV1::InternalPoisoned,
            5,
            16,
        ),
    ] {
        let env = env_observation(boundary, reason);
        assert_eq!(
            full(&projection(&p, &paid, &s, &Ok(true), &env, Some(&f))),
            suppressed_guard_words(want_b, want_r)
        );
    }
    p.latch_terminal(14);
    assert_eq!(guard_words(&p, &f), suppressed_guard_words(5, 16));
    p.latch_terminal(16);
    let env = cap_observation();
    for (code, want_b, want_r) in [(BINDING, 0, 2), (BUDGET, 4, 1), (IO_ERROR, 0, 3)] {
        assert_eq!(
            full(&projection(
                &p,
                &paid,
                &s,
                &Err(error(code, 2, 0, 0)),
                &env,
                Some(&f)
            )),
            suppressed_guard_words(want_b, want_r)
        );
    }
    println!("CORRECTION_PRIVATE_INITIAL_AND_PRECEDENCE=8 PUBLIC_REACHABILITY_CREDIT=0");
}
