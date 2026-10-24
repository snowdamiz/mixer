//! Metadata-only exact MIR type layout query. Not part of Mixer product.
#![feature(rustc_private)]
extern crate rustc_driver;
extern crate rustc_interface;
extern crate rustc_middle;
extern crate rustc_hir;
extern crate rustc_abi;
extern crate rustc_data_structures;
extern crate rustc_hashes;
use rustc_driver::{Callbacks,Compilation};
use rustc_middle::ty::{self,Ty,TyCtxt,TypingEnv,TypeVisitableExt};
use rustc_middle::mir::{self,visit::Visitor};
use std::{env,fs::OpenOptions,io::Write,cell::RefCell,collections::BTreeMap,hash::Hash};
thread_local! {static TYPE_GRAPHS:RefCell<BTreeMap<String,String>>=const {RefCell::new(BTreeMap::new())};}
thread_local! {static TYPE_LAYOUTS:RefCell<BTreeMap<String,String>>=const {RefCell::new(BTreeMap::new())};}
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
fn definition_hash_proof(tcx:TyCtxt<'_>,d:rustc_hir::def_id::DefId)->String{
 use rustc_hir::definitions::DefPathData::*;
 use rustc_hir::def_id::{DefPathHash,DefId,CRATE_DEF_INDEX};
 use rustc_data_structures::stable_hash::StableHasher;
 let stable=tcx.stable_crate_id(d.krate);let path=tcx.def_path(d);
 // Version-pinned official compiler metadata hash, never product semantics.
 let mut hash=DefPathHash::new(stable,rustc_hashes::Hash64::new(stable.as_u64()));
 assert_eq!(hash,tcx.def_path_hash(DefId{krate:d.krate,index:CRATE_DEF_INDEX}),"official root hash reconstruction mismatch");
 let root=hash;let mut steps=Vec::new();
 for item in &path.data{
  let mut hasher=StableHasher::new();hash.local_hash().hash(&mut hasher);
  std::mem::discriminant(&item.data).hash(&mut hasher);
  let name=match item.data {TypeNs(n)|ValueNs(n)|MacroNs(n)|LifetimeNs(n)|AnonAssocTy(n)|OpaqueLifetime(n)=>Some(n),Impl|ForeignMod|CrateRoot|Use|GlobalAsm|Closure|Ctor|AnonConst|OpaqueTy|SyntheticCoroutineBody|NestedStatic=>None};
  if let Some(name)=name{name.as_str().hash(&mut hasher);}item.disambiguator.hash(&mut hasher);
  hash=DefPathHash::new(stable,hasher.finish());steps.push(format!("{{\"component\":{},\"result\":{}}}",j(&format!("{item:?}")),j(&format!("{hash:?}"))));
 }
 assert_eq!(hash,tcx.def_path_hash(d),"official full definition hash reconstruction mismatch");
 format!("{{\"api\":\"rustc1.99.0-Definitions::new+DefKey::compute_stable_hash\",\"pathData\":{},\"root\":{},\"steps\":[{}],\"final\":{},\"compilerRootAndFinalMatch\":true}}",j(&format!("{:?}",path.data)),j(&format!("{root:?}")),steps.join(","),j(&format!("{hash:?}")))
}
fn definition(tcx:TyCtxt<'_>,d:rustc_hir::def_id::DefId)->String{
 let span=tcx.def_span(d);let source=if span.is_dummy(){"null".into()}else{let sm=tcx.sess.source_map();let lo=sm.lookup_char_pos(span.lo());let hi=sm.lookup_char_pos(span.hi());format!("{{\"file\":{},\"startLine\":{},\"startColumn\":{},\"endLine\":{},\"endColumn\":{}}}",j(&sm.span_to_filename(span).prefer_local_unconditionally().to_string()),lo.line,lo.col.0,hi.line,hi.col.0)};
 format!("{{\"rawDefPathHash\":{},\"path\":{},\"disambiguatedDefPath\":{},\"kind\":{},\"crateName\":{},\"crateStableId\":{},\"isLocal\":{},\"span\":{},\"source\":{},\"contextHashProof\":{}}}",j(&format!("{:?}",tcx.def_path_hash(d))),j(&tcx.def_path_str(d)),j(&format!("{:?}",tcx.def_path(d).data)),j(&format!("{:?}",tcx.def_kind(d))),j(tcx.crate_name(d.krate).as_str()),j(&format!("{:?}",tcx.stable_crate_id(d.krate))),d.is_local(),j(&format!("{:?}",span)),source,definition_hash_proof(tcx,d))
}
fn graph<'tcx>(tcx:TyCtxt<'tcx>,t:Ty<'tcx>,depth:usize)->String{
 assert!(depth<128,"structural type graph recursion exceeded");
 let args=|a:ty::GenericArgsRef<'tcx>|a.iter().map(|a|match a.kind(){
  ty::GenericArgKind::Type(t)=>format!("{{\"kind\":\"type\",\"value\":{}}}",graph(tcx,t,depth+1)),
  ty::GenericArgKind::Lifetime(r)=>format!("{{\"kind\":\"region\",\"value\":{}}}",j(&format!("{r:?}"))),
  ty::GenericArgKind::Const(c)=>{let v=c.try_to_value().expect("unsupported non-value generic const");format!("{{\"kind\":\"const\",\"value\":{},\"valtree\":{},\"type\":{}}}",j(&format!("{c:?}")),j(&format!("{:?}",v.valtree)),graph(tcx,v.ty,depth+1))},
 }).collect::<Vec<_>>().join(",");
 match t.kind(){
  ty::Adt(d,a)=>format!("{{\"kind\":\"Adt\",\"definition\":{},\"args\":[{}]}}",definition(tcx,d.did()),args(a)),
  ty::Closure(d,a)=>format!("{{\"kind\":\"Closure\",\"definition\":{},\"args\":[{}]}}",definition(tcx,*d),args(a)),
  ty::FnDef(d,a)=>format!("{{\"kind\":\"FnDef\",\"definition\":{},\"binder\":{},\"args\":[{}]}}",definition(tcx,*d),j(&format!("{:?}",a.bound_vars())),args(a.skip_binder())),
  ty::Ref(r,p,m)=>format!("{{\"kind\":\"Ref\",\"region\":{},\"mutability\":{},\"pointee\":{}}}",j(&format!("{r:?}")),j(&format!("{m:?}")),graph(tcx,*p,depth+1)),
  ty::RawPtr(p,m)=>format!("{{\"kind\":\"RawPtr\",\"mutability\":{},\"pointee\":{}}}",j(&format!("{m:?}")),graph(tcx,*p,depth+1)),
  ty::Tuple(ts)=>format!("{{\"kind\":\"Tuple\",\"elements\":[{}]}}",ts.iter().map(|t|graph(tcx,t,depth+1)).collect::<Vec<_>>().join(",")),
  ty::Array(t,n)=>format!("{{\"kind\":\"Array\",\"element\":{},\"length\":{},\"lengthDebug\":{}}}",graph(tcx,*t,depth+1),n.try_to_target_usize(tcx).expect("unsupported concrete array length"),j(&format!("{n:?}"))),
  ty::Slice(t)=>format!("{{\"kind\":\"Slice\",\"element\":{}}}",graph(tcx,*t,depth+1)),
  ty::Pat(t,p)=>format!("{{\"kind\":\"Pat\",\"base\":{},\"pattern\":{}}}",graph(tcx,*t,depth+1),j(&format!("{p:?}"))),
  ty::FnPtr(..)=>{let b=t.fn_sig(tcx);let sig=b.skip_binder();format!("{{\"kind\":\"FnPtr\",\"binder\":{},\"safety\":{},\"abi\":{},\"variadic\":{},\"inputs\":[{}],\"output\":{}}}",j(&format!("{:?}",b.bound_vars())),j(&format!("{:?}",sig.safety())),j(&format!("{:?}",sig.abi())),sig.c_variadic(),sig.inputs().iter().map(|t|graph(tcx,*t,depth+1)).collect::<Vec<_>>().join(","),graph(tcx,sig.output(),depth+1))},
  ty::Bool|ty::Char|ty::Int(_)|ty::Uint(_)|ty::Float(_)|ty::Str|ty::Never=>format!("{{\"kind\":\"primitive\",\"actual\":{}}}",j(&format!("{:?}",t.kind()))),
  other=>panic!("unsupported actual structural graph kind: {other:?}"),
 }
}
fn remember<'tcx>(tcx:TyCtxt<'tcx>,t:Ty<'tcx>){let t=tcx.erase_and_anonymize_regions(t);let identity=key(tcx,t,0);let actual=graph(tcx,t,0);TYPE_GRAPHS.with(|m|{let mut m=m.borrow_mut();if let Some(previous)=m.insert(identity,actual.clone()){assert_eq!(previous,actual,"ambiguous actual type graph key");}});}
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
  writeln!(file,"{{\"kind\":\"context\",\"target\":{},\"dataLayout\":{},\"localCrateStableId\":{},\"localCrateRootHash\":{}}}",j(&tcx.sess.opts.target_triple.to_string()),j(&tcx.sess.target.data_layout),j(&format!("{:?}",tcx.stable_crate_id(rustc_hir::def_id::LOCAL_CRATE))),j(&format!("{:?}",tcx.def_path_hash(rustc_hir::def_id::DefId{krate:rustc_hir::def_id::LOCAL_CRATE,index:rustc_hir::def_id::CRATE_DEF_INDEX})))).unwrap();
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
   if ["::CallsActivePositions","::CallsPermanentPositions","::NeverActivePositions","::NeverPermanentPositions","::CallsKindActivePositions","::CallsKindPermanentPositions"].iter().any(|suffix|path.ends_with(suffix)){
    let ty::Adt(d,args)=ty.kind()else{panic!("witness class is not actual ADT")};
    for f in d.all_fields(){let ft=tcx.normalize_erasing_regions(env,f.ty(tcx,args));let identity=key(tcx,tcx.erase_and_anonymize_regions(ft),0);if !TYPE_LAYOUTS.with(|m|m.borrow().contains_key(&identity)){let _=layout_record(tcx,env,ft);}}
   }
  }
  TYPE_LAYOUTS.with(|m|for(identity,actual)in m.borrow().iter(){writeln!(file,"{{\"kind\":\"type-layout\",\"identity\":{},\"layout\":{}}}",j(identity),actual).unwrap();});
  TYPE_GRAPHS.with(|m|for(identity,actual)in m.borrow().iter(){writeln!(file,"{{\"kind\":\"type-graph\",\"identity\":{},\"graph\":{}}}",j(identity),actual).unwrap();});
  // Additive diagnostic graph work occurs only after every original body, local,
  // constant, declaration, layout and graph record has been emitted. This keeps
  // compiler allocation-display numbering in the accepted primary query order.
  for &id in tcx.mir_keys(()){
   let path=tcx.def_path_str(id.to_def_id());let kind=tcx.def_kind(id);
   let body=if matches!(kind,rustc_hir::def::DefKind::Fn|rustc_hir::def::DefKind::AssocFn|rustc_hir::def::DefKind::Closure){tcx.optimized_mir(id.to_def_id())}else{tcx.mir_for_ctfe(id.to_def_id())};
   emit_scope_graph(tcx,id.to_def_id(),&path,body,&mut file);
   if path.starts_with("experimental_swift_reactor::execution::frame_operations::tests::"){
    let mut rendered=Vec::new();rustc_middle::mir::pretty::MirWriter::new(tcx).write_mir_fn(body,&mut rendered).expect("additional prior frame body MIR");
    writeln!(file,"{{\"kind\":\"partition-body\",\"partition\":\"prior-frame-test-body-preserve-original-classification\",\"path\":{},\"defPathHash\":{},\"defKind\":{},\"span\":{},\"mir\":{}}}",j(&path),j(&format!("{:?}",tcx.def_path_hash(id.to_def_id()))),j(&format!("{kind:?}")),j(&format!("{:?}",tcx.def_span(id))),j(std::str::from_utf8(&rendered).unwrap())).unwrap();
   }
  }

  Compilation::Continue
 }
}
fn layout_record<'tcx>(tcx:TyCtxt<'tcx>,env:TypingEnv<'tcx>,ty:Ty<'tcx>)->String{
 let ty=tcx.erase_and_anonymize_regions(ty);let l=tcx.layout_of(env.as_query_input(ty)).expect("exact selected type layout");
 remember(tcx,ty);
 let cx=rustc_middle::ty::layout::LayoutCx::new(tcx,env);
 fn fields<'tcx>(tcx:TyCtxt<'tcx>,cx:&rustc_middle::ty::layout::LayoutCx<'tcx>,l:rustc_middle::ty::layout::TyAndLayout<'tcx>)->String{
  let mut out=Vec::new();for i in 0..l.fields.count(){let f=l.field(cx,i);remember(tcx,f.ty);out.push(format!("{{\"index\":{i},\"offset\":{},\"bytes\":{},\"alignment\":{},\"type\":{},\"identity\":{}}}",l.fields.offset(i).bytes(),f.size.bytes(),f.align.abi.bytes(),j(&format!("{:?}",f.ty)),j(&key(tcx,tcx.erase_and_anonymize_regions(f.ty),0))));}out.join(",")
 }
 let mut variants=Vec::new();if let ty::Adt(d,_) = ty.kind(){
  for(index,v)in d.variants().iter_enumerated(){let vl=l.for_variant(&cx,index);variants.push(format!("{{\"index\":{},\"name\":{},\"bytes\":{},\"alignment\":{},\"fieldNames\":[{}],\"fields\":[{}]}}",index.as_usize(),j(v.name.as_str()),vl.size.bytes(),vl.align.abi.bytes(),v.fields.iter().map(|f|j(f.name.as_str())).collect::<Vec<_>>().join(","),fields(tcx,&cx,vl)));}
 }
 let identity=key(tcx,ty,0);let actual=format!("{{\"type\":{},\"identity\":{},\"bytes\":{},\"alignment\":{},\"uninhabited\":{},\"fields\":[{}],\"variantsDebug\":{},\"variants\":[{}]}}",j(&format!("{ty:?}")),j(&identity),l.size.bytes(),l.align.abi.bytes(),l.uninhabited,fields(tcx,&cx,l),j(&format!("{:?}",l.variants)),variants.join(","));
 TYPE_LAYOUTS.with(|m|{let mut m=m.borrow_mut();if let Some(previous)=m.insert(identity,actual.clone()){assert_eq!(previous,actual,"ambiguous actual type layout key");}});actual
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

