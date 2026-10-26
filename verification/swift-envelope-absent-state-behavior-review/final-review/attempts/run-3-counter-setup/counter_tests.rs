use super::*;
use super::tests::{prior,initialized,phase_record,progress,scratch,files,stream,phases,profile_bytes,context,open};
use std::sync::atomic::Ordering;

#[test]
fn independent_counted_terminal_private_returns_prevent_later_walk_dispatch() {
    for kind in ["absent","underfunded","R1","refused"] {
        INDEPENDENT_DISPATCH.store(0,Ordering::SeqCst);
        let p0=prior(false);let mut w=phase_record(&p0);if kind=="refused"{w[1]=0;}
        let terminal=if kind=="R1"{let mut words=[999;16];words[0]=1;words[1]=15;words[13]=425;FixtureEnvelopeReplyV1{words}}
        else {let mut a=initialized(if kind=="absent"{32}else{7_731_056},&p0);let mut c=[0x12;2048];let record=FixtureDecodedRecordV1{words:&w};let mut steps=StepBudget{remaining:if kind=="underfunded"{424}else{425},spent:0};let r=independent_counted_leaf(&mut a,&mut c,&record,&mut steps);assert!(reply_debit_valid(&r,&steps));r};
        let expected_calls=usize::from(kind!="R1");assert_eq!(INDEPENDENT_DISPATCH.load(Ordering::SeqCst),expected_calls);
        let words=terminal.words;let mut p=progress(terminal,1,0);assert!(!leaf_pending(&p));
        let dir=scratch(&format!("counted-{kind}"));let data=stream(&phases(),false,false);files(&dir,&data,&profile_bytes(),&context());let(mut input,_profile,_context,_output)=open(&dir,"unused.report");
        let mut arena=Arena{bytes:vec![0;ARENA_BYTES]};let mut budget=Budget::new(STEP_LIMIT).unwrap();let f=Fixture{cap:5,mask:63,extent:100,types:1,slots:1,pins:1,base:0,capacity:100,entry:10};let mut framing=Framing::new(5);
        walk_fixture_envelope_v1(&mut input,&mut arena,&mut budget,f,data.len() as u64,&mut framing,&mut p).unwrap();
        assert_eq!(INDEPENDENT_DISPATCH.load(Ordering::SeqCst),expected_calls,"later dispatch {kind}");assert_eq!(p.reply.words,words);assert_eq!(p.debit,2706);assert_eq!(framing.framed,5);
        let result=finalize(&p,&framing,&Ok(true),&arena);assert_eq!(result.envelope_debit(),2706);
        println!("counted_private_composition,{kind},initial_calls={expected_calls},later_walk_calls=0,public_paid_N=5,debit=2706");
    }
}

#[test]
fn independent_counted_actual_public_file_dispatch_and_paid_counter() {
    INDEPENDENT_DISPATCH.store(0,Ordering::SeqCst);
    let dir=scratch("counted-public-normal");files(&dir,&stream(&phases(),false,false),&profile_bytes(),&context());let(mut a,mut b,mut c,mut o)=open(&dir,"new.report");
    let result=analyze_fixture_envelope_v1(&mut a,&mut b,&mut c,&mut o).unwrap();
    assert_eq!(INDEPENDENT_DISPATCH.load(Ordering::SeqCst),5);assert_eq!(result.envelope().envelope_debit(),2706);
    println!("counted_actual_public_File,actual_dispatches=5,public_paid_N=5,debit=2706");
}
