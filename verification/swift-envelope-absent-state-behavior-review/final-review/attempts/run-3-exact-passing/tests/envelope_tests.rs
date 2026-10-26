use super::*;
use std::fs::{self, OpenOptions};
use std::path::{Path, PathBuf};
use std::mem::{size_of, align_of};
include!("caller_cases.rs");

fn prior(later: bool) -> [u64;12] {
    if later { [5,50,60,2,1,3,33,0,2,7,0,0] } else { [0,0,0,0,0,1,33,0,0,0,0,0] }
}
fn initialized(length:usize, p:&[u64;12]) -> Vec<u8> {
    let mut a=vec![0xa5;length];
    for (i,v) in p.iter().enumerate() { let off=SCALAR.base+CELLS[i]*8; if off+8<=length { a[off..off+8].copy_from_slice(&v.to_le_bytes()); } }
    a
}
fn phase_record(p:&[u64;12]) -> [u64;16] {
    let phase=p[4]+1;
    [p[0]+1,13,phase,0,p[1]+1,p[2]+1,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,phase,0,0]
}
fn mapped(status:u64,reason:u64,p:&[u64;12],debit:u64)->[u64;16] {
    [status,reason,p[0],p[7],p[4],p[5],p[3],p[8],p[9],p[11],p[10],p[1],p[2],debit,0,0]
}
fn assert_zero_extent(x:&FixtureEnvelopeObservationV1) {
    assert_eq!([x.observed_records(),x.state(),x.phase(),x.mask(),x.last_operation(),x.active_operation(),x.requested_function(),x.pin_failure(),x.terminal_failure(),x.last_work(),x.last_instructions()],[0;11]);
    assert!(!x.full_replay_accepted() && !x.stored_prefix_validated() && !x.semantic_metrics_valid());
}
fn boundary(x:&FixtureEnvelopeObservationV1)->u64 {match x.boundary(){FixtureEnvelopeBoundaryV1::Unavailable=>0,FixtureEnvelopeBoundaryV1::ClosedEnvelopeObserved=>1,FixtureEnvelopeBoundaryV1::CapCutUnknownTail=>2,FixtureEnvelopeBoundaryV1::Refused=>3,FixtureEnvelopeBoundaryV1::AnalysisLimited=>4,FixtureEnvelopeBoundaryV1::InternalPoisoned=>5}}
fn reason_code(x:&FixtureEnvelopeObservationV1)->u64 {match x.reason(){FixtureEnvelopeReasonV1::Observed=>0,FixtureEnvelopeReasonV1::Steps=>1,FixtureEnvelopeReasonV1::Shape=>2,FixtureEnvelopeReasonV1::Coordinate=>3,FixtureEnvelopeReasonV1::TerminalPhase=>4,FixtureEnvelopeReasonV1::Phase=>5,FixtureEnvelopeReasonV1::ReleaseOpen=>6,FixtureEnvelopeReasonV1::TerminalFailure=>7,FixtureEnvelopeReasonV1::PinFailure=>8,FixtureEnvelopeReasonV1::ForbiddenResume=>9,FixtureEnvelopeReasonV1::Acquire=>10,FixtureEnvelopeReasonV1::Identity=>11,FixtureEnvelopeReasonV1::Stage=>12,FixtureEnvelopeReasonV1::PublicationForm=>13,FixtureEnvelopeReasonV1::CheckedAccess=>14,FixtureEnvelopeReasonV1::InternalPoisoned=>15,FixtureEnvelopeReasonV1::FramingUnavailable=>16,FixtureEnvelopeReasonV1::FramingInvalid=>17,FixtureEnvelopeReasonV1::FramingLimited=>18,FixtureEnvelopeReasonV1::EnvelopeUnavailable=>19,FixtureEnvelopeReasonV1::UnavailableState=>20,FixtureEnvelopeReasonV1::IncompleteBoundary=>21}}
fn progress(reply:FixtureEnvelopeReplyV1,valid:u64,debit:u64)->FixtureEnvelopeProgressV1 { FixtureEnvelopeProgressV1{reply_valid:valid,debit,reply} }

