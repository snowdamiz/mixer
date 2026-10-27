// Independent genuine-loader/sole-guard host; absent in default production.
use super::*;
use crate::experimental::swift::{snapshot_encoder_v2::*,independent_snapshot_fields};
#[cfg(not(test))]use std::alloc::GlobalAlloc;
#[cfg(not(test))]struct ReviewAllocator;
#[cfg(not(test))]static ACTIVE:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
#[cfg(not(test))]static CALLS:std::sync::atomic::AtomicUsize=std::sync::atomic::AtomicUsize::new(0);
#[cfg(not(test))]unsafe impl GlobalAlloc for ReviewAllocator{
 unsafe fn alloc(&self,l:std::alloc::Layout)->*mut u8{if ACTIVE.load(std::sync::atomic::Ordering::Relaxed){CALLS.fetch_add(1,std::sync::atomic::Ordering::Relaxed);}std::alloc::System.alloc(l)}
 unsafe fn alloc_zeroed(&self,l:std::alloc::Layout)->*mut u8{if ACTIVE.load(std::sync::atomic::Ordering::Relaxed){CALLS.fetch_add(1,std::sync::atomic::Ordering::Relaxed);}std::alloc::System.alloc_zeroed(l)}
 unsafe fn realloc(&self,p:*mut u8,l:std::alloc::Layout,n:usize)->*mut u8{if ACTIVE.load(std::sync::atomic::Ordering::Relaxed){CALLS.fetch_add(1,std::sync::atomic::Ordering::Relaxed);}std::alloc::System.realloc(p,l,n)}
 unsafe fn dealloc(&self,p:*mut u8,l:std::alloc::Layout){std::alloc::System.dealloc(p,l)}
}
#[cfg(not(test))]#[global_allocator]static ALLOCATOR:ReviewAllocator=ReviewAllocator;
fn measured<T>(f:impl FnOnce()->T)->T{
 #[cfg(test)]{let(v,n)=crate::experimental_swift_reactor::allocation_tests::measure(f);assert_eq!(n.allocations,0);v}
 #[cfg(not(test))]{use std::sync::atomic::Ordering::Relaxed;CALLS.store(0,Relaxed);ACTIVE.store(true,Relaxed);let v=f();ACTIVE.store(false,Relaxed);assert_eq!(CALLS.load(Relaxed),0);v}
}
fn dir()->std::path::PathBuf{std::env::var_os("MIXER_REVIEW_DIR").unwrap().into()}
pub(in crate::experimental_swift_reactor::cache::initial_profile_v1)fn observe_v2(initial:&InitialProfileBorrowV1<'_>){
 let action=std::env::var("MIXER_REVIEW_ACTION").unwrap_or_default();if action.is_empty(){return;}
 let view=measured(||borrow_snapshot_v2(initial));
 if action=="ordinary"{assert!(matches!(view,Err(SnapshotEncodeErrorV2::MissingSelectedProvenance)));println!("INDEPENDENT_MISSING_SELECTED");return;}
 let proof=independent_snapshot_fields(initial);
 let provenance=initial.snapshot_selected_v2().unwrap().independent_provenance_fields();
 let r=initial.control.budget();let s=&initial.scalars;
 let limits=[r.source_bytes as u64,r.metadata_bytes as u64,r.cache_bytes as u64,r.cache_entry_bytes as u64,r.cache_entries as u64,r.active_pins as u64,r.cache_work,r.frames as u64,r.values as u64,r.controls as u64,r.memory_pages as u64,r.state_bytes as u64,r.combined_bytes as u64,r.instruction_fuel,r.execution_work,r.host_calls,r.deadline_ms];
 let scalars=[s.source_extent,s.type_count,s.slot_limit,s.pin_limit,s.initial_nonce,s.cache_base,s.cache_capacity,s.entry_limit];
 let wasi=match initial.wasi.map(AccountedWasi::independent_configuration){None=>"null".to_owned(),Some((w,g))=>format!("{:?}",[w.calls,w.transfer_bytes,w.work,w.one_transfer_bytes as u64,w.iovecs as u64,w.log_bytes as u64,w.deadline_ms,u64::from(g.secure_random),u64::from(g.realtime),u64::from(g.monotonic),u64::from(g.stdout),u64::from(g.stderr)])};
 let facts=format!("{{{proof},{provenance},\"runtime\":{{\"owner\":{},\"limits\":{:?},\"wasi\":{},\"scalars\":{:?}}}}}",initial.cache.owner,limits,wasi,scalars);
 std::fs::write(dir().join("observed.json"),facts).unwrap();
 let mut cursor=measured(||view.unwrap().into_cursor()).unwrap();let mut transfer=[0x69u8;4096];let mut output=Vec::new();let mut blocks=Vec::new();
 let total=cursor.encoded_extent();for number in 0..=((total+4095)/4096){
  transfer.fill(if number%2==0{0x69}else{0x96});let before=cursor.emitted_extent();
  let block=measured(||cursor.next_block(&mut transfer)).unwrap();
  if let Some(block)=block{assert_eq!(block.offset(),before);assert_eq!(block.offset(),output.len()as u64);let n=block.bytes().len();assert!(n>0&&n<=4096);if !block.is_final(){assert_eq!(n,4096);}assert_eq!(block.is_final(),before+n as u64==total);blocks.push((before,n,block.is_final()));output.extend_from_slice(block.bytes());drop(block);assert_eq!(cursor.emitted_extent(),output.len()as u64);assert!(transfer[n..].iter().all(|b|*b==if number%2==0{0x69}else{0x96}));}
  else{assert_eq!(output.len()as u64,total);break;}
 }
 assert_eq!(blocks.len()as u64,(total+4095)/4096);assert!(measured(||cursor.next_block(&mut transfer)).unwrap().is_none());assert!(measured(||cursor.next_block(&mut transfer)).unwrap().is_none());
 std::fs::write(dir().join("actual.mixsnb02"),output).unwrap();std::fs::write(dir().join("blocks.txt"),format!("{:?}",blocks)).unwrap();println!("INDEPENDENT_GUARD_BYTE_STREAM allocation_calls=0 bytes={total}");
}
fn entry(){
 let action=std::env::var("MIXER_REVIEW_ACTION").unwrap_or_default();
 if action=="layouts"{for(n,b,a)in snapshot_layouts_v2(){println!("INDEPENDENT_LAYOUT\t{}\t{}\t{}",n,b,a);}return;}
 let (mut control,adopted,files)=if action=="ordinary"{let(c,a)=adopt(component_selection().budget);(c,a,None)}else{
  use crate::experimental_swift_reactor::retained_profile_loader_v1::load_selected_retained_profile_v1;
  let result=load_selected_retained_profile_v1(File::open(dir().join("source.wasm")).unwrap(),File::open(dir().join("build.bin")).unwrap(),File::open(dir().join("session.bin")).unwrap(),SwiftValidationBudget::default(),&Cancellation::default());let selected=result.selected.expect("independent genuine loader selected proof");let(c,a)=selected.adopt(component_selection().budget,Instant::now(),Cancellation::default()).unwrap();(c,a,Some(result.files))
 };
 let mode=std::env::var("MIXER_REVIEW_WASI").unwrap_or_default();let wasi=if mode=="none"||mode.is_empty(){None}else{
  let mut p=AccountedWasi::prepare(&mut control,CONSTRUCTION_CURSOR_V1).unwrap();let w=if mode=="zero"{WasiBudget{calls:0,transfer_bytes:0,work:0,one_transfer_bytes:0,iovecs:0,log_bytes:0,deadline_ms:30000}}else{WasiBudget{calls:11,transfer_bytes:192,work:512,one_transfer_bytes:96,iovecs:3,log_bytes:128,deadline_ms:30000}};
  let g=if mode=="zero"{WasiGrants::default()}else{WasiGrants{secure_random:false,realtime:true,monotonic:false,stdout:false,stderr:true}};
  let v=p.construct(g,w,Instant::now(),CONSTRUCTION_CURSOR_V1).unwrap();p.complete().unwrap();Some(v)
 };
 let mut cache=None;let mut rows=OpenOptions::new().read(true).write(true).create_new(true).open(dir().join("primary.rows")).unwrap();
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,wasi.as_ref(),adopted,component_selection(),&claims(),&mut rows);
 match &result{InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows:Ok(_)}=>std::fs::write(dir().join("primary.header"),header.bytes).unwrap(),_=>panic!("original primary header/row outcome changed")};
 drop(rows);if let Some(wasi)=wasi{let mut failure=None;SwiftFunctionCache::cleanup(&mut cache,&mut control,Some(&wasi)).unwrap().complete((cache,result),&mut failure);assert!(failure.is_none());wasi.cleanup(&mut control).unwrap();let u=control.finish_owned_cleanup(None);assert_eq!(u.reservations.combined.current,0);assert_eq!(u.reservations.live_tickets,0);}else{cleanup(cache,control,result);}drop(files);println!("INDEPENDENT_PRIMARY_ORIGINAL_OWNERS_CLEANED");
}
#[cfg(test)]#[test]fn independent_encoder_review(){entry();}
#[cfg(not(test))]#[no_mangle]pub extern "C" fn mixer_snapshot_encoder_host_v2(){entry();}
