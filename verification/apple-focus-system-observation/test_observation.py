#!/usr/bin/env python3
"""Executable host controls; synthetic observations never claim UIKit behavior."""
import copy,hashlib,importlib.util,json,pathlib,unittest
from decimal import Decimal as D
import observation as o
H=pathlib.Path(__file__).resolve().parent

def row(seq,start,site='snapshot',context=None,item='reference',system=True,scene='absent'):
 ids=['ObjectIdentifier(0xa)','ObjectIdentifier(0xb)','ObjectIdentifier(0xc)']
 identity={'authored':ids[0],'reference':ids[1],'next':ids[2],'other':'ObjectIdentifier(0xd)',None:None}.get(item)
 matches=[identity==value for value in ids] if system else [False]*3
 item_state=('fixed' if any(matches) else 'null' if identity is None else 'other') if system else 'unavailable'
 return {'sequence':seq,'startedUptime':start,'finishedUptime':start+D('.000001'),'site':site,'contextSequence':context,'stage':'reset','environment':{'selection':'window','identity':'ObjectIdentifier(0xe)','windowIdentity':'ObjectIdentifier(0xe)'},'system':{'state':'present' if system else 'unavailable','identity':'ObjectIdentifier(0xf)' if system else None,'item':{'state':item_state,'identity':identity if system else None,'fixedMatches':matches}},'controls':[{'slot':slot,'identity':identity,'isFocused':slot=='plain-uibutton-reference','attachedToWindow':True,'windowIdentity':'ObjectIdentifier(0xe)','canBecomeFocused':True,'focusGroupIdentifier':None,'focusGroupPriority':0} for slot,identity in zip(o.SLOTS,ids)],'scene':{'state':scene,'identity':None if scene=='absent' else 'ObjectIdentifier(0x10)','systemIdentity':'ObjectIdentifier(0x11)' if scene=='present' else None,'itemIdentity':None}}
def diag(rows):return dict(schema=o.SCHEMA,authoritative=False,atomic=False,entries=rows,dropped=0,revision=len(rows),captureStatus='complete')
def fixture():
 p=H/'inputs/v7'
 b=o.loads((p/'0001-before-1.json').read_bytes())['observation'];a=o.loads((p/'0001-after-1.json').read_bytes())['observation']
 packet=o.loads((p/'0001-keyboard-witness-1.json').read_bytes());w=packet['witness'];binding=packet['binding']
 initial=row(1,b['focusContexts'][0]['uptime']+D('.00001'),'controller-callback',1)
 b['focusSystemDiagnostic']=diag([initial,row(2,binding['baselineUptime']-D('.01'))])
 rows=copy.deepcopy(b['focusSystemDiagnostic']['entries'])
 for context,item in zip(a['focusContexts'][1:],[None,'reference',None]):rows.append(row(len(rows)+1,context['uptime']+D('.00001'),'controller-callback',context['sequence'],item))
 rows.append(row(len(rows)+1,w['after']['uptime']+D('.001'),item=None));a['focusSystemDiagnostic']=diag(rows)
 original=o.loads((p/'0001-after-1.json').read_bytes())['verdict']
 expected={k:binding[k] for k in ['case','generation','actionIndex']}
 return b,a,w,binding,expected,original

