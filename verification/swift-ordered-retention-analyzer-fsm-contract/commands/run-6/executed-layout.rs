// Standalone host value-layout support only. No product module or dependencies.
use std::mem::size_of;
#[repr(C)] struct CheckedPair { status:u64,value:u64 }
#[repr(C)] struct Reply { words:[u64;16] }
#[repr(C)] struct StepBudget { remaining:u64,spent:u64 }
type Candidate2048=[u8;2048];
#[repr(C)] struct InitializationRoles<'a> {
    literal:[u8;2048],retained:Candidate2048,
    caller_candidate:&'a mut Candidate2048,callee_candidate:&'a mut Candidate2048,
    arena:&'a mut [u8],steps:&'a mut StepBudget,budget:StepBudget,
    index:u64,zero:u64,expected:u64,checked:CheckedPair,
    reply:Reply,caller_reply:Reply,reply_move:Reply,error_reply:Reply,
}
#[repr(C)] struct Helper<'a> {
    arena:&'a [u8], candidate:&'a mut [u8], cell:u64, base:u64, stride:u64,
    width:u64,end:u64,checked:CheckedPair,bytes:[u8;8],value:u64,
    returned:CheckedPair,index:u64,read_option:Option<&'a [u8]>,
    write_option:Option<&'a mut [u8]>,arithmetic_option:Option<u64>,
}
fn main(){
    assert_eq!(size_of::<usize>(),8);
    assert_eq!(size_of::<CheckedPair>(),16);
    assert_eq!(size_of::<Reply>(),128);
    assert_eq!(size_of::<StepBudget>(),16);
    assert_eq!(size_of::<Option<u64>>(),16);
    assert!(size_of::<Option<&[u8]>>()<=32);
    assert!(size_of::<Option<&mut [u8]>>()<=32);
    assert!(size_of::<Helper>()<=256);
    assert_eq!(size_of::<Candidate2048>(),2048);
    assert_eq!(size_of::<&mut Candidate2048>(),8);
    assert_eq!(size_of::<InitializationRoles>(),4704);
    println!("pair={} reply={} budget={} option_u64={} read_option={} write_option={} helper={} helper_reservation=256 call_roles=4536 init_roles={} transient_reservation=5120 cap=65536 candidate=2048 candidate_borrow={} payload=96 setup_debit=530 record_debit=128 arena=8388608 rust_report=49152 host_record=8192 aggregate_cap=65536",
        size_of::<CheckedPair>(),size_of::<Reply>(),size_of::<StepBudget>(),
        size_of::<Option<u64>>(),size_of::<Option<&[u8]>>(),
        size_of::<Option<&mut [u8]>>(),size_of::<Helper>(),
        size_of::<InitializationRoles>(),size_of::<&mut Candidate2048>());
}
