#!/usr/bin/env python3
"""Offline evidence consistency, not native behavior/release authorization."""
from pathlib import Path
import copy,hashlib,json,re,sys,xml.etree.ElementTree as ET
O=Path(__file__).resolve().parents[1]
def digest(b):return hashlib.sha256(b).hexdigest()
def invariant(f):
 assert f['interface_descriptors']==38 and f['explicit_descriptors']==24 and f['inherited_descriptors']==14
 assert f['supported_explicit_descriptors']==18 and len(f['existing_unsupported_names'])==6
 assert f['new_restrictions_selected']==[] and not f['implementation_selected']
 assert f['menu_widget_action_fenced'] and not f['menu_preceding_following_batch_fenced_by_widget']
 for flag in ['unqualified_menu_text_mutation_bypass_proven','current_setTarget_retarget_bypass',
 'native_close_universally_revokes_delegate','current_proxy_has_permanent_closed_marker',
 'current_proxy_has_active_connection_identity','inherited_read_return_authority',
 'async_request_entry_guards_sufficient_for_future_native_callbacks','native_runtime_executed',
 'native_effects_proven','remote_exploit_proven','pre36_support_accepted','public_v2_accepted','ota_accepted','ga_accepted']:
  assert f[flag] is False,flag
 for flag in ['preserve_successful_synchronous_successor_return','preserve_actual_record_view_editable_selection_composition',
 'preserve_both_sdk36_guards','preserve_eight_observer_slots','preserve_successful_commit_finish_no_external_work','preserve_synchronous_input_no_replay']:
  assert f[flag] is True,flag
 assert f['host_probe_checks']==26
def inventory(i):
 raw=(O/'logs/javap-2.stdout.txt').read_text().split('Compiled from "InputConnectionWrapper.java"')[0]
 actual=[(re.search(r'(\w+)\(',decl).group(1),desc) for decl,desc in re.findall(r'  (public (?:abstract |default )?[^\n]*\([^\n]*\);)\n    descriptor: (\S+)',raw)]
 assert len(actual)==38 and [(x['name'],x['descriptor']) for x in i['methods']]==actual
 api=ET.parse(O/'official/sdk37/api-versions.xml').getroot().find("class[@name='android/view/inputmethod/InputConnection']")
 metadata={x.attrib['name']:x.attrib for x in api.findall('method')}
 for x in i['methods']:
  assert x['sdk37_metadata']==metadata[x['name']+x['descriptor']]
 assert sum(x['current_route']=='inherited_wrapper_direct_target' for x in i['methods'])==14
 assert sum(x['current_route']=='explicit_nativefield_override' for x in i['methods'])==24
collection=json.loads((O/'collection.json').read_text());checked=0
for entry in collection['sources']:
 b=(O/'inputs'/entry['path']).read_bytes();assert len(b)==entry['bytes'] and digest(b)==entry['sha256'];checked+=1
for entry in collection['official']:
 if 'path' not in entry:continue
 b=(O/entry['path']).read_bytes();assert len(b)==entry['bytes'] and digest(b)==entry['sha256'];checked+=1
official=(O/'official/aosp36/InputConnectionWrapper.java').read_bytes()
assert (O/'probe-source/android/view/inputmethod/InputConnectionWrapper.java').read_bytes()==official
assert b'Copyright (C) 2007 The Android Open Source Project' in official and b'Licensed under the Apache License, Version 2.0' in official
fixture=(O/'probe-source/dev/mixer/android/NativeAppearanceViewsV2.java').read_text()
views=(O/'inputs/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java').read_text()
def block(marker):
 start=views.index(marker);a=views.index('{',start);depth=1;i=a+1
 while depth:
  depth+=(views[i]=='{')-(views[i]=='}');i+=1
 return views[start:i]
for record,marker in zip(json.loads((O/'extracted-source.json').read_text())['blocks'],[
 'static final class Mutation {','@Override public android.view.inputmethod.InputConnection onCreateInputConnection(EditorInfo info)',
 '@Override public boolean onTextContextMenuItem(int id)']):
 b=block(marker);assert b in fixture and digest(b.encode())==record['sha256'] and len(b.encode())==record['bytes']
f=json.loads((O/'findings.json').read_text());invariant(f)
i=json.loads((O/'method-inventory.json').read_text());inventory(i)
controls=0
for key,value in [('unqualified_menu_text_mutation_bypass_proven',True),('native_close_universally_revokes_delegate',True),
 ('new_restrictions_selected',['getExtractedText(MONITOR)']),('native_runtime_executed',True),('ota_accepted',True),
 ('preserve_successful_synchronous_successor_return',False),('preserve_eight_observer_slots',False)]:
 c=copy.deepcopy(f);c[key]=value
 try:invariant(c)
 except AssertionError:controls+=1
 else:raise AssertionError('negative control escaped: '+key)
c=copy.deepcopy(i);c['methods'].pop()
try:inventory(c)
except AssertionError:controls+=1
else:raise AssertionError('missing descriptor escaped')
assert 'checks=26' in (O/'logs/probe-4.stdout.txt').read_text()
assert all(x['exit']==0 for x in json.loads((O/'probe-receipt.json').read_text())['commands'])
for s in json.loads((O/'source-index.json').read_text())['spans']:
 lines=(O/s['path']).read_text().splitlines(keepends=True)
 assert digest(''.join(lines[s['start']-1:s['end']]).encode())==s['sha256']
if '--seal' in sys.argv:
 seal=json.loads((O/'seal.json').read_text())
 for e in seal['members']:
  b=(O/e['path']).read_bytes();assert len(b)==e['bytes'] and digest(b)==e['sha256'],e['path']
 print('PASS final seal members='+str(len(seal['members'])))
print('PASS frozen source/official identities='+str(checked)+'; SDK descriptors=38; exact extracted source blocks=3; negative packet controls='+str(controls)+'; native/OTA/GA not accepted')