#[test]
fn independent_r2_absent_precedes_all_funding_and_preserves_bytes() {
    let p=prior(false); let w=phase_record(&p); let record=FixtureDecodedRecordV1{words:&w};
    let mut debits=Vec::new(); let mut calls=0;
    for length in [0usize,32,7_731_055] {
        let mut arena=initialized(length,&p); let before=arena.clone();
        for credits in [0,1,424,425,426] {
            let mut candidate=[0x5a;2048]; let before_candidate=candidate;
            let mut steps=StepBudget{remaining:credits,spent:0};
            let r=observe_fixture_envelope_v1(&mut arena,&mut candidate,&record,&mut steps);
            assert_eq!(r.words,[3,15,0,0,0,0,0,0,0,0,0,0,0,0,0,0],"length={length} credits={credits}");
            assert_eq!((steps.remaining,steps.spent),(credits,0));
            assert!(arena==before,"arena mutation length={length} credits={credits}");
            assert!(candidate==before_candidate,"candidate mutation");
            assert!(reply_debit_valid(&r,&steps),"canonical zero-poison rejected");
            if length<=32 { debits.push(r.words[13]); } calls+=1;
        }
    }
    assert_eq!(debits,vec![0;10]); println!("r2_original_debits={debits:?}; absent_calls={calls}");
}

#[test]
fn independent_readable_underfunded_all425_first_later_valid_malformed() {
    let mut calls=0;
    for later in [false,true] {
        let p=prior(later); let good=phase_record(&p); let mut bad=good; bad[1]=0;
        let mut arena=initialized(7_731_056,&p); let before=arena.clone();
        for w in [&good,&bad] {
            let record=FixtureDecodedRecordV1{words:w};
            for credits in 0..425 {
                let mut candidate=[0x71;2048]; let before_c=candidate; let mut steps=StepBudget{remaining:credits,spent:0};
                let r=observe_fixture_envelope_v1(&mut arena,&mut candidate,&record,&mut steps);
                assert_eq!(r.words,mapped(2,1,&p,0));
                assert_eq!((steps.remaining,steps.spent),(credits,0));
                assert!(arena==before,"underfunded arena mutation later={later} credits={credits}");
                assert!(candidate==before_c); assert!(reply_debit_valid(&r,&steps)); calls+=1;
            }
        }
    }
    assert_eq!(calls,1700); println!("readable_underfunded_calls={calls}");
}

#[test]
fn independent_full_readability_exact425_and426_normal_and_atomic_refusal() {
    let p=prior(false); let good=phase_record(&p); let mut bad=good; bad[1]=0;
    for credits in [425,426] {
        for accepted in [true,false] {
            let mut arena=initialized(7_731_056,&p); let before=arena.clone(); let mut c=[0x66;2048]; let before_c=c;
            let record=FixtureDecodedRecordV1{words:if accepted{&good}else{&bad}};
            let mut steps=StepBudget{remaining:credits,spent:0}; let r=observe_fixture_envelope_v1(&mut arena,&mut c,&record,&mut steps);
            assert_eq!((steps.remaining,steps.spent,r.words[13]),(credits-425,425,425));
            assert_eq!(reply_debit_valid(&r,&steps),credits==425,"caller only expects exact425 entry");
            if accepted {
                let mut n=p; n[0]=1;n[1]=1;n[2]=1;n[4]=1;n[5]=3;
                assert_eq!(r.words,mapped(1,0,&n,425));
                let mut expected=before;
                for (i,v) in n.iter().enumerate(){let at=SCALAR.base+8*CELLS[i];expected[at..at+8].copy_from_slice(&v.to_le_bytes());}
                assert!(arena==expected);assert!(c[..888]==before_c[..888] && c[984..]==before_c[984..]);
                for (i,v) in n.iter().enumerate(){assert_eq!(&c[888+8*i..896+8*i],v.to_le_bytes().as_slice());}
            } else { assert_eq!(r.words,mapped(2,2,&p,425)); assert!(arena==before);assert!(c==before_c); }
        }
    }
}

