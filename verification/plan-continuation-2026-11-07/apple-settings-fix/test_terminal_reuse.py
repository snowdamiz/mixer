#!/usr/bin/env python3
"""Behavior tests using retained V9 bytes; none is a new native receipt."""
import copy, hashlib, importlib.util, json, pathlib, shutil, sys, tempfile, unittest
HERE=pathlib.Path(__file__).resolve().parent
RUNTIME=HERE/'baseline-runtime/inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation'
sys.path.insert(0,str(RUNTIME))
import settings_telemetry as baseline
import durable_settings
import replay
spec=importlib.util.spec_from_file_location('candidate_settings',HERE/'candidate/settings_telemetry.py')
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
actual=HERE.parent/'apple-runtime'
actual_result=json.loads((actual/'result.json').read_text())
CAPTURES=actual/actual_result['artifacts']['rawCaptures']
ROWS=[json.loads(p.read_text()) for p in sorted(CAPTURES.glob('0000-settings-*.json'))]
TERMINAL=next(r for r in ROWS if r['record'].get('stage')=='terminal')
AFTER=next(r for r in ROWS if r['record'].get('stage')=='after-switch')

class ReuseTests(unittest.TestCase):
 def setUp(self):
  self.scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-20261107-apple-settings-tests-',dir='/tmp')).resolve()
  self.clock=[ROWS[0]['receivedUptime']]
  self.store=durable_settings.TransactionStore(self.scratch,ROWS[0]['ownedSimulatorIdentity'])
  self.session=candidate.Session(None,None,ROWS[0]['sessionDeadlineUptime'],now=lambda:self.clock[0],token=ROWS[0]['generation'],transaction=self.store)
 def tearDown(self):
  shutil.rmtree(self.scratch)
  assert not self.scratch.exists()
 def feed(self,row,session=None):
  self.clock[0]=row['receivedUptime'];return (session or self.session).request(copy.deepcopy(row['record']))
 def before_terminal(self):
  for row in ROWS:
   if row is TERMINAL:break
   self.feed(row)
 def terminal_without_redundant_chunks(self):
  self.before_terminal();response=self.feed(TERMINAL)
  self.assertEqual(response['pending'],['settings-0131-ax'])
  for row in ROWS:
   r=row['record']
   if r.get('sequence',0)>131 and r.get('slot')=='settings-0131-ax':self.feed(row)
  return self.session.summary()
 def test_baseline_remains_incomplete_at_original_29_second_limit(self):
  session=baseline.Session(lambda *args:None,lambda *args:None,ROWS[0]['sessionDeadlineUptime'],now=lambda:self.clock[0],token=ROWS[0]['generation'])
  for row in ROWS:self.feed(row,session)
  state=session.summary();self.assertFalse(state['setupObservationSatisfied'])
  self.assertEqual(state['pendingSlots'],['settings-0131-png'])
  self.assertEqual(len(session.uploads['settings-0131-png']['parts']),23)
  self.assertEqual(baseline.MAX_DURATION,candidate.MAX_DURATION);self.assertEqual(candidate.MAX_DURATION,29)
 def test_identical_terminal_capture_published_and_replayed(self):
  self.assertEqual(AFTER['record']['files']['png'],TERMINAL['record']['files']['png'])
  summary=self.terminal_without_redundant_chunks()
  self.assertTrue(summary['settingsEvidenceComplete']);self.assertTrue(summary['setupObservationSatisfied'])
  self.assertEqual(summary['terminationMarkers'],[]);self.assertEqual(summary['completionMarkers'],[])
  # The original full-case handoff must still reject absent completion markers.
  self.assertFalse(summary['setupObservationSatisfied'] and summary['terminationMarkers']==['terminate-before','terminate-after'] and summary['completionMarkers']==['test-case-finished'])
  self.assertEqual((self.scratch/'settings-0131-png.png').read_bytes(),(CAPTURES/'settings-0083-png.png').read_bytes())
  old=replay.t
  try:
   replay.t=candidate;self.assertEqual(replay.replay(self.scratch),summary)
  finally:replay.t=old
 def test_different_digest_requires_original_chunk_path(self):
  self.before_terminal();row=copy.deepcopy(TERMINAL);row['record']['files']['png']['sha256']='0'*64
  response=self.feed(row);self.assertEqual(response['pending'],['settings-0131-ax','settings-0131-png'])
  self.assertFalse((self.scratch/'settings-0131-png.png').exists())
 def test_different_length_requires_original_chunk_path(self):
  self.before_terminal();row=copy.deepcopy(TERMINAL);row['record']['files']['png']['bytes']+=1
  self.assertEqual(self.feed(row)['pending'],['settings-0131-ax','settings-0131-png'])
 def test_corrupt_cached_bytes_rejected_without_cursor_advance(self):
  self.before_terminal();slot,payload=self.session.completed_png
  self.session.completed_png=(slot,payload[:-1]+bytes([payload[-1]^1]))
  with self.assertRaisesRegex(ValueError,'reuse identity'):self.feed(TERMINAL)
  self.assertEqual(self.session.sequence,130);self.assertIsNone(self.session.terminal)
  self.assertFalse((self.scratch/'0000-settings-0131.json').exists())
 def test_missing_prior_complete_flag_rejected(self):
  self.before_terminal();self.session.uploads[self.session.completed_png[0]]['complete']=False
  with self.assertRaisesRegex(ValueError,'reuse identity'):self.feed(TERMINAL)
  self.assertEqual(self.session.sequence,130)
 def test_early_missing_screenshot_rejected(self):
  self.before_terminal();row=copy.deepcopy(TERMINAL);del row['record']['files']['png']
  with self.assertRaisesRegex(ValueError,'Required screenshot'):self.feed(row)
  self.assertEqual(self.session.sequence,130)
 def test_late_observation_still_rejected(self):
  self.before_terminal();row=copy.deepcopy(TERMINAL);row['receivedUptime']=ROWS[0]['receivedUptime']+29.001
  with self.assertRaisesRegex(ValueError,'duration'):self.feed(row)
  self.assertEqual(self.session.sequence,130)
 def test_wrong_generation_still_rejected(self):
  self.before_terminal();row=copy.deepcopy(TERMINAL);row['record']['generation']='00000000-0000-0000-0000-000000000000'
  with self.assertRaisesRegex(ValueError,'binding'):self.feed(row)
  self.assertEqual(self.session.sequence,130)
 def test_reuse_persistence_failure_rolls_back_new_artifacts(self):
  self.before_terminal();original=self.store.io.write
  def fail(path,payload,role):
   if role=='payload':raise OSError('injected reused PNG persistence failure')
   return original(path,payload,role)
  self.store.io.write=fail
  with self.assertRaisesRegex(OSError,'injected'):self.feed(TERMINAL)
  self.assertEqual(self.session.sequence,130);self.assertIsNone(self.session.terminal)
  self.assertFalse((self.scratch/'settings-0131-png.png').exists())
  self.assertFalse((self.scratch/'0000-settings-0131.json').exists())
  self.assertFalse(durable_settings.unresolved(self.scratch))
  self.store.io.write=original
  self.assertEqual(self.feed(TERMINAL)['pending'],['settings-0131-ax'])
 def test_redundant_png_chunk_is_not_accepted_as_new_evidence(self):
  self.terminal_without_redundant_chunks()
  extra=next(row for row in ROWS if row['record'].get('slot')=='settings-0131-png')
  with self.assertRaisesRegex(ValueError,'Unexpected upload'):self.feed(extra)
  self.assertEqual(self.session.sequence,134)
 def test_replayed_terminal_file_tampering_rejected(self):
  self.terminal_without_redundant_chunks();path=self.scratch/'settings-0131-png.png';path.write_bytes(path.read_bytes()+b'x')
  old=replay.t
  try:
   replay.t=candidate
   with self.assertRaisesRegex(ValueError,'differs from journal'):replay.replay(self.scratch)
  finally:replay.t=old

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(ReuseTests)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 (HERE/'candidate-tests.json').write_text(json.dumps({'scope':'host only; retained V9 replay and injected failures','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'nativeAttempts':0,'scratchRemoved':True},indent=2)+'\n')
 sys.exit(not result.wasSuccessful())
