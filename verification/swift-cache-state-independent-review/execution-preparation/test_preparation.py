"""Reviewer tooling controls. No candidate is admitted/opened/executed here."""
from copy import deepcopy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from harness import HERE,ROOT,bounded,compare_public,protocol,sha
from future_runner import gate,stage_candidate,safe_relative,cases,materialize_variant

DRIVER=Path(sys.argv[1]) if len(sys.argv)>1 else None
OUTPUT=Path(sys.argv[2]) if len(sys.argv)>2 else None
COUNTS={'checks':0,'stub_executions':0}

def valid_shape():
 return {'schema':1,'status':'admitted-independent-cache-state-execution',
  'preaccess_seal_sha256':'1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c',
  'getter_selection_sha256':'80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1',
  'candidate_seal':'verification/swift-cache-state-implementation/NOT-ADMITTED-seal.json',
  'crate_entry':'verification/swift-cache-state-implementation/NOT-ADMITTED-lib.rs',
  'source_members':['verification/swift-cache-state-implementation/NOT-ADMITTED-lib.rs'],
  'review_output_directory':'verification/swift-cache-state-independent-review/implementation-review-NOT-ADMITTED',
  'candidate_seal_sha256':'1'*64,'reviewer_preparation_sha256':'2'*64,'rustc_sha256':'3'*64,
  'rustc':'/NOT-ADMITTED/rustc','rustc_version':'not a real compiler receipt','edition':'2021'}

