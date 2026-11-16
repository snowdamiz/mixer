//! Development-only synchronous boundary. MainActor session serializes each handle.
use super::*;
use std::ptr;
// Bounded development evidence at API boundaries, never on a cache lookup.
fn trace_usage(stage: &str, usage: SwiftRunUsage) {
    let _ = std::io::Write::write_fmt(&mut std::io::stderr().lock(),
        format_args!("R3294_USAGE {stage} {usage:?}\n"));
}
struct Handle {
    owner: Option<PersistentSwiftUIOwner>,
    frame: Vec<u8>,
    close: Option<SwiftUICloseOutcome>,
    failure: String,
}
#[no_mangle]
pub unsafe extern "C" fn mixer_swift_ui_open_v1(bytes:*const u8,len:usize)->*mut std::ffi::c_void {
    open_ui(bytes, len, SwiftRunBudget::default(), false)
}
#[no_mangle]
pub unsafe extern "C" fn mixer_swift_ui_open_profile_v1(bytes:*const u8,len:usize,profile_id:u32)->*mut std::ffi::c_void {
    if !super::turn_budget::profile_supported(profile_id) { return ptr::null_mut(); }
    let mut budget = SwiftRunBudget::default();
    let plan = crate::experimental::cache::storage::SwiftResourcePlan::ui_profile_1();
    let capacity = plan.activation_capacity();
    budget.frames = capacity; budget.active_pins = capacity; budget.cache_entries = capacity;
    open_ui(bytes, len, budget, true)
}
unsafe fn open_ui(bytes:*const u8,len:usize,budget:SwiftRunBudget,per_turn:bool)->*mut std::ffi::c_void {
    if bytes.is_null() || len==0 || len>64*1024*1024 {return ptr::null_mut();}
    let mut handle=Handle{owner:None,frame:Vec::new(),close:None,failure:String::new()};
    let cancellation=crate::Cancellation::default();
    match validate_swift_ui(std::slice::from_raw_parts(bytes,len),SwiftValidationBudget::default(),&cancellation) {
        Err(failure)=>handle.failure=format!("validation:{failure:?}"),
        Ok(proof)=>{
            let _ = std::io::Write::write_fmt(&mut std::io::stderr().lock(),
                format_args!("R3294_VALIDATED {:?} {:?} control_header_bytes={}\n",proof.observations(),proof.usage(),std::mem::size_of::<control::RuntimeControl>()));
            let construct=if per_turn {PersistentSwiftUIOwner::construct_profile_1} else {PersistentSwiftUIOwner::construct};
            match construct(proof,budget,
            crate::experimental_wasi::WasiGrants{secure_random:true,realtime:true,monotonic:true,stdout:true,stderr:true},
            crate::experimental_wasi::WasiBudget::default(),cancellation) {
            Err(failure)=>{handle.failure=format!("construction:{:?}",failure.failure);handle.close=Some(failure.close);},
            Ok(mut owner)=>{
                match owner.initialize_and_start(){Ok(frame)=>handle.frame=frame,Err(failure)=>handle.failure=format!("startup:{failure:?}")}
                trace_usage("startup",owner.usage());
                handle.owner=Some(owner);
            },
        }},
    }
    Box::into_raw(Box::new(handle)).cast()
}
#[no_mangle]
pub unsafe extern "C" fn mixer_swift_ui_frame_v1(raw:*mut std::ffi::c_void,out:*mut u8,capacity:usize)->isize {
    if raw.is_null(){return -1;}let handle=&mut *raw.cast::<Handle>();
    if !handle.failure.is_empty(){return -1;}
    if out.is_null() {return handle.frame.len()as isize;}
    if capacity<handle.frame.len()||capacity>1_048_576{return -1;}
    ptr::copy_nonoverlapping(handle.frame.as_ptr(),out,handle.frame.len());handle.frame.len()as isize
}
#[no_mangle]
pub unsafe extern "C" fn mixer_swift_ui_event_v1(raw:*mut std::ffi::c_void,bytes:*const u8,len:usize)->i32 {
    if raw.is_null()||bytes.is_null()||len==0||len>1_048_576{return -1;}
    let handle=&mut *raw.cast::<Handle>();if !handle.failure.is_empty(){return -1;}
    let Some(owner)=handle.owner.as_mut()else{return -1;};
    match owner.event(std::slice::from_raw_parts(bytes,len)) {
        Ok(frame)=>{trace_usage("event",owner.usage());handle.frame=frame;0},Err(failure)=>{trace_usage("event-failure",owner.usage());handle.failure=format!("event:{failure:?}");-1},
    }
}
#[no_mangle]
pub unsafe extern "C" fn mixer_swift_ui_error_v1(raw:*mut std::ffi::c_void,out:*mut u8,capacity:usize)->usize {
    if raw.is_null()||out.is_null(){return 0;}let handle=&*raw.cast::<Handle>();
    let bytes=handle.failure.as_bytes();let count=capacity.min(bytes.len());ptr::copy_nonoverlapping(bytes.as_ptr(),out,count);count
}
#[no_mangle]
pub unsafe extern "C" fn mixer_swift_ui_consume_v1(raw:*mut std::ffi::c_void,ledger:*mut u64)->i32 {
    if raw.is_null()||ledger.is_null(){return -1;}
    let mut handle=Box::from_raw(raw.cast::<Handle>());
    handle.frame.clear();handle.frame.shrink_to_fit();
    if let Some(owner)=handle.owner.take(){handle.close=Some(owner.consume());}
    match handle.close.take() {
        None=>0, // Rejected before acquisition, never synthetic zero counters.
        Some(SwiftUICloseOutcome::Clean{usage,failure:_})=>{
            let r=usage.reservations;let l=usage.live;
            let actual=[r.retained_source.current,r.retained_metadata.current,r.cache.current,r.state.current,r.wasi.current,r.shared.current,r.construction.current,r.combined.current,
                l.cache_entries.current,l.active_pins.current,l.frames.current,l.values.current,l.controls.current,l.memory_pages.current,r.live_tickets,usize::from(usage.cleanup_invariant.is_some())];
            for (index,value)in actual.iter().enumerate(){*ledger.add(index)=*value as u64;}1
        },
        Some(frozen)=>{handle.close=Some(frozen);let _=Box::into_raw(handle);2},
    }
}
