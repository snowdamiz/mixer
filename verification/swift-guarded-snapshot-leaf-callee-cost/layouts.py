"""Exact qualified matching of released source146 compiler layout DATA."""
import collections,gzip,hashlib,json,re
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];V=R/'verification'
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
RELEASE=V/'swift-semantic-adapter-root-review/guarded-snapshot-full-source146-layout-data-release.json'
RAWPATH=V/'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz'
STD={'Option':'std::option::Option','Result':'std::result::Result','Vec':'std::vec::Vec','ControlFlow':'std::ops::ControlFlow','Infallible':'std::convert::Infallible','Iter':'std::slice::Iter','IterMut':'std::slice::IterMut','IntoIter':'std::array::IntoIter','Zip':'std::iter::Zip','Duration':'std::time::Duration','Instant':'std::time::Instant','Layout':'std::alloc::Layout','Atomic':'std::sync::atomic::Atomic','Ordering':'std::sync::atomic::Ordering'}
CONTROL='Cursor Fault ReservationTicket AdoptedProof AdoptionBodyV1 RuntimeControl SwiftRunBudget SnapshotScopeBorrowV1 SwiftRunFailure SwiftRunUsage SwiftCleanupInvariant SwiftDeadlineOrigin SwiftLiveUsage SwiftReservationCategory SwiftReservationUsage SwiftReservations SwiftRunFailureKind SwiftRunResource SwiftRunStage SnapshotAdmissionErrorV1 SnapshotStopV1 SnapshotPreScopeFailureV1'.split()
CACHE='Partial SwiftFunctionCache SwiftSlot SwiftResident ScanPlan CacheConstructionFailure CacheCleanupTail CacheConstructionPhase'.split()
LOCAL='InitialProfileConstructionOutcomeV1 SelectedInitialProfileV1 ProfileHeaderErrorV1 UnverifiedProfileHeaderV1 SnapshotAttemptV1 SnapshotBranchV1 SnapshotPrimaryRetirementV1 SnapshotOuterV1 SnapshotPhaseStorageV1'.split()
MAPPING={**STD,**{n:'experimental_swift_reactor::control::'+n for n in CONTROL},**{n:'experimental_swift_reactor::cache::'+n for n in CACHE},**{n:'experimental_swift_reactor::cache::initial_profile_v1::'+n for n in LOCAL},'WasiContext':'experimental_wasi::WasiContext','WasiUsage':'experimental_wasi::WasiUsage','AccountedWasi':'experimental_wasi::accounted::AccountedWasi','PinRecord':'experimental::cache::PinRecord','Patch':'experimental::cache::decode::Patch','DecodedFunction':'experimental::cache::DecodedFunction','SwiftValidationUsage':'experimental::swift::SwiftValidationUsage','Live':'experimental_swift_reactor::control::Live','ProfileRowsObservationV1':'experimental_swift_reactor::diagnostic_profile::ProfileRowsObservationV1','ProfileAdapterErrorV1':'experimental_swift_reactor::diagnostic_profile::ProfileAdapterErrorV1'}
def qualified(t):
 if '{closure@' in t:return re.sub(r'\{closure@.*?/vm/src/',r'{closure@src/',t)
 def token(m):
  x=m[0]
  for a,b in [('control::','experimental_swift_reactor::control::'),('accounted::','experimental_wasi::accounted::'),('initial_profile_v1::','experimental_swift_reactor::cache::initial_profile_v1::'),('swift::','experimental::swift::')]:
   if x.startswith(a):return b+x[len(a):]
  return MAPPING.get(x,x)
 return re.sub(r'\b(?:[A-Za-z_]\w*::)*[A-Za-z_]\w*',token,t)

def load_records():
 release=RELEASE.read_bytes()
 if sha(release)!='7e9a1d8e2602e5b8eb8dfdad61da7f4c816ecd52b6e9beebd8759f173346e7ad':raise ValueError('full layout DATA release changed')
 archive=RAWPATH.read_bytes();raw=gzip.decompress(archive)
 if sha(archive)!='1ddc23c6274a1c4f148e9d4a389aa0aeaa070384929280de044f4889a49ec9ec' or len(raw)!=7641979 or sha(raw)!='6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a':raise ValueError('full layout DATA identity')
 records=collections.defaultdict(list);current=None
 for no,line in enumerate(raw.decode().splitlines(),1):
  m=re.fullmatch(r'print-type-size type: `(.+)`: (\d+) bytes, alignment: (\d+) bytes',line)
  if m:
   current=dict(compiler_type=m[1],qualified_key=qualified(m[1]),size=int(m[2]),alignment=int(m[3]),line=no,records=[line]);records[current['qualified_key']].append(current)
  elif line.startswith('print-type-size '):
   if current is None:raise ValueError('orphan compiler record')
   current['records'].append(line)
 if sum(len(v) for v in records.values())!=3072:raise ValueError('complete type record count')
 return records,dict(path=str(RAWPATH.relative_to(R)),archive_sha256=sha(archive),raw_sha256=sha(raw),raw_bytes=len(raw),release_path=str(RELEASE.relative_to(R)),release_sha256=sha(release))

def reconcile(ledger,contract):
 records,binding=load_records();keys=sorted({t for r in contract['exports'].values() for t in r['native']});found={};missing=[]
 for key in keys:
  q=qualified(key);matches=records.get(q,[])
  if matches:
   values={(r['size'],r['alignment']) for r in matches}
   if len(values)!=1:raise ValueError('qualified compiler layout ambiguity '+q)
   size,alignment=next(iter(values));found[key]=dict(qualified=q,size=size,alignment=alignment,kind='exact-qualified-compiler-print-observation',records=matches)
  elif re.fullmatch(r'\[(Option<ReservationTicket>|usize); [34]\]',key):
   element,count=key[1:-1].split('; ');size=ledger['layouts'].get(element)
   if size is None:raise ValueError('array element observation missing')
   found[key]=dict(qualified=q,size=size*int(count),alignment=8,kind='exact-fixed-array-of-observed-element',element=element,element_size=size,count=int(count))
  else:missing.append(dict(key=key,qualified=q,reason='no exact qualified record; no short-name or max-value fallback'))
 return dict(schema=1,source_tree_sha256=SOURCE,compiler_binding=binding,input_keys=len(keys),resolved=found,missing=missing,short_name_fallback=False,actual_payload_body_or_backing_qualified=False)

def substitute(ledger,observations):
 for node in ledger['nodes'].values():
  for key in list(node.get('missing_native',{})):
   if key in observations['resolved']:
    n=node['missing_native'].pop(key);size=observations['resolved'][key]['size'];node['known_native']=node.get('known_native',0)+n*size
 return ledger
