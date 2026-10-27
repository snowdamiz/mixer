"""Resolve every concrete MIR identity against actual compiler type layouts."""
from pathlib import Path
import json,re
from probe import ROOT,INPUT,sha,save
from project import split_top
def normalize(t):
 t=re.sub(r'&\s*\'[^ ,>]+\s*', '&', t)
 t=t.replace("'static","'_")
 aliases={'control':'experimental_swift_reactor::control','initial_profile_v1':'experimental_swift_reactor::cache::initial_profile_v1','accounted':'experimental_wasi::accounted','swift':'experimental::swift','retained_profile_loader_v1':'experimental_swift_reactor::retained_profile_loader_v1','execute':'execute'}
 for old,new in aliases.items():t=re.sub(r'(?<![\w:])'+old+r'::',new+'::',t)
 named={}
 for name in ['SnapshotAccessV1','SnapshotAdmissionErrorV1','SnapshotStopV1','SnapshotScopeV1','SnapshotRunV1','SnapshotScopeFinishV1','SnapshotScopeBorrowV1','SnapshotPreScopeFailureV1','SnapshotWasiAttachmentV1','OriginalAdoptionV1','SnapshotAdoptionV1']:
  named[name]='experimental_swift_reactor::control::'+name if name not in ['SnapshotAccessV1'] else 'experimental_swift_reactor::cache::initial_profile_v1::'+name
 for name in ['SnapshotShapeV1','SnapshotPlanV1','SnapshotPhaseStorageV1','SnapshotProgressV1','SnapshotCauseV1','SnapshotExportErrorV1','SnapshotObservationV1','SnapshotAttemptV1','SnapshotOuterV1','SnapshotWriterV1','SnapshotPrimaryRetirementV1','OriginalBranchV1','OriginalAccessV1','SnapshotBranchV1']:
  named[name]='experimental_swift_reactor::cache::initial_profile_v1::'+name
 for name in ['SnapshotEncodeErrorV2','SnapshotViewV2','SnapshotCursorV2','SnapshotBlockV2']:
  named[name]='experimental::swift::snapshot_encoder_v2::'+name
 for name in ['SelectedSnapshotBodyV1','AdoptionBodyV1','SelectedValidatedProfileV1','LoaderProvenanceV1']:
  named[name]='experimental_swift_reactor::retained_profile_loader_v1::'+name
 for name in ['SwiftDeadlineOrigin','SwiftRunBudget','SwiftRunFailure','SwiftRunUsage','ReservationTicket','SwiftReservationCategory','RuntimeControl','AdoptedProof','Cursor','Fault']:
  named[name]='experimental_swift_reactor::control::'+name
 named.update({'WasiBudget':'experimental_wasi::WasiBudget','WasiUsage':'experimental_wasi::WasiUsage','WasiGrants':'experimental_wasi::WasiGrants','Instant':'std::time::Instant','Duration':'std::time::Duration','TryFromIntError':'std::num::TryFromIntError','Infallible':'std::convert::Infallible','Result':'std::result::Result','Option':'std::option::Option','ControlFlow':'std::ops::ControlFlow'})
 for old,new in named.items():t=re.sub(r'(?<![\w:])'+old+r'\b',new,t)
 # Source paths are identity-bearing for anonymous closures.
 t=t.replace(str(INPUT/'source/vm/src')+'/','source/')
 t=re.sub(r'\s+',' ',t).strip()
 # Default second ControlFlow parameter is unit.
 t=t.replace(', ()>', '>') if t.startswith('std::ops::ControlFlow<') else t
 return t
def instantiate(t,profile='original',T=None):
 p={'Failure':'control::SwiftRunFailure','Retirement':'()'} if profile=='original' else {'Failure':'SnapshotPreScopeFailureV1','Retirement':'Result<(),control::SwiftRunFailure>'}
 b={'Output':'initial_profile_v1::InitialProfileConstructionOutcomeV1','Attempt':'()','Storage':'()','Access':"OriginalAccessV1<'_>"} if profile=='original' else {'Output':'SnapshotOuterV1','Attempt':'SnapshotAttemptV1','Storage':'SnapshotPhaseStorageV1','Access':"SnapshotAccessV1<'_>"}
 for a,v in p.items():t=re.sub(r'<P as [^>]+>::'+a+r'\b',v,t)
 for a,v in b.items():t=re.sub(r'<B as [^>]+>::'+a+(r"<'_>" if a=='Access' else r'\b'),v,t)
 t=re.sub(r'\bB\b','OriginalBranchV1' if profile=='original' else "SnapshotBranchV1<'_>",t)
 if T is not None:t=re.sub(r'\bT\b',T,t)
 return normalize(t)
