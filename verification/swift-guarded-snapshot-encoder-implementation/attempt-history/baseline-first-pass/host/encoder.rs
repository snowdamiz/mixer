// Guard-derived logical encoding only. No operational storage/work/IO authority.
use super::*;
use crate::experimental_swift_reactor::{InitialProfileBorrowV1, LoaderProvenanceV1};
use std::mem::{size_of,align_of};
pub(crate) const SNAPSHOT_TRANSFER_BYTES_V2:usize=4096;
const HEADER:usize=2560;
const CAPS:[u64;9]=[67108864,512,8192,34,79966,8192,4096,4096,4096];
const WIDTHS:[u64;9]=[0,3,1,5,3,4,4,4,4];
const NATIVE:[u64;9]=[1,12,1,20,12,12,16,16,16];
const MAXIMUM:u64=69765152;
#[derive(Debug,PartialEq,Eq)]
pub(crate) enum SnapshotEncodeErrorV2 {
 MissingSelectedProvenance,UnsupportedLayout,UnsupportedPolicy,Arithmetic,
 InternalField{code:u32,section:u32,index:u64},
}
pub(crate) struct SnapshotViewV2<'guard>{
 initial:&'guard InitialProfileBorrowV1<'guard>,
 proof:&'guard ValidatedSwiftReactor,provenance:&'guard LoaderProvenanceV1,
}
pub(crate) struct SnapshotCursorV2<'guard>{
 view:SnapshotViewV2<'guard>,header:[u8;HEADER],extent:u64,emitted:u64,
}
pub(crate) struct SnapshotBlockV2<'block>{bytes:&'block[u8],offset:u64,final_block:bool}
impl SnapshotBlockV2<'_>{
 pub(crate) fn bytes(&self)->&[u8]{self.bytes}
 pub(crate) fn offset(&self)->u64{self.offset}
 pub(crate) fn is_final(&self)->bool{self.final_block}
}
fn field(code:u32,section:usize,index:usize)->SnapshotEncodeErrorV2{
 SnapshotEncodeErrorV2::InternalField{code,section:section as u32,index:index as u64}
}
fn require(ok:bool,code:u32,section:usize,index:usize)->Result<(),SnapshotEncodeErrorV2>{
 if ok {Ok(())}else{Err(field(code,section,index))}
}
fn word(n:usize)->Result<u64,SnapshotEncodeErrorV2>{u64::try_from(n).map_err(|_|SnapshotEncodeErrorV2::Arithmetic)}
fn put(h:&mut[u8],at:usize,n:u64){h[at..at+8].copy_from_slice(&n.to_le_bytes());}
fn get(h:&[u8],at:usize)->u64{u64::from_le_bytes(h[at..at+8].try_into().expect("fixed header word"))}
fn words(h:&mut[u8],at:usize,v:&[u64]){for (i,n) in v.iter().enumerate(){put(h,at+i*8,*n);}}
fn optional(v:Option<u32>)->[u64;2]{match v{None=>[0,0],Some(n)=>[1,u64::from(n)]}}
fn type_id(t:Type)->u64{match t{Type::I32=>1,Type::I64=>2,Type::F32=>3,Type::F64=>4}}
fn result_id(t:Option<Type>)->u64{match t{None=>0,Some(t)=>type_id(t)}}
fn wasi_id(t:WasiFunction)->u64{match t{
 WasiFunction::ArgsGet=>1,WasiFunction::ArgsSizesGet=>2,WasiFunction::EnvironGet=>3,
 WasiFunction::EnvironSizesGet=>4,WasiFunction::ClockResGet=>5,WasiFunction::ClockTimeGet=>6,
 WasiFunction::FdClose=>7,WasiFunction::FdFdstatGet=>8,WasiFunction::FdFdstatSetFlags=>9,
 WasiFunction::FdFilestatGet=>10,WasiFunction::FdFilestatSetSize=>11,WasiFunction::FdFilestatSetTimes=>12,
 WasiFunction::FdPread=>13,WasiFunction::FdPrestatGet=>14,WasiFunction::FdPrestatDirName=>15,
 WasiFunction::FdRead=>16,WasiFunction::FdReaddir=>17,WasiFunction::FdSeek=>18,
 WasiFunction::FdSync=>19,WasiFunction::FdTell=>20,WasiFunction::FdWrite=>21,
 WasiFunction::PathCreateDirectory=>22,WasiFunction::PathFilestatGet=>23,
 WasiFunction::PathFilestatSetTimes=>24,WasiFunction::PathLink=>25,WasiFunction::PathOpen=>26,
 WasiFunction::PathReadlink=>27,WasiFunction::PathRemoveDirectory=>28,WasiFunction::PathRename=>29,
 WasiFunction::PathSymlink=>30,WasiFunction::PathUnlinkFile=>31,WasiFunction::PollOneoff=>32,
 WasiFunction::ProcExit=>33,WasiFunction::RandomGet=>34,
}}
pub(crate) fn borrow_snapshot_v2<'guard>(initial:&'guard InitialProfileBorrowV1<'_>)
 ->Result<SnapshotViewV2<'guard>,SnapshotEncodeErrorV2>{
 let provenance=initial.snapshot_selected_v2().ok_or(SnapshotEncodeErrorV2::MissingSelectedProvenance)?;
 Ok(SnapshotViewV2{initial,proof:initial.snapshot_proof_v2(),provenance})
}
impl<'guard> SnapshotViewV2<'guard>{
 pub(crate) fn into_cursor(self)->Result<SnapshotCursorV2<'guard>,SnapshotEncodeErrorV2>{
  if size_of::<usize>()!=8 || !cfg!(target_endian="little") || !cfg!(target_arch="aarch64")
   || size_of::<ValidatedSwiftReactor>()!=664 {return Err(SnapshotEncodeErrorV2::UnsupportedLayout);}
  match self.proof.policy {policy::Policy::SwiftReactorExperimentV1=>(),policy::Policy::Frozen(_)=>return Err(SnapshotEncodeErrorV2::UnsupportedPolicy)}
  let mut h=[0u8;HEADER];h[..8].copy_from_slice(b"MIXSNB02");
  let p=self.proof;let m=&p.metadata;let u=p.usage;let o=p.observations;
  let source=word(p.source.len())?;
  words(&mut h,8,&[2,2560,0,9,1,1,34,source,word(m.instructions)?,8,664]);
  self.provenance.snapshot_encode_v2((&mut h[512..1088]).try_into().expect("fixed provenance region"))
   .map_err(|_|SnapshotEncodeErrorV2::Arithmetic)?;
  for i in 0..5{let n=get(&h,544+i*8);put(&mut h,96+i*8,n);}
  require(get(&h,536)==source && get(&h,792)==source,1,0,0)?;
  words(&mut h,144,&[word(u.input_visible_bytes)?,word(u.source_bytes)?,word(u.metadata_reserved)?,
   word(u.scratch_reserved)?,word(u.metadata_peak_reserved)?,word(u.scratch_peak_reserved)?,
   word(u.total_peak_reserved)?,u.work_used,u.elapsed_micros,u.deadline_ms]);
  let mm=optional(o.memory_declared_maximum);let tm=optional(o.table_declared_maximum);
  words(&mut h,224,&[word(o.types)?,word(o.type_parameters)?,word(o.imported_functions)?,
   word(o.defined_functions)?,word(o.validated_bodies)?,word(o.instructions)?,word(o.globals)?,
   word(o.exports)?,word(o.data_segments)?,word(o.element_segments)?,word(o.max_parameters_plus_locals)?,
   word(o.max_operand_values)?,word(o.max_control_depth)?,u64::from(o.memory_minimum),mm[0],mm[1],
   u64::from(o.memory_host_maximum),u64::from(o.table_minimum),tm[0],tm[1]]);
  let memory=m.memory.ok_or_else(||field(2,0,0))?;let table=m.table.ok_or_else(||field(3,0,0))?;
  let md=optional(m.declarations.memory_maximum);let td=optional(m.declarations.table_maximum);
  words(&mut h,384,&[1,u64::from(memory.0),u64::from(memory.1),1,u64::from(table.0),u64::from(table.1),
   md[0],md[1],td[0],td[1],word(m.declarations.memory_offset)?,word(m.declarations.table_offset)?,word(m.instructions)?]);
  self.initial.snapshot_runtime_v2((&mut h[1088..1600]).try_into().expect("fixed runtime region"))
   .map_err(|_|SnapshotEncodeErrorV2::Arithmetic)?;
  require(u.input_visible_bytes==p.source.len() && u.source_bytes==p.source.len()
   && source<=get(&h,96) && u.deadline_ms==get(&h,128),4,0,0)?;
  let validation_caps=[67108864,16777216,1048576,512000000,120000];
  for (i,cap) in validation_caps.iter().enumerate(){require(get(&h,96+i*8)<=*cap,5,0,i)?;}
  require(o.imported_functions==34 && o.defined_functions==o.validated_bodies
   && o.imported_functions.checked_add(o.defined_functions).is_some_and(|n|n<=80000)
   && o.instructions==m.instructions && m.instructions<=8000000
   && o.max_parameters_plus_locals<=256 && o.max_operand_values<=128 && o.max_control_depth<=512,6,0,0)?;
  require(memory.0==o.memory_minimum && memory.1==o.memory_host_maximum
   && table.0==o.table_minimum && md==mm && td==tm
   && memory.1==m.declarations.memory_maximum.unwrap_or(768)
   && table.1==m.declarations.table_maximum.unwrap_or(65536)
   && memory.0<=memory.1 && memory.1<=768 && table.0<=table.1 && table.1<=65536
   && m.declarations.memory_offset<=p.source.len() && m.declarations.table_offset<=p.source.len(),7,0,0)?;
  let mut at=2560u64;let mut charged=664u64;
  for sid in 0..9{
   let inventory=self.inventory(sid)?;
   let (count,capacity,native,charge,category)=inventory;
   require(count<=CAPS[sid] && count<=capacity && native==NATIVE[sid]
    && capacity.checked_mul(native)==Some(charge) && category==if sid==0{1}else{2},8,sid,0)?;
   let bytes=if sid==0{count}else{count.checked_mul(WIDTHS[sid]*8).ok_or(SnapshotEncodeErrorV2::Arithmetic)?};
   require(charge<=if sid==0{67108864}else{16777216},9,sid,0)?;
   if sid==0{require(count==source && capacity==source && charge==source,10,sid,0)?;}
   else {charged=charged.checked_add(charge).ok_or(SnapshotEncodeErrorV2::Arithmetic)?;
    let observation=[0usize,0,1,2,3,6,7,8,9][sid];
    require(count==get(&h,224+observation*8),11,sid,0)?;}
   words(&mut h,1600+sid*64,&[sid as u64,count,capacity,native,charge,category,at,bytes]);
   at=at.checked_add(bytes).ok_or(SnapshotEncodeErrorV2::Arithmetic)?;
  }
  require(charged==word(u.metadata_reserved)? && charged<=get(&h,104) && at<=MAXIMUM,12,0,0)?;
  for (i,resolved) in p.imports.iter().enumerate(){put(&mut h,2176+i*8,wasi_id(*resolved));}
  validate_runtime(&h,source,word(o.types)?,word(o.defined_functions)?)?;
  put(&mut h,24,at);
  Ok(SnapshotCursorV2{view:self,header:h,extent:at,emitted:0})
 }
 fn inventory(&self,sid:usize)->Result<(u64,u64,u64,u64,u64),SnapshotEncodeErrorV2>{
  if sid==0{let n=word(self.proof.source.len())?;return Ok((n,n,1,word(self.proof.usage.source_bytes)?,1));}
  let m=&self.proof.metadata;
  let (n,c,s,b,r)=match sid{
   1=>m.signatures.snapshot_inventory_v2(),2=>m.parameters.snapshot_inventory_v2(),
   3=>m.imports.snapshot_inventory_v2(),4=>m.functions.snapshot_inventory_v2(),
   5=>m.globals.snapshot_inventory_v2(),6=>m.exports.snapshot_inventory_v2(),
   7=>m.data.snapshot_inventory_v2(),8=>m.elements.snapshot_inventory_v2(),_=>return Err(field(13,sid,0)),
  };
  require(matches!(r,Resource::Metadata),14,sid,0)?;
  Ok((word(n)?,word(c)?,word(s)?,word(b)?,2))
 }
 fn record_word(&self,sid:usize,index:usize,within:usize)->Result<u64,SnapshotEncodeErrorV2>{
  let m=&self.proof.metadata;let source=self.proof.source.len();
  let span=|s:metadata::Span|->Result<(),SnapshotEncodeErrorV2>{
   require((s.offset as usize).checked_add(s.bytes as usize).is_some_and(|end|end<=source),15,sid,index)
  };
  macro_rules! entry{($field:ident)=>{m.$field.get(index).ok_or_else(||field(16,sid,index))?};}
  let v=match sid{
   1=>{let s=entry!(signatures);require((s.first as usize).checked_add(s.count as usize).is_some_and(|n|n<=m.parameters.len()),17,sid,index)?;
    [u64::from(s.first),u64::from(s.count),result_id(s.result),0,0]},
   2=>[type_id(*entry!(parameters)),0,0,0,0],
   3=>{let i=entry!(imports);span(i.module)?;span(i.name)?;require((i.type_index as usize)<m.signatures.len(),18,sid,index)?;
    [u64::from(i.module.offset),u64::from(i.module.bytes),u64::from(i.name.offset),u64::from(i.name.bytes),u64::from(i.type_index)]},
   4=>{let f=entry!(functions);span(f.body)?;require((f.type_index as usize)<m.signatures.len(),18,sid,index)?;
    [u64::from(f.body.offset),u64::from(f.body.bytes),u64::from(f.type_index),0,0]},
   5=>{let g=entry!(globals);span(g.initializer)?;
    [type_id(g.ty),u64::from(g.mutable),u64::from(g.initializer.offset),u64::from(g.initializer.bytes),0]},
   6=>{let e=entry!(exports);span(e.name)?;require(e.kind<=3,19,sid,index)?;
    [u64::from(e.name.offset),u64::from(e.name.bytes),u64::from(e.kind),u64::from(e.index),0]},
   7|8=>{let s=if sid==7{entry!(data)}else{entry!(elements)};span(s.payload)?;
    [u64::from(s.payload.offset),u64::from(s.payload.bytes),u64::from(s.destination),u64::from(s.count),0]},
   _=>return Err(field(20,sid,index)),
  };
  v.get(within).copied().ok_or_else(||field(21,sid,index))
 }
}
fn validate_runtime(h:&[u8;HEADER],source:u64,types:u64,defined:u64)->Result<(),SnapshotEncodeErrorV2>{
 let caps=[67108864,16777216,16777216,8388608,64,64,64000000,64,16384,4096,768,134217728,268435456,100000000,1000000000,32768,30000];
 for (i,cap) in caps.iter().enumerate(){require(get(h,1128+i*8)<=*cap,22,0,i)?;}
 let wasi_caps=[32768,4194304,32000000,65536,64,65536,30000];
 for (i,cap) in wasi_caps.iter().enumerate(){require(get(h,1264+i*8)<=*cap,23,0,i)?;}
 let presence=get(h,1112);require(presence<=1 && get(h,1120)!=0,24,0,0)?;
 for i in 0..5{require(get(h,1320+i*8)<=1,25,0,i)?;}
 if presence==0{for i in 0..12{require(get(h,1264+i*8)==0,26,0,i)?;}}
 require(get(h,1360)==source && get(h,1368)==types && types<=u32::MAX as u64
  && get(h,1376)==get(h,1160).min(defined) && (1..=64).contains(&get(h,1376))
  && get(h,1384)==get(h,1168) && (1..=64).contains(&get(h,1384)) && get(h,1392)==1
  && get(h,1400)<=get(h,1408) && get(h,1408)==get(h,1144) && get(h,1416)==get(h,1152),27,0,0)
}
impl SnapshotCursorV2<'_>{
 pub(crate) fn encoded_extent(&self)->u64{self.extent}
 pub(crate) fn emitted_extent(&self)->u64{self.emitted}
 pub(crate) fn next_block<'block>(&mut self,transfer:&'block mut[u8;SNAPSHOT_TRANSFER_BYTES_V2])
  ->Result<Option<SnapshotBlockV2<'block>>,SnapshotEncodeErrorV2>{
  if self.emitted==self.extent{return Ok(None);}
  let base=self.emitted;let mut at=base;let mut filled=0usize;
  // At most 4096 output-byte progress steps. Metadata steps emit the remainder
  // of one8-byte word: at most513 record visits, with at most9 directory probes.
  while filled<SNAPSHOT_TRANSFER_BYTES_V2 && at<self.extent{
   if at<HEADER as u64{
    let n=(HEADER-at as usize).min(SNAPSHOT_TRANSFER_BYTES_V2-filled);
    transfer[filled..filled+n].copy_from_slice(&self.header[at as usize..at as usize+n]);filled+=n;at+=n as u64;continue;
   }
   let mut found=None;
   for sid in 0..9{let start=get(&self.header,1600+sid*64+48);let bytes=get(&self.header,1600+sid*64+56);
    if at>=start && at-start<bytes{found=Some((sid,start,bytes));break;}}
   let (sid,start,bytes)=found.ok_or_else(||field(28,0,0))?;let relative=at-start;
   if sid==0{
    let n=usize::try_from((bytes-relative).min((SNAPSHOT_TRANSFER_BYTES_V2-filled)as u64)).map_err(|_|SnapshotEncodeErrorV2::Arithmetic)?;
    let offset=usize::try_from(relative).map_err(|_|SnapshotEncodeErrorV2::Arithmetic)?;
    transfer[filled..filled+n].copy_from_slice(&self.view.proof.source[offset..offset+n]);filled+=n;at+=n as u64;
   }else{
    let row_bytes=WIDTHS[sid]*8;let index=usize::try_from(relative/row_bytes).map_err(|_|SnapshotEncodeErrorV2::Arithmetic)?;
    let within=((relative%row_bytes)/8)as usize;let skip=(relative%8)as usize;
    let value=self.view.record_word(sid,index,within)?.to_le_bytes();let n=(8-skip).min(SNAPSHOT_TRANSFER_BYTES_V2-filled);
    transfer[filled..filled+n].copy_from_slice(&value[skip..skip+n]);filled+=n;at+=n as u64;
   }
  }
  self.emitted=at;
  Ok(Some(SnapshotBlockV2{bytes:&transfer[..filled],offset:base,final_block:at==self.extent}))
 }
}

