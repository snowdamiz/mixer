"""Host integration controls for closed witnesses and fixed result-artifact export."""
import copy
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock
import composition as run
run.inherited=run.h
o=run.oracle
from test_keyboard import fixture

class WitnessBridgeControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name).resolve()
        self.docs=self.root/'Documents';self.docs.mkdir();self.case,self.before,self.after=fixture();self.before['state']['focused']=True;self.after['state']['focused']=True
        for event in self.before['events']+self.after['events']:
            if event['reason']!='startup':event['state']['focused']=True
        self.path=self.docs/'observations.json'
        self.store({k:v for k,v in self.before.items() if k not in {'keyboardWitness','keyboardBinding'}})
        self.bridge=run.inherited.Bridge({'diagnostic':self.docs,'comparator':self.docs},self.root/'captures','host-capability',{'scope':'host-only'},allowed_cases={self.case})
        self.cursor=o.Cursor(self.case)
        for command in o.CASE_COMMAND_SEQUENCE[self.case]:self.cursor.command(command)
        self.cursor.acquired=True
        self.bridge.generation=1;self.bridge.current={'case':self.case,'candidate':'diagnostic','ready':True,'nativeIdentity':self.before['state']['identity'],'commandGeneration':len(self.cursor.done_commands),'actionIndex':0,'keyboardCursor':self.cursor}
        self.bridge.keyboard_cases[self.case]=self.cursor
    def store(self,value):
        temp=self.docs/'next.json';temp.write_text(json.dumps(value));temp.replace(self.path)
    def baseline(self):
        with mock.patch.object(run.keyboard_bridge.time,'monotonic',return_value=100.5):
            return self.bridge.request('baseline',{'action':'native-keyboard','geometry':{'app':dict(x=0,y=0,width=402,height=874),'target':dict(x=303,y=244,width=63,height=44)}})
    def test_witness_persists_before_evaluation_and_replays_against_exact_capture(self):
        acknowledged=self.baseline();self.assertEqual(acknowledged['actionIndex'],1);self.store(self.after)
        w=self.before['keyboardWitness']
        original=run.transport.verdict
        def checking(*args,**kwargs):
            self.assertTrue((self.root/'captures/0001-keyboard-witness-1.json').is_file());return original(*args,**kwargs)
        with mock.patch.object(run.transport,'verdict',side_effect=checking),mock.patch.object(run.keyboard_bridge.time,'monotonic',return_value=103),mock.patch.object(run.transport.time,'sleep',return_value=None):
            result=self.bridge.request('evaluate',{'keyboardWitness':w})
        self.assertTrue(result['passed'],result);self.assertEqual(result['keyboardWitness'],w)
        before=json.loads((self.root/'captures/0001-before-1.json').read_bytes());after=json.loads((self.root/'captures/0001-after-1.json').read_bytes());bound=json.loads((self.root/'captures/0001-keyboard-witness-1.json').read_bytes())
        self.assertNotIn('keyboardWitness',before['observation'])
        exact=before['observation'];exact.update(keyboardWitness=bound['witness'],keyboardBinding=bound['binding'])
        replay=o.verdict('diagnostic',self.case,'native-keyboard',exact,after['observation'])
        self.assertEqual(replay['predicates'],result['predicates']);self.assertEqual(self.cursor.phase_index,1)
        with self.assertRaises(ValueError):self.bridge.request('evaluate',{'keyboardWitness':w})
    def test_missing_witness_fails_without_qualifying_direct_callback(self):
        self.baseline();self.store(self.after)
        with mock.patch.object(run.transport.time,'sleep',return_value=None):result=self.bridge.request('evaluate',{})
        self.assertFalse(result['passed']);self.assertTrue(self.cursor.failed)
    def test_wrong_case_generation_action_and_phase_cannot_reach_oracle(self):
        self.baseline()
        for field,value in [('case','keyboard-enabled-on'),('generation',2),('actionIndex',2),('phase','space-reverse')]:
            w=copy.deepcopy(self.before['keyboardWitness']);w[field]=value
            with mock.patch.object(run.keyboard_bridge.time,'monotonic',return_value=103),mock.patch.object(run.transport,'verdict') as verdict,self.assertRaises(ValueError):self.bridge.request('evaluate',{'keyboardWitness':w})
            verdict.assert_not_called()
        self.assertFalse((self.root/'captures/0001-keyboard-witness-1.json').exists())
    def test_no_added_endpoint_or_arbitrary_fixture_command_authority(self):
        for operation,body in [('keyboard',{}),('command',{'command':'focus'}),('command',{'command':'self-tests'}),('command',{'command':'disable'}),('command',{'command':'/tmp/path'})]:
            with self.assertRaises(ValueError):self.bridge.request(operation,body)
        self.assertEqual(o.COMMANDS,{'resume','reset','set-on','stale','disable'})
        self.assertEqual(run.inherited.Bridge.request.__code__,run.telemetry.diagnostic_bridge(run.CANONICAL_BRIDGE).request.__code__)
        self.assertIs(run.inherited.Bridge.write_command,run.transport.Bridge.write_command)

if __name__=='__main__':unittest.main(verbosity=2)
