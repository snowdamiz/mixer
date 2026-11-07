//! Isolated host controls for the selected absent-state/caller correction.
use super::*;

const READABLE: usize = 7_731_056;
fn prior_projection(s: &[u64; 12], status: u64, reason: u64, debit: u64) -> [u64;16] {
    [status,reason,s[0],s[7],s[4],s[5],s[3],s[8],s[9],s[11],s[10],s[1],s[2],debit,0,0]
}
fn expected_poison() -> [u64;16] {
    let mut expected=[0;16]; expected[0]=3; expected[1]=15; expected
}
fn poststate_expected(remaining: u64, spent: u64, status: u64, reason: u64, debit: u64) -> bool {
    (remaining==0 && spent==425 && debit==425)
        || (spent==0 && debit==0 && ((status==3 && reason==15) || (status==2 && reason==1 && remaining<425)))
}

#[test]
fn absent_zero_short_and_last_unreadable_byte_precede_budget_and_record_checks() {
    let mut cases=0;
    for length in [0,32,READABLE-1] {
        let mut arena=vec![0xA5;length]; let before=arena.clone();
        for credits in [0,1,424,425,426] {
            let mut candidate=[0x5A;2048]; let candidate_before=candidate;
            let record=[u64::MAX;16];
            let mut steps=StepBudget {remaining:credits,spent:0};
            let actual=observe_fixture_envelope_v1(&mut arena,&mut candidate,&FixtureDecodedRecordV1 {words:&record},&mut steps);
            assert_eq!(actual.words,expected_poison(),"length{length} credits{credits}");
            assert_eq!((steps.remaining,steps.spent),(credits,0));
            assert_eq!(arena,before); assert_eq!(candidate,candidate_before);
            assert!(reply_debit_valid(&actual,&steps)); cases+=1;
        }
    }
    assert_eq!(cases,15);
    println!("ABSENT_STATE_CONTROLS=15 ORIGINAL_R2_SUBSET=10 EXTRA_LAST_UNREADABLE=5");
}

#[test]
fn every_present_underfunded_credit_preserves_actual_prior_before_malformed_record() {
    let states=[initial_state(),[4,10,20,1,0,1,33,3,1,7,0,0]];
    let record=[u64::MAX;16]; let mut cases=0;
    for length in [READABLE,ARENA_BYTES] { for state in states {
        let mut arena=Arena {bytes:vec![0xA5;length]}; arena_state(&mut arena,&state);
        let before=arena.bytes.clone(); let mut candidate=[0x5A;2048]; let candidate_before=candidate;
        for credits in 0..425 {
            let mut steps=StepBudget {remaining:credits,spent:0};
            let actual=observe_fixture_envelope_v1(&mut arena.bytes,&mut candidate,&FixtureDecodedRecordV1 {words:&record},&mut steps);
            assert_eq!(actual.words,prior_projection(&state,2,1,0));
            assert_eq!((steps.remaining,steps.spent),(credits,0));
            assert_eq!(arena.bytes,before); assert_eq!(candidate,candidate_before);
            assert!(reply_debit_valid(&actual,&steps)); cases+=1;
        }
    }}
    assert_eq!(cases,1700); println!("PRESENT_UNDERFUNDED_CONTROLS=1700 CREDITS=0..424 LENGTHS=7731056,8388608 STATES=2");
}

#[test]
fn funded425_keeps_normal_observation_and_only_fixed_commit_ranges() {
    let state=initial_state(); let mut next=state;
    next[0]=1; next[3]=1; next[7]=1; next[8]=1; next[9]=7;
    let mut cases=0;
    for length in [READABLE,ARENA_BYTES] {
        let mut arena=Arena {bytes:vec![0xA5;length]}; arena_state(&mut arena,&state);
        let mut expected=arena.bytes.clone();
        for i in 0..12 { put(&mut expected,SCALAR.base/8+CELLS[i],next[i]); }
        let mut candidate=[0x5A;2048]; let mut expected_candidate=candidate;
        for (i,value) in next.iter().enumerate() {expected_candidate[888+i*8..896+i*8].copy_from_slice(&value.to_le_bytes());}
        let mut record=event(1); record[0]=1;
        let mut steps=StepBudget {remaining:425,spent:0};
        let actual=observe_fixture_envelope_v1(&mut arena.bytes,&mut candidate,&FixtureDecodedRecordV1 {words:&record},&mut steps);
        assert_eq!(actual.words,prior_projection(&next,1,0,425));
        assert_eq!((steps.remaining,steps.spent),(0,425));
        assert!(reply_debit_valid(&actual,&steps)); assert_eq!(arena.bytes,expected);
        assert_eq!(candidate,expected_candidate); cases+=1;
    }
    assert_eq!(cases,2); println!("NORMAL_FUNDED425_CONTROLS=2 EXACT_ARENA_AND_CANDIDATE_MUTATION_CHECKED");
}

