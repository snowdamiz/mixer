//! Explicit development UI owner. No capability Module casts or command facade.
use super::{control::*, execution::*, ValidatedSwiftUI};
use crate::{Cancellation, Value, experimental_wasi::{WasiBudget, WasiGrants}};
use std::time::Instant;

pub struct PersistentSwiftUIOwner {
    owner: Option<SwiftReactorInstance>,
    entries: [u32; 4],
    failure: Option<SwiftRunFailure>,
    header: Option<[u32; 4]>, // Fixed buffer bounds, no UI revision/receipt state.
    copy_bytes: usize,
}
pub struct SwiftUIOpenFailure { pub failure: SwiftRunFailure, pub close: SwiftUICloseOutcome }
#[must_use]
#[allow(clippy::large_enum_variant, reason = "Frozen retains its exact owner without an unaccounted allocation.")]
pub enum SwiftUICloseOutcome {
    Clean { usage: SwiftRunUsage, failure: Option<SwiftRunFailure> },
    Frozen { owner: Option<PersistentSwiftUIOwner>, usage: Option<SwiftRunUsage>, failure: Option<SwiftRunFailure> },
}
impl PersistentSwiftUIOwner {
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    pub fn construct(proof: ValidatedSwiftUI, budget: SwiftRunBudget, grants: WasiGrants,
        wasi_budget: WasiBudget, cancellation: Cancellation) -> Result<Self, SwiftUIOpenFailure> {
        Self::construct_policy(proof,budget,grants,wasi_budget,cancellation,false)
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    pub(super) fn construct_profile_1(proof:ValidatedSwiftUI,budget:SwiftRunBudget,grants:WasiGrants,
        wasi_budget:WasiBudget,cancellation:Cancellation)->Result<Self,SwiftUIOpenFailure>{
        Self::construct_policy(proof,budget,grants,wasi_budget,cancellation,true)
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    fn construct_policy(proof:ValidatedSwiftUI,budget:SwiftRunBudget,grants:WasiGrants,
        wasi_budget:WasiBudget,cancellation:Cancellation,per_turn:bool)->Result<Self,SwiftUIOpenFailure>{
        let (proof, entries) = proof.into_parts(); let started = Instant::now();
        let mut adopted = match RuntimeControl::adopt(proof, budget, started, cancellation) {
            Ok(pair) => Some(pair), Err(failure) => return Err(SwiftUIOpenFailure {
                failure, close: close_observation(failure.after_cleanup, Some(failure)) }),
        };
        let mut constructed = Some(SwiftReactorInstance::construct(&mut adopted, grants, wasi_budget,
            started, Cursor { stage: SwiftRunStage::Initialization, function: None, offset: None }));
        match constructed.take().expect("one constructor result") {
            Ok(owner) => {
                drop((adopted, constructed));
                let mut this=Self{owner:Some(owner),entries,failure:None,header:None,copy_bytes:0};
                if per_turn {if let Err(failure)=this.owner.as_mut().unwrap().control.as_mut().unwrap().enable_ui_turns(){
                    return Err(SwiftUIOpenFailure{failure,close:this.consume()})
                }}
                Ok(this)
            },
            Err(ConstructionFailure::Rejected(failure)) => {
                let (mut control, proof) = adopted.take().expect("retained exact adopted pair");
                let _ = control.drop_proof(proof);
                let usage = control.finish_owned_cleanup(None);
                Err(SwiftUIOpenFailure { failure, close: close_observation(Some(usage), Some(failure)) })
            },
            Err(ConstructionFailure::Cleanup(tail)) => {
                let mut failure = None; let mut usage = None;
                tail.complete((adopted, constructed), &mut failure, &mut usage);
                let failure = failure.expect("construction cleanup retains original failure");
                Err(SwiftUIOpenFailure { failure, close: close_observation(usage, Some(failure)) })
            },
        }
    }
    fn fault(&mut self, code: &'static str) -> SwiftRunFailure {
        let owner = self.owner.as_mut().expect("owned UI instance");
        owner.lifecycle = Lifecycle::Terminal;
        let failure = owner.control.as_mut().unwrap().fail(
            Cursor { stage: SwiftRunStage::Invocation, function: None, offset: None },
            Fault::new(SwiftRunFailureKind::GuestTrap, code), owner.wasi.as_ref().map(|w|w.usage()));
        self.failure.get_or_insert(failure); failure
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    fn invoke(&mut self, slot: usize, argument: Option<Value>) -> Result<Option<Value>, SwiftRunFailure> {
        if let Some(failure) = self.failure { return Err(failure); }
        let (result, clean) = frame_operations::ui_execution::invoke(self.owner.as_mut().unwrap(), self.entries[slot], argument);
        if !clean { return Err(self.fault("swift_ui_retained_frame_cleanup")); }
        if let Err(failure) = result { self.failure = Some(failure); }
        result
    }
    fn quiescent(&self)->bool{
        let o=self.owner.as_ref().unwrap();let s=o.state.as_ref().unwrap();
        !matches!(o.lifecycle,Lifecycle::Terminal)&&s.frames.is_empty()&&s.values.is_empty()&&s.controls.is_empty()&&s.frame_cleanup.is_empty()
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    fn begin_turn(&mut self,kind:super::turn_budget::Kind)->Result<Option<u64>,SwiftRunFailure>{
        if let Some(f)=self.failure{return Err(f)}
        let q=self.quiescent();let o=self.owner.as_mut().unwrap();
        let epoch=match o.control.as_mut().unwrap().begin_ui_turn(kind,q){
            Ok(e)=>e,Err(f)=>{self.failure=Some(f);o.lifecycle=Lifecycle::Terminal;return Err(f)}
        };
        if epoch.is_some(){
            if let Err(f)=o.wasi.as_mut().unwrap().begin_ui_turn(o.control.as_mut().unwrap()){
                self.failure=Some(f);o.lifecycle=Lifecycle::Terminal;return Err(f)
            }
        }
        Ok(epoch)
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    fn end_turn(&mut self,epoch:Option<u64>)->Result<(),SwiftRunFailure>{
        let q=self.quiescent();let o=self.owner.as_mut().unwrap();
        if let Err(f)=o.control.as_mut().unwrap().end_ui_turn(epoch,q){self.failure=Some(f);o.lifecycle=Lifecycle::Terminal;return Err(f)}
        Ok(())
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    pub fn initialize_and_start(&mut self) -> Result<Vec<u8>, SwiftRunFailure> {
        if !matches!(self.owner.as_ref().unwrap().lifecycle, Lifecycle::Uninitialized) {
            return Err(self.fault("swift_ui_initializer_repeated"));
        }
        let init=self.begin_turn(super::turn_budget::Kind::Initialize)?;
        if self.invoke(0, None)?.is_some() { return Err(self.fault("swift_ui_initializer_result")); }
        // proc_exit, including zero, is terminal and never reaches this point.
        self.end_turn(init)?;
        self.owner.as_mut().unwrap().lifecycle = Lifecycle::Ready;
        let start=self.begin_turn(super::turn_budget::Kind::Start)?;
        let result = self.invoke(1, None)?;
        let frame=self.snapshot(result)?;self.end_turn(start)?;Ok(frame)
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    pub fn event(&mut self, bytes: &[u8]) -> Result<Vec<u8>, SwiftRunFailure> {
        if !matches!(self.owner.as_ref().unwrap().lifecycle, Lifecycle::Ready) || self.header.is_none() {
            return Err(self.fault("swift_ui_event_before_start"));
        }
        let header = self.header.unwrap();
        if bytes.is_empty() || bytes.len() > 1_048_576 { return Err(self.fault("swift_ui_event_bound")); }
        let event=self.begin_turn(super::turn_budget::Kind::Event)?;
        self.charge_copy(bytes.len())?;
        let owner = self.owner.as_mut().unwrap();
        let cursor = Cursor { stage: SwiftRunStage::Invocation, function: None, offset: None };
        owner.control.as_mut().unwrap().work_with_wasi(Work::Execution, bytes.len() as u64, cursor, owner.wasi.as_ref().map(|w|w.usage()))?;
        let start = header[3] as usize;
        owner.state.as_mut().unwrap().memory[start..start+bytes.len()].copy_from_slice(bytes);
        let result = self.invoke(2, Some(Value::I32(bytes.len() as i32)))?;
        let frame=self.snapshot(result)?;self.end_turn(event)?;Ok(frame)
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    fn charge_copy(&mut self, bytes: usize) -> Result<(), SwiftRunFailure> {
        match self.copy_bytes.checked_add(bytes) {
            Some(next) if next <= 8*1_048_576 => { self.copy_bytes=next; Ok(()) },
            _ => Err(self.fault("swift_ui_cumulative_copy_limit")),
        }
    }
    #[allow(clippy::result_large_err, reason = "Inline failure and frozen-owner reporting must not allocate.")]
    fn snapshot(&mut self, result: Option<Value>) -> Result<Vec<u8>, SwiftRunFailure> {
        let offset = match result { Some(Value::I32(offset)) => offset as u32, _ => return Err(self.fault("swift_ui_header_result")) };
        let memory = &self.owner.as_ref().unwrap().state.as_ref().unwrap().memory;
        let begin = offset as usize;
        let raw = match memory.get(begin..begin.saturating_add(32)) {
            Some(raw) => raw, None => return Err(self.fault("swift_ui_header_range")),
        };
        let mut fields = [0u32;8];
        for (field,bytes) in fields.iter_mut().zip(raw.as_chunks::<4>().0) { *field=u32::from_le_bytes(*bytes); }
        if fields[0]!=0x3349554d || fields[1]!=32 || fields[5]!=1_048_576 || fields[6]!=0 || fields[7]!=0
            || fields[3]==0 || fields[3]>1_048_576 { return Err(self.fault("swift_ui_header_fields")); }
        let ranges=[(offset as u64,32u64),(fields[2]as u64,fields[3]as u64),(fields[4]as u64,fields[5]as u64)];
        for (start,len) in ranges { if start+len>memory.len()as u64 || start+len>1u64<<32 { return Err(self.fault("swift_ui_buffer_range")); } }
        for i in 0..3 { for j in i+1..3 { if ranges[i].0+ranges[i].1>ranges[j].0 && ranges[j].0+ranges[j].1>ranges[i].0 {return Err(self.fault("swift_ui_buffer_overlap"));} } }
        let header=[offset,fields[2],fields[3],fields[4]];
        if self.header.is_some_and(|old|old[0]!=header[0]||old[1]!=header[1]||old[3]!=header[3]) {return Err(self.fault("swift_ui_buffers_changed"));}
        self.header=Some(header); self.charge_copy(fields[3]as usize)?;
        let owner=self.owner.as_mut().unwrap();let control=owner.control.as_mut().unwrap();
        let cursor=Cursor {stage:SwiftRunStage::Invocation,function:None,offset:None};
        let ticket=control.admit(SwiftReservationCategory::Shared,fields[3]as usize,cursor)?;
        let mut bytes=Vec::new();
        if bytes.try_reserve_exact(fields[3]as usize).is_err() {
            let _=control.refund(ticket);return Err(self.fault("swift_ui_copy_allocation"));
        }
        let copied=(|| {
            control.exact_capacity_with_wasi(fields[3]as usize,bytes.capacity(),cursor,owner.wasi.as_ref().map(|w|w.usage()))?;
            control.work_with_wasi(Work::Execution, fields[3]as u64,cursor,owner.wasi.as_ref().map(|w|w.usage()))?;
            bytes.extend_from_slice(&owner.state.as_ref().unwrap().memory[fields[2]as usize..(fields[2]+fields[3])as usize]);
            Ok(())
        })();
        if let Err(failure)=copied {drop(bytes);let _=control.refund(ticket);self.failure=Some(failure);return Err(failure);}
        // Ownership transfers to a bounded host value. No guest staging remains.
        control.refund(ticket)?; Ok(bytes)
    }
    pub fn usage(&self) -> SwiftRunUsage {
        let owner=self.owner.as_ref().unwrap();owner.cache.as_ref().unwrap().trace_counts();owner.control.as_ref().unwrap().usage(owner.wasi.as_ref().map(|w|w.usage()))
    }
    pub fn consume(mut self) -> SwiftUICloseOutcome {
        let mut returned=Some(SwiftReactorInstance::cleanup_owned(&mut self.owner));
        match returned.take().unwrap() {
            Ok(tail) => {let mut failure=self.failure;let mut usage=None;tail.complete((self,returned),&mut failure,&mut usage);close_observation(usage,failure)},
            Err(failure) => {self.failure.get_or_insert(failure);let usage=Some(self.usage());SwiftUICloseOutcome::Frozen{owner:Some(self),usage,failure:Some(failure)}},
        }
    }
}
fn close_observation(usage:Option<SwiftRunUsage>,failure:Option<SwiftRunFailure>)->SwiftUICloseOutcome {
    if usage.is_some_and(|u| fourteen_zero(&u)) {SwiftUICloseOutcome::Clean{usage:usage.unwrap(),failure}}
    else {SwiftUICloseOutcome::Frozen{owner:None,usage,failure}}
}
pub(super) fn fourteen_zero(u:&SwiftRunUsage)->bool {
    let r=&u.reservations;let l=&u.live;
    [r.retained_source.current,r.retained_metadata.current,r.cache.current,r.state.current,r.wasi.current,r.shared.current,r.construction.current,r.combined.current,
        l.cache_entries.current,l.active_pins.current,l.frames.current,l.values.current,l.controls.current,l.memory_pages.current].iter().all(|n|*n==0)
        && r.live_tickets==0 && u.cleanup_invariant.is_none()
}

#[cfg(test)]
mod r3672_tests {
 use super::*;
 use crate::{Type,experimental_wasi::WasiFunction};
 use crate::experimental_swift_reactor::{validate_swift_ui,SwiftValidationBudget,ui_ffi::*};
 use crate::experimental::cache::borrowed::PinToken;
 fn uint(mut n:u32,out:&mut Vec<u8>){loop{let b=(n&127)as u8;n>>=7;out.push(b|if n==0{0}else{128});if n==0{return}}}
 fn name(s:impl AsRef<[u8]>,out:&mut Vec<u8>){let s=s.as_ref();uint(s.len()as u32,out);out.extend(s);}
 fn section(id:u8,data:&[u8],out:&mut Vec<u8>){out.push(id);uint(data.len()as u32,out);out.extend(data);}
 fn signature(params:&[Type],results:&[Type],out:&mut Vec<u8>){
  fn ty(t:Type)->u8{match t{Type::I32=>0x7f,Type::I64=>0x7e,Type::F32=>0x7d,Type::F64=>0x7c}}
  out.push(0x60);uint(params.len()as u32,out);out.extend(params.iter().copied().map(ty));uint(results.len()as u32,out);out.extend(results.iter().copied().map(ty));
 }
 // Actual sealed Swift UI ABI: all 34 approved WASI imports, defined entrypoints,
 // table/memory, and an in-bounds, nonoverlapping v3 header/frame/event buffer.
 fn fixture()->Vec<u8>{
  let mut out=b"\0asm\x01\0\0\0".to_vec();let mut types=vec![37];
  for f in WasiFunction::ALL{signature(f.parameters(),f.results(),&mut types);}
  signature(&[],&[],&mut types);signature(&[],&[Type::I32],&mut types);signature(&[Type::I32],&[Type::I32],&mut types);section(1,&types,&mut out);
  let mut imports=vec![34];for(i,f)in WasiFunction::ALL.into_iter().enumerate(){name("wasi_snapshot_preview1",&mut imports);name(f.name(),&mut imports);imports.push(0);uint(i as u32,&mut imports);}section(2,&imports,&mut out);
  section(3,&[4,34,35,36,34],&mut out);section(4,&[1,0x70,1,1,1],&mut out);section(5,&[1,1,17,17],&mut out);
  let mut exports=vec![5];for(n,k,i)in[("memory",2,0),("_initialize",0,34),("mixer_guest_ui_start_v3",0,35),("mixer_guest_ui_event_v3",0,36),("mixer_guest_ui_ready_v3",0,37)]{name(n,&mut exports);exports.push(k);uint(i,&mut exports);}section(7,&exports,&mut out);
  section(10,&[4,2,0,0x0b,4,0,0x41,0,0x0b,4,0,0x41,0,0x0b,2,0,0x0b],&mut out);
  let mut payload=Vec::new();for n in [0x3349554du32,32,32,4,65536,1_048_576,0,0]{payload.extend(n.to_le_bytes());}payload.extend(b"PING");
  let mut data=vec![1,0,0x41,0,0x0b];uint(payload.len()as u32,&mut data);data.extend(payload);section(11,&data,&mut out);out
 }
 fn unknown(stage:&str)->!{
  let message=format!("R3672_LEDGER_UNKNOWN stage={stage}; freeze entire R3672 runtime namespace; no further payload or Drop cleanup\n");
  eprint!("{message}");
  if let Some(path)=std::env::var_os("R3672_HOLD_FILE"){let _=std::fs::write(path,message);}
  std::process::exit(74)
 }
 fn closed(label:&str,close:SwiftUICloseOutcome)->SwiftRunUsage{
  match close {
   SwiftUICloseOutcome::Clean{usage,..} if fourteen_zero(&usage)=>{
    println!("R3672_CLOSE {label} currents=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] tickets=0 invariant=None");usage
   },
   frozen=>{std::mem::forget(frozen);unknown(label)}
  }
 }
 #[test]
 fn r3672_real_default_and_profile_ui_exports_first_pin_and_events(){unsafe{
  let bytes=fixture();
  for profile in [0u32,1]{
   let raw=if profile==0{mixer_swift_ui_open_v1(bytes.as_ptr(),bytes.len())}else{mixer_swift_ui_open_profile_v1(bytes.as_ptr(),bytes.len(),profile)};
   if raw.is_null(){panic!("actual UI export refused before owner acquisition");}
   let mut error=[0u8;4096];let error_len=mixer_swift_ui_error_v1(raw,error.as_mut_ptr(),error.len());
   let mut frame=[0u8;4];let first=mixer_swift_ui_frame_v1(raw,frame.as_mut_ptr(),frame.len());
   let event=mixer_swift_ui_event_v1(raw,b"x".as_ptr(),1);
   let mut after=[0u8;4];let second=mixer_swift_ui_frame_v1(raw,after.as_mut_ptr(),after.len());
   let mut ledger=[u64::MAX;16];let status=mixer_swift_ui_consume_v1(raw,ledger.as_mut_ptr());
   if status!=1 || ledger!=[0;16]{unknown("actual-ui-export-consume");}
   println!("R3672_CLOSE ABIprofile{profile} currents=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] tickets=0 invariant=None");
   assert_eq!(error_len,0,"{}",String::from_utf8_lossy(&error[..error_len]));assert_eq!(first,4);assert_eq!(&frame,b"PING");assert_eq!(event,0);assert_eq!(second,4);assert_eq!(&after,b"PING");
  }
 }}
 #[test]
 fn r3672_real_capacity_admission_refusal_and_consuming_close(){
  let bytes=fixture();
  for len in [0usize,1,63,64,65,128,255,256,257]{
   let cancellation=Cancellation::default();
   let proof=validate_swift_ui(&bytes,SwiftValidationBudget::default(),&cancellation).ok().expect("valid real UI ABI");
   let mut budget=SwiftRunBudget::default();budget.cache_entries=len;budget.active_pins=len;budget.frames=len;
   let (started,detail,peak)=match PersistentSwiftUIOwner::construct(proof,budget,WasiGrants::default(),WasiBudget::default(),cancellation){
    Ok(mut owner)=>{
     let result=owner.initialize_and_start();let peak=owner.usage().live.active_pins.peak;
     let good=result.as_ref().is_ok_and(|frame|frame==b"PING");let detail=result.err().map(|f|f.code);
     closed(&format!("capacity{len}"),owner.consume());(good,detail,peak)
    },
    Err(failure)=>{let detail=Some(failure.failure.code);closed(&format!("refused-capacity{len}"),failure.close);(false,detail,0)}
   };
   let admitted=matches!(len,1|63|64|256);assert_eq!(started,admitted,"len={len} detail={detail:?}");if admitted{assert!(peak>0);}
   println!("R3672_RUNTIME capacity={len} started={started} detail={detail:?}");
  }
 }
 #[test]
 fn r3672_real_pin_identity_unpin_and_hole_reuse(){
  let bytes=fixture();
  for len in [64usize,256]{
   let mut pins=Vec::with_capacity(len);
   let proof=validate_swift_ui(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).ok().expect("valid UI ABI");
   let mut budget=SwiftRunBudget::default();budget.cache_entries=len;budget.active_pins=len;budget.frames=len;
   let mut owner=match PersistentSwiftUIOwner::construct(proof,budget,WasiGrants::default(),WasiBudget::default(),Cancellation::default()){
    Ok(owner)=>owner,Err(failure)=>{closed("pin-construct-refusal",failure.close);panic!("pin identity constructor refused after clean close");}
   };
   let mut good=true;let mut failure=None;
   {
    let instance=owner.owner.as_mut().unwrap();let cache=instance.cache.as_mut().unwrap();let control=instance.control.as_mut().unwrap();let wasi=instance.wasi.as_ref();
    for slot in 0..len{
     let mut phase=match cache.prepare_operation(control,wasi,Cursor{stage:SwiftRunStage::Cache,function:Some(34),offset:None}){Ok(p)=>p,Err(f)=>{failure=Some(f);break}};
     let mut returned=Some(phase.pin(cache,34));let result=returned.take().unwrap();let completion=phase.complete(returned);
     match result{Ok(pin)=>{good&=pin.slot()==slot;good&=cache.view(&pin,control,wasi).is_ok_and(|v|v.function==34);pins.push(Some(pin));},Err(f)=>{failure=Some(f);break}}
     if let Err(f)=completion{failure=Some(f);break}
    }
    if pins.len()==len && failure.is_none(){
     let hole=len/2;let pin=pins[hole].take().unwrap();let old=(pin.owner(),pin.slot(),pin.nonce());
     if let Err(retained)=cache.release(pin,control,wasi){std::mem::forget(retained);unknown("pin-release-hole");}
     let mut phase=match cache.prepare_operation(control,wasi,Cursor{stage:SwiftRunStage::Cache,function:Some(34),offset:None}){Ok(p)=>p,Err(_)=>unknown("pin-reuse-prepare")};
     let mut returned=Some(phase.pin(cache,34));let result=returned.take().unwrap();let completion=phase.complete(returned);
     match result{Ok(pin)=>{good&=(pin.owner(),pin.slot())==(old.0,old.1)&&pin.nonce()!=old.2;pins[hole]=Some(pin);},Err(f)=>failure=Some(f)}
     if let Err(f)=completion{failure=Some(f);}
     for (slot,pin)in pins.iter().enumerate(){if let Some(pin)=pin{good&=pin.slot()==slot&&pin.owner()==old.0;good&=cache.view(pin,control,wasi).is_ok_and(|v|v.function==34);}}
    }
    for pin in pins.into_iter().flatten(){if let Err(retained)=cache.release(pin,control,wasi){std::mem::forget(retained);unknown("pin-release-all");}}
   }
   let no_live_pins=owner.usage().live.active_pins.current==0;
   closed(&format!("identity{len}"),owner.consume());
   assert!(failure.is_none(),"{failure:?}");assert!(good&&no_live_pins);
   println!("R3672_RUNTIME actual_pin_identity capacity={len} stable=true nonce_renewed=true unpinned_all=true");
  }
 }
}
