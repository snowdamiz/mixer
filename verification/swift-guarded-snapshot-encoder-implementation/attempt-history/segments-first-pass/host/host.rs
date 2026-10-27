// Fresh component host controls. Omitted from ordinary production builds.
use super::*;
use crate::experimental::swift::snapshot_encoder_v2::*;
#[cfg(not(test))]
use std::sync::atomic::{AtomicBool,AtomicUsize,Ordering};
#[cfg(not(test))]use std::alloc::GlobalAlloc;
#[cfg(not(test))]struct Observer;
#[cfg(not(test))]static COUNT:AtomicUsize=AtomicUsize::new(0);
#[cfg(not(test))]static ACTIVE:AtomicBool=AtomicBool::new(false);
#[cfg(not(test))]unsafe impl std::alloc::GlobalAlloc for Observer{
 unsafe fn alloc(&self,l:std::alloc::Layout)->*mut u8{if ACTIVE.load(Ordering::Relaxed){COUNT.fetch_add(1,Ordering::Relaxed);}std::alloc::System.alloc(l)}
 unsafe fn alloc_zeroed(&self,l:std::alloc::Layout)->*mut u8{if ACTIVE.load(Ordering::Relaxed){COUNT.fetch_add(1,Ordering::Relaxed);}std::alloc::System.alloc_zeroed(l)}
 unsafe fn realloc(&self,p:*mut u8,l:std::alloc::Layout,n:usize)->*mut u8{if ACTIVE.load(Ordering::Relaxed){COUNT.fetch_add(1,Ordering::Relaxed);}std::alloc::System.realloc(p,l,n)}
 unsafe fn dealloc(&self,p:*mut u8,l:std::alloc::Layout){std::alloc::System.dealloc(p,l)}
}
#[cfg(not(test))]#[global_allocator]static ALLOCATOR:Observer=Observer;
fn measured<T>(f:impl FnOnce()->T)->T{
 #[cfg(test)]{let (v,n)=crate::experimental_swift_reactor::allocation_tests::measure(f);assert_eq!(n.allocations,0,"encoder allocation");v}
 #[cfg(not(test))]{COUNT.store(0,Ordering::Relaxed);ACTIVE.store(true,Ordering::Relaxed);let v=f();ACTIVE.store(false,Ordering::Relaxed);assert_eq!(COUNT.load(Ordering::Relaxed),0,"encoder allocation");v}
}
fn action()->String{std::env::var("MIXER_ENCODER_ACTION").unwrap_or_default()}
fn directory()->std::path::PathBuf{std::env::var_os("MIXER_ENCODER_DIR").expect("owned evidence path").into()}
pub(in crate::experimental_swift_reactor::cache::initial_profile_v1) fn observe_v2(initial:&InitialProfileBorrowV1<'_>){
 let action=action();if action!="selected" && action!="ordinary"{return;}
 let view=measured(||borrow_snapshot_v2(initial));
 if action=="ordinary"{assert!(matches!(view,Err(SnapshotEncodeErrorV2::MissingSelectedProvenance)));println!("ENCODER_MISSING_SELECTED_REFUSED");return;}
 let view=view.expect("actual selected guard");
 let mut cursor=measured(||view.into_cursor()).expect("complete fixed header");
 let mut transfer=[0xa5u8;4096];let mut all=Vec::new();let mut blocks=0;
 loop{
  let block=measured(||cursor.next_block(&mut transfer)).expect("actual bounded block");
  let Some(block)=block else{break;};
  assert_eq!(block.offset(),all.len()as u64);assert!(!block.bytes().is_empty()&&block.bytes().len()<=4096);
  if !block.is_final(){assert_eq!(block.bytes().len(),4096);}
  all.extend_from_slice(block.bytes());blocks+=1;
  assert_eq!(cursor.emitted_extent(),all.len()as u64);
 }
 assert_eq!(cursor.encoded_extent(),all.len()as u64);assert_eq!(blocks,(all.len()+4095)/4096);
 assert!(measured(||cursor.next_block(&mut transfer)).unwrap().is_none());
 let p=initial.cache.proof();let s=&initial.scalars;
 let facts=format!("USAGE\t{:?}\nOBS\t{:?}\nRUN\t{:?}\nOWNER\t{}\nSCALARS\t{:?}\nWASI\t{:?}\n{}",
  p.usage(),p.observations(),initial.control.budget(),initial.cache.owner,
  [s.source_extent,s.type_count,s.slot_limit,s.pin_limit,s.initial_nonce,s.cache_base,s.cache_capacity,s.entry_limit],
  initial.wasi.map(AccountedWasi::snapshot_configuration_v2),oracle_inventory_v2(initial));
 std::fs::write(directory().join("actual.mixsnb02"),all).unwrap();
 std::fs::write(directory().join("actual.facts"),facts).unwrap();
 println!("ENCODER_GENUINE_GUARD blocks={blocks} allocation_calls=0");
}
fn selected_entry(){
 use crate::experimental_swift_reactor::retained_profile_loader_v1::load_selected_retained_profile_v1;
 let dir=directory();
 let outcome=load_selected_retained_profile_v1(File::open(dir.join("source.wasm")).unwrap(),File::open(dir.join("build.bin")).unwrap(),
  File::open(dir.join("session.bin")).unwrap(),SwiftValidationBudget::default(),&Cancellation::default());
 let selected=outcome.selected.expect("real retained loader");let expected_source=selected.source().to_vec();
 let (mut control,adopted)=selected.adopt(component_selection().budget,Instant::now(),Cancellation::default()).unwrap();
 let wasi=if std::env::var("MIXER_ENCODER_WASI").unwrap_or_default()=="some"{
  let mut phase=AccountedWasi::prepare(&mut control,CONSTRUCTION_CURSOR_V1).unwrap();
  let value=phase.construct(WasiGrants{secure_random:true,realtime:false,monotonic:true,stdout:true,stderr:false},
   WasiBudget{calls:7,transfer_bytes:128,work:256,one_transfer_bytes:64,iovecs:2,log_bytes:64,deadline_ms:30000},
   Instant::now(),CONSTRUCTION_CURSOR_V1).unwrap();phase.complete().unwrap();Some(value)
 }else{None};
 let mut cache=None;let mut rows=std::fs::OpenOptions::new().read(true).write(true).create_new(true).open(dir.join("primary.rows")).unwrap();
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,wasi.as_ref(),adopted,component_selection(),&claims(),&mut rows);
 match &result{InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows:Ok(_)}=>{
  std::fs::write(dir.join("primary.header"),header.bytes).unwrap();
 },_=>panic!("original primary outcome changed")};
 assert_eq!(cache.as_ref().unwrap().proof().source(),expected_source);
 if let Some(wasi)=wasi{
  let mut failed=None;SwiftFunctionCache::cleanup(&mut cache,&mut control,Some(&wasi)).unwrap().complete((cache,result),&mut failed);
  assert!(failed.is_none());wasi.cleanup(&mut control).unwrap();let usage=control.finish_owned_cleanup(None);
  assert_eq!(usage.reservations.combined.current,0);assert_eq!(usage.reservations.live_tickets,0);
 }else{cleanup(cache,control,result);}
 drop(outcome.files);drop(rows);
 println!("PRIMARY_UNCHANGED header_before_rows consuming_original_cleanup");
}
fn ordinary_entry(){
 let (mut control,adopted)=adopt(component_selection().budget);let mut cache=None;
 let mut rows=std::fs::OpenOptions::new().read(true).write(true).create_new(true).open(directory().join("ordinary.rows")).unwrap();
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut rows);
 assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..}));cleanup(cache,control,result);drop(rows);
}
fn emit(){
 let mut bytes=fixture(0,&[0,0x0b],64);assert_eq!(bytes.len(),1947);
 if std::env::var("MIXER_ENCODER_FIXTURE").unwrap_or_default()=="segments"{
  // Find the code section by reading the existing standard section lengths.
  let mut at=8;
  while at<bytes.len(){let begin=at;let id=bytes[at];at+=1;let mut size=0usize;let mut shift=0;
   loop{let b=bytes[at];at+=1;size|=((b&127)as usize)<<shift;shift+=7;if b&128==0{break;}}
   if id==10{let mut element=Vec::new();section(9,&[1,0,0x41,0,0x0b,1,34],&mut element);bytes.splice(begin..begin,element);break;}
   at+=size;
  }
  section(11,&[1,0,0x41,0,0x0b,3,b'a',b'b',b'c'],&mut bytes);
 }
 validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).expect("genuine new derivative validation");
 std::fs::write(directory().join("fixture.wasm"),&bytes).unwrap();println!("GENUINE_FIXTURE {}",bytes.len());
}
fn layouts(){for (name,bytes,alignment) in snapshot_layouts_v2(){println!("ENCODER_LAYOUT\t{name}\t{bytes}\t{alignment}");}}
fn entry(){match action().as_str(){"emit"=>emit(),"selected"=>selected_entry(),"ordinary"=>ordinary_entry(),"layouts"=>layouts(),_=>panic!("unknown owned action")}}
#[cfg(test)]#[test]fn actual_encoder_child_v2(){entry();}
#[cfg(not(test))]#[no_mangle]pub extern "C" fn mixer_snapshot_encoder_host_v2(){entry();}
