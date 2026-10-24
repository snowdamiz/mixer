#!/usr/bin/env python3
"""Small owned stable-Rust proof feasibility experiments; never compiles Mixer."""
from pathlib import Path
import subprocess, json, hashlib, tempfile, shutil, datetime, os
HERE=Path(__file__).resolve().parent
RUSTC='/opt/homebrew/opt/rustup/bin/rustc'
SOURCES={
'public_alias_and_exact_inference':r'''use std::sync::{Arc,atomic::AtomicBool};
use std::mem::{size_of,align_of,size_of_val};
const fn bytes<T>(_: &T) -> usize { size_of::<T>() }
const fn alignment<T>(_: &T) -> usize { align_of::<T>() }
const ITEM_BYTES: usize = bytes(&Arc::<AtomicBool>::clone);
const ITEM_ALIGNMENT: usize = alignment(&Arc::<AtomicBool>::clone);
const fn factory(v: usize) -> impl Fn() -> usize { move || v }
const CLOSURE_BYTES: usize = bytes(&factory(7));
const CLOSURE_ALIGNMENT: usize = alignment(&factory(7));
fn main() {
 let f=Arc::<AtomicBool>::clone;
 let c=factory(7);
 println!("item {} {} {}", ITEM_BYTES, ITEM_ALIGNMENT, std::any::type_name_of_val(&f));
 println!("closure {} {} {}", CLOSURE_BYTES,CLOSURE_ALIGNMENT,std::any::type_name_of_val(&c));
 println!("public_alias {} {}",size_of::<Arc<AtomicBool>>(),size_of_val(&Arc::new(AtomicBool::new(false))));
 assert_eq!(ITEM_BYTES,0);
 assert_eq!(CLOSURE_BYTES,size_of_val(&c));
}
''',
'never_inferred':r'''use std::mem::{size_of,align_of};
fn never() -> ! { panic!("never executed") }
const fn return_size<T>(_: fn() -> T) -> usize { size_of::<T>() }
const fn return_align<T>(_: fn() -> T) -> usize { align_of::<T>() }
const N:usize=return_size(never);
const A:usize=return_align(never);
fn main(){println!("never {} {}",N,A);assert_eq!(N,0);}
''',
'never_named_field':r'''struct Witness { actual: ! }
fn main() {}
''',
'private_std_paths':r'''use std::cell::Cell;
struct W {
 a: std::thread::local_impl::EagerStorage<Cell<bool>>,
 b: core::num::niche_types::UsizeNoHighBit,
 c: *const std::sync::ArcInner<std::sync::atomic::AtomicBool>,
 d: *const std::sync::atomic::private::Align8<usize>,
}
fn main(){}
''',
'private_arc_field_inference':r'''use std::sync::{Arc,atomic::AtomicBool};
fn main(){let arc=Arc::new(AtomicBool::new(false));let private=arc.ptr; println!("{}",std::mem::size_of_val(&private));}
''',
'local_inferred_struct_field':r'''struct W { actual: _ }
fn main() { let closure=||1; let _=W {actual:closure}; }
''',
'closure_tuple_identity':r'''fn require_same<T>(_:&T,_:&T){}
fn main(){let value=1usize;let closure=||value;let tuple=(&value,);require_same(&closure,&tuple);}
''',
'std_tls_optimized_locals':r'''use std::cell::Cell;
thread_local! { static VALUE: Cell<Option<usize>> = const { Cell::new(None) }; }
#[inline(never)] pub fn hook()->Option<usize>{VALUE.with(Cell::get)}
fn main(){assert_eq!(hook(),None);println!("tls hook executed");}
''',
'vec_optimized_locals':r'''#[inline(never)] pub fn first(v:&[u32])->Option<&u32>{v.first()}
fn main(){assert_eq!(first(&[7]),Some(&7));}
''',
}
SOURCES['exact_inference_copy_bound'] = SOURCES['public_alias_and_exact_inference'].replace('impl Fn() -> usize {','impl Fn() -> usize + Copy {')
SOURCES['exact_four_role_classes'] = r'''use std::mem::{size_of,align_of};
#[allow(dead_code)] struct Roles<T> { source:T,argument:T,returned:T,caller:T }
const fn roles_of_value<T:Copy>(_:T)->(usize,usize) { (size_of::<Roles<T>>(),align_of::<Roles<T>>()) }
const fn roles_of_return<T>(_:fn()->T)->(usize,usize){ (size_of::<Roles<T>>(),align_of::<Roles<T>>()) }
fn never()->!{panic!("never executed")}
const NEVER:(usize,usize)=roles_of_return(never);
const ITEM:(usize,usize)=roles_of_value(never);
const fn factory(v:usize)->impl Fn()->usize+Copy{move||v}
const CLOSURE:(usize,usize)=roles_of_value(factory(7));
fn main(){println!("exact four typed roles never {:?} item {:?} closure {:?}",NEVER,ITEM,CLOSURE);assert_eq!(NEVER,(0,1));assert_eq!(ITEM,(0,1));assert_eq!(CLOSURE,(32,8));}
'''

SOURCES['borrowed_factory_without_owner'] = r'''use std::mem::{size_of,align_of};
#[allow(dead_code)] struct Roles<T>{source:T,argument:T,returned:T,caller:T}
fn factory(v:&mut usize)->impl FnMut()->usize+'_ {move||{*v+=1;*v}}
const fn return_roles<T>(_:fn(&'static mut usize)->T)->(usize,usize){(size_of::<Roles<T>>(),align_of::<Roles<T>>())}
const EXACT:(usize,usize)=return_roles(factory);
fn main(){println!("exact borrowed closure four roles {:?}; constructor never called",EXACT);assert_eq!(EXACT,(32,8));}
'''

def sha(b):return hashlib.sha256(b).hexdigest()
def run(argv,**kw):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(argv,capture_output=True,**kw)
 return {'argv':argv,'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')}
def main():
 out=HERE/'experiments';out.mkdir(exist_ok=True)
 version=run([RUSTC,'--version','--verbose']);(out/'toolchain.json').write_text(json.dumps(version,indent=2)+'\n')
 env=os.environ.copy();env.pop('RUSTC_BOOTSTRAP',None)
 records=[]
 temp=Path(tempfile.mkdtemp(prefix='mixer-optimized-accounting-audit-'))
 try:
  for name,source in SOURCES.items():
   case=out/name;case.mkdir(exist_ok=True);src=case/(name+'.rs');src.write_text(source)
   binary=temp/name
   command=run([RUSTC,'--edition=2024','-Copt-level=3','--emit=link,mir','--out-dir',str(temp),str(src)],env=env)
   (case/'compile.json').write_text(json.dumps(command,indent=2)+'\n')
   record={'name':name,'sourceSHA256':sha(src.read_bytes()),'exitCode':command['exitCode'],'bootstrap':False}
   if command['exitCode']==0:
    execution=run([str(binary)],env=env);(case/'execute.json').write_text(json.dumps(execution,indent=2)+'\n');record['executionExitCode']=execution['exitCode']
    mir=temp/(name+'.mir')
    if mir.exists():shutil.copy2(mir,case/'optimized.mir');record['mirSHA256']=sha(mir.read_bytes())
   records.append(record)
 finally:
  shutil.rmtree(temp)
  (out/'suite-cleanup.json').write_text(json.dumps({'temporaryDirectory':str(temp),'removed':not temp.exists(),'scope':'Only this audit owned host compiler artifacts; no native instances or product build targets used.'},indent=2)+'\n')
 (out/'suite-summary.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps(records,indent=2))
if __name__=='__main__':main()
