#!/usr/bin/env python3
"""Prepare an additive unused helper overlay; never execute product code."""
from pathlib import Path
import difflib,hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
BASE=ROOT/'verification/swift-guarded-snapshot-scope-authority-correction'
SRC=BASE/'source/vm/src'
I='experimental_swift_reactor/cache/initial_profile_v1.rs'
C='experimental_swift_reactor/control.rs'
HELPER='experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
ACCEPTED=[
 ('guarded-snapshot-writer-work-host-acceptance.json','21251a3aef2d42373ba71711f8eb389634294d4b5b3b61388e718bfb0a25e281'),
 ('guarded-snapshot-authority-work-host-acceptance.json','82913dae316073164e82b661cab7f6baf83a68879a25c85c97fc014d56da0b73'),
 ('guarded-snapshot-encoder-work-host-acceptance.json','757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351'),
]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def write(name,value):
 path=HERE/name;raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
 if '--verify' in sys.argv:assert path.read_bytes()==raw,('prepared output drift',name)
 else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
def write_text(name,value):
 path=HERE/name;raw=value.encode()
 if '--verify' in sys.argv:assert path.read_bytes()==raw,('prepared text drift',name)
 else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)

def definition(path,marker):
 data=(SRC/path).read_bytes();start=data.index(marker.encode())
 context=data.rfind(b'\n',0,start)+1
 while context:
  previous=data.rfind(b'\n',0,context-1)+1
  if data[previous:context].strip().startswith(b'#['):context=previous
  else:break
 i=data.index(b'{',start);depth=0;state='code';block=0
 while i<len(data):
  pair=data[i:i+2];char=data[i:i+1]
  if state=='line':
   if char==b'\n':state='code'
  elif state=='block':
   if pair==b'/*':block+=1;i+=1
   elif pair==b'*/':
    block-=1;i+=1
    if block==0:state='code'
  elif state=='string':
   if char==b'\\':i+=1
   elif char==b'"':state='code'
  elif pair==b'//':state='line';i+=1
  elif pair==b'/*':state='block';block=1;i+=1
  elif char==b'"':state='string'
  elif char==b'{':depth+=1
  elif char==b'}':
   depth-=1
   if depth==0:
    end=i+1
    if data[end:end+1]==b'\n':end+=1
    return data[context:end],{'path':path,'marker':marker,'line':data[:start].count(b'\n')+1,
       'body_sha256':sha(data[start:end]),'context_sha256':sha(data[context:end]),'context_bytes':end-context}
  i+=1
 raise AssertionError(('unclosed definition',path,marker))

