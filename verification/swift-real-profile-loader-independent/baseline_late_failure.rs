extern crate mixer_vm;
#[path = "../swift-typed-result-codec-implementation/source/vm/tests/swift_reactor_validation_fixture.rs"]
mod fixture;
use mixer_vm::Cancellation;
use mixer_vm::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget, SwiftValidationFailureKind, SwiftValidationUsage};
fn emit(name: &str, u: SwiftValidationUsage) {
    print!("\"{}\":{{\"input_visible_bytes\":{},\"source_bytes\":{},\"metadata_reserved\":{},\"scratch_reserved\":{},\"metadata_peak_reserved\":{},\"scratch_peak_reserved\":{},\"total_peak_reserved\":{},\"work_used\":{},\"deadline_ms\":{}}}", name, u.input_visible_bytes,u.source_bytes,u.metadata_reserved,u.scratch_reserved,u.metadata_peak_reserved,u.scratch_peak_reserved,u.total_peak_reserved,u.work_used,u.deadline_ms);
}
fn main() {
    let mut f=fixture::Fixture::default();
    f.custom_name=Some(b"independent-review-late-function-failure".to_vec());
    f.custom_payload=vec![0xa5;8*1024*1024];
    let valid=f.bytes();
    let proof=validate_swift_reactor(&valid,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();
    assert_eq!(proof.observations().validated_bodies,29);
    let success_usage=proof.usage();
    drop(proof);
    f.bodies[28]=vec![0,0xff,0x0b];
    let invalid=f.bytes();
    let failure=match validate_swift_reactor(&invalid,SwiftValidationBudget::default(),&Cancellation::default()){Ok(_)=>panic!("late opcode unexpectedly accepted"),Err(e)=>e};
    assert_eq!(failure.kind,SwiftValidationFailureKind::Unsupported);
    assert_eq!(failure.code,"opcode");
    assert_eq!(failure.function,Some(62));
    assert!(failure.offset>8*1024*1024);
    assert_eq!(failure.usage.input_visible_bytes,invalid.len());
    assert_eq!(failure.usage.source_bytes,invalid.len());
    assert!(failure.usage.metadata_peak_reserved>0);
    assert!(failure.usage.scratch_peak_reserved>0);
    assert!(failure.usage.total_peak_reserved>invalid.len());
    assert!(failure.usage.total_peak_reserved<=invalid.len()+failure.usage.metadata_peak_reserved+failure.usage.scratch_peak_reserved);
    let path=std::env::var_os("MIXER_BASELINE_LATE_FAILURE_OUT").unwrap();
    std::fs::write(path,&invalid).unwrap();
    print!("{{\"valid_source_bytes\":{},\"late_failure_source_bytes\":{},\"failure_code\":\"{}\",\"failure_function\":{},\"failure_offset\":{},",valid.len(),invalid.len(),failure.code,failure.function.unwrap(),failure.offset);
    emit("success_usage",success_usage);print!(",");emit("failure_usage",failure.usage);println!("}}");
}