#[test]
fn independent_invalid_entry_spent_poison_is_unpaid_and_immutable() {
    let p=prior(false);let w=phase_record(&p);let record=FixtureDecodedRecordV1{words:&w};let mut calls=0;
    for length in [0,7_731_056] { let mut a=initialized(length,&p);let before=a.clone();
        for spent in [1,425,u64::MAX] {for remaining in [0,425] {
            let mut c=[0x29;2048];let before_c=c;let mut s=StepBudget{remaining,spent};let r=observe_fixture_envelope_v1(&mut a,&mut c,&record,&mut s);
            assert_eq!(r.words,[3,15,0,0,0,0,0,0,0,0,0,0,0,0,0,0]);assert_eq!((s.remaining,s.spent),(remaining,spent));assert!(a==before && c==before_c);assert!(!reply_debit_valid(&r,&s));calls+=1;
        }}
    }println!("invalid_entry_spent_calls={calls}");
}

#[test]
fn independent_corrected_caller_poststate_table19() {
    for &(id,remaining,spent,debit,status,reason,expected) in CALLER_CASES {
        let mut words=[0;16];words[0]=status;words[1]=reason;words[13]=debit;
        let r=FixtureEnvelopeReplyV1{words};let s=StepBudget{remaining,spent};
        assert_eq!(reply_debit_valid(&r,&s),expected,"{id}");println!("caller,{id},{expected}");
    }
}

#[test]
fn independent_canonical_helpers_and_malformed_shape_boundary() {
    let p=prior(true);let r=reply(2,1,&p,0);assert_eq!(r.words,mapped(2,1,&p,0));
    for debit in [0,425] {let r=poisoned(debit);assert_eq!(r.words,[3,15,0,0,0,0,0,0,0,0,0,0,0,debit,0,0]);}
    let arena=Arena{bytes:vec![0;ARENA_BYTES]};let mut s=Framing::new(0);s.complete=true;
    let mut malformed=reply(1,1,&p,425);let steps=StepBudget{remaining:0,spent:425};assert!(reply_debit_valid(&malformed,&steps));
    let x=progress(malformed,1,1006);assert!(leaf_pending(&x));let f=finalize(&x,&s,&Ok(true),&arena);
    assert_eq!((boundary(&f),reason_code(&f)),(0,20));assert_zero_extent(&f);
    for (word,value) in [(0,0),(0,4),(1,16),(3,11),(4,6),(5,64),(9,2),(10,2)] {
        malformed=reply(1,0,&p,425);malformed.words[word]=value;
        assert!(reply_debit_valid(&malformed,&steps));let f=finalize(&progress(malformed,1,1006),&s,&Ok(true),&arena);assert_zero_extent(&f);assert_eq!(reason_code(&f),20);
    }
    let x=progress(reply(2,0,&p,425),1,1006);let f=finalize(&x,&s,&Ok(true),&arena);assert_eq!(reason_code(&f),20);assert_zero_extent(&f);
}

#[test]
fn independent_r1_reason15_and_canonical_refusal_terminal_finalization() {
    let arena=Arena{bytes:vec![0;ARENA_BYTES]};
    for limited in [false,true] {let mut s=Framing::new(0);s.limited=limited;s.complete=!limited;let input=Ok(!limited);
        for (status,reason) in [(1,15),(3,0),(3,15)] {let mut words=[999;16];words[0]=status;words[1]=reason;words[13]=0;let x=progress(FixtureEnvelopeReplyV1{words},1,1431);assert!(!leaf_pending(&x));let f=finalize(&x,&s,&input,&arena);assert_eq!((boundary(&f),reason_code(&f),f.envelope_debit()),(if limited{4}else{5},15,1431));assert_zero_extent(&f);}
        let x=progress(reply(2,1,&prior(false),0),1,1006);assert!(!leaf_pending(&x));let f=finalize(&x,&s,&input,&arena);assert_eq!((boundary(&f),reason_code(&f)),(if limited{4}else{3},1));
    }
}

