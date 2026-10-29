#!/usr/bin/env python3
"""Original 18, three adapted binding and fresh lifecycle admission controls."""
import test_admission as original
import contextlib,io,json,sys,unittest
from pathlib import Path
from unittest import mock
import admit as a
from lifecycle_controls import LifecycleControls
HERE=Path(__file__).resolve().parent
LOCAL={'.github/workflows/hosted.yml','hosted/lib/mixer_hosted/browser_auth/store.ex'}
class HostInputBinding(unittest.TestCase):
 def test_local_only_paths_are_never_opened(self):
  seen=set();bound=a.bound
  def checked(path,row):
   name=path.relative_to(a.ROOT).as_posix();seen.add(name)
   if name in LOCAL:raise AssertionError('local preservation file opened by hosted input binding')
   return bound(path,row)
  with mock.patch.object(a,'bound',side_effect=checked):m,p,data=a.inputs()
  self.assertEqual(a.LOCAL_PRESERVATION_ONLY,LOCAL)
  self.assertEqual(len(m['protectedFiles']),11)
  self.assertEqual(set(m['protectedFiles'])-LOCAL,seen&set(m['protectedFiles']))
  self.assertEqual(len(data),136);self.assertEqual(len(p),6)
 def test_every_public_contract_binding_still_fails_closed(self):
  m,_,_=a.inputs();bound=a.bound
  for name in sorted(set(m['protectedFiles'])-LOCAL):
   with self.subTest(path=name):
    def corrupt(path,row):
     if path==a.ROOT/name:raise RuntimeError('injected authenticated input mismatch '+name)
     return bound(path,row)
    with mock.patch.object(a,'bound',side_effect=corrupt):
     with self.assertRaisesRegex(RuntimeError,'injected authenticated input mismatch'):a.inputs()
 def test_corrected_workflow_selects_this_runner_without_local_only_paths(self):
  text=(HERE/'workflow.yml').read_text()
  self.assertIn('/verification/swift-pin-bitmap-independent/',text)
  for name in LOCAL:self.assertNotIn('/'+name+'\n',text)
  for suffix in ('/root_controls.py','/admit.py run','/root-controls-result.json'):
   self.assertIn('verification/swift-pin-bitmap-lifecycle-host-admission'+suffix,text)
if __name__=='__main__':
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(original.PureAdmission),unittest.defaultTestLoader.loadTestsFromTestCase(HostInputBinding),unittest.defaultTestLoader.loadTestsFromTestCase(LifecycleControls)])
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 record={'schema':1,'status':'passed'if result.wasSuccessful()else'failed','testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'pythonVersion':sys.version,'scope':'guarded pure filesystem and mocked runner controls; no product/runtime or live custody evidence','realNestedProcessOrSignalOperations':0,'output':stream.getvalue()}
 target=HERE/'root-controls-result.json'
 if not result.wasSuccessful()and not(HERE/'first-control-failure.json').exists():(HERE/'first-control-failure.json').write_text(json.dumps(record,indent=2)+'\n')
 target.write_text(json.dumps(record,indent=2)+'\n');print(stream.getvalue());print(json.dumps({k:v for k,v in record.items()if k!='output'}));sys.exit(0 if result.wasSuccessful()else 1)
