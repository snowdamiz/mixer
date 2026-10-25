#!/usr/bin/env python3
"""Finite host controls for F1/F2; diagnostics are synthetic, originals frozen."""
import copy
import dataclasses
import hashlib
import unittest
from decimal import Decimal as D, localcontext

import observation as o
from test_observation import fixture, fingerprints, row, diag

CONTROLS=[]

class Correction(unittest.TestCase):
 def result(self,name,values,status):
  initial=repr(copy.deepcopy(values))
  result=o.join(*values)
  actual=result['supplemental']['captureStatus']
  self.assertEqual(actual,status)
  self.assertIs(result['originalVerdict'],values[-1])
  self.assertEqual(initial,repr(values))
  self.assertIs(result['supplemental']['nativePass'],False)
  CONTROLS.append({'name':name,'expected':status,'result':result['supplemental'],
                   'originalVerdictUnchanged':True,'allInputsUnchanged':True})
  return result

 def test_exact_selected_frozen_action(self):
  values=fixture()
  result=self.result('exact original positive join',values,'complete')
  self.assertEqual(result['supplemental']['selectedOriginalAction'],'v7-first-tab')
  self.assertEqual(result['supplemental']['selectedPacketSHA256'],{k:v[1] for k,v in o.RAW_INPUTS.items()})
  self.assertFalse(result['originalVerdict']['passed'])
  self.assertEqual([k for k,v in result['originalVerdict']['predicates'].items() if v is False],['actualNativeFocusTraversal'])
  with self.assertRaises(dataclasses.FrozenInstanceError):values[4].selection='other'

 def test_reviewer_f1_ax_substitution(self):
  values=fixture();values[2]['after']['elements']['authored-toggle']['hasFocus']=True
  self.result('F1 reviewer AX hasFocus substitution',values,'incomplete-original-witness')

 def test_reviewer_f1_app_substitution(self):
  values=fixture();values[0]['state']['focused']=not values[0]['state']['focused']
  self.result('F1 reviewer before.state.focused substitution',values,'incomplete-original-before-observation')

 def test_full_observations_except_only_diagnostic(self):
  for index,path,change in [
   (0,'before extra original field',lambda value:value.update(extraOriginal=True)),
   (1,'after state label',lambda value:value['state'].update(label='Substituted')),
   (1,'after trace removal',lambda value:value.pop('events')),
  ]:
   with self.subTest(path=path):
    values=fixture();change(values[index])
    self.result(path,values,'incomplete-original-'+('before' if index==0 else 'after')+'-observation')

 def test_full_witness_endpoints(self):
  for endpoint in ['before','after']:
   for field,value in [('appForeground',False),('uptime',D('948790.5361624168'))]:
    with self.subTest(endpoint=endpoint,field=field):
     values=fixture();values[2][endpoint][field]=value
     self.result('full AX endpoint '+endpoint+'.'+field,values,'incomplete-original-witness')
   values=fixture();values[2][endpoint]['elements']['next-focus']['label']='Substituted'
   self.result('full AX endpoint '+endpoint+'.label',values,'incomplete-original-witness')
  values=fixture();values[2]['after']['elements']['authored-toggle']['hasFocus']=True
  values[-1]['keyboardWitness']=copy.deepcopy(values[2])
  self.result('witness and verdict cannot jointly substitute raw original',values,'incomplete-original-witness')

 def test_complete_binding_and_exact_decimal(self):
  for field,value in [
   ('case','other'),('generation',True),('actionIndex',D(1)),
   ('baselineUptime',D('948787.11698329100000001')),
   ('evaluatedUptime',D('948794.23105454100000001')),
   ('baselineUptime',948787.116983291),
   ('evaluatedUptime',D('948794.2310545410')),
  ]:
   with self.subTest(field=field,value=value):
    values=fixture()
    if type(value) is D and field.endswith('Uptime') and value.as_tuple().exponent < -15:
     self.assertEqual(float(value),float(values[3][field]))
     self.assertNotEqual(value,values[3][field])
    values[3][field]=value
    self.result('complete binding '+field+' '+str(value),values,'incomplete-original-binding')
  values=fixture();values[3]['extra']=True
  self.result('binding extra field',values,'incomplete-original-binding')
  values=fixture();values[3].pop('evaluatedUptime')
  self.result('binding missing evaluatedUptime',values,'incomplete-original-binding')

 def test_decimal_witness_and_observation_types(self):
  for index,field in [(2,'startedUptime'),(0,'focusContextRevision')]:
   values=fixture()
   if index==2:
    original=values[index][field]
    with localcontext() as context:
     context.prec=40;replacement=original+D('0.00000000000000001')
    self.assertEqual(float(original),float(replacement));self.assertNotEqual(original,replacement)
   else:replacement=D(values[index][field])
   values[index][field]=replacement
   self.result('exact nested numeric type '+field,values,'incomplete-original-'+('witness' if index==2 else 'before-observation'))
  self.assertFalse(o.same_json({'n':1},{'n':D(1)}))
  self.assertFalse(o.same_json({'n':True},{'n':1}))
  self.assertFalse(o.same_json({'n':D('1.0')},{'n':D('1.00')}))
  values=fixture();start=values[1]['focusSystemDiagnostic']['entries'][0]['startedUptime']
  values[1]['focusSystemDiagnostic']['entries'][0]['startedUptime']=D(str(start)+'0')
  self.assertEqual(start,values[1]['focusSystemDiagnostic']['entries'][0]['startedUptime'])
  self.result('exact diagnostic prefix Decimal representation',values,'incomplete-entry-prefix')

 def test_direct_verdict_consistency_and_full_verdict(self):
  for key,change,status in [
   ('keyboardWitness',lambda value:value['after']['elements']['authored-toggle'].update(hasFocus=True),'incomplete-verdict-witness-consistency'),
   ('keyboardBinding',lambda value:value.update(evaluatedUptime=D('948794.231054542')),'incomplete-verdict-binding-consistency'),
  ]:
   values=fixture();change(values[-1][key]);self.result('direct original verdict '+key,values,status)
  values=fixture();values[-1]['passed']=True
  self.result('claimed original pass cannot replace frozen verdict',values,'incomplete-original-verdict')

 def test_wrong_raw_input_digest_fails_selection_and_join(self):
  values=fixture();anchor=values[4]
  for role in ('before','after','witness'):
   with self.subTest(role=role):
    # Valid JSON, identical length, wrong byte digest.
    raw=getattr(anchor,role+'_packet_raw');bad=raw.replace(b'"generation":1',b'"generation":9',1)
    self.assertEqual(len(raw),len(bad));self.assertNotEqual(hashlib.sha256(raw).digest(),hashlib.sha256(bad).digest())
    raws=[anchor.before_packet_raw,anchor.after_packet_raw,anchor.witness_packet_raw]
    raws[('before','after','witness').index(role)]=bad
    with self.assertRaisesRegex(o.Incomplete,'original-action-raw-'+role):o.select_original_action('v7-first-tab',*raws)
    forged=o.OriginalActionAnchor('v7-first-tab',*raws)
    candidate=list(fixture());candidate[4]=forged
    self.result('forged anchor wrong '+role+' raw digest',candidate,'incomplete-original-action-raw-'+role)
  with self.assertRaisesRegex(o.Incomplete,'original-action-selection'):
   o.select_original_action('future-runtime',anchor.before_packet_raw,anchor.after_packet_raw,anchor.witness_packet_raw)
  candidate=list(fixture());candidate[4]=dataclasses.replace(anchor,selection='future-runtime')
  self.result('closed action selection rejects future runtime',candidate,'incomplete-original-action-selection')
  candidate=list(fixture());candidate[4]={'beforeSHA256':o.RAW_INPUTS['before'][1]}
  # Explicit invalid-anchor value has its own regular JSON fingerprint.
  self.result('caller supplied fingerprints cannot select action',candidate,'incomplete-original-action-selection')

 def test_f2_exact_reviewer_middle_reorder(self):
  values=fixture();rows=values[1]['focusSystemDiagnostic']['entries'];old=copy.deepcopy(rows)
  rows[2]['contextSequence'],rows[3]['contextSequence']=3,2
  rows[2]['startedUptime']=values[1]['focusContexts'][2]['uptime']+D('.00001')
  rows[2]['finishedUptime']=rows[2]['startedUptime']+D('.000001')
  rows[3]['startedUptime']=rows[2]['finishedUptime']+D('.000001')
  rows[3]['finishedUptime']=rows[3]['startedUptime']+D('.000001')
  self.assertEqual(rows[:2],old[:2]);self.assertEqual(rows[4:],old[4:])
  self.assertEqual([r['contextSequence'] for r in rows if r['site']!='snapshot'],[1,3,2,4])
  self.result('F2 exact reviewer two middle references and intervals',values,'incomplete-complete-context-order')

 def test_f2_later_intervals_cannot_repair_order(self):
  values=fixture();rows=values[1]['focusSystemDiagnostic']['entries']
  rows[2]['contextSequence'],rows[3]['contextSequence']=3,2
  for index,value in enumerate(rows[2:],2):
   value['startedUptime']=D('948791')+D(index)/D(100)
   value['finishedUptime']=value['startedUptime']+D('.000001')
  self.result('F2 later finite monotonic intervals retain impossible order',values,'incomplete-complete-context-order')

 def test_f2_ordered_callback_prefix_and_original_source_time(self):
  values=fixture();rows=values[1]['focusSystemDiagnostic']['entries']
  self.assertEqual([r['contextSequence'] for r in rows if r['site']!='snapshot'],[1,2,3,4])
  self.result('F2 ordered callback complete original prefix',values,'complete')
  for key,value in [('site','carrier-callback'),('startedUptime',D(0)),('contextSequence',1)]:
   values=fixture();values[1]['focusSystemDiagnostic']['entries'][2][key]=value
   result=o.join(*values)
   self.assertTrue(result['supplemental']['captureStatus'].startswith('incomplete-'))
   self.assertIs(result['supplemental']['nativePass'],False)

if __name__=='__main__':unittest.main(verbosity=2)
