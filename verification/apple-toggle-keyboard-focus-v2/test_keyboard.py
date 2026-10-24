"""V2 focus/metadata controls plus unchanged runtime tests with aligned synthetic focus fixtures."""
import copy
import importlib.util
import pathlib
import unittest
import keyboard_oracle as o
import run


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
_old=load('immutable_keyboard_controls_v1',o.PREVIOUS/'test_keyboard.py')
_base_fixture=_old.fixture

def fixture(*args,**kwargs):
    c,b,a=_base_fixture(*args,**kwargs);w=b['keyboardWitness']
    b['state']['focused']=w['before']['elements']['authored-toggle']['hasFocus']
    a['state']['focused']=w['after']['elements']['authored-toggle']['hasFocus']
    for event in a['events'][len(b['events']):]:event['state']['focused']=a['state']['focused']
    if b['state']['focused'] is not a['state']['focused']:
        a['events'].append(dict(sequence=len(a['events']),uptime=101.25,stage='host-only',reason='focus',state=copy.deepcopy(a['state'])))
    return c,b,a
_old.fixture=fixture
_adapters=load('immutable_keyboard_adapter_controls_v1',o.PREVIOUS/'test_adapters.py')
_adapters.run=run.runtime

class InheritedOracleControls(_old.OracleControls):pass
class InheritedCursorControls(_old.CursorControls):pass
class InheritedWitnessControls(_adapters.WitnessBridgeControls):pass
class InheritedExportControls(_adapters.AttachmentExportControls):pass

class V2Controls(unittest.TestCase):
    def check(self,c,b,a):return o.verdict('diagnostic',c,'native-keyboard',b,a)
    def test_before_and_after_focus_disagreement_both_directions(self):
        for phase in ['space-first','tab-reference']:
            for side in ['before','after']:
                c,b,a=fixture('enabled',False,phase);target=b['state'] if side=='before' else a['state'];target['focused']=not target['focused']
                value=self.check(c,b,a);self.assertFalse(value['passed']);self.assertFalse(value['predicates']['pairedNativeFocus'+side.title()])
    def test_authored_label_must_equal_current_app_before_and_after(self):
        for side in ['before','after']:
            c,b,a=fixture();b['keyboardWitness'][side]['elements']['authored-toggle']['label']='Changed native label'
            value=self.check(c,b,a);self.assertFalse(value['passed']);self.assertFalse(value['predicates']['authoredAXLabelMatchesApp'+side.title()])
        c,b,a=fixture()
        for side in ['before','after']:b['keyboardWitness'][side]['elements']['authored-toggle']['label']='Stable but wrong authored label'
        self.assertFalse(self.check(c,b,a)['passed'])
    def test_all_three_identifier_substitutions_are_rejected_before_and_after(self):
        for name in o.IDS:
            for side in ['before','after']:
                c,b,a=fixture();b['keyboardWitness'][side]['elements'][name]['identifier']='replacement-id';self.assertFalse(self.check(c,b,a)['passed'])
    def test_all_three_label_changes_are_rejected_before_and_after(self):
        for name in o.IDS:
            for side in ['before','after']:
                c,b,a=fixture();b['keyboardWitness'][side]['elements'][name]['label']='changed-label';value=self.check(c,b,a)
                self.assertFalse(value['passed']);self.assertFalse(value['predicates']['allFixedNativeLabelsStable'])
    def test_native_metadata_must_remain_stable_across_keys_and_commands(self):
        for name in o.IDS:
            cursor=o.Cursor('keyboard-enabled-off')
            for command in o.CASE_COMMAND_SEQUENCE[cursor.name]:cursor.command(command)
            _,b,_=fixture('enabled',False,'acquire');cursor.advance(b['keyboardWitness'])
            _,b,_=fixture();w=b['keyboardWitness'];w['before']['uptime']=111;w['after']['uptime']=112
            for side in ['before','after']:w[side]['elements'][name]['label']='changed-between-keys'
            with self.assertRaises(ValueError):cursor.advance(w)
    def test_missing_did_update_focus_signal_is_failed_not_assumed(self):
        c,b,a=fixture('enabled',False,'acquire');self.assertTrue(self.check(c,b,a)['passed'])
        a['events']=[e for e in a['events'] if e['reason']!='focus'];value=self.check(c,b,a)
        self.assertFalse(value['passed']);self.assertTrue(value['missingAppFocusUpdateSignal']);self.assertFalse(value['predicates']['appFocusUpdateSignalObserved'])
        c,b,a=fixture('enabled',False,'acquire');a['events'][-1]['state']['focused']=False;self.assertFalse(self.check(c,b,a)['passed'])
    def test_three_element_scope_rejects_nonfixed_or_unchanged_acquisition(self):
        for final in [None,'plain-uibutton-reference']:
            c,b,a=fixture('enabled',False,'acquire');w=b['keyboardWitness']
            for name in o.IDS:w['after']['elements'][name]['hasFocus']=name==final
            a['state']['focused']=False;a['events']=[e for e in a['events'] if e['reason']!='focus']
            self.assertFalse(self.check(c,b,a)['passed'])
    def test_original_root_synthetic_findings_are_rejected(self):
        c,b,a=fixture();b['state']['focused']=a['state']['focused']=False
        self.assertTrue(o.original.verdict('diagnostic',c,'native-keyboard',b,a)['passed']);self.assertFalse(self.check(c,b,a)['passed'])
        c,b,a=fixture();b['keyboardWitness']['after']['elements']['authored-toggle']['label']='changed'
        self.assertTrue(o.original.verdict('diagnostic',c,'native-keyboard',b,a)['passed']);self.assertFalse(self.check(c,b,a)['passed'])
    def test_exact_runtime_source_is_reused_and_wrapper_is_selected(self):
        self.assertIs(run.runtime.oracle,o);self.assertIs(run.runtime.transport.verdict,o.verdict)
        self.assertEqual(pathlib.Path(run.runtime.ExportingCommands.run.__code__.co_filename),o.PREVIOUS/'run.py')
        self.assertEqual(pathlib.Path(run.runtime.keyboard_bridge.keyboard_bridge.__code__.co_filename),o.PREVIOUS/'keyboard_bridge.py')
        self.assertEqual(pathlib.Path(run.runtime.inherited.cleanup.__code__.co_filename),run.runtime.PARENT/'harness.py')

if __name__=='__main__':unittest.main()
