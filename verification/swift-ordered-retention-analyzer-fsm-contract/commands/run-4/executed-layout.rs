// Standalone host value-layout support only. No product module or dependencies.
use std::mem::size_of;
#[repr(C)] struct CheckedPair { status:u64,value:u64 }
#[repr(C)] struct Reply { words:[u64;16] }
#[repr(C)] struct StepBudget { remaining:u64,spent:u64 }
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
    println!("pair={} reply={} budget={} option_u64={} read_option={} write_option={} helper={} helper_reservation=256 named_roles=4520 transient_reservation=5120 cap=65536 candidate=2048 payload=96 arena=8388608 rust_report=49152 host_record=8192 aggregate_cap=65536",
        size_of::<CheckedPair>(),size_of::<Reply>(),size_of::<StepBudget>(),
        size_of::<Option<u64>>(),size_of::<Option<&[u8]>>(),
        size_of::<Option<&mut [u8]>>(),size_of::<Helper>());
}