class Controls(unittest.TestCase):
 def check_reject(self,mutate):
  values=fixture();before=o.encoded(values[-1]);mutate(*values)
  result=o.join(*values)
  self.assertTrue(result['supplemental']['captureStatus'].startswith('incomplete-'),result)
  self.assertIs(result['originalVerdict'],values[-1]);self.assertEqual(o.encoded(values[-1]),before);self.assertIs(result['supplemental']['nativePass'],False)
 def test_current_exact_join_retains_failure(self):
  v=fixture();r=o.join(*v);self.assertEqual(r['supplemental']['captureStatus'],'complete');self.assertEqual(r['supplemental']['newSequences'],[3,4,5,6]);self.assertIs(r['originalVerdict']['passed'],False);self.assertIs(r['originalVerdict']['predicates']['actualNativeFocusTraversal'],False)
 def test_every_fixed_identity_other_null_unavailable(self):
  for item in ['authored','reference','next','other',None]:
   with self.subTest(item=item):o.validate(diag([row(1,D(1),item=item)]),[])
  o.validate(diag([row(1,D(1),system=False)]),[])
 def test_windowless_controller_and_optional_scene(self):
  for scene in ['absent','unavailable','present']:
   r=row(1,D(1),system=False,scene=scene);r['environment']={'selection':'controller','identity':'ObjectIdentifier(0x20)','windowIdentity':None}
   for control in r['controls']:control.update(attachedToWindow=False,windowIdentity=None)
   o.validate(diag([r]),[])
 def test_fixed_identity_cannot_be_inferred(self):
  self.check_reject(lambda b,a,*_ :a['focusSystemDiagnostic']['entries'][-1]['system']['item'].update(state='fixed',identity='ObjectIdentifier(0xd)',fixedMatches=[True,False,False]))
 def test_duplicate_control_identity(self):
  self.check_reject(lambda b,a,*_ :a['focusSystemDiagnostic']['entries'][-1]['controls'][0].update(identity='ObjectIdentifier(0xb)'))
 def test_exact_case_generation_action(self):
  for key,value in [('case','wrong-case'),('generation',2),('actionIndex',2),('generation',True),('actionIndex',D(1))]:
   with self.subTest(key=key,value=value):self.check_reject(lambda b,a,w,binding,e,v:binding.update({key:value}))
 def test_witness_key_and_phase_unchanged(self):
  for key,value in [('key','space'),('phase','invented'),('publicAPI','synthetic'),('returned',False),('actionIndex',2)]:
   with self.subTest(key=key):self.check_reject(lambda b,a,w,*_:w.update({key:value}))
 def test_before_after_prefix_exact(self):
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][0]['controls'][0].update(isFocused=True))
 def test_reordered_and_missing_sequence(self):
  for seq in [0,3,True]:self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1].update(sequence=seq))
 def test_original_context_prefix_and_dropped(self):
  self.check_reject(lambda b,a,*_:a['focusContexts'][0].update(source='carrier'))
  self.check_reject(lambda b,a,*_:a.update(focusContextDropped=1))
  self.check_reject(lambda b,a,*_:a.update(focusContextDropped=False))
 def test_callback_exact_context_source_and_time(self):
  for change in [dict(contextSequence=1),dict(contextSequence=99),dict(site='carrier-callback'),dict(startedUptime=D(0)),dict(contextSequence=None)]:
   with self.subTest(change=change):self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][2].update(change))
 def test_missing_callback_is_incomplete(self):
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][2].update(site='snapshot',contextSequence=None))
 def test_nonfinite_nonmonotonic_and_late(self):
  for value in [D('NaN'),D('Infinity'),D('-Infinity'),D(-1),D('9999999')]:
   with self.subTest(value=value):self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1].update(finishedUptime=value))
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1].update(startedUptime=D(0)))
 def test_nonfinite_binding(self):
  self.check_reject(lambda b,a,w,binding,*_:binding.update(evaluatedUptime=D('NaN')))
 def test_decimal_comparison_has_no_float_roundtrip(self):
  t=o.loads('{"before":948790.00000000000000001,"after":948790.00000000000000002}')
  self.assertLess(t['before'],t['after']);self.assertEqual(float(t['before']),float(t['after']));self.assertIn(b'948790.00000000000000001',o.encoded(t))
 def test_closed_shapes_and_bounded_metadata(self):
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic'].update(authoritative=True))
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1].update(extra=[]))
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1]['controls'][0].update(focusGroupIdentifier='x'*129))
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1]['controls'][0].update(focusGroupPriority=2**63))
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1]['controls'].pop())
 def test_refuse_truncation_count_and_envelope(self):
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic'].update(dropped=1,captureStatus='incomplete-total-size'))
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic'].update(revision=o.LIMIT+1))
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic'].update(entries=[a['focusSystemDiagnostic']['entries'][-1]]*129))
 def test_entry_and_total_bytes(self):
  oversized=row(1,D(1));oversized['stage']='x'*4097
  with self.assertRaises(o.Incomplete):o.validate(diag([oversized]),[])
  rows=[row(n,D(n)) for n in range(1,100)]
  self.assertGreater(len(o.encoded(diag(rows))),65536)
  with self.assertRaises(o.Incomplete):o.validate(diag(rows),[])
 def test_buffer_caps_never_replace_rows_or_recover(self):
  b=o.Buffer()
  for n in range(1,129):b.append({'sequence':n,'x':n})
  kept=copy.deepcopy(b.entries);b.append({'sequence':129,'x':129});self.assertEqual(b.status,'incomplete-count');self.assertEqual(b.entries,kept);b.append({'sequence':130});self.assertEqual(b.entries,kept)
  b=o.Buffer()
  for n in range(1,129):b.append(row(n,D(n)))
  self.assertEqual(b.status,'incomplete-total-size');self.assertLess(len(b.entries),128);self.assertLessEqual(len(o.encoded(b.value())),65536)
  b=o.Buffer();b.append({'sequence':1,'x':'z'*4096});self.assertEqual(b.status,'incomplete-entry-size');self.assertEqual(b.entries,[])
  b=o.Buffer();b.revision=o.LIMIT;b.dropped=o.LIMIT;b.append({});self.assertEqual(b.status,'incomplete-counter');self.assertLessEqual(len(o.encoded(b.value())),65536)
 def test_duplicate_json_keys_and_nonfinite_json(self):
  for raw in ['{"a":1,"a":2}','{"x":NaN}','{"x":Infinity}']:
   with self.assertRaises(o.Incomplete):o.loads(raw)
 def test_missing_new_data_cannot_grant_pass(self):
  self.check_reject(lambda b,a,*_:a.pop('focusSystemDiagnostic'))
 def test_known_control_identity_stable_across_samples(self):
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1]['controls'][0].update(identity='ObjectIdentifier(0x99)'))
 def test_adapter_never_grants_pass_even_with_pass_claim(self):
  values=fixture();values[-1]['passed']=True
  result=o.join(*values);self.assertIs(result['supplemental']['nativePass'],False);self.assertIs(result['originalVerdict'],values[-1])
 def test_adapter_does_not_mutate_any_input(self):
  values=fixture();initial=[o.encoded(v) for v in values];o.join(*values);self.assertEqual(initial,[o.encoded(v) for v in values])
 def test_binary_float_diagnostic_is_incomplete(self):
  self.check_reject(lambda b,a,*_:a['focusSystemDiagnostic']['entries'][-1].update(finishedUptime=1.1))
 def test_original_v7_oracle_exact_and_enriched_still_false(self):
  p=H/'inputs/v7';b=json.loads((p/'0001-before-1.json').read_bytes());a=json.loads((p/'0001-after-1.json').read_bytes());w=json.loads((p/'0001-keyboard-witness-1.json').read_bytes())
  spec=importlib.util.spec_from_file_location('owned_frozen_keyboard_v2',H/'inputs/oracle/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
  before=copy.deepcopy(b['observation']);before.update(keyboardWitness=w['witness'],keyboardBinding=w['binding'])
  original=oracle.verdict('diagnostic',w['binding']['case'],'native-keyboard',before,a['observation'],b['signature']!=a['signature'])
  self.assertTrue(all(original[k]==a['verdict'][k] for k in original));self.assertFalse(original['passed']);self.assertEqual([k for k,v in original['predicates'].items() if not v],['actualNativeFocusTraversal'])
  enriched_b,enriched_a,*_=fixture();before['focusSystemDiagnostic']=enriched_b['focusSystemDiagnostic'];after=copy.deepcopy(a['observation']);after['focusSystemDiagnostic']=enriched_a['focusSystemDiagnostic']
  self.assertEqual(oracle.verdict('diagnostic',w['binding']['case'],'native-keyboard',before,after,True),original)

if __name__=='__main__':unittest.main(verbosity=2)
