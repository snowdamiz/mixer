"""Pure source/composition and mocked failed-command postflight controls."""
import test_admission as original  # installs denial guard before harness imports
import ast,contextlib,json,os,shutil,types,unittest
from pathlib import Path
from unittest import mock
import admit as a
import bounded_commands as r

HERE=Path(__file__).resolve().parent

def workflow_contract(text):
 job=text.split('jobs:\n',1)[1].split('    steps:\n',1)[0]
 a.need('runner.'not in job and '\n    env:'not in job,'Runner expressions cannot be job-level env')
 a.need('options: [pin-bitmap-lifecycle-v2]'in text,'Exact workflow profile')
 a.need('rustup toolchain install 1.99.0 --profile minimal'in text,'Compiler provisioning changed')
 a.need('workflow_dispatch:'in text and '\n  push:'not in text and '\n  pull_request:'not in text,'Manual workflow only')

class LifecycleControls(unittest.TestCase):
 def setUp(self):
  import tempfile
  self.work=Path(tempfile.mkdtemp(prefix='lifecycle-pure-',dir=HERE))
 def tearDown(self):shutil.rmtree(self.work)
 def fake(self,fail=None,registered=True,save_error=None):
  c=types.SimpleNamespace(receipt={'commands':[]},active=object(),saved=0)
  def run(name,*args,**kwargs):
   row={'name':name,'child_returned':True,'owned_group_gone':True}
   if registered:c.receipt['commands'].append(row)
   if fail is not None:raise fail
   return 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;\n','',row
  def save():
   c.saved+=1
   if save_error is not None:raise save_error
  c.run=run;c.save=save
  return c
 def invoke(self,c):return a.cargo_command(c,'cargo-5',['unchanged'],self.work,{},600,self.work,{'candidateFiles':dict.fromkeys(range(136))},False)
 def test_all_frozen_seals_and_complete_composition_are_enforced(self):
  m,p,data=a.inputs()
  self.assertEqual(len(data),136);self.assertEqual(len(m['overlayPaths']),4)
  self.assertEqual(m['newOverlayPaths'],[a.LIFECYCLE_MEMBER])
  for packet,expected,count in a.FROZEN_PACKETS:
   with self.subTest(packet=packet.name):
    original_sha=a.sha
    def wrong(path):return '0'*64 if path==packet/'seal.json'else original_sha(path)
    with mock.patch.object(a,'sha',side_effect=wrong):
     with self.assertRaisesRegex(RuntimeError,'Frozen packet seal changed'):a.inputs()
 def test_every_fresh_member_is_checked_before_and_after_materialization(self):
  m,p,data=a.inputs();source=self.work/'source';source.mkdir()
  for n,raw in data.items():
   target=source/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
  seen=[];bound=a.bound
  def checked(path,row):seen.append(path.relative_to(source).as_posix());return bound(path,row)
  with mock.patch.object(a,'bound',side_effect=checked):self.assertEqual(a.source_check(source,m),a.CANDIDATE)
  self.assertEqual(set(seen),set(m['candidateFiles']));self.assertEqual(len(seen),136)
  # A fresh overlay mismatch fails under the same full closure checker.
  (source/a.LIFECYCLE_MEMBER).write_bytes(b'changed')
  with self.assertRaises(RuntimeError):a.source_check(source,m)
 def test_runtime_inputs_do_not_open_local_actual_evidence(self):
  read=Path.read_bytes;forbidden=[]
  def guarded(path):
   if 'reviewed-host-slice-actual-results'in path.parts:forbidden.append(str(path));raise AssertionError('raw local CI is not runtime input')
   return read(path)
  with mock.patch.object(Path,'read_bytes',guarded):a.inputs()
  self.assertEqual(forbidden,[])
 def test_exact_plan_driver_caps_and_defaults_are_preserved(self):
  m,plan,data=a.inputs();old=json.loads((a.PACKET/'host-plan.json').read_text())
  self.assertEqual(plan,[old['firstExecutable'],*old['followupCommands']])
  self.assertEqual(a.ACTIVE_SECONDS,2500);self.assertEqual(a.CLEANUP_SECONDS,60)
  self.assertEqual((r.MAX_COMMANDS,r.OUTPUT_CAP),(7,8*1024*1024))
  self.assertEqual((HERE/'bounded_commands.py').read_bytes(),(a.ROOT/'verification/swift-pin-bitmap-host-binding-correction/bounded_commands.py').read_bytes())
  for name in ['src/experimental_swift_reactor/control.rs','src/experimental_swift_reactor/lifecycle.rs','src/experimental/frame_operations.rs']:
   if name in m['candidateFiles']:self.assertEqual(m['candidateFiles'][name],m['baselineFiles'][name])
  self.assertIn('--all-features',plan[4]['argv']);self.assertNotIn('--release',plan[4]['argv']);self.assertIn('--release',plan[5]['argv'])
  self.assertNotIn('--skip',sum([x['argv']for x in plan],[]))
 def test_profile_attempt_repository_and_host_denials(self):
  env={'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_RUN_ATTEMPT':'1','GITHUB_REPOSITORY':'snowdamiz/mixer','GITHUB_SHA':'a'*40,'MIXER_PIN_BITMAP_SELECTION':a.PROFILE,'RUNNER_TEMP':'/imaginary-host-temp'}
  with contextlib.ExitStack()as stack:
   stack.enter_context(mock.patch.object(a.platform,'system',return_value='Linux'))
   stack.enter_context(mock.patch.object(a.platform,'machine',return_value='x86_64'))
   stack.enter_context(mock.patch.object(a,'identity',return_value=[1,2,3]))
   with mock.patch.dict(os.environ,env,clear=True):self.assertEqual(a.hosted(),Path(env['RUNNER_TEMP']))
   for key,bad in [('MIXER_PIN_BITMAP_SELECTION','pin-bitmap-v1'),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_REPOSITORY','other/mixer'),('GITHUB_EVENT_NAME','push')]:
    with mock.patch.dict(os.environ,{**env,key:bad},clear=True):
     with self.assertRaises(RuntimeError):a.hosted()
 def test_workflow_is_new_manual_and_runner_context_is_step_only(self):
  text=(HERE/'workflow.yml').read_text();workflow_contract(text)
  self.assertEqual(a.WORKFLOW_PATH,'.github/workflows/swift-pin-bitmap-lifecycle-admission.yml')
  self.assertIn('/verification/swift-pin-bitmap-lifecycle-correction/',text)
  self.assertIn('${{ runner.temp }}/swift-pin-bitmap-lifecycle-v2-evidence/',text)
  with self.assertRaisesRegex(RuntimeError,'job-level env'):
   workflow_contract(text.replace('    steps:\n','    env:\n      BAD: ${{ runner.temp }}\n    steps:\n'))
 def test_success_gets_postflight_and_retains_custody_state(self):
  c=self.fake();active=c.active
  with mock.patch.object(a,'source_check',return_value=a.CANDIDATE)as post:self.invoke(c)
  post.assert_called_once();self.assertIs(c.active,active)
  self.assertEqual(c.receipt['commands'][0]['sourcePostflight'],{'attempted':True,'verified':True,'members':136})
 def test_failed_cargo_gets_postflight_without_masking_primary(self):
  primary=RuntimeError('Cargo exit 101');c=self.fake(primary);active=c.active
  with mock.patch.object(a,'source_check',return_value=a.CANDIDATE)as post:
   with self.assertRaises(RuntimeError)as caught:self.invoke(c)
  self.assertIs(caught.exception,primary);post.assert_called_once();self.assertIs(c.active,active)
  self.assertEqual(c.receipt['commands'][0]['sourceAfter'],a.CANDIDATE)
 def test_failed_postflight_records_error_without_masking_failed_cargo(self):
  primary=RuntimeError('Cargo exit 101');c=self.fake(primary);post_error=ValueError('source changed')
  with mock.patch.object(a,'source_check',side_effect=post_error):
   with self.assertRaises(RuntimeError)as caught:self.invoke(c)
  self.assertIs(caught.exception,primary)
  self.assertEqual(c.receipt['commands'][0]['sourcePostflight'],{'attempted':True,'verified':False,'error':{'type':'ValueError','message':'source changed'}})
  self.assertEqual(c.saved,1)
 def test_successful_cargo_cannot_hide_failed_postflight(self):
  c=self.fake();post_error=ValueError('source changed')
  with mock.patch.object(a,'source_check',side_effect=post_error):
   with self.assertRaises(ValueError)as caught:self.invoke(c)
  self.assertIs(caught.exception,post_error)
 def test_pre_spawn_failure_still_gets_postflight_without_fake_command(self):
  primary=RuntimeError('aggregate budget cannot fit');c=self.fake(primary,registered=False)
  with mock.patch.object(a,'source_check',return_value=a.CANDIDATE):
   with self.assertRaises(RuntimeError)as caught:self.invoke(c)
  self.assertIs(caught.exception,primary);self.assertEqual(c.receipt['commands'],[])
  self.assertTrue(c.receipt['unregisteredCargoPostflights'][0]['sourcePostflight']['verified'])
 def test_save_failure_cannot_mask_failed_cargo(self):
  primary=RuntimeError('Cargo exit 101');c=self.fake(primary,save_error=OSError('receipt sink failed'))
  with mock.patch.object(a,'source_check',return_value=a.CANDIDATE):
   with self.assertRaises(RuntimeError)as caught:self.invoke(c)
  self.assertIs(caught.exception,primary)
  self.assertEqual(c.receipt['commands'][0]['sourcePostflightReceiptError']['message'],'receipt sink failed')
 def test_nonpassing_summary_still_gets_postflight(self):
  c=self.fake();c.run=lambda *args,**kwargs:('', '', c.receipt['commands'].append({'name':'cargo-5'})or c.receipt['commands'][-1])
  with mock.patch.object(a,'source_check',return_value=a.CANDIDATE)as post:
   with self.assertRaisesRegex(RuntimeError,'Missing/nonpassing'):self.invoke(c)
  post.assert_called_once();self.assertTrue(c.receipt['commands'][0]['sourcePostflight']['verified'])
 def test_execute_postflight_precedes_removal_and_custody_hold_still_preserves(self):
  for custody in [False,True]:
   with self.subTest(custody=custody):
    temp=self.work/('held'if custody else'closed');temp.mkdir();events=[];primary=RuntimeError('Cargo exit 101');instances=[]
    class Commands:
     def __init__(self,out,receipt,deadline):self.out=out;self.receipt=receipt;self.active=None;instances.append(self);(out/'commands').mkdir()
     def bind_scratch(self,scratch):pass
     def save(self):a.save(self.out/'receipt.json',self.receipt)
     def run(self,name,*args,**kwargs):
      row={'name':name,'pid':987654321,'child_returned':not custody or name=='compiler-identity','owned_group_gone':not custody or name=='compiler-identity'};self.receipt['commands'].append(row)
      if name=='compiler-identity':return 'release: 1.99.0\nhost: x86_64-unknown-linux-gnu\n','',row
      self.active=object()if custody else None;raise primary
    checked=a.source_check;removed=shutil.rmtree
    def post(source,m):events.append('postflight');return checked(source,m)
    def remove(path):events.append('remove');return removed(path)
    with contextlib.ExitStack()as stack:
     stack.enter_context(mock.patch.object(a,'hosted',return_value=temp));stack.enter_context(mock.patch.object(a,'Commands',Commands))
     stack.enter_context(mock.patch.object(a.platform,'platform',return_value='mocked-host'))
     stack.enter_context(mock.patch.dict(os.environ,{'GITHUB_SHA':'a'*40},clear=False))
     for name in ['signal','setitimer','getsignal']:stack.enter_context(mock.patch.object(a.signal,name,return_value=None))
     stack.enter_context(mock.patch.object(a,'source_check',side_effect=post));stack.enter_context(mock.patch.object(a.shutil,'rmtree',side_effect=remove))
     with self.assertRaises(RuntimeError)as caught:a.execute()
    self.assertIs(caught.exception,primary);receipt=instances[0].receipt
    self.assertEqual(events[:3],['postflight']*3);self.assertTrue(receipt['commands'][-1]['sourcePostflight']['verified'])
    self.assertEqual(receipt['cleanup']['ownedRootsRemoved'],not custody)
    self.assertEqual(events.count('remove'),0 if custody else 3)
    self.assertEqual((temp/'swift-pin-bitmap-v1').exists(),custody)