// This conservative function-item-use graph includes constants and function
// pointers as well as direct calls. It supplies no layout/accounting exemption.
fn emit_scope_graph<'tcx>(tcx:TyCtxt<'tcx>,id:rustc_hir::def_id::DefId,path:&str,body:&mir::Body<'tcx>,file:&mut std::fs::File){
 let mut rendered=Vec::new();rustc_middle::mir::pretty::MirWriter::new(tcx).write_mir_fn(body,&mut rendered).expect("whole source graph MIR header");
 let text=std::str::from_utf8(&rendered).unwrap();
 writeln!(file,"{{\"kind\":\"scope-graph-body\",\"path\":{},\"defPathHash\":{},\"defKind\":{},\"span\":{},\"header\":{},\"mirSHA256DeferredToEmittedArchive\":true}}",j(path),j(&format!("{:?}",tcx.def_path_hash(id))),j(&format!("{:?}",tcx.def_kind(id))),j(&format!("{:?}",tcx.def_span(id))),j(text.lines().next().expect("MIR header"))).unwrap();
 struct Uses<'a,'tcx>{tcx:TyCtxt<'tcx>,path:&'a str,id:rustc_hir::def_id::DefId,file:&'a mut std::fs::File}
 impl<'tcx> Visitor<'tcx>for Uses<'_,'tcx>{fn visit_const_operand(&mut self,c:&mir::ConstOperand<'tcx>,at:mir::Location){
  if let ty::FnDef(d,_) = c.const_.ty().kind(){writeln!(self.file,"{{\"kind\":\"scope-graph-function-item-use\",\"path\":{},\"bodyDefPathHash\":{},\"location\":{},\"span\":{},\"actualType\":{},\"calleePath\":{},\"calleeDefPathHash\":{}}}",j(self.path),j(&format!("{:?}",self.tcx.def_path_hash(self.id))),j(&format!("{at:?}")),j(&format!("{:?}",c.span)),j(&format!("{:?}",c.const_.ty())),j(&self.tcx.def_path_str(*d)),j(&format!("{:?}",self.tcx.def_path_hash(*d)))).unwrap();}
 }}
 Uses{tcx,path,id,file}.visit_body(body);
}
