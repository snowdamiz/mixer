//! Metadata-only exact MIR type layout query. Not part of Mixer product.
#![feature(rustc_private)]
extern crate rustc_driver;
extern crate rustc_interface;
extern crate rustc_middle;
extern crate rustc_hir;
extern crate rustc_abi;
use rustc_driver::{Callbacks,Compilation};
use rustc_middle::ty::{self,Ty,TyCtxt,TypingEnv};
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
   let path=tcx.def_path_str(id.to_def_id());if !chosen(&path){continue;}
   let kind=tcx.def_kind(id);
   let body=if matches!(kind,rustc_hir::def::DefKind::Fn|rustc_hir::def::DefKind::AssocFn|rustc_hir::def::DefKind::Closure){tcx.optimized_mir(id.to_def_id())}else{tcx.mir_for_ctfe(id.to_def_id())};
   emit_body(tcx,id.to_def_id(),&path,None,body,&mut file);
   for (index,promoted) in tcx.promoted_mir(id.to_def_id()).iter_enumerated(){emit_body(tcx,id.to_def_id(),&path,Some(index.as_usize()),promoted,&mut file);}
  }
  Compilation::Continue
 }
}
fn layout_record<'tcx>(tcx:TyCtxt<'tcx>,env:TypingEnv<'tcx>,ty:Ty<'tcx>)->String{
 let ty=tcx.erase_and_anonymize_regions(ty);let l=tcx.layout_of(env.as_query_input(ty)).expect("exact selected type layout");
 let cx=rustc_middle::ty::layout::LayoutCx::new(tcx,env);
 let mut fields=Vec::new();for i in 0..l.fields.count(){let f=l.field(&cx,i);fields.push(format!("{{\"index\":{i},\"offset\":{},\"bytes\":{},\"alignment\":{},\"type\":{},\"identity\":{}}}",l.fields.offset(i).bytes(),f.size.bytes(),f.align.abi.bytes(),j(&format!("{:?}",f.ty)),j(&key(tcx,f.ty,0))));}
 format!("{{\"type\":{},\"identity\":{},\"bytes\":{},\"alignment\":{},\"uninhabited\":{},\"fields\":[{}],\"variants\":{}}}",j(&format!("{ty:?}")),j(&key(tcx,ty,0)),l.size.bytes(),l.align.abi.bytes(),l.uninhabited,fields.join(","),j(&format!("{:?}",l.variants)))
}
fn emit_body<'tcx>(tcx:TyCtxt<'tcx>,id:rustc_hir::def_id::DefId,path:&str,promoted:Option<usize>,body:&mir::Body<'tcx>,file:&mut std::fs::File){
 let env=TypingEnv::post_analysis(tcx,id);let mut rendered=Vec::new();rustc_middle::mir::pretty::MirWriter::new(tcx).write_mir_fn(body,&mut rendered).expect("complete MIR render");
 writeln!(file,"{{\"kind\":\"body\",\"path\":{},\"defPathHash\":{},\"promoted\":{},\"mir\":{}}}",j(path),j(&format!("{:?}",tcx.def_path_hash(id))),promoted.map_or("null".into(),|n|n.to_string()),j(std::str::from_utf8(&rendered).unwrap())).unwrap();
 for(local,decl)in body.local_decls.iter_enumerated(){writeln!(file,"{{\"kind\":\"local\",\"path\":{},\"promoted\":{},\"local\":{},\"sourceInfo\":{},\"layout\":{}}}",j(path),promoted.map_or("null".into(),|n|n.to_string()),local.as_usize(),j(&format!("{:?}",decl.source_info)),layout_record(tcx,env,decl.ty)).unwrap();}
 struct Operands<'a,'tcx>{tcx:TyCtxt<'tcx>,env:TypingEnv<'tcx>,path:&'a str,file:&'a mut std::fs::File}
 impl<'tcx> Visitor<'tcx>for Operands<'_,'tcx>{fn visit_const_operand(&mut self,c:&mir::ConstOperand<'tcx>,at:mir::Location){let ty=c.const_.ty();if matches!(ty.kind(),ty::FnDef(..)){writeln!(self.file,"{{\"kind\":\"FnDef\",\"path\":{},\"location\":{},\"span\":{},\"layout\":{}}}",j(self.path),j(&format!("{at:?}")),j(&format!("{:?}",c.span)),layout_record(self.tcx,self.env,ty)).unwrap();}}}
 Operands{tcx,env,path,file}.visit_body(body);
}
fn main(){let mut args=env::args().collect::<Vec<_>>();if args.get(1).is_some_and(|s|s.ends_with("rustc")){args.remove(1);}if let Some(root)=env::var_os("MIXER_LAYOUT_SYSROOT"){args.extend(["--sysroot".into(),root.to_str().unwrap().into()]);}rustc_driver::run_compiler(&args,&mut Query);}