fn bytes(words:&[u64])->Vec<u8>{words.iter().flat_map(|v|v.to_le_bytes()).collect()}
fn context()->Vec<u8>{let mut w=vec![0u64;1024];w[..16].copy_from_slice(&[FIXTURE_MAGIC,1,8192,1,5,63,100,1,1,1,1,0,100,10,0,0]);bytes(&w)}
fn profile_bytes()->Vec<u8>{let mut w=vec![0;PROFILE_BYTES as usize/8];w[..16].copy_from_slice(&[PROFILE_MAGIC,1,512,32,80000,100,1,1,1,1,0,100,10,0,0,0]);for row in 0..80000{let i=64+row*4;w[i]=u32::MAX as u64*0x1_0000_0000;w[i+1]=ABSENT;}w[64]=1;w[65]=0;w[66]=1;bytes(&w)}
fn phases()->Vec<[u64;16]>{(1..=5).map(|i|[i,13,i,0,i,i,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,i,0,0]).collect()}
fn stream(records:&[[u64;16]],cap:bool,bad_footer:bool)->Vec<u8>{
    let mut h=[0;64];h[..10].copy_from_slice(&[HEADER_MAGIC,1,512,128,512,5,80000,64,512,63]);
    let n=records.len() as u64;let last=records.last().copied().unwrap_or([0;16]);let mut f=[0;64];
    f[0]=FOOTER_MAGIC;f[1]=1;f[2]=n;f[3]=n+u64::from(cap);f[4]=u64::from(cap);f[5]=n;f[6]=last[4];f[7]=last[5];f[8]=records.iter().filter(|r|r[1]==1).map(|r|r[3]).max().unwrap_or(0);f[9]=u64::from(cap);f[10]=last[4];f[11]=last[5];f[14]=ABSENT;f[15]=63;f[33]=5;f[35]=5;
    if bad_footer{f[0]=0;}let mut out=bytes(&h);for w in records{out.extend(bytes(w));}out.extend(bytes(&f));out
}
fn scratch(name:&str)->PathBuf{let p=PathBuf::from(std::env::var("REVIEW_SCRATCH").unwrap()).join(name);fs::create_dir_all(&p).unwrap();p}
fn files(dir:&Path,stream_bytes:&[u8],p:&[u8],c:&[u8]){fs::write(dir.join("stream.bin"),stream_bytes).unwrap();fs::write(dir.join("profile.bin"),p).unwrap();fs::write(dir.join("context.bin"),c).unwrap();}
fn open(dir:&Path,out:&str)->(File,File,File,File){(File::open(dir.join("stream.bin")).unwrap(),File::open(dir.join("profile.bin")).unwrap(),File::open(dir.join("context.bin")).unwrap(),OpenOptions::new().read(true).write(true).create_new(true).open(dir.join(out)).unwrap())}
fn paired(name:&str,records:&[[u64;16]],cap:bool,bad_footer:bool,mutation:&str,expected_debit:u64)->FixtureEnvelopeOutcomeV1{
    let dir=scratch(name);let mut stream_data=stream(records,cap,bad_footer);let mut p=profile_bytes();let mut c=context();
    match mutation{"header"=>stream_data[0]=0,"profile"=>p[0]=0,"context"=>c[0]=0,_=>{}}
    files(&dir,&stream_data,&p,&c);let(mut a,mut b,mut c,mut o)=open(&dir,"old.report");let old=analyze_fixture(&mut a,&mut b,&mut c,&mut o).unwrap();drop((a,b,c,o));
    let(mut a,mut b,mut c,mut o)=open(&dir,"new.report");let new=analyze_fixture_envelope_v1(&mut a,&mut b,&mut c,&mut o).unwrap();drop((a,b,c,o));
    let mut old_report=fs::read(dir.join("old.report")).unwrap();let mut new_report=fs::read(dir.join("new.report")).unwrap();assert_eq!(old_report.len(),49152);assert_eq!(new_report.len(),49152);
    assert_eq!((old.decision,old.framed_records,old.physical_records,old.observation,old.fixture_framing_observed()),(new.framing().decision,new.framing().framed_records,new.framing().physical_records,new.framing().observation,new.framing().fixture_framing_observed()));
    assert_eq!(&new_report[8..16],1u64.to_le_bytes().as_slice());assert!(new_report[64*8..].iter().all(|v|*v==0));
    assert_eq!(&new_report[4*8..6*8],&[0;16]);old_report[72..80].fill(0);new_report[72..80].fill(0);assert!(old_report==new_report,"report prefix/body mismatch {name}");
    assert_eq!(new.envelope().envelope_debit(),expected_debit);assert!(!new.full_replay_accepted()&&!new.stored_prefix_validated()&&!new.envelope().semantic_metrics_valid());
    println!("actual_File,{name},framed={},decision={:?},debit={},boundary={:?},reason={:?}",new.framing().framed_records,new.framing().decision,new.envelope().envelope_debit(),new.envelope().boundary(),new.envelope().reason());new
}

