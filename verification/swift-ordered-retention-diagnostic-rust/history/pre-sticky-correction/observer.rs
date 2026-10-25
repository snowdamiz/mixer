// Finite test-only owner. No field in RuntimeControl/cache/meter funds this.
pub(super) mod ordered_observer {
    use super::ordered_wire::*;
    use super::super::control::*;
    use std::cell::{Cell,RefCell};
    use std::fs::File;
    use std::marker::PhantomData;
    use std::rc::Rc;
    use std::sync::atomic::{AtomicU32,AtomicU64,Ordering};
    const ACTIVE:u64=1<<63;const CLOSED:u64=1<<62;const INIT:u64=1<<61;
    const COUNTS:u64=(1<<32)-1;
    static GATE_STATE:AtomicU64=AtomicU64::new(CLOSED);
    static FLAGS:AtomicU32=AtomicU32::new(0);
    static NEXT:AtomicU64=AtomicU64::new(1);
    static CURRENT:AtomicU64=AtomicU64::new(0);
    thread_local!{
        static OWNER:Cell<u64>=const{Cell::new(0)};
        static WRITER:RefCell<Option<Writer<File>>>=const{RefCell::new(None)};
    }
    pub struct DispatchGuard{coordinate:u64,dispatches:u64,ended:bool,_single:PhantomData<Rc<()>>}
    #[derive(Debug,Clone,Copy)]
    pub struct EndReceipt{pub finalized:bool,pub flags:u32,pub stored:u64,pub attempted:u64,pub attempts_before:u64,pub attempts_after:u64,pub dispatches:u64,pub gate:u64}
    // Source contract: one synchronous owning thread. Only negative tests create
    // callback threads, at most 64, and join them. Thus count is <=64, never near
    // the 32-bit count carry. No CAS loop, spin, wait or overflow speculation.
    fn enter()->bool {
        let before=GATE_STATE.fetch_add(1,Ordering::AcqRel);
        if before&ACTIVE==0||before&CLOSED!=0 {GATE_STATE.fetch_sub(1,Ordering::Release);return false;}
        if before&COUNTS>=64 {FLAGS.fetch_or(GATE,Ordering::Relaxed);GATE_STATE.fetch_sub(1,Ordering::Release);return false;}
        true
    }
    fn leave(){GATE_STATE.fetch_sub(1,Ordering::Release);}
    fn owner()->bool {let expected=CURRENT.load(Ordering::Acquire);OWNER.with(|o|o.get()!=0&&o.get()==expected)}
    fn invalidate(flag:u32){FLAGS.fetch_or(flag,Ordering::Relaxed);}
    pub fn begin(writer:Writer<File>)->Option<DispatchGuard>{
        let old=GATE_STATE.load(Ordering::Acquire);
        if old!=CLOSED {if enter(){invalidate(LIFECYCLE);leave();}return None;}
        if GATE_STATE.compare_exchange(CLOSED,INIT,Ordering::AcqRel,Ordering::Acquire).is_err(){return None;}
        let coordinate=NEXT.load(Ordering::Relaxed);
        if coordinate==u64::MAX||NEXT.compare_exchange(coordinate,coordinate+1,Ordering::AcqRel,Ordering::Acquire).is_err(){GATE_STATE.fetch_or(CLOSED,Ordering::AcqRel);return None;}
        FLAGS.store(0,Ordering::Relaxed);CURRENT.store(coordinate,Ordering::Release);
        OWNER.with(|o|o.set(coordinate));WRITER.with(|w|{*w.borrow_mut()=Some(writer);});
        if GATE_STATE.compare_exchange(INIT,ACTIVE,Ordering::AcqRel,Ordering::Acquire).is_err(){GATE_STATE.fetch_or(CLOSED,Ordering::AcqRel);return None;}
        Some(DispatchGuard{coordinate,dispatches:0,ended:false,_single:PhantomData})
    }
    impl Drop for DispatchGuard {
        fn drop(&mut self){if !self.ended{let before=GATE_STATE.fetch_or(CLOSED,Ordering::AcqRel);if before&COUNTS==0&&owner(){WRITER.with(|w|drop(w.borrow_mut().take()));OWNER.with(|o|o.set(0));GATE_STATE.store(CLOSED,Ordering::Release);}}}
    }
    impl DispatchGuard {
        pub fn dispatch<T>(&mut self,call:impl FnOnce()->T)->T {
            assert_eq!(OWNER.with(Cell::get),self.coordinate);
            assert_eq!(GATE_STATE.load(Ordering::Acquire),ACTIVE);
            self.dispatches=self.dispatches.checked_add(1).unwrap();call()
        }
        pub fn end(mut self,footer:[u64;64])->EndReceipt {
            self.ended=true;
            let previous=GATE_STATE.fetch_or(CLOSED,Ordering::AcqRel);
            let mut receipt=EndReceipt{finalized:false,flags:FLAGS.load(Ordering::Acquire),stored:0,attempted:0,attempts_before:0,attempts_after:0,dispatches:self.dispatches,gate:previous|CLOSED};
            // Never access WRITER if any admitted callback can still use it.
            if previous&ACTIVE==0||previous&CLOSED!=0||previous&COUNTS!=0||!owner(){return receipt;}
            WRITER.with(|cell|{
                let Ok(mut state)=cell.try_borrow_mut()else{receipt.flags|=BORROW;return;};
                let Some(writer)=state.as_mut()else{return;};
                writer.freeze(receipt.flags);
                if writer.observed_mask!=writer.expected_mask||writer.phase!=5{writer.freeze(LIFECYCLE);}
                receipt.attempts_before=writer.attempts;
                writer.finish(footer);
                receipt.stored=writer.stored;receipt.attempted=writer.attempted;
                receipt.flags=writer.flags;receipt.attempts_after=writer.attempts;receipt.finalized=true;
            });receipt
        }
    }
    pub fn retire_after_quiescence(){
        let now=GATE_STATE.load(Ordering::Acquire);assert_ne!(now&CLOSED,0);assert_eq!(now&COUNTS,0);
        WRITER.with(|w|drop(w.borrow_mut().take()));OWNER.with(|o|o.set(0));
        GATE_STATE.store(CLOSED,Ordering::Release);
    }
    pub fn observe(payload:[u64;11],coordinates:(u64,u64))->bool {
        if !enter(){return false;}
        if !owner(){invalidate(CONTEXT);leave();return false;}
        let accepted=WRITER.with(|cell|{
            let Ok(mut state)=cell.try_borrow_mut()else{invalidate(BORROW);return false;};
            let Some(writer)=state.as_mut()else{invalidate(LIFECYCLE);return false;};
            let operation=match payload[0]{1=>match writer.operation.checked_add(1){Some(n)=>n,None=>{writer.freeze(OVERFLOW);return false;}},12|13=>0,14=>if payload[5]==ABSENT{writer.operation}else{0},_=>writer.operation};
            let mut event=Record([0,payload[0],writer.phase,operation,coordinates.0,coordinates.1,payload[1],payload[2],payload[3],payload[4],payload[5],payload[6],payload[7],payload[8],payload[9],payload[10]]);
            if payload[0]==13{event.0[2]=payload[8];}
            if payload[0]==14{event.0[10]=ABSENT;}
            writer.push(event);true
        });leave();accepted
    }
    pub fn acquire(function:u32,coordinates:(u64,u64)){observe([1,function as u64,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],coordinates);}
    pub fn phase(phase:u64,coordinates:(u64,u64)){observe([13,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,phase,0,0],coordinates);}
    pub fn failure(f:&SwiftRunFailure,terminal:bool){
        let code=source_code(f.code);
        if code==0 {if enter(){invalidate(CODE);leave();}return;}
        let operation=if terminal{0}else{ABSENT};
        observe([14,f.function.map_or(ABSENT,|n|n as u64),ABSENT,ABSENT,ABSENT,operation,ABSENT,0,kind(f.kind),code,stage(f.stage)],(f.at_failure.cache_work,f.at_failure.instructions));
    }
    pub fn stage(s:SwiftRunStage)->u64{match s{SwiftRunStage::Adoption=>1,SwiftRunStage::Cache=>2,SwiftRunStage::Initialization=>3,SwiftRunStage::Invocation=>4,SwiftRunStage::Wasi=>5,SwiftRunStage::Cleanup=>6}}
    pub fn kind(k:SwiftRunFailureKind)->u64{match k{SwiftRunFailureKind::InvalidBudget=>1,SwiftRunFailureKind::Cancelled=>2,SwiftRunFailureKind::Deadline=>3,SwiftRunFailureKind::Allocation=>4,SwiftRunFailureKind::Adoption=>5,SwiftRunFailureKind::CategoryExhausted=>6,SwiftRunFailureKind::CombinedExhausted=>7,SwiftRunFailureKind::ResourceExhausted=>8,SwiftRunFailureKind::FuelExhausted=>9,SwiftRunFailureKind::WorkExhausted=>10,SwiftRunFailureKind::HostCallLimit=>11,SwiftRunFailureKind::PinLimit=>12,SwiftRunFailureKind::FrameLimit=>13,SwiftRunFailureKind::ValueLimit=>14,SwiftRunFailureKind::ControlLimit=>15,SwiftRunFailureKind::DecoderMismatch=>16,SwiftRunFailureKind::UnsupportedEnvironment=>17,SwiftRunFailureKind::GuestTrap=>18,SwiftRunFailureKind::GuestExit=>19,SwiftRunFailureKind::Wasi=>20,SwiftRunFailureKind::Invariant=>21}}
    pub fn cleanup(k:Option<SwiftCleanupInvariant>)->u64{match k{None=>0,Some(SwiftCleanupInvariant::ReservationOwner)=>1,Some(SwiftCleanupInvariant::ReservationUnderflow)=>2,Some(SwiftCleanupInvariant::MissingConstruction)=>3,Some(SwiftCleanupInvariant::ConstructionBound)=>4,Some(SwiftCleanupInvariant::LiveUnderflow)=>5}}
    pub fn source_code(code:&str)->u64{match code{
        "swift_run_cancelled"=>1,
        "swift_run_deadline"=>2,
        "swift_run_work"=>3,
        "swift_run_invalid_budget"=>4,
        "swift_run_category_capacity"=>5,
        "swift_run_combined_capacity"=>6,
        "swift_run_cache_entry_capacity"=>7,
        "swift_run_unexpected_capacity"=>8,
        "swift_cache_allocation"=>9,
        "not_defined_function"=>10,
        "pin_nonce_exhausted"=>11,
        "pin_slots_exhausted"=>12,
        "all_entries_pinned"=>13,
        "swift_plan_identity"=>14,
        "swift_plan_layout"=>15,
        "swift_cache_layout_overflow"=>16,
        "swift_run_live_limit"=>17,
        "swift_run_fuel"=>18,
        "entry_bytes"=>19,
        "entry_cannot_fit"=>20,
        "entry_size_overflow"=>21,
        "swift_cache_index_victim"=>22,
        "swift_cache_index_missing"=>23,
        "swift_cache_index_insert"=>24,
        _=>0,
    }}
    pub fn footer(usage:&SwiftRunUsage,failure:Option<&SwiftRunFailure>)->[u64;64]{
        let mut w=[0;64];w[10]=usage.cache_work;w[11]=usage.instructions;w[14]=ABSENT;
        if let Some(f)=failure{w[12]=kind(f.kind);w[13]=source_code(f.code);w[14]=stage(f.stage);w[32]=1;}
        let r=&usage.reservations;
        w[16..25].copy_from_slice(&[r.retained_source.current as u64,r.retained_metadata.current as u64,r.cache.current as u64,r.state.current as u64,r.wasi.current as u64,r.shared.current as u64,r.construction.current as u64,r.combined.current as u64,r.live_tickets as u64]);
        let l=&usage.live;w[25..31].copy_from_slice(&[l.cache_entries.current as u64,l.active_pins.current as u64,l.frames.current as u64,l.values.current as u64,l.controls.current as u64,l.memory_pages.current as u64]);w[31]=cleanup(usage.cleanup_invariant);w
    }
    pub fn with_borrowed(call:impl FnOnce()){WRITER.with(|w|{let _held=w.borrow_mut();call();});}
    pub fn hold_entry_for_fixture()->bool{enter()}
    pub fn leave_for_fixture(){leave();}
    pub fn flags()->u32{FLAGS.load(Ordering::Acquire)}
    pub fn state()->u64{GATE_STATE.load(Ordering::Acquire)}
}
mod ordered_finite_tests {
    use super::*;use super::ordered_observer::*;use super::ordered_wire::*;
    use crate::experimental::cache::borrowed::PinToken;
    use std::fs::{File,OpenOptions};use std::io::Read;use std::os::unix::fs::OpenOptionsExt;use std::path::PathBuf;
    static FILE_ID:std::sync::atomic::AtomicU64=std::sync::atomic::AtomicU64::new(0);
    fn owned()->(DispatchGuard,PathBuf){
        let id=FILE_ID.fetch_add(1,std::sync::atomic::Ordering::Relaxed);
        let path=PathBuf::from(std::env::var_os("TMPDIR").unwrap()).join(format!("ordered-{id}.bin"));
        let file=OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(&path).unwrap();
        assert!(file.metadata().unwrap().is_file());
        let h=header(4096,49,[[7;32];4]).unwrap();
        let writer=Writer::new(file,4096,49,24,&h).unwrap();(begin(writer).unwrap(),path)
    }
    fn read(path:&PathBuf)->Vec<Record>{let mut raw=Vec::new();File::open(path).unwrap().read_to_end(&mut raw).unwrap();assert!(raw.len()>=1024);assert_eq!((raw.len()-1024)%128,0);raw[512..raw.len()-512].chunks_exact(128).map(|r|Record::decode(r.try_into().unwrap())).collect()}
    fn terminal(mut guard:DispatchGuard,cache:SwiftFunctionCache,mut c:RuntimeControl,failure:Option<SwiftRunFailure>)->EndReceipt {
        if let Some(ref f)=failure{failure_observe(f);}
        let coords=c.ordered_coordinates();phase(4,coords);
        let cleanup_result=guard.dispatch(||super::cleanup(cache,&mut c,None));
        if let Some(ref actual)=cleanup_result{let original=failure.as_ref().expect("cleanup failure needs actual original failure");assert_eq!(actual.kind,original.kind);assert_eq!(actual.code,original.code);}
        let usage=c.finish_owned_cleanup(None);assert_eq!(usage.reservations.combined.current,0);assert_eq!(usage.reservations.live_tickets,0);assert_eq!(usage.live.cache_entries.current,0);assert_eq!(usage.live.active_pins.current,0);
        phase(5,(usage.cache_work,usage.instructions));let f=footer(&usage,failure.as_ref());
        let receipt=guard.end(f);retire_after_quiescence();receipt
    }
    fn failure_observe(f:&SwiftRunFailure){ordered_observer::failure(f,true);}
    #[test]fn ordered_finite_success_nonce_release_evict_and_allocation_parity(){
        let bytes=fixture(0,&[0,0x0b],100);
        let run=|on:bool|{
            let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:2,..SwiftRunBudget::default()});
            let mut enabled=if on{Some(owned())}else{None};
            let (result,stats)=measure(||{
                let mut invoke=||{
                    let p=pin(&mut cache,&mut c,34,None).unwrap();let old_nonce=p.nonce();
                    let q=pin(&mut cache,&mut c,35,None).unwrap();cache.release(q,&mut c,None).map_err(|e|e.failure).unwrap();
                    let q=pin(&mut cache,&mut c,36,None).unwrap();cache.release(q,&mut c,None).map_err(|e|e.failure).unwrap();
                    let view=cache.view(&p,&mut c,None).unwrap();assert_eq!(view.function,34);cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();old_nonce
                };
                if let Some((ref mut g,_))=enabled{g.dispatch(invoke)}else{invoke()}
            });
            let u=c.usage(None);
            let out=(result,u.cache_work,u.live,u.reservations,cache.usage(),stats.attempts,stats.allocated_bytes);
            if let Some((g,path))=enabled{
                let receipt=terminal(g,cache,c,None);assert!(receipt.finalized);assert_eq!(receipt.flags,0);assert_eq!(receipt.gate&((1<<32)-1),0);
                let rows=read(&path);let pubs:Vec<_>=rows.iter().filter(|r|r.0[1]==11).collect();let releases:Vec<_>=rows.iter().filter(|r|r.0[1]==12).collect();
                assert_eq!(pubs[0].0[12],result);assert_eq!(releases.last().unwrap().0[12],result);assert_ne!(pubs[1].0[12],result);
                for release in releases{assert_eq!(release.0[8],ABSENT);let p=pubs.iter().find(|p|p.0[11..13]==release.0[11..13]).unwrap();assert_eq!(p.0[6],release.0[6]);assert_eq!(p.0[7],release.0[7]);assert_eq!(p.0[9..13],release.0[9..13]);}
                assert_eq!(rows.iter().filter(|r|r.0[1]==6).count(),1);assert_eq!(rows.iter().filter(|r|r.0[1]==7).count(),1);assert_eq!(rows.iter().filter(|r|r.0[1]==8).count(),1);
                assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));assert_eq!(flags(),0);
                println!("ORDERED_SUCCESS file={} events={} attempts_before={} attempts_after={} dispatches={} flags=0 actual_nonce={result}",path.display(),rows.len(),receipt.attempts_before,receipt.attempts_after,receipt.dispatches);
            }else{finish(cache,c);}
            out
        };assert_eq!(run(false),run(true));
    }
    #[test]fn ordered_finite_cache_work_partial_and_cancellation(){
        for cancel in [false,true]{
            let bytes=fixture(0,&[0,0x41,1,0x1a,0x0b],100);let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
            let (mut guard,path)=owned();
            if cancel{hooks(Hooks{cancel:Some(3),..Hooks::default()});}else{
                // The original control budget is immutable; construct a separate
                // finite owner with its original narrower authored budget.
                let used=c.usage(None).cache_work;finish(cache,c);
                let pair=new(&bytes,SwiftRunBudget{cache_work:used+15,..SwiftRunBudget::default()});c=pair.0;cache=pair.1;
            }
            let original=guard.dispatch(||pin(&mut cache,&mut c,34,None)).unwrap_err();hooks(Hooks::default());
            assert!(matches!(original.kind,SwiftRunFailureKind::Cancelled|SwiftRunFailureKind::WorkExhausted));
            let original_kind=original.kind;let receipt=terminal(guard,cache,c,Some(original));assert!(receipt.finalized);assert_eq!(receipt.flags,0);assert_eq!(receipt.gate&((1<<32)-1),0);
            let rows=read(&path);assert_eq!(rows.iter().filter(|r|r.0[1]==14&&r.0[3]>0).count(),1);assert_eq!(rows.iter().filter(|r|r.0[1]==14&&r.0[3]==0).count(),1);assert!(!rows.iter().any(|r|r.0[1]==11));
            println!("ORDERED_FAILURE original={original_kind:?} file={} events={} attempts={}",path.display(),rows.len(),receipt.attempts_after);
        }
    }
    #[test]fn ordered_finite_gate_wrong_thread_borrow_duplicate_and_after_end(){
        let (guard,_path)=owned();assert!(begin(Writer::new(OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(PathBuf::from(std::env::var_os("TMPDIR").unwrap()).join(format!("ordered-duplicate-{}.bin",FILE_ID.fetch_add(1,std::sync::atomic::Ordering::Relaxed)))).unwrap(),1,33,24,&header(1,33,[[0;32];4]).unwrap()).unwrap()).is_none());
        // Duplicate begin intentionally invalidates the active lifetime.
        assert_ne!(flags()&LIFECYCLE,0);
        std::thread::spawn(||{assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));}).join().unwrap();
        assert_ne!(flags()&CONTEXT,0);
        with_borrowed(||{assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));});assert_ne!(flags()&BORROW,0);
        assert!(hold_entry_for_fixture());let receipt=guard.end([0;64]);assert!(!receipt.finalized);leave_for_fixture();assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));
        assert_eq!(state()&((1<<32)-1),0);retire_after_quiescence();
    }
    #[allow(dead_code)]
    struct CallbackInventory {
        payload:[u64;11],coordinates:(u64,u64),record:Record,body:crate::experimental::descriptors::FunctionSpanView<'static>,
        gate_before:u64,lifetime:u64,operation:Option<u64>,
        gate:&'static std::sync::atomic::AtomicU64,latch:&'static std::sync::atomic::AtomicU32,owner:&'static Cell<u64>,
        cell:&'static std::cell::RefCell<Option<Writer<File>>>,
        borrow_result:Result<std::cell::RefMut<'static,Option<Writer<File>>>,std::cell::BorrowMutError>,
        borrow:std::cell::RefMut<'static,Option<Writer<File>>>,writer:&'static mut Writer<File>,
        file:&'static mut File,bytes:&'static [u8],offset:usize,retry:std::ops::Range<usize>,
        result:std::io::Result<usize>,error:std::io::Error,error_kind:std::io::ErrorKind,
        encode_words:std::slice::Iter<'static,u64>,encode_byte:[u8;8],encode_index:usize,
        record_borrow:&'static Record,encode_output:&'static mut [u8;128],
        checked:Option<u64>,slice:&'static [u8],attempts:&'static mut u64,
        failure:&'static SwiftRunFailure,source_code:&'static str,source_id:u64,
        closure_self:&'static mut CacheOperationPhase<'static>,closure_cache:&'static mut SwiftFunctionCache,
    }
    #[allow(dead_code)]
    struct FrameInventory {header:[u8;512],footer_words:[u64;64],footer_parameter:[u64;64],encoded_footer:[u8;512],frame_return:[u8;512],digests:[[u8;32];4],frame_borrow:&'static[u64;64],receipt:EndReceipt,writer_option:&'static mut Option<Writer<File>>,owner_coordinate:u64,closed:u64,flags:u32,mask:u64}
    #[allow(dead_code)]
    struct WholeOutputInventory {pin_result:Result<SwiftFunctionPin,SwiftRunFailure>,usage:SwiftRunUsage,wasi:Option<WasiUsage>,failure_borrow:Option<&'static SwiftRunFailure>,footer_borrow:&'static SwiftRunUsage,release_result_size_only:&'static Result<(),SwiftReleaseFailure>}
    #[test]fn ordered_finite_layout_inventory(){
        use std::cell::RefCell;use std::sync::atomic::{AtomicU64,AtomicU32};
        let owner=size_of::<RefCell<Option<Writer<File>>>>();
        let atomics=3*size_of::<AtomicU64>()+size_of::<AtomicU32>()+size_of::<Cell<u64>>();
        let helper=size_of::<CallbackInventory>();let frames=size_of::<FrameInventory>();let outputs=size_of::<WholeOutputInventory>();
        let guard=size_of::<DispatchGuard>();let literal_bytes=502usize;
        let subtotal=owner+atomics+3*helper+frames+outputs+guard+literal_bytes;
        // The separate retirement move happens after footer and original consuming
        // calls. Report its full Option owner as an extra conservative value too.
        let retirement=size_of::<Option<Writer<File>>>();let total=subtotal+retirement;
        println!("ORDERED_LAYOUT writer={} writer_align={} tls={} atomics_tls={} helper={} helper_copies=3 frames={} whole_outputs={} guard={} literals={} retirement={} subtotal={} total={} cap=16384 result_pin={} result_release={} failure={} usage={} option_wasi={} io_result={} io_error={}",size_of::<Writer<File>>(),std::mem::align_of::<Writer<File>>(),owner,atomics,helper,frames,outputs,guard,literal_bytes,retirement,subtotal,total,size_of::<Result<SwiftFunctionPin,SwiftRunFailure>>(),size_of::<Result<(),SwiftReleaseFailure>>(),size_of::<SwiftRunFailure>(),size_of::<SwiftRunUsage>(),size_of::<Option<WasiUsage>>(),size_of::<std::io::Result<usize>>(),size_of::<std::io::Error>());
        assert!(total<=16384,"complete conservative external logical inventory exceeds hard ceiling");
    }

}