#[test]
fn nonzero_entry_spent_is_poison0_and_never_mutates_any_private_budget_field() {
    let mut cases=0;
    for length in [0,32,READABLE-1,READABLE,ARENA_BYTES] {
        let mut arena=Arena {bytes:vec![0xA5;length]};
        if length>=READABLE {arena_state(&mut arena,&initial_state());}
        let before=arena.bytes.clone(); let record=[u64::MAX;16];
        for spent in [1,424,425,426,u64::MAX] {for credits in [0,1,424,425,426] {
            let mut candidate=[0x5A;2048]; let candidate_before=candidate;
            let mut steps=StepBudget {remaining:credits,spent};
            let actual=observe_fixture_envelope_v1(&mut arena.bytes,&mut candidate,&FixtureDecodedRecordV1 {words:&record},&mut steps);
            assert_eq!(actual.words,expected_poison());
            assert_eq!((steps.remaining,steps.spent),(credits,spent));
            assert_eq!(arena.bytes,before); assert_eq!(candidate,candidate_before);
            assert!(!reply_debit_valid(&actual,&steps)); cases+=1;
        }}
    }
    assert_eq!(cases,125); println!("INVALID_ENTRY_SPENT_CONTROLS=125 PRIVATE_STATE_UNCHANGED_CALLER_REJECTS");
}

#[test]
fn finite_caller_matrix_checks_poststate_debit_coherence_only() {
    let domains=[0,1,424,425,426,u64::MAX]; let mut cases=0;
    for remaining in domains {for spent in domains {for status in [0,1,2,3,4,u64::MAX] {
        for reason in [0,1,2,14,15,16,u64::MAX] {for debit in domains {for reserved in [0,u64::MAX] {
            let mut words=[99;16]; words[0]=status; words[1]=reason; words[13]=debit; words[14]=reserved; words[15]=reserved;
            let actual=FixtureEnvelopeReplyV1 {words}; let steps=StepBudget {remaining,spent};
            assert_eq!(reply_debit_valid(&actual,&steps),poststate_expected(remaining,spent,status,reason,debit),
                "poststate remaining{remaining} spent{spent} status{status} reason{reason} debit{debit} reserved{reserved}");
            cases+=1;
        }}}
    }}}
    assert_eq!(cases,18144);
    println!("POSTSTATE_DEBIT_MATRIX_CASES=18144 NO_BEFORE_BUDGET_OR_GENERAL_REPLY_SHAPE_CLAIM");
}

#[test]
fn actual_zero_guard_installation_latches_once_and_preserves_every_main425() {
    let mut controls=0;
    for (length,credits,spent) in [(32,0,0),(32,425,0),(32,426,0),(ARENA_BYTES,0,0),(ARENA_BYTES,424,0),(ARENA_BYTES,425,1)] {
        let mut arena=Arena {bytes:vec![0xA5;length]};
        if length>=READABLE {arena_state(&mut arena,&initial_state());}
        let before=arena.bytes.clone(); let mut candidate=[0x5A;2048]; let candidate_before=candidate;
        let mut main=Budget::new(STEP_LIMIT).unwrap();
        main.setup(SETUP_ENVELOPE).unwrap(); main.report(FINISH_ENVELOPE).unwrap(); main.report(UNDERFUNDED_GUARD).unwrap();
        let mut p=blank_progress(); let record=[u64::MAX;16]; let mut calls=0;
        for _ in 0..4 {
            assert!(main.replay_left>=RECORD_PREFLIGHT);
            main.replay(COMBINED_RECORD).unwrap(); p.debit+=RECORD_ENVELOPE;
            if leaf_pending(&p) {
                let mut steps=StepBudget {remaining:credits,spent};
                let received=observe_fixture_envelope_v1(&mut arena.bytes,&mut candidate,&FixtureDecodedRecordV1 {words:&record},&mut steps);
                assert_eq!(received.words[13],0);
                p.reply=received; p.reply_valid=1;
                if !reply_debit_valid(&p.reply,&steps) {p.reply=poisoned(RECORD_ENVELOPE);}
                calls+=1;
            }
        }
        assert_eq!(calls,1); assert_eq!(main.replay_spent,534+4*471);
        assert_eq!(main.setup_spent,534); assert_eq!(main.report_spent,47+112);
        assert_eq!(p.debit,581+4*425); assert!(!leaf_pending(&p));
        assert_eq!(arena.bytes,before); assert_eq!(candidate,candidate_before);
        if length<READABLE || spent!=0 {
            assert_eq!(&p.reply.words[..2],&[3,15]);
            assert_eq!(p.reply.words[13],if spent==0 {0}else{425});
        } else {assert_eq!(&p.reply.words[..2],&[2,1]); assert_eq!(p.reply.words[13],0);}
        for limited in [false,true] {for cap in [0,1] {
            let mut s=Framing::new(4); s.complete=!limited; s.limited=limited; s.flags=cap;
            let result=finalize(&p,&s,&Ok(!limited),&arena);
            assert_eq!(result.envelope_debit(),2281);
            assert!(!result.full_replay_accepted()); assert!(!result.stored_prefix_validated()); assert!(!result.semantic_metrics_valid());
            if p.reply.words[0]==3 {assert_eq!(result.reason(),&FixtureEnvelopeReasonV1::InternalPoisoned); zero_extent(&result);}
            else {assert_eq!(result.reason(),&FixtureEnvelopeReasonV1::Steps); assert_eq!(result.observed_records(),0);}
        }}
        controls+=1;
    }
    assert_eq!(controls,6);
    println!("ACTUAL_GUARD_DISPATCH_CONTROLS=6 MAIN_B_EVENTS=24 LEAF_CALLS=6 FINALIZER_BRANCHES=24 NO_PUBLIC_REFUND");
}

