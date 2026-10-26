use super::*;

#[test]
fn retained_poison_marker_is_terminal_for_scheduling_and_every_finish_branch() {
    let mut arena = Arena { bytes: vec![0; ARENA_BYTES] };
    let mut p = FixtureEnvelopeProgressV1 {
        reply_valid: 1, debit: 1006,
        reply: FixtureEnvelopeReplyV1 { words: [1, 15, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 425, 0, 0] },
    };
    let mut candidate = [0u8; 2048];
    let before = candidate; let mut leaf_calls = 0;
    let w = [1, 1, 0, 1, 0, 0, 7, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, 0, 0, 0, 0];
    for _ in 0..3 {
        // Main record subdivisions remain prepaid even when poison skips leaf.
        p.debit += RECORD_ENVELOPE;
        if leaf_pending(&p) {
            let mut steps = StepBudget { remaining: 425, spent: 0 };
            p.reply = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &w }, &mut steps);
            leaf_calls += 1;
        }
    }
    assert_eq!(leaf_calls, 0); assert_eq!(candidate, before); assert_eq!(p.debit, 2281);
    assert!(arena.bytes.iter().all(|b| *b == 0));
    for limited in [false, true] { for cap in [0, 1] {
        let mut s = Framing::new(3); s.complete = !limited; s.limited = limited; s.flags = cap;
        let output = finalize(&p, &s, &Ok(!limited), &arena);
        assert_eq!(output.reason(), &FixtureEnvelopeReasonV1::InternalPoisoned);
        assert_eq!(output.boundary(), if limited { &FixtureEnvelopeBoundaryV1::AnalysisLimited } else { &FixtureEnvelopeBoundaryV1::InternalPoisoned });
        assert_eq!([output.observed_records(), output.state(), output.phase(), output.mask(), output.last_operation(), output.active_operation(), output.requested_function(), output.pin_failure(), output.terminal_failure(), output.last_work(), output.last_instructions()], [0; 11]);
        assert_eq!(output.envelope_debit(), 2281); assert!(!output.full_replay_accepted()); assert!(!output.stored_prefix_validated());
    }}
    p.reply.words[0] = 3; p.reply.words[1] = 0; assert!(!leaf_pending(&p));
}

#[test]
fn scalar_overflow_rewrite_matches_closed_unsigned_shape_and_sequence_guards() {
    let mut w = [1, 2, 0, 1, 0, 0, 7, 100, 8, 1, ABSENT, ABSENT, 0, 0, 0, 0];
    for (offset, len, accepted) in [(ABSENT - 1, 1, true), (ABSENT - 1, 2, false), (0, ABSENT - 1, true), (ABSENT, 0, false)] {
        w[7] = offset; w[8] = len; assert_eq!(shape(&w), accepted);
    }
    w[1] = 5; w[7] = 100; w[8] = 8;
    for (a, b, c, accepted) in [(1, 5, 4, false), (1, 4, 4, false), (1, 3, 4, true), (ABSENT, 0, ABSENT, true)] {
        w[13] = a; w[14] = b; w[15] = c; assert_eq!(shape(&w), accepted);
    }
    let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; let mut candidate = [0u8; 2048];
    arena.put64(SCALAR, 7, 0, ABSENT).unwrap(); arena.put64(SCALAR, 13, 0, 1).unwrap(); arena.put64(SCALAR, 14, 0, 33).unwrap();
    let w = [1, 1, 0, 1, 0, 0, 7, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, 0, 0, 0, 0];
    let mut steps = StepBudget { remaining: 425, spent: 0 };
    let r = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &w }, &mut steps);
    assert_eq!(&r.words[..2], &[2, 3]); assert_eq!(r.words[2], ABSENT);
}