#[test]
fn independent_actual_safe_files_reports_and_paid_decode_footer_suppression(){
    let all=phases();let good=paired("complete",&all,false,false,"",2706);assert_eq!((boundary(good.envelope()),reason_code(good.envelope())),(1,0));
    let cap=paired("cap",&all,true,false,"",2706);assert_eq!(boundary(cap.envelope()),2);
    let footer=paired("bad-footer",&all,false,true,"",2706);assert_zero_extent(footer.envelope());assert_eq!(footer.framing().observation.stage,FOOTER_STAGE);
    for (name,mutation) in [("bad-header","header"),("bad-profile","profile"),("unknown-context","context")]{let x=paired(name,&all,false,false,mutation,0);assert_zero_extent(x.envelope());}
    let mut bad=all.clone();bad[1][1]=0;let x=paired("bad-second-record",&bad,false,false,"",1431);assert_zero_extent(x.envelope());assert_eq!(x.framing().framed_records,1);assert_eq!(x.framing().observation.stage,RECORD_STAGE);
}

#[test]
fn independent_actual_files_private_limit_zero_call_and_footer_override(){
    // Private limit seam, actual Files. Unlike public entry, it can stop before
    // the first leaf. Arena still comes from the actual full Arena constructor.
    for bad in [false,true]{let dir=scratch(if bad{"limited-bad-footer"}else{"limited-zero"});files(&dir,&stream(&phases(),false,bad),&profile_bytes(),&context());let(mut a,mut b,mut c,mut o)=open(&dir,"new.report");
        let x=analyze_fixture_envelope_core(&mut a,&mut b,&mut c,&mut o,4_963_868).unwrap();assert_eq!(x.framing().framed_records,0);assert_eq!(x.envelope().envelope_debit(),581);assert_zero_extent(x.envelope());
        if bad{assert_eq!(reason_code(x.envelope()),17);assert_eq!(x.framing().observation.stage,FOOTER_STAGE);}else{assert_eq!((boundary(x.envelope()),reason_code(x.envelope())),(0,19));}
        println!("actual_File_private_limit,bad_footer={bad},debit={},framed={}",x.envelope().envelope_debit(),x.framing().framed_records);
    }
}

#[test]
fn independent_G_report_reservation_111_112_113_before_selected_cell_mutation(){
    let data=stream(&phases(),false,false);
    for free in [111,112,113]{let dir=scratch(&format!("G-{free}"));files(&dir,&data,&profile_bytes(),&context());let(mut a,mut b,mut c,mut o)=open(&dir,"unused.report");
        let mut arena=Arena{bytes:vec![0x44;ARENA_BYTES]};for i in 16..48{arena.put64(CONTEXT,i,0,0).unwrap();}let before:[u64;12]=CELLS.map(|cell|arena.get64(SCALAR,cell,0).unwrap());
        let mut budget=Budget::new(STEP_LIMIT).unwrap();budget.report_spent=REPORT_RESERVE-47-free;
        let f=Fixture{cap:5,mask:63,extent:100,types:1,slots:1,pins:1,base:0,capacity:100,entry:10};let mut s=Framing::new(5);let mut p=progress(poisoned(0),0,0);
        let result=walk_fixture_envelope_v1(&mut a,&mut arena,&mut budget,f,data.len() as u64,&mut s,&mut p);
        if free==111{assert!(result.is_err());assert_eq!(p.debit,581);assert_eq!(p.reply_valid,0);assert_eq!(CELLS.map(|cell|arena.get64(SCALAR,cell,0).unwrap()),before);}
        else{assert!(result.is_ok(),"G admission should succeed {free}");assert_eq!(p.debit,2706);assert_eq!(budget.report_spent,REPORT_RESERVE-(free-112));}
        drop((&mut b,&mut c,&mut o));println!("G_local_credits={free},success={},debit={}",result.is_ok(),p.debit);
    }
}

