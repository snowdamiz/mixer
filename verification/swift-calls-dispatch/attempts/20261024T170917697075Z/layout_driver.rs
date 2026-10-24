//! Metadata-only exact MIR type layout query. Not part of Mixer product.
#![feature(rustc_private)]
extern crate rustc_driver;
extern crate rustc_interface;
extern crate rustc_middle;
extern crate rustc_hir;
extern crate rustc_abi;
use rustc_driver::{Callbacks,Compilation};
use rustc_middle::ty::{self,Ty,TyCtxt,TypingEnv,TypeVisitableExt};
use rustc_middle::mir::{self,visit::Visitor};
use std::{env,fs::OpenOptions,io::Write};
fn j(s:&str)->String{let mut out=String::from("\"");for ch in s.chars(){match ch{'"'=>out.push_str("\\\""),'\\'=>out.push_str("\\\\"),'\n'=>out.push_str("\\n"),'\r'=>out.push_str("\\r"),'\t'=>out.push_str("\\t"),ch if(ch as u32)<32=>out.push_str(&format!("\\u{:04x}",ch as u32)),ch=>out.push(ch)}}out.push('"');out}
fn key<'tcx>(tcx:TyCtxt<'tcx>,t:Ty<'tcx>,depth:usize)->String{
 assert!(depth<128,"type identity recursion exceeded");
 let args=|a:ty::GenericArgsRef<'tcx>|a.iter().map(|arg|match arg.kind(){ty::GenericArgKind::Type(t)=>key(tcx,t,depth+1),ty::GenericArgKind::Lifetime(_)=>"erased-region".into(),ty::GenericArgKind::Const(c)=>format!("const:{c:?}")}).collect::<Vec<_>>().join(",");
 match t.kind(){
  ty::Adt(d,a)=>format!("Adt({:?};{})",tcx.def_path_hash(d.did()),args(a)),
  ty::Closure(d,a)=>format!("Closure({:?};{})",tcx.def_path_hash(*d),args(a)),
  ty::FnDef(d,a)=>format!("FnDef({:?};bounds:{:?};{})",tcx.def_path_hash(*d),a.bound_vars(),args(a.skip_binder())),
  ty::Ref(_,p,m)=>format!("Ref({m:?};{})",key(tcx,*p,depth+1)),
  ty::RawPtr(p,m)=>format!("RawPtr({m:?};{})",key(tcx,*p,depth+1)),
  ty::Tuple(ts)=>format!("Tuple({})",ts.iter().map(|t|key(tcx,t,depth+1)).collect::<Vec<_>>().join(",")),
  ty::Array(t,n)=>format!("Array({};{n:?})",key(tcx,*t,depth+1)),
  ty::Slice(t)=>format!("Slice({})",key(tcx,*t,depth+1)),
  _=>format!("{:?}",t.kind()),
 }
}
fn chosen(path:&str)->bool{
 let prefix="experimental_swift_reactor::execution::frame_operations::";
 if let Some(tail)=path.strip_prefix(&format!("{prefix}call_dispatch::")){
  if tail.starts_with("tests::") {let r=tail.strip_prefix("tests::").unwrap();return ["PC_OVERFLOW","CHECK_COUNT","CANCEL_AT","checkpoint"].iter().any(|n|r==*n||r.starts_with(&format!("{n}::")));}
  return ["check","trap","pop_checked","typed_i32","frame_guard","fetch","prefix","call_selected","signature_mismatch","indirect","local_slot","local_get","local_set","global_get","global_set","select_guard","publication","result_guard","run","complete"].iter().any(|n|tail==*n||tail.starts_with(&format!("{n}::")));
 }
 path.starts_with(prefix)&&["::enter_inner","::host_operation_inner","::prepare_growth"].iter().any(|n|path.ends_with(n)||path.contains(&format!("{n}::")))
}
struct Query;
impl Callbacks for Query{
 fn after_analysis<'tcx>(&mut self,_:&rustc_interface::interface::Compiler,tcx:TyCtxt<'tcx>)->Compilation{
  let Some(output)=env::var_os("MIXER_LAYOUT_OUTPUT")else{return Compilation::Continue;};
  let mut file=OpenOptions::new().create_new(true).write(true).open(output).expect("fresh query output");
  writeln!(file,"{{\"kind\":\"context\",\"target\":{},\"dataLayout\":{}}}",j(&tcx.sess.opts.target_triple.to_string()),j(&tcx.sess.target.data_layout)).unwrap();
  for &id in tcx.mir_keys(()){
   let path=tcx.def_path_str(id.to_def_id());if !chosen(&path){
    let partition=if path.starts_with("experimental_swift_reactor::execution::frame_operations::call_dispatch::tests::") {Some("fixture-only")} else if path.starts_with("experimental_swift_reactor::execution::frame_operations::call_dispatch::") {Some("accounting-const-only")} else if path.starts_with("experimental_swift_reactor::execution::frame_operations::memory_growth_operations::tests::") {Some("unchanged-prior-hook-or-fixture")} else if ["experimental_swift_reactor::execution::EXECUTION_HEADER_BYTES","experimental_swift_reactor::execution::frame_operations::FRAME_OPERATION_BYTES","experimental_swift_reactor::execution::frame_operations::CALLS_PERMANENT_BYTES"].iter().any(|n|path==*n)||path.starts_with("experimental::execution::borrowed::calls_kind_accounting::") {Some("accounting-const-only")} else {None};
    if let Some(partition)=partition {
     let kind=tcx.def_kind(id);let body=if matches!(kind,rustc_hir::def::DefKind::Fn|rustc_hir::def::DefKind::AssocFn|rustc_hir::def::DefKind::Closure){tcx.optimized_mir(id.to_def_id())}else{tcx.mir_for_ctfe(id.to_def_id())};
     let mut rendered=Vec::new();rustc_middle::mir::pretty::MirWriter::new(tcx).write_mir_fn(body,&mut rendered).expect("complete partition MIR");
     writeln!(file,"{{\"kind\":\"partition-body\",\"partition\":{},\"path\":{},\"defPathHash\":{},\"defKind\":{},\"span\":{},\"mir\":{}}}",j(partition),j(&path),j(&format!("{:?}",tcx.def_path_hash(id.to_def_id()))),j(&format!("{:?}",tcx.def_kind(id))),j(&format!("{:?}",tcx.def_span(id))),j(std::str::from_utf8(&rendered).unwrap())).unwrap();
    }continue;
   }
   let kind=tcx.def_kind(id);
   let body=if matches!(kind,rustc_hir::def::DefKind::Fn|rustc_hir::def::DefKind::AssocFn|rustc_hir::def::DefKind::Closure){tcx.optimized_mir(id.to_def_id())}else{tcx.mir_for_ctfe(id.to_def_id())};
   emit_body(tcx,id.to_def_id(),&path,None,body,&mut file);
   for (index,promoted) in tcx.promoted_mir(id.to_def_id()).iter_enumerated(){emit_body(tcx,id.to_def_id(),&path,Some(index.as_usize()),promoted,&mut file);}
  }
  for id in tcx.iter_local_def_id(){
   if !matches!(tcx.def_kind(id),rustc_hir::def::DefKind::Struct|rustc_hir::def::DefKind::Enum|rustc_hir::def::DefKind::Union){continue;}
   let path=tcx.def_path_str(id.to_def_id());
   if !["experimental_swift_reactor::","experimental_wasi::","experimental::"].iter().any(|p|path.starts_with(p)){continue;}
   let env=TypingEnv::post_analysis(tcx,id.to_def_id());let mut ty=tcx.normalize_erasing_regions(env,tcx.type_of(id).instantiate_identity());
   if ["::NeverPositions","::NeverActivePositions","::NeverPermanentPositions"].iter().any(|suffix|path.ends_with(suffix)){ty=tcx.normalize_erasing_regions(env,tcx.type_of(id).instantiate(tcx,tcx.mk_args(&[tcx.types.never.into()])));}
   if ty.has_non_region_param(){writeln!(file,"{{\"kind\":\"generic-declaration\",\"path\":{},\"type\":{}}}",j(&path),j(&format!("{ty:?}"))).unwrap();continue;}
   writeln!(file,"{{\"kind\":\"declaration\",\"path\":{},\"defPathHash\":{},\"layout\":{}}}",j(&path),j(&format!("{:?}",tcx.def_path_hash(id.to_def_id()))),layout_record(tcx,env,ty)).unwrap();
  }
  Compilation::Continue
 }
}
fn layout_record<'tcx>(tcx:TyCtxt<'tcx>,env:TypingEnv<'tcx>,ty:Ty<'tcx>)->String{
 let ty=tcx.erase_and_anonymize_regions(ty);let l=tcx.layout_of(env.as_query_input(ty)).expect("exact selected type layout");
 let cx=rustc_middle::ty::layout::LayoutCx::new(tcx,env);
 fn fields<'tcx>(tcx:TyCtxt<'tcx>,cx:&rustc_middle::ty::layout::LayoutCx<'tcx>,l:rustc_middle::ty::layout::TyAndLayout<'tcx>)->String{
  let mut out=Vec::new();for i in 0..l.fields.count(){let f=l.field(cx,i);out.push(format!("{{\"index\":{i},\"offset\":{},\"bytes\":{},\"alignment\":{},\"type\":{},\"identity\":{}}}",l.fields.offset(i).bytes(),f.size.bytes(),f.align.abi.bytes(),j(&format!("{:?}",f.ty)),j(&key(tcx,f.ty,0))));}out.join(",")
 }
 let mut variants=Vec::new();if let ty::Adt(d,_) = ty.kind(){
  for(index,v)in d.variants().iter_enumerated(){let vl=l.for_variant(&cx,index);variants.push(format!("{{\"index\":{},\"name\":{},\"bytes\":{},\"alignment\":{},\"fieldNames\":[{}],\"fields\":[{}]}}",index.as_usize(),j(v.name.as_str()),vl.size.bytes(),vl.align.abi.bytes(),v.fields.iter().map(|f|j(f.name.as_str())).collect::<Vec<_>>().join(","),fields(tcx,&cx,vl)));}
 }
 format!("{{\"type\":{},\"identity\":{},\"bytes\":{},\"alignment\":{},\"uninhabited\":{},\"fields\":[{}],\"variantsDebug\":{},\"variants\":[{}]}}",j(&format!("{ty:?}")),j(&key(tcx,ty,0)),l.size.bytes(),l.align.abi.bytes(),l.uninhabited,fields(tcx,&cx,l),j(&format!("{:?}",l.variants)),variants.join(","))
}
fn emit_body<'tcx>(tcx:TyCtxt<'tcx>,id:rustc_hir::def_id::DefId,path:&str,promoted:Option<usize>,body:&mir::Body<'tcx>,file:&mut std::fs::File){
 let env=TypingEnv::post_analysis(tcx,id);let mut rendered=Vec::new();rustc_middle::mir::pretty::MirWriter::new(tcx).write_mir_fn(body,&mut rendered).expect("complete MIR render");
 writeln!(file,"{{\"kind\":\"body\",\"path\":{},\"defPathHash\":{},\"promoted\":{},\"mir\":{}}}",j(path),j(&format!("{:?}",tcx.def_path_hash(id))),promoted.map_or("null".into(),|n|n.to_string()),j(std::str::from_utf8(&rendered).unwrap())).unwrap();
 for(local,decl)in body.local_decls.iter_enumerated(){writeln!(file,"{{\"kind\":\"local\",\"path\":{},\"promoted\":{},\"local\":{},\"sourceInfo\":{},\"layout\":{},\"captureLayout\":{}}}",j(path),promoted.map_or("null".into(),|n|n.to_string()),local.as_usize(),j(&format!("{:?}",decl.source_info)),layout_record(tcx,env,decl.ty),if matches!(decl.ty.peel_refs().kind(),ty::Closure(..)){layout_record(tcx,env,decl.ty.peel_refs())}else{"null".into()}).unwrap();}
 struct Operands<'a,'tcx>{tcx:TyCtxt<'tcx>,env:TypingEnv<'tcx>,path:&'a str,promoted:Option<usize>,file:&'a mut std::fs::File}
 impl<'tcx> Visitor<'tcx>for Operands<'_,'tcx>{fn visit_const_operand(&mut self,c:&mir::ConstOperand<'tcx>,at:mir::Location){let ty=c.const_.ty();if !matches!(ty.kind(),ty::FnDef(..)){writeln!(self.file,"{{\"kind\":\"constant-operand\",\"path\":{},\"promoted\":{},\"location\":{},\"span\":{},\"constant\":{},\"layout\":{}}}",j(self.path),self.promoted.map_or("null".into(),|n|n.to_string()),j(&format!("{at:?}")),j(&format!("{:?}",c.span)),j(&format!("{:?}",c.const_)),layout_record(self.tcx,self.env,ty)).unwrap();}if matches!(ty.kind(),ty::FnDef(..)){writeln!(self.file,"{{\"kind\":\"FnDef\",\"path\":{},\"promoted\":{},\"location\":{},\"span\":{},\"calleePath\":{},\"calleeDefPathHash\":{},\"layout\":{}}}",j(self.path),self.promoted.map_or("null".into(),|n|n.to_string()),j(&format!("{at:?}")),j(&format!("{:?}",c.span)),j(&self.tcx.def_path_str(if let ty::FnDef(d,_) = ty.kind(){*d}else{unreachable!()})),j(&format!("{:?}",self.tcx.def_path_hash(if let ty::FnDef(d,_) = ty.kind(){*d}else{unreachable!()}))),layout_record(self.tcx,self.env,ty)).unwrap();}}}
 Operands{tcx,env,path,promoted,file}.visit_body(body);
}
fn main(){let mut args=env::args().collect::<Vec<_>>();if args.get(1).is_some_and(|s|s.ends_with("rustc")){args.remove(1);}if let Some(root)=env::var_os("MIXER_LAYOUT_SYSROOT"){args.extend(["--sysroot".into(),root.to_str().unwrap().into()]);}rustc_driver::run_compiler(&args,&mut Query);}