def main():
 inputs=[];accept={}
 for name,expected in ACCEPTED:
  path=ROOT/'verification/swift-semantic-adapter-root-review'/name;raw=path.read_bytes()
  assert sha(raw)==expected;accept[name]=json.loads(raw)
  inputs.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':expected})
 for name,expected in [('seal.json','351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c'),
                       ('source-manifest.json','6f835a7607d319966204225bde1e4716bcaa4d53260242b36c3bd50f1d1f45a1')]:
  raw=(BASE/name).read_bytes();assert sha(raw)==expected
  inputs.append({'path':str((BASE/name).relative_to(ROOT)),'bytes':len(raw),'sha256':expected})
 manifest=json.loads((BASE/'source-manifest.json').read_text())
 assert len(manifest['members'])==144 and manifest['source_tree_sha256']=='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
 for row in manifest['members']:
  raw=(BASE/'source/vm'/row['path']).read_bytes()
  assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],row['path']
 base=(SRC/I).read_text();needle='fn proposed_emission_work_v1('
 assert base.count(needle)==1
 overlay=base.replace(needle,'// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\n'+needle)
 write_text('overlay/vm/src/'+I,overlay)
 helper=(HERE/'overlay/vm/src'/HELPER).read_bytes()
 assert helper.count(b'checked_snapshot_emission_bound_v1')==1
 assert b'checked_snapshot_emission_bound_v1(' not in overlay.encode()
 assert b'Err(AError::WorkAuditPending)' in overlay.encode()
 delta=''.join(difflib.unified_diff(base.splitlines(True),overlay.splitlines(True),
    fromfile='authority225/source/vm/src/'+I,tofile='emission-overlay/vm/src/'+I))
 delta+=''.join(difflib.unified_diff([],helper.decode().splitlines(True),
    fromfile='/dev/null',tofile='emission-overlay/vm/src/'+HELPER))
 write_text('source-delta.patch',delta)
 # Exact real type declarations close the pure arithmetic host crate. No
 # substitute error, mocked engine, proof constructor or VM module is used.
 specs=[('experimental/swift.rs','pub struct SwiftValidationUsage {'),
   ('experimental_wasi/mod.rs','pub enum Resource {'),
   ('experimental_wasi/mod.rs','pub enum WasiFailure {'),
   ('experimental_wasi/mod.rs','pub struct WasiReservations {'),
   ('experimental_wasi/mod.rs','pub struct WasiUsage {')]
 for name in ['SwiftReservationCategory','SwiftReservationUsage','SwiftReservations','SwiftDeadlineOrigin',
   'SwiftRunStage','SwiftRunResource','SwiftRunFailureKind','SwiftCleanupInvariant','SwiftLiveUsage','SwiftRunUsage','SwiftRunFailure']:
  kind='enum' if name in ['SwiftReservationCategory','SwiftDeadlineOrigin','SwiftRunStage','SwiftRunResource','SwiftRunFailureKind','SwiftCleanupInvariant'] else 'struct'
  specs.append((C,'pub '+kind+' '+name+' {'))
 specs += [(C,'pub(crate) enum SnapshotStopV1'),(C,'pub(crate) enum SnapshotAdmissionErrorV1'),
   (I,'struct SnapshotShapeV1'),(I,'fn checked_add_v1('),(I,'fn checked_mul_v1('),(I,'fn snapshot_shape_v1(')]
 chunks=[];extracted=[]
 for path,marker in specs:
  raw,binding=definition(path,marker);chunks.append(raw);extracted.append(binding)
 write_text('host/source-types.rs',b'\n'.join(chunks).decode())
 e=accept['guarded-snapshot-encoder-work-host-acceptance.json']['accepted_interface']
 assert e['fixed_initialization']==14224 and e['per_call_maximum']==26+68*515+39*(9*515)+139*513+4096==291214
 assert accept['guarded-snapshot-writer-work-host-acceptance.json']['writer_formula']=='1217+4259B+122A'
 fixed=e['fixed_initialization']+1217+4096
 per_block=e['per_call_maximum']+4259+32*122
 assert (fixed,per_block)==(19537,299377)
 production=[]
 for row in manifest['members']:
  if row['path']=='src/'+I:raw=overlay.encode()
  else:raw=(BASE/'source/vm'/row['path']).read_bytes()
  production.append({'path':row['path'],'bytes':len(raw),'sha256':sha(raw)})
 production.append({'path':'src/'+HELPER,'bytes':len(helper),'sha256':sha(helper)})
 production.sort(key=lambda x:x['path'])
 write('source-manifest.json',{'schema':1,'base_source_members':144,'members':production,
    'source_members':145,'tree_format':'sha256 canonical sorted JSON member roster',
    'source_tree_sha256':sha(canonical(production))})
 stable=[]
 for marker in ['fn proposed_emission_work_v1(',"fn begin_snapshot_access_v1<'c>(",'fn write_snapshot_v1(']:
  _,binding=definition(I,marker);stable.append(binding)
 write('input-custody.json',{'schema':1,'inputs':inputs,'base_source_members_verified':144,
   'base_source_tree_sha256':manifest['source_tree_sha256'],'base_sealed_member_count':225,
   'unchanged_actual_path_bindings':stable,'host_real_type_and_pure_shape_extractions':extracted,
   'host_types_sha256':sha((HERE/'host/source-types.rs').read_bytes()),
   'helper_sha256':sha(helper),'authority_source_delta_inherited':True,
   'loader_descriptor_count_mismatch_pending':{'unchanged_source_count':144,'unchanged_support_count':11,'candidate_source_members':145,'genuine_descriptor_qualification_claimed':False},
   'no_engine_or_hosted_harness_imported_or_executed':True})
 write('derivation.json',{'schema':1,'status':'pure emission arithmetic candidate only',
   'accepted_encoder_fixed':e['fixed_initialization'],'accepted_encoder_per_nonempty_call':e['per_call_maximum'],
   'encoder_per_call_expansion':{'call_fixed':26,'I':68*515,'D':39*(9*515),'W':139*513,'Q':4096},
   'accepted_writer_fixed':1217,'accepted_writer_per_block':4259,'accepted_writer_per_attempt':122,
   'attempts_per_block_max':32,'native_requested_bytes_coefficient':32,'transfer_initializer_once':4096,
   'fixed_sum':fixed,'per_block_sum':per_block,'candidate':'19537+299377B+32E',
   'actual_writer_terminal_None_calls':0,'encoder_failed_call_retries_permitted':False,
   'getter_double_charge':False,'original_execution_work_ceiling':1000000000,
   'maximum_geometry':{'extent':69765152,'blocks':17033,'emission':fixed+per_block*17033+32*69765152},
   'helper_source_action_bound':{'entry_return':2,'two_shape_field_fetches':2,'four_checked_operations':4,
      'four_eager_Arithmetic_errors':4,'four_ok_or_inspect_and_output':8,'three_question_operators':6,'three_local_bindings':3,'total':29},
   'placement':'If later selected, evaluate after actual shape under already paid planning and pre-admitted helper storage; no current invocation. The helper29 cannot be funded solely by the emission debit it computes.',
   'authority_delta_placement':'Accepted extra19 belongs to earlier pre-admitted construction routing; excluded from emission.',
   'initializer_attribution':'One4096 initialization included here; future begin7930 also names that same initialization and must not charge two occurrences.',
   'loader_descriptor_integration_pending':'Unchanged retained loader descriptor states source_count144/support_count11. This145-member unused arithmetic overlay does not claim a genuine descriptor; coordinated integration must fix/requalify exact descriptor and support binding separately.',
   'operational_work_selected':False,'WorkAuditPending_preserved':True})
 print(json.dumps({'source_members':145,'source_tree_sha256':sha(canonical(production)),
   'candidate':'19537+299377B+32E','helper_actions':29,'actual_invocation_added':False},sort_keys=True))
if __name__=='__main__':main()