#[test]
fn malformed_zero_forms_fall_back_to_terminal_poison_and_paid_mixed_markers_stay_terminal() {
    let arena=Arena {bytes:vec![]}; let mut cases=0;
    for (remaining,spent,status,reason,debit) in [
        (425,0,2,1,0),(0,0,1,0,0),(425,0,1,15,0),(425,0,2,15,0),
        (0,0,3,0,0),(0,1,3,15,0),(0,425,3,15,0),(0,0,3,15,1)] {
        let steps=StepBudget {remaining,spent};
        let mut p=blank_progress(); p.debit+=425;
        p.reply.words=[99;16]; p.reply.words[0]=status; p.reply.words[1]=reason; p.reply.words[13]=debit;
        p.reply_valid=1; assert!(!reply_debit_valid(&p.reply,&steps));
        if !reply_debit_valid(&p.reply,&steps) {p.reply=poisoned(425);}
        assert_eq!(p.reply.words[13],425); assert!(!leaf_pending(&p)); assert_eq!(p.debit,1006);
        let mut s=Framing::new(1); s.complete=true;
        let out=finalize(&p,&s,&Ok(true),&arena); zero_extent(&out);
        assert_eq!(out.reason(),&FixtureEnvelopeReasonV1::InternalPoisoned); assert_eq!(out.envelope_debit(),1006);
        cases+=1;
    }
    for (status,reason) in [(1,15),(2,15),(3,0),(3,15)] {
        let steps=StepBudget {remaining:0,spent:425};
        let mut p=blank_progress(); p.debit+=425; p.reply_valid=1; p.reply.words=[99;16];
        p.reply.words[0]=status; p.reply.words[1]=reason; p.reply.words[13]=425;
        assert!(reply_debit_valid(&p.reply,&steps)); assert!(!leaf_pending(&p));
        let mut s=Framing::new(1); s.complete=true;
        let out=finalize(&p,&s,&Ok(true),&arena); zero_extent(&out); assert_eq!(out.reason(),&FixtureEnvelopeReasonV1::InternalPoisoned);
        assert_eq!(out.envelope_debit(),1006); cases+=1;
    }
    assert_eq!(cases,12); println!("CALLER_ZERO_REJECTION_AND_PAID_POISON_MARKER_CONTROLS=12 NO_BROAD_FABRICATED_PAID_REPLY_QUALIFICATION");
}

#[test]
fn actual_framing_counter_keeps_prepaid425_for_failure_and_latched_skip() {
    let records=ordered(vec![event(1),event(10),event(9),event(13)]);
    let mut x=inputs(&records,false); let out=invoke(&mut x,STEP_LIMIT).unwrap();
    assert_eq!(out.framing().framed_records,4); assert_eq!(out.envelope().observed_records(),1);
    assert_eq!(out.envelope().reason(),&FixtureEnvelopeReasonV1::Stage);
    assert_eq!(out.envelope().envelope_debit(),2281); assert_unaccepted(&out,&x[3]);
    for mode in 0..2 {
        let mut records=miss();
        if mode==0 {records[0][9]=1;} else {records[0][0]=2;}
        let mut x=inputs(&records,false); let out=invoke(&mut x,STEP_LIMIT).unwrap();
        assert_eq!(out.envelope().envelope_debit(),1006); zero_extent(out.envelope());
        assert_eq!(out.envelope().reason(),&FixtureEnvelopeReasonV1::FramingInvalid); assert_unaccepted(&out,&x[3]);
    }
    println!("ACTUAL_PUBLIC_COUNTER_CONTROLS=3 PREPAID_DECODE_COORDINATE_FAILURE_AND_LATCHED_SKIP");
}
