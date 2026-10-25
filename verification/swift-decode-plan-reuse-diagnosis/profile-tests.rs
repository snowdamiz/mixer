
#[test]
fn plan_reuse_profile_envelopes_without_guest_execution() {
    use super::execution::{self,SwiftReactorInstance};
    use super::execution::frame_operations::{FrameOperationStorage,FrameCompletion};
    use crate::experimental_wasi::accounted::accounted_header_bytes;
    let bytes=fixture(0,&[0,0x0b],100);
    let max=SwiftRunBudget::default();
    let mut pair=Some(adopt(&bytes,max));
    let mut returned=Some(SwiftReactorInstance::construct(&mut pair,WasiGrants::default(),WasiBudget::default(),Instant::now(),cache_cursor()));
    let mut owner=returned.take().unwrap().unwrap();assert!(pair.is_none());drop((pair,returned));
    let constructed=owner.control.as_ref().unwrap().usage(owner.wasi.as_ref().map(AccountedWasi::usage));
    assert_eq!(constructed.reservations.live_tickets,21);
    for f in 34..98 {
        let cache=owner.cache.as_mut().unwrap();let control=owner.control.as_mut().unwrap();let wasi=owner.wasi.as_ref();
        let p=pin(cache,control,f,wasi).unwrap();cache.release(p,control,wasi).map_err(|e|e.failure).unwrap();
    }
    let resident=owner.control.as_ref().unwrap().usage(owner.wasi.as_ref().map(AccountedWasi::usage));
    assert_eq!(resident.live.cache_entries.current,64);assert_eq!(resident.reservations.live_tickets,85);
    let mut preparation=Some(owner.prepare_frames(cache_cursor()));
    let mut phase=preparation.take().unwrap().unwrap();let report=phase.drain();
    let bound=report.bound.unwrap();assert_eq!(report.usage.instructions,0);assert_eq!(report.usage.instruction_fuel,0);
    let frame_bytes=bound.admitted-bound.previous;
    assert!(matches!(phase.complete(FrameOperationStorage{preparation,entry:None,returned:None,drained:Some(report),controlled:None}),FrameCompletion::Completed));
    let floor=foundation_construction_bytes().unwrap();
    let construction=execution::construction_bytes().unwrap();
    let execution_header=execution::execution_header_bytes().unwrap();
    // A conservative simultaneous ceiling calculation, not a claim that every
    // independent category ceiling is reachable in a valid module.
    let categories=max.source_bytes+max.metadata_bytes+max.cache_bytes+max.state_bytes;
    let wasi=accounted_header_bytes().unwrap()+4*65536;
    let shared=constructed.reservations.shared.current;
    let phase_peak=floor+construction.max(frame_bytes+cache_operation_bytes().unwrap());
    let maximum_envelope=categories+wasi+shared+phase_peak;
    println!("PLAN_PROFILE floor={floor} execution_header={execution_header} execution_construction={construction} frame_operation={frame_bytes} category_ceiling_sum={categories} wasi_max={wasi} shared={shared} conservative_combined={maximum_envelope} combined_limit={} constructed_current={} constructed_peak={} resident_current={} resident_peak={} frame_peak={} tickets={}/{}",max.combined_bytes,constructed.reservations.combined.current,constructed.reservations.combined.peak,resident.reservations.combined.current,resident.reservations.combined.peak,report.usage.reservations.combined.peak,report.usage.reservations.live_tickets,report.usage.reservations.peak_tickets);
    assert!(maximum_envelope<=max.combined_bytes);
    assert!(execution_header<=max.state_bytes);assert!(report.usage.reservations.peak_tickets<=86);
    assert_eq!(owner.control.as_ref().unwrap().budget(),max);
    let mut owned=Some(owner);let mut cleanup=Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail=cleanup.take().unwrap().unwrap();let mut failure=None;let mut usage=None;
    tail.complete((owned,cleanup),&mut failure,&mut usage);
    let final_usage=usage.unwrap();assert_eq!(final_usage.reservations.combined.current,0);assert_eq!(final_usage.reservations.live_tickets,0);assert!(failure.is_none());
    println!("PLAN_PROFILE cleanup_zero=true guest_instructions=0 initializes=0 invokes=0");
}
