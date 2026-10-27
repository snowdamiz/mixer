"""Bind exact types in root-released source146 compiler layout output."""
import gzip,re,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V=ROOT/'verification'
RAW_SHA='6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a'
ARCHIVE_SHA='1ddc23c6274a1c4f148e9d4a389aa0aeaa070384929280de044f4889a49ec9ec'
MODULES={'swift':'experimental::swift','metadata':'experimental::metadata','reader':'experimental::reader','descriptor':'experimental_wasi::descriptor','retained_profile_loader_v1':'experimental_swift_reactor::retained_profile_loader_v1','control':'experimental_swift_reactor::control'}
NAMES={'File':'std::fs::File','Error':'std::io::Error','Metadata':'std::fs::Metadata','Instant':'std::time::Instant','Duration':'std::time::Duration','SwiftControl':'experimental::account::SwiftControl','SwiftDeclaration':'experimental::metadata::SwiftDeclaration','FileIdentityV1':'experimental_swift_reactor::retained_profile_loader_v1::FileIdentityV1','BuildView':'experimental_swift_reactor::retained_profile_loader_v1::BuildView','SessionView':'experimental_swift_reactor::retained_profile_loader_v1::SessionView','Section':'experimental_swift_reactor::retained_profile_loader_v1::Section','Bytes':'experimental_swift_reactor::retained_profile_loader_v1::Bytes','Role':'experimental_swift_reactor::retained_profile_loader_v1::Role','Refusal':'experimental_swift_reactor::retained_profile_loader_v1::Refusal','SelectedValidatedProfileV1':'experimental_swift_reactor::retained_profile_loader_v1::SelectedValidatedProfileV1','LoaderFailureV1':'experimental_swift_reactor::retained_profile_loader_v1::LoaderFailureV1','LoaderUsageV1':'experimental_swift_reactor::retained_profile_loader_v1::LoaderUsageV1','ReturnedLoaderFilesV1':'experimental_swift_reactor::retained_profile_loader_v1::ReturnedLoaderFilesV1','LoaderOutcomeV1':'experimental_swift_reactor::retained_profile_loader_v1::LoaderOutcomeV1','ProcessObservationV1':'experimental_swift_reactor::retained_profile_loader_v1::ProcessObservationV1','SwiftMetadata':'experimental::metadata::Metadata<experimental::metadata::SwiftDeclaration>','Option':'std::option::Option','Result':'std::result::Result','Vec':'std::vec::Vec','Ordering':'std::cmp::Ordering','BodyState':'experimental::validate::BodyState','ResolveError':'experimental_wasi::descriptor::ResolveError','TryFromIntError':'std::num::TryFromIntError','TryReserveError':'std::collections::TryReserveError'}
PRIMITIVES={'()':0,'!':0,'bool':1,'u8':1,'i8':1,'u16':2,'i16':2,'u32':4,'i32':4,'u64':8,'i64':8,'u128':16,'i128':16,'usize':8,'isize':8,'f32':4,'f64':8}
def key(t):
 return re.sub(r'\{closure@.*?/src/','{closure@<SRC>/',t).replace("'static","'_")

def mirkey(t):
 t=re.sub(r'\{closure@.*?/src/','{closure@<SRC>/',t).replace("'static","'_")
 for n,v in MODULES.items():t=re.sub(r'(?<![\w:])'+n+r'::',lambda m:v+'::',t)
 for n,v in NAMES.items():t=re.sub(r'(?<![\w:])'+n+r'\b',lambda m:v,t)
 return t

def catalog():
 p=V/'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz'
 data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==ARCHIVE_SHA
 raw=gzip.decompress(data);assert hashlib.sha256(raw).hexdigest()==RAW_SHA
 table={};rows=[]
 for t,n,a in re.findall(rb'^print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes$',raw,re.M):
  t=t.decode();k=key(t);v=(int(n),int(a));assert k not in table or table[k]==v,('ambiguous-layout',k)
  table[k]=v;rows.append({'type':t,'key':k,'bytes':v[0],'alignment':v[1]})
 assert len(rows)==3072
 extra=json.loads((V/'swift-guarded-snapshot-source146-callee-storage-layouts/results.json').read_bytes())
 assert extra['source_tree_sha256']=='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185' and len(extra['queries'])==21
 for row in extra['queries']:
  k=key(row['concrete'].replace('crate::',''));v=(row['size'],row['alignment'])
  assert k not in table or table[k]==v,('layout-query-disagrees',k)
  table[k]=v
 closure_root=V/'swift-guarded-snapshot-source146-closure-layouts'
 closure_meta=json.loads((closure_root/'layout-archive.json').read_bytes());closure_data=(closure_root/'compiler.stdout.gz').read_bytes()
 assert hashlib.sha256(closure_data).hexdigest()==closure_meta['archive_sha256']
 closure_raw=gzip.decompress(closure_data)
 assert hashlib.sha256(closure_raw).hexdigest()==closure_meta['raw_sha256']
 closures=json.loads((closure_root/'results.json').read_bytes())
 assert closures['production_bodies_unchanged'] and len(closures['closures'])==6
 for row in closures['closures']:
  line=row['exact_raw_line'];assert line.encode() in closure_raw
  m=re.fullmatch(r'print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes',line);assert m
  k=key(m[1]);v=(int(m[2]),int(m[3]));assert v==(row['bytes'],row['alignment'])
  assert k not in table or table[k]==v,('closure-layout-disagrees',k)
  table[k]=v
 return table,rows