// All newly concrete interface and aggregate shapes used by later admission.
// Counts are conservative named source places, not a granted floor or RSS.
struct EncoderInitPlacesV2<'g>{
 initial:&'g InitialProfileBorrowV1<'g>,view:SnapshotViewV2<'g>,view_return:Result<SnapshotViewV2<'g>,SnapshotEncodeErrorV2>,
 cursor_return:Result<SnapshotCursorV2<'g>,SnapshotEncodeErrorV2>,header:[u8;HEADER],
 usage:SwiftValidationUsage,observations:SwiftReactorObservations,inventory:(u64,u64,u64,u64,u64),
 words:[u64;20],directory:[u64;8],options:[[u64;2];4],validation_caps:[u64;5],
 memory_table:[(u32,u32);2],scalars:[u64;8],validation_budget:SwiftValidationBudget,
 runtime_budget:crate::experimental_swift_reactor::control::SwiftRunBudget,
 wasi:Option<(crate::experimental_wasi::WasiBudget,crate::experimental_wasi::WasiGrants)>,
}
struct EncoderBlockPlacesV2<'g>{
 cursor:&'g mut SnapshotCursorV2<'g>,transfer:&'g mut[u8;4096],
 block_return:Result<Option<SnapshotBlockV2<'g>>,SnapshotEncodeErrorV2>,
 found:Option<(usize,u64,u64)>,words:[u64;5],word:[u8;8],span:metadata::Span,
 record_return:Result<u64,SnapshotEncodeErrorV2>,span_result:Result<(),SnapshotEncodeErrorV2>,
}
struct EncoderCallerPlacesV2<'g>{
 view:Option<SnapshotViewV2<'g>>,cursor:Option<SnapshotCursorV2<'g>>,transfer:[u8;4096],
 view_move:SnapshotViewV2<'g>,cursor_move:SnapshotCursorV2<'g>,
 cursor_result:Result<SnapshotCursorV2<'g>,SnapshotEncodeErrorV2>,
 block:Option<SnapshotBlockV2<'g>>,block_result:Result<Option<SnapshotBlockV2<'g>>,SnapshotEncodeErrorV2>,
 error:SnapshotEncodeErrorV2,returned_error:Result<(),SnapshotEncodeErrorV2>,
}
pub(crate) fn snapshot_layouts_v2()->[(&'static str,usize,usize);16]{
 macro_rules! l{($t:ty)=>{(stringify!($t),size_of::<$t>(),align_of::<$t>())};}
 [l!(SnapshotViewV2<'static>),l!(SnapshotCursorV2<'static>),l!(SnapshotBlockV2<'static>),l!(SnapshotEncodeErrorV2),
 l!(Result<SnapshotViewV2<'static>,SnapshotEncodeErrorV2>),l!(Result<SnapshotCursorV2<'static>,SnapshotEncodeErrorV2>),
 l!(Result<Option<SnapshotBlockV2<'static>>,SnapshotEncodeErrorV2>),l!(Option<SnapshotViewV2<'static>>),
 l!(Option<SnapshotCursorV2<'static>>),l!(Option<SnapshotBlockV2<'static>>),
 l!(EncoderInitPlacesV2<'static>),l!(EncoderBlockPlacesV2<'static>),l!(EncoderCallerPlacesV2<'static>),
 l!((usize,usize,usize,usize,Resource)),l!((u64,u64,u64,u64,u64)),l!([u8;4096])]
}
#[cfg(any(test,mixer_snapshot_encoder_host))]
pub(crate) fn oracle_inventory_v2(initial:&InitialProfileBorrowV1<'_>)->String{
 let p=initial.snapshot_proof_v2();let m=&p.metadata;
 let mut out=String::new();
 for (i,v) in [m.signatures.snapshot_inventory_v2(),m.parameters.snapshot_inventory_v2(),
  m.imports.snapshot_inventory_v2(),m.functions.snapshot_inventory_v2(),m.globals.snapshot_inventory_v2(),
  m.exports.snapshot_inventory_v2(),m.data.snapshot_inventory_v2(),m.elements.snapshot_inventory_v2()].iter().enumerate(){
  out.push_str(&format!("BUFFER\t{}\t{:?}\n",i+1,v));
 }
 out
}
#[cfg(test)]mod encoder_unit{
 use super::*;
 #[test]fn finite_enum_and_option_mappings_v2(){
  assert_eq!([type_id(Type::I32),type_id(Type::I64),type_id(Type::F32),type_id(Type::F64)],[1,2,3,4]);
  assert_eq!(result_id(None),0);for t in [Type::I32,Type::I64,Type::F32,Type::F64]{assert_eq!(result_id(Some(t)),type_id(t));}
  for (i,t) in WasiFunction::ALL.into_iter().enumerate(){assert_eq!(wasi_id(t),i as u64+1);}
  assert_eq!(optional(None),[0,0]);assert_eq!(optional(Some(0)),[1,0]);assert_eq!(optional(Some(u32::MAX)),[1,u32::MAX as u64]);
 }
}
