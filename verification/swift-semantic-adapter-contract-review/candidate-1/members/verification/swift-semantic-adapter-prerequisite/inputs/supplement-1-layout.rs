// First-party design layout probe only. This is not an analyzer or product code.
use std::mem::{align_of, size_of, offset_of};
#[repr(C)] struct FunctionRow { body_offset:u64, body_len:u64, type_index:u32, flags:u32,
    acquisitions:u32, builds:u32, plan_hits:u32, plan_conflicts:u32,
    last_window:u32, reserved:u32, scan_credit:u64, build_credit:u64,
    last_acquire:u64, last_work:u64, last_instructions:u64, partial_credit:u64 }
#[repr(C)] struct ResidentRow { occupied:u64, function:u64, bytes:u64, pins:u64,
    last_used:u64, publish_acquire:u64, generation:u64, reserved:u64 }
#[repr(C)] struct PinRow { entry:u64, nonce:u64, operation:u64, acquire:u64, work:u64, instructions:u64 }
#[repr(C)] struct PlanRow { function:u64, body_offset:u64, body_len:u64, type_index:u64, requested_bytes:u64 }
#[repr(C)] struct WindowRow { words:[u64;16] }
#[repr(C)] struct TopRow { function:u64, acquisitions:u64, builds:u64, plan_hits:u64,
    plan_conflicts:u64, scan_credit:u64, build_credit:u64, partial_credit:u64 }
#[repr(C)] struct Custody { dev:u64, ino:u64, mode:u64, len:u64, mtime_sec:i64,
    mtime_nsec:i64, ctime_sec:i64, ctime_nsec:i64 }
fn main() {
    assert_eq!(size_of::<usize>(),8);
    assert_eq!(size_of::<FunctionRow>(),96); assert_eq!(align_of::<FunctionRow>(),8);
    assert_eq!(offset_of!(FunctionRow, partial_credit),88);
    assert_eq!(size_of::<ResidentRow>(),64); assert_eq!(size_of::<PinRow>(),48);
    assert_eq!(size_of::<PlanRow>(),40); assert_eq!(size_of::<WindowRow>(),128);
    assert_eq!(size_of::<TopRow>(),64);
    assert_eq!(size_of::<Custody>(),64);
    let regions = [ ("functions",80000*96), ("residents",64*64), ("pins",64*48),
        ("plans",512*40), ("recency",64*8), ("windows",128*128),
        ("histograms",6*66*8), ("top",32*64), ("scalar_state",4096),
        ("contexts",8192), ("io_buffer",65536), ("report",65536) ];
    let mut offset=0;
    for (name,len) in regions {assert_eq!(offset%8,0);println!("{name} offset={offset} bytes={len}");offset+=len;}
    assert_eq!(offset,7_873_120); assert!(offset<=8_388_608);
    println!("arena_used={offset} arena_capacity=8388608 spare={}",8_388_608-offset);
    // Complete declared disjoint transient-role groups. These are conservative
    // reservations, not a claim of physical stack/RSS or accepted implementation.
    let transients=[("wire_and_decode",3072),("record_candidate",2048),
        ("hash_and_io",4096),("metadata_and_results",4096),
        ("path_and_setup",12288),("control_and_helpers",8192),
        ("report_and_errors",8192)];
    let mut transient=0;
    for (name,len) in transients {println!("transient {name} bytes={len}");transient+=len;}
    assert_eq!(transient,41984); assert!(transient<=65536);
    println!("transient_reserved={transient} ceiling=65536 unassigned=23552");
}
