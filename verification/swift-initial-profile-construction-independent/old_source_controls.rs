//! Independently authored finite controls against exact prior source only.
//! This is not the selected initial-profile implementation or its acceptance.
use super::*;
use crate::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget};
use crate::experimental_wasi::{WasiBudget, WasiGrants};
use crate::Cancellation;
use std::fs::{File, OpenOptions};
use std::path::Path;
use std::time::Instant;

fn budget() -> SwiftRunBudget {
    SwiftRunBudget {
        source_bytes: 67108864, metadata_bytes: 16777216, cache_bytes: 16777216,
        cache_entry_bytes: 8388608, cache_entries: 64, active_pins: 64,
        cache_work: 64000000, frames: 64, values: 16384, controls: 4096,
        memory_pages: 768, state_bytes: 134217728, combined_bytes: 268435456,
        instruction_fuel: 100000000, execution_work: 1000000000,
        host_calls: 32768, deadline_ms: 30000,
    }
}
fn cursor() -> Cursor {
    Cursor { stage: SwiftRunStage::Initialization, function: None, offset: None }
}
fn adopt(bytes: &[u8], budget: SwiftRunBudget) -> (RuntimeControl, AdoptedProof) {
    let proof=validate_swift_reactor(bytes,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();
    RuntimeControl::adopt(proof,budget,Instant::now(),Cancellation::default()).unwrap()
}
fn construct(control: &mut RuntimeControl, wasi: Option<&AccountedWasi>, adopted: AdoptedProof) -> SwiftFunctionCache {
    let mut preparation=Some(SwiftFunctionCache::prepare(control,wasi,&adopted,cursor()));
    let mut phase=preparation.take().unwrap().unwrap();
    let mut returned: ConstructionReturnSlot=Some(phase.construct(adopted));
    let cache=match returned.take().unwrap() {Ok(cache)=>cache,Err(_)=>panic!("unexpected actual construction failure")};
    assert!(preparation.is_none() && returned.is_none());
    phase.complete((preparation,returned)).unwrap();
    cache
}
fn shape(cache:&SwiftFunctionCache, control:&RuntimeControl, slots:usize, pins:usize, extra:usize) {
    assert_eq!(cache.next_nonce,1);
    assert_eq!(cache.slots.len(),slots);assert_eq!(cache.slots.capacity(),slots);
    assert_eq!(cache.pins.len(),pins);assert_eq!(cache.pins.capacity(),pins);
    assert_eq!(cache.patches.len(),512);assert_eq!(cache.patches.capacity(),512);
    assert_eq!(cache.index.len(),192);assert_eq!(cache.index.capacity(),192);
    assert_eq!(cache.plans.len(),512);assert_eq!(cache.plans.capacity(),512);
    assert!(cache.slots.iter().all(|s|s.resident.is_none()&&s.pins==0&&s.last_used==0));
    assert!(cache.pins.iter().all(|p|p.nonce==0&&p.entry==0));
    assert!(cache.plans.iter().all(Option::is_none));assert!(cache.index.iter().all(|&x|x==0));
    let expected=SwiftCacheUsage { fixed_reserved:cache.usage.fixed_reserved,..SwiftCacheUsage::default()};
    assert_eq!(cache.usage,expected);
    let B=cache_header_bytes().unwrap()+slots*size_of::<SwiftSlot>()+pins*size_of::<PinRecord>()+512*size_of::<decode::Patch>();
    assert_eq!(cache.usage.fixed_reserved,B);
    assert_eq!(control.usage(None).reservations.cache.current,B+extra);
    assert_eq!(control.usage(None).live.active_pins.current,0);
    assert_eq!(control.usage(None).live.cache_entries.current,0);
}
fn cleanup(cache: SwiftFunctionCache, control: &mut RuntimeControl, wasi: Option<&AccountedWasi>) {
    let mut owned=Some(cache);
    let tail=SwiftFunctionCache::cleanup(&mut owned,control,wasi).unwrap();
    assert!(owned.is_none());
    let mut outcome=None;
    tail.complete((owned,Option::<()>::None),&mut outcome);
    println!("CLEANUP_OUTCOME {:?}",outcome);
}
fn finish(control:RuntimeControl) {
    let u=control.finish_owned_cleanup(None);
    assert_eq!(u.reservations.combined.current,0);assert_eq!(u.reservations.live_tickets,0);
    assert_eq!(u.live.active_pins.current,0);assert_eq!(u.live.cache_entries.current,0);
    println!("FINAL {:?}",u);
}
fn fresh(path:&Path)->File {
    OpenOptions::new().create_new(true).read(true).write(true).open(path).unwrap()
}
pub(super) fn run(fixtures:&Path, output:&Path) {
    let b=std::fs::read(fixtures.join("reactor-29.wasm")).unwrap();
    let (mut control,adopted)=adopt(&b,budget());
    let cache=construct(&mut control,None,adopted);
    shape(&cache,&control,29,64,0);
    let mut file=fresh(&output.join("same-cache.rows.bin"));
    let rows=super::super::diagnostic_profile::write_profile_row_body_v1(cache.proof(),&mut file).unwrap();
    assert_eq!(std::fs::read(output.join("same-cache.rows.bin")).unwrap(),std::fs::read(fixtures.join("reactor-29.rows.bin")).unwrap());
    assert_eq!(file.metadata().unwrap().len(),2560000);
    println!("PASS original_exact_phase_storage_constructor_same_proof_rows {:?}",rows);
    cleanup(cache,&mut control,None);finish(control);

    let (mut control,adopted)=adopt(&b,budget());
    let mut p=AccountedWasi::prepare(&mut control,cursor()).unwrap();
    let wasi=p.construct(WasiGrants::default(),WasiBudget{one_transfer_bytes:64,log_bytes:64,..WasiBudget::default()},Instant::now(),cursor()).unwrap();
    p.complete().unwrap();
    let cache=construct(&mut control,Some(&wasi),adopted);shape(&cache,&control,29,64,0);
    assert!(wasi.checked_usage(&mut control,cursor()).is_ok());
    cleanup(cache,&mut control,Some(&wasi));wasi.cleanup(&mut control).unwrap();finish(control);
    println!("PASS actual_common_control_WASI");

    for bytes in [0,1] {
        let (mut control,adopted)=adopt(&b,budget());
        let ticket=control.admit(SwiftReservationCategory::Cache,bytes,cursor()).unwrap();
        let cache=construct(&mut control,None,adopted);shape(&cache,&control,29,64,bytes);
        println!("PASS authentic_extra_Cache_ticket bytes={} actual_B={} current={}",bytes,cache.usage.fixed_reserved,control.usage(None).reservations.cache.current);
        cleanup(cache,&mut control,None);control.drop_reserved((),ticket).unwrap();finish(control);
    }

    let (mut actual,adopted)=adopt(&b,budget());
    let (mut foreign,foreign_adopted)=adopt(&b,budget());
    let failure=match SwiftFunctionCache::prepare(&mut foreign,None,&adopted,cursor()) {Err(f)=>f,Ok(_)=>panic!("foreign prepare succeeded")};
    assert_eq!(failure.stage,SwiftRunStage::Initialization);assert_eq!(failure.code,"swift_run_reservation_owner");
    assert_eq!(actual.usage(None).reservations.retained_source.current,b.len());
    actual.drop_proof(adopted).unwrap();foreign.drop_proof(foreign_adopted).unwrap();
    println!("PASS original_prepare_foreign_borrow_retains_real_adopted {:?}",failure);finish(actual);finish(foreign);

    let (mut control,own)=adopt(&b,budget());
    let (mut foreign,other)=adopt(&b,budget());
    let mut preparation=Some(SwiftFunctionCache::prepare(&mut control,None,&own,cursor()));
    let mut phase=preparation.take().unwrap().unwrap();
    let mut returned:ConstructionReturnSlot=Some(phase.construct(other));
    let failure=match returned.take().unwrap(){Err(f)=>f,Ok(_)=>panic!("foreign constructor succeeded")};
    assert_eq!(failure.failure.code,"swift_run_reservation_owner");
    assert!(failure.rejected_adopted.is_some());
    phase.complete((preparation,returned)).unwrap();
    foreign.drop_proof(failure.rejected_adopted.unwrap()).unwrap();control.drop_proof(own).unwrap();
    println!("PASS original_construct_prepartial_rejected_Some {:?}",failure.failure);finish(control);finish(foreign);

    let (mut control,adopted)=adopt(&b,budget());
    let mut preparation=Some(SwiftFunctionCache::prepare(&mut control,None,&adopted,cursor()));
    let mut phase=preparation.take().unwrap().unwrap();
    phase.control.control.cancellation().cancel();
    let mut returned:ConstructionReturnSlot=Some(phase.construct(adopted));
    let failure=match returned.take().unwrap(){Err(f)=>f,Ok(_)=>panic!("cancelled construction succeeded")};
    assert!(failure.rejected_adopted.is_none());assert_eq!(failure.failure.kind,SwiftRunFailureKind::Cancelled);
    let completion=phase.complete((preparation,returned));assert!(completion.is_ok());
    assert_eq!(control.usage(None).reservations.retained_source.current,0);
    println!("PASS original_construct_partial_rejected_None {:?} {:?}",failure.failure,completion);finish(control);

    let (mut control,adopted)=adopt(&b,budget());
    let mut cache=construct(&mut control,None,adopted);
    let before=cache.usage;
    let mut phase=cache.prepare_operation(&mut control,None,cursor()).unwrap();
    let mut returned=Some(phase.pin(&mut cache,0));
    let failure=match returned.take().unwrap(){Err(f)=>f,Ok(_)=>panic!("import index acquired")};
    phase.complete(returned).unwrap();
    assert_eq!(cache.next_nonce,1);assert_eq!(cache.usage,before);
    shape(&cache,&control,29,64,0);
    println!("PASS actual_imported_acquisition_failed_but_initial_shape_remains {:?}",failure);
    cleanup(cache,&mut control,None);finish(control);
    println!("OLD_SOURCE_ONLY_CONTROLS_COMPLETE");
}