struct RejectOutput{stamp:Stamp,mode:u8}
impl Write for RejectOutput{fn write(&mut self,b:&[u8])->io::Result<usize>{match self.mode{0=>Ok(0),1=>Ok(b.len()+1),_=>Err(io::Error::other("independent output refusal"))}}fn flush(&mut self)->io::Result<()>{Ok(())}}
impl OutputFile for RejectOutput{fn stamp(&mut self)->io::Result<Stamp>{Ok(self.stamp)}fn position(&mut self)->io::Result<u64>{Ok(0)}}
#[test]
fn independent_outer_output_errors_return_no_aggregate(){
    for mode in [0,1,2]{let dir=scratch(&format!("output-{mode}"));files(&dir,&stream(&phases(),false,false),&profile_bytes(),&context());let(mut a,mut b,mut c,_)=open(&dir,"unused.report");let mut o=RejectOutput{stamp:Stamp{fields:[999_999,999_999+mode as u64,0,0,0,0,0,0],regular:1},mode};
        let r=analyze_fixture_envelope_core(&mut a,&mut b,&mut c,&mut o,STEP_LIMIT);let e=r.unwrap_err();assert_eq!(e.stage,OUTPUT_STAGE);assert_eq!(e.code,match mode{0=>IO_ZERO,1=>IO_OVERREPORTED,_=>IO_ERROR});
    }
}

#[test]
fn independent_32_complete_host_layouts(){
    macro_rules! layout{($name:expr,$t:ty,$n:expr)=>{{assert_eq!(size_of::<$t>(),$n,$name);println!("layout,{},{},{}",$name,size_of::<$t>(),align_of::<$t>());}}}
    layout!("AnalyzerError",AnalyzerError,32);layout!("Decision",Decision,8);layout!("ReplayOutcome",ReplayOutcome,104);layout!("Region",Region,24);layout!("Arena",Arena,24);layout!("Budget",Budget,56);layout!("Stamp",Stamp,72);layout!("Reader",Reader,48);layout!("Fixture",Fixture,72);layout!("Framing",Framing,80);
    layout!("Boundary",FixtureEnvelopeBoundaryV1,8);layout!("Reason",FixtureEnvelopeReasonV1,8);layout!("Observation",FixtureEnvelopeObservationV1,128);layout!("Outcome",FixtureEnvelopeOutcomeV1,232);layout!("StepBudget",StepBudget,16);layout!("CheckedPair",CheckedPair,16);layout!("Reply",FixtureEnvelopeReplyV1,128);layout!("Progress",FixtureEnvelopeProgressV1,144);layout!("DecodedRecord",FixtureDecodedRecordV1<'_>,8);layout!("Candidate2048",Candidate2048,2048);
    layout!("Prior12",[u64;12],96);layout!("Words16",[u64;16],128);layout!("Words64",[u64;64],512);layout!("Word8",[u8;8],8);layout!("Block512",[u8;512],512);layout!("VecOwner",Vec<u8>,24);layout!("Slice",&[u8],16);layout!("MutSlice",&mut[u8],16);layout!("Words16Borrow",&[u64;16],8);layout!("CandidateBorrow",&mut Candidate2048,8);layout!("InputResult",Result<bool,AnalyzerError>,40);layout!("AggregateResult",Result<FixtureEnvelopeOutcomeV1,AnalyzerError>,232);
}
