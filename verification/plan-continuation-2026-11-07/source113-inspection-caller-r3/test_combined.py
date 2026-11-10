#!/usr/bin/env python3
"""Pure combined-candidate controls; accepted R3 source does not qualify runtime."""
from pathlib import Path
import hashlib, importlib.util, json, sys, tempfile, unittest
from contextlib import contextmanager
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
s=importlib.util.spec_from_file_location('combined_metadata_guard',ROOT/'verification/envelope-rust-1991-default-ci-adoption/offline_guard.py')
guard=importlib.util.module_from_spec(s);s.loader.exec_module(guard);__import__('metadata_guard').install(guard,HERE)
import adopt_envelope as a
@contextmanager
def patched(obj,key,value):
 old=getattr(obj,key);setattr(obj,key,value)
 try:yield
 finally:setattr(obj,key,old)
class MetadataDiagnostics(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=HERE/'control-scratch');self.addCleanup(self.temp.cleanup);self.work=Path(self.temp.name);self.base=a.bind()
 def test_projected_installed_whole_job_is_exact_without_qualification(self):
  p=self.base.verify(True)
  self.assertEqual((p['source_count'],p['source_sha256']),(116,'20d70a1778ffdfc7427f8e87bf0849ddfa956794dec4e9096ddf53a985b03b6f'))
  self.assertTrue(p['installed_job_verified']);self.assertFalse(p['exact_compiler_qualified'])
 def test_actual_owner_bootstrap_116_and_profile24_27(self):
  s=importlib.util.spec_from_file_location('rebound_bootstrap',HERE.parent/'generated-java-ci-integration/bootstrap.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
  owner=b.canonical();profile=owner.load_profile();actual=b.admit_source_inputs(owner,profile)
  self.assertEqual(actual,json.loads((HERE/'source-inputs.json').read_bytes()))
  self.assertEqual((len(profile['sdk_files']),len(profile['adapter_files'])),(24,27))
  self.assertEqual(owner.source_digest(profile['sdk_files']),'a689f5653ff2d353e3b0ae202ee6169d64c03448a56ec1d5fee389a9a8ff536f')
  self.assertEqual(owner.source_digest(profile['adapter_files']),'1e8b5753f4eca13028e37e5d0ffd2d1387c33eb11c80dd20e158b372d50a778c')
 def test_full_job_mutations_refuse(self):
  text=(HERE/'verify.yml.candidate').read_text();p=self.work/'verify.yml'
  for old,new in [('timeout-minutes: 12','timeout-minutes: 13'),('--product mixer -j 2','--product mixer -j 3'),('scripts/ci/prepare-cli-host-tests.py','scripts/ci/other.py'),('swift test --package-path cli -j 2','swift test --package-path cli -j 3'),('export RUSTUP_AUTO_INSTALL=0','export RUSTUP_AUTO_INSTALL=1')]:
   self.assertIn(old,text);p.write_text(text.replace(old,new,1))
   with self.subTest(change=old),patched(a,'WORKFLOW',p),self.assertRaisesRegex(RuntimeError,'Installed ordinary Swift job differs'):self.base.verify(True)
 def test_caller_bootstrap_and_sparse_guard_missing_or_drift_refuse(self):
  original=self.base.regular
  for row in json.loads((HERE/'caller-inputs.json').read_bytes()):
   changed=self.work/'changed';changed.write_bytes((ROOT/row['path']).read_bytes()+b'changed')
   def redirect(p):return original(changed if p==ROOT/row['path'] else p)
   with self.subTest(path=row['path']),patched(self.base,'regular',redirect),self.assertRaisesRegex(RuntimeError,'Pinned source differs'):self.base.verify(True)
   def missing(p):
    if p==ROOT/row['path']:raise FileNotFoundError(str(p))
    return original(p)
   with self.subTest(missing=row['path']),patched(self.base,'regular',missing),self.assertRaises(FileNotFoundError):self.base.verify(True)
 def test_historical18_preserved_and_source_snapshot_not_requalified(self):
  prior=HERE.parent/'source113-sparse-closure-fix-r2';seal=json.loads((prior/'seal.json').read_bytes());self.assertEqual(seal['member_count'],18);self.base.check_rows(prior,seal['members'])
  self.assertEqual(json.loads((prior/'binding.json').read_bytes())['source']['sha256'],'c92cd273b5a9b11846375784f9763a3da82d5df9ed15c2efd3fb589007e1d5c1')
  old=(prior/'adopt_envelope.py').read_text();new=(HERE/'adopt_envelope.py').read_text()
  self.assertEqual(old[old.index('class FreshOutput:'):old.index('def main():')],new[new.index('class FreshOutput:'):new.index('def main():')])
  self.base.validate_profile(self.base.PROFILE_IDENTITY,self.base.PROFILE_SHA256)
  policy=self.base.selection()['execution'];self.assertEqual(policy['required_commands'],40)
 def test_extra_runtime_file_and_symlink_refuse(self):
  extra=HERE/'UNSUPPORTED';extra.write_text('diagnostic')
  try:
   with self.assertRaisesRegex(RuntimeError,'shipping closure'):self.base.verify(True)
  finally:extra.unlink()
  extra.symlink_to(HERE/'binding.json')
  try:
   with self.assertRaisesRegex(RuntimeError,'shipping symlink'):self.base.verify(True)
  finally:extra.unlink()
 def test_source_manifest_mismatch_and_extra_owner_refuse(self):
  original=self.base.module_at
  def changed(name,p):
   module=original(name,p)
   if p==ROOT/'scripts/ci/check-android-generated-java.py':
    source_inputs=module.source_inputs
    def inputs(profile):
     rows=source_inputs(profile);rows['cli/Sources/Unreviewed.swift']={'bytes':1,'sha256':'0'*64};return rows
    module.source_inputs=inputs
   return module
  with patched(self.base,'module_at',changed),self.assertRaisesRegex(RuntimeError,'Current owning source closure differs'):self.base.verify(True)
 def test_each_owning_pin_drift_refuses(self):
  original=self.base.regular
  for name in json.loads((HERE/'source-inputs.json').read_bytes()):
   fake=self.work/'changed';fake.write_bytes(b'metadata diagnostic mutation')
   def redirect(p):return original(fake if p==ROOT/name else p)
   with self.subTest(path=name),patched(self.base,'regular',redirect),self.assertRaisesRegex(RuntimeError,'Pinned source differs'):self.base.verify(True)
 def test_host_only_candidate_dispatch_after_actual_installed_checks(self):
  binding=json.loads((HERE/'binding.json').read_bytes());self.assertFalse(binding['adoption']['allowed'])
  self.assertEqual(binding['adoption']['status'],'CANDIDATE_PENDING_COMBINED_REVIEW')
  self.assertFalse(any(binding['qualification'].values()));self.assertFalse(binding['failed_attempt']['rerun_authorized'])
  self.assertTrue(binding['fixture_dispatch']['host_rust_fixture_after_exact_checks'])
  for key in ('combinedAccepted','runtime','GA','exactWindow'):self.assertFalse(binding['fixture_dispatch'][key])
  calls=[]
  def dispatch(base,out,rustc):
   self.assertTrue(base.verify(True)['installed_job_verified']);calls.append((out,rustc));return 0
  with patched(a,'bind',lambda:self.base),patched(a,'run_fixture',dispatch),patched(sys,'argv',['adopt_envelope.py','run','--out',str(self.work/'never'),'--rustc','/synthetic/no-process']):self.assertEqual(a.main(),0)
  self.assertEqual(calls,[(self.work/'never','/synthetic/no-process')]);self.assertFalse((self.work/'never').exists())
 def refused_main(self,regular,expression):
  calls=[]
  with patched(self.base,'regular',regular),patched(self.base,'load_runner',lambda: calls.append('resource')),patched(a,'bind',lambda:self.base),patched(a,'run_fixture',lambda *args:calls.append('dispatch')),patched(sys,'argv',['adopt_envelope.py','run','--out',str(self.work/'never'),'--rustc','/never']),self.assertRaisesRegex((RuntimeError,FileNotFoundError),expression):a.main()
  self.assertEqual(calls,[]);self.assertFalse((self.work/'never').exists())
 def test_wrong_installed_job_refuses_before_resource_or_dispatch(self):
  p=self.work/'workflow';p.write_text('invalid workflow')
  with patched(a,'WORKFLOW',p):self.refused_main(self.base.regular,'ordinary Swift job')
 def test_missing_raw_review_refuses_before_dispatch(self):
  original=self.base.regular
  def missing(p):
   if p==HERE/'inspection-review.json':raise FileNotFoundError('missing raw accepted R3 review')
   return original(p)
  self.refused_main(missing,'missing raw accepted R3 review')
 def test_rejected_forged_and_mismatched_raw_reviews_cannot_be_resealed(self):
  original=self.base.regular;raw=json.loads((HERE/'inspection-review.json').read_bytes());seal=json.loads((HERE/'seal.json').read_bytes())
  variants=[]
  for field,value in [('verdict','REJECTED'),('verdict','ACCEPT_FORGED'),('source113Proposed','0'*64),('checkerSHA256','0'*64),('patchSHA256','0'*64)]:
   value_map=json.loads(json.dumps(raw))
   if field=='verdict':value_map[field]=value
   else:value_map['candidate'][field]=value
   variants.append(value_map)
  for index,value in enumerate(variants):
   fake=self.work/'review';fake.write_text(json.dumps(value));changed=json.loads(json.dumps(seal))
   for row in changed['members']:
    if row['path']=='inspection-review.json':row.update(bytes=fake.stat().st_size,sha256=self.base.sha(fake))
   changed['tree_sha256']=self.base.tree(changed['members']);fake_seal=self.work/'seal';fake_seal.write_text(json.dumps(changed))
   def redirect(p):return original(fake_seal if p==HERE/'seal.json' else fake if p==HERE/'inspection-review.json' else p)
   with self.subTest(variant=index):self.refused_main(redirect,'Accepted R3 raw review hash differs')
 def test_explicit_focused_test_and_accepted_helper_hashes(self):
  for name,digest in [('cli/Tests/MixerBuildTests/AndroidInspectionPolicyReceiptTests.swift','c8ec4accc3a436c449f8c836e9763423a9cb08fe7fca2af549a76fa4e7b17488'),('scripts/ci/prepare-cli-host-tests.py','77aebba7edd46e3d06dfcf91fa4a9cbd016efc7b06e9dac9b447a32755bf1214')]:self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)

 def test_caller_authority_reseal_rejects_before_acquisition(self):
  import copy
  callers_raw=(HERE/'caller-inputs.json').read_bytes()
  callers=json.loads(callers_raw)
  bootstrap=HERE.parent/'generated-java-ci-integration/bootstrap.py'
  boot=bootstrap.relative_to(ROOT).as_posix()
  original_boot=bootstrap.read_bytes()
  changed_boot=original_boot+b'\n# caller authority regression\n'
  encode=lambda value:(json.dumps(value,indent=2)+'\n').encode()
  identity=lambda raw:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
  variants=[('omitted '+row['path'],encode([r for r in callers if r!=row]),None) for row in callers]
  rebased=copy.deepcopy(callers)
  for row in rebased:
   if row['path']==boot:row.update(identity(changed_boot))
  foreign={'path':'.github/workflows/verify.yml',**identity((ROOT/'.github/workflows/verify.yml').read_bytes())}
  variants.extend([
   ('omitted bootstrap and changed installed bytes',encode([r for r in callers if r['path']!=boot]),changed_boot),
   ('same eight paths and rebased bootstrap identity',encode(rebased),changed_boot),
   ('empty roster',encode([]),None),
   ('foreign extra row',encode(sorted(callers+[foreign],key=lambda r:r['path'])),None),
   ('duplicate caller row',encode(callers+[callers[0]]),None),
   ('foreign roster',encode([foreign]),None),
   ('reordered rows',encode(list(reversed(callers))),None),
   ('same data different raw bytes',callers_raw+b' ',None),
  ])
  for field,value in [('bytes',callers[0]['bytes']+1),('sha256','0'*64)]:
   altered=copy.deepcopy(callers);altered[0][field]=value
   variants.append(('same eight paths wrong '+field,encode(altered),None))
  variants.append(('caller identity carries foreign count',encode({'count':8,'rows':callers}),None))
  original=self.base.regular
  def execute(raw,installed_boot,refuse):
   seal=json.loads((HERE/'seal.json').read_bytes())
   for row in seal['members']:
    if row['path']=='caller-inputs.json':row.update(identity(raw))
   seal['tree_sha256']=self.base.tree(seal['members'])
   if 'total_bytes' in seal:seal['total_bytes']=sum(row['bytes'] for row in seal['members'])
   fake=self.work/'caller';fake.write_bytes(raw)
   fake_seal=self.work/'seal';fake_seal.write_bytes(encode(seal))
   fake_boot=self.work/'bootstrap';fake_boot.write_bytes(installed_boot or original_boot)
   def redirect(p):
    return original(fake if p==HERE/'caller-inputs.json' else fake_seal if p==HERE/'seal.json' else fake_boot if p==bootstrap else p)
   calls=[]
   with patched(self.base,'regular',redirect),patched(self.base,'load_runner',lambda:calls.append('resource')),patched(a,'bind',lambda:self.base),patched(a,'run_fixture',lambda *args:calls.append('dispatch') or 0),patched(sys,'argv',['adopt_envelope.py','run','--out',str(self.work/'never'),'--rustc','/never']):
    if refuse:
     with self.assertRaises((RuntimeError,FileNotFoundError,ValueError,TypeError)):a.main()
    else:self.assertEqual(a.main(),0)
   self.assertEqual(calls,[] if refuse else ['dispatch'])
   self.assertFalse((self.work/'never').exists())
  execute(callers_raw,None,False)
  for label,raw,installed_boot in variants:
   with self.subTest(mutation=label):execute(raw,installed_boot,True)
  with self.subTest(mutation='unchanged authority detects changed installed bootstrap'):
   execute(callers_raw,changed_boot,True)

 def test_diagnostic_reverse_precedes_exact_apple_and_guest_history(self):
  binding=json.loads((HERE/'binding.json').read_bytes())
  owner=self.base.module_at('diagnostic_history_owner',ROOT/'scripts/ci/check-android-generated-java.py')
  actual=owner.source_inputs(owner.load_profile(ROOT))
  source_pair15=a.pair16_predecessor(self.base,binding,actual,owner)
  self.assertEqual(owner.source_digest(source_pair15),binding['pair16_transition']['sourceBefore'])
  source116=a.pair15_predecessor(self.base,binding,source_pair15,owner)
  self.assertEqual(owner.source_digest(source116),binding['pair15_transition']['sourceBefore'])
  source115=a.pair14_predecessor(self.base,binding,source116,owner)
  self.assertEqual(owner.source_digest(source115),binding['pair14_transition']['sourceBefore'])
  source114=a.pair13_predecessor(self.base,binding,source115,owner)
  self.assertEqual(owner.source_digest(source114),binding['pair13_transition']['sourceBefore'])
  source113=a.pair12_predecessor(self.base,binding,source114,owner)
  self.assertEqual(owner.source_digest(source113),binding['pair12_transition']['sourceBefore'])
  source175=a.pair11_predecessor(self.base,binding,source113,owner)
  self.assertEqual(owner.source_digest(source175),binding['pair11_transition']['sourceBefore'])
  source303=a.swift_identity_diagnostic_predecessor(self.base,binding,source175,owner)
  self.assertEqual(owner.source_digest(source303),binding['swift_identity_diagnostic_transition']['sourceBefore'])
  source1b=a.apple_accessibility_successor(self.base,binding,source303,owner)
  self.assertEqual(owner.source_digest(source1b),binding['apple_accessibility_transition']['sourceBefore'])
  source0647=a.sdk_fixture_successor(self.base,binding,source1b,owner)
  self.assertEqual(owner.source_digest(source0647),binding['sdk_fixture_transition']['predecessor']['source113'])
  with self.assertRaisesRegex(RuntimeError,'Apple accessibility current source differs'):a.apple_accessibility_successor(self.base,binding,actual,owner)
 def test_qualification_boolean_types_refuse_resealed_numeric_aliases(self):
  import copy
  original=self.base.regular
  baseline=json.loads((HERE/'binding.json').read_bytes())
  paths=[('qualification',key) for key in baseline['qualification']]+[('adoption','allowed'),('adoption','canonicalAdopted'),('fixture_dispatch','runtime'),('fixture_dispatch','GA'),('swift_identity_diagnostic_transition','qualification'),('pair12_transition','qualification')]+[('pair13_transition',key) for key in ('qualification','actualSixConsumers','nativePass','runtimePass','gaPass')]+[('pair14_transition',key) for key in ('qualification','actualSixConsumers','nativePass','runtimePass','gaPass')]+[('pair15_transition',key) for key in ('qualification','actualSixConsumers','nativePass','runtimePass','gaPass')]+[('pair16_transition',key) for key in ('qualification','actualSixConsumers','nativePass','runtimePass','gaPass')]
  for section,key in paths:
   changed=copy.deepcopy(baseline);changed[section][key]=0
   raw=(json.dumps(changed,indent=2)+'\n').encode();fake=self.work/'binding';fake.write_bytes(raw)
   seal=json.loads((HERE/'seal.json').read_bytes())
   for row in seal['members']:
    if row['path']=='binding.json':row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
   seal['tree_sha256']=self.base.tree(seal['members']);fake_seal=self.work/'seal';fake_seal.write_text(json.dumps(seal))
   def redirect(p):return original(fake if p==HERE/'binding.json' else fake_seal if p==HERE/'seal.json' else p)
   with self.subTest(section=section,key=key),patched(self.base,'regular',redirect),self.assertRaises(RuntimeError):self.base.verify(True)
