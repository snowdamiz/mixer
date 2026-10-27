use super::*;
use crate::{Cancellation,Type};
use crate::experimental_swift_reactor::{validate_swift_reactor,SwiftValidationBudget};
use crate::experimental_wasi::{WasiFunction,WasiBudget,WasiGrants};
use std::cell::{Cell,RefCell};
use std::time::Instant;
use std::io::{Read,Seek,Write};
use std::fs::OpenOptions;
thread_local! { static COUNTERS:Cell<[u64;5]>=Cell::new([0;5]); static FAULT:Cell<u32>=Cell::new(0); static SAVED_LIMIT:Cell<usize>=Cell::new(0); static SAVED:RefCell<Option<ReservationTicket>>=RefCell::new(None); }
pub(super) fn mark(n:usize) {COUNTERS.with(|v|{let mut a=v.get();a[n]+=1;v.set(a)});}
pub(super) fn boundary(n:u32,control:&mut RuntimeControl,cache:Option<&mut SwiftFunctionCache>) {
 if n==1 {mark(0);if FAULT.with(Cell::get)==1 {control.cancellation().cancel();}}
 if n==2 {
  match FAULT.with(Cell::get) {
   6=>cache.unwrap().next_nonce=2,
   7=>{SAVED.with(|s|*s.borrow_mut()=cache.unwrap().header.take());},
   _=>{},
  }
 }
}
pub(super) fn phase_boundary(phase:&mut CacheConstructionPhase<'_>) {mark(1);if matches!(FAULT.with(Cell::get),4|45) {phase.constructed=true;}
 #[cfg(test)] if matches!(FAULT.with(Cell::get),46|47) {let limit=phase.control.control.usage(None).reservations.combined.current+95152;let previous=phase.control.control.test_replace_combined_limit(limit);SAVED_LIMIT.with(|s|s.set(previous));}
}
pub(super) fn completion_boundary(_phase:&mut CacheConstructionPhase<'_>) {mark(2);#[cfg(test)] if matches!(FAULT.with(Cell::get),5|45|47) {SAVED.with(|s|*s.borrow_mut()=_phase.control.control.test_replace_construction(None));}}
fn reset(fault:u32) {FAULT.with(|f|f.set(fault));COUNTERS.with(|v|v.set([0;5]));assert!(SAVED.with(|s|s.borrow().is_none()));}
fn claims()->UnverifiedProfileDigestBytesV1 {UnverifiedProfileDigestBytesV1 {baseline:[1;32],candidate:[2;32],original_input:[3;32],event_schema:[4;32],profile_adapter_binary:[5;32],layout_receipt:[6;32],original_validated_snapshot:[7;32],profile_row_body:[8;32]}}
fn file(name:&str)->File {let p=std::path::Path::new(&std::env::var_os("MIXER_INITIAL_PROFILE_EVIDENCE_DIR").unwrap()).join(name);OpenOptions::new().read(true).write(true).create_new(true).open(p).unwrap()}
fn adopt(budget:SwiftRunBudget)->(RuntimeControl,AdoptedProof) {adopt_count(budget,64)}
fn adopt_count(budget:SwiftRunBudget,count:usize)->(RuntimeControl,AdoptedProof) {let bytes=fixture(0,&[0,0x0b],count);assert!(bytes.len()<=4096);if count==64 {assert_eq!(bytes.len(),1947);}let proof=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();RuntimeControl::adopt(proof,budget,Instant::now(),Cancellation::default()).unwrap()}
fn cleanup(mut cache:Option<SwiftFunctionCache>,mut control:RuntimeControl,result:InitialProfileConstructionOutcomeV1) {
 let mut outcome=None;
 let mut returned_outcome=Some(result);
 match returned_outcome.take().expect("actual returned owner sum") {
  InitialProfileConstructionOutcomeV1::SlotOccupied{adopted}|InitialProfileConstructionOutcomeV1::SelectionRefused{adopted,..}|InitialProfileConstructionOutcomeV1::PreparationFailed{adopted,..}=>{control.drop_proof(adopted).unwrap();},
  InitialProfileConstructionOutcomeV1::ConstructionFailed{failure,..}=>{if let Some(adopted)=failure.rejected_adopted {control.drop_proof(adopted).unwrap();}},
  _=>{},
 }
 if cache.is_some() {SwiftFunctionCache::cleanup(&mut cache,&mut control,None).unwrap().complete((cache,returned_outcome),&mut outcome);}
 let enlarged=control.usage(None).reservations.construction.current;
 let usage=control.finish_owned_cleanup(None);
 if enlarged!=foundation_construction_bytes().unwrap() {
  assert_eq!(usage.reservations.combined.current,enlarged);assert_eq!(usage.reservations.construction.current,enlarged);assert_eq!(usage.reservations.live_tickets,1);assert!(usage.cleanup_invariant.is_some());println!("FAULT_QUARANTINE {:?}",usage);
 } else {assert_eq!(usage.reservations.combined.current,0);assert_eq!(usage.reservations.live_tickets,0);}

}

#[cfg(test)]
pub(super) fn selected_owner_outcome_v1(
 selected: super::super::super::retained_profile_loader_v1::SelectedValidatedProfileV1, case:&str,
) {
 use super::super::super::retained_profile_loader_v1::test_provenance_encoding_v1;
 let expected=test_provenance_encoding_v1(selected.test_provenance_v1());
 if let Some(field)=case.strip_prefix("admission-") {
  let mut budget=BUDGET_RECORDS[0].1;
  let cancellation=Cancellation::default();
  match field {"source"=>budget.source_bytes=0,"metadata"=>budget.metadata_bytes=0,
   "combined"=>budget.combined_bytes=0,"deadline"=>budget.deadline_ms=0,
   "cancelled"=>cancellation.cancel(),"invalid"=>budget.source_bytes+=1,_=>panic!("unknown selected refusal")};
  let started=Instant::now();
  let (result,allocations)=crate::experimental_swift_reactor::allocation_tests::measure(||selected.adopt(budget,started,cancellation));
  let failure=match result {Err(f)=>f,Ok(_)=>panic!("selected admission unexpectedly accepted")};
  let expected_kind=match field {"source"|"metadata"=>SwiftRunFailureKind::Adoption,
   "combined"=>SwiftRunFailureKind::CombinedExhausted,"deadline"=>SwiftRunFailureKind::Deadline,
   "cancelled"=>SwiftRunFailureKind::Cancelled,"invalid"=>SwiftRunFailureKind::InvalidBudget,_=>unreachable!()};
  assert_eq!(failure.kind,expected_kind);assert_eq!(failure.stage,SwiftRunStage::Adoption);
  assert_eq!(failure.at_failure.validation.source_bytes,1947);
  let after=failure.after_cleanup.unwrap();assert_eq!(after.reservations.combined.current,0);
  assert_eq!(after.reservations.live_tickets,0);assert_eq!(after.cleanup_invariant,None);
  assert_eq!(allocations.allocations,0);assert!(allocations.deallocations>0);assert!(allocations.freed_bytes>=1947);
  println!("SELECTED_OUTCOME\t{case}\t0\toriginal_refusal_actual_body_destruction\t{:?}\tfreed={}",failure.kind,allocations.freed_bytes);return;
 }
 let fault=match case {"preparation"=>1,"construction"=>4,"completion"=>5,"header"=>6,"owner"=>7,_=>0};
 reset(fault);
 let (mut control,adopted)=selected.adopt(BUDGET_RECORDS[0].1,Instant::now(),Cancellation::default()).unwrap();
 assert_eq!(test_provenance_encoding_v1(adopted.selected_provenance().unwrap()),expected);
 if case=="occupied" {
  let (mut occupied_control,ordinary)=adopt(BUDGET_RECORDS[0].1);
  let mut cache=None;let mut first=file("selected-occupied-first.rows");
  let result=construct_with_initial_profile_v1(&mut cache,&mut occupied_control,None,ordinary,component_selection(),&claims(),&mut first);
  assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..}));
  reset(0);let mut other=file("selected-occupied-other.rows");
  let returned=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut other);
  match returned {InitialProfileConstructionOutcomeV1::SlotOccupied{adopted}=>{
   assert_eq!(test_provenance_encoding_v1(adopted.selected_provenance().unwrap()),expected);control.drop_proof(adopted).unwrap();
  },_=>panic!("selected occupied owner lost")};
  assert_eq!(COUNTERS.with(Cell::get),[0;5]);assert_eq!(other.metadata().unwrap().len(),0);
  assert_eq!(control.finish_owned_cleanup(None).reservations.combined.current,0);
  cleanup(cache,occupied_control,result);println!("SELECTED_OUTCOME\toccupied\t1\tfull_provenance_retained");return;
 }
 if case=="foreign-control" {
  let (mut foreign,ordinary)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file("selected-foreign.rows");
  let result=construct_with_initial_profile_v1(&mut cache,&mut foreign,None,adopted,component_selection(),&claims(),&mut output);
  match result {InitialProfileConstructionOutcomeV1::PreparationFailed{failure,adopted}=>{
   assert_eq!(failure.kind,SwiftRunFailureKind::Invariant);
   assert_eq!(test_provenance_encoding_v1(adopted.selected_provenance().unwrap()),expected);control.drop_proof(adopted).unwrap();
  },_=>panic!("selected foreign proof not returned")};
  foreign.drop_proof(ordinary).unwrap();
  assert_eq!(foreign.finish_owned_cleanup(None).reservations.combined.current,0);
  assert_eq!(control.finish_owned_cleanup(None).reservations.combined.current,0);
  println!("SELECTED_OUTCOME\tforeign-control\t3\tfull_provenance_retained");return;
 }
 let mut selection=alternative(BUDGET_RECORDS[0].1);
 if case=="selection" {selection.local.entries-=1;}
 let mut cache=None;let mut output=file(&format!("selected-{case}.rows"));
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,&selection,&claims(),&mut output);
 let variant=match (&result,case) {
  (InitialProfileConstructionOutcomeV1::SelectionRefused{adopted,..},"selection")=>{
   assert_eq!(test_provenance_encoding_v1(adopted.selected_provenance().unwrap()),expected);2},
  (InitialProfileConstructionOutcomeV1::PreparationFailed{failure,adopted},"preparation")=>{
   assert_eq!(failure.kind,SwiftRunFailureKind::Cancelled);
   assert_eq!(test_provenance_encoding_v1(adopted.selected_provenance().unwrap()),expected);3},
  (InitialProfileConstructionOutcomeV1::ConstructionFailed{failure,completion},"construction")=>{
   assert_eq!(failure.failure.code,"swift_cache_construct_once");assert!(completion.is_ok());
   assert_eq!(test_provenance_encoding_v1(failure.rejected_adopted.as_ref().unwrap().selected_provenance().unwrap()),expected);4},
  (InitialProfileConstructionOutcomeV1::PhaseCompletionFailed{failure},"completion")=>{assert_eq!(failure.code,"swift_run_missing_construction");5},
  (InitialProfileConstructionOutcomeV1::HeaderRefused{error},"header")=>{assert_eq!(error.code,4);6},
  (InitialProfileConstructionOutcomeV1::HeaderOwnerCheckFailed{failure},"owner")=>{assert_eq!(failure.code,"swift_cache_missing_header");7},
  (InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..},"encoded")=>8,
  _=>panic!("selected case outcome mismatch {case}"),
 };
 if let Some(actual)=cache.as_ref() {assert_eq!(test_provenance_encoding_v1(actual.adopted.selected_provenance().unwrap()),expected);}
 let chronology=match case {"selection"=>[0;5],"preparation"=>[1,0,0,0,0],
  "encoded"=>[1,1,1,1,1],_=>[1,1,1,0,0]};
 assert_eq!(COUNTERS.with(Cell::get),chronology);
 if case=="completion" {let ticket=SAVED.with(|s|s.borrow_mut().take());assert!(control.test_replace_construction(ticket).is_none());}
 if case=="header" {cache.as_mut().unwrap().next_nonce=1;}
 if case=="owner" {cache.as_mut().unwrap().header=SAVED.with(|s|s.borrow_mut().take());}
 if case!="encoded" {assert_eq!(output.metadata().unwrap().len(),0);}
 println!("SELECTED_OUTCOME\t{case}\t{variant}\tfull_provenance_retained");
 cleanup(cache,control,result);
}
fn uint(mut n: u32, out: &mut Vec<u8>) {
    loop {
        let byte = (n & 127) as u8;
        n >>= 7;
        out.push(byte | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return;
        }
    }
}
fn text(s: &[u8], out: &mut Vec<u8>) {
    uint(s.len() as u32, out);
    out.extend_from_slice(s);
}
fn section(id: u8, payload: &[u8], out: &mut Vec<u8>) {
    out.push(id);
    uint(payload.len() as u32, out);
    out.extend_from_slice(payload);
}
fn ty(t: Type) -> u8 {
    match t {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
fn signature(params: &[Type], results: &[Type], out: &mut Vec<u8>) {
    out.push(0x60);
    uint(params.len() as u32, out);
    out.extend(params.iter().copied().map(ty));
    uint(results.len() as u32, out);
    out.extend(results.iter().copied().map(ty));
}
fn fixture(params: usize, helper: &[u8], definitions: usize) -> Vec<u8> {
    assert!(definitions >= 29);
    let mut module = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![37];
    for import in WasiFunction::ALL {
        signature(import.parameters(), import.results(), &mut types);
    }
    signature(&[], &[], &mut types);
    signature(&[], &[Type::I32], &mut types);
    signature(&vec![Type::I32; params], &[], &mut types);
    section(1, &types, &mut module);
    let mut imports = vec![34];
    for (index, import) in WasiFunction::ALL.into_iter().enumerate() {
        text(b"wasi_snapshot_preview1", &mut imports);
        text(import.name(), &mut imports);
        imports.push(0);
        uint(index as u32, &mut imports);
    }
    section(2, &imports, &mut module);
    let mut functions = Vec::new();
    uint(definitions as u32, &mut functions);
    for index in 0..definitions {
        uint(
            if index == 0 {
                36
            } else if index == 28 {
                35
            } else {
                34
            },
            &mut functions,
        );
    }
    section(3, &functions, &mut module);
    let mut table = vec![1, 0x70, 1];
    uint(46713, &mut table);
    uint(46713, &mut table);
    section(4, &table, &mut module);
    let mut memory = vec![1, 0];
    uint(584, &mut memory);
    section(5, &memory, &mut module);
    section(6, &[1, 0x7f, 1, 0x41, 0, 0x0b], &mut module);
    let mut exports = vec![3];
    for (name, kind, index) in [
        (b"memory".as_slice(), 2, 0),
        (b"_initialize".as_slice(), 0, 35),
        (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
    ] {
        text(name, &mut exports);
        exports.push(kind);
        uint(index, &mut exports);
    }
    section(7, &exports, &mut module);
    let mut code = Vec::new();
    uint(definitions as u32, &mut code);
    for index in 0..definitions {
        let body: &[u8] = if index == 0 {
            helper
        } else if index == 28 {
            &[0, 0x41, 0, 0x0b]
        } else {
            &[0, 0x0b]
        };
        uint(body.len() as u32, &mut code);
        code.extend_from_slice(body);
    }
    section(10, &code, &mut module);
    module
}

// Complete explicit finite budget roster, no default/partial updates.
const BUDGET_RECORDS:[(&str,SwiftRunBudget);24]=[
 ("selected-complete17",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-source_bytes",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108863,state_bytes:134217728,values:16384}),
 ("drift-metadata_bytes",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777215,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-cache_bytes",SwiftRunBudget {active_pins:64,cache_bytes:16777215,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-cache_entry_bytes",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388607,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-cache_entries",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:63,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-active_pins",SwiftRunBudget {active_pins:63,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-cache_work",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:63999999,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-frames",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:63,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-values",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16383}),
 ("drift-controls",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4095,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-memory_pages",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:767,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-state_bytes",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217727,values:16384}),
 ("drift-combined_bytes",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435455,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-instruction_fuel",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:99999999,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-execution_work",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:999999999,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-host_calls",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32767,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("drift-deadline_ms",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:29999,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("test-selected-zero-slots",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:0,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("test-selected-zero-pins",SwiftRunBudget {active_pins:0,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("test-selected-entry-zero",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:0,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("test-selected-entry-above-capacity",SwiftRunBudget {active_pins:64,cache_bytes:1048576,cache_entries:64,cache_entry_bytes:2097152,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("test-selected-cache-below-fixed-B",SwiftRunBudget {active_pins:64,cache_bytes:1,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:67108864,state_bytes:134217728,values:16384}),
 ("test-selected-zero-source",SwiftRunBudget {active_pins:64,cache_bytes:16777216,cache_entries:64,cache_entry_bytes:8388608,cache_work:64000000,combined_bytes:268435456,controls:4096,deadline_ms:30000,execution_work:1000000000,frames:64,host_calls:32768,instruction_fuel:100000000,memory_pages:768,metadata_bytes:16777216,source_bytes:0,state_bytes:134217728,values:16384}),
];

pub(super) fn selected_layout_raw_v1() {
 println!("VALUES cleanup={} header={} construction={} operation={} foundation={}",cache_cleanup_temporary_bytes().unwrap(),cache_header_bytes().unwrap(),cache_construction_bytes().unwrap(),cache_operation_bytes().unwrap(),foundation_construction_bytes().unwrap());
 macro_rules! row {($id:literal,$ty:ty)=>{println!("TYPE\t{}\t{}\t{}\t{}",$id,stringify!($ty).replace('\n'," "),size_of::<$ty>(),std::mem::align_of::<$ty>());};}
 row!(1,Result<Option<WasiUsage>, SwiftRunFailure>);
 row!(2,Option<Result<WasiUsage, SwiftRunFailure>>);
 row!(3,Result<WasiUsage, SwiftRunFailure>);
 row!(4,PermanentScalarInventory);
 row!(5,PermanentBorrowChainInventory);
 row!(6,Option<PinRecord>);
 row!(7,Option<&'static PinRecord>);
 row!(8,Option<&'static SwiftSlot>);
 row!(9,Option<&'static DecodedFunction>);
 row!(10,(&'static SwiftFunctionPin, &'static PinRecord));
 row!(11,CacheParts<'static, SwiftMode>);
 row!(12,CacheViewParts<'static, SwiftMode>);
 row!(13,PinRecord);
 row!(14,Result<PinRecord, SwiftRunFailure>);
 row!(15,FunctionView<'static>);
 row!(16,Result<FunctionView<'static>, SwiftRunFailure>);
 row!(17,(SwiftRunFailure, SwiftFunctionPin));
 row!(18,Result<(), (SwiftRunFailure, SwiftFunctionPin)>);
 row!(19,SwiftFunctionPin);
 row!(20,SwiftCacheUsage);
 row!(21,SwiftCacheIdentity);
 row!(22,Option<SwiftFunctionCache>);
 row!(23,SwiftFunctionCache);
 row!(24,Result<CacheCleanupTail<'static>, SwiftRunFailure>);
 row!(25,CacheCleanupTail<'static>);
 row!(26,Option<CacheCleanupTail<'static>>);
 row!(27,CleanupCompletionParts<'static>);
 row!(28,Option<SwiftResident>);
 row!(29,SwiftResident);
 row!(30,DecodedFunction);
 row!(31,Vec<SwiftSlot>);
 row!(32,Vec<PinRecord>);
 row!(33,Vec<decode::Patch>);
 row!(34,Vec<u8>);
 row!(35,Vec<Option<ScanPlan>>);
 row!(36,SwiftScratch<'static>);
 row!(37,Option<ReservationTicket>);
 row!(38,ReservationTicket);
 row!(39,CacheControl<'static>);
 row!(40,SwiftRunFailure);
 row!(41,Option<SwiftRunFailure>);
 row!(42,Result<(), SwiftRunFailure>);
 row!(43,SwiftRunUsage);
 row!(44,Option<WasiUsage>);
 row!(45,Fault);
 row!(46,Cursor);
 row!(47,SwiftReleaseFailure);
 row!(48,Result<(), SwiftReleaseFailure>);
 row!(49,ValidatedSwiftReactor);
 row!(50,Option<ScanPlan>);
 row!(51,Result<CacheConstructionPhase<'static>, SwiftRunFailure>);
 row!(52,Result<ReservationTicket, SwiftRunFailure>);
 row!(53,std::collections::TryReserveError);
 row!(54,Result<(), std::collections::TryReserveError>);
 row!(55,Result<u64, u64>);
 row!(56,Option<u64>);
 row!(57,Result<u64, SwiftRunFailure>);
 row!(58,ConstructionScalarInventory);
 row!(59,ConstructionBorrowChainInventory);
 row!(60,SwiftRunBudget);
 row!(61,(u64, SwiftCacheUsage));
 row!(62,Result<(u64, SwiftCacheUsage), SwiftRunFailure>);
 row!(63,PreparedBounds);
 row!(64,CacheConstructionPhase<'static>);
 row!(65,Partial);
 row!(66,Result<SwiftFunctionCache, CacheConstructionFailure>);
 row!(67,CacheConstructionFailure);
 row!(68,ConstructionReturnSlot);
 row!(69,Option<AdoptedProof>);
 row!(70,PlanInventory);
 row!(71,Result<CacheOperationPhase<'static>, SwiftRunFailure>);
 row!(72,OperationScalarInventory);
 row!(73,ResidentIndexInventory);
 row!(74,ResidentMatch);
 row!(75,Option<ResidentMatch>);
 row!(76,OperationBorrowChainInventory);
 row!(77,(&'static SwiftPolicy<'static>,));
 row!(78,Option<FunctionSpanView<'static>>);
 row!(79,Option<crate::experimental::descriptors::SignatureView<'static>>);
 row!(80,Option<&'static mut DecodedFunction>);
 row!(81,Option<&'static mut crate::experimental::cache::DecodedInstruction>);
 row!(82,[u8; 4]);
 row!(83,[u8; 8]);
 row!(84,Result<[u8; 4], std::array::TryFromSliceError>);
 row!(85,Result<[u8; 8], std::array::TryFromSliceError>);
 row!(86,(&'static mut SwiftMeter<'static, 'static>,));
 row!(87,(&'static u32,));
 row!(88,(&'static SwiftSlot, &'static CacheFields<'static, SwiftMode>));
 row!(89,crate::experimental::descriptors::SignatureView<'static>);
 row!(90,Result<SwiftPolicy<'static>, SwiftRunFailure>);
 row!(91,Result<decode::Counts, SwiftRunFailure>);
 row!(92,Result<usize, SwiftRunFailure>);
 row!(93,Result<u8, SwiftRunFailure>);
 row!(94,Result<u32, SwiftRunFailure>);
 row!(95,Result<i64, SwiftRunFailure>);
 row!(96,Result<crate::Type, SwiftRunFailure>);
 row!(97,Result<&'static [u8], SwiftRunFailure>);
 row!(98,crate::Value);
 row!(99,crate::experimental::cache::Operation);
 row!(100,crate::experimental::cache::DecodedInstruction);
 row!(101,decode::Patch);
 row!(102,Vec<crate::Type>);
 row!(103,Vec<crate::experimental::cache::DecodedInstruction>);
 row!(104,Vec<u32>);
 row!(105,Result<Vec<crate::Type>, SwiftRunFailure>);
 row!(106,Result<Vec<crate::experimental::cache::DecodedInstruction>, SwiftRunFailure>);
 row!(107,Result<Vec<u32>, SwiftRunFailure>);
 row!(108,CacheOperationPhase<'static>);
 row!(109,CacheFields<'static, SwiftMode>);
 row!(110,SwiftMeter<'static, 'static>);
 row!(111,decode::Reader<'static>);
 row!(112,decode::PassParts<'static>);
 row!(113,decode::Counts);
 row!(114,SwiftPolicy<'static>);
 row!(115,[bool; 64]);
 row!(116,Result<SwiftResident, SwiftRunFailure>);
 row!(117,Result<DecodedFunction, SwiftRunFailure>);
 row!(118,Result<SwiftFunctionPin, SwiftRunFailure>);
 row!(119,OperationReturnSlot);
 row!(120,FunctionSpanView<'static>);
 row!(121,RuntimeControl);
 row!(122,AccountedWasi);
 row!(123,AdoptedProof);
 row!(124,SwiftSlot);
 row!(125,ScanPlan);
 row!(126,ProfileHeaderErrorV1);
 row!(127,InitialProfileScalarsV1);
 row!(128,UnverifiedProfileDigestBytesV1);
 row!(129,UnverifiedProfileHeaderV1);
 row!(130,InitialProfileBorrowV1<'static>);
 row!(131,ProfileAdmissionFailureV1);
 row!(132,InitialProfileConstructionOutcomeV1);
 row!(133,Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>);
 row!(134,ProfileRowsObservationV1);
 row!(135,ProfileAdapterErrorV1);
 row!(136,Result<InitialProfileScalarsV1, ProfileHeaderErrorV1>);
 row!(137,Result<UnverifiedProfileHeaderV1, ProfileHeaderErrorV1>);
 row!(138,Result<InitialProfileBorrowV1<'static>, ProfileAdmissionFailureV1>);
 row!(139,Option<InitialProfileConstructionOutcomeV1>);
 row!(140,Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>);
 row!(141,(Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>, ConstructionReturnSlot));
 row!(142,Option<CacheConstructionFailure>);
 row!(143,WrapperArgumentsV1<'static>);
 row!(144,WrapperPhaseStorageV1<'static>);
 row!(145,WrapperEmissionStorageV1<'static>);
 row!(146,WrapperCallerStorageV1);
 row!(147,WrapperMoveStorageV1);
 row!(148,SelectedInitialProfileV1);
 row!(149,SelectedLocalStructureV1);
 row!(150,LocalTypeLayoutV1);
 row!(151,File);
 row!(152,std::fs::Metadata);
 row!(153,std::io::Error);
 row!(154,Result<(), std::io::Error>);
 row!(155,Result<usize, std::io::Error>);
 row!(156,Result<u64, std::io::Error>);
 row!(157,Result<std::fs::Metadata, std::io::Error>);
 row!(158,[u8; 4096]);
 row!(159,[u8; 512]);
 row!(160,Option<AccountedWasi>);
 row!(161,&'static SelectedInitialProfileV1);
 row!(162,&'static mut Option<SwiftFunctionCache>);
 row!(163,&'static mut File);
 row!(164,u64);
 row!(165,usize);
 for (index,(name,bytes,alignment)) in super::super::super::retained_profile_loader_v1::ADOPTION_LAYOUTS_V1.iter().enumerate() {
  println!("TYPE\t{}\t{}\t{}\t{}",166+index,name,bytes,alignment);
 }
 macro_rules! extra {($ty:ty)=>{println!("EXTRA\t{}\t{}\t{}",stringify!($ty).replace('\n'," "),size_of::<$ty>(),std::mem::align_of::<$ty>());};}
 extra!(Result<InitialProfileScalarsV1,ProfileAdmissionFailureV1>);
 extra!(Result<u64,ProfileAdmissionFailureV1>);
 extra!(Result<(),ProfileHeaderErrorV1>);
 extra!([Option<usize>;3]);
 extra!(std::array::IntoIter<Option<usize>,3>);
 extra!(std::slice::Iter<'static,Option<ReservationTicket>>);
 extra!(std::iter::Zip<std::slice::Iter<'static,Option<ReservationTicket>>,std::array::IntoIter<Option<usize>,3>>);
 extra!(std::slice::Iter<'static,SwiftSlot>);
 extra!(std::slice::Iter<'static,PinRecord>);
 extra!(std::slice::Iter<'static,u8>);
 extra!(std::slice::Iter<'static,Option<ScanPlan>>);
 extra!([(usize,u64);13]);
 extra!(std::array::IntoIter<(usize,u64),13>);
 extra!((usize,u64));
 extra!([u8;8]);
 extra!(Option<WasiUsage>);
 extra!(crate::experimental_swift_reactor::SwiftReactorObservations);
 extra!(std::ops::RangeInclusive<usize>);
 extra!(std::ops::RangeInclusive<u64>);
 extra!((&'static Option<ReservationTicket>,Option<usize>));
 extra!(Option<(&'static Option<ReservationTicket>,Option<usize>)>);
 extra!(Option<(usize,u64)>);
 extra!(Option<&'static Option<ScanPlan>>);
 extra!(Option<&'static u8>);
}
#[cfg_attr(test,test)] pub(super) fn selected_layout_and_places() {
 selected_layout_raw_v1();
 #[cfg(test)] assert!(matches!(compare_local_structure_v1(&selected_initial_profile_v1().local),Err(ProfileHeaderErrorV1 {code:6,..})));
 #[cfg(not(test))] compare_local_structure_v1(&selected_initial_profile_v1().local).unwrap_or_else(|e|panic!("layout {}",e.code));

}
#[cfg_attr(test,test)] pub(super) fn fresh_header_rows_and_cleanup() {
 reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file("fresh.rows");
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);
 match &result {InitialProfileConstructionOutcomeV1::HeaderEncoded {header,rows}=>{
  assert!(rows.is_ok(),"{:?}",rows);assert_eq!(&header.bytes[..8],b"MIXPRF01");
  for (offset,value) in [(8,1u64),(16,512),(24,32),(32,80000),(40,cache.as_ref().unwrap().proof().source().len() as u64),(48,37),(56,64),(64,64),(72,1),(80,121264),(88,16777216),(96,8388608)] {assert_eq!(u64::from_le_bytes(header.bytes[offset..offset+8].try_into().unwrap()),value);}
  assert_eq!(&header.bytes[104..128],&[0;24]);assert_eq!(&header.bytes[384..],&[0;128]);for i in 0..8 {assert_eq!(&header.bytes[128+i*32..160+i*32],&[i as u8+1;32]);}
 },_=>panic!("unexpected fresh outcome")}
 assert_eq!(COUNTERS.with(Cell::get),[1,1,1,1,1]);
 assert_eq!(output.stream_position().unwrap(),2560000);output.rewind().unwrap();let mut bytes=Vec::new();output.read_to_end(&mut bytes).unwrap();assert_eq!(bytes.len(),2560000);
 for (i,row) in bytes.chunks_exact(32).enumerate() {
  assert_eq!(&row[24..],&[0;8]);assert_eq!(u32::from_le_bytes(row[..4].try_into().unwrap()),u32::from((34..98).contains(&i)));
  let ty=u32::from_le_bytes(row[4..8].try_into().unwrap());let offset=u64::from_le_bytes(row[8..16].try_into().unwrap());let len=u64::from_le_bytes(row[16..24].try_into().unwrap());
  if (34..98).contains(&i) {let descriptor=cache.as_ref().unwrap().proof().execution_function(i as u32).unwrap();assert_eq!(ty,descriptor.type_index);assert_eq!(offset,descriptor.body_offset as u64);assert_eq!(len,descriptor.body.len() as u64);assert_eq!(ty,if i==34 {36} else if i==62 {35} else {34});assert_eq!(len,if i==62 {4} else {2});}
  else {assert_eq!((ty,offset,len),(u32::MAX,u64::MAX,0));}
 }
 cleanup(cache,control,result);
}
#[cfg_attr(test,test)] pub(super) fn complete17_drift_precedes_prepare() {
 for (id,budget) in &BUDGET_RECORDS[1..18] {
  reset(0);let (mut control,adopted)=if *id=="drift-cache_entries" {adopt_count(*budget,29)} else {adopt(*budget)};let mut cache=None;let mut output=file(&format!("{}.rows",id));
  let before=control.usage(None).reservations;
  let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);
  assert!(matches!(result,InitialProfileConstructionOutcomeV1::SelectionRefused{error:ProfileHeaderErrorV1{code:2,..},..}),"{}",id);assert_eq!(COUNTERS.with(Cell::get),[0;5]);assert_eq!(control.usage(None).reservations,before);assert_eq!(output.metadata().unwrap().len(),0);cleanup(cache,control,result);
 }
}
#[cfg(test)] #[test] fn original_prepare_construct_completion_outcomes() {
 for fault in [1,4,5,6,7,45,46,47] {
  reset(fault);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file(&format!("fault-{}.rows",fault));
  let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);
  match (&result,fault) {
   (InitialProfileConstructionOutcomeV1::PreparationFailed{failure,..},1)=>{assert_eq!(failure.kind,SwiftRunFailureKind::Cancelled);assert_eq!(COUNTERS.with(Cell::get),[1,0,0,0,0]);},
   (InitialProfileConstructionOutcomeV1::ConstructionFailed{failure,completion},4)=>{assert_eq!(failure.failure.code,"swift_cache_construct_once");assert!(failure.rejected_adopted.is_some());assert!(completion.is_ok());assert_eq!(COUNTERS.with(Cell::get),[1,1,1,0,0]);},
   (InitialProfileConstructionOutcomeV1::PhaseCompletionFailed{failure},5)=>{assert_eq!(failure.code,"swift_run_missing_construction");assert!(cache.is_some());},
   (InitialProfileConstructionOutcomeV1::HeaderRefused{error},6)=>{assert_eq!(error.code,4);cache.as_mut().unwrap().next_nonce=1;},
   (InitialProfileConstructionOutcomeV1::HeaderOwnerCheckFailed{failure},7)=>{assert_eq!(failure.code,"swift_cache_missing_header");cache.as_mut().unwrap().header=SAVED.with(|s|s.borrow_mut().take());},
   (InitialProfileConstructionOutcomeV1::ConstructionFailed{failure,completion},45)=>{assert!(failure.rejected_adopted.is_some());assert!(completion.is_err());let nested=completion.as_ref().unwrap_err();assert_eq!(nested.code,failure.failure.code);assert_eq!(nested.attempted,failure.failure.attempted);assert_eq!(nested.at_failure,failure.failure.at_failure);assert_eq!(nested.after_cleanup,None);println!("ORIGINAL_NESTED_FAILURE {:?} {:?}",failure.failure,nested);},
   (InitialProfileConstructionOutcomeV1::ConstructionFailed{failure,completion},46|47)=>{assert!(failure.rejected_adopted.is_none());assert_eq!(failure.failure.kind,SwiftRunFailureKind::CombinedExhausted);assert_eq!(completion.is_ok(),fault==46);assert_eq!(COUNTERS.with(Cell::get),[1,1,1,0,0]);},
   _=>panic!("unexpected fault outcome {}",fault),
  }
  if matches!(fault,5|45|47) {let actual=SAVED.with(|s|s.borrow_mut().take());assert!(control.test_replace_construction(actual).is_none());}
  if matches!(fault,46|47) {let actual=SAVED_LIMIT.with(Cell::get);let _=control.test_replace_combined_limit(actual);}
  assert_eq!(output.metadata().unwrap().len(),0);cleanup(cache,control,result);
 }
}
#[cfg_attr(test,test)] pub(super) fn header_retained_when_actual_row_file_refuses() {
 reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file("nonempty.rows");output.write_all(b"X").unwrap();
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);
 match &result {InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows}=>{assert_eq!(&header.bytes[..8],b"MIXPRF01");assert!(rows.is_err());},_=>panic!("missing retained header")}
 assert_eq!(output.metadata().unwrap().len(),1);assert_eq!(COUNTERS.with(Cell::get),[1,1,1,1,1]);
 if let InitialProfileConstructionOutcomeV1::HeaderEncoded{rows,..}=&result {assert_eq!(*rows,super::super::super::diagnostic_profile::write_profile_row_body_v1(cache.as_ref().unwrap().proof(),&mut output));}
 cleanup(cache,control,result);
 reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let created=file("read-only.rows");drop(created);let path=std::path::Path::new(&std::env::var_os("MIXER_INITIAL_PROFILE_EVIDENCE_DIR").unwrap()).join("read-only.rows");let mut output=File::open(path).unwrap();
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);
 match &result {InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows}=>{assert_eq!(&header.bytes[..8],b"MIXPRF01");assert!(rows.is_err());assert_eq!(*rows,super::super::super::diagnostic_profile::write_profile_row_body_v1(cache.as_ref().unwrap().proof(),&mut output));println!("ACTUAL_READ_ONLY_ROW_FAILURE {:?}",rows);},_=>panic!("real write failure lost header")};assert_eq!(output.metadata().unwrap().len(),0);assert_eq!(output.stream_position().unwrap(),0);cleanup(cache,control,result);
}

#[cfg(test)]
static UNIT_TEST_CONFIG_SELECTION_V1:SelectedInitialProfileV1=SelectedInitialProfileV1 {
 budget:SwiftRunBudget {
  source_bytes:67108864,
  metadata_bytes:16777216,
  cache_bytes:16777216,
  cache_entry_bytes:8388608,
  cache_entries:64,
  active_pins:64,
  cache_work:64000000,
  frames:64,
  values:16384,
  controls:4096,
  memory_pages:768,
  state_bytes:134217728,
  combined_bytes:268435456,
  instruction_fuel:100000000,
  execution_work:1000000000,
  host_calls:32768,
  deadline_ms:30000,
 },
 local:SelectedLocalStructureV1 {
  digest_bytes:32,
  digest_slots:8,
  entries:201,
  header_bytes:512,
  header_error_schema:1,
  header_words:16,
  little_endian:1,
  outcome_variant_schema:1,
  row_bytes:32,
  rows:80000,
  schema:1,
  selected_pins:64,
  selected_slots_max:64,
  trailing_zero_bytes:128,
  word_bytes:8,
  cache_cleanup_bytes:65408,
  cache_header_bytes:95152,
  cache_construction_bytes:69944,
  cache_operation_bytes:92350,
  cache_fixed_at_selected_maxslots:121264,
  type_layout:[
   LocalTypeLayoutV1 {id:1,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:2,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:3,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:4,reserved:0,bytes:240,alignment:8},
   LocalTypeLayoutV1 {id:5,reserved:0,bytes:216,alignment:8},
   LocalTypeLayoutV1 {id:6,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:7,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:8,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:9,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:10,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:11,reserved:0,bytes:112,alignment:8},
   LocalTypeLayoutV1 {id:12,reserved:0,bytes:40,alignment:8},
   LocalTypeLayoutV1 {id:13,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:14,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:15,reserved:0,bytes:64,alignment:8},
   LocalTypeLayoutV1 {id:16,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:17,reserved:0,bytes:1120,alignment:8},
   LocalTypeLayoutV1 {id:18,reserved:0,bytes:1120,alignment:8},
   LocalTypeLayoutV1 {id:19,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:20,reserved:0,bytes:96,alignment:8},
   LocalTypeLayoutV1 {id:21,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:22,reserved:0,bytes:1544,alignment:8},
   LocalTypeLayoutV1 {id:23,reserved:0,bytes:1544,alignment:8},
   LocalTypeLayoutV1 {id:24,reserved:0,bytes:1136,alignment:8},
   LocalTypeLayoutV1 {id:25,reserved:0,bytes:1136,alignment:8},
   LocalTypeLayoutV1 {id:26,reserved:0,bytes:1136,alignment:8},
   LocalTypeLayoutV1 {id:27,reserved:0,bytes:40,alignment:8},
   LocalTypeLayoutV1 {id:28,reserved:0,bytes:120,alignment:8},
   LocalTypeLayoutV1 {id:29,reserved:0,bytes:120,alignment:8},
   LocalTypeLayoutV1 {id:30,reserved:0,bytes:96,alignment:8},
   LocalTypeLayoutV1 {id:31,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:32,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:33,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:34,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:35,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:36,reserved:0,bytes:48,alignment:8},
   LocalTypeLayoutV1 {id:37,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:38,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:39,reserved:0,bytes:48,alignment:8},
   LocalTypeLayoutV1 {id:40,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:41,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:42,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:43,reserved:0,bytes:504,alignment:8},
   LocalTypeLayoutV1 {id:44,reserved:0,bytes:112,alignment:8},
   LocalTypeLayoutV1 {id:45,reserved:0,bytes:64,alignment:8},
   LocalTypeLayoutV1 {id:46,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:47,reserved:0,bytes:1120,alignment:8},
   LocalTypeLayoutV1 {id:48,reserved:0,bytes:1120,alignment:8},
   LocalTypeLayoutV1 {id:49,reserved:0,bytes:664,alignment:8},
   LocalTypeLayoutV1 {id:50,reserved:0,bytes:56,alignment:8},
   LocalTypeLayoutV1 {id:51,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:52,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:53,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:54,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:55,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:56,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:57,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:58,reserved:0,bytes:296,alignment:8},
   LocalTypeLayoutV1 {id:59,reserved:0,bytes:184,alignment:8},
   LocalTypeLayoutV1 {id:60,reserved:0,bytes:136,alignment:8},
   LocalTypeLayoutV1 {id:61,reserved:0,bytes:104,alignment:8},
   LocalTypeLayoutV1 {id:62,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:63,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:64,reserved:0,bytes:64,alignment:8},
   LocalTypeLayoutV1 {id:65,reserved:0,bytes:1432,alignment:8},
   LocalTypeLayoutV1 {id:66,reserved:0,bytes:2312,alignment:8},
   LocalTypeLayoutV1 {id:67,reserved:0,bytes:2312,alignment:8},
   LocalTypeLayoutV1 {id:68,reserved:0,bytes:2312,alignment:8},
   LocalTypeLayoutV1 {id:69,reserved:0,bytes:1216,alignment:8},
   LocalTypeLayoutV1 {id:70,reserved:0,bytes:1304,alignment:8},
   LocalTypeLayoutV1 {id:71,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:72,reserved:0,bytes:760,alignment:8},
   LocalTypeLayoutV1 {id:73,reserved:0,bytes:2456,alignment:8},
   LocalTypeLayoutV1 {id:74,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:75,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:76,reserved:0,bytes:976,alignment:8},
   LocalTypeLayoutV1 {id:77,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:78,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:79,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:80,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:81,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:82,reserved:0,bytes:4,alignment:1},
   LocalTypeLayoutV1 {id:83,reserved:0,bytes:8,alignment:1},
   LocalTypeLayoutV1 {id:84,reserved:0,bytes:5,alignment:1},
   LocalTypeLayoutV1 {id:85,reserved:0,bytes:9,alignment:1},
   LocalTypeLayoutV1 {id:86,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:87,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:88,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:89,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:90,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:91,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:92,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:93,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:94,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:95,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:96,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:97,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:98,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:99,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:100,reserved:0,bytes:40,alignment:8},
   LocalTypeLayoutV1 {id:101,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:102,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:103,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:104,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:105,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:106,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:107,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:108,reserved:0,bytes:56,alignment:8},
   LocalTypeLayoutV1 {id:109,reserved:0,bytes:104,alignment:8},
   LocalTypeLayoutV1 {id:110,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:111,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:112,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:113,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:114,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:115,reserved:0,bytes:64,alignment:1},
   LocalTypeLayoutV1 {id:116,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:117,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:118,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:119,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:120,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:121,reserved:0,bytes:1720,alignment:8},
   LocalTypeLayoutV1 {id:122,reserved:0,bytes:1496,alignment:8},
   LocalTypeLayoutV1 {id:123,reserved:0,bytes:1216,alignment:8},
   LocalTypeLayoutV1 {id:124,reserved:0,bytes:136,alignment:8},
   LocalTypeLayoutV1 {id:125,reserved:0,bytes:48,alignment:8},
   LocalTypeLayoutV1 {id:126,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:127,reserved:0,bytes:64,alignment:8},
   LocalTypeLayoutV1 {id:128,reserved:0,bytes:256,alignment:1},
   LocalTypeLayoutV1 {id:129,reserved:0,bytes:512,alignment:1},
   LocalTypeLayoutV1 {id:130,reserved:0,bytes:88,alignment:8},
   LocalTypeLayoutV1 {id:131,reserved:0,bytes:1104,alignment:8},
   LocalTypeLayoutV1 {id:132,reserved:0,bytes:3416,alignment:8},
   LocalTypeLayoutV1 {id:133,reserved:0,bytes:72,alignment:8},
   LocalTypeLayoutV1 {id:134,reserved:0,bytes:64,alignment:8},
   LocalTypeLayoutV1 {id:135,reserved:0,bytes:32,alignment:8},
   LocalTypeLayoutV1 {id:136,reserved:0,bytes:72,alignment:8},
   LocalTypeLayoutV1 {id:137,reserved:0,bytes:520,alignment:8},
   LocalTypeLayoutV1 {id:138,reserved:0,bytes:1104,alignment:8},
   LocalTypeLayoutV1 {id:139,reserved:0,bytes:3416,alignment:8},
   LocalTypeLayoutV1 {id:140,reserved:0,bytes:1096,alignment:8},
   LocalTypeLayoutV1 {id:141,reserved:0,bytes:3408,alignment:8},
   LocalTypeLayoutV1 {id:142,reserved:0,bytes:2312,alignment:8},
   LocalTypeLayoutV1 {id:143,reserved:0,bytes:1264,alignment:8},
   LocalTypeLayoutV1 {id:144,reserved:0,bytes:8424,alignment:8},
   LocalTypeLayoutV1 {id:145,reserved:0,bytes:5272,alignment:8},
   LocalTypeLayoutV1 {id:146,reserved:0,bytes:14736,alignment:8},
   LocalTypeLayoutV1 {id:147,reserved:0,bytes:18072,alignment:8},
   LocalTypeLayoutV1 {id:148,reserved:0,bytes:5080,alignment:8},
   LocalTypeLayoutV1 {id:149,reserved:0,bytes:4944,alignment:8},
   LocalTypeLayoutV1 {id:150,reserved:0,bytes:24,alignment:8},
   LocalTypeLayoutV1 {id:151,reserved:0,bytes:4,alignment:4},
   LocalTypeLayoutV1 {id:152,reserved:0,bytes:144,alignment:8},
   LocalTypeLayoutV1 {id:153,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:154,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:155,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:156,reserved:0,bytes:16,alignment:8},
   LocalTypeLayoutV1 {id:157,reserved:0,bytes:152,alignment:8},
   LocalTypeLayoutV1 {id:158,reserved:0,bytes:4096,alignment:1},
   LocalTypeLayoutV1 {id:159,reserved:0,bytes:512,alignment:1},
   LocalTypeLayoutV1 {id:160,reserved:0,bytes:1496,alignment:8},
   LocalTypeLayoutV1 {id:161,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:162,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:163,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:164,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:165,reserved:0,bytes:8,alignment:8},
   LocalTypeLayoutV1 {id:166,reserved:0,bytes:1160,alignment:8}, // appended: SelectedValidatedProfileV1
   LocalTypeLayoutV1 {id:167,reserved:0,bytes:496,alignment:8}, // appended: LoaderProvenanceV1
   LocalTypeLayoutV1 {id:168,reserved:0,bytes:160,alignment:8}, // appended: LoaderFailureV1
   LocalTypeLayoutV1 {id:169,reserved:0,bytes:1264,alignment:8}, // appended: LoaderOutcomeV1
   LocalTypeLayoutV1 {id:170,reserved:0,bytes:16,alignment:4}, // appended: ReturnedLoaderFilesV1
   LocalTypeLayoutV1 {id:171,reserved:0,bytes:88,alignment:8}, // appended: LoaderUsageV1
   LocalTypeLayoutV1 {id:172,reserved:0,bytes:64,alignment:8}, // appended: FileIdentityV1
   LocalTypeLayoutV1 {id:173,reserved:0,bytes:168,alignment:8}, // appended: BuildView
   LocalTypeLayoutV1 {id:174,reserved:0,bytes:240,alignment:8}, // appended: SessionView
   LocalTypeLayoutV1 {id:175,reserved:0,bytes:41056,alignment:8}, // appended: ProcessObservationV1
   LocalTypeLayoutV1 {id:176,reserved:0,bytes:16392,alignment:8}, // appended: BytesProcess
   LocalTypeLayoutV1 {id:177,reserved:0,bytes:4104,alignment:8}, // appended: BytesPath
   LocalTypeLayoutV1 {id:178,reserved:0,bytes:1536,alignment:8}, // appended: EnvironmentEntries
   LocalTypeLayoutV1 {id:179,reserved:0,bytes:1160,alignment:8}, // appended: ResultSelected
   LocalTypeLayoutV1 {id:180,reserved:0,bytes:664,alignment:8}, // appended: ValidationResult
   LocalTypeLayoutV1 {id:181,reserved:0,bytes:24,alignment:8}, // appended: VecHeader
   LocalTypeLayoutV1 {id:182,reserved:0,bytes:4,alignment:4}, // appended: File
   LocalTypeLayoutV1 {id:183,reserved:0,bytes:4,alignment:4}, // appended: OptionFile
   LocalTypeLayoutV1 {id:184,reserved:0,bytes:40,alignment:8}, // appended: ValidationBudget
   LocalTypeLayoutV1 {id:185,reserved:0,bytes:136,alignment:8}, // appended: ValidationFailure
   LocalTypeLayoutV1 {id:186,reserved:0,bytes:182360,alignment:8}, // appended: ObservationPlaces
   LocalTypeLayoutV1 {id:187,reserved:0,bytes:14328,alignment:8}, // appended: LoaderPlaces
   LocalTypeLayoutV1 {id:188,reserved:0,bytes:968,alignment:8}, // appended: ReadHashPlaces
   LocalTypeLayoutV1 {id:189,reserved:0,bytes:1168,alignment:8}, // appended: AdoptionBodyV1
   LocalTypeLayoutV1 {id:190,reserved:0,bytes:504,alignment:8}, // appended: OptionalProvenance
   LocalTypeLayoutV1 {id:191,reserved:0,bytes:8,alignment:8}, // appended: BorrowedProvenance
   LocalTypeLayoutV1 {id:192,reserved:0,bytes:7584,alignment:8}, // appended: AdoptionEntryPlacesV1
   LocalTypeLayoutV1 {id:193,reserved:0,bytes:21768,alignment:8}, // appended: AdoptionMovePlacesV1
   LocalTypeLayoutV1 {id:194,reserved:0,bytes:2936,alignment:8}, // appended: AdoptionPair
   LocalTypeLayoutV1 {id:195,reserved:0,bytes:2936,alignment:8}, // appended: AdoptionResult
   LocalTypeLayoutV1 {id:196,reserved:0,bytes:2936,alignment:8}, // appended: OptionalAdoptionPair
   LocalTypeLayoutV1 {id:197,reserved:0,bytes:8,alignment:8}, // appended: BorrowedAdoptionBody
   LocalTypeLayoutV1 {id:198,reserved:0,bytes:8,alignment:8}, // appended: BorrowedSelectedCarrier
   LocalTypeLayoutV1 {id:199,reserved:0,bytes:1304,alignment:8}, // appended: FinalRecheckPlacesV1
   LocalTypeLayoutV1 {id:200,reserved:0,bytes:12600,alignment:8}, // appended: AdoptionCleanupPlacesV1
   LocalTypeLayoutV1 {id:201,reserved:0,bytes:496,alignment:1}, // appended: FullProvenanceEncoding

  ],
 },
};
fn component_selection()->&'static SelectedInitialProfileV1 {
 #[cfg(test)] { &UNIT_TEST_CONFIG_SELECTION_V1 }
 #[cfg(not(test))] {selected_initial_profile_v1()}
}
fn alternative(budget:SwiftRunBudget)->SelectedInitialProfileV1 {let local=&component_selection().local;SelectedInitialProfileV1 {budget,local:SelectedLocalStructureV1 {
digest_bytes:local.digest_bytes,
digest_slots:local.digest_slots,
entries:local.entries,
header_bytes:local.header_bytes,
header_error_schema:local.header_error_schema,
header_words:local.header_words,
little_endian:local.little_endian,
outcome_variant_schema:local.outcome_variant_schema,
row_bytes:local.row_bytes,
rows:local.rows,
schema:local.schema,
selected_pins:local.selected_pins,
selected_slots_max:local.selected_slots_max,
trailing_zero_bytes:local.trailing_zero_bytes,
word_bytes:local.word_bytes,
cache_cleanup_bytes:local.cache_cleanup_bytes,
cache_header_bytes:local.cache_header_bytes,
cache_construction_bytes:local.cache_construction_bytes,
cache_operation_bytes:local.cache_operation_bytes,
cache_fixed_at_selected_maxslots:local.cache_fixed_at_selected_maxslots,
type_layout:std::array::from_fn(|i|{let e=&local.type_layout[i];LocalTypeLayoutV1{id:e.id,reserved:e.reserved,bytes:e.bytes,alignment:e.alignment}}),}}}

#[cfg_attr(test,test)] pub(super) fn same_control_wasi_and_unrelated_owners() {
 reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);
 let state=control.admit(SwiftReservationCategory::State,1,CONSTRUCTION_CURSOR_V1).unwrap();
 let zero=control.admit(SwiftReservationCategory::Cache,0,CONSTRUCTION_CURSOR_V1).unwrap();
 let mut phase=AccountedWasi::prepare(&mut control,CONSTRUCTION_CURSOR_V1).unwrap();
 let wasi=phase.construct(WasiGrants::default(),WasiBudget {one_transfer_bytes:64,log_bytes:64,..WasiBudget::default()},Instant::now(),CONSTRUCTION_CURSOR_V1).unwrap();phase.complete().unwrap();
 let mut cache=None;let mut output=file("same-wasi.rows");
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,Some(&wasi),adopted,component_selection(),&claims(),&mut output);
 assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..}));
 assert_eq!(control.usage(Some(wasi.usage())).reservations.state.current,1);
 let mut failed=None;SwiftFunctionCache::cleanup(&mut cache,&mut control,Some(&wasi)).unwrap().complete((cache,result),&mut failed);
 assert!(failed.is_none());control.drop_reserved((),zero).unwrap();control.drop_reserved((),state).unwrap();wasi.cleanup(&mut control).unwrap();
 let usage=control.finish_owned_cleanup(None);assert_eq!(usage.reservations.combined.current,0);assert_eq!(usage.reservations.live_tickets,0);
}
#[cfg_attr(test,test)] pub(super) fn explicit_narrowed_budgets() {
 for (id,budget) in &BUDGET_RECORDS[18..24] {
  reset(0);let selection=alternative(*budget);
  if *id=="test-selected-zero-source" {
   let bytes=fixture(0,&[0,0x0b],64);let proof=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();
   let failure=match RuntimeControl::adopt(proof,*budget,Instant::now(),Cancellation::default()) {Err(f)=>f,Ok(_)=>panic!("source zero adopted")};assert_eq!(failure.kind,SwiftRunFailureKind::Adoption);assert_eq!(failure.code,"swift_run_category_capacity");assert_eq!(failure.resource,Some(SwiftRunResource::Reservation(SwiftReservationCategory::RetainedSource)));continue;
  }
  let (mut control,adopted)=adopt(*budget);let mut cache=None;let mut output=file(&format!("{}.rows",id));
  let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,&selection,&claims(),&mut output);
  match *id {
   "test-selected-zero-slots"|"test-selected-zero-pins"=>assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderRefused{error:ProfileHeaderErrorV1{code:5,..}})),
   "test-selected-entry-zero"|"test-selected-entry-above-capacity"=>assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..})),
   "test-selected-cache-below-fixed-B"=>assert!(matches!(&result,InitialProfileConstructionOutcomeV1::ConstructionFailed{failure:CacheConstructionFailure{rejected_adopted:None,..},completion:Ok(())})),
   _=>panic!("unclosed narrowed record"),
  }
  cleanup(cache,control,result);
 }
}
#[cfg_attr(test,test)] pub(super) fn all64_slot_pin_pairs_checked() {
 let mut output=file("all-pairs-refused-row-output.rows");output.write_all(b"X").unwrap();
 for slots in 1..=64 {for pins in 1..=64 {
  reset(0);
  let budget=SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:slots,active_pins:pins,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000};
  let selection=alternative(budget);let (mut control,adopted)=adopt(budget);let mut cache=None;
  let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,&selection,&claims(),&mut output);
  match &result {InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows}=>{
   assert!(rows.is_err());assert_eq!(u64::from_le_bytes(header.bytes[56..64].try_into().unwrap()),slots as u64);assert_eq!(u64::from_le_bytes(header.bytes[64..72].try_into().unwrap()),pins as u64);
   let expected=95152+slots*size_of::<SwiftSlot>()+pins*size_of::<PinRecord>()+512*size_of::<decode::Patch>();
   assert_eq!(u64::from_le_bytes(header.bytes[80..88].try_into().unwrap()),expected as u64);assert_eq!(control.usage(None).reservations.cache.current,expected);
  },_=>panic!("pair refused {slots}/{pins}")};cleanup(cache,control,result);
 }}
 assert_eq!(output.metadata().unwrap().len(),1);
 println!("4096 actual fresh constructor/header/row-admission/owner-cleanup pairs");
}
#[cfg_attr(test,test)] pub(super) fn local_structure_refusals() {
 for fault in 0..14 {
  let mut selection=alternative(BUDGET_RECORDS[0].1);
  match fault {0=>selection.local.type_layout[0].bytes+=1,1=>selection.local.type_layout[0].alignment+=1,2=>selection.local.type_layout[0].id+=1,3=>selection.local.entries-=1,4=>selection.local.schema+=1,5=>selection.local.little_endian=0,6=>selection.local.word_bytes=4,7=>selection.local.cache_cleanup_bytes+=1,8=>selection.local.cache_header_bytes+=1,9=>selection.local.cache_construction_bytes+=1,10=>selection.local.cache_operation_bytes+=1,11=>selection.local.cache_fixed_at_selected_maxslots+=1,12=>selection.local.type_layout[0].reserved=1,13=>selection.local.header_error_schema+=1,_=>unreachable!()}
  assert!(matches!(compare_local_structure_v1(&selection.local),Err(ProfileHeaderErrorV1{code:6,..})));
  reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file(&format!("local-{fault}.rows"));
  let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,&selection,&claims(),&mut output);
  assert!(matches!(&result,InitialProfileConstructionOutcomeV1::SelectionRefused{error:ProfileHeaderErrorV1{code:6,..},..}));assert_eq!(COUNTERS.with(Cell::get),[0;5]);cleanup(cache,control,result);
 }
}

#[cfg(test)] #[test] fn occupancy_foreign_proof_and_prepare_failures() {
 reset(0);let (mut a,adopted_a)=adopt(BUDGET_RECORDS[0].1);let (mut b,adopted_b)=adopt(BUDGET_RECORDS[0].1);
 let mut cache=None;let mut first=file("occupied-first.rows");let first_result=construct_with_initial_profile_v1(&mut cache,&mut a,None,adopted_a,component_selection(),&claims(),&mut first);
 assert!(matches!(&first_result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..}));
 let identity=cache.as_ref().unwrap().identity();let usage=cache.as_ref().unwrap().usage;let reservations=a.usage(None).reservations;
 reset(0);let mut invalid_selection=alternative(BUDGET_RECORDS[0].1);invalid_selection.local.entries=0;let mut other=file("occupied-second.rows");
 let returned=construct_with_initial_profile_v1(&mut cache,&mut a,None,adopted_b,&invalid_selection,&claims(),&mut other);
 assert_eq!(COUNTERS.with(Cell::get),[0;5]);assert_eq!(cache.as_ref().unwrap().identity(),identity);assert_eq!(cache.as_ref().unwrap().usage,usage);assert_eq!(a.usage(None).reservations,reservations);assert_eq!(other.metadata().unwrap().len(),0);assert_eq!(first.stream_position().unwrap(),2560000);
 match returned {InitialProfileConstructionOutcomeV1::SlotOccupied{adopted}=>b.drop_proof(adopted).unwrap(),_=>panic!("occupied owner lost")};assert_eq!(b.finish_owned_cleanup(None).reservations.combined.current,0);cleanup(cache,a,first_result);
 // A foreign adopted owner is returned and cleaned only by B. A retains its
 // original adopted proof throughout the failed pairing.
 reset(0);let (mut a,own_a)=adopt(BUDGET_RECORDS[0].1);let (mut b,foreign)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file("foreign-adopted.rows");let before=a.usage(None).reservations;
 let result=construct_with_initial_profile_v1(&mut cache,&mut a,None,foreign,component_selection(),&claims(),&mut output);
 match result {InitialProfileConstructionOutcomeV1::PreparationFailed{failure,adopted}=>{assert_eq!(failure.kind,SwiftRunFailureKind::Invariant);assert_eq!(failure.stage,SwiftRunStage::Initialization);assert_eq!(failure.function,None);assert_eq!(failure.offset,None);assert_eq!(failure.at_failure.reservations,before);println!("ORIGINAL_FOREIGN_PREPARE {:?}",failure);b.drop_proof(adopted).unwrap();},_=>panic!("foreign preparation not retained")};
 assert_eq!(COUNTERS.with(Cell::get),[1,0,0,0,0]);a.drop_proof(own_a).unwrap();assert_eq!(a.finish_owned_cleanup(None).reservations.combined.current,0);assert_eq!(b.finish_owned_cleanup(None).reservations.combined.current,0);
 reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);control.test_expire_deadline();let mut cache=None;let mut output=file("expired-prepare.rows");
 let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);assert!(matches!(&result,InitialProfileConstructionOutcomeV1::PreparationFailed{failure:SwiftRunFailure{kind:SwiftRunFailureKind::Deadline,..},..}));assert_eq!(COUNTERS.with(Cell::get),[1,0,0,0,0]);cleanup(cache,control,result);
}
#[cfg(test)] #[test] fn authentic_owner_and_every_initial_field() {
 reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file("state-controls.rows");let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);
 assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..}));
 let c=cache.as_mut().unwrap();
 macro_rules! scalar {($field:ident,$value:expr)=>{{let original=c.$field;c.$field=$value;assert!(inspect_initial_v1(c,&mut control,None).is_err());c.$field=original;}};}
 scalar!(next_nonce,2);scalar!(owner,0);
 let u=c.usage;
 macro_rules! usage {($($field:ident),+)=>{$(c.usage=u;c.usage.$field+=1;assert!(inspect_initial_v1(c,&mut control,None).is_err(),stringify!($field));)+c.usage=u;};}
 usage!(fixed_reserved,resident_bytes,pinned_bytes,construction_bytes,peak_resident_bytes,peak_pinned_bytes,peak_construction_bytes,active_pins,hits,misses,decodes,evictions);
 c.slots[0].pins=1;assert!(inspect_initial_v1(c,&mut control,None).is_err());c.slots[0].pins=0;c.slots[0].last_used=1;assert!(inspect_initial_v1(c,&mut control,None).is_err());c.slots[0].last_used=0;
 c.pins[0].nonce=1;assert!(inspect_initial_v1(c,&mut control,None).is_err());c.pins[0].nonce=0;c.pins[0].entry=1;assert!(inspect_initial_v1(c,&mut control,None).is_err());c.pins[0].entry=0;
 c.index[0]=1;assert!(inspect_initial_v1(c,&mut control,None).is_err());c.index[0]=0;
 c.plans[0]=Some(ScanPlan{function:34,body_offset:0,body_len:0,type_index:0,counts:decode::Counts::default()});assert!(inspect_initial_v1(c,&mut control,None).is_err());c.plans[0]=None;
 macro_rules! vector {($field:ident)=>{{let actual=std::mem::replace(&mut c.$field,Vec::new());assert!(inspect_initial_v1(c,&mut control,None).is_err());c.$field=actual;}};}
 vector!(slots);vector!(pins);vector!(patches);vector!(index);vector!(plans);
 // Capacity is distinct from length. Each deliberate host fault holds and
 // restores the actual original backing storage before engine cleanup.
 macro_rules! capacity {($field:ident,$len:expr,$value:expr)=>{{let actual=std::mem::replace(&mut c.$field,Vec::with_capacity($len+1));c.$field.resize_with($len,$value);assert!(inspect_initial_v1(c,&mut control,None).is_err());c.$field=actual;}};}
 capacity!(slots,64,||SwiftSlot{resident:None,pins:0,last_used:0});capacity!(pins,64,PinRecord::default);capacity!(patches,PATCH_CAPACITY,||decode::EMPTY_PATCH);capacity!(index,RESIDENT_INDEX_BYTES,||0);capacity!(plans,PLAN_CAPACITY,||None);
 let positive=control.admit(SwiftReservationCategory::Cache,1,CONSTRUCTION_CURSOR_V1).unwrap();assert!(matches!(inspect_initial_v1(c,&mut control,None),Err(ProfileAdmissionFailureV1::Refused(ProfileHeaderErrorV1{code:7,..}))));control.drop_reserved((),positive).unwrap();
 let zero=control.admit(SwiftReservationCategory::Cache,0,CONSTRUCTION_CURSOR_V1).unwrap();assert!(inspect_initial_v1(c,&mut control,None).is_ok());control.drop_reserved((),zero).unwrap();
 for index in 0..3 {
  let actual=c.buffers[index].take();assert!(inspect_initial_v1(c,&mut control,None).is_err());c.buffers[index]=actual;
  let bad=control.admit(SwiftReservationCategory::State,1,CONSTRUCTION_CURSOR_V1).unwrap();let actual=c.buffers[index].replace(bad);assert!(matches!(inspect_initial_v1(c,&mut control,None),Err(ProfileAdmissionFailureV1::Refused(ProfileHeaderErrorV1{code:3,..}))));let bad=std::mem::replace(&mut c.buffers[index],actual).unwrap();control.drop_reserved((),bad).unwrap();
 }
 // Genuine live admission/decrement leaves its historical peak intact: a
 // later initial-state check must continue to refuse; no peak/ledger repair.
 control.add_live(Live::ActivePins,1,CONSTRUCTION_CURSOR_V1).unwrap();assert!(inspect_initial_v1(c,&mut control,None).is_err());control.remove_live(Live::ActivePins,1).unwrap();assert!(inspect_initial_v1(c,&mut control,None).is_err());
 let bad=control.admit(SwiftReservationCategory::State,92128,CONSTRUCTION_CURSOR_V1).unwrap();let actual=c.header.replace(bad);assert!(matches!(inspect_initial_v1(c,&mut control,None),Err(ProfileAdmissionFailureV1::Refused(ProfileHeaderErrorV1{code:3,..}))));let bad=std::mem::replace(&mut c.header,actual).unwrap();control.drop_reserved((),bad).unwrap();
 // Authentic foreign header/buffer/proof controls restore their exact original
 // storage and drop foreign owners exclusively through the foreign control.
 let (mut foreign,foreign_adopted)=adopt(BUDGET_RECORDS[0].1);
 let ticket=foreign.admit(SwiftReservationCategory::Cache,92128,CONSTRUCTION_CURSOR_V1).unwrap();let actual=c.header.replace(ticket);assert!(matches!(inspect_initial_v1(c,&mut control,None),Err(ProfileAdmissionFailureV1::Runtime(_))));let ticket=std::mem::replace(&mut c.header,actual).unwrap();foreign.drop_reserved((),ticket).unwrap();
 let ticket=foreign.admit(SwiftReservationCategory::Cache,64*size_of::<SwiftSlot>(),CONSTRUCTION_CURSOR_V1).unwrap();let actual=c.buffers[0].replace(ticket);assert!(matches!(inspect_initial_v1(c,&mut control,None),Err(ProfileAdmissionFailureV1::Runtime(_))));let ticket=std::mem::replace(&mut c.buffers[0],actual).unwrap();foreign.drop_reserved((),ticket).unwrap();
 let actual=std::mem::replace(&mut c.adopted,foreign_adopted);assert!(matches!(inspect_initial_v1(c,&mut control,None),Err(ProfileAdmissionFailureV1::Runtime(_))));let foreign_adopted=std::mem::replace(&mut c.adopted,actual);foreign.drop_proof(foreign_adopted).unwrap();assert_eq!(foreign.finish_owned_cleanup(None).reservations.combined.current,0);
 cleanup(cache,control,result);
}

#[cfg(test)] #[test] fn post_acquire_chronology_cannot_reenter() {
 reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file("chronology-first.rows");let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..}));
 let before=cache.as_ref().unwrap().usage;
 let mut operation=SwiftFunctionCache::prepare_operation(cache.as_ref().unwrap(),&mut control,None,CONSTRUCTION_CURSOR_V1).unwrap();let mut returned:OperationReturnSlot=Some(operation.pin(cache.as_mut().unwrap(),0));assert!(returned.as_ref().unwrap().is_err());let failed=returned.take().unwrap().unwrap_err();operation.complete(returned).unwrap();println!("ACTUAL_IMPORTED_INDEX_CHRONOLOGY {:?}",failed);assert_eq!(cache.as_ref().unwrap().usage,before);assert_eq!(cache.as_ref().unwrap().next_nonce,1);assert!(inspect_initial_v1(cache.as_ref().unwrap(),&mut control,None).is_ok());
 let (mut other,adopted)=adopt(BUDGET_RECORDS[0].1);let mut second=file("chronology-second.rows");reset(0);let refusal=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut second);match refusal {InitialProfileConstructionOutcomeV1::SlotOccupied{adopted}=>other.drop_proof(adopted).unwrap(),_=>panic!("post-acquire owner reentered")};assert_eq!(COUNTERS.with(Cell::get),[0;5]);assert_eq!(second.metadata().unwrap().len(),0);assert_eq!(other.finish_owned_cleanup(None).reservations.combined.current,0);cleanup(cache,control,result);
}

#[cfg(test)]
const ABOVE_CEILING_RECORDS:[SwiftRunBudget;17]=[
 SwiftRunBudget {source_bytes:67108865,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777217,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777217,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388609,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:65,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:65,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000001,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:65,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16385,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4097,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:769,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217729,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435457,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000001,execution_work:1000000000,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000001,host_calls:32768,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32769,deadline_ms:30000},
 SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30001},
];

#[cfg(test)] #[test] fn canonical_ceilings_and_prepare_capacity() {
 for budget in ABOVE_CEILING_RECORDS {
  assert!(matches!(compare_budget_v1(budget,budget),Err(ProfileHeaderErrorV1{code:2,..})));
  let bytes=fixture(0,&[0,0x0b],64);let proof=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();
  let failure=match RuntimeControl::adopt(proof,budget,Instant::now(),Cancellation::default()) {Err(f)=>f,Ok(_)=>panic!("canonical ceiling accepted")};assert_eq!(failure.kind,SwiftRunFailureKind::InvalidBudget);assert_eq!(failure.stage,SwiftRunStage::Adoption);assert_eq!(failure.function,None);assert_eq!(failure.offset,None);println!("ORIGINAL_CEILING {:?}",failure);
 }
 reset(0);let budget=SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:300000,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000};
 // The original300000 grant now honestly refuses the larger foundation at adoption.
 let bytes=fixture(0,&[0,0x0b],64);let proof=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();
 let refused=match RuntimeControl::adopt(proof,budget,Instant::now(),Cancellation::default()) {Err(f)=>f,Ok(_)=>panic!("old narrow foundation unexpectedly fit")};
 assert_eq!(refused.stage,SwiftRunStage::Adoption);assert_eq!(refused.kind,SwiftRunFailureKind::CategoryExhausted);
 assert_eq!(refused.resource,Some(SwiftRunResource::Reservation(SwiftReservationCategory::Construction)));
 assert_eq!(refused.limit,300000);assert_eq!(refused.attempted,foundation_construction_bytes().unwrap() as u64);
 let after=refused.after_cleanup.unwrap();assert_eq!(after.reservations.combined.current,0);assert_eq!(after.reservations.live_tickets,0);
 assert_eq!(COUNTERS.with(Cell::get),[0;5]);println!("ORIGINAL_NARROWED_FOUNDATION_REFUSAL {:?}",refused);
 // Separate explicit400000 grant admits the new foundation but still refuses preparation.
 let budget=SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:400000,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000};
 let (mut control,adopted)=adopt(budget);let selection=alternative(budget);let mut cache=None;let mut output=file("prepare-capacity.rows");let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,&selection,&claims(),&mut output);
 assert!(matches!(&result,InitialProfileConstructionOutcomeV1::PreparationFailed{failure:SwiftRunFailure{kind:SwiftRunFailureKind::CategoryExhausted,resource:Some(SwiftRunResource::Reservation(SwiftReservationCategory::Construction)),..},..}));assert_eq!(COUNTERS.with(Cell::get),[1,0,0,0,0]);cleanup(cache,control,result);
}
#[cfg(test)] #[test] fn foreign_wasi_prepare_owned_cleanup() {
 reset(0);let (mut a,adopted)=adopt(BUDGET_RECORDS[0].1);let (mut b,own_b)=adopt(BUDGET_RECORDS[0].1);
 let mut phase=AccountedWasi::prepare(&mut b,CONSTRUCTION_CURSOR_V1).unwrap();let wasi=phase.construct(WasiGrants::default(),WasiBudget {one_transfer_bytes:64,log_bytes:64,..WasiBudget::default()},Instant::now(),CONSTRUCTION_CURSOR_V1).unwrap();phase.complete().unwrap();let mut cache=None;let mut output=file("foreign-wasi.rows");
 let result=construct_with_initial_profile_v1(&mut cache,&mut a,Some(&wasi),adopted,component_selection(),&claims(),&mut output);
 assert!(matches!(&result,InitialProfileConstructionOutcomeV1::PreparationFailed{failure:SwiftRunFailure{kind:SwiftRunFailureKind::Invariant,..},..}));assert_eq!(COUNTERS.with(Cell::get),[1,0,0,0,0]);cleanup(cache,a,result);wasi.cleanup(&mut b).unwrap();b.drop_proof(own_b).unwrap();assert_eq!(b.finish_owned_cleanup(None).reservations.combined.current,0);
}
#[cfg(test)] #[test] fn control_live_counts_and_peaks() {
 for (i,resource) in [Live::CacheEntries,Live::ActivePins].into_iter().enumerate() {
  reset(0);let (mut control,adopted)=adopt(BUDGET_RECORDS[0].1);let mut cache=None;let mut output=file(&format!("live-{i}.rows"));let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Ok(_),..}));
  control.add_live(resource,1,CONSTRUCTION_CURSOR_V1).unwrap();assert!(matches!(inspect_initial_v1(cache.as_ref().unwrap(),&mut control,None),Err(ProfileAdmissionFailureV1::Refused(ProfileHeaderErrorV1{code:4,..}))));control.remove_live(resource,1).unwrap();assert!(matches!(inspect_initial_v1(cache.as_ref().unwrap(),&mut control,None),Err(ProfileAdmissionFailureV1::Refused(ProfileHeaderErrorV1{code:4,..}))));let usage=control.usage(None);assert_eq!(if i==0 {usage.live.cache_entries} else {usage.live.active_pins},SwiftReservationUsage{current:0,peak:1});cleanup(cache,control,result);
 }
}

#[cfg(test)] const EXHAUSTION_RECORDS:[(&str,SwiftRunBudget);17]=[
 ("source_bytes",SwiftRunBudget {source_bytes:0,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("metadata_bytes",SwiftRunBudget {source_bytes:67108864,metadata_bytes:0,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("cache_bytes",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:0,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("cache_entry_bytes",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:0,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("cache_entries",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:0,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("active_pins",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:0,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("cache_work",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:0,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("frames",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:0,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("values",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:0,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("controls",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:0,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("memory_pages",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:0,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("state_bytes",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:0,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("combined_bytes",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:0,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("instruction_fuel",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:0,execution_work:1000000000,host_calls:32768,deadline_ms:30000}),
 ("execution_work",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:0,host_calls:32768,deadline_ms:30000}),
 ("host_calls",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:0,deadline_ms:30000}),
 ("deadline_ms",SwiftRunBudget {source_bytes:67108864,metadata_bytes:16777216,cache_bytes:16777216,cache_entry_bytes:8388608,cache_entries:64,active_pins:64,cache_work:64000000,frames:64,values:16384,controls:4096,memory_pages:768,state_bytes:134217728,combined_bytes:268435456,instruction_fuel:100000000,execution_work:1000000000,host_calls:32768,deadline_ms:0}),
];
#[cfg(test)] #[test] fn all17_explicit_exhaustions() {
 for (field,budget) in EXHAUSTION_RECORDS {
  reset(0);let bytes=fixture(0,&[0,0x0b],64);let proof=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();
  let pair=RuntimeControl::adopt(proof,budget,Instant::now(),Cancellation::default());
  if matches!(field,"source_bytes"|"metadata_bytes"|"combined_bytes"|"deadline_ms") {
   let failure=match pair {Err(f)=>f,Ok(_)=>panic!("expected adoption exhaustion {field}")};assert_eq!(failure.stage,SwiftRunStage::Adoption);assert!(failure.after_cleanup.is_some());println!("EXHAUSTION {field} {:?}",failure);continue;
  }
  let (mut control,adopted)=pair.unwrap();let selection=alternative(budget);let mut cache=None;let mut output=file(&format!("exhaust-{field}.rows"));output.write_all(b"X").unwrap();let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,&selection,&claims(),&mut output);
  match field {
   "cache_bytes"|"cache_work"=>assert!(matches!(&result,InitialProfileConstructionOutcomeV1::ConstructionFailed{failure:CacheConstructionFailure{rejected_adopted:None,..},completion:Ok(())})),
   "cache_entries"|"active_pins"=>assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderRefused{error:ProfileHeaderErrorV1{code:5,..}})),
   _=>assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Err(_),..}),"unrelated zero field {field}"),
  }
  assert_eq!(output.metadata().unwrap().len(),1);cleanup(cache,control,result);
 }
}
#[cfg(test)] #[test] fn supported_count_boundary() {
 for definitions in [29,79966,79967] {
  reset(0);let bytes=fixture(0,&[0,0x0b],definitions);assert!(bytes.len()<512000);let validation=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default());
  if definitions==79967 {let failure=match validation {Err(f)=>f,Ok(_)=>panic!("static count policy admitted beyond selected boundary")};assert_eq!(failure.code,"profile_vector_limit");assert_eq!(failure.attempted,79967);assert_eq!(failure.limit,79966);assert_eq!(COUNTERS.with(Cell::get),[0;5]);println!("ORIGINAL_STATIC_COUNT_REFUSAL {:?}",failure);continue;}
  let proof=validation.unwrap();assert_eq!(proof.observations().defined_functions,definitions);assert_eq!(proof.observations().validated_bodies,definitions);println!("SYNTHETIC_COUNT_BOUNDARY definitions={definitions} source={} types={}",bytes.len(),proof.observations().types);
  let (mut control,adopted)=RuntimeControl::adopt(proof,BUDGET_RECORDS[0].1,Instant::now(),Cancellation::default()).unwrap();let mut cache=None;let mut output=file(&format!("count-{definitions}.rows"));output.write_all(b"X").unwrap();let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claims(),&mut output);
  assert!(matches!(&result,InitialProfileConstructionOutcomeV1::HeaderEncoded{rows:Err(_),..}));assert_eq!(COUNTERS.with(Cell::get),[1,1,1,1,1]);
  assert_eq!(output.metadata().unwrap().len(),1);cleanup(cache,control,result);
 }
}
