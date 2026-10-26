// Independent test-only append to the selected new tests.rs; no product code
// changes and no new distribution path. Expected bytes were frozen preaccess.
#[test]
fn independent_preaccess_exact_bytes_and_actual_files() {
 let fixture_dir=std::path::PathBuf::from(std::env::var_os("MIXER_INDEPENDENT_PREACCESS_FIXTURES").unwrap());
 let opaque:Vec<u8>=(0u8..=255).collect();
 let claims=UnverifiedProfileDigestBytesV1 {
  baseline:opaque[0..32].try_into().unwrap(),candidate:opaque[32..64].try_into().unwrap(),
  original_input:opaque[64..96].try_into().unwrap(),event_schema:opaque[96..128].try_into().unwrap(),
  profile_adapter_binary:opaque[128..160].try_into().unwrap(),layout_receipt:opaque[160..192].try_into().unwrap(),
  original_validated_snapshot:opaque[192..224].try_into().unwrap(),profile_row_body:opaque[224..256].try_into().unwrap(),
 };
 for count in [29,67] {for with_wasi in [false,true] {
  reset(0);
  let bytes=std::fs::read(fixture_dir.join(format!("reactor-{count}.wasm"))).unwrap();
  let expected_header=std::fs::read(fixture_dir.join(format!("reactor-{count}.header.bin"))).unwrap();
  let expected_rows=std::fs::read(fixture_dir.join(format!("reactor-{count}.rows.bin"))).unwrap();
  let proof=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();
  let (mut control,adopted)=RuntimeControl::adopt(proof,BUDGET_RECORDS[0].1,Instant::now(),Cancellation::default()).unwrap();
  let state=control.admit(SwiftReservationCategory::State,1,CONSTRUCTION_CURSOR_V1).unwrap();
  let zero=control.admit(SwiftReservationCategory::Cache,0,CONSTRUCTION_CURSOR_V1).unwrap();
  let wasi=if with_wasi {let mut p=AccountedWasi::prepare(&mut control,CONSTRUCTION_CURSOR_V1).unwrap();let w=p.construct(WasiGrants::default(),WasiBudget{one_transfer_bytes:64,log_bytes:64,..WasiBudget::default()},Instant::now(),CONSTRUCTION_CURSOR_V1).unwrap();p.complete().unwrap();Some(w)}else{None};
  let mut cache=None;let name=format!("independent-{count}-{with_wasi}.rows");let mut output=file(&name);
  let result=construct_with_initial_profile_v1(&mut cache,&mut control,wasi.as_ref(),adopted,component_selection(),&claims,&mut output);
  match &result {InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows}=>{assert!(rows.is_ok(),"{rows:?}");assert_eq!(header.bytes.as_slice(),expected_header.as_slice());},_=>panic!("independent fixture/header route failed")};
  assert_eq!(COUNTERS.with(Cell::get),[1,1,1,1,1]);assert_eq!(output.stream_position().unwrap(),2560000);output.rewind().unwrap();let mut physical=Vec::new();output.read_to_end(&mut physical).unwrap();assert_eq!(physical,expected_rows);
  assert_eq!(cache.as_ref().unwrap().proof().source(),bytes.as_slice());
  let mut original_failure=None;SwiftFunctionCache::cleanup(&mut cache,&mut control,wasi.as_ref()).unwrap().complete((cache,result),&mut original_failure);assert!(original_failure.is_none());
  control.drop_reserved((),zero).unwrap();control.drop_reserved((),state).unwrap();if let Some(w)=wasi {w.cleanup(&mut control).unwrap();}
  let final_usage=control.finish_owned_cleanup(None);assert_eq!(final_usage.reservations.combined.current,0);assert_eq!(final_usage.reservations.live_tickets,0);
  println!("INDEPENDENT_EXACT_PREACCESS_BYTES count={count} wasi={with_wasi} header512 rows2560000 cleanup0");
 }}
}
#[test]
fn independent_header_retained_for_four_actual_file_errors() {
 let fixture_dir=std::path::PathBuf::from(std::env::var_os("MIXER_INDEPENDENT_PREACCESS_FIXTURES").unwrap());
 for case in [0,1,2,3] {
  reset(0);let bytes=std::fs::read(fixture_dir.join("reactor-29.wasm")).unwrap();let proof=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).unwrap();let (mut control,adopted)=RuntimeControl::adopt(proof,BUDGET_RECORDS[0].1,Instant::now(),Cancellation::default()).unwrap();
  let name=format!("independent-file-error-{case}.rows");let mut output=file(&name);
  if case==0 {output.write_all(b"X").unwrap();}
  if case==1 {output.seek(std::io::SeekFrom::Start(1)).unwrap();}
  if case==2 {drop(output);let p=std::path::Path::new(&std::env::var_os("MIXER_INITIAL_PROFILE_EVIDENCE_DIR").unwrap()).join(&name);output=File::open(p).unwrap();}
  if case==3 {drop(output);output=File::open(std::env::var_os("MIXER_INITIAL_PROFILE_EVIDENCE_DIR").unwrap()).unwrap();}
  let mut cache=None;let claim=claims();let result=construct_with_initial_profile_v1(&mut cache,&mut control,None,adopted,component_selection(),&claim,&mut output);
  match &result {InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows}=>{
   assert_eq!(&header.bytes[..8],b"MIXPRF01");assert_eq!(&header.bytes[104..128],&[0;24]);assert_eq!(&header.bytes[384..],&[0;128]);
   let direct=super::super::super::diagnostic_profile::write_profile_row_body_v1(cache.as_ref().unwrap().proof(),&mut output);assert!(rows.is_err());assert_eq!(*rows,direct);
   let rendered=format!("{:?}",rows);let code=if case==2{9}else if case==3{6}else{8};assert!(rendered.contains(&format!("code: {code},")),"{rendered}");println!("INDEPENDENT_ACTUAL_FILE_ERROR case={case} {rendered}");
  },_=>panic!("actual File refusal lost header")};
  assert_eq!(COUNTERS.with(Cell::get),[1,1,1,1,1]);cleanup(cache,control,result);
 }
}