class Controls(unittest.TestCase):
 def check(self,value):
  COUNTS['checks']+=1
  if not value: self.fail('tooling consistency control failed')

 def stub(self,name,control):
  if DRIVER is None: self.skipTest('self-owned protocol compiler unavailable')
  path=OUTPUT/name; path.mkdir()
  inputs=[]
  for key,payload in [('stream',b'protocol stream'),('profile',b'protocol profile'),('context',bytes(control))]:
   p=path/key; p.write_bytes(payload); inputs.append(p)
  output=path/'report'
  r=bounded([str(DRIVER),*[str(p) for p in inputs],str(output)],ROOT,path,'run',seconds=10)
  COUNTS['stub_executions']+=1
  self.check(r['exit_code']==0 and not r['timed_out'] and not r['output_truncated'])
  return protocol(Path(r['stdout']).read_bytes()),output.read_bytes()

 def test_01_gate_refuses_before_any_candidate_read(self):
  base=valid_shape()
  self.check(gate(base)==base) # Schema consistency only, not an admission.
  mutations=[('status','producer-complete'),('preaccess_seal_sha256','0'*64),
   ('getter_selection_sha256','0'*64),('candidate_seal','verification/elsewhere/seal.json'),
   ('crate_entry','verification/swift-cache-state-implementation/../../other.rs'),
   ('review_output_directory','verification/swift-cache-state-independent-review/preaccess'),
   ('source_members',[]),('rustc','rustc'),('edition','unsafe-open-ended')]
  with patch.object(Path,'read_bytes',side_effect=AssertionError('candidate access forbidden')) as read:
   for key,value in mutations:
    d=deepcopy(base); d[key]=value
    with self.assertRaises(ValueError): stage_candidate(d,Path('/not-created'))
   self.check(read.call_count==0)

 def test_02_closed_paths_and_bound_batch(self):
  for name in ['../outside','/absolute','a/../b','a\\b']:
   with self.assertRaises(ValueError): safe_relative(name)
  for kind,start,count in [('private',0,1),('basics',-1,1),('basics',0,65),('basics',0,0)]:
   with self.assertRaises(ValueError): list(cases(kind,start,count))
  self.check(len(list(cases('basics',0,64)))==39)

 def test_03_independent_materialization_matches_frozen_raw_bytes(self):
  frozen=json.loads((HERE.parent/'preaccess/fixtures/cases.json').read_text())
  schema=json.loads((HERE.parent/'preaccess/fixtures/schema.json').read_text())
  for c,materialized in zip(frozen,cases('basics',0,64)):
   for key,payload in zip(['stream','profile','context'],materialized['payload']):
    self.check(payload==(HERE.parent/'preaccess/fixtures'/c[key]).read_bytes())
  for c in frozen:
   if not c['cap']: continue
   s,p,x=materialize_variant(c['raw_records'],c['config'],schema['profile_rows'])
   base=HERE.parent/'preaccess/fixtures'
   self.check(s==(base/c['stream']).read_bytes())
   self.check(p==(base/c['profile']).read_bytes())
   self.check(x==(base/c['context']).read_bytes())

 def test_04_all_public_getter_positions_via_self_owned_protocol(self):
  for index,(b,r) in enumerate([(b,0) for b in range(7)]+[(1,r) for r in range(18)]):
   d,report=self.stub(f'getter-{index}-{b}-{r}',[1,b,r,0,0])
   self.check(d['cache_state_words']==[b,r]+list(range(1002,1026))+[0]*6)
   self.check(d['framing_words']==[5,71,72,49152,73,74,75,76,15,3,77,78,0,1,0,0])
   self.check(d['envelope_words']==[2,0]+list(range(202,214))+[0,0])
   self.check(d['aggregate_authority']==[0]*4 and d['envelope_metrics']==0)
   self.check(d['input_before']==d['input_after'])
   self.check(len(report)==49152 and set(report)=={0x3b})
  for mask in [1,2,4,8,15]:
   d,_=self.stub(f'authority-bits-{mask}',[1,1,0,mask,0])
   bits=[int(bool(mask&(1<<i))) for i in range(4)]
   self.check(d['aggregate_authority']==bits and d['cache_state_words'][26:30]==bits)

 def test_05_outer_error_preserves_exact_tuple_and_partial_bytes(self):
  d,report=self.stub('outer-error',[0,0,0,0,0])
  self.check(d['api_result']=='Err' and d['error']==[6,8,23,17,0])
  self.check(all(d[k] is None for k in ['cache_state_words','framing_words','envelope_words','aggregate_authority']))
  self.check(report==b'partial' and d['output_position']==7)

 def test_06_driver_does_not_normalize_bad_authority_or_short_report(self):
  d,report=self.stub('bad-authority',[1,1,0,15,0])
  self.check(d['aggregate_authority']==[1]*4 and d['cache_state_words'][26:30]==[1]*4)
  failures=compare_public(d,d['cache_state_words'],report,bytes(8192))
  self.check('authority getter became true' in failures)
  d,report=self.stub('short-report',[2,1,0,0,0])
  self.check('fixed report length/position' in compare_public(d,d['cache_state_words'],report,bytes(8192)))
  d,report=self.stub('bad-reserved',[1,1,0,0,1])
  self.check(d['cache_state_words'][30:]==[9001,9002])
  self.check('cache reserved words' in compare_public(d,d['cache_state_words'],report,bytes(8192)))

 def test_07_protocol_counterexamples_fail_closed(self):
  d,_=self.stub('protocol-baseline',[1,1,0,0,0])
  for field,value in [('protocol',2),('api_result','Accepted'),('cache_state_words',[0]*31),('layouts',[0]*5),('error',[0]*5)]:
   mutated=deepcopy(d); mutated[field]=value
   with self.assertRaises(ValueError): protocol(json.dumps(mutated).encode())
  for field,value in [('input_after','unknown'),('input_positions_after',[0,0]),('output_position','unknown'),('output_after',[0]*7)]:
   mutated=deepcopy(d); mutated[field]=value
   with self.assertRaises(ValueError): protocol(json.dumps(mutated).encode())
  mutated=deepcopy(d); mutated['api_result']='Err'; mutated['error']=[6,8,0,0,0]
  with self.assertRaises(ValueError): protocol(json.dumps(mutated).encode())

 def test_08_timeout_and_output_cap_join_owned_child(self):
  if OUTPUT is None: self.skipTest('owned command output directory absent')
  r=bounded([sys.executable,'-B','-c','import time; time.sleep(5)'],ROOT,OUTPUT,'timeout',seconds=0.2)
  self.check(r['timed_out'] and r['exit_code'] is not None)
  r=bounded([sys.executable,'-B','-c','import sys; sys.stdout.write("x"*8192)'],ROOT,OUTPUT,'output-cap',seconds=5,cap=1024)
  self.check(r['output_truncated'] and Path(r['stdout']).stat().st_size==1024)

 def test_09_driver_preconditions_are_not_API_observations(self):
  if DRIVER is None: self.skipTest('self-owned protocol compiler unavailable')
  path=OUTPUT/'preconditions'; path.mkdir()
  stream=path/'stream'; stream.write_bytes(b'stream')
  context=path/'context'; context.write_bytes(bytes([1,1,0,0,0]))
  profile=path/'profile'; profile.write_bytes(b'profile')
  existing=path/'existing'; existing.write_bytes(b'preserve existing output')
  attempts=[('alias',[str(stream),str(stream),str(context),str(path/'alias-output')]),
   ('existing',[str(stream),str(profile),str(context),str(existing)]),
   ('missing',[str(path/'missing'),str(profile),str(context),str(path/'missing-output')]),
   ('directory',[str(path),str(profile),str(context),str(path/'directory-output')]),
   ('argument-count',[])]
  for name,args in attempts:
   r=bounded([str(DRIVER),*args],ROOT,path,name,seconds=10)
   self.check(r['exit_code']==64 and Path(r['stdout']).read_bytes()==b'')
  self.check(existing.read_bytes()==b'preserve existing output')
  self.check(not (path/'alias-output').exists())

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 print(json.dumps({'methods':result.testsRun,**COUNTS,'failures':len(result.failures),'errors':len(result.errors),
  'skips':len(result.skipped),'scope':'reviewer driver/orchestration protocol only',
  'candidate_source_accesses':0,'candidate_Rust_semantic_executions':0,'product_tests':0}))
 raise SystemExit(not result.wasSuccessful())