def table():
 text=(ROOT/'commands/actual-monomorphic-layouts/stdout').read_text();out={}
 for line in text.splitlines():
  m=re.fullmatch(r'print-type-size type: `(.*)`: (\d+) bytes, alignment: (\d+) bytes',line)
  if m:
   key=normalize(m[1]);value={'bytes':int(m[2]),'alignment':int(m[3]),'actual_identity':m[1],'evidence':'commands/actual-monomorphic-layouts/stdout','raw_line':line}
   if key in out:assert (out[key]['bytes'],out[key]['alignment'])==(value['bytes'],value['alignment'])
   out[key]=value
 if (ROOT/'extra-type-layouts.json').exists():
  for row in json.loads((ROOT/'extra-type-layouts.json').read_text()):
   out[normalize(row['compiler_type'])]={**row,'actual_identity':row['compiler_type']}
 return out
def resolve(t,measured):
 t=normalize(t)
 if t in measured:return measured[t]
 if t.startswith('&'):
  inner=t[1:].strip().removeprefix('mut ')
  fat=inner=='str' or (inner.startswith('[') and ';' not in inner) or inner.startswith('dyn ')
  return {'bytes':16 if fat else 8,'alignment':8,'actual_identity':t,'evidence':'target64 pointer/fat-reference base layout controls'}
 primitives={'()':(0,1),'!':(0,1),'bool':(1,1),'u8':(1,1),'i8':(1,1),'u16':(2,2),'i16':(2,2),'u32':(4,4),'i32':(4,4),'u64':(8,8),'i64':(8,8),'usize':(8,8),'isize':(8,8),'u128':(16,16),'i128':(16,16)}
 if t in primitives:
  size,align=primitives[t];return {'bytes':size,'alignment':align,'actual_identity':t,'evidence':'compiler base layout controls'}
 if t.startswith('fn(') or t.startswith('fn ('):
  return {'bytes':0 if re.search(r'\{.*\}$',t) else 8,'alignment':1 if re.search(r'\{.*\}$',t) else 8,'actual_identity':t,'evidence':'MIR function-item zero size or target64 fn pointer base layout'}
 m=re.fullmatch(r'\[(.*); (\d+)\]',t)
 if m:
  inner=resolve(m[1],measured);return {'bytes':inner['bytes']*int(m[2]),'alignment':inner['alignment'],'actual_identity':t,'evidence':'array layout of actual inner type times fixed source length'}
 raise KeyError(t)
def variants(f,r):
 t=r['compiler_type'];name=f['name'];profiles=['original','selected'] if f['funding_class'] in ['shared-adoption','shared-constructor'] else ['selected' if f['funding_class']!='common' else 'original']
 ts=['std::fs::Metadata','u64'] if '::io_result' in name else ["SnapshotViewV2<'_>","SnapshotCursorV2<'_>","Option<SnapshotBlockV2<'_>>"] if '::encode_result' in name else ['SnapshotPhaseStorageV1'] if name.endswith('::end_construction_phase_with_wasi') else ['Option<experimental_swift_reactor::cache::SwiftFunctionCache>'] if f['source']['path']=='experimental_swift_reactor/cache.rs' and f['source']['return_line']<1800 else [None]
 return [(p,T,instantiate(t,p,T)) for p in profiles for T in ts]
if __name__=='__main__':
 data=json.loads((ROOT/'raw-inventory.json').read_text());measured=table();requests={};unresolved={}
 for f in data['functions']:
  for r in f['roles']:
   for p,T,t in variants(f,r):
    try:requests[t]=resolve(t,measured)
    except KeyError:unresolved.setdefault(t,[]).append({'function':f['id'],'role':r['id']})
 save(ROOT/'resolved-layouts.json',requests);save(ROOT/'unresolved-layouts.json',unresolved)
 print(json.dumps({'resolved':len(requests),'unresolved':len(unresolved)}));print('\n'.join(unresolved))