def split(t):
 result=[];start=0;stack=[]
 pairs={')':'(',']':'[','>':'<','}':'{'}
 for i,c in enumerate(t):
  if c in '([<{':stack.append(c)
  elif c in ')]>}':
   if stack and stack[-1]==pairs[c]:stack.pop()
  elif c==',' and not stack:
   if t[start:i].strip():result.append(t[start:i].strip())
   start=i+1
 if t[start:].strip():result.append(t[start:].strip())
 return result

def resolve(t,table):
 k=key(t)
 if k not in table:k=mirkey(t)
 if k in table:return {'bytes':table[k][0],'alignment':table[k][1],'rule':'exact-source146-compiler-record','compiler_key':k}
 if t in PRIMITIVES:return {'bytes':PRIMITIVES[t],'alignment':min(16, max(1,PRIMITIVES[t])),'rule':'Rust-fixed-primitive-and-bound-aarch64-target','compiler_key':None}
 if t.startswith('&') or t.startswith('*const ') or t.startswith('*mut '):
  inner=t[1:].removeprefix('mut ').strip() if t.startswith('&') else t.split(' ',1)[1]
  fat=inner in ['str','std::path::Path','std::ffi::OsStr','std::ffi::CStr'] or (inner.startswith('[') and ';' not in inner) or inner.startswith('dyn ')
  return {'bytes':16 if fat else 8,'alignment':8,'rule':'inline-reference-only-no-pointee-backing','compiler_key':None}
 m=re.fullmatch(r'\[(.+); (\d+)\]',t)
 if m:
  e=resolve(m.group(1),table)
  if e:return {'bytes':e['bytes']*int(m.group(2)),'alignment':e['alignment'],'rule':'array-element-layout','compiler_key':e.get('compiler_key')}
 # An observed enclosing inline wrapper is a conservative upper bound for T.
 # This never asserts equal extent or spends a padding/alias discount.
 for wrap in ['std::mem::ManuallyDrop','std::mem::MaybeUninit','std::mem::MaybeDangling','std::option::Option']:
  w=wrap+'<'+k+'>'
  if w in table:return {'bytes':table[w][0],'alignment':table[w][1],'rule':'observed-inline-containing-wrapper-upper-bound','compiler_key':w}
 return None

ELEMENTS=['Type','std::option::Option<Type>','experimental::metadata::Signature','experimental::metadata::Import','experimental::metadata::Function','experimental::metadata::Global','experimental::metadata::Export','experimental::metadata::Segment','experimental::validate::Control','u32']

def generic_binding(t,table):
 """Source-closed monomorphization roster, not arbitrary generic replacement."""
 k=key(t);candidates=None;obligation=None
 if k=='T':candidates=ELEMENTS;obligation='actual219 Buffer push/reserve/get value element roster'
 elif k=='std::option::Option<T>':candidates=['std::option::Option<experimental::validate::Control>','std::option::Option<std::option::Option<Type>>'];obligation='only Buffer<Control>/Buffer<Option<Type>> pop callsites in accepted219 closure'
 elif k=='std::option::Option<&mut T>':candidates=['std::option::Option<&mut experimental::metadata::Function>','std::option::Option<&mut experimental::validate::Control>'];obligation='only Function get_mut and Control last_mut callsites'
 elif k in ['experimental::account::Buffer<T>','std::vec::Vec<T>',"std::slice::Iter<'_, T>",'std::option::Option<&T>']:
  candidates=[k.replace('T',e) for e in ELEMENTS];obligation='all10 actual Buffer element types and reserve iteration, conservatively across each generic body'
 elif k=='D':candidates=['experimental::metadata::SwiftDeclaration'];obligation='selected validator invokes metadata read only with SwiftDeclaration'
 elif k in ['experimental::metadata::Metadata<D>','std::result::Result<experimental::metadata::Metadata<D>, experimental::Failure>']:
  candidates=[k.replace('<D>','<experimental::metadata::SwiftDeclaration>')];obligation='selected validator invokes metadata read only with SwiftDeclaration'
 elif k=='experimental_swift_reactor::retained_profile_loader_v1::Bytes<N>':
  candidates=['experimental_swift_reactor::retained_profile_loader_v1::Bytes<4096>','experimental_swift_reactor::retained_profile_loader_v1::Bytes<16384>'];obligation='only authored STR_CAP4096/PROCESS_CAP16384 instantiations in selected219 closure'
 elif k=='[u8; N]':candidates=['[u8; 4096]','[u8; 16384]'];obligation='only authored STR_CAP4096/PROCESS_CAP16384 instantiations in selected219 closure'
 if candidates is None:return None
 observations=[resolve(c,table) for c in candidates]
 if any(o is None for o in observations):return None
 return {'bytes':max(o['bytes'] for o in observations),'alignment':max(o['alignment'] for o in observations),'rule':'maximum-over-closed-actual-source-instantiations','compiler_key':None,'candidates':candidates,'observations':observations,'source_obligation':obligation}
