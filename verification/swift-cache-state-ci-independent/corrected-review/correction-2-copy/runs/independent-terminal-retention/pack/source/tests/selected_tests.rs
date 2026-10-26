use super::*;

#[test]
fn selected_contract_and_all_thirty_two_complete_declarations_are_actual() {
    assert_eq!((RECORD_ENVELOPE, WRAPPER_STEPS, COMBINED_RECORD, UNDERFUNDED_GUARD, SETUP_WRAPPER, FINISH_ENVELOPE, FINAL_WRAPPER), (425, 24, 471, 112, 42, 47, 42));
    assert_eq!(SETUP_ENVELOPE, 534); assert_eq!(RECORD_PREFLIGHT, 8192);
    let actual = [
        size_of::<Result<(), AnalyzerError>>(), size_of::<Result<bool, AnalyzerError>>(), size_of::<Result<u64, AnalyzerError>>(), size_of::<Result<Arena, AnalyzerError>>(),
        size_of::<Result<Budget, AnalyzerError>>(), size_of::<Result<Stamp, AnalyzerError>>(), size_of::<Result<Fixture, AnalyzerError>>(),
        size_of::<FixtureEnvelopeOutcomeV1>(), size_of::<Result<FixtureEnvelopeOutcomeV1, AnalyzerError>>(), size_of::<FixtureEnvelopeObservationV1>(), size_of::<FixtureEnvelopeProgressV1>(), size_of::<FixtureEnvelopeReplyV1>(),
        size_of::<StepBudget>(), size_of::<CheckedPair>(), size_of::<Candidate2048>(), size_of::<&mut Candidate2048>(), size_of::<&[u8]>(), size_of::<&mut [u8]>(), size_of::<Option<&[u8]>>(), size_of::<Option<&mut [u8]>>(),
        size_of::<Option<&[u8; 8]>>(), size_of::<Option<u64>>(), size_of::<std::ops::Range<usize>>(), size_of::<std::ops::RangeFrom<usize>>(), size_of::<std::ops::RangeInclusive<u64>>(),
        size_of::<Framing>(), size_of::<Reader>(), size_of::<Stamp>(), size_of::<AnalyzerError>(), size_of::<ReplayOutcome>(), size_of::<std::fs::Metadata>(), size_of::<io::Result<std::fs::Metadata>>(),
    ];
    assert_eq!(actual, [40,40,40,40,64,80,80,232,232,128,144,128,16,16,2048,8,16,16,16,16,8,16,16,8,24,80,48,72,32,104,144,152]);
    println!("CORRECTED_ACTUAL_COMPLETE_LAYOUTS={actual:?}");
}

#[test]
fn every_early_input_error_precharges_outer_projection_without_inventing_finish() {
    for mode in 0..2 {
        let mut x = inputs(&hit(), false);
        if mode == 0 { x[0].fail_stamp_at = 2; } else { put(&mut x[2].bytes, 0, 0); }
        let out = invoke(&mut x, STEP_LIMIT).unwrap();
        assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::Unavailable);
        assert_eq!(out.envelope().reason(), if mode == 0 { &FixtureEnvelopeReasonV1::FramingInvalid } else { &FixtureEnvelopeReasonV1::FramingUnavailable });
        zero_extent(out.envelope()); assert_eq!(out.envelope().envelope_debit(), 0);
        // Independently enumerate inherited setup/report charges for these two
        // known early paths; finish47 and guard112 have not been reserved.
        let inherited_setup = 15 + 12 + 64 + 512 + 128 + 32 + if mode == 0 { 2 } else { 6 + 1024 + 16 };
        let io_attempts = if mode == 0 { 0 } else { 2 };
        let expected = 42 + 42 + ARENA_BYTES as u64 / 8 + inherited_setup + io_attempts + 6245;
        assert_eq!(out.framing().steps_used, expected);
        assert_unaccepted(&out, &x[3]);
        println!("CORRECTED_EARLY_ERROR mode={mode} steps={expected} envelope_debit=0 outer_final=42 early_projection=13");
    }
}

#[test]
fn private_underfunding_preserves_entire_arena_and_candidate_before_any_reply() {
    for state in [initial_state(), [4,10,20,1,0,1,33,3,1,7,0,0]] { for credits in [0,424] {
        let mut arena = Arena { bytes: vec![0xA5; ARENA_BYTES] }; arena_state(&mut arena, &state);
        let arena_before = arena.bytes.clone(); let mut candidate = [0x5A;2048]; let before = candidate;
        let mut p = blank_progress(); p.reply_valid = 0; p.debit += 425;
        assert_eq!(p.reply_valid, 0); assert!(leaf_pending(&p));
        let w = event(2); let mut steps = StepBudget { remaining: credits, spent: 0 };
        let actual = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &w }, &mut steps);
        assert_eq!(&actual.words[..2], &[2,1]); assert_eq!(actual.words[13], 0);
        assert_eq!((steps.remaining,steps.spent), (credits,0)); assert_eq!(arena.bytes,arena_before); assert_eq!(candidate,before);
        p.reply = actual; p.reply_valid = 1;
        assert!(!leaf_pending(&p)); assert_eq!(p.debit,1006); assert_eq!(p.reply.words[2],state[0]);
    }}
}

#[test]
fn fresh_selected_finite_budget_matrix_matches_all_reply_values_and_debits() {
    let raw = include_bytes!("../inputs/oracle-budget-425.bin"); assert_eq!(raw.len(),5544*45*8);
    let mut arena = Arena { bytes: vec![0;ARENA_BYTES] }; let mut candidate = [0xA5;2048];
    for (index,case) in raw.chunks_exact(45*8).enumerate() {
        let mut s=[0;12]; let mut w=[0;16]; let mut expected=[0;16];
        for i in 0..12 {s[i]=word(case,i);} for i in 0..16 {w[i]=word(case,12+i);expected[i]=word(case,29+i);}
        let credits=word(case,28);arena_state(&mut arena,&s);let before=candidate;
        let mut steps=StepBudget{remaining:credits,spent:0};
        let actual=observe_fixture_envelope_v1(&mut arena.bytes,&mut candidate,&FixtureDecodedRecordV1{words:&w},&mut steps);
        assert_eq!(actual.words,expected,"selected budget oracle case{index}");
        let debit=if credits<425{0}else{425};assert_eq!((steps.remaining,steps.spent),(credits-debit,debit));
        if credits<425 || actual.words[0]==2 {assert_eq!(candidate,before);for i in 0..12{assert_eq!(word(&arena.bytes,SCALAR.base/8+CELLS[i]),s[i]);}}
    }
    println!("CORRECTED_FINITE_BUDGET_CASES=5544 CREDIT_BOUNDARIES=0,424,425,426");
}
